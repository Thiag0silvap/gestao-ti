from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, text

from app.database import Base


class ComputerPrinter(Base):
    __tablename__ = "computer_printers"

    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False)
    name = Column(String(255), nullable=False)
    driver_name = Column(String(255), nullable=True)
    port_name = Column(String(255), nullable=True)
    server_name = Column(String(255), nullable=True)
    share_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_default = Column(Boolean, nullable=True)
    is_network = Column(Boolean, nullable=True)
    is_shared = Column(Boolean, nullable=True)
    status = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)
    last_seen = Column(DateTime, server_default=text("GETDATE()"))
