from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from .config import settings


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _budgeted_json(value: Any, max_chars: int) -> str:
    """Deterministically keep high-value JSON fields inside a character budget."""
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(text) <= max_chars:
        return text
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        priority = [
            "company", "financial_snapshot", "summary", "open_validations", "accounts",
            "recent_invoices", "recent_transactions", "forecast", "working_context",
            "company_baseline", "file_context", "market_snapshot", "information_requests",
        ]
        keys = priority + [key for key in value if key not in priority]
        for key in keys:
            candidate_value = value.get(key)
            if isinstance(candidate_value, list):
                candidate_value = candidate_value[:6]
            elif isinstance(candidate_value, dict):
                candidate_value = dict(list(candidate_value.items())[:18])
            candidate = {**result, key: candidate_value}
            encoded = json.dumps(candidate, ensure_ascii=False, default=str, separators=(",", ":"))
            if len(encoded) > max_chars:
                continue
            result[key] = candidate_value
        text = json.dumps(result, ensure_ascii=False, default=str, separators=(",", ":"))
    return text[:max_chars]


@lru_cache(maxsize=1)
def _llmlingua_compressor():
    from llmlingua import PromptCompressor  # type: ignore
    return PromptCompressor(model_name=settings.llmlingua_model, use_llmlingua2=True)


def compress_context(value: Any) -> tuple[str, dict[str, Any]]:
    original = json.dumps(value, ensure_ascii=False, default=str)
    original_tokens = _estimate_tokens(original)
    if not settings.prompt_compression_enabled or len(original) < settings.prompt_compression_min_chars:
        return original, {"provider": "off", "original_tokens": original_tokens, "compressed_tokens": original_tokens}

    max_chars = max(2500, settings.prompt_compression_max_chars)
    provider = settings.prompt_compression_provider.strip().lower()
    budgeted = _budgeted_json(value, max_chars)

    if provider == "llmlingua":
        try:
            rate = min(0.95, max(0.2, settings.prompt_compression_target_ratio))
            result = _llmlingua_compressor().compress_prompt(
                budgeted,
                rate=rate,
                force_tokens=["\n", "?", "{", "}", ":"],
            )
            compressed = str(result.get("compressed_prompt") or budgeted)
            return compressed, {
                "provider": "llmlingua-2",
                "original_tokens": original_tokens,
                "compressed_tokens": _estimate_tokens(compressed),
            }
        except Exception as exc:
            provider = f"budgeted-fallback:{type(exc).__name__}"

    # Remove redundant whitespace only after deterministic field budgeting.
    compressed = re.sub(r"\s+", " ", budgeted).strip()
    return compressed, {
        "provider": provider or "budgeted",
        "original_tokens": original_tokens,
        "compressed_tokens": _estimate_tokens(compressed),
    }
