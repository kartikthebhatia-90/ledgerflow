# Immersive AI Business Dashboard — Detailed Implementation Plan

> **Implementation status:** LedgerFlow 0.3 implements the local Ollama assistant, persistent final-response fix, company profile, conversation memory, dynamic validation, manual spreadsheet mapping, approval queue, basic forecasting, and optional SearXNG research. See `BUILD_STATUS.md` for the exact completed and remaining items.

## 1. Project Vision

Build a local-first business management application where the AI assistant is the main way the user interacts with the system.

The application should not feel like a normal dashboard with a permanent sidebar, fixed chat panel, and many disconnected pages. Instead, it should feel like one immersive business workspace.

The AI assistant should appear as a friendly floating character inspired by the behaviour of old desktop assistants such as Clippy, while using an original visual design.

The assistant should be able to:

- Understand natural-language business requests.
- Perform multi-step actions inside the application.
- Navigate the user to relevant business areas.
- Reveal hidden navigation only when needed.
- Highlight anomalies, ratios, transactions, assets, liabilities, or invoices.
- Explain what is wrong, why it matters, and what could be done.
- Update dashboard layouts and visualisations.
- Run business checks and calculations.
- Research current market, geopolitical, competitor, and economic conditions.
- Continue from previous sessions using persistent memory.
- Ask for approval before making sensitive or permanent changes.
- Allow the user to perform every task manually as well.

The application should initially support a small local model on modest hardware, while keeping the architecture ready for larger local models or cloud models later.

---

## 2. Core Product Experience

The main experience should follow this pattern:

```text
User asks the floating assistant a business question
        ↓
Assistant understands the request
        ↓
Assistant creates a safe sequence of actions
        ↓
Assistant performs calculations and validations
        ↓
Assistant moves through the dashboard visually
        ↓
Assistant reveals hidden navigation when required
        ↓
Assistant highlights the exact data responsible
        ↓
Assistant explains the cause and business impact
        ↓
Assistant offers next actions
        ↓
User approves, rejects, pauses, or takes manual control
```

Example request:

> Show me why my current ratio is poor.

Expected sequence:

1. The assistant checks the current-ratio calculation.
2. It highlights the current-ratio indicator.
3. It explains the current value and target.
4. It moves to the hidden navigation edge.
5. It reveals the Assets and Liabilities workspace.
6. It highlights the current assets and liabilities affecting the ratio.
7. It identifies the largest contributors.
8. It explains the likely effect on the business.
9. It offers actions such as:
   - Show overdue receivables.
   - Forecast cash flow.
   - Review supplier payments.
   - Prepare recommendations.
10. It waits for the user to choose.

---

## 3. Design Principles

### 3.1 AI as the Central Controller

The AI assistant should be the main command interface, not a small chat widget added to a traditional dashboard.

### 3.2 User Always Retains Control

The user should always be able to:

- Stop an AI-guided sequence.
- Skip a step.
- Return to the previous view.
- Take manual control.
- Open any business area directly.
- Approve or reject proposed changes.
- Disable animations.
- Temporarily hide the assistant.

### 3.3 Safe Tool-Based Execution

The AI should not directly modify frontend code, execute unrestricted terminal commands, or silently change financial records.

Instead, it should call limited, validated tools such as:

```text
navigate_to_workspace
highlight_record
apply_filter
calculate_current_ratio
reconcile_balance_sheet
find_duplicate_invoice
create_dashboard_widget
research_supplier_country
prepare_correction_proposal
```

### 3.4 Evidence Before Explanation

Every important explanation should connect:

```text
Metric or anomaly
        ↓
Calculation
        ↓
Contributing accounts
        ↓
Source transactions or invoices
        ↓
Original uploaded file
```

### 3.5 Local First, Upgradeable Later

The first version should run locally with a small model. The model layer must be replaceable so the application can later use:

- A larger local model.
- NVIDIA-hosted models.
- OpenAI-compatible models.
- Other cloud providers.
- A private self-hosted inference server.

---

