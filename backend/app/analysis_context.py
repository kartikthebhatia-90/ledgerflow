from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .database import COMPANY_ID, get_company_profile
from .upload_intelligence import market_intelligence_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _context_dir() -> Path:
    path = settings.data_path / "context" / COMPANY_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def business_analyst_context_path() -> Path:
    return _context_dir() / "business_analyst_context.json"


def market_analysis_template_path() -> Path:
    return _context_dir() / "market_analysis_template.json"


def market_analysis_context_path() -> Path:
    return _context_dir() / "market_analysis_context.json"


def _read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(fallback or {})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else dict(fallback or {})
    except Exception:
        return dict(fallback or {})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


SECTION_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "overview": {
        "label": "Overview",
        "objective": "Explain the current business position, the most important movements and the decisions that need attention now.",
        "analysis_questions": [
            "What changed in cash, liquidity, revenue, profit and working capital?",
            "Which changes are material, unusual or inconsistent with the available evidence?",
            "What should management do next, by when and with what expected effect?",
        ],
        "decision_rules": [
            "Separate verified facts from estimates and assumptions.",
            "Prioritise cash, solvency, margin and operational continuity.",
            "Do not treat a single incomplete period as a trend.",
        ],
        "output_structure": ["Current position", "Key drivers", "Risks", "Recommended actions", "Evidence gaps"],
    },
    "accounts": {
        "label": "Accounts",
        "objective": "Assess financial controls, reconciliations, coding, journals, receivables, payables and account integrity.",
        "analysis_questions": [
            "Do balances reconcile to source documents and bank evidence?",
            "Which invoices, journals or account mappings require review?",
            "Where could timing, classification or duplicate records distort the financial position?",
        ],
        "decision_rules": [
            "Never post or approve a journal without explicit user approval.",
            "Trace every material number back to a source file and processing product.",
            "Flag unexplained reconciliation differences and duplicate business keys.",
        ],
        "output_structure": ["Reconciliation status", "Control exceptions", "Coding issues", "Proposed corrections", "Approval required"],
    },
    "tax": {
        "label": "Tax",
        "objective": "Assess GST, BAS, PAYG, superannuation and tax evidence while preserving a clear audit trail.",
        "analysis_questions": [
            "Are GST and tax codes supported by the underlying documents?",
            "Do payroll, PAYG and superannuation records agree with the reporting period?",
            "Which tax positions are provisional because evidence is missing or ambiguous?",
        ],
        "decision_rules": [
            "Treat tax estimates as provisional unless the required evidence reconciles.",
            "Identify the exact source documents supporting each tax label.",
            "Recommend professional review when legal interpretation is required.",
        ],
        "output_structure": ["Tax position", "Evidence used", "Exceptions", "Estimated exposure", "Required review"],
    },
    "marketing": {
        "label": "Marketing",
        "objective": "Connect marketing spend to revenue, margin, customer quality and sustainable growth decisions.",
        "analysis_questions": [
            "Which channels consume budget and what verified outcomes are connected to them?",
            "Is customer acquisition efficient after considering gross margin and payment behaviour?",
            "Which campaigns should be scaled, optimised, paused or measured better?",
        ],
        "decision_rules": [
            "Do not present modelled attribution as verified performance.",
            "Compare channel decisions with gross margin and cash collection, not revenue alone.",
            "State when campaign or CRM integration is missing.",
        ],
        "output_structure": ["Spend position", "Channel evidence", "Commercial impact", "Budget recommendation", "Measurement gaps"],
    },
    "intelligence": {
        "label": "Intelligence",
        "objective": "Combine internal business context with verified market and competitor evidence to support strategic decisions.",
        "analysis_questions": [
            "How does the company compare with verified competitors on comparable dimensions?",
            "Which market, macroeconomic, customer, supplier and geopolitical variables can materially affect the business?",
            "What strategic actions are justified by both internal evidence and external evidence?",
        ],
        "decision_rules": [
            "Use business_analyst_context.json as the internal baseline.",
            "Apply market_analysis_template.json to structure the investigation.",
            "Combine only verified uploaded market evidence, saved market reports and cited live research.",
            "Never create competitor values, market shares or claims that are not supported by evidence.",
        ],
        "output_structure": ["Internal baseline", "Competitor comparison", "Market variables", "Scenarios", "Strategic actions", "Evidence and citations"],
    },
}


