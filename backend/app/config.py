from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LedgerFlow"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    data_dir: str = "./data"
    app_timezone: str = "Australia/Melbourne"

    # Model routing. NVIDIA NIM is the recommended cloud provider for this build.
    model_provider: str = "nvidia"
    model_context_size: int = 8192
    model_temperature: float = 0.2
    model_max_output_tokens: int = 420
    # Keep interactive requests bounded. Routine accounting/file questions are
    # answered by deterministic code and never wait for the model in hybrid mode.
    model_timeout_seconds: int = 35

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "openai/gpt-oss-20b"

    # Optional local fallback retained for offline operation.
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:2b-q4_K_M"
    ollama_enabled: bool = False
    ollama_timeout_seconds: int = 600
    ollama_keep_alive: str = "30m"

    # Optional provider fallback.
    cloud_fallback_enabled: bool = False
    cloud_provider: str = ""
    cloud_model: str = ""
    cloud_base_url: str = ""
    cloud_api_key: str = ""

    # Prompt/context budget layer. "budgeted" has no extra dependencies.
    # Set provider to "llmlingua" after installing backend/requirements-llmlingua.txt.
    prompt_compression_enabled: bool = True
    prompt_compression_provider: str = "budgeted"
    prompt_compression_target_ratio: float = 0.55
    prompt_compression_min_chars: int = 4500
    prompt_compression_max_chars: int = 18000
    llmlingua_model: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"

    # Durable agent identity + clearable working context.
    agent_base_personality_file: str = "./agent/BASE_PERSONALITY.md"
    agent_context_max_events: int = 36
    agent_context_max_chars: int = 14000

    agent_autonomy_level: int = 2
    agent_max_steps: int = 15
    require_approval_for_writes: bool = True
    allow_terminal_tool: bool = False
    # "hybrid" uses deterministic code for routine evidence/accounting tasks and
    # NVIDIA only for open-ended reasoning. Other supported values are "always"
    # and "deterministic".
    agent_ai_routing_mode: str = "hybrid"

    # LedgerFlow uses one company-wide business analyst. Legacy multi-agent
    # settings remain parseable for older .env files but are disabled.
    langgraph_enabled: bool = False
    langgraph_max_department_agents: int = 0

    # Apache Superset runs as a sibling service and is embedded through guest
    # tokens. Keep credentials in .env; never expose the service account to the browser.
    superset_enabled: bool = True
    superset_domain: str = "http://127.0.0.1:8088"
    superset_verify_ssl: bool = False
    superset_service_username: str = "admin"
    superset_service_password: str = "change-me"
    superset_dashboard_executive_uuid: str = ""
    superset_dashboard_finance_uuid: str = ""
    superset_dashboard_tax_uuid: str = ""
    superset_dashboard_marketing_uuid: str = ""
    superset_dashboard_operations_uuid: str = ""
    superset_dashboard_people_uuid: str = ""
    superset_dashboard_market_uuid: str = ""

    web_search_provider: str = "none"
    searxng_url: str = "http://127.0.0.1:8080"
    tavily_api_key: str = ""
    brave_search_api_key: str = ""

    validation_interval_minutes: int = 15
    memory_recent_messages: int = 12
    memory_compaction_threshold: int = 40
    max_upload_mb: int = 100
    super_guarantee_rate: float = 0.12

    # Optional project-folder intake. Drop files into file_drop/permanent or
    # file_drop/recurring and LedgerFlow will queue them through the same staged
    # processor as browser uploads. Files are archived after they are queued.
    folder_intake_enabled: bool = True
    folder_intake_dir: str = "./data/source_files"
    folder_intake_scan_seconds: int = 5

    # Optional local OCR for image-only PDFs. Tesseract must be installed on the
    # machine; failures fall back to preservation and human review.
    ocr_enabled: bool = True
    ocr_max_pages: int = 8
    ocr_dpi: int = 180
    tesseract_cmd: str = ""

    # DuckDB is embedded and must not be opened for writing by two app processes.
    duckdb_connect_retries: int = 12
    duckdb_retry_delay_seconds: float = 0.25

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def root_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else self.root_dir / path

    @property
    def base_personality_path(self) -> Path:
        path = Path(self.agent_base_personality_file)
        return path if path.is_absolute() else self.root_dir / path

    @property
    def folder_intake_path(self) -> Path:
        path = Path(self.folder_intake_dir)
        return path if path.is_absolute() else self.root_dir / path


settings = Settings()