## 4. Recommended Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Plotly.js
- Motion for React
- Rive
- React Router
- Zustand or Redux Toolkit
- TanStack Query
- Zod for frontend validation

### Backend

- Python
- FastAPI
- Pydantic
- LangGraph
- DuckDB
- Parquet
- Polars
- SQLite
- Pandera
- APScheduler or a lightweight background-job system

### Local AI

Initial recommendation:

```text
Ollama
Qwen 3 4B Q4
```

Low-hardware fallback:

```text
Qwen 3 2B Q4
```

Later upgrade options:

```text
Qwen 3 9B
Qwen 3 27B
NVIDIA API models
Other OpenAI-compatible models
```

### Search and External Intelligence

Initial local-first option:

```text
SearXNG
```

Optional managed providers:

- Tavily
- Brave Search API
- Alpha Vantage
- FRED
- Government economic data sources
- Industry-specific APIs

---

## 5. High-Level Architecture

```text
                         USER
                           │
                  Floating AI Assistant
                           │
                 Agent Orchestration Layer
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Dashboard Tools     Business Tools    Research Tools
        │                  │                  │
 Navigation, focus,    Accounting,        Web, markets,
 highlights, charts    validation, KPIs   competitors, geo
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                  Data and Memory Layer
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
     Parquet            DuckDB             SQLite
 Business data      Analytical queries   App state, memory,
                                           audit, approvals
```

---

## 6. Immersive Interface Design

## 6.1 Full-Screen Workspace

The application should use the full screen for the current business context.

There should be no permanently visible:

- Sidebar
- Chat panel
- Page list
- Dense toolbar
- Large fixed menu

The visible screen should focus only on:

- Current KPIs
- Relevant charts
- Current investigation
- Selected business records
- Agent guidance
- Temporary actions

---

## 6.2 Floating Assistant

The assistant should be a friendly original animated character.

Possible concept:

- A flexible metallic bookmark.
- A folded financial ribbon.
- A small floating ledger character.
- Large expressive eyes.
- Subtle business-themed accessories.
- A small speech bubble.
- Smooth but lightweight movement.

Working name:

```text
Ledger
```

### Character States

```text
Idle
Listening
Thinking
Searching
Flying
Pointing
Explaining
Warning
Celebrating
Waiting for approval
Sleeping
Error recovery
```

### Character Behaviour

The assistant should:

- Follow the pointer slightly when hovered.
- Move out of the way of important content.
- Remember its last preferred position.
- Use speech bubbles instead of a permanent chat panel.
- Remain small when idle.
- Expand only during active interaction.
- Avoid interrupting unless a critical alert is configured.
- Be draggable.
- Provide a visible stop control during sequences.

---

## 6.3 Hidden Navigation

Business areas should remain hidden until needed.

Possible areas:

```text
Company
Overview
Assets
Liabilities
Invoices
Transactions
Cash Flow
Customers
Suppliers
Reports
Validation
Market Intelligence
Settings
```

The navigation should appear from the left edge when:

- The assistant flies to the edge and reveals it.
- The user hovers at the edge.
- The user uses a keyboard shortcut.
- The user swipes from the left on touch devices.
- The user asks the assistant to show navigation.

The menu should disappear after navigation.

---

## 6.4 Guided Navigation Sequence

Example:

```text
Assistant calculates a problem
        ↓
Assistant highlights affected KPI
        ↓
Assistant explains the issue briefly
        ↓
Assistant flies to the edge
        ↓
Assistant reveals hidden navigation
        ↓
Relevant destination glows
        ↓
Workspace transitions smoothly
        ↓
Assistant moves to affected records
        ↓
Records and values are highlighted
        ↓
Assistant explains cause and impact
```

---

## 6.5 Temporary Interaction Bubbles

The assistant should use temporary bubbles such as:

```text
Ask
Investigate
Navigate
Stop
Go back
Explain more
Show source
Compare periods
Suggest actions
```

These controls should appear near the assistant only while needed.

---

## 7. Dashboard Action Language

The AI should control the interface through a validated action schema.

Example:

