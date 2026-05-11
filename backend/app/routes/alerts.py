from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.computer import Computer
from app.monitoring import build_computer_alerts
from app.models.user import User

router = APIRouter()


@router.get("/alerts/active")
async def active_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    severity_order = {"critical": 0, "warning": 1, "offline": 2}
    alerts = []

    result = await db.execute(select(Computer))
    computers = result.scalars().all()
    
    for computer in computers:
        for alert in build_computer_alerts(computer):
            alerts.append({
                "computer_id": computer.id,
                "hostname": computer.hostname,
                "sector": computer.sector,
                "last_seen": computer.last_seen,
                "cpu_usage_percent": computer.cpu_usage_percent,
                "memory_usage_percent": computer.memory_usage_percent,
                "disk_free_percent": computer.disk_free_percent,
                **alert,
            })

    alerts.sort(key=lambda item: (severity_order.get(item["severity"], 9), item["hostname"], item["metric"]))
    return alerts
