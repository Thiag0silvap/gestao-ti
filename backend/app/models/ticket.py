from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=False)
    status = Column(String(50), nullable=False, server_default="Aberto")
    priority = Column(String(50), nullable=False, server_default="Média")
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=True)
    sector = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("GETDATE()"))
    closed_at = Column(DateTime, nullable=True)