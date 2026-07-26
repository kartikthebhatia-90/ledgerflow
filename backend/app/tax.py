from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .accounting import accounting_dashboard, rebuild_accounting_from_sources
from .database import get_company_profile, get_duckdb, get_integration_settings

ATO_SOURCES = [
    {
        "title": "GST for businesses",
        "url": "https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst",
        "purpose": "GST registration, reporting and credit guidance",
    },
    {
        "title": "Business record keeping",
        "url": "https://www.ato.gov.au/businesses-and-organisations/preparing-lodging-and-paying/record-keeping-for-business",
        "purpose": "Record retention and evidence obligations",
    },
    {
        "title": "Single Touch Payroll",
        "url": "https://www.ato.gov.au/businesses-and-organisations/hiring-and-paying-your-workers/single-touch-payroll",
        "purpose": "Payroll reporting obligations",
    },
    {
        "title": "Payday Super",
        "url": "https://www.ato.gov.au/businesses-and-organisations/super-for-employers/about-payday-super",
        "purpose": "Superannuation payment timing from 1 July 2026",
    },
    {
        "title": "Fringe benefits tax",
        "url": "https://www.ato.gov.au/businesses-and-organisations/hiring-and-paying-your-workers/fringe-benefits-tax",
        "purpose": "FBT registration, records and reporting",
    },
    {
        "title": "Standard Business Reporting",
        "url": "https://softwaredevelopers.ato.gov.au/sbr",
        "purpose": "Future ATO-compatible software reporting",
    },
    {
        "title": "DSP Operational Security Framework",
        "url": "https://softwaredevelopers.ato.gov.au/operational_framework",
        "purpose": "Security requirements for future direct ATO services",
    },
]


def _round(value: float) -> float:
    return round(float(value or 0), 2)


def _obligations(profile: dict[str, Any], bas: dict[str, Any], review_count: int) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    if profile.get("gst_registered"):
        obligations.append({
            "key": "bas",
            "name": "Business Activity Statement",
            "frequency": str(profile.get("bas_frequency") or "quarterly").title(),
            "status": "review" if review_count or bas["net_gst"] else "ready",
            "detail": "Review G1, 1A and 1B against the GST control accounts before lodgment.",
        })
    else:
        obligations.append({
            "key": "gst_registration",
            "name": "GST registration monitoring",
            "frequency": "Ongoing",
            "status": "information",
            "detail": "GST is disabled in the tax profile. Monitor turnover and register when required.",
        })
    obligations.append({
        "key": "income_tax",
        "name": "Income tax return workpaper",
        "frequency": "Annual",
        "status": "review",
        "detail": "Accounting profit has been converted to an indicative taxable-income estimate. Tax adjustments still require review.",
    })
    obligations.append({
        "key": "records",
        "name": "Tax and accounting record retention",
        "frequency": "Continuous",
        "status": "ready" if review_count == 0 else "review",
        "detail": "Keep original evidence, mappings, journal history and approvals together for audit traceability.",
    })
    if profile.get("has_employees") or profile.get("payg_withholding_registered"):
        obligations.extend([
            {
                "key": "stp",
                "name": "Single Touch Payroll reporting",
                "frequency": "Each pay event",
                "status": "review",
                "detail": "Payroll data integration is not yet active; W1 and W2 require payroll-source confirmation.",
            },
            {
                "key": "super",
                "name": "Payday Super",
                "frequency": "Each payday from 1 July 2026",
                "status": "review",
                "detail": "Super payment and fund-receipt dates require payroll and clearing-house integration.",
            },
            {
                "key": "fbt",
                "name": "Fringe benefits review",
                "frequency": "Annual and transaction review",
                "status": "information",
                "detail": "Review motor vehicles, entertainment, loans and employee-paid expenses for possible FBT.",
            },
        ])
    return obligations


