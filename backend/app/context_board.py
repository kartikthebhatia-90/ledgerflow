from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .timezone_utils import resolve_timezone
from .database import COMPANY_ID
from .decision_context import decision_context_dashboard, decision_context_db_path, temporal_context_path
from .document_routing import folder_declared_document_type, strong_filename_document_hint
from .upload_intelligence import company_context_path, market_intelligence_path, upload_library
from .architecture_registry import DEPARTMENT_AGENTS
from .superset_bridge import dashboard_catalogue
from .analysis_context import (
    business_analyst_context_path,
    market_analysis_context_path,
    market_analysis_template_path,
    refresh_analysis_context_files,
)

_BOARD_LOCK = threading.RLock()

APP_SECTIONS: dict[str, dict[str, Any]] = {
    "overview": {
        "label": "Overview",
        "description": "Cash, liquidity, performance movement, working capital and high-level alerts.",
        "x": 0.50,
        "y": 0.28,
    },
    "accounts": {
        "label": "Accounts",
        "description": "Accounts, journals, invoices, reconciliations and financial controls.",
        "x": 0.32,
        "y": 0.40,
    },
    "tax": {
        "label": "Tax",
        "description": "GST, BAS, PAYG, superannuation and tax workpaper evidence.",
        "x": 0.38,
        "y": 0.68,
    },
    "marketing": {
        "label": "Marketing",
        "description": "Revenue, marketing spend, channel efficiency and forecast context.",
        "x": 0.62,
        "y": 0.68,
    },
    "intelligence": {
        "label": "Intelligence",
        "description": "Competitors, market signals, business objectives and strategic analysis.",
        "x": 0.68,
        "y": 0.40,
    },
}
_VALID_LENSES = {"all", *APP_SECTIONS.keys()}

PROCESS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "financial_statements": {
        "label": "Financial statements",
        "description": "Normalises balance sheet, profit and loss and cash-flow lines into statement snapshots.",
        "sections": ["overview", "accounts", "tax", "intelligence"],
    },
    "ledger_and_accounts": {
        "label": "Ledger & account mapping",
        "description": "Maps accounts, categories, tax codes and journal-ready records.",
        "sections": ["accounts", "tax", "overview"],
    },
    "invoice_and_gst": {
        "label": "Invoices & GST",
        "description": "Extracts invoice identities, counterparties, due dates, net values, GST and coding suggestions.",
        "sections": ["accounts", "tax", "overview", "marketing"],
    },
    "bank_and_reconciliation": {
        "label": "Bank & reconciliation",
        "description": "Extracts bank transactions, balances and references used for cash and reconciliation checks.",
        "sections": ["overview", "accounts", "tax"],
    },
    "payroll_and_obligations": {
        "label": "Payroll & obligations",
        "description": "Extracts wages, PAYG withholding, superannuation and net-pay evidence.",
        "sections": ["accounts", "tax", "overview"],
    },
    "working_capital": {
        "label": "Working capital",
        "description": "Builds receivable, payable, inventory and ageing measures for operating-cycle analysis.",
        "sections": ["overview", "accounts", "intelligence"],
    },
    "assets_and_depreciation": {
        "label": "Assets & depreciation",
        "description": "Normalises fixed assets, useful lives, carrying values and depreciation context.",
        "sections": ["accounts", "tax", "overview"],
    },
    "forecast_and_budget": {
        "label": "Forecast & budget",
        "description": "Builds forward revenue, expected orders, budgets and scenario inputs.",
        "sections": ["overview", "marketing", "intelligence"],
    },
    "company_and_requirements": {
        "label": "Company & requirements",
        "description": "Extracts business objectives, operating constraints, use cases and company context.",
        "sections": ["overview", "intelligence"],
    },
    "market_and_competitors": {
        "label": "Market & competitors",
        "description": "Normalises competitor metrics, market signals, geography, relevance and impact horizons.",
        "sections": ["intelligence", "marketing", "overview"],
    },
    "contracts_and_commitments": {
        "label": "Contracts & commitments",
        "description": "Extracts counterparties, values, renewal dates and commitments for strategic and financial use.",
        "sections": ["accounts", "intelligence", "overview"],
    },
    "generic_extraction": {
        "label": "Generic extraction",
        "description": "Stores unclassified evidence until its document type and downstream use are confirmed.",
        "sections": ["intelligence"],
    },
}

DOCUMENT_PIPELINE_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "balance_sheet": {"processes": ["financial_statements", "ledger_and_accounts", "working_capital"], "sections": ["overview", "accounts", "tax", "intelligence"]},
    "profit_loss": {"processes": ["financial_statements", "ledger_and_accounts"], "sections": ["overview", "accounts", "tax", "marketing", "intelligence"]},
    "cash_flow_statement": {"processes": ["financial_statements", "bank_and_reconciliation"], "sections": ["overview", "accounts", "intelligence"]},
    "chart_of_accounts": {"processes": ["ledger_and_accounts"], "sections": ["accounts", "tax", "overview"]},
    "business_requirements": {"processes": ["company_and_requirements"], "sections": ["overview", "intelligence"]},
    "fixed_asset_register": {"processes": ["assets_and_depreciation", "ledger_and_accounts"], "sections": ["accounts", "tax", "overview"]},
    "aged_debtors_creditors": {"processes": ["working_capital"], "sections": ["overview", "accounts", "intelligence"]},
    "material_contracts": {"processes": ["contracts_and_commitments", "company_and_requirements"], "sections": ["accounts", "intelligence", "overview"]},
    "sales_forecast": {"processes": ["forecast_and_budget"], "sections": ["overview", "marketing", "intelligence"]},
    "personnel_plan": {"processes": ["payroll_and_obligations", "forecast_and_budget"], "sections": ["accounts", "tax", "intelligence"]},
    "use_cases_user_stories": {"processes": ["company_and_requirements"], "sections": ["overview", "intelligence"]},
    "historical_tax_returns": {"processes": ["ledger_and_accounts", "financial_statements"], "sections": ["tax", "accounts", "intelligence"]},
    "market_context": {"processes": ["market_and_competitors"], "sections": ["intelligence", "marketing", "overview"]},
    "supplier_invoices": {"processes": ["invoice_and_gst", "ledger_and_accounts", "working_capital"], "sections": ["accounts", "tax", "overview"]},
    "sales_invoices": {"processes": ["invoice_and_gst", "ledger_and_accounts", "working_capital"], "sections": ["accounts", "tax", "overview", "marketing"]},
    "invoices": {"processes": ["invoice_and_gst", "ledger_and_accounts"], "sections": ["accounts", "tax", "overview"]},
    "bank_statements": {"processes": ["bank_and_reconciliation", "ledger_and_accounts"], "sections": ["overview", "accounts", "tax"]},
    "payroll": {"processes": ["payroll_and_obligations", "ledger_and_accounts"], "sections": ["accounts", "tax", "overview"]},
    "assets": {"processes": ["assets_and_depreciation"], "sections": ["accounts", "tax", "overview"]},
    "liabilities": {"processes": ["ledger_and_accounts", "working_capital"], "sections": ["accounts", "overview", "tax"]},
    "assets_liabilities": {"processes": ["financial_statements", "working_capital"], "sections": ["overview", "accounts", "tax"]},
    "customers": {"processes": ["working_capital", "company_and_requirements"], "sections": ["accounts", "marketing", "intelligence"]},
    "suppliers": {"processes": ["working_capital", "company_and_requirements"], "sections": ["accounts", "intelligence"]},
    "inventory": {"processes": ["working_capital", "ledger_and_accounts"], "sections": ["overview", "accounts", "intelligence"]},
    "budgets": {"processes": ["forecast_and_budget", "ledger_and_accounts"], "sections": ["overview", "accounts", "marketing"]},
    "transactions": {"processes": ["bank_and_reconciliation", "ledger_and_accounts"], "sections": ["overview", "accounts", "tax"]},
    "generic": {"processes": ["generic_extraction"], "sections": ["intelligence"]},
}

