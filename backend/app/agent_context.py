from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .upload_intelligence import company_context_path, read_company_context, market_intelligence_path
from .decision_context import temporal_context_path, read_temporal_context_file
from .context_board import board_prompt_context
from .analysis_context import read_analysis_context_files, business_analyst_context_path, market_analysis_template_path, market_analysis_context_path
from .business_store import CLIPPY_PROFILE, clippy_launch_context


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def working_context_path() -> Path:
    path = settings.data_path / "context" / "default" / "agent_working_context.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def assistant_profile_path() -> Path:
    path = settings.data_path / "context" / "default" / "assistant_profile.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _persona_catalogue() -> dict[str, Any]:
    path = _root() / "agent" / "ASSISTANT_PERSONAS.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {
        "default": "business_analyst",
        "personas": {
            "business_analyst": {
                "label": "Business analyst",
                "description": "Evidence-led, structured and practical.",
                "instruction": "Act as a senior business analyst and finish with prioritised actions.",
            }
        },
        "response_styles": {"balanced": "Give enough evidence to support the recommendation."},
    }


def _default_assistant_profile() -> dict[str, Any]:
    return {
        "version": 1,
        "name": "Clippy",
        "persona": "business_analyst",
        "response_style": "balanced",
        "voice_auto_speak": True,
        "voice_language": "en-AU",
        "updated_at": _now(),
    }


def read_assistant_profile() -> dict[str, Any]:
    path = assistant_profile_path()
    payload = _default_assistant_profile()
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                payload.update(saved)
        except Exception:
            pass
    catalogue = _persona_catalogue()
    if payload.get("persona") not in (catalogue.get("personas") or {}):
        payload["persona"] = str(catalogue.get("default") or "business_analyst")
    if payload.get("response_style") not in (catalogue.get("response_styles") or {}):
        payload["response_style"] = "balanced"
    # Clippy is the single canonical analyst in v3, including for upgraded workspaces
    # whose saved profile still contains the legacy assistant name.
    payload["name"] = "Clippy"
    payload["catalogue"] = catalogue
    if not path.exists():
        path.write_text(json.dumps({k: v for k, v in payload.items() if k != "catalogue"}, indent=2), encoding="utf-8")
    return payload


def save_assistant_profile(updates: dict[str, Any]) -> dict[str, Any]:
    current = read_assistant_profile()
    catalogue = current.get("catalogue") or _persona_catalogue()
    persona = str(updates.get("persona", current.get("persona") or "business_analyst"))
    response_style = str(updates.get("response_style", current.get("response_style") or "balanced"))
    if persona not in (catalogue.get("personas") or {}):
        raise ValueError(f"Unknown assistant persona: {persona}")
    if response_style not in (catalogue.get("response_styles") or {}):
        raise ValueError(f"Unknown response style: {response_style}")
    payload = {
        "version": 1,
        "name": "Clippy",
        "persona": persona,
        "response_style": response_style,
        "voice_auto_speak": bool(updates.get("voice_auto_speak", current.get("voice_auto_speak", True))),
        "voice_language": str(updates.get("voice_language", current.get("voice_language") or "en-AU"))[:20],
        "updated_at": _now(),
    }
    assistant_profile_path().write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return read_assistant_profile()


def assistant_personality_prompt() -> str:
    profile = read_assistant_profile()
    catalogue = profile.get("catalogue") or {}
    persona = (catalogue.get("personas") or {}).get(profile.get("persona")) or {}
    style = (catalogue.get("response_styles") or {}).get(profile.get("response_style")) or ""
    return (
        f"Your name is {profile.get('name') or 'Clippy'}. "
        + str(persona.get("instruction") or "")
        + " "
        + str(style)
    ).strip()


def read_business_analyst_method() -> str:
    path = _root() / "agent" / "BUSINESS_ANALYST_METHOD.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "Frame the decision, verify evidence, compare options and recommend next actions."


def read_base_personality() -> str:
    path = settings.base_personality_path
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Clippy is a careful senior business analyst. Use verified data, trace material statements to business.db, and require approval for writes.\n", encoding="utf-8")
    return "\n\n".join([
        path.read_text(encoding="utf-8").strip(),
        assistant_personality_prompt(),
        read_business_analyst_method(),
    ]).strip()


def _empty_context() -> dict[str, Any]:
    return {
        "version": 1,
        "created_at": _now(),
        "updated_at": _now(),
        "summary": "",
        "events": [],
    }


def read_working_context() -> dict[str, Any]:
    path = working_context_path()
    if not path.exists():
        payload = _empty_context()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Working context must be a JSON object")
        payload.setdefault("summary", "")
        payload.setdefault("events", [])
        return payload
    except Exception:
        backup = path.with_suffix(".corrupt.json")
        try:
            path.replace(backup)
        except OSError:
            pass
        payload = _empty_context()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


