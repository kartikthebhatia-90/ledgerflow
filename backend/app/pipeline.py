from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from .config import settings
from .database import (
    COMPANY_ID,
    current_baseline_version,
    current_data_version,
    get_company_profile,
    get_sqlite,
    pipeline_status,
    record_pipeline_run,
    rows_as_dicts,
    utc_now,
)

DEPENDENCIES: dict[str, list[str]] = {
    "supplier_invoices": ["accounts_payable", "current_liabilities", "current_ratio", "cash_forecast", "supplier_concentration"],
    "sales_invoices": ["revenue", "accounts_receivable", "receivable_days", "cash_forecast", "customer_concentration"],
    "invoices": ["accounts_payable", "accounts_receivable", "current_ratio", "cash_forecast"],
    "payments": ["cash", "invoice_status", "cash_forecast", "duplicate_payment_checks"],
    "bank_statements": ["cash", "bank_reconciliation", "cash_forecast", "transaction_anomalies"],
    "transactions": ["revenue", "expenses", "cash", "cash_forecast", "transaction_anomalies"],
    "assets": ["total_assets", "current_assets", "depreciation", "balance_sheet"],
    "liabilities": ["current_liabilities", "debt_ratios", "interest_cost", "balance_sheet"],
    "assets_liabilities": ["current_ratio", "quick_ratio", "working_capital", "balance_sheet"],
    "inventory": ["inventory_value", "current_assets", "quick_ratio", "inventory_turnover"],
    "customers": ["customer_concentration", "receivable_segments", "company_baseline"],
    "suppliers": ["supplier_concentration", "supplier_country_risk", "market_profile"],
    "budgets": ["budget_variance", "forecast", "dashboard"],
    "balance_sheet": ["statement_reconciliation", "current_ratio", "debt_ratios"],
    "profit_loss": ["revenue", "expenses", "margin", "statement_reconciliation"],
    "cash_flow_statement": ["cash_flow_reconciliation", "cash_forecast"],
    "market_context": ["market_profile", "external_risk_score", "market_snapshot"],
    "generic": ["document_coverage", "information_requests"],
}

# These document types enrich company/market knowledge but do not change the
# accounting snapshot. They should not rebuild cash forecasts or Polars KPI
# history simply to make their text/signals available to the assistant.
CONTEXT_ONLY_DATASETS: set[str] = {
    "market_context",
    "business_requirements",
    "material_contracts",
    "use_cases_user_stories",
    "generic",
}


def context_dir(company_id: str = COMPANY_ID) -> Path:
    path = settings.data_path / "context" / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def gold_dir(company_id: str = COMPANY_ID) -> Path:
    path = settings.data_path / "gold" / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _table_count(table: str) -> int:
    rows = rows_as_dicts(f"SELECT COUNT(*) AS value FROM {table}")
    return int(rows[0]["value"] if rows else 0)


def document_coverage(company_id: str = COMPANY_ID) -> dict[str, Any]:
    status = pipeline_status(company_id)
    return {str(row["document_type"]): {"files": int(row["files"]), "rows": int(row["rows"])} for row in status["document_coverage"]}


