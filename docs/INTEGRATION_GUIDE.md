# LedgerFlow Integration Guide

## 1. Ollama

Install Ollama separately, then run:

```powershell
ollama pull qwen3.5:2b-q4_K_M
ollama run qwen3.5:2b-q4_K_M
```

Use this in `.env`:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:2b-q4_K_M
MODEL_CONTEXT_SIZE=2048
MODEL_TEMPERATURE=0.2
OLLAMA_TIMEOUT_SECONDS=600
OLLAMA_KEEP_ALIVE=30m
```

Restart LedgerFlow after editing `.env`.

## 2. SearXNG web research

SearXNG is optional and must be installed separately. After it is reachable locally, use:

```env
WEB_SEARCH_PROVIDER=searxng
SEARXNG_URL=http://127.0.0.1:8080
```

Restart LedgerFlow and test the connection from **Setup & integrations**.

When connected, Market Intelligence can return source titles, snippets, and links. Internal accounting data is not automatically sent to cloud providers; the generated search query uses the saved company context and the user’s research request.

## 3. Upgrading the local model

A stronger model can be installed later without changing the app architecture.

Example:

```powershell
ollama pull qwen3.5:4b-q4_K_M
```

Then change:

```env
OLLAMA_MODEL=qwen3.5:4b-q4_K_M
```

A larger model may require more RAM and may respond more slowly on CPU-only hardware.

## 4. Cloud fallback

Cloud fallback remains disabled by default. The `.env` fields are placeholders for future provider adapters. Do not place a real API key in `.env.example` or share your real `.env`.

## 5. Data preservation during updates

Before replacing the app folder, back up:

```text
.env
data/
```

The `data` folder contains local DuckDB, SQLite, Parquet, uploaded raw evidence, memory, and exports.

## 6. LedgerFlow 0.9 internet permission modes

The Tax & Compliance page stores four modes: offline, official sources only, enrichment and connected. These are permission and staging controls. They do not create a bank, email, supplier-enrichment or ATO connection by themselves.

Supplier enrichment cannot be enabled without explicit external-processing consent. Direct ATO/SBR remains locked in the backend and interface.
