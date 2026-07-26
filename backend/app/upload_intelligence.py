from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analytics import financial_snapshot
from .config import settings
from .database import (
    COMPANY_ID,
    get_sqlite,
    get_uploaded_file,
    list_uploaded_files,
    pipeline_status,
    rows_as_dicts,
    save_upload_analysis,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


DOCUMENT_CATALOGUE: list[dict[str, Any]] = [
    {
        "id": "balance_sheet", "label": "Balance Sheet", "intake_category": "setup", "tier": "required",
        "description": "Assets, liabilities and equity at a point in time.",
        "automation": "Builds liquidity, leverage, working-capital and financial-health measures.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "profit_loss", "label": "Income Statement (Profit & Loss)", "intake_category": "setup", "tier": "required",
        "description": "Revenue, expenses and profit over a reporting period.",
        "automation": "Builds profitability, margin, cost and trend analysis.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "cash_flow_statement", "label": "Cash Flow Statement", "intake_category": "setup", "tier": "required",
        "description": "Operating, investing and financing cash movement.",
        "automation": "Improves cash viability, runway and funding analysis.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "chart_of_accounts", "label": "Chart of Accounts (COA)", "intake_category": "setup", "tier": "required",
        "description": "The account structure used to classify every transaction.",
        "automation": "Improves deterministic categorisation and consistent journal posting.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "business_requirements", "label": "Business Requirement Document (BRD)", "intake_category": "setup", "tier": "required",
        "description": "Business goals, constraints, users and reporting outcomes.",
        "automation": "Aligns the agent's recommendations and generated files with the project objective.",
        "accepted": ["PDF", "CSV", "XLSX"],
    },
    {
        "id": "fixed_asset_register", "label": "Fixed Asset Register", "intake_category": "setup", "tier": "recommended",
        "description": "Equipment, property, acquisition dates and carrying values.",
        "automation": "Supports depreciation schedules and asset-control checks.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "aged_debtors_creditors", "label": "Aged Debtor / Creditor Reports", "intake_category": "setup", "tier": "recommended",
        "description": "Outstanding customer and supplier balances by age.",
        "automation": "Highlights collection pressure, overdue payables and cash-flow risk.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "material_contracts", "label": "Material Contracts", "intake_category": "setup", "tier": "recommended",
        "description": "Long-term supplier, customer, lease or finance commitments.",
        "automation": "Adds commitment, renewal and concentration context to risk analysis.",
        "accepted": ["PDF"],
    },
    {
        "id": "sales_forecast", "label": "Sales Forecasts", "intake_category": "setup", "tier": "recommended",
        "description": "Expected orders, revenue and timing assumptions.",
        "automation": "Improves forward cash-flow and scenario analysis.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "personnel_plan", "label": "Personnel Plan", "intake_category": "setup", "tier": "recommended",
        "description": "Roles, headcount, remuneration and hiring plans.",
        "automation": "Adds workforce cost and capacity assumptions to forecasts.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "use_cases_user_stories", "label": "Use Cases and User Stories", "intake_category": "setup", "tier": "recommended",
        "description": "How owners, accountants, lenders and other users consume outputs.",
        "automation": "Guides dashboard priorities and contextual document generation.",
        "accepted": ["PDF", "CSV", "XLSX"],
    },
    {
        "id": "historical_tax_returns", "label": "Historical Tax Returns", "intake_category": "setup", "tier": "recommended",
        "description": "Prior reported earnings, tax positions and multi-year context.",
        "automation": "Supports long-term trend checks and tax reconciliation.",
        "accepted": ["PDF", "CSV", "XLSX"],
    },
    {
        "id": "supplier_invoices", "label": "All Invoices / Receipts", "intake_category": "recurring", "tier": "operational",
        "description": "Supplier invoices, bills and business receipts.",
        "automation": "Extracts vendor, date, amount and GST from structured files and digital-text PDFs; scanned PDFs are routed for OCR or review.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "bank_statements", "label": "Bank Statements", "intake_category": "recurring", "tier": "operational",
        "description": "Bank transactions and running balances.",
        "automation": "Updates cash and performs deterministic reference/amount matching against invoices where evidence permits.",
        "accepted": ["CSV", "XLSX", "XLSM"],
    },
    {
        "id": "sales_invoices", "label": "Sales Invoices", "intake_category": "recurring", "tier": "operational",
        "description": "Invoices issued to customers.",
        "automation": "Updates accounts receivable and identifies unpaid or overdue customer debt.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
    {
        "id": "payroll", "label": "Payroll Reports", "intake_category": "recurring", "tier": "operational",
        "description": "Gross pay, PAYG withholding, superannuation and payroll periods.",
        "automation": "Stores payroll evidence and prepares PAYG/super review inputs; posting remains review-required unless fields are mapped.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    },
]

CATALOGUE_BY_ID = {item["id"]: item for item in DOCUMENT_CATALOGUE}
ALIASES = {
    "invoices": "supplier_invoices",
    "assets": "balance_sheet",
    "liabilities": "balance_sheet",
    "assets_liabilities": "balance_sheet",
    "transactions": "bank_statements",
    "budgets": "sales_forecast",
    "contracts": "material_contracts",
}


def descriptor(document_type: str, intake_category: str = "recurring") -> dict[str, Any]:
    key = ALIASES.get(document_type, document_type)
    item = CATALOGUE_BY_ID.get(key)
    if item:
        return dict(item)
    return {
        "id": document_type,
        "label": document_type.replace("_", " ").title(),
        "intake_category": intake_category,
        "tier": "operational" if intake_category == "recurring" else "recommended",
        "description": "Uploaded business evidence.",
        "automation": "Preserved, profiled and made available to Ledger for contextual analysis.",
        "accepted": ["CSV", "XLSX", "XLSM", "PDF"],
    }


def company_context_path() -> Path:
    path = settings.data_path / "context" / COMPANY_ID / "company_ai_context.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def market_intelligence_path() -> Path:
    path = settings.data_path / "context" / COMPANY_ID / "market_intelligence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _empty_company_context() -> dict[str, Any]:
    now = _now()
    return {
        "version": 2,
        "created_at": now,
        "updated_at": now,
        "onboarding": {
            "status": "not_started",
            "first_upload_id": None,
            "greeting": "",
            "company_guide": [],
        },
        "document_coverage": {"required_received": [], "required_missing": [], "recommended_received": [], "recommended_missing": []},
        "operating_snapshot": {},
        "upload_history": [],
        "market_intelligence": {
            "status": "not_started",
            "last_started_at": None,
            "last_completed_at": None,
            "summary": "Deep competitor and market analysis has not been initialised.",
            "result_file": str(market_intelligence_path()),
        },
    }


def read_company_context() -> dict[str, Any]:
    path = company_context_path()
    if not path.exists():
        payload = _empty_company_context()
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("company context is not an object")
        base = _empty_company_context()
        base.update(payload)
        base["onboarding"] = {**_empty_company_context()["onboarding"], **dict(payload.get("onboarding") or {})}
        base["market_intelligence"] = {**_empty_company_context()["market_intelligence"], **dict(payload.get("market_intelligence") or {})}
        return base
    except Exception:
        payload = _empty_company_context()
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload


def write_company_context(payload: dict[str, Any]) -> dict[str, Any]:
    payload["updated_at"] = _now()
    company_context_path().write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def _source_rows(document_type: str, filename: str) -> list[dict[str, Any]]:
    if document_type in {"balance_sheet", "profit_loss", "cash_flow_statement"}:
        return rows_as_dicts(
            "SELECT line_item, amount, period_start, period_end, currency FROM statement_snapshots WHERE source_file=? AND statement_type=? ORDER BY ABS(amount) DESC LIMIT 20",
            (filename, document_type),
        )
    if document_type in {"supplier_invoices", "sales_invoices", "invoices"}:
        return rows_as_dicts(
            "SELECT invoice_number, supplier, invoice_date, due_date, amount, subtotal, gst_amount, status, invoice_kind FROM invoices WHERE source_file=? ORDER BY invoice_date DESC LIMIT 30",
            (filename,),
        )
    if document_type == "bank_statements":
        return rows_as_dicts(
            "SELECT transaction_date, description, account_name, amount, balance, currency FROM bank_transactions WHERE source_file=? ORDER BY transaction_date DESC LIMIT 40",
            (filename,),
        )
    if document_type == "payments":
        return rows_as_dicts(
            "SELECT payment_date, reference, counterparty, amount, currency, status FROM payments WHERE source_file=? ORDER BY payment_date DESC LIMIT 40",
            (filename,),
        )
    if document_type in {"assets", "liabilities", "assets_liabilities"}:
        return rows_as_dicts(
            "SELECT name, category, classification, amount, status FROM assets_liabilities WHERE source_file=? ORDER BY ABS(amount) DESC LIMIT 30",
            (filename,),
        )
    if document_type == "payroll":
        return rows_as_dicts(
            "SELECT pay_period, employee, gross_pay, ordinary_time_earnings, payg_withholding, superannuation, net_pay, currency, status FROM payroll_records WHERE source_file=? ORDER BY pay_period DESC LIMIT 50",
            (filename,),
        )
    if document_type == "market_context":
        return rows_as_dicts(
            "SELECT signal_type, topic, entity, geography, direction, relevance_score, estimated_impact FROM market_signals WHERE source_file=? ORDER BY relevance_score DESC NULLS LAST LIMIT 30",
            (filename,),
        )
    return rows_as_dicts(
        "SELECT title, record_json, source_row FROM generic_documents WHERE source_file=? ORDER BY source_row LIMIT 20",
        (filename,),
    )


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _bank_reconciliation_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    invoices = rows_as_dicts("SELECT invoice_number, supplier, amount, status FROM invoices")
    matched_invoice_ids: set[str] = set()
    matched_transactions = 0
    for transaction in rows:
        description = str(transaction.get("description") or "").lower()
        amount = abs(float(transaction.get("amount") or 0))
        for invoice in invoices:
            invoice_number = str(invoice.get("invoice_number") or "").lower()
            supplier = str(invoice.get("supplier") or "").lower()
            invoice_amount = abs(float(invoice.get("amount") or 0))
            reference_match = bool(invoice_number and invoice_number in description)
            supplier_match = bool(supplier and len(supplier) >= 4 and supplier in description)
            amount_match = abs(invoice_amount - amount) <= 0.01 and amount > 0
            if amount_match and (reference_match or supplier_match):
                matched_transactions += 1
                matched_invoice_ids.add(str(invoice.get("invoice_number") or invoice.get("supplier") or len(matched_invoice_ids)))
                break
    return {
        "matched_bank_transactions": matched_transactions,
        "matched_invoices": len(matched_invoice_ids),
        "unmatched_bank_transactions": max(0, len(rows) - matched_transactions),
        "invoice_records_considered": len(invoices),
        "method": "Exact amount plus invoice-number or counterparty reference",
    }


def _analysis_points(document_type: str, rows: list[dict[str, Any]], result: dict[str, Any]) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    impacts: list[str] = []
    if document_type in {"supplier_invoices", "sales_invoices", "invoices"}:
        total = sum(float(item.get("amount") or 0) for item in rows)
        gst = sum(float(item.get("gst_amount") or 0) for item in rows)
        counterparties = sorted({str(item.get("supplier") or "").strip() for item in rows if str(item.get("supplier") or "").strip()})
        findings.append(f"Read {len(rows)} invoice record(s) totalling {_money(total)}, including {_money(gst)} recorded GST.")
        if counterparties:
            findings.append(f"Counterparties identified: {', '.join(counterparties[:4])}{'…' if len(counterparties) > 4 else ''}.")
        if document_type == "sales_invoices":
            impacts.extend(["Accounts receivable and unpaid-customer tracking were refreshed.", "Revenue and GST-on-sales context may have changed."])
        else:
            impacts.extend(["Accounts payable, GST-on-purchases and expense classification queues were refreshed.", "Invoice categorisation remains reviewable where confidence is low."])
    elif document_type == "bank_statements":
        inflow = sum(max(float(item.get("amount") or 0), 0) for item in rows)
        outflow = sum(abs(min(float(item.get("amount") or 0), 0)) for item in rows)
        ending = next((float(item.get("balance") or 0) for item in rows if item.get("balance") is not None), 0)
        findings.append(f"Read {len(rows)} bank transaction(s): {_money(inflow)} inflow and {_money(outflow)} outflow.")
        if ending:
            findings.append(f"Latest available running balance in this file is {_money(ending)}.")
        reconciliation = _bank_reconciliation_summary(rows)
        findings.append(
            f"Deterministic reconciliation matched {reconciliation['matched_bank_transactions']} bank transaction(s) to {reconciliation['matched_invoices']} invoice reference(s); {reconciliation['unmatched_bank_transactions']} transaction(s) remain unmatched."
        )
        impacts.extend(["Cash, transaction history and duplicate-payment checks were refreshed.", "Invoice payment evidence was reconciled using exact amount plus invoice-number or counterparty references; unmatched items remain reviewable."])
    elif document_type in {"balance_sheet", "assets", "liabilities", "assets_liabilities"}:
        values = [(str(item.get("line_item") or item.get("name") or "Item"), float(item.get("amount") or 0)) for item in rows]
        findings.append(f"Read {len(rows)} balance-sheet line item(s).")
        if values:
            top = ", ".join(f"{name} ({_money(abs(amount))})" for name, amount in sorted(values, key=lambda pair: abs(pair[1]), reverse=True)[:4])
            findings.append(f"Largest reported positions: {top}.")
        impacts.extend(["Liquidity, leverage, working capital and account balances were refreshed.", "This file contributes to the company baseline used by the agent."])
    elif document_type == "profit_loss":
        positive = sum(max(float(item.get("amount") or 0), 0) for item in rows)
        negative = sum(abs(min(float(item.get("amount") or 0), 0)) for item in rows)
        findings.append(f"Read {len(rows)} profit-and-loss line item(s), with {_money(positive)} positive and {_money(negative)} negative reported values.")
        impacts.extend(["Revenue, cost, profit and margin analysis were refreshed.", "Taxable-profit context may change after account and tax-code review."])
    elif document_type == "cash_flow_statement":
        net = sum(float(item.get("amount") or 0) for item in rows)
        findings.append(f"Read {len(rows)} cash-flow line item(s) with a net reported movement of {_money(net)}.")
        impacts.extend(["Cash viability and forecast context were refreshed.", "Statement-to-ledger reconciliation can now use this source."])
    elif document_type == "payroll":
        gross = sum(float(item.get("gross_pay") or 0) for item in rows)
        ote = sum(float(item.get("ordinary_time_earnings") or item.get("gross_pay") or 0) for item in rows)
        payg = sum(float(item.get("payg_withholding") or 0) for item in rows)
        super_paid = sum(float(item.get("superannuation") or 0) for item in rows)
        net = sum(float(item.get("net_pay") or 0) for item in rows)
        expected_super = ote * float(settings.super_guarantee_rate)
        super_gap = expected_super - super_paid
        findings.append(f"Read {len(rows)} payroll record(s): {_money(gross)} gross pay, {_money(payg)} recorded PAYG withholding and {_money(super_paid)} recorded superannuation.")
        findings.append(f"At the configured {settings.super_guarantee_rate * 100:.1f}% review rate, expected super on recorded ordinary-time earnings is {_money(expected_super)}; the review variance is {_money(super_gap)}.")
        if net:
            findings.append(f"Recorded net pay totals {_money(net)}.")
        impacts.extend(["Payroll, PAYG withholding and superannuation review inputs were refreshed.", "This is a deterministic review calculation; employee-specific PAYG remains based on the uploaded payroll system values and must be validated before lodgment."])
    elif document_type == "market_context":
        findings.append(f"Read {len(rows)} market or competitor signal(s).")
        topics = [str(item.get("topic") or "") for item in rows if item.get("topic")]
        if topics:
            findings.append(f"Highest-priority topics include {', '.join(topics[:4])}.")
        impacts.extend(["Market exposure and external-risk context were refreshed.", "The opt-in competitor intelligence page can use these verified signals."])
    else:
        findings.append(f"Preserved and profiled {int(result.get('rows_imported') or 0)} structured row(s) from this business document.")
        if result.get("columns"):
            findings.append(f"Recognised fields include {', '.join(str(item) for item in result['columns'][:8])}.")
        impacts.append("The source is now available to Ledger's file context and future task-specific analysis.")

    processing = result.get("processing") or {}
    changed = int(processing.get("changed") or 0)
    unchanged = int(processing.get("unchanged") or 0)
    if changed:
        impacts.append(f"{changed} existing business record(s) were versioned and updated.")
    if unchanged:
        impacts.append(f"{unchanged} unchanged row(s) were skipped to save processing and model tokens.")
    if result.get("needs_mapping"):
        impacts.append("The source is safely stored, but unresolved field mapping prevents it from changing final metrics.")
    if result.get("duplicate"):
        impacts = ["The exact file already existed, so LedgerFlow avoided duplicate processing and database changes."]
    return findings, impacts


def build_upload_analysis(result: dict[str, Any], prior_completed_uploads: int) -> tuple[dict[str, Any], str, str]:
    upload_id = int(result.get("upload_id") or 0)
    filename = str(result.get("filename") or "uploaded file")
    document_type = str(result.get("document_type") or "generic")
    intake_category = str(result.get("intake_category") or "recurring")
    doc = descriptor(document_type, intake_category)
    rows = _source_rows(document_type, filename)
    findings, impacts = _analysis_points(document_type, rows, result)
    upload_record = get_uploaded_file(upload_id) or {}
    metadata = dict(upload_record.get("metadata") or {})
    text_preview = str(metadata.get("text_preview") or "").strip()
    if not rows and text_preview:
        compact_lines = [re.sub(r"\s+", " ", line).strip() for line in text_preview.splitlines() if line.strip()]
        preview = " ".join(compact_lines[:5])[:520]
        findings = [
            f"Read {len(text_preview):,} characters of document text using {str(metadata.get('extraction_method') or 'document text extraction').replace('_', ' ')}.",
            f"Document preview: {preview}" if preview else "Document text was captured for agent context.",
        ]
        impacts = [
            "The document is now available to the agent for contextual explanation and company guidance.",
            "No structured financial values were posted from this prose/PDF source; map or upload a structured export before it changes accounting ratios.",
        ]
    is_initial = prior_completed_uploads == 0
    lifecycle = "initial_setup" if is_initial else "incremental_update"
    if result.get("duplicate") and result.get("category_changed"):
        lifecycle = "category_corrected"
    elif result.get("duplicate"):
        lifecycle = "duplicate_ignored"
    elif result.get("needs_mapping"):
        lifecycle = "awaiting_mapping"

    analysis = {
        "upload_id": upload_id,
        "analysed_at": _now(),
        "filename": filename,
        "document_type": document_type,
        "document_label": doc["label"],
        "intake_category": intake_category,
        "tier": doc["tier"],
        "lifecycle_phase": lifecycle,
        "is_initial_company_file": is_initial,
        "rows_imported": int(result.get("rows_imported") or 0),
        "processing": result.get("processing") or {},
        "data_version": int(result.get("data_version") or 0),
        "baseline_version": int(result.get("baseline_version") or 0),
        "affected_metrics": list(result.get("affected_metrics") or []),
        "findings": findings,
        "business_impact": impacts,
        "issues": list(result.get("issues") or [])[:12],
        "storage": result.get("storage") or "Local business evidence store",
        "model_required": False,
        "analysis_method": "Deterministic document rules, verified imported records and bounded source-text analysis",
        "text_preview_available": bool(text_preview),
        "extraction_method": metadata.get("extraction_method"),
    }

    if lifecycle == "category_corrected":
        destination = "Permanent setup" if intake_category == "setup" else "Recurring evidence"
        message = f"{filename} already existed, so I moved the existing source to {destination} without duplicating any business records."
    elif lifecycle == "duplicate_ignored":
        message = f"I recognised {filename} as {doc['label']}. It is an exact duplicate, so I did not alter the database."
    elif lifecycle == "awaiting_mapping":
        message = f"I recognised {filename} as {doc['label']} and stored it safely. Some fields still need mapping before I can incorporate it into reporting."
    elif is_initial:
        lead = findings[0] if findings else "The first source has been preserved and profiled."
        message = (
            f"Your initial company file is set up. I identified {filename} as {doc['label']}. {lead} "
            "I created the company AI context, refreshed the baseline, and will guide you through the remaining core documents."
        )
    else:
        lead = findings[0] if findings else f"I read {filename}."
        message = (
            f"I identified {filename} as {doc['label']}. {lead} "
            f"It has been incorporated into data version {analysis['data_version'] or 'the current dataset'}, and the affected dashboards and agent context were updated."
        )
    return analysis, message, lifecycle


def _canonical_document_type(value: Any) -> str:
    key = str(value or "").strip().lower()
    return ALIASES.get(key, key)


def _filename_document_hint(filename: str) -> str:
    signal = re.sub(r"[^a-z0-9]+", "_", str(filename or "").lower())
    hints = [
        ("cash_flow_statement", ("cash_flow", "cashflow")),
        ("business_requirements", ("business_requirements", "business_requirement", "brd")),
        ("chart_of_accounts", ("chart_of_accounts", "chart_accounts", "coa")),
        ("profit_loss", ("profit_loss", "profit_and_loss", "income_statement", "p_l")),
        ("balance_sheet", ("balance_sheet", "assets_liabilities")),
        ("fixed_asset_register", ("fixed_asset", "asset_register")),
        ("aged_debtors_creditors", ("aged_debtor", "aged_creditor", "ageing")),
        ("material_contracts", ("material_contract", "supplier_contract", "agreement")),
        ("sales_forecast", ("sales_forecast", "forecast")),
        ("personnel_plan", ("personnel_plan", "headcount_plan")),
        ("use_cases_user_stories", ("use_cases", "user_stories")),
        ("historical_tax_returns", ("historical_tax", "tax_return")),
        ("bank_statements", ("bank_statement",)),
        ("sales_invoices", ("sales_invoice",)),
        ("payroll", ("payroll",)),
        ("supplier_invoices", ("supplier_invoice", "receipt", "tax_invoice")),
        ("market_context", ("market_context", "competitor")),
    ]
    for document_type, tokens in hints:
        if any(token in signal for token in tokens):
            return document_type
    return ""


def _upload_document_types(item: dict[str, Any], include_intent: bool = False) -> set[str]:
    values: set[str] = set()
    primary = _canonical_document_type(item.get("document_type"))
    if primary and primary not in {"profiling", "mixed_business_workbook", "generic"}:
        values.add(primary)
    metadata = dict(item.get("metadata") or {})
    for detected in metadata.get("detected_document_types") or []:
        canonical = _canonical_document_type(detected)
        if canonical and canonical not in {"profiling", "generic"}:
            values.add(canonical)
    analysis = dict(item.get("analysis") or {})
    analysis_type = _canonical_document_type(analysis.get("document_type"))
    if analysis_type and analysis_type not in {"profiling", "generic"}:
        values.add(analysis_type)
    declared = _canonical_document_type(item.get("declared_document_type"))
    if declared and declared != "auto":
        values.add(declared)
    if include_intent and not values:
        hinted = _filename_document_hint(str(item.get("filename") or ""))
        if hinted:
            values.add(hinted)
    return values


def _coverage_from_uploads(uploads: list[dict[str, Any]]) -> dict[str, list[str]]:
    # A card turns green only after a valid, coverage-eligible setup upload.
    # Detected sheet types are included so mixed workbooks can satisfy more than
    # one document category. Failed files remain visible as retry attempts.
    valid_statuses = {"committed", "stored_source", "pending_mapping"}
    setup_received_types: set[str] = set()
    recurring_received_types: set[str] = set()
    for item in uploads:
        if str(item.get("processing_status") or "") not in valid_statuses:
            continue
        category = str(item.get("intake_category") or "recurring")
        if category == "setup":
            setup_received_types.update(_upload_document_types(item))
        else:
            recurring_received_types.update(_upload_document_types(item))
    required = [item for item in DOCUMENT_CATALOGUE if item["intake_category"] == "setup" and item["tier"] == "required"]
    recommended = [item for item in DOCUMENT_CATALOGUE if item["intake_category"] == "setup" and item["tier"] == "recommended"]
    recurring = [item for item in DOCUMENT_CATALOGUE if item["intake_category"] == "recurring"]
    return {
        "required_received": [item["id"] for item in required if item["id"] in setup_received_types],
        "required_missing": [item["id"] for item in required if item["id"] not in setup_received_types],
        "recommended_received": [item["id"] for item in recommended if item["id"] in setup_received_types],
        "recommended_missing": [item["id"] for item in recommended if item["id"] not in setup_received_types],
        "recurring_received": [item["id"] for item in recurring if item["id"] in recurring_received_types],
        "recurring_missing": [item["id"] for item in recurring if item["id"] not in recurring_received_types],
    }


def incorporate_upload_into_context(analysis: dict[str, Any], assistant_message: str) -> dict[str, Any]:
    context = read_company_context()
    # A repeated file is a transient upload-job result, not a new company event.
    # Do not overwrite the original file's successful analysis with a duplicate
    # warning merely because the same bytes were selected again.
    if str(analysis.get("lifecycle_phase") or "") == "duplicate_ignored":
        return context
    uploads = list_uploaded_files()
    coverage = _coverage_from_uploads(uploads)
    history = list(context.get("upload_history") or [])
    history = [item for item in history if int(item.get("upload_id") or 0) != int(analysis.get("upload_id") or 0)]
    history.append(analysis)
    history = history[-60:]
    context["upload_history"] = history
    context["document_coverage"] = coverage
    context["operating_snapshot"] = financial_snapshot()
    context["pipeline"] = {
        key: value for key, value in pipeline_status().items()
        if key in {"data_version", "baseline_version", "uploads", "mapped_uploads", "rows_new", "rows_changed", "rows_unchanged", "document_coverage"}
    }
    onboarding = dict(context.get("onboarding") or {})
    if analysis.get("is_initial_company_file") or onboarding.get("status") == "not_started":
        onboarding.update({
            "status": "started",
            "first_upload_id": onboarding.get("first_upload_id") or analysis.get("upload_id"),
            "started_at": onboarding.get("started_at") or _now(),
            "greeting": assistant_message,
        })
    missing_labels = [CATALOGUE_BY_ID[item]["label"] for item in coverage["required_missing"] if item in CATALOGUE_BY_ID]
    onboarding["company_guide"] = [
        "Review the company profile so Ledger uses the correct industry, location, tax and operating objective.",
        ("Add the remaining core documents: " + ", ".join(missing_labels)) if missing_labels else "All core setup document categories are represented; review mappings and reporting periods.",
        "Continue adding invoices, bank statements, sales invoices and payroll reports through Recurring evidence.",
        "Start competitor intelligence only when you are ready for deeper market processing.",
    ]
    if not coverage["required_missing"]:
        onboarding["status"] = "core_documents_received"
    context["onboarding"] = onboarding
    write_company_context(context)
    save_upload_analysis(int(analysis["upload_id"]), analysis, assistant_message, str(analysis["lifecycle_phase"]))
    return context



def rebuild_company_context_from_uploads() -> dict[str, Any]:
    """Recalculate durable company context after a file is moved or removed."""
    uploads = list_uploaded_files()
    previous = read_company_context()
    context = _empty_company_context()
    context["market_intelligence"] = previous.get("market_intelligence", context.get("market_intelligence", {}))
    coverage = _coverage_from_uploads(uploads)
    history: list[dict[str, Any]] = []
    for item in sorted(uploads, key=lambda row: int(row.get("id") or 0)):
        analysis = dict(item.get("analysis") or {})
        if not analysis:
            continue
        analysis["intake_category"] = str(item.get("intake_category") or analysis.get("intake_category") or "recurring")
        analysis["document_type"] = str(item.get("document_type") or analysis.get("document_type") or "generic")
        history.append(analysis)
    context["upload_history"] = history[-60:]
    context["document_coverage"] = coverage
    context["operating_snapshot"] = financial_snapshot()
    status = pipeline_status()
    context["pipeline"] = {
        key: value for key, value in status.items()
        if key in {"data_version", "baseline_version", "uploads", "mapped_uploads", "rows_new", "rows_changed", "rows_unchanged", "document_coverage"}
    }
    onboarding = dict(context.get("onboarding") or {})
    if uploads:
        first = min(uploads, key=lambda row: int(row.get("id") or 0))
        onboarding.update({
            "status": "core_documents_received" if not coverage["required_missing"] else "started",
            "first_upload_id": int(first.get("id") or 0),
            "started_at": str(first.get("created_at") or _now()),
            "greeting": str(first.get("assistant_message") or "Company evidence is available."),
        })
        missing_labels = [CATALOGUE_BY_ID[item]["label"] for item in coverage["required_missing"] if item in CATALOGUE_BY_ID]
        onboarding["company_guide"] = [
            "Review the company profile so Ledger uses the correct industry, location, tax and operating objective.",
            ("Add the remaining core documents: " + ", ".join(missing_labels)) if missing_labels else "All core setup document categories are represented; review mappings and reporting periods.",
            "Continue adding invoices, bank statements, sales invoices and payroll reports through Recurring evidence.",
            "Start competitor intelligence only when you are ready for deeper market processing.",
        ]
    context["onboarding"] = onboarding
    write_company_context(context)
    return context

def upload_library() -> dict[str, Any]:
    uploads = list_uploaded_files()
    grouped: dict[str, list[dict[str, Any]]] = {"setup": [], "recurring": []}
    for item in uploads:
        category = str(item.get("intake_category") or "recurring")
        doc = descriptor(str(item.get("document_type") or "generic"), category)
        card = {
            "id": item.get("id"),
            "filename": item.get("filename"),
            "document_type": item.get("document_type"),
            "declared_document_type": item.get("declared_document_type") or "auto",
            "suggested_document_type": next(iter(_upload_document_types(item, include_intent=True)), str(item.get("document_type") or "auto")),
            "document_label": doc["label"],
            "tier": doc["tier"],
            "intake_category": category,
            "rows_imported": item.get("rows_imported"),
            "processing_status": item.get("processing_status"),
            "lifecycle_phase": item.get("lifecycle_phase") or (item.get("analysis") or {}).get("lifecycle_phase") or "",
            "display_status": "skipped_duplicate" if str(item.get("lifecycle_phase") or (item.get("analysis") or {}).get("lifecycle_phase") or "") == "duplicate_ignored" else item.get("processing_status"),
            "mapping_status": item.get("mapping_status"),
            "mapping_confidence": item.get("mapping_confidence"),
            "data_version": item.get("data_version"),
            "created_at": item.get("created_at"),
            "last_processed_at": item.get("last_processed_at"),
            "assistant_message": item.get("assistant_message"),
            "analysis": item.get("analysis") or {},
            "file_size": item.get("file_size"),
        }
        grouped.setdefault(category, []).append(card)
    coverage = _coverage_from_uploads(uploads)
    catalogue = {"setup_required": [], "setup_recommended": [], "recurring": []}
    valid_statuses = {"committed", "stored_source", "pending_mapping"}
    for item in DOCUMENT_CATALOGUE:
        record = dict(item)
        attempted = [
            upload for upload in uploads
            if str(upload.get("intake_category") or "recurring") == item["intake_category"]
            and item["id"] in _upload_document_types(upload, include_intent=True)
        ]
        matching = [upload for upload in attempted if str(upload.get("processing_status") or "") in valid_statuses]
        retryable = [upload for upload in attempted if str(upload.get("processing_status") or "") not in valid_statuses]
        record["received"] = bool(matching)
        record["file_count"] = len(matching)
        record["attempt_count"] = len(attempted)
        record["retry_count"] = len(retryable)
        record["state"] = "received" if matching else "needs_retry" if retryable else "missing"
        if item["intake_category"] == "recurring": catalogue["recurring"].append(record)
        elif item["tier"] == "required": catalogue["setup_required"].append(record)
        else: catalogue["setup_recommended"].append(record)
    return {"files": grouped, "catalogue": catalogue, "coverage": coverage, "company_context_file": str(company_context_path())}


def file_context_for_prompt(user_message: str, limit: int = 8) -> dict[str, Any]:
    uploads = list_uploaded_files()
    lower = user_message.lower()
    filename_tokens = {token for token in re.findall(r"[a-z0-9_-]{3,}", lower)}
    matched: list[dict[str, Any]] = []
    for item in uploads:
        filename = str(item.get("filename") or "").lower()
        document_type = str(item.get("document_type") or "").lower()
        score = sum(1 for token in filename_tokens if token in filename or token in document_type)
        if score:
            matched.append({**item, "_score": score})
    chosen = sorted(matched, key=lambda item: int(item.get("_score") or 0), reverse=True)[:limit] if matched else uploads[:limit]
    return {
        "matched_files": [
            {
                "upload_id": item.get("id"),
                "filename": item.get("filename"),
                "document_type": item.get("document_type"),
                "intake_category": item.get("intake_category"),
                "processing_status": item.get("processing_status"),
                "mapping_status": item.get("mapping_status"),
                "rows_imported": item.get("rows_imported"),
                "data_version": item.get("data_version"),
                "analysis": item.get("analysis") or {},
                "assistant_message": item.get("assistant_message") or "",
                "metadata": {key: value for key, value in (item.get("metadata") or {}).items() if key in {"text_preview", "extracted_record", "detected_document_types", "incremental"}},
            }
            for item in chosen
        ],
        "company_ai_context": read_company_context(),
    }
