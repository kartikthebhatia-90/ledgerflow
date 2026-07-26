import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpRight,
  BookOpenCheck,
  Bot,
  BrainCircuit,
  Building2,
  Calculator,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleDollarSign,
  CloudCog,
  Clock3,
  Database,
  ExternalLink,
  GitBranch,
  FileCheck2,
  FileSpreadsheet,
  Files,
  Gauge,
  Landmark,
  Layers3,
  LoaderCircle,
  Megaphone,
  PackageSearch,
  Play,
  ReceiptText,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Search,
  Sparkles,
  Target,
  Trash2,
  UploadCloud,
  UsersRound,
  WalletCards,
  Waypoints,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Sankey,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type {
  AccountingDashboard,
  AgentContextStatus,
  BusinessRecord,
  BusinessStoreStatus,
  CompanyProfile,
  CompetitorIntelligenceStatus,
  DocumentCatalogueItem,
  DocumentTemplate,
  FolderIntakeStatus,
  ClassificationRepairStatus,
  DataQualityDashboard,
  DashboardIntegrity,
  SemanticLayerStatus,
  DecisionContextDashboard,
  GeneratedDocument,
  HRDashboard,
  IntakeCategory,
  InventoryDashboard,
  MarketingDashboard,
  MoneyMapDashboard,
  PipelineStatus,
  SetupStatus,
  Summary,
  TaxDashboard,
  TaxOpportunityAnalysis,
  UploadLibrary,
  UploadProcessingJob,
  UploadResult,
  Workspace,
} from './types'

type Props = {
  activeSection: Workspace
  summary: Summary | null
  accounting: AccountingDashboard | null
  tax: TaxDashboard | null
  marketing: MarketingDashboard | null
  inventory: InventoryDashboard | null
  hr: HRDashboard | null
  moneyMap: MoneyMapDashboard | null
  transactions: BusinessRecord[]
  validations: BusinessRecord[]
  pipelineStatus: PipelineStatus | null
  generatedDocuments: GeneratedDocument[]
  companyProfile: CompanyProfile | null
  setupStatus: SetupStatus | null
  agentContext: AgentContextStatus | null
  uploadLibrary: UploadLibrary | null
  intelligence: CompetitorIntelligenceStatus | null
  processingActivity: UploadProcessingJob | null
  folderIntake: FolderIntakeStatus | null
  classificationRepair: ClassificationRepairStatus | null
  dataQuality: DataQualityDashboard | null
  dashboardIntegrity: DashboardIntegrity | null
  semanticLayer: SemanticLayerStatus | null
  decisionContext: DecisionContextDashboard | null
  businessStore: BusinessStoreStatus | null
  highlighted: string[]
  spotlight: string
  loading: boolean
  onSectionChange: (section: Workspace) => void
  onUpload: (file: File, intakeCategory: IntakeCategory, declaredDocumentType: string) => Promise<UploadResult>
  onGetDocumentTemplates: () => Promise<DocumentTemplate[]>
  onGenerateDocument: (documentType: string, outputFormat: 'pdf' | 'csv', fields: Record<string, unknown>) => Promise<{ blob: Blob; filename: string }>
  onRefreshDocuments: () => Promise<GeneratedDocument[]>
  onDownloadTaxWorkpaper: (format: 'pdf' | 'csv') => Promise<void>
  onAnalyseTaxOpportunities: () => Promise<TaxOpportunityAnalysis>
  onRefresh: () => Promise<void>
  onVerifyDashboard: () => Promise<void>
  onTestModel: () => Promise<Record<string, unknown>>
  onClearAgentContext: () => Promise<void>
  onMoveUpload: (uploadId: number, intakeCategory: IntakeCategory) => Promise<void>
  onDeleteUpload: (uploadId: number, createBackup: boolean, confirmation: string) => Promise<void>
  onRetryUpload: (uploadId: number, intakeCategory: IntakeCategory, declaredDocumentType: string) => Promise<UploadResult>
  onScanFolderIntake: () => Promise<void>
  onRepairClassifications: () => Promise<void>
  onResetAllData: (createBackup: boolean, confirmation: string) => Promise<void>
  onStartCompetitorAnalysis: () => Promise<unknown>
  onRefreshDecisionContext: () => Promise<void>
}

const money = (value: unknown) => new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  maximumFractionDigits: 0,
}).format(Number(value || 0))

const number = (value: unknown, digits = 1) => Number(value || 0).toFixed(digits)

function downloadBlob(download: { blob: Blob; filename: string }) {
  const url = URL.createObjectURL(download.blob)
  const link = document.createElement('a')
  link.href = url
  link.download = download.filename
  link.click()
  URL.revokeObjectURL(url)
}

const chartColors = {
  revenue: 'var(--chart-revenue)',
  expenses: 'var(--chart-expenses)',
  cash: 'var(--chart-cash)',
  bar: 'var(--chart-bar)',
  barAlt: 'var(--chart-bar-2)',
  alert: 'var(--chart-alert)',
  good: 'var(--chart-good)',
  competitor: 'var(--chart-competitor)',
}

function SectionHeading({ eyebrow, title, description, icon: Icon }: { eyebrow: string; title: string; description: string; icon: typeof Gauge }) {
  return (
    <div className="scroll-section-heading compact-section-heading">
      <div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>
      <div className="section-heading-icon"><Icon /></div>
    </div>
  )
}

function MetricCard({ label, value, note, icon: Icon, id, tone = 'neutral' }: { label: string; value: string; note: string; icon: typeof Gauge; id?: string; tone?: string }) {
  return (
    <motion.article id={id} className={`metric-card metric-${tone}`} whileHover={{ y: -4 }}>
      <div className="metric-icon"><Icon size={20} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </motion.article>
  )
}

function DashboardIntegrityPanel({ integrity, onVerify, compact = false }: { integrity: DashboardIntegrity | null; onVerify: Props['onVerifyDashboard']; compact?: boolean }) {
  const [verifying, setVerifying] = useState(false)
  const run = async () => {
    setVerifying(true)
    try { await onVerify() } finally { setVerifying(false) }
  }
  return (
    <article className={`dashboard-integrity-card ${compact ? 'integrity-compact' : ''} ${integrity?.all_reconciled ? 'integrity-good' : 'integrity-warning'}`}>
      <div className="integrity-summary">
        {integrity?.all_reconciled ? <ShieldCheck /> : <AlertTriangle />}
        <span>
          <small>Chart ↔ business.db verification</small>
          <strong>{integrity?.message || 'Verification will run when the dashboard loads.'}</strong>
          {integrity && <small>{integrity.source_counts.business_source_registry || 0} source file(s) · {integrity.source_counts.journal_lines || 0} ledger line(s) · {integrity.source_counts.statement_snapshots || 0} statement row(s)</small>}
        </span>
        <button onClick={() => void run()} disabled={verifying}>{verifying ? <LoaderCircle className="spin" /> : <RefreshCw />} Verify and reload</button>
      </div>
      {!compact && <>
        <div className="chart-integrity-grid">{(integrity?.charts || []).map((chart) => <div key={chart.chart} className={`chart-integrity-${chart.status}`}>{chart.status === 'loaded' ? <CheckCircle2 /> : <AlertTriangle />}<span><strong>{chart.chart}</strong><small>{chart.chart_rows} plotted row(s) · {chart.source}</small></span><b>{chart.status}</b></div>)}</div>
        <details className="integrity-details"><summary>Show database reconciliation checks</summary><div>{(integrity?.checks || []).map((check) => <div key={check.metric}><span><strong>{check.metric}</strong><small>{check.source}</small></span><span><b>{number(check.displayed_value, 2)}</b><small>DB {number(check.database_value, 2)} · difference {number(check.difference, 2)}</small></span><em>{check.status}</em></div>)}</div></details>
      </>}
    </article>
  )
}

