from __future__ import annotations

import asyncio
import json
import uuid
import traceback
from datetime import datetime, timezone
from contextlib import suppress
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from io import BytesIO

from .agent import handle_command, model_status, ollama_available
from .analytics import cash_forecast, dashboard_summary, agent_data_context
from .data_quality import data_quality_dashboard
from .decision_context import initialise_decision_context, decision_context_dashboard, refresh_decision_context
from .context_board import (
    initialise_context_board,
    context_board_dashboard,
    update_context_board_node,
    update_context_board_settings,
    reset_context_board_layout,
    context_file_content,
    save_context_file,
    explain_context_board,
)
from .semantic_layer import semantic_layer_status
from .config import settings
from .database import (
    clear_company_data,
    clear_memory,
    get_company_profile,
    get_generated_document,
    get_integration_settings,
    initialise,
    list_approvals,
    list_generated_documents,
    list_uploaded_files,
    get_upload_processing_task,
    list_active_upload_processing_tasks,
    resolve_approval,
    rows_as_dicts,
    save_company_profile,
    save_generated_document,
    save_integration_settings,
    pipeline_status,
)
from .documents import DOCUMENT_TEMPLATES, generate_document
from .accounting import accounting_dashboard, add_categorisation_rule, rebuild_accounting_from_sources, resolve_invoice_categorisation
from .tax import generate_tax_workpaper, tax_dashboard
from .ingestion import apply_manual_mapping, process_upload, store_source_document
from .job_queue import queue_status, shutdown_job_worker, start_job_worker, submit_background_job
from .background_processing import process_upload_job, start_existing_upload_job, start_upload_job
from .upload_intelligence import upload_library, file_context_for_prompt
from .data_management import delete_uploaded_file, move_uploaded_file
from .competitor_intelligence import analysis_status, process_analysis_job, start_analysis_job
from .classification_repair import classification_repair_plan, schedule_classification_repairs
from .folder_intake import ensure_folder_intake_layout, folder_intake_status, scan_folder_intake
from .memory import memory_context
from .agent_context import agent_context_status, clear_working_context, read_assistant_profile, save_assistant_profile
from .marketing import marketing_dashboard
from .inventory import inventory_dashboard, sync_inventory_from_invoices
from .hr import hr_dashboard, sync_employee_profiles
from .money_map import money_map_dashboard
from .tax_opportunities import analyse_tax_opportunities
from .superset_bridge import (
    superset_status, guest_token_for_department, refresh_superset_views,
)
from .pipeline import build_company_baseline, build_information_requests, build_market_profile, full_pipeline_rebuild, refresh_gold_layers, refresh_market_snapshot
from .business_store import initialise_business_store, rebuild_business_context, business_store_status
from .dashboard_integrity import dashboard_integrity
from .research import company_market_signals, search_web
from .schemas import (
    AgentCommand,
    AgentResponse,
    ApprovalResolution,
    ClearDataRequest,
    CompanyProfile,
    MappingRequest,
    OllamaTestRequest,
    RebuildPipelineRequest,
    GenerateDocumentRequest,
    ResearchRequest,
    SearchTestRequest,
    InvoiceCategorisationResolution, AssistantProfileUpdate,
    CategorisationRuleRequest,
    IntegrationSettingsRequest,
    UploadCategoryChangeRequest,
    UploadDeleteRequest,
    UploadRetryRequest,
)
from .validation import run_validations


