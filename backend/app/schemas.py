from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentCommand(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    workspace: str = "overview"


class DashboardAction(BaseModel):
    type: Literal[
        "character_state", "character_move", "character_say", "spotlight",
        "clear_spotlight", "navigation_reveal", "navigation_highlight",
        "navigation_hide", "navigate", "highlight_records",
        "clear_highlights", "offer_choices", "wait", "apply_filter",
        "open_source", "refresh_data", "generate_document",
        "download_tax_workpaper", "test_model",
    ]
    target: str | None = None
    destination: str | None = None
    state: str | None = None
    message: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    choices: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    document_type: str | None = None
    output_format: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 700


class AgentResponse(BaseModel):
    mode: Literal["guided", "answer", "setup"] = "guided"
    summary: str
    actions: list[DashboardAction]
    used_model: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)
    execution_status: Literal["completed", "planned", "queued", "partial", "blocked", "requires_confirmation", "answered"] = "answered"
    executed_actions: list[str] = Field(default_factory=list)


class OllamaTestRequest(BaseModel):
    base_url: str | None = None
    model: str | None = None


class SearchTestRequest(BaseModel):
    url: str | None = None


class CompanyProfile(BaseModel):
    company_name: str = "Demo Trading Co."
    industry: str = "Wholesale and distribution"
    primary_location: str = "Melbourne, Australia"
    reporting_currency: str = "AUD"
    supplier_regions: str = "Australia, China, Singapore"
    important_currencies: str = "AUD, USD, CNY"
    primary_risks: str = "Cash flow, freight costs, supplier concentration"
    current_objective: str = "Improve working capital"
    current_ratio_target: float = 1.2
    cash_runway_target_days: int = 45
    abn: str = ""
    entity_type: Literal["company", "sole_trader", "partnership", "trust", "not_for_profit"] = "company"
    state_or_territory: str = "VIC"
    gst_registered: bool = False
    gst_accounting_method: Literal["cash", "accrual"] = "accrual"
    bas_frequency: Literal["monthly", "quarterly", "annual"] = "quarterly"
    payg_withholding_registered: bool = False
    has_employees: bool = False
    financial_year_end: str = "30 June"
    income_tax_rate: float = Field(default=25.0, ge=0, le=60)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


DocumentType = Literal[
    "transactions", "bank_statements", "payments", "supplier_invoices",
    "sales_invoices", "invoices", "assets", "liabilities",
    "assets_liabilities", "customers", "suppliers", "inventory", "budgets",
    "balance_sheet", "profit_loss", "cash_flow_statement", "market_context",
    "purchase_orders", "sales_orders", "payroll", "contracts", "generic",
]


class MappingRequest(BaseModel):
    document_type: DocumentType
    mapping: dict[str, str]




class UploadCategoryChangeRequest(BaseModel):
    intake_category: Literal["setup", "recurring"]


class UploadDeleteRequest(BaseModel):
    create_backup: bool = True
    confirmation: str = Field(min_length=6, max_length=120)


class UploadRetryRequest(BaseModel):
    intake_category: Literal["setup", "recurring"]
    declared_document_type: str = Field(min_length=2, max_length=80)


class ApprovalResolution(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = ""


class ClearDataRequest(BaseModel):
    scope: Literal["company", "memory", "market", "all"] = "company"
    create_backup: bool = True
    confirmation: str = Field(min_length=5, max_length=80)


class RebuildPipelineRequest(BaseModel):
    force_full_baseline: bool = True


class GenerateDocumentRequest(BaseModel):
    document_type: str = Field(min_length=2, max_length=80)
    output_format: Literal["pdf", "csv"] = "pdf"
    fields: dict[str, Any] = Field(default_factory=dict)

class InvoiceCategorisationResolution(BaseModel):
    account_code: str = Field(min_length=3, max_length=20)
    tax_code: str = Field(default="GST", min_length=2, max_length=30)
    remember: bool = True
    note: str = Field(default="", max_length=500)


class CategorisationRuleRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=160)
    account_code: str = Field(min_length=3, max_length=20)
    tax_code: str = Field(default="GST", min_length=2, max_length=30)
    match_type: Literal["contains", "supplier_exact", "supplier_contains", "description_contains"] = "contains"


class IntegrationSettingsRequest(BaseModel):
    mode: Literal["offline", "official_only", "enrichment", "connected"] = "offline"
    official_tax_sources: bool = False
    supplier_enrichment: bool = False
    bank_feeds: bool = False
    email_intake: bool = False
    cloud_storage: bool = False
    external_processing_consent: bool = False

class AssistantProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    persona: str | None = Field(default=None, max_length=80)
    response_style: str | None = Field(default=None, max_length=40)
    voice_auto_speak: bool | None = None
    voice_language: str | None = Field(default=None, max_length=20)


class AgentArchitectureRunRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    workspace: str = Field(default="overview", max_length=80)
    intent: str = Field(default="general", max_length=80)


class AgentConfigUpdate(BaseModel):
    enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)
    prompt: str | None = Field(default=None, max_length=20000)
