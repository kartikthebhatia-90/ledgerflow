from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .database import get_duckdb
from .tax import tax_dashboard


SCHEMES = [
    {
        "id": "instant_asset_write_off",
        "title": "$20,000 instant asset write-off",
        "category": "Assets",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/small-business-newsroom/20000-instant-asset-write-off-for-2025-26",
        "official_rule": "Eligible small businesses may immediately deduct the business portion of eligible assets costing less than $20,000 for 2025–26.",
        "check": "Confirm aggregated turnover, asset cost, installation date and business-use percentage.",
    },
    {
        "id": "simplified_depreciation",
        "title": "Simplified depreciation and small-business pool",
        "category": "Assets",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/depreciation-and-capital-expenses-and-allowances/simpler-depreciation-for-small-business",
        "official_rule": "Eligible small businesses can use simplified depreciation rules for qualifying depreciating assets.",
        "check": "Review the fixed-asset register, pool balances and excluded assets.",
    },
    {
        "id": "prepaid_expenses",
        "title": "Immediate deduction for qualifying prepayments",
        "category": "Deductions",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/income-and-deductions-for-business/deductions",
        "official_rule": "Some eligible small-business prepaid expenses covering a service period of no more than 12 months may be immediately deductible.",
        "check": "Identify insurance, subscriptions, rent or service contracts paid in advance and confirm timing rules.",
    },
    {
        "id": "trading_stock",
        "title": "Simplified trading-stock rules",
        "category": "Inventory",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/income-and-deductions-for-business/valuing-trading-stock",
        "official_rule": "Eligible small businesses may use simplified trading-stock rules when the estimated stock-value difference is within the legislated threshold.",
        "check": "Compare opening and closing inventory values and confirm small-business eligibility.",
    },
    {
        "id": "rdti",
        "title": "Research and Development Tax Incentive",
        "category": "Innovation",
        "source_url": "https://business.gov.au/grants-and-programs/research-and-development-tax-incentive",
        "official_rule": "Eligible companies may claim a tax offset for qualifying R&D activities and expenditure after registration.",
        "check": "Identify eligible experimental activities, contemporaneous records, expenditure and the 10-month registration deadline.",
    },
    {
        "id": "employee_costs",
        "title": "Salary, wage and super deductions",
        "category": "People",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/income-and-deductions-for-business/deductions/deductions-for-salaries-wages-and-super-contributions",
        "official_rule": "Businesses can generally deduct eligible employee salaries, wages and super contributions when the relevant requirements are met.",
        "check": "Reconcile payroll, STP, PAYG withholding and super payment timing.",
    },
    {
        "id": "cgt_concessions",
        "title": "Four small-business CGT concessions",
        "category": "Capital gains",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/incentives-and-concessions/small-business-cgt-concessions",
        "official_rule": "Potential concessions include the 15-year exemption, 50% active-asset reduction, retirement exemption and small-business roll-over.",
        "check": "Only relevant to a qualifying CGT event; verify basic conditions, turnover or net-asset tests and the active-asset test.",
    },
    {
        "id": "gst_credits",
        "title": "GST credits and adjustments",
        "category": "GST",
        "source_url": "https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst",
        "official_rule": "GST-registered businesses may claim credits for creditable business purchases and may need adjustments for changed use or bad debts.",
        "check": "Review tax invoices, GST coding, private use, bad debts and prior-period corrections.",
    },
    {
        "id": "government_programs",
        "title": "Government grants and programs finder",
        "category": "Funding",
        "source_url": "https://business.gov.au/grants-and-programs",
        "official_rule": "The official finder searches current grants, funding and support programs based on business circumstances.",
        "check": "Complete the official guided search using location, industry, business size and planned activities.",
    },
]


