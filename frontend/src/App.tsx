import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Bot, Moon, RefreshCw, Sparkles, Sun, Volume2, VolumeX } from 'lucide-react'
import { api } from './api'
import FloatingAssistant from './FloatingAssistant'
import ScrollableSite from './ScrollableSite'
import Sidebar from './Sidebar'
import type {
  AccountingDashboard,
  AssistantProfile,
  AgentAction,
  AgentContextStatus,
  BusinessRecord,
  BusinessStoreStatus,
  CompanyProfile,
  CompetitorIntelligenceStatus,
  GeneratedDocument,
  HRDashboard,
  FolderIntakeStatus,
  ClassificationRepairStatus,
  DataQualityDashboard,
  DashboardIntegrity,
  SemanticLayerStatus,
  DecisionContextDashboard,
  IntakeCategory,
  IntegrationSettings,
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

const workspaceNames: Partial<Record<Workspace, string>> = {
  overview: 'Overview',
  accounts: 'Accounts',
  tax: 'Tax',
  marketing: 'Marketing',
  inventory: 'Inventory',
  hr: 'HR',
  'money-map': 'Money map',
  intelligence: 'Intelligence',
  operations: 'Data management',
  settings: 'Settings',
  quality: 'Data management',
  decisions: 'Data management',
}

const sectionAlias: Partial<Record<Workspace, Workspace>> = {
  'assets-liabilities': 'accounts',
  invoices: 'accounts',
  transactions: 'accounts',
  'cash-flow': 'overview',
  validation: 'accounts',
  market: 'marketing',
  import: 'decisions',
  documents: 'accounts',
  company: 'settings',
  setup: 'settings',
}

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))
const formatMoney = (value: unknown) => new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(Number(value || 0))

