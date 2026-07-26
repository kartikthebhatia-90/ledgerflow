# Data Analytics Semantic Layer

The semantic layer is the inspectable source of truth for how LedgerFlow interprets metrics and dashboards.

## Metric contract

Every metric definition includes:

- stable identifier and label;
- business family and dashboard role;
- calculation meaning;
- canonical and fallback sources;
- analytical grain;
- required evidence;
- guardrails and target fields where relevant.

## Current primary KPIs

- Cash balance
- Working capital
- Current ratio
- Net profit
- Monthly inflows and outflows
- Overdue invoice exposure
- Taxable profit estimate
- Marketing ROAS
- Data Trust score

## Readiness states

- `ready`: required evidence is represented and the canonical basis is available.
- `provisional`: a documented fallback or demonstration basis is being used.
- `blocked`: required evidence is missing.

The state is available through `/api/analytics/semantic-layer` and displayed in Data Trust.

## Updating definitions

Edit the JSON files under `analytics/semantic_layer/`, then restart LedgerFlow. Keep definitions stable, explicit and source-backed. Do not add a metric merely because it can be calculated; add it only when it supports a real decision.
