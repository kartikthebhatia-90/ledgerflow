from __future__ import annotations

import hashlib
import re
import threading
from datetime import datetime, timezone
from typing import Any

from .database import get_company_profile, get_duckdb, utc_now

DEFAULT_ACCOUNTS: list[tuple[str, str, str, str, str, bool, str]] = [
    ("1000", "Cash at bank", "asset", "current asset", "N-T", True, "system"),
    ("1010", "Petty cash", "asset", "current asset", "N-T", True, "system"),
    ("1100", "Accounts receivable", "asset", "current asset", "GST", True, "system"),
    ("1150", "Prepaid expenses", "asset", "current asset", "N-T", True, "system"),
    ("1190", "Other current assets", "asset", "current asset", "N-T", True, "system"),
    ("1200", "Inventory", "asset", "current asset", "GST", True, "system"),
    ("1300", "GST receivable", "asset", "current asset", "GST", True, "system"),
    ("1500", "Plant and equipment", "asset", "non-current asset", "CAP", True, "system"),
    ("1510", "Property and land", "asset", "non-current asset", "CAP", True, "system"),
    ("1520", "Motor vehicles", "asset", "non-current asset", "CAP", True, "system"),
    ("1530", "Furniture and fitout", "asset", "non-current asset", "CAP", True, "system"),
    ("1540", "Computer equipment", "asset", "non-current asset", "CAP", True, "system"),
    ("1550", "Leasehold improvements", "asset", "non-current asset", "CAP", True, "system"),
    ("1560", "Intangible assets", "asset", "non-current asset", "CAP", True, "system"),
    ("1590", "Accumulated depreciation", "asset", "contra asset", "N-T", True, "system"),
    ("2000", "Accounts payable", "liability", "current liability", "GST", True, "system"),
    ("2010", "Credit cards payable", "liability", "current liability", "N-T", True, "system"),
    ("2050", "Accrued expenses", "liability", "current liability", "N-T", True, "system"),
    ("2060", "Income tax payable", "liability", "current liability", "N-T", True, "system"),
    ("2070", "Interest payable", "liability", "current liability", "N-T", True, "system"),
    ("2100", "GST payable", "liability", "current liability", "GST", True, "system"),
    ("2200", "Loans payable", "liability", "financial liability", "N-T", True, "system"),
    ("2210", "Equipment finance", "liability", "financial liability", "N-T", True, "system"),
    ("2290", "Other liabilities", "liability", "financial liability", "N-T", True, "system"),
    ("2300", "PAYG withholding payable", "liability", "current liability", "N-T", True, "system"),
    ("2400", "Superannuation payable", "liability", "current liability", "N-T", True, "system"),
    ("3000", "Owner equity", "equity", "equity", "N-T", True, "system"),
    ("4000", "Sales revenue", "revenue", "operating revenue", "GST", True, "system"),
    ("4100", "Other income", "revenue", "other revenue", "GST", True, "system"),
    ("5000", "Cost of goods sold", "expense", "cost of sales", "GST", True, "system"),
    ("6100", "Office supplies", "expense", "operating expense", "GST", True, "system"),
    ("6110", "Software and subscriptions", "expense", "operating expense", "GST", True, "system"),
    ("6120", "Utilities", "expense", "operating expense", "GST", True, "system"),
    ("6130", "Freight and delivery", "expense", "operating expense", "GST", True, "system"),
    ("6140", "Rent and occupancy", "expense", "operating expense", "GST", True, "system"),
    ("6150", "Advertising and marketing", "expense", "operating expense", "GST", True, "system"),
    ("6160", "Professional fees", "expense", "operating expense", "GST", True, "system"),
    ("6170", "Motor vehicle expenses", "expense", "operating expense", "GST", True, "system"),
    ("6180", "Travel", "expense", "operating expense", "GST", True, "system"),
    ("6190", "Meals and entertainment", "expense", "review expense", "GST", True, "system"),
    ("6200", "Insurance", "expense", "operating expense", "GST", True, "system"),
    ("6210", "Repairs and maintenance", "expense", "operating expense", "GST", True, "system"),
    ("6220", "Wages and salaries", "expense", "payroll expense", "N-T", True, "system"),
    ("6230", "Superannuation expense", "expense", "payroll expense", "N-T", True, "system"),
    ("6240", "Bank fees", "expense", "finance expense", "GST-FREE", True, "system"),
    ("6250", "Interest expense", "expense", "finance expense", "INPUT-TAXED", True, "system"),
    ("6999", "Uncategorised expenses", "expense", "review expense", "REVIEW", True, "system"),
]

