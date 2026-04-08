from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.operational_event import OperationalEvent
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.monitoring import classify_computer_severity

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_computers = db.query(Computer).count()
    total_assets = db.query(Asset).count()

    recent_limit = datetime.now() - timedelta(days=7)

    online_recently = db.query(Computer).filter(
        Computer.last_seen != None,
        Computer.last_seen >= recent_limit
    ).count()

    offline_recently = db.query(Computer).filter(
        (Computer.last_seen == None) | (Computer.last_seen < recent_limit)
    ).count()

    monitors = db.query(Asset).filter(Asset.asset_type == "Monitor").count()
    nobreaks = db.query(Asset).filter(Asset.asset_type == "Nobreak").count()
    stabilizers = db.query(Asset).filter(Asset.asset_type == "Estabilizador").count()
    printers = db.query(Asset).filter(Asset.asset_type == "Impressora").count()

    latest_metrics = {}
    metrics = (
        db.query(SystemMetric)
        .order_by(SystemMetric.computer_id.asc(), SystemMetric.sampled_at.desc(), SystemMetric.id.desc())
        .all()
    )

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
    risky_hosts = []

    computers = db.query(Computer).all()
    for computer in computers:
        severity = classify_computer_severity(computer)

        if severity == "healthy":
            healthy_hosts += 1
        elif severity == "warning":
            warning_hosts += 1
        elif severity == "critical":
            critical_hosts += 1
        else:
            offline_hosts += 1

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

    recent_events = (
        db.query(OperationalEvent, Computer.hostname)
        .join(Computer, Computer.id == OperationalEvent.computer_id)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(8)
        .all()
    )

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
            for event, hostname in recent_events
        ],
        "monitors": monitors,
        "nobreaks": nobreaks,
        "stabilizers": stabilizers,
        "printers": printers
    }
