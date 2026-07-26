# LedgerFlow End-to-End Data Pipeline

## 1. Purpose

LedgerFlow processes company information once into a persistent business structure, then processes only new or changed information on later uploads.

```text
Initial onboarding: full baseline
Later operation: incremental updates
Manual rebuild: new full baseline version
```

Every upload is also assigned to one of two business intake categories:

```text
setup     → maintained baseline and reference records
recurring → invoices, bank data, payments, transactions, and other ongoing operations
```

The category does not bypass document recognition. It controls how the file is presented, tracked, and reviewed.

## 2. Layers

### Intake

Temporary processing area.

### Bronze

Original evidence is stored unchanged with:

- File ID
- SHA-256
- Original name
- Size
- Upload time
- Metadata JSON
- Intake category (`setup` or `recurring`)
- Declared document type, when selected by the user

### Silver

Each detected document or workbook sheet is saved separately as compressed Parquet under its document type.

### DuckDB operational layer

Mapped records are stored in document-specific tables such as:

- `invoices`
- `transactions`
- `payments`
- `bank_transactions`
- `assets_liabilities`
- `customers`
- `suppliers`
- `inventory`
- `budgets`
- `statement_snapshots`
- `market_signals`

### Gold

- `kpi_snapshots.parquet`
- `decision_features.parquet`

Gold is the compact layer normally supplied to the AI and dashboard.

### Context

- `company_baseline.json`
- `market_profile.json`
- `latest_market_snapshot.json`
- `market_brief.md`
- `information_requests.json`

## 3. Recognition

Recognition order:

1. Exact duplicate fingerprint
2. Saved schema and mapping profile
3. Deterministic column aliases
4. Filename and sheet-name hints
5. Confidence score
6. Manual mapping when required

The local AI is not permitted to silently guess critical financial fields.

## 4. Incremental logic

Each row receives:

- Document type
- Business key
- Row hash
- Stable record ID
- Record version
- Current/history status
- Source file
- Source sheet
- Source row

Outcomes:

```text
No previous business key → new
Same business key and same row hash → unchanged and skipped
Same business key and changed row hash → changed and versioned
Invalid/missing required mapping → rejected or pending mapping
```

## 5. Dependency-aware refresh

Examples:

```text
Supplier invoice
→ payables
→ current liabilities
→ current ratio
→ cash forecast

Supplier master
→ supplier concentration
→ supplier country exposure
→ market profile

Market-context signal
→ external risk score
→ market snapshot
→ Market Intelligence display
```

The backend returns the affected metrics after each import.

## 6. Company baseline

The baseline includes:

- Company profile
- Data version
- Baseline version
- First and last full-build time
- Last incremental-update time
- Document coverage
- Entity counts
- Financial snapshot
- Market exposure
- Missing-information requests

A normal import does not rebuild the entire historical pipeline. It updates the current baseline from the changed data. The user can manually request a full rebuild.

## 7. Market file

Recommended columns:

```text
topic
signal_type
entity
geography
observed_at
published_at
value
unit
direction
source_name
source_url
relevance_score
estimated_impact
impact_horizon
```

Examples of signal types:

- Currency
- Commodity
- Competitor
- Regulation
- Geopolitical
- Logistics
- Interest rates
- Labour
- Local demand
- Technology
- Environmental risk

## 8. Information requests

The app creates requests when useful context is missing, including:

- Supplier countries and currencies
- Customer locations and segments
- Bank statements
- Budget
- Inventory
- Competitors
- Business goals

Each request explains why it would improve the analysis.

## 9. Clear-data behaviour

Clear scopes:

```text
company → imported records, import metadata, baseline and Gold data
memory  → conversations, summaries and agent events
market  → uploaded market signals and research cache
all     → all of the above plus company profile reset
```

Optional backup is created before deletion. Application code, `.env`, Ollama, and models are never deleted.

## 10. PDF source evidence and generated documents

PDF uploads are preserved in Bronze. Digitally generated invoice PDFs can be text-extracted and routed into the invoice workflow. Image-only/scanned PDFs remain source-only and require a future OCR workflow or manual review before they affect financial metrics.

The document studio can generate standard PDF or CSV business documents using either a short form or the current stored business data. Generated outputs are downloads and do not automatically post accounting entries.
