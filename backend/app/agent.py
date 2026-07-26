from __future__ import annotations

import json
from typing import Any

import httpx

from .analytics import agent_data_context, dashboard_summary, financial_snapshot
from .accounting import accounting_dashboard
from .agent_context import context_for_prompt, read_base_personality, update_working_context
from .prompt_compression import compress_context
from .config import settings
from .database import (
    create_approval,
    get_company_profile,
    save_agent_event,
    save_conversation_message,
)
from .memory import maybe_compact_memory, memory_context
from .research import search_web
from .upload_intelligence import file_context_for_prompt, upload_library
from .guided_tours import load_walkthrough, render_template
from .tax import tax_dashboard
from .marketing import marketing_dashboard
from .competitor_intelligence import analysis_status
from .agent_execution import execute_deterministic_command
from .data_quality import data_quality_dashboard
from .decision_context import decision_context_dashboard
from .context_board import context_board_dashboard, explain_context_board
from .schemas import AgentCommand, AgentResponse, DashboardAction
from .business_store import clippy_launch_context


def action(action_type: str, **kwargs: Any) -> DashboardAction:
    return DashboardAction(type=action_type, **kwargs)


async def ollama_available() -> tuple[bool, list[str]]:
    if not settings.ollama_enabled:
        return False, []
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            trust_env=False,
        ) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
        models = [str(item.get("name") or "") for item in response.json().get("models", [])]
        return True, models
    except Exception as exc:
        print(f"Ollama availability check failed: {type(exc).__name__}: {exc}")
        return False, []


def _installed_model(configured: str, models: list[str]) -> str | None:
    configured = configured.strip()
    for model in models:
        if model == configured or model.startswith(configured + ":") or configured.startswith(model + ":"):
            return model
    return None


def detect_intent(text: str) -> str:
    text = text.lower().strip()
    file_nouns = ["file", "files", "document", "documents", "upload", "uploaded", "workbook", "spreadsheet", "pdf", "payroll report", "bank statement"]
    file_actions = ["read", "explain", "analyse", "analyze", "show", "summarise", "summarize", "impact", "changed", "incorporated", "what is in"]
    if any(noun in text for noun in file_nouns) and any(verb in text for verb in file_actions):
        return "data_files"
    groups = {
        "money_map": ["money map", "money flow", "where money goes", "sources of money", "department costs"],
        "tax": ["tax", "gst", "bas", "ato", "income tax", "compliance"],
        "inventory": ["inventory", "stock on hand", "reorder", "sku", "warehouse"],
        "hr": ["human resources", "employee", "employees", "headcount", "payroll", "leave balance", "training status"],
        "marketing": ["marketing", "campaign", "advertising", "roas", "channel spend", "customer acquisition"],
        "accounts": ["accounts", "trial balance", "journal", "general ledger", "chart of accounts", "profit and loss"],
        "documents": ["generate file", "create document", "business document", "purchase order", "quotation", "workpaper"],
        "current_ratio": ["current ratio", "liquidity", "working capital", "quick ratio", "assets and liabilities", "assets & liabilities"],
        "anomaly": ["anomaly", "anomalies", "suspicious", "strange payment", "duplicate payment", "unusual payment"],
        "cash_flow": ["cash flow", "cashflow", "cash position", "runway", "forecast"],
        "invoice": ["invoice", "invoices", "payable", "supplier bill"],
        "import": ["upload", "import", "csv", "excel", "spreadsheet", "map columns"],
        "decisions": ["context board", "context map", "data lineage", "source lineage", "processing route", "app section inputs", "decision context", "decision timeline", "decision inputs", "analysis time", "time context", "data cutoff", "last analysis"],
        "setup": ["nvidia", "api key", "ollama", "setup", "install model", "integration", "search setup", "searxng"],
        "validation": ["validation", "error", "mistake", "check data", "reconcile", "review issue"],
        "quality": ["data quality", "data trust", "source coverage", "metric lineage", "reconciliation status"],
        "intelligence": ["competitor analysis", "company comparison", "market intelligence", "compare my company", "deep company analysis", "competitor dashboard"],
        "data_files": ["my files", "uploaded file", "read the file", "read my file", "what is in the file", "permanent files", "recurring files", "file library", "latest upload"],
        "market": ["market", "competitor", "geopolitical", "news", "external risk", "current events", "industry"],
        "company": ["company profile", "company context", "business profile", "my company"],
        "overview": ["overview", "business pulse", "home dashboard", "take me home"],
    }
    for intent, terms in groups.items():
        if any(term in text for term in terms):
            return intent
    return "general"




