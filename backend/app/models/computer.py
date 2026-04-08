from sqlalchemy import Column, Integer, String, Date, DateTime, Float
from app.database import Base


class Computer(Base):
    __tablename__ = "computers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(100), nullable=False)
    user = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    mac_address = Column(String(50), unique=True, nullable=True)
    cpu = Column(String(150), nullable=True)
    ram = Column(String(50), nullable=True)
    memory_type = Column(String(50), nullable=True)
    memory_speed = Column(String(50), nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    disk_free_percent = Column(Float, nullable=True)
    uptime_hours = Column(Float, nullable=True)
    disk = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)

    patrimony_number = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    equipment_status = Column(String(50), nullable=True)
    last_maintenance_date = Column(Date, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)
