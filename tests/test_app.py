from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from database import Database

APP = Path(__file__).resolve().parents[1] / "app.py"


def label(elements, text):
    return next(e for e in elements if e.label == text)


def launch(tmp_path, monkeypatch):
    monkeypatch.setenv("OMOIDE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OMOIDE_API_KEY", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    return app


def test_ui_create_analyze_recap_chapter_source_edit_delete(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    label(app.button, "＋ Add a memory").click().run()
    label(app.text_input, "Title (optional)").set_value("My basketball moment")
    label(app.text_area, "Your memory").set_value("First time I scored a three-pointer playing basketball with friends!")
    label(app.date_input, "Event date").set_value(date(2026, 10, 10))
    label(app.button, "Save memory").click().run()
    assert not app.exception
    assert "My basketball moment" in [t.value for t in app.title]
    db = Database(tmp_path / "omoide.sqlite3")
    first = db.list_entries()[0]
    assert "Basketball" in first["metadata"].tags
    assert first["processing_mode"] == "Demo · rule-based"

    label(app.radio, "Your journal").set_value("Add memory").run()
    label(app.text_input, "Title (optional)").set_value("Earlier practice")
    label(app.text_area, "Your memory").set_value("Basketball practice with friends.")
    label(app.date_input, "Event date").set_value(date(2026, 10, 6))
    label(app.button, "Save memory").click().run()
    assert not app.exception

    label(app.radio, "Your journal").set_value("Rewind").run()
    assert label(app.metric, "Recorded memories").value == "2"
    label(app.button, "Generate recap").click().run()
    assert not app.exception
    assert any("Demo · rule-based" in c.value for c in app.caption)
    next(b for b in app.button if b.label.startswith("↗ #")).click().run()
    assert not app.exception and any("My basketball moment" == t.value or "Earlier practice" == t.value for t in app.title)

    label(app.radio, "Your journal").set_value("Life chapters").run()
    label(app.button, "Create this chapter").click().run()
    assert not app.exception
    label(app.button, "Generate chapter story").click().run()
    assert not app.exception
    chapter = db.list_chapters()[0]
    assert chapter["narrative"]
    assert len(db.chapter_entries(chapter["id"])) == 2
    label(app.button, "Open original →").click().run()
    assert not app.exception
    label(app.text_input, "Title").set_value("Edited practice")
    label(app.text_input, "Tags (comma separated)").set_value("Basketball, Practice")
    label(app.button, "Save changes").click().run()
    assert not app.exception
    assert app.title[0].value == "Edited practice"
    assert db.get_chapter(chapter["id"])["narrative"] is None
    label(app.checkbox, "Delete this memory and its local photograph permanently").check().run()
    label(app.button, "Delete memory").click().run()
    assert not app.exception and len(db.list_entries()) == 1
    assert len(db.chapter_entries(chapter["id"])) == 1


def test_ui_sample_loading_monthly_yearly_and_empty_states(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    label(app.radio, "Your journal").set_value("Rewind").run()
    assert label(app.metric, "Recorded memories").value == "0"
    assert not any(b.label == "Generate recap" for b in app.button)
    label(app.radio, "Your journal").set_value("Memories").run()
    label(app.button, "Load Synthetic Demo Data").click().run()
    assert not app.exception
    assert label(app.metric, "Memories kept").value == "36"
    label(app.button, "Load Synthetic Demo Data").click().run()
    assert label(app.metric, "Memories kept").value == "36"
    label(app.radio, "Your journal").set_value("Rewind").run()
    label(app.selectbox, "Period").set_value("Monthly").run()
    assert label(app.metric, "Recorded memories").value == "10"
    label(app.button, "Generate recap").click().run()
    assert not app.exception
    label(app.selectbox, "Period").set_value("Yearly").run()
    assert label(app.metric, "Recorded memories").value == "36"
    label(app.button, "Generate recap").click().run()
    assert not app.exception


def test_ui_missing_cloud_key_stays_offline(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    label(app.radio, "Processing mode").set_value("Cloud AI").run()
    assert not app.exception
    consent = label(app.checkbox, "I agree to send selected memory text to OpenAI for processing.")
    assert consent.disabled and not consent.value
    label(app.radio, "Your journal").set_value("Add memory").run()
    assert any("Demo · rule-based" in c.value for c in app.caption)
