# LedgerFlow 3.3.1 packaged-data validation

Validated company: **Banksia Office Supplies Pty Ltd — Synthetic Demo**

This is fictional demonstration data. It is structured to behave like a complete Australian B2B office-supplies company, but it is not a real company disclosure.

## Source lifecycle

| Check | Result |
|---|---:|
| Permanent setup sources | 18 |
| Recurring operating sources | 4 |
| Total committed sources | 22 |
| Data version | 22 |
| Initial setup complete | Yes |
| Current lifecycle | Recurring intake |
| Source-to-dashboard lineage steps | 110 |

## Database population

| Business record | Rows |
|---|---:|
| Bank transactions | 66 |
| Open invoices | 26 |
| Payroll records | 18 |
| Customers | 12 |
| Suppliers | 14 |
| Inventory items | 20 |
| Invoice-linked inventory movements | 18 |
| HR employee profiles | 9 |
| Open validation records | 0 |

## Reconciliation controls

| Control | Verified value |
|---|---:|
| Cash = final bank balance | $186,400 |
| Accounts receivable = aged debtors | $124,850 |
| Accounts payable = aged creditors | $97,600 |
| Inventory account = inventory detail | $168,300 |
| Trial-balance debits = credits | $623,950 |
| Current ratio | 3.63 |
| Quick ratio | 2.39 |

## Dashboard checks

- All six displayed Overview measures reconcile to independent `business.db` calculations.
- All five Overview charts contain non-zero database-backed data.
- Data-trust status is **trusted**, scoring **92/100**, with zero open checks.
- June payroll supports BAS labels W1 of **$41,600** and W2 of **$8,126**.
- Marketing evidence contains five channels and **$8,800** of approved spend.
- Inventory contains **7,944 units** with a reconciled value of **$168,300** and three reorder alerts.
- HR shows nine people, **$41,600** gross payroll, **$8,126** PAYG withholding and **$4,992** super.
- Money Map reconciles **$286,400** revenue, **$248,290** operating costs and **$38,110** pre-tax profit.

Use **Verify and reload** in Overview or Accounts after any future import. LedgerFlow will rebuild derived accounting results and repeat the chart-to-database checks.
