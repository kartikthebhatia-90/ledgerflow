# 3.3.5 — Clippy rename complete, manual-only intro

- Agent renamed to Clippy everywhere (was Robert in agent.py, BUSINESS_ANALYST_METHOD.md). Backend now also scrubs any residual "Robert" from model labels.
- Introduction showcase is now purely manual: upload your data, go to Overview, hit ✨. No auto-fire on first launch.
- Idle speech now tells you the intended flow: upload first, then hit ✨.
- Intro narration updated: greets with your company name after upload, closes with a punchy LinkedIn-ready sign-off.

# 3.3.5 — Clippy rename + user-data-aware showcase

- Agent renamed from Robert to Clippy everywhere: backend (agent, context, business_store, main, pipeline), frontend (App, FloatingAssistant, ScrollableSite, types, styles), personality file and assistant profile.
- Introduction action completely rewritten: instead of a generic tour, Clippy now showcases the user's *real* uploaded data. Sections are included only if they have data (money map needs revenue, tax needs an estimate, intelligence needs competitor results). Company name, cash balance, current ratio and revenue are quoted live from business.db.
- No-data path: if zero files are loaded, Clippy directs straight to the upload zone and explains what files are needed.
- Auto-intro on first launch removed — Clippy now waits for the user to hit ✨ after uploading files, so the showcase is always about real data.
- Default speech placeholder updated to guide the user to upload first, then hit ✨.

# 3.3.4 — Speech bubble always stays on screen

- When Robert floats to a card near the top of the viewport, his speech bubble now flips to open BELOW him (with the tail arrow flipped to point up), instead of extending above the screen where it was unreadable.
- The narration text is height-capped to the viewport and scrolls internally in the rare case it is too long, so the bubble can never leave the screen on any monitor size.
- Robert's anchor position is clamped below the top bar and above the bottom edge with safer margins.

# 3.3.3 — Hosted product showcase (Clippy as demo host)

- The introduction is now a full auto-advancing product showcase: Robert floats to each workspace card, dims the rest of the page, spotlights the feature and narrates it like a demo host. Runs across Overview, analyst brief, cash outlook, Money Map, Accounts, Inventory, Tax, HR, Marketing, Intelligence and Data Management (~2.5 minutes; ideal for a LinkedIn screen recording).
- Speech is paced to reading speed (~330 ms per word, 3–9 s per line); the old 3.2 s hard cap no longer truncates narration.
- Spotlight now scrolls the card to the centre of the viewport, and Robert re-anchors to his target while the page scrolls, so he genuinely hovers over each feature.
- A dim veil covers everything except the spotlighted card during the showcase, giving a clean product-demo look on video.
- New triggers: "show me around", "give me a demo", "product tour", plus all previous introduction triggers, the top-bar Sparkles button and the once-per-browser first launch. Stop is available at every moment.

# 3.3.2 — Clippy introduction, UI refinement layer

- Robert (Clippy) now introduces himself with a new deterministic agent action. Triggers: first-ever launch (once per browser), the new Sparkles button in the top bar, or typing "introduce yourself", "who are you", "hello", "what can this app do". The introduction adapts to setup state, quotes real business.db figures, and ends with tappable next steps. Works without any AI key.
- New `greeting` character state: wave animation, raised brows, gold sparkle. Fully disabled under reduced motion.
- UI refinement layer (theme unchanged): spotlight recoloured from off-palette green to the theme gold accent; card hover lift; unified button transitions; accent keyboard-focus rings; themed thin scrollbars; clearer choice chips; table row hover; paper-note speech bubble with gold spine.
- Version bumped to 3.3.2 across run_app.py, FastAPI, package.json and cache-busting URL.

# 3.3.1 — Manual tour and operating workspaces

- Replaces the timed guided overview with Clippy-controlled Next, Back, Finish and Stop buttons.
- Corrects the walkthrough order and scrolls each target card only after its page is rendered.
- Adds invoice-linked Inventory management with snapshot-aware double-count protection, reorder controls and stock search.
- Adds a themed HR workspace for payroll, PAYG, super, departments, leave, training and HR actions.
- Adds a Money Map that traces bank receipts through operating departments, estimated tax and retained profit.
- Adds an official-source Australian tax opportunity review with evidence matching, current-source search and clear accountant-review boundaries.
- Adds deterministic Robert navigation for Inventory, HR and Money Map.

# 3.3.0 — Complete synthetic business story

