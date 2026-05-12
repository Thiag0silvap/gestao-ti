import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
from datetime import datetime

async def debug_all_logs():
    async with AsyncSessionLocal() as db:
        print(f"--- DEBUG ALL AUDIT LOGS ---")
        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)
        result = await db.execute(query)
        logs = result.scalars().all()
        
        if not logs:
            print("Nenhum log de auditoria encontrado na tabela.")
            return

        for log in logs:
            print(f"ID: {log.id} | Data: {log.created_at} | Action: {log.action} | User: {log.username} | IP: {log.ip_address}")

if __name__ == "__main__":
    asyncio.run(debug_all_logs())