def _money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _tour_values(context: dict[str, Any]) -> dict[str, Any]:
    snapshot = context.get("snapshot") or {}
    coverage = context.get("setup_coverage") or {}
    tax = context.get("tax_dashboard") or {}
    marketing = context.get("marketing_dashboard") or {}
    intelligence = context.get("intelligence_status") or {}
    profit = context.get("profit_structure") or {}
    missing = list(coverage.get("required_missing") or [])
    labels = {
        "balance_sheet": "Balance Sheet",
        "profit_loss": "Income Statement (Profit & Loss)",
        "cash_flow_statement": "Cash Flow Statement",
        "chart_of_accounts": "Chart of Accounts",
        "business_requirements": "Business Requirement Document",
    }
    tax_summary = tax.get("summary") or {}
    marketing_summary = marketing.get("summary") or {}
    result = intelligence.get("result") if isinstance(intelligence, dict) else {}
    intelligence_state = "not started"
    if isinstance(result, dict) and result.get("summary"):
        intelligence_state = "complete and available for review"
    elif isinstance(intelligence, dict) and (intelligence.get("job") or {}).get("status") in {"queued", "processing"}:
        intelligence_state = "currently processing"
    return {
        "cash": _money(snapshot.get("cash")),
        "current_ratio": "—" if snapshot.get("current_ratio") is None else f"{float(snapshot.get('current_ratio') or 0):.2f}",
        "quick_ratio": "—" if snapshot.get("quick_ratio") is None else f"{float(snapshot.get('quick_ratio') or 0):.2f}",
        "debt_to_assets_percent": "—" if snapshot.get("debt_to_assets") is None else f"{float(snapshot.get('debt_to_assets') or 0) * 100:.1f}%",
        "revenue_month": _money(snapshot.get("revenue_month")),
        "expenses_month": _money(snapshot.get("expenses_month")),
        "open_checks": int((context.get("data_quality") or {}).get("open_check_total") or len(context.get("open_validations") or [])),
        "cash_runway_days": int(snapshot.get("cash_runway_days") or 0),
        "forecast_low_point": _money((context.get("forecast") or {}).get("low_point")),
        "current_assets": _money(snapshot.get("current_assets")),
        "current_liabilities": _money(snapshot.get("current_liabilities")),
        "working_capital": _money(snapshot.get("working_capital")),
        "statement_revenue": _money(profit.get("revenue")),
        "statement_costs": _money(profit.get("costs")),
        "statement_profit": _money(profit.get("profit")),
        "taxable_income": _money(tax_summary.get("estimated_taxable_income")),
        "income_tax_estimate": _money(tax_summary.get("estimated_income_tax")),
        "tax_review_count": int(tax_summary.get("review_count") or 0),
        "marketing_mode": str(marketing.get("mode") or "demonstration"),
        "marketing_spend": _money(marketing_summary.get("marketing_spend")),
        "marketing_revenue": _money(marketing_summary.get("revenue")),
        "marketing_roas": f"{float(marketing_summary.get('roas') or 0):.2f}x",
        "intelligence_status": intelligence_state,
        "setup_file_count": int((context.get("upload_counts") or {}).get("setup") or 0),
        "recurring_file_count": int((context.get("upload_counts") or {}).get("recurring") or 0),
        "missing_documents": ", ".join(labels.get(item, item.replace("_", " ").title()) for item in missing) or "none",
    }


def _overview_tour_actions(context: dict[str, Any]) -> tuple[list[DashboardAction], list[str], str]:
    script = load_walkthrough("overview")
    values = _tour_values(context)
    missing = list((context.get("setup_coverage") or {}).get("required_missing") or [])
    if missing and bool(script.get("requires_core_setup", True)):
        message = render_template(str(script.get("incomplete_intro") or "Complete the core setup first: {missing_documents}."), values)
        actions = [
            action("character_state", state="explaining", duration_ms=160),
            action("character_say", message=message, duration_ms=950),
            action("navigate", destination="decisions", duration_ms=420),
            action("character_move", target="permanent-file-library", duration_ms=360),
            action("spotlight", target="permanent-file-library", duration_ms=320),
            action("offer_choices", choices=["Open import", "Show latest upload"], duration_ms=160),
        ]
        return actions, ["Check the five core setup documents", "Show the missing-document checklist", "Hold the business tour until the setup is complete"], "guided"

    actions: list[DashboardAction] = [
        action("character_state", state="explaining", duration_ms=180),
        action("character_say", message=render_template(str(script.get("complete_intro") or "The core setup is complete. I’ll guide you through LedgerFlow."), values), duration_ms=1100),
    ]
    for step in list(script.get("steps") or []):
        destination = str(step.get("destination") or "overview")
        target = str(step.get("target") or "")
        message = render_template(str(step.get("message") or ""), values)
        actions.append(action("navigate", destination=destination, duration_ms=430))
        if target:
            actions.append(action("character_move", target=target, duration_ms=300))
            actions.append(action("spotlight", target=target, duration_ms=220))
        if message:
            actions.append(action("character_say", message=message, duration_ms=1250))
        actions.append(action("clear_spotlight", duration_ms=80))
    actions.append(action("offer_choices", choices=["Explain current ratio", "Show tax dashboard", "Start deep company analysis"], duration_ms=160))
    return actions, ["Confirm core setup", "Explain overview analytics", "Walk through accounts, tax, marketing, intelligence, files and settings", "Return to the analytics overview"], "guided"