- Ships a prepared 22-source synthetic business across 18 permanent setup workbooks and four recurring operating workbooks.
- Covers financial statements, chart of accounts, banking, receivables, payables, payroll, tax, fixed assets, inventory, customers, suppliers, contracts, market evidence, budget and forecast.
- Reconciles cash to bank, debtors to accounts receivable, creditors to accounts payable, inventory detail to the balance sheet and the trial balance to zero.
- Prevents opening-balance invoices from being double-posted while preserving their account and ageing evidence.
- Expands account mapping, payroll tax evidence and marketing evidence for a complete real-business-style story.
- Keeps the canonical `business.db`, source registry, lineage, analyst context, lifecycle state and Robert's process memory together.
- Includes the original synthetic source pack for inspection or reload and intentionally excludes `.env`.

# 3.2.0 — Reconciled dashboard data and dark Accounts

- Makes the posted journal ledger the shared balance source for Accounts, Overview ratios, cash, financial-position charts and Robert's brief.
- Falls back to the latest uploaded profit-and-loss snapshot when transaction rows are unavailable, so uploaded statement data appears in the Overview performance chart.
- Adds independent Chart ↔ business.db reconciliation checks with loaded/empty status, plotted-row counts and source traceability.
- Adds a Verify and reload action that rebuilds accounting outputs, rechecks database values and refreshes all pages.
- Restyles Accounts as a dark ruled notebook that matches the full application theme.

# 3.1.0 — Visible AI charts and overview brief

- Renders Intelligence charts from verified company dimensions even when a saved legacy result contains no chart payload.
- Adds a visible build marker to Overview and Intelligence so stale installations are obvious.
- Adds Robert's source-backed business brief to Overview with strengths, watch items and evidence status.
- Keeps synthetic internal figures visibly separate from current external research.

# 3.0.1 — Intelligence chart recovery and live competitor evidence

- Materialises both Intelligence chart datasets instead of returning blank AI planning slots.
- Automatically upgrades saved v1 Intelligence results when they are opened.
- Adds no-key current web research through DDGS, while retaining optional SearXNG support.
- Uses NVIDIA only to extract named competitors grounded in returned source snippets.
- Separates synthetic internal figures from current real-company research.
- Adds cache prevention and a visible Intelligence engine version for update verification.
- Keeps current-ratio navigation linked to the notebook-style Accounts ratio card.

# 3.0.0 — business.db and Robert

- Renamed and automatically migrates the canonical DuckDB store to `data/database/business.db`.
- Added detailed business context, compact launch summaries, source registry, table catalogue, process memory and source-to-dashboard lineage inside `business.db`.
- Added two explicit procedures: Initial setup and continuous Recurring intake.
- Replaced page-specific department agents with Robert, one company-wide senior business analyst.
- Robert reads a compact launch summary first and opens detailed database sections only when required.
- Mirrored legacy context-file information into traceable database sections.
- Replaced the complex architecture canvas with a compact lifecycle, file register, lineage table and database catalogue.
- Removed LangGraph department-agent dependencies and legacy runtime activation.

# 2.1.0 — Connected refresh, page readiness and cleaner data management

- Added one coherent workspace snapshot for Overview, Accounts, Tax, Marketing, files and trust checks.
- Every new backend data version now invalidates and reloads all primary dashboard pages, including watched-folder uploads.
- Added explicit ready/provisional/blocked checks for every primary page.
- Restored the full upload and file-management workspace, which previously existed but was not rendered.
- Simplified the permanent, optional and recurring file catalogues with progressive disclosure.
- Removed the unused Zod frontend dependency.
- The portable distribution excludes virtual environments, caches, secrets and duplicate legacy build assets.
- Analytics continue to use Polars for fast dataframe work and DuckDB/Parquet for local analytical storage, with OpenPyXL, PyMuPDF and pypdf for source-specific extraction.

# 2.0.3 — Business Analyst Supervisor, voice interruption and file registers

- Reworked open-ended analysis into Frame → Route → Department analysis → Challenge → Decision stages.
- Added direct governed data packets for Finance, Tax, Marketing, Operations, People, Market and Executive agents.
- Broad business questions consult every enabled department agent; focused questions route to the relevant specialists plus Executive.
- Added an evidence challenge pass for conflicts, unsupported claims, missing evidence and material risks.
- Added editable assistant personas and answer-depth profiles that apply to the supervisor and department agents.
- Added continuous microphone conversation, automatic answer speech and barge-in interruption when the user starts speaking.
- Added collapsed Permanent files and Temporary / recurring files registers to Data Management.
- Added visible business-analysis stages and trace history to the architecture map.
- Removed the repeated inner Data Management title; the yellow workspace heading remains the only page title.
- Constrained the assistant answer panel so long responses remain scrollable rather than covering the workspace.

# 2.0.2 — Clean app, async agents and single headings

- Replaced synchronous `SqliteSaver` with `AsyncSqliteSaver` for `ainvoke` execution.
- Added `aiosqlite` and clean async checkpoint connection shutdown.
- Separated agent-run records from LangGraph checkpoint storage.
- Full reset now removes uploaded source files, derived AI context, agent runs and checkpoint databases.
- New full package starts without company data or a default company profile.
- Preserved full-map file and folder drag-and-drop.
- Removed the repeated white page title; the yellow workspace label is now the only page heading.
- Retained the Australia/Melbourne timezone fallback and `tzdata` dependency.