def build_information_requests(company_id: str = COMPANY_ID) -> list[dict[str, Any]]:
    coverage = document_coverage(company_id)
    profile = get_company_profile()
    definitions = [
        ("supplier_master", "Supplier list with countries and currencies", "Required to map geopolitical, currency and shipping risk to actual suppliers.", "high", ["CSV", "Excel", "manual answer"], ["suppliers"]),
        ("customer_master", "Customer list with locations or segments", "Improves customer concentration, receivables and regional demand analysis.", "medium", ["CSV", "Excel"], ["customers"]),
        ("bank_statements", "Recent bank statement or transaction export", "Improves cash accuracy, reconciliation and duplicate-payment checks.", "high", ["CSV", "Excel"], ["bank_statements", "transactions"]),
        ("budget", "Current budget or forecast", "Enables budget-versus-actual analysis and more useful cash scenarios.", "medium", ["CSV", "Excel"], ["budgets"]),
        ("inventory", "Inventory or product catalogue", "Enables inventory value, turnover, product exposure and supply-chain analysis.", "medium", ["CSV", "Excel"], ["inventory"]),
        ("competitors", "Competitor names and operating markets", "Allows targeted market monitoring instead of broad generic news.", "medium", ["CSV", "Excel", "manual answer"], ["market_context"]),
        ("business_goals", "Business goals and KPI targets", "Helps Ledger judge performance against company-specific priorities.", "medium", ["manual answer"], []),
    ]
    requests: list[dict[str, Any]] = []
    sql = get_sqlite()
    for key, information, reason, priority, formats, satisfies in definitions:
        covered = any(name in coverage and coverage[name]["rows"] > 0 for name in satisfies)
        if key == "business_goals":
            covered = bool(str(profile.get("current_objective") or "").strip())
        status = "resolved" if covered else "open"
        sql.execute(
            "INSERT INTO information_requests(company_id, request_key, information, reason, priority, accepted_formats, status, created_at, resolved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(company_id, request_key) DO UPDATE SET information=excluded.information, reason=excluded.reason, priority=excluded.priority, accepted_formats=excluded.accepted_formats, status=excluded.status, resolved_at=excluded.resolved_at",
            (company_id, key, information, reason, priority, json.dumps(formats), status, utc_now(), utc_now() if covered else None),
        )
        requests.append({"request_key": key, "information": information, "reason": reason, "priority": priority, "accepted_formats": formats, "status": status})
    sql.commit(); sql.close()
    (context_dir(company_id) / "information_requests.json").write_text(json.dumps({"generated_at": utc_now(), "requests": requests}, indent=2), encoding="utf-8")
    return requests


def build_market_profile(company_id: str = COMPANY_ID) -> dict[str, Any]:
    profile = get_company_profile()
    suppliers = rows_as_dicts("SELECT name, country, category, currency FROM suppliers ORDER BY name")
    customers = rows_as_dicts("SELECT name, country, segment FROM customers ORDER BY name")
    supplier_countries = sorted({str(item.get("country") or "").strip() for item in suppliers if str(item.get("country") or "").strip()})
    currencies = sorted({str(item.get("currency") or "").strip() for item in suppliers if str(item.get("currency") or "").strip()})
    if not supplier_countries:
        supplier_countries = [item.strip() for item in str(profile.get("supplier_regions") or "").split(",") if item.strip()]
    if not currencies:
        currencies = [item.strip() for item in str(profile.get("important_currencies") or "").split(",") if item.strip()]
    market_profile = {
        "company_id": company_id,
        "generated_at": utc_now(),
        "industry": profile.get("industry"),
        "primary_location": profile.get("primary_location"),
        "operating_countries": [profile.get("primary_location")],
        "supplier_countries": supplier_countries,
        "customer_countries": sorted({str(item.get("country") or "").strip() for item in customers if str(item.get("country") or "").strip()}),
        "currencies": currencies,
        "suppliers": suppliers[:50],
        "customers": customers[:50],
        "competitors": [],
        "commodities": [],
        "transport_routes": [],
        "regulators": [],
        "labour_categories": [],
        "technology_dependencies": [],
        "risk_topics": [item.strip() for item in str(profile.get("primary_risks") or "").split(",") if item.strip()],
        "source": "Company profile plus uploaded supplier/customer/market-context files",
    }
    (context_dir(company_id) / "market_profile.json").write_text(json.dumps(market_profile, indent=2, default=str), encoding="utf-8")
    return market_profile


def refresh_market_snapshot(company_id: str = COMPANY_ID) -> dict[str, Any]:
    signals = rows_as_dicts("""
        SELECT id, signal_type, topic, entity, geography, observed_at, published_at,
               value, unit, direction, source_name, source_url, relevance_score,
               estimated_impact, impact_horizon, source_file
        FROM market_signals
        ORDER BY relevance_score DESC NULLS LAST, COALESCE(published_at, observed_at) DESC
    """)
    high = [item for item in signals if float(item.get("relevance_score") or 0) >= 0.75]
    medium = [item for item in signals if 0.4 <= float(item.get("relevance_score") or 0) < 0.75]
    watch = [item for item in signals if float(item.get("relevance_score") or 0) < 0.4]
    snapshot = {
        "generated_at": utc_now(),
        "high_priority": high[:20],
        "medium_priority": medium[:30],
        "watchlist": watch[:30],
        "company_implications": [str(item.get("estimated_impact") or "") for item in (high + medium) if item.get("estimated_impact")][:20],
        "signal_count": len(signals),
    }
    output = context_dir(company_id) / "latest_market_snapshot.json"
    output.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    brief_lines = ["# Market Context Brief", "", f"Generated: {snapshot['generated_at']}", "", "## Highest-priority signals"]
    if not high: brief_lines.append("No high-priority uploaded market signals are currently stored.")
    for item in high[:10]:
        brief_lines.append(f"- **{item.get('topic') or item.get('signal_type')}** — {item.get('estimated_impact') or 'Impact not yet described'}")
    brief_lines.extend(["", "## Information still useful", "See `information_requests.json` for missing company context that would improve analysis."])
    (context_dir(company_id) / "market_brief.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")
    return snapshot


