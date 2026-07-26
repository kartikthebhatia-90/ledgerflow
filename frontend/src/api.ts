import type { AccountingDashboard, AgentContextStatus, AgentResponse, AssistantProfile, BusinessRecord, BusinessStoreStatus, ClassificationRepairStatus, CompanyProfile, CompetitorIntelligenceStatus, DashboardIntegrity, DocumentTemplate, FolderIntakeStatus, GeneratedDocument, HRDashboard, IntakeCategory, IntegrationSettings, InventoryDashboard, MarketingDashboard, MarketState, MoneyMapDashboard, DataQualityDashboard, SemanticLayerStatus, DecisionContextDashboard, PipelineStatus, SetupStatus, Summary, TaxDashboard, TaxOpportunityAnalysis, UploadLibrary, UploadProcessingJob, Workspace, WorkspaceSnapshot } from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, options)
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    throw new Error(`LedgerFlow API is not reachable for ${url}. Start the app once and wait for the health-gated browser window. ${detail}`)
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string; error?: string; endpoint?: string }
    const detail = payload.detail || payload.error || response.statusText || 'Unknown server error'
    const endpoint = payload.endpoint || url
    throw new Error(`${endpoint} returned ${response.status}: ${detail}`)
  }
  return response.json() as Promise<T>
}

async function requestDownload(url: string, options?: RequestInit): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(url, options)
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string; error?: string; endpoint?: string }
    const detail = payload.detail || payload.error || response.statusText || 'Unknown server error'
    const endpoint = payload.endpoint || url
    throw new Error(`${endpoint} returned ${response.status}: ${detail}`)
  }
  const disposition = response.headers.get('Content-Disposition') || ''
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || 'ledgerflow_document'
  return { blob: await response.blob(), filename }
}

