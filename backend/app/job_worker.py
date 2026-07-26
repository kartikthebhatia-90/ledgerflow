from __future__ import annotations

import importlib
import json
import sys
import traceback
from typing import Any


def _mark_failure(function_name: str, args: list[Any], detail: str) -> None:
    try:
        if function_name == "process_upload_job" and args:
            from .database import update_upload_processing_task, utc_now
            update_upload_processing_task(
                str(args[0]), status="failed", stage="failed", progress=100,
                stage_message="Background processor stopped", error_message=detail,
                completed_at=utc_now(),
            )
        elif function_name == "process_analysis_job" and args:
            from .database import update_competitor_analysis_job, utc_now
            update_competitor_analysis_job(
                str(args[0]), status="failed", stage="failed", progress=100,
                stage_message="Deep analysis processor stopped", error_message=detail,
                completed_at=utc_now(),
            )
    except Exception:
        traceback.print_exc()


def execute(module_name: str, function_name: str, args: list[Any]) -> bool:
    try:
        module = importlib.import_module(module_name)
        target = getattr(module, function_name)
        target(*args)
        return True
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        _mark_failure(function_name, args, detail)
        return False


def service() -> int:
    print("LedgerFlow background business worker ready", flush=True)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
            name = str(payload.get("name") or "job")
            module_name = str(payload["module"])
            function_name = str(payload["function"])
            args = list(payload.get("args") or [])
            print(f"=== {name} started ===", flush=True)
            ok = execute(module_name, function_name, args)
            print(f"=== {name} {'completed' if ok else 'failed'} ===", flush=True)
        except Exception:
            traceback.print_exc()
    return 0


def main() -> int:
    if len(sys.argv) == 1:
        return service()
    if len(sys.argv) != 4:
        print("Usage: python -m app.job_worker [<module> <function> <json-args>]", file=sys.stderr)
        return 2
    module_name, function_name, raw_args = sys.argv[1:]
    args = json.loads(raw_args)
    return 0 if execute(module_name, function_name, list(args)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
