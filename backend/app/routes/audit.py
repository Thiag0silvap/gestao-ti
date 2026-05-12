from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/logs")
async def list_audit_logs(
    action: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista os logs de auditoria do sistema. Acesso restrito a administradores.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem ver os logs.")

    stmt = select(AuditLog).order_by(desc(AuditLog.created_at))

    if action:
        stmt = stmt.filter(AuditLog.action == action)
    if username:
        stmt = stmt.filter(AuditLog.username.ilike(f"%{username}%"))

    stmt = stmt.limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "created_at": log.created_at,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "status": log.status,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details
        }
        for log in logs
    ]
