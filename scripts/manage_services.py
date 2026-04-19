#!/usr/bin/env python3
"""Service manager for Cuckoo-Echo. Linux only."""

Usage:
    python scripts/manage_services.py start     # Start all services
    python scripts/manage_services.py stop    # Stop all services
    python scripts/manage_services.py status   # Check service status
    python scripts/manage_services.py restart  # Restart all services
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def check_port(port: int) -> bool:
    """Check if a port is in use."""
    import socket
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def check_health(port: int) -> bool:
    """Check if service is healthy via HTTP."""
    import urllib.request
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
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

        subprocess.Popen(
            config["command"],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    print("")
    print("Services started:")
    for name, config in SERVICES.items():
        print(f"  {name}: http://localhost:{config['port']}")
    print("=" * 50)


def stop_services() -> None:
    """Stop all services."""
    print("=" * 50)
    print("Stopping Cuckoo-Echo services...")

    subprocess.run(["pkill", "-f", "uvicorn|admin_service"], check=False)

    print("  All services stopped.")
    print("=" * 50)


def status_services() -> int:
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
