from sqlalchemy import Column, Integer, String, Boolean, DateTime, text
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="operator")
    sector = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, nullable=False, server_default=text("GETDATE()"))