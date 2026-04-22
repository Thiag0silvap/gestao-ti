from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text

from app.database import Base


class RemoteAction(Base):
    __tablename__ = "remote_actions"

    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    action_type = Column(String(40), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True, server_default=text("'pending'"))
    requested_by = Column(String(100), nullable=False)
    source_ip = Column(String(50), nullable=True)
    justification = Column(String(300), nullable=True)
    payload_json = Column(String(1000), nullable=True)
    result_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("GETDATE()"))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
