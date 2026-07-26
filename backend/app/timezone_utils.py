from __future__ import annotations

from datetime import timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_APP_TIMEZONE = "Australia/Melbourne"


def resolve_timezone(name: str | None) -> tuple[tzinfo, str, str]:
    """Return a usable timezone without allowing missing Windows tzdata to stop startup.

    Python's zoneinfo uses the operating-system timezone database when available
    and otherwise the optional PyPI tzdata package. Fresh Windows virtual
    environments often have neither until tzdata is installed.
    """
    requested = (name or DEFAULT_APP_TIMEZONE).strip() or DEFAULT_APP_TIMEZONE
    candidates: list[str] = []
    for candidate in (requested, DEFAULT_APP_TIMEZONE, "UTC"):
        if candidate not in candidates:
            candidates.append(candidate)

    errors: list[str] = []
    for candidate in candidates:
        try:
            return ZoneInfo(candidate), candidate, ""
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            errors.append(f"{candidate}: {type(exc).__name__}")

    # Absolute last resort. This keeps the application operational and avoids
    # pretending that a fixed offset is Melbourne time during daylight saving.
    warning = "Timezone database unavailable; UTC fallback active. " + "; ".join(errors)
    return timezone.utc, "UTC", warning
