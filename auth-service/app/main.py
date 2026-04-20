import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import jwt
from datetime import datetime, timedelta

from .models import User
from .db import db_init
from .redis_client import redis_client



logger = logging.getLogger(__name__)


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


@app.get("/health")
def health():
  return {"status": "Sistema de autenticación funcionando!"}


@app.post("/login")
def login(data):
  
  return {}


@app.post("/logout")
def logout(data):
  return {}


@app.post("/signup")
def signup(data):
    try:
      # Verificar si el usuario ya existe
      existing_user = User.get_by_email(data.email)
      if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe.")

      # Crear un nuevo usuario
      new_user = User(
        email=data.email,
        password=data.password,
        name=data.name
      )
      new_user.save()

      return {"message": "Usuario creado exitosamente."}
    except Exception as e:
      logger.exception(f"Error en el endpoint de signup: {e}")
      raise HTTPException(status_code=500, detail="Error interno del servidor.")


# @app.post("/refresh")
# def refresh(data):
#   return {}


if __name__ == "__main__":
  asyncio.run(db_init())
  logger.info("Sistema de autenticación operando!")