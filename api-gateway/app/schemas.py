from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    sku: str
    qty: int

class OrderCreate(BaseModel):
    customer: str
    items: List[Item]



""" Schemas para autenticación"""
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str