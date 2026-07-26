from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .accounting import accounting_dashboard
from .analytics import dashboard_summary, financial_snapshot
from .classification_repair import classification_repair_plan
from .database import rows_as_dicts
from .marketing import marketing_dashboard
from .tax import tax_dashboard
from .upload_intelligence import upload_library


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(
    check_id: str,
    label: str,
    status: str,
    severity: str,
    detail: str,
    *,
    evidence: dict[str, Any] | None = None,
    recommendation: str = "",
) -> dict[str, Any]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence": evidence or {},
        "recommendation": recommendation,
    }


def _page_readiness(
    summary: dict[str, Any],
    accounts: dict[str, Any],
    tax: dict[str, Any],
    marketing: dict[str, Any],
    library: dict[str, Any],
) -> list[dict[str, Any]]:
    """Explain whether each user-facing page has usable, source-backed data."""
    coverage = library.get("coverage") or {}
    files = library.get("files") or {}
    required_missing = list(coverage.get("required_missing") or [])
    uploaded_count = len(files.get("setup") or []) + len(files.get("recurring") or [])
    account_rows = len(accounts.get("accounts") or [])
    tax_summary = tax.get("summary") or {}
    marketing_summary = marketing.get("summary") or {}

    def page(
        page_id: str,
        label: str,
        row_count: int,
        status: str,
        detail: str,
        missing: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": page_id,
            "label": label,
            "status": status,
            "has_data": row_count > 0,
            "record_count": row_count,
            "detail": detail,
            "missing": missing or [],
        }

    overview_has_values = any(
        abs(float(summary.get(key) or 0)) > 0
        for key in ("total_assets", "total_liabilities", "revenue_month", "expenses_month", "cash")
    )
    overview_status = "ready" if overview_has_values and not required_missing else "provisional" if overview_has_values else "blocked"
    account_status = "ready" if account_rows and not int((accounts.get("summary") or {}).get("review_count") or 0) else "provisional" if account_rows else "blocked"
    tax_has_data = any(abs(float(tax_summary.get(key) or 0)) > 0 for key in ("accounting_profit", "estimated_taxable_income", "net_gst"))
    tax_status = "ready" if tax_has_data and not int(tax_summary.get("review_count") or 0) else "provisional" if tax_has_data else "blocked"
    marketing_has_data = abs(float(marketing_summary.get("revenue") or 0)) > 0 or abs(float(marketing_summary.get("marketing_spend") or 0)) > 0
    marketing_status = "ready" if marketing_has_data and str(marketing.get("mode")) == "actual" else "provisional" if marketing_has_data else "blocked"

    return [
        page("overview", "Overview", len(summary.get("performance_series") or []), overview_status,
             "Headline financials and trends are populated." if overview_has_values else "No usable headline financial values are available.",
             required_missing),
        page("accounts", "Accounts", account_rows, account_status,
             f"{account_rows} account row(s) are available." if account_rows else "No chart-of-accounts or ledger rows are available.",
             ["chart_of_accounts"] if not account_rows else []),
        page("tax", "Tax", len(tax.get("obligations") or []), tax_status,
             "Tax estimates have an accounting evidence basis." if tax_has_data else "Tax calculations have no financial evidence basis yet.",
             ["profit_loss", "tax_profile"] if not tax_has_data else []),
        page("marketing", "Marketing", len(marketing.get("channels") or []), marketing_status,
             "Posted marketing evidence is active." if str(marketing.get("mode")) == "actual" else "Only clearly labelled provisional or demonstration context is available.",
             ["marketing_spend", "campaign_attribution"] if str(marketing.get("mode")) != "actual" else []),
        page("operations", "Data management", uploaded_count, "ready" if uploaded_count else "blocked",
             f"{uploaded_count} processed source file(s) are registered." if uploaded_count else "No processed source files are registered."),
    ]


