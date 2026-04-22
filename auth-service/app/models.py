from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()

class User(Base):
  """Tabla de usuarios"""

  __tablename__ = "users"


  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255), nullable=False)
  password = Column(String(255), nullable=False)
  email = Column(String(255), unique=True, nullable=False)
  role = Column(String(50), nullable=False, default="user")
  created_at = Column(DateTime, default=datetime.utcnow)
  