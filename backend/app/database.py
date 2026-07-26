from __future__ import annotations

import json
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from .config import settings

COMPANY_ID = "default"
EMPTY_MODE_MARKER = ".empty_company_data"

ASSETS = [
    ("asset-cash", "Cash", "asset", "current", 19500.0, "warning", "sample"),
    ("asset-receivables", "Accounts receivable", "asset", "current", 61000.0, "warning", "sample"),
    ("asset-inventory", "Inventory", "asset", "current", 52000.0, "healthy", "sample"),
    ("asset-equipment", "Equipment", "asset", "non-current", 210000.0, "healthy", "sample"),
]
LIABILITIES = [
    ("liability-payables", "Supplier payables", "liability", "current", 71000.0, "critical", "sample"),
    ("liability-loan", "Short-term loan", "liability", "current", 48000.0, "warning", "sample"),
    ("liability-other", "Other current liabilities", "liability", "current", 65000.0, "warning", "sample"),
    ("liability-long-loan", "Long-term loan", "liability", "non-current", 88000.0, "healthy", "sample"),
]
INVOICES = [
    ("inv-1001", "INV-1001", "Northstar Supplies", "2026-06-02", "2026-07-02", 4200.0, "paid", "sample"),
    ("inv-1002", "INV-1002", "Metro Freight", "2026-06-09", "2026-07-09", 24850.0, "review", "sample"),
    ("inv-1003", "INV-1003", "Bright Packaging", "2026-06-14", "2026-07-14", 6120.0, "due", "sample"),
    ("inv-1004", "INV-1004", "Northstar Supplies", "2026-06-20", "2026-07-20", 4570.0, "due", "sample"),
    ("inv-1005", "INV-1005", "City Utilities", "2026-06-24", "2026-07-24", 2880.0, "due", "sample"),
]
TRANSACTIONS = [
    ("txn-001", "2026-06-03", "Customer receipts", "income", 44000.0, "normal", "sample"),
    ("txn-002", "2026-06-07", "Payroll", "expense", -18800.0, "normal", "sample"),
    ("txn-003", "2026-06-11", "Metro Freight INV-1002", "supplier payment", -24530.0, "anomaly", "sample"),
    ("txn-dup-001", "2026-06-22", "Metro Freight INV-1002", "supplier payment", -24850.0, "critical", "sample"),
    ("txn-005", "2026-06-26", "Rent", "expense", -7600.0, "normal", "sample"),
]

DEFAULT_PROFILE = {
    "company_name": "Banksia Office Supplies Pty Ltd",
    "industry": "B2B office supplies and workplace consumables distribution",
    "primary_location": "Melbourne, Victoria, Australia",
    "reporting_currency": "AUD",
    "supplier_regions": "Australia, China, Malaysia",
    "important_currencies": "AUD, USD",
    "primary_risks": "Imported paper costs, freight lead times, large-customer concentration, digital-ad efficiency",
    "current_objective": "Lift gross margin, reduce working-capital drag and expand recurring corporate accounts.",
    "current_ratio_target": 1.5,
    "cash_runway_target_days": 60,
    "abn": "",
    "entity_type": "company",
    "state_or_territory": "VIC",
    "gst_registered": True,
    "gst_accounting_method": "accrual",
    "bas_frequency": "quarterly",
    "payg_withholding_registered": True,
    "has_employees": True,
    "financial_year_end": "30 June",
    "income_tax_rate": 25.0,
}

