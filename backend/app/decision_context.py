from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .database import COMPANY_ID, get_sqlite
from .timezone_utils import resolve_timezone

DECISION_CONTEXT_FILENAME = "temporal_decision_context.json"
_CONTEXT_LOCK = threading.RLock()

DECISION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "liquidity_cash": {
        "label": "Liquidity and cash",
        "description": "Cash runway, working capital and short-term payment capacity.",
        "required": {"balance_sheet", "cash_flow_statement"},
        "supporting": {"bank_statements", "aged_debtors_creditors", "sales_invoices", "supplier_invoices"},
    },
    "profit_margin": {
        "label": "Profit and margin",
        "description": "Revenue, gross margin, operating cost and pricing decisions.",
        "required": {"profit_loss"},
        "supporting": {"sales_invoices", "supplier_invoices", "sales_forecast"},
    },
    "tax_compliance": {
        "label": "Tax and compliance",
        "description": "GST, BAS, payroll and tax evidence readiness.",
        "required": {"chart_of_accounts"},
        "supporting": {"supplier_invoices", "sales_invoices", "payroll", "bank_statements", "historical_tax_returns"},
    },
    "growth_marketing": {
        "label": "Growth and marketing",
        "description": "Marketing efficiency, demand signals and commercial growth.",
        "required": {"sales_invoices"},
        "supporting": {"supplier_invoices", "sales_forecast", "market_context", "business_requirements"},
    },
    "competitor_market": {
        "label": "Competitor and market",
        "description": "Peer positioning, market risks and strategic response.",
        "required": {"market_context"},
        "supporting": {"balance_sheet", "profit_loss", "sales_forecast", "business_requirements", "material_contracts"},
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timezone():
    zone, _, _ = resolve_timezone(settings.app_timezone)
    return zone


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def decision_context_db_path() -> Path:
    path = settings.data_path / "database" / "decision_context.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def temporal_context_path() -> Path:
    path = settings.data_path / "context" / COMPANY_ID / DECISION_CONTEXT_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(decision_context_db_path(), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def initialise_decision_context() -> None:
    con = _connect()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS temporal_sources (
            source_key TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            upload_id INTEGER,
            filename TEXT NOT NULL,
            document_type TEXT NOT NULL,
            intake_category TEXT NOT NULL,
            uploaded_at_utc TEXT NOT NULL,
            processed_at_utc TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            data_version INTEGER NOT NULL DEFAULT 0,
            freshness_state TEXT NOT NULL,
            freshness_hours REAL NOT NULL DEFAULT 0,
            decision_role TEXT NOT NULL,
            processing_status TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            refreshed_at_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_temporal_sources_type ON temporal_sources(document_type);
        CREATE INDEX IF NOT EXISTS idx_temporal_sources_processed ON temporal_sources(processed_at_utc);

        CREATE TABLE IF NOT EXISTS decision_nodes (
            decision_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            description TEXT NOT NULL,
            readiness TEXT NOT NULL,
            source_count INTEGER NOT NULL DEFAULT 0,
            fresh_source_count INTEGER NOT NULL DEFAULT 0,
            stale_source_count INTEGER NOT NULL DEFAULT 0,
            last_evaluated_at_utc TEXT NOT NULL,
            summary TEXT NOT NULL,
            decision_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS decision_links (
            decision_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            connection_role TEXT NOT NULL,
            reason TEXT NOT NULL,
            connected_at_utc TEXT NOT NULL,
            PRIMARY KEY (decision_id, source_key),
            FOREIGN KEY (decision_id) REFERENCES decision_nodes(decision_id),
            FOREIGN KEY (source_key) REFERENCES temporal_sources(source_key)
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_key TEXT NOT NULL UNIQUE,
            analysis_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at_utc TEXT NOT NULL,
            completed_at_utc TEXT NOT NULL DEFAULT '',
            data_cutoff_utc TEXT NOT NULL DEFAULT '',
            source_count INTEGER NOT NULL DEFAULT 0,
            stale_source_count INTEGER NOT NULL DEFAULT 0,
            summary TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS context_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source_key TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    con.commit()
    con.close()


def _parse_datetime(raw: Any) -> datetime:
    text = str(raw or "").strip()
    if not text:
        return _utc_now()
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except Exception:
        return _utc_now()


def _infer_effective_date(filename: str, metadata: dict[str, Any], processed_at: datetime) -> str:
    candidates = [
        metadata.get("period_end"), metadata.get("statement_date"), metadata.get("invoice_date"),
        metadata.get("pay_period"), metadata.get("observed_at"), metadata.get("published_at"),
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return text[:10]
    name = filename.replace("_", " ").replace("-", " ")
    match = re.search(r"(20\d{2})[ _.-]?(0[1-9]|1[0-2])[ _.-]?([0-3]\d)", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    month_names = "January February March April May June July August September October November December".split()
    for index, month in enumerate(month_names, start=1):
        match = re.search(rf"\b{month}\s+(20\d{{2}})\b", name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}-{index:02d}-01"
    fy = re.search(r"FY\s?(20\d{2})", name, re.IGNORECASE)
    if fy:
        return f"{fy.group(1)}-06-30"
    return processed_at.date().isoformat()


def _role_for(document_type: str) -> str:
    mapping = {
        "balance_sheet": "financial position",
        "profit_loss": "performance",
        "cash_flow_statement": "cash movement",
        "chart_of_accounts": "accounting control",
        "business_requirements": "business objectives",
        "fixed_asset_register": "asset planning",
        "aged_debtors_creditors": "working capital",
        "material_contracts": "commitments and risk",
        "sales_forecast": "forward outlook",
        "personnel_plan": "workforce planning",
        "use_cases_user_stories": "decision requirements",
        "historical_tax_returns": "tax history",
        "market_context": "market and competitor evidence",
        "supplier_invoices": "cost and payable evidence",
        "sales_invoices": "revenue and receivable evidence",
        "bank_statements": "cash verification",
        "payroll": "payroll and compliance evidence",
    }
    return mapping.get(document_type, "supporting evidence")


def _freshness(document_type: str, intake_category: str, processed_at: datetime, now: datetime) -> tuple[str, float]:
    hours = max(0.0, (now - processed_at).total_seconds() / 3600)
    days = hours / 24
    if document_type == "market_context":
        return ("fresh" if days <= 31 else "watch" if days <= 62 else "stale", round(hours, 1))
    if intake_category == "recurring":
        return ("fresh" if days <= 45 else "watch" if days <= 90 else "stale", round(hours, 1))
    return ("reference", round(hours, 1))


def _safe_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _load_upload_sources() -> list[dict[str, Any]]:
    sql = get_sqlite()
    columns = {str(row[1]) for row in sql.execute("PRAGMA table_info(uploaded_files)").fetchall()}
    wanted = [
        "id", "filename", "original_filename", "document_type", "intake_category", "created_at",
        "last_processed_at", "data_version", "processing_status", "metadata_json", "analysis_json",
    ]
    selected = [name for name in wanted if name in columns]
    rows = sql.execute(f"SELECT {', '.join(selected)} FROM uploaded_files ORDER BY id ASC").fetchall()
    sql.close()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        metadata = _safe_json(item.get("metadata_json"))
        analysis = _safe_json(item.get("analysis_json"))
        filename = str(item.get("original_filename") or item.get("filename") or f"upload-{item.get('id')}")
        processed = _parse_datetime(item.get("last_processed_at") or item.get("created_at"))
        uploaded = _parse_datetime(item.get("created_at"))
        document_type = str(item.get("document_type") or "generic")
        intake_category = str(item.get("intake_category") or "recurring")
        effective = _infer_effective_date(filename, {**metadata, **analysis}, processed)
        result.append({
            "source_key": f"upload:{int(item.get('id') or 0)}",
            "upload_id": int(item.get("id") or 0),
            "filename": filename,
            "document_type": document_type,
            "intake_category": intake_category,
            "uploaded_at": uploaded,
            "processed_at": processed,
            "effective_date": effective,
            "data_version": int(item.get("data_version") or 0),
            "processing_status": str(item.get("processing_status") or "unknown"),
            "role": _role_for(document_type),
            "metadata": {"analysis": analysis, "metadata": metadata},
        })
    return result


def _latest_analysis() -> dict[str, Any]:
    sql = get_sqlite()
    try:
        row = sql.execute(
            "SELECT job_id, status, created_at, updated_at, completed_at, stage, progress, stage_message, result_json "
            "FROM competitor_analysis_jobs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except Exception:
        row = None
    sql.close()
    if not row:
        return {}
    item = dict(row)
    result = _safe_json(item.get("result_json"))
    return {
        "run_key": str(item.get("job_id") or ""),
        "analysis_type": "competitor_and_market",
        "status": str(item.get("status") or "unknown"),
        "started_at_utc": str(item.get("created_at") or ""),
        "completed_at_utc": str(item.get("completed_at") or ""),
        "updated_at_utc": str(item.get("updated_at") or ""),
        "summary": str(result.get("summary") or item.get("stage_message") or ""),
        "progress": int(item.get("progress") or 0),
    }


def _build_decisions(sources: list[dict[str, Any]], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    source_types = {source["document_type"] for source in sources if source["processing_status"] in {"committed", "stored_source", "pending_mapping"}}
    for decision_id, definition in DECISION_DEFINITIONS.items():
        required = set(definition["required"])
        supporting = set(definition["supporting"])
        connected = [source for source in sources if source["document_type"] in required | supporting]
        required_present = required & source_types
        if required and required_present == required:
            readiness = "ready"
        elif required_present or connected:
            readiness = "provisional"
        else:
            readiness = "blocked"
        stale = [source for source in connected if source["freshness_state"] == "stale"]
        fresh = [source for source in connected if source["freshness_state"] in {"fresh", "reference"}]
        if readiness == "ready" and stale:
            readiness = "review_freshness"
        summary = (
            f"{len(connected)} connected input(s); {len(fresh)} current/reference and {len(stale)} stale. "
            f"Required evidence: {len(required_present)}/{len(required)}."
        )
        decisions.append({
            "decision_id": decision_id,
            "label": definition["label"],
            "description": definition["description"],
            "readiness": readiness,
            "source_count": len(connected),
            "fresh_source_count": len(fresh),
            "stale_source_count": len(stale),
            "last_evaluated_at_utc": _iso(now),
            "summary": summary,
            "required_types": sorted(required),
            "missing_required": sorted(required - source_types),
        })
        for source in connected:
            role = "required" if source["document_type"] in required else "supporting"
            links.append({
                "decision_id": decision_id,
                "source_key": source["source_key"],
                "connection_role": role,
                "reason": f"{source['role']} contributes to {definition['label'].lower()} decisions.",
            })
    return decisions, links


def refresh_decision_context(reason: str = "manual_refresh") -> dict[str, Any]:
    with _CONTEXT_LOCK:
        return _refresh_decision_context_locked(reason)


def _refresh_decision_context_locked(reason: str) -> dict[str, Any]:
    initialise_decision_context()
    now = _utc_now()
    tz = _timezone()
    sources = _load_upload_sources()
    for source in sources:
        state, hours = _freshness(source["document_type"], source["intake_category"], source["processed_at"], now)
        source["freshness_state"] = state
        source["freshness_hours"] = hours
    decisions, links = _build_decisions(sources, now)
    last_analysis = _latest_analysis()
    con = _connect()
    con.execute("DELETE FROM decision_links")
    con.execute("DELETE FROM decision_nodes")
    con.execute("DELETE FROM temporal_sources")
    for source in sources:
        con.execute(
            "INSERT INTO temporal_sources(source_key, company_id, upload_id, filename, document_type, intake_category, uploaded_at_utc, processed_at_utc, effective_date, data_version, freshness_state, freshness_hours, decision_role, processing_status, metadata_json, refreshed_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source["source_key"], COMPANY_ID, source["upload_id"], source["filename"], source["document_type"],
                source["intake_category"], _iso(source["uploaded_at"]), _iso(source["processed_at"]), source["effective_date"],
                source["data_version"], source["freshness_state"], source["freshness_hours"], source["role"],
                source["processing_status"], json.dumps(source["metadata"], default=str), _iso(now),
            ),
        )
    for decision in decisions:
        con.execute(
            "INSERT INTO decision_nodes(decision_id, label, description, readiness, source_count, fresh_source_count, stale_source_count, last_evaluated_at_utc, summary, decision_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision["decision_id"], decision["label"], decision["description"], decision["readiness"],
                decision["source_count"], decision["fresh_source_count"], decision["stale_source_count"],
                decision["last_evaluated_at_utc"], decision["summary"], json.dumps(decision, default=str),
            ),
        )
    for link in links:
        con.execute(
            "INSERT INTO decision_links(decision_id, source_key, connection_role, reason, connected_at_utc) VALUES (?, ?, ?, ?, ?)",
            (link["decision_id"], link["source_key"], link["connection_role"], link["reason"], _iso(now)),
        )
    con.execute(
        "INSERT INTO context_events(occurred_at_utc, event_type, detail, payload_json) VALUES (?, ?, ?, ?)",
        (_iso(now), "context_refresh", reason, json.dumps({"source_count": len(sources), "decision_count": len(decisions)})),
    )
    if last_analysis.get("run_key"):
        con.execute(
            "INSERT INTO analysis_runs(run_key, analysis_type, status, started_at_utc, completed_at_utc, data_cutoff_utc, source_count, stale_source_count, summary, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_key) DO UPDATE SET status=excluded.status, completed_at_utc=excluded.completed_at_utc, data_cutoff_utc=excluded.data_cutoff_utc, source_count=excluded.source_count, stale_source_count=excluded.stale_source_count, summary=excluded.summary, result_json=excluded.result_json",
            (
                last_analysis["run_key"], last_analysis["analysis_type"], last_analysis["status"],
                last_analysis.get("started_at_utc") or _iso(now), last_analysis.get("completed_at_utc") or "",
                max((_iso(source["processed_at"]) for source in sources), default=""), len(sources),
                sum(1 for source in sources if source["freshness_state"] == "stale"), last_analysis.get("summary") or "",
                json.dumps(last_analysis, default=str),
            ),
        )
    con.commit()
    con.close()
    return decision_context_dashboard(refresh=False)


def decision_context_dashboard(*, refresh: bool = True) -> dict[str, Any]:
    initialise_decision_context()
    if refresh:
        return refresh_decision_context("dashboard_read")
    now = _utc_now()
    tz, timezone_label, timezone_warning = resolve_timezone(settings.app_timezone)
    con = _connect()
    sources = [dict(row) for row in con.execute("SELECT * FROM temporal_sources ORDER BY processed_at_utc DESC, upload_id DESC").fetchall()]
    decisions = [dict(row) for row in con.execute("SELECT * FROM decision_nodes ORDER BY decision_id").fetchall()]
    links = [dict(row) for row in con.execute("SELECT * FROM decision_links ORDER BY decision_id, source_key").fetchall()]
    analyses = [dict(row) for row in con.execute("SELECT * FROM analysis_runs ORDER BY started_at_utc DESC LIMIT 12").fetchall()]
    events = [dict(row) for row in con.execute("SELECT * FROM context_events ORDER BY id DESC LIMIT 20").fetchall()]
    con.close()
    for source in sources:
        source["metadata"] = _safe_json(source.pop("metadata_json", "{}"))
        source["uploaded_at_local"] = _iso(_parse_datetime(source["uploaded_at_utc"]).astimezone(tz))
        source["processed_at_local"] = _iso(_parse_datetime(source["processed_at_utc"]).astimezone(tz))
    for decision in decisions:
        decision["decision"] = _safe_json(decision.pop("decision_json", "{}"))
    for analysis in analyses:
        analysis["result"] = _safe_json(analysis.pop("result_json", "{}"))
    data_cutoff = max((source["processed_at_utc"] for source in sources), default="")
    freshness_counts: dict[str, int] = {"fresh": 0, "watch": 0, "stale": 0, "reference": 0}
    for source in sources:
        freshness_counts[source["freshness_state"]] = freshness_counts.get(source["freshness_state"], 0) + 1
    latest_analysis = analyses[0] if analyses else {}
    payload = {
        "version": 1,
        "timezone": timezone_label,
        "timezone_warning": timezone_warning,
        "current_time_utc": _iso(now),
        "current_time_local": _iso(now.astimezone(tz)),
        "data_cutoff_utc": data_cutoff,
        "data_cutoff_local": _iso(_parse_datetime(data_cutoff).astimezone(tz)) if data_cutoff else "",
        "last_analysis": latest_analysis,
        "summary": {
            "source_count": len(sources),
            "decision_count": len(decisions),
            "ready_decisions": sum(1 for item in decisions if item["readiness"] == "ready"),
            "provisional_decisions": sum(1 for item in decisions if item["readiness"] in {"provisional", "review_freshness"}),
            "blocked_decisions": sum(1 for item in decisions if item["readiness"] == "blocked"),
            "freshness": freshness_counts,
        },
        "sources": sources,
        "decisions": decisions,
        "links": links,
        "analysis_history": analyses,
        "events": events,
        "database_file": str(decision_context_db_path()),
        "context_file": str(temporal_context_path()),
        "decision_engine_note": "The AI receives this timestamped context before strategic reasoning. Source links show which uploaded evidence is allowed to influence each decision domain.",
    }
    temporal_context_path().write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def read_temporal_context_file() -> dict[str, Any]:
    path = temporal_context_path()
    if not path.exists():
        try:
            return refresh_decision_context("context_file_created")
        except Exception:
            return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def record_analysis_event(run_key: str, status: str, summary: str = "", result: dict[str, Any] | None = None) -> None:
    with _CONTEXT_LOCK:
        _record_analysis_event_locked(run_key, status, summary, result)


def _record_analysis_event_locked(run_key: str, status: str, summary: str = "", result: dict[str, Any] | None = None) -> None:
    initialise_decision_context()
    now = _utc_now()
    con = _connect()
    existing = con.execute("SELECT started_at_utc FROM analysis_runs WHERE run_key=?", (run_key,)).fetchone()
    started = str(existing[0]) if existing else _iso(now)
    completed = _iso(now) if status in {"completed", "failed"} else ""
    source_count = int(con.execute("SELECT COUNT(*) FROM temporal_sources").fetchone()[0])
    stale_count = int(con.execute("SELECT COUNT(*) FROM temporal_sources WHERE freshness_state='stale'").fetchone()[0])
    cutoff = str(con.execute("SELECT COALESCE(MAX(processed_at_utc),'') FROM temporal_sources").fetchone()[0])
    con.execute(
        "INSERT INTO analysis_runs(run_key, analysis_type, status, started_at_utc, completed_at_utc, data_cutoff_utc, source_count, stale_source_count, summary, result_json) VALUES (?, 'competitor_and_market', ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(run_key) DO UPDATE SET status=excluded.status, completed_at_utc=excluded.completed_at_utc, data_cutoff_utc=excluded.data_cutoff_utc, source_count=excluded.source_count, stale_source_count=excluded.stale_source_count, summary=excluded.summary, result_json=excluded.result_json",
        (run_key, status, started, completed, cutoff, source_count, stale_count, summary, json.dumps(result or {}, default=str)),
    )
    con.execute(
        "INSERT INTO context_events(occurred_at_utc, event_type, source_key, detail, payload_json) VALUES (?, ?, ?, ?, ?)",
        (_iso(now), f"analysis_{status}", run_key, summary, json.dumps(result or {}, default=str)),
    )
    con.commit()
    con.close()
    decision_context_dashboard(refresh=False)
