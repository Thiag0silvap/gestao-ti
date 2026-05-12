from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.audit_service import log_action

router = APIRouter()


@router.post("/assets")
async def create_asset(
    data: AssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.computer_id:
        result_comp = await db.execute(select(Computer).filter(Computer.id == data.computer_id))
        computer = result_comp.scalars().first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    asset = Asset(**data.model_dump())

    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    await log_action(
        db,
        "ASSET_CREATED",
        user=current_user,
        entity_type="ASSET",
        entity_id=asset.id,
        request=request,
        details={"name": asset.name, "type": asset.asset_type}
    )
    await db.commit()

    return asset


@router.get("/assets")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Asset))
    return result.scalars().all()


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalars().first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    return asset


@router.put("/assets/{asset_id}")
async def update_asset(
    asset_id: int,
    data: AssetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalars().first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    if data.computer_id:
        result_comp = await db.execute(select(Computer).filter(Computer.id == data.computer_id))
        computer = result_comp.scalars().first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    for key, value in data.model_dump().items():
        setattr(asset, key, value)

    await db.commit()
    await db.refresh(asset)

    await log_action(
        db,
        "ASSET_UPDATED",
        user=current_user,
        entity_type="ASSET",
        entity_id=asset.id,
        request=request,
        details={"name": asset.name}
    )
    await db.commit()

    return asset


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalars().first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    await log_action(
        db,
        "ASSET_DELETED",
        user=current_user,
        entity_type="ASSET",
        entity_id=asset.id,
        request=request,
        details={"name": asset.name}
    )
    await db.delete(asset)
    await db.commit()

    return {"message": "Ativo deletado com sucesso"}