from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.computer import Computer
from app.models.operational_event import OperationalEvent
from app.models.remote_action import RemoteAction
from app.models.user import User
from app.schemas.remote_action import RemoteActionCreate, RemoteActionResponse

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_REMOTE_ACTIONS = {"restart", "shutdown", "logoff", "lock", "update_agent"}
ALLOWED_OPERATOR_ROLES = {"admin", "technician"}


def ensure_remote_action_role(current_user: User) -> None:
    if current_user.role not in ALLOWED_OPERATOR_ROLES:
        raise HTTPException(status_code=403, detail="Acesso negado")


async def add_remote_action_event(
    db: AsyncSession,
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


async def get_active_remote_action(db: AsyncSession, computer_id: int) -> RemoteAction | None:
    stmt = (
        select(RemoteAction)
        .filter(
            RemoteAction.computer_id == computer_id,
            RemoteAction.status.in_(("pending", "running")),
        )
        .order_by(RemoteAction.created_at.asc(), RemoteAction.id.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def build_agent_download_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + settings.AGENT_RELEASE_DOWNLOAD_PATH


def get_agent_release_metadata_path() -> Path | None:
    release_file = (settings.AGENT_RELEASE_FILE or "").strip()
    if not release_file:
        return None

    configured_path = ""
    if hasattr(settings, "AGENT_RELEASE_METADATA_FILE"):
        configured_path = (settings.AGENT_RELEASE_METADATA_FILE or "").strip()

    if configured_path:
        return Path(configured_path)

    return Path(release_file).with_suffix(Path(release_file).suffix + ".version.json")


def compute_file_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            if chunk:
                digest.update(chunk)
    return digest.hexdigest()


def load_agent_release_metadata() -> dict:
    release_file = (settings.AGENT_RELEASE_FILE or "").strip()
    if not release_file:
        raise HTTPException(
            status_code=400,
            detail="Arquivo de release do agente nao esta configurado no backend.",
        )

    release_path = Path(release_file)
    if not release_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Arquivo de release do agente nao foi encontrado no backend.",
        )

    metadata_path = get_agent_release_metadata_path()
    if metadata_path is None or not metadata_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=(
                "Metadados do release do agente nao encontrados. "
                "Gere e publique o arquivo InventoryAgent.exe.version.json junto do executavel."
            ),
        )

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Metadados do release do agente invalidos: {exc}",
        ) from exc

    version = str(metadata.get("version") or "").strip()
    sha256 = str(metadata.get("sha256") or "").strip().lower()
    if not version or not sha256:
        raise HTTPException(
            status_code=400,
            detail="Metadados do release do agente incompletos. Campos obrigatorios: version e sha256.",
        )

    actual_sha256 = compute_file_sha256(release_path).lower()
    if actual_sha256 != sha256:
        raise HTTPException(
            status_code=400,
            detail="O hash do executavel publicado nao confere com o metadata do release do agente.",
        )

    configured_version = (settings.AGENT_LATEST_VERSION or "").strip()
    if configured_version and configured_version != version:
        logger.warning(
            "AGENT_LATEST_VERSION=%s difere do metadata do release=%s. O backend usara a versao do metadata.",
            configured_version,
            version,
        )

    return {
        "version": version,
        "sha256": sha256,
        "release_path": str(release_path),
        "metadata_path": str(metadata_path),
    }


@router.get("/computers/{computer_id}/remote-actions")
async def list_remote_actions(
    computer_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()
    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    stmt = (
        select(RemoteAction)
        .filter(RemoteAction.computer_id == computer_id)
        .order_by(RemoteAction.created_at.desc(), RemoteAction.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()

    return [serialize_remote_action(action) for action in actions]


@router.post("/computers/{computer_id}/remote-actions")
async def create_remote_action(
    computer_id: int,
    data: RemoteActionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    result_comp = await db.execute(select(Computer).filter(Computer.id == computer_id))
    computer = result_comp.scalars().first()
    if not computer:
        raise HTTPException(status_code=404, detail="Computador nao encontrado")

    normalized_action = data.action_type.strip().lower()
    if normalized_action not in ALLOWED_REMOTE_ACTIONS:
        raise HTTPException(status_code=400, detail="Acao remota invalida")

    justification = (data.justification or "").strip() or None
    if not justification:
        raise HTTPException(status_code=400, detail="Justificativa obrigatoria para acao remota")

    active_action = await get_active_remote_action(db, computer_id)
    if active_action:
        raise HTTPException(
            status_code=409,
            detail=f"Ja existe uma acao {active_action.status} para esta maquina.",
        )

    action_payload = None
    if normalized_action == "update_agent":
        release_metadata = load_agent_release_metadata()
        action_payload = {
            "version": release_metadata["version"],
            "download_url": build_agent_download_url(request),
            "sha256": release_metadata["sha256"],
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
    await db.flush()

    display_name = {
        "restart": "reinicializacao",
        "shutdown": "desligamento",
        "logoff": "logoff",
        "lock": "bloqueio de sessao",
        "update_agent": "atualizacao do agente",
    }[normalized_action]
    extra_reason = f" Justificativa: {justification}." if justification else ""
    await add_remote_action_event(
        db=db,
        computer_id=computer_id,
        severity="warning",
        title="Acao remota solicitada",
        message=(
            f"{current_user.username} solicitou {display_name} para o host {computer.hostname}."
            f"{extra_reason}"
        ),
    )

    await db.commit()
    await db.refresh(action)
    logger.warning(
        "Acao remota criada: id=%s computer_id=%s hostname=%s tipo=%s versao_alvo=%s requested_by=%s.",
        action.id,
        computer_id,
        computer.hostname,
        normalized_action,
        action_payload.get("version") if isinstance(action_payload, dict) else None,
        current_user.username,
    )
    return serialize_remote_action(action)


@router.post("/computers/{computer_id}/remote-actions/{action_id}/cancel")
async def cancel_remote_action(
    computer_id: int,
    action_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_remote_action_role(current_user)

    stmt = (
        select(RemoteAction)
        .filter(RemoteAction.id == action_id, RemoteAction.computer_id == computer_id)
    )
    result = await db.execute(stmt)
    action = result.scalars().first()
    
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

    await add_remote_action_event(
        db=db,
        computer_id=computer_id,
        severity="warning",
        title="Acao remota cancelada",
        message=f"{current_user.username} cancelou a acao {action.action_type} antes da execucao.",
    )

    await db.commit()
    await db.refresh(action)
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
