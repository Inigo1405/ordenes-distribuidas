from fastapi import FastAPI
from .redis_client import redis_client

app = FastAPI()


@app.get("/")
def root():
  return {"status": "Sistema de autenticación funcionando!"}


@app.post("/login")
def login():
  return {}


@app.post("/logout")
def logout():
  return {}


@app.post("/signup")
def signup():
  return {}


@app.post("/refresh")
def refresh():
  return {}