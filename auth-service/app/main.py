import jwt
import uuid
import os
import hmac
import asyncio
import logging
import hashlib

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from .models import User
from .schemas import LoginRequest, LogoutRequest, SignupRequest, RefreshRequest
from .db import Session, db_init
from .redis_client import redis_client
from .config import ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, PRIVATE_KEY, PUBLIC_KEY


logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



@asynccontextmanager
async def lifespan(app: FastAPI):
  try:
    await db_init()
    logger.info("Base de datos inicializada (auth-service).")
  except Exception:
    logger.exception("Error inicializando base de datos (auth-service).")
    raise
  yield


app = FastAPI(lifespan=lifespan)


@app.get("/internal/health")
def health():
  return {"status": "Sistema de autenticación funcionando!"}


@app.post("/internal/login")
async def login(data: LoginRequest):
  try:
    logger.info(f"Intentando login para email: {data.email}")
    
    async with Session() as session:  
      result = await session.execute(select(User).where(User.email == data.email))
      user = result.scalar_one_or_none()
 
      if user is None or user.password != data.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

      access_token, jti = create_access_token({
        "id": user.id,
        "email": user.email
      })

      refresh_token, refresh_jti = create_refresh_token(user.id)

      redis_client.set(f"token:{jti}", "valid", ex=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
      redis_client.set(f"token:{refresh_jti}", str(user.id), ex=7 * 24 * 3600)
      
      return {
        "message": "Login exitoso.",
        "email": user.email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
      }
      
  except HTTPException:
    raise
  
  except Exception as e:
    logger.exception(f"Error en el endpoint de login: {e}")
    raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.post("/internal/logout")
async def logout(data: LogoutRequest):
  try:
    token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
    access_jti  = payload.get("jti")

    refresh_payload = jwt.decode(refresh_token, PUBLIC_KEY, algorithms=[ALGORITHM])
    refresh_jti = refresh_payload.get("jti")

    redis_client.delete(f"token:{access_jti }")
    redis_client.delete(f"refresh:{refresh_jti}")
    
    return {"message": "Logout exitoso."}
  
  except Exception:
    raise HTTPException(status_code=401, detail="Error en logout")


@app.post("/internal/signup")
async def signup(data: SignupRequest):
  try:
    async with Session() as session:
      result = await session.execute(select(User).where(User.email == data.email))
      existing_user = result.scalar_one_or_none()

      if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe.")

      new_user = User(
        name=data.name,
        password=hash_password(data.password),
        email=data.email,
        role=data.role
      )

      try:
        session.add(new_user)
        await session.commit()
    
      except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="El usuario ya existe.")
      
      await session.refresh(new_user)

      access_token, jti = create_access_token({
        "id": new_user.id,
        "email": new_user.email
      })

      refresh_token, refresh_jti = create_refresh_token(new_user.id)

      redis_client.set(f"token:{jti}", "valid", ex=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
      redis_client.set(f"token:{refresh_jti}", str(new_user.id), ex=7 * 24 * 3600)

      return {
        "message": "Usuario creado exitosamente.",
        "user": new_user.email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
      }
    
  except HTTPException:
    raise
  
  except Exception as e:
    logger.exception(f"Error en el endpoint de signup: {e}")
    raise HTTPException(status_code=500, detail="Error interno del servidor.")
  
  
@app.post("/internal/verify")
def verify(token: str):
  payload = verify_token(token)
  return {
    "sub": payload.get("sub"),
    "email": payload.get("email"),
    "name": payload.get("name"),
    "role": payload.get("role"),
  }


@app.post("/internal/refresh")
def refresh_access_token(refresh_token: RefreshRequest):
  try:
    payload = jwt.decode(refresh_token, PUBLIC_KEY, algorithms=[ALGORITHM])

    if payload.get("type") != "refresh":
      raise HTTPException(status_code=400, detail="Token de refresh inválido")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not redis_client.exists(f"refresh:{jti}"):
      raise HTTPException(status_code=401, detail="Refresh inválido")
    
    redis_client.delete(f"refresh:{jti}")

    new_access, new_access_jti = create_access_token({
      "id": user_id,
      "email": payload.get("email")
    })

    new_refresh, new_refresh_jti = create_refresh_token(user_id)

    redis_client.set(f"token:{new_access_jti}", "valid", ex=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    redis_client.set(f"refresh:{new_refresh_jti}", user_id, ex=7*24*3600)

    return {
      "access_token": new_access,
      "refresh_token": new_refresh
    }
  
  except jwt.ExpiredSignatureError:
    raise HTTPException(status_code=401, detail="Refresh expirado")

  except jwt.InvalidTokenError:
    raise HTTPException(status_code=401, detail="Token inválido")
  



# --- TOKEN ---
def create_access_token(user_data: dict):  
  expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  jti = str(uuid.uuid4())

  to_encode = {
    "sub": str(user_data["id"]),
    "email": user_data["email"],
    "jti": jti,
    "exp": expire,
    "iat": datetime.now(timezone.utc),
    "type": "access"
  }
  
  encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
  return encoded_jwt, jti


def create_refresh_token(user_id: str):
  expire = datetime.now(timezone.utc) + timedelta(days=7)
  jti = str(uuid.uuid4())
  
  to_encode = {
    "sub": str(user_id),
    "jti": jti,
    "exp": expire,
    "iat": datetime.now(timezone.utc),
    "type": "refresh"
  }

  encoded = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
  return encoded, jti


def verify_token(token: str = Depends(oauth2_scheme)):
  try:
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
    
    jti = payload.get("jti")
    if not jti:
      raise HTTPException(status_code=401, detail="Token inválido")

    if not redis_client.exists(f"token:{jti}"):
      raise HTTPException(status_code=401, detail="Token inválido o revocado")

    return payload

  except jwt.ExpiredSignatureError:
    raise HTTPException(status_code=401, detail="Token expirado")

  except jwt.InvalidTokenError:
    raise HTTPException(status_code=401, detail="Token inválido")
  

def hash_password(plain: str) -> str:
  salt = os.urandom(32)
  key = hashlib.pbkdf2_hmac(
    "sha256",
    plain.encode("utf-8"),
    salt, 
    iterations=260_000
  )
  # Guardamos salt + hash juntos en hex para almacenarlos en la DB
  return salt.hex() + ":" + key.hex()


def verify_password(plain: str, hashed: str) -> bool:
  salt_hex, key_hex = hashed.split(":")
  salt = bytes.fromhex(salt_hex)
  key = hashlib.pbkdf2_hmac(
    "sha256",
    plain.encode("utf-8"),
    salt,
    iterations = 260_000
  )
  # compare_digest evita timing attacks
  return hmac.compare_digest(key.hex(), key_hex)



if __name__ == "__main__":
  asyncio.run(db_init())
  logger.info("Sistema de autenticación operando!")