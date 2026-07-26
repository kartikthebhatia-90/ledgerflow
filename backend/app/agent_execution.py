from __future__ import annotations

import re
from typing import Any

from .agent_context import clear_working_context
from .classification_repair import schedule_classification_repairs
from .competitor_intelligence import process_analysis_job, start_analysis_job
from .data_quality import data_quality_dashboard
from .decision_context import decision_context_dashboard, refresh_decision_context
from .context_board import context_board_dashboard
from .folder_intake import scan_folder_intake
from .job_queue import submit_background_job
from .schemas import DashboardAction
from .validation import run_validations


def _action(action_type: str, **kwargs: Any) -> DashboardAction:
    return DashboardAction(type=action_type, **kwargs)


def _contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _core_ready(context: dict[str, Any]) -> bool:
    return not bool((context.get("setup_coverage") or {}).get("required_missing"))


def _blocked_for_setup(context: dict[str, Any], requested: str) -> dict[str, Any]:
    missing = list((context.get("setup_coverage") or {}).get("required_missing") or [])
    labels = ", ".join(str(item).replace("_", " ").title() for item in missing) or "required setup documents"
    return {
        "handled": True,
        "mode": "setup",
        "execution_status": "blocked",
        "summary": f"I did not start {requested} because the core setup is incomplete. Missing: {labels}.",
        "plan": ["Check core setup coverage", "Stop the requested action", "Show the missing evidence"],
        "actions": [
            _action("character_state", state="warning", duration_ms=120),
            _action("navigate", destination="decisions", duration_ms=420),
            _action("character_move", target="permanent-file-library", duration_ms=260),
            _action("spotlight", target="permanent-file-library", duration_ms=220),
            _action("character_say", message=f"I cannot run {requested} yet. Add or repair: {labels}.", duration_ms=1000),
        ],
        "executed_actions": [],
    }


def _money_compact(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "$0"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:,.1f}m"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:,.0f}k"
    return f"${amount:,.0f}"


def _say(message: str) -> DashboardAction:
    """Speak at a readable pace: ~330 ms per word plus settle time, capped at 9 s."""
    words = max(1, len(message.split()))
    duration = min(9000, max(3000, 1100 + words * 330))
    return _action("character_say", message=message, duration_ms=duration)


