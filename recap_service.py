"""Calendar periods and counts come from stored records, never the language model."""
import calendar
from collections import Counter
from datetime import date, timedelta

from ai_service import AIService


def period_bounds(period, anchor: date):
    if period == "Weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "Monthly":
        return anchor.replace(day=1), anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    if period == "Yearly":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    raise ValueError("Select Weekly, Monthly, or Yearly")


def statistics(entries):
    topics = Counter(tag for e in entries for tag in set(e["metadata"].tags))
    locations = Counter(e["location"] or e["metadata"].location for e in entries if e["location"] or e["metadata"].location)
    return {
        "count": len(entries),
        "topics": dict(sorted(topics.items(), key=lambda x: (-x[1], x[0]))),
        "locations": dict(sorted(locations.items(), key=lambda x: (-x[1], x[0]))),
        "sports_count": sum(e["metadata"].activity == "sports" for e in entries),
        "milestone_ids": [e["id"] for e in entries if e["metadata"].is_milestone],
        "synthetic_count": sum(bool(e["synthetic"]) for e in entries),
    }


class RecapService:
    def __init__(self, db, ai=None):
        self.db = db
        self.ai = ai or AIService()

    def generate(self, period, anchor):
        start, end = period_bounds(period, anchor)
        entries = self.db.list_entries(start, end)
        if not entries:
            raise ValueError("No memories recorded in this period")
        stats = statistics(entries)
        result = self.ai.narrate(entries, f"Your {period.lower()} rewind")
        self.db.save_recap(period, start, end, result.value, stats, result.mode, [e["id"] for e in entries])
        return result
