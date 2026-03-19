from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
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
        for key, value in data.model_dump().items():
            setattr(computer, key, value)

        computer.last_seen = datetime.now()

        db.commit()
        db.refresh(computer)

        return {
            "message": "Computador atualizado",
            "computer": computer
        }

    new_computer = Computer(**data.model_dump())
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

    for key, value in data.model_dump().items():
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