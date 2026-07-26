from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .analytics import cash_forecast, dashboard_summary
from .accounting import accounting_dashboard
from .database import get_company_profile, rows_as_dicts


DOCUMENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "sales_invoice",
        "name": "Sales invoice",
        "description": "Create a customer invoice with tax, due date, and payment instructions.",
        "formats": ["pdf", "csv"],
        "mode": "form",
    },
    {
        "id": "purchase_order",
        "name": "Purchase order",
        "description": "Create a purchase order to send to a supplier.",
        "formats": ["pdf", "csv"],
        "mode": "form",
    },
    {
        "id": "quotation",
        "name": "Quotation / estimate",
        "description": "Create a quote before confirming a customer order.",
        "formats": ["pdf", "csv"],
        "mode": "form",
    },
    {
        "id": "payment_receipt",
        "name": "Payment receipt",
        "description": "Confirm that a customer or supplier payment was received.",
        "formats": ["pdf", "csv"],
        "mode": "form",
    },
    {
        "id": "expense_claim",
        "name": "Expense claim",
        "description": "Create an employee expense reimbursement record.",
        "formats": ["pdf", "csv"],
        "mode": "form",
    },
    {
        "id": "customer_statement",
        "name": "Customer account statement",
        "description": "Build a statement from invoice records already stored in LedgerFlow.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "supplier_payment_schedule",
        "name": "Supplier payment schedule",
        "description": "Export open supplier invoices ordered by due date.",
        "formats": ["csv", "pdf"],
        "mode": "data",
    },
    {
        "id": "inventory_count_sheet",
        "name": "Inventory count sheet",
        "description": "Create a stocktake sheet from the current inventory master.",
        "formats": ["csv", "pdf"],
        "mode": "data",
    },
    {
        "id": "cash_flow_forecast",
        "name": "90-day cash-flow forecast",
        "description": "Export the current LedgerFlow cash forecast.",
        "formats": ["csv", "pdf"],
        "mode": "data",
    },
    {
        "id": "management_summary",
        "name": "Management summary",
        "description": "Create a compact PDF or CSV summary of current business performance.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "trial_balance",
        "name": "Trial balance",
        "description": "Export account debit, credit, and closing balances from the general ledger.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "general_ledger",
        "name": "General ledger",
        "description": "Export journal lines with account, tax code, counterparty, and source evidence.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "profit_loss_report",
        "name": "Profit and loss report",
        "description": "Create a ledger-based revenue and expense report.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "balance_sheet_report",
        "name": "Balance sheet report",
        "description": "Create a ledger-based assets, liabilities, and equity report.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
    {
        "id": "gst_transaction_report",
        "name": "GST transaction report",
        "description": "Export invoice GST treatment and review status for BAS preparation.",
        "formats": ["pdf", "csv"],
        "mode": "data",
    },
]


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("_")
    return cleaned or "ledgerflow_document"


