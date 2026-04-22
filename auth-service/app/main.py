import jwt
import os
import hmac
import asyncio
import logging
import hashlib
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from .models import User
from .schemas import LoginRequest, LogoutRequest, SignupRequest
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

      if user is None or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

      access_token = create_access_token(data={"user": user.email, "name": user.name})
      redis_client.set(f"token:{access_token}", user.email, ex=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
      
      return {
        "message": "Login exitoso.",
        "user": {"email": user.email, "name": user.name},
        "access_token": access_token, "token_type": "bearer"
      }
      
  except HTTPException:
    raise
  
  except Exception as e:
    logger.exception(f"Error en el endpoint de login: {e}")
    raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.post("/internal/logout")
async def logout(data: LogoutRequest):
  
  return {"message": "Logout exitoso."}


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
        email=data.email
      )
      session.add(new_user)
      await session.commit()

      return {
        "message": "Usuario creado exitosamente.",
        "user": new_user.email
      }
    
  except HTTPException:
    raise
  
  except Exception as e:
    logger.exception(f"Error en el endpoint de signup: {e}")
    raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.post("/internal/refresh")
def refresh(token):
  try:
    pass
  
  except jwt.ExpiredSignatureError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El refresh token ha expirado. Inicia sesión de nuevo.")
  
  except jwt.InvalidTokenError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido.")
  



def create_access_token(data: dict, expires_delta: timedelta | None = None):
  to_encode = data.copy()
  
  expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
  to_encode.update({"exp": expire}) 
  
  encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
  
  return encoded_jwt


def verify_token(token: str = Depends(oauth2_scheme)):
  try:
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
    return payload
  
  except jwt.ExpiredSignatureError:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED, 
      detail="El token ha expirado",
      headers={"WWW-Authenticate": "Bearer"},
    )
  
  except jwt.InvalidTokenError:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED, 
      detail="Token inválido",
      headers={"WWW-Authenticate": "Bearer"},
    )
  
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