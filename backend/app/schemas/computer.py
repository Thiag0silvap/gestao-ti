from datetime import date, datetime
from pydantic import BaseModel


class ComputerBase(BaseModel):
    hostname: str
    user: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    cpu: str | None = None
    ram: str | None = None
    disk: str | None = None
    os: str | None = None
    sector: str | None = None

    patrimony_number: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    equipment_status: str | None = None
    last_maintenance_date: date | None = None
    notes: str | None = None


class ComputerCreate(ComputerBase):
    pass


class ComputerUpdate(ComputerBase):
    pass


class ComputerResponse(ComputerBase):
    id: int
    last_seen: datetime | None = None

    class Config:
        from_attributes = True