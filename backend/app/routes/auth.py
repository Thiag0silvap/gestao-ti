from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

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
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    existing_user = db.query(User).filter(
        func.lower(User.username) == data.username.lower()
    ).first()

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
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.post("/auth/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        func.lower(User.username) == form_data.username.lower()
    ).first()

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
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    users = db.query(User).all()

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
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "username": current_user.username,
        "role": current_user.role,
        "sector": current_user.sector,
        "is_active": current_user.is_active
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    existing_user = db.query(User).filter(
        func.lower(User.username) == data.username.lower(),
        User.id != user_id
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username já existe")

    user.name = data.name
    user.username = data.username.lower()
    user.role = data.role
    user.sector = data.sector
    user.is_active = data.is_active

    if data.password:
        user.password_hash = get_password_hash(data.password)

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.patch("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar seu próprio usuário")

    user.is_active = not user.is_active

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "sector": user.sector,
        "is_active": user.is_active
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir seu próprio usuário")

    db.delete(user)
    db.commit()

    return {"message": "Usuário deletado com sucesso"}