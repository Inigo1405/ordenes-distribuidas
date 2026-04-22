from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
import json
import pika
import uuid
import httpx

from .schemas import LoginRequest, LogoutRequest, SignupRequest, OrderCreate
from .redis_client import redis_client
from .services.auth_client import send_auth
from .services.rabbit import get_channel
from .config import AUTH_URL


app = FastAPI()

channel = get_channel()

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Valida el token JWT consultando al auth-service y retorna el payload del usuario."""
    token = credentials.credentials
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.post(
                f"{AUTH_URL}/internal/verify",
                params={"token": token}
            )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Token inválido o expirado.")
        return r.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")

@app.get("/health")
async def health():
    return {"status": "La API gateway está en funcionamiento. =D"}


@app.post("/orders")
async def create_order(order: OrderCreate, x_request_id: str | None = Header(default=None), current_user: dict = Depends(get_current_user)):
    request_id = x_request_id or str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    user_email = current_user["email"]
    redis_client.set(order_id, "RECEIVED")
    created_at = datetime.now(timezone.utc).isoformat()

    redis_client.hset(f"order:{order_id}", mapping={
        "customer": order.customer,
        "items": json.dumps([i.dict() for i in order.items]),
        "created_at": created_at,
        "owner_email": user_email
    })

    payload = {
        "request_id": request_id,
        "order_id": order_id,
        "customer": order.customer,
        "items": [i.dict() for i in order.items],
        "created_at": created_at,
        "owner_email": user_email
    }

    try:
        channel.basic_publish(
            exchange="orders",
            routing_key="order.created", # Topic key
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,     # Mensaje persistente
                content_type="application/json"
            )
        )
        
        return {"order_id": order_id, "status": redis_client.get(order_id), "owner": user_email}
        
    except Exception as e:
        redis_client.set(order_id, "FAILED")
        return {
            "order_id": order_id,
            "status": redis_client.get(order_id),
            "error": str(e)
        }


@app.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    status = redis_client.get(order_id)
 
    if status is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
 
    order_data = redis_client.hgetall(f"order:{order_id}")
 
    owner_email = order_data.get("owner_email")
    is_admin = current_user.get("role") == "admin"
 
    if not is_admin and current_user["email"] != owner_email:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta orden.")
 
    return {
        "order_id": order_id,
        "status": status,
        "data": order_data
    }

@app.get("/orders")
async def list_orders(current_user: dict = Depends(get_current_user)):
    """Lista órdenes: admin ve todas, usuario normal solo ve las suyas."""
    is_admin = current_user.get("role") == "admin"
    user_email = current_user["email"]
 
    order_keys = redis_client.keys("order:*")
    orders = []
 
    for key in order_keys:
        order_id = key.replace("order:", "") if isinstance(key, str) else key.decode().replace("order:", "")
        order_data = redis_client.hgetall(key)
        owner_email = order_data.get("owner_email") if isinstance(list(order_data.keys())[0] if order_data else "", str) else order_data.get(b"owner_email", b"").decode()
 
        if is_admin or owner_email == user_email:
            status = redis_client.get(order_id)
            orders.append({
                "order_id": order_id,
                "status": status,
                "data": order_data
            })
 
    return {"orders": orders, "total": len(orders)}


@app.get("/auth/health")
async def auth_health():
    send_auth()
    url = f"{AUTH_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(url)
        r.raise_for_status()
        return r.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")


@app.post("/auth/signup")
async def auth_signup(data: SignupRequest):
    url = f"{AUTH_URL}/internal/signup"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.post(
                url,
                json=data.dict()
            )
        if r.status_code >= 400:
            return {"error": r.json().get("detail", "Error en auth service"), "status_code": r.status_code}
        return r.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")


@app.post("/auth/login")
async def auth_login(data: LoginRequest):
    url = f"{AUTH_URL}/login"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.post(
                url,
                json=data.dict()
            )
        r.raise_for_status()
        return r.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")


@app.post("/auth/logout")
async def auth_logout(data: LogoutRequest):
    url = f"{AUTH_URL}/internal/logout"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.post(
                url,
                json=data.dict()
            )
        r.raise_for_status()
        return r.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")
    