def build_company_baseline(company_id: str = COMPANY_ID, force_full: bool = False) -> dict[str, Any]:
    from .analytics import financial_snapshot

    path = context_dir(company_id) / "company_baseline.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try: existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception: existing = {}
    old_version = current_baseline_version(company_id)
    is_full = force_full or not existing or old_version == 0
    baseline_version = old_version + 1 if is_full else old_version
    coverage = document_coverage(company_id)
    market_profile = build_market_profile(company_id)
    requests = build_information_requests(company_id)
    baseline = {
        "company_id": company_id,
        "baseline_version": baseline_version,
        "baseline_type": "full" if is_full else "incremental_refresh",
        "first_full_build": existing.get("first_full_build") or utc_now(),
        "last_full_build": utc_now() if is_full else existing.get("last_full_build"),
        "last_incremental_update": utc_now(),
        "data_version": current_data_version(company_id),
        "company_profile": get_company_profile(),
        "document_coverage": coverage,
        "entity_counts": {
            "suppliers": _table_count("suppliers"),
            "customers": _table_count("customers"),
            "invoices": _table_count("invoices"),
            "payments": _table_count("payments"),
            "transactions": _table_count("transactions"),
            "assets_liabilities": _table_count("assets_liabilities"),
            "inventory": _table_count("inventory"),
            "market_signals": _table_count("market_signals"),
        },
        "financial_snapshot": financial_snapshot(),
        "market_exposure": market_profile,
        "open_information_requests": [item for item in requests if item["status"] == "open"],
        "processing_model": "Initial full baseline followed by row-level incremental processing and dependency-aware Gold refreshes.",
    }
    path.write_text(json.dumps(baseline, indent=2, default=str), encoding="utf-8")
    if is_full:
        sql = get_sqlite()
        sql.execute(
            "INSERT INTO company_baselines(company_id, baseline_version, created_at, baseline_path, data_version, document_coverage_json) VALUES (?, ?, ?, ?, ?, ?)",
            (company_id, baseline_version, utc_now(), str(path), current_data_version(company_id), json.dumps(coverage)),
        )
        sql.commit(); sql.close()
    return baseline


def refresh_context_layers(affected_datasets: list[str] | None = None, company_id: str = COMPANY_ID) -> dict[str, Any]:
    """Refresh market/document context without rebuilding financial Gold layers."""
    affected_datasets = sorted(set(affected_datasets or []))
    affected_metrics = sorted({metric for dataset in affected_datasets for metric in DEPENDENCIES.get(dataset, ["document_coverage"])})
    coverage = document_coverage(company_id)
    market_profile = build_market_profile(company_id)
    requests = build_information_requests(company_id)
    market_snapshot = refresh_market_snapshot(company_id)

    path = context_dir(company_id) / "company_baseline.json"
    baseline: dict[str, Any] = {}
    if path.exists():
        try:
            baseline = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            baseline = {}

    baseline_version = current_baseline_version(company_id)
    if baseline_version == 0:
        baseline_version = 1
        sql = get_sqlite()
        sql.execute(
            "INSERT INTO company_baselines(company_id, baseline_version, created_at, baseline_path, data_version, document_coverage_json) VALUES (?, ?, ?, ?, ?, ?)",
            (company_id, baseline_version, utc_now(), str(path), current_data_version(company_id), json.dumps(coverage)),
        )
        sql.commit(); sql.close()

    baseline.update({
        "company_id": company_id,
        "baseline_version": baseline_version,
        "baseline_type": baseline.get("baseline_type") or "context_only_initialisation",
        "first_full_build": baseline.get("first_full_build"),
        "last_full_build": baseline.get("last_full_build"),
        "last_incremental_update": utc_now(),
        "data_version": current_data_version(company_id),
        "company_profile": get_company_profile(),
        "document_coverage": coverage,
        "market_exposure": market_profile,
        "open_information_requests": [item for item in requests if item["status"] == "open"],
        "processing_model": "Context-only refresh; financial Gold metrics were intentionally left unchanged.",
    })
    baseline.setdefault("financial_snapshot", {})
    entity_counts = dict(baseline.get("entity_counts") or {})
    entity_counts["market_signals"] = _table_count("market_signals")
    baseline["entity_counts"] = entity_counts
    path.write_text(json.dumps(baseline, indent=2, default=str), encoding="utf-8")

    result = {
        "affected_datasets": affected_datasets,
        "affected_metrics": affected_metrics,
        "data_version": current_data_version(company_id),
        "baseline_version": baseline_version,
        "market_signal_count": market_snapshot["signal_count"],
        "gold_paths": [],
        "context_only": True,
    }
    record_pipeline_run("context_only_refresh", "completed", result, company_id)
    return result