def context_for_prompt() -> dict[str, Any]:
    current = read_working_context()
    company = read_company_context()
    temporal = read_temporal_context_file()
    board = board_prompt_context()
    analysis_context = read_analysis_context_files()
    enabled_context = {str(item.get("context_key")) for item in board.get("enabled_context_layers", [])}
    allowed_keys = {str(item.get("source_key")) for item in board.get("enabled_sources", [])}
    temporal_sources = list(temporal.get("sources") or [])
    if allowed_keys:
        temporal_sources = [item for item in temporal_sources if str(item.get("source_key")) in allowed_keys]
    working_enabled = not board or "context:working_memory" in enabled_context
    company_enabled = not board or "context:company_context" in enabled_context
    time_enabled = not board or "context:time_context" in enabled_context
    market_enabled = not board or "context:market_intelligence" in enabled_context
    return {
        "business_db_launch_context": clippy_launch_context(),
        "clippy_profile": CLIPPY_PROFILE,
        "summary": str(current.get("summary") or "")[-6000:] if working_enabled else "",
        "recent_events": list(current.get("events") or [])[-8:] if working_enabled else [],
        "context_board": board,
        "temporal_decision_context": {
            "timezone": temporal.get("timezone"),
            "current_time_local": temporal.get("current_time_local"),
            "data_cutoff_local": temporal.get("data_cutoff_local"),
            "last_analysis": temporal.get("last_analysis", {}),
            "summary": temporal.get("summary", {}),
            "decisions": list(temporal.get("decisions") or [])[:8],
            "recent_sources": temporal_sources[:20],
        } if time_enabled else {},
        "company_ai_context": {
            "onboarding": company.get("onboarding", {}),
            "document_coverage": company.get("document_coverage", {}),
            "operating_snapshot": company.get("operating_snapshot", {}),
            "latest_uploads": list(company.get("upload_history") or [])[-8:],
            "market_intelligence": company.get("market_intelligence", {}) if market_enabled else {},
        } if company_enabled else {},
        "business_analyst_context": analysis_context.get("business_analyst_context", {}),
        "market_analysis_template": analysis_context.get("market_analysis_template", {}) if market_enabled else {},
        "market_analysis_context": analysis_context.get("market_analysis_context", {}) if market_enabled else {},
    }


def update_working_context(
    *,
    user_message: str,
    intent: str,
    workspace: str,
    outcome: str,
    model: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = read_working_context()
    event = {
        "ended_at": _now(),
        "workspace": workspace,
        "intent": intent,
        "user_request": user_message[:800],
        "outcome": outcome[:1200],
        "model": model,
        "evidence_keys": sorted((evidence or {}).keys()),
    }
    events = list(current.get("events") or [])
    events.append(event)
    events = events[-max(4, settings.agent_context_max_events):]

    summary_lines = [
        f"- {item.get('ended_at', '')}: [{item.get('intent', 'general')}] {item.get('user_request', '')} -> {item.get('outcome', '')}"
        for item in events[-12:]
    ]
    summary = "Recent LedgerFlow continuity:\n" + "\n".join(summary_lines)
    summary = summary[-max(2000, settings.agent_context_max_chars):]
    payload = {
        "version": 1,
        "created_at": current.get("created_at") or _now(),
        "updated_at": _now(),
        "summary": summary,
        "events": events,
    }
    working_context_path().write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def clear_working_context() -> dict[str, Any]:
    payload = _empty_context()
    working_context_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def agent_context_status() -> dict[str, Any]:
    current = read_working_context()
    return {
        "base_personality_file": str(settings.base_personality_path),
        "base_personality_present": settings.base_personality_path.exists(),
        "working_context_file": str(working_context_path()),
        "working_context_events": len(current.get("events") or []),
        "working_context_updated_at": current.get("updated_at"),
        "company_context_file": str(company_context_path()),
        "company_context_present": company_context_path().exists(),
        "market_intelligence_file": str(market_intelligence_path()),
        "temporal_decision_context_file": str(temporal_context_path()),
        "temporal_decision_database_file": str(settings.data_path / "database" / "decision_context.sqlite"),
        "temporal_context_present": temporal_context_path().exists(),
        "context_board_database_file": str(settings.data_path / "database" / "decision_context.sqlite"),
        "context_board_enabled": True,
        "market_intelligence_status": read_company_context().get("market_intelligence", {}).get("status", "not_started"),
        "business_analyst_context_file": str(business_analyst_context_path()),
        "market_analysis_template_file": str(market_analysis_template_path()),
        "market_analysis_context_file": str(market_analysis_context_path()),
        "assistant_profile_file": str(assistant_profile_path()),
        "assistant_profile": {k: v for k, v in read_assistant_profile().items() if k != "catalogue"},
        "base_is_preserved_on_clear": True,
    }