# 2.0.0 — LangGraph Department Agents + Apache Superset

- Rebuilt open-ended AI analysis around a LangGraph supervisor and seven department agents.
- Added editable department prompts, generated department context files and local run traces.
- Added Apache Superset Docker integration, separate analytics snapshot, starter datasets/dashboards and embedded guest-token bridge.
- Replaced the source-to-app map with a source-to-product-to-agent-to-dashboard-to-supervisor architecture map.
- Kept file/folder drag-and-drop directly on the map and removed the duplicate upload/pipeline panel.
- Preserved deterministic routines, approvals and source inclusion/exclusion controls.

# Changelog
## 1.4.6 — Restored collapsible panels and whole-folder drop

- Restores Permanent company knowledge, Broader operating context and Recurring operating evidence as collapsed drawers instead of deleting them.
- Keeps All uploaded and staged files and AI context files as collapsed drawers.
- Hides the legacy duplicate upload/pipeline centre from Data Management.
- Supports dropping multiple files or a complete nested folder anywhere on the lineage map.
- Adds Add files and Add folder controls inside the visual.
- Automatically opens the all-source drawer after a successful upload.
- Uses cache-busted frontend assets.


## 1.4.4 — Interactive Data Processing Map

- Redesigned Data Management as a minimal source → extraction → business area → Ledger AI constellation.
- Added full-map drag-and-drop upload with automatic processing and immediate map refresh.
- Added clickable connections that explain the extraction, validation, publishing and AI-decision step.
- Added source-node extraction summaries and editable classification, inclusion, processing order, products, business areas and transformation instructions.
- Kept every staged, processed and archived source visible, including bank statements.
- Moved source and AI-context inventories into collapsed drawers and removed the separate upload/pipeline workspace.
- Made core context nodes appear only after zooming in while keeping every context file accessible from the compact list.
- Added editable business_analyst_context.json, market_analysis_template.json and market_analysis_context.json to the actual agent prompt.
- Updated competitor analysis to combine the internal business context, market template, market orchestration context and verified market report.
- Removed the pipeline-pulse presentation and cache-busted the standalone map.

## 1.4.3 — Editable Data Lineage Constellation

- Restored the constellation visual instead of the department pipeline.
- Replaced source priority with explicit source -> extraction product -> app section -> Ledger AI lineage.
- Added editable file inclusion, document classification, processing order, extraction products, app-section use and transformation notes.
- Added editable processing-product routes and context-to-section connections.
- Updated the AI prompt to obey visible lineage rather than vague influence levels.
- Added cache-busted 1.4.3 frontend assets.


## 1.3.0 — Data Management

- Combined Context Board and Data & Files into one Data management workspace.
- Removed the standalone Data trust navigation page while retaining its checks and overview metric.
- Added direct discovery of staged files under data/source_files before database ingestion.
- Added safe frontend fallback nodes so the context canvas cannot remain blank during an API error.
- Updated assistant navigation, guided walkthroughs and semantic dashboard metadata.

## 1.2.0 — Context Constellation

- Replaced the temporal decision dashboard with an interactive source-to-AI Context Board.
- Added draggable context levels, decision lenses, source editing and editable context files.
- Added context-board persistence to the separate decision SQLite database.
- Added prompt filtering so excluded sources and disabled context layers do not influence strategic AI reasoning.
- Added protected context-file backups and deterministic board explanations.

## 1.1.0 — Temporal Decision Context

- Added a live date and time display to the dashboard top bar.
- Added a separate `decision_context.sqlite` database.
- Added `temporal_decision_context.json` to the durable agent context.
- Added the Decision Context page with source chronology, freshness, analysis history and source-to-decision lineage.
- Added deterministic agent navigation and refresh commands for Decision Context.
- Refreshes temporal context after uploads, deep analysis and data reset.
- Added Australia/Melbourne as the default configurable application timezone.

## 1.0.0 — Data Analytics action engine and semantic dashboard

- Added an executable agent action registry; action requests now run or return an exact blocker instead of producing click-by-click instructions.
- Added direct agent execution for folder scanning, classification repair, validation refresh, company analysis, document generation, tax workpapers, NVIDIA testing, context clearing and protected reset navigation.
- Added `analytics/semantic_layer` with metric definitions, source precedence, dashboard contracts and action ownership.
- Added `/api/analytics/data-quality` and `/api/analytics/semantic-layer`.
- Added a Data Trust dashboard with transparent severity-weighted scoring, source coverage, reconciliation checks and metric readiness.
- Reconciled Overview open-check counts with business, account and tax review queues.
- Added an honest sparse-data marketing fallback: current-period bars replace a misleading zero-heavy trend.
- Added recurring-document coverage to the shared coverage model.
- Added compatible classification groups so the assets/liabilities ratio bridge is not incorrectly reprocessed as a filename mismatch.
- Added stale competitor-analysis recovery after an interrupted process.
- Added `skipped_duplicate` display status for exact duplicates.
- Updated the guided Overview to include Data Trust and use the complete open-review count.
- Updated frontend and API versions to 1.0.0.