_CONTEXT_SECTIONS: dict[str, list[str]] = {
    "context:base_personality": list(APP_SECTIONS),
    "context:business_analyst": list(APP_SECTIONS),
    "context:market_template": ["intelligence"],
    "context:market_analysis": ["intelligence"],
    "context:market_intelligence": ["intelligence", "marketing", "overview"],
    "context:time_context": list(APP_SECTIONS),
    "context:working_memory": list(APP_SECTIONS),
    "context:company_context": list(APP_SECTIONS),
    "context:semantic_layer": list(APP_SECTIONS),
}

_SOURCE_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".pdf"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _context_layers() -> dict[str, dict[str, Any]]:
    return {
        "context:base_personality": {
            "label": "System rules",
            "kind": "markdown",
            "path": settings.base_personality_path,
            "description": "Protected behavioural rules and safety guardrails used by Ledger AI.",
            "protected": True,
            "locked_enabled": True,
            "graph_visibility": "zoom",
            "list_group": "Core AI files",
        },
        "context:business_analyst": {
            "label": "Business analyst context",
            "kind": "json",
            "path": business_analyst_context_path(),
            "description": "Generated internal business-analysis context with a section for every app workspace, connected evidence, decision rules and user instructions.",
            "protected": False,
            "locked_enabled": True,
            "graph_visibility": "zoom",
            "list_group": "Core AI files",
        },
        "context:market_template": {
            "label": "Market analysis template",
            "kind": "json",
            "path": market_analysis_template_path(),
            "description": "Editable competitor, market, macroeconomic, supplier, customer and geopolitical analysis template.",
            "protected": False,
            "graph_visibility": "zoom",
            "list_group": "Market analysis",
        },
        "context:market_analysis": {
            "label": "Market analysis context",
            "kind": "json",
            "path": market_analysis_context_path(),
            "description": "Combines internal business context, the market template, connected market files and the saved market report for Intelligence analysis.",
            "protected": False,
            "graph_visibility": "zoom",
            "list_group": "Market analysis",
        },
        "context:market_intelligence": {
            "label": "Saved market report",
            "kind": "json",
            "path": market_intelligence_path(),
            "description": "Saved competitor comparison, market signals and deep-analysis output.",
            "protected": False,
            "graph_visibility": "zoom",
            "list_group": "Market analysis",
        },
        "context:time_context": {
            "label": "Time and freshness",
            "kind": "json",
            "path": temporal_context_path(),
            "description": "Current time, effective dates, data cutoff and previous analysis timestamps.",
            "protected": False,
            "graph_visibility": "zoom",
            "list_group": "Core AI files",
        },
        "context:working_memory": {
            "label": "Working memory",
            "kind": "json",
            "path": settings.data_path / "context" / COMPANY_ID / "agent_working_context.json",
            "description": "Recent conversational continuity and completed interactions.",
            "protected": False,
            "graph_visibility": "list_only",
            "list_group": "Supporting context",
        },
        "context:company_context": {
            "label": "Company source register",
            "kind": "json",
            "path": company_context_path(),
            "description": "Company onboarding, document coverage, upload history and operating snapshot.",
            "protected": False,
            "graph_visibility": "list_only",
            "list_group": "Supporting context",
        },
        "context:semantic_layer": {
            "label": "Metric definitions",
            "kind": "json",
            "path": _root() / "analytics" / "semantic_layer" / "metrics.json",
            "description": "Canonical KPI definitions, controlling sources and interpretation rules.",
            "protected": True,
            "graph_visibility": "list_only",
            "list_group": "Supporting context",
        },
    }


