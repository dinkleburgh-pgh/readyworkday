# Project Guidelines

## Architecture
- Entry point: `app_unloadv1.7.py` (Streamlit monolith). Treat `backups/` as read-only reference.
- State is JSON-file based (`.truck_state.json`, `truck_fleet.json`, `auth_users.json`, etc.). Keep schema changes backward-compatible.
- UI relies on `st.session_state` and Streamlit reruns — avoid changes that reset session keys unexpectedly.

## Logic Storage & Runtime Flow
- Core runtime logic lives in `app_unloadv1.7.py` and is page-routed by `st.session_state.active_screen`.
- Durable app state is loaded/saved through `load_state()` and `save_state()`. Most UI actions should persist via `_mark_and_save()` after state mutations.
- Derived operational counts should come from shared helpers (`current_load_day_completion()`, `_current_load_progress_snapshot()`, `_current_load_day_remaining_breakdown()`) instead of ad-hoc per-page math.
- Route-level logic and truck-level logic are different: when reporting "totals", prefer route-level counting to avoid double-counting when spare/OOS/swap coverage is active.
- Route assignment overlays are applied via `_active_oos_spare_assignments()` and `_active_route_swap_assignments()`; update these pathways when changing coverage behavior.
- Screen rendering is state-machine style: each button mutates session state, optionally calls `_mark_and_save()`, then relies on Streamlit rerun to re-evaluate the active page.

### Change Safety Rules
- Do not create parallel sources of truth for progress counts; extend shared helpers and consume those outputs across pages.
- Keep JSON schema changes backward-compatible and provide defaults/migration-safe reads.
- Prefer targeted helper updates over broad refactors in page blocks.
- When modifying a cross-page helper, verify impact on at least `LOAD`, `UNLOAD`, and `FLEET` views.

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