DEFAULT_MARKET_TEMPLATE: dict[str, Any] = {
    "version": 1,
    "template_name": "LedgerFlow market and competitor analysis",
    "purpose": "Structure market analysis around the company's verified internal position and external evidence without inventing competitor facts.",
    "instructions_to_ai": [
        "Read business_analyst_context.json first to understand the company, current financial position, constraints and decision questions.",
        "Read market_analysis_context.json to identify the approved market files, saved market report and current analysis cutoff.",
        "Use market_intelligence.json and uploaded market_context evidence as verified internal market evidence.",
        "Use live research only when the application supplies a source URL and citation metadata.",
        "Separate facts, estimates, scenarios and recommendations.",
        "Do not rank competitors when comparable verified variables are insufficient.",
    ],
    "analysis_dimensions": {
        "competitors": [
            "revenue growth", "gross margin", "net margin", "liquidity", "cash resilience", "pricing", "customer proposition", "channel mix", "geographic coverage", "service level"
        ],
        "customers_and_demand": [
            "segment demand", "customer concentration", "retention", "payment behaviour", "tender activity", "office occupancy", "substitution risk"
        ],
        "suppliers_and_operations": [
            "supplier concentration", "lead time", "freight cost", "inventory availability", "commodity inputs", "currency exposure", "service continuity"
        ],
        "macroeconomic": [
            "inflation", "interest rates", "AUD movements", "employment", "business confidence", "consumer and SME demand"
        ],
        "regulatory_and_geopolitical": [
            "tax and employment regulation", "trade restrictions", "shipping disruption", "regional conflict", "sanctions", "data and privacy obligations"
        ],
        "technology_and_channels": [
            "search cost", "platform dependence", "automation", "CRM quality", "e-commerce conversion", "cyber and vendor risk"
        ],
    },
    "required_output": [
        "Executive market summary",
        "Company baseline",
        "Verified competitor comparison",
        "Material external variables",
        "Base, upside and downside scenarios",
        "Recommended actions with timing and owners",
        "Evidence gaps and required next data",
        "Source citations",
    ],
    "user_instructions": [],
}


def ensure_market_analysis_template() -> dict[str, Any]:
    path = market_analysis_template_path()
    existing = _read_json(path)
    if not existing:
        _write_json(path, DEFAULT_MARKET_TEMPLATE)
        return dict(DEFAULT_MARKET_TEMPLATE)
    # Add new defaults without overwriting user edits.
    merged = dict(DEFAULT_MARKET_TEMPLATE)
    merged.update(existing)
    for key in ("analysis_dimensions",):
        nested = dict(DEFAULT_MARKET_TEMPLATE.get(key) or {})
        nested.update(existing.get(key) or {})
        merged[key] = nested
    _write_json(path, merged)
    return merged


