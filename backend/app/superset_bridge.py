from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import duckdb

from .accounting import accounting_dashboard
from .analytics import dashboard_summary
from .competitor_intelligence import analysis_status
from .config import settings
from .database import duckdb_path, get_duckdb
from .marketing import marketing_dashboard
from .tax import tax_dashboard


DASHBOARD_CATALOGUE: dict[str, dict[str, Any]] = {
    "executive": {
        "label": "Executive command centre",
        "department": "Executive",
        "view": "superset_department_metrics",
        "uuid_setting": "superset_dashboard_executive_uuid",
    },
    "finance": {
        "label": "Finance and accounting",
        "department": "Finance",
        "view": "superset_finance_records",
        "uuid_setting": "superset_dashboard_finance_uuid",
    },
    "tax": {
        "label": "Tax and compliance",
        "department": "Tax",
        "view": "superset_tax_records",
        "uuid_setting": "superset_dashboard_tax_uuid",
    },
    "marketing": {
        "label": "Growth and marketing",
        "department": "Marketing",
        "view": "superset_marketing_records",
        "uuid_setting": "superset_dashboard_marketing_uuid",
    },
    "operations": {
        "label": "Operations and supply",
        "department": "Operations",
        "view": "superset_operations_records",
        "uuid_setting": "superset_dashboard_operations_uuid",
    },
    "people": {
        "label": "People and payroll",
        "department": "People",
        "view": "superset_people_records",
        "uuid_setting": "superset_dashboard_people_uuid",
    },
    "market": {
        "label": "Market and competitors",
        "department": "Market intelligence",
        "view": "superset_market_records",
        "uuid_setting": "superset_dashboard_market_uuid",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _generated_dashboard_assets() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "superset" / "generated_dashboards.json"
    if not path.exists():
        return {}
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        return dict(body.get("dashboards") or {})
    except Exception:
        return {}


def dashboard_catalogue() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    generated = _generated_dashboard_assets()
    for dashboard_id, definition in DASHBOARD_CATALOGUE.items():
        generated_item = generated.get(dashboard_id) or {}
        uuid_value = str(getattr(settings, str(definition["uuid_setting"]), "") or generated_item.get("uuid") or "")
        result.append(
            {
                "id": f"dashboard:{dashboard_id}",
                "dashboard_id": dashboard_id,
                "node_type": "dashboard",
                "label": definition["label"],
                "department": definition["department"],
                "view": definition["view"],
                "uuid": uuid_value,
                "configured": bool(uuid_value),
                "superset_domain": settings.superset_domain,
                "description": f"Apache Superset visual analytics for {definition['department']} using {definition['view']}.",
                "superset_dashboard_id": generated_item.get("dashboard_id"),
                "dataset_id": generated_item.get("dataset_id"),
                "slug": generated_item.get("slug") or f"ledgerflow-{dashboard_id}",
            }
        )
    return result


def refresh_superset_views() -> dict[str, Any]:
    """Create a separate read-only analytics snapshot for Apache Superset.

    The main LedgerFlow database remains the transactional/analytical source of
    truth. Superset reads a copied snapshot so a separate Docker process never
    competes with LedgerFlow for the writer lock on business.duckdb.
    """
    summary = dashboard_summary()
    accounting = accounting_dashboard()
    tax = tax_dashboard()
    marketing = marketing_dashboard()
    intelligence = analysis_status()
    generated_at = _now()

    metric_rows: list[tuple[str, str, float | None, str, str, str]] = []

    def add(department: str, metric: str, value: Any, text: str = "", source: str = "LedgerFlow") -> None:
        try:
            numeric: float | None = float(value) if value is not None else None
        except (TypeError, ValueError):
            numeric = None
        metric_rows.append((department, metric, numeric, text or ("" if value is None else str(value)), generated_at, source))

    add("Executive", "Cash", summary.get("cash"), source="dashboard_summary")
    add("Executive", "Current ratio", summary.get("current_ratio"), source="dashboard_summary")
    add("Executive", "Monthly inflows", summary.get("revenue_month"), source="dashboard_summary")
    add("Executive", "Cash runway days", summary.get("cash_runway_days"), source="dashboard_summary")
    acc_summary = accounting.get("summary") or {}
    add("Finance", "Revenue", acc_summary.get("revenue"), source="accounting_dashboard")
    add("Finance", "Expenses", acc_summary.get("expenses"), source="accounting_dashboard")
    add("Finance", "Net profit", acc_summary.get("net_profit"), source="accounting_dashboard")
    tax_summary = tax.get("summary") or {}
    add("Tax", "Estimated taxable income", tax_summary.get("estimated_taxable_income"), source="tax_dashboard")
    add("Tax", "Estimated income tax", tax_summary.get("estimated_income_tax"), source="tax_dashboard")
    add("Tax", "Review count", tax_summary.get("review_count"), source="tax_dashboard")
    marketing_summary = marketing.get("summary") or {}
    add("Marketing", "Marketing spend", marketing_summary.get("marketing_spend"), source="marketing_dashboard")
    add("Marketing", "Revenue context", marketing_summary.get("revenue"), source="marketing_dashboard")
    add("Marketing", "ROAS", marketing_summary.get("roas"), source="marketing_dashboard")
    result = intelligence.get("result") if isinstance(intelligence, dict) else {}
    company = result.get("company") if isinstance(result, dict) else {}
    add("Market intelligence", "Company position score", (company or {}).get("score"), source="competitor_intelligence")

    snapshot_path = settings.data_path / "database" / "superset.duckdb"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    source_path = duckdb_path()
    snap = duckdb.connect(str(snapshot_path))
    created: list[str] = []
    try:
        snap.execute(
            """
            CREATE TABLE IF NOT EXISTS superset_department_metrics (
                department VARCHAR,
                metric VARCHAR,
                value_numeric DOUBLE,
                value_text VARCHAR,
                generated_at TIMESTAMP,
                source VARCHAR
            )
            """
        )
        snap.execute("DELETE FROM superset_department_metrics")
        if metric_rows:
            snap.executemany("INSERT INTO superset_department_metrics VALUES (?, ?, ?, ?, ?, ?)", metric_rows)
        if source_path.exists():
            safe_source = source_path.resolve().as_posix().replace("'", "''")
            try:
                snap.execute(f"ATTACH '{safe_source}' AS ledger_source (READ_ONLY)")
            except Exception:
                # It may already be attached in a long-running development process.
                pass
            tables = {
                "superset_finance_records": "SELECT * FROM ledger_source.statement_snapshots",
                "superset_tax_records": "SELECT invoice_number, supplier, invoice_date, due_date, amount, subtotal, gst_amount, tax_code, validation_status, source_file FROM ledger_source.invoices",
                "superset_marketing_records": "SELECT invoice_number, supplier, invoice_date, amount, description, account_code, category, validation_status, source_file FROM ledger_source.invoices WHERE account_code='6150' OR lower(description) LIKE '%marketing%' OR lower(description) LIKE '%advertis%' OR lower(description) LIKE '%google ads%' OR lower(description) LIKE '%facebook%' OR lower(description) LIKE '%instagram%'",
                "superset_operations_records": "SELECT * FROM ledger_source.bank_transactions",
                "superset_people_records": "SELECT * FROM ledger_source.payroll_records",
                "superset_market_records": "SELECT * FROM ledger_source.market_signals",
            }
            for name, query in tables.items():
                try:
                    snap.execute(f"CREATE OR REPLACE TABLE {name} AS {query}")
                    created.append(name)
                except Exception:
                    # Freshly cleared installations may not have every source table yet.
                    continue
            try:
                snap.execute("DETACH ledger_source")
            except Exception:
                pass
    finally:
        snap.close()
    return {
        "ok": True,
        "generated_at": generated_at,
        "metric_count": len(metric_rows),
        "tables": created,
        "snapshot_path": str(snapshot_path),
    }


async def superset_status() -> dict[str, Any]:
    result = {
        "enabled": settings.superset_enabled,
        "domain": settings.superset_domain,
        "connected": False,
        "detail": "Superset integration is disabled.",
        "dashboards": dashboard_catalogue(),
        "studio_url": settings.superset_domain,
    }
    if not settings.superset_enabled:
        return result
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=settings.superset_verify_ssl, trust_env=False) as client:
            response = await client.get(f"{settings.superset_domain.rstrip('/')}/health")
            response.raise_for_status()
        result.update({"connected": True, "detail": "Apache Superset is reachable."})
    except Exception as exc:
        result["detail"] = f"Superset is configured but not reachable: {type(exc).__name__}: {exc}"
    return result


async def _login_token() -> str:
    if not settings.superset_service_username or not settings.superset_service_password:
        raise RuntimeError("SUPERSET_SERVICE_USERNAME and SUPERSET_SERVICE_PASSWORD are required")
    async with httpx.AsyncClient(timeout=15.0, verify=settings.superset_verify_ssl, trust_env=False) as client:
        response = await client.post(
            f"{settings.superset_domain.rstrip('/')}/api/v1/security/login",
            json={
                "username": settings.superset_service_username,
                "password": settings.superset_service_password,
                "provider": "db",
                "refresh": True,
            },
        )
        response.raise_for_status()
    token = str(response.json().get("access_token") or "")
    if not token:
        raise RuntimeError("Superset login did not return an access token")
    return token


async def guest_token_for_department(department_id: str) -> dict[str, Any]:
    catalogue = {item["dashboard_id"]: item for item in dashboard_catalogue()}
    dashboard = catalogue.get(department_id)
    if not dashboard:
        raise KeyError(f"Unknown Superset dashboard: {department_id}")
    if not dashboard.get("uuid"):
        raise RuntimeError(f"No embedded dashboard UUID configured for {department_id}")
    access_token = await _login_token()
    payload = {
        "resources": [{"type": "dashboard", "id": dashboard["uuid"]}],
        "rls": [],
        "user": {
            "username": "ledgerflow-embedded",
            "first_name": "LedgerFlow",
            "last_name": dashboard["department"],
        },
    }
    async with httpx.AsyncClient(timeout=15.0, verify=settings.superset_verify_ssl, trust_env=False) as client:
        response = await client.post(
            f"{settings.superset_domain.rstrip('/')}/api/v1/security/guest_token/",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError("Superset guest-token endpoint returned no token")
    return {
        "token": token,
        "dashboard": dashboard,
        "superset_domain": settings.superset_domain,
    }