def _money(value: Any, currency: str) -> str:
    try:
        return f"{currency} {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _document_number(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _form_rows(document_type: str, fields: dict[str, Any]) -> tuple[str, list[list[Any]], dict[str, Any]]:
    profile = get_company_profile()
    currency = str(fields.get("currency") or profile.get("reporting_currency") or "AUD")
    quantity = _number(fields.get("quantity"), 1.0)
    unit_price = _number(fields.get("unit_price"), _number(fields.get("amount"), 0.0))
    tax_rate = _number(fields.get("tax_rate"), 10.0)
    subtotal = quantity * unit_price
    tax = subtotal * tax_rate / 100
    total = subtotal + tax
    today = date.today()
    due_date = str(fields.get("due_date") or (today + timedelta(days=30)).isoformat())
    recipient = str(fields.get("counterparty") or fields.get("recipient") or "Counterparty")
    description = str(fields.get("description") or "Business goods or services")

    config = {
        "sales_invoice": ("Sales Invoice", "INV"),
        "purchase_order": ("Purchase Order", "PO"),
        "quotation": ("Quotation", "QTE"),
        "payment_receipt": ("Payment Receipt", "RCT"),
        "expense_claim": ("Expense Claim", "EXP"),
    }
    title, prefix = config[document_type]
    number = str(fields.get("document_number") or _document_number(prefix))

    if document_type == "payment_receipt":
        amount = _number(fields.get("amount"), total)
        rows = [["Payment date", str(fields.get("document_date") or today.isoformat())], ["Received from", recipient], ["Reference", str(fields.get("reference") or number)], ["Payment method", str(fields.get("payment_method") or "Bank transfer")], ["Amount received", _money(amount, currency)], ["Notes", str(fields.get("notes") or "")]]
    elif document_type == "expense_claim":
        amount = _number(fields.get("amount"), subtotal)
        rows = [["Claim date", str(fields.get("document_date") or today.isoformat())], ["Employee", recipient], ["Expense category", str(fields.get("category") or "General business expense")], ["Description", description], ["Amount", _money(amount, currency)], ["Tax included", str(fields.get("tax_included") or "Yes")], ["Approval status", str(fields.get("status") or "Pending")]]
    else:
        rows = [["Description", "Quantity", "Unit price", "Tax", "Line total"], [description, f"{quantity:g}", _money(unit_price, currency), f"{tax_rate:g}%", _money(total, currency)]]

    meta = {
        "title": title,
        "number": number,
        "document_date": str(fields.get("document_date") or today.isoformat()),
        "due_date": due_date,
        "recipient": recipient,
        "currency": currency,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "notes": str(fields.get("notes") or ""),
        "company": profile,
    }
    return title, rows, meta