type TourStep = {
  destination: Workspace
  target: string
  title: string
  message: string
}

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>('overview')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [transactions, setTransactions] = useState<BusinessRecord[]>([])
  const [validations, setValidations] = useState<BusinessRecord[]>([])
  const [companyProfile, setCompanyProfile] = useState<CompanyProfile | null>(null)
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null)
  const [accounting, setAccounting] = useState<AccountingDashboard | null>(null)
  const [generatedDocuments, setGeneratedDocuments] = useState<GeneratedDocument[]>([])
  const [tax, setTax] = useState<TaxDashboard | null>(null)
  const [marketing, setMarketing] = useState<MarketingDashboard | null>(null)
  const [inventory, setInventory] = useState<InventoryDashboard | null>(null)
  const [hr, setHr] = useState<HRDashboard | null>(null)
  const [moneyMap, setMoneyMap] = useState<MoneyMapDashboard | null>(null)
  const [integrationSettings, setIntegrationSettings] = useState<IntegrationSettings | null>(null)
  const [agentContext, setAgentContext] = useState<AgentContextStatus | null>(null)
  const [assistantProfile, setAssistantProfile] = useState<AssistantProfile | null>(null)
  const [uploadLibrary, setUploadLibrary] = useState<UploadLibrary | null>(null)
  const [intelligence, setIntelligence] = useState<CompetitorIntelligenceStatus | null>(null)
  const [processingActivity, setProcessingActivity] = useState<UploadProcessingJob | null>(null)
  const [folderIntake, setFolderIntake] = useState<FolderIntakeStatus | null>(null)
  const [classificationRepair, setClassificationRepair] = useState<ClassificationRepairStatus | null>(null)
  const [dataQuality, setDataQuality] = useState<DataQualityDashboard | null>(null)
  const [dashboardIntegrity, setDashboardIntegrity] = useState<DashboardIntegrity | null>(null)
  const [semanticLayer, setSemanticLayer] = useState<SemanticLayerStatus | null>(null)
  const [decisionContext, setDecisionContext] = useState<DecisionContextDashboard | null>(null)
  const [businessStore, setBusinessStore] = useState<BusinessStoreStatus | null>(null)
  const [clock, setClock] = useState(new Date())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [panelWarnings, setPanelWarnings] = useState<string[]>([])

  const [assistantState, setAssistantState] = useState('idle')
  const [assistantTarget, setAssistantTarget] = useState('idle')
  const [speech, setSpeech] = useState('Upload your data first, then hit ✨ and I\'ll walk you through exactly what LedgerFlow found in your files.')
  const [choices, setChoices] = useState<string[]>([])
  const [citations, setCitations] = useState<Array<{ title: string; url: string }>>([])
  const [running, setRunning] = useState(false)
  const [spotlight, setSpotlight] = useState('')
  const [highlighted, setHighlighted] = useState<string[]>([])
  const [modelLabel, setModelLabel] = useState('NVIDIA NIM · checking configuration')
  const [executionStatus, setExecutionStatus] = useState('idle')
  const [executedActions, setExecutedActions] = useState<string[]>([])
  const [reducedMotion, setReducedMotion] = useState(false)
  const [darkMode, setDarkMode] = useState(true)
  const [tourSteps, setTourSteps] = useState<TourStep[]>([])
  const [tourIndex, setTourIndex] = useState(-1)
  const runToken = useRef(0)
  const setupTourTriggered = useRef(false)
  const observedDataVersion = useRef<number | null>(null)
  const actionOutcome = useRef('')

  const loadData = useCallback(async () => {
    setError('')
    setPanelWarnings([])
    try {
      await api.health()

      const snapshot = await api.workspaceSnapshot()
      setSummary(snapshot.summary)
      setTransactions(snapshot.transactions)
      setValidations(snapshot.validations)
      setCompanyProfile(snapshot.company_profile)
      setAccounting(snapshot.accounting)
      setTax(snapshot.tax)
      setMarketing(snapshot.marketing)
      setInventory(snapshot.inventory)
      setHr(snapshot.hr)
      setMoneyMap(snapshot.money_map)
      setDataQuality(snapshot.data_quality)
      setDashboardIntegrity(snapshot.dashboard_integrity)
      setPipelineStatus(snapshot.pipeline)
      setUploadLibrary(snapshot.upload_library)
      observedDataVersion.current = Number(snapshot.pipeline.data_version || 0)

      const optionalNames = ['Pipeline', 'Generated documents', 'Integrations', 'Agent context', 'File library', 'Company intelligence', 'Folder intake', 'Classification repair', 'Business database']
      const optional = await Promise.allSettled([
        api.pipelineStatus(), api.generatedDocuments(), api.integrationSettings(),
        api.agentContext(), api.uploadLibrary(), api.competitorIntelligence(),
        api.folderIntakeStatus(), api.classificationRepairStatus(), api.businessStoreStatus(),
      ])
      if (optional[0].status === 'fulfilled') setPipelineStatus(optional[0].value)
      if (optional[1].status === 'fulfilled') setGeneratedDocuments(optional[1].value.records)
      if (optional[2].status === 'fulfilled') setIntegrationSettings(optional[2].value)
      if (optional[3].status === 'fulfilled') setAgentContext(optional[3].value)
      if (optional[4].status === 'fulfilled') setUploadLibrary(optional[4].value)
      if (optional[5].status === 'fulfilled') setIntelligence(optional[5].value)
      if (optional[6].status === 'fulfilled') setFolderIntake(optional[6].value)
      if (optional[7].status === 'fulfilled') setClassificationRepair(optional[7].value)
      if (optional[8].status === 'fulfilled') setBusinessStore(optional[8].value)

      const failures = optional.map((result, index) => result.status === 'rejected' ? `${optionalNames[index]}: ${result.reason instanceof Error ? result.reason.message : String(result.reason)}` : '').filter(Boolean)

      // Load the semantic layer after the dashboard panels have settled. The
      // endpoint reads several of the same local datasets, so serialising this
      // optional request avoids unnecessary DuckDB contention during refresh.
      try {
        setSemanticLayer(await api.semanticLayer())
      } catch (semanticError) {
        failures.push(`Analytics semantic layer: ${semanticError instanceof Error ? semanticError.message : String(semanticError)}`)
      }
      try {
        setDecisionContext(await api.decisionContext())
      } catch (decisionError) {
        failures.push(`Context board: ${decisionError instanceof Error ? decisionError.message : String(decisionError)}`)
      }
      setPanelWarnings(failures)
    } catch (err) {
      const detail = err instanceof Error ? err.message : 'Could not connect to the backend.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshSetup = useCallback(async () => {
    const [setupResult, profileResult] = await Promise.allSettled([api.setupStatus(), api.assistantProfile()])
    if (setupResult.status === 'fulfilled') {
      const status = setupResult.value
      setSetupStatus(status)
      const provider = status.provider || status.model
      if (provider?.ok) setModelLabel(`${String(provider.provider || 'NVIDIA')} ${provider.verified ? 'verified' : 'configured'} · ${String(provider.model || provider.configured || '')}`)
      else setModelLabel(`Safe planner · ${String(provider?.detail || 'model provider not configured')}`)
    } else {
      setSetupStatus(null)
      setModelLabel('Safe planner · backend model check unavailable')
    }
    if (profileResult.status === 'fulfilled') setAssistantProfile(profileResult.value)
  }, [])

  const verifyDashboard = useCallback(async () => {
    setAssistantState('processing')
    setSpeech('Rebuilding derived accounting data and checking every displayed value against business.db…')
    const result = await api.verifyDashboard()
    setDashboardIntegrity(result)
    await loadData()
    setAssistantState(result.all_reconciled ? 'explaining' : 'warning')
    setSpeech(result.message)
  }, [loadData])

  useEffect(() => {
    void loadData()
    void refreshSetup()
  }, [loadData, refreshSetup])


  useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void Promise.allSettled([
        api.uploadLibrary(), api.pipelineStatus(), api.folderIntakeStatus(), api.classificationRepairStatus(),
      ]).then((results) => {
        if (results[0].status === 'fulfilled') setUploadLibrary(results[0].value)
        if (results[1].status === 'fulfilled') {
          const next = results[1].value
          setPipelineStatus(next)
          const nextVersion = Number(next.data_version || 0)
          if (observedDataVersion.current !== null && nextVersion !== observedDataVersion.current) void loadData()
          observedDataVersion.current = nextVersion
        }
        if (results[2].status === 'fulfilled') setFolderIntake(results[2].value)
        if (results[3].status === 'fulfilled') setClassificationRepair(results[3].value)
      })
    }, 4500)
    return () => window.clearInterval(timer)
  }, [loadData])

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    document.documentElement.dataset.motion = reducedMotion ? 'reduced' : 'full'
  }, [darkMode, reducedMotion])

  const scrollToWorkspace = useCallback((destination: Workspace, behavior: ScrollBehavior = 'smooth') => {
    const section = sectionAlias[destination] || destination
    setWorkspace(section)
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        document.getElementById(`section-${section}`)?.scrollIntoView({ behavior: reducedMotion ? 'auto' : behavior, block: 'start' })
      })
    })
  }, [reducedMotion])

  const executeAction = async (action: AgentAction, token: number) => {
    if (runToken.current !== token) return false
    // Speech stays on screen long enough to read, even in reduced motion.
    const cap = action.type === 'character_say' ? 9500 : 3200
    const duration = reducedMotion && action.type !== 'character_say'
      ? Math.min(action.duration_ms ?? 0, 60)
      : Math.min(action.duration_ms ?? 600, cap)
    switch (action.type) {
      case 'character_state': setAssistantState(action.state || 'idle'); break
      case 'character_move': setAssistantTarget(action.target || 'idle'); break
      case 'character_say': setSpeech(action.message || ''); break
      case 'spotlight':
        setSpotlight(action.target || '')
        if (action.target) {
          document.getElementById(action.target)?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center', inline: 'nearest' })
        }
        break
      case 'clear_spotlight': setSpotlight(''); break
      case 'navigate':
        if (action.destination) {
          scrollToWorkspace(action.destination as Workspace)
          setSpotlight('')
          await wait(reducedMotion ? 40 : 620)
        }
        break
      case 'highlight_records': setHighlighted(action.record_ids || []); break
      case 'clear_highlights': setHighlighted([]); break
      case 'offer_choices': setChoices(action.choices || []); break
      case 'navigation_reveal':
      case 'navigation_highlight':
      case 'navigation_hide':
      case 'wait':
      case 'apply_filter':
      case 'open_source':
        break
      case 'refresh_data':
        await loadData()
        break
      case 'generate_document': {
        const format = action.output_format === 'csv' ? 'csv' : 'pdf'
        const download = await api.generateDocument(action.document_type || 'management_summary', format, action.payload || {})
        const url = URL.createObjectURL(download.blob)
        const link = document.createElement('a')
        link.href = url
        link.download = download.filename
        link.click()
        URL.revokeObjectURL(url)
        await refreshDocuments()
        actionOutcome.current = `Created and downloaded ${download.filename}.`
        break
      }
      case 'download_tax_workpaper': {
        const format = action.output_format === 'csv' ? 'csv' : 'pdf'
        await downloadTaxWorkpaper(format)
        actionOutcome.current = `Created and downloaded the tax workpaper as ${format.toUpperCase()}.`
        break
      }
      case 'test_model': {
        const result = await api.testModel()
        const ok = Boolean(result.ok)
        const detail = String(result.detail || result.response || (ok ? 'Model connection succeeded.' : 'Model connection failed.'))
        setModelLabel(ok ? `${String(result.provider || 'NVIDIA')} verified · ${String(result.model || '')}` : 'Safe planner · model test failed')
        actionOutcome.current = detail
        setSpeech(detail)
        break
      }
    }
    if (duration > 0) await wait(duration)
    return runToken.current === token
  }

  const runSequence = async (actions: AgentAction[]) => {
    actionOutcome.current = ''
    const token = ++runToken.current
    setRunning(true)
    setChoices([])
    setHighlighted([])
    setSpotlight('')
    for (const action of actions) {
      if (!(await executeAction(action, token))) return false
    }
    if (runToken.current === token) {
      setRunning(false)
      setAssistantState('idle')
      return true
    }
    return false
  }

  const stopSequence = (announce = true) => {
    runToken.current += 1
    setRunning(false)
    setAssistantState('idle')
    setAssistantTarget('idle')
    setSpotlight('')
    setChoices([])
    if (announce) setSpeech('Stopped. Manual scrolling and controls are available.')
  }

  const buildManualTour = (): TourStep[] => {
    if (!summary || !accounting || !tax || !marketing || !inventory || !hr || !moneyMap) return []
    return [
      { destination: 'overview', target: 'overview-metric-grid', title: 'Executive indicators', message: `Start with cash of ${formatMoney(summary.cash)}, a current ratio of ${Number(summary.current_ratio || 0).toFixed(2)}, monthly inflows of ${formatMoney(summary.revenue_month)}, and the current data-trust status.` },
      { destination: 'overview', target: 'clippy-overview-brief', title: 'Clippy’s business brief', message: 'Clippy converts the verified numbers into strengths, attention points and evidence status before opening detailed records.' },
      { destination: 'overview', target: 'overview-performance-chart', title: 'Operating movement', message: `This compares inflows with outflows across the observed periods. The latest inflow is ${formatMoney(summary.revenue_month)}.` },
      { destination: 'overview', target: 'overview-cash-forecast-chart', title: 'Cash outlook', message: `The forecast starts from ${formatMoney(summary.cash)} and shows a projected low point of ${formatMoney(summary.forecast_low_point)}.` },
      { destination: 'overview', target: 'overview-position-chart', title: 'Financial position', message: `Current assets are ${formatMoney(summary.current_assets)}, current liabilities are ${formatMoney(summary.current_liabilities)}, and working capital is ${formatMoney(summary.working_capital)}.` },
      { destination: 'overview', target: 'overview-profit-chart', title: 'Profit structure', message: `The latest uploaded Profit and Loss statement reports ${formatMoney(summary.profit_structure.revenue)} of revenue and ${formatMoney(summary.profit_structure.profit)} of provisional profit.` },
      { destination: 'overview', target: 'overview-invoice-chart', title: 'Invoice exposure', message: `Open invoices total ${formatMoney(summary.open_invoice_total)}, including ${formatMoney(summary.overdue_invoice_total)} overdue.` },
      { destination: 'money-map', target: 'money-map-flow', title: 'Money map', message: `This traces ${formatMoney(moneyMap.summary.revenue)} from customer sources into operating departments, tax and ${formatMoney(moneyMap.summary.retained_profit)} of retained profit.` },
      { destination: 'accounts', target: 'current-ratio-card', title: 'Accounting ratios', message: `Accounts explains the current ratio of ${Number(summary.current_ratio || 0).toFixed(2)}, quick ratio of ${Number(summary.quick_ratio || 0).toFixed(2)}, and working-capital position.` },
      { destination: 'accounts', target: 'accounts-table', title: 'Account register', message: `The register contains ${accounting.accounts.length} accounts and keeps draft or low-confidence classifications visible for review.` },
      { destination: 'inventory', target: 'inventory-dashboard', title: 'Inventory control', message: `${inventory.summary.sku_count} SKUs hold ${formatMoney(inventory.summary.inventory_value)} of inventory, with ${inventory.summary.reorder_count} reorder alerts.` },
      { destination: 'inventory', target: 'inventory-register', title: 'Replenishment register', message: 'Invoice lines with SKU and quantity can update stock automatically after the latest inventory snapshot, without double-counting earlier invoices.' },
      { destination: 'tax', target: 'tax-summary', title: 'Tax obligations', message: `The current indicative income-tax estimate is ${formatMoney(tax.summary.estimated_income_tax)} and net GST is ${formatMoney(tax.summary.net_gst)}.` },
      { destination: 'tax', target: 'tax-opportunity-review', title: 'Tax opportunity review', message: 'Use this button to scan current official ATO and business.gov.au guidance and match common concessions to the evidence in business.db.' },
      { destination: 'hr', target: 'hr-payroll-table', title: 'People and payroll', message: `HR organises ${hr.summary.headcount} people, ${formatMoney(hr.summary.gross_pay)} of gross payroll, leave, training and compliance actions.` },
      { destination: 'marketing', target: 'marketing-channel-chart', title: 'Growth analytics', message: `${formatMoney(marketing.summary.marketing_spend)} of marketing spend is compared with ${formatMoney(marketing.summary.revenue)} of revenue context across ${marketing.summary.channels} channels.` },
      { destination: 'intelligence', target: 'market-intelligence-workspace', title: 'Company intelligence', message: 'Intelligence combines internal company dimensions with separately identified competitor and market evidence, leaving unsupported peer figures blank.' },
      { destination: 'decisions', target: 'upload-zone', title: 'Data management', message: 'Initial setup forms the business once. Recurring intake then updates business.db, affected dashboards and Clippy’s compact context continuously.' },
      { destination: 'settings', target: 'model-settings', title: 'Settings and safety', message: 'Settings controls the optional AI provider, Clippy’s permanent personality, clearable working context and safe business-data reset.' },
    ]
  }

  const showTourStep = (steps: TourStep[], index: number) => {
    if (!steps.length) {
      setSpeech('The dashboard is still loading. Try the overview again after the page finishes refreshing.')
      return
    }
    if (index < 0 || index >= steps.length) {
      setTourIndex(-1)
      setTourSteps([])
      setRunning(false)
      setAssistantState('idle')
      setAssistantTarget('idle')
      setSpotlight('')
      setChoices(['Restart guided overview'])
      setSpeech('The guided overview is complete. You stayed in control of every step.')
      return
    }
    const step = steps[index]
    setTourSteps(steps)
    setTourIndex(index)
    setRunning(true)
    setAssistantState('explaining')
    setWorkspace(sectionAlias[step.destination] || step.destination)
    setSpeech(`${index + 1} of ${steps.length} — ${step.title}. ${step.message}`)
    setChoices([...(index > 0 ? ['Back'] : []), index === steps.length - 1 ? 'Finish' : 'Next', 'Stop tour'])
    window.setTimeout(() => {
      const target = document.getElementById(step.target)
      if (!target) {
        setSpeech(`${index + 1} of ${steps.length} — ${step.title}. This card has not rendered yet; press Back and Next to retry after the page finishes loading.`)
        return
      }
      target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center', inline: 'nearest' })
      setAssistantTarget(step.target)
      setSpotlight(step.target)
    }, reducedMotion ? 40 : 180)
  }

  const startManualTour = () => {
    stopSequence(false)
    const steps = buildManualTour()
    showTourStep(steps, 0)
  }

  const sendCommand = async (message: string) => {
    const normalisedMessage = message.trim().toLowerCase()
    const manualOverviewRequest = ['overview', 'start overview', 'guided overview', 'take me through the app', 'show me everything', 'give me an overview'].includes(normalisedMessage)
      || (normalisedMessage.includes('overview') && ['start', 'guide', 'guided', 'show', 'take me', 'walk'].some((term) => normalisedMessage.includes(term)))
    if (manualOverviewRequest) {
      startManualTour()
      return
    }
    stopSequence(false)
    setCitations([])
    setExecutionStatus('checking')
    setExecutedActions([])
    setSpeech('Reading verified records, durable context and the current dashboard…')
    setAssistantState('thinking')
    setRunning(true)
    try {
      const response = await api.command(message, workspace)
      setModelLabel(response.used_model)
      setCitations(response.citations || [])
      setExecutionStatus(response.execution_status || 'answered')
      setExecutedActions(response.executed_actions || [])
      const completed = await runSequence(response.actions)
      if (completed) {
        setSpeech(actionOutcome.current || response.summary)
        if (response.execution_status === 'planned') setExecutionStatus('completed')
      }
      await loadData()
    } catch (err) {
      setRunning(false)
      setExecutionStatus('failed')
      setAssistantState('warning')
      const detail = err instanceof Error ? err.message : 'The request could not be completed.'
      const backendOnline = await api.health().then(() => true).catch(() => false)
      setSpeech(backendOnline ? `The backend is online, but the agent request failed safely: ${detail}` : detail)
    }
  }


  useEffect(() => {
    if (!uploadLibrary || loading || running || setupTourTriggered.current) return
    const requiredTotal = uploadLibrary.catalogue.setup_required.length || 5
    const received = uploadLibrary.coverage.required_received || []
    const missing = uploadLibrary.coverage.required_missing || []
    const coreReady = missing.length === 0 && received.length >= requiredTotal
    if (!coreReady) return
    const signature = [...received].sort().join('|') || 'core-setup'
    const key = `ledgerflow:v331:guided-setup:${signature}`
    if (window.localStorage.getItem(key)) return
    setupTourTriggered.current = true
    window.localStorage.setItem(key, new Date().toISOString())
    setAssistantState('explaining')
    setSpeech('The core setup is complete. Press Start guided overview when you are ready; nothing will move until you choose the next step.')
    setChoices(['Start guided overview'])
  }, [uploadLibrary, loading, running])

  const chooseAction = (choice: string) => {
    if (choice === 'Next') {
      showTourStep(tourSteps, tourIndex + 1)
      return
    }
    if (choice === 'Back') {
      showTourStep(tourSteps, tourIndex - 1)
      return
    }
    if (choice === 'Finish') {
      showTourStep(tourSteps, tourSteps.length)
      return
    }
    if (choice === 'Stop tour') {
      setTourIndex(-1)
      setTourSteps([])
      stopSequence()
      return
    }
    setChoices([])
    const commands: Record<string, string> = {
      'Start guided overview': 'overview',
      'Restart guided overview': 'overview',
      'Forecast cash flow': 'Show the overview cash flow and explain the pressure',
      'Suggest improvements': 'Explain the current ratio and suggest improvements',
      'Return to overview': 'Take me to the overview',
      'Show accounts': 'Take me to accounts and explain the account table',
      'Show tax dashboard': 'Take me to tax and explain the estimate',
      'Show validation issues': 'Show account validation issues and explain the highest priority item',
      'Generate a file': 'Generate management summary PDF',
      'Generate tax workpaper': 'Generate tax workpaper PDF',
      'Explain GST position': 'Explain my GST position and show the tax dashboard',
      'Explain channel efficiency': 'Explain marketing channel efficiency and show the marketing dashboard',
      'Show revenue trend': 'Show marketing and explain revenue compared with spend',
      'Open import': 'Take me to the business data upload centre',
      'Show the money map': 'Show the money map',
      'Show data management': 'Show data management',
      'What files are missing?': 'Show the missing-document checklist and explain what is required',
      'Explain the current ratio': 'Explain the current ratio',
      'Clear agent context': 'Clear working context',
      'Test NVIDIA': 'Test NVIDIA now',
      'Review company context': 'Take me to company and agent settings',
      'Research supplier risks': 'Research current events that may affect my suppliers',
      'Start deep company analysis': 'Start deep company analysis',
      'Show latest upload': 'Read the latest uploaded file and explain its business impact',
      'Refresh validations': 'Refresh validations',
      'Flag for review': 'Flag the suspicious payment for review',
      'Leave unchanged': 'Stop the investigation',
    }
    if (choice === 'Leave unchanged') stopSequence()
    else void sendCommand(commands[choice] || choice)
  }

  const upload = async (file: File, intakeCategory: IntakeCategory, declaredDocumentType: string) => {
    stopSequence(false)
    setAssistantTarget('upload-zone')
    setAssistantState('processing')
    setRunning(true)
    setSpeech(`Receiving ${file.name} and starting the staged local processor…`)
    try {
      const started = await api.startUpload(file, intakeCategory, declaredDocumentType)
      setProcessingActivity(started)
      let current = started
      for (let attempt = 0; attempt < 1800; attempt += 1) {
        if (current.status === 'completed' || current.status === 'failed') break
        await wait(450)
        current = await api.uploadJob(started.job_id)
        setProcessingActivity(current)
        setSpeech(current.stage_message || `Processing ${file.name}…`)
      }
      if (current.status === 'failed') throw new Error(current.error_message || 'The file processor stopped before completion.')
      const result = current.result as UploadResult | undefined
      if (!result) throw new Error('The upload job finished without a result payload.')
      setRunning(false)
      setAssistantState('explaining')
      setSpeech(current.assistant_message || result.assistant_message || `${file.name} was processed and added to company context.`)
      setChoices(result.needs_mapping ? ['Open import', 'Show validation issues'] : ['Show latest upload', 'Show accounts', 'Start deep company analysis'])
      await wait(120)
      await loadData()
      window.setTimeout(() => { setAssistantState('idle'); setProcessingActivity(null) }, 1800)
      return result
    } catch (error) {
      setRunning(false)
      setAssistantState('warning')
      setProcessingActivity(null)
      const message = error instanceof Error ? error.message : 'Upload processing failed.'
      setSpeech(message)
      throw error
    }
  }

  const retryUpload = async (uploadId: number, intakeCategory: IntakeCategory, declaredDocumentType: string) => {
    stopSequence(false)
    setAssistantTarget('upload-zone')
    setAssistantState('processing')
    setRunning(true)
    setSpeech('Reprocessing the preserved source with the corrected document type…')
    try {
      const started = await api.retryUpload(uploadId, intakeCategory, declaredDocumentType)
      setProcessingActivity(started)
      let current = started
      for (let attempt = 0; attempt < 1800; attempt += 1) {
        if (current.status === 'completed' || current.status === 'failed') break
        await wait(450)
        current = await api.uploadJob(started.job_id)
        setProcessingActivity(current)
        setSpeech(current.stage_message || 'Corrective processing is running…')
      }
      if (current.status === 'failed') throw new Error(current.error_message || 'Corrective processing stopped before completion.')
      const result = current.result as UploadResult | undefined
      if (!result) throw new Error('The corrective upload finished without a result payload.')
      setRunning(false)
      setAssistantState('explaining')
      setSpeech(current.assistant_message || result.assistant_message || 'The file was reprocessed and document coverage was refreshed.')
      setChoices(result.needs_mapping ? ['Open import', 'Show validation issues'] : ['Show latest upload', 'Show accounts'])
      await wait(120)
      await loadData()
      window.setTimeout(() => { setAssistantState('idle'); setProcessingActivity(null) }, 1800)
      return result
    } catch (error) {
      setRunning(false)
      setAssistantState('warning')
      setProcessingActivity(null)
      const message = error instanceof Error ? error.message : 'Corrective processing failed.'
      setSpeech(message)
      throw error
    }
  }

  const startCompetitorAnalysis = async () => {
    stopSequence(false)
    scrollToWorkspace('intelligence')
    setAssistantTarget('market-intelligence-workspace')
    setAssistantState('processing')
    setRunning(true)
    setSpeech('Starting the opt-in company and competitor analysis…')
    try {
      const started = await api.startCompetitorIntelligence()
      setIntelligence((current) => ({ ...(current || { result: {}, context: {}, result_file: '' }), job: started }))
      for (let attempt = 0; attempt < 1200; attempt += 1) {
        await wait(600)
        const status = await api.competitorIntelligence()
        setIntelligence(status)
        const job = status.job
        if (job) setSpeech(job.stage_message || 'Analysing company and competitor context…')
        if (!job || job.status === 'completed' || job.status === 'failed') {
          setRunning(false)
          if (job?.status === 'failed') throw new Error(job.error_message || 'Deep company analysis failed.')
          setAssistantState('explaining')
          setSpeech((status.result as { summary?: string }).summary || 'Deep company analysis completed and was saved to market intelligence context.')
          setChoices(['Show latest upload', 'Return to overview'])
          await loadData()
          window.setTimeout(() => setAssistantState('idle'), 1800)
          return status
        }
      }
      throw new Error('Deep analysis did not finish within the polling window.')
    } catch (error) {
      setRunning(false)
      setAssistantState('warning')
      const detail = error instanceof Error ? error.message : 'Deep company analysis failed.'
      const backendOnline = await api.health().then(() => true).catch(() => false)
      setSpeech(backendOnline ? `The backend is online, but deep analysis stopped safely: ${detail}` : detail)
      throw error
    }
  }

  const getDocumentTemplates = useCallback(async () => (await api.documentTemplates()).records, [])
  const refreshDocuments = useCallback(async () => {
    const result = await api.generatedDocuments()
    setGeneratedDocuments(result.records)
    return result.records
  }, [])

  const downloadTaxWorkpaper = async (format: 'pdf' | 'csv') => {
    const download = await api.taxWorkpaper(format)
    const url = URL.createObjectURL(download.blob)
    const link = document.createElement('a')
    link.href = url
    link.download = download.filename
    link.click()
    URL.revokeObjectURL(url)
    await refreshDocuments()
  }

  const analyseTaxOpportunities = async (): Promise<TaxOpportunityAnalysis> => api.analyseTaxOpportunities()

  const clearAgentContext = async () => {
    const result = await api.clearAgentContext()
    setAgentContext(result)
    setSpeech('Working context cleared. Ledger’s permanent base personality and company data were preserved.')
  }

  const moveUpload = async (uploadId: number, intakeCategory: IntakeCategory) => {
    const result = await api.moveUpload(uploadId, intakeCategory)
    setSpeech(String(result.message || `The file was moved to ${intakeCategory === 'setup' ? 'Permanent setup' : 'Recurring evidence'}.`))
    await loadData()
  }

  const deleteUpload = async (uploadId: number, createBackup: boolean, confirmation: string) => {
    setAssistantState('processing')
    setSpeech('Removing the selected source and rebuilding affected dashboards…')
    try {
      const result = await api.deleteUpload(uploadId, createBackup, confirmation)
      setSpeech(String(result.message || 'The selected source was removed and dependent data was rebuilt.'))
      await loadData()
    } finally {
      setAssistantState('idle')
    }
  }

  const resetAllData = async (createBackup: boolean, confirmation: string) => {
    setAssistantState('processing')
    setSpeech('Resetting business evidence, databases, generated outputs and clearable context…')
    try {
      const result = await api.clearData('all', createBackup, confirmation)
      setProcessingActivity(null)
      setChoices([])
      setCitations([])
      setHighlighted([])
      setSpotlight('')
      Object.keys(window.localStorage).filter((key) => key.startsWith('ledgerflow:v100:guided-setup:') || key.startsWith('ledgerflow:v331:guided-setup:')).forEach((key) => window.localStorage.removeItem(key))
      setupTourTriggered.current = false
      setSpeech(`LedgerFlow was reset. ${result.backup_created ? 'A local backup was created first.' : 'No backup was requested.'} The base agent personality and .env configuration were preserved.`)
      await loadData()
      await refreshSetup()
    } finally {
      setAssistantState('idle')
    }
  }


  const scanFolderIntake = async () => {
    setAssistantState('processing')
    setSpeech('Scanning the Permanent and Recurring app folders for new evidence…')
    try {
      const result = await api.scanFolderIntake()
      const queued = Array.isArray(result.queued) ? result.queued.length : 0
      setSpeech(queued ? `${queued} pasted file(s) were queued through the staged processor.` : 'Folder scan completed. No new supported files were waiting.')
      await loadData()
    } finally { setAssistantState('idle') }
  }

  const repairClassifications = async () => {
    setAssistantState('processing')
    setSpeech('Correcting legacy file classifications and rebuilding document coverage…')
    try {
      const result = await api.runClassificationRepair()
      const count = Number(result.repair_count || 0)
      setSpeech(count ? `${count} corrective classification job(s) were started. Coverage will refresh as they finish.` : 'No classification repair was required.')
      await loadData()
    } finally { setAssistantState('idle') }
  }

  const updateAssistantProfile = useCallback(async (updates: Partial<AssistantProfile>) => {
    const saved = await api.saveAssistantProfile(updates)
    setAssistantProfile(saved)
    setSpeech(`${saved.name || 'Clippy'} personality updated to ${(saved.catalogue?.personas?.[saved.persona]?.label || saved.persona).toLowerCase()}.`)
  }, [])

  const sectionChanged = useCallback((section: Workspace) => setWorkspace(section), [])

  return (
    <div className="app-shell">
      <Sidebar
        active={workspace}
        companyName={companyProfile?.company_name || ''}
        modelLabel={modelLabel}
        darkMode={darkMode}
        onNavigate={(destination) => scrollToWorkspace(destination)}
        onToggleTheme={() => setDarkMode((value) => !value)}
        onRefresh={() => { void loadData(); void refreshSetup() }}
      />

      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-heading single-page-heading">
            <span className="eyebrow">{workspaceNames[workspace] || 'Workspace'}</span>
          </div>
          <div className="topbar-actions">
            <div className="topbar-clock" aria-label="Current analysis date and time">
              <span>{new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(clock)}</span>
              <strong>{new Intl.DateTimeFormat('en-AU', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(clock)}</strong>
              <small>{decisionContext?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone}</small>
            </div>
            <button className="icon-button" onClick={() => setReducedMotion((value) => !value)} title={reducedMotion ? 'Enable motion' : 'Reduce motion'}>{reducedMotion ? <VolumeX size={17} /> : <Volume2 size={17} />}</button>
            <button className="icon-button" onClick={() => { void loadData(); void refreshSetup() }} title="Refresh data"><RefreshCw size={17} /></button>
            <button className="icon-button" onClick={() => sendCommand('introduce yourself')} title="Clippy showcases your live data — hit this after uploading files"><Sparkles size={17} /></button>
            <button className="icon-button assistant-launcher" onClick={() => sendCommand('overview')} title="Ask Clippy for a guided overview"><Bot size={17} /></button>
          </div>
        </header>

        <AnimatePresence>
          {error && (
            <motion.div className="connection-error connection-error-detailed" initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }}>
              <strong>LedgerFlow API is offline</strong>
              <span>{error}</span>
              <small>The health check failed. Start LedgerFlow once, wait for the browser to open, and close duplicate app processes only when the error specifically reports a DuckDB lock.</small>
              <button onClick={() => void loadData()}>Retry connection</button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {!error && panelWarnings.length > 0 && (
            <motion.div className="panel-warning" initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }}>
              <div>
                <strong>Some dashboard panels could not refresh</strong>
                <span>{panelWarnings[0]}</span>
                {panelWarnings.length > 1 && <small>{panelWarnings.length - 1} additional panel warning(s). Uploaded files remain preserved.</small>}
              </div>
              <button onClick={() => void loadData()}>Retry panels</button>
              <button className="warning-dismiss" onClick={() => setPanelWarnings([])} aria-label="Dismiss panel warning">×</button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="app-content">
        <ScrollableSite
        activeSection={workspace}
        summary={summary}
        accounting={accounting}
        tax={tax}
        marketing={marketing}
        inventory={inventory}
        hr={hr}
        moneyMap={moneyMap}
        transactions={transactions}
        validations={validations}
        pipelineStatus={pipelineStatus}
        generatedDocuments={generatedDocuments}
        companyProfile={companyProfile}
        setupStatus={setupStatus}
        agentContext={agentContext}
        uploadLibrary={uploadLibrary}
        intelligence={intelligence}
        processingActivity={processingActivity}
        folderIntake={folderIntake}
        classificationRepair={classificationRepair}
        dataQuality={dataQuality}
        dashboardIntegrity={dashboardIntegrity}
        semanticLayer={semanticLayer}
        decisionContext={decisionContext}
        businessStore={businessStore}
        highlighted={highlighted}
        spotlight={spotlight}
        loading={loading}
        onSectionChange={sectionChanged}
        onUpload={upload}
        onGetDocumentTemplates={getDocumentTemplates}
        onGenerateDocument={api.generateDocument}
        onRefreshDocuments={refreshDocuments}
        onDownloadTaxWorkpaper={downloadTaxWorkpaper}
        onAnalyseTaxOpportunities={analyseTaxOpportunities}
        onRefresh={loadData}
        onVerifyDashboard={verifyDashboard}
        onTestModel={api.testModel}
        onClearAgentContext={clearAgentContext}
        onMoveUpload={moveUpload}
        onDeleteUpload={deleteUpload}
        onRetryUpload={retryUpload}
        onScanFolderIntake={scanFolderIntake}
        onRepairClassifications={repairClassifications}
        onResetAllData={resetAllData}
        onStartCompetitorAnalysis={startCompetitorAnalysis}
        onRefreshDecisionContext={async () => { const result = await api.refreshDecisionContext(); setDecisionContext(result) }}
      />
        </div>
      </div>

      <FloatingAssistant
        assistantState={assistantState}
        target={assistantTarget}
        speech={speech}
        choices={choices}
        citations={citations}
        running={running}
        reducedMotion={reducedMotion}
        modelLabel={modelLabel}
        executionStatus={executionStatus}
        executedActions={executedActions}
        processingProgress={processingActivity?.progress ?? (assistantState === 'processing' ? intelligence?.job?.progress ?? 0 : 0)}
        processingStage={processingActivity?.stage_message || (assistantState === 'processing' ? intelligence?.job?.stage_message || '' : '')}
        profile={assistantProfile}
        onProfileChange={updateAssistantProfile}
        onSubmit={sendCommand}
        onChoice={chooseAction}
        onStop={() => stopSequence()}
      />

      <div className="keyboard-hint"><Sparkles size={14} /> Ask Clippy anything, or hit ✨ to tour your live data</div>
    </div>
  )
}
