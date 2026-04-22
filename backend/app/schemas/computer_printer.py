from datetime import datetime

from pydantic import BaseModel


class ComputerPrinterBase(BaseModel):
    name: str
    driver_name: str | None = None
    port_name: str | None = None
    server_name: str | None = None
    share_name: str | None = None
    location: str | None = None
    is_default: bool | None = None
    is_network: bool | None = None
    is_shared: bool | None = None
    status: str | None = None
    source: str | None = None


class ComputerPrinterCreate(ComputerPrinterBase):
    pass


class ComputerPrinterResponse(ComputerPrinterBase):
    id: int
    computer_id: int
    last_seen: datetime | None = None

    class Config:
        from_attributes = True
