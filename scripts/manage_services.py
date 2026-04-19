#!/usr/bin/env python3
"""Cross-platform service manager for Cuckoo-Echo.

Usage:
    python scripts/manage_services.py start     # Start all services
    python scripts/manage_services.py stop    # Stop all services
    python scripts/manage_services.py status   # Check service status
    python scripts/manage_services.py restart  # Restart all services
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent

SERVICES = {
    "api_gateway": {
        "port": 8000,
        "command": ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"],
    },
    "chat_service": {
        "port": 8001,
        "command": ["uvicorn", "chat_service.main:app", "--host", "0.0.0.0", "--port", "8001"],
    },
    "admin_service": {
        "port": 8002,
        "command": ["python", "-m", "admin_service.main"],
    },
}


CREATE_NEW_CONSOLE = 0x00000010 if sys.platform == "win32" else 0


def get_uvicorn_processes() -> list[dict]:
    """Find running uvicorn and python processes."""
    processes = []
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-Command", "Get-Process python,uvicorn -ErrorAction SilentlyContinue | Select-Object Id,ProcessName | ConvertTo-Json"],
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn|python.*admin_service"],
                capture_output=True,
                text=True,
            )
        if result.returncode == 0 and result.stdout.strip():
            processes.append({"platform": sys.platform, "output": result.stdout})
    except Exception:
        pass
    return processes


def check_port(port: int, retries: int = 3) -> bool:
    """Check if a port is in use."""
    import socket

    for _ in range(retries):
        try:
            with socket.create_connection(("localhost", port), timeout=2):
                return True
        except (OSError, ConnectionRefusedError):
            import time
            time.sleep(1)
    return False


def start_services() -> None:
    """Start all services."""
    print("=" * 50)
    print("Starting Cuckoo-Echo services...")

    for name, config in SERVICES.items():
        port = config["port"]
        if check_port(port):
            print(f"  {name}: already running on port {port}")
            continue

        print(f"  Starting {name} on port {port}...")

        if sys.platform == "win32":
            cmd_str = " ".join(config["command"])
            subprocess.Popen(
                ["powershell", "-NoExit", "-Command", 
                 f"cd '{PROJECT_DIR}'; uv run {cmd_str}"],
                cwd=PROJECT_DIR,
                creationflags=CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(
                ["uv", "run"] + config["command"],
                cwd=PROJECT_DIR,
                start_new_session=True,
            )
        
        print(f"    Launched: {name}")

    print("")
    print("Services started:")
    for name, config in SERVICES.items():
        print(f"  {name}: http://localhost:{config['port']}")

    print("=" * 50)


def stop_services() -> None:
    """Stop all services."""
    print("=" * 50)
    print("Stopping Cuckoo-Echo services...")

    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-Command", 
             "Get-Process -Name python,powershell -ErrorAction SilentlyContinue | "
             "Where-Object {$_.CommandLine -match 'uvicorn|admin_service|api_gateway|chat_service'} | "
             "Stop-Process -Force"],
            check=False,
        )
    else:
        subprocess.run(["pkill", "-f", "uvicorn|admin_service"], check=False)

    print("  All services stopped.")
    print("=" * 50)


def check_health(port: int) -> bool:
    """Check if service is healthy via HTTP."""
    import urllib.request
    import urllib.error
    
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def status_services() -> None:
    """Check service status."""
    print("=" * 50)
    print("Service status:")

    all_running = True
    for name, config in SERVICES.items():
        port = config["port"]
        port_open = check_port(port)
        healthy = check_health(port) if port_open else False
        
        if healthy:
            print(f"  {name}: HEALTHY on port {port}")
        elif port_open:
            print(f"  {name}: RUNNING (port open) on port {port}")
        else:
            print(f"  {name}: STOPPED")
            all_running = False

    print("=" * 50)
    return 0 if all_running else 1


def restart_services() -> None:
    """Restart all services."""
    stop_services()
    import time
    time.sleep(2)
    start_services()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1].lower()

    if command == "start":
        start_services()
        return 0
    elif command == "stop":
        stop_services()
        return 0
    elif command == "status":
        return status_services()
    elif command == "restart":
        restart_services()
        return 0
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())