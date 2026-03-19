from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetUpdate

router = APIRouter()


@router.post("/assets")
def create_asset(
    data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.computer_id:
        computer = db.query(Computer).filter(Computer.id == data.computer_id).first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    asset = Asset(**data.model_dump())

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.get("/assets")
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Asset).all()


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    return asset


@router.put("/assets/{asset_id}")
def update_asset(
    asset_id: int,
    data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    if data.computer_id:
        computer = db.query(Computer).filter(Computer.id == data.computer_id).first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    for key, value in data.model_dump().items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)

    return asset


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    db.delete(asset)
    db.commit()

    return {"message": "Ativo deletado com sucesso"}