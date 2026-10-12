"""Conservative suggestions: narrow interests or explicitly named trip locations."""
from collections import defaultdict

from ai_service import AIService
from models import INTERESTS


def suggestions(entries):
    groups = defaultdict(list)
    for entry in entries:
        metadata = entry["metadata"]
        topics = {t.casefold() for t in [*metadata.tags, *metadata.chapter_topics]}
        for topic in INTERESTS:
            if topic.casefold() in topics:
                groups[topic].append(entry["id"])
        location = entry["location"] or metadata.location
        if "travel" in topics and location:
            groups[f"Trip to {location.strip().casefold()}"].append(entry["id"])
    return [{"topic": topic, "title": f"My {topic} Journey" if topic in INTERESTS else topic.capitalize(),
             "entry_ids": ids} for topic, ids in sorted(groups.items()) if len(ids) >= 2]


class ChapterService:
    def __init__(self, db, ai=None):
        self.db = db
        self.ai = ai or AIService()

    def suggestions(self):
        existing = {frozenset(e["id"] for e in self.db.chapter_entries(c["id"])) for c in self.db.list_chapters()}
        return [s for s in suggestions(self.db.list_entries()) if frozenset(s["entry_ids"]) not in existing]

    def generate(self, chapter_id):
        chapter = self.db.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError("Chapter no longer exists")
        entries = self.db.chapter_entries(chapter_id)
        if not entries:
            raise ValueError("Add chapter memories before generating a story")
        result = self.ai.narrate(entries, chapter["title"])
        self.db.save_chapter_narrative(chapter_id, result.value, result.mode)
        return result
