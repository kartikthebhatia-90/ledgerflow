# Backend Connection Troubleshooting

## Fast check

Open:

```text
http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"ok": true, "app": "LedgerFlow", "version": "0.9.0"}
```

If this works but the page is stale, refresh with `Ctrl+F5`.

## Correct startup method

Run only one of these:

```bat
start_existing_install.bat
```

or:

```bash
python run_app.py
```

`run_app.py` now checks port 8000 first. It reuses an existing LedgerFlow instance and refuses to start a second writer.

## DuckDB lock error

Typical cause:

- LedgerFlow was started twice.
- A previous Python process did not exit.
- A DuckDB viewer has `data/database/business.duckdb` open for writing.
- A development auto-reloader created another process.

Resolution:

1. Close every LedgerFlow terminal.
2. Close VS Code database viewers or DuckDB clients using the file.
3. In Windows Task Manager, stop only Python processes belonging to this LedgerFlow folder.
4. Start LedgerFlow once.
5. Do not run Uvicorn with multiple workers or reload against the same DuckDB file.

The backend retries a short number of times and then emits a lock-specific message with the database path.

## Port already in use

When another application uses port 8000, either stop it or set a different local port:

```env
APP_PORT=8001
```

Then open `http://127.0.0.1:8001`.

Do not change the port merely because LedgerFlow is already running; the launcher will reuse it.

## Frontend cannot reach backend

Check, in order:

1. `/api/health` responds.
2. Browser URL matches `APP_HOST` and `APP_PORT`.
3. `frontend/dist/index.html` exists.
4. No proxy/VPN/browser extension is blocking localhost.
5. The browser console does not show a cached old asset.
6. Refresh with `Ctrl+F5`.

The normal production build is served by FastAPI from the same origin, so no separate Vite server is required.

## NVIDIA test fails

1. Confirm `.env` exists in the project root.
2. Confirm `MODEL_PROVIDER=nvidia`.
3. Confirm `NVIDIA_API_KEY` is non-empty and contains no quotes copied accidentally.
4. Confirm `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`.
5. Confirm the configured model is available to the key.
6. Restart LedgerFlow after editing `.env`.
7. Use **Settings → Test NVIDIA**.

The dashboards and deterministic safe planner still work when the external model is unavailable.

## LLMLingua fails to load

The optional adapter requires additional model dependencies and may download model weights:

```bash
python -m pip install -r backend/requirements-llmlingua.txt
```

If the environment cannot load it, set:

```env
PROMPT_COMPRESSION_PROVIDER=budgeted
```

LedgerFlow also falls back to `budgeted` automatically at runtime.

## Reset only agent continuity

Use **Settings → Clear working context** or:

```bash
curl -X DELETE http://127.0.0.1:8000/api/agent/context
```

This preserves `agent/BASE_PERSONALITY.md`, company data and accounting records.

## Development checks

```bash
python -m compileall backend/app
cd frontend
npm ci
npm run build
```

For API inspection, open `/docs`.