```json
{
  "goal": "explain_current_ratio",
  "actions": [
    {
      "type": "character_state",
      "state": "thinking"
    },
    {
      "type": "spotlight",
      "target": "current-ratio-card"
    },
    {
      "type": "character_move",
      "target": "current-ratio-card"
    },
    {
      "type": "character_say",
      "message": "Your current liabilities are greater than your current assets."
    },
    {
      "type": "character_move",
      "target": "navigation-edge"
    },
    {
      "type": "navigation_reveal"
    },
    {
      "type": "navigation_highlight",
      "destination": "assets-liabilities"
    },
    {
      "type": "navigate",
      "destination": "assets-liabilities"
    },
    {
      "type": "highlight_records",
      "record_ids": [
        "cash",
        "receivables",
        "supplier-payables",
        "short-term-loan"
      ]
    }
  ]
}
```

Every action must be validated before execution.

### Allowed Action Categories

```text
character.look_at
character.move_to
character.point_at
character.change_expression
character.say
character.wait

navigation.reveal
navigation.highlight
navigation.hide

workspace.open
workspace.transition
workspace.filter
workspace.focus

element.spotlight
element.pulse
element.connect
element.expand
element.scroll_into_view

chart.focus_point
chart.annotate
chart.compare_periods

record.highlight
record.open
record.compare
record.open_source

user.request_approval
user.offer_choices
user.pause_sequence
```

The model must not be allowed to execute arbitrary JavaScript.

---

## 8. Agent Workflow Engine

Use LangGraph as the main agent controller.

### Core Workflow

```text
START
  ↓
Understand Request
  ↓
Load Company Context
  ↓
Inspect Current Dashboard State
  ↓
Create Investigation Plan
  ↓
Run Risk and Permission Check
  ├── Safe → Continue
  └── Sensitive → Request Approval
  ↓
Execute One Tool
  ↓
Verify Tool Result
  ├── Failed → Retry or Repair
  └── Passed → Continue
  ↓
Generate Dashboard Action
  ↓
Animate and Guide User
  ↓
Explain Findings
  ↓
Offer Next Actions
  ↓
Save Checkpoint
  ↓
END
```

### Agent Responsibilities

The agent should:

- Understand the user’s goal.
- Break it into steps.
- Select approved tools.
- Track progress.
- Pause for approval when needed.
- Recover from failed steps.
- Explain results.
- Save its state.
- Resume unfinished work later.

---

## 9. Agent Permission Levels

### Level 1 — Suggest Only

The agent may:

- Read data.
- Calculate KPIs.
- Identify anomalies.
- Explain findings.
- Suggest actions.

It may not change anything.

### Level 2 — Safe Automatic Actions

The agent may:

- Navigate.
- Apply filters.
- Highlight data.
- Run calculations.
- Search the web.
- Generate temporary charts.
- Prepare reports.
- Create non-permanent dashboard views.

It must request approval before permanent changes.

### Level 3 — Trusted Workflows

The user can approve specific repeated workflows such as:

```text
Monthly invoice processing
Weekly cash-flow review
Daily validation checks
Supplier risk monitoring
```

Even at this level, the agent must not:

- Delete original files.
- Change reconciled financial data silently.
- Send payments.
- Send external communications without approval.
- Expose private company data externally without approval.

---

## 10. Business Data Ingestion

The first version should support:

- CSV
- XLSX
- XLS
- Structured exports from accounting systems

Later versions can support:

- PDF invoices
- Scanned invoices
- Bank statements
- Contracts
- Purchase orders
- Receipts

### Ingestion Pipeline

```text
Upload
  ↓
Save untouched original
  ↓
Create file hash
  ↓
Detect document type
  ↓
Inspect headers and values
  ↓
Map columns
  ↓
Validate data types
  ↓
Apply business rules
  ↓
Separate valid and invalid records
  ↓
Write valid records to Parquet
  ↓
Write invalid records to quarantine
  ↓
Refresh DuckDB views
  ↓
Update KPIs
  ↓
Update agent context
  ↓
Refresh relevant dashboard objects
```