def data_quality_dashboard() -> dict[str, Any]:
    """Return source-backed trust checks for dashboard and agent use.

    The score is deliberately transparent. It is not a credit rating and does
    not replace accountant review. Critical failures have the largest weight,
    followed by high and medium issues.
    """
    library = upload_library()
    coverage = library.get("coverage") or {}
    catalogue = library.get("catalogue") or {}
    summary = dashboard_summary()
    snapshot = financial_snapshot()
    accounts = accounting_dashboard()
    tax = tax_dashboard()
    marketing = marketing_dashboard()
    repairs = classification_repair_plan()

    checks: list[dict[str, Any]] = []

    required_total = len(catalogue.get("setup_required") or []) or 5
    required_received = len(coverage.get("required_received") or [])
    required_missing = list(coverage.get("required_missing") or [])
    checks.append(_check(
        "core-document-coverage",
        "Core document coverage",
        "pass" if not required_missing else "fail",
        "critical" if required_missing else "info",
        f"{required_received}/{required_total} required setup document categories are represented.",
        evidence={"received": required_received, "total": required_total, "missing": required_missing},
        recommendation="Upload or correctly classify every missing core document before relying on the full dashboard." if required_missing else "",
    ))

    recommended_total = len(catalogue.get("setup_recommended") or [])
    recommended_received = len(coverage.get("recommended_received") or [])
    checks.append(_check(
        "recommended-context-coverage",
        "Recommended context coverage",
        "pass" if recommended_total and recommended_received == recommended_total else "warning",
        "low",
        f"{recommended_received}/{recommended_total} recommended context categories are represented.",
        evidence={"received": recommended_received, "total": recommended_total, "missing": coverage.get("recommended_missing") or []},
        recommendation="Add missing recommended context only where it improves a real decision or forecast.",
    ))

    checks.append(_check(
        "classification-integrity",
        "Classification integrity",
        "pass" if not repairs else "fail",
        "high" if repairs else "info",
        "No unresolved classification repair is queued." if not repairs else f"{len(repairs)} file classification repair(s) remain.",
        evidence={"repair_count": len(repairs), "repairs": repairs[:10]},
        recommendation="Run classification repair and wait for every corrective job to complete." if repairs else "",
    ))

    account_summary = accounts.get("summary") or {}
    account_review = int(account_summary.get("review_count") or 0)
    draft_journals = int(account_summary.get("draft_journal_count") or 0)
    checks.append(_check(
        "account-review-queue",
        "Account review queue",
        "pass" if account_review == 0 and draft_journals == 0 else "warning",
        "high" if account_review >= 5 else "medium" if account_review or draft_journals else "info",
        f"{account_review} account categorisation task(s) and {draft_journals} draft journal(s) remain.",
        evidence={"open_tasks": account_review, "draft_journals": draft_journals},
        recommendation="Resolve categorisation tasks before treating invoice-driven account and tax totals as final." if account_review or draft_journals else "",
    ))

    ledger_cash = next((float(row.get("balance") or 0) for row in accounts.get("accounts") or [] if str(row.get("code")) == "1000"), 0.0)
    baseline_cash = float(snapshot.get("cash") or 0)
    cash_difference = round(ledger_cash - baseline_cash, 2)
    cash_tolerance = max(1.0, abs(baseline_cash) * 0.005)
    cash_reconciled = abs(cash_difference) <= cash_tolerance
    checks.append(_check(
        "cash-reconciliation",
        "Cash reconciliation",
        "pass" if cash_reconciled else "warning",
        "high" if not cash_reconciled else "info",
        "Dashboard cash and posted-ledger cash reconcile." if cash_reconciled else f"Financial-position cash and posted-ledger cash differ by ${cash_difference:,.2f}.",
        evidence={"financial_position_cash": baseline_cash, "posted_ledger_cash": ledger_cash, "difference": cash_difference, "tolerance": cash_tolerance},
        recommendation="Label the two grains separately or post/reconcile the bank movement before presenting one cash value as canonical." if not cash_reconciled else "",
    ))

    ledger_ar = float(account_summary.get("accounts_receivable") or 0)
    baseline_ar_rows = rows_as_dicts("SELECT COALESCE(SUM(amount),0) AS value FROM assets_liabilities WHERE category='asset' AND lower(name) LIKE '%receiv%'")
    baseline_ar = float((baseline_ar_rows[0] if baseline_ar_rows else {}).get("value") or 0)
    ar_difference = round(ledger_ar - baseline_ar, 2)
    ar_tolerance = max(1.0, abs(baseline_ar) * 0.01)
    ar_reconciled = abs(ar_difference) <= ar_tolerance
    checks.append(_check(
        "receivables-reconciliation",
        "Receivables reconciliation",
        "pass" if ar_reconciled else "warning",
        "medium" if not ar_reconciled else "info",
        "Financial-position and ledger receivables reconcile." if ar_reconciled else f"Financial-position and posted-ledger receivables differ by ${ar_difference:,.2f}.",
        evidence={"financial_position_receivables": baseline_ar, "posted_ledger_receivables": ledger_ar, "difference": ar_difference},
        recommendation="Show the statement date and transaction cut-off, then reconcile later invoices separately." if not ar_reconciled else "",
    ))

    tax_summary = tax.get("summary") or {}
    tax_reviews = int(tax_summary.get("review_count") or 0)
    checks.append(_check(
        "tax-readiness",
        "Tax evidence readiness",
        "pass" if tax_reviews == 0 else "warning",
        "medium" if tax_reviews else "info",
        f"{tax_reviews} tax evidence or coding review(s) remain.",
        evidence={"review_count": tax_reviews, "basis": tax_summary.get("basis_label") or tax_summary.get("basis")},
        recommendation="Keep estimates provisional until coding and registration settings are reviewed." if tax_reviews else "",
    ))

    marketing_mode = str(marketing.get("mode") or "demonstration")
    checks.append(_check(
        "marketing-attribution",
        "Marketing attribution source",
        "pass" if marketing_mode == "actual" else "warning",
        "low",
        "Verified posted marketing evidence is active." if marketing_mode == "actual" else "Marketing remains in clearly labelled demonstration mode.",
        evidence={"mode": marketing_mode},
        recommendation="Upload or connect verified campaign and CRM data before making channel-allocation decisions." if marketing_mode != "actual" else "",
    ))

    validation_rows = rows_as_dicts("SELECT severity, COUNT(*) AS count FROM validations WHERE COALESCE(status,'open')='open' GROUP BY severity")
    validation_counts = {str(row.get("severity") or "unknown"): int(row.get("count") or 0) for row in validation_rows}
    validations_total = sum(validation_counts.values())
    checks.append(_check(
        "business-validation-queue",
        "Business validation queue",
        "pass" if validations_total == 0 else "warning",
        "high" if validation_counts.get("critical", 0) else "medium" if validations_total else "info",
        f"{validations_total} business validation check(s) remain open.",
        evidence={"by_severity": validation_counts},
        recommendation="Resolve critical and high checks before using the affected metrics for decisions." if validations_total else "",
    ))

    severity_weight = {"critical": 28, "high": 16, "medium": 8, "low": 3, "info": 0}
    score = 100
    for item in checks:
        if item["status"] in {"fail", "warning"}:
            score -= severity_weight.get(str(item.get("severity")), 5)
    score = max(0, min(100, score))
    status = "trusted" if score >= 85 else "review" if score >= 65 else "not_ready"

    issue_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in checks:
        if item["status"] in {"fail", "warning"} and item["severity"] in issue_counts:
            issue_counts[item["severity"]] += 1

    source_coverage = [
        {"label": "Required setup", "received": required_received, "total": required_total},
        {"label": "Recommended context", "received": recommended_received, "total": recommended_total},
        {"label": "Recurring categories", "received": len(coverage.get("recurring_received") or []), "total": len(catalogue.get("recurring") or [])},
    ]
    reconciliations = [
        {"label": "Cash", "difference": cash_difference, "status": "reconciled" if cash_reconciled else "difference"},
        {"label": "Receivables", "difference": ar_difference, "status": "reconciled" if ar_reconciled else "difference"},
    ]
    page_readiness = _page_readiness(summary, accounts, tax, marketing, library)

    return {
        "generated_at": _now(),
        "score": score,
        "status": status,
        "checks": checks,
        "issue_counts": issue_counts,
        "source_coverage": source_coverage,
        "reconciliations": reconciliations,
        "page_readiness": page_readiness,
        "pages_ready": sum(1 for page in page_readiness if page["status"] == "ready"),
        "pages_total": len(page_readiness),
        "open_check_total": validations_total + account_review + tax_reviews,
        "dashboard_open_checks": int(summary.get("critical_alerts") or 0),
        "definitions": {
            "score": "100 less transparent severity-weighted deductions; informational checks do not reduce the score.",
            "status": {"trusted": "85-100", "review": "65-84", "not_ready": "0-64"},
        },
    }
