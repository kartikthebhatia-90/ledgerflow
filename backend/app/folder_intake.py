from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .background_processing import process_upload_job, start_upload_job
from .config import settings
from .document_routing import folder_declared_document_type
from .job_queue import submit_background_job

_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".pdf"}
_STATE: dict[str, Any] = {
    "last_scan_at": "",
    "last_result": {"queued": [], "errors": []},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _roots() -> dict[str, Path]:
    # A packaged dataset may live inside data/source_files so the entire company
    # state stays under data/. The marker deliberately takes precedence over an
    # older copied .env that still points FOLDER_INTAKE_DIR at ./file_drop.
    packaged_root = settings.data_path / "source_files"
    marker = packaged_root / ".use_as_folder_intake"
    root = packaged_root if marker.exists() else settings.folder_intake_path
    return {
        "root": root,
        "setup": root / "permanent",
        "recurring": root / "recurring",
        "archive": root / "archive",
    }


def ensure_folder_intake_layout() -> dict[str, str]:
    roots = _roots()
    for key in ("setup", "recurring", "archive"):
        roots[key].mkdir(parents=True, exist_ok=True)
    readme = roots["root"] / "README.txt"
    if not readme.exists():
        readme.write_text(
            "LedgerFlow folder intake\n\n"
            "Paste permanent/setup files into the displayed permanent path.\n"
            "Paste invoices, bank statements, sales invoices and payroll into the displayed recurring path.\n\n"
            "Optional: create a document-type subfolder such as:\n"
            "  file_drop/permanent/cash_flow_statement\n"
            "  file_drop/permanent/business_requirements\n"
            "  file_drop/recurring/bank_statements\n"
            "  file_drop/recurring/payroll\n\n"
            "Supported extensions: CSV, XLSX, XLSM and PDF. Files are moved to file_drop/archive after they are queued.\n",
            encoding="utf-8",
        )
    for category, examples in {
        "setup": "Permanent company documents belong here. Use optional type subfolders for exact routing.\n",
        "recurring": "Recurring invoices, receipts, bank statements, sales invoices and payroll belong here.\n",
    }.items():
        note = roots[category] / "README.txt"
        if not note.exists():
            note.write_text(examples, encoding="utf-8")
    return {key: str(value) for key, value in roots.items()}


def _candidate_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in _ALLOWED_EXTENSIONS
        and not path.name.startswith("~$")
        and not path.name.startswith(".")
    )


def folder_intake_status() -> dict[str, Any]:
    paths = ensure_folder_intake_layout()
    roots = _roots()
    setup_files = _candidate_files(roots["setup"])
    recurring_files = _candidate_files(roots["recurring"])
    return {
        "enabled": settings.folder_intake_enabled,
        "paths": paths,
        "scan_seconds": max(2, int(settings.folder_intake_scan_seconds)),
        "pending": {
            "setup": [str(path.relative_to(roots["setup"])) for path in setup_files],
            "recurring": [str(path.relative_to(roots["recurring"])) for path in recurring_files],
            "total": len(setup_files) + len(recurring_files),
        },
        "last_scan_at": _STATE.get("last_scan_at", ""),
        "last_result": _STATE.get("last_result", {"queued": [], "errors": []}),
    }


def scan_folder_intake() -> dict[str, Any]:
    ensure_folder_intake_layout()
    if not settings.folder_intake_enabled:
        result = {"ok": True, "enabled": False, "queued": [], "errors": []}
        _STATE.update({"last_scan_at": _now(), "last_result": result})
        return result

    roots = _roots()
    queued: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for category_key, intake_category in (("setup", "setup"), ("recurring", "recurring")):
        category_root = roots[category_key]
        for path in _candidate_files(category_root):
            relative = path.relative_to(category_root)
            try:
                content = path.read_bytes()
                declared_document_type = folder_declared_document_type(path, category_root)
                task = start_upload_job(path.name, content, intake_category, declared_document_type)
                pending_path = str(task.pop("pending_path"))
                submit_background_job("folder-intake", process_upload_job, str(task["job_id"]), pending_path)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_target = roots["archive"] / intake_category / relative.parent / f"{timestamp}__{path.name}"
                archive_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(archive_target))
                queued.append({
                    "job_id": task["job_id"],
                    "filename": path.name,
                    "intake_category": intake_category,
                    "declared_document_type": declared_document_type,
                    "archived_to": str(archive_target),
                })
            except Exception as exc:
                errors.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})

    result = {"ok": not errors, "enabled": True, "queued": queued, "errors": errors}
    _STATE.update({"last_scan_at": _now(), "last_result": result})
    return result
