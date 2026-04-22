import argparse
import getpass
import ipaddress
import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import random
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv
import psutil
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_DIR = get_runtime_dir()
ENV_FILE = RUNTIME_DIR / ".env"
load_dotenv(ENV_FILE, encoding="utf-8-sig")
APP_VERSION = "1.1.4"

DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_REMOTE_ACTION_INTERVAL_SECONDS = 20
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_SECTOR = "Nao informado"
DEFAULT_EQUIPMENT_STATUS = "Ativo"
DEFAULT_NOTES = "Cadastro automatico pelo agente"
IGNORED_INTERFACE_TOKENS = (
    "virtual",
    "vmware",
    "vethernet",
    "hyper-v",
    "loopback",
    "bluetooth",
    "tunnel",
    "pseudo",
    "docker",
    "wsl",
    "vpn",
    "tap",
    "tun",
    "ppp",
    "wireguard",
    "anyconnect",
    "openvpn",
    "zerotier",
    "tailscale",
    "fortinet",
)
MEMORY_TYPE_MAP = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    34: "DDR5",
}
ALLOWED_REMOTE_ACTIONS = {"restart", "shutdown", "logoff", "lock", "update_agent"}
STATE_DIR = RUNTIME_DIR / "state"
AGENT_ID_FILE = STATE_DIR / "agent_id.txt"
STATUS_FILE = STATE_DIR / "status.json"
OFFLINE_QUEUE_FILE = STATE_DIR / "offline_queue.jsonl"
MAX_OFFLINE_QUEUE_ITEMS = 250
MAX_OFFLINE_QUEUE_BYTES = 5 * 1024 * 1024


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_text_atomic(path: Path, content: str) -> None:
    ensure_state_dir()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def write_json_atomic(path: Path, payload: dict) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=True, indent=2))


def get_or_create_agent_id() -> str:
    ensure_state_dir()

    if AGENT_ID_FILE.exists():
        existing_value = AGENT_ID_FILE.read_text(encoding="utf-8").strip()
        if existing_value:
            return existing_value

    agent_id = str(uuid.uuid4())
    write_text_atomic(AGENT_ID_FILE, f"{agent_id}\n")
    return agent_id


def load_offline_queue_records() -> list[dict]:
    if not OFFLINE_QUEUE_FILE.exists():
        return []

    records: list[dict] = []
    try:
        for line in OFFLINE_QUEUE_FILE.read_text(encoding="utf-8").splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and isinstance(parsed.get("payload"), dict):
                records.append(parsed)
    except OSError:
        logging.exception("Falha ao ler fila offline local.")

    return records


def rewrite_offline_queue_records(records: list[dict]) -> None:
    ensure_state_dir()

    if not records:
        if OFFLINE_QUEUE_FILE.exists():
            OFFLINE_QUEUE_FILE.unlink()
        return

    serialized = "\n".join(json.dumps(record, ensure_ascii=True) for record in records) + "\n"
    write_text_atomic(OFFLINE_QUEUE_FILE, serialized)


def trim_offline_queue_records(records: list[dict]) -> list[dict]:
    trimmed = list(records)

    while len(trimmed) > MAX_OFFLINE_QUEUE_ITEMS:
        trimmed.pop(0)

    while True:
        serialized = "\n".join(json.dumps(record, ensure_ascii=True) for record in trimmed).encode("utf-8")
        if len(serialized) <= MAX_OFFLINE_QUEUE_BYTES or not trimmed:
            break
        trimmed.pop(0)

    return trimmed


def enqueue_offline_payload(payload: dict, error_message: str | None) -> int:
    records = load_offline_queue_records()
    records.append(
        {
            "queued_at": now_iso(),
            "error_message": error_message,
            "payload": payload,
        }
    )
    trimmed_records = trim_offline_queue_records(records)
    rewrite_offline_queue_records(trimmed_records)
    return len(trimmed_records)


def get_offline_queue_size() -> int:
    return len(load_offline_queue_records())


def update_local_status(sync_state: dict, current_state: str, next_scheduled_at: str | None = None) -> None:
    status_payload = {
        "agent_id": sync_state["agent_id"],
        "computer_id": sync_state.get("computer_id"),
        "agent_version": APP_VERSION,
        "agent_started_at": sync_state["agent_started_at"],
        "current_state": current_state,
        "last_attempt_at": sync_state.get("last_attempt_at"),
        "last_success_at": sync_state.get("last_success_at"),
        "last_error_at": sync_state.get("last_error_at"),
        "last_error_message": sync_state.get("last_error_message"),
        "last_remote_action_check_at": sync_state.get("last_remote_action_check_at"),
        "sync_attempt": sync_state.get("sync_attempt", 0),
        "consecutive_failures": sync_state.get("consecutive_failures", 0),
        "offline_queue_size": get_offline_queue_size(),
        "next_scheduled_at": next_scheduled_at,
    }

    try:
        write_json_atomic(STATUS_FILE, status_payload)
    except OSError:
        logging.exception("Falha ao atualizar status local do agente.")


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    log_dir = RUNTIME_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "inventory_agent.log",
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def log_runtime_context() -> None:
    logging.info("Diretorio de execucao: %s", RUNTIME_DIR)
    logging.info("Arquivo de ambiente: %s", ENV_FILE)
    logging.info("Arquivo de ambiente encontrado: %s", ENV_FILE.exists())


