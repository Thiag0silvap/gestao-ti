import getpass
import platform
import socket
import subprocess
import uuid

import psutil
import requests


API_URL = "http://127.0.0.1:8000/computers"


def run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False
        )
        output = result.stdout.strip()

        if result.returncode != 0 or not output:
            return None

        return output
    except Exception:
        return None


def get_hostname() -> str:
    return socket.gethostname()


def get_logged_user() -> str:
    return getpass.getuser()


def get_ip_address() -> str | None:
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception:
        return None


def get_mac_address() -> str:
    mac = uuid.getnode()
    mac_str = ":".join([f"{(mac >> elements) & 0xff:02X}" for elements in range(40, -1, -8)])
    return mac_str


def get_cpu() -> str:
    cpu_name = run_command([
        "wmic", "cpu", "get", "name"
    ])

    if cpu_name:
        lines = [line.strip() for line in cpu_name.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]

    return platform.processor() or "Não identificado"


def get_ram() -> str:
    total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3))
    return f"{total_ram_gb}GB"


def get_disk() -> str:
    total_disk_gb = round(psutil.disk_usage("C:\\").total / (1024 ** 3))
    return f"{total_disk_gb}GB"


def get_os() -> str:
    return f"{platform.system()} {platform.release()}"


def get_manufacturer() -> str | None:
    output = run_command([
        "wmic", "computersystem", "get", "manufacturer"
    ])

    if output:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]

    return None


def get_model() -> str | None:
    output = run_command([
        "wmic", "computersystem", "get", "model"
    ])

    if output:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]

    return None


def get_serial_number() -> str | None:
    output = run_command([
        "wmic", "bios", "get", "serialnumber"
    ])

    if output:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]

    return None


def build_payload() -> dict:
    hostname = get_hostname()

    return {
        "hostname": hostname,
        "user": get_logged_user(),
        "ip_address": get_ip_address(),
        "mac_address": get_mac_address(),
        "cpu": get_cpu(),
        "ram": get_ram(),
        "disk": get_disk(),
        "os": get_os(),
        "sector": "TI",
        "patrimony_number": hostname,
        "serial_number": get_serial_number(),
        "manufacturer": get_manufacturer(),
        "model": get_model(),
        "equipment_status": "Ativo",
        "last_maintenance_date": None,
        "notes": "Cadastro automático pelo agente"
    }


def send_inventory() -> None:
    payload = build_payload()

    print("Enviando dados para API...")
    print(payload)

    response = requests.post(API_URL, json=payload, timeout=10)

    print(f"Status Code: {response.status_code}")
    print("Resposta da API:")

    try:
        print(response.json())
    except Exception:
        print(response.text)


if __name__ == "__main__":
    send_inventory()