def _top_contributors(context: dict[str, Any], category: str, classification: str = "current") -> list[dict[str, Any]]:
    records = [
        record for record in context["assets_liabilities"]
        if record.get("category") == category and record.get("classification") == classification
    ]
    return sorted(records, key=lambda item: float(item.get("amount") or 0), reverse=True)[:4]


def factual_fallback(intent: str, context: dict[str, Any], research: dict[str, Any] | None = None) -> str:
    snapshot = context["snapshot"]
    ratio = snapshot.get("current_ratio")
    ratio_text = "unavailable" if ratio is None else f"{ratio:.2f}"
    if intent == "money_map":
        return "Open Money map to trace customer receipts into operating departments, estimated tax and retained profit. It reconciles the latest bank receipts with the latest Profit and Loss period."
    if intent == "inventory":
        return "Open Inventory to review stock on hand, reorder alerts, inventory value and invoice-linked movements. Structured invoice lines after the latest stock snapshot can update quantities automatically."
    if intent == "hr":
        return "Open HR to review every employee in the latest payroll period, department cost, PAYG withholding, superannuation, leave, training and the HR action queue."
    if intent == "tax":
        return "Open Tax & compliance to review the indicative income-tax estimate, BAS labels, GST reconciliation, obligations and review-required ATO workpapers."
    if intent == "marketing":
        return "Open Marketing performance to compare channel spend with revenue. Demonstration allocations are clearly labelled until posted marketing and campaign-attribution data are available."
    if intent == "accounts":
        return f"Open Accounts to review the chart of accounts, trial balance, posted and draft journals, and validation queue. Current working capital is ${snapshot['working_capital']:,.0f}."
    if intent == "documents":
        return "Open the Accounts document rail to create a reviewable PDF or CSV, then use the document library to download prior outputs."
    if intent == "current_ratio":
        liabilities = _top_contributors(context, "liability")
        names = ", ".join(str(item["name"]) for item in liabilities[:3]) or "current liabilities"
        return (
            f"Your current ratio is {ratio_text}: current assets are ${snapshot['current_assets']:,.0f} and current liabilities are "
            f"${snapshot['current_liabilities']:,.0f}. The largest near-term pressure comes from {names}. Working capital is "
            f"${snapshot['working_capital']:,.0f}. Review cash, receivables and the largest liabilities before committing more cash."
        )
    if intent == "anomaly":
        issues = [item for item in context["open_validations"] if "duplicate" in str(item.get("check_name", ""))]
        if issues:
            return f"I found {len(issues)} duplicate-related warning(s). The highest-priority issue is: {issues[0]['description']} {issues[0]['recommendation']}"
        return "No open duplicate-payment validation is currently stored. Run validation again after importing the latest transactions."
    if intent == "cash_flow":
        forecast = context["forecast"]
        return (
            f"Available cash is ${snapshot['cash']:,.0f}, with an estimated runway of {snapshot['cash_runway_days']} days. "
            f"The 90-day forecast reaches a low point of ${forecast['low_point']:,.0f}. This estimate uses recent net movement and known unpaid invoice due dates, so resolve duplicate-payment warnings before relying on it."
        )
    if intent == "invoice":
        open_total = snapshot.get("open_invoice_total", 0)
        overdue = snapshot.get("overdue_invoice_total", 0)
        return f"Open invoices total ${open_total:,.0f}, including ${overdue:,.0f} overdue. I can take you to the invoice records and highlight any items linked to validation warnings."
    if intent == "decisions":
        board = context.get("context_board") or {}
        if board:
            explanation = explain_context_board(lens=str((board.get("settings") or {}).get("active_lens") or "all"))
            return str(explanation.get("summary") or "Open Data management to inspect and edit the sources that influence Ledger AI.")
        decision = context.get("decision_context") or {}
        summary = decision.get("summary") or {}
        last = decision.get("last_analysis") or {}
        last_text = str(last.get("completed_at_utc") or last.get("started_at_utc") or "no completed analysis yet")
        return (
            f"The timestamped decision context contains {int(summary.get('source_count') or 0)} connected input(s). "
            f"{int(summary.get('ready_decisions') or 0)} decision domain(s) are ready, "
            f"{int(summary.get('provisional_decisions') or 0)} are provisional and "
            f"{int(summary.get('blocked_decisions') or 0)} are blocked. Last analysis: {last_text}."
        )
    if intent == "quality":
        quality = context.get("data_quality") or {}
        return f"The data trust score is {int(quality.get('score') or 0)}/100 with {int(quality.get('open_check_total') or 0)} open checks across validation, accounting and tax. Open Data management to review the connected sources and then use the file controls below the context map."
    if intent == "validation":
        issues = context["open_validations"]
        if not issues:
            return "No open validation issues are currently stored. The dashboard will rerun checks after imports and at the configured interval."
        return f"There are {len(issues)} open validation issues. The highest priority is {issues[0]['description']} Recommended next step: {issues[0]['recommendation']}"
    if intent == "market":
        if research and research.get("live"):
            return f"I found {len(research.get('results', []))} current web results related to your company context. Open Market Intelligence to review the cited sources and assess which events could affect suppliers, costs, or demand."
        return "Live market research is not connected. The dashboard can still show company exposure, but current web sources require SearXNG or another search provider."
    if intent == "company":
        profile = context["snapshot"]["company"]
        return f"Your saved company context is {profile.get('company_name')}, a {profile.get('industry')} business based in {profile.get('primary_location')}. Update it to improve ratio targets, research queries, and dashboard priorities."
    if intent == "data_files":
        files = list((context.get("file_context") or {}).get("matched_files") or [])
        if not files:
            return "No uploaded business files are currently registered. Open Data management to add permanent setup documents or recurring evidence and control how they influence Ledger AI."
        latest = files[0]
        analysis = latest.get("analysis") or {}
        findings = list(analysis.get("findings") or [])
        impact = list(analysis.get("business_impact") or [])
        detail = " ".join((findings + impact)[:3])
        return f"I can access {len(files)} relevant uploaded file record(s). The closest match is {latest.get('filename')}, identified as {str(latest.get('document_type') or 'business document').replace('_', ' ')}. {detail}".strip()
    if intent == "intelligence":
        market = ((context.get("file_context") or {}).get("company_ai_context") or {}).get("market_intelligence") or {}
        status = str(market.get("status") or "not_started")
        if status == "completed":
            return f"Deep competitor intelligence is complete. {market.get('summary') or ''} Open Company intelligence to inspect the verified positioning chart and the two agent-selected chart slots."
        return "Deep competitor intelligence has not been completed. Open Company intelligence and start it explicitly; LedgerFlow will use local company metrics, uploaded market evidence and any configured research source without fabricating competitor values."
    if intent == "import":
        return "Open Data management to upload permanent setup documents or recurring evidence. The same page shows each file, the data extracted from it, the app sections that consume it and the path into Ledger AI. Inclusion, document type, processing route and section connections are editable."
    if intent == "setup":
        return "Open Settings to test the configured model provider. NVIDIA NIM is the default cloud provider; Ollama remains an optional local fallback. The application never installs system software silently."
    if intent == "overview":
        missing = list((context.get("setup_coverage") or {}).get("required_missing") or [])
        if missing:
            return f"The full guided overview is held until the five core setup documents are represented. Missing: {_tour_values(context)['missing_documents']}."
        return f"The core setup is complete. The guided overview covers cash of ${snapshot['cash']:,.0f}, a current ratio of {ratio_text}, the cash forecast, financial position, profit structure, accounts, tax, marketing, company intelligence and file coverage."
    return (
        f"I can answer from the loaded business data. Current cash is ${snapshot['cash']:,.0f}, the current ratio is {ratio_text}, "
        f"and there are {len(context['open_validations'])} open validation issues. Ask a specific question and I will use the relevant records rather than a generic response."
    )


