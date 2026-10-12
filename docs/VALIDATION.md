# Executed validation

Environment: Codex cloud, Linux, Python 3.12.14, Streamlit 1.50.0. A separate clean Python 3.11.17 environment was also tested. All records used in checks were fictional. No live AI credential was available.

| Check | Outcome |
| --- | --- |
| `python -m pytest -q` in the project virtual environment | **25 passed**, no failed or skipped tests |
| `python -m pip check` | No broken requirements |
| `bash scripts/setup.sh` | Successful repeatable install, dependency check, and 25 passing tests |
| Fresh Python 3.11 virtual environment installed with `--require-hashes -r requirements.lock` | Successful; dependency check and all 25 tests passed |
| Streamlit process and internal health request | Started and restarted successfully; health response `ok` |
| Chromium desktop: create Chinese memory → save → inspect metadata | Passed; original shown separately, rule-based tags and milestone visible |
| Chromium desktop: generate weekly recap → source button → original | Passed |
| Chromium desktop: confirm Basketball chapter → generate story → timeline → original | Passed |
| Chromium desktop: edit title → save → confirm deletion → delete | Passed; test record removed |
| Chromium mobile: 390-pixel viewport and capture form | Accessible; document width 390 pixels, no horizontal overflow, no browser page errors |
| Synthetic dataset | 36 records; repeat loading inserted 0 duplicates; September 26, October 10, October 5–11 week 6 |
| SQLite foreign-key check after browser deletion | No violations; remaining chapter has six fictional Basketball members |

The Streamlit AppTest suite also exercises weekly/monthly/yearly recap screens, sample loading twice, empty periods, missing cloud credentials, metadata correction, source navigation, and editing/deleting through the UI.

Photo tests validate decoded uploads, camera-metadata removal, replacement and deletion cleanup, and invalid-file rejection. Cloud adapter tests use mocked responses for strict structured output, malformed JSON, timeout fallback, and the consent guard. Date boundary tests include a week crossing New Year and a leap-year February.

The current local journal contains exactly 36 Synthetic Demo Data records and a six-entry Basketball chapter from the browser walkthrough. The temporary browser-created test record was deleted. Its deletion cleared affected stories; the Basketball story was regenerated successfully after restarting the server, with source navigation checked again.

## Not verified

- Actual OpenAI inference, API account access, model availability, and model-generated factual accuracy.
- ASUS UGen Intel Arc Pro B70 compatibility, local LLM inference, or GPU performance.
- New cloud-task restoration or publication; saving a configuration draft does not publish it.
- Windows/macOS operation, authenticated shared hosting, accessibility conformance, or production load.

The current instance is functional in offline Demo Mode. Cloud inference is optional and requires a securely supplied key plus explicit in-app consent.
