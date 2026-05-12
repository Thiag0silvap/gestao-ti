from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from app.models.audit_log import AuditLog
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

async def log_action(
    db: AsyncSession | None = None,
    action: str = "UNKNOWN",
    user: User | None = None,
    username: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    status: str = "SUCCESS",
    details: dict | None = None,
    request: Request | None = None
) -> AuditLog | None:
    """
    Grava um log de auditoria no banco de dados.
    Se 'db' não for fornecido, cria uma nova sessão independente e faz o commit.
    """
    from app.database import AsyncSessionLocal
    
    local_db = db
    should_close = False
    
    if local_db is None:
        local_db = AsyncSessionLocal()
        should_close = True

    try:
        ip_address = None
        user_agent = None
        
        if request:
            # Tentar pegar IP de headers de proxy ou direto
            ip_address = request.headers.get("x-forwarded-for") or request.client.host
            user_agent = request.headers.get("user-agent")

        # Prioridade para o username:
        # 1. Parâmetro explícito username
        # 2. Objeto user
        # 3. Username nos detalhes (fallback para login)
        # 4. anonymous
        effective_username = username
        if not effective_username and user:
            effective_username = user.username
        if not effective_username and details and "username" in details:
            effective_username = details["username"]
        if not effective_username:
            effective_username = "anonymous"

        new_log = AuditLog(
            user_id=user.id if user else None,
            username=effective_username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )

        local_db.add(new_log)
        
        if should_close:
            await local_db.commit()
            await local_db.refresh(new_log)
        else:
            await local_db.flush()
        
        return new_log
    except Exception as e:
        # Logs de auditoria não devem travar a aplicação se falharem
        logger.error(f"Erro ao gravar log de auditoria: {e}")
        if should_close:
            await local_db.rollback()
        return None
    finally:
        if should_close:
            await local_db.close()
