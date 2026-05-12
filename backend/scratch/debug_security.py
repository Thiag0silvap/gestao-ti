import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
from datetime import datetime, timedelta

async def debug_audit_logs():
    async with AsyncSessionLocal() as db:
        print(f"--- DEBUG AUDIT LOGS ---")
        print(f"Hora atual do sistema: {datetime.now()}")
        
        # Pegar as últimas 15 entradas de auditoria relacionadas a login
        query = select(AuditLog).where(
            AuditLog.action.in_(["LOGIN_FAILURE", "LOGIN_BLOCKED", "LOGIN_SUCCESS"])
        ).order_by(AuditLog.created_at.desc()).limit(15)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        if not logs:
            print("Nenhum log de login encontrado.")
            return

        for log in logs:
            print(f"ID: {log.id} | Data: {log.created_at} | Action: {log.action} | User: {log.username} | IP: {log.ip_address} | Status: {log.status}")

if __name__ == "__main__":
    asyncio.run(debug_audit_logs())
