# Build status — LedgerFlow 0.9.1

- Backend compilation: passed.
- Frontend TypeScript/Vite production build: passed.
- First-file staged upload: passed.
- Agent file explanation after upload: passed.
- Concurrent dashboard refresh: 56 requests, 0 HTTP 500 responses, 0 DuckDB tuple-deletion conflicts.
- Runtime data and API keys are excluded from the release archive.


**Updated:** 15 July 2026  
**Version:** 0.9.1  
**Milestone:** Observable file intelligence, hybrid NVIDIA routing, isolated processing, and opt-in company intelligence

## Implemented and retained

- Setup/permanent and recurring intake categories.
- CSV, XLSX, XLSM, digital-text PDF, and optional local OCR intake.
- Automatic recognition, aliases, saved mappings, and manual mapping.
- Bronze → Silver → DuckDB → Gold → Context pipeline.
- Exact-file duplicate skip and row-level versioning.
- Balance-sheet opening journals and invoice double-entry journals.
- Chart of accounts, trial balance, journals, and human validation.
- BAS-style labels, indicative tax estimate, and PDF/CSV workpapers.
- PDF/CSV business documents and local document library.
- Company profile, market context, validations, approvals, and pipeline controls.

## New in 0.9

- Immediate upload-job API with persisted, visible processing stages.
- One persistent isolated business worker for serial DuckDB/Polars processing.
- File-specific deterministic explanations and different initial/incremental greetings.
- Permanent required, permanent recommended, and recurring document catalogues.
- Separate visual file registers for setup and recurring evidence.
- Persistent `company_ai_context.json` and separate `market_intelligence.json`.
- Hybrid AI routing: routine file/accounting/tax work bypasses NVIDIA; open-ended reasoning may use NVIDIA.
- Fast file-question path that reads stored upload intelligence without rebuilding every dashboard.
- Optional local Tesseract OCR with safe review fallback.
- Payroll evidence ingestion and PAYG/super review summaries.
- Deterministic bank-to-invoice matching using amount plus reference/counterparty evidence.
- Opt-in Company Intelligence workspace with verified positioning and two agent-selected chart slots.
- Context-only refresh path so market files do not rebuild unrelated financial Gold analytics.
- Health-gated launcher, worker diagnostics, and safer optional-endpoint failure handling.

## Verified in this build

- Python compilation of all backend modules and launcher.
- React/TypeScript/Vite production build.
- FastAPI startup and bundled frontend serving from a clean release directory.
- Health response confirms a live persistent subprocess worker.
- Five-file serial sequence completed: balance sheet, supplier invoice, bank statement, payroll report, and competitor context.
- Digital PDF invoice extraction completed and produced file-specific GST/vendor analysis.
- HTTP upload exposed the real stages from received through completed.
- A file prompt returned through the deterministic business engine in approximately 0.03 seconds with an NVIDIA key configured.
- Initial upload and later incremental-update messages were both verified.
- Opt-in competitor intelligence completed with one company score and two chart slots while correctly withholding an unsupported peer ranking.
- Working-context clearing preserved base personality, company context, and market-intelligence context.

## Known build note

The production JavaScript bundle is approximately 773 kB before gzip and triggers Vite's advisory chunk-size warning. It builds successfully. Route/component code splitting remains a future performance improvement.

## Not implemented or intentionally bounded

- A Tesseract binary is not bundled; image-only PDF OCR depends on a local installation and uncertain results remain review-required.
- No direct bank feed; reconciliation uses uploaded evidence and deterministic amount/reference matching.
- Payroll files are ingested for review, but LedgerFlow is not an STP submission or payroll payment engine.
- Complete invoice-line and mixed-GST extraction is not guaranteed for every supplier layout.
- No verified campaign/CRM marketing-attribution feed.
- Competitor rankings remain blank until comparable verified peer metrics exist.
- No live official tax-rule updater, authentication/roles, multi-company tenancy, or direct ATO/SBR lodgment.
