from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import settings


def walkthrough_path() -> Path:
    return settings.root_dir / "agent" / "GUIDED_WALKTHROUGHS.json"


def load_walkthrough(name: str = "overview") -> dict[str, Any]:
    path = walkthrough_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        script = payload.get(name) or {}
        return script if isinstance(script, dict) else {}
    except Exception:
        return {}


class _SafeValues(defaultdict[str, str]):
    def __missing__(self, key: str) -> str:
        return "—"


def render_template(template: str, values: dict[str, Any]) -> str:
    safe = _SafeValues(str)
    safe.update({key: str(value) for key, value in values.items()})
    try:
        return str(template).format_map(safe)
    except Exception:
        return str(template)