---

## 11. Storage Strategy

Do not use Excel as the internal database.

Use:

```text
Raw files → Parquet → DuckDB
```

### Storage Responsibilities

#### Parquet

Store:

- Transactions
- Invoices
- Invoice lines
- Payments
- Assets
- Liabilities
- Customers
- Suppliers
- KPI snapshots
- External signals

#### DuckDB

Use for:

- Analytical queries
- KPI calculations
- Trend analysis
- Dashboard datasets
- Reconciliation
- Anomaly detection

#### SQLite

Use for:

- User settings
- Agent sessions
- Workflow checkpoints
- Approvals
- Dashboard layouts
- Audit logs
- Memory
- File metadata
- Validation history

#### Excel

Use only for:

- Import
- Export
- User-facing reports
- Manual review

---

## 12. Standard Business Data Model

Recommended tables:

```text
companies
company_locations
accounts
transactions
invoices
invoice_lines
payments
customers
suppliers
assets
liabilities
balance_sheet_snapshots
income_statement_snapshots
cash_flow_snapshots
budgets
external_signals
validation_issues
kpi_snapshots
decision_features
uploaded_files
agent_sessions
agent_actions
audit_log
```

Recommended common fields:

```text
company_id
source_file_id
source_row_number
record_date
currency
created_at
updated_at
validation_status
confidence_score
```

---

## 13. Validation System

## 13.1 File and Schema Validation

Checks should include:

- Missing columns
- Duplicate headers
- Invalid dates
- Mixed date formats
- Invalid amounts
- Empty rows
- Empty files
- Duplicate uploads
- Corrupted rows
- Missing invoice numbers
- Missing supplier IDs
- Invalid currency formats
- Unexpected nulls

---

## 13.2 Accounting Validation

Checks should include:

- Assets = liabilities + equity
- Debits = credits
- Invoice total = subtotal + tax − discount
- Invoice total = sum of invoice lines
- Payment matches invoice
- Paid invoice has corresponding payment
- Opening balance + movement = closing balance
- Accounts receivable matches unpaid customer invoices
- Accounts payable matches unpaid supplier invoices
- Cash movement matches transaction activity
- Tax calculations match configured rules
- Currency conversions use correct dates and rates

---

## 13.3 Business Logic Validation

Checks should include:

- Duplicate invoices
- Duplicate payments
- Unusual payment amount
- Large payment to a new supplier
- Sudden margin decline
- Sudden revenue change
- Expense outside normal range
- Invoice sequence gaps
- Delayed data entry
- Customer concentration
- Supplier concentration
- Overdue receivables
- Overdue payables
- Low cash runway
- Budget variance
- Unexpected inventory movement
- Unusual debt growth
- Working-capital deterioration

---

## 13.4 Validation Output

Example:

```json
{
  "severity": "high",
  "check": "accounting_equation",
  "description": "Assets do not equal liabilities plus equity.",
  "difference": 14820.50,
  "source_file": "balance_sheet_june.xlsx",
  "recommended_action": "Review retained earnings and current liabilities.",
  "requires_approval": true
}
```

---

## 14. Decision Features for the Agent

The agent should not receive every transaction in every prompt.

Create a compact table:

```text
decision_features
```

### Financial Features

- Cash available
- Cash runway
- Monthly revenue
- Revenue growth
- Gross margin
- Operating margin
- Net margin
- Fixed costs
- Variable costs
- Burn rate
- Current ratio
- Quick ratio
- Debt-to-equity ratio
- Working capital
- Accounts receivable
- Accounts payable
- Overdue receivables
- Overdue payables
- Inventory turnover
- Budget variance
- Estimated tax liability

### Risk Features

- Critical validation failures
- Suspicious transactions
- Customer concentration
- Supplier concentration
- Currency exposure
- Interest-rate exposure
- Revenue volatility
- Expense volatility
- Data freshness
- Missing-data percentage
- Reconciliation difference
- External risk score

### Operational Features