def _data_rows(document_type: str, fields: dict[str, Any]) -> tuple[str, list[list[Any]], dict[str, Any]]:
    profile = get_company_profile()
    currency = str(profile.get("reporting_currency") or "AUD")
    meta: dict[str, Any] = {"company": profile, "currency": currency, "number": _document_number("DOC"), "document_date": date.today().isoformat(), "recipient": "", "due_date": "", "notes": ""}

    if document_type == "customer_statement":
        counterparty = str(fields.get("counterparty") or "").strip()
        records = rows_as_dicts("SELECT invoice_number, supplier, invoice_date, due_date, amount, status FROM invoices ORDER BY invoice_date DESC")
        if counterparty:
            records = [row for row in records if counterparty.lower() in str(row.get("supplier", "")).lower()]
        rows = [["Invoice", "Customer", "Invoice date", "Due date", "Amount", "Status"]]
        rows += [[row.get("invoice_number"), row.get("supplier"), row.get("invoice_date"), row.get("due_date"), _money(row.get("amount"), currency), row.get("status")] for row in records]
        title = "Customer Account Statement"
        meta["recipient"] = counterparty or "All customers"
    elif document_type == "supplier_payment_schedule":
        records = rows_as_dicts("SELECT invoice_number, supplier, invoice_date, due_date, amount, status FROM invoices WHERE lower(status) NOT IN ('paid','cancelled','void') ORDER BY due_date")
        rows = [["Invoice", "Supplier", "Invoice date", "Due date", "Amount", "Status"]]
        rows += [[row.get("invoice_number"), row.get("supplier"), row.get("invoice_date"), row.get("due_date"), _money(row.get("amount"), currency), row.get("status")] for row in records]
        title = "Supplier Payment Schedule"
    elif document_type == "inventory_count_sheet":
        records = rows_as_dicts("SELECT sku, name, quantity, unit_cost, total_value, location, status FROM inventory ORDER BY name")
        rows = [["SKU", "Item", "System quantity", "Counted quantity", "Variance", "Unit cost", "Location", "Status"]]
        rows += [[row.get("sku"), row.get("name"), row.get("quantity"), "", "", _money(row.get("unit_cost"), currency), row.get("location"), row.get("status")] for row in records]
        title = "Inventory Count Sheet"
    elif document_type == "cash_flow_forecast":
        forecast = cash_forecast(90)
        points = forecast.get("series") or forecast.get("cash_series") or []
        rows = [["Period", "Actual cash", "Forecast cash"]]
        rows += [[point.get("month") or point.get("date"), point.get("cash"), point.get("forecast")] for point in points]
        title = "90-Day Cash-Flow Forecast"
    elif document_type == "management_summary":
        summary = dashboard_summary()
        rows = [["Metric", "Value"], ["Available cash", _money(summary.get("cash"), currency)], ["Current assets", _money(summary.get("current_assets"), currency)], ["Current liabilities", _money(summary.get("current_liabilities"), currency)], ["Current ratio", summary.get("current_ratio")], ["Working capital", _money(summary.get("working_capital"), currency)], ["Monthly revenue", _money(summary.get("revenue_month"), currency)], ["Monthly expenses", _money(summary.get("expenses_month"), currency)], ["Cash runway (days)", summary.get("cash_runway_days")], ["Open invoices", _money(summary.get("open_invoice_total"), currency)], ["Overdue invoices", _money(summary.get("overdue_invoice_total"), currency)], ["Critical alerts", summary.get("critical_alerts")]]
        title = "Management Summary"
    elif document_type == "trial_balance":
        accounting = accounting_dashboard()
        rows = [["Code", "Account", "Type", "Debits", "Credits", "Balance", "Tax code"]]
        rows += [[item.get("code"), item.get("name"), item.get("account_type"), _money(item.get("debits"), currency), _money(item.get("credits"), currency), _money(item.get("balance"), currency), item.get("tax_code")] for item in accounting.get("accounts", [])]
        title = "Trial Balance"
    elif document_type == "general_ledger":
        accounting = accounting_dashboard()
        rows = [["Journal", "Line", "Account", "Account name", "Debit", "Credit", "Tax code", "Counterparty", "Source"]]
        rows += [[item.get("journal_id"), item.get("line_number"), item.get("account_code"), item.get("account_name"), _money(item.get("debit"), currency), _money(item.get("credit"), currency), item.get("tax_code"), item.get("counterparty"), item.get("source_file")] for item in accounting.get("journal_lines", [])]
        title = "General Ledger"
    elif document_type == "profit_loss_report":
        accounting = accounting_dashboard()
        relevant = [item for item in accounting.get("accounts", []) if item.get("account_type") in {"revenue", "expense"}]
        rows = [["Code", "Account", "Type", "Amount"]]
        rows += [[item.get("code"), item.get("name"), item.get("account_type"), _money(item.get("balance"), currency)] for item in relevant]
        rows += [["", "Net profit", "result", _money(accounting.get("summary", {}).get("profit"), currency)]]
        title = "Profit and Loss Report"
    elif document_type == "balance_sheet_report":
        accounting = accounting_dashboard()
        relevant = [item for item in accounting.get("accounts", []) if item.get("account_type") in {"asset", "liability", "equity"}]
        rows = [["Code", "Account", "Type", "Amount"]]
        rows += [[item.get("code"), item.get("name"), item.get("account_type"), _money(item.get("balance"), currency)] for item in relevant]
        title = "Balance Sheet Report"
    elif document_type == "gst_transaction_report":
        records = rows_as_dicts("SELECT invoice_number, supplier, invoice_date, amount, subtotal, gst_amount, invoice_kind, account_code, category, tax_code, validation_status, source_file FROM invoices ORDER BY invoice_date DESC")
        rows = [["Invoice", "Counterparty", "Date", "Total", "Subtotal", "GST", "Kind", "Account", "Category", "Tax code", "Validation", "Source"]]
        rows += [[item.get("invoice_number"), item.get("supplier"), item.get("invoice_date"), _money(item.get("amount"), currency), _money(item.get("subtotal"), currency), _money(item.get("gst_amount"), currency), item.get("invoice_kind"), item.get("account_code"), item.get("category"), item.get("tax_code"), item.get("validation_status"), item.get("source_file")] for item in records]
        title = "GST Transaction Report"
    else:
        raise ValueError("Unsupported document template.")
    return title, rows, meta