EMPTY_PROFILE = {
    "company_name": "",
    "industry": "",
    "primary_location": "",
    "reporting_currency": "AUD",
    "supplier_regions": "",
    "important_currencies": "",
    "primary_risks": "",
    "current_objective": "",
    "current_ratio_target": 1.2,
    "cash_runway_target_days": 45,
    "abn": "",
    "entity_type": "company",
    "state_or_territory": "VIC",
    "gst_registered": False,
    "gst_accounting_method": "accrual",
    "bas_frequency": "quarterly",
    "payg_withholding_registered": False,
    "has_employees": False,
    "financial_year_end": "30 June",
    "income_tax_rate": 25.0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    names = [
        "intake", "bronze", "silver", "gold", "context", "raw", "staging",
        "curated", "quarantine", "database", "memory", "audit", "exports", "backups",
    ]
    for name in names:
        (settings.data_path / name).mkdir(parents=True, exist_ok=True)
    for layer in ["bronze", "silver", "gold", "context", "quarantine"]:
        (settings.data_path / layer / COMPANY_ID).mkdir(parents=True, exist_ok=True)


def duckdb_path() -> Path:
    database_dir = settings.data_path / "database"
    database_dir.mkdir(parents=True, exist_ok=True)
    canonical = database_dir / "business.db"
    legacy = database_dir / "business.duckdb"
    if not canonical.exists() and legacy.exists():
        legacy.replace(canonical)
    return canonical


def sqlite_path() -> Path:
    return settings.data_path / "database" / "application.sqlite"


def empty_mode_path() -> Path:
    return settings.data_path / EMPTY_MODE_MARKER


def get_duckdb() -> duckdb.DuckDBPyConnection:
    _ensure_dirs()
    path = duckdb_path()
    last_error: Exception | None = None
    attempts = max(1, settings.duckdb_connect_retries)
    for attempt in range(attempts):
        try:
            return duckdb.connect(str(path))
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(max(0.05, settings.duckdb_retry_delay_seconds))
    message = str(last_error or "Unknown DuckDB connection error")
    if "lock" in message.lower() or "conflicting lock" in message.lower():
        raise RuntimeError(
            f"LedgerFlow could not open {path} because another process holds the DuckDB write lock. "
            "Close duplicate LedgerFlow/Python processes and any DuckDB database viewer, then restart once. "
            f"Original error: {message}"
        ) from last_error
    raise RuntimeError(f"LedgerFlow could not open DuckDB at {path}: {message}") from last_error


def get_sqlite() -> sqlite3.Connection:
    _ensure_dirs()
    connection = sqlite3.connect(sqlite_path(), timeout=15)
    connection.row_factory = sqlite3.Row
    # journal_mode is configured once during initialise(). Repeating that pragma on
    # every high-frequency polling read can request an unnecessary schema lock.
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    return connection


def _sqlite_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_sqlite_column(connection: sqlite3.Connection, table: str, name: str, declaration: str) -> None:
    if name not in _sqlite_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def _duckdb_columns(connection: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table}')").fetchall()}


def _add_duckdb_column(connection: duckdb.DuckDBPyConnection, table: str, name: str, declaration: str) -> None:
    if name not in _duckdb_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def _create_business_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS assets_liabilities (
            id VARCHAR PRIMARY KEY, name VARCHAR, category VARCHAR,
            classification VARCHAR, amount DOUBLE, status VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id VARCHAR PRIMARY KEY, invoice_number VARCHAR, supplier VARCHAR,
            invoice_date DATE, due_date DATE, amount DOUBLE, status VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR PRIMARY KEY, transaction_date DATE, description VARCHAR,
            category VARCHAR, amount DOUBLE, status VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id VARCHAR PRIMARY KEY, payment_date DATE, reference VARCHAR,
            counterparty VARCHAR, amount DOUBLE, currency VARCHAR, status VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id VARCHAR PRIMARY KEY, transaction_date DATE, description VARCHAR,
            account_name VARCHAR, amount DOUBLE, balance DOUBLE, currency VARCHAR,
            status VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id VARCHAR PRIMARY KEY, customer_code VARCHAR, name VARCHAR,
            country VARCHAR, segment VARCHAR, status VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id VARCHAR PRIMARY KEY, supplier_code VARCHAR, name VARCHAR,
            country VARCHAR, category VARCHAR, currency VARCHAR, status VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id VARCHAR PRIMARY KEY, sku VARCHAR, name VARCHAR, quantity DOUBLE,
            unit_cost DOUBLE, total_value DOUBLE, location VARCHAR, status VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id VARCHAR PRIMARY KEY, movement_date DATE, sku VARCHAR, item_name VARCHAR,
            movement_type VARCHAR, signed_quantity DOUBLE, unit_cost DOUBLE,
            source_invoice VARCHAR, source_file VARCHAR, evidence_mode VARCHAR,
            applied_to_stock BOOLEAN, note VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inventory_reorder_settings (
            sku VARCHAR PRIMARY KEY, reorder_point DOUBLE, target_stock DOUBLE,
            lead_time_days INTEGER, preferred_supplier VARCHAR, updated_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id VARCHAR PRIMARY KEY, period VARCHAR, account VARCHAR, category VARCHAR,
            budget_amount DOUBLE, actual_amount DOUBLE, variance DOUBLE,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS payroll_records (
            id VARCHAR PRIMARY KEY, pay_period VARCHAR, employee VARCHAR,
            gross_pay DOUBLE, ordinary_time_earnings DOUBLE, payg_withholding DOUBLE,
            superannuation DOUBLE, net_pay DOUBLE, currency VARCHAR,
            status VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS employee_profiles (
            employee VARCHAR PRIMARY KEY, employee_code VARCHAR, department VARCHAR,
            role_title VARCHAR, employment_type VARCHAR, start_date DATE,
            manager VARCHAR, location VARCHAR, status VARCHAR, evidence_mode VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS employee_leave_balances (
            employee VARCHAR PRIMARY KEY, annual_leave_days DOUBLE,
            personal_leave_days DOUBLE, leave_taken_days DOUBLE,
            next_review_date DATE, evidence_mode VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS employee_training (
            id VARCHAR PRIMARY KEY, employee VARCHAR, course_name VARCHAR,
            due_date DATE, completion_status VARCHAR, evidence_mode VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_signals (
            id VARCHAR PRIMARY KEY, signal_type VARCHAR, topic VARCHAR, entity VARCHAR,
            geography VARCHAR, observed_at TIMESTAMP, published_at TIMESTAMP,
            value VARCHAR, unit VARCHAR, direction VARCHAR, source_name VARCHAR,
            source_url VARCHAR, relevance_score DOUBLE, estimated_impact VARCHAR,
            impact_horizon VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS statement_snapshots (
            id VARCHAR PRIMARY KEY, statement_type VARCHAR, period_start DATE,
            period_end DATE, line_item VARCHAR, amount DOUBLE, currency VARCHAR,
            source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS generic_documents (
            id VARCHAR PRIMARY KEY, document_type VARCHAR, title VARCHAR,
            record_json VARCHAR, source_file VARCHAR, source_row INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS validations (
            id VARCHAR PRIMARY KEY, severity VARCHAR, check_name VARCHAR,
            description VARCHAR, target_id VARCHAR, recommendation VARCHAR
        )
    """)
    _add_duckdb_column(con, "validations", "status", "VARCHAR DEFAULT 'open'")
    _add_duckdb_column(con, "validations", "detected_at", "TIMESTAMP")
    _add_duckdb_column(con, "validations", "evidence_json", "VARCHAR")

    # Accounting extensions are additive so existing LedgerFlow databases migrate in place.
    for name, declaration in [
        ("invoice_kind", "VARCHAR DEFAULT 'supplier'"),
        ("currency", "VARCHAR DEFAULT 'AUD'"),
        ("subtotal", "DOUBLE DEFAULT 0"),
        ("gst_amount", "DOUBLE DEFAULT 0"),
        ("description", "VARCHAR DEFAULT ''"),
        ("supplier_abn", "VARCHAR DEFAULT ''"),
        ("account_code", "VARCHAR DEFAULT ''"),
        ("category", "VARCHAR DEFAULT ''"),
        ("tax_code", "VARCHAR DEFAULT 'REVIEW'"),
        ("categorisation_confidence", "DOUBLE DEFAULT 0"),
        ("validation_status", "VARCHAR DEFAULT 'needs_review'"),
        ("source_upload_id", "INTEGER DEFAULT 0"),
        ("sku", "VARCHAR DEFAULT ''"),
        ("quantity", "DOUBLE DEFAULT 0"),
        ("unit_cost", "DOUBLE DEFAULT 0"),
    ]:
        _add_duckdb_column(con, "invoices", name, declaration)

    con.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            code VARCHAR PRIMARY KEY, name VARCHAR, account_type VARCHAR,
            subtype VARCHAR, default_tax_code VARCHAR, active BOOLEAN, source VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS categorisation_rules (
            id VARCHAR PRIMARY KEY, keyword VARCHAR, match_type VARCHAR,
            account_code VARCHAR, tax_code VARCHAR, priority INTEGER,
            source VARCHAR, active BOOLEAN, use_count INTEGER, last_used_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id VARCHAR PRIMARY KEY, entry_date DATE, reference VARCHAR, description VARCHAR,
            source_type VARCHAR, source_id VARCHAR, status VARCHAR, created_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS journal_lines (
            id VARCHAR PRIMARY KEY, journal_id VARCHAR, line_number INTEGER,
            account_code VARCHAR, account_name VARCHAR, debit DOUBLE, credit DOUBLE,
            tax_code VARCHAR, counterparty VARCHAR, source_file VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS account_validation_tasks (
            id VARCHAR PRIMARY KEY, task_type VARCHAR, source_id VARCHAR, source_file VARCHAR,
            counterparty VARCHAR, description VARCHAR, amount DOUBLE,
            suggested_account_code VARCHAR, suggested_account_name VARCHAR,
            suggested_tax_code VARCHAR, confidence DOUBLE, reason VARCHAR, status VARCHAR,
            created_at TIMESTAMP, resolved_at TIMESTAMP
        )
    """)


def _create_app_tables(sql: sqlite3.Connection) -> None:
    sql.executescript("""
        CREATE TABLE IF NOT EXISTS agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_message TEXT NOT NULL,
            workspace TEXT NOT NULL,
            response_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            document_type TEXT NOT NULL,
            rows_imported INTEGER NOT NULL DEFAULT 0,
            curated_path TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS import_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL UNIQUE,
            company_id TEXT NOT NULL,
            upload_id INTEGER,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            rows_received INTEGER NOT NULL DEFAULT 0,
            rows_new INTEGER NOT NULL DEFAULT 0,
            rows_changed INTEGER NOT NULL DEFAULT 0,
            rows_unchanged INTEGER NOT NULL DEFAULT 0,
            rows_rejected INTEGER NOT NULL DEFAULT 0,
            affected_datasets_json TEXT NOT NULL DEFAULT '[]',
            error_message TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(upload_id) REFERENCES uploaded_files(id)
        );
        CREATE TABLE IF NOT EXISTS row_fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            business_key TEXT NOT NULL,
            row_hash TEXT NOT NULL,
            record_version INTEGER NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            source_file_id INTEGER,
            source_sheet TEXT NOT NULL DEFAULT '',
            source_row_number INTEGER NOT NULL DEFAULT 0,
            record_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(company_id, document_type, business_key, record_version)
        );
        CREATE INDEX IF NOT EXISTS idx_row_fp_current
          ON row_fingerprints(company_id, document_type, business_key, is_current);
        CREATE TABLE IF NOT EXISTS mapping_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            schema_signature TEXT NOT NULL,
            mapping_json TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 1,
            use_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(company_id, document_type, schema_signature)
        );
        CREATE TABLE IF NOT EXISTS data_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            affected_datasets_json TEXT NOT NULL,
            import_job_id TEXT,
            UNIQUE(company_id, version_number)
        );
        CREATE TABLE IF NOT EXISTS company_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            baseline_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            baseline_path TEXT NOT NULL,
            data_version INTEGER NOT NULL,
            document_coverage_json TEXT NOT NULL,
            UNIQUE(company_id, baseline_version)
        );
        CREATE TABLE IF NOT EXISTS information_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            request_key TEXT NOT NULL,
            information TEXT NOT NULL,
            reason TEXT NOT NULL,
            priority TEXT NOT NULL,
            accepted_formats TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            UNIQUE(company_id, request_key)
        );
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            run_type TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS clear_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            scope TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT NOT NULL,
            workspace TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memory_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            summary TEXT NOT NULL,
            message_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            action_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            resolved_at TEXT,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS research_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            query TEXT NOT NULL,
            provider TEXT NOT NULL,
            result_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS generated_documents (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            document_type TEXT NOT NULL,
            title TEXT NOT NULL,
            output_format TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            counterparty TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS integration_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS upload_processing_tasks (
            job_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL DEFAULT 'default',
            filename TEXT NOT NULL,
            intake_category TEXT NOT NULL,
            declared_document_type TEXT NOT NULL DEFAULT 'auto',
            status TEXT NOT NULL DEFAULT 'queued',
            stage TEXT NOT NULL DEFAULT 'received',
            progress INTEGER NOT NULL DEFAULT 0,
            stage_message TEXT NOT NULL DEFAULT '',
            upload_id INTEGER,
            result_json TEXT NOT NULL DEFAULT '{}',
            analysis_json TEXT NOT NULL DEFAULT '{}',
            assistant_message TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS competitor_analysis_jobs (
            job_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL DEFAULT 'default',
            status TEXT NOT NULL DEFAULT 'queued',
            stage TEXT NOT NULL DEFAULT 'queued',
            progress INTEGER NOT NULL DEFAULT 0,
            stage_message TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );
    """)
    for name, declaration in [
        ("columns_json", "TEXT DEFAULT '[]'"),
        ("mapping_status", "TEXT DEFAULT 'mapped'"),
        ("company_id", "TEXT DEFAULT 'default'"),
        ("file_id", "TEXT DEFAULT ''"),
        ("original_filename", "TEXT DEFAULT ''"),
        ("file_type", "TEXT DEFAULT ''"),
        ("file_size", "INTEGER DEFAULT 0"),
        ("raw_path", "TEXT DEFAULT ''"),
        ("bronze_path", "TEXT DEFAULT ''"),
        ("silver_paths_json", "TEXT DEFAULT '[]'"),
        ("processing_status", "TEXT DEFAULT 'committed'"),
        ("mapping_confidence", "REAL DEFAULT 0"),
        ("row_count", "INTEGER DEFAULT 0"),
        ("rows_new", "INTEGER DEFAULT 0"),
        ("rows_changed", "INTEGER DEFAULT 0"),
        ("rows_unchanged", "INTEGER DEFAULT 0"),
        ("rows_rejected", "INTEGER DEFAULT 0"),
        ("data_version", "INTEGER DEFAULT 0"),
        ("baseline_version", "INTEGER DEFAULT 0"),
        ("metadata_json", "TEXT DEFAULT '{}'"),
        ("last_processed_at", "TEXT DEFAULT ''"),
        ("intake_category", "TEXT DEFAULT 'recurring'"),
        ("declared_document_type", "TEXT DEFAULT 'auto'"),
        ("analysis_json", "TEXT DEFAULT '{}'"),
        ("assistant_message", "TEXT DEFAULT ''"),
        ("lifecycle_phase", "TEXT DEFAULT ''"),
    ]:
        _add_sqlite_column(sql, "uploaded_files", name, declaration)


def initialise() -> None:
    _ensure_dirs()
    con = get_duckdb()
    _create_business_tables(con)
    if not empty_mode_path().exists():
        if con.execute("SELECT COUNT(*) FROM assets_liabilities").fetchone()[0] == 0:
            con.executemany("INSERT INTO assets_liabilities VALUES (?, ?, ?, ?, ?, ?, ?)", ASSETS + LIABILITIES)
        if con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 0:
            con.executemany("INSERT INTO invoices(id, invoice_number, supplier, invoice_date, due_date, amount, status, source_file) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", INVOICES)
        if con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0:
            con.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)", TRANSACTIONS)
    con.close()

    sql = get_sqlite()
    sql.execute("PRAGMA journal_mode=WAL")
    sql.execute("PRAGMA synchronous=NORMAL")
    _create_app_tables(sql)
    existing = sql.execute("SELECT COUNT(*) FROM company_profile").fetchone()[0]
    if existing == 0:
        sql.execute(
            "INSERT INTO company_profile(id, profile_json, updated_at) VALUES (1, ?, ?)",
            (json.dumps(EMPTY_PROFILE if empty_mode_path().exists() else DEFAULT_PROFILE), utc_now()),
        )
    if sql.execute("SELECT COUNT(*) FROM integration_settings").fetchone()[0] == 0:
        sql.execute(
            "INSERT INTO integration_settings(id, settings_json, updated_at) VALUES (1, ?, ?)",
            (json.dumps({
                "mode": "offline",
                "official_tax_sources": False,
                "supplier_enrichment": False,
                "bank_feeds": False,
                "email_intake": False,
                "cloud_storage": False,
                "ato_sbr": False,
                "external_processing_consent": False,
            }), utc_now()),
        )
    sql.commit()
    sql.close()
    # Imported lazily to avoid a circular import during module loading.
    from .accounting import seed_accounting_reference_data
    seed_accounting_reference_data()


def rows_as_dicts(query: str, parameters: tuple = ()) -> list[dict[str, Any]]:
    con = get_duckdb()
    cursor = con.execute(query, parameters)
    columns = [item[0] for item in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    con.close()
    return rows


def save_agent_event(message: str, workspace: str, response: dict[str, Any]) -> None:
    sql = get_sqlite()
    sql.execute(
        "INSERT INTO agent_events(created_at, user_message, workspace, response_json) VALUES (?, ?, ?, ?)",
        (utc_now(), message, workspace, json.dumps(response, default=str)),
    )
    sql.commit(); sql.close()


def save_conversation_message(role: str, content: str, model: str, workspace: str) -> None:
    sql = get_sqlite()
    sql.execute(
        "INSERT INTO conversation_messages(created_at, role, content, model, workspace) VALUES (?, ?, ?, ?, ?)",
        (utc_now(), role, content, model, workspace),
    )
    sql.commit(); sql.close()


def recent_conversation(limit: int = 12) -> list[dict[str, Any]]:
    sql = get_sqlite()
    rows = sql.execute(
        "SELECT role, content, model, workspace, created_at FROM conversation_messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    sql.close()
    return [dict(row) for row in reversed(rows)]


def conversation_count() -> int:
    sql = get_sqlite(); value = int(sql.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0]); sql.close(); return value


def latest_memory_summary() -> str:
    sql = get_sqlite(); row = sql.execute("SELECT summary FROM memory_summaries ORDER BY id DESC LIMIT 1").fetchone(); sql.close(); return str(row[0]) if row else ""


def save_memory_summary(summary: str, message_count: int) -> None:
    sql = get_sqlite(); sql.execute("INSERT INTO memory_summaries(created_at, summary, message_count) VALUES (?, ?, ?)", (utc_now(), summary, message_count)); sql.commit(); sql.close()


def clear_memory() -> None:
    sql = get_sqlite(); sql.execute("DELETE FROM conversation_messages"); sql.execute("DELETE FROM memory_summaries"); sql.execute("DELETE FROM agent_events"); sql.commit(); sql.close()


def get_company_profile() -> dict[str, Any]:
    sql = get_sqlite(); row = sql.execute("SELECT profile_json FROM company_profile WHERE id = 1").fetchone(); sql.close()
    base = EMPTY_PROFILE if empty_mode_path().exists() else DEFAULT_PROFILE
    if not row: return dict(base)
    try: return {**base, **json.loads(row[0])}
    except Exception: return dict(base)


def save_company_profile(profile: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_PROFILE, **profile}
    sql = get_sqlite()
    sql.execute(
        "INSERT INTO company_profile(id, profile_json, updated_at) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at",
        (json.dumps(merged), utc_now()),
    )
    sql.commit(); sql.close(); return merged


def create_approval(action_type: str, title: str, payload: dict[str, Any]) -> int:
    sql = get_sqlite(); cursor = sql.execute(
        "INSERT INTO approvals(created_at, action_type, title, payload_json, status) VALUES (?, ?, ?, ?, 'pending')",
        (utc_now(), action_type, title, json.dumps(payload, default=str)),
    ); approval_id = int(cursor.lastrowid); sql.commit(); sql.close(); return approval_id


def list_approvals() -> list[dict[str, Any]]:
    sql = get_sqlite(); rows = sql.execute("SELECT * FROM approvals ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id DESC").fetchall(); sql.close()
    result = []
    for row in rows:
        item = dict(row)
        try: item["payload"] = json.loads(item.pop("payload_json"))
        except Exception: item["payload"] = {}
        result.append(item)
    return result


def resolve_approval(approval_id: int, decision: str, note: str = "") -> bool:
    sql = get_sqlite(); cursor = sql.execute(
        "UPDATE approvals SET status=?, resolved_at=?, note=? WHERE id=? AND status='pending'",
        (decision, utc_now(), note, approval_id),
    ); changed = cursor.rowcount > 0; sql.commit(); sql.close(); return changed


def save_research_cache(query: str, provider: str, results: list[dict[str, Any]]) -> None:
    sql = get_sqlite(); sql.execute(
        "INSERT INTO research_cache(created_at, query, provider, result_json) VALUES (?, ?, ?, ?)",
        (utc_now(), query, provider, json.dumps(results, default=str)),
    ); sql.commit(); sql.close()


def list_uploaded_files() -> list[dict[str, Any]]:
    sql = get_sqlite(); rows = sql.execute("SELECT * FROM uploaded_files ORDER BY id DESC").fetchall(); sql.close()
    result = []
    for row in rows:
        item = dict(row)
        for source, target, default in [
            ("columns_json", "columns", []), ("silver_paths_json", "silver_paths", []),
            ("metadata_json", "metadata", {}), ("analysis_json", "analysis", {}),
        ]:
            try: item[target] = json.loads(item.pop(source) or json.dumps(default))
            except Exception: item[target] = default
        result.append(item)
    return result


def get_uploaded_file(upload_id: int) -> dict[str, Any] | None:
    sql = get_sqlite()
    row = sql.execute("SELECT * FROM uploaded_files WHERE id=?", (upload_id,)).fetchone()
    sql.close()
    if not row:
        return None
    item = dict(row)
    for source, target, default in [
        ("columns_json", "columns", []),
        ("silver_paths_json", "silver_paths", []),
        ("metadata_json", "metadata", {}),
        ("analysis_json", "analysis", {}),
    ]:
        try:
            item[target] = json.loads(item.pop(source) or json.dumps(default))
        except Exception:
            item[target] = default
    return item


def completed_upload_count(company_id: str = COMPANY_ID, exclude_upload_id: int | None = None) -> int:
    sql = get_sqlite()
    query = "SELECT COUNT(*) FROM uploaded_files WHERE company_id=? AND processing_status IN ('committed','stored_source','pending_mapping')"
    params: list[Any] = [company_id]
    if exclude_upload_id is not None:
        query += " AND id<>?"
        params.append(exclude_upload_id)
    value = int(sql.execute(query, tuple(params)).fetchone()[0])
    sql.close()
    return value


def save_upload_analysis(upload_id: int, analysis: dict[str, Any], assistant_message: str, lifecycle_phase: str) -> None:
    sql = get_sqlite()
    sql.execute(
        "UPDATE uploaded_files SET analysis_json=?, assistant_message=?, lifecycle_phase=? WHERE id=?",
        (json.dumps(analysis, ensure_ascii=False, default=str), assistant_message, lifecycle_phase, upload_id),
    )
    sql.commit()
    sql.close()


def create_upload_processing_task(job_id: str, filename: str, intake_category: str, declared_document_type: str) -> dict[str, Any]:
    now = utc_now()
    sql = get_sqlite()
    sql.execute(
        "INSERT INTO upload_processing_tasks(job_id, company_id, filename, intake_category, declared_document_type, status, stage, progress, stage_message, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'queued', 'received', 3, 'File received securely', ?, ?)",
        (job_id, COMPANY_ID, filename, intake_category, declared_document_type, now, now),
    )
    sql.commit(); sql.close()
    return get_upload_processing_task(job_id) or {}


def update_upload_processing_task(job_id: str, **values: Any) -> dict[str, Any]:
    allowed = {
        'status', 'stage', 'progress', 'stage_message', 'upload_id', 'result_json',
        'analysis_json', 'assistant_message', 'error_message', 'completed_at',
    }
    updates: list[str] = []
    params: list[Any] = []
    for key, value in values.items():
        if key not in allowed:
            continue
        if key in {'result_json', 'analysis_json'} and not isinstance(value, str):
            value = json.dumps(value or {}, ensure_ascii=False, default=str)
        updates.append(f"{key}=?")
        params.append(value)
    updates.append("updated_at=?")
    params.append(utc_now())
    params.append(job_id)
    sql = get_sqlite()
    sql.execute(f"UPDATE upload_processing_tasks SET {', '.join(updates)} WHERE job_id=?", tuple(params))
    sql.commit(); sql.close()
    return get_upload_processing_task(job_id) or {}


def get_upload_processing_task(job_id: str) -> dict[str, Any] | None:
    sql = get_sqlite(); row = sql.execute("SELECT * FROM upload_processing_tasks WHERE job_id=?", (job_id,)).fetchone(); sql.close()
    if not row:
        return None
    item = dict(row)
    for key in ['result_json', 'analysis_json']:
        target = key.replace('_json', '')
        try: item[target] = json.loads(item.pop(key) or '{}')
        except Exception: item[target] = {}
    return item


def list_active_upload_processing_tasks(company_id: str = COMPANY_ID) -> list[dict[str, Any]]:
    sql = get_sqlite()
    rows = sql.execute("SELECT job_id FROM upload_processing_tasks WHERE company_id=? AND status IN ('queued','processing') ORDER BY created_at DESC", (company_id,)).fetchall()
    sql.close()
    return [item for row in rows if (item := get_upload_processing_task(str(row[0])))]


def create_competitor_analysis_job(job_id: str) -> dict[str, Any]:
    now = utc_now(); sql = get_sqlite()
    sql.execute("INSERT INTO competitor_analysis_jobs(job_id, company_id, status, stage, progress, stage_message, created_at, updated_at) VALUES (?, ?, 'queued', 'queued', 2, 'Deep analysis queued', ?, ?)", (job_id, COMPANY_ID, now, now))
    sql.commit(); sql.close()
    return get_competitor_analysis_job(job_id) or {}


def update_competitor_analysis_job(job_id: str, **values: Any) -> dict[str, Any]:
    allowed = {'status', 'stage', 'progress', 'stage_message', 'result_json', 'error_message', 'completed_at'}
    updates: list[str] = []; params: list[Any] = []
    for key, value in values.items():
        if key not in allowed: continue
        if key == 'result_json' and not isinstance(value, str): value = json.dumps(value or {}, ensure_ascii=False, default=str)
        updates.append(f"{key}=?"); params.append(value)
    updates.append('updated_at=?'); params.append(utc_now()); params.append(job_id)
    sql = get_sqlite(); sql.execute(f"UPDATE competitor_analysis_jobs SET {', '.join(updates)} WHERE job_id=?", tuple(params)); sql.commit(); sql.close()
    return get_competitor_analysis_job(job_id) or {}


def get_competitor_analysis_job(job_id: str) -> dict[str, Any] | None:
    sql = get_sqlite(); row = sql.execute("SELECT * FROM competitor_analysis_jobs WHERE job_id=?", (job_id,)).fetchone(); sql.close()
    if not row: return None
    item = dict(row)
    try: item['result'] = json.loads(item.pop('result_json') or '{}')
    except Exception: item['result'] = {}
    return item


def latest_competitor_analysis_job(company_id: str = COMPANY_ID) -> dict[str, Any] | None:
    sql = get_sqlite(); row = sql.execute("SELECT job_id FROM competitor_analysis_jobs WHERE company_id=? ORDER BY created_at DESC LIMIT 1", (company_id,)).fetchone(); sql.close()
    return get_competitor_analysis_job(str(row[0])) if row else None


def save_generated_document(document_id: str, document_type: str, title: str, output_format: str, filename: str, file_path: str, status: str = "draft", counterparty: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    sql = get_sqlite()
    sql.execute(
        "INSERT OR REPLACE INTO generated_documents(id, created_at, document_type, title, output_format, filename, file_path, status, counterparty, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (document_id, utc_now(), document_type, title, output_format, filename, file_path, status, counterparty, json.dumps(metadata or {}, default=str)),
    )
    sql.commit(); sql.close()
    return {"id": document_id, "document_type": document_type, "title": title, "output_format": output_format, "filename": filename, "file_path": file_path, "status": status, "counterparty": counterparty, "metadata": metadata or {}}


def list_generated_documents() -> list[dict[str, Any]]:
    sql = get_sqlite(); rows = sql.execute("SELECT * FROM generated_documents ORDER BY created_at DESC").fetchall(); sql.close()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try: item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        except Exception: item["metadata"] = {}
        result.append(item)
    return result


def get_generated_document(document_id: str) -> dict[str, Any] | None:
    sql = get_sqlite(); row = sql.execute("SELECT * FROM generated_documents WHERE id=?", (document_id,)).fetchone(); sql.close()
    if not row: return None
    item = dict(row)
    try: item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    except Exception: item["metadata"] = {}
    return item


def get_integration_settings() -> dict[str, Any]:
    defaults = {
        "mode": "offline", "official_tax_sources": False, "supplier_enrichment": False,
        "bank_feeds": False, "email_intake": False, "cloud_storage": False,
        "ato_sbr": False, "external_processing_consent": False,
    }
    sql = get_sqlite(); row = sql.execute("SELECT settings_json FROM integration_settings WHERE id=1").fetchone(); sql.close()
    if not row: return defaults
    try: return {**defaults, **json.loads(row[0])}
    except Exception: return defaults


def save_integration_settings(values: dict[str, Any]) -> dict[str, Any]:
    current = get_integration_settings(); current.update(values)
    # ATO/SBR cannot be activated by a local toggle; it requires DSP registration and conformance.
    current["ato_sbr"] = False
    sql = get_sqlite()
    sql.execute("INSERT INTO integration_settings(id, settings_json, updated_at) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET settings_json=excluded.settings_json, updated_at=excluded.updated_at", (json.dumps(current), utc_now()))
    sql.commit(); sql.close(); return current


def next_data_version(company_id: str, reason: str, datasets: list[str], import_job_id: str | None = None) -> int:
    sql = get_sqlite()
    current = int(sql.execute("SELECT COALESCE(MAX(version_number), 0) FROM data_versions WHERE company_id=?", (company_id,)).fetchone()[0])
    version = current + 1
    sql.execute(
        "INSERT INTO data_versions(company_id, version_number, created_at, reason, affected_datasets_json, import_job_id) VALUES (?, ?, ?, ?, ?, ?)",
        (company_id, version, utc_now(), reason, json.dumps(sorted(set(datasets))), import_job_id),
    )
    sql.commit(); sql.close(); return version


def current_data_version(company_id: str = COMPANY_ID) -> int:
    sql = get_sqlite(); value = int(sql.execute("SELECT COALESCE(MAX(version_number), 0) FROM data_versions WHERE company_id=?", (company_id,)).fetchone()[0]); sql.close(); return value


def current_baseline_version(company_id: str = COMPANY_ID) -> int:
    sql = get_sqlite(); value = int(sql.execute("SELECT COALESCE(MAX(baseline_version), 0) FROM company_baselines WHERE company_id=?", (company_id,)).fetchone()[0]); sql.close(); return value


def save_mapping_profile(document_type: str, schema_signature: str, mapping: dict[str, str], company_id: str = COMPANY_ID) -> None:
    sql = get_sqlite(); now = utc_now()
    sql.execute(
        "INSERT INTO mapping_profiles(company_id, document_type, schema_signature, mapping_json, approved, use_count, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 1, ?, ?) "
        "ON CONFLICT(company_id, document_type, schema_signature) DO UPDATE SET mapping_json=excluded.mapping_json, approved=1, use_count=mapping_profiles.use_count+1, updated_at=excluded.updated_at",
        (company_id, document_type, schema_signature, json.dumps(mapping), now, now),
    )
    sql.commit(); sql.close()


def load_mapping_profile(document_type: str, schema_signature: str, company_id: str = COMPANY_ID) -> dict[str, str] | None:
    sql = get_sqlite(); row = sql.execute(
        "SELECT mapping_json FROM mapping_profiles WHERE company_id=? AND document_type=? AND schema_signature=? AND approved=1",
        (company_id, document_type, schema_signature),
    ).fetchone()
    if row:
        sql.execute("UPDATE mapping_profiles SET use_count=use_count+1, updated_at=? WHERE company_id=? AND document_type=? AND schema_signature=?", (utc_now(), company_id, document_type, schema_signature)); sql.commit()
    sql.close()
    if not row: return None
    try: return json.loads(row[0])
    except Exception: return None


def record_pipeline_run(run_type: str, status: str, details: dict[str, Any], company_id: str = COMPANY_ID) -> None:
    sql = get_sqlite(); now = utc_now()
    sql.execute(
        "INSERT INTO pipeline_runs(company_id, run_type, started_at, completed_at, status, details_json) VALUES (?, ?, ?, ?, ?, ?)",
        (company_id, run_type, now, now, status, json.dumps(details, default=str)),
    ); sql.commit(); sql.close()


def pipeline_status(company_id: str = COMPANY_ID) -> dict[str, Any]:
    sql = get_sqlite()
    uploads = int(sql.execute("SELECT COUNT(*) FROM uploaded_files WHERE company_id=?", (company_id,)).fetchone()[0])
    mapped = int(sql.execute("SELECT COUNT(*) FROM uploaded_files WHERE company_id=? AND mapping_status='mapped'", (company_id,)).fetchone()[0])
    rows_new = int(sql.execute("SELECT COALESCE(SUM(rows_new),0) FROM uploaded_files WHERE company_id=?", (company_id,)).fetchone()[0])
    rows_changed = int(sql.execute("SELECT COALESCE(SUM(rows_changed),0) FROM uploaded_files WHERE company_id=?", (company_id,)).fetchone()[0])
    rows_unchanged = int(sql.execute("SELECT COALESCE(SUM(rows_unchanged),0) FROM uploaded_files WHERE company_id=?", (company_id,)).fetchone()[0])
    jobs = [dict(row) for row in sql.execute("SELECT * FROM import_jobs WHERE company_id=? ORDER BY id DESC LIMIT 10", (company_id,)).fetchall()]
    coverage_rows = sql.execute("SELECT document_type, COUNT(*) AS files, COALESCE(SUM(rows_imported),0) AS rows FROM uploaded_files WHERE company_id=? GROUP BY document_type ORDER BY files DESC", (company_id,)).fetchall()
    category_rows = sql.execute("SELECT intake_category, COUNT(*) AS files, COALESCE(SUM(rows_imported),0) AS rows FROM uploaded_files WHERE company_id=? GROUP BY intake_category ORDER BY intake_category", (company_id,)).fetchall()
    recent_uploads = [dict(row) for row in sql.execute("SELECT id, filename, document_type, intake_category, rows_imported, processing_status, mapping_status, created_at FROM uploaded_files WHERE company_id=? ORDER BY id DESC LIMIT 12", (company_id,)).fetchall()]
    requests = [dict(row) for row in sql.execute("SELECT * FROM information_requests WHERE company_id=? ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id", (company_id,)).fetchall()]
    mappings = int(sql.execute("SELECT COUNT(*) FROM mapping_profiles WHERE company_id=?", (company_id,)).fetchone()[0])
    sql.close()
    return {
        "company_id": company_id,
        "empty_mode": empty_mode_path().exists(),
        "data_version": current_data_version(company_id),
        "baseline_version": current_baseline_version(company_id),
        "uploads": uploads,
        "mapped_uploads": mapped,
        "rows_new": rows_new,
        "rows_changed": rows_changed,
        "rows_unchanged": rows_unchanged,
        "saved_mapping_profiles": mappings,
        "document_coverage": [dict(row) for row in coverage_rows],
        "intake_categories": [dict(row) for row in category_rows],
        "recent_uploads": recent_uploads,
        "recent_jobs": jobs,
        "information_requests": requests,
        "layers": {
            layer: str(settings.data_path / layer / company_id)
            for layer in ["bronze", "silver", "gold", "context", "quarantine"]
        },
    }


def _backup_data(scope: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = settings.data_path / "backups" / f"before_clear_{scope}_{timestamp}"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ["bronze", "silver", "gold", "context", "raw", "curated", "quarantine", "database", "memory", "audit", "exports"]:
        source = settings.data_path / name
        if source.exists(): shutil.copytree(source, destination / name, dirs_exist_ok=True)
    return str(destination)


def _clear_directory_contents(path: Path, preserve_names: set[str] | None = None) -> None:
    preserve = preserve_names or set()
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    for child in path.iterdir():
        if child.name in preserve:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def clear_company_data(scope: str = "company", backup: bool = True) -> dict[str, Any]:
    if scope not in {"company", "memory", "market", "all"}:
        raise ValueError("Scope must be company, memory, market, or all.")
    backup_path = _backup_data(scope) if backup else ""

    if scope in {"company", "all"}:
        con = get_duckdb()
        for table in [
            "assets_liabilities", "invoices", "transactions", "payments", "bank_transactions",
            "customers", "suppliers", "inventory", "budgets", "payroll_records", "statement_snapshots",
            "generic_documents", "validations", "journal_lines", "journal_entries",
            "account_validation_tasks", "inventory_movements", "inventory_reorder_settings",
            "employee_profiles", "employee_leave_balances", "employee_training",
        ]:
            con.execute(f"DELETE FROM {table}")
        available_tables = {str(row[0]) for row in con.execute("SHOW TABLES").fetchall()}
        for table in [
            "business_source_registry", "business_catalog", "business_context_detail",
            "business_context_summary", "business_lineage", "business_lifecycle",
            "clippy_process_memory",
        ]:
            if table in available_tables:
                con.execute(f"DELETE FROM {table}")
        if scope == "all": con.execute("DELETE FROM market_signals")
        con.close()
        sql = get_sqlite()
        for table in [
            "row_fingerprints", "import_jobs", "uploaded_files", "mapping_profiles",
            "data_versions", "company_baselines", "pipeline_runs", "approvals",
            "information_requests", "generated_documents", "upload_processing_tasks",
            "competitor_analysis_jobs",
        ]:
            sql.execute(f"DELETE FROM {table}")
        if scope == "all":
            sql.execute("DELETE FROM information_requests")
            sql.execute("UPDATE company_profile SET profile_json=?, updated_at=? WHERE id=1", (json.dumps(EMPTY_PROFILE), utc_now()))
        sql.commit(); sql.close()
        for name in ["intake", "bronze", "silver", "gold", "raw", "staging", "curated", "quarantine", "exports"]:
            target = settings.data_path / name
            if target.exists(): shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
        company_context = settings.data_path / "context" / COMPANY_ID
        context_files = ["company_baseline.json", "information_requests.json", "company_ai_context.json", "temporal_decision_context.json"]
        if scope == "all":
            context_files.extend([
                "agent_working_context.json", "market_intelligence.json", "market_profile.json",
                "latest_market_snapshot.json", "market_brief.md",
            ])
        for name in context_files:
            path = company_context / name
            if path.exists(): path.unlink()
        for suffix in ["", "-wal", "-shm"]:
            decision_db = settings.data_path / "database" / f"decision_context.sqlite{suffix}"
            if decision_db.exists():
                decision_db.unlink()
        empty_mode_path().write_text("Company data intentionally cleared. Demo seed disabled.\n", encoding="utf-8")

        if scope == "all":
            # Remove every uploaded/staged source while preserving only intake instructions.
            source_root = settings.data_path / "source_files"
            _clear_directory_contents(source_root, {"README.md", ".use_as_folder_intake"})
            (source_root / "permanent").mkdir(parents=True, exist_ok=True)
            (source_root / "recurring").mkdir(parents=True, exist_ok=True)

            file_drop_root = Path(__file__).resolve().parents[2] / "file_drop"
            _clear_directory_contents(file_drop_root, {"README.txt"})
            for name in ("permanent", "recurring", "archive"):
                (file_drop_root / name).mkdir(parents=True, exist_ok=True)

            # Context files are derived data. Base prompts live under agent/ and remain intact.
            context_root = settings.data_path / "context" / COMPANY_ID
            if context_root.exists():
                shutil.rmtree(context_root)
            context_root.mkdir(parents=True, exist_ok=True)

            # These databases use independent connections and are recreated lazily.
            for database_name in ("langgraph_runs.sqlite", "langgraph_checkpoints.sqlite"):
                for suffix in ("", "-wal", "-shm"):
                    target = settings.data_path / "database" / f"{database_name}{suffix}"
                    if target.exists():
                        target.unlink()

    if scope in {"memory", "all"}:
        clear_memory()
        memory_dir = settings.data_path / "memory"
        if memory_dir.exists(): shutil.rmtree(memory_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)
        working_context = settings.data_path / "context" / COMPANY_ID / "agent_working_context.json"
        if working_context.exists(): working_context.unlink()

    if scope in {"market", "all"}:
        con = get_duckdb(); con.execute("DELETE FROM market_signals"); con.close()
        sql = get_sqlite(); sql.execute("DELETE FROM research_cache"); sql.execute("DELETE FROM information_requests"); sql.commit(); sql.close()
        context_dir = settings.data_path / "context" / COMPANY_ID
        for name in ["market_profile.json", "latest_market_snapshot.json", "market_brief.md", "information_requests.json"]:
            path = context_dir / name
            if path.exists(): path.unlink()
        silver_market = settings.data_path / "silver" / COMPANY_ID / "market_context"
        if silver_market.exists(): shutil.rmtree(silver_market)

    initialise()
    sql = get_sqlite(); sql.execute(
        "INSERT INTO clear_events(created_at, scope, backup_path, details_json) VALUES (?, ?, ?, ?)",
        (utc_now(), scope, backup_path, json.dumps({"empty_mode": empty_mode_path().exists()})),
    ); sql.commit(); sql.close()
    return {"ok": True, "scope": scope, "backup_created": bool(backup_path), "backup_path": backup_path, "empty_mode": empty_mode_path().exists()}