- Invoice processing time
- Average collection period
- Average payment period
- Revenue per customer
- Revenue per location
- Product profitability
- Service profitability
- Top cost drivers
- Seasonal patterns
- Capacity utilisation

---

## 15. Ratio and Anomaly Explanations

Whenever the agent highlights a ratio or anomaly, it should explain:

```text
What it measures
Current value
Historical value
Business-specific target
What caused it
What effect it may have
Confidence level
Recommended actions
```

Example:

```text
Metric: Current ratio
Current value: 0.72
Target: 1.20–2.00
Previous value: 1.05

Primary causes:
- Low cash balance
- High supplier payables
- Short-term loan pressure
- Slow customer collections

Possible effect:
The business may struggle to meet obligations due within the next 12 months.
```

Targets should consider:

- Industry
- Company size
- Business model
- Location
- Historical performance
- Seasonality
- User-defined goals

---

## 16. Memory and Continuity

Do not store the entire conversation as one growing file.

Use four memory layers.

### 16.1 Workflow Memory

Stores:

- Current task
- Current step
- Completed steps
- Failed steps
- Pending approvals
- Current dashboard state

### 16.2 Company Memory

Stores:

- Company type
- Locations
- Currency
- Financial year
- Suppliers
- Customers
- Business goals
- Risk thresholds
- Preferred KPIs

### 16.3 Decision Memory

Stores:

- Recommendation
- Evidence
- User decision
- Approval status
- Result
- Follow-up date

### 16.4 Conversation Summary

Stores:

- Recent objectives
- Open questions
- Important corrections
- User preferences
- Active investigation
- Current dashboard focus

### Compaction Process

```text
Keep recent messages
  ↓
Summarise older messages
  ↓
Extract confirmed facts
  ↓
Extract unresolved questions
  ↓
Preserve approvals and decisions
  ↓
Remove repeated content
  ↓
Save versioned summary
```

---

## 17. Web, Market, and Geopolitical Intelligence

The agent should research only signals relevant to the company.

### Company Exposure Profile

Store:

```text
Industry
Company size
Business locations
Customer locations
Supplier locations
Currencies
Commodities
Public competitors
Private competitors
Interest-rate exposure
Transport dependence
Regulatory exposure
```

### Relevant External Signals

Possible signals:

- Exchange rates
- Interest rates
- Inflation
- Commodity prices
- Shipping disruptions
- Supplier-country risks
- Tariffs
- Regulations
- Competitor activity
- Consumer demand
- Industry trends
- Political instability
- Sanctions
- Port disruptions
- Labour-market changes

### Research Process

```text
Identify company exposure
  ↓
Select relevant external topics
  ↓
Search trusted sources
  ↓
Extract facts and dates
  ↓
Compare against internal business data
  ↓
Estimate likely business impact
  ↓
Display citations
  ↓
Store external signal separately from confirmed internal facts
```

---

## 18. Dashboard Visualisation Rules

The agent should create dashboards through safe specifications.

Example:

```json
{
  "goal": "cash_and_supplier_risk",
  "widgets": [
    {
      "type": "kpi",
      "metric": "available_cash",
      "position": 1
    },
    {
      "type": "forecast_chart",
      "metric": "cash_balance",
      "period": "90_days",
      "position": 2
    },
    {
      "type": "aging_chart",
      "metric": "accounts_payable",
      "position": 3
    },
    {
      "type": "risk_list",
      "metric": "supplier_external_risk",
      "position": 4
    }
  ],
  "reason": "Upcoming supplier payments present the largest short-term risk."
}
```

### Allowed Visual Components

- KPI card
- Trend line
- Bar chart
- Waterfall chart
- Cash-flow chart
- Receivables aging
- Payables aging
- Forecast chart
- Risk heatmap
- Budget versus actual
- Customer concentration chart
- Supplier concentration chart
- Location map
- External-risk card
- Validation alert
- Source-document viewer

---

## 19. Model Strategy

### Initial Model

Recommended:

```text
qwen3.5:2b-q4_K_M
```

Use through Ollama.

### Low-Hardware Mode

