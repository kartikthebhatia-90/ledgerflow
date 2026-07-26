from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .analytics import financial_snapshot
from .database import get_duckdb, rows_as_dicts


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def run_validations() -> list[dict[str, Any]]:
    snapshot = financial_snapshot()
    issues: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    ratio = snapshot.get("current_ratio")
    target = snapshot.get("current_ratio_target", 1.2)
    if ratio is not None and ratio < target:
        severity = "critical" if ratio < 1 else "high"
        issues.append({
            "id": "val-current-ratio",
            "severity": severity,
            "check_name": "low_current_ratio",
            "description": f"Current ratio is {ratio:.2f}, below the configured target of {target:.2f}.",
            "target_id": "current-ratio-card",
            "recommendation": "Review cash, receivables, supplier payables, and short-term debt before committing additional cash.",
            "evidence": {
                "current_assets": snapshot["current_assets"],
                "current_liabilities": snapshot["current_liabilities"],
                "working_capital": snapshot["working_capital"],
            },
        })

    runway = int(snapshot.get("cash_runway_days") or 0)
    runway_target = int(snapshot.get("cash_runway_target_days") or 45)
    if runway and runway < runway_target:
        issues.append({
            "id": "val-cash-runway",
            "severity": "critical" if runway < 21 else "high",
            "check_name": "low_cash_runway",
            "description": f"Estimated cash runway is {runway} days, below the configured target of {runway_target} days.",
            "target_id": "cash-card",
            "recommendation": "Review near-term payments, overdue receivables, and discretionary spending.",
            "evidence": {"cash": snapshot["cash"], "expenses_month": snapshot["expenses_month"]},
        })

    overdue = float(snapshot.get("overdue_invoice_total") or 0)
    if overdue > 0:
        issues.append({
            "id": "val-overdue-invoices",
            "severity": "high" if overdue > max(snapshot.get("cash", 0), 1) else "medium",
            "check_name": "overdue_invoices",
            "description": f"Unpaid invoices worth ${overdue:,.2f} are past their due date.",
            "target_id": "asset-receivables",
            "recommendation": "Review overdue customers and prioritise collection follow-up.",
            "evidence": {"overdue_total": overdue},
        })

    invoice_dupes = rows_as_dicts("""
        SELECT invoice_number, COUNT(*) AS count, SUM(amount) AS total
        FROM invoices
        GROUP BY invoice_number
        HAVING COUNT(*) > 1
    """)
    for row in invoice_dupes:
        invoice_number = str(row["invoice_number"])
        records = rows_as_dicts("SELECT id, supplier, invoice_date, due_date, amount, status FROM invoices WHERE invoice_number=?", (invoice_number,))
        issues.append({
            "id": f"val-invoice-{_slug(invoice_number)}",
            "severity": "critical",
            "check_name": "duplicate_invoice_number",
            "description": f"Invoice number {invoice_number} appears {int(row['count'])} times.",
            "target_id": str(records[-1]["id"]) if records else "invoices-table",
            "recommendation": "Compare the source documents and payment records before approving another payment.",
            "evidence": {"invoice_number": invoice_number, "records": records},
        })

    transactions = rows_as_dicts("SELECT id, transaction_date, description, category, amount, status FROM transactions ORDER BY transaction_date")
    seen: dict[str, list[dict[str, Any]]] = {}
    invoice_pattern = re.compile(r"\b(?:inv|invoice)[-\s]*([a-z0-9-]+)\b", re.IGNORECASE)
    for transaction in transactions:
        description = str(transaction.get("description") or "")
        match = invoice_pattern.search(description)
        key = match.group(1).lower() if match else re.sub(r"\W+", " ", description.lower()).strip()
        if not key:
            continue
        prior = seen.setdefault(key, [])
        for earlier in prior:
            current_amount = abs(float(transaction.get("amount") or 0))
            earlier_amount = abs(float(earlier.get("amount") or 0))
            comparable = min(current_amount, earlier_amount) / max(current_amount, earlier_amount, 1) >= 0.9
            if comparable and current_amount > 0:
                issue_id = f"val-txn-{_slug(key)}-{str(transaction['id'])}"
                issues.append({
                    "id": issue_id,
                    "severity": "critical",
                    "check_name": "possible_duplicate_payment",
                    "description": f"Two similar payments reference {key}: ${earlier_amount:,.2f} and ${current_amount:,.2f}.",
                    "target_id": str(transaction["id"]),
                    "recommendation": "Compare the linked invoice and source bank entries before changing either record.",
                    "evidence": {"earlier": earlier, "current": transaction},
                })
                break
        prior.append(transaction)

    receivable_days = int(snapshot.get("receivable_days") or 0)
    if receivable_days > 60:
        issues.append({
            "id": "val-receivable-days",
            "severity": "high" if receivable_days > 75 else "medium",
            "check_name": "slow_receivables",
            "description": f"Estimated receivable days are {receivable_days}, which may delay available cash.",
            "target_id": "asset-receivables",
            "recommendation": "Segment overdue customers and prioritise the largest balances first.",
            "evidence": {"receivable_days": receivable_days, "open_invoice_total": snapshot["open_invoice_total"]},
        })

    con = get_duckdb()
    previous = {
        row[0]: row[1]
        for row in con.execute("SELECT id, COALESCE(status, 'open') FROM validations").fetchall()
    }
    con.execute("DELETE FROM validations")
    for issue in issues:
        status = previous.get(issue["id"], "open")
        con.execute(
            "INSERT INTO validations(id, severity, check_name, description, target_id, recommendation, status, detected_at, evidence_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                issue["id"], issue["severity"], issue["check_name"], issue["description"],
                issue["target_id"], issue["recommendation"], status,
                now.replace(tzinfo=None), json.dumps(issue["evidence"], default=str),
            ),
        )
    con.close()
    return issues