ACCOUNTING_REBUILD_LOCK = threading.RLock()
ACCOUNTING_SNAPSHOT_LOCK = threading.RLock()
_ACCOUNTING_CACHE: dict[str, Any] | None = None


DEFAULT_RULES: list[tuple[str, str, str, str, int]] = [
    ("officeworks", "contains", "6100", "GST", 100),
    ("stationery", "contains", "6100", "GST", 90),
    ("printer ink", "contains", "6100", "GST", 90),
    ("microsoft", "contains", "6110", "GST", 100),
    ("adobe", "contains", "6110", "GST", 100),
    ("software", "contains", "6110", "GST", 70),
    ("subscription", "contains", "6110", "GST", 70),
    ("electricity", "contains", "6120", "GST", 100),
    ("water", "contains", "6120", "GST", 80),
    ("gas bill", "contains", "6120", "GST", 90),
    ("utilities", "contains", "6120", "GST", 75),
    ("freight", "contains", "6130", "GST", 95),
    ("courier", "contains", "6130", "GST", 90),
    ("delivery", "contains", "6130", "GST", 75),
    ("rent", "contains", "6140", "GST", 90),
    ("lease", "contains", "6140", "GST", 75),
    ("google ads", "contains", "6150", "GST", 95),
    ("advertising", "contains", "6150", "GST", 90),
    ("marketing", "contains", "6150", "GST", 80),
    ("accounting", "contains", "6160", "GST", 90),
    ("bookkeeping", "contains", "6160", "GST", 90),
    ("legal", "contains", "6160", "GST", 90),
    ("consulting", "contains", "6160", "GST", 75),
    ("petrol", "contains", "6170", "GST", 90),
    ("diesel", "contains", "6170", "GST", 90),
    ("shell", "contains", "6170", "GST", 85),
    ("bp ", "contains", "6170", "GST", 85),
    ("uber", "contains", "6180", "GST", 80),
    ("hotel", "contains", "6180", "GST", 75),
    ("airline", "contains", "6180", "GST", 75),
    ("restaurant", "contains", "6190", "GST", 80),
    ("cafe", "contains", "6190", "GST", 70),
    ("insurance", "contains", "6200", "GST", 90),
    ("repair", "contains", "6210", "GST", 85),
    ("maintenance", "contains", "6210", "GST", 85),
    ("payroll", "contains", "6220", "N-T", 90),
    ("wages", "contains", "6220", "N-T", 90),
    ("bank fee", "contains", "6240", "GST-FREE", 90),
    ("interest", "contains", "6250", "INPUT-TAXED", 90),
    ("laptop", "contains", "1500", "CAP", 85),
    ("machinery", "contains", "1500", "CAP", 90),
    ("equipment", "contains", "1500", "CAP", 75),
]


def _normalise(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9& .-]+", " ", str(value or "").lower())).strip()


def seed_accounting_reference_data() -> None:
    con = get_duckdb()
    con.executemany(
        "INSERT OR IGNORE INTO chart_of_accounts(code, name, account_type, subtype, default_tax_code, active, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        DEFAULT_ACCOUNTS,
    )
    existing = int(con.execute("SELECT COUNT(*) FROM categorisation_rules").fetchone()[0])
    if existing == 0:
        for keyword, match_type, account_code, tax_code, priority in DEFAULT_RULES:
            rule_id = f"rule-{hashlib.sha1(f'{keyword}|{account_code}'.encode()).hexdigest()[:16]}"
            con.execute(
                "INSERT OR IGNORE INTO categorisation_rules(id, keyword, match_type, account_code, tax_code, priority, source, active, use_count, last_used_at) VALUES (?, ?, ?, ?, ?, ?, 'system', TRUE, 0, NULL)",
                (rule_id, keyword, match_type, account_code, tax_code, priority),
            )
    con.close()


