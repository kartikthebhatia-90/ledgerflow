<div align="center">

# LedgerFlow

### Local-first business intelligence with evidence-aware AI workflows

LedgerFlow brings finance, cash flow, inventory, tax, workforce planning, market intelligence and operational evidence into one connected business environment.

<br>

<img src="readme%20sources/business-functions.png" alt="LedgerFlow business functions" width="760">

</div>

---

## What LedgerFlow does

LedgerFlow is a full-stack business operating platform built around a shared company context.

Instead of treating finance, operations, inventory, people, tax and market intelligence as separate systems, LedgerFlow connects them so that a change in one area can be understood across the rest of the organisation.

The platform combines deterministic business logic, local analytical processing, traceable source evidence, connected operational workspaces, structured Bronze–Silver–Gold data pipelines and an embedded AI assistant called **Clippy**.

Clippy is not intended to replace business systems or make unsupported decisions. It works as an interface to trusted workflows, helping users understand performance, identify risks, prepare structured analysis and move from a question to a controlled business action.

> **AI should assist the business through trusted context, while calculations, validation and sensitive actions remain controlled by deterministic systems and human review.**

---

## How the application helps

LedgerFlow reduces the effort required to understand what is happening across the business by combining financial position, cash movement, invoice exposure, operational performance, data quality and market context in one interface.

<table>
<tr>
<td width="50%" valign="top">

### Executive overview

The executive workspace consolidates operating performance, assets and liabilities, profitability, cash exposure, invoice movement and data-trust indicators.

It is designed to answer three questions quickly:

1. What is happening now?
2. What is likely to require attention next?
3. Can the displayed information be trusted?

<br>

<img src="readme%20sources/02_overview.png" alt="LedgerFlow executive overview" width="100%">

</td>
<td width="50%" valign="top">

### Money Map

Money Map shows how customer income moves through operating activities, costs and retained value.

It helps users understand where money originates, where it is being consumed, which areas are creating pressure and how operational decisions affect cash.

<br>

<img src="readme%20sources/03_money_map.png" alt="LedgerFlow Money Map" width="100%">

</td>
</tr>
</table>

These workspaces are supported by connected modules for accounts, data management, inventory, tax, people, marketing and market intelligence.

The benefit is not simply having multiple dashboards in one application. The benefit is that the workspaces share business context.

For example:

- an inventory purchase affects cash, working capital and supplier exposure;
- overdue invoices affect liquidity forecasts and collection priorities;
- hiring plans interact with budgets and revenue expectations;
- tax obligations influence available cash; and
- market opportunities can be assessed against internal capacity and margins.

---

## Clippy: embedded AI assistance

Clippy is LedgerFlow's AI operating layer.

It is designed to convert natural-language requests into structured, reviewable workflows rather than acting as an unrestricted chatbot.

Clippy can support KPI and financial explanations, management summaries, guided analysis, missing-information detection, risk identification, workspace navigation, structured report preparation and controlled workflow execution.

Only task-relevant context should be supplied to the configured model. Sensitive outputs and write actions remain subject to deterministic validation and human approval.

---

## Evidence-aware intelligence

LedgerFlow treats source evidence, data quality and lineage as product features.

The intended trust model preserves original source files, document classifications, validation outcomes, processing history, version information, reconciliation results, confidence indicators, generated reports and links between outputs and supporting records.

The objective is not only to produce an answer, but to make the basis of that answer inspectable.

---

## Under the hood

<div align="center">

<img src="readme%20sources/system-architecture.png" alt="LedgerFlow system architecture" width="820">

</div>

LedgerFlow separates deterministic processing from language-model assistance.

### Deterministic core

Repeatable and testable operations remain in application logic, including calculations, classifications, validation rules, reconciliations, thresholds, data transformations, document generation, workflow routing and approval requirements.

### AI layer

Language models are used where interpretation adds value, including natural-language understanding, explanations, summaries, guided analysis, recommendations and structured text generation.

This separation reduces the risk of treating a language model as the source of truth for accounting, compliance or operational calculations.

### Data flow

```text
Business files and user inputs
                │
                ▼
     Classification and validation
                │
                ▼
        Bronze → Silver → Gold
                │
                ▼
 Deterministic business processing
                │
        ┌───────┴────────┐
        ▼                ▼
Business workspaces   AI-ready context
                         │
                         ▼
                       Clippy
                         │
                         ▼
              Human review and action
```

### Architecture layers

