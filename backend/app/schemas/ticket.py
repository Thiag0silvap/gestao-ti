from datetime import datetime
from pydantic import BaseModel


class TicketBase(BaseModel):
    title: str
    description: str
    status: str = "Aberto"
    priority: str = "Média"
    assigned_to_id: int | None = None
    computer_id: int | None = None
    sector: str | None = None


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = "Média"
    assigned_to_id: int | None = None
    computer_id: int | None = None


class TicketUpdate(BaseModel):
    title: str
    description: str
    status: str
    priority: str
    assigned_to_id: int | None = None
    computer_id: int | None = None
    sector: str | None = None
    closed_at: datetime | None = None


class TicketResponse(TicketBase):
    id: int
    requester_id: int
    created_at: datetime | None = None
    closed_at: datetime | None = None

    class Config:
        from_attributes = True