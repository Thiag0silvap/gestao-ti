from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.computer import Computer
from app.models.operational_event import OperationalEvent
from app.models.system_metric import SystemMetric
from app.monitoring import classify_computer_severity
from app.schemas.computer import ComputerCreate

router = APIRouter()


def add_operational_event(
    db: Session,
    computer_id: int,
    severity: str,
    event_type: str,
    title: str,
    message: str,
    metric: str | None = None,
) -> None:
    db.add(
        OperationalEvent(
            computer_id=computer_id,
            severity=severity,
            event_type=event_type,
            metric=metric,
            title=title,
            message=message,
        )
    )


def describe_sync_message(data: ComputerCreate) -> str:
    parts = []

    if data.cpu_usage_percent is not None:
        parts.append(f"CPU {data.cpu_usage_percent:.1f}%")

    if data.memory_usage_percent is not None:
        parts.append(f"memoria {data.memory_usage_percent:.1f}%")

    if data.disk_free_percent is not None:
        parts.append(f"disco livre {data.disk_free_percent:.1f}%")

    if data.uptime_hours is not None:
        parts.append(f"uptime {data.uptime_hours:.1f}h")

    if not parts:
        return "O agente reportou inventario basico sem telemetria detalhada."

    return "Telemetria recebida: " + ", ".join(parts) + "."


def create_sync_events(
    db: Session,
    computer: Computer,
    previous_severity: str | None,
    is_new: bool,
    data: ComputerCreate,
) -> None:
    current_severity = classify_computer_severity(computer)

    if is_new:
        add_operational_event(
            db=db,
            computer_id=computer.id,
            severity="info",
            event_type="discovery",
            title="Host registrado",
            message="A maquina foi cadastrada no monitoramento e enviou o primeiro inventario.",
        )

    add_operational_event(
        db=db,
        computer_id=computer.id,
        severity="info",
        event_type="agent_sync",
        title="Sincronizacao do agente",
        message=describe_sync_message(data),
    )

    if previous_severity == current_severity:
        return

    severity_titles = {
        "healthy": ("info", "Host estabilizado", "A telemetria voltou para uma faixa saudavel."),
        "warning": ("warning", "Host em atencao", "A maquina entrou em faixa de atencao operacional."),
        "critical": ("critical", "Host critico", "A maquina entrou em faixa critica de monitoramento."),
        "offline": ("offline", "Host offline", "A maquina esta sem comunicacao dentro da janela esperada."),
    }
    severity, title, message = severity_titles[current_severity]
    add_operational_event(
        db=db,
        computer_id=computer.id,
        severity=severity,
        event_type="severity_change",
        title=title,
        message=message,
    )


@router.post("/agent/computers/sync")
def sync_computer(
    data: ComputerCreate,
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db)
):
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent key")

    computer = db.query(Computer).filter(
        Computer.mac_address == data.mac_address
    ).first()

    if computer:
        previous_severity = classify_computer_severity(computer)
        computer.hostname = data.hostname
        computer.user = data.user
        computer.ip_address = data.ip_address
        computer.cpu = data.cpu
        computer.ram = data.ram
        computer.memory_type = data.memory_type
        computer.memory_speed = data.memory_speed
        computer.cpu_usage_percent = data.cpu_usage_percent
        computer.memory_usage_percent = data.memory_usage_percent
        computer.disk_free_gb = data.disk_free_gb
        computer.disk_free_percent = data.disk_free_percent
        computer.uptime_hours = data.uptime_hours
        computer.disk = data.disk
        computer.os = data.os
        computer.sector = data.sector
        computer.patrimony_number = data.patrimony_number
        computer.serial_number = data.serial_number
        computer.manufacturer = data.manufacturer
        computer.model = data.model
        computer.equipment_status = data.equipment_status
        computer.last_maintenance_date = data.last_maintenance_date
        computer.notes = data.notes
        computer.last_seen = datetime.now()

        db.commit()
        db.refresh(computer)

        if any(
            value is not None
            for value in (
                data.cpu_usage_percent,
                data.memory_usage_percent,
                data.disk_free_gb,
                data.disk_free_percent,
                data.uptime_hours,
            )
        ):
            metric = SystemMetric(
                computer_id=computer.id,
                cpu_usage_percent=data.cpu_usage_percent,
                memory_usage_percent=data.memory_usage_percent,
                disk_free_gb=data.disk_free_gb,
                disk_free_percent=data.disk_free_percent,
                uptime_hours=data.uptime_hours,
            )
            db.add(metric)
        create_sync_events(db, computer, previous_severity, False, data)
        db.commit()

        return {
            "message": "Computador atualizado com sucesso",
            "id": computer.id,
            "hostname": computer.hostname
        }

    new_computer = Computer(
        hostname=data.hostname,
        user=data.user,
        ip_address=data.ip_address,
        mac_address=data.mac_address,
        cpu=data.cpu,
        ram=data.ram,
        memory_type=data.memory_type,
        memory_speed=data.memory_speed,
        cpu_usage_percent=data.cpu_usage_percent,
        memory_usage_percent=data.memory_usage_percent,
        disk_free_gb=data.disk_free_gb,
        disk_free_percent=data.disk_free_percent,
        uptime_hours=data.uptime_hours,
        disk=data.disk,
        os=data.os,
        sector=data.sector,
        patrimony_number=data.patrimony_number,
        serial_number=data.serial_number,
        manufacturer=data.manufacturer,
        model=data.model,
        equipment_status=data.equipment_status,
        last_maintenance_date=data.last_maintenance_date,
        notes=data.notes,
        last_seen=datetime.now()
    )

    db.add(new_computer)
    db.commit()
    db.refresh(new_computer)

    if any(
        value is not None
        for value in (
            data.cpu_usage_percent,
            data.memory_usage_percent,
            data.disk_free_gb,
            data.disk_free_percent,
            data.uptime_hours,
        )
    ):
        metric = SystemMetric(
            computer_id=new_computer.id,
            cpu_usage_percent=data.cpu_usage_percent,
            memory_usage_percent=data.memory_usage_percent,
            disk_free_gb=data.disk_free_gb,
            disk_free_percent=data.disk_free_percent,
            uptime_hours=data.uptime_hours,
        )
        db.add(metric)
    create_sync_events(db, new_computer, None, True, data)
    db.commit()

    return {
        "message": "Computador cadastrado com sucesso",
        "id": new_computer.id,
        "hostname": new_computer.hostname
    }
