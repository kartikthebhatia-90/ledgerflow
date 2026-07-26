# LedgerFlow 0.9 - Accounting, Documents and Tax Workflow

## 1. Initial setup versus recurring operation

An invoice is not required to create the company baseline. Upload an opening or latest balance sheet first. LedgerFlow converts the most recent balance-sheet period into a balanced opening journal and posts the residual net assets to Owner equity.

Recurring invoices then update accounts payable, accounts receivable, expenses, revenue and GST control accounts.

## 2. Automatic file identification

Identification uses, in order:

1. File type and filename.
2. Workbook sheet names and structural layouts.
3. Strong field combinations such as invoice number + counterparty + amount.
4. Alias matching for expected accounting fields.
5. Previously approved schema mappings.
6. Human mapping when required fields cannot be established.

Invoice structural checks run before generic transaction scoring. This avoids an invoice being mistaken for a transaction merely because it contains date, description and amount columns.

## 3. Invoice extraction

Structured CSV/XLSX invoice fields include:

- Invoice number and kind (supplier or sales)
- Counterparty and ABN
- Invoice and due dates
- Description
- Subtotal, GST and total
- Currency and status

Digital-text PDFs are parsed for the same fields. Image-only PDFs remain in Bronze storage and receive a document-extraction validation task.

## 4. Categorisation engine

The deterministic categorisation order is:

1. User-confirmed supplier exact match.
2. Supplier-specific or description-specific saved rules.
3. Common keyword rules.
4. Uncategorised expense fallback and human review.

Every result records an account, tax code, confidence, reason and validation status. Typical built-in mappings cover office supplies, software, utilities, freight, rent, marketing, professional fees, vehicles, travel, entertainment, insurance, repairs, payroll, banking, interest and capital equipment.

High-confidence routine matches are posted. Uncertain or capital-sensitive matches remain draft. Approval can remember the supplier rule for later invoices.

## 5. Double-entry ledger

### Supplier invoice

```text
Debit  Expense or asset
Debit  GST receivable, where applicable
Credit Accounts payable
```

### Sales invoice

```text
Debit  Accounts receivable
Credit Sales revenue
Credit GST payable, where applicable
```

Every journal is checked through equal debit and credit totals. Draft journals remain visible for review but are excluded from final account balances, accounting profit and tax estimates.

## 6. Opening balance sheet mapping

The most recent balance sheet maps common labels to accounts such as cash, petty cash, receivables, prepayments, inventory, property, vehicles, equipment, payables, accrued expenses, tax payable, loans and equipment finance. The balancing amount posts to Owner equity.

This is an opening-position conversion, not a substitute for historical transaction migration. An accountant should review the opening trial balance before production use.

## 7. Accounts workspace

The Accounts page contains:

- Ledger profit and control-account KPIs
- Invoice categorisation results and confidence
- Chart of accounts and trial balance
- Balanced journal register
- Validation queue
- Account and GST-code approval controls
- Reusable supplier mapping option

## 8. Business Document Centre

Operational forms use entered fields; accounting reports use verified ledger data. Outputs are stored as reviewable drafts in `data/exports` and registered in SQLite.

Supported outputs include:

- Sales invoice, purchase order, quotation, receipt and expense claim
- Customer statement and supplier payment schedule
- Inventory count sheet and cash-flow forecast
- Management summary
- Trial balance and general ledger
- Profit and loss, balance sheet and GST transaction report

## 9. Tax & Compliance workspace

The tax page uses the saved Australian tax profile and **posted** ledger entries. It presents:

- Indicative income-tax calculation
- BAS-style G1, 1A, 1B, W1 and W2 labels
- GST control reconciliation
- Obligations for GST, income tax, records, STP, super and FBT where relevant
- Evidence and categorisation exceptions
- Potential review opportunities such as missing GST treatment, capital purchases and entertainment/FBT
- PDF and CSV ATO-ready workpapers

The workpaper is deliberately labelled as non-official and review-required.

## 10. Internet permissions

Four staged modes are represented:

- **Offline:** all external features disabled.
- **Official sources only:** intended for controlled ATO/government rule checks.
- **Enrichment:** adds limited supplier-name research and requires explicit consent.
- **Connected:** reserves bank, email and cloud integrations.

Version 0.9 stores and enforces these permissions but does not activate live rule ingestion, supplier lookup, bank feeds, email ingestion or ATO submission. Existing optional SearXNG research remains separately configured through `.env`.

## 11. Production work still required

- OCR and layout-aware extraction for scanned invoices
- Invoice line-item tables and mixed-tax invoices
- Payment matching and bank reconciliation
- Period locking, reversals and manual journals
- Payroll/STP and super integrations
- Asset depreciation and inventory costing
- Multi-entity and user-role controls
- Automated official-source rule versioning with administrator approval
- Security review, backups, test coverage and migration tooling
- DSP/OSF/SBR work before direct ATO lodgment
