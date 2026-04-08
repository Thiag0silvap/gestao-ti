from datetime import datetime


def classify_computer_severity(computer, reference: datetime | None = None) -> str:
    if not computer.last_seen:
        return "offline"

    now = reference or datetime.now()
    age_hours = (now - computer.last_seen).total_seconds() / 3600
    if age_hours > 24:
        return "offline"

    cpu = computer.cpu_usage_percent or 0
    memory = computer.memory_usage_percent or 0
    disk_free = computer.disk_free_percent if computer.disk_free_percent is not None else 100

    if cpu >= 90 or memory >= 90 or disk_free <= 10:
        return "critical"

    if cpu >= 75 or memory >= 80 or disk_free <= 20:
        return "warning"

    return "healthy"


def build_computer_alerts(computer, reference: datetime | None = None) -> list[dict]:
    alerts = []
    now = reference or datetime.now()

    if not computer.last_seen:
        alerts.append({
            "severity": "offline",
            "metric": "connectivity",
            "title": "Host sem comunicacao",
            "message": "A maquina ainda nao reportou dados para o sistema.",
        })
        return alerts

    age_hours = (now - computer.last_seen).total_seconds() / 3600
    if age_hours > 24:
        alerts.append({
            "severity": "offline",
            "metric": "connectivity",
            "title": "Host offline",
            "message": f"Sem comunicacao ha {age_hours:.1f} horas.",
        })

    if computer.cpu_usage_percent is not None:
        if computer.cpu_usage_percent >= 90:
            alerts.append({
                "severity": "critical",
                "metric": "cpu",
                "title": "CPU critica",
                "message": f"CPU em {computer.cpu_usage_percent:.1f}%.",
            })
        elif computer.cpu_usage_percent >= 75:
            alerts.append({
                "severity": "warning",
                "metric": "cpu",
                "title": "CPU elevada",
                "message": f"CPU em {computer.cpu_usage_percent:.1f}%.",
            })

    if computer.memory_usage_percent is not None:
        if computer.memory_usage_percent >= 90:
            alerts.append({
                "severity": "critical",
                "metric": "memory",
                "title": "Memoria critica",
                "message": f"Memoria em {computer.memory_usage_percent:.1f}%.",
            })
        elif computer.memory_usage_percent >= 80:
            alerts.append({
                "severity": "warning",
                "metric": "memory",
                "title": "Memoria elevada",
                "message": f"Memoria em {computer.memory_usage_percent:.1f}%.",
            })

    if computer.disk_free_percent is not None:
        if computer.disk_free_percent <= 10:
            alerts.append({
                "severity": "critical",
                "metric": "disk",
                "title": "Disco critico",
                "message": f"Espaco livre em {computer.disk_free_percent:.1f}%.",
            })
        elif computer.disk_free_percent <= 20:
            alerts.append({
                "severity": "warning",
                "metric": "disk",
                "title": "Disco em atencao",
                "message": f"Espaco livre em {computer.disk_free_percent:.1f}%.",
            })

    return alerts
