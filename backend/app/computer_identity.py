from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.computer import Computer
from app.models.computer_printer import ComputerPrinter
from app.models.operational_event import OperationalEvent
from app.models.remote_action import RemoteAction
from app.models.system_metric import SystemMetric
from app.models.ticket import Ticket


UNKNOWN_VALUES = {"", "-", "unknown", "none", "null", "nao informado", "não informado"}
PRESERVED_SECTOR_VALUES = {"", "nao informado", "não informado"}


@dataclass(frozen=True)
class IdentityMatch:
    computer: Computer | None
    strategy: str | None


def normalize_identity(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    if normalized.lower() in UNKNOWN_VALUES:
        return None

    return normalized


def normalized_lower(value: str | None) -> str | None:
    normalized = normalize_identity(value)
    return normalized.lower() if normalized else None


def values_match(left: str | None, right: str | None) -> bool:
    left_normalized = normalized_lower(left)
    right_normalized = normalized_lower(right)
    return bool(left_normalized and right_normalized and left_normalized == right_normalized)


def should_update_sector(current_sector: str | None, incoming_sector: str | None) -> bool:
    current = normalized_lower(current_sector)
    incoming = normalized_lower(incoming_sector)

    if not incoming:
        return False

    if not current:
        return True

    if current in PRESERVED_SECTOR_VALUES:
        return True

    return values_match(current_sector, incoming_sector)


def find_computer_by_identity(db: Session, data) -> IdentityMatch:
    strategies = [
        ("agent_id", Computer.agent_id, normalize_identity(data.agent_id), False),
        ("serial_number", Computer.serial_number, normalize_identity(data.serial_number), True),
        ("patrimony_number", Computer.patrimony_number, normalize_identity(data.patrimony_number), True),
        ("mac_address", Computer.mac_address, normalize_identity(data.mac_address), True),
        ("hostname", Computer.hostname, normalize_identity(data.hostname), True),
    ]

    for strategy, column, value, case_insensitive in strategies:
        if not value:
            continue

        query = db.query(Computer)
        if case_insensitive:
            query = query.filter(func.lower(column) == value.lower())
        else:
            query = query.filter(column == value)

        computer = query.order_by(Computer.last_seen.desc(), Computer.id.asc()).first()
        if computer:
            return IdentityMatch(computer=computer, strategy=strategy)

    return IdentityMatch(computer=None, strategy=None)


def find_duplicate_computers(db: Session, primary: Computer, data) -> list[Computer]:
    filters = []

    if normalize_identity(data.agent_id):
        filters.append(Computer.agent_id == data.agent_id)
    if normalize_identity(data.serial_number):
        filters.append(func.lower(Computer.serial_number) == data.serial_number.lower())
    if normalize_identity(data.patrimony_number):
        filters.append(func.lower(Computer.patrimony_number) == data.patrimony_number.lower())
    if normalize_identity(data.mac_address):
        filters.append(func.lower(Computer.mac_address) == data.mac_address.lower())
    if normalize_identity(data.hostname):
        filters.append(func.lower(Computer.hostname) == data.hostname.lower())

    if not filters:
        return []

    return (
        db.query(Computer)
        .filter(Computer.id != primary.id, or_(*filters))
        .order_by(Computer.last_seen.desc(), Computer.id.asc())
        .all()
    )


def fill_missing_computer_fields(primary: Computer, duplicate: Computer) -> None:
    fields = [
        "user",
        "ip_address",
        "mac_address",
        "cpu",
        "ram",
        "memory_type",
        "memory_speed",
        "disk",
        "os",
        "sector",
        "patrimony_number",
        "serial_number",
        "manufacturer",
        "model",
        "equipment_status",
        "agent_id",
        "agent_state",
        "agent_version",
        "agent_started_at",
        "agent_last_attempt_at",
        "agent_last_success_at",
        "agent_last_error_at",
        "agent_last_error_message",
        "agent_consecutive_failures",
        "agent_offline_queue_size",
        "collected_at",
        "sync_attempt",
        "last_maintenance_date",
        "last_seen",
        "notes",
    ]

    for field in fields:
        if getattr(primary, field, None) in (None, "") and getattr(duplicate, field, None) not in (None, ""):
            setattr(primary, field, getattr(duplicate, field))


def merge_duplicate_computers(db: Session, primary: Computer, duplicates: list[Computer]) -> int:
    merged_count = 0

    for duplicate in duplicates:
        for model in (Asset, Ticket, RemoteAction, SystemMetric, OperationalEvent, ComputerPrinter):
            db.query(model).filter(model.computer_id == duplicate.id).update(
                {model.computer_id: primary.id},
                synchronize_session=False,
            )

        duplicate_snapshot = {
            column.name: getattr(duplicate, column.name)
            for column in Computer.__table__.columns
        }
        db.delete(duplicate)
        db.flush()

        shadow_duplicate = type("DuplicateSnapshot", (), duplicate_snapshot)
        fill_missing_computer_fields(primary, shadow_duplicate)
        merged_count += 1

    return merged_count