def classify_invoice(supplier: str, description: str, amount: float = 0.0, connection: Any | None = None) -> dict[str, Any]:
    owns_connection = connection is None
    if owns_connection:
        seed_accounting_reference_data()
    supplier_norm = _normalise(supplier)
    description_norm = _normalise(description)
    haystack = f"{supplier_norm} {description_norm}".strip()
    con = connection or get_duckdb()
    rules = con.execute(
        "SELECT id, keyword, match_type, account_code, tax_code, priority, source FROM categorisation_rules WHERE active=TRUE ORDER BY priority DESC, length(keyword) DESC"
    ).fetchall()
    account_rows = con.execute("SELECT code, name, account_type, default_tax_code FROM chart_of_accounts WHERE active=TRUE").fetchall()
    account_lookup = {str(row[0]): {"code": str(row[0]), "name": str(row[1]), "account_type": str(row[2]), "default_tax_code": str(row[3])} for row in account_rows}
    selected = None
    for row in rules:
        rule_id, keyword, match_type, account_code, tax_code, priority, source = row
        keyword_norm = _normalise(keyword)
        matched = False
        if match_type == "supplier_exact":
            matched = supplier_norm == keyword_norm
        elif match_type == "supplier_contains":
            matched = keyword_norm in supplier_norm
        elif match_type == "description_contains":
            matched = keyword_norm in description_norm
        else:
            matched = keyword_norm in haystack
        if matched:
            selected = {
                "rule_id": str(rule_id),
                "keyword": str(keyword),
                "account_code": str(account_code),
                "tax_code": str(tax_code),
                "priority": int(priority),
                "source": str(source),
            }
            break
    if selected:
        con.execute("UPDATE categorisation_rules SET use_count=use_count+1, last_used_at=? WHERE id=?", (utc_now(), selected["rule_id"]))
        account = account_lookup.get(selected["account_code"], {"name": "Mapped account", "account_type": "expense"})
        confidence = min(0.99, 0.86 + max(0, selected["priority"] - 70) / 250)
        result = {
            **selected,
            "account_name": account.get("name"),
            "account_type": account.get("account_type"),
            "confidence": round(confidence, 2),
            "status": "auto_approved" if confidence >= 0.95 else "suggested",
            "reason": f"Matched the saved keyword '{selected['keyword']}'.",
        }
    else:
        result = {
            "rule_id": "",
            "keyword": "",
            "account_code": "6999",
            "account_name": "Uncategorised expenses",
            "account_type": "expense",
            "tax_code": "REVIEW",
            "confidence": 0.35,
            "status": "needs_review",
            "reason": "No approved supplier or keyword rule matched this invoice.",
            "source": "fallback",
        }
    # Large purchases that look capital in nature should stay reviewable even after a keyword match.
    if amount >= 1000 and result["account_code"] == "1500":
        result["status"] = "suggested"
        result["confidence"] = min(float(result["confidence"]), 0.9)
        result["reason"] += " Capital treatment and depreciation require review."
    if owns_connection:
        con.close()
    return result


def _account_name(con: Any, code: str) -> str:
    row = con.execute("SELECT name FROM chart_of_accounts WHERE code=?", (code,)).fetchone()
    return str(row[0]) if row else code


def _journal_line(con: Any, journal_id: str, line_no: int, account_code: str, debit: float, credit: float, tax_code: str, counterparty: str, source_file: str) -> None:
    line_id = f"{journal_id}-{line_no}"
    con.execute(
        "INSERT OR REPLACE INTO journal_lines(id, journal_id, line_number, account_code, account_name, debit, credit, tax_code, counterparty, source_file) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (line_id, journal_id, line_no, account_code, _account_name(con, account_code), round(debit, 2), round(credit, 2), tax_code, counterparty, source_file),
    )


