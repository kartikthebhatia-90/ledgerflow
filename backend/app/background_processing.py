from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .config import settings
from .database import (
    completed_upload_count,
    create_upload_processing_task,
    get_upload_processing_task,
    get_uploaded_file,
    update_upload_processing_task,
    utc_now,
)
from .ingestion import process_upload, store_source_document
from .upload_intelligence import build_upload_analysis, incorporate_upload_into_context
from .validation import run_validations
from .decision_context import refresh_decision_context
from .superset_bridge import refresh_superset_views
from .business_store import record_ingestion_lineage


def start_upload_job(filename: str, content: bytes, intake_category: str, declared_document_type: str) -> dict[str, Any]:
    job_id = f"uploadjob_{uuid.uuid4().hex[:18]}"
    staging = settings.data_path / "staging" / "upload_jobs"
    staging.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in Path(filename).name)
    pending_path = staging / f"{job_id}_{safe_name}"
    pending_path.write_bytes(content)
    task = create_upload_processing_task(job_id, filename, intake_category, declared_document_type)
    task["pending_path"] = str(pending_path)
    return task


def start_existing_upload_job(upload_id: int, intake_category: str, declared_document_type: str) -> dict[str, Any]:
    """Create a corrective processing job from LedgerFlow's preserved source bytes."""
    record = get_uploaded_file(upload_id)
    if not record:
        raise ValueError("Uploaded file not found.")
    candidates = [record.get("raw_path")]
    metadata = dict(record.get("metadata") or {})
    if metadata.get("file_metadata_path"):
        candidates.append(str(Path(str(metadata["file_metadata_path"])).parent / str(record.get("original_filename") or record.get("filename") or "")))
    source_path = next((Path(str(value)) for value in candidates if value and Path(str(value)).is_file()), None)
    if source_path is None:
        bronze_dir = settings.data_path / "bronze" / str(record.get("company_id") or "default") / str(record.get("file_id") or "")
        if bronze_dir.exists():
            source_path = next((path for path in bronze_dir.iterdir() if path.is_file() and path.suffix.lower() != ".json"), None)
    if source_path is None or not source_path.exists():
        raise ValueError("The preserved source file could not be found. Delete the failed record and upload the original file again.")
    return start_upload_job(
        str(record.get("original_filename") or record.get("filename") or source_path.name),
        source_path.read_bytes(),
        intake_category,
        declared_document_type,
    )


def process_upload_job(job_id: str, pending_path: str) -> None:
    task = get_upload_processing_task(job_id)
    if not task:
        return
    path = Path(pending_path)

    def progress(stage: str, value: int, message: str) -> None:
        print(f"upload {job_id}: stage {stage} ({value}%)", flush=True)
        update_upload_processing_task(
            job_id,
            status="processing",
            stage=stage,
            progress=value,
            stage_message=message,
        )
        # A brief yield makes each real stage visible without deliberately slowing large files.
        time.sleep(0.06)

    try:
        print(f"upload {job_id}: received", flush=True)
        update_upload_processing_task(
            job_id,
            status="processing",
            stage="received",
            progress=5,
            stage_message="File received; beginning secure local processing",
        )
        content = path.read_bytes()
        extension = Path(str(task.get("filename") or path.name)).suffix.lower()
        print(f"upload {job_id}: reading prior upload count", flush=True)
        prior_count = completed_upload_count()
        print(f"upload {job_id}: dispatching {extension}", flush=True)
        if extension == ".pdf":
            result = store_source_document(
                str(task["filename"]), content, str(task["intake_category"]),
                str(task["declared_document_type"]), progress_callback=progress,
            )
        else:
            result = process_upload(
                str(task["filename"]), content, str(task["intake_category"]),
                str(task["declared_document_type"]), progress_callback=progress,
            )
        print(f"upload {job_id}: ingestion complete ({result.get('document_type')})", flush=True)
        update_upload_processing_task(
            job_id,
            status="processing",
            stage="analysing",
            progress=95,
            upload_id=int(result.get("upload_id") or 0),
            stage_message="Explaining what the file contains and how it changes the company view",
        )
        analysis, assistant_message, lifecycle = build_upload_analysis(result, prior_count)
        print(f"upload {job_id}: deterministic analysis complete", flush=True)
        incorporate_upload_into_context(analysis, assistant_message)
        print(f"upload {job_id}: company context complete", flush=True)
        result = {**result, "analysis": analysis, "assistant_message": assistant_message, "lifecycle_phase": lifecycle}
        # Market/context-only evidence does not change financial ledgers. Running
        # the complete finance validation suite here adds avoidable DuckDB work
        # and can delay the job after all useful market processing has finished.
        # Financial uploads still refresh validations immediately; a periodic
        # validation task also remains available for the whole application.
        document_type = str(result.get("document_type") or "")
        if document_type not in {
            "market_context",
            "business_requirements",
            "material_contracts",
            "use_cases_user_stories",
            "generic",
        }:
            run_validations()
            print(f"upload {job_id}: validations complete", flush=True)
        else:
            print(f"upload {job_id}: finance validations skipped for {document_type}", flush=True)
        try:
            refresh_decision_context(f"upload_completed:{result.get('upload_id') or 0}")
            print(f"upload {job_id}: temporal decision context refreshed", flush=True)
        except Exception as exc:
            print(f"upload {job_id}: temporal decision context refresh skipped: {type(exc).__name__}: {exc}", flush=True)
        try:
            refresh_superset_views()
            print(f"upload {job_id}: Superset analytics snapshot refreshed", flush=True)
        except Exception as exc:
            print(f"upload {job_id}: Superset snapshot refresh skipped: {type(exc).__name__}: {exc}", flush=True)
        progress("business_store", 98, "Updating business.db, Clippy's launch summary and source lineage")
        business_context = record_ingestion_lineage(result, "upload_completed")
        result["business_store"] = business_context
        print(f"upload {job_id}: writing completed job state", flush=True)
        update_upload_processing_task(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            stage_message="File understood, database updated and agent context refreshed",
            result_json=result,
            analysis_json=analysis,
            assistant_message=assistant_message,
            completed_at=utc_now(),
        )
        print(f"upload {job_id}: completed", flush=True)
    except Exception as exc:
        update_upload_processing_task(
            job_id,
            status="failed",
            stage="failed",
            progress=100,
            stage_message="Processing stopped",
            error_message=f"{type(exc).__name__}: {exc}",
            completed_at=utc_now(),
        )
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
