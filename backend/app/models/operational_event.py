from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text

from app.database import Base


class OperationalEvent(Base):
    __tablename__ = "operational_events"

    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    event_type = Column(String(50), nullable=False)
    metric = Column(String(50), nullable=True)
    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("GETDATE()"))