def _opening_account_code(line_item: str, amount: float) -> tuple[str, bool]:
    """Map common opening-balance labels to the default chart of accounts."""
    value = _normalise(line_item)
    mappings = [
        (("accumulated depreciation",), "1590"),
        (("accounts receivable", "trade debtors"), "1100"),
        (("petty cash",), "1010"),
        (("cash", "bank"), "1000"),
        (("pre paid", "pre-paid", "prepaid"), "1150"),
        (("other current asset",), "1190"),
        (("inventory", "stock on hand"), "1200"),
        (("gst receivable", "gst credit"), "1300"),
        (("property", "land"), "1510"),
        (("vehicle", "delivery van", "motor van"), "1520"),
        (("furniture", "fitout"), "1530"),
        (("computer",), "1540"),
        (("renovation", "improvement", "leasehold"), "1550"),
        (("intangible", "goodwill"), "1560"),
        (("lease liability",), "2210"),
        (("equipment loan",), "2200"),
        (("equipment finance", "hire purchase"), "2210"),
        (("equipment", "tools", "machinery", "plant"), "1500"),
        (("accounts payable", "trade creditors"), "2000"),
        (("credit card",), "2010"),
        (("accrued wage", "accrued expense"), "2050"),
        (("gst payable",), "2100"),
        (("payg withholding",), "2300"),
        (("superannuation payable", "super payable"), "2400"),
        (("income tax", "tax payable"), "2060"),
        (("interest payable",), "2070"),
        (("loan", "borrowings"), "2200"),
        (("other current liabil", "other long term liabil", "other liability"), "2290"),
        (("owner equity", "shareholder equity", "retained earnings"), "3000"),
    ]
    for tokens, code in mappings:
        if any(token in value for token in tokens):
            return code, True
    return ("1190" if amount >= 0 else "2290"), False


def _rebuild_opening_balance_journal(con: Any) -> dict[str, Any]:
    """Post the most recent uploaded balance sheet as the ledger opening position."""
    con.execute("DELETE FROM journal_lines WHERE journal_id IN (SELECT id FROM journal_entries WHERE source_type='opening_balance')")
    con.execute("DELETE FROM journal_entries WHERE source_type='opening_balance'")
    latest = con.execute("SELECT MAX(period_end) FROM statement_snapshots WHERE statement_type='balance_sheet'").fetchone()[0]
    if latest is None:
        return {"period_end": None, "lines": 0, "unmapped_lines": 0}
    rows = con.execute(
        "SELECT line_item, amount, source_file FROM statement_snapshots WHERE statement_type='balance_sheet' AND period_end=? ORDER BY line_item",
        (latest,),
    ).fetchall()
    journal_id = "je-opening-balance"
    con.execute(
        "INSERT OR REPLACE INTO journal_entries(id, entry_date, reference, description, source_type, source_id, status, created_at) VALUES (?, ?, ?, ?, 'opening_balance', ?, 'posted', ?)",
        (journal_id, latest, f"OPEN-{latest}", f"Opening balance sheet at {latest}", str(latest), utc_now()),
    )
    line_no = 1
    total_debit = 0.0
    total_credit = 0.0
    unmapped = 0
    for line_item, raw_amount, source_file in rows:
        amount = float(raw_amount or 0)
        if abs(amount) < 0.005:
            continue
        code, mapped = _opening_account_code(str(line_item or ""), amount)
        if not mapped:
            unmapped += 1
        debit = abs(amount) if amount >= 0 else 0.0
        credit = abs(amount) if amount < 0 else 0.0
        _journal_line(con, journal_id, line_no, code, debit, credit, "N-T", str(line_item or "Opening balance"), str(source_file or ""))
        total_debit += debit
        total_credit += credit
        line_no += 1
    difference = round(total_debit - total_credit, 2)
    if abs(difference) >= 0.005:
        _journal_line(con, journal_id, line_no, "3000", 0.0 if difference > 0 else abs(difference), difference if difference > 0 else 0.0, "N-T", "Opening equity", "Opening balance sheet")
        line_no += 1
    return {"period_end": str(latest), "lines": line_no - 1, "unmapped_lines": unmapped}


def rebuild_accounting_from_sources() -> dict[str, Any]:
    """Rebuild opening balances and invoice journals as one serial write."""
    with ACCOUNTING_REBUILD_LOCK:
        return _rebuild_accounting_from_sources_locked()