def get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def get_settings() -> dict:
    interval_raw = os.getenv("INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
    remote_action_interval_raw = os.getenv(
        "REMOTE_ACTION_INTERVAL_SECONDS",
        str(DEFAULT_REMOTE_ACTION_INTERVAL_SECONDS),
    )
    timeout_raw = os.getenv("REQUEST_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))

    try:
        interval_seconds = max(30, int(interval_raw))
    except ValueError as exc:
        raise ValueError("INTERVAL_SECONDS deve ser um numero inteiro >= 30") from exc

    try:
        remote_action_interval_seconds = max(10, int(remote_action_interval_raw))
    except ValueError as exc:
        raise ValueError("REMOTE_ACTION_INTERVAL_SECONDS deve ser um numero inteiro >= 10") from exc

    try:
        timeout_seconds = max(5, int(timeout_raw))
    except ValueError as exc:
        raise ValueError("REQUEST_TIMEOUT_SECONDS deve ser um numero inteiro >= 5") from exc

    api_url = (os.getenv("API_URL") or "").strip()
    preferred_ip_prefixes = [
        prefix.strip()
        for prefix in (os.getenv("PREFERRED_IP_PREFIXES") or "").split(",")
        if prefix.strip()
    ]
    settings = {
        "api_url": api_url,
        "api_key": (os.getenv("AGENT_API_KEY") or "").strip(),
        "interval_seconds": interval_seconds,
        "remote_action_interval_seconds": remote_action_interval_seconds,
        "timeout_seconds": timeout_seconds,
        "sector": (os.getenv("DEFAULT_SECTOR") or DEFAULT_SECTOR).strip(),
        "patrimony_number": (os.getenv("PATRIMONY_NUMBER") or "").strip(),
        "equipment_status": (os.getenv("EQUIPMENT_STATUS") or DEFAULT_EQUIPMENT_STATUS).strip(),
        "notes": (os.getenv("AGENT_NOTES") or DEFAULT_NOTES).strip(),
        "verify_ssl": get_env_bool("VERIFY_SSL", True),
        "preferred_ip_prefixes": preferred_ip_prefixes,
    }

    if not settings["api_url"]:
        raise ValueError("API_URL nao definida no .env do agent")

    if not settings["api_key"]:
        raise ValueError("AGENT_API_KEY nao definida no .env do agent")

    parsed_url = urlparse(api_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("API_URL do agent esta invalida")

    settings["api_base_url"] = f"{parsed_url.scheme}://{parsed_url.netloc}"
    api_host_parts = parsed_url.hostname.split(".") if parsed_url.hostname else []
    if not settings["preferred_ip_prefixes"] and len(api_host_parts) == 4:
        settings["preferred_ip_prefixes"] = [
            ".".join(api_host_parts[:3]) + ".",
            ".".join(api_host_parts[:2]) + ".",
        ]

    return settings


def get_request_timeout(settings: dict) -> tuple[int, int]:
    connect_timeout = min(5, settings["timeout_seconds"])
    read_timeout = max(connect_timeout, settings["timeout_seconds"])
    return connect_timeout, read_timeout


def get_sleep_interval(settings: dict) -> int:
    base_interval = settings["interval_seconds"]
    jitter_window = min(30, max(5, int(base_interval * 0.1)))
    return base_interval + random.randint(0, jitter_window)


def get_remote_action_interval(settings: dict) -> int:
    return settings["remote_action_interval_seconds"]


def create_http_session() -> requests.Session:
    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    # Avoid inheriting machine-wide proxy settings for local API traffic.
    session.trust_env = False
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def run_command(command: list[str], timeout_seconds: int = 10) -> str | None:
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    output = (result.stdout or "").strip()
    if result.returncode != 0 or not output:
        return None

    return output


def run_command_result(command: list[str], timeout_seconds: int = 10) -> tuple[bool, str | None]:
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return False, str(exc)

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip() or None
    return result.returncode == 0, output


def parse_command_output(output: str) -> str | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[1]
    if len(lines) == 1:
        return lines[0]
    return None


def parse_reg_query_output(output: str) -> str | None:
    for line in output.splitlines():
        normalized = line.strip()
        if not normalized or "REG_" not in normalized:
            continue

        parts = normalized.split(None, 2)
        if len(parts) == 3:
            value = parts[2].strip()
            if value:
                return value

    return None


def query_registry_value(key_path: str, value_name: str) -> str | None:
    output = run_command(["reg", "query", key_path, "/v", value_name])
    if not output:
        return None

    return parse_reg_query_output(output)


def normalize_blank(value) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    if normalized.lower() in {"unknown", "none", "null"}:
        return None

    return normalized


def normalize_bool(value) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "sim"}:
        return True
    if normalized in {"false", "0", "no", "nao", "não"}:
        return False

    return None


def get_hostname() -> str:
    return socket.gethostname()


def get_logged_user() -> str:
    if os.name == "nt":
        powershell_output = run_command(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).UserName"],
            timeout_seconds=5,
        )
        parsed_user = parse_command_output(powershell_output) if powershell_output else None
        if parsed_user:
            return parsed_user.split("\\")[-1].lower()

        wmic_output = run_command(
            ["wmic", "computersystem", "get", "username"],
            timeout_seconds=5,
        )
        parsed_user = parse_command_output(wmic_output) if wmic_output else None
        if parsed_user:
            return parsed_user.split("\\")[-1].lower()

    try:
        users = psutil.users()
        if users:
            return users[0].name.split("\\")[-1].lower()
    except Exception:
        logging.debug("Falha ao obter usuario interativo via psutil.", exc_info=True)

    try:
        return getpass.getuser().lower()
    except Exception:
        return os.getenv("USERNAME", "desconhecido").lower()


def is_valid_local_ipv4(ip_address: str | None) -> bool:
    if not ip_address:
        return False

    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return False

    return (
        parsed_ip.version == 4
        and not parsed_ip.is_loopback
        and not parsed_ip.is_link_local
        and not parsed_ip.is_multicast
        and not parsed_ip.is_unspecified
    )


def normalize_mac_address(raw_value: str | None) -> str | None:
    if not raw_value:
        return None

    mac_value = raw_value.replace("-", ":").upper()
    if len(mac_value) == 17 and mac_value != "00:00:00:00:00:00":
        return mac_value
    return None


def get_fallback_mac_address() -> str:
    mac = uuid.getnode()
    return ":".join([f"{(mac >> elements) & 0xFF:02X}" for elements in range(40, -1, -8)])


def get_network_identity(settings: dict | None = None) -> dict:
    settings = settings or {}
    preferred_prefixes = settings.get("preferred_ip_prefixes") or []

    candidates: list[dict] = []

    try:
        stats = psutil.net_if_stats()
        addresses_by_interface = psutil.net_if_addrs()

        for interface_name, interface_addresses in addresses_by_interface.items():
            interface_stats = stats.get(interface_name)
            if interface_stats and not interface_stats.isup:
                continue

            interface_name_normalized = interface_name.lower()
            is_ignored_interface = any(
                token in interface_name_normalized for token in IGNORED_INTERFACE_TOKENS
            )
            mac_address = next(
                (
                    normalize_mac_address(address.address)
                    for address in interface_addresses
                    if address.family == psutil.AF_LINK
                ),
                None,
            )

            for address in interface_addresses:
                if address.family != socket.AF_INET or not is_valid_local_ipv4(address.address):
                    continue

                score = 0
                if any(address.address.startswith(prefix) for prefix in preferred_prefixes):
                    score += 100
                if not is_ignored_interface:
                    score += 35
                if mac_address:
                    score += 10
                if is_ignored_interface:
                    score -= 80

                candidates.append(
                    {
                        "score": score,
                        "interface_name": interface_name,
                        "ip_address": address.address,
                        "mac_address": mac_address,
                    }
                )
    except Exception:
        logging.debug("Falha ao obter IP/MAC via interfaces locais", exc_info=True)

    if candidates:
        candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
        selected = candidates[0]
        logging.debug(
            "Interface selecionada: %s (IP=%s, MAC=%s, score=%s)",
            selected["interface_name"],
            selected["ip_address"],
            selected["mac_address"],
            selected["score"],
        )
        return {
            "ip_address": selected["ip_address"],
            "mac_address": selected["mac_address"] or get_fallback_mac_address(),
            "interface_name": selected["interface_name"],
        }

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip_address = sock.getsockname()[0]
            if is_valid_local_ipv4(ip_address):
                return {
                    "ip_address": ip_address,
                    "mac_address": get_fallback_mac_address(),
                    "interface_name": None,
                }
    except Exception:
        logging.debug("Falha ao obter IP via socket externo", exc_info=True)

    return {
        "ip_address": None,
        "mac_address": get_fallback_mac_address(),
        "interface_name": None,
    }


def get_ip_address(settings: dict | None = None) -> str | None:
    return get_network_identity(settings)["ip_address"]


def get_mac_address(settings: dict | None = None) -> str:
    return get_network_identity(settings)["mac_address"]


def get_cpu() -> str:
    wmic_output = run_command(["wmic", "cpu", "get", "name"])
    if wmic_output:
        parsed = parse_command_output(wmic_output)
        if parsed:
            return parsed

    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"]
    )
    if powershell_output:
        parsed = parse_command_output(powershell_output) or powershell_output.splitlines()[0].strip()
        if parsed:
            return parsed

    registry_output = query_registry_value(
        r"HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        "ProcessorNameString",
    )
    if registry_output:
        return registry_output

    return platform.processor() or "Nao identificado"


