from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from .config import settings

# A persistent, isolated Python process runs all heavy DuckDB/Polars work on one
# main thread. FastAPI remains responsive, jobs cannot overlap, and the embedded
# database never inherits stale web-server thread state.
_LOCK = threading.RLock()
_PROCESS: subprocess.Popen[str] | None = None
_LOG_HANDLE: TextIO | None = None
_SUBMITTED_COUNT = 0


def _job_log_path() -> Path:
    path = settings.data_path / "logs" / "background_jobs.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _start_process() -> subprocess.Popen[str]:
    global _PROCESS, _LOG_HANDLE
    backend_dir = settings.root_dir / "backend"
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(backend_dir) + (os.pathsep + existing if existing else "")
    _LOG_HANDLE = _job_log_path().open("a", encoding="utf-8")
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    _PROCESS = subprocess.Popen(
        [sys.executable, "-m", "app.job_worker"],
        cwd=settings.root_dir,
        env=env,
        stdin=subprocess.PIPE,
        stdout=_LOG_HANDLE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        creationflags=creationflags,
    )
    return _PROCESS


def _ensure_process() -> subprocess.Popen[str]:
    global _PROCESS
    with _LOCK:
        if _PROCESS is not None and _PROCESS.poll() is None and _PROCESS.stdin is not None:
            return _PROCESS
        if _PROCESS is not None:
            try:
                _PROCESS.stdin and _PROCESS.stdin.close()
            except OSError:
                pass
        if _LOG_HANDLE is not None:
            try:
                _LOG_HANDLE.close()
            except OSError:
                pass
        return _start_process()


def start_job_worker() -> dict[str, Any]:
    _ensure_process()
    return queue_status()


def submit_background_job(name: str, target: Callable[..., Any], *args: Any) -> None:
    global _SUBMITTED_COUNT
    payload = {
        "name": name,
        "module": target.__module__,
        "function": target.__name__,
        "args": list(args),
    }
    line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
    with _LOCK:
        process = _ensure_process()
        try:
            assert process.stdin is not None
            process.stdin.write(line)
            process.stdin.flush()
            _SUBMITTED_COUNT += 1
        except (BrokenPipeError, OSError):
            process = _start_process()
            assert process.stdin is not None
            process.stdin.write(line)
            process.stdin.flush()
            _SUBMITTED_COUNT += 1


def shutdown_job_worker() -> None:
    global _PROCESS, _LOG_HANDLE
    with _LOCK:
        process = _PROCESS
        _PROCESS = None
        if process is not None:
            try:
                process.stdin and process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        if _LOG_HANDLE is not None:
            try:
                _LOG_HANDLE.close()
            except OSError:
                pass
            _LOG_HANDLE = None


def queue_status() -> dict[str, Any]:
    with _LOCK:
        alive = bool(_PROCESS is not None and _PROCESS.poll() is None)
        return {
            "serialised": True,
            "isolation": "persistent_subprocess",
            "worker_alive": alive,
            "worker_pid": _PROCESS.pid if alive and _PROCESS is not None else None,
            "submitted_count": _SUBMITTED_COUNT,
            "log_file": str(_job_log_path()),
        }
