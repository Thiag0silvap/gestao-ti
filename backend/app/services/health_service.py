import time
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import engine

class HealthService:
    @staticmethod
    async def get_system_health(db: AsyncSession, start_time: datetime):
        """
        Coleta informações de saúde do sistema.
        """
        health_status = "healthy"
        db_status = "online"
        db_response_time = 0
        
        # 1. Verificar Banco de Dados
        start_db_check = time.time()
        try:
            # Executa uma query simples para testar a conexão
            await db.execute(text("SELECT 1"))
            db_response_time = round((time.time() - start_db_check) * 1000, 2) # em ms
        except Exception as e:
            health_status = "degraded"
            db_status = f"offline: {str(e)}"
            db_response_time = -1

        # 2. Calcular Uptime
        uptime_delta = datetime.now() - start_time
        uptime_seconds = int(uptime_delta.total_seconds())
        
        # 3. Informações do Pool (se disponível no engine)
        pool_info = {}
        try:
            if hasattr(engine, "pool"):
                pool = engine.pool
                size = pool.size()
                checkedout = pool.checkedout()
                checkedin = pool.checkedin()
                
                # Cálculo amigável
                pool_info = {
                    "pool_size_base": size,
                    "connections_in_use": checkedout,
                    "connections_idle": checkedin,
                    "total_connections": checkedout + checkedin,
                    "usage_percent": round((checkedout / size) * 100, 2) if size > 0 else 0
                }
        except:
            pool_info = {"status": "unavailable"}

        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "version": getattr(settings, "VERSION", "0.1.0"),
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(uptime_delta).split(".")[0], # Formato HH:MM:SS
            "components": {
                "database": {
                    "status": db_status,
                    "response_time_ms": db_response_time,
                    "pool": pool_info
                },
                "api": {
                    "status": "online",
                    "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        }
