# LedgerFlow v3 business data architecture

## Canonical business file

`data/database/business.db` is the main DuckDB database for business evidence, derived
tables, Robert's persistent operating context, processing history and traceability.
On first v3 launch, an existing `business.duckdb` is automatically moved to this name.

`application.sqlite` remains a small technical control database for upload jobs,
application settings and queues. It is not the source of business analysis.

## The two procedures

### 1. Initial setup

1. Load foundational files such as the chart of accounts, opening balances, company
   profile and historical reference data.
2. Validate the files and build the full detailed business tables.
3. Register every source and derived table in the catalogue.
4. create Robert's compact launch summary so he can orient quickly.
5. Mark setup complete when the required foundations are present.

### 2. Recurring intake

1. Accept new invoices, bank records, expenses, journals, payroll and other evidence.
2. Preserve the raw source and validate its structure and values.
3. Write clean data to `business.db`.
4. refresh affected summaries and Robert's launch context.
5. Append lineage and process-memory records so each run remains traceable.

This procedure is designed to continue indefinitely. It does not recreate the database
or discard prior history.

## Canonical control tables

| Table | Purpose |
|---|---|
| `business_system` | Database identity, schema version and canonical path |
| `robert_profile` | Robert's role, personality and behavioural rules |
| `business_lifecycle` | Initial-setup and recurring-intake status |
| `business_source_registry` | One record per ingested source with classification and state |
| `business_lineage` | Source → raw → clean → store → served destination events |
| `business_catalog` | Inventory of every business table and its purpose |
| `business_context_detail` | Detailed structured business context |
| `business_context_summary` | Compact summaries, including Robert's launch context |
| `robert_process_memory` | Durable record of procedures Robert knows have run |

## Traceability

Every ingestion records the source filename, upload ID, checksum where available,
procedure, processing stage, destination table or section, row count, status and time.
The Data Management page surfaces this as a short “where the data went” view, while
the database retains the complete history.

## Robert's startup behaviour

Robert reads `business_context_summary` first. This gives him the company identity,
coverage, quality, lifecycle and recent processing state without scanning every row.
He opens `business_context_detail`, the source registry or business tables only when
the question needs more evidence. His conclusions must be traceable to those records.
