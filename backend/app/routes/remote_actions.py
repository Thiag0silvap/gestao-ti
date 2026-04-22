from datetime import datetime
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.computer import Computer
from app.models.operational_event import OperationalEvent
from app.models.remote_action import RemoteAction
from app.models.user import User
from app.schemas.remote_action import RemoteActionCreate, RemoteActionResponse

router = APIRouter()

ALLOWED_REMOTE_ACTIONS = {"restart", "shutdown", "logoff", "lock", "update_agent"}
ALLOWED_OPERATOR_ROLES = {"admin", "technician"}


def ensure_remote_action_role(current_user: User) -> None:
    if current_user.role not in ALLOWED_OPERATOR_ROLES:
        raise HTTPException(status_code=403, detail="Acesso negado")


def add_remote_action_event(
    db: Session,
    computer_id: int,
    severity: str,
    title: str,
    message: str,
) -> None:
    db.add(
        OperationalEvent(
            computer_id=computer_id,
            severity=severity,
            event_type="remote_action",
            title=title,
            message=message,
        )
    )


def serialize_remote_action(action: RemoteAction) -> dict:
    payload = None
    if action.payload_json:
        try:
            payload = json.loads(action.payload_json)
        except json.JSONDecodeError:
            payload = None

    return RemoteActionResponse.model_validate(
        {
            "id": action.id,
            "computer_id": action.computer_id,
            "action_type": action.action_type,
            "status": action.status,
            "requested_by": action.requested_by,
            "source_ip": action.source_ip,
            "justification": action.justification,
            "payload": payload,
            "result_message": action.result_message,
            "created_at": action.created_at,
            "started_at": action.started_at,
            "completed_at": action.completed_at,
            "expires_at": action.expires_at,
        }
    ).model_dump(mode="json")


def get_active_remote_action(db: Session, computer_id: int) -> RemoteAction | None:
    return (
        db.query(RemoteAction)
        .filter(
            RemoteAction.computer_id == computer_id,
            RemoteAction.status.in_(("pending", "running")),
        )
        .order_by(RemoteAction.created_at.asc(), RemoteAction.id.asc())
        .first()
    )


def build_agent_download_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + settings.AGENT_RELEASE_DOWNLOAD_PATH


@router.get("/computers/{computer_id}/remote-actions")
def list_remote_actions(
    computer_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    computer = db.query(Computer).filter(Computer.id == computer_id).first()
    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    actions = (
        db.query(RemoteAction)
        .filter(RemoteAction.computer_id == computer_id)
        .order_by(RemoteAction.created_at.desc(), RemoteAction.id.desc())
        .limit(limit)
        .all()
    )

    return [serialize_remote_action(action) for action in actions]


@router.post("/computers/{computer_id}/remote-actions")
def create_remote_action(
    computer_id: int,
    data: RemoteActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    computer = db.query(Computer).filter(Computer.id == computer_id).first()
    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    normalized_action = data.action_type.strip().lower()
    if normalized_action not in ALLOWED_REMOTE_ACTIONS:
        raise HTTPException(status_code=400, detail="Acao remota invalida")

    justification = (data.justification or "").strip() or None
    if not justification:
        raise HTTPException(status_code=400, detail="Justificativa obrigatoria para acao remota")

    active_action = get_active_remote_action(db, computer_id)
    if active_action:
        raise HTTPException(
            status_code=409,
            detail=f"Ja existe uma acao {active_action.status} para esta maquina.",
        )

    action_payload = None
    if normalized_action == "update_agent":
        if not settings.AGENT_LATEST_VERSION or not settings.AGENT_RELEASE_FILE:
            raise HTTPException(
                status_code=400,
                detail="Atualizacao do agente nao esta configurada no backend.",
            )
        action_payload = {
            "version": settings.AGENT_LATEST_VERSION,
            "download_url": build_agent_download_url(request),
        }

    action = RemoteAction(
        computer_id=computer_id,
        action_type=normalized_action,
        status="pending",
        requested_by=current_user.username,
        source_ip=request.client.host if request.client else None,
        justification=justification,
        payload_json=json.dumps(action_payload, ensure_ascii=True) if action_payload else None,
        expires_at=data.expires_at,
    )
    db.add(action)
    db.flush()

    display_name = {
        "restart": "reinicializacao",
        "shutdown": "desligamento",
        "logoff": "logoff",
        "lock": "bloqueio de sessao",
        "update_agent": "atualizacao do agente",
    }[normalized_action]
    extra_reason = f" Justificativa: {justification}." if justification else ""
    add_remote_action_event(
        db=db,
        computer_id=computer_id,
        severity="warning",
        title="Acao remota solicitada",
        message=(
            f"{current_user.username} solicitou {display_name} para o host {computer.hostname}."
            f"{extra_reason}"
        ),
    )

    db.commit()
    db.refresh(action)
    return serialize_remote_action(action)


@router.post("/computers/{computer_id}/remote-actions/{action_id}/cancel")
def cancel_remote_action(
    computer_id: int,
    action_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    action = (
        db.query(RemoteAction)
        .filter(RemoteAction.id == action_id, RemoteAction.computer_id == computer_id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Acao remota nao encontrada")

    if action.status != "pending":
        raise HTTPException(status_code=400, detail="Somente acoes pendentes podem ser canceladas")

    action.status = "cancelled"
    action.completed_at = datetime.now()
    action.result_message = (
        f"Acao cancelada por {current_user.username}"
        + (f" a partir do IP {request.client.host}" if request.client else "")
        + "."
    )

    add_remote_action_event(
        db=db,
        computer_id=computer_id,
        severity="warning",
        title="Acao remota cancelada",
        message=f"{current_user.username} cancelou a acao {action.action_type} antes da execucao.",
    )

    db.commit()
    db.refresh(action)
    return serialize_remote_action(action)


@router.get(settings.AGENT_RELEASE_DOWNLOAD_PATH)
def download_agent_release(
    x_api_key: str = Header(default=""),
):
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent key")

    release_file = settings.AGENT_RELEASE_FILE
    if not release_file:
        raise HTTPException(status_code=404, detail="Arquivo de release do agente nao configurado")

    return FileResponse(
        path=release_file,
        media_type="application/octet-stream",
        filename="InventoryAgent.exe",
    )
