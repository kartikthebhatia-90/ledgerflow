# LedgerFlow 2.0 — LangGraph Department Agents and Apache Superset

## Architecture

LedgerFlow now separates evidence processing, department reasoning, visual review and final decision synthesis.

```text
Uploaded or staged files
        ↓
Deterministic extraction, normalisation and validation
        ↓
Governed data products
        ↓
LangGraph department agents (parallel when relevant)
        ├── Executive
        ├── Finance & Accounts
        ├── Tax & Compliance
        ├── Sales & Marketing
        ├── Operations & Supply
        ├── People & Payroll
        └── Market & Strategy
        ↓                         ↓
Department context files      Apache Superset dashboards
        └───────────────┬─────────┘
                        ↓
                 Ledger Supervisor
                        ↓
             Traceable business decision
```

## LangGraph runtime

The supervisor selects only relevant agents. Selected agents run from a shared state and return structured evidence, finding, recommendation, expected impact, timing and uncertainty. Their outputs are reduced into a shared collection and synthesised into one answer.

Agent prompts are editable under:

```text
agent/departments/
```

Generated department contexts are stored under:

```text
data/context/default/agents/
```

Run traces are stored in:

```text
data/database/langgraph_runs.sqlite
```

The normal Ledger assistant now uses the same orchestration for non-deterministic analysis. Existing deterministic commands, approvals and write controls remain in place.

## Apache Superset runtime

Superset runs as a separate Docker service on port 8088. LedgerFlow publishes a separate analytics snapshot:

```text
data/database/superset.duckdb
```

This avoids allowing the Superset process to compete for LedgerFlow's main `business.duckdb` writer lock.

Starter department datasets and dashboards are created automatically when possible. Their embedded UUIDs are written to:

```text
superset/generated_dashboards.json
```

The backend can also use explicit `SUPERSET_DASHBOARD_*_UUID` values from `.env`.

## Data Management map

The map displays:

1. Source files on the outer orbit.
2. Governed extraction products on the processing orbit.
3. LangGraph department agents on the agent orbit.
4. Superset department dashboards near the centre.
5. Ledger Supervisor in the centre.
6. Core context files after zooming in.

Clicking a line explains the data handed between nodes. Clicking an agent exposes its prompt, generated context and test-run control. Clicking a dashboard opens the embedded Superset view when configured.

Files and folders can be dropped anywhere on the map. Upload, classification, extraction and map refresh happen in sequence.

## Local startup

Start LedgerFlow first so `superset.duckdb` is created, then start Superset:

```powershell
.\.venv\Scripts\Activate.ps1
python .\run_app.py
```

In a second PowerShell terminal:

```powershell
.\START_SUPERSET.ps1
```

Superset requires Docker Desktop. Open Data Management after both services are running.
