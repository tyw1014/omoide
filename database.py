"""Small SQLite repository. Foreign keys, parameterized SQL, and explicit transactions."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from models import MemoryInput, Metadata

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
 occurred_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 location TEXT, media_path TEXT, metadata_json TEXT NOT NULL, processing_mode TEXT NOT NULL,
 processing_note TEXT, synthetic INTEGER NOT NULL DEFAULT 0, demo_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS chapters (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 narrative_json TEXT, processing_mode TEXT
);
CREATE TABLE IF NOT EXISTS chapter_entries (
 chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
 entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
 PRIMARY KEY(chapter_id,entry_id)
);
CREATE TABLE IF NOT EXISTS recaps (
 id INTEGER PRIMARY KEY, period_type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
 narrative_json TEXT NOT NULL, statistics_json TEXT NOT NULL, processing_mode TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(period_type,start_date,end_date)
);
CREATE TABLE IF NOT EXISTS recap_sources (
 recap_id INTEGER NOT NULL REFERENCES recaps(id) ON DELETE CASCADE,
 entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
 PRIMARY KEY(recap_id,entry_id)
);
CREATE INDEX IF NOT EXISTS entries_date ON entries(occurred_at);
"""


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        item = dict(row)
        if "metadata_json" in item:
            item["metadata"] = Metadata.model_validate_json(item.pop("metadata_json"))
        for field in ("narrative_json", "statistics_json"):
            if field in item:
                item[field.removesuffix("_json")] = json.loads(item.pop(field)) if item[field] else None
        return item

    @staticmethod
    def invalidate(conn, entry_id=None, occurred_at=None):
        if entry_id is not None:
            conn.execute("UPDATE chapters SET narrative_json=NULL,processing_mode=NULL WHERE id IN (SELECT chapter_id FROM chapter_entries WHERE entry_id=?)", (entry_id,))
            conn.execute("DELETE FROM recaps WHERE id IN (SELECT recap_id FROM recap_sources WHERE entry_id=?)", (entry_id,))
        if occurred_at:
            conn.execute("DELETE FROM recaps WHERE start_date<=? AND end_date>=?", (occurred_at, occurred_at))

    def create_entry(self, memory: MemoryInput, metadata: Metadata, mode, *, media_path=None, note=None, synthetic=False, demo_key=None):
        memory = MemoryInput.model_validate(memory)
        metadata = Metadata.model_validate(metadata)
        with self.connect() as c:
            cur = c.execute("INSERT INTO entries (title,content,occurred_at,location,media_path,metadata_json,processing_mode,processing_note,synthetic,demo_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (memory.title, memory.content, memory.occurred_at.isoformat(), memory.location, media_path, metadata.model_dump_json(), mode, note, int(synthetic), demo_key))
            self.invalidate(c, occurred_at=memory.occurred_at.isoformat())
            return cur.lastrowid

    def get_entry(self, entry_id):
        with self.connect() as c:
            return self.decode(c.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone())

    def list_entries(self, start=None, end=None):
        with self.connect() as c:
            if start and end:
                rows = c.execute("SELECT * FROM entries WHERE occurred_at BETWEEN ? AND ? ORDER BY occurred_at DESC,id DESC", (str(start), str(end)))
            else:
                rows = c.execute("SELECT * FROM entries ORDER BY occurred_at DESC,id DESC")
            return [self.decode(row) for row in rows]

    def update_entry(self, entry_id, memory: MemoryInput, metadata: Metadata, mode, *, media_path=None, note=None):
        memory = MemoryInput.model_validate(memory)
        metadata = Metadata.model_validate(metadata)
        with self.connect() as c:
            old = c.execute("SELECT occurred_at FROM entries WHERE id=?", (entry_id,)).fetchone()
            if old is None:
                raise ValueError("Memory no longer exists")
            self.invalidate(c, entry_id, old["occurred_at"])
            self.invalidate(c, occurred_at=memory.occurred_at.isoformat())
            c.execute("UPDATE entries SET title=?,content=?,occurred_at=?,location=?,media_path=?,metadata_json=?,processing_mode=?,processing_note=? WHERE id=?",
                      (memory.title, memory.content, memory.occurred_at.isoformat(), memory.location, media_path, metadata.model_dump_json(), mode, note, entry_id))

    def delete_entry(self, entry_id):
        with self.connect() as c:
            old = c.execute("SELECT occurred_at FROM entries WHERE id=?", (entry_id,)).fetchone()
            if old:
                self.invalidate(c, entry_id, old["occurred_at"])
                c.execute("DELETE FROM entries WHERE id=?", (entry_id,))

    def list_chapters(self):
        with self.connect() as c:
            return [self.decode(r) for r in c.execute("SELECT c.*,COUNT(ce.entry_id) AS entry_count FROM chapters c LEFT JOIN chapter_entries ce ON ce.chapter_id=c.id GROUP BY c.id ORDER BY c.id DESC")]

    def get_chapter(self, chapter_id):
        with self.connect() as c:
            return self.decode(c.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone())

    def chapter_entries(self, chapter_id):
        with self.connect() as c:
            return [self.decode(r) for r in c.execute("SELECT e.* FROM entries e JOIN chapter_entries ce ON ce.entry_id=e.id WHERE ce.chapter_id=? ORDER BY e.occurred_at,e.id", (chapter_id,))]

    def create_chapter(self, title, description, entry_ids):
        if not title.strip() or len(title) > 160 or len(description) > 3000:
            raise ValueError("Use a title of 1–160 characters and a description up to 3,000 characters")
        with self.connect() as c:
            cid = c.execute("INSERT INTO chapters(title,description) VALUES (?,?)", (title.strip(), description.strip())).lastrowid
            c.executemany("INSERT INTO chapter_entries VALUES (?,?)", [(cid, i) for i in set(entry_ids)])
            return cid

    def update_chapter(self, chapter_id, title, description, entry_ids):
        if not title.strip() or len(title) > 160 or len(description) > 3000:
            raise ValueError("Invalid chapter title or description")
        with self.connect() as c:
            c.execute("UPDATE chapters SET title=?,description=?,narrative_json=NULL,processing_mode=NULL WHERE id=?", (title.strip(), description.strip(), chapter_id))
            c.execute("DELETE FROM chapter_entries WHERE chapter_id=?", (chapter_id,))
            c.executemany("INSERT INTO chapter_entries VALUES (?,?)", [(chapter_id, i) for i in set(entry_ids)])

    def save_chapter_narrative(self, chapter_id, narrative, mode):
        narrative.verify_sources({e["id"] for e in self.chapter_entries(chapter_id)})
        with self.connect() as c:
            c.execute("UPDATE chapters SET narrative_json=?,processing_mode=? WHERE id=?", (narrative.model_dump_json(), mode, chapter_id))

    def delete_chapter(self, chapter_id):
        with self.connect() as c:
            c.execute("DELETE FROM chapters WHERE id=?", (chapter_id,))

    def save_recap(self, period, start, end, narrative, statistics, mode, entry_ids):
        narrative.verify_sources(set(entry_ids))
        with self.connect() as c:
            c.execute("DELETE FROM recaps WHERE period_type=? AND start_date=? AND end_date=?", (period, str(start), str(end)))
            rid = c.execute("INSERT INTO recaps(period_type,start_date,end_date,narrative_json,statistics_json,processing_mode) VALUES (?,?,?,?,?,?)", (period, str(start), str(end), narrative.model_dump_json(), json.dumps(statistics), mode)).lastrowid
            c.executemany("INSERT INTO recap_sources VALUES (?,?)", [(rid, i) for i in set(entry_ids)])
            return rid

    def get_recap(self, period, start, end):
        with self.connect() as c:
            return self.decode(c.execute("SELECT * FROM recaps WHERE period_type=? AND start_date=? AND end_date=?", (period, str(start), str(end))).fetchone())

    def has_demo_key(self, key):
        with self.connect() as c:
            return c.execute("SELECT 1 FROM entries WHERE demo_key=?", (key,)).fetchone() is not None
