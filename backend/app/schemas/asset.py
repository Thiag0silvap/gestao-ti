from datetime import datetime
from pydantic import BaseModel


class AssetBase(BaseModel):
    computer_id: int | None = None
    asset_type: str
    patrimony_number: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    asset_status: str | None = None
    sector: str | None = None
    notes: str | None = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(AssetBase):
    pass


class AssetResponse(AssetBase):
    id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True