from __future__ import annotations

from datetime import datetime, timezone
import asyncio
from typing import Any

import httpx

from .config import settings
from .database import get_company_profile, rows_as_dicts, save_research_cache


async def search_web(query: str, limit: int = 6) -> dict[str, Any]:
    provider = settings.web_search_provider.lower().strip()
    if provider != "searxng":
        try:
            from ddgs import DDGS

            def run_search() -> list[dict[str, Any]]:
                raw = DDGS(timeout=18).text(query, max_results=limit)
                return [
                    {
                        "title": str(item.get("title") or item.get("href") or "Research result"),
                        "url": str(item.get("href") or item.get("url") or ""),
                        "content": str(item.get("body") or item.get("content") or "")[:600],
                        "engine": "DDGS metasearch",
                        "publishedDate": str(item.get("date") or ""),
                    }
                    for item in list(raw or [])
                    if str(item.get("href") or item.get("url") or "")
                ][:limit]

            results = await asyncio.to_thread(run_search)
            save_research_cache(query, "ddgs", results)
            return {
                "live": bool(results),
                "provider": "ddgs",
                "message": (
                    f"Retrieved {len(results)} current web results at {datetime.now(timezone.utc).isoformat()}."
                    if results else "No relevant current web results were returned."
                ),
                "results": results,
            }
        except Exception as exc:
            return {
                "live": False,
                "provider": "ddgs",
                "message": f"Automatic web research was unavailable: {type(exc).__name__}. Configure SearXNG for a dedicated research provider.",
                "results": [],
            }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            trust_env=False,
            headers={"User-Agent": "LedgerFlow/0.4 local business assistant"},
        ) as client:
            response = await client.get(
                f"{settings.searxng_url.rstrip('/')}/search",
                params={"q": query, "format": "json", "language": "en"},
            )
            response.raise_for_status()
            payload = response.json()
        results: list[dict[str, Any]] = []
        for item in payload.get("results", [])[:limit]:
            url = str(item.get("url") or "")
            if not url:
                continue
            results.append({
                "title": str(item.get("title") or url),
                "url": url,
                "content": str(item.get("content") or "")[:600],
                "engine": ", ".join(item.get("engines") or []) if isinstance(item.get("engines"), list) else str(item.get("engine") or ""),
                "publishedDate": str(item.get("publishedDate") or ""),
            })
        save_research_cache(query, "searxng", results)
        return {
            "live": True,
            "provider": "searxng",
            "message": f"Retrieved {len(results)} current results at {datetime.now(timezone.utc).isoformat()}.",
            "results": results,
        }
    except Exception as exc:
        return {
            "live": False,
            "provider": "searxng",
            "message": f"SearXNG is configured but the research request failed: {type(exc).__name__}.",
            "results": [],
        }


async def company_market_signals() -> dict[str, Any]:
    profile = get_company_profile()
    uploaded = rows_as_dicts("""
        SELECT id, topic, signal_type, entity, geography, direction,
               relevance_score, estimated_impact, source_name, source_url
        FROM market_signals
        ORDER BY relevance_score DESC NULLS LAST
        LIMIT 12
    """)
    uploaded_signals = [
        {
            "id": str(item.get("id")),
            "name": str(item.get("topic") or item.get("signal_type") or "Uploaded market signal"),
            "status": "critical" if float(item.get("relevance_score") or 0) >= 0.85 else "watch",
            "impact": str(item.get("estimated_impact") or f"Linked to {item.get('entity') or item.get('geography') or 'company context'}."),
            "url": str(item.get("source_url") or ""),
            "source": str(item.get("source_name") or "uploaded market file"),
            "relevance_score": item.get("relevance_score"),
            "entity": item.get("entity"),
            "geography": item.get("geography"),
            "direction": item.get("direction"),
        }
        for item in uploaded
    ]
    query = (
        f"{profile.get('industry')} {profile.get('primary_location')} "
        f"business risks suppliers {profile.get('supplier_regions')} "
        f"currencies {profile.get('important_currencies')} latest"
    )
    live = await search_web(query, limit=5)
    if live["live"]:
        web_signals = [
            {
                "id": f"signal-live-{index}",
                "name": result["title"],
                "status": "watch",
                "impact": result["content"] or "Open the source to assess the likely company impact.",
                "url": result["url"],
                "source": result.get("engine", "web"),
            }
            for index, result in enumerate(live["results"], start=1)
        ]
        return {
            "live": True,
            "contextual": bool(uploaded_signals),
            "message": f"{live['message']} {len(uploaded_signals)} uploaded market-context signal(s) are also linked to this company.",
            "signals": (uploaded_signals + web_signals)[:12],
        }

    if uploaded_signals:
        return {
            "live": False,
            "contextual": True,
            "message": f"Live web search is disabled, but {len(uploaded_signals)} uploaded market-context signal(s) are active and mapped to company context.",
            "signals": uploaded_signals,
        }

    return {
        "live": False,
        "contextual": False,
        "message": live["message"],
        "signals": [
            {"id": "signal-aud", "name": "Currency exposure", "status": "watch", "impact": f"Monitor {profile.get('important_currencies')} because currency moves can affect imported costs."},
            {"id": "signal-freight", "name": "Supplier and freight exposure", "status": "watch", "impact": f"Supplier regions include {profile.get('supplier_regions')}; logistics disruptions may affect delivery timing and margins."},
            {"id": "signal-rates", "name": "Working-capital costs", "status": "moderate", "impact": "Interest-rate changes can affect short-term borrowing and cash-flow pressure."},
        ],
    }
