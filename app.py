"""Omoide: a private, single-user Streamlit memory scrapbook."""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from ai_service import AIService, CloudProvider, DEMO_LABEL
from chapter_service import ChapterService
from config import data_dir
from database import Database
from demo_data import load_demo
from memory_service import MemoryService
from models import INTERESTS, MemoryInput, Metadata, Narrative
from recap_service import RecapService, period_bounds, statistics

st.set_page_config(page_title="Omoide · Your days, remembered", page_icon="🌿", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif;}
h1,h2,h3 {font-family:'Lora',Georgia,serif!important;letter-spacing:-.025em;}
.block-container {max-width:1120px;padding-top:2.4rem;padding-bottom:4rem;}
[data-testid="stSidebar"] {border-right:1px solid #e4e4d9;}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:18px;}
[data-testid="stMetric"] {background:#f0eee7;border-radius:14px;padding:16px;}
[data-testid="stMetricValue"] {font-family:'Lora',Georgia,serif;font-size:2rem;}
.eyebrow {color:#77856c;font-size:.73rem;letter-spacing:.18em;text-transform:uppercase;margin-bottom:10px;}
.brand {font-family:'Lora',Georgia,serif;font-size:2rem;color:#354c3c;margin:0;}
.intro {color:#7b8072;max-width:630px;line-height:1.7;margin-bottom:2rem;}
.journal-rule {height:1px;background:#dddcd0;margin:1.5rem 0;}
button {border-radius:10px!important;}
[data-testid="stTextInput"] input,textarea {border-radius:10px!important;}
@media (max-width:640px) {.block-container {padding-top:1.5rem;}}
</style>
""", unsafe_allow_html=True)

root = data_dir()
db = Database(root / "omoide.sqlite3")


def navigate(page):
    st.session_state.next_page = page
    st.session_state.pop("focus_entry", None)
    st.query_params.pop("entry", None)


def open_memory(entry_id):
    st.session_state.next_page = "Memories"
    st.session_state.focus_entry = entry_id
    st.query_params["entry"] = str(entry_id)


def all_memories():
    navigate("Memories")


if "page" not in st.session_state:
    st.session_state.page = "Memories"
    if "entry" in st.query_params:
        try:
            st.session_state.focus_entry = int(st.query_params["entry"])
        except (ValueError, TypeError):
            pass

if "next_page" in st.session_state:
    st.session_state.page = st.session_state.pop("next_page")


def sidebar_navigation():
    st.session_state.pop("focus_entry", None)
    st.query_params.pop("entry", None)

with st.sidebar:
    st.markdown('<p class="eyebrow">A little space for your life</p><h2 style="font-size:2.4rem;margin:0;color:#354c3c">omoide.</h2>', unsafe_allow_html=True)
    st.caption("思い出 · memories worth keeping")
    st.markdown('<div class="journal-rule"></div>', unsafe_allow_html=True)
    st.radio("Your journal", ["Memories", "Add memory", "Rewind", "Life chapters"], key="page", label_visibility="collapsed", on_change=sidebar_navigation)
    st.markdown('<div class="journal-rule"></div>', unsafe_allow_html=True)
    with st.expander("Processing & privacy"):
        processing = st.radio("Processing mode", ["Demo (offline)", "Cloud AI"], key="processing")
        consent = False
        key = os.getenv("OMOIDE_API_KEY")
        if processing == "Cloud AI":
            st.caption("OpenAI receives the text, dates, and locations used in extraction or stories. Photos stay local and are never analyzed. Viewing records sends nothing.")
            consent = st.checkbox("I agree to send selected memory text to OpenAI for processing.", key="cloud_consent", disabled=not bool(key))
            if not key:
                st.info("Set OMOIDE_API_KEY in your local .env or secure environment settings. Demo Mode is available now.")
            elif not consent:
                st.caption("Until you opt in, processing uses Demo Mode.")
        else:
            # Consent is not retained when switching back to offline mode.
            st.session_state.pop("cloud_consent", None)
            st.caption("Offline keyword rules and record excerpts. No live LLM inference or external transmission.")
    st.caption("Local journal · SQLite storage\n\nSingle-user prototype. Run only on a trusted private machine.")

ai = AIService(CloudProvider(key, os.getenv("OMOIDE_MODEL", "gpt-4o-mini"), consent=True)) if processing == "Cloud AI" and consent and key else AIService()
memories = MemoryService(db, root / "media", ai)
chapters = ChapterService(db, ai)
recaps = RecapService(db, ai)

if st.session_state.pop("notice", None) is not None:
    # The actual message is retained separately during reruns below.
    st.success(st.session_state.pop("notice_text", "Saved. Your journal is up to date."))


def flash(text):
    st.session_state.notice = True
    st.session_state.notice_text = text
    st.rerun()


def source_buttons(ids, prefix):
    for entry_id in dict.fromkeys(ids):
        entry = db.get_entry(entry_id)
        if entry:
            st.button(f"↗ #{entry_id} · {entry['title'] or 'Untitled memory'} · {entry['occurred_at']}", key=f"{prefix}-{entry_id}", on_click=open_memory, args=(entry_id,))


def show_narrative(data, mode, prefix):
    narrative = Narrative.model_validate(data)
    st.caption(f"{mode} · Generated story, separate from your originals")
    st.subheader(narrative.title)
    st.write(narrative.overview.text)
    with st.expander("Overview sources"):
        source_buttons(narrative.overview.entry_ids, prefix + "-overview")
    for index, highlight in enumerate(narrative.highlights):
        with st.container(border=True):
            st.write(highlight.text)
            source_buttons(highlight.entry_ids, f"{prefix}-highlight-{index}")
    st.write(narrative.conclusion.text)
    with st.expander("Closing sources"):
        source_buttons(narrative.conclusion.entry_ids, prefix + "-conclusion")


def show_card(entry, prefix):
    metadata = entry["metadata"]
    with st.container(border=True):
        suffix = " · Synthetic Demo Data" if entry["synthetic"] else ""
        st.caption(f"{entry['occurred_at']} · {entry['location'] or metadata.location or 'No location recorded'}{suffix}")
        st.subheader(entry["title"] or "An everyday moment")
        st.text(entry["content"][:450] + ("…" if len(entry["content"]) > 450 else ""))
        if metadata.tags or metadata.is_milestone:
            st.caption(" / ".join(metadata.tags) + (" · ★ Milestone" if metadata.is_milestone else ""))
        photo = memories.photo_path(entry["media_path"])
        if photo:
            st.image(str(photo), width=340)
            st.caption("Stored photograph · visual contents have not been analyzed")
        st.button("Open original →", key=f"{prefix}-open-{entry['id']}", on_click=open_memory, args=(entry["id"],))


def split_labels(text):
    return [s.strip() for s in text.split(",") if s.strip()]


def memory_detail(entry_id):
    st.button("← All memories", on_click=all_memories)
    entry = db.get_entry(entry_id)
    if entry is None:
        st.info("This memory has been deleted or no longer exists.")
        return
    st.caption(f"ORIGINAL MEMORY #{entry_id} · {entry['occurred_at']}" + (" · Synthetic Demo Data" if entry["synthetic"] else ""))
    st.title(entry["title"] or "An everyday moment")
    st.text(entry["content"])
    st.caption(f"Recorded {entry['created_at']} · Event date {entry['occurred_at']}")
    if entry["location"]:
        st.caption(f"Location: {entry['location']}")
    photo = memories.photo_path(entry["media_path"])
    if photo:
        st.image(str(photo), width=550)
        st.caption("Stored locally · photo contents have not been analyzed")
    metadata = entry["metadata"]
    with st.container(border=True):
        st.caption(entry["processing_mode"] + " · Metadata, separate from original content")
        st.write(metadata.summary)
        st.caption("Topics: " + (", ".join(metadata.tags) or "None recorded"))
        st.caption(f"Activity: {metadata.activity} · Milestone: {'Yes' if metadata.is_milestone else 'No'}")
        if metadata.people:
            st.caption("Mentioned people: " + ", ".join(metadata.people))
        if metadata.location:
            st.caption("Extracted / corrected location: " + metadata.location)
        if entry["processing_note"]:
            st.warning(entry["processing_note"])
    with st.expander("Edit memory & metadata"):
        with st.form(f"edit-{entry_id}"):
            title = st.text_input("Title", value=entry["title"], max_chars=160)
            occurred = st.date_input("Event date", value=datetime.fromisoformat(entry["occurred_at"]).date())
            content = st.text_area("Original description", value=entry["content"], height=150, max_chars=12000)
            location = st.text_input("Location", value=entry["location"] or "", max_chars=160)
            st.caption("You can correct generated fields below, or re-analyze the edited original.")
            summary = st.text_area("Summary", value=metadata.summary, max_chars=1200)
            tags = st.text_input("Tags (comma separated)", value=", ".join(metadata.tags))
            activity = st.selectbox("Activity", ["sports", "music", "study", "travel", "social", "everyday", "other"], index=["sports", "music", "study", "travel", "social", "everyday", "other"].index(metadata.activity))
            people = st.text_input("Mentioned people (comma separated)", value=", ".join(metadata.people))
            extracted_location = st.text_input("Metadata location", value=metadata.location or "")
            topics = st.multiselect("Suggested chapter interests", INTERESTS, default=[t for t in metadata.chapter_topics if t in INTERESTS])
            milestone = st.checkbox("This is a milestone", value=metadata.is_milestone)
            reanalyze = st.checkbox("Re-analyze original instead of saving the metadata fields above")
            upload = st.file_uploader("Replace photograph", type=["jpg", "jpeg", "png", "webp"])
            remove = st.checkbox("Remove existing photograph") if entry["media_path"] else False
            if st.form_submit_button("Save changes", type="primary"):
                try:
                    original = MemoryInput(title=title, content=content, occurred_at=occurred, location=location.strip() or None)
                    corrected = None if reanalyze else Metadata(summary=summary, tags=split_labels(tags), activity=activity, people=split_labels(people), location=extracted_location.strip() or None, is_milestone=milestone, chapter_topics=topics)
                    memories.update(entry_id, original, metadata=corrected, photo=upload.getvalue() if upload else None, remove_photo=remove)
                    flash("Memory updated. Regenerate affected stories to use the latest record.")
                except ValueError:
                    st.error("Check the description, summary, dates, and labels. Photographs must be JPEG, PNG, or WebP, up to 5 MB / 25 megapixels.")
    with st.expander("Delete this memory"):
        confirmed = st.checkbox("Delete this memory and its local photograph permanently", key=f"delete-confirm-{entry_id}")
        if st.button("Delete memory", disabled=not confirmed):
            memories.delete(entry_id)
            all_memories()
            flash("Memory and associated photo deleted. Affected stories were cleared.")


page = st.session_state.page
if page == "Memories":
    focus = st.session_state.get("focus_entry")
    if focus:
        memory_detail(focus)
    else:
        st.markdown('<p class="eyebrow">Your life, one moment at a time</p>', unsafe_allow_html=True)
        st.title("Small moments. A story only you can tell.")
        st.markdown(
            '<p class="intro">Tracing memories through everyday moments.<br>'
            '在平凡瑣碎的日常裡，找出回憶的軌跡。<br>'
            '何気ない日々に、思い出の軌跡を</p>',
            unsafe_allow_html=True,
        )
        top = st.columns([1, 1, 2])
        top[0].button("＋ Add a memory", type="primary", on_click=navigate, args=("Add memory",), use_container_width=True)
        top[1].button("Revisit your week →", on_click=navigate, args=("Rewind",), use_container_width=True)
        entries = db.list_entries()
        if not entries:
            with st.container(border=True):
                st.subheader("A fresh page, waiting for you.")
                st.write("Record a moment of your own, or explore 36 fictional memories spanning six weeks.")
                if st.button("Load Synthetic Demo Data", type="primary", key="load-demo"):
                    added = load_demo(db, root / "media")
                    flash(f"Added {added} Synthetic Demo Data records. They are clearly marked and processed offline.")
        else:
            counts = statistics(entries)
            for col, label, value in zip(st.columns(3), ["Memories kept", "Life chapters", "Recorded milestones"], [len(entries), len(db.list_chapters()), len(counts["milestone_ids"])]):
                col.metric(label, value)
            st.markdown('<div class="journal-rule"></div>', unsafe_allow_html=True)
            left, right = st.columns([2, 1])
            query = left.text_input("Find a memory", placeholder="Search your original words, title, or tags…")
            tag_choices = sorted({t for e in entries for t in e["metadata"].tags})
            topic = right.selectbox("Topic", ["All topics", *tag_choices])
            filtered = [e for e in entries if (topic == "All topics" or topic in e["metadata"].tags) and (not query or query.casefold() in " ".join([e["title"], e["content"], *e["metadata"].tags]).casefold())]
            st.caption(f"{len(filtered)} memories · newest event first")
            # Bound rendering for larger journals while keeping every record accessible.
            pages = max(1, (len(filtered) + 11) // 12)
            selected_page = st.number_input("Feed page", min_value=1, max_value=pages, value=1, step=1) if pages > 1 else 1
            columns = st.columns(2)
            for index, entry in enumerate(filtered[(selected_page - 1) * 12:selected_page * 12]):
                with columns[index % 2]:
                    show_card(entry, "feed")
            if not filtered:
                st.info("No memories match yet. Try another topic or a shorter search.")
            with st.expander("Demo data & export"):
                if st.button("Load Synthetic Demo Data", key="load-demo"):
                    flash(f"Added {load_demo(db, root / 'media')} fictional records. Existing sample records were preserved.")
                export = {
                    "format": "omoide-v1",
                    "memories": [{**e, "metadata": e["metadata"].model_dump()} for e in entries],
                    "chapters": [{**c, "entry_ids": [e["id"] for e in db.chapter_entries(c["id"])]} for c in db.list_chapters()],
                }
                st.download_button("Export journal JSON", json.dumps(export, ensure_ascii=False, indent=2), "omoide-journal.json", "application/json")
                st.caption("Export contains originals, metadata, chapters, and local photo filenames. Photo files are not embedded.")

elif page == "Add memory":
    st.markdown('<p class="eyebrow">Capture</p>', unsafe_allow_html=True)
    st.title("What would you like to remember?")
    st.write("A small detail is enough. Your original words stay yours.")
    st.caption(f"Processing: {ai.provider.label} · Photographs are stored locally and never analyzed")
    with st.form("new-memory", clear_on_submit=True):
        title = st.text_input("Title (optional)", placeholder="Give this moment a name", max_chars=160)
        col1, col2 = st.columns(2)
        occurred = col1.date_input("Event date", value=datetime.now(ZoneInfo("Asia/Taipei")).date())
        location = col2.text_input("Location (optional)", placeholder="Where did it happen?", max_chars=160)
        content = st.text_area("Your memory", placeholder="今天跟朋友去打球，終於第一次在比賽中投進壓哨三分球！", height=200, max_chars=12000)
        photo = st.file_uploader("Photograph (optional)", type=["jpg", "jpeg", "png", "webp"])
        if st.form_submit_button("Save memory", type="primary"):
            try:
                with st.spinner("Keeping this moment…"):
                    entry_id = memories.create(MemoryInput(title=title, content=content, occurred_at=occurred, location=location.strip() or None), photo=photo.getvalue() if photo else None)
                open_memory(entry_id)
                flash("Memory saved. Your original and generated metadata are shown separately below.")
            except ValueError:
                st.error("Write a description and check the date. Photographs must be JPEG, PNG, or WebP, up to 5 MB / 25 megapixels.")

elif page == "Rewind":
    st.markdown('<p class="eyebrow">Rewind</p>', unsafe_allow_html=True)
    st.title("A little look back.")
    st.write("See the threads running through the moments you recorded.")
    entries = db.list_entries()
    col1, col2 = st.columns(2)
    period = col1.selectbox("Period", ["Weekly", "Monthly", "Yearly"])
    default = datetime.fromisoformat(entries[0]["occurred_at"]).date() if entries else datetime.now(ZoneInfo("Asia/Taipei")).date()
    anchor = col2.date_input("A date in the period", value=default)
    start, end = period_bounds(period, anchor)
    st.caption(f"{start:%b %d, %Y} — {end:%b %d, %Y} · Weeks run Monday–Sunday")
    selected = db.list_entries(start, end)
    stats = statistics(selected)
    for col, label, value in zip(st.columns(3), ["Recorded memories", "Sports records", "Recorded milestones"], [stats["count"], stats["sports_count"], len(stats["milestone_ids"])]):
        col.metric(label, value)
    st.caption("Counts are computed from stored entries. They describe what you recorded, rather than everything you did.")
    if stats["synthetic_count"]:
        st.caption(f"Includes {stats['synthetic_count']} Synthetic Demo Data records.")
    with st.expander("Recorded topics & locations", expanded=bool(selected)):
        st.write("Topic counts: " + (" · ".join(f"{t}: {n}" for t, n in stats["topics"].items()) or "None"))
        st.write("Recorded location counts: " + (" · ".join(f"{t}: {n}" for t, n in stats["locations"].items()) or "None"))
    if not selected:
        st.info("No memories in this period. Choose another date or record your first moment.")
    else:
        if st.button("Generate recap", type="primary"):
            with st.spinner("Bringing your memories together…"):
                result = recaps.generate(period, anchor)
            if result.note:
                st.warning(result.note)
        saved = db.get_recap(period, start, end)
        if saved:
            show_narrative(saved["narrative"], saved["processing_mode"], "recap")
        with st.expander("All original memories in this period"):
            source_buttons([e["id"] for e in selected], "recap-all")

elif page == "Life chapters":
    st.markdown('<p class="eyebrow">Life chapters</p>', unsafe_allow_html=True)
    st.title("Some stories take more than a day.")
    st.write("Connect a practice, a project, or a trip across time. You choose which moments belong.")
    all_entries = db.list_entries()
    entry_map = {e["id"]: e for e in all_entries}

    def entry_label(i):
        e = entry_map[i]
        return f"#{i} · {e['occurred_at']} · {e['title'] or e['content'][:60]}"

    existing = db.list_chapters()
    chapter_id = st.session_state.get("chapter_id")
    if chapter_id and db.get_chapter(chapter_id):
        if st.button("← All chapters"):
            st.session_state.pop("chapter_id", None)
            st.rerun()
        chapter = db.get_chapter(chapter_id)
        st.subheader(chapter["title"])
        st.write(chapter["description"])
        member_entries = db.chapter_entries(chapter_id)
        if st.button("Generate chapter story", type="primary", disabled=not member_entries):
            with st.spinner("Following the thread…"):
                result = chapters.generate(chapter_id)
            if result.note:
                st.warning(result.note)
            chapter = db.get_chapter(chapter_id)
        if chapter["narrative"]:
            show_narrative(chapter["narrative"], chapter["processing_mode"], "chapter-story")
        st.subheader("Your timeline")
        if not member_entries:
            st.info("Add memories below to begin this chapter.")
        for entry in member_entries:
            show_card(entry, "timeline")
        with st.expander("Edit chapter & membership"):
            with st.form(f"chapter-edit-{chapter_id}"):
                title = st.text_input("Chapter title", value=chapter["title"], max_chars=160)
                description = st.text_area("Chapter description", value=chapter["description"], max_chars=3000)
                ids = st.multiselect("Member memories", list(entry_map), default=[e["id"] for e in member_entries], format_func=entry_label)
                if st.form_submit_button("Save chapter changes"):
                    try:
                        db.update_chapter(chapter_id, title, description, ids)
                        flash("Chapter updated. Generate a new story for its current members.")
                    except ValueError:
                        st.error("Give the chapter a title.")
            confirm = st.checkbox("Delete this chapter (keep its memories)")
            if st.button("Delete chapter", disabled=not confirm):
                db.delete_chapter(chapter_id)
                st.session_state.pop("chapter_id", None)
                flash("Chapter deleted. Its memories are still in your journal.")
    else:
        if existing:
            for c in existing:
                with st.container(border=True):
                    st.subheader(c["title"])
                    st.write(c["description"])
                    st.caption(f"{c['entry_count']} memories · A story across time")
                    if st.button("Open chapter →", key=f"open-chapter-{c['id']}"):
                        st.session_state.chapter_id = c["id"]
                        st.rerun()
        else:
            st.info("Your first chapter is waiting. Confirm a suggestion or create one yourself.")
        st.subheader("Threads you might want to follow")
        candidates = chapters.suggestions()
        if not candidates:
            st.caption("No new suggestions yet. Record at least two memories about a specific interest, or create a chapter manually.")
        for index, candidate in enumerate(candidates):
            with st.expander(f"{candidate['title']} · {len(candidate['entry_ids'])} memories"):
                st.caption("Suggested from shared specific topics or an explicitly named trip location. Membership is yours to confirm.")
                with st.form(f"suggestion-{index}"):
                    title = st.text_input("Chapter title", value=candidate["title"], max_chars=160)
                    ids = st.multiselect("Confirm memories", candidate["entry_ids"], default=candidate["entry_ids"], format_func=entry_label)
                    if st.form_submit_button("Create this chapter"):
                        try:
                            if not ids:
                                raise ValueError("Select at least one memory")
                            st.session_state.chapter_id = db.create_chapter(title, f"A collection of recorded {candidate['topic'].lower()} moments.", ids)
                            flash("Chapter created. Your timeline is ready; generate its story when you like.")
                        except ValueError:
                            st.error("Give the chapter a title and select at least one memory.")
        with st.expander("Create a chapter yourself"):
            with st.form("manual-chapter"):
                title = st.text_input("Chapter title", max_chars=160, placeholder="My own thread")
                description = st.text_area("Chapter description", max_chars=3000)
                ids = st.multiselect("Member memories", list(entry_map), format_func=entry_label)
                if st.form_submit_button("Create chapter"):
                    try:
                        st.session_state.chapter_id = db.create_chapter(title, description, ids)
                        flash("Chapter created.")
                    except ValueError:
                        st.error("Give the chapter a title.")

st.markdown('<div class="journal-rule"></div>', unsafe_allow_html=True)
st.caption("OMOIDE · You live your life. We help you remember it.")
