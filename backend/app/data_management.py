from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .accounting import rebuild_accounting_from_sources
from .config import settings
from .database import (
    COMPANY_ID,
    get_duckdb,
    get_sqlite,
    get_uploaded_file,
    next_data_version,
    utc_now,
)
from .pipeline import CONTEXT_ONLY_DATASETS, refresh_context_layers, refresh_gold_layers
from .upload_intelligence import rebuild_company_context_from_uploads
from .validation import run_validations


SOURCE_TABLES = [
    "assets_liabilities",
    "transactions",
    "payments",
    "bank_transactions",
    "customers",
    "suppliers",
    "inventory",
    "budgets",
    "payroll_records",
    "statement_snapshots",
    "market_signals",
    "generic_documents",
]


def _safe_remove(path: Path) -> bool:
    """Remove only paths inside LedgerFlow's configured data directory."""
    try:
        root = settings.data_path.resolve()
        resolved = path.resolve()
        if resolved == root or root not in resolved.parents:
            return False
        if resolved.is_dir():
            shutil.rmtree(resolved, ignore_errors=True)
        else:
            resolved.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _backup_upload(record: dict[str, Any]) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = settings.data_path / "backups" / f"before_delete_upload_{record['id']}_{timestamp}"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "upload_record.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

    copied: set[str] = set()
    candidates: list[Path] = []
    for value in [record.get("raw_path"), record.get("curated_path")]:
        if value:
            candidates.append(Path(str(value)))
    for value in record.get("silver_paths") or []:
        if value:
            candidates.append(Path(str(value)))
    metadata = record.get("metadata") or {}
    if metadata.get("file_metadata_path"):
        candidates.append(Path(str(metadata["file_metadata_path"])))

    bronze_dir = settings.data_path / "bronze" / COMPANY_ID / str(record.get("file_id") or "")
    if record.get("file_id"):
        candidates.append(bronze_dir)
    digest = str(record.get("sha256") or "")
    if digest:
        candidates.extend((settings.data_path / "raw").glob(f"{digest[:12]}_*"))

    files_dir = destination / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in copied or not resolved.exists():
            continue
        copied.add(key)
        target = files_dir / f"{len(copied):02d}_{resolved.name}"
        if resolved.is_dir():
            shutil.copytree(resolved, target, dirs_exist_ok=True)
        else:
            shutil.copy2(resolved, target)
    return str(destination)


def move_uploaded_file(upload_id: int, intake_category: str) -> dict[str, Any]:
    if intake_category not in {"setup", "recurring"}:
        raise ValueError("File category must be setup or recurring.")
    record = get_uploaded_file(upload_id)
    if not record:
        raise ValueError("Uploaded file not found.")

    metadata = dict(record.get("metadata") or {})
    metadata["intake_category"] = intake_category
    metadata.setdefault("category_history", []).append({"changed_at": utc_now(), "intake_category": intake_category})
    analysis = dict(record.get("analysis") or {})
    if analysis:
        analysis["intake_category"] = intake_category

    sql = get_sqlite()
    sql.execute(
        "UPDATE uploaded_files SET intake_category=?, metadata_json=?, analysis_json=?, last_processed_at=? WHERE id=?",
        (intake_category, json.dumps(metadata, default=str), json.dumps(analysis, default=str), utc_now(), upload_id),
    )
    sql.commit()
    sql.close()
    rebuild_company_context_from_uploads()
    return {
        "ok": True,
        "upload_id": upload_id,
        "filename": record.get("filename"),
        "intake_category": intake_category,
        "message": f"{record.get('filename')} was moved to {'Permanent setup' if intake_category == 'setup' else 'Recurring evidence'} without reprocessing its data.",
    }



