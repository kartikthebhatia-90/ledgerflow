from __future__ import annotations

import re
from pathlib import Path

# High-confidence filename routes. These are intentionally conservative and are
# used before structural column scoring. They prevent context documents such as
# BRDs, aged reports and fixed-asset registers from being posted as invoices or
# balance sheets simply because they contain generic financial columns.
_FILENAME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("business_requirements", ("business_requirements", "business_requirement", "business_requirements_document", "brd")),
    ("use_cases_user_stories", ("use_cases_and_user_stories", "use_cases", "user_stories", "user_story")),
    ("material_contracts", ("material_supplier_contract", "material_contract", "supplier_contract", "supplier_agreement")),
    ("historical_tax_returns", ("historical_tax_returns", "historical_tax_return", "tax_returns", "tax_return")),
    ("fixed_asset_register", ("fixed_asset_register", "fixed_assets_register", "asset_register")),
    ("aged_debtors_creditors", ("aged_debtors", "aged_creditors", "aged_receivables", "aged_payables", "debtor_ageing", "creditor_ageing")),
    ("cash_flow_statement", ("cash_flow_statement", "statement_of_cash_flows", "cashflow_statement")),
    ("profit_loss", ("profit_loss", "profit_and_loss", "income_statement", "statement_of_profit")),
    ("chart_of_accounts", ("chart_of_accounts", "chart_accounts", "coa_")),
    ("balance_sheet", ("balance_sheet", "statement_of_financial_position", "assets_liabilities_ratio_bridge")),
    ("sales_forecast", ("sales_forecast", "revenue_forecast", "forecast_sales")),
    ("personnel_plan", ("personnel_plan", "workforce_plan", "headcount_plan")),
    ("market_context", ("market_context", "competitor_context", "market_and_competitors")),
    ("bank_statements", ("bank_statement", "bank_transactions")),
    ("payroll", ("payroll_report", "pay_run", "payroll_")),
    ("sales_invoices", ("sales_invoices", "sales_invoice", "customer_invoice", "issued_invoice")),
    ("supplier_invoices", ("supplier_invoice", "supplier_invoices", "vendor_invoice", "purchase_invoice", "receipt_", "tax_invoice")),
]

SETUP_DOCUMENT_TYPES = {
    "balance_sheet",
    "profit_loss",
    "cash_flow_statement",
    "chart_of_accounts",
    "business_requirements",
    "fixed_asset_register",
    "aged_debtors_creditors",
    "material_contracts",
    "sales_forecast",
    "personnel_plan",
    "use_cases_user_stories",
    "historical_tax_returns",
    "market_context",
}

RECURRING_DOCUMENT_TYPES = {
    "supplier_invoices",
    "sales_invoices",
    "bank_statements",
    "payroll",
}

KNOWN_DOCUMENT_TYPES = SETUP_DOCUMENT_TYPES | RECURRING_DOCUMENT_TYPES


def normalise_route_token(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def strong_filename_document_hint(filename: str) -> str:
    signal = normalise_route_token(Path(filename).stem)
    wrapped = f"_{signal}_"
    for document_type, tokens in _FILENAME_RULES:
        for token in tokens:
            token_norm = normalise_route_token(token)
            if token_norm and (token_norm in signal or f"_{token_norm}_" in wrapped):
                return document_type
    return ""


def expected_intake_category(document_type: str, fallback: str = "recurring") -> str:
    if document_type in SETUP_DOCUMENT_TYPES:
        return "setup"
    if document_type in RECURRING_DOCUMENT_TYPES:
        return "recurring"
    return fallback if fallback in {"setup", "recurring"} else "recurring"


def folder_declared_document_type(path: Path, category_root: Path) -> str:
    """Read a document type from a subfolder such as permanent/cash_flow_statement."""
    try:
        relative = path.relative_to(category_root)
    except ValueError:
        return "auto"
    for part in relative.parts[:-1]:
        candidate = normalise_route_token(part)
        if candidate in KNOWN_DOCUMENT_TYPES:
            return candidate
        if candidate == "invoices_receipts":
            return "supplier_invoices"
    return strong_filename_document_hint(path.name) or "auto"
