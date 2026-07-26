export type Workspace =
  | 'overview'
  | 'assets-liabilities'
  | 'invoices'
  | 'transactions'
  | 'cash-flow'
  | 'validation'
  | 'market'
  | 'import'
  | 'accounts'
  | 'documents'
  | 'tax'
  | 'company'
  | 'setup'
  | 'marketing'
  | 'inventory'
  | 'hr'
  | 'money-map'
  | 'intelligence'
  | 'operations'
  | 'settings'
  | 'quality'
  | 'decisions'


export type AssistantProfile = {
  version: number
  name: string
  persona: string
  response_style: string
  voice_auto_speak: boolean
  voice_language: string
  updated_at: string
  catalogue: {
    default: string
    personas: Record<string, { label: string; description: string; instruction: string }>
    response_styles: Record<string, string>
  }
}

export type AgentAction = {
  type: string
  target?: string | null
  destination?: Workspace | null
  state?: string | null
  message?: string | null
  record_ids?: string[]
  choices?: string[]
  filters?: Record<string, unknown>
  document_type?: string | null
  output_format?: 'pdf' | 'csv' | string | null
  payload?: Record<string, unknown>
  duration_ms?: number
}

export type AgentResponse = {
  mode: 'guided' | 'answer' | 'setup'
  summary: string
  actions: AgentAction[]
  used_model: string
  evidence: Record<string, unknown>
  plan: string[]
  citations: Array<{ title: string; url: string }>
  execution_status: 'completed' | 'planned' | 'queued' | 'partial' | 'blocked' | 'requires_confirmation' | 'answered'
  executed_actions: string[]
}

export type CompanyProfile = {
  company_name: string
  industry: string
  primary_location: string
  reporting_currency: string
  supplier_regions: string
  important_currencies: string
  primary_risks: string
  current_objective: string
  current_ratio_target: number
  cash_runway_target_days: number
  abn: string
  entity_type: 'company' | 'sole_trader' | 'partnership' | 'trust' | 'not_for_profit'
  state_or_territory: string
  gst_registered: boolean
  gst_accounting_method: 'cash' | 'accrual'
  bas_frequency: 'monthly' | 'quarterly' | 'annual'
  payg_withholding_registered: boolean
  has_employees: boolean
  financial_year_end: string
  income_tax_rate: number
}

export type Summary = {
  company: CompanyProfile
  current_assets: number
  current_liabilities: number
  current_ratio: number | null
  quick_ratio: number | null
  working_capital: number
  cash: number
  inventory: number
  total_assets: number
  total_liabilities: number
  debt_to_assets: number | null
  anomaly_count: number
  revenue_month: number
  expenses_month: number
  revenue_change: number
  gross_margin: number
  receivable_days: number
  payable_days: number
  cash_runway_days: number
  open_invoice_total: number
  overdue_invoice_total: number
  current_ratio_target: number
  cash_runway_target_days: number
  critical_alerts: number
  business_validation_count?: number
  account_review_count?: number
  cash_series: Array<{ month: string; cash: number | null; forecast: number | null }>
  performance_series: Array<{ month: string; revenue: number; expenses: number }>
  position_series: Array<{ label: string; value: number }>
  profit_structure: { period_end: string; series: Array<{ label: string; value: number }>; revenue: number; costs: number; profit: number }
  invoice_exposure_series: Array<{ label: string; open: number; overdue: number }>
  forecast_low_point: number
  forecast_method: string
  metric_sources?: Record<string, string>
}

export type DashboardIntegrity = {
  verified_at: string
  status: 'reconciled' | 'mismatch'
  all_reconciled: boolean
  message: string
  loaded_charts: number
  total_charts: number
  source_counts: Record<string, number>
  checks: Array<{ metric: string; displayed_value: number; database_value: number; difference: number; source: string; status: 'reconciled' | 'mismatch' }>
  charts: Array<{ chart: string; status: 'loaded' | 'empty'; chart_rows: number; nonzero: boolean; source: string; message: string }>
}

export type BusinessRecord = Record<string, string | number | boolean | null | Record<string, unknown>>