export const api = {
  health: () => request<{ ok: boolean; app: string; version: string }>('/api/health'),
  pipelineStatus: () => request<PipelineStatus>('/api/pipeline/status'),
  rebuildPipeline: (forceFullBaseline = true) => request<Record<string, unknown>>('/api/pipeline/rebuild', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_full_baseline: forceFullBaseline }),
  }),
  marketContext: () => request<{ profile: Record<string, unknown>; snapshot: Record<string, unknown> }>('/api/context/market'),
  informationRequests: () => request<{ records: BusinessRecord[] }>('/api/context/information-requests'),
  clearData: (scope: 'company' | 'memory' | 'market' | 'all', createBackup: boolean, confirmation: string) => request<Record<string, unknown>>('/api/data/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, create_backup: createBackup, confirmation }),
  }),
  summary: () => request<Summary>('/api/dashboard/summary'),
  workspaceSnapshot: () => request<WorkspaceSnapshot>('/api/dashboard/workspace'),
  verifyDashboard: () => request<DashboardIntegrity>('/api/dashboard/verify', { method: 'POST' }),
  businessStoreStatus: () => request<BusinessStoreStatus>('/api/business-store/status'),
  refreshBusinessStore: () => request<BusinessStoreStatus>('/api/business-store/refresh', { method: 'POST' }),
  dataQuality: () => request<DataQualityDashboard>('/api/analytics/data-quality'),
  semanticLayer: () => request<SemanticLayerStatus>('/api/analytics/semantic-layer'),
  decisionContext: () => request<DecisionContextDashboard>('/api/decision-context'),
  refreshDecisionContext: () => request<DecisionContextDashboard>('/api/decision-context/refresh', { method: 'POST' }),
  assetsLiabilities: () => request<{ records: BusinessRecord[] }>('/api/data/assets-liabilities'),
  invoices: () => request<{ records: BusinessRecord[] }>('/api/data/invoices'),
  transactions: () => request<{ records: BusinessRecord[] }>('/api/data/transactions'),
  validations: () => request<{ records: BusinessRecord[] }>('/api/validations'),
  refreshValidations: () => request<{ records: BusinessRecord[]; issue_count: number }>('/api/validations/refresh', { method: 'POST' }),
  market: () => request<MarketState>('/api/market/signals'),
  research: (query: string) => request<{ live: boolean; message: string; results: BusinessRecord[] }>('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  }),
  setupStatus: () => request<SetupStatus>('/api/setup/status'),
  companyProfile: () => request<CompanyProfile>('/api/company/profile'),
  saveCompanyProfile: (profile: CompanyProfile) => request<{ ok: boolean; profile: CompanyProfile }>('/api/company/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  }),
  approvals: () => request<{ records: BusinessRecord[] }>('/api/approvals'),
  resolveApproval: (id: number, decision: 'approved' | 'rejected', note = '') => request<{ records: BusinessRecord[] }>(`/api/approvals/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note }),
  }),
  memory: () => request<Record<string, unknown>>('/api/memory'),
  clearMemory: () => request<{ ok: boolean }>('/api/memory', { method: 'DELETE' }),
  command: (message: string, workspace: Workspace) => request<AgentResponse>('/api/agent/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, workspace }),
  }),
  startUpload: async (file: File, intakeCategory: IntakeCategory = 'recurring', declaredDocumentType = 'auto') => {
    const data = new FormData()
    data.append('file', file)
    data.append('intake_category', intakeCategory)
    data.append('declared_document_type', declaredDocumentType)
    return request<UploadProcessingJob>('/api/upload/start', { method: 'POST', body: data })
  },
  uploadJob: (jobId: string) => request<UploadProcessingJob>(`/api/upload/jobs/${encodeURIComponent(jobId)}`),
  uploadLibrary: () => request<UploadLibrary>('/api/uploads/library'),
  folderIntakeStatus: () => request<FolderIntakeStatus>('/api/folder-intake/status'),
  scanFolderIntake: () => request<Record<string, unknown>>('/api/folder-intake/scan', { method: 'POST' }),
  classificationRepairStatus: () => request<ClassificationRepairStatus>('/api/uploads/classification-repair'),
  runClassificationRepair: () => request<Record<string, unknown>>('/api/uploads/classification-repair', { method: 'POST' }),
  moveUpload: (uploadId: number, intakeCategory: IntakeCategory) => request<Record<string, unknown>>(`/api/uploads/${uploadId}/category`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intake_category: intakeCategory }),
  }),
  deleteUpload: (uploadId: number, createBackup: boolean, confirmation: string) => request<Record<string, unknown>>(`/api/uploads/${uploadId}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ create_backup: createBackup, confirmation }),
  }),
  retryUpload: (uploadId: number, intakeCategory: IntakeCategory, declaredDocumentType: string) => request<UploadProcessingJob>(`/api/uploads/${uploadId}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intake_category: intakeCategory, declared_document_type: declaredDocumentType }),
  }),
  competitorIntelligence: () => request<CompetitorIntelligenceStatus>('/api/intelligence/competitors'),
  startCompetitorIntelligence: () => request<Record<string, unknown> & { job_id: string; status: string; stage: string; progress: number; stage_message: string }>('/api/intelligence/competitors/start', { method: 'POST' }),
  documentTemplates: () => request<{ records: DocumentTemplate[] }>('/api/document-templates'),
  generatedDocuments: () => request<{ records: GeneratedDocument[] }>('/api/documents'),
  accountsDashboard: () => request<AccountingDashboard>('/api/accounts/dashboard'),
  resolveInvoiceCategorisation: (invoiceId: string, accountCode: string, taxCode: string, remember = true, note = '') => request<AccountingDashboard>(`/api/accounts/invoices/${encodeURIComponent(invoiceId)}/categorisation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account_code: accountCode, tax_code: taxCode, remember, note }),
  }),
  taxDashboard: () => request<TaxDashboard>('/api/tax/dashboard'),
  marketingDashboard: () => request<MarketingDashboard>('/api/marketing/dashboard'),
  inventoryDashboard: () => request<InventoryDashboard>('/api/inventory/dashboard'),
  syncInventory: () => request<InventoryDashboard>('/api/inventory/sync', { method: 'POST' }),
  hrDashboard: () => request<HRDashboard>('/api/hr/dashboard'),
  moneyMapDashboard: () => request<MoneyMapDashboard>('/api/money-map/dashboard'),
  analyseTaxOpportunities: () => request<TaxOpportunityAnalysis>('/api/tax/opportunities/analyse', { method: 'POST' }),
  testModel: () => request<Record<string, unknown>>('/api/setup/test-model', { method: 'POST' }),
  assistantProfile: () => request<AssistantProfile>('/api/agent/profile'),
  saveAssistantProfile: (profile: Partial<AssistantProfile>) => request<AssistantProfile>('/api/agent/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  }),
  agentContext: () => request<AgentContextStatus>('/api/agent/context'),
  clearAgentContext: () => request<AgentContextStatus & { ok: boolean }>('/api/agent/context', { method: 'DELETE' }),
  taxWorkpaper: (outputFormat: 'pdf' | 'csv') => requestDownload(`/api/tax/workpaper?output_format=${outputFormat}`),
  integrationSettings: () => request<IntegrationSettings>('/api/integrations/settings'),
  saveIntegrationSettings: (settings: IntegrationSettings) => request<IntegrationSettings>('/api/integrations/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  }),
  generateDocument: (documentType: string, outputFormat: 'pdf' | 'csv', fields: Record<string, unknown>) => requestDownload('/api/documents/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_type: documentType, output_format: outputFormat, fields }),
  }),
  mapUpload: (uploadId: number, documentType: string, mapping: Record<string, string>) => request<Record<string, unknown>>(`/api/uploads/${uploadId}/map`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_type: documentType, mapping }),
  }),
  testOllama: () => request<Record<string, unknown>>('/api/setup/test-ollama', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  }),
  testSearch: () => request<Record<string, unknown>>('/api/setup/test-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  }),
}
