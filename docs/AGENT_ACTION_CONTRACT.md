# Agent Action Contract

## Rule

When LedgerFlow can perform the requested action, Ledger performs it. It does not answer with instructions telling the user to perform the same action.

## Registered commands

| User intent | Execution |
|---|---|
| `overview` | Runs the setup-gated scripted walkthrough |
| `show accounts/tax/marketing/data trust` | Navigates and spotlights the requested section |
| `scan folders` | Scans both file-drop folders and queues supported files |
| `repair classifications` | Schedules safe corrective reprocessing |
| `refresh validations` | Runs validations and refreshes Data Trust |
| `start deep company analysis` | Starts or resumes the analysis job |
| `generate management summary PDF/CSV` | Generates and downloads the file |
| `generate tax workpaper PDF/CSV` | Generates and downloads the workpaper |
| `test NVIDIA` | Calls the configured model test and reports the actual result |
| `clear working context` | Clears only recent conversation continuity |
| `reset all data` | Opens the protected confirmation control; no deletion occurs without confirmation |

## Ambiguity

If the requested action is executable but underspecified, Ledger asks only for the missing choice. Example: `generate a file` opens the document rail and offers specific output choices.

## Setup gating

The complete guided tour, deep company analysis and management-document generation require the five core setup categories:

- Balance Sheet
- Profit and Loss
- Cash Flow Statement
- Chart of Accounts
- Business Requirements Document

When setup is incomplete, Ledger opens the missing-document checklist and names the exact blockers.

## Model boundary

NVIDIA may explain results, compare alternatives or support strategic analysis. It does not decide whether a registered application action should run. The deterministic action registry owns that decision.
