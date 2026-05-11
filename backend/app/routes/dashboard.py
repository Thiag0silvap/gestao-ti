from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.computer_printer import ComputerPrinter
from app.models.operational_event import OperationalEvent
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.monitoring import OFFLINE_AFTER, classify_computer_severity

router = APIRouter()


@router.get("/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Total de computadores
    result_total_comp = await db.execute(select(func.count()).select_from(Computer))
    total_computers = result_total_comp.scalar()

    # Total de ativos
    result_total_assets = await db.execute(select(func.count()).select_from(Asset))
    total_assets = result_total_assets.scalar()

    recent_limit = datetime.now() - OFFLINE_AFTER

    # Online recentemente
    result_online = await db.execute(
        select(func.count()).select_from(Computer).filter(
            Computer.last_seen != None,
            Computer.last_seen >= recent_limit
        )
    )
    online_recently = result_online.scalar()

    # Offline recentemente
    result_offline = await db.execute(
        select(func.count()).select_from(Computer).filter(
            (Computer.last_seen == None) | (Computer.last_seen < recent_limit)
        )
    )
    offline_recently = result_offline.scalar()

    # Contagem de ativos por tipo
    result_monitors = await db.execute(select(func.count()).select_from(Asset).filter(Asset.asset_type == "Monitor"))
    monitors = result_monitors.scalar()

    result_nobreaks = await db.execute(select(func.count()).select_from(Asset).filter(Asset.asset_type == "Nobreak"))
    nobreaks = result_nobreaks.scalar()

    result_stabilizers = await db.execute(select(func.count()).select_from(Asset).filter(Asset.asset_type == "Estabilizador"))
    stabilizers = result_stabilizers.scalar()

    result_printers = await db.execute(select(func.count()).select_from(ComputerPrinter))
    printers = result_printers.scalar()

    # Métricas recentes (CPU, Memória, Disco)
    # Nota: Em bases grandes, essa query pode ser otimizada.
    result_metrics = await db.execute(
        select(SystemMetric)
        .order_by(SystemMetric.computer_id.asc(), SystemMetric.sampled_at.desc(), SystemMetric.id.desc())
    )
    metrics = result_metrics.scalars().all()

    latest_metrics = {}
    for metric in metrics:
        latest_metrics.setdefault(metric.computer_id, metric)

    metric_values = list(latest_metrics.values())

    average_cpu_usage = round(
        sum(metric.cpu_usage_percent for metric in metric_values if metric.cpu_usage_percent is not None)
        / max(1, len([metric for metric in metric_values if metric.cpu_usage_percent is not None])),
        1,
    ) if metric_values else 0

    average_memory_usage = round(
        sum(metric.memory_usage_percent for metric in metric_values if metric.memory_usage_percent is not None)
        / max(1, len([metric for metric in metric_values if metric.memory_usage_percent is not None])),
        1,
    ) if metric_values else 0

    hosts_with_high_cpu = sum(
        1 for metric in metric_values
        if metric.cpu_usage_percent is not None and metric.cpu_usage_percent >= 85
    )

    hosts_with_low_disk = sum(
        1 for metric in metric_values
        if metric.disk_free_percent is not None and metric.disk_free_percent <= 15
    )

    healthy_hosts = 0
    warning_hosts = 0
    critical_hosts = 0
    offline_hosts = 0
    agent_offline_queue_hosts = 0
    agent_offline_queue_items = 0
    agent_failure_hosts = 0
    agent_updating_hosts = 0
    agent_without_telemetry = 0
    risky_hosts = []

    # Processamento de computadores e severidade
    result_computers = await db.execute(select(Computer))
    computers = result_computers.scalars().all()
    
    for computer in computers:
        severity = classify_computer_severity(computer)
        agent_queue_size = computer.agent_offline_queue_size or 0
        agent_state = (computer.agent_state or "").lower()

        if severity == "healthy":
            healthy_hosts += 1
        elif severity == "warning":
            warning_hosts += 1
        elif severity == "critical":
            critical_hosts += 1
        else:
            offline_hosts += 1

        if agent_queue_size > 0:
            agent_offline_queue_hosts += 1
            agent_offline_queue_items += agent_queue_size

        if (computer.agent_consecutive_failures or 0) > 0 or computer.agent_last_error_message:
            agent_failure_hosts += 1

        if agent_state == "updating":
            agent_updating_hosts += 1

        if not computer.agent_id and not computer.agent_version:
            agent_without_telemetry += 1

        if severity in {"warning", "critical", "offline"}:
            risky_hosts.append({
                "id": computer.id,
                "hostname": computer.hostname,
                "severity": severity,
                "cpu_usage_percent": computer.cpu_usage_percent,
                "memory_usage_percent": computer.memory_usage_percent,
                "disk_free_percent": computer.disk_free_percent,
                "last_seen": computer.last_seen,
            })

    severity_order = {"critical": 0, "warning": 1, "offline": 2}
    risky_hosts.sort(key=lambda host: (severity_order.get(host["severity"], 9), host["hostname"]))

    # Eventos recentes com Join
    result_recent_events = await db.execute(
        select(OperationalEvent, Computer.hostname)
        .join(Computer, Computer.id == OperationalEvent.computer_id)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(8)
    )
    recent_events_rows = result_recent_events.all()

    return {
        "total_computers": total_computers,
        "online_recently": online_recently,
        "offline_recently": offline_recently,
        "total_assets": total_assets,
        "average_cpu_usage": average_cpu_usage,
        "average_memory_usage": average_memory_usage,
        "hosts_with_high_cpu": hosts_with_high_cpu,
        "hosts_with_low_disk": hosts_with_low_disk,
        "healthy_hosts": healthy_hosts,
        "warning_hosts": warning_hosts,
        "critical_hosts": critical_hosts,
        "offline_hosts": offline_hosts,
        "agent_offline_queue_hosts": agent_offline_queue_hosts,
        "agent_offline_queue_items": agent_offline_queue_items,
        "agent_failure_hosts": agent_failure_hosts,
        "agent_updating_hosts": agent_updating_hosts,
        "agent_without_telemetry": agent_without_telemetry,
        "top_risky_hosts": risky_hosts[:5],
        "recent_events": [
            {
                "id": event.id,
                "computer_id": event.computer_id,
                "hostname": hostname,
                "severity": event.severity,
                "event_type": event.event_type,
                "metric": event.metric,
                "title": event.title,
                "message": event.message,
                "created_at": event.created_at,
            }
            for event, hostname in recent_events_rows
        ],
        "monitors": monitors,
        "nobreaks": nobreaks,
        "stabilizers": stabilizers,
        "printers": printers
    }
