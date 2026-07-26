from __future__ import annotations

from typing import Any

from .background_processing import process_upload_job, start_existing_upload_job
from .data_management import move_uploaded_file
from .database import list_active_upload_processing_tasks, list_uploaded_files
from .document_routing import expected_intake_category, strong_filename_document_hint
from .job_queue import submit_background_job

_COMPLETE = {"committed", "stored_source", "pending_mapping"}

_COMPATIBLE_TYPES = {
    "balance_sheet": {"balance_sheet", "assets_liabilities", "assets", "liabilities"},
    "supplier_invoices": {"supplier_invoices", "invoices"},
    "sales_invoices": {"sales_invoices", "invoices"},
    "aged_debtors_creditors": {"aged_debtors_creditors"},
}

def _type_is_compatible(expected_type: str, recorded_types: set[str]) -> bool:
    accepted = _COMPATIBLE_TYPES.get(expected_type, {expected_type})
    return bool(accepted & recorded_types)



def _recorded_types(item: dict[str, Any]) -> set[str]:
    values = {str(item.get("document_type") or "").strip().lower()}
    metadata = dict(item.get("metadata") or {})
    values.update(str(value or "").strip().lower() for value in metadata.get("detected_document_types") or [])
    declared = str(item.get("declared_document_type") or "").strip().lower()
    if declared and declared != "auto":
        values.add(declared)
    return {value for value in values if value}


def classification_repair_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for item in list_uploaded_files():
        expected_type = strong_filename_document_hint(str(item.get("filename") or ""))
        if not expected_type:
            continue
        expected_category = expected_intake_category(expected_type, str(item.get("intake_category") or "recurring"))
        status = str(item.get("processing_status") or "").strip().lower()
        types = _recorded_types(item)
        type_mismatch = not _type_is_compatible(expected_type, types)
        category_mismatch = str(item.get("intake_category") or "recurring") != expected_category
        failed_or_stale = status not in _COMPLETE
        if not (type_mismatch or category_mismatch or failed_or_stale):
            continue
        action = "move" if category_mismatch and not type_mismatch and not failed_or_stale else "reprocess"
        plan.append({
            "upload_id": int(item.get("id") or 0),
            "filename": str(item.get("filename") or ""),
            "current_document_type": str(item.get("document_type") or ""),
            "expected_document_type": expected_type,
            "current_intake_category": str(item.get("intake_category") or "recurring"),
            "expected_intake_category": expected_category,
            "processing_status": status,
            "action": action,
            "reason": (
                "The filename identifies a different document category than the stored classification."
                if type_mismatch else
                "The file belongs in the other evidence library."
                if category_mismatch else
                "The previous processing attempt did not complete."
            ),
        })
    return plan


def schedule_classification_repairs() -> dict[str, Any]:
    active = list_active_upload_processing_tasks()
    active_filenames = {str(item.get("filename") or "") for item in active}
    moved: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in classification_repair_plan():
        if item["filename"] in active_filenames:
            skipped.append({**item, "skip_reason": "A processing job for this file is already active."})
            continue
        if item["action"] == "move":
            result = move_uploaded_file(int(item["upload_id"]), str(item["expected_intake_category"]))
            moved.append({**item, "result": result})
            continue
        try:
            task = start_existing_upload_job(
                int(item["upload_id"]),
                str(item["expected_intake_category"]),
                str(item["expected_document_type"]),
            )
            pending_path = str(task.pop("pending_path"))
            submit_background_job("classification-repair", process_upload_job, str(task["job_id"]), pending_path)
            jobs.append({**item, "job": task})
            active_filenames.add(item["filename"])
        except ValueError as exc:
            skipped.append({**item, "skip_reason": str(exc)})
    return {
        "ok": True,
        "repair_count": len(moved) + len(jobs),
        "moved": moved,
        "jobs": jobs,
        "skipped": skipped,
        "remaining_plan": classification_repair_plan(),
    }