def _rebuild_accounting_from_sources_locked() -> dict[str, Any]:
    seed_accounting_reference_data()
    profile = get_company_profile()
    gst_registered = bool(profile.get("gst_registered", False))
    con = get_duckdb()
    opening = _rebuild_opening_balance_journal(con)
    opening_cutoff = str(opening.get("period_end") or "")
    con.execute("DELETE FROM journal_lines WHERE journal_id IN (SELECT id FROM journal_entries WHERE source_type='invoice')")
    con.execute("DELETE FROM journal_entries WHERE source_type='invoice'")
    con.execute("DELETE FROM account_validation_tasks WHERE status='open' AND task_type='invoice_categorisation'")

    invoices = con.execute(
        "SELECT id, invoice_number, supplier, invoice_date, due_date, amount, status, source_file, invoice_kind, currency, subtotal, gst_amount, description, account_code, category, tax_code, categorisation_confidence, validation_status FROM invoices ORDER BY invoice_date, id"
    ).fetchall()
    posted = 0
    included_in_opening = 0
    review = 0
    processed = 0
    for row in invoices:
        (
            invoice_id, invoice_number, supplier, invoice_date, due_date, amount, status, source_file,
            invoice_kind, currency, subtotal, gst_amount, description, account_code, category, tax_code,
            confidence, validation_status,
        ) = row
        total = abs(float(amount or 0))
        kind = str(invoice_kind or "supplier")
        description = str(description or "")
        manual_approved = str(validation_status or "") == "approved" and bool(account_code)
        classification = classify_invoice(str(supplier or ""), description, total, con) if not manual_approved else {
            "account_code": str(account_code),
            "account_name": _account_name(con, str(account_code)),
            "tax_code": str(tax_code or "GST"),
            "confidence": float(confidence or 1.0),
            "status": "approved",
            "reason": "Previously approved by a user.",
        }
        if kind == "sales":
            classification = {
                "account_code": "4000",
                "account_name": "Sales revenue",
                "tax_code": str(tax_code or "GST"),
                "confidence": max(float(confidence or 0), 0.99),
                "status": "auto_approved",
                "reason": "Sales invoice routed to sales revenue.",
            }

        effective_tax_code = str(classification.get("tax_code") or "REVIEW")
        explicit_gst = abs(float(gst_amount or 0))
        if explicit_gst > 0:
            gst = explicit_gst
            net = abs(float(subtotal or 0)) or max(total - gst, 0)
        elif gst_registered and effective_tax_code == "GST":
            gst = round(total / 11, 2)
            net = round(total - gst, 2)
        else:
            gst = 0.0
            net = total

        validation = "approved" if classification["status"] in {"auto_approved", "approved"} else "needs_review"
        con.execute(
            "UPDATE invoices SET invoice_kind=?, currency=COALESCE(NULLIF(currency,''), ?), subtotal=?, gst_amount=?, description=?, account_code=?, category=?, tax_code=?, categorisation_confidence=?, validation_status=? WHERE id=?",
            (kind, str(currency or profile.get("reporting_currency") or "AUD"), net, gst, description, classification["account_code"], classification["account_name"], effective_tax_code, float(classification["confidence"]), validation, invoice_id),
        )

        journal_id = f"je-invoice-{invoice_id}"
        entry_description = f"{kind.title()} invoice {invoice_number} · {supplier}"
        within_opening_balance = bool(opening_cutoff and str(invoice_date or "") <= opening_cutoff)
        journal_status = (
            "draft" if validation != "approved"
            else "included_in_opening" if within_opening_balance
            else "posted"
        )
        con.execute(
            "INSERT OR REPLACE INTO journal_entries(id, entry_date, reference, description, source_type, source_id, status, created_at) VALUES (?, ?, ?, ?, 'invoice', ?, ?, ?)",
            (journal_id, invoice_date, str(invoice_number), entry_description, str(invoice_id), journal_status, utc_now()),
        )
        if kind == "sales":
            _journal_line(con, journal_id, 1, "1100", total, 0, effective_tax_code, str(supplier), str(source_file))
            _journal_line(con, journal_id, 2, "4000", 0, net, effective_tax_code, str(supplier), str(source_file))
            if gst:
                _journal_line(con, journal_id, 3, "2100", 0, gst, "GST", str(supplier), str(source_file))
        else:
            _journal_line(con, journal_id, 1, str(classification["account_code"]), net, 0, effective_tax_code, str(supplier), str(source_file))
            line_no = 2
            if gst:
                _journal_line(con, journal_id, line_no, "1300", gst, 0, "GST", str(supplier), str(source_file))
                line_no += 1
            _journal_line(con, journal_id, line_no, "2000", 0, total, effective_tax_code, str(supplier), str(source_file))

        if validation != "approved":
            task_id = f"task-{hashlib.sha1(str(invoice_id).encode()).hexdigest()[:16]}"
            con.execute(
                "INSERT OR REPLACE INTO account_validation_tasks(id, task_type, source_id, source_file, counterparty, description, amount, suggested_account_code, suggested_account_name, suggested_tax_code, confidence, reason, status, created_at, resolved_at) VALUES (?, 'invoice_categorisation', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, NULL)",
                (task_id, str(invoice_id), str(source_file), str(supplier), description or str(invoice_number), total, classification["account_code"], classification["account_name"], effective_tax_code, float(classification["confidence"]), classification["reason"], utc_now()),
            )
            review += 1
        elif within_opening_balance:
            included_in_opening += 1
        else:
            posted += 1
        processed += 1
    con.close()
    invalidate_accounting_cache()
    return {
        "opening_balance": opening,
        "processed_invoices": processed,
        "posted_invoices": posted,
        "invoices_included_in_opening_balance": included_in_opening,
        "items_needing_review": review,
    }


