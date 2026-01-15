"""Operating hours value object."""

from dataclasses import dataclass
from datetime import time
from typing import Self


@dataclass(frozen=True, slots=True)
class TimeRange:
    """A time range within a day."""

    start: time
    end: time

    def contains(self, t: time) -> bool:
        """Check if a time falls within this range."""
        if self.start <= self.end:
            return self.start <= t <= self.end
        # Handle overnight ranges (e.g., 22:00-02:00)
        return t >= self.start or t <= self.end


@dataclass(frozen=True, slots=True)
class OperatingHours:
    """Parsed business operating hours.

    Parses OSM opening_hours format (simplified subset):
    - "Mo-Fr 08:00-18:00"
    - "Mo-Fr 08:00-18:00; Sa 08:00-12:00"
    - "24/7"
    """

    raw: str
    schedule: dict[int, list[TimeRange]]  # weekday (0=Mon) -> time ranges
    is_24_7: bool = False

    def is_open_at(self, weekday: int, t: time) -> bool:
        """Check if open at given weekday (0=Monday) and time."""
        if self.is_24_7:
            return True

        ranges = self.schedule.get(weekday, [])
        return any(r.contains(t) for r in ranges)

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Parse OSM opening_hours string."""
        raw = raw.strip()

        if raw.lower() in ("24/7", "24 hours"):
            return cls(raw=raw, schedule={}, is_24_7=True)

        schedule: dict[int, list[TimeRange]] = {}
        day_map = {"mo": 0, "tu": 1, "we": 2, "th": 3, "fr": 4, "sa": 5, "su": 6}

        # Split by semicolon for multiple rules
        for rule in raw.split(";"):
            rule = rule.strip()
            if not rule:
                continue

            try:
                # Simple parsing: "Mo-Fr 08:00-18:00" or "Sa 08:00-12:00"
                parts = rule.split()
                if len(parts) < 2:
                    continue

                days_part = parts[0].lower()
                time_part = parts[1]

                # Parse days
                days: list[int] = []
                if "-" in days_part:
                    start_day, end_day = days_part.split("-")
                    start_idx = day_map.get(start_day[:2], -1)
                    end_idx = day_map.get(end_day[:2], -1)
                    if start_idx >= 0 and end_idx >= 0:
                        days = list(range(start_idx, end_idx + 1))
                else:
                    day_idx = day_map.get(days_part[:2], -1)
                    if day_idx >= 0:
                        days = [day_idx]

                # Parse time range
                if "-" in time_part:
                    start_str, end_str = time_part.split("-")
                    start_time = time.fromisoformat(start_str)
                    end_time = time.fromisoformat(end_str)
                    time_range = TimeRange(start=start_time, end=end_time)

                    for day in days:
                        if day not in schedule:
                            schedule[day] = []
                        schedule[day].append(time_range)
            except (ValueError, IndexError):
                # Skip unparseable rules
                continue

        return cls(raw=raw, schedule=schedule, is_24_7=False)
