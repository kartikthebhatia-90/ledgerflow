from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .database import get_duckdb
from .tax import tax_dashboard


def _source_label(description: str) -> str:
    text = description.lower()
    if "key account" in text:
        return "Key accounts"
    if "healthcare" in text or "education" in text:
        return "Healthcare & education"
    if "commercial" in text:
        return "Commercial customers"
    return "Other receipts"


def _department(line_item: str) -> str:
    text = line_item.lower()
    if "cost of goods" in text or "freight" in text or "depreciation" in text:
        return "Operations & supply"
    if "payroll" in text or "wage" in text or "super" in text:
        return "People"
    if "rent" in text or "utilit" in text:
        return "Facilities"
    if "advert" in text or "marketing" in text:
        return "Growth"
    if "software" in text or "subscription" in text:
        return "Technology"
    if "interest" in text or "finance" in text or "bank" in text:
        return "Finance"
    return "Other operations"


def money_map_dashboard() -> dict[str, Any]:
    con = get_duckdb()
    try:
        latest_bank_month = con.execute(
            "SELECT MAX(substr(CAST(transaction_date AS VARCHAR),1,7)) FROM bank_transactions"
        ).fetchone()[0]
        bank_rows = con.execute(
            """
            SELECT description, amount
            FROM bank_transactions
            WHERE substr(CAST(transaction_date AS VARCHAR),1,7)=?
              AND amount>0
            """,
            [latest_bank_month or ""],
        ).fetchall()
        latest_statement_period = con.execute(
            "SELECT MAX(period_end) FROM statement_snapshots WHERE statement_type='profit_loss'"
        ).fetchone()[0]
        statement_rows = con.execute(
            """
            SELECT line_item, amount
            FROM statement_snapshots
            WHERE statement_type='profit_loss' AND period_end=?
            """,
            [latest_statement_period],
        ).fetchall()
    finally:
        con.close()

    source_totals: dict[str, float] = {}
    for description, amount in bank_rows:
        label = _source_label(str(description or ""))
        source_totals[label] = source_totals.get(label, 0.0) + float(amount or 0)

    statement_revenue = sum(float(amount or 0) for _line, amount in statement_rows if float(amount or 0) > 0)
    department_totals: dict[str, float] = {}
    for line_item, amount in statement_rows:
        value = float(amount or 0)
        if value >= 0:
            continue
        department = _department(str(line_item or ""))
        department_totals[department] = department_totals.get(department, 0.0) + abs(value)

    if not source_totals and statement_revenue:
        source_totals = {"Recorded revenue": statement_revenue}
    revenue = statement_revenue or sum(source_totals.values())
    operating_costs = sum(department_totals.values())
    pre_tax_profit = max(0.0, revenue - operating_costs)
    tax_estimate = min(pre_tax_profit, float(tax_dashboard()["summary"].get("estimated_income_tax") or 0))
    retained_profit = max(0.0, pre_tax_profit - tax_estimate)

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    def node(name: str, group: str) -> int:
        nodes.append({"name": name, "group": group})
        return len(nodes) - 1

    revenue_node = None
    source_nodes: list[tuple[int, float]] = []
    for name, value in sorted(source_totals.items(), key=lambda item: item[1], reverse=True):
        source_nodes.append((node(name, "source"), round(value, 2)))
    revenue_node = node("Revenue hub", "hub")
    for source_node, value in source_nodes:
        links.append({"source": source_node, "target": revenue_node, "value": value})

    for name, value in sorted(department_totals.items(), key=lambda item: item[1], reverse=True):
        destination = node(name, "department")
        links.append({"source": revenue_node, "target": destination, "value": round(value, 2)})

    profit_node = node("Profit before tax", "profit")
    links.append({"source": revenue_node, "target": profit_node, "value": round(pre_tax_profit, 2)})
    if pre_tax_profit > 0:
        tax_node = node("Estimated income tax", "tax")
        retained_node = node("Retained profit", "retained")
        if tax_estimate > 0:
            links.append({"source": profit_node, "target": tax_node, "value": round(tax_estimate, 2)})
        if retained_profit > 0:
            links.append({"source": profit_node, "target": retained_node, "value": round(retained_profit, 2)})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": str(latest_statement_period or latest_bank_month or ""),
        "summary": {
            "revenue": round(revenue, 2),
            "operating_costs": round(operating_costs, 2),
            "profit_before_tax": round(pre_tax_profit, 2),
            "estimated_tax": round(tax_estimate, 2),
            "retained_profit": round(retained_profit, 2),
            "profit_margin_pct": round((pre_tax_profit / revenue * 100) if revenue else 0, 1),
        },
        "sources": [{"name": key, "value": round(value, 2)} for key, value in source_totals.items()],
        "departments": [{"name": key, "value": round(value, 2)} for key, value in department_totals.items()],
        "nodes": nodes,
        "links": links,
        "source_note": "Receipts use the latest bank month; department flows and profit use the latest uploaded Profit & Loss period.",
    }