def refresh_business_analyst_context(
    *,
    source_nodes: list[dict[str, Any]],
    process_nodes: list[dict[str, Any]],
    temporal: dict[str, Any],
    app_sections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    path = business_analyst_context_path()
    existing = _read_json(path)
    company = get_company_profile()
    existing_sections = existing.get("sections") if isinstance(existing.get("sections"), dict) else {}
    process_map = {str(item.get("process_id")): item for item in process_nodes}

    sections: dict[str, Any] = {}
    for section_id, definition in app_sections.items():
        blueprint = SECTION_BLUEPRINTS.get(section_id, {})
        sources = [
            item for item in source_nodes
            if item.get("enabled") and section_id in (item.get("app_sections") or [])
        ]
        process_ids = sorted({
            str(process_id)
            for item in sources
            for process_id in (item.get("extraction_targets") or [])
            if process_id in process_map and process_map[process_id].get("enabled")
        })
        prior = existing_sections.get(section_id) if isinstance(existing_sections.get(section_id), dict) else {}
        sections[section_id] = {
            "label": blueprint.get("label") or definition.get("label") or section_id.title(),
            "objective": prior.get("objective") or prior.get("objective_override") or blueprint.get("objective") or definition.get("description") or "",
            "analysis_questions": prior.get("analysis_questions") or prior.get("analysis_questions_override") or blueprint.get("analysis_questions") or [],
            "decision_rules": prior.get("decision_rules") or prior.get("decision_rules_override") or blueprint.get("decision_rules") or [],
            "output_structure": prior.get("output_structure") or prior.get("output_structure_override") or blueprint.get("output_structure") or [],
            "user_instructions": prior.get("user_instructions") or [],
            "connected_sources": [
                {
                    "source_key": item.get("id"),
                    "label": item.get("label"),
                    "document_type": item.get("document_type"),
                    "processing_order": item.get("processing_order"),
                    "processing_status": item.get("processing_status"),
                    "effective_date": item.get("effective_date"),
                    "freshness_state": item.get("freshness_state"),
                    "extraction_targets": item.get("extraction_targets") or [],
                    "transformation_note": item.get("transformation_note") or "",
                    "analyst_notes": item.get("notes") or "",
                }
                for item in sorted(sources, key=lambda row: (int(row.get("processing_order") or 100), str(row.get("label") or "")))
            ],
            "processing_products": [
                {
                    "process_id": process_id,
                    "label": process_map[process_id].get("label"),
                    "description": process_map[process_id].get("description"),
                    "notes": process_map[process_id].get("notes") or "",
                }
                for process_id in process_ids
            ],
            "evidence_status": "connected" if sources else "awaiting_sources",
        }

    payload = {
        "version": 1,
        "generated_at": _now(),
        "context_role": "Primary internal business-analysis context supplied to Ledger AI.",
        "company": {
            "company_name": company.get("company_name"),
            "industry": company.get("industry"),
            "primary_location": company.get("primary_location"),
            "reporting_currency": company.get("reporting_currency"),
            "current_objective": company.get("current_objective"),
            "primary_risks": company.get("primary_risks"),
        },
        "analysis_time": {
            "timezone": temporal.get("timezone"),
            "current_time_local": temporal.get("current_time_local"),
            "data_cutoff_local": temporal.get("data_cutoff_local"),
            "last_analysis": temporal.get("last_analysis") or {},
        },
        "decision_policy": {
            "role": "Act as a careful business analyst and decision-support partner.",
            "instructions": (
                existing.get("decision_policy", {}).get("instructions")
                if isinstance(existing.get("decision_policy"), dict) and existing.get("decision_policy", {}).get("instructions")
                else [
                    "Analyse the connected evidence before recommending a decision.",
                    "Follow the visible source → extraction → app section lineage.",
                    "Use only included sources and respect their processing order and transformation notes.",
                    "State the evidence, the reasoning, the recommendation, the expected effect and the main uncertainty.",
                    "Never silently post accounting entries, alter source evidence or invent missing figures.",
                ]
            ),
            "user_instructions": existing.get("decision_policy", {}).get("user_instructions", []) if isinstance(existing.get("decision_policy"), dict) else [],
        },
        "sections": sections,
        "source_index": [
            {
                "source_key": item.get("id"),
                "label": item.get("label"),
                "document_type": item.get("document_type"),
                "included": bool(item.get("enabled")),
                "processing_order": item.get("processing_order"),
                "app_sections": item.get("app_sections") or [],
                "extraction_targets": item.get("extraction_targets") or [],
            }
            for item in source_nodes
        ],
        "market_analysis": {
            "instruction": "For Intelligence and market questions, combine this file with market_analysis_template.json, market_analysis_context.json and verified market evidence.",
            "template_file": str(market_analysis_template_path()),
            "market_context_file": str(market_analysis_context_path()),
            "market_report_file": str(market_intelligence_path()),
        },
    }
    _write_json(path, payload)
    return payload


def refresh_market_analysis_context(
    *,
    business_context: dict[str, Any],
    source_nodes: list[dict[str, Any]],
    temporal: dict[str, Any],
) -> dict[str, Any]:
    template = ensure_market_analysis_template()
    existing = _read_json(market_analysis_context_path())
    market_report = _read_json(market_intelligence_path())
    market_sources = [
        item for item in source_nodes
        if item.get("enabled") and (
            item.get("document_type") == "market_context"
            or "market_and_competitors" in (item.get("extraction_targets") or [])
            or "intelligence" in (item.get("app_sections") or [])
        )
    ]
    payload = {
        "version": 1,
        "generated_at": _now(),
        "context_role": "Market-analysis orchestration context supplied in addition to the internal business-analysis context.",
        "analysis_time": {
            "timezone": temporal.get("timezone"),
            "current_time_local": temporal.get("current_time_local"),
            "data_cutoff_local": temporal.get("data_cutoff_local"),
            "last_analysis": temporal.get("last_analysis") or {},
        },
        "instructions_to_ai": template.get("instructions_to_ai") or [],
        "analysis_dimensions": template.get("analysis_dimensions") or {},
        "required_output": template.get("required_output") or [],
        "business_context_reference": {
            "path": str(business_analyst_context_path()),
            "company": business_context.get("company") or {},
            "intelligence_section": (business_context.get("sections") or {}).get("intelligence") or {},
        },
        "market_report_reference": {
            "path": str(market_intelligence_path()),
            "status": market_report.get("status") or ("available" if market_report else "not_started"),
            "generated_at": market_report.get("generated_at") or "",
            "summary": market_report.get("summary") or "",
        },
        "connected_market_sources": [
            {
                "source_key": item.get("id"),
                "label": item.get("label"),
                "document_type": item.get("document_type"),
                "effective_date": item.get("effective_date"),
                "freshness_state": item.get("freshness_state"),
                "processing_status": item.get("processing_status"),
                "transformation_note": item.get("transformation_note") or "",
            }
            for item in market_sources
        ],
        "decision_rule": (
            existing.get("decision_rule")
            or "Market recommendations require both the internal business baseline and verified external or uploaded market evidence. Unsupported competitor values must remain blank."
        ),
        "user_instructions": existing.get("user_instructions") or template.get("user_instructions") or [],
        "custom_variables": existing.get("custom_variables") or {},
        "analyst_notes": existing.get("analyst_notes") or "",
    }
    _write_json(market_analysis_context_path(), payload)
    return payload


def refresh_analysis_context_files(
    *,
    source_nodes: list[dict[str, Any]],
    process_nodes: list[dict[str, Any]],
    temporal: dict[str, Any],
    app_sections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    business = refresh_business_analyst_context(
        source_nodes=source_nodes,
        process_nodes=process_nodes,
        temporal=temporal,
        app_sections=app_sections,
    )
    market = refresh_market_analysis_context(
        business_context=business,
        source_nodes=source_nodes,
        temporal=temporal,
    )
    return {"business_analyst_context": business, "market_analysis_context": market}


def read_analysis_context_files() -> dict[str, Any]:
    ensure_market_analysis_template()
    return {
        "business_analyst_context": _read_json(business_analyst_context_path()),
        "market_analysis_template": _read_json(market_analysis_template_path()),
        "market_analysis_context": _read_json(market_analysis_context_path()),
    }


def refresh_market_report_reference() -> dict[str, Any]:
    """Refresh only the saved-report metadata without changing connected source lineage."""
    path = market_analysis_context_path()
    payload = _read_json(path)
    template = ensure_market_analysis_template()
    report = _read_json(market_intelligence_path())
    if not payload:
        payload = {
            "version": 1,
            "context_role": "Market-analysis orchestration context supplied in addition to the internal business-analysis context.",
            "connected_market_sources": [],
        }
    payload["generated_at"] = _now()
    payload["instructions_to_ai"] = template.get("instructions_to_ai") or []
    payload["analysis_dimensions"] = template.get("analysis_dimensions") or {}
    payload["required_output"] = template.get("required_output") or []
    payload["market_report_reference"] = {
        "path": str(market_intelligence_path()),
        "status": report.get("status") or ("available" if report else "not_started"),
        "generated_at": report.get("generated_at") or "",
        "summary": report.get("summary") or "",
    }
    _write_json(path, payload)
    return payload