export type IntakeCategory = 'setup' | 'recurring'

export type DocumentTemplate = {
  id: string
  name: string
  description: string
  formats: Array<'pdf' | 'csv'>
  mode: 'form' | 'data'
}


export type DataQualityCheck = {
  id: string
  label: string
  status: 'pass' | 'warning' | 'fail' | string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info' | string
  detail: string
  evidence: Record<string, unknown>
  recommendation: string
}

export type DataQualityDashboard = {
  generated_at: string
  score: number
  status: 'trusted' | 'review' | 'not_ready' | string
  checks: DataQualityCheck[]
  issue_counts: Record<string, number>
  source_coverage: Array<{ label: string; received: number; total: number }>
  reconciliations: Array<{ label: string; difference: number; status: string }>
  page_readiness: Array<{
    id: string
    label: string
    status: 'ready' | 'provisional' | 'blocked' | string
    has_data: boolean
    record_count: number
    detail: string
    missing: string[]
  }>
  pages_ready: number
  pages_total: number
  open_check_total: number
  dashboard_open_checks: number
  definitions: Record<string, unknown>
}

export type WorkspaceSnapshot = {
  generated_at: string
  pipeline: PipelineStatus
  summary: Summary
  transactions: BusinessRecord[]
  validations: BusinessRecord[]
  company_profile: CompanyProfile
  accounting: AccountingDashboard
  tax: TaxDashboard
  marketing: MarketingDashboard
  inventory: InventoryDashboard
  hr: HRDashboard
  money_map: MoneyMapDashboard
  data_quality: DataQualityDashboard
  upload_library: UploadLibrary
  dashboard_integrity: DashboardIntegrity
}

export type InventoryItem = {
  sku: string
  name: string
  quantity: number
  unit_cost: number
  total_value: number
  location: string
  status: string
  source_file: string
  reorder_point: number
  target_stock: number
  lead_time_days: number
  preferred_supplier: string
  stock_state: 'healthy' | 'watch' | 'reorder' | string
  suggested_order: number
}

export type InventoryDashboard = {
  generated_at: string
  summary: {
    sku_count: number
    units_on_hand: number
    inventory_value: number
    reorder_count: number
    invoice_linked_movements: number
    auto_applied_movements: number
  }
  items: InventoryItem[]
  movements: Array<{
    movement_date: string
    sku: string
    item_name: string
    movement_type: string
    signed_quantity: number
    unit_cost: number
    source_invoice: string
    source_file: string
    evidence_mode: string
    applied_to_stock: boolean
    note: string
  }>
  value_by_category: Array<{ label: string; value: number; sku: string }>
  method: string
}

export type HREmployee = {
  employee: string
  employee_code: string
  department: string
  role_title: string
  employment_type: string
  start_date: string
  manager: string
  location: string
  status: string
  gross_pay: number
  payg_withholding: number
  superannuation: number
  expected_super: number
  super_gap: number
  net_pay: number
  currency: string
  source_file: string
  annual_leave_days: number
  personal_leave_days: number
  leave_taken_days: number
  next_review_date: string
  training: string
  training_due: string
  training_status: string
  evidence_mode: string
}

export type HRDashboard = {
  generated_at: string
  period: string
  summary: {
    headcount: number
    gross_pay: number
    net_pay: number
    payg_withholding: number
    superannuation: number
    annual_leave_days: number
    open_actions: number
  }
  employees: HREmployee[]
  department_costs: Array<{ department: string; gross_pay: number; headcount: number }>
  actions: Array<{ type: string; severity: string; employee: string; detail: string; due_date: string }>
  disclaimer: string
}

export type MoneyMapDashboard = {
  generated_at: string
  period: string
  summary: {
    revenue: number
    operating_costs: number
    profit_before_tax: number
    estimated_tax: number
    retained_profit: number
    profit_margin_pct: number
  }
  sources: Array<{ name: string; value: number }>
  departments: Array<{ name: string; value: number }>
  nodes: Array<{ name: string; group: string }>
  links: Array<{ source: number; target: number; value: number }>
  source_note: string
}

