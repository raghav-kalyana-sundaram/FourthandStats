"""Time / date utilities."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC datetime as an ISO 8601 string."""
    return utc_now().isoformat()


def parse_season_range(spec: str) -> list[int]:
    """Parse a season specification string into a list of integer seasons.

    Supports:
        "2025"         → [2025]
        "2024 2025"    → [2024, 2025]
        "2020-2025"    → [2020, 2021, 2022, 2023, 2024, 2025]
        "1999-2025"    → full range
    """
    spec = spec.strip()
    if "-" in spec and not spec.startswith("-"):
        parts = spec.split("-")
        if len(parts) == 2:
            start, end = int(parts[0].strip()), int(parts[1].strip())
            return list(range(start, end + 1))
    return [int(s.strip()) for s in spec.replace(",", " ").split()]
