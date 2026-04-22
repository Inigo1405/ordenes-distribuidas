from pydantic import BaseModel

class SignupRequest(BaseModel):
  name: str
  email: str
  password: str
  role: str = "user" 

class LoginRequest(BaseModel):
  email: str
  password: str

class LogoutRequest(BaseModel):
  token: str
  refresh_token: str