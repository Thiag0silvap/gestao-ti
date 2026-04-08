import argparse
import getpass
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime

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

DEFAULT_INTERVAL_SECONDS = 300
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
)
MEMORY_TYPE_MAP = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    34: "DDR5",
}


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
    timeout_raw = os.getenv("REQUEST_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))

    try:
        interval_seconds = max(30, int(interval_raw))
    except ValueError as exc:
        raise ValueError("INTERVAL_SECONDS deve ser um numero inteiro >= 30") from exc

    try:
        timeout_seconds = max(5, int(timeout_raw))
    except ValueError as exc:
        raise ValueError("REQUEST_TIMEOUT_SECONDS deve ser um numero inteiro >= 5") from exc

    settings = {
        "api_url": (os.getenv("API_URL") or "").strip(),
        "api_key": (os.getenv("AGENT_API_KEY") or "").strip(),
        "interval_seconds": interval_seconds,
        "timeout_seconds": timeout_seconds,
        "sector": (os.getenv("DEFAULT_SECTOR") or DEFAULT_SECTOR).strip(),
        "patrimony_number": (os.getenv("PATRIMONY_NUMBER") or "").strip(),
        "equipment_status": (os.getenv("EQUIPMENT_STATUS") or DEFAULT_EQUIPMENT_STATUS).strip(),
        "notes": (os.getenv("AGENT_NOTES") or DEFAULT_NOTES).strip(),
        "verify_ssl": get_env_bool("VERIFY_SSL", True),
    }

    if not settings["api_url"]:
        raise ValueError("API_URL nao definida no .env do agent")

    if not settings["api_key"]:
        raise ValueError("AGENT_API_KEY nao definida no .env do agent")

    return settings


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


def normalize_blank(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if normalized.lower() in {"unknown", "none", "null"}:
        return None

    return normalized


def get_hostname() -> str:
    return socket.gethostname()


def get_logged_user() -> str:
    try:
        return getpass.getuser().lower()
    except Exception:
        return os.getenv("USERNAME", "desconhecido").lower()


def get_ip_address() -> str | None:
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        if ip_address and not ip_address.startswith("127.") and not ip_address.startswith("169.254."):
            return ip_address
    except Exception:
        logging.debug("Falha ao obter IP via gethostbyname", exc_info=True)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip_address = sock.getsockname()[0]
            if ip_address and not ip_address.startswith("127."):
                return ip_address
    except Exception:
        logging.debug("Falha ao obter IP via socket externo", exc_info=True)

    try:
        stats = psutil.net_if_stats()
        for interface_name, addresses in psutil.net_if_addrs().items():
            interface_name_normalized = interface_name.lower()
            if any(token in interface_name_normalized for token in IGNORED_INTERFACE_TOKENS):
                continue

            interface_stats = stats.get(interface_name)
            if interface_stats and not interface_stats.isup:
                continue

            for address in addresses:
                if (
                    address.family == socket.AF_INET
                    and address.address
                    and not address.address.startswith("127.")
                    and not address.address.startswith("169.254.")
                ):
                    return address.address
    except Exception:
        logging.debug("Falha ao obter IP via interfaces locais", exc_info=True)

    return None


def get_mac_address() -> str:
    try:
        stats = psutil.net_if_stats()
        addresses = psutil.net_if_addrs()

        for interface_name, interface_addresses in addresses.items():
            interface_stats = stats.get(interface_name)
            if interface_stats and not interface_stats.isup:
                continue

            for address in interface_addresses:
                mac_value = address.address.replace("-", ":").upper()
                if address.family == psutil.AF_LINK and len(mac_value) == 17 and mac_value != "00:00:00:00:00:00":
                    return mac_value
    except Exception:
        logging.debug("Falha ao obter MAC via psutil", exc_info=True)

    mac = uuid.getnode()
    return ":".join([f"{(mac >> elements) & 0xFF:02X}" for elements in range(40, -1, -8)])


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


def build_payload(settings: dict) -> dict:
    hostname = get_hostname()
    memory_type, memory_speed = get_memory_details()
    cpu_usage_percent = get_cpu_usage_percent()
    memory_usage_percent = get_memory_usage_percent()
    disk_free_gb = get_disk_free_gb()
    disk_free_percent = get_disk_free_percent()
    uptime_hours = get_uptime_hours()

    return {
        "hostname": hostname,
        "user": get_logged_user(),
        "ip_address": get_ip_address(),
        "mac_address": get_mac_address(),
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
        "last_maintenance_date": None,
        "notes": settings["notes"],
    }


def log_payload(payload: dict) -> None:
    summary = {
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
    }
    logging.info("Payload coletado: %s", json.dumps(summary, ensure_ascii=True))


def send_inventory(session: requests.Session, settings: dict, dry_run: bool = False) -> bool:
    payload = build_payload(settings)
    headers = {"X-API-KEY": settings["api_key"]}

    log_payload(payload)

    if dry_run:
        logging.info("Modo dry-run ativo. Nenhum dado foi enviado para a API.")
        return True

    try:
        response = session.post(
            settings["api_url"],
            json=payload,
            headers=headers,
            timeout=settings["timeout_seconds"],
            verify=settings["verify_ssl"],
        )
    except requests.exceptions.RequestException as exc:
        logging.error("Erro de conexao com a API: %s", exc)
        return False

    response_text = response.text.strip()

    if 200 <= response.status_code < 300:
        logging.info("Sincronizacao concluida com status %s", response.status_code)
        if response_text:
            logging.info("Resposta da API: %s", response_text)
        return True

    logging.error("Falha ao sincronizar. Status: %s", response.status_code)
    if response_text:
        logging.error("Resposta da API: %s", response_text)
    return False


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

    try:
        settings = get_settings()
    except ValueError as exc:
        logging.error("%s", exc)
        return 1

    session = create_http_session()

    logging.info("Agente iniciado.")
    logging.info("API_URL: %s", settings["api_url"])
    logging.info("Intervalo configurado: %s segundos", settings["interval_seconds"])

    try:
        while True:
            success = send_inventory(session, settings, dry_run=args.dry_run)

            if args.once:
                return 0 if success else 1

            logging.info(
                "Aguardando %s segundos para o proximo envio.",
                settings["interval_seconds"],
            )
            time.sleep(settings["interval_seconds"])
    except KeyboardInterrupt:
        logging.info("Execucao interrompida pelo usuario.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