def _connect() -> sqlite3.Connection:
    path = decision_context_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _ensure_columns(con: sqlite3.Connection, table: str, definitions: dict[str, str]) -> None:
    columns = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")}
    for name, ddl in definitions.items():
        if name not in columns:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def initialise_context_board() -> None:
    con = _connect()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS context_board_nodes (
            node_id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            context_level TEXT NOT NULL DEFAULT 'medium',
            weight REAL NOT NULL DEFAULT 0.58,
            enabled INTEGER NOT NULL DEFAULT 1,
            label_override TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            decision_scopes_json TEXT NOT NULL DEFAULT '[]',
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS context_board_processes (
            process_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1,
            label_override TEXT NOT NULL DEFAULT '',
            description_override TEXT NOT NULL DEFAULT '',
            app_sections_json TEXT NOT NULL DEFAULT '[]',
            agent_ids_json TEXT NOT NULL DEFAULT '[]',
            notes TEXT NOT NULL DEFAULT '',
            x REAL NOT NULL DEFAULT 0.5,
            y REAL NOT NULL DEFAULT 0.5,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS context_board_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS context_board_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            node_id TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    _ensure_columns(
        con,
        "context_board_nodes",
        {
            "document_type_override": "TEXT NOT NULL DEFAULT ''",
            "extraction_targets_json": "TEXT NOT NULL DEFAULT '[]'",
            "app_sections_json": "TEXT NOT NULL DEFAULT '[]'",
            "transformation_note": "TEXT NOT NULL DEFAULT ''",
            "processing_order": "INTEGER NOT NULL DEFAULT 100",
        },
    )
    _ensure_columns(
        con,
        "context_board_processes",
        {
            "agent_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        },
    )
    con.commit()
    con.close()


def _json_load(raw: Any, fallback: Any) -> Any:
    try:
        return json.loads(str(raw))
    except Exception:
        return fallback


def _valid_sections(values: Any, fallback: list[str]) -> list[str]:
    if not isinstance(values, list):
        return list(fallback)
    result = [str(value) for value in values if str(value) in APP_SECTIONS]
    return list(dict.fromkeys(result)) or list(fallback)


def _valid_processes(values: Any, fallback: list[str]) -> list[str]:
    if not isinstance(values, list):
        return list(fallback)
    result = [str(value) for value in values if str(value) in PROCESS_DEFINITIONS]
    return list(dict.fromkeys(result)) or list(fallback)


def _pipeline_defaults(document_type: str) -> dict[str, list[str]]:
    return DOCUMENT_PIPELINE_DEFAULTS.get(document_type, DOCUMENT_PIPELINE_DEFAULTS["generic"])


def _settings(con: sqlite3.Connection) -> dict[str, Any]:
    values = {str(row["key"]): _json_load(row["value_json"], None) for row in con.execute("SELECT key, value_json FROM context_board_settings")}
    active = str(values.get("active_lens") or "all")
    return {
        "active_lens": active if active in _VALID_LENSES else "all",
        "show_excluded": bool(values.get("show_excluded", True)),
        "auto_story": bool(values.get("auto_story", True)),
    }


def _save_setting(con: sqlite3.Connection, key: str, value: Any) -> None:
    con.execute(
        "INSERT INTO context_board_settings(key, value_json, updated_at_utc) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at_utc=excluded.updated_at_utc",
        (key, json.dumps(value, ensure_ascii=False), _now()),
    )


def _ellipse_position(index: int, total: int, radius_x: float, radius_y: float, phase: float = -math.pi / 2) -> tuple[float, float]:
    total = max(1, total)
    angle = phase + (2 * math.pi * index / total)
    x = 0.5 + radius_x * math.cos(angle)
    y = 0.5 + radius_y * math.sin(angle)
    return round(min(0.96, max(0.04, x)), 4), round(min(0.94, max(0.06, y)), 4)


def _context_position(index: int, total: int) -> tuple[float, float]:
    return _ellipse_position(index, total, 0.15, 0.19, phase=-math.pi / 2 + math.pi / 6)


def _source_position(index: int, total: int) -> tuple[float, float]:
    return _ellipse_position(index, total, 0.44, 0.42)


def _process_position(index: int, total: int) -> tuple[float, float]:
    return _ellipse_position(index, total, 0.34, 0.31, phase=-math.pi / 2 + math.pi / 12)


def _row_settings(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in con.execute("SELECT * FROM context_board_nodes"):
        item = dict(row)
        item["decision_scopes"] = _json_load(item.pop("decision_scopes_json", "[]"), [])
        item["extraction_targets"] = _json_load(item.pop("extraction_targets_json", "[]"), [])
        item["app_sections"] = _json_load(item.pop("app_sections_json", "[]"), [])
        item["enabled"] = bool(item.get("enabled"))
        result[str(item["node_id"])] = item
    return result


def _process_settings(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in con.execute("SELECT * FROM context_board_processes"):
        item = dict(row)
        item["enabled"] = bool(item.get("enabled"))
        item["app_sections"] = _json_load(item.pop("app_sections_json", "[]"), [])
        item["agent_ids"] = _json_load(item.pop("agent_ids_json", "[]"), [])
        result[str(item["process_id"])] = item
    return result


def _ensure_source_or_context(
    con: sqlite3.Connection,
    current: dict[str, dict[str, Any]],
    *,
    node_id: str,
    node_type: str,
    x: float,
    y: float,
    app_sections: list[str],
    extraction_targets: list[str] | None = None,
    processing_order: int = 100,
) -> dict[str, Any]:
    existing = current.get(node_id)
    if existing:
        return existing
    extraction_targets = extraction_targets or []
    payload = {
        "node_id": node_id,
        "node_type": node_type,
        "x": x,
        "y": y,
        "context_level": "medium",
        "weight": 0.58,
        "enabled": True,
        "label_override": "",
        "notes": "",
        "decision_scopes": app_sections,
        "document_type_override": "",
        "extraction_targets": extraction_targets,
        "app_sections": app_sections,
        "transformation_note": "",
        "processing_order": processing_order,
        "updated_at_utc": _now(),
    }
    con.execute(
        """
        INSERT OR IGNORE INTO context_board_nodes(
            node_id, node_type, x, y, context_level, weight, enabled, label_override, notes,
            decision_scopes_json, updated_at_utc, document_type_override, extraction_targets_json,
            app_sections_json, transformation_note, processing_order
        ) VALUES (?, ?, ?, ?, 'medium', 0.58, 1, '', '', ?, ?, '', ?, ?, '', ?)
        """,
        (node_id, node_type, x, y, json.dumps(app_sections), payload["updated_at_utc"], json.dumps(extraction_targets), json.dumps(app_sections), processing_order),
    )
    current[node_id] = payload
    return payload


def _ensure_process(con: sqlite3.Connection, current: dict[str, dict[str, Any]], process_id: str, x: float, y: float) -> dict[str, Any]:
    existing = current.get(process_id)
    if existing:
        return existing
    definition = PROCESS_DEFINITIONS[process_id]
    payload = {
        "process_id": process_id,
        "enabled": True,
        "label_override": "",
        "description_override": "",
        "app_sections": list(definition["sections"]),
        "agent_ids": [agent_id for agent_id, agent in DEPARTMENT_AGENTS.items() if process_id in agent["processes"]],
        "notes": "",
        "x": x,
        "y": y,
        "updated_at_utc": _now(),
    }
    con.execute(
        "INSERT OR IGNORE INTO context_board_processes(process_id, enabled, label_override, description_override, app_sections_json, agent_ids_json, notes, x, y, updated_at_utc) VALUES (?, 1, '', '', ?, ?, '', ?, ?, ?)",
        (process_id, json.dumps(definition["sections"]), json.dumps(payload["agent_ids"]), x, y, payload["updated_at_utc"]),
    )
    current[process_id] = payload
    return payload


def _fallback_temporal(error: Exception | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    zone, timezone_label, timezone_warning = resolve_timezone(settings.app_timezone)
    warnings = [item for item in (timezone_warning, f"{type(error).__name__}: {error}" if error else "") if item]
    return {
        "current_time_local": now.astimezone(zone).isoformat(timespec="seconds"),
        "timezone": timezone_label,
        "data_cutoff_local": "",
        "last_analysis": {},
        "sources": [],
        "context_warning": " | ".join(warnings),
    }


def _candidate_source_roots() -> list[tuple[Path, str]]:
    """Return every supported local source library, even when an old .env overrides folder intake.

    Earlier builds allowed ``FOLDER_INTAKE_DIR=./file_drop`` while the packaged
    Banksia dataset lives in ``data/source_files``.  The lineage map must not
    silently become empty because of that setting.  We therefore discover from
    the configured intake root, the packaged data library and the legacy
    ``file_drop`` root, then deduplicate them by resolved path.
    """
    candidates = [
        (settings.folder_intake_path, "configured intake"),
        (settings.data_path / "source_files", "data source library"),
        (settings.root_dir / "file_drop", "legacy file drop"),
    ]
    result: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for root, label in candidates:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append((root, label))
    return result


def _staged_source_files() -> list[dict[str, Any]]:
    result_by_fingerprint: dict[str, dict[str, Any]] = {}

    def add_path(
        path: Path,
        *,
        library_root: Path,
        route_root: Path,
        intake_category: str,
        status: str,
        library_label: str,
    ) -> None:
        if not path.is_file() or path.suffix.lower() not in _SOURCE_EXTENSIONS or path.name.startswith((".", "~$")):
            return
        try:
            stat = path.stat()
        except OSError:
            return
        visible_name = path.name.split("__", 1)[-1] if "__" in path.name else path.name
        # A file can exist in both a packaged library and a legacy drop folder.
        # Filename + size is stable after an intake move and avoids duplicate nodes.
        fingerprint = f"{visible_name.strip().lower()}|{int(stat.st_size)}"
        try:
            relative = path.relative_to(library_root).as_posix()
        except ValueError:
            relative = path.name
        digest = hashlib.sha1(f"{library_label}|{relative}|{stat.st_size}".encode("utf-8")).hexdigest()[:18]
        document_type = folder_declared_document_type(path, route_root) or strong_filename_document_hint(visible_name) or "generic"
        # Archived names may contain timestamps; parent folders remain the most
        # reliable routing hint.
        for part in reversed(path.parts[:-1]):
            candidate = str(part).strip().lower()
            if candidate in DOCUMENT_PIPELINE_DEFAULTS:
                document_type = candidate
                break
        modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")
        payload = {
            "id": 0,
            "source_key": f"file:{digest}",
            "filename": visible_name,
            "file_path": str(path),
            "relative_path": relative,
            "source_library": library_label,
            "document_type": document_type,
            "document_label": document_type.replace("_", " ").title(),
            "intake_category": intake_category,
            "tier": "archived" if status in {"archived_source", "processed_source"} else "staged",
            "processing_status": status,
            "display_status": {
                "archived_source": "archived after intake",
                "processed_source": "preserved processed source",
            }.get(status, "staged in data"),
            "rows_imported": 0,
            "data_version": 0,
            "created_at": modified,
            "last_processed_at": "",
            "assistant_message": (
                "Source is preserved after processing and remains visible in Data Management lineage."
                if status in {"archived_source", "processed_source"}
                else f"Present in {library_label} and available for deterministic import."
            ),
            "analysis": {"findings": [f"Source discovered from {library_label} and visible in Data Management lineage."]},
        }
        existing = result_by_fingerprint.get(fingerprint)
        # Prefer a currently staged source over an archived/raw fallback.
        rank = {"staged_source": 3, "archived_source": 2, "processed_source": 1}
        if not existing or rank.get(status, 0) > rank.get(str(existing.get("processing_status") or ""), 0):
            result_by_fingerprint[fingerprint] = payload

    for root, library_label in _candidate_source_roots():
        scan_roots: list[tuple[Path, Path, str, str]] = [
            (root / "permanent", root / "permanent", "setup", "staged_source"),
            (root / "recurring", root / "recurring", "recurring", "staged_source"),
            (root / "archive" / "setup", root / "permanent", "setup", "archived_source"),
            (root / "archive" / "permanent", root / "permanent", "setup", "archived_source"),
            (root / "archive" / "recurring", root / "recurring", "recurring", "archived_source"),
        ]
        for category_root, route_root, intake_category, status in scan_roots:
            if not category_root.exists():
                continue
            for path in sorted(category_root.rglob("*")):
                add_path(
                    path,
                    library_root=root,
                    route_root=route_root,
                    intake_category=intake_category,
                    status=status,
                    library_label=library_label,
                )

    # Last-resort visibility for files that have already moved through ingestion
    # but whose SQLite upload record is missing or was reset.
    raw_root = settings.data_path / "raw"
    if raw_root.exists():
        for path in sorted(raw_root.rglob("*")):
            hint = strong_filename_document_hint(path.name) or "generic"
            intake_category = "setup" if hint in {
                "balance_sheet", "profit_loss", "cash_flow_statement", "chart_of_accounts",
                "business_requirements", "fixed_asset_register", "aged_debtors_creditors",
                "material_contracts", "sales_forecast", "personnel_plan",
                "use_cases_user_stories", "historical_tax_returns", "market_context",
            } else "recurring"
            add_path(
                path,
                library_root=settings.data_path,
                route_root=raw_root,
                intake_category=intake_category,
                status="processed_source",
                library_label="processed raw evidence",
            )

    return sorted(
        result_by_fingerprint.values(),
        key=lambda item: (0 if item.get("intake_category") == "setup" else 1, str(item.get("filename") or "").lower()),
    )


def _source_discovery_status() -> list[dict[str, Any]]:
    status: list[dict[str, Any]] = []
    for root, label in _candidate_source_roots():
        count = 0
        if root.exists():
            try:
                count = sum(
                    1
                    for path in root.rglob("*")
                    if path.is_file()
                    and path.suffix.lower() in _SOURCE_EXTENSIONS
                    and not path.name.startswith((".", "~$"))
                )
            except OSError:
                count = 0
        status.append({"label": label, "path": str(root), "exists": root.exists(), "supported_file_count": count})
    raw_root = settings.data_path / "raw"
    raw_count = 0
    if raw_root.exists():
        try:
            raw_count = sum(1 for path in raw_root.rglob("*") if path.is_file() and path.suffix.lower() in _SOURCE_EXTENSIONS)
        except OSError:
            raw_count = 0
    status.append({"label": "processed raw evidence", "path": str(raw_root), "exists": raw_root.exists(), "supported_file_count": raw_count})
    return status


def _preview_text(path: Path, kind: str) -> str:
    if not path.exists():
        return "This context file will be created when first used."
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Unable to preview: {type(exc).__name__}: {exc}"
    if kind == "json":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                keys = ", ".join(list(data.keys())[:8])
                return f"JSON context with keys: {keys or 'none'}"
        except Exception:
            pass
    compact = " ".join(text.split())
    return compact[:260] + ("…" if len(compact) > 260 else "")


def context_board_dashboard(*, refresh_sources: bool = True) -> dict[str, Any]:
    with _BOARD_LOCK:
        initialise_context_board()
        try:
            temporal = decision_context_dashboard(refresh=refresh_sources)
        except Exception as exc:
            temporal = _fallback_temporal(exc)
        try:
            library = upload_library()
        except Exception:
            library = {"files": {"setup": [], "recurring": []}}

        temporal_sources = {str(item.get("source_key")): item for item in temporal.get("sources") or []}
        files = list((library.get("files") or {}).get("setup") or []) + list((library.get("files") or {}).get("recurring") or [])
        represented = {str(item.get("filename") or "").strip().lower() for item in files}
        files.extend(item for item in _staged_source_files() if str(item.get("filename") or "").strip().lower() not in represented)

        con = _connect()
        stored = _row_settings(con)
        process_stored = _process_settings(con)
        settings_payload = _settings(con)

        source_nodes: list[dict[str, Any]] = []
        for index, item in enumerate(files):
            upload_id = int(item.get("id") or 0)
            node_id = str(item.get("source_key") or (f"upload:{upload_id}" if upload_id else f"file:{index}"))
            source_temporal = temporal_sources.get(node_id, {})
            raw_document_type = str(item.get("document_type") or "generic")
            defaults = _pipeline_defaults(raw_document_type)
            x, y = _source_position(index, len(files))
            board = _ensure_source_or_context(
                con,
                stored,
                node_id=node_id,
                node_type="source",
                x=x,
                y=y,
                app_sections=list(defaults["sections"]),
                extraction_targets=list(defaults["processes"]),
                processing_order=(index + 1) * 10,
            )
            document_type = str(board.get("document_type_override") or raw_document_type or "generic")
            selected_defaults = _pipeline_defaults(document_type)
            extraction_targets = _valid_processes(board.get("extraction_targets"), selected_defaults["processes"])
            app_sections = _valid_sections(board.get("app_sections") or board.get("decision_scopes"), selected_defaults["sections"])
            analysis = item.get("analysis") if isinstance(item.get("analysis"), dict) else {}
            findings = analysis.get("findings") if isinstance(analysis, dict) else []
            source_nodes.append(
                {
                    "id": node_id,
                    "upload_id": upload_id,
                    "node_type": "source",
                    "label": board.get("label_override") or item.get("filename") or node_id,
                    "filename": item.get("filename") or node_id,
                    "file_path": item.get("file_path") or "",
                    "relative_path": item.get("relative_path") or "",
                    "document_type": document_type,
                    "detected_document_type": raw_document_type,
                    "document_label": item.get("document_label") or document_type.replace("_", " ").title(),
                    "intake_category": item.get("intake_category") or "recurring",
                    "tier": item.get("tier") or "",
                    "processing_status": item.get("display_status") or item.get("processing_status") or "unknown",
                    "rows_imported": int(item.get("rows_imported") or 0),
                    "data_version": int(item.get("data_version") or 0),
                    "created_at": item.get("created_at") or "",
                    "processed_at": item.get("last_processed_at") or source_temporal.get("processed_at_local") or source_temporal.get("processed_at_utc") or "",
                    "effective_date": source_temporal.get("effective_date") or "",
                    "freshness_state": source_temporal.get("freshness_state") or ("reference" if item.get("intake_category") == "setup" else "watch"),
                    "preview": item.get("assistant_message") or ((findings or [""])[0] if isinstance(findings, list) else "") or f"{int(item.get('rows_imported') or 0)} imported row(s).",
                    "x": float(board.get("x") if board.get("x") is not None else x),
                    "y": float(board.get("y") if board.get("y") is not None else y),
                    "enabled": bool(board.get("enabled", True)),
                    "notes": str(board.get("notes") or ""),
                    "transformation_note": str(board.get("transformation_note") or ""),
                    "processing_order": int(board.get("processing_order") or (index + 1) * 10),
                    "extraction_targets": extraction_targets,
                    "app_sections": app_sections,
                    "updated_at": board.get("updated_at_utc") or "",
                }
            )

        used_process_ids = sorted({process_id for source in source_nodes for process_id in source["extraction_targets"]})
        process_nodes: list[dict[str, Any]] = []
        for index, process_id in enumerate(used_process_ids):
            definition = PROCESS_DEFINITIONS[process_id]
            x, y = _process_position(index, len(used_process_ids))
            board = _ensure_process(con, process_stored, process_id, x, y)
            input_sources = [source["id"] for source in source_nodes if process_id in source["extraction_targets"]]
            source_sections = sorted({section for source in source_nodes if process_id in source["extraction_targets"] for section in source["app_sections"]})
            sections = _valid_sections(board.get("app_sections"), source_sections or list(definition["sections"]))
            process_nodes.append(
                {
                    "id": f"process:{process_id}",
                    "process_id": process_id,
                    "node_type": "process",
                    "label": board.get("label_override") or definition["label"],
                    "description": board.get("description_override") or definition["description"],
                    "enabled": bool(board.get("enabled", True)),
                    "notes": str(board.get("notes") or ""),
                    "app_sections": sections,
                    "agent_ids": [agent_id for agent_id in (board.get("agent_ids") or []) if agent_id in DEPARTMENT_AGENTS] or [agent_id for agent_id, agent in DEPARTMENT_AGENTS.items() if process_id in agent["processes"]],
                    "input_source_ids": input_sources,
                    "input_count": len(input_sources),
                    "x": float(board.get("x") if board.get("x") is not None else x),
                    "y": float(board.get("y") if board.get("y") is not None else y),
                    "updated_at": board.get("updated_at_utc") or "",
                }
            )

        try:
            analysis_contexts = refresh_analysis_context_files(
                source_nodes=source_nodes,
                process_nodes=process_nodes,
                temporal=temporal,
                app_sections=APP_SECTIONS,
            )
        except Exception as exc:
            analysis_contexts = {"warning": f"{type(exc).__name__}: {exc}"}

        context_nodes: list[dict[str, Any]] = []
        layers = _context_layers()
        graph_layer_ids = [
            node_id for node_id, definition in layers.items()
            if str(definition.get("graph_visibility") or "zoom") != "list_only"
        ]
        graph_index = {node_id: index for index, node_id in enumerate(graph_layer_ids)}
        for index, (node_id, definition) in enumerate(layers.items()):
            visible_index = graph_index.get(node_id, 0)
            x, y = _context_position(visible_index, max(1, len(graph_layer_ids)))
            default_sections = _CONTEXT_SECTIONS.get(node_id, list(APP_SECTIONS))
            board = _ensure_source_or_context(
                con,
                stored,
                node_id=node_id,
                node_type="context",
                x=x,
                y=y,
                app_sections=default_sections,
                extraction_targets=[],
                processing_order=index,
            )
            path = Path(definition["path"])
            context_nodes.append(
                {
                    "id": node_id,
                    "node_type": "context",
                    "label": board.get("label_override") or definition["label"],
                    "kind": definition["kind"],
                    "file_path": str(path),
                    "description": definition["description"],
                    "protected": bool(definition["protected"]),
                    "locked_enabled": bool(definition.get("locked_enabled", False)),
                    "graph_visibility": str(definition.get("graph_visibility") or "zoom"),
                    "list_group": str(definition.get("list_group") or "AI context"),
                    "present": path.exists(),
                    "preview": _preview_text(path, str(definition["kind"])),
                    "x": float(board.get("x") if board.get("x") is not None else x),
                    "y": float(board.get("y") if board.get("y") is not None else y),
                    "enabled": True if definition.get("locked_enabled") else bool(board.get("enabled", True)),
                    "notes": str(board.get("notes") or ""),
                    "app_sections": _valid_sections(board.get("app_sections") or board.get("decision_scopes"), default_sections),
                    "updated_at": board.get("updated_at_utc") or "",
                }
            )

        con.commit()
        settings_payload = _settings(con)
        events = [dict(row) for row in con.execute("SELECT occurred_at_utc, event_type, node_id, detail FROM context_board_events ORDER BY id DESC LIMIT 20")]
        con.close()

        process_map = {node["process_id"]: node for node in process_nodes}
        active_lens = str(settings_payload.get("active_lens") or "all")

        section_nodes: list[dict[str, Any]] = []
        for section_id, definition in APP_SECTIONS.items():
            process_ids = [node["process_id"] for node in process_nodes if node["enabled"] and section_id in node["app_sections"]]
            source_ids = [
                source["id"]
                for source in source_nodes
                if source["enabled"]
                and section_id in source["app_sections"]
                and any(process_id in process_ids for process_id in source["extraction_targets"])
            ]
            context_ids = [node["id"] for node in context_nodes if node["enabled"] and section_id in node["app_sections"]]
            section_nodes.append(
                {
                    "id": f"section:{section_id}",
                    "section_id": section_id,
                    "node_type": "section",
                    "label": definition["label"],
                    "description": definition["description"],
                    "x": definition["x"],
                    "y": definition["y"],
                    "source_ids": source_ids,
                    "process_ids": process_ids,
                    "context_ids": context_ids,
                    "source_count": len(source_ids),
                    "process_count": len(process_ids),
                    "context_count": len(context_ids),
                }
            )

        # LangGraph department agents sit between extracted products and the
        # executive supervisor. Superset dashboard nodes expose each agent's
        # published visual-analytics surface without replacing source lineage.
        agent_nodes: list[dict[str, Any]] = []
        for agent_id, definition in DEPARTMENT_AGENTS.items():
            process_ids = [
                node["process_id"] for node in process_nodes
                if node["enabled"] and agent_id in (node.get("agent_ids") or [])
            ]
            source_ids = [
                source["id"] for source in source_nodes
                if source["enabled"]
                and bool(set(source["extraction_targets"]).intersection(definition["processes"]))
            ]
            context_ids = [
                node["id"] for node in context_nodes
                if node["enabled"] and bool(set(node["app_sections"]).intersection(definition["workspaces"]))
            ]
            agent_nodes.append({
                "id": f"agent:{agent_id}",
                "agent_id": agent_id,
                "node_type": "agent",
                "label": definition["label"],
                "department": definition["department"],
                "description": definition["purpose"],
                "workspaces": list(definition["workspaces"]),
                "process_ids": process_ids,
                "source_ids": source_ids,
                "context_ids": context_ids,
                "source_count": len(source_ids),
                "process_count": len(process_ids),
                "context_count": len(context_ids),
                "colour": definition["colour"],
                "x": definition["x"],
                "y": definition["y"],
                "enabled": True,
            })

        dashboards_by_id = {item["dashboard_id"]: item for item in dashboard_catalogue()}
        dashboard_nodes: list[dict[str, Any]] = []
        for agent in agent_nodes:
            dashboard = dashboards_by_id.get(agent["agent_id"]) or {}
            # Place the dashboard between its agent and the centre supervisor.
            x = (float(agent["x"]) + 0.5) / 2
            y = (float(agent["y"]) + 0.5) / 2
            dashboard_nodes.append({
                **dashboard,
                "id": f"dashboard:{agent['agent_id']}",
                "node_type": "dashboard",
                "agent_id": agent["agent_id"],
                "x": x,
                "y": y,
                "enabled": True,
            })

        def source_active(source: dict[str, Any]) -> bool:
            return bool(source["enabled"] and (active_lens == "all" or active_lens in source["app_sections"]))

        def process_active(process: dict[str, Any]) -> bool:
            return bool(process["enabled"] and (active_lens == "all" or active_lens in process["app_sections"]))

        edges: list[dict[str, Any]] = []
        for source in source_nodes:
            for process_id in source["extraction_targets"]:
                process = process_map.get(process_id)
                if not process:
                    continue
                edges.append(
                    {
                        "id": f"edge:{source['id']}:{process_id}",
                        "edge_type": "extract",
                        "source": source["id"],
                        "target": f"process:{process_id}",
                        "enabled": bool(source["enabled"] and process["enabled"]),
                        "active": bool(source_active(source) and process_active(process)),
                        "label": f"Extract → {process['label']}",
                        "stage": "Source to normalised data",
                        "detail": source.get("transformation_note") or process.get("description") or "Extract, normalise and validate the configured fields.",
                        "business_effect": f"Creates {process['label']} evidence from {source['label']}.",
                    }
                )
        for process in process_nodes:
            for section_id in process["app_sections"]:
                edges.append(
                    {
                        "id": f"edge:process:{process['process_id']}:{section_id}",
                        "edge_type": "consume",
                        "source": process["id"],
                        "target": f"section:{section_id}",
                        "enabled": bool(process["enabled"]),
                        "active": bool(process_active(process) and (active_lens == "all" or active_lens == section_id)),
                        "label": f"Publish → {APP_SECTIONS[section_id]['label']}",
                        "stage": "Normalised data to app section",
                        "detail": process.get("description") or "Publish the validated data product to the selected app section.",
                        "business_effect": f"Allows {APP_SECTIONS[section_id]['label']} to use {process['label']}.",
                    }
                )
        for context in context_nodes:
            for section_id in context["app_sections"]:
                edges.append(
                    {
                        "id": f"edge:{context['id']}:{section_id}",
                        "edge_type": "context",
                        "source": context["id"],
                        "target": f"section:{section_id}",
                        "enabled": bool(context["enabled"]),
                        "active": bool(context["enabled"] and (active_lens == "all" or active_lens == section_id)),
                        "label": f"Context → {APP_SECTIONS[section_id]['label']}",
                        "stage": "AI context supplied to section",
                        "detail": context.get("description") or "Supply instructions and contextual evidence to the app section.",
                        "business_effect": f"Adds {context['label']} to {APP_SECTIONS[section_id]['label']} reasoning.",
                    }
                )
        for section in section_nodes:
            edges.append(
                {
                    "id": f"edge:{section['id']}:ai",
                    "edge_type": "decision",
                    "source": section["id"],
                    "target": "ai:ledger",
                    "enabled": True,
                    "active": active_lens == "all" or active_lens == section["section_id"],
                    "label": f"Decide with {section['label']}",
                    "stage": "App section to Ledger AI",
                    "detail": f"Ledger AI receives the verified {section['label']} evidence, section instructions and connected context files.",
                    "business_effect": f"Supports business-analyst decisions for {section['label']}.",
                }
            )

        # Replace direct section-to-AI wiring with the LangGraph and Superset
        # architecture: source -> extraction -> department agent -> dashboard /
        # supervisor. Context files supply the relevant agents directly.
        edges = [edge for edge in edges if edge.get("edge_type") == "extract"]
        agent_map = {node["agent_id"]: node for node in agent_nodes}
        for process in process_nodes:
            for agent_id, agent in agent_map.items():
                if agent_id not in (process.get("agent_ids") or []):
                    continue
                edges.append({
                    "id": f"edge:{process['id']}:agent:{agent_id}",
                    "edge_type": "agent_input",
                    "source": process["id"],
                    "target": f"agent:{agent_id}",
                    "enabled": bool(process["enabled"]),
                    "active": bool(process_active(process)),
                    "label": f"Analyse with {agent['label']}",
                    "stage": "Validated product to department agent",
                    "detail": f"{agent['label']} receives {process['label']} under its department prompt and source permissions.",
                    "business_effect": f"Makes {process['label']} available to {agent['department']} reasoning.",
                })
        for context in context_nodes:
            for agent_id, agent in agent_map.items():
                if not set(context["app_sections"]).intersection(agent["workspaces"]):
                    continue
                edges.append({
                    "id": f"edge:{context['id']}:agent:{agent_id}",
                    "edge_type": "agent_context",
                    "source": context["id"],
                    "target": f"agent:{agent_id}",
                    "enabled": bool(context["enabled"]),
                    "active": bool(context["enabled"]),
                    "label": f"Instructions → {agent['label']}",
                    "stage": "Context engineering",
                    "detail": context.get("description") or "Supply governed context to the department agent.",
                    "business_effect": f"Controls how {agent['label']} interprets connected evidence.",
                })
        for agent in agent_nodes:
            edges.extend([
                {
                    "id": f"edge:agent:{agent['agent_id']}:dashboard",
                    "edge_type": "publish_dashboard",
                    "source": f"agent:{agent['agent_id']}",
                    "target": f"dashboard:{agent['agent_id']}",
                    "enabled": True,
                    "active": True,
                    "label": "Publish visual analytics",
                    "stage": "Department output to Apache Superset",
                    "detail": f"{agent['label']} publishes governed metrics and records to its Superset dataset and dashboard.",
                    "business_effect": f"Creates an inspectable visual analytics surface for {agent['department']}.",
                },
                {
                    "id": f"edge:agent:{agent['agent_id']}:supervisor",
                    "edge_type": "agent_decision",
                    "source": f"agent:{agent['agent_id']}",
                    "target": "supervisor:ledger",
                    "enabled": True,
                    "active": True,
                    "label": "Return department finding",
                    "stage": "LangGraph agent to supervisor",
                    "detail": f"The {agent['label']} returns evidence, finding, recommendation, impact, timing and uncertainty.",
                    "business_effect": "Allows the supervisor to reconcile cross-department findings into one decision.",
                },
                {
                    "id": f"edge:dashboard:{agent['agent_id']}:supervisor",
                    "edge_type": "dashboard_evidence",
                    "source": f"dashboard:{agent['agent_id']}",
                    "target": "supervisor:ledger",
                    "enabled": True,
                    "active": True,
                    "label": "Visual evidence",
                    "stage": "Superset dashboard to decision review",
                    "detail": "The embedded dashboard provides a human-reviewable visual evidence surface; it does not create unsupported facts.",
                    "business_effect": "Supports review and explanation of the final decision.",
                },
            ])

        lenses = [
            {
                "id": "all",
                "label": "All sections",
                "description": "Show the complete source-to-app lineage.",
                "readiness": "configured",
                "source_count": len([source for source in source_nodes if source["enabled"]]),
            }
        ]
        for section in section_nodes:
            lenses.append(
                {
                    "id": section["section_id"],
                    "label": section["label"],
                    "description": section["description"],
                    "readiness": "connected" if section["source_count"] else "awaiting_sources",
                    "source_count": section["source_count"],
                }
            )

        active_sources = [source for source in source_nodes if source_active(source)]
        active_processes = [process for process in process_nodes if process_active(process)]
        active_contexts = [context for context in context_nodes if context["enabled"] and (active_lens == "all" or active_lens in context["app_sections"])]
        return {
            "version": 5,
            "board_name": "LangGraph Agent and Superset Data Map",
            "current_time_local": temporal.get("current_time_local"),
            "timezone": temporal.get("timezone"),
            "data_cutoff_local": temporal.get("data_cutoff_local"),
            "last_analysis": temporal.get("last_analysis") or {},
            "settings": settings_payload,
            "ai_node": {
                "id": "supervisor:ledger",
                "label": "Ledger Supervisor",
                "x": 0.5,
                "y": 0.5,
                "active_lens": active_lens,
                "included_node_count": len(active_sources) + len(active_contexts),
                "source_count": len(source_nodes),
                "context_count": len(context_nodes),
            },
            "source_nodes": source_nodes,
            "process_nodes": process_nodes,
            "section_nodes": section_nodes,
            "agent_nodes": agent_nodes,
            "dashboard_nodes": dashboard_nodes,
            "context_nodes": context_nodes,
            "context_inventory": context_nodes,
            "analysis_context_files": {
                "business_analyst_context": str(business_analyst_context_path()),
                "market_analysis_template": str(market_analysis_template_path()),
                "market_analysis_context": str(market_analysis_context_path()),
                "market_report": str(market_intelligence_path()),
            },
            "edges": edges,
            "decision_lenses": lenses,
            "app_sections": [{"id": key, **value} for key, value in APP_SECTIONS.items()],
            "process_catalogue": [{"id": key, **value} for key, value in PROCESS_DEFINITIONS.items()],
            "document_types": sorted(DOCUMENT_PIPELINE_DEFAULTS),
            "events": events,
            "source_discovery": _source_discovery_status(),
            "summary": {
                "source_count": len(source_nodes),
                "process_count": len(process_nodes),
                "section_count": len(section_nodes),
                "agent_count": len(agent_nodes),
                "dashboard_count": len(dashboard_nodes),
                "context_count": len(context_nodes),
                "included_count": len([source for source in source_nodes if source["enabled"]]),
                "excluded_count": len([source for source in source_nodes if not source["enabled"]]),
                "active_source_count": len(active_sources),
                "active_process_count": len(active_processes),
                "active_context_count": len(active_contexts),
            },
            "interaction_note": "Every source flows through extraction into one or more LangGraph department agents. Agents publish governed datasets to Apache Superset and return structured findings to Ledger Supervisor. Context files remain editable and control what each agent may see.",
            "context_warning": temporal.get("context_warning") or str(analysis_contexts.get("warning") or ""),
        }


def update_context_board_node(node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with _BOARD_LOCK:
        dashboard = context_board_dashboard(refresh_sources=False)
        source_nodes = {item["id"]: item for item in dashboard["source_nodes"]}
        context_nodes = {item["id"]: item for item in dashboard["context_nodes"]}
        process_nodes = {item["id"]: item for item in dashboard["process_nodes"]}
        con = _connect()

        if node_id in process_nodes:
            process = process_nodes[node_id]
            process_id = str(process["process_id"])
            label = str(payload.get("label", process.get("label") or "")).strip()[:180]
            description = str(payload.get("description", process.get("description") or "")).strip()[:1200]
            enabled = bool(payload.get("enabled", process.get("enabled", True)))
            notes = str(payload.get("notes", process.get("notes") or ""))[:4000]
            sections = _valid_sections(payload.get("app_sections"), list(process.get("app_sections") or PROCESS_DEFINITIONS[process_id]["sections"]))
            agent_ids = [str(item) for item in (payload.get("agent_ids") or process.get("agent_ids") or []) if str(item) in DEPARTMENT_AGENTS]
            if not agent_ids:
                agent_ids = [agent_id for agent_id, definition in DEPARTMENT_AGENTS.items() if process_id in definition["processes"]]
            x = min(0.96, max(0.04, float(payload.get("x", process.get("x", 0.5)))))
            y = min(0.94, max(0.06, float(payload.get("y", process.get("y", 0.5)))))
            con.execute(
                "UPDATE context_board_processes SET enabled=?, label_override=?, description_override=?, app_sections_json=?, agent_ids_json=?, notes=?, x=?, y=?, updated_at_utc=? WHERE process_id=?",
                (int(enabled), label, description, json.dumps(sections), json.dumps(agent_ids), notes, x, y, _now(), process_id),
            )
            detail = f"Processing product {process_id} updated"
        elif node_id in source_nodes or node_id in context_nodes:
            node = source_nodes.get(node_id) or context_nodes.get(node_id) or {}
            node_type = str(node.get("node_type") or "source")
            label = str(payload.get("label", node.get("label") or "")).strip()[:180]
            notes = str(payload.get("notes", node.get("notes") or ""))[:4000]
            x = min(0.96, max(0.04, float(payload.get("x", node.get("x", 0.5)))))
            y = min(0.94, max(0.06, float(payload.get("y", node.get("y", 0.5)))))
            enabled = bool(payload.get("enabled", node.get("enabled", True)))
            if node_type == "context" and node.get("locked_enabled"):
                enabled = True
            default_sections = list(node.get("app_sections") or APP_SECTIONS)
            sections = _valid_sections(payload.get("app_sections"), default_sections)
            document_type = str(payload.get("document_type", node.get("document_type") or "")).strip()
            if node_type == "source" and document_type not in DOCUMENT_PIPELINE_DEFAULTS:
                document_type = "generic"
            default_processes = _pipeline_defaults(document_type or "generic")["processes"] if node_type == "source" else []
            processes = _valid_processes(payload.get("extraction_targets"), list(node.get("extraction_targets") or default_processes)) if node_type == "source" else []
            transformation_note = str(payload.get("transformation_note", node.get("transformation_note") or ""))[:4000]
            try:
                processing_order = max(0, min(9999, int(payload.get("processing_order", node.get("processing_order") or 100))))
            except Exception:
                processing_order = int(node.get("processing_order") or 100)
            con.execute(
                """
                UPDATE context_board_nodes
                SET x=?, y=?, enabled=?, label_override=?, notes=?, decision_scopes_json=?, app_sections_json=?,
                    document_type_override=?, extraction_targets_json=?, transformation_note=?, processing_order=?, updated_at_utc=?
                WHERE node_id=?
                """,
                (x, y, int(enabled), label, notes, json.dumps(sections), json.dumps(sections), document_type if node_type == "source" else "", json.dumps(processes), transformation_note, processing_order, _now(), node_id),
            )
            detail = f"{node_type.title()} lineage updated"
        else:
            con.close()
            raise KeyError(f"Unknown data-lineage node: {node_id}")

        con.execute(
            "INSERT INTO context_board_events(occurred_at_utc, event_type, node_id, detail, payload_json) VALUES (?, 'lineage_updated', ?, ?, ?)",
            (_now(), node_id, detail, json.dumps(payload, ensure_ascii=False, default=str)),
        )
        con.commit()
        con.close()
        return context_board_dashboard(refresh_sources=False)


def update_context_board_settings(payload: dict[str, Any]) -> dict[str, Any]:
    with _BOARD_LOCK:
        initialise_context_board()
        con = _connect()
        if "active_lens" in payload:
            lens = str(payload.get("active_lens") or "all")
            if lens not in _VALID_LENSES:
                raise ValueError(f"Invalid app-section filter: {lens}")
            _save_setting(con, "active_lens", lens)
        if "show_excluded" in payload:
            _save_setting(con, "show_excluded", bool(payload.get("show_excluded")))
        if "auto_story" in payload:
            _save_setting(con, "auto_story", bool(payload.get("auto_story")))
        con.execute(
            "INSERT INTO context_board_events(occurred_at_utc, event_type, detail, payload_json) VALUES (?, 'settings_updated', 'Lineage view settings changed', ?)",
            (_now(), json.dumps(payload)),
        )
        con.commit()
        con.close()
        return context_board_dashboard(refresh_sources=False)


def reset_context_board_layout() -> dict[str, Any]:
    with _BOARD_LOCK:
        initialise_context_board()
        con = _connect()
        con.execute("DELETE FROM context_board_nodes")
        con.execute("DELETE FROM context_board_processes")
        con.execute(
            "INSERT INTO context_board_events(occurred_at_utc, event_type, detail) VALUES (?, 'layout_reset', 'Editable lineage layout and mappings returned to defaults')",
            (_now(),),
        )
        con.commit()
        con.close()
        return context_board_dashboard(refresh_sources=False)


def context_file_content(node_id: str) -> dict[str, Any]:
    definition = _context_layers().get(node_id)
    if not definition:
        raise KeyError(f"Unknown context file: {node_id}")
    path = Path(definition["path"])
    content = path.read_text(encoding="utf-8") if path.exists() else ("{}\n" if definition["kind"] == "json" else "")
    return {
        "node_id": node_id,
        "label": definition["label"],
        "kind": definition["kind"],
        "path": str(path),
        "protected": bool(definition["protected"]),
        "content": content,
        "exists": path.exists(),
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds") if path.exists() else "",
    }


def save_context_file(node_id: str, content: str, *, confirmed: bool = False) -> dict[str, Any]:
    definition = _context_layers().get(node_id)
    if not definition:
        raise KeyError(f"Unknown context file: {node_id}")
    if definition["protected"] and not confirmed:
        raise PermissionError("This protected context requires explicit confirmation before saving.")
    if len(content.encode("utf-8")) > 2_000_000:
        raise ValueError("Context file exceeds the 2 MB safety limit.")
    path = Path(definition["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if definition["kind"] == "json":
        parsed = json.loads(content or "{}")
        content = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        backup_dir = settings.data_path / "backups" / "context_board"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, backup_dir / f"{stamp}__{path.name}")
    path.write_text(content, encoding="utf-8")
    con = _connect()
    con.execute(
        "INSERT INTO context_board_events(occurred_at_utc, event_type, node_id, detail, payload_json) VALUES (?, 'context_file_saved', ?, ?, ?)",
        (_now(), node_id, f"Saved {path.name}", json.dumps({"path": str(path), "characters": len(content)})),
    )
    con.commit()
    con.close()
    return context_file_content(node_id)


def _lineage_for_source(dashboard: dict[str, Any], source: dict[str, Any]) -> tuple[list[str], list[str]]:
    process_map = {item["process_id"]: item for item in dashboard.get("process_nodes") or []}
    processes = [process_map[item]["label"] for item in source.get("extraction_targets") or [] if item in process_map]
    sections = [APP_SECTIONS[item]["label"] for item in source.get("app_sections") or [] if item in APP_SECTIONS]
    return processes, sections


def explain_context_board(node_id: str = "", lens: str = "") -> dict[str, Any]:
    dashboard = context_board_dashboard(refresh_sources=False)
    active_lens = lens if lens in _VALID_LENSES else str(dashboard.get("settings", {}).get("active_lens") or "all")
    all_nodes = dashboard["source_nodes"] + dashboard["process_nodes"] + dashboard["section_nodes"] + dashboard["context_nodes"]
    node = next((item for item in all_nodes if item["id"] == node_id), None)
    if node and node.get("node_type") == "source":
        processes, sections = _lineage_for_source(dashboard, node)
        status = "included" if node.get("enabled") else "excluded"
        message = (
            f"{node['label']} is {status}. LedgerFlow classifies it as {str(node.get('document_type') or 'generic').replace('_', ' ')}; "
            f"it is processed through {', '.join(processes) or 'no configured extraction product'} and supplies {', '.join(sections) or 'no app section'}. "
            f"Its processing order is {int(node.get('processing_order') or 0)}. Edit the selected source to change its type, extraction products, app destinations or inclusion state."
        )
    elif node and node.get("node_type") == "process":
        sections = [APP_SECTIONS[item]["label"] for item in node.get("app_sections") or [] if item in APP_SECTIONS]
        message = (
            f"{node['label']} receives {int(node.get('input_count') or 0)} source file(s), performs the displayed normalisation and validation step, "
            f"and supplies {', '.join(sections) or 'no app section'}. The process can be enabled, renamed, described and rerouted from the inspector."
        )
    elif node and node.get("node_type") == "section":
        message = (
            f"{node['label']} receives {int(node.get('source_count') or 0)} source file(s) through {int(node.get('process_count') or 0)} processing product(s), "
            f"plus {int(node.get('context_count') or 0)} context layer(s), before its evidence is made available to Ledger AI."
        )
    elif node and node.get("node_type") == "context":
        sections = [APP_SECTIONS[item]["label"] for item in node.get("app_sections") or [] if item in APP_SECTIONS]
        message = (
            f"{node['label']} is an editable AI context layer used by {', '.join(sections) or 'no app section'}. "
            f"The file is {'present' if node.get('present') else 'not created yet'} at {node.get('file_path')}. Its content and section connections can be edited from the inspector."
        )
    elif node and node.get("node_type") == "ai":
        message = dashboard.get("interaction_note") or "Ledger AI consumes evidence through the visible app-section connections."
    else:
        active_sources = [
            item for item in dashboard["source_nodes"]
            if item.get("enabled") and (active_lens == "all" or active_lens in (item.get("app_sections") or []))
        ]
        active_processes = [
            item for item in dashboard["process_nodes"]
            if item.get("enabled") and (active_lens == "all" or active_lens in (item.get("app_sections") or []))
        ]
        label = "all app sections" if active_lens == "all" else APP_SECTIONS[active_lens]["label"]
        message = (
            f"The {label} lineage currently includes {len(active_sources)} source file(s), {len(active_processes)} extraction product(s) and "
            f"{len(dashboard['context_nodes'])} visible context layer(s). Files are not weighted by vague priority: their actual extraction route and app-section use determine what reaches Ledger AI."
        )
    return {"summary": message, "node": node, "active_lens": active_lens}


def _context_excerpt(node_id: str) -> str:
    try:
        content = str(context_file_content(node_id).get("content") or "")
    except Exception:
        return ""
    return content[:2200]


def board_prompt_context() -> dict[str, Any]:
    try:
        dashboard = context_board_dashboard(refresh_sources=False)
    except Exception:
        return {}
    active_lens = str(dashboard.get("settings", {}).get("active_lens") or "all")
    sources = [
        item for item in dashboard["source_nodes"]
        if item.get("enabled") and (active_lens == "all" or active_lens in (item.get("app_sections") or []))
    ]
    sources.sort(key=lambda item: (int(item.get("processing_order") or 100), str(item.get("label") or "")))
    contexts = [
        item for item in dashboard["context_nodes"]
        if item.get("enabled") and (active_lens == "all" or active_lens in (item.get("app_sections") or []))
    ]
    processes = [
        item for item in dashboard["process_nodes"]
        if item.get("enabled") and (active_lens == "all" or active_lens in (item.get("app_sections") or []))
    ]
    return {
        "active_app_section": active_lens,
        "lineage_rule": "Use only included sources. Read them in processing order, through their configured extraction products, and only for the app sections shown in app_sections. Use business_analyst_context.json as the governing internal decision brief. For Intelligence and market questions, combine it with market_analysis_template.json, market_analysis_context.json, the saved market report and verified market evidence.",
        "analysis_context_files": dashboard.get("analysis_context_files") or {},
        "enabled_sources": [
            {
                "source_key": item["id"],
                "label": item["label"],
                "document_type": item.get("document_type"),
                "processing_order": item.get("processing_order"),
                "extraction_targets": item.get("extraction_targets"),
                "app_sections": item.get("app_sections"),
                "freshness_state": item.get("freshness_state"),
                "effective_date": item.get("effective_date"),
                "notes": item.get("notes"),
                "transformation_note": item.get("transformation_note"),
                "preview": item.get("preview"),
            }
            for item in sources
        ][:30],
        "processing_products": [
            {
                "process_id": item["process_id"],
                "label": item["label"],
                "description": item.get("description"),
                "app_sections": item.get("app_sections"),
                "input_count": item.get("input_count"),
                "notes": item.get("notes"),
            }
            for item in processes
        ],
        "enabled_context_layers": [
            {
                "context_key": item["id"],
                "label": item["label"],
                "app_sections": item.get("app_sections"),
                "notes": item.get("notes"),
                "preview": item.get("preview"),
                "content_excerpt": _context_excerpt(item["id"]),
            }
            for item in contexts
        ],
        "excluded_source_count": int(dashboard.get("summary", {}).get("excluded_count") or 0),
        "data_cutoff_local": dashboard.get("data_cutoff_local"),
        "current_time_local": dashboard.get("current_time_local"),
        "last_analysis": dashboard.get("last_analysis") or {},
    }
