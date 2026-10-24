import io
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from pydantic import ValidationError

from ai_service import AIService, CloudProvider, DEMO_LABEL, DemoProvider, GeminiProvider
from chapter_service import ChapterService, suggestions
from database import Database
from demo_data import load_demo
from models import MemoryInput, Metadata, Narrative
from recap_service import RecapService, period_bounds, statistics


def memory(content="Basketball practice with friends.", when=date(2026, 10, 10), **kwargs):
    return MemoryInput(content=content, occurred_at=when, **kwargs)


def test_persistence_edit_and_original_preservation(db, service):
    original = "  Today I played basketball.\nMy words stay unchanged.  "
    eid = service.create(memory(original, title="Practice"))
    reopened = Database(db.path)
    entry = reopened.get_entry(eid)
    assert entry["content"] == original
    assert entry["occurred_at"] == "2026-10-10"
    created = datetime.fromisoformat(entry["created_at"])
    assert abs((datetime.now(timezone.utc) - created).total_seconds()) < 60
    service.update(eid, memory("Learning guitar", title="New title"))
    assert reopened.get_entry(eid)["title"] == "New title"
    assert reopened.get_entry(eid)["metadata"].tags == ["Guitar"]


def test_metadata_corrections(db, service):
    eid = service.create(memory())
    metadata = db.get_entry(eid)["metadata"].model_copy(update={"tags": ["My practice"], "is_milestone": True})
    service.update(eid, memory(), metadata=metadata)
    assert db.get_entry(eid)["processing_mode"] == "User edited"
    assert db.get_entry(eid)["metadata"].tags == ["My practice"]


def test_entry_delete_cascades_and_invalidates_stories(db, service):
    eid = service.create(memory())
    cid = db.create_chapter("Basketball", "", [eid])
    ChapterService(db).generate(cid)
    RecapService(db).generate("Weekly", date(2026, 10, 10))
    service.delete(eid)
    assert db.get_entry(eid) is None
    assert db.chapter_entries(cid) == []
    assert db.get_chapter(cid)["narrative"] is None
    assert db.get_recap("Weekly", *period_bounds("Weekly", date(2026, 10, 10))) is None
    with db.connect() as conn:
        assert list(conn.execute("PRAGMA foreign_key_check")) == []
        assert conn.execute("SELECT COUNT(*) FROM recap_sources").fetchone()[0] == 0


def test_edit_and_insert_invalidate_cached_recaps(db, service):
    eid = service.create(memory())
    cid = db.create_chapter("Journey", "", [eid])
    ChapterService(db).generate(cid)
    RecapService(db).generate("Monthly", date(2026, 10, 1))
    service.update(eid, memory("Guitar practice", when=date(2026, 9, 10)))
    assert db.get_chapter(cid)["narrative"] is None
    assert db.get_recap("Monthly", date(2026, 10, 1), date(2026, 10, 31)) is None
    RecapService(db).generate("Monthly", date(2026, 9, 1))
    service.create(memory("Tea with friends", when=date(2026, 9, 11)))
    assert db.get_recap("Monthly", date(2026, 9, 1), date(2026, 9, 30)) is None


def test_stats_use_occurrence_dates_and_inclusive_boundaries(db, service):
    service.create(memory(when=date(2026, 10, 5), location="Court"))
    service.create(memory("First time I played an entire song on guitar", when=date(2026, 10, 11)))
    service.create(memory("Tea with friends", when=date(2026, 10, 12)))
    service.create(memory("Basketball practice", when=date(2026, 9, 30)))
    weekly = statistics(db.list_entries(*period_bounds("Weekly", date(2026, 10, 10))))
    assert weekly["count"] == 2
    assert weekly["sports_count"] == 1
    assert weekly["topics"]["Guitar"] == 1
    assert weekly["locations"] == {"Court": 1}
    assert len(weekly["milestone_ids"]) == 1
    assert statistics(db.list_entries(*period_bounds("Monthly", date(2026, 10, 1))))["count"] == 3


@pytest.mark.parametrize("period,anchor,expected", [
    ("Weekly", date(2027, 1, 1), (date(2026, 12, 28), date(2027, 1, 3))),
    ("Monthly", date(2028, 2, 12), (date(2028, 2, 1), date(2028, 2, 29))),
    ("Yearly", date(2026, 10, 12), (date(2026, 1, 1), date(2026, 12, 31))),
])
def test_period_boundaries(period, anchor, expected):
    assert period_bounds(period, anchor) == expected


def test_validated_ai_metadata_before_insertion(db, service):
    valid = DemoProvider().extract("Guitar practice").model_dump()
    with pytest.raises(ValidationError):
        db.create_entry(memory(), {**valid, "tags": "not a list"}, "Cloud")
    with pytest.raises(ValidationError):
        Metadata.model_validate({**valid, "is_milestone": "yes"})
    assert db.list_entries() == []


@pytest.mark.parametrize("provider_type", [CloudProvider, GeminiProvider])
@pytest.mark.parametrize("bad_output", ["not json", '{"summary":"missing fields"}', '{}'])
def test_cloud_malformed_output_falls_back_without_leaking(bad_output, provider_type):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, content=bad_output))])
    ai = AIService(provider_type("test-key", consent=True, client=client))
    result = ai.extract("今天跟朋友打籃球，第一次投進三分球！")
    assert result.mode == DEMO_LABEL
    assert "Basketball" in result.value.tags
    assert result.value.is_milestone
    assert "test-key" not in result.note