def invalidate_accounting_cache() -> None:
    global _ACCOUNTING_CACHE
    with ACCOUNTING_SNAPSHOT_LOCK:
        _ACCOUNTING_CACHE = None


def accounting_dashboard() -> dict[str, Any]:
    """Return the latest posted accounting snapshot without mutating the ledger.

    Rebuilds happen at startup and after source-changing actions. Keeping this
    GET path read-only prevents concurrent Accounts, Tax and Marketing requests
    from deleting and recreating the same DuckDB journal tuples. A small shared
    snapshot cache also prevents the three dashboard panels from repeating the
    same trial-balance queries during one browser refresh.
    """
    global _ACCOUNTING_CACHE
    with ACCOUNTING_SNAPSHOT_LOCK:
        if _ACCOUNTING_CACHE is not None:
            return _ACCOUNTING_CACHE
        con = get_duckdb()
        trial = con.execute(
            """
            SELECT c.code, c.name, c.account_type, c.subtype, c.default_tax_code,
                   COALESCE(SUM(l.debit),0) AS debits,
                   COALESCE(SUM(l.credit),0) AS credits,
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
            GROUP BY c.code, c.name, c.account_type, c.subtype, c.default_tax_code
            ORDER BY c.code
            """
        ).fetchall()
        accounts = [
            {
                "code": str(row[0]), "name": str(row[1]), "account_type": str(row[2]), "subtype": str(row[3]),
                "tax_code": str(row[4]), "debits": float(row[5] or 0), "credits": float(row[6] or 0), "balance": float(row[7] or 0),
            }
            for row in trial
        ]
        summary = {"assets": 0.0, "liabilities": 0.0, "equity": 0.0, "revenue": 0.0, "expenses": 0.0}
        for account in accounts:
            key = {"asset": "assets", "liability": "liabilities", "equity": "equity", "revenue": "revenue", "expense": "expenses"}.get(account["account_type"])
            if key:
                summary[key] += account["balance"]
        summary["profit"] = summary["revenue"] - summary["expenses"]
        summary["accounts_receivable"] = next((a["balance"] for a in accounts if a["code"] == "1100"), 0.0)
        summary["accounts_payable"] = next((a["balance"] for a in accounts if a["code"] == "2000"), 0.0)
        summary["gst_receivable"] = next((a["balance"] for a in accounts if a["code"] == "1300"), 0.0)
        summary["gst_payable"] = next((a["balance"] for a in accounts if a["code"] == "2100"), 0.0)
        summary["net_gst"] = summary["gst_payable"] - summary["gst_receivable"]
        summary["review_count"] = int(con.execute("SELECT COUNT(*) FROM account_validation_tasks WHERE status='open'").fetchone()[0])
        summary["draft_journal_count"] = int(con.execute("SELECT COUNT(*) FROM journal_entries WHERE status='draft'").fetchone()[0])

        journals = con.execute(
            """
            SELECT e.id, e.entry_date, e.reference, e.description, e.source_type, e.source_id, e.status,
                   SUM(l.debit) AS debit_total, SUM(l.credit) AS credit_total
            FROM journal_entries e LEFT JOIN journal_lines l ON l.journal_id=e.id
            GROUP BY e.id, e.entry_date, e.reference, e.description, e.source_type, e.source_id, e.status
            ORDER BY e.entry_date DESC, e.id DESC LIMIT 100
            """
        ).fetchall()
        journal_rows = [
            {"id": str(r[0]), "entry_date": str(r[1]), "reference": str(r[2]), "description": str(r[3]), "source_type": str(r[4]), "source_id": str(r[5]), "status": str(r[6]), "debit_total": float(r[7] or 0), "credit_total": float(r[8] or 0)}
            for r in journals
        ]
        lines = con.execute("SELECT * FROM journal_lines ORDER BY journal_id, line_number LIMIT 500").fetchall()
        line_columns = [d[0] for d in con.description]
        journal_lines = [dict(zip(line_columns, row)) for row in lines]
        tasks = con.execute("SELECT * FROM account_validation_tasks ORDER BY CASE status WHEN 'open' THEN 1 ELSE 2 END, confidence, created_at DESC LIMIT 100").fetchall()
        task_columns = [d[0] for d in con.description]
        validations = [dict(zip(task_columns, row)) for row in tasks]
        invoices = con.execute(
            "SELECT id, invoice_number, supplier, invoice_date, due_date, amount, invoice_kind, description, account_code, category, tax_code, categorisation_confidence, validation_status, source_file FROM invoices ORDER BY invoice_date DESC LIMIT 200"
        ).fetchall()
        invoice_columns = [d[0] for d in con.description]
        invoice_rows = [dict(zip(invoice_columns, row)) for row in invoices]
        con.close()
        result = {"summary": summary, "accounts": accounts, "journals": journal_rows, "journal_lines": journal_lines, "validations": validations, "invoices": invoice_rows}
        _ACCOUNTING_CACHE = result
        return result