Use:

```text
qwen3.5:2b-q4_K_M
```

Use shorter context and rely more heavily on deterministic tools.

### Upgrade Path

Later models can include:

```text
qwen3.5:9b-q4_K_M
qwen3.5:27b-q4_K_M
NVIDIA-hosted models
Other OpenAI-compatible cloud models
```

### Model Gateway

Create a provider interface:

```text
Application
  ↓
Model Gateway
  ├── Ollama
  ├── NVIDIA
  ├── OpenAI-compatible provider
  ├── Gemini
  ├── Anthropic
  └── Future self-hosted server
```

The rest of the application should not depend on a single model provider.

---

## 20. Example Environment File

```env
# Local model
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen3.5:2b-q4_K_M
MODEL_BASE_URL=http://localhost:11434
MODEL_CONTEXT_SIZE=12288
MODEL_TEMPERATURE=0.2

# Optional cloud model
CLOUD_FALLBACK_ENABLED=false
CLOUD_PROVIDER=
CLOUD_MODEL=
CLOUD_BASE_URL=
CLOUD_API_KEY=

# Agent
AGENT_AUTONOMY_LEVEL=2
AGENT_MAX_STEPS=15
AGENT_MAX_RETRIES=2
REQUIRE_APPROVAL_FOR_WRITES=true
REQUIRE_APPROVAL_FOR_EXTERNAL_DATA=true
ALLOW_TERMINAL_TOOL=false

# Search
WEB_SEARCH_PROVIDER=searxng
SEARXNG_URL=http://localhost:8080
TAVILY_API_KEY=
BRAVE_SEARCH_API_KEY=

# Storage
DATA_DIR=./data
DUCKDB_PATH=./data/database/business.duckdb
SQLITE_PATH=./data/database/application.sqlite

# Memory
MEMORY_COMPACTION_ENABLED=true
MEMORY_COMPACTION_THRESHOLD=12000
CHECKPOINT_AFTER_EACH_TOOL=true

# App
APP_SECRET=replace-with-random-secret
MAX_UPLOAD_MB=100
```

The real `.env` must never be included in source control or shared ZIP files.

---

## 21. Recommended Folder Structure

