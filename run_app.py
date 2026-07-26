from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(ROOT)
load_dotenv(ROOT / ".env")


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex((host, port)) == 0


def _existing_ledgerflow(host: str, port: int) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") and payload.get("app") == os.getenv("APP_NAME", "LedgerFlow"):
            return payload
        return None
    except Exception:
        return None


def _open_when_ready(url: str, host: str, port: int) -> None:
    """Open the UI only after the API health endpoint is ready."""
    for _ in range(180):
        if _existing_ledgerflow(host, port):
            webbrowser.open(url)
            return
        time.sleep(0.25)
    print(f"LedgerFlow started but the browser was not opened automatically. Open {url} manually.")


try:
    import uvicorn
except ImportError as exc:
    raise SystemExit(
        "Dependencies are not installed. Run setup_and_run.bat on Windows or ./setup_and_run.sh on macOS/Linux."
    ) from exc

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    url = f"http://{host}:{port}/?build=3.3.5"

    # Prevent the common DuckDB lock failure caused by starting LedgerFlow twice.
    if _port_open(host, port):
        existing = _existing_ledgerflow(host, port)
        if existing:
            existing_version = str(existing.get("version") or "unknown")
            if existing_version != "3.3.5":
                raise SystemExit(
                    f"An older LedgerFlow server ({existing_version}) is still running on {url}. "
                    "Stop the old VS Code terminal with Ctrl+C, close any other LedgerFlow Python process, then run this package again."
                )
            print(f"LedgerFlow 3.3.5 is already running at {url}.")
            webbrowser.open(url)
            raise SystemExit(0)
        raise SystemExit(
            f"Port {port} is already in use by another application. Stop it or change APP_PORT in .env before starting LedgerFlow."
        )

    print(f"LedgerFlow 3.3.5 is starting at {url}")
    threading.Thread(target=_open_when_ready, args=(url, host, port), daemon=True).start()
    uvicorn.run("app.main:app", host=host, port=port, reload=False, workers=1)
