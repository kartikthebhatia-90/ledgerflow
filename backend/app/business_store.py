from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .database import COMPANY_ID, get_duckdb, get_company_profile, list_uploaded_files, pipeline_status


CLIPPY_PROFILE = {
    "name": "Clippy",
    "role": "Senior business analyst",
    "purpose": "Turn verified company evidence into clear findings, decisions and practical next actions.",
    "personality": {
        "tone": "calm, commercially aware, concise and approachable",
        "traits": ["evidence-led", "curious", "practical", "transparent", "risk-aware"],
        "behaviour": [
            "Lead with the business implication.",
            "Distinguish facts, calculations, assumptions and recommendations.",
            "Trace material statements to a source file, record or calculation.",
            "Never invent missing figures; mark them provisional or request evidence.",
            "Use deterministic calculations before model reasoning.",
            "Explain finance, tax and operations in plain Australian business language.",
            "Prioritise actions by impact, urgency, confidence and effort.",
        ],
    },
}

CORE_SETUP_TYPES = {
    "balance_sheet",
    "profit_loss",
    "cash_flow_statement",
    "chart_of_accounts",
    "business_requirements",
}

BUSINESS_TABLES = [
    "assets_liabilities", "invoices", "transactions", "payments", "bank_transactions",
    "customers", "suppliers", "inventory", "inventory_movements", "inventory_reorder_settings",
    "budgets", "payroll_records", "employee_profiles", "employee_leave_balances",
    "employee_training", "market_signals",
    "statement_snapshots", "generic_documents", "validations", "chart_of_accounts",
    "categorisation_rules", "journal_entries", "journal_lines", "account_validation_tasks",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialise_business_store() -> None:
    con = get_duckdb()
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_system (
                key VARCHAR PRIMARY KEY, value_json VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS clippy_profile (
                id INTEGER PRIMARY KEY, profile_json VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_lifecycle (
                id INTEGER PRIMARY KEY, phase VARCHAR, setup_complete BOOLEAN,
                setup_completed_at TIMESTAMP, data_version INTEGER,
                last_run_id VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_source_registry (
                upload_id INTEGER PRIMARY KEY, file_id VARCHAR, filename VARCHAR,
                document_type VARCHAR, intake_category VARCHAR, processing_status VARCHAR,
                source_sha256 VARCHAR, rows_received INTEGER, rows_new INTEGER,
                rows_changed INTEGER, rows_rejected INTEGER, data_version INTEGER,
                raw_path VARCHAR, bronze_path VARCHAR, silver_paths_json VARCHAR,
                uploaded_at TIMESTAMP, processed_at TIMESTAMP, metadata_json VARCHAR,
                analysis_json VARCHAR
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_lineage (
                event_id VARCHAR PRIMARY KEY, run_id VARCHAR, upload_id INTEGER,
                stage_order INTEGER, stage VARCHAR, operation VARCHAR,
                source_name VARCHAR, destination_name VARCHAR, record_count INTEGER,
                status VARCHAR, detail_json VARCHAR, created_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_catalog (
                table_name VARCHAR PRIMARY KEY, business_domain VARCHAR,
                row_count INTEGER, columns_json VARCHAR, source_files_json VARCHAR,
                description VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_context_detail (
                section_key VARCHAR PRIMARY KEY, section_label VARCHAR,
                content_json VARCHAR, source_upload_ids_json VARCHAR,
                data_version INTEGER, content_hash VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS business_context_summary (
                summary_key VARCHAR PRIMARY KEY, summary_text VARCHAR,
                summary_json VARCHAR, detail_sections_json VARCHAR,
                data_version INTEGER, approximate_tokens INTEGER, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS clippy_process_memory (
                process_id VARCHAR PRIMARY KEY, process_type VARCHAR, trigger_name VARCHAR,
                status VARCHAR, steps_json VARCHAR, affected_sections_json VARCHAR,
                result_summary VARCHAR, data_version INTEGER, started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        con.execute("""
            INSERT OR REPLACE INTO clippy_profile VALUES (1, ?, ?)
        """, [json.dumps(CLIPPY_PROFILE, ensure_ascii=False), _now()])
        con.execute("""
            INSERT OR IGNORE INTO business_lifecycle
            VALUES (1, 'initial_setup', FALSE, NULL, 0, '', ?)
        """, [_now()])
        con.execute("""
            INSERT OR REPLACE INTO business_system VALUES
            ('canonical_database', ?, ?),
            ('architecture', ?, ?)
        """, [
            json.dumps({"file": "data/database/business.db", "engine": "DuckDB", "role": "canonical business and Clippy context store"}),
            _now(),
            json.dumps({"agent": "Clippy", "agent_model": "single_business_analyst", "procedures": ["initial_setup", "recurring_intake"]}),
            _now(),
        ])
    finally:
        con.close()


def _json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def _table_description(table: str) -> tuple[str, str]:
    mapping = {
        "assets_liabilities": ("finance", "Financial position records"),
        "statement_snapshots": ("finance", "Balance sheet, profit and loss, and cash-flow statement lines"),
        "invoices": ("accounts", "Supplier and customer invoices"),
        "transactions": ("accounts", "Imported financial transactions"),
        "bank_transactions": ("accounts", "Bank statement activity"),
        "payments": ("accounts", "Payments matched to invoices"),
        "chart_of_accounts": ("accounts", "Canonical account classification structure"),
        "journal_entries": ("accounts", "Accounting journal headers"),
        "journal_lines": ("accounts", "Debit and credit journal lines"),
        "payroll_records": ("people", "Payroll, PAYG and superannuation evidence"),
        "budgets": ("planning", "Budget and actual records"),
        "market_signals": ("market", "Uploaded market and competitor evidence"),
        "validations": ("quality", "Business data quality checks"),
        "account_validation_tasks": ("quality", "Accounting classifications requiring review"),
    }
    return mapping.get(table, ("business", table.replace("_", " ").title()))


def refresh_business_catalog() -> list[dict[str, Any]]:
    con = get_duckdb()
    catalog: list[dict[str, Any]] = []
    try:
        available = {str(row[0]) for row in con.execute("SHOW TABLES").fetchall()}
        for table in BUSINESS_TABLES:
            if table not in available:
                continue
            row_count = int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            columns = [
                {"name": str(row[1]), "type": str(row[2])}
                for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()
            ]
            source_files: list[str] = []
            if any(column["name"] == "source_file" for column in columns):
                source_files = [
                    str(row[0]) for row in
                    con.execute(f'SELECT DISTINCT source_file FROM "{table}" WHERE source_file IS NOT NULL ORDER BY source_file').fetchall()
                ]
            domain, description = _table_description(table)
            record = {
                "table_name": table, "business_domain": domain, "row_count": row_count,
                "columns": columns, "source_files": source_files, "description": description,
            }
            catalog.append(record)
            con.execute("""
                INSERT OR REPLACE INTO business_catalog
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [table, domain, row_count, _json(columns), _json(source_files), description, _now()])
    finally:
        con.close()
    return catalog


def sync_source_registry() -> list[dict[str, Any]]:
    uploads = list_uploaded_files()
    con = get_duckdb()
    try:
        # The registry is a current-state mirror of SQLite upload metadata.
        # Rebuild it atomically so repeated context refreshes cannot duplicate
        # the same source when older databases lack a primary-key constraint.
        con.execute("DELETE FROM business_source_registry")
        for item in uploads:
            con.execute("""
                INSERT OR REPLACE INTO business_source_registry VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                int(item.get("id") or 0), str(item.get("file_id") or ""), str(item.get("filename") or ""),
                str(item.get("document_type") or ""), str(item.get("intake_category") or ""),
                str(item.get("processing_status") or ""), str(item.get("sha256") or ""),
                int(item.get("row_count") or item.get("rows_imported") or 0), int(item.get("rows_new") or 0),
                int(item.get("rows_changed") or 0), int(item.get("rows_rejected") or 0),
                int(item.get("data_version") or 0), str(item.get("raw_path") or ""),
                str(item.get("bronze_path") or ""), _json(item.get("silver_paths") or []),
                item.get("created_at") or _now(), item.get("last_processed_at") or item.get("created_at") or _now(),
                _json(item.get("metadata") or {}), _json(item.get("analysis") or {}),
            ])
    finally:
        con.close()
    return uploads


def ensure_source_lineage(uploads: list[dict[str, Any]]) -> int:
    """Backfill trace steps for packaged or migrated sources.

    Normal browser intake records these steps at commit time. Prepared demo
    databases and older installs may already contain the source registry but
    predate the lineage table, so create the same trace once per source.
    """
    con = get_duckdb()
    inserted = 0
    try:
        for item in uploads:
            upload_id = int(item.get("id") or 0)
            if not upload_id:
                continue
            existing = int(con.execute(
                "SELECT COUNT(*) FROM business_lineage WHERE upload_id=?",
                [upload_id],
            ).fetchone()[0])
            if existing:
                continue
            filename = str(item.get("filename") or f"upload-{upload_id}")
            rows = int(item.get("row_count") or item.get("rows_imported") or 0)
            run_id = f"registry_{upload_id}_{int(item.get('data_version') or 0)}"
            silver = item.get("silver_paths") or []
            if isinstance(silver, str):
                silver = [silver]
            stages = [
                ("source", filename, "upload registry", "Source file registered"),
                ("raw", filename, str(item.get("raw_path") or "data/raw"), "Immutable source preserved"),
                ("clean", filename, ", ".join(str(path) for path in silver) or "data/silver", "Rows cleaned, mapped and versioned"),
                ("store", filename, "data/database/business.db", "Business records and detailed context committed"),
                ("serve", "business.db", "dashboards + Clippy launch context", "Metrics and compact context refreshed"),
            ]
            for order, (stage, source, destination, operation) in enumerate(stages, 1):
                con.execute("""
                    INSERT OR REPLACE INTO business_lineage VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                """, [
                    f"{run_id}_{order}", run_id, upload_id, order, stage, operation,
                    source, destination, rows,
                    _json({"backfilled_from_registry": True, "filename": filename}),
                    item.get("last_processed_at") or item.get("created_at") or _now(),
                ])
                inserted += 1
    finally:
        con.close()
    return inserted


def _context_files() -> dict[str, Any]:
    root = settings.data_path / "context" / COMPANY_ID
    result: dict[str, Any] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        key = str(path.relative_to(root)).replace("\\", "/")
        try:
            result[key] = json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower() == ".json" else path.read_text(encoding="utf-8")[:40000]
        except Exception as exc:
            result[key] = {"read_error": f"{type(exc).__name__}: {exc}"}
    return result


def rebuild_business_context(trigger: str, process_type: str | None = None) -> dict[str, Any]:
    """Build detailed and compact context sections inside business.db."""
    initialise_business_store()
    uploads = sync_source_registry()
    ensure_source_lineage(uploads)
    catalog = refresh_business_catalog()
    version = int((pipeline_status() or {}).get("data_version") or 0)
    received_types: set[str] = set()
    for item in uploads:
        if str(item.get("processing_status") or "") not in {"committed", "stored_source", "pending_mapping"}:
            continue
        detected = (item.get("metadata") or {}).get("detected_document_types") or [item.get("document_type")]
        received_types.update(str(value) for value in detected if value)
    missing = sorted(CORE_SETUP_TYPES - received_types)
    setup_complete = not missing
    phase = "recurring_intake" if setup_complete else "initial_setup"
    process_type = process_type or phase

    from .accounting import accounting_dashboard
    from .analytics import dashboard_summary
    from .data_quality import data_quality_dashboard
    from .marketing import marketing_dashboard
    from .tax import tax_dashboard

    sections = {
        "company": get_company_profile(),
        "sources": {
            "files": uploads,
            "required_received": sorted(CORE_SETUP_TYPES & received_types),
            "required_missing": missing,
        },
        "data_catalog": {"tables": catalog},
        "financial_position": dashboard_summary(),
        "accounts": accounting_dashboard(),
        "tax": tax_dashboard(),
        "marketing": marketing_dashboard(),
        "quality": data_quality_dashboard(),
        "legacy_context_import": _context_files(),
        "clippy": CLIPPY_PROFILE,
    }
    upload_ids = [int(item.get("id") or 0) for item in uploads]
    con = get_duckdb()
    try:
        for key, content in sections.items():
            encoded = _json(content)
            con.execute("""
                INSERT OR REPLACE INTO business_context_detail
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                key, key.replace("_", " ").title(), encoded, _json(upload_ids), version,
                hashlib.sha256(encoded.encode("utf-8")).hexdigest(), _now(),
            ])

        summary = sections["financial_position"]
        quality = sections["quality"]
        compact = {
            "company": sections["company"],
            "lifecycle": {
                "phase": phase, "setup_complete": setup_complete,
                "required_missing": missing, "data_version": version,
            },
            "headline_metrics": {
                key: summary.get(key) for key in (
                    "cash", "current_assets", "current_liabilities", "current_ratio",
                    "working_capital", "revenue_month", "expenses_month", "cash_runway_days",
                )
            },
            "data_trust": {
                "score": quality.get("score"), "status": quality.get("status"),
                "open_checks": quality.get("open_check_total"),
            },
            "source_count": len(uploads),
            "table_count": len(catalog),
            "tables_with_data": sum(1 for item in catalog if item["row_count"] > 0),
            "clippy_operating_rule": "Use this summary first; open detailed sections only when the question requires them.",
        }
        summary_text = (
            f"{sections['company'].get('company_name') or 'The company'} is at data version {version}. "
            f"Lifecycle: {phase.replace('_', ' ')}. {len(uploads)} source files feed "
            f"{compact['tables_with_data']} populated business tables. Data trust is "
            f"{quality.get('status', 'unknown')} ({quality.get('score', 0)}/100). "
            f"Cash is {summary.get('cash', 0)}, working capital is {summary.get('working_capital', 0)}, "
            f"and current-period revenue is {summary.get('revenue_month', 0)}. "
            + (f"Initial setup still needs: {', '.join(missing)}." if missing else "Initial setup is complete; accept recurring evidence continuously.")
        )
        con.execute("""
            INSERT OR REPLACE INTO business_context_summary
            VALUES ('clippy_launch_context', ?, ?, ?, ?, ?, ?)
        """, [summary_text, _json(compact), _json(list(sections)), version, max(1, len(summary_text) // 4), _now()])
        previous = con.execute("SELECT setup_completed_at FROM business_lifecycle WHERE id=1").fetchone()
        completed_at = (previous[0] if previous else None) or (_now() if setup_complete else None)
        run_id = f"process_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        con.execute("""
            INSERT OR REPLACE INTO business_lifecycle VALUES (1, ?, ?, ?, ?, ?, ?)
        """, [phase, setup_complete, completed_at, version, run_id, _now()])
        con.execute("""
            INSERT INTO clippy_process_memory VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?)
        """, [
            run_id, process_type, trigger,
            _json(["identify source", "validate", "store detailed business data", "refresh summaries", "record lineage"]),
            _json(list(sections)), summary_text, version, _now(), _now(),
        ])
    finally:
        con.close()
    return {"phase": phase, "setup_complete": setup_complete, "required_missing": missing, "data_version": version, "summary": compact}


def record_ingestion_lineage(result: dict[str, Any], trigger: str = "file_upload") -> dict[str, Any]:
    context = rebuild_business_context(trigger)
    upload_id = int(result.get("upload_id") or 0)
    run_id = f"ingest_{upload_id}_{int(result.get('data_version') or 0)}"
    filename = str(result.get("filename") or "")
    rows = int(result.get("rows_imported") or 0)
    silver = list(result.get("silver_paths") or [])
    stages = [
        ("source", filename, str(result.get("storage") or "local intake"), "Source file registered"),
        ("raw", filename, str(result.get("raw_path") or "data/raw"), "Immutable source preserved"),
        ("clean", filename, ", ".join(str(item) for item in silver) or "data/silver", "Rows cleaned, mapped and versioned"),
        ("store", filename, "data/database/business.db", "Business records and detailed context committed"),
        ("serve", "business.db", "dashboards + Clippy launch context", "Metrics and compact context refreshed"),
    ]
    con = get_duckdb()
    try:
        for order, (stage, source, destination, operation) in enumerate(stages, 1):
            event_id = f"{run_id}_{order}"
            con.execute("""
                INSERT OR REPLACE INTO business_lineage VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
            """, [event_id, run_id, upload_id, order, stage, operation, source, destination, rows, _json({"result": result}), _now()])
    finally:
        con.close()
    return context


def clippy_launch_context() -> dict[str, Any]:
    initialise_business_store()
    con = get_duckdb()
    try:
        summary = con.execute("""
            SELECT summary_text, summary_json, detail_sections_json, data_version, updated_at
            FROM business_context_summary WHERE summary_key='clippy_launch_context'
        """).fetchone()
        if not summary:
            return rebuild_business_context("launch_context_missing")
        lifecycle = con.execute("SELECT phase, setup_complete, setup_completed_at, data_version, updated_at FROM business_lifecycle WHERE id=1").fetchone()
        return {
            "profile": CLIPPY_PROFILE,
            "summary_text": summary[0],
            "summary": json.loads(summary[1] or "{}"),
            "detail_sections": json.loads(summary[2] or "[]"),
            "data_version": int(summary[3] or 0),
            "updated_at": str(summary[4] or ""),
            "lifecycle": {
                "phase": lifecycle[0], "setup_complete": bool(lifecycle[1]),
                "setup_completed_at": str(lifecycle[2] or ""), "data_version": int(lifecycle[3] or 0),
                "updated_at": str(lifecycle[4] or ""),
            } if lifecycle else {},
        }
    finally:
        con.close()


def business_store_status() -> dict[str, Any]:
    launch = clippy_launch_context()
    con = get_duckdb()
    try:
        sources = [
            dict(zip(
                ["upload_id", "filename", "document_type", "intake_category", "processing_status", "rows_received", "rows_new", "rows_changed", "rows_rejected", "data_version", "uploaded_at", "processed_at"],
                row,
            ))
            for row in con.execute("""
                SELECT upload_id, filename, document_type, intake_category, processing_status,
                       rows_received, rows_new, rows_changed, rows_rejected, data_version,
                       uploaded_at, processed_at
                FROM business_source_registry ORDER BY processed_at DESC LIMIT 100
            """).fetchall()
        ]
        lineage = [
            dict(zip(
                ["event_id", "run_id", "upload_id", "stage_order", "stage", "operation", "source_name", "destination_name", "record_count", "status", "created_at"],
                row,
            ))
            for row in con.execute("""
                SELECT event_id, run_id, upload_id, stage_order, stage, operation,
                       source_name, destination_name, record_count, status, created_at
                FROM business_lineage ORDER BY created_at DESC, stage_order ASC LIMIT 250
            """).fetchall()
        ]
        catalog = [
            dict(zip(["table_name", "business_domain", "row_count", "description", "updated_at"], row))
            for row in con.execute("""
                SELECT table_name, business_domain, row_count, description, updated_at
                FROM business_catalog ORDER BY business_domain, table_name
            """).fetchall()
        ]
        processes = [
            dict(zip(["process_id", "process_type", "trigger_name", "status", "result_summary", "data_version", "completed_at"], row))
            for row in con.execute("""
                SELECT process_id, process_type, trigger_name, status, result_summary, data_version, completed_at
                FROM clippy_process_memory ORDER BY completed_at DESC LIMIT 30
            """).fetchall()
        ]
    finally:
        con.close()
    return {
        "database": {"file": "data/database/business.db", "engine": "DuckDB", "canonical": True},
        "clippy": launch,
        "sources": sources,
        "lineage": lineage,
        "catalog": catalog,
        "processes": processes,
    }