## 0.9.4 — Guided analytics and folder intake

- Added an editable, deterministic whole-dashboard walkthrough for the `overview` command.
- Gated the walkthrough until all five required setup documents are valid.
- Added an automatic one-time setup-completion greeting and guided tour.
- Removed oversized section titles while retaining compact blue eyebrow labels.
- Converted Overview into an analytics-only workspace with five explanatory chart groups.
- Added watched `file_drop/permanent` and `file_drop/recurring` folders plus archive handling.
- Added automatic startup classification repair for legacy misclassified files.
- Fixed Cash Flow, BRD, Use Cases, Fixed Asset and aged-report routing from filenames.
- Fixed supplier invoices remaining in Permanent setup.
- Optimised corrective reprocessing to avoid an unnecessary intermediate dashboard rebuild.
- Added provisional Profit & Loss tax basis when posted journals cover only a partial reporting period.

## 0.9.2 — File correction and safe reset

- Added per-upload move controls between Permanent setup and Recurring evidence.
- Added source-aware per-upload deletion with optional local backup.
- Rebuilds accounting, analytics and company AI context after a selected source is removed.
- Added a typed-confirmation full reset in Settings while preserving `.env`, NVIDIA configuration and the base personality.
- Fixed Business Requirements and other contextual PDFs being misread as zero-value invoices.
- Fixed required-document coverage counting failed or incorrectly categorised uploads.
- Fixed failed uploads being blocked as exact duplicates on retry.
- Added active-upload guards to move, delete and reset operations.
- Verified all primary dashboards remain available after a file deletion and after a full reset.

## 0.9.0 — File intelligence and isolated processing

- Added immediate staged upload jobs with persisted progress.
- Added a persistent isolated business worker for serial DuckDB/Polars processing.
- Added deterministic file-specific analysis and initial-versus-incremental assistant messages.
- Added durable company AI context and separate market-intelligence context.
- Added permanent required/recommended and recurring document catalogues.
- Added payroll ingestion, super review inputs, and bank-to-invoice reference matching.
- Added optional local Tesseract OCR for image-only PDFs.
- Added opt-in Company Intelligence with verified comparison and two agent chart slots.
- Fixed file-action intent routing and false backend-outage handling.
- Added hybrid AI routing so routine file/accounting/tax requests bypass NVIDIA and respond through deterministic code.
- Reduced the default model timeout to 35 seconds for bounded interactive recovery.
- Added worker diagnostics and health-gated startup.

## 0.8.0 — 15 July 2026

### Added

- Continuous scroll dashboard with Overview, Accounts, Tax, Marketing, Data & files and Settings sections.
- Compact progress navigation and visible agent spotlight.
- Sticky Accounts document-generation rail.
- Marketing dashboard and `/api/marketing/dashboard`.
- NVIDIA NIM primary provider and `/api/setup/test-model`.
- Deterministic prompt budgeting and optional LLMLingua-2 support.
- Permanent agent base personality and clearable working continuity.
- `/api/agent/context` status and clear operations.
- Single-instance launcher and DuckDB lock retries/diagnostics.
- Architecture, feature-inventory and troubleshooting documentation.

### Changed

- Replaced the permanent global sidebar with a connected scroll experience.
- Made setup/model status provider-neutral.
- Updated assistant routes to the new section IDs.
- Preserved Ollama as an optional local provider.
- Corrected the tax dashboard to use `estimated_taxable_income`/`accounting_profit` from the backend.

### Retained

- v0.7 staged intake pipeline, accounting engine, tax workpapers, document generation, validations, approvals and company/market context.

## 0.7.0

- Automatic invoice recognition and mapping.
- Double-entry accounting, draft/posted journals and human validation.
- Business Document Centre.
- Australian Tax & Compliance workspace and workpapers.

## 1.4.5 — Source Discovery Hotfix

- Fixed an empty Data Management map when `FOLDER_INTAKE_DIR` points to a legacy `file_drop` folder while packaged data lives in `data/source_files`.
- Source lineage now scans the configured intake root, `data/source_files`, legacy `file_drop`, intake archives and `data/raw` fallback evidence.
- Duplicate copies are collapsed by visible filename and file size.
- Added source-discovery diagnostics to the map loading state.
- Added a new static asset cache key for the lineage runtime.
