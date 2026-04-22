from datetime import datetime

from pydantic import BaseModel, Field


class RemoteActionCreate(BaseModel):
    action_type: str
    justification: str | None = Field(default=None, max_length=300)
    expires_at: datetime | None = None


class RemoteActionStatusUpdate(BaseModel):
    computer_id: int
    status: str
    result_message: str | None = Field(default=None, max_length=500)


class RemoteActionResponse(BaseModel):
    id: int
    computer_id: int
    action_type: str
    status: str
    requested_by: str
    source_ip: str | None = None
    justification: str | None = None
    payload: dict | None = None
    result_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True
