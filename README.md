# ReadyWorkday (TruckApp)

ReadyWorkday is a Streamlit app for managing daily truck operations: unload workflow, load tracking, shortages, fleet status, and supervisor actions.

Current release: **v1.3.0**

## Recent updates (v1.3.0)

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
streamlit run app_unloadv1.3.py
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
- The script runs `app_unloadv1.3.py`.

## Containerized run (Docker)

This workspace now includes `Dockerfile`, `docker-compose.yml`, and `.dockerignore`.

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
$env:APP_FILE="app_unloadv1.3.py"
docker compose up --build
```

Bash:

```bash
APP_FILE=app_unloadv1.3.py docker compose up --build
```

## Deploy with Portainer

Recommended approach: deploy as a **Git-based Stack** so Portainer can access the full build context (`Dockerfile`, app files, and `requirements.txt`).

1. Push this workspace to GitHub/GitLab.
2. In Portainer, open **Stacks → Add stack → Repository**.
3. Set repository URL/branch and compose path to `docker-compose.yml`.
4. Set env var `APP_FILE=app_unloadv1.3.py` (or another app file if needed).
5. Deploy and open `http://<docker-host>:8501`.

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

- Main app (latest): `app_unloadv1.3.py`
- Previous app entry: `app_unloadv1.2.py`
- Legacy app entry: `app_unloadv1.1.py`
- Fleet config: `truck_fleet.json`
- Load duration history: `load_durations.json`
- State snapshots: `state_history/`
- Release notes: `CHANGELOG.md`
- Backup snapshots: `backups/`
