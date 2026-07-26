# Apply LedgerFlow 2.0.3 hotfix

This overlay preserves the existing `.env`, uploaded source files and runtime databases when extracted over a LedgerFlow 2.0.2 project.

1. Stop LedgerFlow with `Ctrl+C`.
2. Extract the hotfix into the project root and replace matching files.
3. In VS Code PowerShell:

```powershell
cd "D:\path\to\ledgerflow_dashboard"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
.\VERIFY_LEDGERFLOW_V203.ps1
python .\run_app.py
```

4. Open `http://127.0.0.1:8000/?build=2.0.3` and press `Ctrl+F5`.
5. Open Data management. Expand Permanent files and Temporary / recurring files to verify the source registers.
6. Use Talk to Ledger to test voice conversation. Allow microphone access when Chrome requests it.
