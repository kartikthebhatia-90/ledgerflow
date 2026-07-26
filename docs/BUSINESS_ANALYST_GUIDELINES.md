# LedgerFlow 2.0.3 — Business Analyst Supervisor and Voice Conversation

## Decision workflow

Every non-trivial open-ended request follows this sequence:

1. **Frame** — define the decision, time horizon, success measures and evidence available.
2. **Route** — select the relevant department agents. Broad management requests use every enabled agent.
3. **Analyse** — agents receive direct governed data packets for their department and run in parallel.
4. **Challenge** — check conflicts, unsupported claims, missing evidence, compliance constraints and feasibility.
5. **Decide** — Ledger reconciles the findings into one recommendation, next actions and uncertainty statement.

The user-facing answer gives a decision rationale and evidence trail. It does not expose private hidden reasoning.

## Department access

- Executive: snapshot, forecast, profit structure, data quality and information requests.
- Finance & Accounts: statements, invoices, transactions, forecast and accounts dashboard.
- Tax & Compliance: tax dashboard, invoice evidence and payroll obligations.
- Sales & Marketing: revenue, invoices, marketing dashboard and market signals.
- Operations & Supply: transactions, assets, forecast, supplier evidence and contracts.
- People & Payroll: payroll, employee context, tax and transaction evidence.
- Market & Strategy: company market profile, competitor evidence, research and market-analysis templates.

## Voice conversation

The fixed **Talk to Ledger** control uses browser speech recognition with continuous and interim results. When speech is detected while Ledger is speaking, the current speech-synthesis queue is cancelled and the new utterance is accepted as the next question. Echo filtering prevents Ledger's own spoken answer from being submitted as a user request.

Microphone permission is controlled by the browser. Chrome or Edge on `127.0.0.1` is recommended for local testing.

## Personality

The assistant profile is saved in:

```text
data/context/default/assistant_profile.json
```

Available roles:

- Business analyst
- Executive adviser
- Analyst coach

Available answer depths:

- Concise
- Balanced
- Detailed

The selected profile is incorporated into the supervisor, challenge reviewer and each department agent on the next request.

## File registers

Data Management contains collapsed menus for:

- Permanent files
- Temporary / recurring files
- AI context files
- Department agents
- Superset dashboards
- Business-analysis traces

The two source-file menus show every source currently present in the architecture response. Selecting a filename focuses its node and opens its editable inspector.
