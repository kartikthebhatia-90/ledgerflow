from __future__ import annotations

from typing import Any

from .accounting import accounting_dashboard
from .analytics import dashboard_summary
from .database import get_duckdb

CHANNEL_RULES = [
    ("Paid search", ("google ads", "search ads", "sem", "ppc")),
    ("Social", ("facebook", "instagram", "linkedin", "tiktok", "social")),
    ("Email & CRM", ("mailchimp", "hubspot", "klaviyo", "email", "crm")),
    ("Content & SEO", ("content", "seo", "copywriting", "blog")),
    ("Events & partnerships", ("event", "sponsor", "partnership", "expo")),
]


def _channel_for(text: str) -> str:
    normalised = text.lower()
    for channel, terms in CHANNEL_RULES:
        if any(term in normalised for term in terms):
            return channel
    return "Brand & other"


def marketing_dashboard() -> dict[str, Any]:
    accounting = accounting_dashboard()
    business = dashboard_summary()
    revenue = float(accounting.get("summary", {}).get("revenue") or business.get("revenue_month") or 0)
    marketing_account = next((item for item in accounting.get("accounts", []) if str(item.get("code")) == "6150"), None)
    actual_spend = float((marketing_account or {}).get("balance") or 0)

    con = get_duckdb()
    rows = con.execute(
        """
        SELECT supplier, description, amount, invoice_date
        FROM invoices
        WHERE account_code='6150' AND COALESCE(validation_status,'') NOT IN ('review','pending')
        ORDER BY invoice_date DESC
        """
    ).fetchall()
    con.close()

    invoice_spend = sum(abs(float(row[2] or 0)) for row in rows)
    if actual_spend <= 0.01 and invoice_spend > 0.01:
        # Invoices dated on or before the latest opening balance are evidence for
        # channel spend but are not reposted to the ledger, preventing double counting.
        actual_spend = invoice_spend

    channel_totals: dict[str, float] = {}
    for supplier, description, amount, _ in rows:
        channel = _channel_for(f"{supplier or ''} {description or ''}")
        channel_totals[channel] = channel_totals.get(channel, 0.0) + abs(float(amount or 0))

    demonstration = actual_spend <= 0.01
    spend = actual_spend
    if demonstration:
        spend = max(2400.0, revenue * 0.08 if revenue > 0 else 12000.0)
        demo_mix = {
            "Paid search": 0.34,
            "Social": 0.24,
            "Email & CRM": 0.14,
            "Content & SEO": 0.18,
            "Events & partnerships": 0.10,
        }
        channel_totals = {name: spend * share for name, share in demo_mix.items()}
    elif not channel_totals:
        channel_totals = {"Brand & other": spend}

    attributed_revenue = revenue * (0.24 if demonstration else 0.0)
    roas = attributed_revenue / spend if spend else 0.0
    spend_ratio = spend / revenue if revenue else 0.0
    channels = []
    efficiency = {
        "Paid search": 4.2,
        "Social": 2.8,
        "Email & CRM": 6.1,
        "Content & SEO": 3.5,
        "Events & partnerships": 1.9,
        "Brand & other": 2.2,
    }
    for name, amount in sorted(channel_totals.items(), key=lambda item: item[1], reverse=True):
        estimated_roas = efficiency.get(name, 2.2) if demonstration else 0.0
        channels.append({
            "channel": name,
            "spend": round(amount, 2),
            "share": round(amount / spend * 100, 1) if spend else 0,
            "attributed_revenue": round(amount * estimated_roas, 2) if demonstration else 0.0,
            "roas": estimated_roas,
            "status": "scale" if estimated_roas >= 4 else "optimise" if estimated_roas >= 2.5 else "review",
        })

    raw_series = list(business.get("performance_series") or [])[-12:]
    observed = [point for point in raw_series if abs(float(point.get("revenue") or 0)) > 0.01 or abs(float(point.get("expenses") or 0)) > 0.01]
    performance_mode = "trend" if len(observed) >= 4 else "current_period"
    performance = []
    if performance_mode == "trend":
        total_observed_revenue = sum(max(0.0, float(point.get("revenue") or 0)) for point in observed) or 1.0
        for point in observed:
            month_revenue = float(point.get("revenue") or 0)
            month_spend = spend * max(0.0, month_revenue) / total_observed_revenue
            performance.append({
                "month": point.get("month"),
                "revenue": round(month_revenue, 2),
                "marketing_spend": round(month_spend, 2),
            })
    else:
        current_label = str((observed[-1] if observed else {"month": "Current"}).get("month") or "Current")
        performance = [
            {"metric": "Revenue", "period": current_label, "value": round(revenue, 2)},
            {"metric": "Marketing spend", "period": current_label, "value": round(spend, 2)},
            {"metric": "Attributed revenue", "period": current_label, "value": round(attributed_revenue, 2)},
        ]

    return {
        "mode": "demonstration" if demonstration else "actual",
        "disclaimer": "Demonstration allocation is shown because no posted marketing ledger spend was found." if demonstration else "Spend is based on approved account 6150 invoice evidence; attributed revenue requires campaign integrations.",
        "summary": {
            "revenue": round(revenue, 2),
            "marketing_spend": round(spend, 2),
            "spend_to_revenue_pct": round(spend_ratio * 100, 1),
            "attributed_revenue": round(attributed_revenue, 2),
            "roas": round(roas, 2),
            "channels": len(channels),
        },
        "channels": channels,
        "performance_mode": performance_mode,
        "performance": performance,
        "recommendations": [
            "Connect campaign and CRM data before treating attribution as verified.",
            "Compare channel ROAS with gross margin, not revenue alone.",
            "Move budget only after checking conversion quality and customer payback period.",
        ],
    }
