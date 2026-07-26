from __future__ import annotations

from typing import Any


DEPARTMENT_AGENTS: dict[str, dict[str, Any]] = {
    "executive": {
        "label": "Executive analyst", "department": "Executive", "workspaces": ["overview"],
        "processes": ["financial_statements", "working_capital", "forecast_and_budget", "company_and_requirements", "generic_extraction"],
        "purpose": "Integrate cross-functional evidence into prioritised business decisions, timing and expected impact.",
        "colour": "#e2b33d", "x": 0.50, "y": 0.28,
    },
    "finance": {
        "label": "Finance agent", "department": "Finance & Accounts", "workspaces": ["accounts", "overview"],
        "processes": ["financial_statements", "ledger_and_accounts", "working_capital", "bank_and_reconciliation", "invoice_and_gst", "assets_and_depreciation"],
        "purpose": "Analyse financial position, profitability, cash conversion, reconciliations and accounting controls.",
        "colour": "#5e9e6b", "x": 0.30, "y": 0.42,
    },
    "tax": {
        "label": "Tax agent", "department": "Tax & Compliance", "workspaces": ["tax", "accounts"],
        "processes": ["invoice_and_gst", "ledger_and_accounts", "payroll_and_obligations", "assets_and_depreciation"],
        "purpose": "Evaluate GST, PAYG, taxable income, evidence gaps and compliance actions.",
        "colour": "#b84b3a", "x": 0.34, "y": 0.70,
    },
    "marketing": {
        "label": "Growth agent", "department": "Sales & Marketing", "workspaces": ["marketing", "overview"],
        "processes": ["forecast_and_budget", "invoice_and_gst", "working_capital", "market_and_competitors"],
        "purpose": "Connect revenue, customer evidence and channel spend to growth efficiency and commercial recommendations.",
        "colour": "#c98a2c", "x": 0.66, "y": 0.70,
    },
    "operations": {
        "label": "Operations agent", "department": "Operations & Supply", "workspaces": ["overview", "accounts"],
        "processes": ["bank_and_reconciliation", "working_capital", "contracts_and_commitments", "assets_and_depreciation", "forecast_and_budget"],
        "purpose": "Analyse supplier, inventory, delivery, working-capital and operating-capacity evidence.",
        "colour": "#5d8f9f", "x": 0.72, "y": 0.48,
    },
    "people": {
        "label": "People agent", "department": "People & Payroll", "workspaces": ["accounts", "tax", "overview"],
        "processes": ["payroll_and_obligations", "forecast_and_budget", "company_and_requirements"],
        "purpose": "Analyse payroll, headcount, superannuation, workforce cost and capacity evidence.",
        "colour": "#9f7aa8", "x": 0.70, "y": 0.32,
    },
    "market": {
        "label": "Market intelligence agent", "department": "Market & Strategy", "workspaces": ["intelligence", "marketing", "overview"],
        "processes": ["market_and_competitors", "forecast_and_budget", "company_and_requirements", "contracts_and_commitments"],
        "purpose": "Combine internal context with competitor, market, macroeconomic and cited research evidence.",
        "colour": "#b45a49", "x": 0.50, "y": 0.78,
    },
}

KEYWORDS: dict[str, tuple[str, ...]] = {
    "executive": ("overview", "business", "priority", "decision", "management", "summary"),
    "finance": ("cash", "profit", "margin", "account", "invoice", "reconcile", "liquidity", "ratio", "debt", "asset"),
    "tax": ("tax", "gst", "bas", "payg", "ato", "compliance", "deduction"),
    "marketing": ("marketing", "campaign", "roas", "customer", "sales", "growth", "advertising", "channel"),
    "operations": ("supplier", "inventory", "stock", "delivery", "freight", "operations", "contract", "warehouse"),
    "people": ("payroll", "employee", "staff", "headcount", "superannuation", "wages", "people"),
    "market": ("market", "competitor", "industry", "geopolitical", "benchmark", "research", "strategy"),
}