def get_ram() -> str:
    total_ram_gb = round(psutil.virtual_memory().total / (1024**3))
    return f"{total_ram_gb}GB"


def get_memory_usage_percent() -> float:
    return round(psutil.virtual_memory().percent, 1)


def get_disk() -> str:
    total_disk_gb = round(psutil.disk_usage("C:\\").total / (1024**3))
    return f"{total_disk_gb}GB"


def get_disk_free_gb() -> float:
    return round(psutil.disk_usage("C:\\").free / (1024**3), 1)


def get_disk_free_percent() -> float:
    disk_usage = psutil.disk_usage("C:\\")
    return round(100 - disk_usage.percent, 1)


def get_os() -> str:
    return f"{platform.system()} {platform.release()}"


def get_cpu_usage_percent() -> float:
    return round(psutil.cpu_percent(interval=1), 1)


def get_uptime_hours() -> float:
    uptime_seconds = time.time() - psutil.boot_time()
    return round(uptime_seconds / 3600, 1)


def get_manufacturer() -> str | None:
    wmic_output = run_command(["wmic", "computersystem", "get", "manufacturer"])
    if wmic_output:
        parsed = parse_command_output(wmic_output)
        if parsed:
            return parsed

    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Manufacturer"]
    )
    if powershell_output:
        parsed = parse_command_output(powershell_output) or powershell_output.splitlines()[0].strip()
        if parsed:
            return parsed

    registry_output = query_registry_value(
        r"HKLM\HARDWARE\DESCRIPTION\System\BIOS",
        "SystemManufacturer",
    )
    if registry_output:
        return registry_output

    return None