def build_introduction(context: dict[str, Any]) -> dict[str, Any]:
    """User-data-aware showcase: Clippy spotlights what the user has already set
    up, narrates their real figures, and skips sections with no data yet.
    Designed to be triggered manually after uploading a file — not on first launch.
    Works without an AI key. Every number comes from business.db.
    """
    snapshot   = context.get("snapshot") or {}
    company    = str(snapshot.get("company") or "your business").strip()
    cash       = _money_compact(snapshot.get("cash"))
    revenue    = _money_compact(snapshot.get("revenue_month"))
    try:
        ratio  = f"{float(snapshot.get('current_ratio') or 0):.2f}"
    except (TypeError, ValueError):
        ratio  = "0.00"
    coverage   = context.get("setup_coverage") or {}
    core_ready = not bool(coverage.get("required_missing"))
    upload_counts = context.get("upload_counts") or {}
    file_total = int(upload_counts.get("setup") or 0) + int(upload_counts.get("recurring") or 0)

    # Build only the stops that have real data behind them
    stops: list[tuple[str, str, str]] = []

    # Always show overview if core is ready
    if core_ready:
        stops.append((
            "overview", "overview-metric-grid",
            f"This is {company} — {cash} cash on hand, a current ratio of {ratio} "
            f"and {revenue} of monthly inflow. Every figure on this screen is read "
            "live from one DuckDB file and traces back to your uploaded source data."
        ))
        stops.append((
            "overview", "clippy-overview-brief",
            "This is my analyst brief for your business — strengths, attention points "
            "and evidence quality, generated from the verified numbers in your files. "
            "No invented data, no hallucinated figures."
        ))
        stops.append((
            "overview", "overview-cash-forecast-chart",
            "The cash outlook projects forward from your current balance and flags the "
            "low point early. LedgerFlow tells you about cash problems before they arrive."
        ))

    # Money Map only if we have revenue data
    if snapshot.get("revenue_month"):
        stops.append((
            "money-map", "money-map-flow",
            f"The Money Map traces {revenue} of your customer revenue through each "
            "operating department, estimated tax, and down to retained profit. "
            "You can see exactly where every dollar goes."
        ))

    # Accounts if we have accounts data
    if core_ready:
        stops.append((
            "accounts", "current-ratio-card",
            "Accounts keeps your liquidity ratios live and gives you a full account "
            "register where every classification stays visible and reviewable. "
            "No black boxes."
        ))

    # Tax if we have tax estimate
    tax_ctx = context.get("tax_dashboard") or {}
    if tax_ctx.get("summary", {}).get("estimated_income_tax"):
        stops.append((
            "tax", "tax-summary",
            "Tax keeps your indicative income-tax estimate and net GST position live. "
            "It can also scan current ATO guidance and match concessions to your evidence."
        ))

    # HR if we have payroll
    hr_ctx = context.get("accounts_dashboard") or {}
    if file_total > 3:
        stops.append((
            "hr", "hr-payroll-table",
            "HR organises payroll, PAYG withholding, superannuation, leave, training "
            "and a compliance action queue — all source-backed from your uploaded files."
        ))

    # Intelligence if competitor data exists
    intel_ctx = context.get("intelligence_status") or {}
    if intel_ctx.get("has_results") or intel_ctx.get("competitor_count"):
        stops.append((
            "intelligence", "market-intelligence-workspace",
            "Intelligence places your business next to competitor and market evidence. "
            "Any figure we cannot verify stays blank — we never invent competitor data."
        ))

    # Data management always last
    stops.append((
        "decisions", "upload-zone",
        f"Everything starts here — you have {file_total} verified files loaded right now. "
        "Drop in new spreadsheets or PDFs and LedgerFlow profiles, validates, versions "
        "and flows them from bronze to silver to gold into business.db automatically."
    ))

    # --- no data yet path ---
    if not core_ready and file_total == 0:
        actions = [
            _action("character_state", state="greeting", duration_ms=1400),
            _say("G'day! I'm Clippy, your built-in business analyst. "
                 "Drop in your first file using the upload zone below, "
                 "then come back to the Overview and hit ✨ — "
                 "I'll walk you through exactly what LedgerFlow has built from your data."),
            _action("character_state", state="explaining", duration_ms=150),
            _action("navigate", destination="decisions", duration_ms=700),
            _action("spotlight", target="upload-zone", duration_ms=650),
            _action("character_move", target="upload-zone", duration_ms=900),
            _say("Drag in your balance sheet, profit and loss, cash flow, "
                 "chart of accounts and business requirements. "
                 "Once they land I can analyse the full business."),
            _action("clear_spotlight", duration_ms=250),
            _action("character_state", state="idle", duration_ms=100),
            _action("offer_choices", choices=["Show data management", "What files do I need?"], duration_ms=150),
        ]
        return {
            "handled": True, "mode": "guided", "execution_status": "completed",
            "summary": "Clippy pointed to the upload zone — no files loaded yet.",
            "plan": ["Greet", "Direct to upload zone", "List required files"],
            "actions": actions, "executed_actions": ["introduced_assistant"],
        }

    # --- main showcase ---
    actions: list[DashboardAction] = [
        _action("character_state", state="greeting", duration_ms=1400),
        _say(f"G'day! I'm Clippy, your built-in business analyst. "
             f"You've uploaded your files — let me show you exactly what "
             f"LedgerFlow has built from your data for {company}."),
        _action("character_state", state="explaining", duration_ms=150),
    ]
    prev_dest = ""
    for destination, target, message in stops:
        if destination != prev_dest:
            actions.append(_action("navigate", destination=destination, duration_ms=750))
            prev_dest = destination
        actions.append(_action("spotlight", target=target, duration_ms=650))
        actions.append(_action("character_move", target=target, duration_ms=900))
        actions.append(_say(message))
        actions.append(_action("clear_spotlight", duration_ms=250))

    actions.extend([
        _action("navigate", destination="overview", duration_ms=750),
        _action("character_state", state="greeting", duration_ms=800),
        _say(f"That's {company} in LedgerFlow — "
             "every number traced to a source file, "
             "nothing invented, nothing hidden. Ask me anything."),
        _action("character_state", state="idle", duration_ms=100),
        _action("offer_choices", choices=[
            "Start guided overview", "Explain the current ratio",
            "Show the money map", "Show data management"
        ] if core_ready else ["Show data management", "What files are missing?"], duration_ms=150),
    ])

    summary = (
        f"Clippy showcased {company}'s live data across "
        f"{len(stops)} sections ({file_total} files loaded), "
        "with every figure pulled from business.db."
    )
    return {
        "handled": True, "mode": "guided", "execution_status": "completed",
        "summary": summary,
        "plan": [
            "Greet using the user's company name",
            "Spotlight only the sections that have real data behind them",
            "Close with next-step choices suited to setup state",
        ],
        "actions": actions, "executed_actions": ["introduced_assistant", "hosted_showcase"],
    }


