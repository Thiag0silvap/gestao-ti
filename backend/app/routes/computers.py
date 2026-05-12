from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.computer_identity import find_computer_by_identity, should_update_sector
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.computer_printer import ComputerPrinter
from app.models.operational_event import OperationalEvent
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.monitoring import classify_computer_severity
from app.schemas.computer import ComputerCreate
from app.services.audit_service import log_action

router = APIRouter()


def serialize_computer(computer: Computer) -> dict:
    payload = {
        column.name: getattr(computer, column.name)
        for column in Computer.__table__.columns
    }
    payload["health_status"] = classify_computer_severity(computer)
    return payload


def apply_computer_payload(computer: Computer, data: ComputerCreate, preserve_existing_sector: bool = False) -> None:
    for key, value in data.model_dump(exclude={"printers"}).items():
        if key == "sector" and preserve_existing_sector and not should_update_sector(computer.sector, value):
            continue
        setattr(computer, key, value)


@router.post("/computers")
async def create_or_update_computer(
    data: ComputerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    identity_match = await find_computer_by_identity(db, data)
    computer = identity_match.computer

    if computer:
        apply_computer_payload(computer, data)
        computer.last_seen = datetime.now()

        await db.commit()
        await db.refresh(computer)

        return {
            "message": "Computador atualizado",
            "computer": serialize_computer(computer)
        }

    new_computer = Computer(**data.model_dump(exclude={"printers"}))
    new_computer.last_seen = datetime.now()

    db.add(new_computer)
    await db.commit()
    await db.refresh(new_computer)

    return {
        "message": "Computador cadastrado",
        "computer": serialize_computer(new_computer)
    }


@router.get("/computers")
async def list_computers(
    sector: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Computer)

    if sector:
        stmt = stmt.filter(Computer.sector == sector)

    result = await db.execute(stmt)
    computers = result.scalars().all()
    return [serialize_computer(computer) for computer in computers]


@router.get("/computers/{computer_id}")
async def get_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    return serialize_computer(computer)


@router.get("/computers/{computer_id}/assets")
async def get_computer_assets(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    result_assets = await db.execute(select(Asset).filter(Asset.computer_id == computer_id))
    return result_assets.scalars().all()


@router.get("/computers/{computer_id}/printers")
async def get_computer_printers(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    stmt = (
        select(ComputerPrinter)
        .filter(ComputerPrinter.computer_id == computer_id)
        .order_by(ComputerPrinter.is_default.desc(), ComputerPrinter.name.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/computers/{computer_id}/metrics")
async def get_computer_metrics(
    computer_id: int,
    limit: int = Query(default=24, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    stmt = (
        select(SystemMetric)
        .filter(SystemMetric.computer_id == computer_id)
        .order_by(SystemMetric.sampled_at.desc(), SystemMetric.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = list(result.scalars().all())
    metrics.reverse()

    return [
        {
            "id": metric.id,
            "cpu_usage_percent": metric.cpu_usage_percent,
            "memory_usage_percent": metric.memory_usage_percent,
            "disk_free_gb": metric.disk_free_gb,
            "disk_free_percent": metric.disk_free_percent,
            "uptime_hours": metric.uptime_hours,
            "sampled_at": metric.sampled_at,
        }
        for metric in metrics
    ]


@router.get("/computers/{computer_id}/events")
async def get_computer_events(
    computer_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    stmt = (
        select(OperationalEvent)
        .filter(OperationalEvent.computer_id == computer_id)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": event.id,
            "computer_id": event.computer_id,
            "severity": event.severity,
            "event_type": event.event_type,
            "metric": event.metric,
            "title": event.title,
            "message": event.message,
            "created_at": event.created_at,
        }
        for event in events
    ]


@router.put("/computers/{computer_id}")
async def update_computer(
    computer_id: int,
    data: ComputerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    apply_computer_payload(computer, data)

    await db.commit()
    await db.refresh(computer)

    await log_action(
        db,
        "COMPUTER_UPDATED",
        user=current_user,
        entity_type="COMPUTER",
        entity_id=computer.id,
        request=request,
        details={"hostname": computer.hostname, "sector": computer.sector}
    )
    await db.commit()

    return serialize_computer(computer)


@router.delete("/computers/{computer_id}")
async def delete_computer(
    computer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result.scalars().first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    await log_action(
        db,
        "COMPUTER_DELETED",
        user=current_user,
        entity_type="COMPUTER",
        entity_id=computer.id,
        request=request,
        details={"hostname": computer.hostname}
    )
    await db.delete(computer)
    await db.commit()

    return {"message": "Computador deletado com sucesso"}