app = FastAPI(title=settings.app_name, version="3.3.5")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return actionable local diagnostics instead of an opaque 500 body."""
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}",
            "error_type": type(exc).__name__,
            "endpoint": request.url.path,
        },
    )


async def validation_loop() -> None:
    while True:
        await asyncio.sleep(max(settings.validation_interval_minutes, 1) * 60)
        try:
            # Keep scheduled DuckDB writes on the same serial business worker as
            # uploads instead of competing from a FastAPI request thread.
            submit_background_job("scheduled-validation", run_validations)
        except Exception as exc:
            print(f"Scheduled validation failed: {type(exc).__name__}: {exc}")


async def folder_intake_loop() -> None:
    while True:
        await asyncio.sleep(max(2, int(settings.folder_intake_scan_seconds)))
        try:
            await asyncio.to_thread(scan_folder_intake)
        except Exception as exc:
            print(f"Folder intake scan failed: {type(exc).__name__}: {exc}")


@app.on_event("startup")
async def startup() -> None:
    initialise()
    initialise_business_store()
    initialise_decision_context()
    initialise_context_board()
    ensure_folder_intake_layout()
    start_job_worker()
    await asyncio.to_thread(rebuild_accounting_from_sources)
    await asyncio.to_thread(sync_inventory_from_invoices)
    await asyncio.to_thread(sync_employee_profiles)
    await asyncio.to_thread(run_validations)
    try:
        await asyncio.to_thread(refresh_gold_layers, [])
    except Exception as exc:
        print(f"Pipeline startup refresh failed: {type(exc).__name__}: {exc}")
    try:
        await asyncio.to_thread(refresh_superset_views)
    except Exception as exc:
        print(f"Superset view refresh failed: {type(exc).__name__}: {exc}")
    try:
        await asyncio.to_thread(refresh_decision_context, "startup")
    except Exception as exc:
        print(f"Decision context startup refresh failed: {type(exc).__name__}: {exc}")
    try:
        repair_result = await asyncio.to_thread(schedule_classification_repairs)
        if repair_result.get("repair_count"):
            print(f"Scheduled {repair_result['repair_count']} classification repair(s).")
    except Exception as exc:
        print(f"Classification repair scheduling failed: {type(exc).__name__}: {exc}")
    try:
        await asyncio.to_thread(scan_folder_intake)
    except Exception as exc:
        print(f"Initial folder intake scan failed: {type(exc).__name__}: {exc}")
    try:
        await asyncio.to_thread(rebuild_business_context, "application_start")
    except Exception as exc:
        print(f"business.db context refresh failed: {type(exc).__name__}: {exc}")
    app.state.validation_task = asyncio.create_task(validation_loop())
    app.state.folder_intake_task = asyncio.create_task(folder_intake_loop())


@app.on_event("shutdown")
async def shutdown() -> None:
    for task_name in ("validation_task", "folder_intake_task"):
        task = getattr(app.state, task_name, None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    shutdown_job_worker()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "app": settings.app_name, "version": "3.3.5", "job_queue": queue_status(), "agent": "Clippy", "agent_architecture": "single_business_analyst"}


@app.get("/api/diagnostics/jobs")
def background_job_status() -> dict:
    return queue_status()


@app.get("/api/setup/status")
async def setup_status() -> dict:
    provider_status = await model_status()
    ollama_ok, models = await ollama_available() if settings.ollama_enabled else (False, [])
    search_ok = False
    search_detail = "Not configured"
    if settings.web_search_provider == "searxng":
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
                response = await client.get(
                    f"{settings.searxng_url.rstrip('/')}/search",
                    params={"q": "business", "format": "json"},
                )
                response.raise_for_status()
                search_ok = True
                search_detail = "SearXNG is reachable"
        except Exception:
            search_detail = "SearXNG is configured but not reachable"
    elif settings.web_search_provider in {"tavily", "brave"}:
        key = settings.tavily_api_key if settings.web_search_provider == "tavily" else settings.brave_search_api_key
        search_ok = bool(key)
        search_detail = "API key configured" if key else "API key missing"

    memory = memory_context()
    return {
        "backend": {"ok": True, "detail": "FastAPI 3.3.5 single-analyst business workspace is running"},
        "storage": {"ok": True, "detail": "DuckDB, SQLite, Parquet, and local folders are ready", "path": str(settings.data_path)},
        "architecture": {"ok": True, "framework": "single business analyst", "enabled": True, "agent": "Clippy"},
        "superset": {"ok": settings.superset_enabled, "domain": settings.superset_domain},
        "provider": provider_status,
        "ollama": {
            "ok": ollama_ok,
            "detail": "Ollama is reachable" if ollama_ok else "Ollama fallback is disabled or unavailable",
            "base_url": settings.ollama_base_url,
            "models": models,
        },
        "model": {
            "ok": bool(provider_status.get("ok")),
            "detail": str(provider_status.get("detail") or "Model provider unavailable"),
            "configured": str(provider_status.get("model") or ""),
            "provider": settings.model_provider,
        },
        "search": {"ok": search_ok, "detail": search_detail, "provider": settings.web_search_provider},
        "memory": {"ok": True, "detail": f"{memory['message_count']} saved messages; compact summary {'available' if memory['summary'] else 'not yet needed'}"},
        "agent_context": {"ok": True, "detail": f"{agent_context_status()['working_context_events']} working-context events; base personality preserved", **agent_context_status()},
        "compression": {"ok": settings.prompt_compression_enabled, "detail": f"{settings.prompt_compression_provider} prompt budget layer", "provider": settings.prompt_compression_provider},
        "validation": {"ok": True, "detail": f"Automatic checks run every {settings.validation_interval_minutes} minutes and after imports"},
        "cloud": {
            "ok": bool(provider_status.get("ok")),
            "detail": f"Primary provider: {settings.model_provider}",
        },
    }


@app.post("/api/setup/test-ollama")
async def test_ollama(request: OllamaTestRequest) -> dict:
    base_url = (request.base_url or settings.ollama_base_url).rstrip("/")
    model = request.model or settings.ollama_model
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = [item.get("name", "") for item in response.json().get("models", [])]
        present = any(item == model or item.startswith(model + ":") or model.startswith(item + ":") for item in models)
        return {"ok": True, "models": models, "configured_model_present": present}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": [], "configured_model_present": False}


@app.post("/api/setup/test-model")
async def test_model() -> dict:
    return await model_status(verify=True)


@app.post("/api/setup/test-search")
async def test_search(request: SearchTestRequest) -> dict:
    url = (request.url or settings.searxng_url).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(f"{url}/search", params={"q": "Australian business", "format": "json"})
            response.raise_for_status()
            payload = response.json()
        return {"ok": True, "result_count": len(payload.get("results", []))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/dashboard/summary")
def summary_endpoint() -> dict:
    return dashboard_summary()


@app.get("/api/dashboard/workspace")
def workspace_dashboard_endpoint() -> dict:
    """Return one coherent read model for every primary page.

    Keeping the core page reads in one request prevents the UI from mixing
    values from different data versions while an upload or folder-intake job is
    committing its final changes.
    """
    summary = dashboard_summary()
    accounting = accounting_dashboard()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline_status(),
        "summary": summary,
        "transactions": rows_as_dicts("SELECT * FROM transactions ORDER BY transaction_date DESC LIMIT 500"),
        "validations": rows_as_dicts("SELECT * FROM validations ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END"),
        "company_profile": get_company_profile(),
        "accounting": accounting,
        "tax": tax_dashboard(),
        "marketing": marketing_dashboard(),
        "inventory": inventory_dashboard(),
        "hr": hr_dashboard(),
        "money_map": money_map_dashboard(),
        "data_quality": data_quality_dashboard(),
        "upload_library": upload_library(),
        "dashboard_integrity": dashboard_integrity(summary, accounting),
    }


@app.post("/api/dashboard/verify")
def verify_dashboard_endpoint() -> dict:
    """Rebuild derived accounting data, then prove charts and metrics match business.db."""
    rebuild_accounting_from_sources()
    summary = dashboard_summary()
    accounting = accounting_dashboard()
    return dashboard_integrity(summary, accounting)


@app.get("/api/analytics/data-quality")
def data_quality_endpoint() -> dict:
    return data_quality_dashboard()


@app.get("/api/analytics/semantic-layer")
def semantic_layer_endpoint() -> dict:
    return semantic_layer_status()


@app.get("/api/decision-context")
def decision_context_endpoint() -> dict:
    return decision_context_dashboard()


@app.post("/api/decision-context/refresh")
def refresh_decision_context_endpoint() -> dict:
    return refresh_decision_context("manual_api_refresh")


@app.get("/api/context-board")
def context_board_endpoint(refresh: bool = True) -> dict:
    return context_board_dashboard(refresh_sources=refresh)


@app.patch("/api/context-board/nodes/{node_id:path}")
def context_board_node_endpoint(node_id: str, payload: dict) -> dict:
    try:
        return update_context_board_node(node_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/context-board/settings")
def context_board_settings_endpoint(payload: dict) -> dict:
    try:
        return update_context_board_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/context-board/reset-layout")
def context_board_reset_endpoint() -> dict:
    return reset_context_board_layout()


@app.get("/api/context-board/context/{node_id:path}")
def context_board_context_file_endpoint(node_id: str) -> dict:
    try:
        return context_file_content(node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/context-board/context/{node_id:path}")
def context_board_context_save_endpoint(node_id: str, payload: dict) -> dict:
    try:
        return save_context_file(node_id, str(payload.get("content") or ""), confirmed=bool(payload.get("confirmed")))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/context-board/explain")
def context_board_explain_endpoint(payload: dict) -> dict:
    return explain_context_board(str(payload.get("node_id") or ""), str(payload.get("lens") or ""))



@app.get("/api/business-store/status")
def business_store_status_endpoint() -> dict:
    return business_store_status()


@app.post("/api/business-store/refresh")
def business_store_refresh_endpoint() -> dict:
    rebuild_business_context("manual_refresh")
    return business_store_status()


@app.get("/api/superset/status")
async def superset_status_endpoint() -> dict:
    return await superset_status()


@app.post("/api/superset/refresh-views")
def superset_refresh_views_endpoint() -> dict:
    return refresh_superset_views()


@app.post("/api/superset/guest-token/{department_id}")
async def superset_guest_token_endpoint(department_id: str) -> dict:
    try:
        return await guest_token_for_department(department_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"{type(exc).__name__}: {exc}") from exc

@app.get("/api/forecast/cash")
def forecast_endpoint(days: int = 90) -> dict:
    days = max(30, min(days, 365))
    return cash_forecast(days)


@app.get("/api/data/assets-liabilities")
def assets_liabilities() -> dict:
    return {"records": rows_as_dicts("SELECT * FROM assets_liabilities ORDER BY category, classification DESC, amount DESC")}


@app.get("/api/data/invoices")
def invoices() -> dict:
    return {"records": rows_as_dicts("SELECT * FROM invoices ORDER BY invoice_date DESC")}


@app.get("/api/data/transactions")
def transactions() -> dict:
    return {"records": rows_as_dicts("SELECT * FROM transactions ORDER BY transaction_date DESC")}


@app.get("/api/validations")
def validations() -> dict:
    return {"records": rows_as_dicts("SELECT * FROM validations ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END")}


@app.post("/api/validations/refresh")
def refresh_validations() -> dict:
    issues = run_validations()
    return {"ok": True, "issue_count": len(issues), "records": rows_as_dicts("SELECT * FROM validations ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END")}


@app.get("/api/market/signals")
async def market_signals() -> dict:
    return await company_market_signals()


@app.post("/api/research")
async def research(request: ResearchRequest) -> dict:
    return await search_web(request.query, limit=8)


@app.get("/api/company/profile")
def company_profile() -> dict:
    return get_company_profile()


@app.put("/api/company/profile")
def update_company_profile(profile: CompanyProfile) -> dict:
    saved = save_company_profile(profile.model_dump())
    rebuild_accounting_from_sources()
    run_validations()
    refresh_gold_layers(["company_profile"])
    return {"ok": True, "profile": saved}


@app.get("/api/memory")
def memory_status() -> dict:
    return memory_context()


@app.delete("/api/memory")
def memory_clear() -> dict:
    clear_memory()
    return {"ok": True}


@app.get("/api/agent/profile")
def assistant_profile_endpoint() -> dict:
    return read_assistant_profile()


@app.patch("/api/agent/profile")
def assistant_profile_update_endpoint(request: AssistantProfileUpdate) -> dict:
    try:
        return save_assistant_profile(request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/agent/context")
def get_agent_context_status() -> dict:
    return agent_context_status()


@app.delete("/api/agent/context")
def clear_agent_context() -> dict:
    clear_working_context()
    return {"ok": True, **agent_context_status()}


@app.get("/api/approvals")
def approvals() -> dict:
    return {"records": list_approvals()}


@app.post("/api/approvals/{approval_id}/resolve")
def approval_resolve(approval_id: int, request: ApprovalResolution) -> dict:
    changed = resolve_approval(approval_id, request.decision, request.note)
    if not changed:
        raise HTTPException(status_code=404, detail="Pending approval not found.")
    return {"ok": True, "records": list_approvals()}


@app.get("/api/folder-intake/status")
def get_folder_intake_status() -> dict:
    return folder_intake_status()


@app.post("/api/folder-intake/scan")
def scan_folder_intake_endpoint() -> dict:
    return scan_folder_intake()


@app.get("/api/uploads/classification-repair")
def get_classification_repair_status() -> dict:
    return {"plan": classification_repair_plan()}


@app.post("/api/uploads/classification-repair")
def run_classification_repair() -> dict:
    return schedule_classification_repairs()


@app.get("/api/uploads")
def uploads() -> dict:
    return {"records": list_uploaded_files()}


@app.get("/api/uploads/library")
def uploads_library() -> dict:
    return upload_library()


@app.patch("/api/uploads/{upload_id}/category")
def change_upload_category(upload_id: int, request: UploadCategoryChangeRequest) -> dict:
    if list_active_upload_processing_tasks():
        raise HTTPException(status_code=409, detail="Wait for the active upload to finish before moving evidence.")
    try:
        return move_uploaded_file(upload_id, request.intake_category)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@app.post("/api/uploads/{upload_id}/delete")
def delete_upload(upload_id: int, request: UploadDeleteRequest) -> dict:
    if not request.confirmation.strip().upper().startswith("DELETE"):
        raise HTTPException(status_code=400, detail="Type DELETE in the confirmation field.")
    if list_active_upload_processing_tasks():
        raise HTTPException(status_code=409, detail="Wait for the active upload to finish before deleting evidence.")
    try:
        return delete_uploaded_file(upload_id, request.create_backup)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@app.post("/api/uploads/{upload_id}/retry")
def retry_upload(upload_id: int, request: UploadRetryRequest) -> dict:
    if list_active_upload_processing_tasks():
        raise HTTPException(status_code=409, detail="Wait for the active upload to finish before retrying evidence.")
    try:
        task = start_existing_upload_job(upload_id, request.intake_category, request.declared_document_type)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    pending_path = str(task.pop("pending_path"))
    submit_background_job("corrective-upload", process_upload_job, str(task["job_id"]), pending_path)
    return task


@app.get("/api/upload/jobs/{job_id}")
def upload_job_status(job_id: str) -> dict:
    task = get_upload_processing_task(job_id)
    if not task:
        raise HTTPException(status_code=404, detail="Upload processing job not found.")
    return task


@app.post("/api/upload/start")
async def upload_start(
    file: UploadFile = File(...),
    intake_category: str = Form("recurring"),
    declared_document_type: str = Form("auto"),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    extension = Path(file.filename).suffix.lower()
    if extension not in {".csv", ".xlsx", ".xlsm", ".pdf"}:
        raise HTTPException(status_code=400, detail="This version supports CSV, XLSX, XLSM, and PDF files.")
    if intake_category not in {"setup", "recurring"}:
        raise HTTPException(status_code=400, detail="Upload category must be setup or recurring.")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"The file exceeds the {settings.max_upload_mb} MB limit.")
    task = start_upload_job(file.filename, content, intake_category, declared_document_type)
    pending_path = str(task.pop("pending_path"))
    submit_background_job("upload", process_upload_job, str(task["job_id"]), pending_path)
    return task


@app.post("/api/uploads/{upload_id}/map")
def map_upload(upload_id: int, request: MappingRequest) -> dict:
    try:
        result = apply_manual_mapping(upload_id, request.document_type, request.mapping)
        run_validations()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    intake_category: str = Form("recurring"),
    declared_document_type: str = Form("auto"),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    extension = Path(file.filename).suffix.lower()
    if extension not in {".csv", ".xlsx", ".xlsm", ".pdf"}:
        raise HTTPException(status_code=400, detail="This version supports CSV, XLSX, XLSM, and PDF files.")
    if intake_category not in {"setup", "recurring"}:
        raise HTTPException(status_code=400, detail="Upload category must be setup or recurring.")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"The file exceeds the {settings.max_upload_mb} MB limit.")
    try:
        result = store_source_document(file.filename, content, intake_category, declared_document_type) if extension == ".pdf" else process_upload(file.filename, content, intake_category, declared_document_type)
        run_validations()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc


@app.get("/api/document-templates")
def document_templates() -> dict:
    return {"records": DOCUMENT_TEMPLATES}


@app.post("/api/documents/generate")
def create_business_document(request: GenerateDocumentRequest) -> Response:
    try:
        content, filename, media_type = generate_document(request.document_type, request.output_format, request.fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    export_path = settings.data_path / "exports" / filename
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_bytes(content)
    document_id = f"doc_{uuid.uuid4().hex[:16]}"
    template = next((item for item in DOCUMENT_TEMPLATES if item["id"] == request.document_type), {})
    save_generated_document(
        document_id, request.document_type, str(template.get("name") or request.document_type.replace("_", " ").title()),
        request.output_format, filename, str(export_path), "draft", str(request.fields.get("counterparty") or ""),
        {"fields": request.fields, "review_required": True},
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-LedgerFlow-Document-ID": document_id},
    )


@app.get("/api/documents")
def generated_document_library() -> dict:
    return {"records": list_generated_documents()}


@app.get("/api/documents/{document_id}/download")
def download_generated_document(document_id: str) -> FileResponse:
    record = get_generated_document(document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generated document not found.")
    path = Path(str(record.get("file_path") or ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="The generated file is missing from the exports folder.")
    return FileResponse(path, filename=str(record.get("filename") or path.name))


@app.get("/api/accounts/dashboard")
def accounts_dashboard_endpoint() -> dict:
    return accounting_dashboard()


@app.post("/api/accounts/invoices/{invoice_id}/categorisation")
def resolve_invoice_category(invoice_id: str, request: InvoiceCategorisationResolution) -> dict:
    try:
        return resolve_invoice_categorisation(invoice_id, request.account_code, request.tax_code, request.remember, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/accounts/categorisation-rules")
def create_categorisation_rule(request: CategorisationRuleRequest) -> dict:
    try:
        return add_categorisation_rule(request.keyword, request.account_code, request.tax_code, request.match_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/marketing/dashboard")
def marketing_dashboard_endpoint() -> dict:
    return marketing_dashboard()


@app.get("/api/inventory/dashboard")
def inventory_dashboard_endpoint() -> dict:
    return inventory_dashboard()


@app.post("/api/inventory/sync")
def inventory_sync_endpoint() -> dict:
    sync_inventory_from_invoices()
    return inventory_dashboard()


@app.get("/api/hr/dashboard")
def hr_dashboard_endpoint() -> dict:
    return hr_dashboard()


@app.get("/api/money-map/dashboard")
def money_map_dashboard_endpoint() -> dict:
    return money_map_dashboard()


@app.get("/api/tax/dashboard")
def tax_dashboard_endpoint() -> dict:
    return tax_dashboard()


@app.post("/api/tax/opportunities/analyse")
async def tax_opportunities_endpoint() -> dict:
    return await analyse_tax_opportunities()


@app.get("/api/tax/workpaper")
def tax_workpaper_endpoint(output_format: str = "pdf") -> Response:
    try:
        content, filename, media_type = generate_tax_workpaper(output_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    export_path = settings.data_path / "exports" / filename
    export_path.write_bytes(content)
    document_id = f"doc_{uuid.uuid4().hex[:16]}"
    save_generated_document(document_id, "ato_ready_tax_workpaper", "ATO-ready tax workpaper", output_format, filename, str(export_path), "draft", "", {"official_form": False, "review_required": True})
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-LedgerFlow-Document-ID": document_id})


@app.get("/api/integrations/settings")
def integration_settings_endpoint() -> dict:
    return get_integration_settings()


@app.put("/api/integrations/settings")
def update_integration_settings_endpoint(request: IntegrationSettingsRequest) -> dict:
    values = request.model_dump()
    if values["mode"] == "offline":
        values.update({"official_tax_sources": False, "supplier_enrichment": False, "bank_feeds": False, "email_intake": False, "cloud_storage": False})
    if values.get("supplier_enrichment") and not values.get("external_processing_consent"):
        raise HTTPException(status_code=400, detail="Supplier enrichment requires explicit external-processing consent.")
    return save_integration_settings(values)


@app.get("/api/pipeline/status")
def pipeline_status_endpoint() -> dict:
    return pipeline_status()


@app.post("/api/pipeline/rebuild")
def rebuild_pipeline(request: RebuildPipelineRequest) -> dict:
    try:
        if request.force_full_baseline:
            return full_pipeline_rebuild()
        return refresh_gold_layers([])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline rebuild failed: {exc}") from exc


@app.get("/api/context/market")
def market_context_endpoint() -> dict:
    return {
        "profile": build_market_profile(),
        "snapshot": refresh_market_snapshot(),
    }


@app.get("/api/context/information-requests")
def information_requests_endpoint() -> dict:
    return {"records": build_information_requests()}


@app.get("/api/intelligence/competitors")
def competitor_intelligence_status_endpoint() -> dict:
    return analysis_status()


@app.post("/api/intelligence/competitors/start")
def competitor_intelligence_start_endpoint() -> dict:
    job = start_analysis_job()
    start_background = bool(job.pop("start_background", False))
    if start_background:
        submit_background_job("competitor-intelligence", process_analysis_job, str(job["job_id"]))
    return job


@app.post("/api/data/clear")
async def clear_data(request: ClearDataRequest) -> dict:
    if list_active_upload_processing_tasks():
        raise HTTPException(status_code=409, detail="Wait for the active upload to finish before resetting LedgerFlow.")
    if not request.confirmation.strip().upper().startswith("CLEAR"):
        raise HTTPException(status_code=400, detail="Type CLEAR in the confirmation field.")
    try:
        result = await asyncio.to_thread(clear_company_data, request.scope, request.create_backup)
        await asyncio.to_thread(rebuild_accounting_from_sources)
        await asyncio.to_thread(run_validations)
        await asyncio.to_thread(refresh_gold_layers, [])
        await asyncio.to_thread(refresh_decision_context, "data_reset")
        await asyncio.to_thread(rebuild_business_context, "data_reset")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clear operation failed: {exc}") from exc


@app.get("/api/export/business-report.xlsx")
def export_business_report() -> StreamingResponse:
    workbook = Workbook()
    default = workbook.active
    default.title = "Summary"
    summary = dashboard_summary()
    default.append(["Metric", "Value"])
    for key in ["cash", "current_assets", "current_liabilities", "current_ratio", "quick_ratio", "working_capital", "cash_runway_days", "revenue_month", "expenses_month"]:
        default.append([key, summary.get(key)])
    for title, query in [
        ("Assets & Liabilities", "SELECT * FROM assets_liabilities ORDER BY category, amount DESC"),
        ("Invoices", "SELECT * FROM invoices ORDER BY invoice_date DESC"),
        ("Transactions", "SELECT * FROM transactions ORDER BY transaction_date DESC"),
        ("Validations", "SELECT * FROM validations ORDER BY severity"),
    ]:
        sheet = workbook.create_sheet(title)
        rows = rows_as_dicts(query)
        if rows:
            sheet.append(list(rows[0].keys()))
            for row in rows:
                sheet.append([row[key] for key in rows[0].keys()])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ledgerflow_business_report.xlsx"},
    )


@app.post("/api/agent/command", response_model=AgentResponse)
async def agent_command(command: AgentCommand) -> AgentResponse:
    try:
        return await handle_command(command)
    except Exception as exc:
        print(f"Agent command failed safely: {type(exc).__name__}: {exc}")
        return AgentResponse(
            mode="answer",
            summary=(
                "The backend and file database are connected, but this request hit an internal analysis error. "
                f"The deterministic file pipeline remains available. Technical detail: {type(exc).__name__}: {exc}"
            ),
            actions=[],
            used_model="deterministic recovery layer",
            evidence={"error_type": type(exc).__name__},
            plan=["Keep uploaded evidence unchanged", "Return a recoverable error instead of disconnecting the assistant"],
            citations=[],
        )


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-store, no-cache, must-revalidate"})

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str):
        candidate = DIST / path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
else:
    @app.get("/", include_in_schema=False)
    def no_frontend() -> dict:
        return {"message": "Frontend build not found. Run npm install and npm run build inside the frontend folder.", "api_docs": "/docs"}