export type TaxOpportunityAnalysis = {
  generated_at: string
  obligation_snapshot: {
    estimated_taxable_income: number
    estimated_income_tax: number
    net_gst: number
    review_count: number
  }
  schemes: Array<{
    id: string
    title: string
    category: string
    source_url: string
    official_rule: string
    check: string
    status: string
    evidence: string
  }>
  official_search: {
    live: boolean
    message: string
    results: Array<{ title: string; url: string; content: string; source: string }>
  }
  scope_note: string
}

export type SemanticMetric = {
  id: string
  label: string
  family: string
  role: string
  format: string
  definition: string
  canonical_source: string
  status: 'ready' | 'provisional' | 'blocked' | string
  missing_documents: string[]
  value?: unknown
}

export type SemanticLayerStatus = {
  version: string
  root: string
  metrics: SemanticMetric[]
  dashboard: { sections: Array<Record<string, unknown>>; [key: string]: unknown }
  sources: Record<string, unknown>
  actions: Record<string, unknown>
  core_setup_complete: boolean
  quality: { score: number; status: string; open_check_total: number }
}

export type DecisionContextSource = {
  source_key: string
  upload_id: number
  filename: string
  document_type: string
  intake_category: string
  uploaded_at_utc: string
  processed_at_utc: string
  uploaded_at_local?: string
  processed_at_local?: string
  effective_date: string
  data_version: number
  freshness_state: string
  freshness_hours: number
  decision_role: string
  processing_status: string
}

export type DecisionContextNode = {
  decision_id: string
  label: string
  description: string
  readiness: string
  source_count: number
  fresh_source_count: number
  stale_source_count: number
  last_evaluated_at_utc: string
  summary: string
  decision?: Record<string, unknown>
}

export type DecisionContextDashboard = {
  version: number
  timezone: string
  current_time_utc: string
  current_time_local: string
  data_cutoff_utc: string
  data_cutoff_local: string
  last_analysis: Record<string, unknown>
  summary: {
    source_count: number
    decision_count: number
    ready_decisions: number
    provisional_decisions: number
    blocked_decisions: number
    freshness: Record<string, number>
  }
  sources: DecisionContextSource[]
  decisions: DecisionContextNode[]
  links: Array<{ decision_id: string; source_key: string; connection_role: string; reason: string }>
  analysis_history: Array<Record<string, unknown>>
  events: Array<Record<string, unknown>>
  database_file: string
  context_file: string
  decision_engine_note: string
}

export type MarketState = {
  live: boolean
  contextual?: boolean
  message: string
  signals: BusinessRecord[]
}

export type SetupStatus = Record<string, {
  ok: boolean
  detail: string
  [key: string]: unknown
}>

export type UploadResult = {
  upload_id: number
  file_id?: string
  duplicate: boolean
  filename: string
  document_type: string
  intake_category?: IntakeCategory
  detected_document_types?: string[]
  rows_imported: number
  columns: string[]
  issues: string[]
  needs_mapping: boolean
  mapping_requests?: Array<{
    sheet: string
    document_type: string
    confidence: number
    columns: string[]
    suggested_mapping: Record<string, string>
  }>
  processing?: { new: number; changed: number; unchanged: number; rejected: number }
  data_version?: number
  baseline_version?: number
  affected_metrics?: string[]
  storage?: string
  analysis?: UploadAnalysis
  assistant_message?: string
  lifecycle_phase?: string
}

export type UploadAnalysis = {
  upload_id: number
  analysed_at: string
  filename: string
  document_type: string
  declared_document_type: string
  suggested_document_type: string
  document_label: string
  intake_category: IntakeCategory
  tier: string
  lifecycle_phase: string
  is_initial_company_file: boolean
  rows_imported: number
  processing: { new?: number; changed?: number; unchanged?: number; rejected?: number }
  data_version: number
  baseline_version: number
  affected_metrics: string[]
  findings: string[]
  business_impact: string[]
  issues: string[]
  storage: string
  model_required: boolean
  analysis_method: string
}

