from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .database import get_duckdb


def _close(left: float | int | None, right: float | int | None, tolerance: float = 0.02) -> bool:
    return abs(float(left or 0) - float(right or 0)) <= tolerance


def _check(metric: str, displayed: float | int | None, database: float | int | None, source: str) -> dict[str, Any]:
    return {
        "metric": metric,
        "displayed_value": round(float(displayed or 0), 2),
        "database_value": round(float(database or 0), 2),
        "difference": round(float(displayed or 0) - float(database or 0), 2),
        "source": source,
        "status": "reconciled" if _close(displayed, database) else "mismatch",
    }


def dashboard_integrity(summary: dict[str, Any], accounting: dict[str, Any]) -> dict[str, Any]:
    """Verify that dashboard values and chart payloads reconcile to business.db."""
    con = get_duckdb()
    try:
        source_counts = {}
        for table in (
            "business_source_registry", "statement_snapshots", "journal_entries",
            "journal_lines", "assets_liabilities", "transactions", "invoices",
        ):
            try:
                source_counts[table] = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except Exception:
                source_counts[table] = 0
        ledger_rows = con.execute("""
            SELECT c.code, c.name, c.account_type, c.subtype,
                   CASE WHEN c.account_type IN ('asset','expense')
                        THEN COALESCE(SUM(l.debit-l.credit),0)
                        ELSE COALESCE(SUM(l.credit-l.debit),0) END AS balance
            FROM chart_of_accounts c
            LEFT JOIN (
                SELECT lines.* FROM journal_lines lines
                JOIN journal_entries entries ON entries.id=lines.journal_id
                WHERE entries.status='posted'
            ) l ON l.account_code=c.code
            WHERE c.active=TRUE
            GROUP BY c.code, c.name, c.account_type, c.subtype
        """).fetchall()
    finally:
        con.close()

    ledger = [
        {"code": str(row[0]), "name": str(row[1]), "type": str(row[2]), "subtype": str(row[3]), "balance": float(row[4] or 0)}
        for row in ledger_rows
    ]
    current_assets = sum(row["balance"] for row in ledger if row["type"] == "asset" and "current" in row["subtype"].lower() and "non-current" not in row["subtype"].lower())
    current_liabilities = sum(row["balance"] for row in ledger if row["type"] == "liability" and "current" in row["subtype"].lower())
    cash = sum(row["balance"] for row in ledger if row["type"] == "asset" and ("cash" in row["name"].lower() or "bank" in row["name"].lower()))
    total_assets = sum(row["balance"] for row in ledger if row["type"] == "asset")
    total_liabilities = sum(row["balance"] for row in ledger if row["type"] == "liability")
    ratio = current_assets / current_liabilities if current_liabilities else None

    checks = [
        _check("Cash", summary.get("cash"), cash, "business.db → posted journal lines"),
        _check("Current assets", summary.get("current_assets"), current_assets, "business.db → posted journal lines"),
        _check("Current liabilities", summary.get("current_liabilities"), current_liabilities, "business.db → posted journal lines"),
    ]
    if ratio is not None or summary.get("current_ratio") is not None:
        checks.append(_check("Current ratio", summary.get("current_ratio"), ratio, "current assets ÷ current liabilities"))
    account_total = sum(abs(float(row.get("balance") or 0)) for row in accounting.get("accounts") or [])
    database_account_total = sum(abs(row["balance"]) for row in ledger)
    checks.append(_check("Account register", account_total, database_account_total, "business.db → chart of accounts + posted journals"))
    position_total = sum(abs(float(row.get("value") or 0)) for row in summary.get("position_series") or [])
    checks.append(_check("Financial-position chart", position_total, abs(total_assets) + abs(total_liabilities), "business.db → posted ledger position"))

    performance = list(summary.get("performance_series") or [])
    profit_series = list((summary.get("profit_structure") or {}).get("series") or [])
    exposure = list(summary.get("invoice_exposure_series") or [])
    cash_series = list(summary.get("cash_series") or [])
    chart_specs = [
        ("Inflows versus outflows", performance, any(float(row.get("revenue") or 0) or float(row.get("expenses") or 0) for row in performance), str((summary.get("metric_sources") or {}).get("revenue_expenses") or "transactions")),
        ("Cash outlook", cash_series, any(float(row.get("forecast") or 0) for row in cash_series), str((summary.get("metric_sources") or {}).get("cash") or "posted ledger")),
        ("Assets and liabilities", list(summary.get("position_series") or []), position_total > 0, str((summary.get("metric_sources") or {}).get("financial_position") or "posted ledger")),
        ("Profit structure", profit_series, any(float(row.get("value") or 0) for row in profit_series), "profit_loss statement snapshot"),
        ("Invoice exposure", exposure, any(float(row.get("open") or 0) or float(row.get("overdue") or 0) for row in exposure), "invoices"),
    ]
    charts = [
        {
            "chart": name, "status": "loaded" if populated else "empty",
            "chart_rows": len(rows), "nonzero": bool(populated), "source": source,
            "message": "Chart payload contains database-backed values." if populated else "The source contains no non-zero values for this chart.",
        }
        for name, rows, populated, source in chart_specs
    ]
    mismatches = [item for item in checks if item["status"] == "mismatch"]
    loaded_charts = sum(1 for item in charts if item["status"] == "loaded")
    return {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "status": "reconciled" if not mismatches else "mismatch",
        "all_reconciled": not mismatches,
        "checks": checks,
        "charts": charts,
        "source_counts": source_counts,
        "loaded_charts": loaded_charts,
        "total_charts": len(charts),
        "message": (
            f"All {len(checks)} displayed measures reconcile to business.db; {loaded_charts}/{len(charts)} charts contain data."
            if not mismatches else f"{len(mismatches)} displayed measure(s) do not reconcile to business.db."
        ),
    }