def resolve_invoice_categorisation(invoice_id: str, account_code: str, tax_code: str, remember: bool = True, note: str = "") -> dict[str, Any]:
    seed_accounting_reference_data()
    con = get_duckdb()
    account = con.execute("SELECT name FROM chart_of_accounts WHERE code=? AND active=TRUE", (account_code,)).fetchone()
    if not account:
        con.close()
        raise ValueError("The selected account code does not exist.")
    invoice = con.execute("SELECT supplier, description FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not invoice:
        con.close()
        raise ValueError("Invoice not found.")
    supplier, description = str(invoice[0] or ""), str(invoice[1] or "")
    con.execute(
        "UPDATE invoices SET account_code=?, category=?, tax_code=?, categorisation_confidence=1.0, validation_status='approved' WHERE id=?",
        (account_code, str(account[0]), tax_code, invoice_id),
    )
    con.execute("UPDATE account_validation_tasks SET status='resolved', resolved_at=?, reason=CASE WHEN ?='' THEN reason ELSE reason || ' User note: ' || ? END WHERE source_id=? AND task_type='invoice_categorisation'", (utc_now(), note, note, invoice_id))
    if remember and supplier.strip():
        keyword = _normalise(supplier)
        rule_id = f"rule-user-{hashlib.sha1(f'{keyword}|{account_code}|{tax_code}'.encode()).hexdigest()[:16]}"
        con.execute(
            "INSERT OR REPLACE INTO categorisation_rules(id, keyword, match_type, account_code, tax_code, priority, source, active, use_count, last_used_at) VALUES (?, ?, 'supplier_exact', ?, ?, 200, 'user', TRUE, 0, NULL)",
            (rule_id, keyword, account_code, tax_code),
        )
    con.close()
    rebuild_accounting_from_sources()
    return accounting_dashboard()


def add_categorisation_rule(keyword: str, account_code: str, tax_code: str = "GST", match_type: str = "contains") -> dict[str, Any]:
    seed_accounting_reference_data()
    keyword_norm = _normalise(keyword)
    if not keyword_norm:
        raise ValueError("A keyword or supplier name is required.")
    con = get_duckdb()
    if not con.execute("SELECT 1 FROM chart_of_accounts WHERE code=?", (account_code,)).fetchone():
        con.close()
        raise ValueError("The selected account code does not exist.")
    rule_id = f"rule-user-{hashlib.sha1(f'{keyword_norm}|{account_code}|{tax_code}|{match_type}'.encode()).hexdigest()[:16]}"
    con.execute(
        "INSERT OR REPLACE INTO categorisation_rules(id, keyword, match_type, account_code, tax_code, priority, source, active, use_count, last_used_at) VALUES (?, ?, ?, ?, ?, 150, 'user', TRUE, 0, NULL)",
        (rule_id, keyword_norm, match_type, account_code, tax_code),
    )
    con.close()
    rebuild_accounting_from_sources()
    return {"ok": True, "id": rule_id}
