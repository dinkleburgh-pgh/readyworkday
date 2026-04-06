# Project Guidelines

## Architecture
- Primary app is a Streamlit monolith in `app_unloadv1.7.py`. Treat this as the active entrypoint unless explicitly asked to target older backups.
- Persistent app data is JSON-file based (for example: `.truck_state.json`, `truck_fleet.json`, `auth_users.json`, `communications_chat.json`). Keep schema changes backward-compatible when possible.
- UI behavior relies on Streamlit reruns and `st.session_state`; avoid changes that reset session keys unexpectedly.
- Historical snapshots under `backups/` are reference-only unless the task explicitly targets them.

## Build And Run
- Create environment and install deps:
  - Windows PowerShell: `python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt`
- Run app locally: `streamlit run app_unloadv1.7.py`
- Docker run (preferred for parity): `docker compose up --build`
- No automated tests are currently defined in this repo. If adding logic-heavy changes, add focused tests where practical or provide manual verification steps.

## Conventions
- Keep changes minimal and targeted; this project has a large single-file app, so broad refactors are risky unless requested.
- Follow existing naming patterns (`load_*`, `save_*`, helper functions with leading underscore) and preserve current public behavior.
- Reuse existing constants/config patterns near the top of the app instead of introducing scattered literals.
- When updating release behavior, keep version metadata and release notes aligned (see `CHANGELOG.md` and version constants in `app_unloadv1.7.py`).

## Pitfalls
- Avoid introducing breaking changes to JSON persistence keys without migration logic.
- Keep cross-platform behavior in mind (Windows and Linux/TrueNAS paths/scripts are both used).
- For production/container changes, do not hardcode insecure auth cookie values; preserve environment-variable based configuration.

## Key References
- Project setup, run modes, and deployment notes: `README.md`
- Release history and behavior changes by version: `CHANGELOG.md`
