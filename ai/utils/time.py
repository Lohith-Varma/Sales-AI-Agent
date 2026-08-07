"""Timezone-safe clocks, deadlines, and duration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from time import perf_counter


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Convert an aware timestamp to UTC and reject ambiguous naive values."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


def duration_seconds(started_at: datetime, ended_at: datetime) -> float:
    """Return a positive duration between two aware timestamps."""

    start_utc = ensure_utc(started_at)
    end_utc = ensure_utc(ended_at)
    if end_utc <= start_utc:
        raise ValueError("ended_at must be later than started_at")
    return (end_utc - start_utc).total_seconds()


def add_business_days(reference: date, business_days: int) -> date:
    """Add weekdays to a date without assuming a regional holiday calendar."""

    if business_days < 0:
        raise ValueError("business_days cannot be negative")

    result = reference
    remaining = business_days
    while remaining:
        result += timedelta(days=1)
        if result.weekday() < 5:
            remaining -= 1
    return result


@dataclass(frozen=True, slots=True)
class MonotonicTimer:
    """Measure elapsed time without being affected by wall-clock adjustments."""

    _started: float = field(default_factory=perf_counter)

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed monotonic seconds."""

        return max(0.0, perf_counter() - self._started)

    @property
    def elapsed_milliseconds(self) -> float:
        """Return elapsed monotonic milliseconds."""

        return self.elapsed_seconds * 1_000


@dataclass(frozen=True, slots=True)
class Deadline:
    """A monotonic timeout budget shared across cooperating operations."""

    timeout_seconds: float
    _started: float = field(default_factory=perf_counter)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @property
    def elapsed_seconds(self) -> float:
        """Return time consumed from the deadline budget."""

        return max(0.0, perf_counter() - self._started)

    @property
    def remaining_seconds(self) -> float:
        """Return the non-negative time remaining in the budget."""

        return max(0.0, self.timeout_seconds - self.elapsed_seconds)

    @property
    def expired(self) -> bool:
        """Return whether the timeout budget has been exhausted."""

        return self.remaining_seconds <= 0.0

    def require_remaining(self) -> float:
        """Return remaining seconds or raise ``TimeoutError`` when expired."""

        remaining = self.remaining_seconds
        if remaining <= 0:
            raise TimeoutError("deadline expired")
        return remaining


__all__ = [
    "Deadline",
    "MonotonicTimer",
    "add_business_days",
    "duration_seconds",
    "ensure_utc",
    "utc_now",
]
