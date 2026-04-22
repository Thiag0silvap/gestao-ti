from datetime import datetime
import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.computer import Computer
from app.models.computer_printer import ComputerPrinter
from app.models.operational_event import OperationalEvent
from app.models.remote_action import RemoteAction
from app.models.system_metric import SystemMetric
from app.monitoring import classify_computer_severity
from app.schemas.computer import ComputerCreate
from app.schemas.remote_action import RemoteActionStatusUpdate

router = APIRouter()
ALLOWED_AGENT_ACTION_STATUSES = {"running", "success", "failed"}


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


def expire_overdue_actions(db: Session, computer_id: int) -> None:
    now = datetime.now()
    overdue_actions = (
        db.query(RemoteAction)
        .filter(
            RemoteAction.computer_id == computer_id,
            RemoteAction.status == "pending",
            RemoteAction.expires_at.isnot(None),
            RemoteAction.expires_at < now,
        )
        .all()
    )

    for action in overdue_actions:
        action.status = "expired"
        action.completed_at = now
        action.result_message = "A acao expirou antes de ser processada pelo agente."
        add_operational_event(
            db=db,
            computer_id=computer_id,
            severity="warning",
            event_type="remote_action",
            title="Acao remota expirada",
            message=f"A acao {action.action_type} expirou sem execucao.",
        )


def get_next_pending_action(db: Session, computer_id: int) -> RemoteAction | None:
    expire_overdue_actions(db, computer_id)
    return (
        db.query(RemoteAction)
        .filter(RemoteAction.computer_id == computer_id, RemoteAction.status == "pending")
        .order_by(RemoteAction.created_at.asc(), RemoteAction.id.asc())
        .first()
    )


def serialize_remote_action(action: RemoteAction | None) -> dict | None:
    if not action:
        return None

    payload = None
    if action.payload_json:
        try:
            payload = json.loads(action.payload_json)
        except json.JSONDecodeError:
            payload = None

    return {
        "id": action.id,
        "action_type": action.action_type,
        "status": action.status,
        "requested_by": action.requested_by,
        "justification": action.justification,
        "payload": payload,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "expires_at": action.expires_at.isoformat() if action.expires_at else None,
    }


def sync_computer_printers(db: Session, computer_id: int, printers: list | None) -> None:
    if printers is None:
        return

    db.query(ComputerPrinter).filter(ComputerPrinter.computer_id == computer_id).delete()

    for printer in printers:
        if not printer.name:
            continue

        db.add(ComputerPrinter(
            computer_id=computer_id,
            name=printer.name,
            driver_name=printer.driver_name,
            port_name=printer.port_name,
            server_name=printer.server_name,
            share_name=printer.share_name,
            location=printer.location,
            is_default=printer.is_default,
            is_network=printer.is_network,
            is_shared=printer.is_shared,
            status=printer.status,
            source=printer.source or "agent",
            last_seen=datetime.now(),
        ))


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
        computer.agent_id = data.agent_id
        computer.agent_state = data.agent_state
        computer.agent_version = data.agent_version
        computer.agent_started_at = data.agent_started_at
        computer.agent_last_attempt_at = data.agent_last_attempt_at
        computer.agent_last_success_at = data.agent_last_success_at
        computer.agent_last_error_at = data.agent_last_error_at
        computer.agent_last_error_message = data.agent_last_error_message
        computer.agent_consecutive_failures = data.agent_consecutive_failures
        computer.agent_offline_queue_size = data.agent_offline_queue_size
        computer.collected_at = data.collected_at
        computer.sync_attempt = data.sync_attempt
        computer.last_maintenance_date = data.last_maintenance_date
        computer.notes = data.notes
        computer.last_seen = datetime.now()

        db.commit()
        db.refresh(computer)
        sync_computer_printers(db, computer.id, data.printers)

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
        pending_action = get_next_pending_action(db, computer.id)
        db.commit()

        return {
            "message": "Computador atualizado com sucesso",
            "id": computer.id,
            "hostname": computer.hostname,
            "remote_action": serialize_remote_action(pending_action),
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
        agent_id=data.agent_id,
        agent_state=data.agent_state,
        agent_version=data.agent_version,
        agent_started_at=data.agent_started_at,
        agent_last_attempt_at=data.agent_last_attempt_at,
        agent_last_success_at=data.agent_last_success_at,
        agent_last_error_at=data.agent_last_error_at,
        agent_last_error_message=data.agent_last_error_message,
        agent_consecutive_failures=data.agent_consecutive_failures,
        agent_offline_queue_size=data.agent_offline_queue_size,
        collected_at=data.collected_at,
        sync_attempt=data.sync_attempt,
        last_maintenance_date=data.last_maintenance_date,
        notes=data.notes,
        last_seen=datetime.now()
    )

    db.add(new_computer)
    db.commit()
    db.refresh(new_computer)
    sync_computer_printers(db, new_computer.id, data.printers)

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
    pending_action = get_next_pending_action(db, new_computer.id)
    db.commit()

    return {
        "message": "Computador cadastrado com sucesso",
        "id": new_computer.id,
        "hostname": new_computer.hostname,
        "remote_action": serialize_remote_action(pending_action),
    }


@router.post("/agent/remote-actions/{action_id}/status")
def update_remote_action_status(
    action_id: int,
    data: RemoteActionStatusUpdate,
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent key")

    if data.status not in ALLOWED_AGENT_ACTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid action status")

    action = db.query(RemoteAction).filter(RemoteAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Remote action not found")

    if action.computer_id != data.computer_id:
        raise HTTPException(status_code=403, detail="Remote action does not belong to this computer")

    now = datetime.now()

    if data.status == "running":
        action.status = "running"
        action.started_at = now
        action.result_message = data.result_message
        add_operational_event(
            db=db,
            computer_id=action.computer_id,
            severity="warning",
            event_type="remote_action",
            title="Acao remota em execucao",
            message=f"O agente iniciou a acao {action.action_type}.",
        )
    else:
        action.status = data.status
        if action.started_at is None:
            action.started_at = now
        action.completed_at = now
        action.result_message = data.result_message
        add_operational_event(
            db=db,
            computer_id=action.computer_id,
            severity="info" if data.status == "success" else "critical",
            event_type="remote_action",
            title="Acao remota concluida" if data.status == "success" else "Acao remota falhou",
            message=(
                f"Resultado da acao {action.action_type}: "
                f"{data.result_message or ('executada com sucesso' if data.status == 'success' else 'falha sem detalhes')}."
            ),
        )

    db.commit()
    db.refresh(action)

    return {
        "message": "Status da acao remota atualizado",
        "remote_action": {
            "id": action.id,
            "computer_id": action.computer_id,
            "action_type": action.action_type,
            "status": action.status,
            "result_message": action.result_message,
            "started_at": action.started_at,
            "completed_at": action.completed_at,
        },
    }
