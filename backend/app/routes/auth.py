from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import create_access_token
from app.core.dependencies import get_current_user
from app.core.security import get_password_hash, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate

router = APIRouter()


@router.post("/users")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(User).filter(func.lower(User.username) == data.username.lower())
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username já existe")

    if not data.password:
        raise HTTPException(status_code=400, detail="Senha é obrigatória")

    user = User(
        name=data.name,
        username=data.username.lower(),
        password_hash=get_password_hash(data.password),
        role=data.role,
        sector=data.sector,
        is_active=data.is_active
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).filter(func.lower(User.username) == form_data.username.lower())
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos"
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(select(User))
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "role": user.role,
            "sector": user.sector,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "username": current_user.username,
        "role": current_user.role,
        "sector": current_user.sector,
        "is_active": current_user.is_active
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    result_existing = await db.execute(
        select(User).filter(
            func.lower(User.username) == data.username.lower(),
            User.id != user_id
        )
    )
    existing_user = result_existing.scalars().first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username já existe")

    user.name = data.name
    user.username = data.username.lower()
    user.role = data.role
    user.sector = data.sector
    user.is_active = data.is_active

    if data.password:
        user.password_hash = get_password_hash(data.password)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.patch("/users/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar seu próprio usuário")

    user.is_active = not user.is_active

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir seu próprio usuário")

    await db.delete(user)
    await db.commit()

    return {"message": "Usuário deletado com sucesso"}