def should_use_model(user_message: str, intent: str) -> tuple[bool, str]:
    """Route fast, repeatable work to code and reserve AI for judgement-heavy work."""
    mode = settings.agent_ai_routing_mode.strip().lower()
    if mode == "deterministic":
        return False, "AI routing is set to deterministic"
    if mode == "always":
        return True, "AI routing is set to always"

    lower = user_message.lower()
    explicit_ai_terms = (
        "use ai", "ask ai", "use nvidia", "deep analysis", "analyse deeply", "analyze deeply",
        "strategic recommendation", "strategy recommendation", "scenario analysis", "write a narrative",
        "brainstorm", "what should we do", "recommend a strategy", "compare alternatives",
    )
    if any(term in lower for term in explicit_ai_terms):
        return True, "The user explicitly requested judgement-heavy AI reasoning"

    # These intents generally need synthesis or external/contextual reasoning.
    if intent in {"general", "market", "intelligence"}:
        return True, f"{intent} is an open-ended reasoning intent"

    # File reading, accounting, tax labels, reconciliations, navigation and
    # validation are grounded in pre-calculated records and should be immediate.
    return False, f"{intent} is handled by the deterministic business engine"


def lightweight_file_context() -> dict[str, Any]:
    """Minimal shape used by file questions so they do not rebuild every dashboard."""
    return {
        "snapshot": {"current_ratio": None},
        "assets_liabilities": [],
        "recent_invoices": [],
        "recent_transactions": [],
        "open_validations": [],
        "forecast": {},
        "company_baseline": {},
        "market_profile": {},
        "market_snapshot": {},
        "information_requests": {},
        "market_signals": [],
    }