def get_model() -> str | None:
    wmic_output = run_command(["wmic", "computersystem", "get", "model"])
    if wmic_output:
        parsed = parse_command_output(wmic_output)
        if parsed:
            return parsed

    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Model"]
    )
    if powershell_output:
        parsed = parse_command_output(powershell_output) or powershell_output.splitlines()[0].strip()
        if parsed:
            return parsed

    registry_output = query_registry_value(
        r"HKLM\HARDWARE\DESCRIPTION\System\BIOS",
        "SystemProductName",
    )
    if registry_output:
        return registry_output

    return None


def get_serial_number() -> str | None:
    wmic_output = run_command(["wmic", "bios", "get", "serialnumber"])
    if wmic_output:
        parsed = parse_command_output(wmic_output)
        if parsed:
            return parsed

    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_BIOS).SerialNumber"]
    )
    if powershell_output:
        parsed = parse_command_output(powershell_output) or powershell_output.splitlines()[0].strip()
        if parsed:
            return parsed

    for value_name in ("SystemSerialNumber", "BaseBoardSerialNumber"):
        registry_output = query_registry_value(
            r"HKLM\HARDWARE\DESCRIPTION\System\BIOS",
            value_name,
        )
        if registry_output:
            return registry_output

    return None


def get_memory_details() -> tuple[str | None, str | None]:
    powershell_script = (
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select-Object SMBIOSMemoryType, ConfiguredClockSpeed, Speed, Capacity | "
        "ConvertTo-Json -Compress"
    )
    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", powershell_script],
        timeout_seconds=20,
    )

    if not powershell_output:
        return None, None

    try:
        module_data = json.loads(powershell_output)
    except json.JSONDecodeError:
        logging.debug("Falha ao interpretar JSON da memoria: %s", powershell_output)
        return None, None

    if isinstance(module_data, dict):
        modules = [module_data]
    elif isinstance(module_data, list):
        modules = module_data
    else:
        return None, None

    memory_types: set[str] = set()
    memory_speeds: set[int] = set()

    for module in modules:
        try:
            memory_type_code = int(module.get("SMBIOSMemoryType") or 0)
        except (TypeError, ValueError):
            memory_type_code = 0

        resolved_type = MEMORY_TYPE_MAP.get(memory_type_code)
        if resolved_type:
            memory_types.add(resolved_type)

        for raw_value in (module.get("ConfiguredClockSpeed"), module.get("Speed")):
            try:
                speed_value = int(raw_value)
            except (TypeError, ValueError):
                continue

            if speed_value > 0:
                memory_speeds.add(speed_value)

    memory_type = None
    if memory_types:
        memory_type = "/".join(sorted(memory_types))

    memory_speed = None
    if memory_speeds:
        memory_speed = " / ".join(f"{value} MHz" for value in sorted(memory_speeds))

    return memory_type, memory_speed


def get_printers() -> list[dict]:
    powershell_script = (
        "Get-CimInstance Win32_Printer | "
        "Select-Object Name,DriverName,PortName,ServerName,ShareName,Location,Default,Network,Shared,PrinterStatus | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    powershell_output = run_command(
        ["powershell", "-NoProfile", "-Command", powershell_script],
        timeout_seconds=20,
    )

    if not powershell_output:
        return get_registry_printers()

    try:
        printer_data = json.loads(powershell_output)
    except json.JSONDecodeError:
        logging.debug("Falha ao interpretar JSON das impressoras: %s", powershell_output)
        return get_registry_printers()

    if isinstance(printer_data, dict):
        printers = [printer_data]
    elif isinstance(printer_data, list):
        printers = printer_data
    else:
        return get_registry_printers()

    collected_printers = []
    seen_names = set()

    for printer in printers:
        name = normalize_blank(printer.get("Name"))
        if not name or name in seen_names:
            continue

        seen_names.add(name)
        collected_printers.append({
            "name": name,
            "driver_name": normalize_blank(printer.get("DriverName")),
            "port_name": normalize_blank(printer.get("PortName")),
            "server_name": normalize_blank(printer.get("ServerName")),
            "share_name": normalize_blank(printer.get("ShareName")),
            "location": normalize_blank(printer.get("Location")),
            "is_default": normalize_bool(printer.get("Default")),
            "is_network": normalize_bool(printer.get("Network")),
            "is_shared": normalize_bool(printer.get("Shared")),
            "status": normalize_blank(str(printer.get("PrinterStatus"))) if printer.get("PrinterStatus") is not None else None,
            "source": "agent",
        })

    return collected_printers or get_registry_printers()


