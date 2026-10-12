# Starting Omoide in a cloud task

Each cloud task already has an isolated environment. Use the existing checkout at `/workspace/omoide`; do not create a Git worktree unless the user explicitly requests one.

The snapshot retains source files, `.venv`, and local data, but running processes must be restarted. Preserve the user's `.env` and data directory. Default to offline Demo Mode. Do not send journal records to OpenAI during startup validation; cloud processing requires the user's explicit opt-in in the app. Photos are never sent or analyzed.

1. Work in `/workspace/omoide`. Check whether the existing Omoide Streamlit process is already running before starting another instance. Use local requests for checks; do not create a public preview or a user-facing localhost link.
2. If dependencies are missing or have intentionally changed, run `bash scripts/setup.sh`. It installs the hash-pinned lockfile, checks dependencies, and runs the tests without changing journal data. No API key is required.
3. Launch the service from the project root and keep the exec session running:

   ```bash
   cd /workspace/omoide
   .venv/bin/python -m streamlit run app.py --server.port 8501
   ```

   The repository configuration binds to `127.0.0.1`, preserves XSRF protection, and disables usage telemetry. Do not bind to a public interface for this unauthenticated prototype.

4. Check startup logs and the local health endpoint using Python:

   ```bash
   .venv/bin/python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5).read() == b'ok'"
   ```

5. Verify the meaningful UI flow, using its temporary test database:

   ```bash
   .venv/bin/python -m pytest -q tests/test_app.py
   ```

   This exercises capture → analysis → saved original → weekly recap → chapter timeline → original → edit → delete in Demo Mode. A healthy port alone does not verify functionality. Use a browser for additional visual checks when available.

6. The sample dataset is optional; use **Load Synthetic Demo Data** in the UI or `.venv/bin/python demo_data.py` when the user wants fictional sample records. The loader is idempotent and always offline. Do not erase user records or reset their database to prepare a demo.

The optional credential is `OMOIDE_API_KEY`, supplied securely through environment settings. The OpenAI destination is `api.openai.com`; the default model is `gpt-4o-mini` and can be changed with `OMOIDE_MODEL`. Missing credentials leave Demo Mode fully functional. Actual cloud inference and ASUS Intel GPU compatibility require separate validation.
