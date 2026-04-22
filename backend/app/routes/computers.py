from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.computer_printer import ComputerPrinter
from app.models.operational_event import OperationalEvent
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.schemas.computer import ComputerCreate

router = APIRouter()


@router.post("/computers")
def create_or_update_computer(
    data: ComputerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = None

    if data.mac_address:
        computer = db.query(Computer).filter(
            Computer.mac_address == data.mac_address
        ).first()

    if computer:
        for key, value in data.model_dump(exclude={"printers"}).items():
            setattr(computer, key, value)

        computer.last_seen = datetime.now()

        db.commit()
        db.refresh(computer)

        return {
            "message": "Computador atualizado",
            "computer": computer
        }

    new_computer = Computer(**data.model_dump(exclude={"printers"}))
    new_computer.last_seen = datetime.now()

    db.add(new_computer)
    db.commit()
    db.refresh(new_computer)

    return {
        "message": "Computador cadastrado",
        "computer": new_computer
    }


@router.get("/computers")
def list_computers(
    sector: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Computer)

    if sector:
        query = query.filter(Computer.sector == sector)

    return query.all()


@router.get("/computers/{computer_id}")
def get_computer(
    computer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    return computer


@router.get("/computers/{computer_id}/assets")
def get_computer_assets(
    computer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    assets = db.query(Asset).filter(Asset.computer_id == computer_id).all()
    return assets


@router.get("/computers/{computer_id}/printers")
def get_computer_printers(
    computer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    return (
        db.query(ComputerPrinter)
        .filter(ComputerPrinter.computer_id == computer_id)
        .order_by(ComputerPrinter.is_default.desc(), ComputerPrinter.name.asc())
        .all()
    )


@router.get("/computers/{computer_id}/metrics")
def get_computer_metrics(
    computer_id: int,
    limit: int = Query(default=24, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador nÃ£o encontrado")

    metrics = (
        db.query(SystemMetric)
        .filter(SystemMetric.computer_id == computer_id)
        .order_by(SystemMetric.sampled_at.desc(), SystemMetric.id.desc())
        .limit(limit)
        .all()
    )

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
def get_computer_events(
    computer_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    events = (
        db.query(OperationalEvent)
        .filter(OperationalEvent.computer_id == computer_id)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(limit)
        .all()
    )

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
def update_computer(
    computer_id: int,
    data: ComputerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    for key, value in data.model_dump(exclude={"printers"}).items():
        setattr(computer, key, value)

    db.commit()
    db.refresh(computer)

    return computer


@router.delete("/computers/{computer_id}")
def delete_computer(
    computer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    computer = db.query(Computer).filter(Computer.id == computer_id).first()

    if not computer:
        raise HTTPException(status_code=404, detail="Computador não encontrado")

    db.delete(computer)
    db.commit()

    return {"message": "Computador deletado com sucesso"}