def build_actions(intent: str, context: dict[str, Any], model_connected: bool) -> tuple[list[DashboardAction], list[str], str]:
    if intent == "overview":
        return _overview_tour_actions(context)
    snapshot = context["snapshot"]
    ratio = snapshot.get("current_ratio")
    ratio_text = "unavailable" if ratio is None else f"{ratio:.2f}"
    actions: list[DashboardAction] = [action("character_state", state="thinking", duration_ms=250)]
    plan: list[str] = ["Read verified local business data", "Choose a safe dashboard route", "Explain the evidence"]
    mode = "guided"

    ratio_ids = [str(item.get("id")) for item in (_top_contributors(context, "asset") + _top_contributors(context, "liability"))]
    anomaly_ids = [str(item.get("id")) for item in context["recent_transactions"] if item.get("status") in {"anomaly", "critical"}][:4]
    invoice_review_ids = [str(item.get("id")) for item in context["recent_invoices"] if item.get("status") in {"review", "overdue"}][:4]
    validation_ids = [str(item.get("id")) for item in context["open_validations"][:4]]
    routes: dict[str, tuple[str, str, list[str], list[str]]] = {
        "money_map": ("money-map", "money-map-flow", [], ["Show accounts", "Show tax dashboard", "Return to overview"]),
        "inventory": ("inventory", "inventory-dashboard", [], ["Open import", "Show accounts", "Return to overview"]),
        "hr": ("hr", "hr-payroll-table", [], ["Open import", "Show accounts", "Return to overview"]),
        "current_ratio": ("accounts", "current-ratio-card", ratio_ids, ["Forecast cash flow", "Suggest improvements", "Return to overview"]),
        "accounts": ("accounts", "accounts-table", ratio_ids, ["Explain current ratio", "Show validation issues", "Generate a file"]),
        "anomaly": ("accounts", anomaly_ids[0] if anomaly_ids else "journal-register", anomaly_ids, ["Compare invoice records", "Flag for review", "Leave unchanged"]),
        "cash_flow": ("overview", "cash-flow-chart", [], ["Show supplier payments", "Show incoming receivables", "Create 90-day forecast"]),
        "invoice": ("accounts", "invoice-classification-table", invoice_review_ids, ["Show validation issues", "Generate a file", "Open import"]),
        "validation": ("accounts", "accounts-validation", validation_ids, ["Explain current ratio", "Refresh validations", "Return to overview"]),
        "quality": ("decisions", "context-board-runtime", [], ["Refresh validations", "Open import", "Return to overview"]),
        "decisions": ("decisions", "context-board-runtime", [], ["Refresh data lineage", "Explain the active app-section route", "Start deep company analysis"]),
        "tax": ("tax", "tax-summary", [], ["Explain GST position", "Generate tax workpaper", "Return to overview"]),
        "marketing": ("marketing", "marketing-channel-chart", [], ["Explain channel efficiency", "Show revenue trend", "Return to overview"]),
        "intelligence": ("intelligence", "competitor-positioning-chart", [], ["Start deep company analysis", "Open import", "Return to overview"]),
        "data_files": ("decisions", "permanent-file-library", [], ["Open import", "Show latest upload", "Start deep company analysis"]),
        "market": ("intelligence", "market-intelligence-workspace", [], ["Start deep company analysis", "Review company context", "Return to overview"]),
        "documents": ("accounts", "document-generator-rail", [], ["Generate a file", "Show accounts", "Return to overview"]),
        "import": ("decisions", "upload-zone", [], ["Review company context", "Show validation issues", "Return to overview"]),
        "setup": ("settings", "model-settings", [], ["Test NVIDIA", "Clear agent context", "Return to overview"]),
        "company": ("settings", "company-profile-form", [], ["Save company context", "Research supplier risks", "Return to overview"]),
        "overview": ("overview", "overview-dashboard", [], ["Explain current ratio", "Show accounts", "Show tax dashboard"]),
    }

    if intent in routes:
        destination, target, record_ids, choices = routes[intent]
        plan.insert(1, f"Open {destination.replace('-', ' ')}")
        actions.extend([
            action("character_say", message="I found the relevant evidence. I’ll show you where it lives.", duration_ms=700),
            action("character_move", target="navigation-edge", duration_ms=450),
            action("navigation_reveal", duration_ms=250),
            action("navigation_highlight", destination=destination, duration_ms=300),
            action("navigate", destination=destination, duration_ms=450),
            action("navigation_hide", duration_ms=180),
        ])
        if record_ids:
            actions.append(action("highlight_records", record_ids=record_ids, duration_ms=450))
        actions.extend([
            action("character_move", target=target, duration_ms=500),
            action("spotlight", target=target, duration_ms=300),
            action("offer_choices", choices=choices, duration_ms=200),
        ])
        if intent == "current_ratio":
            actions.insert(2, action("character_say", message=f"The verified current ratio is {ratio_text}.", duration_ms=600))
    else:
        mode = "answer"
        choices = ["Explain current ratio", "Show suspicious payment", "Show validation issues", "Open import"]
        if not model_connected:
            choices[-1] = "Configure model"
        actions.extend([
            action("character_state", state="explaining", duration_ms=200),
            action("offer_choices", choices=choices, duration_ms=200),
        ])
    return actions, plan, mode


