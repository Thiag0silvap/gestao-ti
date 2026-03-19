from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    name: str
    username: str
    role: str
    sector: str | None = None
    is_active: bool = True


class UserCreate(BaseModel):
    name: str
    username: str
    password: str | None = None
    role: str
    sector: str | None = None
    is_active: bool = True


class UserResponse(UserBase):
    id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True