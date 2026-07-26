from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings
from .data_quality import data_quality_dashboard
from .analytics import dashboard_summary
from .tax import tax_dashboard
from .marketing import marketing_dashboard
from .upload_intelligence import upload_library


def semantic_root() -> Path:
    return settings.root_dir / "analytics" / "semantic_layer"


def _read_json(name: str, fallback: dict[str, Any]) -> dict[str, Any]:
    path = semantic_root() / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else fallback
    except Exception:
        return fallback


def semantic_layer_status() -> dict[str, Any]:
    """Return semantic metadata without allowing one dashboard read to fail the endpoint.

    The frontend loads several panels together. Re-reading every dashboard inside this
    endpoint can briefly collide with another local database reader or with an upload
    commit. Semantic metadata is optional, so it must degrade to a partial response
    rather than returning HTTP 500 and presenting a dashboard refresh warning.
    """
    metrics_payload = _read_json("metrics.json", {"version": "unknown", "metrics": []})
    dashboard = _read_json("dashboard.json", {"version": "unknown", "sections": []})
    sources = _read_json("source_inventory.json", {"version": "unknown", "sources": []})
    actions = _read_json("actions.json", {"version": "unknown", "actions": []})

    warnings: list[str] = []

    def safe_read(label: str, reader, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = reader()
            return payload if isinstance(payload, dict) else fallback
        except Exception as exc:
            warnings.append(f"{label}: {type(exc).__name__}: {exc}")
            return fallback

    library = safe_read("upload library", upload_library, {"coverage": {}})
    coverage = library.get("coverage") or {}
    ready_documents = set(coverage.get("required_received") or []) | set(coverage.get("recommended_received") or []) | set(coverage.get("recurring_received") or [])
    quality = safe_read("data quality", data_quality_dashboard, {"score": None, "status": "temporarily_unavailable", "open_check_total": None})
    summary = safe_read("dashboard summary", dashboard_summary, {})
    tax = safe_read("tax dashboard", tax_dashboard, {"summary": {}})
    marketing = safe_read("marketing dashboard", marketing_dashboard, {"summary": {}, "mode": "unknown"})
    value_map = {
        "cash_balance": summary.get("cash"),
        "working_capital": summary.get("working_capital"),
        "current_ratio": summary.get("current_ratio"),
        "net_profit": (summary.get("profit_structure") or {}).get("profit"),
        "monthly_inflows": summary.get("revenue_month"),
        "monthly_outflows": summary.get("expenses_month"),
        "overdue_invoice_total": summary.get("overdue_invoice_total"),
        "taxable_profit": (tax.get("summary") or {}).get("estimated_taxable_income"),
        "marketing_roas": (marketing.get("summary") or {}).get("roas"),
        "data_trust_score": quality.get("score"),
    }

    metrics: list[dict[str, Any]] = []
    for definition in metrics_payload.get("metrics") or []:
        item = dict(definition)
        metric_id = str(item.get("id") or "")
        required = set(item.get("required_documents") or [])
        missing = sorted(required - ready_documents)
        status = "blocked" if missing else "ready"
        if metric_id == "taxable_profit" and not missing:
            basis = str((tax.get("summary") or {}).get("profit_basis") or "").lower()
            status = "provisional" if "provisional" in basis or "snapshot" in basis else "ready"
        elif metric_id == "marketing_roas" and not missing:
            status = "ready" if str(marketing.get("mode") or "") == "actual" else "provisional"
        item.update({"status": status, "missing_documents": missing, "value": value_map.get(metric_id)})
        metrics.append(item)

    sections: list[dict[str, Any]] = []
    core_ready = not bool(coverage.get("required_missing"))
    for definition in dashboard.get("sections") or []:
        item = dict(definition)
        item["status"] = "ready" if core_ready or not item.get("requires_core_setup") else "blocked"
        sections.append(item)

    return {
        "version": metrics_payload.get("version") or dashboard.get("version") or "1.0.0",
        "root": str(semantic_root()),
        "metrics": metrics,
        "dashboard": {**dashboard, "sections": sections},
        "sources": sources,
        "actions": actions,
        "core_setup_complete": core_ready,
        "quality": {"score": quality.get("score"), "status": quality.get("status"), "open_check_total": quality.get("open_check_total")},
        "degraded": bool(warnings),
        "warnings": warnings,
    }
