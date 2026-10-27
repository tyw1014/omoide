**[Watch the Omoide demo video on YouTube](https://youtu.be/UzQToVdO0W8)**

# Omoide（思い出）

**Tracing memories through everyday moments.**

在平凡瑣碎的日常裡，找出回憶的軌跡。

何気ない日々に、思い出の軌跡を

Omoide is a single-user life journal that connects everyday records into revisitable stories. Capture a moment, look back through a weekly recap, and follow a recurring interest across dates in a **Life Chapter**. Built for the 2026 ASUS UGen AI League Hackathon with Python, Streamlit, SQLite, and local photograph storage.

## Features

- **Capture:** create, view, edit, search, filter, and delete memories. Store the event date separately from the creation timestamp; optionally attach a photograph.
- **Organize:** generate summaries, tags, activity categories, explicit entities, and milestone flags. Originals stay separate from generated metadata, which you can correct or re-analyze.
- **Rewind:** generate weekly, monthly, and yearly recaps with source links. Record counts, topics, locations, sports counts, and milestones come from stored data rather than an LLM.
- **Life Chapters:** confirm suggestions based on specific interests or named trip locations, edit memberships, and view a chronological timeline and cited story. One memory can belong to several chapters.
- **Export:** download JSON containing original records, metadata, chapters, and local photo filenames. Photo files are not embedded; import is not implemented.

## Run locally

### 1. Install prerequisites and download the project

Install [Python](https://www.python.org/downloads/) **3.11 or newer** and [Git](https://git-scm.com/downloads). Python **3.12** is recommended. The project has been tested on Linux with Python 3.11 and 3.12; macOS, Windows, and newer Python versions have not been verified.

Open **Terminal** on Linux/macOS, or **PowerShell** / **Command Prompt** on Windows:

```text
git clone https://github.com/tyw1014/omoide.git
cd omoide
```

If you already have the project, skip both commands and open a terminal in its folder. Run the following commands from the directory containing `app.py` and `requirements.lock`.

### 2. Follow the instructions for your system

#### Linux (Bash)

Check that `python3 --version` reports 3.11 or newer, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m streamlit run app.py
```

On Ubuntu/Debian, if `venv` or `ensurepip` is missing, install the package matching your Python version, such as `sudo apt install python3.12-venv`, then create the environment using that interpreter.

#### macOS (Terminal, Zsh or Bash)

Check that `python3 --version` reports 3.11 or newer. If necessary, install a supported Python version using the link above. Then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m streamlit run app.py
```

#### Windows (PowerShell or Command Prompt)

Check that `py -3 --version` reports 3.11 or newer, then run in either shell:

```text
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If `py` is unavailable but `python --version` reports a supported version, replace the first command with `python -m venv .venv`. The remaining commands stay the same. Using the virtual environment's executable directly avoids activation and PowerShell execution-policy changes.

**For other `python` commands in this README, Windows users should substitute `.\.venv\Scripts\python.exe`.** Linux/macOS users should keep the virtual environment activated.

### 3. Open, stop, and restart the app

Open the local address printed by Streamlit in your browser. Keep the terminal open; press **Ctrl+C** there to stop the app. The repository configuration binds to the loopback interface and disables Streamlit usage telemetry.

For later launches, open a terminal in the project folder:

- **Linux/macOS:** run `source .venv/bin/activate`, then `python -m streamlit run app.py`.
- **Windows:** run `.\.venv\Scripts\python.exe -m streamlit run app.py`.

Reinstall dependencies when the dependency files change or you recreate the virtual environment.

## Try the demo

**No API key is required.** The default **Demo Mode** uses offline keyword rules for metadata and excerpts of original records for stories. Outputs are labeled `Demo · rule-based`; they are not live LLM inference.

1. Click **Load Synthetic Demo Data** on the empty home screen, or run `python demo_data.py` from the project folder.
2. Explore 36 fictional memories spanning September 1–October 11, 2026. Loading again preserves existing samples without adding duplicates; deleted samples can be loaded again.
3. Open **Rewind**, select **Weekly** and October 10, 2026, then generate a recap. The original sample dataset has six records in the October 5–11 week.
4. Open **Life chapters**, confirm a Basketball or Guitar suggestion, and generate its story. Use a source button or **Open original** to inspect the supporting record.

Samples are marked **Synthetic Demo Data** and always processed offline, even when a cloud provider is selected. See [the three-minute demo script](docs/DEMO.md) for a presentation walkthrough.

## Optional cloud AI

Choose **Google Gemini** or **OpenAI** for live structured extraction and story generation. Both use the existing OpenAI Python SDK; Gemini requests use Google's [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai).

### Configure a provider

If you do not already have `.env`, copy `.env.example` to `.env` in the project folder:

- **Linux/macOS:** `cp .env.example .env`
- **Windows:** `copy .env.example .env`

If `.env` already exists, edit it without overwriting your existing settings. Add the key for your chosen provider; you do not need both keys.

**Google Gemini** — obtain a key from [Google AI Studio](https://aistudio.google.com/apikey):

```dotenv
GEMINI_API_KEY=your_gemini_api_key
OMOIDE_GEMINI_MODEL=gemini-3.5-flash-lite
```

**OpenAI** — obtain a key from [OpenAI API settings](https://platform.openai.com/api-keys):

```dotenv
OMOIDE_API_KEY=your_openai_api_key
OMOIDE_MODEL=gpt-4o-mini
```

The model variables are optional and default to the values shown. Model access depends on your provider account. Use a model that supports structured JSON output. Restart Streamlit after changing `.env`; existing process environment variables take precedence over `.env` values.

In a cloud environment, enter keys securely in environment settings instead of committing them:

| Provider | Key variable | Model variable | Required HTTPS destination |
| --- | --- | --- | --- |
| Google Gemini | `GEMINI_API_KEY` | `OMOIDE_GEMINI_MODEL` | `generativelanguage.googleapis.com` |
| OpenAI | `OMOIDE_API_KEY` | `OMOIDE_MODEL` | `api.openai.com` |

### Select the provider and opt in

In **Processing & privacy**, select **Cloud AI**, choose the **AI provider**, and check the consent box naming that provider. Missing credentials or consent keeps processing offline. Switching providers or returning to Demo Mode clears consent.

Extraction sends the original text and supplied location. Recaps and chapter stories send the selected records' original text, IDs, dates, and locations. Browsing and sample loading send no journal content to AI providers. **Photos are stored locally and never sent to AI providers or analyzed.**

Both adapters request structured JSON, validate responses with Pydantic, and reject narrative source IDs outside the selected records. The shared `CloudProvider` uses an SDK timeout of **120.0 seconds** and **one retry**. The total wait can exceed 120 seconds; this is not an overall operation deadline.

Malformed output, refusal, timeout, or an API error produces a labeled offline fallback with a visible notice. The app does not retry with the other cloud provider. Cloud narratives are limited to 100 selected records; larger selections fall back to Demo Mode. Stored results retain the provider label used when they were created.

## Storage and privacy

The default database is `data/omoide.sqlite3`; photographs are in `data/media/`. Set `OMOIDE_DATA_DIR` to use another directory. Relative paths resolve against the project root.

- `.env`, `.venv`, the data directory, and caches are ignored by Git. Never commit real API keys or private journal data.
- Photos accept JPEG, PNG, or WebP up to 5 MB / 25 megapixels. They are decoded, oriented, resized, and saved as JPEGs without camera metadata.
- Deleting or replacing a photograph removes the old local file. Deleting a memory removes its chapter associations and clears affected stories. Editing records or memberships also invalidates affected stories; regenerate them to use current records.
- Counts describe what was recorded, not everything the user did. Citations identify supporting records but do not guarantee every generated sentence is correct.
- This is a **single-user local prototype without authentication, multi-user isolation, or encryption at rest**. Use it on a trusted private machine and keep the loopback binding. Do not expose it as a public journal service.
- Back up the data directory while the app is stopped. Deletion does not remove previously downloaded exports or backups.

## Testing and validation

From the project folder, using the virtual environment:

```bash
python -m pytest -q
python -m pip check
```

The suite covers persistence, CRUD, foreign keys, story invalidation, calendar statistics, metadata validation, chapter grouping, citations, photo cleanup, repeatable samples, provider consent, and the Streamlit capture → recap → chapter → original → edit → delete flow. Gemini request construction is tested with the real SDK and an in-process HTTP transport; no live key is needed.

**38 automated tests pass on the tested Linux/Python 3.12 environment.** Earlier validation also exercised the original MVP on Python 3.11 and the core flow in desktop/mobile Chromium. See [the validation report](docs/VALIDATION.md) for details.

Live OpenAI/Gemini inference, account access, current model availability, macOS/Windows execution, and production deployment have **not** been verified. Automated cloud-provider checks use mocked responses.

## Project structure

| File | Responsibility |
| --- | --- |
| `app.py` | Streamlit navigation, forms, journal cards, timelines, and consent |
| `config.py` | `.env` loading and private local data directory |
| `database.py` | SQLite schema, queries, foreign keys, and story invalidation |
| `models.py` | Validated input, metadata, and narrative contracts |
| `ai_service.py` | Demo rules, OpenAI/Gemini adapters, validation, and prompts |
| `memory_service.py` | Memory lifecycle and local photograph storage |
| `recap_service.py` | Calendar periods, deterministic statistics, and recaps |
| `chapter_service.py` | Conservative chapter suggestions and narratives |
| `demo_data.py` | Repeatable fictional dataset |
| `tests/` | Business logic, provider, and Streamlit tests |

`requirements.txt` pins direct dependencies; `requirements.lock` pins transitive dependencies with artifact hashes for Python 3.11 compatibility. Refresh intentionally with `uv pip compile requirements.txt --python-version 3.11 --generate-hashes --output-file requirements.lock`, then reinstall and retest. Cloud startup instructions are in [CLOUD_START.md](docs/CLOUD_START.md).

## Limitations and future development

Demo rules recognize a small English/Traditional Chinese vocabulary and explicit milestone words. They leave unknown people empty and cannot reliably infer continuity from an unnamed achievement. Trip suggestions use a named location, so separate trips to the same place may appear together. Review suggestions and correct chapter membership manually. The interface is primarily English and supports Chinese and Japanese text.

Future work includes authenticated hosting, encryption, data import, improved topic continuity and grounding, and a local inference provider. **ASUS UGen Intel Arc Pro B70 32GB integration is planned for Stage II and has not been verified.** The MVP does not perform GPU inference, video understanding, speech transcription, or psychological assessment.