_INTRO_TRIGGERS = (
    "introduce yourself",
    "introduce your self",
    "who are you",
    "what are you",
    "what can you do",
    "what can this app do",
    "what does this app do",
    "what can ledgerflow do",
    "help me get started",
    "getting started",
    "show me around",
    "give me a demo",
    "product demo",
    "product tour",
    "showcase the app",
    "demo the app",
)
_INTRO_GREETINGS = {"hi", "hello", "hey", "hi clippy", "hello clippy", "hey clippy", "g'day", "gday", "intro", "introduction", "introduce"}


def execute_deterministic_command(text: str, context: dict[str, Any]) -> dict[str, Any] | None:
    """Execute action-oriented commands instead of replying with instructions.

    Read-only navigation is returned as an executable UI action sequence. Safe
    local operations are executed here before the response is created.
    Destructive requests are routed to the existing confirmation interface.
    """
    lower = re.sub(r"\s+", " ", text.lower().strip())

    # Self-introduction: Clippy explains who he is and what LedgerFlow helps with.
    if lower in _INTRO_GREETINGS or any(trigger in lower for trigger in _INTRO_TRIGGERS):
        return build_introduction(context)

    # Full overview is owned by the guided-tour builder in agent.py.
    if lower in {"overview", "start overview", "guided overview", "take me through the app", "show me everything"}:
        return None

    navigation = [
        (("money map", "money flow", "where money goes", "sources of money"), "money-map", "money-map-flow", "Money map"),
        (("accounts", "account", "trial balance", "journal"), "accounts", "accounts-table", "Financial control"),
        (("inventory", "stock", "reorder", "sku"), "inventory", "inventory-dashboard", "Inventory management"),
        (("tax", "gst", "bas", "compliance"), "tax", "tax-summary", "Tax and compliance"),
        (("human resources", "payroll", "employee", "employees", "leave balance"), "hr", "hr-payroll-table", "People and payroll"),
        (("marketing", "growth", "channel", "roas"), "marketing", "marketing-channel-chart", "Growth analytics"),
        (("context board", "context map", "data lineage", "source lineage", "processing route", "app section inputs", "decision context", "decision timeline", "decision inputs", "time context", "analysis timeline", "data management"), "decisions", "upload-zone", "Data management"),
        (("competitor", "intelligence", "market analysis"), "intelligence", "market-intelligence-workspace", "Company intelligence"),
        (("data quality", "data trust", "quality checks", "source coverage"), "decisions", "upload-zone", "Data management"),
        (("data and files", "data & files", "upload centre", "upload center", "files"), "decisions", "upload-zone", "Data management"),
        (("settings", "nvidia", "model settings", "agent context"), "settings", "model-settings", "Agent and settings"),
        (("home", "decision overview", "analytics overview"), "overview", "overview-dashboard", "Decision overview"),
    ]
    navigation_verbs = ("show", "open", "go to", "take me to", "navigate", "scroll to", "bring me to")
    if any(verb in lower for verb in navigation_verbs):
        for terms, destination, target, label in navigation:
            if any(term in lower for term in terms):
                return {
                    "handled": True,
                    "mode": "guided",
                    "execution_status": "planned",
                    "summary": f"Opened {label} and highlighted the relevant section.",
                    "plan": [f"Navigate to {label}", "Highlight the requested evidence"],
                    "actions": [
                        _action("character_state", state="explaining", duration_ms=120),
                        _action("navigate", destination=destination, duration_ms=420),
                        _action("character_move", target=target, duration_ms=260),
                        _action("spotlight", target=target, duration_ms=220),
                        _action("character_say", message=f"This is {label}. I have opened the section rather than giving you navigation instructions.", duration_ms=850),
                    ],
                    "executed_actions": [f"navigate:{destination}", f"spotlight:{target}"],
                }

    if _contains(lower, "refresh context board", "rebuild context board", "refresh decision context", "update decision context", "refresh time context", "rebuild decision timeline"):
        refresh_decision_context("agent_requested_refresh")
        result = context_board_dashboard(refresh_sources=False)
        summary_data = result.get("summary") or {}
        summary = (
            f"Refreshed the Context Board with {summary_data.get('source_count', 0)} source(s) and "
            f"{summary_data.get('context_count', 0)} editable context layer(s). "
            f"{summary_data.get('included_count', 0)} included file(s) currently feed Ledger AI through the configured processing routes."
        )
        return {
            "handled": True,
            "mode": "guided",
            "execution_status": "completed",
            "summary": summary,
            "plan": ["Refresh uploaded sources", "Preserve source inclusion, extraction routes and app-section connections", "Open Data management"],
            "actions": [
                _action("navigate", destination="decisions", duration_ms=320),
                _action("character_move", target="context-board-runtime", duration_ms=220),
                _action("spotlight", target="context-board-runtime", duration_ms=180),
                _action("character_say", message=summary, duration_ms=900),
            ],
            "executed_actions": ["refresh_context_board", "navigate:decisions"],
            "result": result,
        }

    if _contains(lower, "scan folders", "scan the folders", "process pasted files", "check file drop", "check watched folders"):
        result = scan_folder_intake()
        queued = len(result.get("queued") or [])
        errors = len(result.get("errors") or [])
        summary = f"Scanned the Permanent and Recurring folders. Queued {queued} file(s)"
        summary += f" and found {errors} error(s)." if errors else "."
        return {
            "handled": True,
            "mode": "answer",
            "execution_status": "completed" if not errors else "partial",
            "summary": summary,
            "plan": ["Scan both watched folders", "Queue supported files", "Refresh the file centre"],
            "actions": [
                _action("navigate", destination="decisions", duration_ms=320),
                _action("character_move", target="folder-intake-panel", duration_ms=220),
                _action("spotlight", target="folder-intake-panel", duration_ms=180),
                _action("refresh_data", duration_ms=50),
                _action("character_say", message=summary, duration_ms=900),
            ],
            "executed_actions": ["scan_folders"],
            "result": result,
        }

    if _contains(lower, "repair classifications", "fix classifications", "reclassify files", "repair file types"):
        result = schedule_classification_repairs()
        repairs = int(result.get("repair_count") or 0)
        summary = f"Started {repairs} classification repair(s)." if repairs else "Checked classifications; no repair is currently required."
        return {
            "handled": True,
            "mode": "answer",
            "execution_status": "queued" if repairs else "completed",
            "summary": summary,
            "plan": ["Inspect stored file types", "Schedule safe corrective jobs", "Refresh coverage after completion"],
            "actions": [
                _action("navigate", destination="decisions", duration_ms=320),
                _action("character_move", target="folder-intake-panel", duration_ms=220),
                _action("spotlight", target="folder-intake-panel", duration_ms=180),
                _action("refresh_data", duration_ms=50),
                _action("character_say", message=summary, duration_ms=850),
            ],
            "executed_actions": ["repair_classifications"],
            "result": result,
        }

    if _contains(lower, "refresh validations", "run validations", "recheck data", "check the data", "validate data"):
        issues = run_validations()
        quality = data_quality_dashboard()
        summary = f"Re-ran validation and data-trust checks. {len(issues)} business validation item(s) are open; the data trust score is {quality.get('score', 0)}/100."
        return {
            "handled": True,
            "mode": "answer",
            "execution_status": "completed",
            "summary": summary,
            "plan": ["Run deterministic business validations", "Reconcile dashboard sources", "Open Data management"],
            "actions": [
                _action("navigate", destination="decisions", duration_ms=320),
                _action("character_move", target="context-board-runtime", duration_ms=220),
                _action("spotlight", target="context-board-runtime", duration_ms=180),
                _action("refresh_data", duration_ms=50),
                _action("character_say", message=summary, duration_ms=950),
            ],
            "executed_actions": ["refresh_validations", "refresh_data_quality"],
            "result": {"validations": issues, "quality": quality},
        }

    if _contains(lower, "start deep company analysis", "run deep company analysis", "start competitor analysis", "analyse competitors", "analyze competitors"):
        if not _core_ready(context):
            return _blocked_for_setup(context, "deep company analysis")
        job = start_analysis_job()
        if job.get("start_background"):
            submit_background_job("competitor-analysis", process_analysis_job, str(job["job_id"]))
        summary = "Deep company analysis is already running." if not job.get("start_background") else "Started deep company analysis and opened Company intelligence."
        return {
            "handled": True,
            "mode": "guided",
            "execution_status": "queued",
            "summary": summary,
            "plan": ["Verify core setup", "Start the competitor-analysis job", "Open its progress workspace"],
            "actions": [
                _action("navigate", destination="intelligence", duration_ms=320),
                _action("character_move", target="market-intelligence-workspace", duration_ms=220),
                _action("spotlight", target="market-intelligence-workspace", duration_ms=180),
                _action("refresh_data", duration_ms=50),
                _action("character_say", message=summary, duration_ms=900),
            ],
            "executed_actions": ["start_company_analysis"],
            "result": job,
        }

    if _contains(lower, "generate management summary", "create management summary", "download management summary", "generate a pdf summary"):
        if not _core_ready(context):
            return _blocked_for_setup(context, "management-summary generation")
        output_format = "csv" if "csv" in lower else "pdf"
        return {
            "handled": True,
            "mode": "guided",
            "execution_status": "planned",
            "summary": f"Generated the management summary as {output_format.upper()} and refreshed the document register.",
            "plan": ["Use the verified dashboard snapshot", f"Generate {output_format.upper()}", "Refresh generated outputs"],
            "actions": [
                _action("navigate", destination="accounts", duration_ms=320),
                _action("character_move", target="document-generator-rail", duration_ms=220),
                _action("spotlight", target="document-generator-rail", duration_ms=180),
                _action("generate_document", document_type="management_summary", output_format=output_format, duration_ms=50),
                _action("character_say", message=f"The management summary {output_format.upper()} has been created and downloaded.", duration_ms=850),
            ],
            "executed_actions": [f"generate_document:management_summary:{output_format}"],
        }

    if _contains(lower, "generate tax workpaper", "download tax workpaper", "create tax workpaper"):
        if not _core_ready(context):
            return _blocked_for_setup(context, "tax-workpaper generation")
        output_format = "csv" if "csv" in lower else "pdf"
        return {
            "handled": True,
            "mode": "guided",
            "execution_status": "planned",
            "summary": f"Generated the tax workpaper as {output_format.upper()}.",
            "plan": ["Open Tax and compliance", "Generate the review-required workpaper"],
            "actions": [
                _action("navigate", destination="tax", duration_ms=320),
                _action("character_move", target="tax-summary", duration_ms=220),
                _action("spotlight", target="tax-summary", duration_ms=180),
                _action("download_tax_workpaper", output_format=output_format, duration_ms=50),
                _action("character_say", message=f"The tax workpaper {output_format.upper()} has been created and downloaded.", duration_ms=850),
            ],
            "executed_actions": [f"download_tax_workpaper:{output_format}"],
        }

    if _contains(lower, "test nvidia", "test the model", "test configured model", "verify nvidia", "check nvidia connection"):
        summary = "Testing the configured model connection now."
        return {
            "handled": True,
            "mode": "answer",
            "execution_status": "planned",
            "summary": summary,
            "plan": ["Open model settings", "Run the configured provider test", "Report the actual result"],
            "actions": [
                _action("navigate", destination="settings", duration_ms=320),
                _action("character_move", target="model-settings", duration_ms=220),
                _action("spotlight", target="model-settings", duration_ms=180),
                _action("character_say", message=summary, duration_ms=350),
                _action("test_model", duration_ms=50),
            ],
            "executed_actions": ["test_model"],
        }

    if lower in {"generate a file", "create a file", "make a file", "generate document", "create document"}:
        return {
            "handled": True,
            "mode": "guided",
            "execution_status": "requires_confirmation",
            "summary": "Choose the business output and I will create it directly.",
            "plan": ["Open generated outputs", "Ask only for the missing output choice", "Execute the selected generation action"],
            "actions": [
                _action("navigate", destination="accounts", duration_ms=320),
                _action("character_move", target="document-generator-rail", duration_ms=220),
                _action("spotlight", target="document-generator-rail", duration_ms=180),
                _action("offer_choices", choices=["Generate management summary PDF", "Generate management summary CSV", "Generate tax workpaper"], duration_ms=120),
            ],
            "executed_actions": ["open_document_generator"],
        }

    if _contains(lower, "clear working context", "clear agent context", "forget recent conversation"):
        result = clear_working_context()
        summary = "Cleared recent working context. Base personality, company context, uploaded evidence and market intelligence were preserved."
        return {
            "handled": True,
            "mode": "answer",
            "execution_status": "completed",
            "summary": summary,
            "plan": ["Clear only recent conversational continuity", "Preserve permanent context layers"],
            "actions": [
                _action("navigate", destination="settings", duration_ms=320),
                _action("character_move", target="agent-context-settings", duration_ms=220),
                _action("spotlight", target="agent-context-settings", duration_ms=180),
                _action("refresh_data", duration_ms=50),
                _action("character_say", message=summary, duration_ms=950),
            ],
            "executed_actions": ["clear_working_context"],
            "result": result,
        }

    if _contains(lower, "delete all data", "reset all data", "reset the app", "clear all data"):
        summary = "I opened the protected reset control. I did not delete anything because the reset requires the existing CLEAR ALL confirmation."
        return {
            "handled": True,
            "mode": "setup",
            "execution_status": "requires_confirmation",
            "summary": summary,
            "plan": ["Open the protected reset interface", "Require explicit confirmation", "Do not perform a destructive action in chat"],
            "actions": [
                _action("navigate", destination="settings", duration_ms=320),
                _action("character_move", target="reset-all-data", duration_ms=220),
                _action("spotlight", target="reset-all-data", duration_ms=180),
                _action("character_say", message=summary, duration_ms=1000),
            ],
            "executed_actions": ["open_reset_confirmation"],
        }

    return None
