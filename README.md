# ReadyWorkday (TruckApp)

ReadyWorkday is a Streamlit app for managing daily truck operations: unload workflow, load tracking, shortages, fleet status, and supervisor actions.

Current release: **v1.6.0**

## Recent updates (v1.6.0)

- Promoted `app_unloadv1.6.py` as the primary app entry file for this release.
- Route badges were stabilized and expanded: swap/spare/OOS load-on badges now render consistently across views, with badge chips layered above OOS indicators.
- Pace calculations now show **time impact** (instead of truck count deltas), always account for a 30-minute break (7h30 effective shift), and live-update like the time card.
- Added **Last Truck (#)** pace tile showing added/saved time with color-coded +/- indicators.
- `STATUS_LOADED` statistics were redesigned into richer visual metric tiles, including route/source and pace impact context.
- Fleet swap flow now supports one-way route assignment and a clear-assignment action.
- Login popup behavior on navigation/back was reduced with improved silent re-auth handling.
- Default repo state/fleet baseline was aligned to the approved current configuration (`.truck_state.json`, `truck_fleet.json`, `off_schedule_defaults.json`).

## Prior updates (v1.5.0)

- Added user-management success confirmation dialogs for **Create user** and **Save user changes**.
- User picker labels now show role before enabled state (for example: `username (Loader • Enabled)`).
- Management (Supervisor) tab was simplified by removing the top statistics strip.
- In Progress + Load layouts now stack properly on mobile to prevent clipped side-by-side columns.
- State-history archives now include load-day metadata (`history_load_day_num`, `history_load_day_label`, and run/ship date keys).

## Prior updates (v1.4.0)

- In Progress page now uses a centered desktop layout (aligned with other status pages) while preserving a prominent timer card for display screens.
- Daily Notes card on In Progress now renders note lines as bullets with larger, bolder text.
- Added In Progress keep-awake behavior (Wake Lock API first, media-session fallback) to reduce display sleep during active loading.
- STATUS_SHOP workflow simplified: page shows current shop trucks only, with concise **Send** and **Return** controls and in-page return mode.
- Added Load-page **Load Progress** dropdown under Off Day with live totals and remaining counts.
- Remaining list in Load Progress is now on-demand via **Show remaining / Hide remaining** toggle.
- Improved mobile numeric keypad reliability for unload wearers entry with stronger focus/retry behavior.

## Prior updates (v1.3.1)

- Fresh-slate runtime data reset committed: no load duration history and no active OOS/spare assignments in the default state files.
- In Progress elapsed timer now starts flashing at **20:00**.
- OOS workflow safety: once an OOS route is assigned a spare, that OOS route is removed from Unloaded to prevent double loading.

## Earlier updates (v1.3.0)

- In Progress layout refinements: centered **Current Truck** + timer, tighter spacing, and sticky **Daily Notes** with internal scroll.
- Status color controls in App Settings: configurable status bubble colors plus a one-click **Reset to defaults color scheme** action.
- Sidebar live status now uses a colored dot indicator only (no colored sidebar button backgrounds).
- Truck status color behavior updated so bubble colors control matching truck buttons, with text forced black except OOS/Spare white-on-grey.
- OOS page improvements: **Add** truck action moved into the OOS grid flow and retained section split for **Spare** / **Out Of Service**.
- Shorts quality-of-life updates: delete now requires confirm/cancel, Recents label centering on In Progress, and simpler warning text (**Load time exceeded**).

## What the app does

- Tracks truck status across: **Dirty**, **Unloaded**, **In Progress**, **Loaded**, **Shop**, **Out Of Service**, **Spare**, and **Special**.
- Supports unload batching with wearer totals and batch capacity checks.
- Tracks live load timers with warning thresholds and duration history.
- Captures shortages with a button-driven flow or manual sheet entry.
- Includes Fleet Management tools (notes, status changes, shop actions, add/remove trucks).
- Generates operational PDFs (load/shortages, batch cards, end-of-day summary).
- Persists state locally in JSON files.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`:
	- `streamlit`
	- `pandas`
	- `reportlab`

## Quick start (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app_unloadv1.6.py
```

Then open: `http://localhost:8501`

## Quick start (Linux / TrueNAS)

```bash
chmod +x run_streamlit.sh
./run_streamlit.sh
```

Notes:
- `run_streamlit.sh` starts Streamlit in the background.
- Script log output goes to `.data/streamlit.log`.
- The script runs `app_unloadv1.6.py` by default.

## Containerized run (Docker)

This workspace now includes `Dockerfile`, `docker-compose.yml`, `docker-compose.portainer.yml`, and `.dockerignore`.

### Start (recommended)

```bash
docker compose up --build
```

Open: `http://localhost:8501`

### Run in background

```bash
docker compose up --build -d
```

### Use a different app entry file

PowerShell:

```powershell
$env:APP_FILE="app_unloadv1.6.py"
docker compose up --build
```

Bash:

```bash
APP_FILE=app_unloadv1.6.py docker compose up --build
```

## Deploy with Portainer

Use a **Git-based Stack** in Portainer.

### Option A: Build in Portainer (requires working compose build permissions)

1. Push this workspace to GitHub/GitLab.
2. In Portainer, open **Stacks → Add stack → Repository**.
3. Set repository URL/branch and compose path to `docker-compose.yml`.
4. Set env var `APP_FILE=app_unloadv1.6.py`.
5. Deploy.

### Option B: No-build Portainer stack (recommended if you get `mkdir /.docker: permission denied`)

1. Ensure image `ghcr.io/dinkleburgh-pgh/readyworkday:latest` exists (published from GitHub Actions).
2. In Portainer, use the same repository/branch but set compose path to `docker-compose.portainer.yml`.
3. Set env vars:
	- `IMAGE_NAME=ghcr.io/dinkleburgh-pgh/readyworkday:latest`
	- `APP_FILE=app_unloadv1.6.py`
4. Deploy and open `http://<docker-host>:8501`.

Notes:
- If GHCR package visibility is private, add registry credentials in Portainer before deploy.
- The no-build compose avoids Portainer compose-build permissions entirely.

### Stop

```bash
docker compose down
```

## Basic daily flow

1. **Ready Workday**: set run date, load day(s), and warning/settings.
2. **Unload**: select dirty trucks, assign batch/wearers, mark trucks unloaded.
3. **Load**: start next truck from unloaded list.
4. **In Progress**: monitor timer, record shortages.
5. **Save & Done**: finalize shortages and mark truck loaded.
6. **Fleet Management**: update status, shop actions, notes, and add/remove trucks.

## Key project files

- Main app (latest): `app_unloadv1.6.py`
- Previous release entry file: `app_unloadv1.5.py`
- Previous release snapshot: `backups/v1.4/app_unloadv1.4.py`
- Legacy snapshots: `backups/v1.3/`, `backups/v1.2/`, `backups/v1.1/`, `backups/v1.0/`
- Fleet config: `truck_fleet.json`
- Load duration history: `load_durations.json`
- State snapshots: `state_history/`
- Release notes: `CHANGELOG.md`
- Backup snapshots: `backups/`
