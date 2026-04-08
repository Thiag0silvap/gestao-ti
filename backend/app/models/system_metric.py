from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, text

from app.database import Base


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    disk_free_percent = Column(Float, nullable=True)
    uptime_hours = Column(Float, nullable=True)
    sampled_at = Column(DateTime, nullable=False, server_default=text("GETDATE()"))