def _build_csv(title: str, rows: list[list[Any]], meta: dict[str, Any]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([title])
    writer.writerow(["Generated by", "LedgerFlow"])
    writer.writerow(["Generated at", datetime.now().isoformat(timespec="seconds")])
    if meta.get("recipient"):
        writer.writerow(["Counterparty", meta["recipient"]])
    writer.writerow([])
    writer.writerows(rows)
    if meta.get("subtotal") is not None and len(rows) > 1:
        writer.writerow([])
        writer.writerow(["Subtotal", meta.get("subtotal")])
        writer.writerow(["Tax", meta.get("tax")])
        writer.writerow(["Total", meta.get("total")])
    if meta.get("notes"):
        writer.writerow([])
        writer.writerow(["Notes", meta["notes"]])
    return buffer.getvalue().encode("utf-8-sig")


def _pdf_table(rows: list[list[Any]], available_width: float) -> Table:
    if not rows:
        rows = [["No records available"]]
    columns = max(len(row) for row in rows)
    raw_rows = [list(row) + [""] * (columns - len(row)) for row in rows]
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.4, textColor=colors.white)
    cell_style = ParagraphStyle("TableCell", parent=styles["Normal"], fontName="Helvetica", fontSize=7.2, leading=8.5, textColor=colors.HexColor("#172634"))
    normalised = [
        [Paragraph(escape(str(value if value is not None else "")), header_style if row_index == 0 else cell_style) for value in row]
        for row_index, row in enumerate(raw_rows)
    ]
    col_widths = [available_width / columns] * columns
    table = Table(normalised, colWidths=col_widths, repeatRows=1 if len(normalised) > 1 else 0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15324A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9C7D3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _build_pdf(title: str, rows: list[list[Any]], meta: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="RightSmall", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8, textColor=colors.HexColor("#526576")))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#526576")))
    story: list[Any] = []
    company = meta.get("company") or {}
    company_name = str(company.get("company_name") or "Your business")
    company_context = " | ".join(item for item in [str(company.get("primary_location") or ""), str(company.get("reporting_currency") or "")] if item)
    header = Table([
        [Paragraph(f"<b>{escape(company_name)}</b><br/><font size='8'>{escape(company_context)}</font>", styles["Normal"]), Paragraph(f"<b>{escape(title)}</b><br/><font size='8'>{escape(str(meta.get('number', '')))}</font>", styles["RightSmall"])],
    ], colWidths=[115 * mm, 63 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#2C8DB8")), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([header, Spacer(1, 7 * mm)])

    info_rows = [["Document date", meta.get("document_date", date.today().isoformat())]]
    if meta.get("recipient"):
        info_rows.append(["Counterparty", meta["recipient"]])
    if meta.get("due_date") and title not in {"Payment Receipt", "Expense Claim"}:
        info_rows.append(["Due / valid until", meta["due_date"]])
    info = Table(info_rows, colWidths=[42 * mm, 136 * mm])
    info.setStyle(TableStyle([("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (1, 0), (1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#526576")), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([info, Spacer(1, 5 * mm), _pdf_table(rows, 178 * mm)])

    if meta.get("subtotal") is not None and len(rows) > 1:
        currency = str(meta.get("currency") or "AUD")
        totals = Table([
            ["Subtotal", _money(meta.get("subtotal"), currency)],
            ["Tax", _money(meta.get("tax"), currency)],
            ["Total", _money(meta.get("total"), currency)],
        ], colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
        totals.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"), ("LINEABOVE", (0, 2), (-1, 2), 0.8, colors.HexColor("#2C8DB8")), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.extend([Spacer(1, 5 * mm), totals])

    if meta.get("notes"):
        story.extend([Spacer(1, 5 * mm), Paragraph(f"<b>Notes</b><br/>{escape(str(meta['notes']))}", styles["Muted"])])
    story.extend([Spacer(1, 9 * mm), Paragraph("Generated locally by LedgerFlow. Review before issuing externally.", styles["Muted"])])
    document.build(story)
    return buffer.getvalue()


def generate_document(document_type: str, output_format: str, fields: dict[str, Any]) -> tuple[bytes, str, str]:
    template = next((item for item in DOCUMENT_TEMPLATES if item["id"] == document_type), None)
    if not template:
        raise ValueError("Unknown document template.")
    if output_format not in template["formats"]:
        raise ValueError("The selected output format is not supported for this document.")

    if template["mode"] == "form":
        title, rows, meta = _form_rows(document_type, fields)
    else:
        title, rows, meta = _data_rows(document_type, fields)

    stem = _safe_filename(f"{document_type}_{meta.get('number') or datetime.now().strftime('%Y%m%d_%H%M%S')}")
    if output_format == "pdf":
        return _build_pdf(title, rows, meta), f"{stem}.pdf", "application/pdf"
    return _build_csv(title, rows, meta), f"{stem}.csv", "text/csv; charset=utf-8"