def purge_uploaded_file_for_reprocessing(upload_id: int) -> dict[str, Any]:
    """Remove a stale contribution without rebuilding dashboards mid-retry.

    The corrective job already holds a staging copy of the original bytes. The
    replacement upload will refresh accounting, validation, Gold data and agent
    context once, after the corrected records have been committed.
    """
    record = get_uploaded_file(upload_id)
    if not record:
        raise ValueError("Uploaded file not found.")
    filename = str(record.get("filename") or "")
    metadata = dict(record.get("metadata") or {})

    con = get_duckdb()
    try:
        for table in SOURCE_TABLES:
            con.execute(f"DELETE FROM {table} WHERE source_file=?", (filename,))
        con.execute("DELETE FROM invoices WHERE source_file=? OR source_upload_id=?", (filename, upload_id))
        con.execute("DELETE FROM account_validation_tasks WHERE source_file=? OR source_id=?", (filename, str(upload_id)))
    finally:
        con.close()

    sql = get_sqlite()
    try:
        sql.execute("DELETE FROM row_fingerprints WHERE source_file_id=?", (upload_id,))
        sql.execute("DELETE FROM import_jobs WHERE upload_id=?", (upload_id,))
        sql.execute("DELETE FROM uploaded_files WHERE id=?", (upload_id,))
        sql.commit()
    finally:
        sql.close()

    file_paths: list[Path] = []
    for value in [record.get("raw_path"), record.get("curated_path")]:
        if value:
            file_paths.append(Path(str(value)))
    for value in record.get("silver_paths") or []:
        if value:
            file_paths.append(Path(str(value)))
    if metadata.get("file_metadata_path"):
        file_paths.append(Path(str(metadata["file_metadata_path"])))
    if record.get("file_id"):
        file_paths.append(settings.data_path / "bronze" / COMPANY_ID / str(record["file_id"]))
    digest = str(record.get("sha256") or "")
    if digest:
        file_paths.extend((settings.data_path / "raw").glob(f"{digest[:12]}_*"))
    for path in sorted(set(file_paths), key=lambda item: len(str(item)), reverse=True):
        _safe_remove(path)
    return {"ok": True, "upload_id": upload_id, "filename": filename}

def delete_uploaded_file(upload_id: int, create_backup: bool = True) -> dict[str, Any]:
    record = get_uploaded_file(upload_id)
    if not record:
        raise ValueError("Uploaded file not found.")
    filename = str(record.get("filename") or "")
    document_type = str(record.get("document_type") or "generic")
    metadata = dict(record.get("metadata") or {})
    affected = [str(item) for item in (metadata.get("detected_document_types") or [document_type]) if item]
    backup_path = _backup_upload(record) if create_backup else ""

    con = get_duckdb()
    try:
        for table in SOURCE_TABLES:
            con.execute(f"DELETE FROM {table} WHERE source_file=?", (filename,))
        con.execute("DELETE FROM invoices WHERE source_file=? OR source_upload_id=?", (filename, upload_id))
        con.execute("DELETE FROM account_validation_tasks WHERE source_file=? OR source_id=?", (filename, str(upload_id)))
    finally:
        con.close()

    sql = get_sqlite()
    try:
        sql.execute("DELETE FROM row_fingerprints WHERE source_file_id=?", (upload_id,))
        sql.execute("DELETE FROM import_jobs WHERE upload_id=?", (upload_id,))
        sql.execute("DELETE FROM uploaded_files WHERE id=?", (upload_id,))
        sql.execute(
            "INSERT INTO clear_events(created_at, scope, backup_path, details_json) VALUES (?, ?, ?, ?)",
            (utc_now(), "single_upload", backup_path, json.dumps({"upload_id": upload_id, "filename": filename, "document_type": document_type})),
        )
        sql.commit()
    finally:
        sql.close()

    file_paths: list[Path] = []
    for value in [record.get("raw_path"), record.get("curated_path")]:
        if value:
            file_paths.append(Path(str(value)))
    for value in record.get("silver_paths") or []:
        if value:
            file_paths.append(Path(str(value)))
    if metadata.get("file_metadata_path"):
        file_paths.append(Path(str(metadata["file_metadata_path"])))
    if record.get("file_id"):
        file_paths.append(settings.data_path / "bronze" / COMPANY_ID / str(record["file_id"]))
    digest = str(record.get("sha256") or "")
    if digest:
        file_paths.extend((settings.data_path / "raw").glob(f"{digest[:12]}_*"))
    for path in sorted(set(file_paths), key=lambda item: len(str(item)), reverse=True):
        _safe_remove(path)

    new_version = next_data_version(COMPANY_ID, f"Removed uploaded evidence {filename}", affected or [document_type])
    accounting = rebuild_accounting_from_sources()
    run_validations()
    if affected and set(affected).issubset(CONTEXT_ONLY_DATASETS):
        pipeline = refresh_context_layers(affected)
    else:
        pipeline = refresh_gold_layers(affected)
    context = rebuild_company_context_from_uploads()
    return {
        "ok": True,
        "upload_id": upload_id,
        "filename": filename,
        "document_type": document_type,
        "data_version": new_version,
        "backup_created": bool(backup_path),
        "backup_path": backup_path,
        "accounting": accounting,
        "pipeline": pipeline,
        "remaining_uploads": int(context.get("pipeline", {}).get("uploads") or 0),
        "message": f"{filename} and the records contributed by that source were removed. Dependent dashboards and agent context were rebuilt.",
    }