def refresh_gold_layers(affected_datasets: list[str] | None = None, company_id: str = COMPANY_ID) -> dict[str, Any]:
    from .analytics import financial_snapshot, cash_forecast

    affected_datasets = sorted(set(affected_datasets or []))
    affected_metrics = sorted({metric for dataset in affected_datasets for metric in DEPENDENCIES.get(dataset, ["dashboard"])})
    snapshot = financial_snapshot()
    now = datetime.now(timezone.utc)
    snapshot_record = {
        "company_id": company_id,
        "snapshot_time": now,
        "data_version": current_data_version(company_id),
        **{key: value for key, value in snapshot.items() if key != "company"},
    }
    kpi_path = gold_dir(company_id) / "kpi_snapshots.parquet"
    new_frame = pl.DataFrame([snapshot_record], strict=False)
    if kpi_path.exists():
        old = pl.read_parquet(kpi_path)
        new_frame = pl.concat([old, new_frame], how="diagonal_relaxed").tail(5000)
    new_frame.write_parquet(kpi_path, compression="zstd")

    decision = {
        "company_id": company_id,
        "snapshot_time": now,
        "data_version": current_data_version(company_id),
        "cash_available": snapshot.get("cash", 0),
        "cash_runway_days": snapshot.get("cash_runway_days", 0),
        "current_ratio": snapshot.get("current_ratio"),
        "quick_ratio": snapshot.get("quick_ratio"),
        "working_capital": snapshot.get("working_capital", 0),
        "revenue_growth": snapshot.get("revenue_change", 0),
        "gross_margin": snapshot.get("gross_margin", 0),
        "receivable_days": snapshot.get("receivable_days", 0),
        "payable_days": snapshot.get("payable_days", 0),
        "overdue_receivables": snapshot.get("overdue_invoice_total", 0),
        "validation_error_count": _table_count("validations"),
        "anomaly_count": snapshot.get("anomaly_count", 0),
        "external_risk_signal_count": _table_count("market_signals"),
        "forecast_low_point_90d": cash_forecast(90).get("low_point"),
        "affected_metrics": json.dumps(affected_metrics),
    }
    pl.DataFrame([decision], strict=False).write_parquet(gold_dir(company_id) / "decision_features.parquet", compression="zstd")
    baseline = build_company_baseline(company_id, force_full=False)
    market_snapshot = refresh_market_snapshot(company_id)
    result = {
        "affected_datasets": affected_datasets,
        "affected_metrics": affected_metrics,
        "data_version": current_data_version(company_id),
        "baseline_version": baseline["baseline_version"],
        "market_signal_count": market_snapshot["signal_count"],
        "gold_paths": [str(kpi_path), str(gold_dir(company_id) / "decision_features.parquet")],
    }
    record_pipeline_run("incremental_gold_refresh", "completed", result, company_id)
    return result


def full_pipeline_rebuild(company_id: str = COMPANY_ID) -> dict[str, Any]:
    details = refresh_gold_layers(list(DEPENDENCIES), company_id)
    baseline = build_company_baseline(company_id, force_full=True)
    details["baseline_version"] = baseline["baseline_version"]
    record_pipeline_run("full_rebuild", "completed", details, company_id)
    return details