def tax_dashboard() -> dict[str, Any]:
    accounting = accounting_dashboard()
    profile = get_company_profile()
    integrations = get_integration_settings()
    con = get_duckdb()

    sales = con.execute("SELECT COALESCE(SUM(amount),0), COALESCE(SUM(gst_amount),0) FROM invoices WHERE invoice_kind='sales' AND validation_status='approved'").fetchone()
    purchases = con.execute("SELECT COALESCE(SUM(amount),0), COALESCE(SUM(gst_amount),0) FROM invoices WHERE invoice_kind<>'sales' AND validation_status='approved'").fetchone()
    wages = con.execute("SELECT COALESCE(SUM(l.debit-l.credit),0) FROM journal_lines l JOIN journal_entries e ON e.id=l.journal_id WHERE l.account_code='6220' AND e.status='posted'").fetchone()[0]
    payg_withheld = con.execute("SELECT COALESCE(SUM(l.credit-l.debit),0) FROM journal_lines l JOIN journal_entries e ON e.id=l.journal_id WHERE l.account_code='2300' AND e.status='posted'").fetchone()[0]
    payroll_period = con.execute("SELECT MAX(substr(pay_period, 1, 7)) FROM payroll_records").fetchone()[0]
    if payroll_period:
        payroll_totals = con.execute(
            """
            SELECT COALESCE(SUM(gross_pay),0), COALESCE(SUM(payg_withholding),0)
            FROM payroll_records
            WHERE substr(pay_period, 1, 7)=?
            """,
            (payroll_period,),
        ).fetchone()
        wages = float(payroll_totals[0] or 0)
        payg_withheld = float(payroll_totals[1] or 0)
    unresolved = int(con.execute("SELECT COUNT(*) FROM account_validation_tasks WHERE status='open'").fetchone()[0])
    missing_gst = int(con.execute("SELECT COUNT(*) FROM invoices WHERE invoice_kind<>'sales' AND tax_code='REVIEW'").fetchone()[0])
    capital_review = int(con.execute("SELECT COUNT(*) FROM invoices WHERE account_code='1500'").fetchone()[0])
    entertainment_review = int(con.execute("SELECT COUNT(*) FROM invoices WHERE account_code='6190'").fetchone()[0])
    evidence_missing = int(con.execute("SELECT COUNT(*) FROM invoices WHERE source_file IS NULL OR source_file='' ").fetchone()[0])
    con.close()

    g1 = _round(sales[0]) if profile.get("gst_registered") else 0.0
    one_a = _round(sales[1]) if profile.get("gst_registered") else 0.0
    one_b = _round(purchases[1]) if profile.get("gst_registered") else 0.0
    bas = {
        "G1": g1,
        "1A": one_a,
        "1B": one_b,
        "W1": _round(wages),
        "W2": _round(payg_withheld),
        "net_gst": _round(one_a - one_b),
        "purchase_total": _round(purchases[0]),
        "sales_total": _round(sales[0]),
    }

    accounting_profit = _round(accounting["summary"].get("profit", 0))
    posted_revenue = abs(_round(accounting["summary"].get("revenue", 0)))
    profit_basis = "Posted accounting journals"
    statement_row = None
    fallback_con = get_duckdb()
    try:
        statement_row = fallback_con.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS net_profit,
                COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS reported_revenue,
                MAX(period_end)
            FROM statement_snapshots
            WHERE statement_type='profit_loss'
              AND period_end=(SELECT MAX(period_end) FROM statement_snapshots WHERE statement_type='profit_loss')
            """
        ).fetchone()
    finally:
        fallback_con.close()
    statement_profit = _round((statement_row or [0, 0, ""])[0])
    statement_revenue = abs(_round((statement_row or [0, 0, ""])[1]))
    # A newly uploaded P&L can cover a full reporting period while posted
    # transaction journals contain only a partial month. Use the statement as a
    # clearly-labelled provisional tax basis until posted revenue substantially
    # represents the same period.
    posted_ledger_is_partial = statement_revenue > 0.005 and posted_revenue < statement_revenue * 0.75
    if abs(statement_profit) > 0.005 and (abs(accounting_profit) < 0.005 or posted_ledger_is_partial):
        accounting_profit = statement_profit
        profit_basis = f"Latest uploaded Profit & Loss snapshot ending {(statement_row or ['', '', ''])[2]} (provisional; posted journals cover only part of the statement period)"
    non_deductible_estimate = 0.0
    if entertainment_review:
        # Kept at zero to avoid claiming that all entertainment is non-deductible.
        non_deductible_estimate = 0.0
    taxable_income = max(0.0, accounting_profit + non_deductible_estimate)
    configured_rate = float(profile.get("income_tax_rate") or 0)
    income_tax_estimate = _round(taxable_income * configured_rate / 100)

    opportunities: list[dict[str, Any]] = []
    if missing_gst:
        opportunities.append({"title": "Review missing GST treatment", "count": missing_gst, "impact": "Potential GST credits or corrections", "status": "review"})
    if capital_review:
        opportunities.append({"title": "Review capital purchases", "count": capital_review, "impact": "Confirm depreciation and effective-life treatment", "status": "review"})
    if entertainment_review:
        opportunities.append({"title": "Review entertainment and FBT", "count": entertainment_review, "impact": "Check deductibility, GST credits and possible FBT", "status": "review"})
    if unresolved:
        opportunities.append({"title": "Resolve uncategorised invoices", "count": unresolved, "impact": "Required before reliable BAS and income-tax estimates", "status": "high"})
    if evidence_missing:
        opportunities.append({"title": "Attach missing source evidence", "count": evidence_missing, "impact": "Improves substantiation and audit traceability", "status": "review"})
    if not opportunities:
        opportunities.append({"title": "No obvious exceptions detected", "count": 0, "impact": "Continue periodic review and accountant sign-off", "status": "ready"})

    return {
        "profile": {
            "entity_type": profile.get("entity_type"),
            "abn": profile.get("abn"),
            "state_or_territory": profile.get("state_or_territory"),
            "gst_registered": bool(profile.get("gst_registered")),
            "gst_accounting_method": profile.get("gst_accounting_method"),
            "bas_frequency": profile.get("bas_frequency"),
            "has_employees": bool(profile.get("has_employees")),
            "payg_withholding_registered": bool(profile.get("payg_withholding_registered")),
            "financial_year_end": profile.get("financial_year_end"),
            "income_tax_rate": configured_rate,
        },
        "summary": {
            "estimated_income_tax": income_tax_estimate,
            "estimated_taxable_income": taxable_income,
            "accounting_profit": accounting_profit,
            "profit_basis": profit_basis,
            "net_gst": bas["net_gst"],
            "review_count": unresolved,
            "confidence": "low" if unresolved else "medium",
            "disclaimer": "Indicative workpaper only. It is not tax advice or an official ATO lodgment calculation.",
        },
        "bas": bas,
        "obligations": _obligations(profile, bas, unresolved),
        "opportunities": opportunities,
        "internet": {
            "mode": integrations.get("mode", "offline"),
            "official_sources_enabled": bool(integrations.get("official_tax_sources")),
            "supplier_enrichment_enabled": bool(integrations.get("supplier_enrichment")),
            "ato_sbr_enabled": False,
            "ato_sbr_status": "Locked until DSP registration, OSF compliance and SBR conformance are completed.",
            "last_verified": "2026-07-13",
            "sources": ATO_SOURCES,
        },
        "reconciliation": {
            "gst_payable_control": _round(accounting["summary"].get("gst_payable", 0)),
            "gst_receivable_control": _round(accounting["summary"].get("gst_receivable", 0)),
            "bas_net_gst": bas["net_gst"],
            "difference": _round((accounting["summary"].get("gst_payable", 0) - accounting["summary"].get("gst_receivable", 0)) - bas["net_gst"]),
        },
    }


def _money(value: Any) -> str:
    try:
        return f"AUD {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "AUD 0.00"


def _build_pdf(payload: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#44546a")))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=14, leading=17, spaceBefore=8, textColor=colors.HexColor("#14324a")))
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    story: list[Any] = [
        Paragraph("LedgerFlow ATO-ready Tax Workpaper", styles["Title"]),
        Paragraph(f"Prepared {date.today().isoformat()} · review before use", styles["Small"]),
        Spacer(1, 6 * mm),
        Paragraph("Business profile", styles["Section"]),
    ]
    profile = payload["profile"]
    profile_rows = [
        ["Entity type", profile.get("entity_type")], ["ABN", profile.get("abn") or "Not configured"],
        ["GST registered", "Yes" if profile.get("gst_registered") else "No"],
        ["GST method", profile.get("gst_accounting_method")], ["BAS frequency", profile.get("bas_frequency")],
        ["Financial year end", profile.get("financial_year_end")],
    ]
    table = Table(profile_rows, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d4df")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f7")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)

    story.extend([Spacer(1, 5 * mm), Paragraph("Indicative income-tax estimate", styles["Section"])])
    summary = payload["summary"]
    income_rows = [
        ["Accounting profit", _money(summary["accounting_profit"])],
        ["Estimated taxable income", _money(summary["estimated_taxable_income"])],
        ["Configured estimate rate", f"{profile.get('income_tax_rate', 0):.2f}%"],
        ["Estimated income tax", _money(summary["estimated_income_tax"])],
    ]
    table = Table(income_rows, colWidths=[90 * mm, 75 * mm])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d4df")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e6f2ec")), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)

    story.extend([Spacer(1, 5 * mm), Paragraph("BAS-style labels", styles["Section"])])
    bas = payload["bas"]
    bas_rows = [["Label", "Description", "Estimate"], ["G1", "Total sales", _money(bas["G1"])], ["1A", "GST on sales", _money(bas["1A"])], ["1B", "GST on purchases", _money(bas["1B"])], ["W1", "Salary, wages and other payments", _money(bas["W1"])], ["W2", "Amount withheld", _money(bas["W2"])], ["Net GST", "1A less 1B", _money(bas["net_gst"])]]
    table = Table(bas_rows, colWidths=[25 * mm, 95 * mm, 45 * mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d4df")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14324a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (-1, 1), (-1, -1), "RIGHT"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)

    story.extend([Spacer(1, 5 * mm), Paragraph("Review items and opportunities", styles["Section"])])
    opp_rows = [["Review item", "Count", "Reason"]]
    for item in payload["opportunities"]:
        opp_rows.append([Paragraph(escape(str(item["title"])), styles["Small"]), str(item["count"]), Paragraph(escape(str(item["impact"])), styles["Small"])])
    table = Table(opp_rows, colWidths=[55 * mm, 20 * mm, 90 * mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d4df")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14324a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)

    story.extend([PageBreak(), Paragraph("Compliance obligations", styles["Section"])])
    obligation_rows = [["Obligation", "Frequency", "Status", "Work required"]]
    for item in payload["obligations"]:
        obligation_rows.append([Paragraph(escape(str(item["name"])), styles["Small"]), str(item["frequency"]), str(item["status"]), Paragraph(escape(str(item["detail"])), styles["Small"])])
    table = Table(obligation_rows, colWidths=[42 * mm, 28 * mm, 22 * mm, 73 * mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d4df")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14324a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.append(table)
    story.extend([Spacer(1, 6 * mm), Paragraph("Official references", styles["Section"])])
    for source in ATO_SOURCES:
        story.append(Paragraph(f"<b>{escape(source['title'])}</b><br/>{escape(source['purpose'])}<br/><font color='#44657c'>{escape(source['url'])}</font>", styles["Small"]))
        story.append(Spacer(1, 2 * mm))
    story.extend([Spacer(1, 5 * mm), Paragraph(escape(payload["summary"]["disclaimer"]), styles["Small"])])
    doc.build(story)
    return buffer.getvalue()


def _build_csv(payload: dict[str, Any]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["LedgerFlow ATO-ready Tax Workpaper", date.today().isoformat()])
    writer.writerow([])
    writer.writerow(["BAS label", "Description", "Estimate AUD"])
    bas = payload["bas"]
    for label, description in [("G1", "Total sales"), ("1A", "GST on sales"), ("1B", "GST on purchases"), ("W1", "Salary, wages and other payments"), ("W2", "Amount withheld")]:
        writer.writerow([label, description, bas[label]])
    writer.writerow(["NET_GST", "1A less 1B", bas["net_gst"]])
    writer.writerow([])
    writer.writerow(["Income tax estimate"])
    for key in ["accounting_profit", "estimated_taxable_income", "estimated_income_tax", "confidence"]:
        writer.writerow([key, payload["summary"][key]])
    writer.writerow([])
    writer.writerow(["Obligation", "Frequency", "Status", "Detail"])
    for item in payload["obligations"]:
        writer.writerow([item["name"], item["frequency"], item["status"], item["detail"]])
    writer.writerow([])
    writer.writerow(["Review item", "Count", "Impact"])
    for item in payload["opportunities"]:
        writer.writerow([item["title"], item["count"], item["impact"]])
    return output.getvalue().encode("utf-8-sig")


def generate_tax_workpaper(output_format: str = "pdf") -> tuple[bytes, str, str]:
    payload = tax_dashboard()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_format == "pdf":
        return _build_pdf(payload), f"ato_ready_tax_workpaper_{stamp}.pdf", "application/pdf"
    if output_format == "csv":
        return _build_csv(payload), f"ato_ready_tax_workpaper_{stamp}.csv", "text/csv; charset=utf-8"
    raise ValueError("Tax workpaper format must be pdf or csv.")
