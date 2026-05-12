from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.health_service import HealthService
from app.services.metrics_service import MetricsService

router = APIRouter(tags=["Monitoring"])


@router.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Healthcheck detalhado: status do banco, pool de conexões, versão e uptime.
    """
    start_time = getattr(request.app.state, "start_time", None)
    return await HealthService.get_system_health(db, start_time)


@router.get("/metrics")
async def operational_metrics(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Métricas operacionais: agentes, chamados, alertas e uptime da plataforma.
    """
    start_time = getattr(request.app.state, "start_time", None)
    return await MetricsService.get_operational_metrics(db, start_time)

