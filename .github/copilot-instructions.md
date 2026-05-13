# Project Guidelines

## Architecture
- Entry point: `app_unloadv1.7.py` (Streamlit monolith). Treat `backups/` as read-only reference.
- State is JSON-file based (`.truck_state.json`, `truck_fleet.json`, `auth_users.json`, etc.). Keep schema changes backward-compatible.
- UI relies on `st.session_state` and Streamlit reruns — avoid changes that reset session keys unexpectedly.

## Build & Run
```sh
# Local (Windows)
python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt
streamlit run app_unloadv1.7.py

# Docker (preferred for production parity)
docker compose up --build
```

## Conventions
- Keep changes minimal and targeted — broad refactors of the large single-file app are risky unless requested.
- Follow existing naming: `load_*` / `save_*` for persistence, `_helper` prefix for internal helpers.
- Reuse constants defined near the top (`BATCH_COUNT`, `AUTO_REFRESH`, warn thresholds) — don't scatter literals.
- When bumping a release: align version constants in `app_unloadv1.7.py` **and** `CHANGELOG.md`.

## Pitfalls
- Adding/renaming JSON keys requires migration logic or a backward-compatible default.
- Paths run on both Windows (dev) and Linux/TrueNAS (production) — keep them cross-platform.
- Auth cookie values must come from environment variables, not hardcoded strings.
- No automated tests exist — for logic-heavy changes, add focused unit tests or document manual verification steps.

## Live Verification
- The user will always share the live app browser page (localhost:8501).
- After any UI change, always do a live check using the browser tools — take a screenshot or read the page to confirm the result looks correct before declaring the task done.
- Do not rely on code review alone for UI/visual changes; always verify in the browser.

## Key References
- Deployment & run modes: [`README.md`](../README.md)
- Release history: [`CHANGELOG.md`](../CHANGELOG.md)
