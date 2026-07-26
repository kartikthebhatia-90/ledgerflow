# LedgerFlow Upload and Document Guide

## Version 0.9 automatic processing

Leave the document selector on **Auto** for normal use. LedgerFlow now recognises supported balance sheets, structured supplier/sales invoices, and digital-text PDF invoices. High-confidence invoice mappings create posted journals. Uncertain categories create balanced drafts in **Accounts -> Validation queue** and do not affect final balances or tax estimates until approved.

A balance sheet is sufficient to initialise the opening ledger. Invoices are needed to begin the recurring payable/receivable workflow, but are not mandatory for initial setup.

Recommended test files are in `samples/`: `Balance_Sheet_Sample_Healthy.xlsx`, `Supplier_Invoices_AutoMap.csv`, `Sales_Invoices_AutoMap.csv`, `Unknown_Supplier_Human_Review.csv`, and the two PDF invoices.

## 1. Two separate intake categories

### Setup library

Use this for records that define the business baseline. They are not uploaded every day, but they are not immutable: upload a replacement or updated version when the business changes.

### Recurring inbox

Use this for operational files that arrive repeatedly. LedgerFlow compares business keys and row hashes so new and changed records are processed while unchanged rows are skipped.

## 2. Setup files to upload

### Minimum baseline

| File | Recommended format | Update cadence | Why it is needed |
|---|---|---|---|
| Latest or opening balance sheet | CSV/XLSX | Monthly or at onboarding | Establishes assets, liabilities, and equity position |
| Asset register | CSV/XLSX | When assets change; monthly review | Fixed assets, current assets, values, and classifications |
| Liability and loan register | CSV/XLSX | When borrowing changes; monthly review | Current/non-current debt, balances, and liquidity pressure |
| Customer master | CSV/XLSX | When customers change | Customer identity, location, segment, and status |
| Supplier master | CSV/XLSX | When suppliers change | Supplier identity, country, category, currency, and status |
| Latest bank statement or opening bank balances | CSV/XLSX | At onboarding, then recurring | Establishes available cash and bank accounts |

### Strongly recommended

| File | Recommended format | Update cadence | Why it is needed |
|---|---|---|---|
| Profit-and-loss history, ideally 12-24 months | CSV/XLSX | Monthly | Revenue, costs, margins, seasonality, and trends |
| Cash-flow statement | CSV/XLSX | Monthly | Operating, investing, and financing cash movement |
| Inventory opening stock | CSV/XLSX | At onboarding; then recurring updates | Quantity, unit cost, value, and stock location |
| Budget and forecast | CSV/XLSX | Monthly or quarterly | Actual-versus-budget analysis and cash planning |
| Chart of accounts | CSV/XLSX | When accounts change | Standard account structure; currently stored for future formal accounting support |
| Tax and reporting settings | CSV/XLSX or PDF | When settings change | Tax rates, reporting currency, financial year, and registration references |

### Context and governance

| File | Recommended format | Update cadence | Processing behaviour |
|---|---|---|---|
| Market-context file | CSV/XLSX | Weekly, monthly, or when a major event occurs | Imported into market signals and company context |
| Key contracts and loan agreements | PDF | When signed or amended | Preserved as source evidence; structured term extraction is not enabled yet |
| Insurance and fixed-asset evidence | PDF | On renewal or acquisition | Preserved as source evidence |
| Business registration and policy documents | PDF | When changed | Preserved as source evidence |

The company profile itself is entered in **Company context** rather than uploaded as a file.

## 3. Recurring files to upload

### Normal daily or weekly flow

| File | Recommended format | Typical cadence | Current processing |
|---|---|---|---|
| Supplier invoices and bills | CSV/XLSX; PDF for evidence | Daily or weekly | Structured rows update payables; PDFs are archived pending extraction |
| Sales invoices | CSV/XLSX; PDF for evidence | Daily or weekly | Structured rows update receivables |
| Bank statements or bank exports | CSV/XLSX | Daily, weekly, or monthly | Updates bank transactions and cash movement |
| Payments and receipts | CSV/XLSX | Daily or weekly | Updates payment and transaction records |
| General transaction or expense export | CSV/XLSX | Daily, weekly, or monthly | Updates revenue/expense transactions |

### Upload when the business uses them

- Purchase orders
- Sales orders
- Inventory movements and stocktakes
- Payroll summaries
- Expense claims
- Credit notes
- Customer receipts
- Supplier remittance records

These can be stored now. Some are retained as generic operational records until their dedicated accounting workflows are implemented.

## 4. File rules

- Use CSV/XLSX/XLSM for automatic mapping, validation, metrics, and incremental processing.
- Use PDF for source evidence. PDF field extraction and OCR remain future work.
- Keep stable identifiers such as invoice number, customer/supplier code, SKU, payment reference, and account name.
- Do not change column meanings between uploads. LedgerFlow saves approved schema mappings and reuses them.
- Use one row per business record for normal imports. The supplied business.gov.au-style balance-sheet template is a supported exception: LedgerFlow converts its year columns and section rows into long-form records automatically.
- Dates should use ISO format (`YYYY-MM-DD`) where possible.
- Amounts should be numeric and currency should be a separate column where multiple currencies are used.

### Supported multi-year balance-sheet template

LedgerFlow 0.9 directly recognises the supplied business.gov.au-style workbook when:

- The worksheet contains a balance-sheet title and the standard Current assets / Fixed assets / Current liabilities / Long-term liabilities sections.
- Each reporting column heading is a real date or contains a four-digit year. Full dates such as `30 Jun 2026` are preferred.
- Detail rows contain numeric values. Blank rows and calculated Total, Total Assets, Total Liabilities, Net Assets, and Working Capital rows are not imported, preventing double counting.
- The explanatory `Using this balance sheet` worksheet is ignored.

Each populated workbook produces 23 detail line items for each reporting period. Liabilities are stored as negative statement amounts internally. A blank template without valid reporting periods or values is retained for mapping rather than committed.

## 5. Documents LedgerFlow can create

The **Document studio** creates the following as PDF or CSV:

- Sales invoice
- Purchase order
- Quotation / estimate
- Payment receipt
- Expense claim
- Customer account statement
- Supplier payment schedule
- Inventory count sheet
- 90-day cash-flow forecast
- Management summary

Form documents use the saved company profile plus a short form. Data documents use the latest records already stored in LedgerFlow. Generated documents should be reviewed before being issued externally.