1. **Frontend experience** — React, TypeScript and Vite.
2. **API and orchestration** — FastAPI routes, workflow routing and background processing.
3. **Deterministic engine** — calculations, validation, classification and approval rules.
4. **Clippy layer** — task-specific AI assistance through an OpenAI-compatible model gateway.
5. **Data intake** — uploads, watched folders, forms and future connectors.
6. **Data pipeline** — Bronze, Silver and Gold processing tiers.
7. **Storage and compute** — Polars, DuckDB, SQLite and versioned local evidence.
8. **Analytics and outputs** — dashboards, reports, document trails and optional Apache Superset integration.

---

## Technology

| Area | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python, Uvicorn |
| Data processing | Polars |
| Analytical engine | DuckDB |
| Application metadata | SQLite |
| AI integration | OpenAI-compatible model gateway |
| Current model route | NVIDIA NIM |
| Extended analytics | Apache Superset |
| Deployment model | Local-first and company-controlled |

---

## Repository structure

```text
ledgerflow/
├── agent/                    Clippy behaviour and workflow configuration
├── analytics/                Semantic-layer definitions and business metrics
├── backend/                  FastAPI services and deterministic business logic
├── data/                     Local pipeline structure and runtime evidence
├── docs/                     Architecture and product documentation
├── file_drop/                Folder-based document intake
├── frontend/                 React and TypeScript application
├── readme sources/           Product screenshots and architecture graphics
├── samples/                  Synthetic business demonstration dataset
├── superset/                 Optional analytics environment
├── README.md
└── VERSION
```

---

## Design principles

### Local-first control

Core analytical processing and business evidence can remain within a company-controlled environment.

### Evidence before confidence

Outputs should be connected to their source, transformation and validation state wherever possible.

### Human-in-the-loop operation

AI may explain, prepare, monitor and recommend. Material actions remain reviewable.

### Tasks over prompt engineering

Users interact with defined business functions rather than repeatedly reconstructing company context through large prompts.

### Shared operational context

Finance, inventory, tax, people, marketing and market intelligence are treated as connected parts of the same operating system.

---

## Future possibilities

The long-term direction of LedgerFlow is a network of connected, evidence-aware business systems that can coordinate activity across departments and, eventually, across organisations.

### Interconnected business networks

Future versions could allow approved business systems to exchange structured operational events directly.

For example:

- one company raises a purchase order;
- the supplier receives a validated order event;
- fulfilment updates are shared automatically;
- an invoice is generated when agreed conditions are met;
- the buyer receives and validates the invoice;
- accounts payable, cash forecasting and supplier exposure update automatically; and
- both businesses retain an auditable record of the transaction.

This would reduce manual re-entry, reconciliation delays and duplicated document handling while preserving approval controls.

### Autonomous invoice and settlement workflows

LedgerFlow could support invoice generation from confirmed deliveries, automated three-way matching, supplier and customer balance updates, payment scheduling against cash forecasts, dispute detection, exception routing, tax treatment validation and settlement recommendations for human approval.

### Adaptive AI marketing

A future marketing layer could continuously assess campaign performance and change direction within approved limits.

It could:

- shift campaign goals as business priorities change;
- reallocate spend between channels;
- adjust audience targeting;
- test messaging and creative variants;
- respond to inventory levels and margin changes;
- pause activity when operational capacity is constrained;
- optimise for revenue, margin, retention or customer acquisition; and
- provide a clear explanation of every adjustment.

### Connected planning

Future planning workflows could connect sales forecasts, inventory demand, supplier lead times, staffing requirements, marketing activity, working capital, tax obligations and operational capacity.

A change in one plan could automatically update the assumptions and risks in the others.

### Business-to-business operational agents

Approved agents could eventually coordinate routine work between organisations, including purchase order management, delivery confirmation, invoice exchange, contract milestone tracking, supplier onboarding, compliance document requests, service-level monitoring and exception resolution.

### Continuous business optimisation

Future versions could monitor the organisation as a connected system rather than a collection of departments.

This could enable early cash-pressure detection, dynamic inventory replenishment, automated supplier-risk monitoring, workforce-capacity planning, margin-aware pricing recommendations, customer-retention intervention, compliance deadline tracking and continuous operational scenario analysis.

The goal is not unrestricted automation. The goal is controlled autonomy: systems that can monitor, prepare, coordinate and optimise while remaining explainable, permissioned and reviewable.

---

## Project status

LedgerFlow is an active full-stack product prototype focused on local-first business intelligence, deterministic automation and evidence-aware AI assistance.

The included business records are synthetic demonstration data.