def _official(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host == "ato.gov.au" or host.endswith(".ato.gov.au") or host == "business.gov.au" or host.endswith(".business.gov.au")


def _business_signals() -> dict[str, Any]:
    con = get_duckdb()
    try:
        return {
            "capital_invoice_count": int(con.execute("SELECT COUNT(*) FROM invoices WHERE account_code='1500'").fetchone()[0]),
            "inventory_value": float(con.execute("SELECT COALESCE(SUM(total_value),0) FROM inventory").fetchone()[0]),
            "payroll_rows": int(con.execute("SELECT COUNT(*) FROM payroll_records").fetchone()[0]),
            "gst_review_rows": int(con.execute("SELECT COUNT(*) FROM invoices WHERE tax_code='REVIEW'").fetchone()[0]),
            "software_spend": float(con.execute("SELECT COALESCE(SUM(amount),0) FROM invoices WHERE lower(category) LIKE '%software%'").fetchone()[0]),
        }
    finally:
        con.close()


async def _check_official_sources() -> list[dict[str, str]]:
    """Check only the curated government pages without sending business data.

    The request URLs contain no company name, figures, industry, location or
    derived eligibility signals. Evidence matching remains entirely local.
    """
    headers = {"User-Agent": "LedgerFlow/3.3.1 official-tax-guidance-check"}

    async def check(scheme: dict[str, str]) -> dict[str, str] | None:
        url = scheme["source_url"]
        if not _official(url):
            return None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                trust_env=False,
                headers=headers,
            ) as client:
                response = await client.get(url)
            if response.status_code >= 400 or not _official(str(response.url)):
                return None
            return {
                "title": scheme["title"],
                "url": str(response.url),
                "content": scheme["official_rule"],
                "source": "ATO" if "ato.gov.au" in str(response.url) else "business.gov.au",
            }
        except Exception:
            return None

    checked = await asyncio.gather(*(check(scheme) for scheme in SCHEMES))
    return [item for item in checked if item is not None]


async def analyse_tax_opportunities() -> dict[str, Any]:
    tax = tax_dashboard()
    signals = _business_signals()
    official_results = await _check_official_sources()
    schemes: list[dict[str, Any]] = []
    for scheme in SCHEMES:
        status = "eligibility review"
        evidence = "No direct trigger found in current records; retain for periodic review."
        if scheme["id"] == "instant_asset_write_off":
            evidence = f"{signals['capital_invoice_count']} capital-coded invoice(s) require an asset-by-asset threshold and date check."
        elif scheme["id"] == "simplified_depreciation":
            evidence = "A fixed-asset register is present; compare existing depreciation with simplified-pool eligibility."
        elif scheme["id"] == "prepaid_expenses":
            evidence = "Software, insurance and contract records may contain qualifying prepayments; service periods are still required."
        elif scheme["id"] == "trading_stock":
            evidence = f"Inventory records total {signals['inventory_value']:.2f}; compare opening and closing stock before applying the simplified rule."
        elif scheme["id"] == "rdti":
            evidence = f"Software-related spend of {signals['software_spend']:.2f} is present, but ordinary subscriptions are not R&D. Qualifying experimental activities must be separately evidenced."
        elif scheme["id"] == "employee_costs":
            status = "evidence present" if signals["payroll_rows"] else "missing payroll"
            evidence = f"{signals['payroll_rows']} payroll record(s) support a wages and super deduction review."
        elif scheme["id"] == "cgt_concessions":
            status = "event dependent"
            evidence = "No CGT event is recorded; review only before selling an active business asset or ownership interest."
        elif scheme["id"] == "gst_credits":
            status = "review now" if signals["gst_review_rows"] else "evidence present"
            evidence = f"{signals['gst_review_rows']} invoice(s) still have review-level GST treatment."
        schemes.append({**scheme, "status": status, "evidence": evidence})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "obligation_snapshot": {
            "estimated_taxable_income": tax["summary"]["estimated_taxable_income"],
            "estimated_income_tax": tax["summary"]["estimated_income_tax"],
            "net_gst": tax["summary"]["net_gst"],
            "review_count": tax["summary"]["review_count"],
        },
        "schemes": schemes,
        "official_search": {
            "live": bool(official_results),
            "message": (
                f"Found {len(official_results)} current official result(s)."
                if official_results else
                "The live official-page check was unavailable; the built-in catalogue still links directly to the curated government pages."
            ),
            "results": official_results,
        },
        "scope_note": (
            "Broad federal opportunity scan, not a claim that every concession applies and not an exhaustive substitute for tailored tax advice. "
            "Eligibility, timing, elections, aggregated turnover and evidence must be confirmed by a registered tax professional."
        ),
    }