def parse_registry_values(output: str | None) -> dict[str, str]:
    if not output:
        return {}

    values = {}
    for line in output.splitlines():
        normalized = line.strip()
        if not normalized or "REG_" not in normalized:
            continue

        match = re.match(r"^(?P<name>.+?)\s{2,}REG_\w+\s{2,}(?P<value>.*)$", normalized)
        if not match:
            continue

        name = normalize_blank(match.group("name"))
        value = normalize_blank(match.group("value"))
        if name and value:
            values[name] = value

    return values


def get_default_printer_name() -> str | None:
    output = run_command(
        ["reg", "query", r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Windows", "/v", "Device"]
    )
    values = parse_registry_values(output)
    raw_device = values.get("Device")
    if not raw_device:
        return None

    return normalize_blank(raw_device.split(",", 1)[0])


def get_registry_printers() -> list[dict]:
    devices_output = run_command(
        ["reg", "query", r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Devices"]
    )
    devices = parse_registry_values(devices_output)
    default_printer_name = get_default_printer_name()
    printers = []

    for name, raw_value in devices.items():
        port_name = None
        value_parts = [part.strip() for part in raw_value.split(",") if part.strip()]
        if len(value_parts) >= 2:
            port_name = value_parts[-1]

        printers.append({
            "name": name,
            "driver_name": None,
            "port_name": normalize_blank(port_name),
            "server_name": None,
            "share_name": None,
            "location": None,
            "is_default": name == default_printer_name,
            "is_network": name.startswith("\\\\"),
            "is_shared": None,
            "status": None,
            "source": "agent_registry",
        })

    return printers


def build_payload(settings: dict, sync_state: dict) -> dict:
    hostname = get_hostname()
    memory_type, memory_speed = get_memory_details()
    cpu_usage_percent = get_cpu_usage_percent()
    memory_usage_percent = get_memory_usage_percent()
    disk_free_gb = get_disk_free_gb()
    disk_free_percent = get_disk_free_percent()
    uptime_hours = get_uptime_hours()
    printers = get_printers()
    collected_at = now_iso()
    network_identity = get_network_identity(settings)

    return {
        "agent_id": sync_state["agent_id"],
        "agent_state": "syncing",
        "agent_started_at": sync_state["agent_started_at"],
        "agent_last_attempt_at": sync_state.get("last_attempt_at"),
        "agent_last_success_at": sync_state.get("last_success_at"),
        "agent_last_error_at": sync_state.get("last_error_at"),
        "agent_last_error_message": sync_state.get("last_error_message"),
        "agent_consecutive_failures": sync_state.get("consecutive_failures", 0),
        "agent_offline_queue_size": get_offline_queue_size(),
        "collected_at": collected_at,
        "sync_attempt": sync_state["sync_attempt"],
        "hostname": hostname,
        "user": get_logged_user(),
        "ip_address": network_identity["ip_address"],
        "mac_address": network_identity["mac_address"],
        "cpu": get_cpu(),
        "cpu_usage_percent": cpu_usage_percent,
        "ram": get_ram(),
        "memory_usage_percent": memory_usage_percent,
        "memory_type": normalize_blank(memory_type),
        "memory_speed": normalize_blank(memory_speed),
        "disk": get_disk(),
        "disk_free_gb": disk_free_gb,
        "disk_free_percent": disk_free_percent,
        "os": get_os(),
        "uptime_hours": uptime_hours,
        "sector": settings["sector"],
        "patrimony_number": settings["patrimony_number"] or hostname,
        "serial_number": get_serial_number(),
        "manufacturer": get_manufacturer(),
        "model": get_model(),
        "equipment_status": settings["equipment_status"],
        "agent_version": APP_VERSION,
        "printers": printers,
        "last_maintenance_date": None,
        "notes": settings["notes"],
    }


def log_payload(payload: dict) -> None:
    summary = {
        "agent_id": payload["agent_id"],
        "hostname": payload["hostname"],
        "user": payload["user"],
        "ip_address": payload["ip_address"],
        "mac_address": payload["mac_address"],
        "cpu_usage_percent": payload["cpu_usage_percent"],
        "memory_usage_percent": payload["memory_usage_percent"],
        "disk_free_percent": payload["disk_free_percent"],
        "uptime_hours": payload["uptime_hours"],
        "sector": payload["sector"],
        "serial_number": payload["serial_number"],
        "manufacturer": payload["manufacturer"],
        "model": payload["model"],
        "agent_version": payload["agent_version"],
        "agent_state": payload["agent_state"],
        "agent_consecutive_failures": payload["agent_consecutive_failures"],
        "agent_offline_queue_size": payload["agent_offline_queue_size"],
        "printers_count": len(payload.get("printers") or []),
        "sync_attempt": payload["sync_attempt"],
    }
    logging.info("Payload coletado: %s", json.dumps(summary, ensure_ascii=True))


def build_remote_action_status_url(settings: dict, action_id: int) -> str:
    return f"{settings['api_base_url']}/agent/remote-actions/{action_id}/status"


def build_remote_action_poll_url(settings: dict, computer_id: int) -> str:
    return f"{settings['api_base_url']}/agent/computers/{computer_id}/remote-action"


def post_inventory_payload(
    session: requests.Session,
    settings: dict,
    payload: dict,
    *,
    source_label: str,
    sync_state: dict | None = None,
) -> tuple[bool, bool, str | None]:
    headers = {"X-API-KEY": settings["api_key"]}

    try:
        response = session.post(
            settings["api_url"],
            json=payload,
            headers=headers,
            timeout=get_request_timeout(settings),
            verify=settings["verify_ssl"],
        )
    except requests.exceptions.RequestException as exc:
        error_message = f"Erro de conexao com a API: {exc}"
        logging.error("%s", error_message)
        return False, False, error_message

    response_text = response.text.strip()
    response_json = None
    content_type = (response.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            response_json = response.json()
        except ValueError:
            response_json = None

    if 200 <= response.status_code < 300:
        logging.info("%s concluido com status %s", source_label, response.status_code)
        if response_text:
            logging.info("Resposta da API: %s", response_text)

        should_exit = False
        if response_json and response_json.get("id"):
            if sync_state is not None:
                sync_state["computer_id"] = int(response_json["id"])
            should_exit = process_remote_action(
                session=session,
                settings=settings,
                computer_id=int(response_json["id"]),
                action_data=response_json.get("remote_action"),
            )
        return True, should_exit, None

    error_message = f"Falha ao sincronizar. Status: {response.status_code}"
    logging.error("%s", error_message)
    if response_text:
        logging.error("Resposta da API: %s", response_text)
    return False, False, response_text or error_message


def send_remote_action_status(
    session: requests.Session,
    settings: dict,
    computer_id: int,
    action_id: int,
    status: str,
    result_message: str | None,
) -> bool:
    headers = {"X-API-KEY": settings["api_key"]}
    payload = {
        "computer_id": computer_id,
        "status": status,
        "result_message": result_message,
    }

    try:
        response = session.post(
            build_remote_action_status_url(settings, action_id),
            json=payload,
            headers=headers,
            timeout=get_request_timeout(settings),
            verify=settings["verify_ssl"],
        )
    except requests.exceptions.RequestException as exc:
        logging.error("Falha ao reportar status da acao remota %s: %s", action_id, exc)
        return False

    if 200 <= response.status_code < 300:
        return True

    logging.error(
        "Nao foi possivel atualizar a acao remota %s. Status: %s Resposta: %s",
        action_id,
        response.status_code,
        response.text.strip(),
    )
    return False


def poll_remote_action(
    session: requests.Session,
    settings: dict,
    sync_state: dict,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        return False

    computer_id = sync_state.get("computer_id")
    if not computer_id:
        return False

    headers = {"X-API-KEY": settings["api_key"]}
    sync_state["last_remote_action_check_at"] = now_iso()
    update_local_status(sync_state, current_state="checking_actions")

    try:
        response = session.get(
            build_remote_action_poll_url(settings, int(computer_id)),
            headers=headers,
            timeout=get_request_timeout(settings),
            verify=settings["verify_ssl"],
        )
    except requests.exceptions.RequestException as exc:
        logging.debug("Falha ao consultar acoes remotas: %s", exc)
        return False

    if not 200 <= response.status_code < 300:
        logging.debug(
            "Consulta de acoes remotas retornou status %s: %s",
            response.status_code,
            response.text.strip(),
        )
        return False

    try:
        response_json = response.json()
    except ValueError:
        logging.debug("Consulta de acoes remotas retornou resposta invalida.")
        return False

    return process_remote_action(
        session=session,
        settings=settings,
        computer_id=int(computer_id),
        action_data=response_json.get("remote_action"),
    )


def build_agent_updater_script(current_executable: Path, downloaded_executable: Path) -> Path:
    backup_executable = current_executable.with_suffix(".bak.exe")
    updater_script = current_executable.with_name("agent_updater.cmd")

    script_content = f"""@echo off
setlocal
set "APP={current_executable}"
set "NEW={downloaded_executable}"
set "BAK={backup_executable}"
timeout /t 3 /nobreak >nul
copy /Y "%APP%" "%BAK%" >nul
copy /Y "%NEW%" "%APP%" >nul
if errorlevel 1 (
  copy /Y "%BAK%" "%APP%" >nul
  exit /b 1
)
del /Q "%NEW%" >nul 2>&1
start "" "%APP%"
del /Q "%~f0" >nul 2>&1
"""
    updater_script.write_text(script_content, encoding="utf-8")
    return updater_script


def start_agent_updater(updater_script: Path) -> None:
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        ["cmd", "/c", str(updater_script)],
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=False,
    )


def execute_agent_update(
    session: requests.Session,
    settings: dict,
    action_payload: dict | None,
) -> tuple[bool, str, bool]:
    if not getattr(sys, "frozen", False):
        return False, "Atualizacao remota suportada apenas no executavel empacotado.", False

    if not action_payload:
        return False, "Acao de atualizacao sem payload.", False

    target_version = (action_payload.get("version") or "").strip()
    download_url = (action_payload.get("download_url") or "").strip()
    if not target_version or not download_url:
        return False, "Payload de atualizacao incompleto.", False

    if target_version == APP_VERSION:
        return True, f"Agente ja esta na versao {APP_VERSION}.", False

    current_executable = Path(sys.executable).resolve()
    downloaded_executable = current_executable.with_name("InventoryAgent.next.exe")

    headers = {"X-API-KEY": settings["api_key"]}
    try:
        response = session.get(
            download_url,
            headers=headers,
            timeout=max(settings["timeout_seconds"], 30),
            verify=settings["verify_ssl"],
            stream=True,
        )
        response.raise_for_status()
        with open(downloaded_executable, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    file_handle.write(chunk)
    except requests.exceptions.RequestException as exc:
        return False, f"Falha ao baixar nova versao do agente: {exc}", False
    except OSError as exc:
        return False, f"Falha ao salvar nova versao do agente: {exc}", False

    try:
        updater_script = build_agent_updater_script(current_executable, downloaded_executable)
        start_agent_updater(updater_script)
    except OSError as exc:
        return False, f"Falha ao preparar atualizacao local: {exc}", False

    return True, f"Atualizacao para a versao {target_version} iniciada sem reiniciar o computador.", True


def execute_remote_action(
    session: requests.Session,
    settings: dict,
    action_type: str,
    action_payload: dict | None,
) -> tuple[bool, str, bool]:
    action_commands = {
        "restart": (
            ["shutdown", "/r", "/t", "15", "/f", "/c", "Reinicio remoto solicitado pelo Atlas TI"],
            "Reinicio agendado para 15 segundos.",
        ),
        "shutdown": (
            ["shutdown", "/s", "/t", "15", "/f", "/c", "Desligamento remoto solicitado pelo Atlas TI"],
            "Desligamento agendado para 15 segundos.",
        ),
        "logoff": (
            ["shutdown", "/l"],
            "Logoff solicitado com sucesso.",
        ),
        "lock": (
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            "Bloqueio de sessao executado com sucesso.",
        ),
    }

    if action_type == "update_agent":
        return execute_agent_update(session, settings, action_payload)

    if action_type not in action_commands:
        return False, "Acao remota nao permitida pelo agente.", False

    command, success_message = action_commands[action_type]
    success, output = run_command_result(command, timeout_seconds=15)
    if success:
        return True, success_message, False

    return False, output or "Falha ao executar acao remota.", False


def process_remote_action(
    session: requests.Session,
    settings: dict,
    computer_id: int,
    action_data: dict | None,
) -> bool:
    if not action_data:
        return False

    action_id = action_data.get("id")
    action_type = (action_data.get("action_type") or "").strip().lower()
    action_payload = action_data.get("payload")

    if not action_id or action_type not in ALLOWED_REMOTE_ACTIONS:
        logging.warning("Acao remota ignorada por dados invalidos: %s", action_data)
        return False

    logging.warning("Acao remota recebida: %s (id=%s)", action_type, action_id)
    send_remote_action_status(
        session=session,
        settings=settings,
        computer_id=computer_id,
        action_id=action_id,
        status="running",
        result_message="Agente iniciou a execucao da acao remota.",
    )

    success, result_message, should_exit = execute_remote_action(
        session=session,
        settings=settings,
        action_type=action_type,
        action_payload=action_payload if isinstance(action_payload, dict) else None,
    )
    final_status = "success" if success else "failed"

    send_remote_action_status(
        session=session,
        settings=settings,
        computer_id=computer_id,
        action_id=action_id,
        status=final_status,
        result_message=result_message,
    )

    if success:
        logging.warning("Acao remota %s concluida: %s", action_id, result_message)
    else:
        logging.error("Acao remota %s falhou: %s", action_id, result_message)

    return should_exit


def flush_offline_queue(
    session: requests.Session,
    settings: dict,
) -> tuple[bool, bool, int]:
    records = load_offline_queue_records()
    if not records:
        return True, False, 0

    logging.info("Tentando reenviar %s item(ns) da fila offline.", len(records))
    should_exit = False
    flushed_count = 0

    for index, record in enumerate(records):
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue

        success, item_should_exit, _ = post_inventory_payload(
            session=session,
            settings=settings,
            payload=payload,
            source_label="Reenvio da fila offline",
        )
        should_exit = should_exit or item_should_exit

        if not success:
            remaining_records = records[index:]
            rewrite_offline_queue_records(remaining_records)
            logging.warning(
                "Fila offline mantida com %s item(ns) pendente(s).",
                len(remaining_records),
            )
            return False, should_exit, flushed_count

        flushed_count += 1

    rewrite_offline_queue_records([])
    logging.info("Fila offline reenviada com sucesso (%s item(ns)).", flushed_count)
    return True, should_exit, flushed_count


def send_inventory(
    session: requests.Session,
    settings: dict,
    sync_state: dict,
    dry_run: bool = False,
) -> tuple[bool, bool]:
    sync_state["sync_attempt"] += 1
    payload = build_payload(settings, sync_state)
    sync_state["last_attempt_at"] = payload["collected_at"]

    log_payload(payload)
    update_local_status(sync_state, current_state="syncing")

    if dry_run:
        logging.info("Modo dry-run ativo. Nenhum dado foi enviado para a API.")
        sync_state["last_success_at"] = payload["collected_at"]
        sync_state["last_error_at"] = None
        sync_state["last_error_message"] = None
        sync_state["consecutive_failures"] = 0
        update_local_status(sync_state, current_state="idle")
        return True, False

    queue_success, queue_should_exit, flushed_count = flush_offline_queue(
        session=session,
        settings=settings,
    )
    if queue_should_exit:
        sync_state["last_success_at"] = now_iso()
        sync_state["last_error_at"] = None
        sync_state["last_error_message"] = None
        sync_state["consecutive_failures"] = 0
        update_local_status(sync_state, current_state="updating")
        return True, True

    if not queue_success:
        queue_size = enqueue_offline_payload(payload, "Fila offline ainda nao pode ser reenviada.")
        sync_state["consecutive_failures"] += 1
        sync_state["last_error_at"] = now_iso()
        sync_state["last_error_message"] = "Fila offline ainda nao pode ser reenviada."
        update_local_status(sync_state, current_state="degraded")
        logging.warning("Payload atual adicionado na fila offline. Total pendente: %s", queue_size)
        return False, False

    if flushed_count:
        update_local_status(sync_state, current_state="syncing")

    success, should_exit, error_message = post_inventory_payload(
        session=session,
        settings=settings,
        payload=payload,
        source_label="Sincronizacao",
        sync_state=sync_state,
    )

    if success:
        sync_state["last_success_at"] = payload["collected_at"]
        sync_state["last_error_at"] = None
        sync_state["last_error_message"] = None
        sync_state["consecutive_failures"] = 0
        update_local_status(sync_state, current_state="updating" if should_exit else "idle")
        return True, should_exit

    queue_size = enqueue_offline_payload(payload, error_message)
    sync_state["consecutive_failures"] += 1
    sync_state["last_error_at"] = now_iso()
    sync_state["last_error_message"] = error_message
    update_local_status(sync_state, current_state="degraded")
    logging.warning("Payload atual adicionado na fila offline. Total pendente: %s", queue_size)
    return False, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agente de inventario para sincronizar dados do computador com a API."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma unica sincronizacao e encerra.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Coleta os dados e mostra logs sem enviar para a API.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa logs mais detalhados.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(debug=args.debug)
    log_runtime_context()
    ensure_state_dir()

    try:
        settings = get_settings()
    except ValueError as exc:
        logging.error("%s", exc)
        return 1

    session = create_http_session()
    sync_state = {
        "agent_id": get_or_create_agent_id(),
        "agent_started_at": now_iso(),
        "sync_attempt": 0,
        "computer_id": None,
        "consecutive_failures": 0,
        "last_attempt_at": None,
        "last_success_at": None,
        "last_error_at": None,
        "last_error_message": None,
        "last_remote_action_check_at": None,
    }
    update_local_status(sync_state, current_state="starting")

    logging.info("Agente iniciado.")
    logging.info("Agent ID: %s", sync_state["agent_id"])
    logging.info("Versao do agente: %s", APP_VERSION)
    logging.info("API_URL: %s", settings["api_url"])
    logging.info("Intervalo configurado: %s segundos", settings["interval_seconds"])
    logging.info(
        "Intervalo de acoes remotas: %s segundos",
        settings["remote_action_interval_seconds"],
    )

    try:
        while True:
            try:
                success, should_exit = send_inventory(
                    session,
                    settings,
                    sync_state,
                    dry_run=args.dry_run,
                )
            except Exception as exc:  # noqa: BLE001
                sync_state["consecutive_failures"] += 1
                sync_state["last_error_at"] = now_iso()
                sync_state["last_error_message"] = str(exc)
                update_local_status(sync_state, current_state="crashed")
                logging.exception("Falha inesperada no ciclo principal do agente: %s", exc)
                success = False
                should_exit = False

            if args.once or should_exit:
                return 0 if success else 1

            sleep_seconds = get_sleep_interval(settings)
            next_scheduled_at = datetime.fromtimestamp(time.time() + sleep_seconds).isoformat(timespec="seconds")
            update_local_status(sync_state, current_state="idle", next_scheduled_at=next_scheduled_at)
            logging.info(
                "Aguardando %s segundos para o proximo envio.",
                sleep_seconds,
            )
            wait_until = time.time() + sleep_seconds
            while time.time() < wait_until:
                pause_seconds = min(get_remote_action_interval(settings), max(0, wait_until - time.time()))
                if pause_seconds > 0:
                    time.sleep(pause_seconds)

                if time.time() < wait_until:
                    try:
                        should_exit = poll_remote_action(
                            session=session,
                            settings=settings,
                            sync_state=sync_state,
                            dry_run=args.dry_run,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logging.debug("Falha inesperada ao consultar acoes remotas: %s", exc)
                        should_exit = False

                    if should_exit:
                        update_local_status(sync_state, current_state="updating")
                        return 0
    except KeyboardInterrupt:
        update_local_status(sync_state, current_state="stopped")
        logging.info("Execucao interrompida pelo usuario.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
