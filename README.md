<div align="center">

# LedgerFlow

### Local-first business operations, analytics and AI assistance for growing companies

**LedgerFlow brings finance, cash flow, inventory, tax, people, marketing, market intelligence and business evidence into one connected workspace—supported by Clippy, an embedded AI copilot.**

![LedgerFlow business functions](docs/images/clippy-business-functions.png)

</div>

> **Project status:** Active personal full-stack project and product prototype. Internal figures shown in the demo are synthetic demonstration data. External research is handled separately and should remain cited and reviewable.

---

## Contents

- [Overview](#overview)
- [Vision](#vision)
- [What LedgerFlow does](#what-ledgerflow-does)
- [Clippy: the embedded AI copilot](#clippy-the-embedded-ai-copilot)
- [How the application works](#how-the-application-works)
- [Business workspaces](#business-workspaces)
- [Data trust and evidence](#data-trust-and-evidence)
- [System architecture](#system-architecture)
- [Technology stack](#technology-stack)
- [Key repository areas](#key-repository-areas)
- [Supported inputs](#supported-inputs)
- [Getting started](#getting-started)
- [Environment configuration](#environment-configuration)
- [Running and verifying the application](#running-and-verifying-the-application)
- [Privacy and security model](#privacy-and-security-model)
- [Roadmap](#roadmap)
- [Important limitations](#important-limitations)

---

## Overview

LedgerFlow is a local-first business management and intelligence workspace built for the needs of small and mid-sized companies.

The project explores a simple product question:

> How can a company use modern analytics and AI across the whole business without handing over all of its operational data, relying on disconnected subscriptions or asking employees to engineer long prompts for every task?

LedgerFlow answers this by combining:

- a connected business dashboard;
- deterministic calculations and business rules;
- traceable source documents and data lineage;
- local analytical processing;
- an OpenAI-compatible language-model gateway; and
- a human-in-the-loop assistant called **Clippy**.

The application is intended to help operators understand what is happening, identify risks, prepare evidence-backed outputs and make faster decisions while retaining human approval for sensitive actions.

---

## Vision

The long-term vision is to give mid-sized companies the ability to operate with a higher level of automation and intelligence while preserving control over their systems and data.

LedgerFlow is designed around five principles:

### 1. Interconnected operations

Finance, inventory, tax, people, marketing and market intelligence should not exist as separate information islands. A change in one area should be visible in the areas it affects.

Examples:

- an inventory purchase can affect cash, working capital and supplier exposure;
- overdue invoices can change the cash outlook and collection priorities;
- hiring plans can be considered alongside budgets and revenue forecasts; and
- external market opportunities can be assessed against internal margins and operating capacity.

### 2. Local-first control

Core business data should be processable inside the company-controlled environment. External AI services should be optional and narrowly configured rather than becoming the system of record.

### 3. Human-in-the-loop autonomy

AI may explain, prepare, monitor and recommend. Important writes, approvals and business decisions should remain reviewable by a person.

### 4. Evidence before confidence

A number, recommendation or generated report should be traceable to its supporting source, transformation and validation state whenever possible.

### 5. Tasks instead of prompt engineering

Users should select a business function, provide the minimum required input and receive a consistent output. They should not need to re-explain the entire company or workflow in every AI conversation.

---

## What LedgerFlow does

LedgerFlow provides one interface for managing and analysing multiple parts of a company.

Current and showcased capabilities include:

- executive performance summaries;
- inflow, outflow and cash-outlook analysis;
- account registers and liquidity measures;
- finance and evidence reporting;
- inventory visibility;
- tax and compliance workspaces;
- HR and operational people information;
- marketing views;
- company and competitor intelligence;
- file intake, classification and validation;
- PDF and CSV document outputs;
- data-quality and reconciliation checks; and
- AI-assisted explanations through Clippy.

The objective is not merely to place several dashboards in the same application. The objective is to create a shared business context that allows the workspaces to inform one another.

---

## Clippy: the embedded AI copilot

Clippy is the assistant layer inside LedgerFlow.

It is designed to work as an interface to trusted workflows—not as an unrestricted chatbot operating independently of the application.

### What Clippy is responsible for

Clippy can support tasks such as:

- explaining a KPI or financial movement in plain language;
- summarising business performance;
- guiding a user to the correct workspace;
- preparing structured analysis from verified context;
- generating management-ready summaries;
- identifying missing information before a task continues;
- presenting recommendations for human review; and
- converting a simple request into an approved application workflow.

### Deterministic engine and AI layer

LedgerFlow separates two types of work:

#### Deterministic application logic

Used for operations that must be repeatable and testable, including:

- calculations;
- classifications;
- validation rules;
- thresholds;
- file processing;
- data transformations;
- document generation;
- navigation and task routing; and
- approval requirements.

#### Language-model assistance

Used for tasks where language and interpretation add value, including:

- natural-language understanding;
- explanations;
- summaries;
- guided analysis;
- tailored recommendations; and
- structured text generation.

This separation reduces the risk of treating a language model as the source of truth for accounting, compliance or operational calculations.

---

## How the application works

The simplified application flow is:

```text
Business files and user inputs
              │
              ▼
Classification, validation and versioning
              │
              ▼
Bronze → Silver → Gold data pipeline
              │
              ▼
Deterministic calculations and business rules
              │
              ├──────────────► Dashboard workspaces and reports
              │
              ▼
Curated context supplied to Clippy when required
              │
              ▼
Explanation, recommendation or structured output
              │
              ▼
Human review, approval and action
```

### Step 1: Data intake

LedgerFlow receives business evidence through supported file uploads, recurring intake folders and structured application forms.

The intake process is designed to preserve the original source before downstream transformation.

### Step 2: Classification and validation

The application identifies the document type where possible, checks expected fields and records validation outcomes.

Invalid, incomplete or low-confidence information should remain visible rather than being silently accepted as trusted data.

### Step 3: Medallion data pipeline

LedgerFlow follows a Bronze, Silver and Gold approach:

- **Bronze:** original files, snapshots and source captures;
- **Silver:** cleaned, standardised and validated business entities; and
- **Gold:** curated metrics, ratios, flows, reports and AI-ready context.

### Step 4: Deterministic processing

Polars and DuckDB support fast transformations and analytical queries. Business calculations are performed in application code so they can be reproduced and reviewed.

### Step 5: Connected workspaces

The application presents the resulting information through operational workspaces such as the executive overview, Money Map, accounts, tax, inventory and intelligence.

### Step 6: Clippy assistance

When an AI-supported task is requested, LedgerFlow provides the configured model with selected, task-relevant context rather than indiscriminately exposing the complete data store.

### Step 7: Human review

Generated recommendations and sensitive actions remain subject to review. The environment setting `REQUIRE_APPROVAL_FOR_WRITES` is intended to preserve approval controls for write operations.

---

## Business workspaces

### Executive overview

The executive view brings together operating movement, cash outlook, assets and liabilities, profitability, invoice exposure and data-trust indicators.

It is designed to answer three questions quickly:

1. What is happening now?
2. What is likely to require attention next?
3. Can the displayed information be trusted?

![Executive overview](docs/images/overview.png)

### Money Map

The Money Map visualises how customer income moves through operating departments and contributes to retained profit.

It converts static totals into a connected flow so users can understand where money originates, where it is consumed and where pressure is forming.

![Money Map](docs/images/money-map.png)

### Accounts and evidence

The accounts workspace combines ratios, balances, account-register information and generated document outputs.

Its evidence-first approach is intended to connect reported values back to the files and records that produced them.

![Accounts and evidence](docs/images/accounts-evidence.png)

### Data management

The data-management workspace is the entry point for company evidence.

It supports initial setup and recurring intake, then classifies, validates, versions and traces imported information as it moves through the data pipeline.

![Data management](docs/images/data-management.png)

### Market intelligence

The intelligence workspace combines internal company-position metrics with separately sourced external competitor and market evidence.

Synthetic internal demonstration figures are clearly distinguished from real external research so they are not accidentally merged or represented as the same evidence type.

![Market intelligence](docs/images/market-intelligence.png)

---

## Data trust and evidence

LedgerFlow treats data quality as a product feature rather than an implementation detail.

The intended trust model includes:

- preservation of source files;
- document classification;
- schema and content validation;
- version tracking;
- processing status;
- error visibility;
- confidence scoring where relevant;
- reconciliation checks;
- reprocessing support; and
- traceable report generation.

This is especially important for AI-assisted analysis. Clippy should explain trusted data and clearly identify missing or uncertain context instead of inventing unsupported values.

---

## System architecture

![LedgerFlow and Clippy system architecture](docs/images/system-architecture.png)

LedgerFlow is organised into the following architectural layers:

1. **User experience layer** — business workspaces and task-oriented Clippy functions.
2. **Frontend application shell** — React, TypeScript and Vite dashboard interface.
3. **API and orchestration** — FastAPI routes, workflow routing, validation and background processes.
4. **Clippy assistant layer** — deterministic action engine plus an OpenAI-compatible LLM gateway.
5. **Data intake layer** — uploaded files, watched folders, forms and future connectors.
6. **Data pipeline** — Bronze, Silver and Gold processing tiers.
7. **Storage and compute** — Polars, DuckDB, SQLite and versioned local evidence.
8. **Analytics and outputs** — dashboards, reports, document trails and optional Superset integration.

---

## Technology stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | React | Component-based user interface |
| Frontend language | TypeScript | Typed application code |
| Frontend tooling | Vite | Development and production build tooling |
| Backend | FastAPI | API routes, orchestration and SPA hosting |
| Application runtime | Uvicorn | ASGI server |
| Data processing | Polars | Fast dataframe transformations |
| Analytical database | DuckDB | Local analytical queries |
| Application metadata | SQLite | App state and supporting metadata |
| AI gateway | OpenAI-compatible chat completions | Model-provider abstraction |
| Current configured provider | NVIDIA NIM | Hosted OpenAI-compatible model access |
| Extended analytics | Apache Superset via Docker | Optional analytical dashboards |

The normal packaged application can use the included `frontend/dist` build. Node.js is only required when rebuilding the frontend.

---

## Key repository areas

The important areas of the project include:

```text
ledgerflow_dashboard/
├── agent/
│   └── BASE_PERSONALITY.md        # Base behaviour and tone for Clippy
├── backend/
│   ├── app/
│   │   └── main.py                # FastAPI routes and SPA hosting
│   └── requirements-llmlingua.txt # Optional prompt-compression dependency
├── frontend/
│   ├── src/                       # React and TypeScript source
│   └── dist/                      # Production frontend build
├── data/                          # Local application data and evidence
├── docs/
│   └── images/                    # README screenshots and architecture graphics
├── .env.example                   # Safe configuration template
├── setup_and_run.bat              # Windows setup and launcher
├── setup_and_run.sh               # macOS/Linux setup and launcher
└── README.md
```

Do not commit local runtime data, API keys, virtual environments, caches or generated temporary files.

---

## Supported inputs

LedgerFlow supports or is designed around the following intake formats:

- CSV;
- XLSX;
- XLSM; and
- digital-text PDF.

Optional local Tesseract OCR can be enabled for scanned PDFs. OCR should be treated as a fallback because extracted text may require additional validation.

A complete accounting demonstration commonly uses source material such as:

- Balance Sheet;
- Profit and Loss Statement;
- Cash Flow Statement;
- Chart of Accounts; and
- Business Requirements Document.

---

## Getting started

### Prerequisites

For the standard Windows setup:

- Windows 10 or 11;
- Python 3.11 or a compatible installed Python version;
- Git;
- an NVIDIA API key only when NVIDIA-backed AI features are required; and
- Docker Desktop only when using the optional Apache Superset integration.

Node.js 22 or later is only required when rebuilding the frontend. It is not required for normal use when `frontend/dist` is already included.

### 1. Open the project in VS Code

From PowerShell:

```powershell
cd D:\projects\5\ledgerflow_dashboard
code .
```

### 2. Create the local environment file

Copy the safe example file:

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code and add your own local values. Never commit this file.

### 3. Run the Windows launcher

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_and_run.bat
```

The launcher is designed to:

- create `.venv` when required;
- install backend dependencies;
- use the included frontend build or rebuild it when missing;
- create `.env` from `.env.example` when necessary;
- prevent duplicate application processes;
- wait for the API health endpoint; and
- open or expose the application at the default local address.

### 4. Open LedgerFlow

```text
http://127.0.0.1:8000
```

---

## Environment configuration

A safe example configuration for NVIDIA NIM is shown below. Replace placeholder values only inside your local `.env` file.

```dotenv
MODEL_PROVIDER=nvidia
NVIDIA_API_KEY=replace_with_your_local_key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=openai/gpt-oss-20b
MODEL_TIMEOUT_SECONDS=35
MODEL_MAX_OUTPUT_TOKENS=420
AGENT_AI_ROUTING_MODE=hybrid

PROMPT_COMPRESSION_PROVIDER=
AGENT_BASE_PERSONALITY_FILE=agent/BASE_PERSONALITY.md
AGENT_CONTEXT_MAX_EVENTS=40
REQUIRE_APPROVAL_FOR_WRITES=true

DATA_DIR=data
DUCKDB_CONNECT_RETRIES=5
WEB_SEARCH_PROVIDER=
```

### Important environment variables

| Variable | Purpose |
|---|---|
| `MODEL_PROVIDER` | Selects the configured model-provider integration |
| `NVIDIA_API_KEY` | Local secret used for NVIDIA NIM requests |
| `NVIDIA_BASE_URL` | OpenAI-compatible NVIDIA API base URL |
| `NVIDIA_MODEL` | Model identifier used by the application |
| `MODEL_TIMEOUT_SECONDS` | Maximum model-request duration |
| `MODEL_MAX_OUTPUT_TOKENS` | Output-token limit for model responses |
| `AGENT_AI_ROUTING_MODE` | Controls routing between deterministic and AI-supported behaviour |
| `PROMPT_COMPRESSION_PROVIDER` | Optional prompt-compression configuration |
| `AGENT_BASE_PERSONALITY_FILE` | Clippy base-instruction file |
| `AGENT_CONTEXT_MAX_EVENTS` | Maximum retained context events used by the agent layer |
| `REQUIRE_APPROVAL_FOR_WRITES` | Requires review before configured write actions |
| `DATA_DIR` | Local application-data directory |
| `DUCKDB_CONNECT_RETRIES` | Retry count for DuckDB connections |
| `WEB_SEARCH_PROVIDER` | Optional external research-provider configuration |

The configured NVIDIA route uses:

```text
{NVIDIA_BASE_URL}/chat/completions
```

### Optional LLMLingua support

```powershell
python -m pip install -r backend/requirements-llmlingua.txt
```

Only install this optional dependency when prompt compression is required by your configuration.

---

## Running and verifying the application

### Health check

Once the app is running, verify the backend:

```text
http://127.0.0.1:8000/api/health
```

A successful health response confirms that the FastAPI service is available.

### Manual development server

The launcher is recommended for normal use. For backend development, the FastAPI app can be started from the backend directory:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Return to the project root afterwards:

```powershell
cd ..
```

### Frontend rebuild

Only rebuild the frontend when modifying React or TypeScript source and when Node.js is installed:

```powershell
cd frontend
npm install
npm run build
cd ..
```

The resulting production files are written to `frontend/dist` and served by the FastAPI application.

### Refresh after an update

After replacing application files or rebuilding the frontend:

1. stop any running LedgerFlow, Python or Uvicorn process;
2. preserve `.env` and the `data` directory;
3. run `setup_and_run.bat` again; and
4. use `Ctrl+F5` in the browser to force a clean refresh.

---

## Privacy and security model

LedgerFlow is designed to support a company-controlled deployment model.

### Local-first processing

- Polars, DuckDB and SQLite run locally.
- Source evidence can remain within the configured local data directory.
- Deterministic calculations do not require an external language model.
- The frontend and backend can run on the same controlled machine or internal environment.

### Controlled model access

AI requests should receive only the context required for the selected task. API keys are stored in `.env` and must not be embedded in frontend code or committed to Git.

### Human approval

Sensitive actions should remain reviewable. Approval controls are especially important for:

- financial writes;
- file changes;
- external communications;
- compliance outputs;
- employee-related actions; and
- automated recommendations with material business impact.

### Repository safety

The following must remain outside Git:

- `.env`;
- `.venv/`;
- local databases;
- uploaded company documents;
- generated evidence containing confidential information;
- private logs;
- API keys; and
- personal or customer data.

---

## Roadmap

Potential future development includes:

- fully local OpenAI-compatible model deployment;
- additional accounting and business-system connectors;
- role-based access controls;
- configurable approval chains;
- scheduled monitoring and alerts;
- expanded evidence and audit trails;
- reusable task blocks for common business workflows;
- supplier, customer and recruitment research;
- private internal knowledge search; and
- job-search workflows that can analyse a vacancy link, compare it with a stored master resume, produce a tailored resume and cover letter, prepare interview questions and record the application.

These roadmap items describe the product direction and should not be interpreted as completed functionality unless they are present in the running version.

---

## Important limitations

- LedgerFlow is currently a personal project and product prototype.
- Demonstration internal financial figures are synthetic.
- External research may change and should be verified from cited sources.
- Language-model responses can be incomplete or incorrect and require review.
- OCR output can contain extraction errors.
- The application does not replace professional accounting, tax, legal, employment or compliance advice.
- No autonomous system should perform material business actions without appropriate permissions, validation and human oversight.

---

## Project purpose

LedgerFlow demonstrates how a modern business platform can combine local analytics, traceable evidence, deterministic workflows and practical AI assistance.

Its central product principle is:

> **One connected business context, controlled by the company, with AI assistance built around trusted workflows rather than unrestricted prompting.**