export type UploadProcessingJob = {
  job_id: string
  filename: string
  intake_category: IntakeCategory
  declared_document_type: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  stage: string
  progress: number
  stage_message: string
  upload_id?: number
  result?: UploadResult
  analysis?: UploadAnalysis
  assistant_message?: string
  error_message?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

export type DocumentCatalogueItem = {
  id: string
  label: string
  intake_category: IntakeCategory
  tier: 'required' | 'recommended' | 'operational' | string
  description: string
  automation: string
  accepted: string[]
  received: boolean
  file_count: number
  attempt_count: number
  retry_count: number
  state: 'received' | 'needs_retry' | 'missing' | string
}

export type UploadedFileCard = {
  id: number
  filename: string
  document_type: string
  declared_document_type: string
  suggested_document_type: string
  document_label: string
  tier: string
  intake_category: IntakeCategory
  rows_imported: number
  processing_status: string
  lifecycle_phase?: string
  display_status?: string
  mapping_status: string
  mapping_confidence: number
  data_version: number
  created_at: string
  last_processed_at: string
  assistant_message: string
  analysis: UploadAnalysis | Record<string, never>
  file_size: number
}

export type UploadLibrary = {
  files: { setup: UploadedFileCard[]; recurring: UploadedFileCard[] }
  catalogue: { setup_required: DocumentCatalogueItem[]; setup_recommended: DocumentCatalogueItem[]; recurring: DocumentCatalogueItem[] }
  coverage: { required_received: string[]; required_missing: string[]; recommended_received: string[]; recommended_missing: string[]; recurring_received?: string[]; recurring_missing?: string[] }
  company_context_file: string
}

export type BusinessStoreStatus = {
  database: { file: string; engine: string; canonical: boolean }
  clippy: {
    profile: Record<string, unknown>
    summary_text: string
    summary: {
      lifecycle?: { phase?: string; setup_complete?: boolean; required_missing?: string[]; data_version?: number }
      source_count?: number
      table_count?: number
      tables_with_data?: number
      data_trust?: { score?: number; status?: string; open_checks?: number }
    }
    detail_sections: string[]
    data_version: number
    updated_at: string
    lifecycle: { phase?: string; setup_complete?: boolean; setup_completed_at?: string; data_version?: number; updated_at?: string }
  }
  sources: Array<{
    upload_id: number
    filename: string
    document_type: string
    intake_category: string
    processing_status: string
    rows_received: number
    rows_new: number
    rows_changed: number
    rows_rejected: number
    data_version: number
    uploaded_at: string
    processed_at: string
  }>
  lineage: Array<{
    event_id: string
    run_id: string
    upload_id: number
    stage_order: number
    stage: string
    operation: string
    source_name: string
    destination_name: string
    record_count: number
    status: string
    created_at: string
  }>
  catalog: Array<{ table_name: string; business_domain: string; row_count: number; description: string; updated_at: string }>
  processes: Array<{ process_id: string; process_type: string; trigger_name: string; status: string; result_summary: string; data_version: number; completed_at: string }>
}

export type CompetitorAnalysisResult = {
  generated_at: string
  company: { name: string; industry: string; location: string; score: number; dimensions: Record<string, number>; score_method: string }
  competitors: Array<{ entity: string; dimensions: Record<string, number>; verified_dimensions: number; score: number | null; status: string; evidence_summary?: string; source_title?: string; source_url?: string }>
  comparison_ready: boolean
  comparison_note: string
  positioning_chart: { title: string; dimensions: string[]; series: Array<{ entity: string; score: number | null; dimensions: Record<string, number>; verified: boolean }> }
  agent_chart_slots: Array<{
    id: string
    title: string
    chart_type: string
    reason: string
    data_requirements: string[]
    status: string
    data?: Array<{ label: string; value: number }>
    x_key?: string
    y_key?: string
    source_note?: string
  }>
  chart_planner: string
  competitive_brief?: {
    evidence_basis: string
    named_competitors: string[]
    company_strengths: string[]
    watch_items: string[]
    research_result_count: number
  }
  data_mode?: { internal: 'synthetic_demonstration' | 'uploaded_company_evidence'; external: 'current_cited_research' | 'uploaded_market_evidence_only' }
  market_signals: BusinessRecord[]
  research: { live: boolean; message: string; results: BusinessRecord[] }
  data_gaps: string[]
  summary: string
}

export type CompetitorIntelligenceStatus = {
  job: null | { job_id: string; status: string; stage: string; progress: number; stage_message: string; error_message?: string; result?: CompetitorAnalysisResult }
  result: CompetitorAnalysisResult | Record<string, never>
  context: Record<string, unknown>
  result_file: string
}

export type PipelineStatus = {
  company_id: string
  empty_mode: boolean
  data_version: number
  baseline_version: number
  uploads: number
  mapped_uploads: number
  rows_new: number
  rows_changed: number
  rows_unchanged: number
  saved_mapping_profiles: number
  document_coverage: Array<{ document_type: string; files: number; rows: number }>
  intake_categories?: Array<{ intake_category: string; files: number; rows: number }>
  recent_uploads?: BusinessRecord[]
  recent_jobs: BusinessRecord[]
  information_requests: BusinessRecord[]
  layers: Record<string, string>
}

export type AccountingDashboard = {
  summary: Record<string, number>
  accounts: BusinessRecord[]
  journals: BusinessRecord[]
  journal_lines: BusinessRecord[]
  validations: BusinessRecord[]
  invoices: BusinessRecord[]
}

export type GeneratedDocument = {
  id: string
  created_at: string
  document_type: string
  title: string
  output_format: string
  filename: string
  file_path: string
  status: string
  counterparty: string
  metadata?: Record<string, unknown>
}

export type TaxDashboard = {
  profile: Record<string, string | number | boolean>
  summary: Record<string, string | number>
  bas: Record<string, number>
  obligations: BusinessRecord[]
  opportunities: BusinessRecord[]
  internet: {
    mode: string
    official_sources_enabled: boolean
    supplier_enrichment_enabled: boolean
    ato_sbr_enabled: boolean
    ato_sbr_status: string
    last_verified: string
    sources: Array<{ title: string; url: string; purpose: string }>
  }
  reconciliation: Record<string, number>
}

export type IntegrationSettings = {
  mode: 'offline' | 'official_only' | 'enrichment' | 'connected'
  official_tax_sources: boolean
  supplier_enrichment: boolean
  bank_feeds: boolean
  email_intake: boolean
  cloud_storage: boolean
  ato_sbr?: boolean
  external_processing_consent: boolean
}

export type MarketingDashboard = {
  mode: 'actual' | 'demonstration'
  disclaimer: string
  summary: {
    revenue: number
    marketing_spend: number
    spend_to_revenue_pct: number
    attributed_revenue: number
    roas: number
    channels: number
  }
  channels: Array<{
    channel: string
    spend: number
    share: number
    attributed_revenue: number
    roas: number
    status: string
  }>
  performance_mode?: 'trend' | 'current_period'
  performance: Array<{ month?: string; revenue?: number; marketing_spend?: number; metric?: string; period?: string; value?: number }>
  recommendations: string[]
}

export type AgentContextStatus = {
  base_personality_file: string
  base_personality_present: boolean
  working_context_file: string
  working_context_events: number
  working_context_updated_at: string
  company_context_file?: string
  company_context_present?: boolean
  market_intelligence_file?: string
  market_intelligence_status?: string
  temporal_decision_context_file?: string
  temporal_decision_database_file?: string
  temporal_context_present?: boolean
  base_is_preserved_on_clear: boolean
}


export type FolderIntakeStatus = {
  enabled: boolean
  paths: { root: string; setup: string; recurring: string; archive: string }
  scan_seconds: number
  pending: { setup: string[]; recurring: string[]; total: number }
  last_scan_at: string
  last_result: { queued: Array<Record<string, unknown>>; errors: Array<Record<string, unknown>> }
}

export type ClassificationRepairStatus = {
  plan: Array<{
    upload_id: number
    filename: string
    current_document_type: string
    expected_document_type: string
    current_intake_category: IntakeCategory
    expected_intake_category: IntakeCategory
    processing_status: string
    action: string
    reason: string
  }>
}