@pytest.mark.parametrize("provider_type", [CloudProvider, GeminiProvider])
def test_cloud_consent_guard_and_structured_request(provider_type):
    client = Mock()
    with pytest.raises(PermissionError):
        provider_type("test-key", client=client)
    client.chat.completions.create.assert_not_called()
    valid = DemoProvider().extract("Basketball practice").model_dump_json()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, content=valid))])
    result = provider_type("test-key", consent=True, client=client).extract("Basketball practice")
    assert result.activity == "sports"
    assert client.chat.completions.create.call_args.kwargs["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("provider_type", [CloudProvider, GeminiProvider])
def test_cloud_timeout_fallback(provider_type):
    client = Mock()
    client.chat.completions.create.side_effect = TimeoutError("private payload test-key")
    result = AIService(provider_type("test-key", consent=True, client=client)).extract("Guitar practice")
    assert result.mode == DEMO_LABEL
    assert "private" not in result.note


def test_specific_chapters_and_broad_tag_exclusion(db, service):
    a = service.create(memory("Basketball practice with friends", when=date(2026, 9, 1)))
    b = service.create(memory("Basketball match", when=date(2026, 10, 10)))
    service.create(memory("Guitar with friends"))
    service.create(memory("Tea with friends"))
    groups = suggestions(db.list_entries())
    assert len(groups) == 1
    assert set(groups[0]["entry_ids"]) == {a, b}
    cid = db.create_chapter(groups[0]["title"], "Across time", groups[0]["entry_ids"])
    assert [e["id"] for e in db.chapter_entries(cid)] == [a, b]
    assert ChapterService(db).suggestions() == []


def test_travel_requires_same_explicit_location(db, service):
    a = service.create(memory("Trip with friends", location="Kyoto"))
    b = service.create(memory("Travel with friends", location="kyoto"))
    service.create(memory("Travel with friends", location="Taipei"))
    service.create(memory("Travel with friends"))
    groups = suggestions(db.list_entries())
    assert len(groups) == 1
    assert set(groups[0]["entry_ids"]) == {a, b}


def test_many_to_many_membership_and_chapter_deletion(db, service):
    eid = service.create(memory())
    cid = db.create_chapter("First", "", [eid])
    second = db.create_chapter("Second", "", [eid])
    ChapterService(db).generate(cid)
    db.update_chapter(cid, "Changed", "", [])
    assert db.get_chapter(cid)["narrative"] is None
    assert db.chapter_entries(cid) == []
    db.delete_chapter(second)
    assert db.get_entry(eid) is not None


def test_narratives_reference_only_originals(db, service):
    a = service.create(memory())
    b = service.create(memory("Guitar practice"))
    cid = db.create_chapter("My days", "", [a, b])
    chapter = ChapterService(db).generate(cid)
    recap = RecapService(db).generate("Weekly", date(2026, 10, 10))
    for result in [chapter, recap]:
        assert set(result.value.source_ids()) <= {a, b}
        for eid in result.value.source_ids():
            assert db.get_entry(eid)
    invalid = recap.value.model_dump()
    invalid["overview"]["entry_ids"] = [99999]
    with pytest.raises(ValueError):
        Narrative.model_validate(invalid).verify_sources({a, b})
    with pytest.raises(ValueError):
        db.save_chapter_narrative(cid, Narrative.model_validate(invalid), "Cloud")


def test_empty_dataset(service, db):
    assert statistics([])["count"] == 0
    assert suggestions([]) == []
    with pytest.raises(ValueError):
        RecapService(db).generate("Weekly", date(2026, 10, 10))
    with pytest.raises(ValidationError):
        service.create(memory("  "))
    with pytest.raises(ValidationError):
        MemoryInput(content="A memory")


def test_photo_lifecycle_and_bad_upload(db, service):
    data = io.BytesIO()
    image = Image.new("RGB", (20, 20), "green")
    exif = Image.Exif()
    exif[270] = "Private camera metadata"
    image.save(data, "JPEG", exif=exif)
    eid = service.create(memory(), photo=data.getvalue())
    path = service.photo_path(db.get_entry(eid)["media_path"])
    assert path and path.exists()
    with Image.open(path) as decoded:
        assert not decoded.getexif()
    assert service.photo_path("../journal.sqlite3") is None
    service.delete(eid)
    assert not path.exists()
    with pytest.raises(ValueError):
        service.create(memory(), photo=b"invalid image")
    assert db.list_entries() == []


def test_photo_replace_and_remove(db, service):
    data = io.BytesIO()
    Image.new("RGB", (8, 8)).save(data, "PNG")
    eid = service.create(memory(), photo=data.getvalue())
    old = service.photo_path(db.get_entry(eid)["media_path"])
    service.update(eid, memory(), photo=data.getvalue())
    new = service.photo_path(db.get_entry(eid)["media_path"])
    assert new != old and new.exists() and not old.exists()
    service.update(eid, memory(), remove_photo=True)
    assert not new.exists() and db.get_entry(eid)["media_path"] is None


def test_demo_36_records_and_idempotence(db, tmp_path, monkeypatch):
    monkeypatch.delenv("OMOIDE_API_KEY", raising=False)
    assert load_demo(db, tmp_path / "media") == 36
    assert load_demo(db, tmp_path / "media") == 0
    entries = db.list_entries()
    assert len(entries) == 36
    assert all(e["synthetic"] and e["processing_mode"] == DEMO_LABEL for e in entries)
    assert statistics(db.list_entries(date(2026, 9, 1), date(2026, 9, 30)))["count"] == 26
    assert statistics(db.list_entries(date(2026, 10, 1), date(2026, 10, 31)))["count"] == 10
    assert statistics(db.list_entries(date(2026, 10, 5), date(2026, 10, 11)))["count"] == 6
    assert {s["topic"] for s in suggestions(entries)} >= {"Basketball", "Guitar", "Coursework", "Programming"}
