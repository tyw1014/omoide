# Omoide（思い出）

**Tracing memories through everyday moments.**

在平凡瑣碎的日常裡，找出回憶的軌跡。

何気ない日々に、思い出の軌跡を

A working, single-user journaling MVP for the 2026 ASUS UGen AI League Hackathon. Capture a memory, revisit a week, and connect related records into a Life Chapter. Python, Streamlit, SQLite, and local media storage keep the prototype small enough to run on a laptop.

## Run locally

### 1. Install the prerequisites and get the project

Install [Python](https://www.python.org/downloads/) **3.11 or newer** (3.12 recommended) and [Git](https://git-scm.com/downloads). On Windows, enable the Python installer option to add Python to `PATH` if offered. The cloud instance was tested with Python 3.12.14 on Linux; macOS and Windows have not been tested.

Open **Terminal** on Linux/macOS, or **PowerShell** / **Command Prompt** on Windows, then download the project:

```text
git clone https://github.com/tyw1014/omoide.git
cd omoide
```

If you already have the project, open a terminal in its `omoide` folder and skip both commands above. Run the commands below from the folder containing `app.py` and `requirements.lock`.

### 2. Set up and launch for your operating system

#### Linux (Bash)

Check that `python3 --version` reports 3.11 or newer, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m streamlit run app.py
```

On Ubuntu/Debian, if creating the environment reports that `venv` or `ensurepip` is missing, install the matching venv package (for example, `sudo apt install python3.12-venv` for Python 3.12), then retry with that Python interpreter.

#### macOS (Terminal, Zsh or Bash)

Check that `python3 --version` reports 3.11 or newer. If it reports an older version, install a supported Python version using the link above. Then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m streamlit run app.py
```

#### Windows (PowerShell or Command Prompt)

Check that `py -3 --version` reports 3.11 or newer, then run these commands in either shell:

```text
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If `py` is unavailable but `python --version` reports 3.11 or newer, use `python -m venv .venv` for the first command instead. The remaining commands stay the same. These commands use the virtual environment directly, so activation and PowerShell execution-policy changes are unnecessary. For other `python` commands in this README, use `.\.venv\Scripts\python.exe` in place of `python` on Windows.

### 3. Open the app, stop it, and run it again

Open the local address printed by Streamlit in your browser. The checked-in server configuration binds to the loopback interface and disables usage telemetry. Keep the terminal open while using the app; press **Ctrl+C** in that terminal to stop it.

For later launches, open a terminal in the project folder. On Linux/macOS, run `source .venv/bin/activate`, then `python -m streamlit run app.py`. On Windows, run `.\.venv\Scripts\python.exe -m streamlit run app.py`. You only need to reinstall dependencies when the dependency files change or you recreate the virtual environment.

**No API key is required.** The application defaults to **Demo Mode**: offline keyword rules for metadata and original-record excerpts for stories. These results are labeled `Demo · rule-based`; they are not live LLM inference.

Click **Load Synthetic Demo Data** on the empty home screen, or run:

```bash
python demo_data.py
```

This adds 36 fictional records between September 1 and October 11, 2026. Every sample is marked **Synthetic Demo Data**. Stable sample keys prevent duplicate insertion when loading again. Deleted sample records can be reloaded; edited samples retain their keys and are preserved. Sample loading always runs offline, including when cloud processing is selected.

## What works

- **Memories:** create, view, edit, search, filter, and delete records; choose the event date independently from the creation timestamp.
- **Metadata:** original descriptions remain separate from generated summaries, tags, activity, explicit entities, and milestone flags. Correct metadata manually or explicitly re-analyze an edited record.
- **Rewind:** calendar weeks (Monday–Sunday), months, and years, with deterministic counts of memories, topics, sports records, locations, and milestones. Generate and retain a cited recap for the selected period.
- **Life Chapters:** suggestions based on specific interests or explicit trip locations; confirm membership before creating a chapter. Edit the title, description, and membership; one memory can belong to multiple chapters. Generate a cited story and view the chronological timeline.
- **Traceability:** every story section has source buttons that open the original entry. Editing, deleting, or changing chapter membership clears affected stored stories; additions clear recaps for the affected date range. Regenerate to reflect current records.
- **Photos:** JPEG, PNG, and WebP uploads and previews; max 5 MB / 25 megapixels. Images are decoded, oriented, resized, and saved as local JPEGs without camera metadata. Deleting or replacing an attachment cleans up the old file. **Photo contents are not analyzed.**
- **Export:** download JSON with originals, metadata, chapter memberships, and local photo filenames. Images are not embedded; import is not implemented.

## Optional cloud AI

Copy `.env.example` to `.env` and configure either provider (or both). No key is needed for Demo Mode.

For **OpenAI**, keep using the existing settings:

```dotenv
OMOIDE_API_KEY=<your OpenAI key>
OMOIDE_MODEL=gpt-4o-mini
```

For **Google Gemini**, get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) and set:

```dotenv
GEMINI_API_KEY=<your Gemini API key>
OMOIDE_GEMINI_MODEL=gemini-3.8-flash
```

Restart Streamlit after changing `.env`. `OMOIDE_GEMINI_MODEL` is optional; it defaults to `gemini-3.8-flash`. Set it to another Gemini model that supports structured output if required by your account or current model availability. Gemini uses Google's [OpenAI-compatible API](https://ai.google.dev/gemini-api/docs/openai), so no additional SDK or dependency installation is needed.

Keep `.env` out of Git. In Codex cloud, enter credentials securely in environment settings:

| Provider | API key variable | Optional model variable | Required HTTPS destination |
| --- | --- | --- | --- |
| OpenAI | `OMOIDE_API_KEY` | `OMOIDE_MODEL` | `api.openai.com` |
| Google Gemini | `GEMINI_API_KEY` | `OMOIDE_GEMINI_MODEL` | `generativelanguage.googleapis.com` |

Never put a key in source code, chat, or setup scripts. Configure only the key for the provider you want to use; an OpenAI key cannot authenticate Gemini, or vice versa.

In **Processing & privacy**, select **Cloud AI**, choose **OpenAI** or **Google Gemini** under **AI provider**, then check the consent box naming that provider. Only a submitted extraction or story-generation action sends data to the selected provider: extraction uses the original text and supplied location; stories use the selected entries' original text, IDs, dates, and locations. Browsing and sample loading do not send journal records. Photographs are never transmitted. Switching providers or returning to Demo Mode clears consent and requires a fresh opt-in. A failed request falls back to offline processing; it does not send your records to the other cloud provider.

Both adapters request structured JSON schema output, validate it with Pydantic, and reject source IDs outside the selected records. They use a 25-second SDK timeout and one retry. Missing consent or the selected provider's credentials keeps processing offline; invalid JSON, refusal, timeout, or API failure produces a labeled Demo fallback with a visible notice. Cloud narratives are limited to 100 records per request; larger selections fall back to Demo Mode. Existing results keep the provider label used when they were created, including after you switch providers.

**Live OpenAI and Gemini requests have not been tested:** this environment has no API keys. Tests exercise the Gemini SDK request URL, authentication and structured payload with an in-process HTTP transport, plus metadata/recap/chapter integration, malformed output, API errors, timeout, invalid citations, and consent reset when changing providers. These tests do not establish real account access or model availability. Citations establish which records a result references; they cannot prove every model-generated sentence is factually correct. Review generated text and correct metadata as needed.

## Storage and privacy

By default, the database is `data/omoide.sqlite3` and photos are in `data/media/`. Set `OMOIDE_DATA_DIR` to use another directory; relative values resolve against the project root. `.env`, `.venv`, generated data, and caches are ignored by Git. Directories use private filesystem permissions on Linux, and database/media files use owner-only permissions.

This MVP has **no accounts, authentication, encryption at rest, or multi-user isolation**. Use it on a trusted private machine. Keep its loopback binding; do not expose the server as a public journal service. Back up the data directory while the app is stopped. Deletion removes current records and media, and clears affected stories; it does not erase previously downloaded exports or filesystem backups.

## Test

```bash
python -m pytest -q
python -m pip check
```

The suite covers persistence after reopening, CRUD, foreign keys, story invalidation, occurrence-date statistics and calendar boundaries, validated metadata, cloud error fallback and consent, conservative grouping, many-to-many memberships, citations, photo cleanup, repeatable sample loading, and the Streamlit capture → recap → chapter → original → edit → delete flow.

See [VALIDATION.md](docs/VALIDATION.md) for executed checks and [DEMO.md](docs/DEMO.md) for the three-minute presentation script.

## Project map

| File | Responsibility |
| --- | --- |
| `app.py` | Streamlit navigation, journal forms, cards, timelines, consent |
| `config.py` | `.env` loading and private data directory |
| `database.py` | SQLite schema, queries, foreign keys, story invalidation |
| `models.py` | Validated original-input and structured-output contracts |
| `ai_service.py` | Provider interface, offline rules, OpenAI/Gemini adapters, prompts |
| `memory_service.py` | Memory lifecycle and photograph storage |
| `recap_service.py` | Calendar periods, database-derived statistics, recaps |
| `chapter_service.py` | Conservative suggestions and chapter narratives |
| `demo_data.py` | Repeatable fictional dataset |
| `tests/` | Business logic and Streamlit interaction tests |

`requirements.txt` pins direct dependencies; `requirements.lock` pins transitive dependencies with artifact hashes, resolved for Python 3.11 compatibility. Refresh intentionally with `uv pip compile requirements.txt --python-version 3.11 --generate-hashes --output-file requirements.lock`, then reinstall and retest. The cloud setup uses the lockfile without rewriting it.

## Scope and next steps

All P0 flows are implemented. P1 includes photos, monthly/yearly recaps, metadata editing, empty/error states, and basic JSON export.

Demo processing is deliberately simple: it recognizes a small English/Traditional Chinese topic vocabulary and explicit milestone words, leaves people unknown, and cannot infer that an unnamed later achievement continues an earlier hobby. Trip suggestions use the named location; separate trips to the same location can appear together. Membership confirmation and editing provide correction. The interface is primarily English and supports Chinese journal text.

Future work: authenticate and encrypt before shared hosting; evaluate better grounding and topic continuity; add data import; test a local inference provider, image understanding, and transcription. **ASUS UGen Intel Arc Pro B70 32GB integration is planned for Stage II and has not been verified.** This prototype does not perform GPU inference, video understanding, or psychological assessment.
