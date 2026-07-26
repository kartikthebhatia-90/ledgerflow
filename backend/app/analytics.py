from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from .config import settings
from .database import COMPANY_ID, get_company_profile, rows_as_dicts


def _single_value(query: str, parameters: tuple = ()) -> float:
    rows = rows_as_dicts(query, parameters)
    if not rows:
        return 0.0
    value = next(iter(rows[0].values()))
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _ledger_financial_values() -> dict[str, float | int]:
    """Calculate the same posted-ledger values displayed on the Accounts page."""
    rows = rows_as_dicts("""
        SELECT c.code, c.name, c.account_type, c.subtype,
               CASE WHEN c.account_type IN ('asset','expense')
                    THEN COALESCE(SUM(l.debit-l.credit),0)
                    ELSE COALESCE(SUM(l.credit-l.debit),0) END AS balance,
               COUNT(l.id) AS posted_lines
        FROM chart_of_accounts c
        LEFT JOIN (
            SELECT lines.* FROM journal_lines lines
            JOIN journal_entries entries ON entries.id=lines.journal_id
            WHERE entries.status='posted'
        ) l ON l.account_code=c.code
        WHERE c.active=TRUE
        GROUP BY c.code, c.name, c.account_type, c.subtype
    """)
    values: dict[str, float | int] = {
        "posted_lines": sum(int(row.get("posted_lines") or 0) for row in rows),
        "current_assets": 0.0, "current_liabilities": 0.0, "inventory": 0.0,
        "cash": 0.0, "total_assets": 0.0, "total_liabilities": 0.0,
        "revenue": 0.0, "expenses": 0.0,
    }
    for row in rows:
        account_type = str(row.get("account_type") or "").lower()
        subtype = str(row.get("subtype") or "").lower()
        name = str(row.get("name") or "").lower()
        balance = float(row.get("balance") or 0)
        if account_type == "asset":
            values["total_assets"] = float(values["total_assets"]) + balance
            if "current" in subtype and "non-current" not in subtype:
                values["current_assets"] = float(values["current_assets"]) + balance
            if "inventory" in name:
                values["inventory"] = float(values["inventory"]) + balance
            if "cash" in name or "bank" in name:
                values["cash"] = float(values["cash"]) + balance
        elif account_type == "liability":
            values["total_liabilities"] = float(values["total_liabilities"]) + balance
            if "current" in subtype:
                values["current_liabilities"] = float(values["current_liabilities"]) + balance
        elif account_type == "revenue":
            values["revenue"] = float(values["revenue"]) + balance
        elif account_type == "expense":
            values["expenses"] = float(values["expenses"]) + balance
    return values