```text
immersive-business-agent/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── start.bat
├── start.sh
│
├── backend/
│   ├── pyproject.toml
│   ├── tests/
│   └── app/
│       ├── main.py
│       ├── config.py
│       │
│       ├── agent/
│       │   ├── graph.py
│       │   ├── state.py
│       │   ├── planner.py
│       │   ├── executor.py
│       │   ├── verifier.py
│       │   ├── permissions.py
│       │   ├── recovery.py
│       │   └── memory.py
│       │
│       ├── models/
│       │   ├── gateway.py
│       │   ├── ollama_provider.py
│       │   ├── cloud_provider.py
│       │   └── model_router.py
│       │
│       ├── tools/
│       │   ├── data_tools.py
│       │   ├── accounting_tools.py
│       │   ├── analysis_tools.py
│       │   ├── research_tools.py
│       │   ├── dashboard_tools.py
│       │   ├── document_tools.py
│       │   └── memory_tools.py
│       │
│       ├── ingestion/
│       │   ├── detector.py
│       │   ├── csv_reader.py
│       │   ├── excel_reader.py
│       │   ├── column_mapper.py
│       │   └── normalizer.py
│       │
│       ├── validation/
│       │   ├── schemas/
│       │   ├── accounting_rules.py
│       │   ├── business_rules.py
│       │   ├── anomaly_rules.py
│       │   └── reconciliation.py
│       │
│       ├── analytics/
│       │   ├── kpis.py
│       │   ├── feature_builder.py
│       │   ├── forecasting.py
│       │   ├── competitor_analysis.py
│       │   └── risk_scoring.py
│       │
│       ├── dashboard/
│       │   ├── action_schema.py
│       │   ├── layout_schema.py
│       │   ├── chart_queries.py
│       │   └── investigation_sequences.py
│       │
│       ├── providers/
│       │   ├── web_search.py
│       │   ├── market_data.py
│       │   └── economic_data.py
│       │
│       ├── database/
│       │   ├── duckdb_manager.py
│       │   ├── sqlite_manager.py
│       │   ├── parquet_manager.py
│       │   └── migrations/
│       │
│       └── jobs/
│           ├── scheduler.py
│           ├── validation_jobs.py
│           └── external_refresh.py
│
├── frontend/
│   ├── package.json
│   └── src/
│       ├── assistant/
│       │   ├── FloatingAssistant.tsx
│       │   ├── AssistantBubble.tsx
│       │   ├── AssistantMotion.tsx
│       │   ├── AssistantStateMachine.ts
│       │   └── AssistantControls.tsx
│       │
│       ├── navigation/
│       │   ├── HiddenNavigation.tsx
│       │   ├── EdgeTrigger.tsx
│       │   └── NavigationController.ts
│       │
│       ├── workspace/
│       │   ├── WorkspaceShell.tsx
│       │   ├── TransitionController.tsx
│       │   └── SpotlightLayer.tsx
│       │
│       ├── dashboard/
│       │   ├── widgets/
│       │   ├── charts/
│       │   ├── layout/
│       │   └── DashboardRenderer.tsx
│       │
│       ├── investigations/
│       │   ├── SequenceRunner.ts
│       │   ├── HighlightManager.ts
│       │   ├── ExplanationLayer.tsx
│       │   └── InvestigationBreadcrumb.tsx
│       │
│       ├── state/
│       ├── services/
│       ├── types/
│       └── App.tsx
│
├── shared/
│   ├── dashboard-action-schema.json
│   ├── financial-evidence-schema.json
│   └── api-contracts/
│
├── data/
│   ├── raw/
│   ├── staging/
│   ├── curated/
│   ├── quarantine/
│   ├── database/
│   ├── memory/
│   ├── checkpoints/
│   ├── audit/
│   └── exports/
│
└── samples/
    ├── assets.csv
    ├── liabilities.csv
    ├── invoices.csv
    ├── payments.csv
    └── balance_sheet.csv
```

---

## 22. Development Phases

## Phase 1 — Core Local Foundation

Build:

- FastAPI backend
- React frontend
- Ollama integration
- Replaceable model provider
- DuckDB
- Parquet storage
- SQLite application database
- CSV and Excel upload
- Basic company setup
- Core accounting validations
- Basic KPIs
- Agent chat bubble
- Agent checkpointing
- Audit log

---

## Phase 2 — Immersive Assistant

Build:

- Floating character
- Speech bubbles
- Character states
- Dragging
- Hover interactions
- Hidden navigation
- Guided navigation
- Spotlight and highlight system
- Stop, pause, skip, and return controls
- Reduced-motion mode
- Keyboard shortcuts

---

## Phase 3 — Agent Sequences

Build:

- Investigation planner
- Safe action schema
- Sequence runner
- Navigation actions
- Record highlighting
- Chart focusing
- Explanation generation
- Approval checkpoints
- Error recovery
- Sequence history

---

## Phase 4 — Business Intelligence

Build:

- Decision features
- Advanced KPI calculations
- Ratio explanations
- Anomaly detection
- Receivables aging
- Payables aging
- Cash-runway analysis
- Working-capital analysis
- Supplier and customer concentration
- Budget-versus-actual analysis

---

## Phase 5 — Web and Market Intelligence

Build:

- SearXNG integration
- Company exposure profile
- Competitor research
- Geopolitical signals
- Currency monitoring
- Interest-rate monitoring
- Commodity monitoring
- Regulatory monitoring
- Source citations
- External-risk scoring

---

## Phase 6 — Documents and Invoices

Build:

- PDF invoice support
- OCR
- Invoice extraction
- Invoice confidence scoring
- Duplicate detection
- Payment matching
- Source-document viewer
- Human confirmation workflow

---

## Phase 7 — Advanced Agent Capabilities

Build:

- Cash-flow forecasting
- Revenue forecasting
- Scenario analysis
- What-if analysis
- Automated recurring workflows
- Role-based permissions
- Multi-company support
- Cloud-model escalation
- Model routing
- Plugin system

---

## 23. First Usable Version

The first production-quality version should include:

1. Floating AI assistant.
2. Small speech bubble interaction.
3. Hidden navigation.
4. Guided movement between business areas.
5. CSV and Excel upload.
6. Assets, liabilities, invoices, payments, and balance-sheet support.
7. Basic accounting validation.
8. Current ratio, quick ratio, debt ratio, cash runway, receivables, and payables.
9. Highlighting of affected records.
10. Explanation of cause and business effect.
11. Agent approval system.
12. Ollama with a small local model.
13. Replaceable model provider.
14. DuckDB, Parquet, and SQLite.
15. Persistent memory and checkpoints.
16. Audit log.
17. Manual access to every function.
18. Stop, skip, return, and reduced-motion controls.

---

## 24. Acceptance Criteria

The first version should be considered successful when the following works reliably.

### Scenario 1 — Ratio Investigation

User asks:

> Why is my current ratio bad?

The system should:

- Calculate the ratio correctly.
- Highlight the ratio.
- Explain the current value.
- Reveal navigation.
- Move to Assets and Liabilities.
- Highlight contributing accounts.
- Show source values.
- Explain likely effect.
- Offer next actions.

### Scenario 2 — Invoice Anomaly

User asks:

> Show me the suspicious supplier payment.

The system should:

- Identify the anomaly.
- Navigate to the relevant records.
- Highlight the payment.
- Link it to the invoice.
- Explain why it was flagged.
- Offer safe actions.
- Require approval before modifying records.

### Scenario 3 — Business Guidance

User asks:

> Show me what is affecting cash flow this month.

The system should:

- Calculate inflows and outflows.
- Identify primary drivers.
- Focus the relevant chart period.
- Navigate to major contributors.
- Explain risks.
- Offer actions.

### Scenario 4 — External Risk

User asks:

> Could current events affect my suppliers?

The system should:

- Identify supplier locations.
- Research relevant events.
- Rank likely effects.
- Show sources.
- Connect external risks to supplier records.
- Suggest actions without changing data.

---

## 25. Security and Reliability Rules

1. Preserve every original uploaded file.
2. Never silently overwrite financial records.
3. Maintain source-row traceability.
4. Require approval for sensitive actions.
5. Separate AI conclusions from verified facts.
6. Display assumptions and confidence.
7. Keep an audit log of every action.
8. Never expose API keys to the frontend.
9. Never include the real `.env` in a ZIP.
10. Support backup and rollback.
11. Mark forecasts as estimates.
12. Block high-confidence recommendations when critical reconciliation errors remain unresolved.
13. Do not give the local model unrestricted terminal access.
14. Validate every dashboard action.
15. Allow the user to interrupt any agent sequence.
16. Provide keyboard and reduced-motion accessibility.
17. Keep web-retrieved information separate from internal accounting truth.
18. Require explicit approval before sending private company data to a cloud model.

---

## 26. Final Recommended Stack

```text
Frontend:
React
TypeScript
Vite
Plotly.js
Motion for React
Rive
React Router

Backend:
Python
FastAPI
Pydantic
LangGraph
Polars
Pandera

Storage:
Parquet
DuckDB
SQLite

Local AI:
Ollama
Qwen 3 4B Q4

Search:
SearXNG
Optional Tavily or Brave Search

Architecture:
Tool-based agent
Validated dashboard action language
Persistent checkpoints
User approval system
```

---

## 27. Final Product Definition

The final application should feel like:

> A living business workspace where a friendly floating AI companion understands the company, guides the user visually, investigates problems, explains the evidence, and performs safe sequences of actions—while the user remains in control at all times.

The model should communicate, plan, and guide.

The Python tools should perform the financial calculations and data operations.

The frontend should convert the agent’s validated commands into smooth navigation, highlighting, animation, and explanation.

The entire system should remain local-first, efficient, auditable, and ready to upgrade to stronger models later.
