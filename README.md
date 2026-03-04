# ReadyWorkday (TruckApp)

ReadyWorkday is a Streamlit app for managing daily truck operations: unload workflow, load tracking, shortages, fleet status, and supervisor actions.

Current release: **v1.2.1**

## Recent updates (v1.2.1)

- Fleet page now reopens in a clean "Select Truck" state when you enter Fleet from navigation.
- Fleet status changes now refresh sidebar badge counts immediately after apply.
- Fleet truck picker now flashes trucks that are currently **In Progress**.
- OOS status page now separates trucks under **Spare** and **Out Of Service** headers.
- Shorts button-mode entry now uses compact rows with per-row delete (✕).
- Truck button rendering improvements: centered **New** button label and larger fit for 3-digit truck numbers.

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
streamlit run app_unloadv1.2.py
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
- The script runs `app_unloadv1.2.py`.

## Basic daily flow

1. **Ready Workday**: set run date, load day(s), and warning/settings.
2. **Unload**: select dirty trucks, assign batch/wearers, mark trucks unloaded.
3. **Load**: start next truck from unloaded list.
4. **In Progress**: monitor timer, record shortages.
5. **Save & Done**: finalize shortages and mark truck loaded.
6. **Fleet Management**: update status, shop actions, notes, and add/remove trucks.

## Key project files

- Main app (latest): `app_unloadv1.2.py`
- Legacy app entry: `app_unloadv1.1.py`
- Fleet config: `truck_fleet.json`
- Load duration history: `load_durations.json`
- State snapshots: `state_history/`
- Release notes: `CHANGELOG.md`
- Backup snapshots: `backups/`