def financial_snapshot() -> dict[str, Any]:
    profile = get_company_profile()
    current_assets = _single_value(
        "SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='asset' AND classification='current'"
    )
    current_liabilities = _single_value(
        "SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='liability' AND classification='current'"
    )
    inventory = _single_value(
        "SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='asset' AND lower(name) LIKE '%inventory%'"
    )
    cash = _single_value(
        "SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='asset' AND (id='asset-cash' OR lower(name) LIKE '%cash%')"
    )
    total_assets = _single_value("SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='asset'")
    total_liabilities = _single_value("SELECT COALESCE(SUM(amount), 0) AS value FROM assets_liabilities WHERE category='liability'")
    ledger = _ledger_financial_values()
    use_ledger = int(ledger["posted_lines"]) > 0
    if use_ledger:
        current_assets = float(ledger["current_assets"])
        current_liabilities = float(ledger["current_liabilities"])
        inventory = float(ledger["inventory"])
        cash = float(ledger["cash"])
        total_assets = float(ledger["total_assets"])
        total_liabilities = float(ledger["total_liabilities"])
    anomaly_count = int(_single_value("SELECT COUNT(*) AS value FROM transactions WHERE status IN ('anomaly', 'critical')"))

    monthly = rows_as_dicts("""
        SELECT strftime(transaction_date, '%Y-%m') AS month,
               SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS revenue,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expenses
        FROM transactions
        GROUP BY 1
        ORDER BY 1
    """)
    latest_revenue = float(monthly[-1]["revenue"] or 0) if monthly else 0.0
    latest_expenses = float(monthly[-1]["expenses"] or 0) if monthly else 0.0
    revenue_source = "transactions"
    if not monthly and (float(ledger["revenue"]) or float(ledger["expenses"])):
        latest_revenue = float(ledger["revenue"])
        latest_expenses = float(ledger["expenses"])
        revenue_source = "posted_ledger"
    if not monthly and not latest_revenue and not latest_expenses:
        latest_period = rows_as_dicts("SELECT MAX(period_end) AS period_end FROM statement_snapshots WHERE statement_type='profit_loss'")
        period_end = latest_period[0].get("period_end") if latest_period else None
        if period_end:
            statement_rows = rows_as_dicts(
                "SELECT amount FROM statement_snapshots WHERE statement_type='profit_loss' AND period_end=?",
                (period_end,),
            )
            latest_revenue = sum(float(row.get("amount") or 0) for row in statement_rows if float(row.get("amount") or 0) > 0)
            latest_expenses = abs(sum(float(row.get("amount") or 0) for row in statement_rows if float(row.get("amount") or 0) < 0))
            revenue_source = "profit_loss_snapshot"
    previous_revenue = float(monthly[-2]["revenue"] or 0) if len(monthly) > 1 else latest_revenue
    revenue_change = ((latest_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue else 0.0
    operating_margin = ((latest_revenue - latest_expenses) / latest_revenue * 100) if latest_revenue else 0.0
    avg_daily_expense = latest_expenses / 30 if latest_expenses else 0.0
    cash_runway_days = int(cash / avg_daily_expense) if avg_daily_expense else 0

    open_invoice_total = _single_value("SELECT COALESCE(SUM(amount), 0) AS value FROM invoices WHERE status NOT IN ('paid', 'cancelled')")
    overdue_invoice_total = _single_value(
        "SELECT COALESCE(SUM(amount), 0) AS value FROM invoices WHERE status NOT IN ('paid', 'cancelled') AND due_date < current_date"
    )
    revenue_for_days = max(latest_revenue, 1.0)
    receivable_days = round(open_invoice_total / revenue_for_days * 30)
    payable_days = round(current_liabilities / max(latest_expenses, 1.0) * 30)

    current_ratio = current_assets / current_liabilities if current_liabilities else None
    quick_ratio = (current_assets - inventory) / current_liabilities if current_liabilities else None
    debt_to_assets = total_liabilities / total_assets if total_assets else None

    return {
        "company": profile,
        "current_assets": round(current_assets, 2),
        "current_liabilities": round(current_liabilities, 2),
        "current_ratio": round(current_ratio, 2) if current_ratio is not None else None,
        "quick_ratio": round(quick_ratio, 2) if quick_ratio is not None else None,
        "working_capital": round(current_assets - current_liabilities, 2),
        "cash": round(cash, 2),
        "inventory": round(inventory, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "debt_to_assets": round(debt_to_assets, 2) if debt_to_assets is not None else None,
        "anomaly_count": anomaly_count,
        "revenue_month": round(latest_revenue, 2),
        "expenses_month": round(latest_expenses, 2),
        "revenue_change": round(revenue_change, 1),
        "gross_margin": round(operating_margin, 1),
        "receivable_days": int(receivable_days),
        "payable_days": int(payable_days),
        "cash_runway_days": cash_runway_days,
        "open_invoice_total": round(open_invoice_total, 2),
        "overdue_invoice_total": round(overdue_invoice_total, 2),
        "current_ratio_target": float(profile.get("current_ratio_target", 1.2)),
        "cash_runway_target_days": int(profile.get("cash_runway_target_days", 45)),
        "metric_sources": {
            "financial_position": "posted_ledger" if use_ledger else "assets_liabilities",
            "revenue_expenses": revenue_source,
            "cash": "posted_ledger" if use_ledger else "assets_liabilities",
        },
    }


def performance_series(months: int = 6) -> list[dict[str, Any]]:
    rows = rows_as_dicts("""
        SELECT strftime(transaction_date, '%Y-%m') AS month_key,
               SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS revenue,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expenses
        FROM transactions
        GROUP BY 1
        ORDER BY 1
    """)
    if not rows:
        latest = rows_as_dicts("SELECT MAX(period_end) AS period_end FROM statement_snapshots WHERE statement_type='profit_loss'")
        period_end = latest[0].get("period_end") if latest else None
        if period_end:
            statement_rows = rows_as_dicts(
                "SELECT amount FROM statement_snapshots WHERE statement_type='profit_loss' AND period_end=?",
                (period_end,),
            )
            revenue = sum(float(row.get("amount") or 0) for row in statement_rows if float(row.get("amount") or 0) > 0)
            expenses = abs(sum(float(row.get("amount") or 0) for row in statement_rows if float(row.get("amount") or 0) < 0))
            return [{"month": str(period_end), "revenue": round(revenue, 2), "expenses": round(expenses, 2)}]
    if rows:
        # Show the latest periods actually present in the source. Generating a
        # zero-valued current month when the latest bank export ends in the
        # previous month makes loaded data look missing.
        result = []
        for row in rows[-months:]:
            key = str(row.get("month_key") or "")
            try:
                label = datetime.strptime(key, "%Y-%m").strftime("%b")
            except ValueError:
                label = key
            result.append({
                "month": label,
                "revenue": round(float(row.get("revenue") or 0), 2),
                "expenses": round(float(row.get("expenses") or 0), 2),
            })
        return result
    return []


def cash_forecast(days: int = 90) -> dict[str, Any]:
    snapshot = financial_snapshot()
    recent = rows_as_dicts("""
        SELECT transaction_date, amount
        FROM transactions
        WHERE transaction_date >= current_date - INTERVAL 90 DAY
        ORDER BY transaction_date
    """)
    total_net = sum(float(row["amount"] or 0) for row in recent)
    covered_days = 90 if recent else 30
    daily_net = total_net / covered_days

    due_rows = rows_as_dicts("""
        SELECT due_date, amount FROM invoices
        WHERE status NOT IN ('paid', 'cancelled')
          AND due_date BETWEEN current_date AND current_date + INTERVAL 90 DAY
        ORDER BY due_date
    """)
    due_by_date: dict[date, float] = defaultdict(float)
    for row in due_rows:
        due = row["due_date"]
        if isinstance(due, datetime):
            due = due.date()
        due_by_date[due] += float(row["amount"] or 0)

    balance = float(snapshot["cash"])
    today = date.today()
    points: list[dict[str, Any]] = []
    for day_offset in range(0, days + 1, 7):
        point_date = today + timedelta(days=day_offset)
        if day_offset:
            balance += daily_net * 7
            for due_date, amount in due_by_date.items():
                if point_date - timedelta(days=6) <= due_date <= point_date:
                    balance -= amount
        points.append({
            "date": point_date.isoformat(),
            "label": point_date.strftime("%d %b"),
            "forecast": round(balance, 2),
        })
    return {
        "days": days,
        "starting_cash": snapshot["cash"],
        "daily_net_assumption": round(daily_net, 2),
        "series": points,
        "low_point": min((item["forecast"] for item in points), default=snapshot["cash"]),
        "method": "Recent 90-day average net movement adjusted for known unpaid invoice due dates.",
    }




def financial_position_series() -> list[dict[str, Any]]:
    rows = rows_as_dicts("""
        SELECT
          CASE
            WHEN category='asset' AND lower(name) LIKE '%cash%' THEN 'Cash'
            WHEN category='asset' AND lower(name) LIKE '%receivable%' THEN 'Receivables'
            WHEN category='asset' AND lower(name) LIKE '%inventory%' THEN 'Inventory'
            WHEN category='asset' AND classification='current' THEN 'Other current assets'
            WHEN category='asset' THEN 'Non-current assets'
            WHEN category='liability' AND classification='current' THEN 'Current liabilities'
            WHEN category='liability' THEN 'Non-current liabilities'
            ELSE 'Other'
          END AS label,
          SUM(amount) AS value
        FROM assets_liabilities
        GROUP BY 1
        HAVING ABS(SUM(amount)) > 0.005
        ORDER BY CASE label
          WHEN 'Cash' THEN 1 WHEN 'Receivables' THEN 2 WHEN 'Inventory' THEN 3
          WHEN 'Other current assets' THEN 4 WHEN 'Non-current assets' THEN 5
          WHEN 'Current liabilities' THEN 6 WHEN 'Non-current liabilities' THEN 7 ELSE 8 END
    """)
    if not rows:
        rows = rows_as_dicts("""
            SELECT
              CASE
                WHEN c.account_type='asset' AND (lower(c.name) LIKE '%cash%' OR lower(c.name) LIKE '%bank%') THEN 'Cash'
                WHEN c.account_type='asset' AND lower(c.name) LIKE '%receivable%' THEN 'Receivables'
                WHEN c.account_type='asset' AND lower(c.name) LIKE '%inventory%' THEN 'Inventory'
                WHEN c.account_type='asset' AND lower(c.subtype) LIKE '%current%' AND lower(c.subtype) NOT LIKE '%non-current%' THEN 'Other current assets'
                WHEN c.account_type='asset' THEN 'Non-current assets'
                WHEN c.account_type='liability' AND lower(c.subtype) LIKE '%current%' THEN 'Current liabilities'
                WHEN c.account_type='liability' THEN 'Non-current liabilities'
                ELSE 'Other'
              END AS label,
              SUM(CASE WHEN c.account_type IN ('asset','expense') THEN l.debit-l.credit ELSE l.credit-l.debit END) AS value
            FROM journal_lines l
            JOIN journal_entries e ON e.id=l.journal_id AND e.status='posted'
            JOIN chart_of_accounts c ON c.code=l.account_code
            WHERE c.account_type IN ('asset','liability')
            GROUP BY 1
            HAVING ABS(SUM(CASE WHEN c.account_type IN ('asset','expense') THEN l.debit-l.credit ELSE l.credit-l.debit END)) > 0.005
        """)
    return [{"label": str(row.get("label") or "Other"), "value": round(abs(float(row.get("value") or 0)), 2)} for row in rows]


def profit_structure() -> dict[str, Any]:
    latest = rows_as_dicts("SELECT MAX(period_end) AS period_end FROM statement_snapshots WHERE statement_type='profit_loss'")
    period_end = latest[0].get("period_end") if latest else None
    if not period_end:
        return {"period_end": "", "series": [], "revenue": 0.0, "costs": 0.0, "profit": 0.0}
    rows = rows_as_dicts(
        "SELECT line_item, amount FROM statement_snapshots WHERE statement_type='profit_loss' AND period_end=?",
        (period_end,),
    )
    revenue = sum(float(row.get("amount") or 0) for row in rows if float(row.get("amount") or 0) > 0)
    costs = abs(sum(float(row.get("amount") or 0) for row in rows if float(row.get("amount") or 0) < 0))
    profit = revenue - costs
    cogs = abs(sum(float(row.get("amount") or 0) for row in rows if any(token in str(row.get("line_item") or "").lower() for token in ("cost of goods", "cogs", "cost of sales"))))
    finance_tax = abs(sum(float(row.get("amount") or 0) for row in rows if any(token in str(row.get("line_item") or "").lower() for token in ("interest", "tax")) and float(row.get("amount") or 0) < 0))
    operating = max(0.0, costs - cogs - finance_tax)
    series = [
        {"label": "Revenue", "value": round(revenue, 2)},
        {"label": "Cost of goods", "value": round(cogs, 2)},
        {"label": "Operating costs", "value": round(operating, 2)},
        {"label": "Finance & tax", "value": round(finance_tax, 2)},
        {"label": "Net profit", "value": round(profit, 2)},
    ]
    return {"period_end": str(period_end), "series": series, "revenue": round(revenue, 2), "costs": round(costs, 2), "profit": round(profit, 2)}


def invoice_exposure_series() -> list[dict[str, Any]]:
    rows = rows_as_dicts("""
        SELECT
          CASE WHEN invoice_kind='sales' THEN 'Receivables' ELSE 'Payables' END AS label,
          SUM(CASE WHEN status NOT IN ('paid','cancelled') THEN amount ELSE 0 END) AS open_total,
          SUM(CASE WHEN status NOT IN ('paid','cancelled') AND due_date < current_date THEN amount ELSE 0 END) AS overdue_total
        FROM invoices
        GROUP BY 1
        ORDER BY 1
    """)
    return [{
        "label": str(row.get("label") or "Invoices"),
        "open": round(abs(float(row.get("open_total") or 0)), 2),
        "overdue": round(abs(float(row.get("overdue_total") or 0)), 2),
    } for row in rows]


def dashboard_summary() -> dict[str, Any]:
    snapshot = financial_snapshot()
    forecast = cash_forecast(90)
    validation_count = int(_single_value("SELECT COUNT(*) AS value FROM validations WHERE COALESCE(status, 'open')='open'"))
    account_review_count = int(_single_value("SELECT COUNT(*) AS value FROM account_validation_tasks WHERE status='open'"))
    monthly = performance_series(6)
    cash_series = []
    for item in monthly:
        cash_series.append({"month": item["month"], "cash": None, "forecast": None})
    # Keep a compact three-point forecast for the overview chart.
    forecast_points = forecast["series"]
    if forecast_points:
        cash_series = [
            {"month": "Now", "cash": snapshot["cash"], "forecast": snapshot["cash"]},
            {"month": "30d", "cash": None, "forecast": forecast_points[min(4, len(forecast_points) - 1)]["forecast"]},
            {"month": "60d", "cash": None, "forecast": forecast_points[min(8, len(forecast_points) - 1)]["forecast"]},
            {"month": "90d", "cash": None, "forecast": forecast_points[-1]["forecast"]},
        ]
    profit = profit_structure()
    return {
        **snapshot,
        "critical_alerts": validation_count + account_review_count,
        "business_validation_count": validation_count,
        "account_review_count": account_review_count,
        "cash_series": cash_series,
        "performance_series": monthly,
        "position_series": financial_position_series(),
        "profit_structure": profit,
        "invoice_exposure_series": invoice_exposure_series(),
        "forecast_low_point": round(float(forecast.get("low_point") or 0), 2),
        "forecast_method": forecast["method"],
    }


def _load_context_json(name: str) -> dict[str, Any]:
    path = settings.data_path / "context" / COMPANY_ID / name
    if not path.exists():
        return {}
    try:
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def agent_data_context() -> dict[str, Any]:
    snapshot = financial_snapshot()
    assets = rows_as_dicts("SELECT id, name, category, classification, amount, status, source_file FROM assets_liabilities ORDER BY amount DESC LIMIT 20")
    invoices = rows_as_dicts("SELECT id, invoice_number, supplier, invoice_date, due_date, amount, status, source_file FROM invoices ORDER BY invoice_date DESC LIMIT 15")
    transactions = rows_as_dicts("SELECT id, transaction_date, description, category, amount, status, source_file FROM transactions ORDER BY transaction_date DESC LIMIT 20")
    validations = rows_as_dicts("SELECT id, severity, check_name, description, target_id, recommendation, status FROM validations WHERE COALESCE(status, 'open')='open' ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END LIMIT 15")
    market_signals = rows_as_dicts("SELECT signal_type, topic, entity, geography, direction, relevance_score, estimated_impact, source_name, source_url FROM market_signals ORDER BY relevance_score DESC NULLS LAST LIMIT 12")
    return {
        "snapshot": snapshot,
        "assets_liabilities": assets,
        "recent_invoices": invoices,
        "recent_transactions": transactions,
        "open_validations": validations,
        "forecast": cash_forecast(90),
        "company_baseline": _load_context_json("company_baseline.json"),
        "market_profile": _load_context_json("market_profile.json"),
        "market_snapshot": _load_context_json("latest_market_snapshot.json"),
        "information_requests": _load_context_json("information_requests.json"),
        "market_signals": market_signals,
    }
