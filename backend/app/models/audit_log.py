from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # Usuário (opcional para falhas de login)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(100), nullable=True)
    
    # Ação
    action = Column(String(100), nullable=False, index=True) # EX: LOGIN_SUCCESS, COMPUTER_DELETE
    entity_type = Column(String(50), nullable=True, index=True) # EX: COMPUTER, TICKET, USER
    entity_id = Column(String(100), nullable=True)
    
    # Status e Origem
    status = Column(String(20), nullable=False, default="SUCCESS") # SUCCESS, FAILURE, WARNING
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Detalhes extras (quais campos mudaram, erro ocorrido, etc)
    details = Column(JSON, nullable=True)

    # Relacionamento
    user = relationship("User", backref="audit_logs")
