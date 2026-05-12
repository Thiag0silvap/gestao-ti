from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from app.models.audit_log import AuditLog
import logging

logger = logging.getLogger(__name__)

# Configurações de Segurança
MAX_FAILURES_USER_IP = 5
MAX_FAILURES_IP_GLOBAL = 10
WINDOW_MINUTES = 10
BLOCK_DURATION_MINUTES = 15

class SecurityService:
    @staticmethod
    async def is_blocked(db: AsyncSession, username: str, ip_address: str) -> bool:
        """
        Verifica se um login deve ser bloqueado por excesso de tentativas falhas.
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=WINDOW_MINUTES)
        
        # 1. Verificar falhas por Usuário + IP (Proteção contra brute-force direcionado)
        query_user_ip = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.action == "LOGIN_FAILURE",
                AuditLog.username == username,
                AuditLog.ip_address == ip_address,
                AuditLog.created_at >= window_start
            )
        )
        result_user_ip = await db.execute(query_user_ip)
        count_user_ip = result_user_ip.scalar() or 0
        
        if count_user_ip >= MAX_FAILURES_USER_IP:
            logger.warning(f"Bloqueio detectado: Usuário '{username}' e IP '{ip_address}' atingiram {count_user_ip} falhas.")
            return True

        # 2. Verificar falhas por IP Global (Proteção contra ataques horizontais/scanner)
        query_ip_global = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.action == "LOGIN_FAILURE",
                AuditLog.ip_address == ip_address,
                AuditLog.created_at >= window_start
            )
        )
        result_ip_global = await db.execute(query_ip_global)
        count_ip_global = result_ip_global.scalar() or 0
        
        if count_ip_global >= MAX_FAILURES_IP_GLOBAL:
            logger.warning(f"Bloqueio detectado: IP '{ip_address}' atingiu {count_ip_global} falhas globais.")
            return True

        return False

    @staticmethod
    async def get_remaining_block_time(db: AsyncSession, username: str, ip_address: str) -> int:
        """
        Retorna quanto tempo falta para o bloqueio expirar (em minutos).
        Útil para logs administrativos.
        """
        # Simplificação: assume que o último log de falha define o início do período de bloqueio
        query = select(AuditLog.created_at).where(
            and_(
                AuditLog.action == "LOGIN_FAILURE",
                or_(
                    and_(AuditLog.username == username, AuditLog.ip_address == ip_address),
                    AuditLog.ip_address == ip_address
                )
            )
        ).order_by(AuditLog.created_at.desc()).limit(1)
        
        result = await db.execute(query)
        last_failure = result.scalar()
        
        if not last_failure:
            return 0
            
        expires_at = last_failure + timedelta(minutes=BLOCK_DURATION_MINUTES)
        remaining = expires_at - datetime.now()
        
        return max(0, int(remaining.total_seconds() / 60))