async def model_status(verify: bool = False) -> dict[str, Any]:
    provider = settings.model_provider.strip().lower()
    if provider == "nvidia":
        if not settings.nvidia_api_key:
            return {"ok": False, "provider": "nvidia", "detail": "NVIDIA_API_KEY is missing", "model": settings.nvidia_model, "verified": False}
        if not verify:
            return {"ok": True, "provider": "nvidia", "detail": "NVIDIA NIM is configured; use Test NVIDIA to verify the key and model", "model": settings.nvidia_model, "verified": False}
        payload = {
            "model": settings.nvidia_model,
            "messages": [{"role": "user", "content": "Reply only with OK."}],
            "temperature": 0,
            "max_tokens": 3,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=30.0, connect=15.0), trust_env=False) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            content = str((((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
            return {"ok": True, "provider": "nvidia", "detail": "NVIDIA NIM chat completion succeeded", "model": settings.nvidia_model, "verified": True, "response": content[:80]}
        except Exception as exc:
            return {"ok": False, "provider": "nvidia", "detail": f"NVIDIA test failed: {type(exc).__name__}: {exc}", "model": settings.nvidia_model, "verified": False}
    if provider == "ollama":
        if not settings.ollama_enabled:
            return {"ok": False, "provider": "ollama", "detail": "OLLAMA_ENABLED is false", "model": settings.ollama_model, "verified": False}
        available, models = await ollama_available()
        installed = _installed_model(settings.ollama_model, models)
        return {"ok": bool(available and installed), "provider": "ollama", "detail": installed or "Ollama/model unavailable", "model": settings.ollama_model, "models": models, "verified": bool(available and installed)}
    return {"ok": False, "provider": provider, "detail": "Unsupported MODEL_PROVIDER", "model": "", "verified": False}


async def ask_model(
    user_message: str,
    intent: str,
    context: dict[str, Any],
    fallback: str,
    research: dict[str, Any] | None,
) -> tuple[str, str, bool, dict[str, Any]]:
    use_model, routing_reason = should_use_model(user_message, intent)
    provider = settings.model_provider.strip().lower()
    routing = {
        "enabled": use_model,
        "mode": settings.agent_ai_routing_mode,
        "reason": routing_reason,
        "provider": provider,
        "input_chars": 0,
        "output_chars": 0,
        "bypassed": not use_model,
    }
    if not use_model:
        return fallback, "deterministic business engine", False, routing
    if provider == "nvidia" and not settings.nvidia_api_key:
        routing["bypassed"] = True
        routing["reason"] = "NVIDIA_API_KEY is missing; deterministic fallback used"
        return fallback, "built-in safe planner (NVIDIA_API_KEY missing)", False, routing
    if provider == "ollama" and not settings.ollama_enabled:
        routing["bypassed"] = True
        routing["reason"] = "OLLAMA_ENABLED is false; deterministic fallback used"
        return fallback, "built-in safe planner (Ollama disabled)", False, routing

    memory = memory_context()
    durable_context = context_for_prompt()
    board_context = durable_context.get("context_board") or {}
    allowed_types = {str(item.get("document_type")) for item in board_context.get("enabled_sources", []) if item.get("document_type")}
    board_configured = bool(board_context)
    financial_allowed = not board_configured or bool(allowed_types & {"balance_sheet", "profit_loss", "cash_flow_statement", "bank_statements", "aged_debtors_creditors"})
    invoice_allowed = not board_configured or bool(allowed_types & {"supplier_invoices", "sales_invoices"})
    transaction_allowed = not board_configured or "bank_statements" in allowed_types
    market_allowed = not board_configured or "market_context" in allowed_types
    compact = {
        "company": context["snapshot"].get("company"),
        "financial_snapshot": context["snapshot"] if financial_allowed else {},
        "assets_liabilities": context["assets_liabilities"][:12] if financial_allowed else [],
        "recent_invoices": context["recent_invoices"][:8] if invoice_allowed else [],
        "recent_transactions": context["recent_transactions"][:10] if transaction_allowed else [],
        "open_validations": context["open_validations"][:8],
        "forecast": {"low_point": context["forecast"].get("low_point"), "method": context["forecast"].get("method")} if financial_allowed else {},
        "memory_summary": memory.get("summary", "")[-1800:],
        "recent_conversation": memory.get("recent_messages", [])[-6:],
        "working_context": durable_context,
        "research_results": (research or {}).get("results", [])[:5] if market_allowed else [],
        "company_baseline": context.get("company_baseline", {}) if financial_allowed else {},
        "market_profile": context.get("market_profile", {}) if market_allowed else {},
        "market_snapshot": context.get("market_snapshot", {}) if market_allowed else {},
        "information_requests": context.get("information_requests", {}),
        "uploaded_market_signals": context.get("market_signals", [])[:8] if market_allowed else [],
        "file_context": context.get("file_context", {}),
    }
    compressed_context, compression = compress_context(compact)
    system = (
        read_base_personality()
        + "\n\nAnswer the user's actual question using only the verified context supplied. "
          "Never replace the answer with a generic capability message. Do not invent numbers or claim a live source if no research result is supplied. "
          "If the request asks the application to perform an action, never replace execution with instructions; use the supplied deterministic action result or state the exact blocker. "
          "Respect the editable data-lineage map: excluded sources must not influence the answer; use each included file only through its configured extraction products and app-section connections; follow the displayed processing order; and use the active app-section filter as the current story. "
          "Use business_analyst_context as the governing internal decision brief. Before recommending an action, identify the evidence, explain the business implication, state the recommendation, expected effect, timing and uncertainty. "
          "For market or competitor analysis, combine business_analyst_context with market_analysis_template, market_analysis_context, the saved market report, uploaded market evidence and any supplied cited research. Never invent competitor metrics or unsupported market claims. "
          "Keep the answer under 190 words and do not include markdown tables."
    )
    prompt = (
        f"Intent: {intent}\nUser question: {user_message}\n"
        f"Verified context: {compressed_context}\n"
        f"Safe factual fallback if context is insufficient: {fallback}"
    )
    if provider == "nvidia":
        payload = {
            "model": settings.nvidia_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": settings.model_temperature,
            "max_tokens": settings.model_max_output_tokens,
            "stream": False,
        }
        try:
            timeout = float(settings.model_timeout_seconds)
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=timeout, connect=15.0), trust_env=False) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            message = ((body.get("choices") or [{}])[0].get("message") or {})
            content = str(message.get("content") or "").strip()
            if not content:
                return fallback, "built-in safe planner (NVIDIA returned empty content)", False, compression
            usage = body.get("usage") or {}
            compression["api_prompt_tokens"] = usage.get("prompt_tokens")
            compression["api_completion_tokens"] = usage.get("completion_tokens")
            return content, f"NVIDIA NIM: {settings.nvidia_model}", True, compression
        except Exception as exc:
            print(f"NVIDIA request failed: {type(exc).__name__}: {exc}")
            return fallback, f"built-in safe planner (NVIDIA failed: {type(exc).__name__})", False, compression

    if provider == "ollama":
        available, models = await ollama_available()
        model_to_use = _installed_model(settings.ollama_model.strip(), models) if available else None
        if not model_to_use:
            return fallback, "built-in safe planner (Ollama unavailable)", False, compression
        request_payload = {
            "model": model_to_use,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": {
                "temperature": settings.model_temperature,
                "num_ctx": min(max(settings.model_context_size, 1024), 32768),
                "num_predict": settings.model_max_output_tokens,
            },
        }
        try:
            timeout = float(settings.ollama_timeout_seconds)
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=timeout, connect=10.0), trust_env=False) as client:
                response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=request_payload)
                response.raise_for_status()
            content = str(response.json().get("message", {}).get("content", "")).strip()
            if content:
                return content, f"Ollama: {model_to_use}", True, compression
        except Exception as exc:
            print(f"Ollama request failed: {type(exc).__name__}: {exc}")
        return fallback, "built-in safe planner (Ollama failed)", False, compression

    return fallback, f"built-in safe planner (unsupported provider: {provider})", False, compression