function OverviewSection({ summary, dataQuality, intelligence, dashboardIntegrity, onVerifyDashboard }: { summary: Summary; dataQuality: DataQualityDashboard | null; intelligence: CompetitorIntelligenceStatus | null; dashboardIntegrity: DashboardIntegrity | null; onVerifyDashboard: Props['onVerifyDashboard']; validations: BusinessRecord[]; transactions: BusinessRecord[] }) {
  const chartData = summary.performance_series.map((row) => ({ ...row, label: row.month }))
  const positionData = summary.position_series || []
  const profitData = summary.profit_structure?.series || []
  const exposureData = summary.invoice_exposure_series || []
  const cycleData = [
    { label: 'Receivable days', value: summary.receivable_days },
    { label: 'Payable days', value: summary.payable_days },
    { label: 'Cash runway', value: summary.cash_runway_days },
  ]
  const rawIntelligence = intelligence?.result
  const intelligenceResult = rawIntelligence && typeof rawIntelligence === 'object' && 'company' in rawIntelligence ? rawIntelligence : null
  const brief = intelligenceResult?.competitive_brief
  const briefStrengths = brief?.company_strengths || [
    `Liquidity: ${summary.current_ratio == null ? 'not available' : `${number(summary.current_ratio, 2)} current ratio`}`,
    `Cash resilience: ${summary.cash_runway_days} estimated runway days`,
  ]
  const briefWatchItems = brief?.watch_items?.length
    ? brief.watch_items
    : [
        `${dataQuality?.open_check_total || 0} data or reconciliation checks remain open`,
        summary.receivable_days > summary.payable_days ? 'Receivables are converting slower than supplier obligations' : 'Working-capital timing is currently balanced',
      ]
  return (
    <section id="section-overview" data-section="overview" className="scroll-dashboard-section overview-section analytics-only-overview">
      <div id="overview-dashboard" className="section-inner">
        <div className="analytics-overview-intro"><span className="eyebrow">Live business analytics · build 3.3.1</span><small>{summary.company.company_name || 'Current company'} · verified local evidence</small></div>
        <div id="overview-metric-grid" className="metric-grid metric-grid-four">
          <MetricCard label="Cash" value={money(summary.cash)} note={`${summary.cash_runway_days} estimated runway days`} icon={CircleDollarSign} tone={summary.cash_runway_days < summary.cash_runway_target_days ? 'warn' : 'good'} />
          <MetricCard id="current-ratio-card" label="Current ratio" value={summary.current_ratio == null ? '—' : number(summary.current_ratio, 2)} note={`Target ${number(summary.current_ratio_target, 2)}`} icon={Gauge} tone={(summary.current_ratio || 0) < summary.current_ratio_target ? 'warn' : 'good'} />
          <MetricCard label={summary.metric_sources?.revenue_expenses === 'transactions' ? 'Monthly inflows' : 'Latest statement inflows'} value={money(summary.revenue_month)} note={`${number(summary.revenue_change)}% period change · ${summary.metric_sources?.revenue_expenses || 'business data'}`} icon={ArrowUpRight} tone="good" />
          <MetricCard label="Open checks" value={String(dataQuality?.open_check_total ?? summary.critical_alerts ?? 0)} note={`${summary.anomaly_count} anomalous transactions · all review queues`} icon={AlertTriangle} tone={(dataQuality?.open_check_total ?? summary.critical_alerts ?? 0) ? 'warn' : 'good'} />
          <MetricCard label="Data trust" value={`${dataQuality?.score ?? 0}/100`} note={dataQuality?.status === 'trusted' ? 'Sources reconcile' : `${dataQuality?.open_check_total ?? 0} checks need review`} icon={ShieldCheck} tone={dataQuality?.status === 'trusted' ? 'good' : 'warn'} />
        </div>
        <article id="clippy-overview-brief" className="glass-card overview-brief-card">
          <div className="overview-brief-heading"><div><span className="eyebrow">Clippy’s business brief</span><h3>{intelligenceResult ? 'Financial position and competitive context' : 'Financial position and immediate priorities'}</h3></div><Bot /></div>
          <p>{intelligenceResult?.summary || `Cash is ${money(summary.cash)}, the current ratio is ${summary.current_ratio == null ? 'not available' : number(summary.current_ratio, 2)}, and monthly inflows are ${money(summary.revenue_month)}. Run Intelligence to add a source-backed competitor view.`}</p>
          <div className="overview-brief-grid">
            <div><strong>What is working</strong>{briefStrengths.slice(0, 3).map((item) => <span key={item}><CheckCircle2 />{item}</span>)}</div>
            <div><strong>What needs attention</strong>{briefWatchItems.slice(0, 3).map((item) => <span key={item}><AlertTriangle />{item}</span>)}</div>
            <div><strong>Evidence status</strong><span><ShieldCheck />{dataQuality?.score ?? 0}/100 data trust</span><span><BrainCircuit />{intelligenceResult ? `${intelligenceResult.competitors.length} competitor evidence record(s)` : 'Competitive analysis not yet run'}</span></div>
          </div>
          {intelligenceResult?.data_mode?.internal === 'synthetic_demonstration' && <small className="brief-caveat">Internal figures are synthetic demonstration data; current external research is kept separate.</small>}
        </article>
        <DashboardIntegrityPanel integrity={dashboardIntegrity} onVerify={onVerifyDashboard} />
        <div className="analytics-chart-grid">
          <article id="overview-performance-chart" className="glass-card analytics-chart-card">
            <div className="card-heading"><div><span className="eyebrow">Operating movement</span><h3>Inflows versus outflows</h3></div><ChartNoAxesCombined /></div>
            <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Area type="monotone" dataKey="revenue" stroke={chartColors.revenue} fill={chartColors.revenue} fillOpacity={0.18} strokeWidth={2.5} /><Line type="monotone" dataKey="expenses" stroke={chartColors.expenses} strokeWidth={2.25} dot={false} /></AreaChart></ResponsiveContainer></div>
          </article>
          <article id="overview-cash-forecast-chart" className="glass-card analytics-chart-card">
            <div className="card-heading"><div><span className="eyebrow">Cash outlook</span><h3>Now to 90 days</h3></div><WalletCards /></div>
            <div id="cash-flow-chart" className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={summary.cash_series}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Line type="monotone" dataKey="forecast" stroke={chartColors.cash} strokeWidth={3} /></LineChart></ResponsiveContainer></div>
            <small className="chart-explanation">Projected low point: {money(summary.forecast_low_point)}. {summary.forecast_method}</small>
          </article>
          <article id="overview-position-chart" className="glass-card analytics-chart-card">
            <div className="card-heading"><div><span className="eyebrow">Financial position</span><h3>Assets and liabilities</h3></div><Landmark /></div>
            <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={positionData} margin={{ left: 8, right: 8 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" interval={0} angle={-18} textAnchor="end" height={70} /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="value" fill={chartColors.bar} radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </article>
          <article id="overview-profit-chart" className="glass-card analytics-chart-card">
            <div className="card-heading"><div><span className="eyebrow">Profit structure</span><h3>Latest uploaded P&amp;L</h3></div><CircleDollarSign /></div>
            <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={profitData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" interval={0} angle={-15} textAnchor="end" height={65} /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="value" fill={chartColors.bar} radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div>
            <small className="chart-explanation">Period ending {summary.profit_structure?.period_end || 'not available'} · net {money(summary.profit_structure?.profit || 0)}</small>
          </article>
          <article id="overview-working-capital-chart" className="glass-card analytics-chart-card">
            <div className="card-heading"><div><span className="eyebrow">Working-capital cycle</span><h3>Collection, payment and runway days</h3></div><RefreshCw /></div>
            <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={cycleData} layout="vertical" margin={{ left: 18, right: 24 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis dataKey="label" type="category" width={110} /><Tooltip formatter={(value) => `${Number(value)} days`} /><Bar dataKey="value" fill={chartColors.barAlt} radius={[0, 8, 8, 0]} /></BarChart></ResponsiveContainer></div>
            <small className="chart-explanation">The three measures use different business grains and are shown together only as an operating-cycle diagnostic.</small>
          </article>
          <article id="overview-invoice-chart" className="glass-card analytics-chart-card analytics-chart-wide">
            <div className="card-heading"><div><span className="eyebrow">Invoice exposure</span><h3>Open and overdue balances</h3></div><ReceiptText /></div>
            <div className="chart-frame compact-chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={exposureData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="open" fill={chartColors.good} radius={[8, 8, 0, 0]} /><Bar dataKey="overdue" fill={chartColors.alert} radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </article>
        </div>
      </div>
    </section>
  )
}

function DocumentRail({ templatesLoader, generate, documents, refreshDocuments }: { templatesLoader: Props['onGetDocumentTemplates']; generate: Props['onGenerateDocument']; documents: GeneratedDocument[]; refreshDocuments: Props['onRefreshDocuments'] }) {
  const [templates, setTemplates] = useState<DocumentTemplate[]>([])
  const [templateId, setTemplateId] = useState('management_summary')
  const [format, setFormat] = useState<'pdf' | 'csv'>('pdf')
  const [counterparty, setCounterparty] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')

  useEffect(() => {
    void templatesLoader().then((records) => {
      setTemplates(records)
      if (records.length && !records.some((item) => item.id === templateId)) setTemplateId(records[0].id)
    })
  }, [templatesLoader, templateId])

  const selected = templates.find((item) => item.id === templateId)
  useEffect(() => {
    if (selected && !selected.formats.includes(format)) setFormat(selected.formats[0])
  }, [selected, format])

  const create = async () => {
    if (!selected) return
    setBusy(true)
    setStatus('Creating a reviewable draft…')
    try {
      const output = await generate(selected.id, format, { counterparty, description, unit_price: amount, amount, quantity: 1, tax_rate: 10 })
      downloadBlob(output)
      await refreshDocuments()
      setStatus(`${output.filename} created and saved to the local document register.`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Document generation failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside id="document-generator-rail" className="glass-card document-side-rail">
      <div className="card-heading"><div><span className="eyebrow">Generate files</span><h3>Document rail</h3></div><Files /></div>
      <label>Document<select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>{templates.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <div className="segmented-control">{selected?.formats.map((item) => <button key={item} className={format === item ? 'active' : ''} onClick={() => setFormat(item)}>{item.toUpperCase()}</button>)}</div>
      {selected?.mode === 'form' && <>
        <label>Counterparty<input value={counterparty} onChange={(event) => setCounterparty(event.target.value)} /></label>
        <label>Description<input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <label>Amount<input type="number" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
      </>}
      <button className="primary-button wide-button" onClick={() => void create()} disabled={busy || !selected}>{busy ? <LoaderCircle className="spin" /> : <FileSpreadsheet />} Create {format.toUpperCase()}</button>
      <p className="soft-note rail-note">{status || selected?.description}</p>
      <div className="recent-documents">
        <span>Recent files</span>
        {documents.slice(0, 4).map((item) => <a key={item.id} href={`/api/documents/${encodeURIComponent(item.id)}/download`}><FileSpreadsheet size={14} /><div><strong>{item.title}</strong><small>{item.output_format.toUpperCase()}</small></div><ArrowDownToLine size={14} /></a>)}
      </div>
    </aside>
  )
}

function AccountsSection({ summary, accounting, dashboardIntegrity, onVerifyDashboard, templatesLoader, generate, documents, refreshDocuments, highlighted }: { summary: Summary; accounting: AccountingDashboard; dashboardIntegrity: DashboardIntegrity | null; onVerifyDashboard: Props['onVerifyDashboard']; templatesLoader: Props['onGetDocumentTemplates']; generate: Props['onGenerateDocument']; documents: GeneratedDocument[]; refreshDocuments: Props['onRefreshDocuments']; highlighted: string[] }) {
  const ratios = [
    { label: 'Current ratio', value: summary.current_ratio == null ? '—' : number(summary.current_ratio, 2), note: `${money(summary.current_assets)} / ${money(summary.current_liabilities)}` },
    { label: 'Quick ratio', value: summary.quick_ratio == null ? '—' : number(summary.quick_ratio, 2), note: 'Liquidity excluding inventory' },
    { label: 'Debt to assets', value: summary.debt_to_assets == null ? '—' : `${number(summary.debt_to_assets * 100)}%`, note: 'Liability load against assets' },
    { label: 'Working capital', value: money(summary.working_capital), note: 'Current assets less liabilities' },
  ]
  return (
    <section id="section-accounts" data-section="accounts" className="scroll-dashboard-section accounts-section">
      <div className="section-inner">
        <SectionHeading eyebrow="Accounting control room" title="Ratios, accounts and evidence in one connected view" description="Posted balances drive the ratios. Draft journals and low-confidence classifications stay visible but do not silently alter final reporting." icon={BookOpenCheck} />
        <DashboardIntegrityPanel integrity={dashboardIntegrity} onVerify={onVerifyDashboard} compact />
        <div className="accounts-layout">
          <div className="accounts-main-column">
            <div className="ratio-ribbon">{ratios.map((item, index) => <article id={index === 0 ? 'current-ratio-card' : undefined} key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.note}</small></article>)}</div>
            <article id="accounts-table" className="glass-card accounts-table-card">
              <div className="card-heading"><div><span className="eyebrow">Chart of accounts and trial balance</span><h3>Account register</h3></div><Landmark /></div>
              <div className="table-shell premium-table-shell">
                <table>
                  <thead><tr><th>Code</th><th>Account</th><th>Type</th><th>Debits</th><th>Credits</th><th>Balance</th></tr></thead>
                  <tbody>{accounting.accounts.map((account) => (
                    <tr key={String(account.code)} className={highlighted.includes(String(account.code)) ? 'agent-highlight-row' : ''}>
                      <td><span className="account-code">{String(account.code)}</span></td>
                      <td><strong>{String(account.name)}</strong><small>{String(account.subtype)}</small></td>
                      <td><span className="status-pill">{String(account.account_type)}</span></td>
                      <td>{money(account.debits)}</td><td>{money(account.credits)}</td><td className={Number(account.balance || 0) < 0 ? 'negative' : 'positive'}><strong>{money(account.balance)}</strong></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </article>
            <div className="accounts-lower-grid">
              <article id="journal-register" className="glass-card compact-register"><div className="card-heading"><div><span className="eyebrow">Journal register</span><h3>Recent entries</h3></div><ReceiptText /></div>{accounting.journals.slice(0, 6).map((item) => <div key={String(item.id)}><span><strong>{String(item.reference || item.id)}</strong><small>{String(item.description)}</small></span><span><b>{money(item.debit_total)}</b><small>{String(item.status)}</small></span></div>)}</article>
              <article id="accounts-validation" className="glass-card compact-register"><div className="card-heading"><div><span className="eyebrow">Human validation</span><h3>Items needing review</h3></div><AlertTriangle /></div>{accounting.validations.slice(0, 6).map((item, index) => <div key={String(item.id || index)}><span><strong>{String(item.task_type || item.invoice_id || 'Review')}</strong><small>{String(item.reason || item.note || 'Confirm account and GST treatment')}</small></span><span><b>{number(item.confidence, 0)}%</b><small>{String(item.status)}</small></span></div>)}{!accounting.validations.length && <div className="empty-state"><CheckCircle2 /><span>No account validation tasks.</span></div>}</article>
            </div>
          </div>
          <DocumentRail templatesLoader={templatesLoader} generate={generate} documents={documents} refreshDocuments={refreshDocuments} />
        </div>
      </div>
    </section>
  )
}

function TaxSection({ tax, onDownload, onAnalyse }: { tax: TaxDashboard; onDownload: Props['onDownloadTaxWorkpaper']; onAnalyse: Props['onAnalyseTaxOpportunities'] }) {
  const basEntries = Object.entries(tax.bas)
  const taxableProfit = tax.summary.estimated_taxable_income ?? tax.summary.accounting_profit ?? 0
  const [analysis, setAnalysis] = useState<TaxOpportunityAnalysis | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const analyse = async () => {
    setAnalysing(true)
    setAnalysisError('')
    try {
      setAnalysis(await onAnalyse())
      window.setTimeout(() => document.getElementById('tax-opportunity-review')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : 'The tax opportunity review could not be completed.')
    } finally {
      setAnalysing(false)
    }
  }
  return (
    <section id="section-tax" data-section="tax" className="scroll-dashboard-section tax-section">
      <div id="tax-summary" className="section-inner">
        <SectionHeading eyebrow="Australian tax and compliance" title="Know the estimated obligation and the evidence behind it" description="Posted journals are preferred. When they are unavailable, the latest Profit and Loss snapshot is shown provisionally and remains accountant-review required." icon={Calculator} />
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Taxable profit" value={money(taxableProfit)} note={String(tax.summary.profit_basis || 'Indicative accounting basis')} icon={CircleDollarSign} />
          <MetricCard label="Income tax estimate" value={money(tax.summary.estimated_income_tax)} note={`${number(tax.profile.income_tax_rate)}% configured rate`} icon={Calculator} tone="warn" />
          <MetricCard label="Net GST" value={money(tax.summary.net_gst)} note="GST payable less receivable" icon={Landmark} tone={Number(tax.summary.net_gst || 0) > 0 ? 'warn' : 'good'} />
          <MetricCard label="Review exceptions" value={String(tax.summary.review_count || 0)} note="Evidence or coding checks" icon={ShieldCheck} />
        </div>
        <div className="tax-dashboard-grid">
          <article className="glass-card bas-card"><div className="card-heading"><div><span className="eyebrow">BAS-style preview</span><h3>Reporting labels</h3></div><FileSpreadsheet /></div><div className="bas-grid">{basEntries.map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{money(value)}</strong></div>)}</div><div className="tax-actions"><button className="primary-button" onClick={() => void onDownload('pdf')}><ArrowDownToLine /> PDF workpaper</button><button className="secondary-button" onClick={() => void onDownload('csv')}><ArrowDownToLine /> CSV workpaper</button></div></article>
          <article className="glass-card obligation-card"><div className="card-heading"><div><span className="eyebrow">Responsibility map</span><h3>Obligations</h3></div><ShieldCheck /></div>{tax.obligations.map((item, index) => <div key={String(item.id || index)}><span className="obligation-state">{String(item.status || 'review')}</span><div><strong>{String(item.title || item.name || item.obligation)}</strong><p>{String(item.description || item.detail || item.action || '')}</p></div></div>)}</article>
        </div>
        <article className="tax-opportunity-strip"><span>Review opportunities</span>{tax.opportunities.slice(0, 4).map((item, index) => <div key={String(item.id || index)}><Sparkles size={15} /><p>{String(item.title || item.description || item.opportunity)}</p></div>)}</article>
        <article id="tax-opportunity-review" className="glass-card tax-opportunity-review">
          <div className="card-heading">
            <div>
              <span className="eyebrow">Official-source opportunity review</span>
              <h3>Analyse obligations and possible concessions</h3>
              <small>Checks curated current ATO and business.gov.au pages, then matches common concessions to the evidence already in business.db. Company figures never leave the app.</small>
            </div>
            <Landmark />
          </div>
          <button className="primary-button tax-analysis-button" disabled={analysing} onClick={() => void analyse()}>
            {analysing ? <LoaderCircle className="spin" /> : <Search />}
            {analysing ? 'Checking official sources…' : 'Analyse tax obligations and opportunities'}
          </button>
          {analysisError && <div className="mode-banner warning"><AlertTriangle /><div><strong>Review unavailable</strong><p>{analysisError}</p></div></div>}
          {analysis && (
            <>
              <div className="tax-analysis-summary">
                <div><span>Estimated income tax</span><strong>{money(analysis.obligation_snapshot.estimated_income_tax)}</strong></div>
                <div><span>Net GST</span><strong>{money(analysis.obligation_snapshot.net_gst)}</strong></div>
                <div><span>Catalogue reviewed</span><strong>{analysis.schemes.length} areas</strong></div>
                <div><span>Live official results</span><strong>{analysis.official_search.results.length}</strong></div>
              </div>
              <p className="soft-note">{analysis.official_search.message} {analysis.scope_note}</p>
              <div className="tax-scheme-grid">
                {analysis.schemes.map((scheme) => (
                  <article key={scheme.id}>
                    <div><span>{scheme.category}</span><b>{scheme.status}</b></div>
                    <h4>{scheme.title}</h4>
                    <p>{scheme.evidence}</p>
                    <small>{scheme.check}</small>
                    <a href={scheme.source_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Official guidance</a>
                  </article>
                ))}
              </div>
              {analysis.official_search.results.length > 0 && (
                <details className="official-search-results">
                  <summary>Show current official search results</summary>
                  <div>{analysis.official_search.results.map((result) => <a key={result.url} href={result.url} target="_blank" rel="noreferrer"><strong>{result.title}</strong><small>{result.source}</small><p>{result.content}</p></a>)}</div>
                </details>
              )}
            </>
          )}
        </article>
      </div>
    </section>
  )
}

function MoneyMapSection({ moneyMap }: { moneyMap: MoneyMapDashboard }) {
  return (
    <section id="section-money-map" data-section="money-map" className="scroll-dashboard-section money-map-section">
      <div className="section-inner">
        <SectionHeading eyebrow="End-to-end financial flow" title="See where money comes from, where it goes and what becomes profit" description="The flow reconciles the latest bank-receipt sources with department costs from the latest uploaded Profit and Loss statement." icon={Waypoints} />
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Revenue" value={money(moneyMap.summary.revenue)} note={`Period ${moneyMap.period}`} icon={CircleDollarSign} tone="good" />
          <MetricCard label="Operating costs" value={money(moneyMap.summary.operating_costs)} note="Allocated to departments" icon={WalletCards} />
          <MetricCard label="Profit before tax" value={money(moneyMap.summary.profit_before_tax)} note={`${number(moneyMap.summary.profit_margin_pct)}% margin`} icon={ArrowUpRight} tone="good" />
          <MetricCard label="Retained profit" value={money(moneyMap.summary.retained_profit)} note={`After ${money(moneyMap.summary.estimated_tax)} estimated tax`} icon={Landmark} />
        </div>
        <article id="money-map-flow" className="glass-card money-map-card">
          <div className="card-heading"><div><span className="eyebrow">Money map</span><h3>Income → departments → profit</h3><small>{moneyMap.source_note}</small></div><Waypoints /></div>
          <div className="money-sankey">
            <ResponsiveContainer width="100%" height="100%">
              <Sankey data={{ nodes: moneyMap.nodes, links: moneyMap.links }} nodePadding={28} linkCurvature={0.55} margin={{ top: 20, right: 125, bottom: 20, left: 125 }}>
                <Tooltip formatter={(value) => money(value)} />
              </Sankey>
            </ResponsiveContainer>
          </div>
          <div className="money-map-ledgers">
            <div><span>Money sources</span>{moneyMap.sources.map((item) => <p key={item.name}><strong>{item.name}</strong><b>{money(item.value)}</b></p>)}</div>
            <div><span>Department use</span>{moneyMap.departments.map((item) => <p key={item.name}><strong>{item.name}</strong><b>{money(item.value)}</b></p>)}</div>
          </div>
        </article>
      </div>
    </section>
  )
}

function InventorySection({ inventory }: { inventory: InventoryDashboard }) {
  const [query, setQuery] = useState('')
  const [stockFilter, setStockFilter] = useState('all')
  const filtered = inventory.items.filter((item) => {
    const matchesText = `${item.sku} ${item.name} ${item.location}`.toLowerCase().includes(query.toLowerCase())
    return matchesText && (stockFilter === 'all' || item.stock_state === stockFilter)
  })
  return (
    <section id="section-inventory" data-section="inventory" className="scroll-dashboard-section inventory-section">
      <div id="inventory-dashboard" className="section-inner">
        <SectionHeading eyebrow="Inventory management" title="Stock, reorder controls and invoice-linked movements" description="SKU and quantity fields from recurring invoices update stock after the latest inventory snapshot. Earlier movements remain visible without being counted twice." icon={PackageSearch} />
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Inventory value" value={money(inventory.summary.inventory_value)} note={`${inventory.summary.sku_count} active SKUs`} icon={PackageSearch} tone="good" />
          <MetricCard label="Units on hand" value={number(inventory.summary.units_on_hand, 0)} note="Across all storage locations" icon={Layers3} />
          <MetricCard label="Reorder alerts" value={String(inventory.summary.reorder_count)} note="At or below configured reorder point" icon={AlertTriangle} tone={inventory.summary.reorder_count ? 'warn' : 'good'} />
          <MetricCard label="Invoice movements" value={String(inventory.summary.invoice_linked_movements)} note={`${inventory.summary.auto_applied_movements} applied after the snapshot`} icon={ReceiptText} />
        </div>
        <div className="inventory-grid">
          <article className="glass-card inventory-value-card">
            <div className="card-heading"><div><span className="eyebrow">Stock concentration</span><h3>Highest-value inventory</h3></div><ChartNoAxesCombined /></div>
            <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={inventory.value_by_category} layout="vertical" margin={{ left: 18, right: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number" tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`}/><YAxis type="category" dataKey="label" width={145}/><Tooltip formatter={(value) => money(value)}/><Bar dataKey="value" fill={chartColors.bar} radius={[0, 8, 8, 0]}/></BarChart></ResponsiveContainer></div>
          </article>
          <article className="glass-card inventory-movement-card">
            <div className="card-heading"><div><span className="eyebrow">Automatic maintenance</span><h3>Latest invoice-linked movements</h3></div><ReceiptText /></div>
            <div className="inventory-movement-list">{inventory.movements.slice(0, 8).map((movement, index) => <div key={`${movement.source_invoice}-${movement.sku}-${index}`}><span className={movement.signed_quantity < 0 ? 'movement-out' : 'movement-in'}>{movement.signed_quantity > 0 ? '+' : ''}{number(movement.signed_quantity, 0)}</span><p><strong>{movement.item_name}</strong><small>{movement.source_invoice} · {movement.movement_date}</small></p><b>{movement.applied_to_stock ? 'Applied' : 'In snapshot'}</b></div>)}</div>
            <p className="soft-note">{inventory.method}</p>
          </article>
        </div>
        <article id="inventory-register" className="glass-card inventory-register-card">
          <div className="card-heading"><div><span className="eyebrow">Inventory register</span><h3>Stock on hand and replenishment</h3></div><PackageSearch /></div>
          <div className="table-tools"><label><Search size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search SKU, item or location" /></label><select value={stockFilter} onChange={(event) => setStockFilter(event.target.value)}><option value="all">All stock states</option><option value="reorder">Reorder</option><option value="watch">Watch</option><option value="healthy">Healthy</option></select></div>
          <div className="table-shell premium-table-shell"><table><thead><tr><th>SKU</th><th>Item</th><th>On hand</th><th>Reorder</th><th>Suggested order</th><th>Value</th><th>Location</th><th>Status</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.sku}><td><span className="account-code">{item.sku}</span></td><td><strong>{item.name}</strong><small>{item.lead_time_days} day lead time</small></td><td>{number(item.quantity, 0)}</td><td>{number(item.reorder_point, 0)}</td><td>{number(item.suggested_order, 0)}</td><td><strong>{money(item.total_value)}</strong></td><td>{item.location}</td><td><span className={`status-pill stock-${item.stock_state}`}>{item.stock_state}</span></td></tr>)}</tbody></table></div>
        </article>
      </div>
    </section>
  )
}

function HRSection({ hr }: { hr: HRDashboard }) {
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('all')
  const departments = Array.from(new Set(hr.employees.map((employee) => employee.department))).sort()
  const filtered = hr.employees.filter((employee) => {
    const matches = `${employee.employee} ${employee.employee_code} ${employee.role_title} ${employee.department}`.toLowerCase().includes(query.toLowerCase())
    return matches && (department === 'all' || employee.department === department)
  })
  return (
    <section id="section-hr" data-section="hr" className="scroll-dashboard-section hr-section">
      <div className="section-inner">
        <SectionHeading eyebrow="People and payroll" title="Payroll, workforce, leave and compliance in one organised view" description="Uploaded payroll remains the financial source. Synthetic demo profiles fill department, role, leave and training fields until an HR master is uploaded." icon={UsersRound} />
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Headcount" value={String(hr.summary.headcount)} note={`Payroll period ${hr.period}`} icon={UsersRound} tone="good" />
          <MetricCard label="Gross payroll" value={money(hr.summary.gross_pay)} note={`${money(hr.summary.net_pay)} net pay`} icon={WalletCards} />
          <MetricCard label="PAYG + super" value={money(hr.summary.payg_withholding + hr.summary.superannuation)} note={`${money(hr.summary.payg_withholding)} PAYG · ${money(hr.summary.superannuation)} super`} icon={Landmark} />
          <MetricCard label="HR actions" value={String(hr.summary.open_actions)} note={`${number(hr.summary.annual_leave_days)} annual leave days available`} icon={ShieldCheck} tone={hr.summary.open_actions ? 'warn' : 'good'} />
        </div>
        <div className="hr-grid">
          <article className="glass-card hr-department-card"><div className="card-heading"><div><span className="eyebrow">Department payroll</span><h3>People cost by function</h3></div><ChartNoAxesCombined /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={hr.department_costs}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="department" interval={0} angle={-15} textAnchor="end" height={62}/><YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`}/><Tooltip formatter={(value) => money(value)}/><Bar dataKey="gross_pay" fill={chartColors.barAlt} radius={[8, 8, 0, 0]}/></BarChart></ResponsiveContainer></div></article>
          <article className="glass-card hr-action-card"><div className="card-heading"><div><span className="eyebrow">HR control queue</span><h3>Leave, training and compliance</h3></div><ShieldCheck /></div>{hr.actions.length ? <div className="hr-action-list">{hr.actions.map((action, index) => <div key={`${action.employee}-${index}`}><AlertTriangle/><p><strong>{action.employee}</strong><span>{action.detail}</span></p><b>{action.due_date || action.severity}</b></div>)}</div> : <div className="empty-state"><CheckCircle2/><p>No open HR control actions.</p></div>}<p className="soft-note">{hr.disclaimer}</p></article>
        </div>
        <article id="hr-payroll-table" className="glass-card hr-payroll-card">
          <div className="card-heading"><div><span className="eyebrow">Employee and payroll register</span><h3>Everyone in the latest payroll period</h3></div><UsersRound /></div>
          <div className="table-tools"><label><Search size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search employee, role or department" /></label><select value={department} onChange={(event) => setDepartment(event.target.value)}><option value="all">All departments</option>{departments.map((item) => <option value={item} key={item}>{item}</option>)}</select></div>
          <div className="table-shell premium-table-shell"><table><thead><tr><th>Employee</th><th>Department</th><th>Role</th><th>Gross</th><th>PAYG</th><th>Super</th><th>Net</th><th>Leave</th><th>Training</th></tr></thead><tbody>{filtered.map((employee) => <tr key={employee.employee}><td><strong>{employee.employee}</strong><small>{employee.employee_code} · since {employee.start_date}</small></td><td><span className="status-pill">{employee.department}</span></td><td>{employee.role_title}</td><td>{money(employee.gross_pay)}</td><td>{money(employee.payg_withholding)}</td><td>{money(employee.superannuation)}</td><td><strong>{money(employee.net_pay)}</strong></td><td>{number(employee.annual_leave_days)} days<small>{number(employee.personal_leave_days)} personal</small></td><td><span className={`status-pill training-${employee.training_status}`}>{employee.training_status}</span><small>{employee.training}</small></td></tr>)}</tbody></table></div>
        </article>
      </div>
    </section>
  )
}

function MarketingSection({ marketing }: { marketing: MarketingDashboard }) {
  return (
    <section id="section-marketing" data-section="marketing" className="scroll-dashboard-section marketing-section">
      <div className="section-inner">
        <SectionHeading eyebrow="Marketing performance" title="See budget, channels and revenue in the same commercial context" description="Campaign spend is compared with revenue and channel efficiency. Demonstration figures are clearly labelled until integrations provide verified attribution." icon={Megaphone} />
        <div className="mode-banner"><Megaphone /><div><strong>{marketing.mode === 'demonstration' ? 'Demonstration allocation active' : 'Posted marketing spend active'}</strong><p>{marketing.disclaimer}</p></div></div>
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Marketing spend" value={money(marketing.summary.marketing_spend)} note={`${number(marketing.summary.spend_to_revenue_pct)}% of revenue`} icon={WalletCards} />
          <MetricCard label="Revenue context" value={money(marketing.summary.revenue)} note="Accounting revenue used for comparison" icon={CircleDollarSign} tone="good" />
          <MetricCard label="Attributed revenue" value={money(marketing.summary.attributed_revenue)} note={marketing.mode === 'demonstration' ? 'Illustrative only' : 'Requires campaign data'} icon={ArrowUpRight} />
          <MetricCard label="ROAS" value={`${number(marketing.summary.roas, 2)}x`} note={`${marketing.summary.channels} channel groups`} icon={Gauge} />
        </div>
        <div className="marketing-grid">
          <article className="glass-card marketing-trend-card"><div className="card-heading"><div><span className="eyebrow">Commercial relationship</span><h3>{marketing.performance_mode === 'trend' ? 'Revenue versus marketing spend' : 'Current-period commercial context'}</h3><small>{marketing.performance_mode === 'trend' ? 'Observed periods only' : 'A bar comparison is used because there are not enough observed periods for an honest trend.'}</small></div><ChartNoAxesCombined /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%">{marketing.performance_mode === 'trend' ? <LineChart data={marketing.performance}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="month"/><YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`}/><Tooltip formatter={(value) => money(value)}/><Line type="monotone" dataKey="revenue" stroke={chartColors.revenue} strokeWidth={3}/><Line type="monotone" dataKey="marketing_spend" stroke={chartColors.expenses} strokeWidth={2.25}/></LineChart> : <BarChart data={marketing.performance} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number" tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`}/><YAxis type="category" dataKey="metric" width={118}/><Tooltip formatter={(value) => money(value)}/><Bar dataKey="value" fill={chartColors.bar} radius={[0, 8, 8, 0]}/></BarChart>}</ResponsiveContainer></div></article>
          <article id="marketing-channel-chart" className="glass-card channel-card"><div className="card-heading"><div><span className="eyebrow">Channel allocation</span><h3>Spend and efficiency</h3></div><Megaphone /></div><div className="channel-bars">{marketing.channels.map((channel) => <div key={channel.channel}><div><strong>{channel.channel}</strong><span>{money(channel.spend)} · {number(channel.share)}%</span></div><div className="channel-track"><i style={{ width: `${Math.min(100, channel.share * 2.4)}%` }} /></div><small>{channel.roas ? `${number(channel.roas, 1)}x ROAS · ${channel.status}` : 'Attribution not connected'}</small></div>)}</div></article>
        </div>
        <article id="marketing-market-context" className="marketing-recommendations"><span>Recommended controls</span>{marketing.recommendations.map((item) => <div key={item}><CheckCircle2 /><p>{item}</p></div>)}</article>
      </div>
    </section>
  )
}

function IntelligenceSection({ intelligence, onStart }: { intelligence: CompetitorIntelligenceStatus | null; onStart: Props['onStartCompetitorAnalysis'] }) {
  const rawResult = intelligence?.result
  const result = rawResult && typeof rawResult === 'object' && 'company' in rawResult ? rawResult : null
  const job = intelligence?.job
  const processing = job?.status === 'queued' || job?.status === 'processing'
  const series = Array.isArray(result?.positioning_chart?.series) ? result.positioning_chart.series : []
  const dimensionEntries = result?.company?.dimensions && typeof result.company.dimensions === 'object'
    ? Object.entries(result.company.dimensions)
    : []
  const fallbackSlots = [
    { id: 'slot-one', title: 'Agent-selected chart slot 1', chart_type: 'waiting', reason: 'The agent will choose this after reading available evidence.', data_requirements: ['Start deep analysis'], status: 'empty', data: [] as Array<{ label: string; value: number }>, source_note: '' },
    { id: 'slot-two', title: 'Agent-selected chart slot 2', chart_type: 'waiting', reason: 'The chart remains blank until its required evidence exists.', data_requirements: ['Start deep analysis'], status: 'empty', data: [] as Array<{ label: string; value: number }>, source_note: '' },
  ]
  const slots = Array.isArray(result?.agent_chart_slots) && result.agent_chart_slots.length
    ? result.agent_chart_slots
    : fallbackSlots
  const marketSignals = Array.isArray(result?.market_signals) ? result.market_signals : []
  const research = result?.research && typeof result.research === 'object'
    ? result.research
    : { live: false, message: 'Live research is not configured', results: [] }
  const researchResults = Array.isArray(research.results) ? research.results : []
  const competitors = Array.isArray(result?.competitors) ? result.competitors : []
  const competitiveBrief = result?.competitive_brief
  const derivedChartData = (index: number) => {
    if (index === 0) {
      const signals = marketSignals
        .filter((item) => item.relevance_score != null)
        .slice(0, 8)
        .map((item) => ({ label: String(item.topic || item.signal_type || 'Market signal').slice(0, 32), value: Number(item.relevance_score || 0) * 100 }))
      if (signals.length) return signals
    }
    if (index === 1) {
      const evidence = competitors.slice(0, 8).map((item) => ({ label: item.entity.slice(0, 32), value: Number(item.verified_dimensions || 0) }))
      if (evidence.some((item) => item.value > 0)) return evidence
    }
    return dimensionEntries.map(([label, value]) => ({ label, value: Number(value) }))
  }

  return (
    <section id="section-intelligence" data-section="intelligence" className="scroll-dashboard-section intelligence-section">
      <div id="market-intelligence-workspace" className="section-inner">
        <SectionHeading eyebrow="Opt-in deep analysis" title="Company position, competitors and market intelligence" description="This workspace stays dormant until you start it. It then uses verified company metrics, uploaded competitor evidence and current cited research. Missing competitor figures remain visibly blank rather than being invented." icon={BrainCircuit} />
        {result?.data_mode?.internal === 'synthetic_demonstration' && <div className="intelligence-data-warning"><AlertTriangle /><span><strong>Synthetic internal dataset detected</strong><small>Internal financial figures are demonstration data. Current external research is kept separate and can describe real competitors, but it is not merged into the synthetic financial score.</small></span></div>}
        <div className="intelligence-launch-card glass-card">
          <div>
            <span className="eyebrow">Intelligence engine v3.3.1</span>
            <h3>{result ? 'Refresh the deep company analysis' : 'Start the deep company analysis'}</h3>
            <p>{result?.summary || 'LedgerFlow will calculate the company position locally, inspect uploaded market evidence, test the configured research source, and ask NVIDIA only to choose two useful future chart structures.'}</p>
          </div>
          <button className="primary-button intelligence-start-button" disabled={processing} onClick={() => void onStart()}>{processing ? <LoaderCircle className="spin" /> : <Play />} {processing ? 'Analysing…' : result ? 'Run again' : 'Start analysis'}</button>
          {processing && <div className="intelligence-progress"><div><span>{job?.stage_message}</span><strong>{job?.progress || 0}%</strong></div><i><b style={{ width: `${job?.progress || 0}%` }} /></i></div>}
        </div>

        <div className="intelligence-main-grid">
          <article id="competitor-positioning-chart" className="glass-card competitor-position-card">
            <div className="card-heading"><div><span className="eyebrow">Verified positioning</span><h3>{result?.positioning_chart?.title || 'Company versus competitors'}</h3></div><Target /></div>
            {series.length ? <>
              <div className="chart-frame intelligence-chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={series} layout="vertical" margin={{ left: 18, right: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number" domain={[0, 140]}/><YAxis type="category" dataKey="entity" width={118}/><Tooltip formatter={(value) => `${number(value, 1)} / 140`}/><Bar dataKey="score" fill={chartColors.competitor} radius={[0, 8, 8, 0]}/></BarChart></ResponsiveContainer></div>
              <p className="soft-note">{result?.comparison_note}</p>
            </> : <div className="intelligence-empty-chart"><BrainCircuit /><strong>Analysis not started</strong><span>The company position chart will appear after explicit activation. Competitor bars appear only when comparable verified metrics exist.</span></div>}
          </article>
          <article className="glass-card company-dimension-card">
            <div className="card-heading"><div><span className="eyebrow">Company dimensions</span><h3>{result?.company?.name || 'Local company scorecard'}</h3></div><Gauge /></div>
            {dimensionEntries.length ? <div className="dimension-list">{dimensionEntries.map(([key, value]) => <div key={key}><span>{key}</span><div><i style={{ width: `${Math.min(100, Number(value) / 1.4)}%` }} /></div><strong>{number(value, 1)}</strong></div>)}</div> : <div className="empty-state"><Layers3 /><span>Run deep analysis to calculate liquidity, cash resilience, margin strength and revenue momentum.</span></div>}
            <p className="soft-note">{result?.company?.score_method || 'This is an internal operating-position indicator, not a credit rating or fabricated market benchmark.'}</p>
          </article>
        </div>

        <div className="agent-chart-slot-grid">
          {slots.map((slot, index) => {
            const requirements = Array.isArray(slot.data_requirements) ? slot.data_requirements : []
            const chartData = Array.isArray(slot.data) && slot.data.length ? slot.data : derivedChartData(index)
            return <article key={slot.id || index} className="glass-card agent-chart-slot"><div className="chart-slot-head"><span>AI-planned chart 0{index + 1}</span><b>{slot.status || 'empty'}</b></div><h3>{slot.title || `Agent-selected chart ${index + 1}`}</h3>{chartData.length ? <div className="chart-frame ai-materialised-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ left: 4, right: 8, bottom: 26 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="label" interval={0} angle={-18} textAnchor="end" height={58}/><YAxis/><Tooltip formatter={(value) => number(value, 1)}/><Bar dataKey="value" fill={index === 0 ? chartColors.bar : chartColors.competitor} radius={[7,7,0,0]}/></BarChart></ResponsiveContainer></div> : <div className="blank-chart-visual"><ChartNoAxesCombined /><i/><i/><i/></div>}<p>{slot.reason || 'Waiting for sufficient verified evidence.'}</p><small className="chart-source-note">{slot.source_note || result?.chart_planner}</small>{!chartData.length && <div className="requirements-row">{requirements.map((item) => <span key={item}>{item}</span>)}</div>}</article>
          })}
        </div>

        {result && <div className="competitive-analysis-grid">
          <article className="glass-card competitor-register-card">
            <div className="card-heading"><div><span className="eyebrow">Competitive analysis</span><h3>Named competitors and evidence coverage</h3></div><Landmark /></div>
            {competitors.length ? <div className="competitor-register">{competitors.map((item) => <div key={item.entity}><span><strong>{item.entity}</strong><small>{item.evidence_summary || item.status}</small>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">{item.source_title || 'Open supporting source'} <ArrowUpRight /></a>}</span><span><b>{item.verified_dimensions} verified dimensions</b><small>{item.score == null ? 'Qualitative evidence only' : `Position score ${number(item.score, 1)}`}</small></span></div>)}</div> : <div className="empty-state"><AlertTriangle /><span>No named competitor was supported by the available evidence. Run the analysis again for automatic web research, or upload a competitor file.</span></div>}
          </article>
          <article className="glass-card competitive-brief-card">
            <div className="card-heading"><div><span className="eyebrow">Clippy’s evidence brief</span><h3>Strengths and external watch items</h3></div><BrainCircuit /></div>
            <p>{competitiveBrief?.evidence_basis || 'The brief uses verified company records and clearly identified external evidence.'}</p>
            <div className="brief-list"><strong>Company strengths</strong>{(competitiveBrief?.company_strengths || []).map((item) => <span key={item}><CheckCircle2 />{item}</span>)}</div>
            <div className="brief-list"><strong>Watch items</strong>{(competitiveBrief?.watch_items || []).map((item) => <span key={item}><AlertTriangle />{item}</span>)}{!competitiveBrief?.watch_items?.length && <small>No uploaded market watch items.</small>}</div>
          </article>
        </div>}

        {result && <article className="glass-card research-evidence-card">
          <div className="card-heading"><div><span className="eyebrow">Current external evidence</span><h3>Research used for the real company</h3></div><CloudCog /></div>
          {researchResults.length ? <div className="research-result-grid">{researchResults.map((item, index) => <a key={String(item.url || index)} href={String(item.url || '#')} target="_blank" rel="noreferrer"><strong>{String(item.title || 'Research result')}</strong><p>{String(item.content || 'Open the source for details.')}</p><small>{String(item.engine || 'web')} · {String(item.publishedDate || 'date unavailable')}</small><ArrowUpRight /></a>)}</div> : <div className="empty-state"><CloudCog /><span>{research.message || 'Automatic web research did not return evidence. Uploaded competitor evidence is still analysed.'}</span></div>}
        </article>}

        {result && <article className="market-evidence-strip"><div><FileCheck2 /><span><strong>{marketSignals.length} uploaded market signals</strong><small>{research.live ? `${researchResults.length} live research results available` : research.message || 'Live research is not configured'}</small></span></div><div><ShieldCheck /><span><strong>Stored separately in agent context</strong><small>{intelligence?.result_file || 'data/context/default/market_intelligence.json'}</small></span></div></article>}
      </div>
    </section>
  )
}

function CatalogueCard({ item, onSelect }: { item: DocumentCatalogueItem; onSelect: (item: DocumentCatalogueItem) => void }) {
  const needsRetry = item.state === 'needs_retry'
  const stateClass = item.received ? 'received' : needsRetry ? 'needs-retry' : ''
  const badge = item.received ? `${item.file_count} received` : needsRetry ? `${item.retry_count} needs retry` : item.tier
  return <button className={`catalogue-card ${stateClass}`} onClick={() => onSelect(item)}><div className="catalogue-card-head"><span className="catalogue-icon">{item.received ? <CheckCircle2 /> : needsRetry ? <AlertTriangle /> : <FileSpreadsheet />}</span><b>{badge}</b></div><strong>{item.label}</strong><p>{item.description}</p><small>{needsRetry ? 'A matching file exists, but processing did not complete. Retry it from the file register below.' : item.automation}</small><div className="format-row">{item.accepted.map((format) => <i key={format}>{format}</i>)}</div></button>
}

function FileRegister({ title, files, empty, onMove, onDelete, onRetry }: { title: string; files: UploadLibrary['files']['setup']; empty: string; onMove: Props['onMoveUpload']; onDelete: Props['onDeleteUpload']; onRetry: Props['onRetryUpload'] }) {
  const [workingId, setWorkingId] = useState<number | null>(null)
  const move = async (file: UploadLibrary['files']['setup'][number]) => {
    const destination: IntakeCategory = file.intake_category === 'setup' ? 'recurring' : 'setup'
    const label = destination === 'setup' ? 'Permanent setup' : 'Recurring evidence'
    if (!window.confirm(`Move ${file.filename} to ${label}? The imported records will not be duplicated or reprocessed.`)) return
    setWorkingId(file.id)
    try { await onMove(file.id, destination) } finally { setWorkingId(null) }
  }
  const remove = async (file: UploadLibrary['files']['setup'][number]) => {
    const confirmation = window.prompt(`Remove ${file.filename} and all records contributed by it? A local backup will be created first. Type DELETE to continue.`) || ''
    if (!confirmation.trim()) return
    setWorkingId(file.id)
    try { await onDelete(file.id, true, confirmation) } finally { setWorkingId(null) }
  }
  const retry = async (file: UploadLibrary['files']['setup'][number]) => {
    const suggested = file.suggested_document_type && !['profiling', 'generic', 'auto'].includes(file.suggested_document_type) ? file.suggested_document_type : file.declared_document_type
    if (!suggested || suggested === 'auto') {
      window.alert('Select the intended document card above, then upload the original file again so LedgerFlow knows the correct type.')
      return
    }
    if (!window.confirm(`Reprocess ${file.filename} as ${suggested.replaceAll('_', ' ')} using the preserved source file?`)) return
    setWorkingId(file.id)
    try { await onRetry(file.id, file.intake_category, suggested) } finally { setWorkingId(null) }
  }
  const completeStatuses = new Set(['committed', 'stored_source', 'pending_mapping'])
  return <article className="glass-card file-register-card"><div className="card-heading"><div><span className="eyebrow">Processed evidence</span><h3>{title}</h3></div><Files /></div><div className="uploaded-file-grid">{files.map((file) => { const needsRetry = !completeStatuses.has(file.processing_status); return <div key={file.id} className={`uploaded-file-card ${needsRetry ? 'needs-retry' : ''}`}><div className="uploaded-file-main">{needsRetry ? <AlertTriangle /> : <FileCheck2 />}<span><strong>{file.filename}</strong><small>{file.document_label} · data v{file.data_version || 0}</small></span><b>{needsRetry ? 'needs retry' : (file.display_status || file.processing_status).replaceAll('_', ' ')}</b></div><p>{file.assistant_message || file.analysis?.findings?.[0] || `${file.rows_imported} imported rows`}</p>{needsRetry && <div className="file-retry-note">This source is present, but it does not count toward document coverage until corrective processing completes.</div>}<div className="uploaded-file-meta"><span>{file.rows_imported} rows</span><span>{Math.round(Number(file.mapping_confidence || 0) * 100)}% mapping</span><span>{new Date(file.created_at).toLocaleDateString('en-AU')}</span></div><div className="uploaded-file-actions">{needsRetry && <button className="retry-inline" disabled={workingId === file.id} onClick={() => void retry(file)}>{workingId === file.id ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />} Retry processing</button>}<button disabled={workingId === file.id} onClick={() => void move(file)}><RefreshCw size={14} /> Move to {file.intake_category === 'setup' ? 'recurring' : 'permanent'}</button><button className="danger-inline" disabled={workingId === file.id} onClick={() => void remove(file)}>{workingId === file.id ? <LoaderCircle size={14} className="spin" /> : <Trash2 size={14} />} Delete file</button></div></div> })}{!files.length && <div className="empty-state"><Files /><span>{empty}</span></div>}</div></article>
}

function DecisionContextSection({ context, onRefresh }: { context: DecisionContextDashboard | null; onRefresh: Props['onRefreshDecisionContext'] }) {
  const [refreshing, setRefreshing] = useState(false)
  const sourceMap = useMemo(() => new Map((context?.sources || []).map((source) => [source.source_key, source])), [context])
  const formatDateTime = (value: unknown) => {
    if (!value) return 'Not available'
    const parsed = new Date(String(value))
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' })
  }
  const refresh = async () => {
    setRefreshing(true)
    try { await onRefresh() } finally { setRefreshing(false) }
  }
  const latestSources = (context?.sources || []).slice(0, 10)
  const decisions = context?.decisions || []
  return (
    <section id="section-decisions" data-section="decisions" className="scroll-dashboard-section decision-context-section">
      <div id="decision-context-dashboard" className="section-inner">
        <SectionHeading eyebrow="AI context orchestration" title="Context board and time-aware evidence" description="A separate timestamped database connects uploaded evidence, data freshness, analysis cutoffs and AI decision domains. Ledger reads this context before strategic reasoning." icon={Clock3} />
        <div className="decision-context-toolbar">
          <div className="decision-live-clock"><Clock3 /><span><small>Current analysis time</small><strong>{formatDateTime(context?.current_time_local)}</strong><b>{context?.timezone || 'Australia/Melbourne'}</b></span></div>
          <button className="primary-button" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? <LoaderCircle className="spin" /> : <RefreshCw />} Refresh decision context</button>
        </div>
        <div className="metric-grid metric-grid-four decision-context-metrics">
          <MetricCard label="Connected inputs" value={String(context?.summary.source_count || 0)} note={`${context?.summary.freshness?.fresh || 0} fresh · ${context?.summary.freshness?.reference || 0} reference`} icon={Files} tone="good" />
          <MetricCard label="Ready decisions" value={String(context?.summary.ready_decisions || 0)} note={`${context?.summary.provisional_decisions || 0} provisional`} icon={CheckCircle2} tone="good" />
          <MetricCard label="Data cutoff" value={context?.data_cutoff_local ? new Date(context.data_cutoff_local).toLocaleDateString('en-AU') : '—'} note={formatDateTime(context?.data_cutoff_local)} icon={Database} />
          <MetricCard label="Last analysis" value={String(context?.last_analysis?.status || 'Not run').replaceAll('_', ' ')} note={formatDateTime(context?.last_analysis?.completed_at_utc || context?.last_analysis?.started_at_utc)} icon={BrainCircuit} tone={context?.last_analysis?.status === 'completed' ? 'good' : 'warn'} />
        </div>

        <article className="glass-card decision-flow-card">
          <div className="card-heading"><div><span className="eyebrow">Decision lineage</span><h3>Which inputs are connected to the decision-processing AI</h3><small>Only the displayed connections are allowed to influence each decision domain.</small></div><Waypoints /></div>
          <div className="decision-flow-grid">
            <div className="decision-flow-column input-column">
              <span className="decision-flow-label">Timestamped inputs</span>
              {latestSources.map((source) => <div key={source.source_key} className={`decision-source-node freshness-${source.freshness_state}`}><FileCheck2 /><span><strong>{source.filename}</strong><small>{source.document_type.replaceAll('_', ' ')} · {source.freshness_state}</small><b>{formatDateTime(source.processed_at_local || source.processed_at_utc)}</b></span></div>)}
              {!latestSources.length && <div className="empty-state"><Files /><span>No processed evidence is connected yet.</span></div>}
            </div>
            <div className="decision-flow-connector"><ArrowUpRight /><span>normalise time<br/>and freshness</span></div>
            <div className="decision-database-node"><Database /><strong>Temporal decision database</strong><span>Separate SQLite store</span><small>{context?.database_file || 'data/database/decision_context.sqlite'}</small><div><b>Context file</b><code>{context?.context_file || 'temporal_decision_context.json'}</code></div></div>
            <div className="decision-flow-connector"><GitBranch /><span>link permitted<br/>evidence</span></div>
            <div className="decision-flow-column decision-column">
              <span className="decision-flow-label">Decision domains</span>
              {decisions.map((decision) => {
                const connected = (context?.links || []).filter((link) => link.decision_id === decision.decision_id).slice(0, 4)
                return <div key={decision.decision_id} className={`decision-node readiness-${decision.readiness}`}><BrainCircuit /><span><strong>{decision.label}</strong><small>{decision.description}</small><div className="decision-source-chips">{connected.map((link) => <b key={`${link.decision_id}-${link.source_key}`}>{sourceMap.get(link.source_key)?.filename || link.source_key}</b>)}</div></span><em>{decision.readiness.replaceAll('_', ' ')}</em></div>
              })}
            </div>
          </div>
          <p className="decision-engine-note">{context?.decision_engine_note}</p>
        </article>

        <div className="decision-context-lower-grid">
          <article className="glass-card decision-timeline-card"><div className="card-heading"><div><span className="eyebrow">Evidence chronology</span><h3>Recent uploaded and processed inputs</h3></div><Clock3 /></div><div className="decision-timeline">{latestSources.map((source) => <div key={`timeline-${source.source_key}`}><i /><span><strong>{source.filename}</strong><small>Effective {source.effective_date} · data v{source.data_version}</small><b>Uploaded {formatDateTime(source.uploaded_at_local || source.uploaded_at_utc)}<br/>Processed {formatDateTime(source.processed_at_local || source.processed_at_utc)}</b></span></div>)}{!latestSources.length && <div className="empty-state"><Clock3 /><span>The timeline will populate after files are processed.</span></div>}</div></article>
          <article className="glass-card analysis-history-card"><div className="card-heading"><div><span className="eyebrow">Analysis memory</span><h3>Last and previous analysis runs</h3></div><BrainCircuit /></div><div className="analysis-run-list">{(context?.analysis_history || []).map((run, index) => <div key={String(run.run_key || index)}><span className={`status-pill ${String(run.status || '')}`} >{String(run.status || 'unknown')}</span><section><strong>{String(run.analysis_type || 'analysis').replaceAll('_', ' ')}</strong><small>{String(run.summary || 'No summary stored')}</small><b>{formatDateTime(run.completed_at_utc || run.started_at_utc)}</b></section></div>)}{!(context?.analysis_history || []).length && <div className="empty-state"><BrainCircuit /><span>No deep analysis has been recorded yet.</span></div>}</div></article>
        </div>
      </div>
    </section>
  )
}

function DataQualitySection({ quality, semanticLayer }: { quality: DataQualityDashboard | null; semanticLayer: SemanticLayerStatus | null }) {
  const issueData = Object.entries(quality?.issue_counts || {}).map(([severity, count]) => ({ severity, count }))
  const coverageData = (quality?.source_coverage || []).map((item) => ({ ...item, missing: Math.max(0, item.total - item.received) }))
  const reconciliationData = (quality?.reconciliations || []).map((item) => ({ ...item, absolute_difference: Math.abs(item.difference) }))
  const metricStates = (semanticLayer?.metrics || []).reduce<Record<string, number>>((result, metric) => {
    result[metric.status] = (result[metric.status] || 0) + 1
    return result
  }, {})
  const metricStateData = Object.entries(metricStates).map(([status, count]) => ({ status, count }))
  return (
    <section id="section-quality" data-section="quality" className="scroll-dashboard-section quality-section">
      <div id="data-quality-dashboard" className="section-inner">
        <SectionHeading eyebrow="Data trust and metric governance" title="Source coverage, reconciliation and analytical readiness" description="Every headline metric is tied to a canonical definition, source grain and evidence requirement. Warnings remain visible instead of being hidden behind a polished dashboard." icon={ShieldCheck} />
        <div className="metric-grid metric-grid-four">
          <MetricCard label="Trust score" value={`${quality?.score ?? 0}/100`} note={quality?.status || 'not available'} icon={ShieldCheck} tone={quality?.status === 'trusted' ? 'good' : 'warn'} />
          <MetricCard label="Open checks" value={String(quality?.open_check_total ?? 0)} note="Validation + accounting + tax" icon={AlertTriangle} tone={(quality?.open_check_total || 0) > 0 ? 'warn' : 'good'} />
          <MetricCard label="Core coverage" value={`${quality?.source_coverage?.[0]?.received ?? 0}/${quality?.source_coverage?.[0]?.total ?? 0}`} note="Required permanent evidence" icon={FileCheck2} tone={(quality?.source_coverage?.[0]?.received || 0) === (quality?.source_coverage?.[0]?.total || -1) ? 'good' : 'warn'} />
          <MetricCard label="Metric contracts" value={String(semanticLayer?.metrics?.length || 0)} note={`Semantic layer v${semanticLayer?.version || '—'}`} icon={Layers3} tone="good" />
        </div>
        <div className="analytics-chart-grid quality-chart-grid">
          <article className="glass-card analytics-chart-card"><div className="card-heading"><div><span className="eyebrow">Issue mix</span><h3>Open issues by severity</h3></div><AlertTriangle /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={issueData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="severity" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" radius={[8,8,0,0]} /></BarChart></ResponsiveContainer></div></article>
          <article className="glass-card analytics-chart-card"><div className="card-heading"><div><span className="eyebrow">Source coverage</span><h3>Received versus missing evidence</h3></div><Files /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={coverageData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="received" stackId="coverage" radius={[8,8,0,0]} /><Bar dataKey="missing" stackId="coverage" radius={[8,8,0,0]} /></BarChart></ResponsiveContainer></div></article>
          <article className="glass-card analytics-chart-card"><div className="card-heading"><div><span className="eyebrow">Reconciliation</span><h3>Difference requiring explanation</h3></div><RefreshCw /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={reconciliationData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="absolute_difference" radius={[8,8,0,0]} /></BarChart></ResponsiveContainer></div></article>
          <article className="glass-card analytics-chart-card"><div className="card-heading"><div><span className="eyebrow">Metric readiness</span><h3>Ready, provisional and blocked definitions</h3></div><Target /></div><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={metricStateData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="status" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" radius={[8,8,0,0]} /></BarChart></ResponsiveContainer></div></article>
        </div>
        <div className="quality-detail-grid">
          <article className="glass-card"><div className="card-heading"><div><span className="eyebrow">Trust checks</span><h3>What is safe, provisional or blocked</h3></div><ShieldCheck /></div><div className="quality-check-list">{(quality?.checks || []).map((item) => <div key={item.id} className={`quality-check quality-${item.status}`}><span>{item.severity}</span><div><strong>{item.label}</strong><p>{item.detail}</p>{item.recommendation && <small>{item.recommendation}</small>}</div><b>{item.status}</b></div>)}</div></article>
          <article className="glass-card"><div className="card-heading"><div><span className="eyebrow">Canonical metrics</span><h3>Definitions and controlling sources</h3></div><BookOpenCheck /></div><div className="semantic-metric-list">{(semanticLayer?.metrics || []).map((metric) => <div key={metric.id}><span>{metric.status}</span><div><strong>{metric.label}</strong><p>{metric.definition}</p><small>Source: {metric.canonical_source} · role: {metric.role}</small></div></div>)}</div></article>
        </div>
      </div>
    </section>
  )
}

function OperationsSection({ pipelineStatus, documents, uploadLibrary, processingActivity, folderIntake, classificationRepair, dataQuality, onUpload, onRefreshDocuments, onMoveUpload, onDeleteUpload, onRetryUpload, onScanFolderIntake, onRepairClassifications }: { pipelineStatus: PipelineStatus | null; documents: GeneratedDocument[]; uploadLibrary: UploadLibrary | null; processingActivity: UploadProcessingJob | null; folderIntake: FolderIntakeStatus | null; classificationRepair: ClassificationRepairStatus | null; dataQuality: DataQualityDashboard | null; onUpload: Props['onUpload']; onRefreshDocuments: Props['onRefreshDocuments']; onMoveUpload: Props['onMoveUpload']; onDeleteUpload: Props['onDeleteUpload']; onRetryUpload: Props['onRetryUpload']; onScanFolderIntake: Props['onScanFolderIntake']; onRepairClassifications: Props['onRepairClassifications'] }) {
  const [category, setCategory] = useState<IntakeCategory>('setup')
  const [declaredType, setDeclaredType] = useState('balance_sheet')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('Select a document card or let Ledger identify the file automatically.')
  const fileRef = useRef<HTMLInputElement>(null)
  const selectDocument = (item: DocumentCatalogueItem) => { setCategory(item.intake_category); setDeclaredType(item.id); setMessage(`${item.label} selected. Choose the source file when ready.`); document.getElementById('upload-zone')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) }
  const submitFile = async (file: File) => {
    setBusy(true); setMessage(`Clippy is processing ${file.name} in the background…`)
    try {
      const result = await onUpload(file, category, declaredType)
      setMessage(result.assistant_message || (result.needs_mapping ? `${file.name} is stored and needs column mapping.` : `${file.name}: ${result.rows_imported} rows incorporated.`))
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Upload failed.') } finally { setBusy(false) }
  }
  const setupRequired = uploadLibrary?.catalogue.setup_required || []
  const setupRecommended = uploadLibrary?.catalogue.setup_recommended || []
  const recurring = uploadLibrary?.catalogue.recurring || []
  const activeProgress = processingActivity && ['queued', 'processing'].includes(processingActivity.status)
  return (
    <section id="section-operations" data-section="operations" className="scroll-dashboard-section operations-section">
      <div className="section-inner">
        <SectionHeading eyebrow="Business data and file centre" title="Permanent company knowledge and recurring operating evidence" description="Every upload is classified, read, versioned and explained. Routine processing is deterministic and fast; the model is used only when a task requires interpretation." icon={Database} />
        <article className="page-readiness-strip" aria-label="Dashboard data readiness">
          <div className="readiness-strip-heading"><span>Dashboard checks</span><strong>{dataQuality?.pages_ready || 0}/{dataQuality?.pages_total || 5} ready</strong></div>
          <div className="page-readiness-grid">{(dataQuality?.page_readiness || []).map((page) => (
            <div key={page.id} className={`page-readiness-item readiness-${page.status}`}>
              {page.status === 'ready' ? <CheckCircle2 /> : <AlertTriangle />}
              <span><strong>{page.label}</strong><small>{page.detail}</small></span>
              <b>{page.status}</b>
            </div>
          ))}</div>
        </article>
        <article id="folder-intake-panel" className="glass-card folder-intake-card">
          <div className="card-heading"><div><span className="eyebrow">App-folder intake</span><h3>Paste files into Permanent or Recurring</h3></div><Files /></div>
          <div className="folder-path-grid">
            <div><span>Permanent folder</span><code>{folderIntake?.paths.setup || 'file_drop/permanent'}</code></div>
            <div><span>Recurring folder</span><code>{folderIntake?.paths.recurring || 'file_drop/recurring'}</code></div>
            <div><span>Pending files</span><strong>{folderIntake?.pending.total || 0}</strong></div>
            <div><span>Classification repairs</span><strong>{classificationRepair?.plan.length || 0}</strong></div>
          </div>
          <p>LedgerFlow scans these folders automatically, queues supported files through the staged processor, and moves originals into the archive folder after queuing. Document-type subfolders provide exact routing.</p>
          <div className="folder-action-row"><button className="primary-button" onClick={() => void onScanFolderIntake()}><RefreshCw /> Scan folders now</button><button className="secondary-button" disabled={!classificationRepair?.plan.length} onClick={() => void onRepairClassifications()}><FileCheck2 /> Repair classifications</button></div>
        </article>
        <div className="operations-grid operations-grid-enhanced">
          <article id="upload-zone" className="glass-card upload-studio">
            <div className="card-heading"><div><span className="eyebrow">Staged background processor</span><h3>Upload business evidence</h3></div>{activeProgress ? <LoaderCircle className="spin" /> : <UploadCloud />}</div>
            <div className="intake-tabs"><button className={category === 'setup' ? 'active' : ''} onClick={() => { setCategory('setup'); setDeclaredType('auto') }}><Building2 /> Permanent setup</button><button className={category === 'recurring' ? 'active' : ''} onClick={() => { setCategory('recurring'); setDeclaredType('auto') }}><RefreshCw /> Recurring evidence</button></div>
            <label>Selected document type<select value={declaredType} onChange={(event) => setDeclaredType(event.target.value)}><option value="auto">Let Ledger identify it</option>{[...setupRequired, ...setupRecommended, ...recurring].filter((item) => item.intake_category === category).map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
            <button className="drop-zone" onClick={() => fileRef.current?.click()} disabled={busy || Boolean(activeProgress)}>{busy || activeProgress ? <LoaderCircle className="spin" /> : <UploadCloud />}<strong>{activeProgress ? processingActivity?.stage_message : busy ? 'Starting processor…' : 'Choose CSV, XLSX, XLSM or PDF'}</strong><span>{activeProgress ? `${processingActivity?.progress || 0}% complete` : 'Original evidence remains local; only task-specific context is sent to NVIDIA.'}</span></button>
            {activeProgress && <div className="upload-progress-panel"><div><span>{processingActivity?.stage.replaceAll('_', ' ')}</span><strong>{processingActivity?.progress}%</strong></div><i><b style={{ width: `${processingActivity?.progress || 0}%` }} /></i></div>}
            <input ref={fileRef} hidden type="file" accept=".csv,.xlsx,.xlsm,.pdf" onChange={(event) => { const file = event.target.files?.[0]; if (file) void submitFile(file); event.target.value = '' }} />
            <p className="soft-note">{message}</p>
          </article>
          <article className="glass-card pipeline-card"><div className="card-heading"><div><span className="eyebrow">Pipeline pulse</span><h3>Bronze → Silver → DuckDB → Gold → Context</h3></div><Database /></div><div className="pipeline-stage-row">{['Bronze', 'Silver', 'DuckDB', 'Gold', 'Context'].map((stage, index) => <div key={stage}><span>0{index + 1}</span><strong>{stage}</strong><small>{activeProgress && index <= Math.floor((processingActivity?.progress || 0) / 22) ? 'Processing' : pipelineStatus?.layers?.[stage.toLowerCase()] || 'Ready'}</small></div>)}</div><div className="pipeline-stats"><div><span>Data version</span><strong>{pipelineStatus?.data_version || 0}</strong></div><div><span>Baseline</span><strong>{pipelineStatus?.baseline_version || 0}</strong></div><div><span>Uploads</span><strong>{pipelineStatus?.uploads || 0}</strong></div><div><span>Saved mappings</span><strong>{pipelineStatus?.saved_mapping_profiles || 0}</strong></div></div></article>
        </div>

        <div id="permanent-file-library" className="document-category-section permanent-category-section simplified-library-section">
          <details className="catalogue-disclosure" open>
            <summary><span><strong>Permanent company knowledge</strong><small>Required foundation files</small></span><b>{uploadLibrary?.coverage.required_received.length || 0}/{setupRequired.length} represented</b></summary>
            <div className="catalogue-grid">{setupRequired.map((item) => <CatalogueCard key={item.id} item={item} onSelect={selectDocument} />)}</div>
          </details>
          <details className="catalogue-disclosure">
            <summary><span><strong>Optional operating context</strong><small>Forecasts, contracts, assets and plans</small></span><b>{uploadLibrary?.coverage.recommended_received.length || 0}/{setupRecommended.length} represented</b></summary>
            <div className="catalogue-grid catalogue-grid-recommended">{setupRecommended.map((item) => <CatalogueCard key={item.id} item={item} onSelect={selectDocument} />)}</div>
          </details>
          <FileRegister title="Permanent files" files={uploadLibrary?.files.setup || []} empty="No permanent setup evidence has been uploaded yet." onMove={onMoveUpload} onDelete={onDeleteUpload} onRetry={onRetryUpload} />
        </div>

        <div id="recurring-file-library" className="document-category-section recurring-category-section simplified-library-section">
          <details className="catalogue-disclosure">
            <summary><span><strong>Recurring operating evidence</strong><small>Invoices, banking, receivables and payroll</small></span><b>{uploadLibrary?.files.recurring.length || 0} processed files</b></summary>
            <div className="catalogue-grid recurring-catalogue-grid">{recurring.map((item) => <CatalogueCard key={item.id} item={item} onSelect={selectDocument} />)}</div>
          </details>
          <FileRegister title="Recurring files" files={uploadLibrary?.files.recurring || []} empty="No recurring invoices, statements, sales invoices or payroll reports have been uploaded yet." onMove={onMoveUpload} onDelete={onDeleteUpload} onRetry={onRetryUpload} />
        </div>

        <article className="glass-card document-library-wide"><div className="card-heading"><div><span className="eyebrow">Generated outputs</span><h3>Business document register</h3></div><button className="icon-button" onClick={() => void onRefreshDocuments()}><RefreshCw /></button></div><div className="document-grid">{documents.map((item) => <a key={item.id} href={`/api/documents/${encodeURIComponent(item.id)}/download`}><div className="document-tile-icon"><FileSpreadsheet /></div><div><strong>{item.title}</strong><span>{item.filename}</span><small>{new Date(item.created_at).toLocaleDateString('en-AU')} · {item.status}</small></div><ArrowDownToLine /></a>)}{!documents.length && <div className="empty-state"><Files /><span>Generated files will appear here.</span></div>}</div></article>
      </div>
    </section>
  )
}

function SimpleDataManagement({ pipelineStatus, uploadLibrary, processingActivity, folderIntake, classificationRepair, businessStore, onUpload, onMoveUpload, onDeleteUpload, onRetryUpload, onScanFolderIntake, onRepairClassifications }: { pipelineStatus: PipelineStatus | null; uploadLibrary: UploadLibrary | null; processingActivity: UploadProcessingJob | null; folderIntake: FolderIntakeStatus | null; classificationRepair: ClassificationRepairStatus | null; businessStore: BusinessStoreStatus | null; onUpload: Props['onUpload']; onMoveUpload: Props['onMoveUpload']; onDeleteUpload: Props['onDeleteUpload']; onRetryUpload: Props['onRetryUpload']; onScanFolderIntake: Props['onScanFolderIntake']; onRepairClassifications: Props['onRepairClassifications'] }) {
  const [category, setCategory] = useState<IntakeCategory>('setup')
  const [declaredType, setDeclaredType] = useState('auto')
  const [busy, setBusy] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [message, setMessage] = useState('Choose a procedure and add a file. Clippy will identify, validate, store and trace it.')
  const fileRef = useRef<HTMLInputElement>(null)
  const setupRequired = uploadLibrary?.catalogue.setup_required || []
  const recurring = uploadLibrary?.catalogue.recurring || []
  const lifecycle = businessStore?.clippy.lifecycle || businessStore?.clippy.summary.lifecycle || {}
  const setupComplete = Boolean(lifecycle.setup_complete)
  const activeProgress = processingActivity && ['queued', 'processing'].includes(processingActivity.status)
  const selectDocument = (item: DocumentCatalogueItem) => {
    setCategory(item.intake_category)
    setDeclaredType(item.id)
    setMessage(`${item.label} selected. Choose the source file when ready.`)
    document.getElementById('upload-zone')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  const submitFiles = async (files: File[]) => {
    const supported = files.filter((file) => /\.(csv|xlsx|xlsm|pdf)$/i.test(file.name))
    const rejected = files.length - supported.length
    if (!supported.length) {
      setMessage('No supported files were selected. Use CSV, XLSX, XLSM or PDF files.')
      return
    }
    setBusy(true)
    let completed = 0
    const failures: string[] = []
    for (const [index, file] of supported.entries()) {
      setMessage(`Clippy is processing file ${index + 1} of ${supported.length}: ${file.name}`)
      try {
        await onUpload(file, category, declaredType)
        completed += 1
      } catch (error) {
        failures.push(`${file.name}: ${error instanceof Error ? error.message : 'Upload failed'}`)
      }
    }
    const rejectedNote = rejected ? ` ${rejected} unsupported file(s) were skipped.` : ''
    const failureNote = failures.length ? ` Failed: ${failures.join(' | ')}` : ''
    setMessage(`${completed} of ${supported.length} supported file(s) processed and traced.${rejectedNote}${failureNote}`)
    setBusy(false)
  }
  return (
    <section id="section-decisions" data-section="decisions" className="scroll-dashboard-section operations-section simple-data-management">
      <div className="section-inner">
        <SectionHeading eyebrow="Business data" title="Two procedures. One traceable business database." description="Initial setup forms the company once. Recurring intake then runs continuously, updating business.db, dashboards and Clippy's compact launch context." icon={Database} />

        <div className="lifecycle-status-bar">
          <div><Database /><span><small>Canonical store</small><strong>{businessStore?.database.file || 'data/database/business.db'}</strong></span></div>
          <div><Gauge /><span><small>Current procedure</small><strong>{String(lifecycle.phase || 'initial_setup').replaceAll('_', ' ')}</strong></span></div>
          <div><Layers3 /><span><small>Data version</small><strong>v{lifecycle.data_version || pipelineStatus?.data_version || 0}</strong></span></div>
          <div><ShieldCheck /><span><small>Clippy context</small><strong>{businessStore?.clippy.updated_at ? 'Current' : 'Building'}</strong></span></div>
        </div>

        <div className="procedure-grid">
          <article className={`procedure-card ${setupComplete ? 'procedure-complete' : 'procedure-active'}`}>
            <header><span>01</span><div><small>Runs until complete</small><h3>Initial setup</h3></div>{setupComplete ? <CheckCircle2 /> : <Clock3 />}</header>
            <p>Validates the five foundation sources, builds detailed business tables and forms Clippy's first company summary.</p>
            <div className="procedure-checklist">{setupRequired.map((item) => <button key={item.id} onClick={() => selectDocument(item)} className={item.received ? 'received' : ''}>{item.received ? <CheckCircle2 /> : <UploadCloud />}<span><strong>{item.label}</strong><small>{item.received ? 'Stored and represented' : 'Required'}</small></span></button>)}</div>
          </article>
          <article className={`procedure-card ${setupComplete ? 'procedure-active' : ''}`}>
            <header><span>02</span><div><small>Runs continuously</small><h3>Recurring intake</h3></div><RefreshCw /></header>
            <p>Add operating evidence forever. Only new or changed records are incorporated before affected summaries refresh.</p>
            <div className="procedure-checklist">{recurring.map((item) => <button key={item.id} onClick={() => selectDocument(item)}><UploadCloud /><span><strong>{item.label}</strong><small>{item.file_count || 0} processed file(s)</small></span></button>)}</div>
          </article>
        </div>

        <div className="operations-grid">
          <article id="upload-zone" className="glass-card upload-studio">
            <div className="card-heading"><div><span className="eyebrow">Add evidence</span><h3>{category === 'setup' ? 'Initial company file' : 'Recurring operating file'}</h3></div>{activeProgress ? <LoaderCircle className="spin" /> : <UploadCloud />}</div>
            <div className="intake-tabs"><button className={category === 'setup' ? 'active' : ''} onClick={() => { setCategory('setup'); setDeclaredType('auto') }}><Building2 /> Initial setup</button><button className={category === 'recurring' ? 'active' : ''} onClick={() => { setCategory('recurring'); setDeclaredType('auto') }}><RefreshCw /> Recurring intake</button></div>
            <label>Document type<select value={declaredType} onChange={(event) => setDeclaredType(event.target.value)}><option value="auto">Identify automatically</option>{[...setupRequired, ...recurring].filter((item) => item.intake_category === category).map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
            <button
              className={`drop-zone ${dragActive ? 'drop-zone-active' : ''}`}
              onClick={() => fileRef.current?.click()}
              onDragEnter={(event) => { event.preventDefault(); if (!busy) setDragActive(true) }}
              onDragOver={(event) => { event.preventDefault(); if (!busy) setDragActive(true) }}
              onDragLeave={(event) => { event.preventDefault(); if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragActive(false) }}
              onDrop={(event) => {
                event.preventDefault()
                setDragActive(false)
                if (!busy && !activeProgress) void submitFiles(Array.from(event.dataTransfer.files))
              }}
              disabled={busy || Boolean(activeProgress)}
            >
              {busy || activeProgress ? <LoaderCircle className="spin" /> : <UploadCloud />}
              <strong>{activeProgress ? processingActivity?.stage_message : busy ? 'Processing file batch…' : dragActive ? 'Drop all files here' : 'Drag and drop multiple files, or click to browse'}</strong>
              <span>{activeProgress ? `${processingActivity?.progress || 0}% complete` : 'CSV, XLSX, XLSM and PDF · files are processed one at a time for safe tracing.'}</span>
            </button>
            {activeProgress && <div className="upload-progress-panel"><div><span>{processingActivity?.stage.replaceAll('_', ' ')}</span><strong>{processingActivity?.progress}%</strong></div><i><b style={{ width: `${processingActivity?.progress || 0}%` }} /></i></div>}
            <input ref={fileRef} hidden type="file" multiple accept=".csv,.xlsx,.xlsm,.pdf" onChange={(event) => { const files = Array.from(event.target.files || []); if (files.length) void submitFiles(files); event.target.value = '' }} />
            <p className="soft-note">{message}</p>
          </article>
          <article className="glass-card clippy-context-card"><div className="card-heading"><div><span className="eyebrow">Fast launch context</span><h3>What Clippy reads first</h3></div><Bot /></div><p>{businessStore?.clippy.summary_text || 'Clippy’s compact business summary will be formed when business.db is initialised.'}</p><div className="context-summary-metrics"><div><span>Sources</span><strong>{businessStore?.clippy.summary.source_count || 0}</strong></div><div><span>Tables</span><strong>{businessStore?.clippy.summary.tables_with_data || 0}</strong></div><div><span>Detail sections</span><strong>{businessStore?.clippy.detail_sections.length || 0}</strong></div><div><span>Trust</span><strong>{businessStore?.clippy.summary.data_trust?.score || 0}/100</strong></div></div></article>
        </div>

        <FileRegister title="Initial setup files" files={uploadLibrary?.files.setup || []} empty="No initial setup evidence has been uploaded." onMove={onMoveUpload} onDelete={onDeleteUpload} onRetry={onRetryUpload} />
        <FileRegister title="Recurring files" files={uploadLibrary?.files.recurring || []} empty="No recurring operating evidence has been uploaded." onMove={onMoveUpload} onDelete={onDeleteUpload} onRetry={onRetryUpload} />

        <details className="traceability-panel" open>
          <summary><span><Waypoints /><strong>Where the data went</strong></span><b>{businessStore?.lineage.length || 0} recorded steps</b></summary>
          <div className="lineage-table-wrap"><table><thead><tr><th>Stage</th><th>Operation</th><th>From</th><th>To</th><th>Rows</th><th>Status</th></tr></thead><tbody>{(businessStore?.lineage.slice(0, 40) || []).map((item) => <tr key={item.event_id}><td><span className="status-pill">{item.stage}</span></td><td>{item.operation}</td><td>{item.source_name}</td><td><strong>{item.destination_name}</strong></td><td>{item.record_count}</td><td>{item.status}</td></tr>)}</tbody></table>{!businessStore?.lineage.length && <div className="empty-state"><Waypoints /><span>Lineage appears after the next completed intake.</span></div>}</div>
        </details>

        <details className="traceability-panel">
          <summary><span><Database /><strong>What is inside business.db</strong></span><b>{businessStore?.catalog.length || 0} business tables</b></summary>
          <div className="business-catalog-grid">{(businessStore?.catalog || []).map((item) => <div key={item.table_name}><span>{item.business_domain}</span><strong>{item.description}</strong><small>{item.table_name} · {item.row_count} rows</small></div>)}</div>
        </details>

        <div className="folder-utility-row"><span><Files /> Watched folders: <code>{folderIntake?.paths.setup || 'file_drop/permanent'}</code> and <code>{folderIntake?.paths.recurring || 'file_drop/recurring'}</code></span><button className="secondary-button" onClick={() => void onScanFolderIntake()}><RefreshCw /> Scan now</button>{Boolean(classificationRepair?.plan.length) && <button className="secondary-button" onClick={() => void onRepairClassifications()}><FileCheck2 /> Repair {classificationRepair?.plan.length}</button>}</div>
      </div>
    </section>
  )
}

function SettingsSection({ setupStatus, agentContext, companyProfile, onTestModel, onClearAgentContext, onResetAllData, onRefresh }: { setupStatus: SetupStatus | null; agentContext: AgentContextStatus | null; companyProfile: CompanyProfile | null; onTestModel: Props['onTestModel']; onClearAgentContext: Props['onClearAgentContext']; onResetAllData: Props['onResetAllData']; onRefresh: Props['onRefresh'] }) {
  const [testResult, setTestResult] = useState('')
  const [clearing, setClearing] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetText, setResetText] = useState('')
  const [backupBeforeReset, setBackupBeforeReset] = useState(true)
  const provider = setupStatus?.provider || setupStatus?.model
  const test = async () => {
    setTestResult('Testing configured provider…')
    try { const result = await onTestModel(); setTestResult(JSON.stringify(result, null, 2)) } catch (error) { setTestResult(error instanceof Error ? error.message : 'Provider test failed.') }
  }
  const clear = async () => {
    setClearing(true)
    try { await onClearAgentContext(); setTestResult('Working context cleared. Base personality was preserved.') } finally { setClearing(false) }
  }
  const reset = async () => {
    if (!resetText.trim().toUpperCase().startsWith('CLEAR')) return
    if (!window.confirm('Reset all LedgerFlow business data? Uploaded evidence, databases, generated documents, company context and market intelligence will be removed.')) return
    setResetting(true)
    try {
      await onResetAllData(backupBeforeReset, resetText)
      setResetText('')
      setTestResult('LedgerFlow business data was reset. Base personality and .env configuration were preserved.')
    } finally { setResetting(false) }
  }
  return (
    <section id="section-settings" data-section="settings" className="scroll-dashboard-section settings-section">
      <div className="section-inner">
        <SectionHeading eyebrow="System and agent controls" title="External model, durable personality and local data safety" description="The NVIDIA key remains in your local .env. Ledger reads its base personality on every request and updates a separate clearable working-context file after every completed interaction." icon={Settings2} />
        <div className="settings-grid">
          <article id="model-settings" className="glass-card settings-card"><div className="card-heading"><div><span className="eyebrow">Model provider</span><h3>NVIDIA NIM</h3></div><CloudCog /></div><div className={`provider-status ${provider?.ok ? 'connected' : 'offline'}`}><span>{provider?.verified ? 'Verified' : provider?.ok ? 'Configured' : 'Needs configuration'}</span><strong>{String(provider?.configured || provider?.model || 'MODEL_PROVIDER=nvidia')}</strong><p>{String(provider?.detail || 'Add NVIDIA_API_KEY to .env and restart LedgerFlow.')}</p></div><button className="primary-button" onClick={() => void test()}><RefreshCw /> Test configured model</button><pre>{testResult}</pre></article>
          <article id="agent-context-settings" className="glass-card settings-card"><div className="card-heading"><div><span className="eyebrow">Agent continuity</span><h3>Five-layer context model</h3></div><Bot /></div><div className="context-file-map"><div><ShieldCheck /><span><strong>Base personality</strong><small>{agentContext?.base_personality_file || 'agent/BASE_PERSONALITY.md'}</small></span><b>Immutable</b></div><div><Database /><span><strong>Working context</strong><small>{agentContext?.working_context_file || 'data/context/default/agent_working_context.json'}</small></span><b>{agentContext?.working_context_events || 0} events</b></div><div><Building2 /><span><strong>Company AI context</strong><small>{agentContext?.company_context_file || 'data/context/default/company_ai_context.json'}</small></span><b>{agentContext?.company_context_present ? 'Active' : 'Created after first file'}</b></div><div><Clock3 /><span><strong>Temporal decision context</strong><small>{agentContext?.temporal_decision_context_file || 'data/context/default/temporal_decision_context.json'}</small></span><b>{agentContext?.temporal_context_present ? 'Active' : 'Created on refresh'}</b></div><div><BrainCircuit /><span><strong>Market intelligence</strong><small>{agentContext?.market_intelligence_file || 'data/context/default/market_intelligence.json'}</small></span><b>{agentContext?.market_intelligence_status || 'not started'}</b></div></div><button className="secondary-button danger-button" disabled={clearing} onClick={() => void clear()}>{clearing ? <LoaderCircle className="spin" /> : <Trash2 />} Clear working context only</button><p className="soft-note">Clearing removes recent conversational continuity only. Base personality, company onboarding, file analyses, market intelligence and uploaded evidence remain available.</p></article>
          <article id="company-profile-form" className="glass-card settings-card company-summary-card"><div className="card-heading"><div><span className="eyebrow">Company context</span><h3>{companyProfile?.company_name || 'Company profile'}</h3></div><Building2 /></div><div className="company-context-list"><div><span>Industry</span><strong>{companyProfile?.industry || 'Not set'}</strong></div><div><span>Location</span><strong>{companyProfile?.primary_location || 'Not set'}</strong></div><div><span>Objective</span><strong>{companyProfile?.current_objective || 'Not set'}</strong></div><div><span>Tax profile</span><strong>{companyProfile?.entity_type || 'company'} · {companyProfile?.gst_registered ? 'GST registered' : 'Not GST registered'}</strong></div></div><button className="secondary-button" onClick={() => void onRefresh()}><RefreshCw /> Refresh all local context</button></article>
          <article id="reset-all-data" className="glass-card settings-card reset-data-card"><div className="card-heading"><div><span className="eyebrow">Danger zone</span><h3>Reset all app data</h3></div><Trash2 /></div><p>Removes uploaded evidence, imported records, generated outputs, company context, market intelligence and working context. It does not remove the app, <code>.env</code>, NVIDIA configuration or the base agent personality.</p><label className="reset-backup-option"><input type="checkbox" checked={backupBeforeReset} onChange={(event) => setBackupBeforeReset(event.target.checked)} /><span>Create a local backup before reset</span></label><label>Type <strong>CLEAR ALL</strong> to enable reset<input value={resetText} onChange={(event) => setResetText(event.target.value)} placeholder="CLEAR ALL" /></label><button className="secondary-button danger-button reset-all-button" disabled={resetting || !resetText.trim().toUpperCase().startsWith('CLEAR')} onClick={() => void reset()}>{resetting ? <LoaderCircle className="spin" /> : <Trash2 />} Delete all data and reset app</button></article>
        </div>
      </div>
    </section>
  )
}

export default function ScrollableSite(props: Props) {
  const { activeSection, summary, accounting, tax, marketing, inventory, hr, moneyMap, transactions, validations, pipelineStatus, generatedDocuments, companyProfile, setupStatus, agentContext, uploadLibrary, intelligence, processingActivity, folderIntake, classificationRepair, dataQuality, dashboardIntegrity, businessStore, highlighted, spotlight, loading } = props

  useEffect(() => {
    document.querySelectorAll('.spotlight-target').forEach((element) => element.classList.remove('spotlight-target'))
    document.body.classList.remove('demo-spotlight-active')
    if (!spotlight) return
    const target = document.getElementById(spotlight)
    target?.classList.add('spotlight-target')
    if (target) document.body.classList.add('demo-spotlight-active')
    return () => {
      target?.classList.remove('spotlight-target')
      document.body.classList.remove('demo-spotlight-active')
    }
  }, [spotlight])

  const ready = useMemo(() => Boolean(summary && accounting && tax && marketing && inventory && hr && moneyMap), [summary, accounting, tax, marketing, inventory, hr, moneyMap])
  if (loading || !ready || !summary || !accounting || !tax || !marketing || !inventory || !hr || !moneyMap) return <div className="loading-screen"><LoaderCircle className="spin" /><span>Building the connected business story…</span></div>

  return (
    <main className="scroll-site">
      {activeSection === 'overview' && <OverviewSection summary={summary} dataQuality={dataQuality} intelligence={intelligence} dashboardIntegrity={dashboardIntegrity} onVerifyDashboard={props.onVerifyDashboard} validations={validations} transactions={transactions} />}
      {activeSection === 'money-map' && <MoneyMapSection moneyMap={moneyMap} />}
      {activeSection === 'accounts' && <AccountsSection summary={summary} accounting={accounting} dashboardIntegrity={dashboardIntegrity} onVerifyDashboard={props.onVerifyDashboard} templatesLoader={props.onGetDocumentTemplates} generate={props.onGenerateDocument} documents={generatedDocuments} refreshDocuments={props.onRefreshDocuments} highlighted={highlighted} />}
      {activeSection === 'inventory' && <InventorySection inventory={inventory} />}
      {activeSection === 'tax' && <TaxSection tax={tax} onDownload={props.onDownloadTaxWorkpaper} onAnalyse={props.onAnalyseTaxOpportunities} />}
      {activeSection === 'hr' && <HRSection hr={hr} />}
      {activeSection === 'marketing' && <MarketingSection marketing={marketing} />}
      {activeSection === 'intelligence' && <IntelligenceSection intelligence={intelligence} onStart={props.onStartCompetitorAnalysis} />}
      {activeSection === 'decisions' && <SimpleDataManagement pipelineStatus={pipelineStatus} uploadLibrary={uploadLibrary} processingActivity={processingActivity} folderIntake={folderIntake} classificationRepair={classificationRepair} businessStore={businessStore} onUpload={props.onUpload} onMoveUpload={props.onMoveUpload} onDeleteUpload={props.onDeleteUpload} onRetryUpload={props.onRetryUpload} onScanFolderIntake={props.onScanFolderIntake} onRepairClassifications={props.onRepairClassifications} />}
      {activeSection === 'settings' && <SettingsSection setupStatus={setupStatus} agentContext={agentContext} companyProfile={companyProfile} onTestModel={props.onTestModel} onClearAgentContext={props.onClearAgentContext} onResetAllData={props.onResetAllData} onRefresh={props.onRefresh} />}
    </main>
  )
}
