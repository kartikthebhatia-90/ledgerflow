from __future__ import annotations

from typing import Any

import httpx

from .config import settings


async def call_chat_model(
    *,
    system: str,
    prompt: str,
    fallback: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[str, str, bool, dict[str, Any]]:
    """Call the configured OpenAI-compatible model without coupling orchestration to UI code."""
    provider = settings.model_provider.strip().lower()
    metadata: dict[str, Any] = {
        "provider": provider,
        "model": "",
        "connected": False,
        "fallback": False,
    }

    if provider == "nvidia":
        metadata["model"] = settings.nvidia_model
        if not settings.nvidia_api_key:
            metadata.update({"fallback": True, "reason": "NVIDIA_API_KEY is missing"})
            return fallback, "deterministic business analyst", False, metadata
        payload = {
            "model": settings.nvidia_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": settings.model_temperature if temperature is None else temperature,
            "max_tokens": max_tokens or settings.model_max_output_tokens,
            "stream": False,
        }
        try:
            timeout = float(settings.model_timeout_seconds)
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=timeout, connect=15.0),
                trust_env=False,
            ) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.nvidia_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            content = str((((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
            if not content:
                metadata.update({"fallback": True, "reason": "empty model response"})
                return fallback, "deterministic business analyst", False, metadata
            usage = body.get("usage") or {}
            metadata.update(
                {
                    "connected": True,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                }
            )
            return content, f"NVIDIA NIM: {settings.nvidia_model}", True, metadata
        except Exception as exc:
            metadata.update({"fallback": True, "reason": f"{type(exc).__name__}: {exc}"})
            return fallback, "deterministic business analyst", False, metadata

    if provider == "ollama" and settings.ollama_enabled:
        metadata["model"] = settings.ollama_model
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": {
                "temperature": settings.model_temperature if temperature is None else temperature,
                "num_ctx": min(max(settings.model_context_size, 1024), 32768),
                "num_predict": max_tokens or settings.model_max_output_tokens,
            },
        }
        try:
            timeout = float(settings.ollama_timeout_seconds)
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=timeout, connect=10.0),
                trust_env=False,
            ) as client:
                response = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
            content = str(response.json().get("message", {}).get("content", "")).strip()
            if content:
                metadata["connected"] = True
                return content, f"Ollama: {settings.ollama_model}", True, metadata
        except Exception as exc:
            metadata["reason"] = f"{type(exc).__name__}: {exc}"

    metadata.update({"fallback": True, "reason": metadata.get("reason") or "provider unavailable"})
    return fallback, "deterministic business analyst", False, metadata
