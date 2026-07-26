from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .analytics import financial_snapshot
from .config import settings
from .decision_context import record_analysis_event, refresh_decision_context
from .database import (
    COMPANY_ID,
    create_competitor_analysis_job,
    get_company_profile,
    get_competitor_analysis_job,
    latest_competitor_analysis_job,
    rows_as_dicts,
    update_competitor_analysis_job,
    utc_now,
)
from .research import search_web
from .upload_intelligence import market_intelligence_path, read_company_context, write_company_context
from .analysis_context import read_analysis_context_files, refresh_market_report_reference


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float, minimum: float = 0, maximum: float = 140) -> float:
    return round(max(minimum, min(maximum, value)), 1)


def _numeric(value: Any) -> float | None:
    text = str(value or "").replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _company_dimensions(snapshot: dict[str, Any]) -> dict[str, float]:
    ratio = float(snapshot.get("current_ratio") or 0)
    ratio_target = float(snapshot.get("current_ratio_target") or 1.2) or 1.2
    runway = float(snapshot.get("cash_runway_days") or 0)
    runway_target = float(snapshot.get("cash_runway_target_days") or 45) or 45
    margin = float(snapshot.get("gross_margin") or 0)
    growth = float(snapshot.get("revenue_change") or 0)
    return {
        "Liquidity": _clamp((ratio / ratio_target) * 100),
        "Cash resilience": _clamp((runway / runway_target) * 100),
        "Margin strength": _clamp((margin / 30.0) * 100),
        "Revenue momentum": _clamp(50 + growth * 3.0),
    }