async def handle_command(command: AgentCommand) -> AgentResponse:
    text = command.message.strip()
    intent = detect_intent(text)
    if command.workspace == "decisions" and intent == "general":
        intent = "decisions"
    # A file explanation is already fully grounded in the stored upload analysis.
    # Avoid rebuilding every financial dashboard before answering it.
    context = lightweight_file_context() if intent == "data_files" else agent_data_context()
    context["business_db"] = clippy_launch_context()
    context["file_context"] = file_context_for_prompt(text)
    library = upload_library()
    context["setup_coverage"] = library.get("coverage") or {}
    context["upload_counts"] = {
        "setup": len((library.get("files") or {}).get("setup") or []),
        "recurring": len((library.get("files") or {}).get("recurring") or []),
    }
    context["profit_structure"] = (dashboard_summary().get("profit_structure") or {})
    # Clippy starts with the compact business.db launch context, then receives
    # detailed governed packets only when the request needs them.
    if intent in {"overview", "quality", "accounts", "tax", "marketing", "company", "general"}:
        context["data_quality"] = data_quality_dashboard()
        context["tax_dashboard"] = tax_dashboard()
        context["marketing_dashboard"] = marketing_dashboard()
        context["accounts_dashboard"] = accounting_dashboard()
        context["intelligence_status"] = analysis_status()
        context["payroll_context"] = {
            "matched_files": [item for item in (context.get("file_context") or {}).get("matched_files", []) if "payroll" in str(item).lower()],
            "has_employees": bool((get_company_profile() or {}).get("has_employees")),
        }
        profile = get_company_profile() or {}
        context["supplier_context"] = {
            "supplier_regions": profile.get("supplier_regions"),
            "primary_risks": profile.get("primary_risks"),
        }
    if intent == "decisions":
        context["decision_context"] = decision_context_dashboard()
        context["context_board"] = context_board_dashboard(refresh_sources=False)

    deterministic = execute_deterministic_command(text, context)
    if deterministic is not None:
        evidence = {
            "setup_coverage": context.get("setup_coverage") or {},
            "core_setup_complete": not bool((context.get("setup_coverage") or {}).get("required_missing")),
            "execution_result": deterministic.get("result") or {},
            "data_quality": context.get("data_quality") or {},
        }
        response = AgentResponse(
            mode=str(deterministic.get("mode") or "answer"),
            summary=str(deterministic.get("summary") or "Action completed."),
            actions=list(deterministic.get("actions") or []),
            used_model="deterministic action engine",
            evidence=evidence,
            plan=list(deterministic.get("plan") or []),
            citations=[],
            execution_status=str(deterministic.get("execution_status") or "completed"),
            executed_actions=list(deterministic.get("executed_actions") or []),
        )
        save_conversation_message("user", text, "user", command.workspace)
        save_conversation_message("assistant", response.summary, response.used_model, command.workspace)
        save_agent_event(text, command.workspace, response.model_dump())
        update_working_context(
            user_message=text, intent=intent, workspace=command.workspace, outcome=response.summary,
            model=response.used_model, evidence=evidence,
        )
        return response

    research: dict[str, Any] | None = None
    citations: list[dict[str, str]] = []

    if intent == "market":
        profile = get_company_profile()
        research_query = f"{text} | company: {profile.get('industry')} | location: {profile.get('primary_location')} | suppliers: {profile.get('supplier_regions')}"
        research = await search_web(research_query, limit=5)
        citations = [
            {"title": str(item.get("title") or "Source"), "url": str(item.get("url") or "")}
            for item in research.get("results", []) if item.get("url")
        ]

    fallback = factual_fallback(intent, context, research)
    summary, used_model, model_connected, compression = await ask_model(text, intent, context, fallback, research)
    used_model = used_model.replace("Ledger", "Clippy").replace("Robert", "Clippy")
    actions, plan, mode = build_actions(intent, context, model_connected)

    # Explicit write-like requests become reviewable approvals rather than silent changes.
    lower = text.lower()
    if any(term in lower for term in ["flag for review", "prepare correction", "change the record", "delete", "mark as paid"]):
        approval_id = create_approval(
            "financial_record_review",
            "Review requested by Ledger",
            {"user_request": text, "intent": intent, "evidence": context.get("open_validations", [])[:3]},
        )
        summary += f" I created approval request #{approval_id}; no financial record was changed."

    maybe_compact_memory()
    save_conversation_message("user", text, "user", command.workspace)
    save_conversation_message("assistant", summary, used_model, command.workspace)

    evidence = {
        "snapshot": context["snapshot"],
        "open_validations": context["open_validations"][:8],
        "research_live": bool(research and research.get("live")),
        "prompt_compression": compression,
        "matched_files": (context.get("file_context") or {}).get("matched_files", [])[:6],
        "market_intelligence": ((context.get("file_context") or {}).get("company_ai_context") or {}).get("market_intelligence", {}),
        "setup_coverage": context.get("setup_coverage") or {},
        "core_setup_complete": not bool((context.get("setup_coverage") or {}).get("required_missing")),
    }
    response = AgentResponse(
        mode=mode,
        summary=summary,
        actions=actions,
        used_model=used_model,
        evidence=evidence,
        plan=plan,
        citations=citations,
        execution_status="answered",
        executed_actions=[],
    )
    save_agent_event(text, command.workspace, response.model_dump())
    update_working_context(
        user_message=text, intent=intent, workspace=command.workspace, outcome=summary,
        model=used_model, evidence=evidence,
    )
    return response
