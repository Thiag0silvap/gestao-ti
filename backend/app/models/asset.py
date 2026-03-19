from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=True)
    asset_type = Column(String(50), nullable=False)
    patrimony_number = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    asset_status = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=text("GETDATE()"))