def _competitor_dimensions(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for signal in signals:
        entity = str(signal.get("entity") or "").strip()
        if not entity:
            continue
        topic = f"{signal.get('signal_type', '')} {signal.get('topic', '')}".lower()
        value = _numeric(signal.get("value"))
        if value is None:
            continue
        dimensions = grouped.setdefault(entity, {})
        if any(token in topic for token in ["current ratio", "liquidity", "working capital"]):
            dimensions.setdefault("Liquidity", []).append(_clamp((value / 1.2) * 100))
        elif any(token in topic for token in ["margin", "profitability", "gross profit"]):
            dimensions.setdefault("Margin strength", []).append(_clamp((value / 30.0) * 100))
        elif any(token in topic for token in ["growth", "revenue", "sales"]):
            dimensions.setdefault("Revenue momentum", []).append(_clamp(50 + value * 3.0))
        elif any(token in topic for token in ["cash", "runway", "resilience", "debt"]):
            dimensions.setdefault("Cash resilience", []).append(_clamp(value))
    result: list[dict[str, Any]] = []
    for entity, values in grouped.items():
        dimensions = {key: round(sum(items) / len(items), 1) for key, items in values.items() if items}
        result.append({
            "entity": entity,
            "dimensions": dimensions,
            "verified_dimensions": len(dimensions),
            "score": round(sum(dimensions.values()) / len(dimensions), 1) if len(dimensions) >= 2 else None,
            "status": "comparable" if len(dimensions) >= 2 else "more verified metrics required",
        })
    return sorted(result, key=lambda item: float(item.get("score") or -1), reverse=True)


def _deterministic_chart_slots(snapshot: dict[str, Any], signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if signals:
        first = {
            "id": "risk_exposure",
            "title": "External risk exposure by topic",
            "chart_type": "weighted_bar",
            "reason": "Uploaded market signals can be ranked by relevance and estimated business impact.",
            "data_requirements": ["Market signal topic", "Relevance score", "Estimated impact"],
            "status": "ready" if len(signals) >= 3 else "waiting_for_more_data",
        }
    else:
        first = {
            "id": "risk_exposure",
            "title": "External risk exposure by topic",
            "chart_type": "weighted_bar",
            "reason": "This becomes useful after market-context or competitor evidence is uploaded.",
            "data_requirements": ["Market context file", "Competitor names", "Risk relevance"],
            "status": "empty",
        }
    if float(snapshot.get("receivable_days") or 0) or float(snapshot.get("payable_days") or 0):
        second = {
            "id": "cash_conversion",
            "title": "Cash conversion versus peer benchmark",
            "chart_type": "range_and_marker",
            "reason": "Receivable and payable timing are available locally; verified peer values are still required.",
            "data_requirements": ["Receivable days", "Payable days", "Verified peer benchmark"],
            "status": "partial",
        }
    else:
        second = {
            "id": "supplier_concentration",
            "title": "Supplier and customer concentration",
            "chart_type": "treemap",
            "reason": "Concentration can reveal dependence risk when supplier/customer master data and transaction values are present.",
            "data_requirements": ["Supplier master", "Customer master", "Purchases or sales by counterparty"],
            "status": "empty",
        }
    return [first, second]


def _nvidia_chart_slots(company: dict[str, Any], snapshot: dict[str, Any], signals: list[dict[str, Any]], fallback: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    if settings.model_provider.strip().lower() != "nvidia" or not settings.nvidia_api_key:
        return fallback, "deterministic chart planner"
    prompt = {
        "task": "Select exactly two useful future competitor-analysis chart slots. Do not invent any figures.",
        "allowed_chart_types": ["weighted_bar", "range_and_marker", "treemap", "scatter", "radar", "line"],
        "company": {key: company.get(key) for key in ["industry", "primary_location", "current_objective", "primary_risks"]},
        "available_company_metrics": {key: snapshot.get(key) for key in ["current_ratio", "cash_runway_days", "gross_margin", "revenue_change", "receivable_days", "payable_days"]},
        "uploaded_market_signal_count": len(signals),
        "market_analysis_template": read_analysis_context_files().get("market_analysis_template", {}),
        "business_analyst_context": read_analysis_context_files().get("business_analyst_context", {}).get("sections", {}).get("intelligence", {}),
        "output_schema": [{"id": "snake_case", "title": "text", "chart_type": "allowed value", "reason": "text", "data_requirements": ["text"], "status": "ready|partial|empty"}],
    }
    payload = {
        "model": settings.nvidia_model,
        "messages": [
            {"role": "system", "content": "Return only a valid JSON array of two chart slot objects. Never create competitor numbers or claims."},
            {"role": "user", "content": json.dumps(prompt, default=str)},
        ],
        "temperature": 0.1,
        "max_tokens": 420,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(35.0, connect=12.0), trust_env=False) as client:
            response = client.post(
                f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        content = str((((response.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) == 2:
            clean = []
            allowed = {"weighted_bar", "range_and_marker", "treemap", "scatter", "radar", "line"}
            for index, item in enumerate(parsed):
                if not isinstance(item, dict):
                    raise ValueError("chart slot is not an object")
                chart_type = str(item.get("chart_type") or fallback[index]["chart_type"])
                clean.append({
                    "id": str(item.get("id") or fallback[index]["id"])[:60],
                    "title": str(item.get("title") or fallback[index]["title"])[:120],
                    "chart_type": chart_type if chart_type in allowed else fallback[index]["chart_type"],
                    "reason": str(item.get("reason") or fallback[index]["reason"])[:320],
                    "data_requirements": [str(value)[:120] for value in list(item.get("data_requirements") or [])[:6]],
                    "status": str(item.get("status") or fallback[index]["status"]),
                })
            return clean, f"NVIDIA chart planner: {settings.nvidia_model}"
    except Exception as exc:
        return fallback, f"deterministic chart planner (NVIDIA unavailable: {type(exc).__name__})"
    return fallback, "deterministic chart planner"


def _materialise_chart_slots(
    slots: list[dict[str, Any]],
    snapshot: dict[str, Any],
    signals: list[dict[str, Any]],
    competitors: list[dict[str, Any]],
    company_dimensions: dict[str, float],
) -> list[dict[str, Any]]:
    """Attach real, bounded datasets to the two planned charts.

    NVIDIA may select useful chart concepts, but it never supplies figures. This
    step ensures the UI receives only figures already present in company records
    or uploaded market evidence.
    """
    operating_data = [
        {"label": label, "value": round(float(value), 1)}
        for label, value in company_dimensions.items()
    ]
    competitor_data = [
        {
            "label": str(item.get("entity") or "Competitor")[:32],
            "value": int(item.get("verified_dimensions") or 0),
        }
        for item in competitors[:8]
    ]
    signal_data = [
        {
            "label": str(item.get("topic") or item.get("signal_type") or "Market signal")[:32],
            "value": round(float(item.get("relevance_score") or 0) * 100, 1),
        }
        for item in signals[:8]
        if item.get("relevance_score") is not None
    ]
    working_capital_data = [
        {"label": "Receivable days", "value": round(float(snapshot.get("receivable_days") or 0), 1)},
        {"label": "Payable days", "value": round(float(snapshot.get("payable_days") or 0), 1)},
        {"label": "Cash runway", "value": round(float(snapshot.get("cash_runway_days") or 0), 1)},
    ]
    working_capital_data = [item for item in working_capital_data if item["value"]]

    datasets = [
        (
            "Market-signal relevance",
            signal_data,
            "Uploaded market evidence · relevance score (%)",
        ) if signal_data else (
            "Company operating strength",
            operating_data,
            "Verified business.db metrics · normalised score",
        ),
        (
            "Competitor evidence coverage",
            competitor_data,
            "Uploaded competitor evidence · verified comparable dimensions",
        ) if competitor_data else (
            "Working-capital operating days",
            working_capital_data or operating_data,
            "Verified business.db metrics",
        ),
    ]
    materialised: list[dict[str, Any]] = []
    for index, slot in enumerate(slots[:2]):
        title, data, source_note = datasets[index]
        materialised.append({
            **slot,
            "title": title,
            "chart_type": "bar",
            "status": "ready" if data else "empty",
            "data": data,
            "x_key": "label",
            "y_key": "value",
            "source_note": source_note,
        })
    return materialised


def _research(company: dict[str, Any]) -> dict[str, Any]:
    company_name = re.sub(
        r"\s*[-–—]\s*(?:synthetic|demonstration|demo).*$",
        "",
        str(company.get("company_name") or ""),
        flags=re.IGNORECASE,
    ).strip()
    query = f"{company_name} {company.get('industry', '')} direct competitors market {company.get('primary_location', '')}".strip()
    try:
        return asyncio.run(search_web(query, limit=8))
    except Exception as exc:
        return {"live": False, "message": f"Market research unavailable: {type(exc).__name__}", "results": []}


def _nvidia_research_competitors(company: dict[str, Any], research: dict[str, Any]) -> list[dict[str, Any]]:
    results = list(research.get("results") or [])
    if not results or settings.model_provider.strip().lower() != "nvidia" or not settings.nvidia_api_key:
        return []
    evidence = [
        {"source_index": index, "title": item.get("title"), "snippet": item.get("content"), "url": item.get("url")}
        for index, item in enumerate(results)
    ]
    prompt = {
        "task": "Identify up to six direct competitors of the named company only when supported by the supplied search evidence.",
        "company": company.get("company_name"),
        "industry": company.get("industry"),
        "rules": [
            "Do not use the target company as a competitor.",
            "Do not invent financial figures, rankings or market shares.",
            "Every competitor must cite one valid source_index from the evidence.",
            "Return an empty array when the evidence does not support a direct competitor.",
        ],
        "evidence": evidence,
        "output_schema": [{"entity": "company name", "evidence_summary": "short supported explanation", "source_index": 0}],
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(40.0, connect=12.0), trust_env=False) as client:
            response = client.post(
                f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.nvidia_model,
                    "messages": [
                        {"role": "system", "content": "Return only a valid JSON array grounded in the supplied evidence."},
                        {"role": "user", "content": json.dumps(prompt, default=str)},
                    ],
                    "temperature": 0,
                    "max_tokens": 700,
                    "stream": False,
                },
            )
            response.raise_for_status()
        content = str((((response.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        parsed = json.loads(content)
        competitors: list[dict[str, Any]] = []
        target = str(company.get("company_name") or "").lower()
        for item in list(parsed or [])[:6]:
            source_index = int(item.get("source_index"))
            entity = str(item.get("entity") or "").strip()
            if not entity or entity.lower() in target or not (0 <= source_index < len(results)):
                continue
            source = results[source_index]
            competitors.append({
                "entity": entity,
                "dimensions": {},
                "verified_dimensions": 0,
                "score": None,
                "status": "current research evidence",
                "evidence_summary": str(item.get("evidence_summary") or "")[:320],
                "source_title": str(source.get("title") or ""),
                "source_url": str(source.get("url") or ""),
            })
        return competitors
    except Exception:
        return []


def build_competitor_analysis() -> dict[str, Any]:
    company = get_company_profile()
    snapshot = financial_snapshot()
    signals = rows_as_dicts(
        "SELECT signal_type, topic, entity, geography, observed_at, published_at, value, unit, direction, source_name, source_url, relevance_score, estimated_impact, impact_horizon FROM market_signals ORDER BY relevance_score DESC NULLS LAST LIMIT 100"
    )
    company_dimensions = _company_dimensions(snapshot)
    company_score = round(sum(company_dimensions.values()) / len(company_dimensions), 1)
    competitors = _competitor_dimensions(signals)
    fallback_slots = _deterministic_chart_slots(snapshot, signals)
    slots, slot_planner = _nvidia_chart_slots(company, snapshot, signals, fallback_slots)
    research = _research(company)
    research_competitors = _nvidia_research_competitors(company, research)
    existing_names = {str(item.get("entity") or "").strip().lower() for item in competitors}
    competitors.extend(item for item in research_competitors if str(item.get("entity") or "").strip().lower() not in existing_names)
    comparable = [item for item in competitors if item.get("score") is not None]
    slots = _materialise_chart_slots(slots, snapshot, signals, competitors, company_dimensions)
    strongest = sorted(company_dimensions.items(), key=lambda item: item[1], reverse=True)
    watch_signals = [
        str(item.get("topic") or item.get("signal_type") or "")
        for item in signals
        if str(item.get("topic") or item.get("signal_type") or "").strip()
    ][:5]
    result = {
        "version": 2,
        "generated_at": _now(),
        "data_mode": {
            "internal": "synthetic_demonstration" if re.search(r"\b(?:synthetic|demonstration|demo)\b", str(company.get("company_name") or ""), re.IGNORECASE) else "uploaded_company_evidence",
            "external": "current_cited_research" if research.get("live") else "uploaded_market_evidence_only",
        },
        "company": {
            "name": company.get("company_name") or "Your company",
            "industry": company.get("industry") or "Not specified",
            "location": company.get("primary_location") or "Not specified",
            "score": company_score,
            "dimensions": company_dimensions,
            "score_method": "Normalised local liquidity, runway, margin and revenue-momentum indicators; not an external credit rating.",
        },
        "competitors": competitors,
        "comparison_ready": bool(comparable),
        "comparison_note": (
            f"{len(comparable)} competitor(s) have at least two verified comparable dimensions."
            if comparable else
            "No competitor has enough verified numeric evidence yet. Upload a market-context file with competitor entities and metrics; LedgerFlow will not fabricate peer values."
        ),
        "positioning_chart": {
            "title": "Company position versus verified competitors",
            "dimensions": list(company_dimensions),
            "series": [{"entity": company.get("company_name") or "Your company", "score": company_score, "dimensions": company_dimensions, "verified": True}] + [
                {"entity": item["entity"], "score": item["score"], "dimensions": item["dimensions"], "verified": True}
                for item in comparable
            ],
        },
        "agent_chart_slots": slots,
        "chart_planner": slot_planner,
        "competitive_brief": {
            "evidence_basis": "Uploaded company and competitor evidence plus configured cited web research.",
            "named_competitors": [item["entity"] for item in competitors],
            "company_strengths": [f"{name}: {value:.1f}/140" for name, value in strongest[:2]],
            "watch_items": watch_signals,
            "research_result_count": len(list(research.get("results") or [])),
        },
        "market_signals": signals[:20],
        "research": {
            "live": bool(research.get("live")),
            "message": research.get("message") or "",
            "results": list(research.get("results") or [])[:8],
        },
        "data_gaps": [
            "Competitor names and comparable metrics" if not competitors else "Additional comparable dimensions for each competitor",
            "Verified market-share or revenue benchmark",
            "Peer margin, liquidity and cash-conversion measures",
        ],
        "summary": (
            f"The local company position score is {company_score:.1f}/140 across four normalised operating dimensions. "
            + (f"{len(comparable)} competitor(s) can be compared using uploaded evidence." if comparable else "Verified competitor metrics are not yet sufficient for a peer ranking.")
        ),
    }
    market_intelligence_path().write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    context = read_company_context()
    context["market_intelligence"] = {
        "status": "completed",
        "last_started_at": context.get("market_intelligence", {}).get("last_started_at"),
        "last_completed_at": result["generated_at"],
        "summary": result["summary"],
        "comparison_ready": result["comparison_ready"],
        "competitor_count": len(competitors),
        "verified_comparable_count": len(comparable),
        "chart_slots": slots,
        "result_file": str(market_intelligence_path()),
    }
    write_company_context(context)
    try:
        refresh_market_report_reference()
    except Exception as exc:
        print(f"Market analysis context refresh failed: {type(exc).__name__}: {exc}")
    return result


def _active_job_is_fresh(job: dict[str, Any], max_age_seconds: int = 180) -> bool:
    if str(job.get("status") or "") not in {"queued", "processing"}:
        return False
    raw = str(job.get("updated_at") or job.get("created_at") or "")
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - timestamp).total_seconds() <= max_age_seconds
    except Exception:
        return False


def start_analysis_job() -> dict[str, Any]:
    existing = latest_competitor_analysis_job()
    if existing and _active_job_is_fresh(existing):
        return {**existing, "start_background": False}
    if existing and str(existing.get("status") or "") in {"queued", "processing"}:
        update_competitor_analysis_job(
            str(existing.get("job_id")), status="failed", stage="failed", progress=100,
            stage_message="A stale analysis job was recovered after restart",
            error_message="The previous process ended before the analysis completed.", completed_at=utc_now(),
        )
    job_id = f"marketjob_{uuid.uuid4().hex[:18]}"
    context = read_company_context()
    market = dict(context.get("market_intelligence") or {})
    market.update({"status": "queued", "last_started_at": _now(), "summary": "Deep company and competitor analysis is queued."})
    context["market_intelligence"] = market
    write_company_context(context)
    created = create_competitor_analysis_job(job_id)
    try:
        refresh_decision_context("competitor_analysis_started")
        record_analysis_event(job_id, "queued", "Deep company and competitor analysis queued.")
    except Exception as exc:
        print(f"Decision context analysis-start record failed: {type(exc).__name__}: {exc}")
    return {**created, "start_background": True}


def process_analysis_job(job_id: str) -> None:
    def stage(name: str, progress: int, message: str) -> None:
        update_competitor_analysis_job(job_id, status="processing", stage=name, progress=progress, stage_message=message)
        time.sleep(0.12)
    try:
        stage("company", 12, "Reading the verified company profile and operating metrics")
        stage("evidence", 30, "Collecting uploaded market signals and competitor evidence")
        stage("positioning", 52, "Normalising comparable company-position dimensions")
        stage("research", 68, "Checking the configured market-research source")
        stage("charts", 82, "Selecting two high-value chart slots without inventing figures")
        result = build_competitor_analysis()
        stage("context", 95, "Saving market intelligence as a separate agent-context category")
        update_competitor_analysis_job(
            job_id, status="completed", stage="completed", progress=100,
            stage_message="Deep company and competitor analysis completed",
            result_json=result, completed_at=utc_now(),
        )
        try:
            refresh_decision_context("competitor_analysis_completed")
            record_analysis_event(job_id, "completed", str(result.get("summary") or "Deep company and competitor analysis completed."), result)
        except Exception as exc:
            print(f"Decision context analysis-completion record failed: {type(exc).__name__}: {exc}")
    except Exception as exc:
        context = read_company_context()
        market = dict(context.get("market_intelligence") or {})
        market.update({"status": "failed", "summary": f"Deep analysis failed: {type(exc).__name__}: {exc}"})
        context["market_intelligence"] = market
        write_company_context(context)
        update_competitor_analysis_job(
            job_id, status="failed", stage="failed", progress=100,
            stage_message="Deep analysis stopped", error_message=f"{type(exc).__name__}: {exc}", completed_at=utc_now(),
        )
        try:
            record_analysis_event(job_id, "failed", f"Deep analysis failed: {type(exc).__name__}: {exc}")
        except Exception as context_exc:
            print(f"Decision context analysis-failure record failed: {type(context_exc).__name__}: {context_exc}")


def analysis_status() -> dict[str, Any]:
    job = latest_competitor_analysis_job()
    result: dict[str, Any] = {}
    if market_intelligence_path().exists():
        try: result = json.loads(market_intelligence_path().read_text(encoding="utf-8"))
        except Exception: result = {}
    # Upgrade saved v1 results so old blank chart slots become real charts
    # immediately after installing v3, even before the next full analysis run.
    slots = list(result.get("agent_chart_slots") or [])
    if result and (int(result.get("version") or 1) < 2 or any(not item.get("data") for item in slots)):
        snapshot = financial_snapshot()
        signals = rows_as_dicts(
            "SELECT signal_type, topic, entity, geography, observed_at, published_at, value, unit, direction, source_name, source_url, relevance_score, estimated_impact, impact_horizon FROM market_signals ORDER BY relevance_score DESC NULLS LAST LIMIT 100"
        )
        competitors = list(result.get("competitors") or _competitor_dimensions(signals))
        dimensions = dict((result.get("company") or {}).get("dimensions") or _company_dimensions(snapshot))
        fallback = slots[:2] if len(slots) >= 2 else _deterministic_chart_slots(snapshot, signals)
        result["agent_chart_slots"] = _materialise_chart_slots(fallback, snapshot, signals, competitors, dimensions)
        result["version"] = 2
        market_intelligence_path().write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {
        "job": job,
        "result": result,
        "context": read_company_context().get("market_intelligence", {}),
        "result_file": str(market_intelligence_path()),
    }
