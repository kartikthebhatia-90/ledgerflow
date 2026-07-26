# LedgerFlow Feature Inventory

This document separates functionality recovered from the uploaded v0.7 archive from work added in v0.8.

## Recovered v0.7 capabilities

### Application shell

- FastAPI application serving a built React/Vite single-page frontend.
- Local Windows/macOS/Linux launcher scripts.
- Local `.env` configuration and file-backed runtime data.
- Health, setup and OpenAPI endpoints.

### Intake and source preservation

- Setup/permanent and recurring upload categories.
- CSV, XLSX, XLSM and digital-text PDF inputs.
- Maximum upload-size enforcement.
- Original evidence retention with metadata and SHA-256 fingerprint.
- Duplicate file skip.
- Upload register and mapping status.
- Quarantine/manual mapping path for unknown structures.

### Recognition and mapping

- Filename and worksheet-name hints.
- Deterministic column aliases.
- Schema signatures and saved mappings.
- Worksheet-by-worksheet Excel processing.
- Supplier invoice, sales invoice and general invoice routing.
- Balance sheet, P&L, cash flow, transactions, bank, payments, assets, liabilities, customers, suppliers, inventory, budget and market-context routing.
- Digital PDF invoice field extraction.
- Scanned/image-only PDF source preservation without OCR.

### Staged data pipeline

- Bronze immutable originals.
- Silver document-specific compressed Parquet.
- DuckDB operational tables.
- Gold KPI snapshots and decision features.
- Context company baseline, market profile, market snapshot and information requests.
- Business keys, row hashes, stable record IDs and record versions.
- New/changed/unchanged/rejected counters.
- Incremental update and manual full rebuild.
- Dependency-aware refresh.
- Backup-aware clear-data scopes.

### Accounting

- Expanded chart of accounts.
- Latest balance sheet converted to balanced opening journal.
- Supplier and sales invoice double-entry journals.
- Account and tax-code inference from keyword/supplier rules.
- Confidence and reason recorded with classifications.
- Draft journal path for low-confidence invoices.
- Posted-only trial balance and tax feed.
- Human categorisation resolution.
- Optional reusable exact-supplier rule.
- Accounts summary, register, journals and validation queue.

### Tax and compliance

- Australian company tax-profile fields.
- BAS-style G1, 1A, 1B, W1 and W2 estimates.
- Net GST estimate and control-account context.
- Accounting profit, indicative taxable income and configured-rate tax estimate.
- GST, record-keeping, STP, super and FBT obligation prompts.
- Review opportunities and evidence gaps.
- PDF/CSV tax workpaper generation.
- Official-source reference metadata.
- Direct ATO/SBR route intentionally disabled.

### Documents

- Document-template catalogue.
- PDF and CSV generation.
- Management and accounting reports.
- Operational forms such as invoices, quotations and purchase orders.
- Local export storage and document register.
- Repeat download endpoint.

### Analytics and context

- Cash, assets, liabilities, current ratio, quick ratio, working capital and debt-to-assets.
- Cash runway and 90-day forecast.
- Revenue/expense performance series.
- Open invoices, overdue amount, anomalies and validation counts.
- Company profile and market-signal context.
- Optional web research providers.
- Conversation memory, summaries, approvals and audit-related records.

### Agent

- Intent routing and deterministic factual fallback.
- Optional Ollama integration.
- Guided dashboard actions: move, navigate, highlight, spotlight and choices.
- Safe planner when a model is unavailable.
- Final response restoration after guided sequences.

## Added or changed in v0.8

### UI

- Replaced separate permanent-side-nav workspaces with a continuous scroll site.
- Added compact scroll-progress navigation.
- Added seamless full-height section transitions and active-section observation.
- Added Overview, Accounts, Tax, Marketing, Data & files and Settings story sequence.
- Added sticky Accounts document-generation rail.
- Added account register with debit, credit and balance presentation.
- Added visible DOM spotlight effect for agent targets.
- Retained user stop/manual control and reduced-motion option.

### Marketing

- New marketing dashboard endpoint.
- Uses posted marketing account `6150` when available.
- Heuristic channel grouping from supplier/description text.
- Spend-to-revenue context.
- Clearly labelled demonstration allocation when no posted marketing spend exists.
- Illustrative ROAS only in demonstration mode.
- Explicit statement that verified attribution requires campaign/CRM integrations.

### Model routing

- NVIDIA NIM is the default primary provider.
- Direct OpenAI-compatible `chat/completions` request through `httpx`.
- Provider-neutral health and Settings test.
- Ollama retained as optional local primary/fallback.
- Model-unavailable state degrades to deterministic planner.

### Prompt budget

- Dependency-free deterministic JSON budgeting.
- Prioritised high-value context fields.
- Character and list limits.
- Estimated before/after token metadata.
- Optional lazy Microsoft LLMLingua-2 adapter.
- Automatic deterministic fallback if LLMLingua is unavailable.

### Agent identity and continuity

- Permanent `agent/BASE_PERSONALITY.md` read for each command.
- Clearable `agent_working_context.json` updated after completed commands.
- Separate status and clear API.
- Settings UI displays both file paths and event count.
- Clear action preserves base personality and business data.

### Reliability

- Single-instance port check in `run_app.py`.
- Existing instance reuse.
- Clear conflict when another application owns the port.
- One Uvicorn worker to avoid embedded-database write contention.
- DuckDB connection retry and lock-specific diagnostics.
- More informative frontend backend-connection banner.
