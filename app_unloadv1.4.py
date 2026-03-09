import streamlit as st # type: ignore
import logging
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component
from datetime import date, timedelta, datetime
import time
from io import BytesIO
import json
import html
import os
# Load quick-select amounts from JSON
def load_quick_amounts():
    try:
        with open("shortage_quick_amounts.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}
QUICK_AMOUNTS_MAP = load_quick_amounts()
# App metadata (do not edit)
_APP_VERSION = "1.4.0"
_APP_DATE = "20260309"  

# Setup logging
logging.basicConfig(
    filename="truckapp.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
import streamlit.components.v1 as components
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# PDF (ReportLab)
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.pdfgen import canvas # type: ignore

st.set_page_config(page_title="Load Management", layout="centered")

# ==========================================================
# CONFIG
# ==========================================================
FLEET_MIN = 50
FLEET_MAX = 96
FLEET = list(range(FLEET_MIN, FLEET_MAX + 1))
PERSISTENT_SPARE_TRUCKS = set(range(10, 18))

BATCH_COUNT = 6
BATCH_CAP = 400  # cannot go over

DEFAULT_WARN_MIN = 15  # default 15 minutes
ROLLOVER_PROMPT_HOUR = 6
ROLLOVER_SNOOZE_SECONDS = 60 * 60

DEFAULT_SHORT_ITEMS = [
    "None",
    "Towels",
    "Toilet Paper",
    "Paper Towels",
    "Soap",
    "Trash Bags",
    "Aprons",
    "Mats",
    "Other",
]

SHORTS_MODE_EXCEL = "Excel Sheet (current)"
SHORTS_MODE_BUTTONS = "Button Selection"
SHORTS_MODE_DISABLE = "Disable (manual input)"
SHORTS_MODE_OPTIONS = [SHORTS_MODE_BUTTONS, SHORTS_MODE_EXCEL, SHORTS_MODE_DISABLE]

SHORTS_BUTTON_MAP = {
    "3x10": ["Black", "Onyx", "Copper", "Indigo", "Blue", "Brown"],
    "3x5": ["Black", "Onyx", "Copper", "Indigo", "Blue", "Brown"],
    "4x6": ["Logo", "Black", "Onyx", "Copper", "Indigo", "Blue", "Brown", "2x3"],
    "Paper": [
        "C-PULL",
        "DRC (AIRLAID)",
        "BROWN HW",
        "SIG HW",
        "SIG Z-FOLD",
        "SIG DUAL TP",
        "JRT",
        "B&V TP",
        "B&V Z-FOLD",
    ],
    "Bulk": {
        "Dust Mops": ["WET MOP", "24\"", "36\"", "46\"", "60\"", "Fender Covers"],
        "Aprons": ["White", "Black", "Red", "Green", "Blue", "Denim"],
        "Towels": [
            "Grid/Terry",
            "Glass",
            "Regular",
            "Premium",
            "Small Ink",
            "Large Ink",
            "Napkins",
            "Red Shop",
            "White Shop",
        ],
    },
}

# Badge colors
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#f59e0b"
BLUE = "#2563eb"
PURPLE = "#a855f7"

DEFAULT_STATUS_BADGE_COLORS = {
    "dirty": RED,
    "shop": "#7400ff",
    "in_progress": ORANGE,
    "unloaded": GREEN,
    "loaded": BLUE,
    "off": "#6b7280",
    "oos_spare": "#6b7280",
}


def _normalize_hex_color(value, fallback: str) -> str:
    try:
        raw = str(value).strip()
    except Exception:
        return fallback
    if not raw:
        return fallback
    if raw.startswith("#") and len(raw) == 4:
        raw = f"#{raw[1]*2}{raw[2]*2}{raw[3]*2}"
    if not (raw.startswith("#") and len(raw) == 7):
        return fallback
    allowed = "0123456789abcdefABCDEF"
    if any(ch not in allowed for ch in raw[1:]):
        return fallback
    return raw.lower()


def _get_status_badge_colors() -> dict[str, str]:
    raw = st.session_state.get("status_badge_colors")
    raw_map = raw if isinstance(raw, dict) else {}
    out = {}
    for key, default_color in DEFAULT_STATUS_BADGE_COLORS.items():
        out[key] = _normalize_hex_color(raw_map.get(key), default_color)
    return out


STATUS_BADGE_PICKER_KEYS = {
    "dirty": "mgmt_badge_color_dirty",
    "shop": "mgmt_badge_color_shop",
    "in_progress": "mgmt_badge_color_in_progress",
    "unloaded": "mgmt_badge_color_unloaded",
    "loaded": "mgmt_badge_color_loaded",
    "off": "mgmt_badge_color_off",
    "oos_spare": "mgmt_badge_color_oos_spare",
}


def _set_status_badge_picker_values(color_map: dict[str, str]):
    for color_key, widget_key in STATUS_BADGE_PICKER_KEYS.items():
        st.session_state[widget_key] = _normalize_hex_color(
            color_map.get(color_key), DEFAULT_STATUS_BADGE_COLORS[color_key]
        )

# ==========================================================
# STATE
# ==========================================================
STATE_FILE = ".truck_state.json"
FLEET_FILE = "truck_fleet.json"
DURATIONS_FILE = "load_durations.json"
OFF_SCHEDULE_DEFAULTS_FILE = "off_schedule_defaults.json"
HISTORY_DIR = "state_history"


def _fleet_path() -> str:
    return os.path.join(os.getcwd(), FLEET_FILE)


def load_fleet_file() -> list[int] | None:
    path = _fleet_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "fleet" in data:
            data = data["fleet"]
        if isinstance(data, list):
            return sorted({int(x) for x in data})
    except Exception:
        return None
    return None


def save_fleet_file(fleet: list[int]):
    path = _fleet_path()
    try:
        payload = {"fleet": sorted({int(x) for x in fleet})}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _state_path() -> str:
    return os.path.join(os.getcwd(), STATE_FILE)


def _history_dir_path() -> str:
    return os.path.join(os.getcwd(), HISTORY_DIR)


def _history_state_path(run_date_key: str) -> str:
    return os.path.join(_history_dir_path(), f"state_{run_date_key}.json")


def _durations_path() -> str:
    return os.path.join(os.getcwd(), DURATIONS_FILE)


def _off_schedule_defaults_path() -> str:
    return os.path.join(os.getcwd(), OFF_SCHEDULE_DEFAULTS_FILE)


def _normalize_off_schedule(raw) -> dict[int, list[int]]:
    normalized: dict[int, list[int]] = {i: [] for i in range(1, 6)}
    if not isinstance(raw, dict):
        return normalized

    for day_raw, trucks_raw in raw.items():
        try:
            day_num = int(day_raw)
        except Exception:
            continue
        if day_num < 1 or day_num > 5:
            continue

        if not isinstance(trucks_raw, (list, tuple, set)):
            continue

        trucks: list[int] = []
        for truck_raw in trucks_raw:
            try:
                trucks.append(int(truck_raw))
            except Exception:
                continue
        normalized[day_num] = sorted(set(trucks))

    return normalized


def _off_schedule_has_entries(schedule: dict[int, list[int]] | None) -> bool:
    if not isinstance(schedule, dict):
        return False
    for trucks in schedule.values():
        if isinstance(trucks, list) and len(trucks) > 0:
            return True
    return False


def load_off_schedule_defaults() -> dict[int, list[int]]:
    path = _off_schedule_defaults_path()
    if not os.path.exists(path):
        return {i: [] for i in range(1, 6)}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_off_schedule(data)
    except Exception:
        return {i: [] for i in range(1, 6)}


def save_off_schedule_defaults(schedule):
    path = _off_schedule_defaults_path()
    normalized = _normalize_off_schedule(schedule or {})
    payload = {str(day): list(trucks) for day, trucks in normalized.items()}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_duration_history() -> list[dict]:
    path = _durations_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def append_load_duration(truck: int, seconds: int):
    path = _durations_path()
    record = {
        "ts": time.time(),
        "run_date": st.session_state.run_date.isoformat() if st.session_state.get("run_date") else None,
        "truck": int(truck),
        "seconds": int(seconds),
    }
    try:
        data = load_duration_history()
        data.append(record)
        data = data[-2000:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_state() -> dict:
    path = _state_path()
    if not os.path.exists(path):
        logging.warning(f"State file not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logging.info(f"Loaded state from {path}")
    except Exception as e:
        logging.error(f"Failed to load state from {path}: {e}")
        return {}

    out = {}
    for k, v in data.items():
        if k in {
            "cleaned_set",
            "inprog_set",
            "loaded_set",
            "shop_set",
            "off_set",
            "spare_set",
            "special_set",
            "used_spares_today",
            "spares_needing_return",
        }:
            out[k] = set(map(int, v)) if v else set()
        elif k == "run_date":
            out[k] = date.fromisoformat(v) if v else None
        elif k == "ship_dates":
            out[k] = [date.fromisoformat(s) for s in v] if v else []
        elif k in {"wearers", "shop_notes", "shop_spares", "off_notes", "oos_spare_assignments", "sup_notes_global", "sup_notes_daily", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule", "shop_prev_status", "shorts_button_state"}:
            if isinstance(v, dict):
                new = {}
                for kk, vv in v.items():
                    try:
                        ik = int(kk)
                    except Exception:
                        ik = kk
                    new[ik] = vv
                out[k] = new
            else:
                out[k] = v
        elif k == "daily_notes":
            out[k] = v if v is not None else ""
        elif k == "last_setup_date":
            out[k] = date.fromisoformat(v) if v else None
        else:
            out[k] = v
    return out


def _run_date_key(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _current_run_date_key() -> str | None:
    return st.session_state.get("run_date_key") or _run_date_key(st.session_state.get("run_date"))


def _serialize_state() -> dict:
    data = {}
    keys = list(defaults.keys())
    for k in keys:
        v = st.session_state.get(k, defaults.get(k))
        if k in {
            "cleaned_set",
            "inprog_set",
            "loaded_set",
            "shop_set",
            "off_set",
            "spare_set",
            "special_set",
            "used_spares_today",
            "spares_needing_return",
        }:
            data[k] = sorted(list(v))
        elif k == "run_date":
            data[k] = v.isoformat() if v else None
        elif k == "last_setup_date":
            data[k] = v.isoformat() if v else None
        elif k == "ship_dates":
            data[k] = [d.isoformat() for d in v]
        elif k in {"wearers", "shop_notes", "shop_spares", "off_notes", "oos_spare_assignments", "sup_notes_global", "sup_notes_daily", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule", "shop_prev_status", "shorts_button_state"}:
            ser = {}
            for kk, vv in (v or {}).items():
                ser[str(kk)] = vv
            data[k] = ser
        elif k == "daily_notes":
            data[k] = v if v is not None else ""
        else:
            data[k] = v
    return data


def _write_state_file(path: str, data: dict):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.debug(f"Saved state to {path}")
    except Exception as e:
        logging.error(f"Failed to save state to {path}: {e}")


def save_state():
    path = _state_path()
    _write_state_file(path, _serialize_state())
    try:
        st.session_state._next_up_sync_mtime = float(os.path.getmtime(path))
    except Exception:
        pass
    save_off_schedule_defaults(st.session_state.get("off_schedule") or {})
    logging.debug("save_state() called")


def _sync_next_up_from_state_file(force: bool = False):
    path = _state_path()
    if not os.path.exists(path):
        return
    try:
        current_mtime = float(os.path.getmtime(path))
    except Exception:
        return

    last_seen_mtime = float(st.session_state.get("_next_up_sync_mtime") or 0.0)
    if (not force) and current_mtime <= last_seen_mtime:
        return

    disk_next_up = load_state().get("next_up_truck")
    try:
        disk_next_up = int(disk_next_up) if disk_next_up is not None else None
    except Exception:
        disk_next_up = None

    local_next_up = st.session_state.get("next_up_truck")
    try:
        local_next_up = int(local_next_up) if local_next_up is not None else None
    except Exception:
        local_next_up = None

    if local_next_up != disk_next_up:
        st.session_state.next_up_truck = disk_next_up

    st.session_state._next_up_sync_mtime = current_mtime


def archive_current_state(run_date_key: str | None):
    if not run_date_key:
        return
    path = _history_state_path(run_date_key)
    _write_state_file(path, _serialize_state())


def apply_run_config(run_date: date, ship_dates: list[date]):
    new_key = _run_date_key(run_date)
    old_key = _current_run_date_key()
    old_ship_dates = st.session_state.get("ship_dates") or []
    old_ship_keys = sorted(
        d.isoformat() if isinstance(d, date) else str(d)
        for d in old_ship_dates
    )
    new_ship_keys = sorted(d.isoformat() for d in (ship_dates or []))
    if old_key and new_key and old_key != new_key:
        archive_current_state(old_key)
    st.session_state.run_date = run_date
    st.session_state.ship_dates = ship_dates
    st.session_state.setup_done = True
    st.session_state.last_setup_date = date.today()
    st.session_state.run_date_key = new_key
    if (old_key != new_key) or (old_ship_keys != new_ship_keys):
        day_num = ship_day_number(ship_dates[0]) if ship_dates else None
        reset_status_for_new_day(day_num)
    _mark_and_save()


loaded = load_state()
if "sup_notes_global" not in loaded and "sup_notes" in loaded:
    raw_notes = loaded.get("sup_notes") or {}
    normalized = {}
    if isinstance(raw_notes, dict):
        for kk, vv in raw_notes.items():
            try:
                ik = int(kk)
            except Exception:
                ik = kk
            normalized[ik] = vv
    loaded["sup_notes_global"] = normalized
if "sup_notes_daily" not in loaded:
    loaded["sup_notes_daily"] = {}
if "shorts_button_state" not in loaded:
    loaded["shorts_button_state"] = {}
if "shorts_mode" not in loaded:
    loaded["shorts_mode"] = SHORTS_MODE_DISABLE if loaded.get("shorts_disabled") else SHORTS_MODE_BUTTONS

loaded_off_schedule = (
    _normalize_off_schedule(loaded.get("off_schedule") or {})
    if isinstance(loaded.get("off_schedule"), dict)
    else {i: [] for i in range(1, 6)}
)
file_off_schedule = load_off_schedule_defaults()

if _off_schedule_has_entries(loaded_off_schedule):
    default_off_schedule = loaded_off_schedule
elif _off_schedule_has_entries(file_off_schedule):
    default_off_schedule = file_off_schedule
else:
    default_off_schedule = loaded_off_schedule if isinstance(loaded.get("off_schedule"), dict) else file_off_schedule

loaded["off_schedule"] = {int(day): list(trucks) for day, trucks in default_off_schedule.items()}
save_off_schedule_defaults(default_off_schedule)

defaults = {
    # work states
    "cleaned_set": set(),
    "inprog_set": set(),             # max 1
    "loaded_set": set(),

    # management / off + shop
    "off_set": set(),
    "spare_set": set(PERSISTENT_SPARE_TRUCKS),
    "off_notes": {},                 # {truck: text}
    "oos_spare_assignments": {},     # {oos_route: spare_truck}
    "used_spares_today": set(),      # spares that actually loaded an OOS route today
    "spares_needing_return": set(),  # used previous day; start Dirty, return to Spare after unload
    "shop_set": set(),
    "shop_notes": {},                # {truck: text}
    "shop_spares": {},               # {truck: text}
    "shop_prev_status": {},          # {truck: status}
    "shop_notice_log": [],
    "special_set": set(),

    # management per-truck notes
    "sup_notes_global": {},          # {truck: text}
    "sup_notes_daily": {},           # {truck: text}

    # global daily notes
    "daily_notes": "",

    # batching
    "wearers": {},                   # {truck:int}
    "batches": {i: {"trucks": [], "total": 0} for i in range(1, BATCH_COUNT + 1)},

    # unload batching state
    "unload_inprog_truck": None,
    "unload_inprog_start_time": None,
    "unload_inprog_wearers": 0,

    # setup / workday
    "setup_done": False,
    "run_date": None,
    "run_date_key": None,
    "last_setup_date": None,
    "ship_dates": [],

    # navigation
    "active_screen": "SETUP",        # SETUP | UNLOAD | LOAD | SHORTS | STATUS_* | IN_PROGRESS | BREAK
    "shorts_truck": None,
    # selected truck (for TRUCK edit view)
    "selected_truck": None,
    # queued next-up truck (Unloaded)
    "next_up_truck": None,
    # pending OOS route awaiting spare assignment
    "pending_oos_route": None,
    "next_up_return_screen": None,
    # track last requested page from URL to avoid stale query param lock-in
    "last_requested_page": None,
    # navigation history for browser back
    "nav_seq": 0,
    "last_screen_for_history": None,
    "last_nav_seen": None,
    "sup_manage_pref_action": None,

    # timing
    "inprog_start_time": None,       # epoch seconds
    "break_start_time": None,         # epoch seconds
    "break_duration": 30 * 60,
    "break_used": False,
    "load_durations": {},            # {truck:int_seconds}
    "load_start_times": {},          # {truck: epoch}
    "load_finish_times": {},         # {truck: epoch}

    # shorts
    "shorts": {},                    # {truck: [ {item, qty, note}, ... ]}
    "shorts_initials": {},           # {truck: "AB"}
    "shorts_initials_ts": {},        # {truck: iso_timestamp}
    "shorts_initials_history": {},   # {truck: [ {initials, ts}, ... ]}
    "shorts_button_state": {},       # {truck: {step, category, bulk_group, item, qty}}
    "shorts_mode": SHORTS_MODE_BUTTONS,
    "shorts_disabled": False,
    "batching_disabled": False,

    # warning threshold
    "warn_seconds": DEFAULT_WARN_MIN * 60,

    # timezone
    "timezone_key": "America/New_York",

    # app theme
    "ui_theme": "Dark",

    # live truck button styling (status colors + auto-fit text)
    "live_button_styling": True,

    # sidebar status badge colors
    "status_badge_colors": dict(DEFAULT_STATUS_BADGE_COLORS),

    # activity log
    "activity_log": [],

    # Any additional trucks added by management (persisted)
    "extra_fleet": [],
    # Any trucks explicitly removed from fleet (persisted)
    "removed_fleet": [],

    # Off schedule by day number (1-5)
    "off_schedule": {int(day): list(trucks) for day, trucks in default_off_schedule.items()},

    # in-progress tick (for timer refresh)
    "inprog_last_tick": 0.0,

    # shop notice UI state
    "hide_shop_notice": False,

    # overnight rollover prompt
    "rollover_prompt_snooze_until": 0.0,
    "rollover_prompt_hour": ROLLOVER_PROMPT_HOUR,
    "rollover_prompt_snooze_minutes": max(1, ROLLOVER_SNOOZE_SECONDS // 60),
}
for k, v in defaults.items():
    if k not in st.session_state:
        # prefer loaded state when available
        if k in loaded:
            st.session_state[k] = loaded[k]
        else:
            st.session_state[k] = v

if not st.session_state.get("_persistent_spares_seeded"):
    persistent_spares = {int(t) for t in PERSISTENT_SPARE_TRUCKS}
    pending_spare_return = {
        int(t) for t in (st.session_state.get("spares_needing_return") or set())
    }
    current_oos = {int(t) for t in (st.session_state.get("off_set") or set())}
    current_spares = {int(t) for t in (st.session_state.get("spare_set") or set())}

    st.session_state.off_set = current_oos - persistent_spares
    blocked = (
        {int(t) for t in (st.session_state.get("off_set") or set())}
        | {int(t) for t in (st.session_state.get("shop_set") or set())}
        | {int(t) for t in (st.session_state.get("loaded_set") or set())}
        | {int(t) for t in (st.session_state.get("inprog_set") or set())}
    )
    st.session_state.spare_set = (
        (current_spares - pending_spare_return)
        | ((persistent_spares - blocked) - pending_spare_return)
    )
    st.session_state.spares_needing_return = (
        pending_spare_return - set(st.session_state.spare_set)
    )
    st.session_state._persistent_spares_seeded = True

# Auto-mark trucks as off for current load day

# Do not auto-update off_set with off_today. Off trucks should not be automatically sent to Out Of Service.

# Force app theme to dark regardless of device preferences.
st.session_state.ui_theme = "Dark"

# Keep next-up synced from shared state so updates from another device (e.g., mobile)
# are reflected on this session without being overwritten by stale local memory.
_sync_next_up_from_state_file()

# Bootstrap persistence once per session without clobbering every rerun.
if not st.session_state.get("_initial_state_bootstrap_saved"):
    save_state()
    st.session_state._initial_state_bootstrap_saved = True

if st.session_state.get("ui_theme") == "Light":
        st.markdown(
                """
                <style>
                    .truck-bubble, button[kind="primary"] {
                        border: 1px solid rgba(15, 23, 42, 0.25) !important;
                        background: #dbeafe !important;
                        color: #0f172a !important;
                        outline: 2px solid rgba(15, 23, 42, 0.28) !important;
                        outline-offset: -2px !important;
                        font-weight: 900 !important;
                    }
                    button[kind="primary"]:hover {
                        border-color: rgba(15, 23, 42, 0.45) !important;
                        background: #f8fafc !important;
                    }
                    button[kind="primary"]:active {
                        background: #eef2f7 !important;
                    }
                    [data-testid="stAppViewContainer"], .stApp {
                        background-color: #f6f7fb;
                        color: #0f172a;
                    }
                    section[data-testid="stSidebar"] {
                        background-color: #f1f5f9;
                    }
                    section[data-testid="stSidebar"] .stButton > button {
                        color: #0f172a !important;
                        border-color: rgba(15, 23, 42, 0.2) !important;
                        background: linear-gradient(180deg, rgba(15,23,42,0.06), rgba(15,23,42,0.02)) !important;
                    }
                    section[data-testid="stSidebar"] .stButton > button:hover {
                        border-color: rgba(15, 23, 42, 0.35) !important;
                        box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.12), 0 10px 22px rgba(0,0,0,0.10) !important;
                    }
                    section[data-testid="stSidebar"] .stButton > button:active {
                        color: #0b1220 !important;
                    }
                    .stButton > button, .stDownloadButton > button {
                        color: #0f172a !important;
                        border: 1px solid rgba(15, 23, 42, 0.25) !important;
                        background: #ffffff !important;
                    }
                    .stButton > button:hover, .stDownloadButton > button:hover {
                        border-color: rgba(15, 23, 42, 0.45) !important;
                        background: #f8fafc !important;
                        box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.12), 0 10px 22px rgba(0,0,0,0.10) !important;
                    }
                    .stButton > button:active, .stDownloadButton > button:active {
                        color: #0b1220 !important;
                        background: #eef2f7 !important;
                    }
                    .stAlert > div {
                        color: #0f172a !important;
                    }
                    .stAlert [data-testid="stMarkdownContainer"] {
                        color: #0f172a !important;
                    }
                    [data-testid="stExpander"] details {
                        border: 1px solid rgba(15, 23, 42, 0.22) !important;
                        border-radius: 10px !important;
                        background: #f8fafc !important;
                    }
                    [data-testid="stExpander"] summary,
                    [data-testid="stExpander"] summary * {
                        color: #0f172a !important;
                        font-weight: 800 !important;
                    }
                    [data-testid="stExpander"] summary {
                        background: #e2e8f0 !important;
                        border-radius: 10px !important;
                    }
                    [data-testid="stExpander"] summary svg {
                        color: #0f172a !important;
                        fill: #0f172a !important;
                    }
                    .stSelectbox label, .stMultiSelect label, .stRadio div {
                        color: #0f172a !important;
                    }
                    [data-testid="stSelectbox"] div[role="combobox"],
                    [data-testid="stMultiSelect"] div[role="combobox"],
                    div[data-baseweb="select"],
                    div[data-baseweb="select"] > div,
                    div[data-baseweb="select"] > div > div {
                        background-color: #0f172a !important;
                        color: #e2e8f0 !important;
                        border: 1px solid rgba(148, 163, 184, 0.45) !important;
                    }
                    div[data-baseweb="select"]:focus-within > div {
                        border-color: rgba(59, 130, 246, 0.62) !important;
                        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
                    }
                    [data-testid="stSelectbox"] div[role="combobox"] *,
                    [data-testid="stMultiSelect"] div[role="combobox"] *,
                    div[data-baseweb="select"] > div * {
                        color: #e2e8f0 !important;
                    }
                    div[data-baseweb="select"] input {
                        color: #e2e8f0 !important;
                        caret-color: #e2e8f0 !important;
                        background: transparent !important;
                    }
                    div[data-baseweb="tag"] {
                        background-color: #1e293b !important;
                        border: 1px solid rgba(148, 163, 184, 0.45) !important;
                    }
                    div[data-baseweb="tag"] *,
                    div[data-baseweb="tag"] svg {
                        color: #e2e8f0 !important;
                        fill: #e2e8f0 !important;
                    }
                    div[data-baseweb="popover"] [role="listbox"],
                    div[data-baseweb="popover"] [role="menu"],
                    div[data-baseweb="popover"] ul {
                        background-color: #0f172a !important;
                        color: #e2e8f0 !important;
                        border: 1px solid rgba(148, 163, 184, 0.45) !important;
                    }
                    div[data-baseweb="popover"] [role="option"],
                    div[data-baseweb="popover"] li {
                        background-color: #0f172a !important;
                        color: #e2e8f0 !important;
                    }
                    div[data-baseweb="popover"] [role="option"]:hover,
                    div[data-baseweb="popover"] li:hover {
                        background-color: rgba(148, 163, 184, 0.22) !important;
                    }
                    div[data-baseweb="popover"] [role="option"][aria-selected="true"],
                    div[data-baseweb="popover"] li[aria-selected="true"] {
                        background-color: rgba(59, 130, 246, 0.3) !important;
                        color: #e2e8f0 !important;
                    }
                    [data-testid="stNumberInput"] input,
                    [data-testid="stTextInput"] input,
                    [data-testid="stTextArea"] textarea {
                        background-color: #0f172a !important;
                        color: #e2e8f0 !important;
                        caret-color: #e2e8f0 !important;
                        border: 1px solid rgba(148, 163, 184, 0.45) !important;
                    }
                    [data-testid="stTextInput"] input::placeholder,
                    [data-testid="stTextArea"] textarea::placeholder {
                        color: rgba(226, 232, 240, 0.72) !important;
                    }
                    .stMarkdown, .stText, .stCaption, .stMetric, .stSelectbox, .stRadio, .stNumberInput, .stTextInput {
                        color: #0f172a;
                    }
                    @media (max-width: 980px) {
                        [data-testid="stExpander"] summary,
                        [data-testid="stExpander"] summary * {
                            font-size: 1.02rem !important;
                            line-height: 1.2 !important;
                        }
                    }
                </style>
                """,
                unsafe_allow_html=True,
        )
else:
        st.markdown(
                """
                <style>
                    [data-testid="stAppViewContainer"], .stApp {
                        background-color: #0b1020;
                        color: #e2e8f0;
                    }
                    section[data-testid="stSidebar"] {
                        background-color: #0f172a;
                    }
                    .stButton > button, .stDownloadButton > button {
                        color: #e2e8f0 !important;
                        border: 1px solid rgba(148, 163, 184, 0.35) !important;
                        background: rgba(30, 41, 59, 0.85) !important;
                    }
                    .stButton > button:hover, .stDownloadButton > button:hover {
                        border-color: rgba(148, 163, 184, 0.6) !important;
                        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25), 0 10px 22px rgba(0,0,0,0.25) !important;
                    }
                    .stSelectbox, .stSelectbox label, .stSelectbox div, .stSelectbox span,
                    .stTextInput input, .stNumberInput input, .stTextArea textarea,
                    .stRadio div, .stMultiSelect div {
                        color: #e2e8f0 !important;
                    }
                    [data-testid="stSelectbox"] div[role="combobox"],
                    [data-testid="stMultiSelect"] div[role="combobox"],
                    [data-testid="stNumberInput"] input,
                    [data-testid="stTextInput"] input,
                    [data-testid="stTextArea"] textarea {
                        background-color: #0f172a !important;
                        border: 1px solid rgba(148, 163, 184, 0.3) !important;
                    }
                </style>
                """,
                unsafe_allow_html=True,
        )

# If management has previously added trucks, merge them into the runtime FLEET
try:
    fleet_from_file = load_fleet_file()
    if fleet_from_file:
        FLEET = sorted(set(fleet_from_file))
    else:
        extra = st.session_state.get("extra_fleet") or []
        extra_ints = [int(x) for x in extra]
        removed = st.session_state.get("removed_fleet") or []
        removed_ints = [int(x) for x in removed]
        # Compute runtime FLEET = base range + extras - removed
        base = set(range(FLEET_MIN, FLEET_MAX + 1))
        FLEET = sorted((base | set(extra_ints)) - set(removed_ints))
        # Persist initial fleet file for future runs
        save_fleet_file(FLEET)
except Exception as e:
    logging.error(f"Exception during fleet initialization: {e}")

# Ensure active trucks from persisted state are always visible in Fleet views,
# even if they are missing from truck_fleet.json.
try:
    status_keys = (
        "cleaned_set",
        "inprog_set",
        "loaded_set",
        "shop_set",
        "off_set",
        "spare_set",
        "special_set",
    )
    active_state_trucks: set[int] = set()
    for sk in status_keys:
        for raw in (st.session_state.get(sk) or set()):
            try:
                active_state_trucks.add(int(raw))
            except Exception:
                pass

    if active_state_trucks:
        merged_fleet = sorted(set(FLEET) | active_state_trucks)
        if merged_fleet != FLEET:
            FLEET = merged_fleet
            save_fleet_file(FLEET)
except Exception as e:
    logging.error(f"Exception while merging active trucks into fleet: {e}")

# ==========================================================
# CSS (bubbled truck lists on status pages)
# ==========================================================
st.markdown(
    """
    <style>
        .main .block-container,
        [data-testid="stMainBlockContainer"],
        section.main > div.block-container,
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-top: 0.25rem !important;
        }
        @media (max-width: 980px) {
            .main .block-container,
            [data-testid="stMainBlockContainer"],
            section.main > div.block-container,
            [data-testid="stAppViewContainer"] .main .block-container {
                padding-top: 0.08rem !important;
            }
        }
        .shop-notice {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.65);
            margin: 0 0 -4px 0;
            overflow: hidden;
        }
        .notice-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            cursor: pointer;
            font-weight: 800;
            background: rgba(30, 41, 59, 0.88);
            border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            user-select: none;
        }
        .notice-bar-title {
            letter-spacing: 0.04em;
        }
        .notice-bar-toggle {
            opacity: 0.9;
            font-size: 0.85rem;
        }
        .notice-item {
            display: flex;
            align-items: baseline;
            gap: 8px;
            padding: 6px 12px;
            border-top: 1px solid rgba(148, 163, 184, 0.16);
        }
        .notice-item .timestamp {
            min-width: 72px;
            color: #93c5fd;
            font-weight: 700;
            opacity: 0.9;
        }
        .notice-item .body {
            flex: 1;
        }
        .shop-notice.collapsed .notice-item {
            display: none;
        }
        @keyframes noticeFlashBlue {
            0%, 100% {
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35), 0 12px 26px rgba(0, 0, 0, 0.22);
            }
            50% {
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.62), 0 16px 32px rgba(0, 0, 0, 0.28);
            }
        }
        @keyframes noticeFlashAmber {
            0%, 100% {
                box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.35), 0 10px 20px rgba(0, 0, 0, 0.20);
            }
            50% {
                box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.62), 0 14px 26px rgba(0, 0, 0, 0.26);
            }
        }
        .shop-notice.flash {
            animation: noticeFlashBlue 1.1s ease-in-out infinite;
        }
        .shop-notice.flash-collapsed {
            animation: noticeFlashAmber 1.1s ease-in-out infinite;
        }
        .truck-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }
        .truck-bubble, button[kind="primary"] {
            width: 48px;
            height: 48px;
            min-width: 44px !important;
            min-height: 44px !important;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 900;
            display: flex;
            align-items: center;
            justify-content: center;
            user-select: none;
        }
        @media (max-width: 600px) {
            .truck-bubble, button[kind="primary"] {
                width: 38px !important;
                height: 38px !important;
                font-size: 15px !important;
                border-radius: 10px !important;
            }
        }
        /* Make sidebar and text more readable on mobile */
        @media (max-width: 600px) {
            .stSidebar, section[data-testid="stSidebar"] {
                font-size: 15px !important;
            }
            .stApp, [data-testid="stAppViewContainer"] {
                font-size: 16px !important;
            }
        }
        /* Make touch targets larger */
        .stButton > button, .stDownloadButton > button {
            min-height: 44px !important;
            min-width: 44px !important;
            font-size: 18px !important;
            white-space: nowrap !important;
            line-height: 1.05 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        @media (max-width: 600px) {
            .stButton > button, .stDownloadButton > button {
                font-size: 15px !important;
            }
        }
        @media (max-width: 980px) {
            .stButton > button[kind="primary"] {
                width: 100% !important;
                max-width: 100% !important;
            }
            [data-testid="stSelectbox"] div[role="combobox"],
            [data-testid="stMultiSelect"] div[role="combobox"],
            [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
            [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
            div[data-baseweb="select"] > div {
                background: #0f172a !important;
                background-color: #0f172a !important;
                border: 1px solid rgba(148, 163, 184, 0.55) !important;
                color: #e2e8f0 !important;
            }
            [data-testid="stSelectbox"] div[role="combobox"] *,
            [data-testid="stMultiSelect"] div[role="combobox"] *,
            div[data-baseweb="select"] > div * {
                color: #e2e8f0 !important;
                -webkit-text-fill-color: #e2e8f0 !important;
            }
            div[data-baseweb="select"] input {
                background: transparent !important;
                color: #e2e8f0 !important;
                -webkit-text-fill-color: #e2e8f0 !important;
            }
            div[data-baseweb="popover"] [role="listbox"],
            div[data-baseweb="popover"] [role="menu"],
            div[data-baseweb="popover"] ul {
                background: #0f172a !important;
                background-color: #0f172a !important;
                color: #e2e8f0 !important;
                border: 1px solid rgba(148, 163, 184, 0.55) !important;
            }
            div[data-baseweb="popover"] [role="option"],
            div[data-baseweb="popover"] li {
                background-color: #0f172a !important;
                color: #e2e8f0 !important;
                -webkit-text-fill-color: #e2e8f0 !important;
            }
            div[data-baseweb="popover"] [role="option"][aria-selected="true"],
            div[data-baseweb="popover"] li[aria-selected="true"] {
                background-color: rgba(59, 130, 246, 0.32) !important;
                color: #e2e8f0 !important;
                -webkit-text-fill-color: #e2e8f0 !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# Query-param helpers (for status bar links)
# ==========================================================
def _get_query_params():
    return dict(st.query_params)

def _set_query_params(**kwargs):
    # Update query params using the modern API
    for k, v in kwargs.items():
        if v is None:
            try:
                st.query_params.pop(k, None)
            except Exception:
                pass
        else:
            st.query_params[k] = v

def _page_param_for_screen(screen: str | None) -> str | None:
    if screen == "SUPERVISOR":
        return "MANAGEMENT"
    return screen

def _push_nav_history(force: bool = False):
    current = st.session_state.get("active_screen")
    if not current:
        return
    last = st.session_state.get("last_screen_for_history")
    pick_value = None
    if current == "BATCH":
        pick_candidate = st.session_state.get("unload_inprog_truck")
        if pick_candidate is None:
            pick_candidate = st.session_state.get("unload_truck_select")
        try:
            if pick_candidate is not None:
                pick_value = str(int(pick_candidate))
        except Exception:
            pick_value = None

    truck_value = None
    truck_candidate = None
    if current == "TRUCK":
        truck_candidate = st.session_state.get("selected_truck")
    elif current == "SHORTS":
        truck_candidate = st.session_state.get("shorts_truck")
    elif current == "IN_PROGRESS":
        try:
            truck_candidate = next(iter(st.session_state.get("inprog_set") or set()), None)
        except Exception:
            truck_candidate = None
    elif current == "STATUS_LOADED":
        truck_candidate = st.session_state.get("selected_truck")

    try:
        if truck_candidate is not None:
            truck_value = str(int(truck_candidate))
    except Exception:
        truck_value = None

    from_page_value = None
    if current == "TRUCK":
        from_raw = st.session_state.get("_from_page")
        from_page_value = str(from_raw).strip() if from_raw else None

    fleet_mode = None
    fleet_truck = None
    fleet_action = None
    fleet_state = None
    if current == "FLEET":
        if st.session_state.get("sup_manage_new_mode"):
            fleet_mode = "new"
        elif st.session_state.get("sup_manage_multi_mode"):
            fleet_mode = "multi"
        else:
            fleet_mode = "single"
        fleet_candidate = st.session_state.get("sup_manage_truck")
        try:
            if fleet_candidate is not None:
                fleet_truck = str(int(fleet_candidate))
        except Exception:
            fleet_truck = None
        fleet_action_raw = st.session_state.get("sup_manage_action")
        fleet_action = str(fleet_action_raw).strip() if fleet_action_raw else None
        fleet_state = (fleet_mode, fleet_truck, fleet_action)

    previous_fleet_state = st.session_state.get("last_fleet_nav_state")
    fleet_changed = current == "FLEET" and fleet_state != previous_fleet_state
    should_update = force or current != last or fleet_changed
    if not should_update:
        return

    seq = int(st.session_state.get("nav_seq") or 0)
    if force or current != last:
        seq += 1
        st.session_state.nav_seq = seq
        st.session_state.last_screen_for_history = current

    if current == "FLEET":
        st.session_state.last_fleet_nav_state = fleet_state
    else:
        st.session_state.last_fleet_nav_state = None

    _set_query_params(
        page=_page_param_for_screen(current),
        nav=str(seq),
        truck=truck_value,
        pick=pick_value,
        start=None,
        fleet_mode=fleet_mode,
        fleet_truck=fleet_truck,
        fleet_action=fleet_action,
        **{"from": from_page_value},
    )

# ==========================================================
# Helpers
# ==========================================================
LOAD_DAY_NAME_BY_NUM = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
}


def load_day_label(day_num: int) -> str:
    d = int(day_num)
    return f"Day {d} ({LOAD_DAY_NAME_BY_NUM.get(d, 'Unknown')})"


def ship_day_number(d: date) -> int | None:
    wd = d.weekday()  # Mon=0 ... Sun=6
    # Map Monday->Day1 ... Friday->Day5. For weekend ship dates (Sat/Sun),
    # treat them as Day 1 (rare cases where loads occur on weekend).
    return wd + 1 if 0 <= wd <= 4 else 1

def fmt_long_date(d: date) -> str:
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")

def seconds_to_mmss(sec: int) -> str:
    total = max(0, int(sec))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02}:{s:02}"

def _get_timezone_key() -> str:
    return st.session_state.get("timezone_key") or "America/New_York"

def _get_tzinfo():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(_get_timezone_key())
    except Exception:
        return None

def _normalized_tz_key() -> str:
    tz_key = _get_timezone_key()
    if ZoneInfo is None:
        return "UTC"
    try:
        ZoneInfo(tz_key)
        return tz_key
    except Exception:
        return "UTC"

def _format_ts(ts: float) -> str:
    tzinfo = _get_tzinfo()
    try:
        dt = datetime.fromtimestamp(ts, tz=tzinfo) if tzinfo else datetime.fromtimestamp(ts)
    except Exception:
        dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")

def log_action(message: str):
    try:
        tzinfo = _get_tzinfo()
        now_ts = datetime.now(tzinfo) if tzinfo else datetime.now()
    except Exception:
        now_ts = datetime.now()
    stamp = f"{now_ts.month}/{now_ts.day} {now_ts.strftime('%I:%M %p')}"
    entry = f"{stamp} - {message}"
    log = list(st.session_state.get("activity_log") or [])
    log.append(entry)
    st.session_state.activity_log = log[-50:]


def get_truck_notes(truck: int) -> tuple[str, str, str]:
    t = int(truck)
    global_note = (st.session_state.sup_notes_global.get(t) or "").strip()
    daily_note = (st.session_state.sup_notes_daily.get(t) or "").strip()
    if global_note and daily_note:
        combined = f"Global: {global_note}\nDaily: {daily_note}"
    elif global_note:
        combined = global_note
    else:
        combined = daily_note
    return global_note, daily_note, combined

def _format_note_lines_as_bullets_html(note_text: str, *, empty_html: str = "") -> str:
    lines: list[str] = []
    for raw in (note_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[:1] in {"-", "*", "•"}:
            line = line[1:].strip()
        if line:
            lines.append(line)
    if not lines:
        return empty_html
    li_html = "".join(f"<li style='margin:0 0 6px 0;'>{html.escape(line)}</li>" for line in lines)
    return f"<ul style='margin:0; padding-left:1.2em;'>{li_html}</ul>"

def _now_local():
    try:
        tzinfo = _get_tzinfo()
        return datetime.now(tzinfo) if tzinfo else datetime.now()
    except Exception:
        return datetime.now()


def _day_key_from_ts(ts: float) -> str:
    try:
        tzinfo = _get_tzinfo()
        dt = datetime.fromtimestamp(ts, tz=tzinfo) if tzinfo else datetime.fromtimestamp(ts)
    except Exception:
        dt = datetime.fromtimestamp(ts)
    return dt.date().isoformat()


def _today_day_key() -> str:
    return _now_local().date().isoformat()

def _current_ship_day_num() -> int | None:
    ship_dates = st.session_state.get("ship_dates") or []
    if not ship_dates:
        return None
    try:
        return ship_day_number(ship_dates[0])
    except Exception:
        return None

def _previous_ship_day_num(day_num: int | None) -> int | None:
    if not day_num:
        return None
    return 5 if day_num == 1 else max(1, day_num - 1)

def _next_ship_day_num(day_num: int | None) -> int | None:
    if not day_num:
        return None
    return 1 if day_num == 5 else min(5, day_num + 1)


def _next_ship_date_for_day(run_date: date, day_num: int) -> date:
    target_weekday = max(0, min(4, int(day_num) - 1))
    start = run_date + timedelta(days=1)
    for offset in range(14):
        candidate = start + timedelta(days=offset)
        if candidate.weekday() == target_weekday:
            return candidate
    return start


def _holiday_ship_dates_for_days(run_date: date, day_nums: list[int]) -> list[date]:
    return sorted(_next_ship_date_for_day(run_date, int(day)) for day in day_nums)


def render_holiday_load_day_picker(run_date: date, key_prefix: str) -> tuple[list[date], bool]:
    st.caption("Select the two load days we are loading today.")
    day_options = [1, 2, 3, 4, 5]
    tomorrow_num = ship_day_number(run_date + timedelta(days=1)) or 1
    second_default = _next_ship_day_num(tomorrow_num) or 1

    left, right = st.columns(2)
    with left:
        day_1 = st.selectbox(
            "Load day 1",
            options=day_options,
            index=day_options.index(int(tomorrow_num)),
            format_func=load_day_label,
            key=f"{key_prefix}_holiday_day_1",
        )
    with right:
        day_2 = st.selectbox(
            "Load day 2",
            options=day_options,
            index=day_options.index(int(second_default)),
            format_func=load_day_label,
            key=f"{key_prefix}_holiday_day_2",
        )

    if int(day_1) == int(day_2):
        st.error("Select two different load days for holiday mode.")
        return [], False

    ship_dates = _holiday_ship_dates_for_days(run_date, [int(day_1), int(day_2)])
    st.caption(
        "Holiday load days: "
        + ", ".join(f"{load_day_label(ship_day_number(d) or 1)} ({d.isoformat()})" for d in ship_dates)
    )
    return ship_dates, True

def off_trucks_for_day(day_num: int | None) -> set[int]:
    if not day_num:
        return set()
    schedule = st.session_state.get("off_schedule") or {}
    raw = schedule.get(int(day_num), []) or []
    try:
        return {int(x) for x in raw}
    except Exception:
        return set()

def off_trucks_for_today() -> set[int]:
    return off_trucks_for_day(_current_ship_day_num())

def off_trucks_for_next_day() -> set[int]:
    return off_trucks_for_day(_next_ship_day_num(_current_ship_day_num()))


def _get_rollover_prompt_hour() -> int:
    try:
        hour = int(st.session_state.get("rollover_prompt_hour", ROLLOVER_PROMPT_HOUR))
    except Exception:
        hour = ROLLOVER_PROMPT_HOUR
    return max(0, min(23, hour))


def _get_rollover_snooze_minutes() -> int:
    try:
        minutes = int(
            st.session_state.get(
                "rollover_prompt_snooze_minutes",
                max(1, ROLLOVER_SNOOZE_SECONDS // 60),
            )
        )
    except Exception:
        minutes = max(1, ROLLOVER_SNOOZE_SECONDS // 60)
    return max(1, min(240, minutes))


def _get_rollover_snooze_seconds() -> int:
    return _get_rollover_snooze_minutes() * 60


def scheduled_trucks_for_current_load_day() -> set[int]:
    off_today = {int(t) for t in off_trucks_for_today()}
    oos = {int(t) for t in (st.session_state.get("off_set") or set())}
    spare = {int(t) for t in (st.session_state.get("spare_set") or set())}
    blocked = off_today | oos | spare
    return {int(t) for t in FLEET} - blocked


def current_load_day_completion() -> dict[str, object]:
    scheduled = scheduled_trucks_for_current_load_day()
    loaded = {int(t) for t in (st.session_state.get("loaded_set") or set())}
    complete = sorted(scheduled & loaded)
    remaining = sorted(scheduled - loaded)
    return {
        "scheduled_total": len(scheduled),
        "loaded_count": len(complete),
        "remaining": remaining,
    }


def _rollover_prompt_due() -> bool:
    if not st.session_state.get("setup_done"):
        return False
    run_date = st.session_state.get("run_date")
    if not isinstance(run_date, date):
        return False
    now_local = _now_local()
    if now_local.date() <= run_date:
        return False
    return now_local.hour >= _get_rollover_prompt_hour()


def _start_next_load_day_now():
    today = _now_local().date()
    apply_run_config(today, [today + timedelta(days=1)])
    st.session_state.rollover_prompt_snooze_until = 0.0
    st.session_state.active_screen = "UNLOAD"


def render_rollover_prompt_if_needed():
    if not _rollover_prompt_due():
        return

    try:
        snooze_until = float(st.session_state.get("rollover_prompt_snooze_until") or 0.0)
    except Exception:
        snooze_until = 0.0
    if time.time() < snooze_until:
        return

    run_date = st.session_state.get("run_date")
    completion = current_load_day_completion()
    scheduled_total = int(completion.get("scheduled_total", 0) or 0)
    loaded_count = int(completion.get("loaded_count", 0) or 0)
    remaining = completion.get("remaining") or []
    remaining_list = [int(t) for t in remaining]
    all_done = len(remaining_list) == 0
    prompt_hour = _get_rollover_prompt_hour()
    snooze_minutes = _get_rollover_snooze_minutes()

    if all_done:
        st.success(
            f"Load day {run_date.isoformat()} is complete ({loaded_count}/{scheduled_total} scheduled loaded). "
            "Start the next load day?"
        )
    else:
        preview = ", ".join(f"#{int(t)}" for t in remaining_list[:12])
        extra = len(remaining_list) - min(len(remaining_list), 12)
        suffix = f", +{extra} more" if extra > 0 else ""
        st.warning(
            f"Current load day {run_date.isoformat()} is still active after {prompt_hour}:00. "
            f"Loaded {loaded_count}/{scheduled_total} scheduled trucks. "
            f"Remaining: {preview}{suffix}."
        )
    st.caption(f"If you keep the current load day, you'll be reminded again in {snooze_minutes} minutes.")

    c_start, c_keep = st.columns(2)
    with c_start:
        if st.button("Start next load day", key="rollover_start_next_day", use_container_width=True):
            _start_next_load_day_now()
            _mark_and_save()
            st.rerun()
    with c_keep:
        if st.button("Keep current load day", key="rollover_keep_current_day", use_container_width=True):
            st.session_state.rollover_prompt_snooze_until = time.time() + _get_rollover_snooze_seconds()
            _mark_and_save()
            st.rerun()


def is_duplicate_notice(truck: int, notice_type: str) -> bool:
    day_key = _today_day_key()
    t = int(truck)
    for entry in st.session_state.get("shop_notice_log") or []:
        if entry.get("type") != notice_type:
            continue
        try:
            if int(entry.get("truck", -1)) != t:
                continue
        except Exception:
            continue
        ts = entry.get("ts")
        if ts is None:
            continue
        if _day_key_from_ts(float(ts)) == day_key:
            return True
    return False


def push_shop_notice(message: str, kind: str = "shop", notice_type: str | None = None, truck: int | None = None):
    now_ts = time.time()
    log = list(st.session_state.get("shop_notice_log") or [])
    record = {"ts": now_ts, "msg": message, "kind": kind}
    if notice_type:
        record["type"] = notice_type
    if truck is not None:
        record["truck"] = int(truck)
    log.append(record)
    st.session_state.shop_notice_log = log[-50:]
    st.session_state.hide_shop_notice = False

def render_shop_notice():
    shop_trucks = sorted(st.session_state.shop_set)
    log = list(st.session_state.get("shop_notice_log") or [])
    if not log and not shop_trucks:
        return
    if not log and shop_trucks:
        safe_items = ", ".join(f"#{t}" for t in shop_trucks)
        push_shop_notice(f"Sent to shop: {safe_items}", kind="shop")
        log = list(st.session_state.get("shop_notice_log") or [])
        save_state()

    recent = log[-10:]
    lines = []
    last_day_key = None
    for entry in reversed(recent):
        try:
            tzinfo = _get_tzinfo()
            ts_dt = datetime.fromtimestamp(entry.get("ts", time.time()), tz=tzinfo) if tzinfo else datetime.fromtimestamp(entry.get("ts", time.time()))
        except Exception:
            ts_dt = datetime.fromtimestamp(entry.get("ts", time.time()))
        day_key = ts_dt.date().isoformat()
        if day_key != last_day_key:
            header = ts_dt.strftime("%a %m/%d")
            lines.append(
                "<div class='notice-item' style='font-weight:800; letter-spacing:0.04em;'>"
                f"  <span class='timestamp' style='color:#93c5fd;'>{header}</span>"
                "</div>"
            )
            last_day_key = day_key
        stamp = ts_dt.strftime("%I:%M %p")
        raw_msg = str(entry.get("msg", ""))
        msg = html.escape(raw_msg)
        kind = entry.get("kind") or "shop"
        is_sent_to_shop = raw_msg.strip().lower().startswith("sent to shop")
        if kind == "return":
            body_style = " style='color:#22c55e; font-weight:700;'"
        elif is_sent_to_shop:
            body_style = " style='color:#ef4444; font-weight:700;'"
        else:
            body_style = ""
        lines.append(
            "<div class='notice-item'>"
            f"  <span class='timestamp'>{stamp}</span>"
            f"  <span class='body'{body_style}>{msg}</span>"
            "</div>"
        )
    notice_id = str(log[-1].get("ts", time.time()))
    st.markdown(
        (
            f"<div class='shop-notice' data-notice-id='{notice_id}'>"
            "  <div class='notice-bar'>"
            "    <span class='notice-bar-title'>Notices</span>"
            "    <span class='notice-bar-toggle'>Collapse</span>"
            "  </div>"
            f"  {''.join(lines)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
        (function(){
            const root = window.parent.document;
            const notices = root.querySelectorAll('.shop-notice');
            if (!notices || !notices.length) return;
            const notice = notices[notices.length - 1];
            const bar = notice.querySelector('.notice-bar');
            const toggle = notice.querySelector('.notice-bar-toggle');
            if (!notice || !bar || !toggle) return;

            const storage = (() => {
                try { return window.parent.localStorage; } catch(e) { return null; }
            })();
            const getStored = (key, fallback) => {
                try {
                    if (!storage) return fallback;
                    const val = storage.getItem(key);
                    return val == null ? fallback : val;
                } catch (e) {
                    return fallback;
                }
            };
            const setStored = (key, value) => {
                try {
                    if (storage) storage.setItem(key, value);
                } catch (e) {}
            };

            const id = notice.getAttribute('data-notice-id') || '';
            const ackId = getStored('shopNoticeAckId', '');

            const applyState = () => {
                const collapsed = getStored('shopNoticeCollapsed', '0') === '1';
                if (collapsed) {
                    notice.classList.add('collapsed');
                    toggle.textContent = 'Expand';
                } else {
                    notice.classList.remove('collapsed');
                    toggle.textContent = 'Collapse';
                }
            };

            const applyFlashState = () => {
                const collapsed = getStored('shopNoticeCollapsed', '0') === '1';
                const hasUnacknowledged = id && ackId !== id;
                notice.classList.remove('flash');
                notice.classList.remove('flash-collapsed');
                if (!hasUnacknowledged) return;
                if (collapsed) notice.classList.add('flash-collapsed');
                else notice.classList.add('flash');
            };

            const acknowledgeNotice = () => {
                if (!id) return;
                setStored('shopNoticeAckId', id);
                notice.classList.remove('flash');
                notice.classList.remove('flash-collapsed');
            };

            applyState();
            applyFlashState();
            if (!bar.dataset.bound) {
                bar.addEventListener('click', function(){
                    acknowledgeNotice();
                    const collapsed = notice.classList.contains('collapsed');
                    setStored('shopNoticeCollapsed', collapsed ? '0' : '1');
                    applyState();
                });
                bar.dataset.bound = '1';
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )

def _get_client_user_agent() -> str:
    try:
        ctx = getattr(st, "context", None)
        headers = getattr(ctx, "headers", None) if ctx is not None else None
        ua = str(headers.get("user-agent", "")).strip().lower() if headers else ""
        if ua:
            return ua
    except Exception:
        pass

    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers  # type: ignore
        headers = _get_websocket_headers() or {}
        ua = str(headers.get("User-Agent") or headers.get("user-agent") or "").strip().lower()
        if ua:
            return ua
    except Exception:
        pass

    return ""


def _is_mobile_client() -> bool:
    try:
        query_params = _get_query_params()
        force_mobile = str(query_params.get("mobile", "")).strip().lower()
        if force_mobile in {"1", "true", "yes", "y", "on"}:
            return True
        if force_mobile in {"0", "false", "no", "n", "off"}:
            return False
    except Exception:
        pass

    user_agent = _get_client_user_agent()
    if not user_agent:
        return False
    mobile_tokens = [
        "iphone",
        "android",
        "mobile",
        "ipad",
        "ipod",
        "windows phone",
        "opera mini",
        "opera mobi",
        "blackberry",
    ]
    return any(tok in user_agent for tok in mobile_tokens)

def _truck_grid_columns(default_cols: int = 8) -> int:
    base_cols = max(1, int(default_cols))
    if _is_mobile_client():
        return 2 if base_cols > 1 else 1
    return base_cols


def _force_mobile_button_grid(expected_labels: list[str], mobile_cols: int = 2, primary_only: bool = False):
    labels = sorted({str(v).strip() for v in (expected_labels or []) if str(v).strip()})
    cols = max(1, int(mobile_cols))
    if not labels or cols <= 1:
        return

    button_selector = 'button[kind="primary"]' if primary_only else 'button'
    labels_json = json.dumps(labels)
    selector_json = json.dumps(button_selector)
    cell_width = f"calc({100.0 / float(cols):.6f}% - 0.36rem)"
    cell_width_json = json.dumps(cell_width)

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const root = window.parent.document;
                const expected = new Set({labels_json});
                const selector = {selector_json};
                const cellWidth = {cell_width_json};

                const normalize = (value) => String(value || '').replace(/\u2063/g, '').trim();
                const isMobileViewport = () => {{
                    try {{
                        return window.parent.matchMedia('(max-width: 980px)').matches || window.parent.innerWidth <= 980;
                    }} catch (e) {{
                        return (window.parent.innerWidth || window.innerWidth || 1200) <= 980;
                    }}
                }};

                const resetContainer = (node) => {{
                    if (!node) return;
                    node.style.removeProperty('display');
                    node.style.removeProperty('flex-wrap');
                    node.style.removeProperty('align-items');
                    node.style.removeProperty('column-gap');
                    node.style.removeProperty('row-gap');
                }};
                const resetSlot = (node) => {{
                    if (!node) return;
                    node.style.removeProperty('min-width');
                    node.style.removeProperty('flex');
                    node.style.removeProperty('width');
                    node.style.removeProperty('max-width');
                }};

                const findGroupContainer = (btn, matchedButtons) => {{
                    let node = btn.parentElement;
                    for (let depth = 0; node && depth < 10; depth += 1, node = node.parentElement) {{
                        let count = 0;
                        for (const candidate of matchedButtons) {{
                            if (node.contains(candidate)) count += 1;
                            if (count > 24) break;
                        }}
                        if (count >= 2 && count <= 24) return node;
                    }}
                    return null;
                }};

                const applyGrid = () => {{
                    const mobile = isMobileViewport();
                    const buttons = Array.from(root.querySelectorAll(selector));
                    const matched = buttons.filter((btn) => {{
                        const label = normalize(btn.innerText || btn.textContent || '');
                        return !!label && expected.has(label);
                    }});
                    if (!matched.length) return;

                    const groupMap = new Map();
                    matched.forEach((btn) => {{
                        const container = findGroupContainer(btn, matched);
                        if (!container) return;
                        if (!groupMap.has(container)) groupMap.set(container, []);
                        groupMap.get(container).push(btn);
                    }});

                    groupMap.forEach((groupButtons, container) => {{
                        const uniqueButtons = Array.from(new Set(groupButtons));
                        if (uniqueButtons.length < 1) {{
                            resetContainer(container);
                            uniqueButtons.forEach((btn) => resetSlot(btn));
                            return;
                        }}

                        const slots = new Set();
                        uniqueButtons.forEach((btn) => {{
                            let slot = btn;
                            while (slot.parentElement && slot.parentElement !== container) {{
                                slot = slot.parentElement;
                            }}
                            slots.add(slot || btn);
                        }});

                        if (mobile) {{
                            const targetWidth = uniqueButtons.length === 1 ? '100%' : cellWidth;
                            container.style.setProperty('display', 'flex', 'important');
                            container.style.setProperty('flex-wrap', 'wrap', 'important');
                            container.style.setProperty('align-items', 'stretch', 'important');
                            container.style.setProperty('column-gap', '0.36rem', 'important');
                            container.style.setProperty('row-gap', '0.36rem', 'important');
                            slots.forEach((slot) => {{
                                slot.style.setProperty('min-width', '0', 'important');
                                slot.style.setProperty('flex', `0 0 ${{targetWidth}}`, 'important');
                                slot.style.setProperty('width', targetWidth, 'important');
                                slot.style.setProperty('max-width', targetWidth, 'important');
                            }});
                            uniqueButtons.forEach((btn) => {{
                                btn.style.setProperty('width', '100%', 'important');
                                btn.style.setProperty('min-width', '0', 'important');
                            }});
                        }} else {{
                            resetContainer(container);
                            slots.forEach((slot) => resetSlot(slot));
                        }}
                    }});
                }};

                applyGrid();
                setTimeout(applyGrid, 60);
                setTimeout(applyGrid, 220);
                setTimeout(applyGrid, 500);
                setTimeout(applyGrid, 900);
            }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _color_text_for_background(bg_hex: str) -> str:
    normalized = _normalize_hex_color(bg_hex, "#334155")
    try:
        r = int(normalized[1:3], 16)
        g = int(normalized[3:5], 16)
        b = int(normalized[5:7], 16)
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return "#0f172a" if luminance > 0.65 else "#ffffff"
    except Exception:
        return "#ffffff"


def _color_darken(bg_hex: str, factor: float = 0.62) -> str:
    normalized = _normalize_hex_color(bg_hex, "#334155")
    try:
        r = int(normalized[1:3], 16)
        g = int(normalized[3:5], 16)
        b = int(normalized[5:7], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#1e293b"


def _truck_status_colors(truck_num: int, badge_colors: dict[str, str] | None = None) -> tuple[str, str, str]:
    colors = badge_colors or _get_status_badge_colors()
    status = current_status_label(int(truck_num))
    if status == "Dirty":
        bg = colors["dirty"]
        text_color = "#000000"
    elif status == "Unloaded":
        bg = colors["unloaded"]
        text_color = "#000000"
    elif status == "In Progress":
        bg = colors["in_progress"]
        text_color = "#000000"
    elif status == "Loaded":
        bg = colors["loaded"]
        text_color = "#000000"
    elif status == "Shop":
        bg = colors["shop"]
        text_color = "#000000"
    elif status in ("Out Of Service", "Spare"):
        bg = colors["oos_spare"]
        text_color = "#ffffff"
    elif status == "Special":
        bg = "#7c3aed"
        text_color = "#000000"
    else:
        bg = "#334155"
        text_color = "#000000"

    border = _color_darken(bg, factor=0.62)
    return bg, border, text_color


def render_truck_status_card(truck_num: int, compact_top: bool = False, size_variant: str = "default"):
    t = int(truck_num)
    cur_status = current_status_label(t)
    card_bg, card_border, card_text = _truck_status_colors(t)
    status_safe = html.escape(str(cur_status))
    top_margin = "0px" if compact_top else "6px"
    if str(size_variant).strip().lower() == "fleet":
        card_max_width = "500px"
        card_padding = "12px 10px"
        truck_font_size = "32px"
        status_font_size = "17px"
        status_margin_top = "3px"
    else:
        card_max_width = "560px"
        card_padding = "16px 12px"
        truck_font_size = "36px"
        status_font_size = "14px"
        status_margin_top = "2px"
    oos_center_overlay_html = ""
    if cur_status == "Out Of Service":
        oos_center_overlay_html = (
            "<div style='position:absolute; inset:8px; pointer-events:none; display:flex; align-items:center; justify-content:center;'>"
            "  <div style='font-size:86px; font-weight:900; color:rgba(185,28,28,0.48); line-height:1;'>×</div>"
            "</div>"
        )
    st.markdown(
        (
            f"<div style='max-width:{card_max_width}; margin:{top_margin} auto 10px auto; padding:{card_padding}; "
            f"border:3px solid {card_border}; border-radius:16px; "
            f"background:{card_bg}; box-shadow:0 12px 28px rgba(0,0,0,0.22); position:relative; overflow:hidden;'>"
            f"  <div style='text-align:center; font-size:{truck_font_size}; font-weight:900; margin:0; color:{card_text};'>"
            f"  Truck {t}"
            "  </div>"
            f"  <div style='text-align:center; font-size:{status_font_size}; font-weight:700; margin-top:{status_margin_top}; color:{card_text}; opacity:0.9;'>"
            f"  {status_safe}"
            "  </div>"
            f"  {oos_center_overlay_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

def render_numeric_truck_buttons(
    trucks: list[int],
    key_prefix: str,
    default_cols: int = 8,
    trailing_button_label: str | None = None,
    trailing_button_value: str | None = None,
    additional_buttons: list[tuple[str, str]] | None = None,
    flash_trucks: set[int] | None = None,
    muted_trucks: set[int] | None = None,
    outlined_trucks: set[int] | None = None,
    force_text_color: str | None = None,
) -> int | str | None:
    ordered = sorted({int(t) for t in (trucks or [])})

    trailing_buttons: list[tuple[str, str]] = []
    if trailing_button_label:
        trailing_value = trailing_button_value if trailing_button_value is not None else trailing_button_label
        trailing_buttons.append((str(trailing_button_label).strip(), str(trailing_value).strip()))
    for entry in (additional_buttons or []):
        if not isinstance(entry, (list, tuple)) or not entry:
            continue
        label_raw = str(entry[0]).strip()
        if not label_raw:
            continue
        value_raw = str(entry[1]).strip() if len(entry) > 1 else label_raw
        trailing_buttons.append((label_raw, value_raw if value_raw else label_raw))

    if not ordered and not trailing_buttons:
        return None

    live_button_styling = bool(st.session_state.get("live_button_styling", True))
    trailing_labels_json = json.dumps([label for label, _ in trailing_buttons]) if trailing_buttons else "[]"
    force_text_color_json = json.dumps(_normalize_hex_color(force_text_color, "#000000") if force_text_color else "")
    try:
        oos_labels_json = json.dumps(sorted({str(int(t)) for t in (st.session_state.get("off_set") or set())}))
    except Exception:
        oos_labels_json = "[]"

    if not live_button_styling:
        components.html(
            """
            <script>
            (function() {
                try {
                    const root = window.parent.document;
                    const buttons = root.querySelectorAll('button[kind="primary"]');
                    buttons.forEach((btn) => {
                        const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                        if (!/^\d+$/.test(raw)) return;

                        [
                            'background',
                            'border',
                            'color',
                            'font-weight',
                            'display',
                            'align-items',
                            'justify-content',
                            'text-align',
                            'padding',
                            'overflow',
                            'white-space',
                            'font-size',
                            'line-height'
                        ].forEach((prop) => btn.style.removeProperty(prop));
                        delete btn.dataset.origFontSize;

                        const textNodes = btn.querySelectorAll('p, span');
                        textNodes.forEach((node) => {
                            [
                                'font-weight',
                                'font-size',
                                'line-height',
                                'margin',
                                'padding',
                                'text-align',
                                'color'
                            ].forEach((prop) => node.style.removeProperty(prop));
                        });
                    });

                    if (window.parent.__truckColorResizeHandler) {
                        window.parent.removeEventListener('resize', window.parent.__truckColorResizeHandler);
                        window.parent.__truckColorResizeHandler = null;
                    }
                    window.parent.__truckColorResizeBound = false;
                } catch (e) {}
            })();
            </script>
            """,
            height=0,
            width=0,
        )

    status_color_map = _get_status_badge_colors()
    color_map: dict[str, dict[str, str]] = {}
    muted_set = {int(t) for t in (muted_trucks or set())}
    for truck_num in ordered:
        if int(truck_num) in muted_set:
            color_map[str(int(truck_num))] = {
                "bg": "#6b7280",
                "border": "#4b5563",
                "fg": "#ffffff",
            }
        else:
            bg, border, text_color = _truck_status_colors(truck_num, status_color_map)
            color_map[str(int(truck_num))] = {"bg": bg, "border": border, "fg": text_color}

    if live_button_styling and (color_map or trailing_buttons):
        color_map_json = json.dumps(color_map)
        components.html(
            f"""
            <script>
            (function() {{
                const root = window.parent.document;
                const colorMap = {color_map_json};
                const trailingLabels = new Set({trailing_labels_json});
                const forceTextColor = {force_text_color_json};
                const applyTruckColors = () => {{
                    try {{
                        const buttons = root.querySelectorAll('button[kind="primary"]');
                        buttons.forEach((btn) => {{
                            const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                            if (!/^\d+$/.test(raw)) {{
                                if (trailingLabels.has(raw)) {{
                                    btn.style.setProperty('display', 'flex', 'important');
                                    btn.style.setProperty('align-items', 'center', 'important');
                                    btn.style.setProperty('justify-content', 'center', 'important');
                                    btn.style.setProperty('text-align', 'center', 'important');
                                    btn.style.setProperty('font-weight', '800', 'important');
                                    btn.style.setProperty('width', '100%', 'important');
                                    btn.style.setProperty('min-width', '0', 'important');
                                    btn.style.setProperty('padding', '0', 'important');
                                    btn.style.setProperty('overflow', 'hidden', 'important');
                                    btn.style.setProperty('white-space', 'nowrap', 'important');
                                    if (forceTextColor) {{
                                        btn.style.setProperty('color', forceTextColor, 'important');
                                    }}
                                    const textNodes = btn.querySelectorAll('p, span');
                                    textNodes.forEach((node) => {{
                                        node.style.setProperty('display', 'flex', 'important');
                                        node.style.setProperty('align-items', 'center', 'important');
                                        node.style.setProperty('justify-content', 'center', 'important');
                                        node.style.setProperty('width', '100%', 'important');
                                        node.style.setProperty('text-align', 'center', 'important');
                                        node.style.setProperty('margin', '0', 'important');
                                        node.style.setProperty('padding', '0', 'important');
                                        if (forceTextColor) {{
                                            node.style.setProperty('color', forceTextColor, 'important');
                                        }}
                                    }});
                                }}
                                return;
                            }}
                            const colors = colorMap[raw];
                            if (!colors) return;
                            const fg = forceTextColor || colors.fg || '#000000';
                            btn.style.setProperty('background', colors.bg, 'important');
                            btn.style.setProperty('border', `1px solid ${{colors.border}}`, 'important');
                            btn.style.setProperty('color', fg, 'important');
                            btn.style.setProperty('font-weight', '900', 'important');
                            btn.style.setProperty('display', 'flex', 'important');
                            btn.style.setProperty('align-items', 'center', 'important');
                            btn.style.setProperty('justify-content', 'center', 'important');
                            btn.style.setProperty('text-align', 'center', 'important');
                            btn.style.setProperty('width', '100%', 'important');
                            btn.style.setProperty('min-width', '0', 'important');
                            btn.style.setProperty('padding', '0', 'important');
                            btn.style.setProperty('overflow', 'hidden', 'important');
                            btn.style.setProperty('white-space', 'nowrap', 'important');
                            const charCount = raw.length;
                            const baseSize = parseFloat(btn.dataset.origFontSize || window.getComputedStyle(btn).fontSize || '18');
                            if (!btn.dataset.origFontSize) btn.dataset.origFontSize = String(baseSize);
                            const widthPx = Math.max(18, btn.clientWidth - (charCount >= 3 ? 2 : 6));
                            const heightPx = Math.max(18, btn.clientHeight - 6);
                            const perChar = charCount >= 3 ? 0.5 : 0.62;
                            const widthLimited = widthPx / Math.max(perChar, raw.length * perChar);
                            const heightLimited = heightPx * 0.9;
                            const maxScale = charCount >= 3 ? baseSize * 2.3 : baseSize * 2;
                            const targetPx = Math.min(maxScale, widthLimited, heightLimited);
                            const scaledSize = String(Math.max(10, Math.round(targetPx))) + 'px';
                            btn.style.setProperty('font-size', scaledSize, 'important');
                            btn.style.setProperty('line-height', '1', 'important');
                            const textNodes = btn.querySelectorAll('p, span');
                            textNodes.forEach((node) => {{
                                node.style.setProperty('color', fg, 'important');
                                node.style.setProperty('font-weight', '900', 'important');
                                node.style.setProperty('font-size', scaledSize, 'important');
                                node.style.setProperty('line-height', '1', 'important');
                                node.style.setProperty('margin', '0', 'important');
                                node.style.setProperty('padding', '0', 'important');
                                node.style.setProperty('text-align', 'center', 'important');
                            }});
                        }});
                    }} catch (e) {{}}
                }};
                applyTruckColors();
                setTimeout(applyTruckColors, 50);
                setTimeout(applyTruckColors, 250);
                if (window.parent.__truckColorResizeHandler) {{
                    window.parent.removeEventListener('resize', window.parent.__truckColorResizeHandler);
                }}
                window.parent.__truckColorResizeHandler = () => setTimeout(applyTruckColors, 0);
                window.parent.addEventListener('resize', window.parent.__truckColorResizeHandler);
                window.parent.__truckColorResizeBound = true;
            }})();
            </script>
            """,
            height=0,
            width=0,
        )

    if outlined_trucks is not None:
        outlined_labels_json = json.dumps(sorted({str(int(t)) for t in (outlined_trucks or set())}))
        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    const root = window.parent.document;
                    const outlinedSet = new Set({outlined_labels_json});

                    const applyOutline = () => {{
                        const buttons = root.querySelectorAll('button[kind="primary"]');
                        buttons.forEach((btn) => {{
                            const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                            if (!/^\d+$/.test(raw)) return;
                            if (outlinedSet.has(raw)) {{
                                btn.style.setProperty('box-shadow', '0 0 0 3px rgba(250, 204, 21, 0.98), 0 0 0 5px rgba(15, 23, 42, 0.92)', 'important');
                                btn.style.setProperty('outline', '2px solid rgba(250, 204, 21, 1)', 'important');
                                btn.style.setProperty('outline-offset', '-2px', 'important');
                                btn.dataset.truckSelectedOutline = '1';
                            }} else {{
                                if (btn.dataset.truckSelectedOutline === '1') {{
                                    btn.style.removeProperty('box-shadow');
                                    btn.style.removeProperty('outline');
                                    btn.style.removeProperty('outline-offset');
                                    delete btn.dataset.truckSelectedOutline;
                                }}
                            }}
                        }});
                    }};

                    if (window.parent.__truckOutlineObserver) {{
                        try {{ window.parent.__truckOutlineObserver.disconnect(); }} catch (e) {{}}
                    }}
                    if (window.parent.__truckOutlineResizeHandler) {{
                        try {{
                            window.parent.removeEventListener('resize', window.parent.__truckOutlineResizeHandler);
                            window.parent.removeEventListener('orientationchange', window.parent.__truckOutlineResizeHandler);
                        }} catch (e) {{}}
                    }}

                    const runBurst = () => {{
                        let passes = 0;
                        const burstTick = () => {{
                            applyOutline();
                            passes += 1;
                            if (passes < 12) {{
                                window.parent.requestAnimationFrame(burstTick);
                            }}
                        }};
                        burstTick();
                    }};

                    const resizeHandler = () => setTimeout(applyOutline, 0);
                    window.parent.__truckOutlineResizeHandler = resizeHandler;
                    window.parent.addEventListener('resize', resizeHandler);
                    window.parent.addEventListener('orientationchange', resizeHandler);

                    const observerTarget = root.body || root.documentElement;
                    const observer = new MutationObserver(() => {{
                        applyOutline();
                    }});
                    observer.observe(observerTarget, {{ childList: true, subtree: true }});
                    window.parent.__truckOutlineObserver = observer;

                    applyOutline();
                    setTimeout(applyOutline, 50);
                    setTimeout(applyOutline, 220);
                    setTimeout(applyOutline, 500);
                    setTimeout(applyOutline, 900);
                    runBurst();
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
            width=0,
        )

    if ordered:
        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    const root = window.parent.document;
                    const oosSet = new Set({oos_labels_json});
                    const styleId = 'truck-oos-cross-style';
                    if (!root.getElementById(styleId)) {{
                        const styleEl = root.createElement('style');
                        styleEl.id = styleId;
                        styleEl.textContent = `
                        button[kind="primary"].truck-oos-x {{
                            position: relative !important;
                            overflow: hidden !important;
                        }}
                        button[kind="primary"].truck-oos-x::before,
                        button[kind="primary"].truck-oos-x::after {{
                            content: '' !important;
                            position: absolute !important;
                            left: -10%;
                            top: 50%;
                            width: 120%;
                            height: 3px;
                            border-radius: 999px;
                            background: rgba(220, 38, 38, 0.95);
                            box-shadow: 0 0 3px rgba(255,255,255,0.65);
                            pointer-events: none !important;
                            z-index: 9 !important;
                            transform-origin: center !important;
                        }}
                        button[kind="primary"].truck-oos-x::before {{
                            transform: translateY(-50%) rotate(33deg) !important;
                        }}
                        button[kind="primary"].truck-oos-x::after {{
                            transform: translateY(-50%) rotate(-33deg) !important;
                        }}
                        button[kind="primary"].truck-oos-x p,
                        button[kind="primary"].truck-oos-x span {{
                            position: relative !important;
                            z-index: 1 !important;
                        }}`;
                        root.head.appendChild(styleEl);
                    }}

                    const applyOosCross = () => {{
                        const buttons = root.querySelectorAll('button[kind="primary"]');
                        buttons.forEach((btn) => {{
                            const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                            if (!/^\d+$/.test(raw)) {{
                                btn.classList.remove('truck-oos-x');
                                return;
                            }}
                            if (oosSet.has(raw)) {{
                                btn.classList.add('truck-oos-x');
                            }} else {{
                                btn.classList.remove('truck-oos-x');
                            }}
                        }});
                    }};

                    applyOosCross();
                    setTimeout(applyOosCross, 50);
                    setTimeout(applyOosCross, 250);
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
            width=0,
        )

    if flash_trucks is not None:
        flash_labels_json = json.dumps(sorted({str(int(t)) for t in (flash_trucks or set())}))
        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    const root = window.parent.document;
                    const flashSet = new Set({flash_labels_json});
                    const styleId = 'truck-flash-pulse-style';
                    if (!root.getElementById(styleId)) {{
                        const styleEl = root.createElement('style');
                        styleEl.id = styleId;
                        styleEl.textContent = `@keyframes truckFlashPulse {{
                            0%, 100% {{
                                opacity: 1;
                                box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.55), 0 0 14px rgba(251, 191, 36, 0.45);
                            }}
                            50% {{
                                opacity: 1;
                                box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.95), 0 0 26px rgba(251, 191, 36, 0.95);
                            }}
                        }}
                        @-webkit-keyframes truckFlashPulse {{
                            0%, 100% {{
                                opacity: 1;
                                box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.55), 0 0 14px rgba(251, 191, 36, 0.45);
                            }}
                            50% {{
                                opacity: 1;
                                box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.95), 0 0 26px rgba(251, 191, 36, 0.95);
                            }}
                        }}`;
                        root.head.appendChild(styleEl);
                    }}

                    const buttons = root.querySelectorAll('button[kind="primary"]');
                    buttons.forEach((btn) => {{
                        const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                        if (!/^\d+$/.test(raw)) return;
                        if (flashSet.has(raw)) {{
                            btn.style.setProperty('visibility', 'visible', 'important');
                            btn.style.setProperty('opacity', '1', 'important');
                            btn.style.setProperty('position', 'relative', 'important');
                            btn.style.setProperty('z-index', '1', 'important');
                            btn.style.setProperty('transform', 'translateZ(0)', 'important');
                            btn.style.setProperty('backface-visibility', 'hidden', 'important');
                            btn.style.setProperty('-webkit-backface-visibility', 'hidden', 'important');
                            btn.style.setProperty('animation', 'truckFlashPulse 1s ease-in-out infinite', 'important');
                            btn.style.setProperty('-webkit-animation', 'truckFlashPulse 1s ease-in-out infinite', 'important');
                            btn.dataset.truckFlash = '1';
                        }} else if (btn.dataset.truckFlash === '1') {{
                            btn.style.removeProperty('animation');
                            btn.style.removeProperty('-webkit-animation');
                            btn.style.removeProperty('box-shadow');
                            btn.style.removeProperty('transform');
                            btn.style.removeProperty('backface-visibility');
                            btn.style.removeProperty('-webkit-backface-visibility');
                            btn.style.removeProperty('position');
                            btn.style.removeProperty('z-index');
                            delete btn.dataset.truckFlash;
                        }}
                    }});
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
            width=0,
        )

    button_entries: list[tuple[str, int | str, bool]] = [(str(int(t)), int(t), True) for t in ordered]

    cols_per_row = _truck_grid_columns(default_cols)
    if len(trailing_buttons) > 1 and cols_per_row > 1:
        remainder = len(button_entries) % cols_per_row
        if remainder == cols_per_row - 1:
            button_entries.append(("", f"__spacer_{key_prefix}_{len(button_entries)}", False))

    for trailing_label, trailing_value in trailing_buttons:
        button_entries.append((str(trailing_label), str(trailing_value), False))

    for start in range(0, len(button_entries), cols_per_row):
        row_vals = button_entries[start : start + cols_per_row]
        row_cols = st.columns(cols_per_row)
        for idx, entry in enumerate(row_vals):
            label, value, _is_numeric = entry
            with row_cols[idx]:
                if not str(label).strip():
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    continue
                if st.button(label, key=f"{key_prefix}_{value}", use_container_width=True, type="primary"):
                    if _is_numeric:
                        return int(value)
                    return str(value)
    _force_mobile_button_grid([label for (label, _, _) in button_entries if str(label).strip()], mobile_cols=2, primary_only=True)
    return None


def _add_truck_to_fleet(truck: int) -> tuple[bool, str]:
    t = int(truck)
    if t in FLEET:
        return False, f"Truck {t} already exists in fleet."

    extras = list(st.session_state.get("extra_fleet") or [])
    try:
        extras = [int(x) for x in extras]
    except Exception:
        pass
    extras.append(t)
    st.session_state["extra_fleet"] = sorted(set(extras))

    try:
        FLEET[:] = sorted(set(FLEET) | {t})
    except Exception:
        pass

    save_fleet_file(FLEET)
    _mark_and_save()
    return True, f"Truck {t} added to fleet."


def _render_add_truck_to_fleet_form(number_key: str, button_key: str) -> int | None:
    st.write("### Add truck to fleet")
    try:
        suggested = max(FLEET) + 1 if FLEET else FLEET_MAX + 1
    except Exception:
        suggested = FLEET_MAX + 1

    new_truck = st.number_input(
        "Truck number to add",
        min_value=1,
        max_value=9999,
        value=int(suggested),
        step=1,
        key=number_key,
    )
    if st.button("Add truck to fleet", key=button_key):
        t = int(new_truck)
        ok, message = _add_truck_to_fleet(t)
        if ok:
            st.success(message)
            return t
        st.warning(message)
    return None


def _apply_truck_status_change(
    truck: int,
    status_label: str,
    shop_load_on: str = "",
    emit_shop_return_notice: bool = True,
):
    t = int(truck)
    was_shop = t in st.session_state.shop_set
    prev_status = current_status_label(t)

    st.session_state.cleaned_set.discard(t)
    st.session_state.loaded_set.discard(t)
    st.session_state.inprog_set.discard(t)
    st.session_state.shop_set.discard(t)
    st.session_state.off_set.discard(t)
    st.session_state.spare_set.discard(t)
    st.session_state.special_set.discard(t)

    if status_label == "Dirty":
        pass
    elif status_label == "Unloaded":
        _mark_truck_unloaded_after_batch(t)
    elif status_label == "In Progress":
        start_loading_truck(t)
    elif status_label == "Loaded":
        st.session_state.loaded_set.add(t)
        st.session_state.load_finish_times[t] = time.time()
    elif status_label == "Shop":
        st.session_state.shop_set.add(t)
        load_on = (shop_load_on or "").strip()
        if load_on:
            st.session_state.shop_spares[int(t)] = load_on
            push_shop_notice(f"Sent to shop: #{t} (Load on: {load_on})", kind="shop", notice_type="shop_send", truck=t)
        else:
            st.session_state.shop_spares.pop(int(t), None)
            push_shop_notice(f"Sent to shop: #{t}", kind="shop", notice_type="shop_send", truck=t)
        if not was_shop:
            st.session_state.shop_prev_status[int(t)] = prev_status
    elif status_label == "Out Of Service":
        pending_return = _spares_needing_return_set()
        if t in pending_return:
            pending_return.discard(t)
            st.session_state.spares_needing_return = pending_return
        st.session_state.off_set.add(t)
        st.session_state.cleaned_set.add(t)
    elif status_label == "Spare":
        pending_return = _spares_needing_return_set()
        if t in pending_return:
            pending_return.discard(t)
            st.session_state.spares_needing_return = pending_return
        used_today = _normalize_spare_tracking_set(
            st.session_state.get("used_spares_today") or set()
        )
        used_today.discard(t)
        st.session_state.used_spares_today = used_today
        st.session_state.spare_set.add(t)
    elif status_label == "Special":
        st.session_state.special_set.add(t)

    if was_shop and status_label != "Shop" and emit_shop_return_notice:
        push_shop_notice(f"Returned from shop: #{t} — {status_label}", kind="return")


def _send_truck_to_shop(truck: int, reason: str = "", load_on: str = ""):
    t = int(truck)
    if t not in st.session_state.shop_set:
        st.session_state.shop_prev_status[int(t)] = current_status_label(t)

    st.session_state.shop_set.add(t)
    st.session_state.shop_notes[t] = (reason or "").strip()

    load_on_val = (load_on or "").strip()
    if load_on_val:
        st.session_state.shop_spares[t] = load_on_val
    else:
        st.session_state.shop_spares.pop(t, None)

    msg = f"Sent to shop: #{t}" + (f" — {reason}" if reason else "")
    if load_on_val:
        msg += f" (Load on: {load_on_val})"
    push_shop_notice(msg, kind="shop", notice_type="shop_send", truck=t)
    log_action(f"Truck {t} sent to Shop")

    if st.session_state.get("next_up_truck") == t:
        st.session_state.next_up_truck = None

    st.session_state.cleaned_set.discard(t)
    st.session_state.inprog_set.discard(t)
    st.session_state.loaded_set.discard(t)
    st.session_state.off_set.discard(t)
    st.session_state.spare_set.discard(t)
    st.session_state.special_set.discard(t)
    remove_truck_from_batches(t)


def _return_truck_from_shop(truck: int) -> tuple[bool, str | None]:
    t = int(truck)
    if t not in st.session_state.shop_set:
        return False, None

    st.session_state.shop_set.discard(t)
    st.session_state.shop_notes.pop(t, None)
    st.session_state.shop_spares.pop(t, None)
    prev = st.session_state.shop_prev_status.pop(int(t), None)

    if prev == "Loaded":
        st.session_state.loaded_set.add(t)
    elif prev == "In Progress":
        start_loading_truck(t)
    elif prev == "Out Of Service":
        st.session_state.off_set.add(t)
        st.session_state.cleaned_set.add(t)
    elif prev == "Spare":
        st.session_state.spare_set.add(t)
    elif prev == "Special":
        st.session_state.special_set.add(t)

    prev_label = "Dirty" if prev in ("Unloaded", "Off", "Shop", None) else prev
    push_shop_notice(
        f"Returned from shop: #{t}" + (f" — {prev_label}" if prev_label else ""),
        kind="return",
    )
    log_action(f"Truck {t} returned from Shop")
    return True, prev_label

def render_fleet_management():
    st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Select Truck</div>", unsafe_allow_html=True)
    selected = st.session_state.get("sup_manage_truck")
    if selected is None and st.session_state.get("sup_manage_new_mode"):
        st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Step 2 - Add new truck</div>", unsafe_allow_html=True)
        c_back_new = st.columns(3)[1]
        with c_back_new:
            if st.button("Select Truck", use_container_width=True, key="sup_manage_new_back"):
                st.session_state.sup_manage_new_mode = False
                st.session_state.sup_manage_multi_mode = False
                st.rerun()

        st.divider()
        added_truck = _render_add_truck_to_fleet_form(
            number_key="sup_add_truck_num",
            button_key="sup_add_truck_add",
        )
        if added_truck is not None:
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_multi_mode = False
            st.rerun()
        return

    if selected is None and st.session_state.get("sup_manage_multi_mode"):
        st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Step 2 - Multi Status</div>", unsafe_allow_html=True)
        c_back_multi = st.columns(3)[1]
        with c_back_multi:
            if st.button("Select Truck", use_container_width=True, key="sup_manage_multi_back"):
                st.session_state.sup_manage_multi_mode = False
                st.session_state.sup_manage_multi_selected_trucks = []
                st.rerun()

        selected_trucks_key = "sup_manage_multi_selected_trucks"
        if selected_trucks_key not in st.session_state:
            st.session_state[selected_trucks_key] = []

        multi_selected = sorted({
            int(t) for t in (st.session_state.get(selected_trucks_key) or []) if int(t) in set(FLEET)
        })
        st.session_state[selected_trucks_key] = multi_selected

        s1, s2 = st.columns([1, 1])
        with s1:
            if st.button("Select All", use_container_width=True, key="sup_manage_multi_select_all"):
                st.session_state[selected_trucks_key] = sorted({int(t) for t in FLEET})
                st.rerun()
        with s2:
            if st.button("Clear", use_container_width=True, key="sup_manage_multi_select_clear"):
                st.session_state[selected_trucks_key] = []
                st.rerun()

        clicked_multi_truck = render_numeric_truck_buttons(
            FLEET,
            "sup_manage_multi_pick",
            default_cols=8,
            outlined_trucks=set(st.session_state[selected_trucks_key]),
        )
        if clicked_multi_truck is not None:
            clicked_num = int(clicked_multi_truck)
            currently_selected = set(int(t) for t in (st.session_state.get(selected_trucks_key) or []))
            if clicked_num in currently_selected:
                currently_selected.discard(clicked_num)
            else:
                currently_selected.add(clicked_num)
            st.session_state[selected_trucks_key] = sorted(currently_selected)
            st.rerun()

        target_trucks = sorted(st.session_state[selected_trucks_key])
        st.caption(f"Selected trucks: {len(target_trucks)}")
        selected_statuses = sorted({current_status_label(t) for t in target_trucks})
        if len(selected_statuses) == 0:
            st.caption("Current status for selected: None")
        elif len(selected_statuses) == 1:
            st.caption(f"Current status for selected: {selected_statuses[0]}")
        else:
            st.caption("Current status for selected: Mixed")

        status_options = ["Dirty", "Unloaded", "In Progress", "Loaded", "Shop", "Out Of Service", "Spare"]
        default_status = "Dirty"
        if len(target_trucks) == 1:
            default_status = current_status_label(int(target_trucks[0]))
        default_idx = status_options.index(default_status) if default_status in status_options else 0
        status_sel = st.selectbox("Status", status_options, index=default_idx, key="sup_manage_multi_status_sel")
        shop_load_on = ""
        if status_sel == "Shop":
            shop_load_on = st.text_input("Load On? (optional)", key="sup_manage_multi_status_load_on")

        if st.button("Apply status change", key="sup_manage_multi_apply_status"):
            if not target_trucks:
                st.warning("Select at least one truck.")
            elif status_sel == "In Progress" and len(target_trucks) > 1:
                st.warning("In Progress can only be set for one truck at a time.")
            else:
                for truck_num in target_trucks:
                    _apply_truck_status_change(
                        int(truck_num),
                        status_sel,
                        shop_load_on=shop_load_on,
                    )
                _mark_and_save()
                if len(target_trucks) == 1:
                    st.success(f"Truck {target_trucks[0]} status updated to {status_sel}.")
                else:
                    st.success(f"Updated {len(target_trucks)} trucks to {status_sel}.")
                st.rerun()
        return

    if selected is None:
        flash_trucks = {int(t) for t in (st.session_state.get("inprog_set") or set())}
        clicked_truck = render_numeric_truck_buttons(
            FLEET,
            "sup_manage_pick",
            default_cols=8,
            trailing_button_label="New",
            trailing_button_value="__NEW_TRUCK__",
            additional_buttons=[("Multi", "__MULTI_STATUS__")],
            flash_trucks=flash_trucks,
        )
        if clicked_truck == "__NEW_TRUCK__":
            st.session_state.sup_manage_new_mode = True
            st.session_state.sup_manage_multi_mode = False
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()
        if clicked_truck == "__MULTI_STATUS__":
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_multi_mode = True
            st.session_state.sup_manage_truck = None
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            if "sup_manage_multi_selected_trucks" not in st.session_state:
                st.session_state.sup_manage_multi_selected_trucks = []
            st.rerun()
        if clicked_truck is not None:
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_multi_mode = False
            st.session_state.sup_manage_multi_selected_trucks = []
            st.session_state.sup_manage_truck = int(clicked_truck)
            pref_action = st.session_state.get("sup_manage_pref_action")
            if pref_action:
                st.session_state.sup_manage_action = pref_action
                st.session_state.sup_manage_pref_action = None
            else:
                st.session_state.sup_manage_action = None
            st.rerun()
        return

    sel = int(selected)
    render_truck_status_card(sel, size_variant="fleet")
    c_back = st.columns(3)[1]
    with c_back:
        if st.button("Change Truck", use_container_width=True, key="sup_manage_back"):
            st.session_state.sup_manage_truck = None
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_multi_mode = False
            st.session_state.sup_manage_multi_selected_trucks = []
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()

    action = st.session_state.get("sup_manage_action")
    if not action:
        st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Step 2 - Choose option</div>", unsafe_allow_html=True)
        action_labels = ["Shop", "Status", "Notes", "Ran Special", "Add/Remove"]
        if sel in st.session_state.inprog_set:
            action_labels.append("In Progress")
        cols = st.columns(3)
        for idx, label in enumerate(action_labels):
            col = cols[idx % 3]
            with col:
                if st.button(label, key=f"sup_manage_action_btn_{label}", use_container_width=True):
                    if label == "In Progress":
                        st.session_state.selected_truck = int(sel)
                        st.session_state.active_screen = "IN_PROGRESS"
                        _mark_and_save()
                        st.rerun()
                    st.session_state.sup_manage_action = label
                    st.rerun()
        return

    c_back_action = st.columns(3)[1]
    with c_back_action:
        if st.button("Change Option", use_container_width=True, key="sup_manage_back_action"):
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()
    action_heading = "Status" if action == "Status" else f"Step 3 - {action}"
    st.markdown(f"<div style='text-align:center; font-weight:800; font-size:22px;'>{action_heading}</div>", unsafe_allow_html=True)

    last_dur = st.session_state.load_durations.get(sel)
    inprog_now = (sel in st.session_state.inprog_set)
    live_elapsed = elapsed_seconds() if inprog_now and (next(iter(st.session_state.inprog_set)) == sel) else None
    batch_id = None
    for bi, b in st.session_state.batches.items():
        if sel in b.get("trucks", []):
            batch_id = bi
            break
    st.caption(
        f"Truck {sel} • Batch {batch_id if batch_id else '—'} • Wearers {int(st.session_state.wearers.get(sel, 0) or 0)} • "
        f"Last {seconds_to_mmss(last_dur) if last_dur is not None else 'N/A'} • "
        f"Current {seconds_to_mmss(live_elapsed) if live_elapsed is not None else ('In progress' if inprog_now else 'N/A')}"
    )

    st.divider()
    if action == "Notes":
        st.write("### Notes")
        global_note, daily_note, _ = get_truck_notes(sel)
        note_val_global = st.text_area(
            "General notes (persist across days)",
            value=global_note,
            height=110,
            key="sup_manage_note_global_text",
        )
        note_val_daily = st.text_area(
            "Daily notes (reset each run day)",
            value=daily_note,
            height=110,
            key="sup_manage_note_daily_text",
        )
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("Clear daily", use_container_width=True, key="sup_manage_clear_note_daily"):
                st.session_state.sup_notes_daily.pop(int(sel), None)
                st.success("Daily note cleared.")
                save_state()
        with c2:
            if st.button("Save notes", use_container_width=True, key="sup_manage_save_note"):
                st.session_state.sup_notes_global[int(sel)] = (note_val_global or "").strip()
                st.session_state.sup_notes_daily[int(sel)] = (note_val_daily or "").strip()
                st.success("Notes saved.")
                save_state()
        with c3:
            if st.button("Clear global", use_container_width=True, key="sup_manage_clear_note_global"):
                st.session_state.sup_notes_global.pop(int(sel), None)
                st.success("General note cleared.")
                save_state()

    elif action == "Status":
        st.write("### Status")
        status_feedback_key = "sup_manage_status_feedback"
        pending_status_feedback = st.session_state.pop(status_feedback_key, None)
        if pending_status_feedback:
            st.success(str(pending_status_feedback))
        cur_status = current_status_label(sel)
        st.caption(f"Current status: {cur_status}")

        status_options = ["Dirty", "Unloaded", "In Progress", "Loaded", "Shop", "Out Of Service", "Spare"]
        status_sel = st.selectbox("Status", status_options, index=status_options.index(cur_status) if cur_status in status_options else 0, key="sup_manage_status_sel")
        shop_load_on = ""
        if status_sel == "Shop":
            shop_load_on = st.text_input("Load On? (optional)", key="sup_manage_status_load_on")
        if st.button("Apply status change", key="sup_manage_apply_status"):
            _apply_truck_status_change(
                int(sel),
                status_sel,
                shop_load_on=shop_load_on,
            )
            _mark_and_save()
            st.session_state[status_feedback_key] = f"Truck {int(sel)} status updated to {status_sel}."
            st.session_state.sup_pending_status = None
            st.rerun()

    elif action == "Batch":
        st.write("### Batch assignment")
        w = st.number_input("Wearers", min_value=0, step=1, value=int(st.session_state.get("wearers", {}).get(sel, 0)), key="sup_manage_wearers")
        components.html(
            f"""
            <script>
            (function() {{
                try {{
                    const root = window.parent.document;
                    const inputs = Array.from(root.querySelectorAll('input[aria-label="Wearers"]'));
                    inputs.forEach((el) => {{
                        el.setAttribute('inputmode', 'numeric');
                        el.setAttribute('pattern', '[0-9]*');
                        el.setAttribute('type', 'tel');
                        el.setAttribute('enterkeyhint', 'done');
                    }});
                    const target = inputs.length ? inputs[inputs.length - 1] : null;
                    const isMobile = {str(_is_mobile_client()).lower()};
                    const focusToken = 'fleet-wearers-{int(sel)}';
                    if (isMobile && target && window.parent.__wearersFocusToken !== focusToken) {{
                        const openKeyboard = () => {{
                            try {{
                                target.focus({{ preventScroll: true }});
                                target.click();
                                const len = (target.value || '').length;
                                if (target.setSelectionRange) target.setSelectionRange(len, len);
                            }} catch (e) {{}}
                        }};
                        setTimeout(openKeyboard, 0);
                        setTimeout(openKeyboard, 120);
                        setTimeout(openKeyboard, 320);
                        window.parent.__wearersFocusToken = focusToken;
                    }}
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
            width=0,
        )
        allowed = batch_allowed_ids(w)
        if not allowed:
            st.warning("No batch can accept this truck with that many wearers.")
        else:
            batch_pick = st.selectbox("Assign to batch", options=allowed, key="sup_manage_batch", format_func=lambda i: f"Batch {i} (current {st.session_state.batches[i]['total']}/{BATCH_CAP})")
            if st.button("Assign to batch", key="sup_manage_assign"):
                st.session_state.sup_pending_assign = {"truck": sel, "wearers": int(w), "batch": int(batch_pick)}

            pending_a = st.session_state.get("sup_pending_assign")
            if pending_a and pending_a.get("truck") == sel:
                st.warning(f"Confirm assign Truck {sel} to Batch {pending_a.get('batch')} (wearers: {pending_a.get('wearers')})")
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("Confirm assign", key="sup_manage_confirm_assign"):
                        st.session_state.wearers[sel] = int(pending_a.get("wearers"))
                        batch_assign(sel, int(pending_a.get("wearers")), int(pending_a.get("batch")))
                        post_unload_status = _mark_truck_unloaded_after_batch(sel)
                        _mark_and_save()
                        if post_unload_status == "Spare":
                            st.success(
                                f"Truck {sel} assigned to Batch {pending_a.get('batch')} and returned to Spare."
                            )
                        else:
                            st.success(
                                f"Truck {sel} assigned to Batch {pending_a.get('batch')} and marked Unloaded."
                            )
                        st.session_state.sup_pending_assign = None
                with c2:
                    if st.button("Cancel assign", key="sup_manage_cancel_assign"):
                        st.session_state.sup_pending_assign = None
                        st.rerun()

    elif action == "Shop":
        st.write("### Shop")
        st.markdown(
            """
            <style>
              button[aria-label="Returned"] {
                background: #16a34a !important;
                color: #ffffff !important;
                border: 1px solid #166534 !important;
              }
              button[aria-label="Returned"]:hover {
                background: #15803d !important;
                border-color: #14532d !important;
              }
              button[aria-label="Returned"]:active {
                background: #166534 !important;
                border-color: #14532d !important;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )
        shop_reason = st.text_input("Shop reason (optional)", key="sup_manage_shop_reason")
        shop_spare = st.text_input("Load On? (optional)", key="sup_manage_shop_spare")

        def _send_to_shop(reason: str, spare: str):
            _send_truck_to_shop(sel, reason, spare)
            _mark_and_save()
            st.success(f"Truck {sel} sent to Shop.")
            st.rerun()

        if st.button("Send to Shop", use_container_width=True, key="sup_manage_send_shop"):
            if is_duplicate_notice(sel, "shop_send"):
                st.session_state.shop_send_confirm = {"truck": sel, "reason": shop_reason, "spare": shop_spare}
            else:
                st.session_state.shop_send_confirm = None
                _send_to_shop(shop_reason, shop_spare)

        confirm_send = st.session_state.get("shop_send_confirm")
        if confirm_send and confirm_send.get("truck") == sel:
            st.warning(f"Truck {sel} already has a Shop notice today. Send again?")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm send", use_container_width=True, key="sup_manage_send_shop_confirm"):
                    st.session_state.shop_send_confirm = None
                    _send_to_shop(confirm_send.get("reason", ""), confirm_send.get("spare", ""))
            with c2:
                if st.button("Cancel", use_container_width=True, key="sup_manage_send_shop_cancel"):
                    st.session_state.shop_send_confirm = None
                    st.rerun()
        if st.button("Returned", use_container_width=True, key="sup_manage_returned_shop"):
            ok_returned, _ = _return_truck_from_shop(sel)
            if ok_returned:
                _mark_and_save()
                st.success(f"Truck {sel} returned from Shop.")
                st.rerun()
            else:
                st.warning(f"Truck {sel} is not currently in Shop.")

    elif action == "Ran Special":
        st.write("### Ran Special")
        special_note = st.text_input("Special note (optional)", key="sup_manage_special_note")
        def _mark_ran_special(note: str):
            was_shop = sel in st.session_state.shop_set
            st.session_state.special_set.add(sel)
            if st.session_state.get("next_up_truck") == sel:
                st.session_state.next_up_truck = None
            st.session_state.cleaned_set.discard(sel)
            st.session_state.inprog_set.discard(sel)
            st.session_state.loaded_set.discard(sel)
            st.session_state.off_set.discard(sel)
            st.session_state.spare_set.discard(sel)
            st.session_state.shop_set.discard(sel)
            remove_truck_from_batches(sel)
            msg = f"Ran special: #{sel} needs unload" + (f" — {note}" if note else "")
            push_shop_notice(msg, kind="shop", notice_type="ran_special", truck=sel)
            if was_shop:
                push_shop_notice(f"Returned from shop: #{sel} — Ran Special", kind="return", notice_type="return", truck=sel)
            log_action(f"Truck {sel} ran special (needs unload)")
            _mark_and_save()
            st.success(f"Truck {sel} marked Ran Special (needs unload).")
            st.rerun()

        if st.button("Mark Ran Special", use_container_width=True, key="sup_manage_special"):
            if is_duplicate_notice(sel, "ran_special"):
                st.session_state.ran_special_confirm = {"truck": sel, "note": special_note}
            else:
                st.session_state.ran_special_confirm = None
                _mark_ran_special(special_note)

        confirm_special = st.session_state.get("ran_special_confirm")
        if confirm_special and confirm_special.get("truck") == sel:
            st.warning(f"Truck {sel} already has a Ran Special notice today. Send again?")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm ran special", use_container_width=True, key="sup_manage_special_confirm"):
                    st.session_state.ran_special_confirm = None
                    _mark_ran_special(confirm_special.get("note", ""))
            with c2:
                if st.button("Cancel", use_container_width=True, key="sup_manage_special_cancel"):
                    st.session_state.ran_special_confirm = None
                    st.rerun()

    elif action == "Add/Remove":
        st.write("### Remove truck from fleet")
        if st.button("Remove truck", key="sup_manage_remove"):
            st.session_state.sup_pending_remove = sel
        pending_r = st.session_state.get("sup_pending_remove")
        if pending_r == sel:
            st.warning(f"Confirm removal of Truck {sel} from fleet. This is persistent and will wipe related data for this truck.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm remove", key="sup_manage_confirm_remove"):
                    t = int(sel)
                    removed = list(st.session_state.get("removed_fleet") or [])
                    try:
                        removed = [int(x) for x in removed]
                    except Exception:
                        pass
                    removed.append(t)
                    st.session_state["removed_fleet"] = sorted(set(removed))
                    try:
                        FLEET[:] = sorted(set(FLEET) - {t})
                    except Exception:
                        pass
                    save_fleet_file(FLEET)
                    st.session_state.sup_manage_truck = None
                    st.session_state.sup_manage_new_mode = False
                    st.session_state.sup_manage_action = None
                    st.session_state.sup_manage_pref_action = None
                    st.session_state.sup_pending_remove = None
                    st.session_state.active_screen = "FLEET"
                    _mark_and_save()
                    st.rerun()
            with c2:
                if st.button("Cancel removal", key="sup_manage_cancel_remove"):
                    st.session_state.sup_pending_remove = None
                    st.rerun()

        st.divider()
        added_truck = _render_add_truck_to_fleet_form(
            number_key="sup_add_truck_num",
            button_key="sup_add_truck_add",
        )
        if added_truck is not None:
            st.rerun()


def average_load_time_seconds(trucks: list[int]) -> int | None:
    history = load_duration_history()
    if trucks:
        truck_set = {int(t) for t in trucks}
        durations = [int(r.get("seconds")) for r in history if int(r.get("truck", -1)) in truck_set]
    else:
        durations = [int(r.get("seconds")) for r in history if r.get("seconds") is not None]
    if not durations:
        return None
    return int(sum(durations) / len(durations))


def _normalize_oos_spare_assignments():
    raw = st.session_state.get("oos_spare_assignments") or {}
    normalized: dict[int, int] = {}
    used_spares: set[int] = set()
    eligible_spares = (
        set(st.session_state.get("spare_set", set()))
        | set(st.session_state.get("cleaned_set", set()))
        | set(st.session_state.get("inprog_set", set()))
        | set(st.session_state.get("loaded_set", set()))
    )
    for route_raw, spare_raw in raw.items():
        try:
            route = int(route_raw)
            spare = int(spare_raw)
        except Exception:
            continue
        if route not in st.session_state.off_set:
            continue
        if spare not in eligible_spares:
            continue
        if spare in st.session_state.off_set or spare in st.session_state.shop_set:
            continue
        if spare == route:
            continue
        if spare in used_spares:
            continue
        used_spares.add(spare)
        normalized[route] = spare
    st.session_state.oos_spare_assignments = normalized


def _normalize_spare_tracking_set(raw_value) -> set[int]:
    normalized: set[int] = set()
    if isinstance(raw_value, (set, list, tuple)):
        iterator = raw_value
    else:
        iterator = []
    for raw in iterator:
        try:
            normalized.add(int(raw))
        except Exception:
            continue
    return normalized


def _spares_needing_return_set() -> set[int]:
    normalized = _normalize_spare_tracking_set(
        st.session_state.get("spares_needing_return") or set()
    )
    st.session_state.spares_needing_return = normalized
    return normalized


def _mark_truck_unloaded_after_batch(truck: int) -> str:
    t = int(truck)
    pending_return = _spares_needing_return_set()
    if t in pending_return:
        pending_return.discard(t)
        st.session_state.spares_needing_return = pending_return

        used_today = _normalize_spare_tracking_set(
            st.session_state.get("used_spares_today") or set()
        )
        used_today.discard(t)
        st.session_state.used_spares_today = used_today

        st.session_state.cleaned_set.discard(t)
        st.session_state.spare_set.add(t)
        st.session_state.loaded_set.discard(t)
        st.session_state.inprog_set.discard(t)
        st.session_state.shop_set.discard(t)
        st.session_state.off_set.discard(t)
        st.session_state.special_set.discard(t)
        return "Spare"

    st.session_state.cleaned_set.add(t)
    return "Unloaded"

def normalize_states():
    st.session_state.used_spares_today = _normalize_spare_tracking_set(
        st.session_state.get("used_spares_today") or set()
    )
    pending_return = _spares_needing_return_set()

    # Shop excludes everything else
    st.session_state.cleaned_set -= st.session_state.shop_set
    st.session_state.inprog_set -= st.session_state.shop_set
    st.session_state.loaded_set -= st.session_state.shop_set

    # OOS and Spare trucks are excluded from Unloaded and active workflow states.
    off_oos = set(st.session_state.off_set)
    spare_only = set(st.session_state.get("spare_set", set()))
    blocked = off_oos | spare_only
    st.session_state.cleaned_set -= blocked
    st.session_state.inprog_set -= blocked
    st.session_state.loaded_set -= blocked
    st.session_state.shop_set -= blocked
    st.session_state.special_set -= blocked

    pending_return -= (
        set(st.session_state.get("spare_set", set()))
        | set(st.session_state.get("off_set", set()))
        | set(st.session_state.get("shop_set", set()))
    )
    if pending_return:
        st.session_state.cleaned_set -= pending_return
        st.session_state.inprog_set -= pending_return
        st.session_state.loaded_set -= pending_return
    st.session_state.spares_needing_return = pending_return

    # Trucks that were scheduled Off on the previous day should begin as Unloaded
    # because they did not run that day.
    previous_day_num = _previous_ship_day_num(_current_ship_day_num())
    previous_day_off = off_trucks_for_day(previous_day_num)
    if previous_day_off:
        eligible_previous_day_off = (
            {int(t) for t in previous_day_off}
            - set(st.session_state.off_set)
            - set(st.session_state.get("spare_set", set()))
            - set(st.session_state.shop_set)
            - set(st.session_state.loaded_set)
            - set(st.session_state.inprog_set)
        )
        st.session_state.cleaned_set |= eligible_previous_day_off

    # Clear next-up if it is no longer Unloaded
    next_up = st.session_state.get("next_up_truck")
    if next_up is not None:
        try:
            n = int(next_up)
            if n not in st.session_state.cleaned_set:
                st.session_state.next_up_truck = None
        except Exception:
            st.session_state.next_up_truck = None

    # Loaded excludes cleaned
    st.session_state.cleaned_set -= st.session_state.loaded_set

    # In progress max 1
    if len(st.session_state.inprog_set) > 1:
        keep = min(st.session_state.inprog_set)
        st.session_state.inprog_set = {keep}

    _normalize_oos_spare_assignments()
    assigned_oos_routes = {
        int(route)
        for route in (st.session_state.get("oos_spare_assignments") or {}).keys()
        if route is not None
    }
    if assigned_oos_routes:
        st.session_state.cleaned_set -= assigned_oos_routes
        next_up = st.session_state.get("next_up_truck")
        if next_up is not None:
            try:
                if int(next_up) in assigned_oos_routes:
                    st.session_state.next_up_truck = None
            except Exception:
                st.session_state.next_up_truck = None

    pending_oos_route = st.session_state.get("pending_oos_route")
    if pending_oos_route is not None:
        try:
            route_num = int(pending_oos_route)
        except Exception:
            route_num = None
        off_today = {int(t) for t in off_trucks_for_today()}
        if (
            route_num is None
            or route_num not in st.session_state.off_set
            or route_num in off_today
        ):
            st.session_state.pending_oos_route = None

def current_status_label(truck: int) -> str:
    t = int(truck)
    if t in st.session_state.off_set:
        return "Out Of Service"
    if t in st.session_state.get("spare_set", set()):
        return "Spare"
    if t in st.session_state.shop_set:
        return "Shop"
    if t in st.session_state.inprog_set:
        return "In Progress"
    if t in st.session_state.loaded_set:
        return "Loaded"
    if t in st.session_state.cleaned_set:
        return "Unloaded"
    if t in st.session_state.special_set:
        return "Special"
    return "Dirty"

def elapsed_seconds() -> int:
    if not st.session_state.inprog_start_time:
        return 0
    return int(time.time() - st.session_state.inprog_start_time)

def start_loading_truck(truck: int):
    t = int(truck)
    if t in st.session_state.cleaned_set:
        st.session_state.cleaned_set.discard(t)
    st.session_state.spare_set.discard(t)

    assigned_oos_route = None
    for route_raw, spare_raw in (st.session_state.get("oos_spare_assignments") or {}).items():
        try:
            route_num = int(route_raw)
            spare_num = int(spare_raw)
        except Exception:
            continue
        if spare_num == t and route_num in st.session_state.off_set:
            assigned_oos_route = route_num
            break
    if assigned_oos_route is not None:
        used_spares_today = _normalize_spare_tracking_set(
            st.session_state.get("used_spares_today") or set()
        )
        used_spares_today.add(t)
        st.session_state.used_spares_today = used_spares_today

    st.session_state.inprog_set = {t}
    st.session_state.inprog_start_time = time.time()
    st.session_state.load_start_times[t] = st.session_state.inprog_start_time
    st.session_state.load_finish_times.pop(t, None)
    if st.session_state.get("next_up_truck") == t:
        st.session_state.next_up_truck = None
    log_action(f"Start loading Truck {t}")


def _start_next_up_from_queue_if_possible() -> bool:
    if st.session_state.inprog_set:
        return False

    next_up = st.session_state.get("next_up_truck")
    if next_up is None:
        return False

    try:
        n = int(next_up)
    except Exception:
        st.session_state.next_up_truck = None
        return False

    off_today_set = {int(t) for t in (off_trucks_for_today() or [])}
    if (
        n in off_today_set
        or n in st.session_state.off_set
        or n in st.session_state.loaded_set
        or n in st.session_state.inprog_set
    ):
        return False

    cleaned_set = {int(t) for t in (st.session_state.get("cleaned_set") or set())}
    spare_set = {int(t) for t in (st.session_state.get("spare_set") or set())}
    if n not in cleaned_set and n not in spare_set:
        return False

    if n in st.session_state.shop_set:
        st.session_state.pending_start_truck = n
        st.session_state.active_screen = "STATUS_CLEANED"
        _mark_and_save()
        return True

    start_loading_truck(n)
    st.session_state.active_screen = "IN_PROGRESS"
    _mark_and_save()
    return True

def mark_return_from_shop(truck: int, new_status_label: str):
    t = int(truck)
    if t not in st.session_state.shop_set:
        return
    st.session_state.shop_set.discard(t)
    st.session_state.shop_notes.pop(t, None)
    st.session_state.shop_spares.pop(t, None)
    st.session_state.shop_prev_status.pop(t, None)
    push_shop_notice(f"Returned from shop: #{t} — {new_status_label}", kind="return")
    log_action(f"Truck {t} returned from Shop")

def render_next_up_controls(context_key: str):
    unloaded = sorted(st.session_state.cleaned_set)
    current = st.session_state.get("next_up_truck")
    off_today = off_trucks_for_today()
    off_today_set = {int(t) for t in (off_today or [])}
    st.write("### Next up queue")
    if current:
        st.info(f"Current next up: Truck {int(current)}")
    else:
        st.caption("No next-up truck set.")
    if not unloaded:
        st.caption("No Unloaded trucks available.")
        return
    pick = st.selectbox(
        "Select next up",
        options=unloaded,
        format_func=lambda t: f"Truck {int(t)} — Off" if int(t) in off_today_set else f"Truck {int(t)}",
        key=f"next_up_select_{context_key}",
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Set Next Up", key=f"next_up_set_{context_key}", use_container_width=True):
            if int(pick) in off_today_set:
                st.session_state.next_up_pending = int(pick)
            else:
                st.session_state.next_up_truck = int(pick)
                _mark_and_save()
                st.success(f"Next up set to Truck {int(pick)}.")
                if st.session_state.get("next_up_return_screen"):
                    st.session_state.active_screen = st.session_state.next_up_return_screen
                    st.session_state.next_up_return_screen = None
                st.rerun()
    with c2:
        if st.button("Clear Next Up", key=f"next_up_clear_{context_key}", use_container_width=True):
            st.session_state.next_up_truck = None
            _mark_and_save()
            st.success("Next up cleared.")
            if st.session_state.get("next_up_return_screen"):
                st.session_state.active_screen = st.session_state.next_up_return_screen
                st.session_state.next_up_return_screen = None
            st.rerun()

    pending_next = st.session_state.get("next_up_pending")
    if pending_next is not None:
        st.warning(f"Truck #{int(pending_next)} is off Day {_current_ship_day_num() or '?'} — set as Next Up anyway?")
        c3, c4 = st.columns([1, 1])
        with c3:
            if st.button("Confirm Next Up", key=f"next_up_confirm_{context_key}", use_container_width=True):
                st.session_state.next_up_truck = int(pending_next)
                st.session_state.next_up_pending = None
                _mark_and_save()
                st.success(f"Next up set to Truck {int(pending_next)}.")
                if st.session_state.get("next_up_return_screen"):
                    st.session_state.active_screen = st.session_state.next_up_return_screen
                    st.session_state.next_up_return_screen = None
                st.rerun()
        with c4:
            if st.button("Cancel", key=f"next_up_cancel_{context_key}", use_container_width=True):
                st.session_state.next_up_pending = None
                st.rerun()

    if current:
        off_today = off_trucks_for_today()
        off_day_num = _current_ship_day_num()
        off_day_label = str(int(off_day_num)) if off_day_num else "?"
        if off_today:
            c_off = st.columns([1, 1, 1])[1]
            off_list_text = ", ".join(str(int(t)) for t in sorted(off_today))
            off_button_label = "Show Off"
            with c_off:
                if st.button(off_button_label, key=f"next_up_show_off_{context_key}", use_container_width=True):
                    st.info(f"Off Day {off_day_label}: {off_list_text}")

def remove_truck_from_batches(truck: int):
    t = int(truck)
    for i in range(1, BATCH_COUNT + 1):
        if t in st.session_state.batches[i]["trucks"]:
            st.session_state.batches[i]["trucks"].remove(t)
            st.session_state.batches[i]["total"] -= int(st.session_state.wearers.get(t, 0) or 0)

def apply_off_schedule(day_num: int | None):
    scheduled = sorted(off_trucks_for_day(day_num))
    for t in scheduled:
        if t in st.session_state.shop_set:
            continue
        st.session_state.cleaned_set.add(t)
        st.session_state.inprog_set.discard(t)
        st.session_state.loaded_set.discard(t)
        remove_truck_from_batches(t)


def reset_status_for_new_day(day_num: int | None):
    shorts_disabled = bool(st.session_state.get("shorts_disabled"))
    batching_disabled = bool(st.session_state.get("batching_disabled"))
    shorts_mode = st.session_state.get("shorts_mode") or SHORTS_MODE_BUTTONS
    persistent_spares = {int(t) for t in PERSISTENT_SPARE_TRUCKS}
    preserved_oos = set(st.session_state.get("off_set") or set()) - persistent_spares

    used_spares_prev_day = _normalize_spare_tracking_set(
        st.session_state.get("used_spares_today") or set()
    )
    loaded_or_inprog = (
        set(st.session_state.get("loaded_set") or set())
        | set(st.session_state.get("inprog_set") or set())
    )
    for route_raw, spare_raw in (st.session_state.get("oos_spare_assignments") or {}).items():
        try:
            route_num = int(route_raw)
            spare_num = int(spare_raw)
        except Exception:
            continue
        if route_num in st.session_state.off_set and spare_num in loaded_or_inprog:
            used_spares_prev_day.add(spare_num)

    used_spares_prev_day -= preserved_oos
    preserved_spares = (
        set(st.session_state.get("spare_set") or set())
        | persistent_spares
    ) - used_spares_prev_day

    # Reset all trucks to dirty, preserving shop status, then apply off schedule.
    st.session_state.cleaned_set = set()
    st.session_state.loaded_set = set()
    st.session_state.inprog_set = set()
    st.session_state.special_set = set()
    st.session_state.off_set = preserved_oos
    st.session_state.spare_set = preserved_spares
    st.session_state.used_spares_today = set()
    st.session_state.spares_needing_return = used_spares_prev_day
    st.session_state.off_notes = {}
    st.session_state.oos_spare_assignments = {}

    st.session_state.inprog_start_time = None
    st.session_state.load_start_times = {}
    st.session_state.load_finish_times = {}
    st.session_state.load_durations = {}
    st.session_state.break_start_time = None
    st.session_state.break_used = False

    st.session_state.next_up_truck = None
    st.session_state.next_up_return_screen = None
    st.session_state.pending_oos_route = None
    st.session_state.pending_start_truck = None
    st.session_state.start_blocked = False
    st.session_state.start_blocking_truck = None
    st.session_state.start_attempt_truck = None

    st.session_state.unload_inprog_truck = None
    st.session_state.unload_inprog_start_time = None
    st.session_state.unload_inprog_wearers = 0

    st.session_state.shorts_disabled = shorts_disabled
    st.session_state.batching_disabled = batching_disabled
    st.session_state.shorts_mode = shorts_mode
    st.session_state.sup_notes_daily = {}
    st.session_state.shop_spares = {}
    st.session_state.shorts_button_state = {}

    st.session_state.wearers = {}
    st.session_state.batches = {i: {"trucks": [], "total": 0} for i in range(1, BATCH_COUNT + 1)}

    apply_off_schedule(_previous_ship_day_num(day_num))


def remove_truck_entirely(truck: int):
    """Remove any references to a truck across session state (but does not
    modify persisted extra/removed lists)."""
    t = int(truck)
    # Remove from membership sets
    for s in (
        "cleaned_set",
        "inprog_set",
        "loaded_set",
        "shop_set",
        "off_set",
        "spare_set",
        "special_set",
        "used_spares_today",
        "spares_needing_return",
    ):
        try:
            st.session_state[s].discard(t)
        except Exception:
            pass

    # Remove batch membership
    remove_truck_from_batches(t)

    # Remove wearers and notes
    st.session_state.wearers.pop(t, None)
    assignments = st.session_state.get("oos_spare_assignments") or {}
    cleaned_assignments: dict[int, int] = {}
    for route, spare in assignments.items():
        try:
            route_num = int(route)
            spare_num = int(spare)
        except Exception:
            continue
        if route_num == t or spare_num == t:
            continue
        cleaned_assignments[route_num] = spare_num
    st.session_state.oos_spare_assignments = cleaned_assignments
    st.session_state.shop_notes.pop(t, None)
    st.session_state.shop_spares.pop(t, None)
    st.session_state.shop_prev_status.pop(t, None)
    st.session_state.off_notes.pop(t, None)
    st.session_state.sup_notes_global.pop(t, None)
    st.session_state.sup_notes_daily.pop(t, None)

    # Remove timing data
    st.session_state.load_durations.pop(t, None)
    st.session_state.load_start_times.pop(t, None)
    st.session_state.load_finish_times.pop(t, None)

    # Remove shorts data
    st.session_state.shorts.pop(t, None)
    st.session_state.shorts_initials.pop(t, None)
    st.session_state.shorts_initials_ts.pop(t, None)
    st.session_state.shorts_initials_history.pop(t, None)
    st.session_state.shorts_button_state.pop(t, None)

    if st.session_state.get("next_up_truck") == t:
        st.session_state.next_up_truck = None
    if st.session_state.get("pending_oos_route") == t:
        st.session_state.pending_oos_route = None

def batch_allowed_ids(wearers_needed: int) -> list[int]:
    allowed = []
    for i in range(1, BATCH_COUNT + 1):
        total = st.session_state.batches[i]["total"]
        if total + int(wearers_needed) <= BATCH_CAP:
            allowed.append(i)
    return allowed

def batch_assign(truck: int, wearers: int, batch_id: int):
    t = int(truck)
    w = int(wearers)
    b = int(batch_id)
    remove_truck_from_batches(t)
    st.session_state.batches[b]["trucks"].append(t)
    st.session_state.batches[b]["total"] += w
    log_action(f"Assign Truck {t} to Batch {b} ({w} wearers)")

def ensure_shorts_model(truck: int):
    t = int(truck)
    if t not in st.session_state.shorts:
        st.session_state.shorts[t] = [{"item": "None", "qty": None, "note": ""}]
        return
    rows = st.session_state.shorts.get(t)
    if not rows or not isinstance(rows, list) or len(rows) != 1:
        return
    row = rows[0] if isinstance(rows[0], dict) else {}
    item = str(row.get("item", "")).strip()
    qty = row.get("qty", None)
    note = str(row.get("note", "")).strip()
    has_initials = bool(st.session_state.shorts_initials.get(t)) or bool(st.session_state.shorts_initials_history.get(t))
    if item == "Towels" and (qty == 1 or qty == "1") and not note and not has_initials:
        st.session_state.shorts[t] = [{"item": "None", "qty": None, "note": ""}]

def _default_shorts_button_state() -> dict:
    return {
        "step": "category",
        "category": None,
        "bulk_group": None,
        "item": None,
        "qty": 1,
    }

def _get_shorts_button_state(truck: int) -> dict:
    t = int(truck)
    state = st.session_state.get("shorts_button_state") or {}
    return state.get(t, _default_shorts_button_state())

def _set_shorts_button_state(truck: int, new_state: dict):
    t = int(truck)
    state = st.session_state.get("shorts_button_state") or {}
    state[t] = new_state
    st.session_state.shorts_button_state = state

def _reset_shorts_button_state(truck: int):
    _set_shorts_button_state(truck, _default_shorts_button_state())

def _short_row_has_item(row: dict) -> bool:
    if not isinstance(row, dict):
        return False
    item = str(row.get("item", "")).strip()
    return bool(item and item != "None")

def _shorts_button_add_item(truck: int, label: str, qty: int):
    t = int(truck)
    target_label = str(label or "").strip()
    if not target_label:
        return
    ensure_shorts_model(t)
    rows = list(st.session_state.shorts.get(t, []))
    rows = [r for r in rows if _short_row_has_item(r)]
    existing_note = ""
    deduped_rows = []
    for row in rows:
        item = str(row.get("item", "")).strip()
        if item == target_label:
            note = str(row.get("note", "")).strip()
            if note:
                existing_note = note
            continue
        deduped_rows.append(row)
    deduped_rows.append({"item": target_label, "qty": int(qty), "note": existing_note})
    st.session_state.shorts[t] = deduped_rows

def render_shorts_button_flow(truck: int):
    t = int(truck)
    state = _get_shorts_button_state(t)
    step = state.get("step") or "category"
    category = state.get("category")
    bulk_group = state.get("bulk_group")
    item = state.get("item")

    st.write("### Select Shortages")
    if step == "category":
        cat_entries: list[tuple[str, str]] = [("cat", cat) for cat in SHORTS_BUTTON_MAP.keys()]
        cat_entries.append(("recents", "Recents"))
        cols_per_row = _truck_grid_columns(len(cat_entries))
        for start in range(0, len(cat_entries), cols_per_row):
            row_entries = cat_entries[start : start + cols_per_row]
            row_cols = st.columns(cols_per_row)
            for idx, (entry_type, label) in enumerate(row_entries):
                with row_cols[idx]:
                    if entry_type == "cat":
                        if st.button(label, use_container_width=True, key=f"shorts_cat_{t}_{label}"):
                            next_step = "bulk_group" if label == "Bulk" else "item"
                            _set_shorts_button_state(t, {"step": next_step, "category": label, "bulk_group": None, "item": None, "qty": 1})
                            st.rerun()
                    else:
                        if st.button(label, use_container_width=True, key=f"shorts_cat_{t}_recents"):
                            _set_shorts_button_state(t, {"step": "recents", "category": None, "bulk_group": None, "item": None, "qty": 1})
                            st.rerun()
        _force_mobile_button_grid([label for _, label in cat_entries], mobile_cols=2)

        if st.session_state.get("active_screen") == "IN_PROGRESS":
            components.html(
                """
                <script>
                (function(){
                    try {
                        const root = window.parent.document;
                        const centerRecents = () => {
                            const buttons = root.querySelectorAll('button');
                            buttons.forEach((btn) => {
                                const raw = (btn.innerText || btn.textContent || '').replace(/\u2063/g, '').trim();
                                if (raw !== 'Recents') return;
                                btn.style.setProperty('display', 'flex', 'important');
                                btn.style.setProperty('align-items', 'center', 'important');
                                btn.style.setProperty('justify-content', 'center', 'important');
                                btn.style.setProperty('text-align', 'center', 'important');
                                const nodes = btn.querySelectorAll('p, span');
                                nodes.forEach((node) => {
                                    node.style.setProperty('text-align', 'center', 'important');
                                    node.style.setProperty('margin', '0', 'important');
                                    node.style.setProperty('padding', '0', 'important');
                                    node.style.setProperty('width', '100%', 'important');
                                });
                            });
                        };
                        centerRecents();
                        setTimeout(centerRecents, 50);
                        setTimeout(centerRecents, 200);
                    } catch (e) {}
                })();
                </script>
                """,
                height=0,
                width=0,
            )
        return

    if step == "recents":
        st.caption("Recent shortages for today (most recent first)")
        recent_rows = list(reversed([r for r in st.session_state.shorts.get(t, []) if (r.get("item") or "") != "None" and r.get("item")]))
        if not recent_rows:
            st.info("No shortages recorded yet today.")
        else:
            for idx, r in enumerate(recent_rows):
                label = f"{r.get('item','')}"
                if st.button(label, use_container_width=True, key=f"shorts_recent_{t}_{idx}"):
                    # Try to parse category and bulk_group from label
                    item_label = r.get('item','')
                    qty_val = r.get('qty',1)
                    # If Bulk, try to extract bulk_group
                    if item_label.startswith("Bulk - "):
                        parts = item_label.split(" - ")
                        bulk_group = parts[1] if len(parts) > 2 else None
                        item_name = parts[-1]
                        _set_shorts_button_state(t, {"step": "qty", "category": "Bulk", "bulk_group": bulk_group, "item": item_name, "qty": qty_val})
                    elif " - " in item_label:
                        cat, item_name = item_label.split(" - ", 1)
                        _set_shorts_button_state(t, {"step": "qty", "category": cat, "bulk_group": None, "item": item_name, "qty": qty_val})
                    else:
                        _set_shorts_button_state(t, {"step": "qty", "category": None, "bulk_group": None, "item": item_label, "qty": qty_val})
                    st.rerun()
        if st.button("Back to categories", use_container_width=True, key=f"shorts_recents_back_{t}"):
            _reset_shorts_button_state(t)
            st.rerun()
        return

    if step == "bulk_group":
        st.caption("Bulk group")
        groups = list(SHORTS_BUTTON_MAP.get("Bulk", {}).keys())
        cols_per_row = _truck_grid_columns(3)
        for start in range(0, len(groups), cols_per_row):
            row_groups = groups[start : start + cols_per_row]
            row_cols = st.columns(cols_per_row)
            for idx, group in enumerate(row_groups):
                with row_cols[idx]:
                    if st.button(group, use_container_width=True, key=f"shorts_bulk_{t}_{group}"):
                        _set_shorts_button_state(t, {"step": "item", "category": "Bulk", "bulk_group": group, "item": None, "qty": 1})
                        st.rerun()
        _force_mobile_button_grid(groups, mobile_cols=2)
        if st.button("Back to categories", use_container_width=True, key=f"shorts_bulk_back_{t}"):
            _reset_shorts_button_state(t)
            st.rerun()
        return

    if step == "item":
        if category == "Bulk":
            items = list(SHORTS_BUTTON_MAP.get("Bulk", {}).get(bulk_group or "", []))
            title = f"Bulk — {bulk_group}" if bulk_group else "Bulk"
        else:
            items = list(SHORTS_BUTTON_MAP.get(category or "", []))
            title = category or "Items"
        st.caption(f"Select item — {title}")
        cols_per_row = _truck_grid_columns(3)
        for start in range(0, len(items), cols_per_row):
            row_items = items[start : start + cols_per_row]
            row_cols = st.columns(cols_per_row)
            for idx, it in enumerate(row_items):
                with row_cols[idx]:
                    if st.button(it, use_container_width=True, key=f"shorts_item_{t}_{it}"):
                        state = {"step": "qty", "category": category, "bulk_group": bulk_group, "item": it, "qty": 1}
                        _set_shorts_button_state(t, state)
                        st.rerun()
        _force_mobile_button_grid(items, mobile_cols=2)
        if st.button("Back", use_container_width=True, key=f"shorts_item_back_{t}"):
            prev_step = "bulk_group" if category == "Bulk" else "category"
            _set_shorts_button_state(t, {"step": prev_step, "category": category if prev_step != "category" else None, "bulk_group": bulk_group if prev_step == "bulk_group" else None, "item": None, "qty": 1})
            st.rerun()
        return

    if step == "qty":
        label = item or ""
        st.caption(f"Select amount for {label}")
        # Load quick-select values for this item
        quick_amounts = QUICK_AMOUNTS_MAP.get(label, [1, 2, 5, 10])
        if not isinstance(quick_amounts, list) or not quick_amounts:
            quick_amounts = [1, 2, 5, 10]
        quick_cols_per_row = _truck_grid_columns(min(len(quick_amounts), 4))
        # Quick-select buttons directly add the item
        for start in range(0, len(quick_amounts), quick_cols_per_row):
            row_amounts = quick_amounts[start : start + quick_cols_per_row]
            row_cols = st.columns(quick_cols_per_row)
            for idx, val in enumerate(row_amounts):
                with row_cols[idx]:
                    if st.button(str(val), key=f"shorts_quick_amt_{t}_{label}_{val}"):
                        if category == "Bulk":
                            full_label = f"Bulk - {bulk_group} - {label}" if bulk_group else f"Bulk - {label}"
                        elif category:
                            full_label = f"{category} - {label}"
                        else:
                            full_label = f"{label}"
                        _shorts_button_add_item(t, full_label, val)
                        _reset_shorts_button_state(t)
                        st.rerun()
                _force_mobile_button_grid([str(v) for v in quick_amounts], mobile_cols=2)

        custom_qty = st.number_input(
            "Custom amount",
            min_value=1,
            step=1,
            value=int(state.get("qty") or 1),
            key=f"shorts_custom_qty_{t}_{label}",
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Add custom amount", use_container_width=True, key=f"shorts_custom_add_{t}"):
                if category == "Bulk":
                    full_label = f"Bulk - {bulk_group} - {label}" if bulk_group else f"Bulk - {label}"
                elif category:
                    full_label = f"{category} - {label}"
                else:
                    full_label = f"{label}"
                _shorts_button_add_item(t, full_label, int(custom_qty))
                _reset_shorts_button_state(t)
                st.rerun()
        with c2:
            if st.button("Back", use_container_width=True, key=f"shorts_qty_back_{t}"):
                _set_shorts_button_state(t, {"step": "item", "category": category, "bulk_group": bulk_group, "item": None, "qty": 1})
                st.rerun()
        return

    if step in ("more", "done"):
        _reset_shorts_button_state(t)
        st.rerun()
        return

def go(screen: str):
    st.session_state.active_screen = screen
    _push_nav_history(force=True)
    st.rerun()


def _mark_and_save():
    normalize_states()
    save_state()


def render_page_heading(title: str):
    safe_title = html.escape(str(title or ""))
    st.markdown(
        (
            "<div style='text-align:center; font-size:30px; font-weight:800; "
            "line-height:1.1; margin:-0.24rem 0 0.44rem 0;'>"
            f"{safe_title}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def badge_label(label: str) -> str:
    return label


def sidebar_badge_link(label: str, value: str | int, color: str, target_page: str):
    # Sidebar status button (default theme styling).
    display_text = f"{badge_label(label)}  •  {value}"

    with st.sidebar.container():
        if st.button(display_text, key=f"sidebar_badge_{target_page}", use_container_width=True):
            st.session_state.active_screen = target_page
            _mark_and_save()
            st.rerun()


def _apply_sidebar_badge_dots(dot_map: dict[str, str]):
    normalized_map = {
        str(label): _normalize_hex_color(color, "#6b7280")
        for label, color in (dot_map or {}).items()
        if str(label).strip()
    }
    if not normalized_map:
        return

    dot_map_json = json.dumps(normalized_map)
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const root = window.parent.document;
                const styleId = 'sidebar-status-dot-style';
                if (!root.getElementById(styleId)) {{
                    const styleEl = root.createElement('style');
                    styleEl.id = styleId;
                    styleEl.textContent = `
                    section[data-testid="stSidebar"] .stButton > button.status-dot-badge {{
                        display: flex !important;
                        align-items: center !important;
                        justify-content: flex-start !important;
                        gap: 0.5rem !important;
                    }}
                    section[data-testid="stSidebar"] .stButton > button.status-dot-badge::before {{
                        content: '';
                        width: 0.72rem;
                        height: 0.72rem;
                        border-radius: 9999px;
                        flex: 0 0 0.72rem;
                        background: var(--status-dot-color, #6b7280);
                        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.3);
                    }}`;
                    root.head.appendChild(styleEl);
                }}

                const normalize = (s) => (s || '').replace(/\u2063/g, '').replace(/\s+/g, ' ').trim();
                const rawMap = {dot_map_json};
                const colorMap = new Map(Object.entries(rawMap).map(([k, v]) => [normalize(k), v]));

                const applyBadgeDots = () => {{
                    const sidebar = root.querySelector('section[data-testid="stSidebar"]');
                    if (!sidebar) return false;
                    let appliedAny = false;
                    const buttons = sidebar.querySelectorAll('.stButton > button');
                    buttons.forEach((btn) => {{
                        const raw = normalize(btn.innerText || btn.textContent || '');
                        const dotColor = colorMap.get(raw);
                        if (!dotColor) return;
                        btn.classList.add('status-dot-badge');
                        btn.style.setProperty('--status-dot-color', dotColor);
                        appliedAny = true;
                    }});
                    return appliedAny;
                }};

                applyBadgeDots();

                let attempts = 0;
                const maxAttempts = 24;
                const retryApply = () => {{
                    attempts += 1;
                    applyBadgeDots();
                    if (attempts >= maxAttempts) return;
                    setTimeout(retryApply, 50);
                }};
                setTimeout(retryApply, 0);

                const sidebar = root.querySelector('section[data-testid="stSidebar"]');
                if (!sidebar) return;
                if (root.__statusDotObserverAll) {{
                    try {{ root.__statusDotObserverAll.disconnect(); }} catch (e) {{}}
                }}
                const observer = new MutationObserver(() => {{
                    applyBadgeDots();
                }});
                observer.observe(sidebar, {{ childList: true, subtree: true }});
                root.__statusDotObserverAll = observer;
                setTimeout(() => {{
                    try {{ observer.disconnect(); }} catch (e) {{}}
                    if (root.__statusDotObserverAll === observer) delete root.__statusDotObserverAll;
                }}, 2500);
            }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

def render_truck_bubbles(
    trucks: list[int],
    from_page: str | None = None,
    muted_trucks: set[int] | None = None,
):
    # This is what you asked for: bubbled lists INSIDE each status link page
    if not trucks:
        st.write("None")
        return

    clicked_truck = render_numeric_truck_buttons(
        trucks,
        f"bubble_{from_page}",
        default_cols=8,
        muted_trucks=muted_trucks,
    )
    if clicked_truck is not None:
        t = int(clicked_truck)
        if from_page == "UNLOAD":
            st.session_state["unload_truck_select"] = int(t)
            st.session_state.active_screen = "BATCH"
            _set_query_params(page="BATCH", pick=str(int(t)))
        elif from_page == "STATUS_CLEANED":
            st.session_state.selected_truck = int(t)
            if int(t) in st.session_state.off_set:
                st.session_state.pending_oos_route = int(t)
                st.session_state.pending_start_truck = None
            else:
                st.session_state.pending_start_truck = int(t)
                st.session_state.pending_oos_route = None
        elif from_page == "STATUS_LOADED":
            st.session_state.selected_truck = int(t)
            st.session_state.active_screen = "STATUS_LOADED"
        elif from_page == "STATUS_DIRTY":
            st.session_state["unload_truck_select"] = int(t)
            st.session_state.active_screen = "BATCH"
            _set_query_params(page="BATCH", pick=str(int(t)))
        elif from_page == "STATUS_SHOP":
            if bool(st.session_state.get("status_shop_return_mode", False)):
                ok_returned, _ = _return_truck_from_shop(int(t))
                st.session_state.status_shop_feedback = {
                    "ok": bool(ok_returned),
                    "truck": int(t),
                }
                _mark_and_save()
                st.rerun()
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_multi_mode = False
            st.session_state.sup_manage_multi_selected_trucks = []
            st.session_state.sup_manage_truck = int(t)
            st.session_state.sup_manage_action = "Shop"
            st.session_state.sup_manage_pref_action = None
            st.session_state.active_screen = "FLEET"
        else:
            st.session_state.selected_truck = int(t)
            st.session_state.active_screen = "TRUCK"
        _mark_and_save()
        st.rerun()

def generate_pdf_bytes() -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    x = 40
    y = h - 40
    line = 14

    def draw(text: str, bold=False):
        nonlocal y
        if y < 60:
            c.showPage()
            y = h - 40
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if not bold else 11)
        c.drawString(x, y, text[:140])
        y -= line

    run = st.session_state.run_date
    ship_dates = st.session_state.ship_dates
    loaded_trucks = sorted(st.session_state.loaded_set)

    draw("Truck Readiness — End of Day", bold=True)
    draw(f"Run date: {fmt_long_date(run) if run else 'N/A'}")

    if ship_dates:
        ship_str = ", ".join(
            [f"{d.isoformat()} (Day {ship_day_number(d)})" if ship_day_number(d) else d.isoformat() for d in ship_dates]
        )
        draw(f"Ship dates: {ship_str}")
    else:
        draw("Ship dates: N/A")

    draw(" ")

    durations = [
        st.session_state.load_durations.get(t)
        for t in loaded_trucks
        if st.session_state.load_durations.get(t) is not None
    ]
    if durations:
        avg = int(sum(durations) / len(durations))
        draw(f"Average load time (today): {seconds_to_mmss(avg)}", bold=True)
    else:
        draw("Average load time (today): N/A", bold=True)

    draw(" ")
    draw("Loaded trucks:", bold=True)

    if not loaded_trucks:
        draw("None")
    else:
        draw(", ".join(str(t) for t in loaded_trucks))

        # Build shortages matrix: items on rows, trucks on columns
        item_set = set()
        qty_map = {}
        for t in loaded_trucks:
            items = st.session_state.shorts.get(t, [])
            for it in items:
                name = (it.get("item") or "").strip()
                if not name:
                    continue
                item_set.add(name)
                qty = int(it.get("qty") or 0)
                qty_map.setdefault(t, {})[name] = qty_map.setdefault(t, {}).get(name, 0) + qty

        items = sorted(item_set)
        if not items:
            draw("No shortages recorded.")
        else:
            def draw_centered_text(tx, ty, tw, th, text, font="Helvetica", size=9):
                c.setFont(font, size)
                text = str(text)
                text_width = c.stringWidth(text, font, size)
                x_pos = tx + max(2, (tw - text_width) / 2)
                y_pos = ty - th + (th - size) / 2 + 2
                c.drawString(x_pos, y_pos, text)

            def draw_left_text(tx, ty, tw, th, text, font="Helvetica", size=9):
                c.setFont(font, size)
                text = str(text)
                max_chars = max(6, int(tw / 6))
                if len(text) > max_chars:
                    text = text[: max_chars - 3] + "..."
                y_pos = ty - th + (th - size) / 2 + 2
                c.drawString(tx + 2, y_pos, text)

            def draw_table(trucks_chunk, start_y):
                nonlocal y
                margin = 40
                max_width = w - (margin * 2)
                item_w = 140
                col_w = max(32, int((max_width - item_w) / max(1, len(trucks_chunk))))
                header_h = 18
                row_h = 16
                needed = header_h + row_h * len(items) + 8
                if start_y - needed < 60:
                    c.showPage()
                    start_y = h - 40

                y = start_y
                c.setLineWidth(0.5)
                # Header row
                c.rect(margin, y - header_h, item_w, header_h)
                draw_centered_text(margin, y, item_w, header_h, "Item", font="Helvetica-Bold", size=9)
                for idx, t in enumerate(trucks_chunk):
                    cx = margin + item_w + (idx * col_w)
                    c.rect(cx, y - header_h, col_w, header_h)
                    draw_centered_text(cx, y, col_w, header_h, f"{t}", font="Helvetica-Bold", size=9)
                y -= header_h

                # Item rows
                for item in items:
                    c.rect(margin, y - row_h, item_w, row_h)
                    draw_left_text(margin, y, item_w, row_h, item)
                    for idx, t in enumerate(trucks_chunk):
                        cx = margin + item_w + (idx * col_w)
                        c.rect(cx, y - row_h, col_w, row_h)
                        qty = qty_map.get(t, {}).get(item, "")
                        draw_centered_text(cx, y, col_w, row_h, qty if qty else "")
                    y -= row_h
                return y - 10

            margin = 40
            max_width = w - (margin * 2)
            item_w = 140
            max_cols = max(1, int((max_width - item_w) / 32))
            y -= 8
            for i in range(0, len(loaded_trucks), max_cols):
                chunk = loaded_trucks[i : i + max_cols]
                y = draw_table(chunk, y)

    c.save()
    return buf.getvalue()


def generate_batch_cards_pdf_bytes() -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    x = 40
    y = h - 40
    line = 14

    def draw_line(text: str, bold=False):
        nonlocal y
        if y < 60:
            c.showPage()
            y = h - 40
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if not bold else 12)
        c.drawString(x, y, text[:140])
        y -= line

    def wrap_text(text: str, max_chars: int = 90) -> list[str]:
        words = (text or "").split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= max_chars:
                current = f"{current} {w}".strip()
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines or [""]

    run = st.session_state.run_date or date.today()
    draw_line("Unload Batch Cards", bold=True)
    draw_line(f"Run date: {fmt_long_date(run)}")
    draw_line(" ")

    for i in range(1, BATCH_COUNT + 1):
        batch = st.session_state.batches.get(i, {"trucks": [], "total": 0})
        trucks = batch.get("trucks", [])
        total = int(batch.get("total", 0) or 0)
        draw_line(f"Batch {i}", bold=True)
        if trucks:
            parts = []
            for t in trucks:
                wearers = int(st.session_state.wearers.get(int(t), 0) or 0)
                parts.append(f"{int(t)} ({wearers})")
            truck_text = "Trucks (wearers): " + ", ".join(parts)
        else:
            truck_text = "Trucks (wearers): None"
        for line_text in wrap_text(truck_text):
            draw_line(line_text)
        draw_line(f"Total wearers: {total} / {BATCH_CAP}")
        draw_line(" ")

    c.save()
    return buf.getvalue()


def generate_end_of_day_pdf_bytes() -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    x = 40
    y = h - 40
    line = 14

    def draw(text: str, bold=False):
        nonlocal y
        if y < 60:
            c.showPage()
            y = h - 40
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if not bold else 11)
        c.drawString(x, y, text[:140])
        y -= line

    def wrap_text(text: str, max_chars: int = 90) -> list[str]:
        words = (text or "").split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= max_chars:
                current = f"{current} {w}".strip()
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines or [""]

    run = st.session_state.run_date
    ship_dates = st.session_state.ship_dates
    loaded_trucks = sorted(st.session_state.loaded_set)

    draw("End of Day Summary", bold=True)
    draw(f"Run date: {fmt_long_date(run) if run else 'N/A'}")

    if ship_dates:
        ship_str = ", ".join(
            [f"{d.isoformat()} (Day {ship_day_number(d)})" if ship_day_number(d) else d.isoformat() for d in ship_dates]
        )
        draw(f"Ship dates: {ship_str}")
    else:
        draw("Ship dates: N/A")

    draw(" ")
    durations = [
        st.session_state.load_durations.get(t)
        for t in loaded_trucks
        if st.session_state.load_durations.get(t) is not None
    ]
    if durations:
        avg = int(sum(durations) / len(durations))
        draw(f"Average load time (today): {seconds_to_mmss(avg)}", bold=True)
    else:
        draw("Average load time (today): N/A", bold=True)

    draw(" ")
    draw("Loaded trucks:", bold=True)
    if not loaded_trucks:
        draw("None")
    else:
        draw(", ".join(str(t) for t in loaded_trucks))

        # Build shortages matrix: items on rows, trucks on columns
        item_set = set()
        qty_map = {}
        for t in loaded_trucks:
            items = st.session_state.shorts.get(t, [])
            for it in items:
                name = (it.get("item") or "").strip()
                if not name or name == "None":
                    continue
                item_set.add(name)
                qty = int(it.get("qty") or 0)
                qty_map.setdefault(t, {})[name] = qty_map.setdefault(t, {}).get(name, 0) + qty

        items = sorted(item_set)
        if not items:
            draw("No shortages recorded.")
        else:
            def draw_centered_text(tx, ty, tw, th, text, font="Helvetica", size=9):
                c.setFont(font, size)
                text = str(text)
                text_width = c.stringWidth(text, font, size)
                x_pos = tx + max(2, (tw - text_width) / 2)
                y_pos = ty - th + (th - size) / 2 + 2
                c.drawString(x_pos, y_pos, text)

            def draw_left_text(tx, ty, tw, th, text, font="Helvetica", size=9):
                c.setFont(font, size)
                text = str(text)
                max_chars = max(6, int(tw / 6))
                if len(text) > max_chars:
                    text = text[: max_chars - 3] + "..."
                y_pos = ty - th + (th - size) / 2 + 2
                c.drawString(tx + 2, y_pos, text)

            def draw_table(trucks_chunk, start_y):
                nonlocal y
                margin = 40
                max_width = w - (margin * 2)
                item_w = 140
                col_w = max(32, int((max_width - item_w) / max(1, len(trucks_chunk))))
                header_h = 18
                row_h = 16
                needed = header_h + row_h * len(items) + 8
                if start_y - needed < 60:
                    c.showPage()
                    start_y = h - 40

                y = start_y
                c.setLineWidth(0.5)
                c.rect(margin, y - header_h, item_w, header_h)
                draw_centered_text(margin, y, item_w, header_h, "Item", font="Helvetica-Bold", size=9)
                for idx, t in enumerate(trucks_chunk):
                    cx = margin + item_w + (idx * col_w)
                    c.rect(cx, y - header_h, col_w, header_h)
                    draw_centered_text(cx, y, col_w, header_h, f"{t}", font="Helvetica-Bold", size=9)
                y -= header_h

                for item in items:
                    c.rect(margin, y - row_h, item_w, row_h)
                    draw_left_text(margin, y, item_w, row_h, item)
                    for idx, t in enumerate(trucks_chunk):
                        cx = margin + item_w + (idx * col_w)
                        c.rect(cx, y - row_h, col_w, row_h)
                        qty = qty_map.get(t, {}).get(item, "")
                        draw_centered_text(cx, y, col_w, row_h, qty if qty else "")
                    y -= row_h
                return y - 10

            margin = 40
            max_width = w - (margin * 2)
            item_w = 140
            max_cols = max(1, int((max_width - item_w) / 32))
            y -= 8
            for i in range(0, len(loaded_trucks), max_cols):
                chunk = loaded_trucks[i : i + max_cols]
                y = draw_table(chunk, y)

    draw(" ")
    draw("Batch cards:", bold=True)
    for i in range(1, BATCH_COUNT + 1):
        batch = st.session_state.batches.get(i, {"trucks": [], "total": 0})
        trucks = batch.get("trucks", [])
        total = int(batch.get("total", 0) or 0)
        draw(f"Batch {i}", bold=True)
        if trucks:
            parts = []
            for t in trucks:
                wearers = int(st.session_state.wearers.get(int(t), 0) or 0)
                parts.append(f"{int(t)} ({wearers})")
            truck_text = "Trucks (wearers): " + ", ".join(parts)
        else:
            truck_text = "Trucks (wearers): None"
        for line_text in wrap_text(truck_text):
            draw(line_text)
        draw(f"Total wearers: {total} / {BATCH_CAP}")
        draw(" ")

    c.save()
    return buf.getvalue()

def save_shorts_stop_timer(truck: int, initials: str, edited_rows: list[dict]) -> bool:
    t = int(truck)
    ini = (initials or "").strip()
    if not ini:
        st.error("Initials are required to save shortages.")
        return False

    st.session_state.shorts_initials[t] = ini
    st.session_state.shorts[t] = edited_rows

    # record initials timestamp and history
    try:
        tzinfo = _get_tzinfo()
        now_ts = datetime.now(tzinfo).isoformat() if tzinfo else datetime.now().isoformat()
    except Exception:
        now_ts = datetime.now().isoformat()
    st.session_state.shorts_initials_ts[t] = now_ts
    hist = st.session_state.shorts_initials_history.get(t, [])
    hist.append({"initials": ini, "ts": now_ts})
    st.session_state.shorts_initials_history[t] = hist

    if st.session_state.inprog_start_time:
        sec = elapsed_seconds()
        st.session_state.load_durations[t] = sec
        append_load_duration(t, sec)
        st.session_state.inprog_start_time = None
        st.session_state.inprog_set.clear()
        st.session_state.loaded_set.add(t)
        # record finish time for this truck
        st.session_state.load_finish_times[t] = time.time()

    item_count = sum(1 for r in edited_rows if (r.get("item") or "").strip())
    log_action(f"Shorts saved for Truck {t} ({item_count} items)")

    save_state()
    return True


def _navigate_after_shorts_save(saved_truck: int):
    t = int(saved_truck)
    auto_for = st.session_state.get("shorts_autostart_next_up_for_truck")
    should_auto_start_next = False
    try:
        should_auto_start_next = auto_for is not None and int(auto_for) == t
    except Exception:
        should_auto_start_next = False

    st.session_state.shorts_autostart_next_up_for_truck = None

    next_up = st.session_state.get("next_up_truck")
    if should_auto_start_next and next_up is not None and not st.session_state.inprog_set:
        st.session_state.shorts_pending_next_up_confirm_for_truck = t
    else:
        st.session_state.shorts_pending_next_up_confirm_for_truck = None

    if next_up is not None and not st.session_state.inprog_set:
        st.session_state.selected_truck = t
        st.session_state.active_screen = "STATUS_LOADED"
    else:
        st.session_state.active_screen = "LOAD"
    st.rerun()

# ==========================================================
# Setup-first enforcement
# ==========================================================

# Require setup only when no run config exists.
if (not st.session_state.setup_done) or (st.session_state.get("run_date") is None):
    st.session_state.active_screen = "SETUP"

normalize_states()

# Restore in-progress start time from persisted per-truck start times
if st.session_state.inprog_set and not st.session_state.inprog_start_time:
    try:
        active_truck = next(iter(st.session_state.inprog_set))
        restored = st.session_state.load_start_times.get(active_truck)
        if restored:
            st.session_state.inprog_start_time = restored
        else:
            st.session_state.inprog_start_time = time.time()
    except Exception:
        pass

# ==========================================================
# Derived lists
# ==========================================================
oos_spare_set = set(st.session_state.off_set) | set(st.session_state.get("spare_set", set()))
off_today = off_trucks_for_today()
dirty_trucks = sorted(
    set(FLEET)
    - st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - oos_spare_set
)
cleaned_effective_set = (
    set(st.session_state.cleaned_set)
) - set(st.session_state.get("spare_set", set())) - set(st.session_state.loaded_set) - set(st.session_state.inprog_set) - set(st.session_state.shop_set)
cleaned_list = sorted(cleaned_effective_set)
cleaned_ready_to_load = sorted(set(cleaned_list) - {int(t) for t in off_today})

active_oos_assignments: dict[int, int] = {}
for route_raw, spare_raw in (st.session_state.get("oos_spare_assignments") or {}).items():
    try:
        route_num = int(route_raw)
        spare_num = int(spare_raw)
    except Exception:
        continue
    if route_num in st.session_state.off_set:
        active_oos_assignments[route_num] = spare_num

oos_routes_needing_spare = sorted(
    set(st.session_state.off_set)
    - {int(t) for t in off_today}
    - set(active_oos_assignments.keys())
)
status_cleaned_trucks = sorted(set(cleaned_ready_to_load) | set(oos_routes_needing_spare))

loaded_list = sorted(st.session_state.loaded_set)
shop_list = sorted(st.session_state.shop_set)
inprog_truck = next(iter(st.session_state.inprog_set)) if st.session_state.inprog_set else None

if st.session_state.get("start_blocked"):
    try:
        blocking_truck = int(st.session_state.get("start_blocking_truck"))
    except Exception:
        blocking_truck = None
    if (blocking_truck is None) or (blocking_truck not in st.session_state.inprog_set):
        st.session_state.start_blocked = False
        st.session_state.start_blocking_truck = None
        st.session_state.start_attempt_truck = None

true_available = sorted(
    st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - oos_spare_set
    - off_today
)

render_rollover_prompt_if_needed()

is_first_client_page_load = not bool(st.session_state.get("_nav_session_initialized"))
if is_first_client_page_load:
    st.session_state._nav_session_initialized = True

# ==========================================================
# Apply query-param navigation (status bar links)
# ==========================================================
qp = _get_query_params()
raw_page = qp.get("page", None)
requested = raw_page[0] if isinstance(raw_page, list) else raw_page
if requested == "MANAGEMENT":
    requested = "SUPERVISOR"
# Notice collapse/expand handled via Streamlit buttons (no URL params).
raw_nav = qp.get("nav", None)
nav_val = None
if raw_nav is not None:
    try:
        nav_val = int(raw_nav[0] if isinstance(raw_nav, list) else raw_nav)
    except Exception:
        nav_val = None
nav_from_url = False
if nav_val is not None and nav_val != st.session_state.get("last_nav_seen"):
    st.session_state.last_nav_seen = nav_val
    nav_from_url = True

# If a truck param is provided in the URL, store it for specific views only
raw_truck = qp.get("truck", None)
if raw_truck and requested in ("TRUCK", "SHORTS", "IN_PROGRESS", "STATUS_LOADED"):
    try:
        tval = int(raw_truck[0] if isinstance(raw_truck, list) else raw_truck)
        st.session_state.selected_truck = tval
    except Exception:
        st.session_state.selected_truck = None

# If a pick param is present (used by UNLOAD page bubbles), set the unload selectbox
raw_pick = qp.get("pick", None)
if raw_pick:
    try:
        pval = int(raw_pick[0] if isinstance(raw_pick, list) else raw_pick)
        st.session_state["unload_truck_select"] = pval
    except Exception:
        pass

# remember where we came from (status page) to return back
raw_from = qp.get("from", None)
if raw_from:
    st.session_state._from_page = raw_from[0] if isinstance(raw_from, list) else raw_from

# If a start param is present and we're navigating to IN_PROGRESS, begin the in-progress timer
raw_start = qp.get("start", None)
if raw_start and requested == "IN_PROGRESS" and raw_truck:
    try:
        sv = int(raw_truck[0] if isinstance(raw_truck, list) else raw_truck)
        # Only start if nothing else is in progress
        if not st.session_state.inprog_set:
            if sv in st.session_state.shop_set:
                st.session_state.pending_start_truck = sv
                st.session_state.active_screen = "STATUS_CLEANED"
                _mark_and_save()
            else:
                start_loading_truck(sv)
                _mark_and_save()
                st.session_state.selected_truck = sv
        else:
            # record that a start was attempted but blocked by an existing in-progress truck
            st.session_state.start_blocked = True
            st.session_state.start_blocking_truck = next(iter(st.session_state.inprog_set))
            st.session_state.start_attempt_truck = sv
            # return user to Cleaned status to show the popup
            st.session_state.active_screen = "STATUS_CLEANED"
    except Exception:
        pass

# Restore Fleet sub-state from URL (so refresh stays on the same Fleet sub-page).
raw_fleet_mode = qp.get("fleet_mode", None)
fleet_mode_val = (raw_fleet_mode[0] if isinstance(raw_fleet_mode, list) else raw_fleet_mode)
fleet_mode_val = str(fleet_mode_val).strip().lower() if fleet_mode_val is not None else ""

raw_fleet_truck = qp.get("fleet_truck", None)
fleet_truck_val = None
if raw_fleet_truck is not None:
    try:
        fleet_truck_val = int(raw_fleet_truck[0] if isinstance(raw_fleet_truck, list) else raw_fleet_truck)
    except Exception:
        fleet_truck_val = None

raw_fleet_action = qp.get("fleet_action", None)
fleet_action_val = raw_fleet_action[0] if isinstance(raw_fleet_action, list) else raw_fleet_action
fleet_action_val = str(fleet_action_val).strip() if fleet_action_val not in (None, "") else None

if requested == "FLEET" and (is_first_client_page_load or nav_from_url):
    if fleet_mode_val == "new":
        st.session_state.sup_manage_new_mode = True
        st.session_state.sup_manage_multi_mode = False
        st.session_state.sup_manage_truck = None
        st.session_state.sup_manage_action = None
        st.session_state.sup_manage_multi_selected_trucks = []
    elif fleet_mode_val == "multi":
        st.session_state.sup_manage_new_mode = False
        st.session_state.sup_manage_multi_mode = True
        st.session_state.sup_manage_truck = None
        st.session_state.sup_manage_action = None
        if "sup_manage_multi_selected_trucks" not in st.session_state:
            st.session_state.sup_manage_multi_selected_trucks = []
    else:
        st.session_state.sup_manage_new_mode = False
        st.session_state.sup_manage_multi_mode = False
        st.session_state.sup_manage_multi_selected_trucks = []
        st.session_state.sup_manage_truck = int(fleet_truck_val) if fleet_truck_val is not None else None
        if fleet_truck_val is None:
            st.session_state.sup_manage_action = None
        else:
            st.session_state.sup_manage_action = fleet_action_val

valid_pages = {
    "SETUP", "UNLOAD", "LOAD", "SHORTS", "FLEET",
    "STATUS_DIRTY", "STATUS_CLEANED", "STATUS_LOADED", "STATUS_SHOP", "STATUS_OOS", "STATUS_OFF",
    "TRUCK", "SUPERVISOR", "MANAGEMENT",
    "IN_PROGRESS",
    "BREAK",
    "BATCH",
}
prev_requested = st.session_state.get("last_requested_page")
if requested in valid_pages:
    # Only honor a query-param page change when it changes from the last URL
    # value (prevents stale URLs from overriding in-app navigation).
    if (
        is_first_client_page_load
        or requested != prev_requested
        or requested == st.session_state.active_screen
    ):
        st.session_state.active_screen = requested
st.session_state.last_requested_page = requested

# When browser Back/Forward changes the URL, force a rerun to refresh the page.
if nav_from_url and requested in valid_pages and requested != st.session_state.active_screen:
    st.session_state.active_screen = requested
    st.rerun()

# If the URL is stale (user navigated via UI), keep the URL page in sync.
if (
    (not is_first_client_page_load)
    and requested
    and requested == prev_requested
    and requested != st.session_state.active_screen
):
    _set_query_params(page=_page_param_for_screen(st.session_state.active_screen))

# If a pick param was provided, open the BATCH page for that truck
if st.session_state.active_screen == "BATCH" and st.session_state.get("unload_truck_select") is not None:
    try:
        p = int(st.session_state.get("unload_truck_select"))
        st.session_state.unload_inprog_truck = p
        st.session_state.unload_inprog_start_time = None
        st.session_state.unload_inprog_wearers = 0
        st.session_state.next_up_truck = p
    except Exception:
        pass

# If we're navigating away, clear the batch pick so it doesn't lock navigation
if st.session_state.active_screen != "BATCH":
    st.session_state["unload_truck_select"] = None
    st.session_state.unload_inprog_truck = None
    st.session_state.unload_inprog_start_time = None
    st.session_state.unload_inprog_wearers = 0

# If navigating to SHORTS with a truck param, open that truck's short sheet
if st.session_state.active_screen == "SHORTS" and raw_truck:
    try:
        st.session_state.shorts_truck = int(raw_truck[0] if isinstance(raw_truck, list) else raw_truck)
        ensure_shorts_model(st.session_state.shorts_truck)
    except Exception:
        pass

# Keep the URL in sync with in-app navigation so browser Back stays in-app.
if nav_val is not None:
    st.session_state.nav_seq = max(int(st.session_state.get("nav_seq") or 0), nav_val)
if nav_from_url:
    st.session_state.last_screen_for_history = st.session_state.active_screen
else:
    _push_nav_history()

# Force a full refresh on browser Back/Forward so the page updates with the URL.
components.html(
    """
    <script>
    (function(){
        const root = window.parent;
        if (!root || root.__truckNavListener) return;
        root.__truckNavListener = true;
        root.addEventListener('popstate', function(){
            try { root.location.reload(); } catch(e) {}
        });
    })();
    </script>
    """,
    height=0,
    width=0,
)

# Global notice for management Shop assignments
render_shop_notice()

# ==========================================================
# SIDEBAR
# ==========================================================
st.sidebar.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)
if st.session_state.setup_done:
    run = st.session_state.run_date
    ship = st.session_state.ship_dates[0] if st.session_state.ship_dates else None
    ship_day = ship_day_number(ship) if ship else None
    current_day = fmt_long_date(run) if run else "N/A"
    if ship_day:
        load_day = f"Day {ship_day}"
    elif ship:
        load_day = "(weekend)"
    else:
        load_day = "N/A"
    unload_day_num = _previous_ship_day_num(ship_day_number(run) if run else None)
    if unload_day_num:
        unload_day = f"Day {unload_day_num}"
    else:
        unload_day = "N/A"
    st.sidebar.markdown(
        f"<div style='margin:0; padding:0; font-size:0.9rem; line-height:1.15; text-align:center;'>"
        f"  <div style='margin:0; padding:0; font-weight:800;'>Workday</div>"
        f"  <div style='margin:0 0 6px 0; padding:0;'>{current_day}</div>"
        f"  <div style='margin:0; padding:0; font-weight:800;'>Load</div>"
        f"  <div style='margin:0; padding:0;'>{load_day}</div>"
        f"  <div style='margin:6px 0 0 0; padding:0; font-weight:800;'>Unloads</div>"
        f"  <div style='margin:0; padding:0;'>{unload_day}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# Current time
tz_key = _normalized_tz_key()
with st.sidebar:
    components.html(
        (
            "<div style='margin:6px 0 0 0; padding:0; text-align:center;'>"
            "  <div id='sidebar-clock' style='font-size:30px; font-weight:900; color:#93c5fd;'></div>"
            "</div>"
            "<script>"
            "(function(){"
            f"  const tz = '{tz_key}';"
            "  const el = document.getElementById('sidebar-clock');"
            "  if (!el) return;"
            "  const fmt = new Intl.DateTimeFormat('en-US', {"
            "    timeZone: tz,"
            "    hour: 'numeric',"
            "    minute: '2-digit',"
            "    second: '2-digit',"
            "    hour12: true"
            "  });"
            "  const tick = () => {"
            "    const now = new Date();"
            "    el.textContent = fmt.format(now);"
            "  };"
            "  tick();"
            "  setInterval(tick, 1000);"
            "})();"
            "</script>"
        ),
        height=38,
    )

# Unload at top, Load middle
if st.sidebar.button("Unload", use_container_width=True):
    st.session_state.active_screen = "UNLOAD"
    _mark_and_save()
    st.rerun()

if st.sidebar.button("Load", use_container_width=True):
    st.session_state.active_screen = "LOAD"
    _mark_and_save()
    st.rerun()

if st.session_state.active_screen == "LOAD":
    st.markdown("<h2 style='text-align:center; margin:0 0 8px 0;'>Load Management</h2>", unsafe_allow_html=True)

if st.sidebar.button("Fleet", use_container_width=True):
    st.session_state.sup_manage_truck = None
    st.session_state.sup_manage_new_mode = False
    st.session_state.sup_manage_action = None
    st.session_state.sup_manage_pref_action = None
    st.session_state.active_screen = "FLEET"
    _mark_and_save()
    st.rerun()

break_start = st.session_state.get("break_start_time")
if break_start:
    break_remaining = (st.session_state.break_duration or 0) - (time.time() - break_start)
    if break_remaining > 0:
        if st.sidebar.button("On Break", use_container_width=True):
            st.session_state.active_screen = "BREAK"
            _mark_and_save()
            st.rerun()

# ---- REVERTED STATUS BAR LOOK (single card) ----
st.sidebar.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='text-align:center; font-weight:800; font-size:1.2rem; margin:0 0 4px 0;'>Live status</div>", unsafe_allow_html=True)
shop_list_no_oos = [t for t in shop_list if t not in oos_spare_set]
dirty_trucks_no_oos = [t for t in dirty_trucks if t not in oos_spare_set]
spare_set_now = set(st.session_state.get("spare_set", set()))
cleaned_list_no_oos = [t for t in status_cleaned_trucks if t not in spare_set_now]
loaded_list_no_oos = [t for t in loaded_list if t not in oos_spare_set]
inprog_truck_no_oos = inprog_truck if inprog_truck not in oos_spare_set else None

badge_colors = _get_status_badge_colors()

sidebar_badge_link("Dirty", len(dirty_trucks_no_oos), badge_colors["dirty"], "UNLOAD")
sidebar_badge_link("Shop", len(shop_list_no_oos), badge_colors["shop"], "STATUS_SHOP")
sidebar_badge_link("In Progress", str(inprog_truck_no_oos) if inprog_truck_no_oos is not None else "None", badge_colors["in_progress"], "IN_PROGRESS")
sidebar_badge_link("Unloaded", len(cleaned_list_no_oos), badge_colors["unloaded"], "STATUS_CLEANED")
sidebar_badge_link("Loaded", len(loaded_list_no_oos), badge_colors["loaded"], "STATUS_LOADED")

# OFF and OOS/SPARE badges
sidebar_badge_link("OFF", len(sorted(list(off_today))), badge_colors["off"], "STATUS_OFF")
sidebar_badge_link("OOS/SPARE", len(sorted(list(oos_spare_set))), badge_colors["oos_spare"], "STATUS_OOS")
_apply_sidebar_badge_dots(
    {
        f"{badge_label('Dirty')}  •  {len(dirty_trucks_no_oos)}": badge_colors["dirty"],
        f"{badge_label('Shop')}  •  {len(shop_list_no_oos)}": badge_colors["shop"],
        f"{badge_label('In Progress')}  •  {str(inprog_truck_no_oos) if inprog_truck_no_oos is not None else 'None'}": badge_colors["in_progress"],
        f"{badge_label('Unloaded')}  •  {len(cleaned_list_no_oos)}": badge_colors["unloaded"],
        f"{badge_label('Loaded')}  •  {len(loaded_list_no_oos)}": badge_colors["loaded"],
        f"{badge_label('OFF')}  •  {len(sorted(list(off_today)))}": badge_colors["off"],
        f"{badge_label('OOS/SPARE')}  •  {len(sorted(list(oos_spare_set)))}": badge_colors["oos_spare"],
    }
)

if st.session_state.setup_done:
    st.sidebar.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
    st.sidebar.subheader("Short sheet")
    if loaded_list:
        pick = st.sidebar.selectbox("Short Sheet", options=loaded_list, key="sidebar_shorts_pick")
        if st.sidebar.button("Open selected short sheet", use_container_width=True):
            sel = int(pick)
            st.session_state.shorts_truck = sel
            ensure_shorts_model(sel)
            save_state()
            # update URL to include truck so SHORTS opens the correct sheet
            _set_query_params(page="SHORTS", truck=str(sel))
            st.rerun()
    else:
        st.sidebar.caption("No loaded trucks yet today.")

    # Management button at bottom of nav
    st.sidebar.divider()
    if st.sidebar.button("Management", use_container_width=True):
        st.session_state.active_screen = "SUPERVISOR"
        _mark_and_save()
        st.rerun()
    version_label = str(_APP_VERSION).strip()
    if version_label and not version_label.lower().startswith("v"):
        version_label = f"v{version_label}"
    st.sidebar.markdown(
        f"<div style='font-size:0.72rem; opacity:0.65; text-align:center; margin-top:4px;'>Version {html.escape(version_label)}</div>",
        unsafe_allow_html=True,
    )
# ==========================================================
# PAGES
# ==========================================================

# --------------------------
# Status pages (NOW bubbled)
# --------------------------
if st.session_state.active_screen.startswith("STATUS_"):
    title = st.session_state.active_screen.replace("STATUS_", "").replace("_", " ").title()
    # Title normalization
    if title == "Shop":
        title = "Shop"
    if title == "Cleaned":
        title = "Unloaded"
    if st.session_state.active_screen == "STATUS_OOS":
        title = "OOS/SPARE"
    if st.session_state.active_screen == "STATUS_OFF":
        title = "OFF"
    render_page_heading(title)


    mapping = {
        "STATUS_DIRTY": dirty_trucks,
        "STATUS_CLEANED": status_cleaned_trucks,
        "STATUS_LOADED": loaded_list,
        "STATUS_SHOP": shop_list,
        "STATUS_OFF": sorted(list(off_today)),
        "STATUS_OOS": sorted(list(oos_spare_set)),
    }
    trucks = mapping.get(st.session_state.active_screen, [])

    if st.session_state.active_screen == "STATUS_SHOP":
        return_mode_key = "status_shop_return_mode"
        if return_mode_key not in st.session_state:
            st.session_state[return_mode_key] = False

        status_shop_feedback = st.session_state.pop("status_shop_feedback", None)
        if isinstance(status_shop_feedback, dict):
            try:
                feedback_truck = int(status_shop_feedback.get("truck"))
            except Exception:
                feedback_truck = None
            if status_shop_feedback.get("ok") and feedback_truck is not None:
                st.success(f"Truck {feedback_truck} returned from Shop.")
            elif feedback_truck is not None:
                st.warning(f"Truck {feedback_truck} is not currently in Shop.")

        c_send, c_return = st.columns([1, 1])
        with c_send:
            if st.button("Send", use_container_width=True, key="status_shop_send_btn"):
                st.session_state.sup_manage_truck = None
                st.session_state.sup_manage_new_mode = False
                st.session_state.sup_manage_multi_mode = False
                st.session_state.sup_manage_multi_selected_trucks = []
                st.session_state.sup_manage_action = None
                st.session_state.sup_manage_pref_action = "Shop"
                st.session_state.active_screen = "FLEET"
                _mark_and_save()
                st.rerun()
        with c_return:
            return_mode_on = bool(st.session_state.get(return_mode_key, False))
            return_label = "Return: ON" if return_mode_on else "Return"
            if st.button(return_label, use_container_width=True, key="status_shop_return_btn"):
                st.session_state[return_mode_key] = not return_mode_on
                st.rerun()

        if bool(st.session_state.get(return_mode_key, False)):
            st.caption("Return mode is ON. Tap a truck below to return it from Shop.")
        else:
            st.caption("Showing trucks currently in Shop.")

    if st.session_state.active_screen == "STATUS_OOS":
        oos_only = sorted(list(st.session_state.off_set))
        spare_only = sorted(list(st.session_state.get("spare_set", set())))
        st.write("### Spare")
        render_truck_bubbles(spare_only, st.session_state.active_screen)
        st.write("### Out Of Service")
        add_mode_key = "status_oos_add_mode"
        oos_add_options = sorted({int(t) for t in FLEET} - {int(t) for t in oos_only})

        oos_click = render_numeric_truck_buttons(
            oos_only,
            "status_oos_grid",
            default_cols=8,
            trailing_button_label="Add" if oos_add_options else None,
            trailing_button_value="__ADD_OOS__" if oos_add_options else None,
        )
        if oos_click == "__ADD_OOS__":
            st.session_state[add_mode_key] = not bool(st.session_state.get(add_mode_key, False))
            st.rerun()
        elif oos_click is not None:
            st.session_state.selected_truck = int(oos_click)
            st.session_state.active_screen = "TRUCK"
            _mark_and_save()
            st.rerun()

        if st.session_state.get(add_mode_key, False):
            if oos_add_options:
                st.caption("Select truck to add to Out Of Service.")
                add_pick = render_numeric_truck_buttons(
                    oos_add_options,
                    "status_oos_add_pick_grid",
                    default_cols=8,
                )
                if add_pick is not None:
                    t = int(add_pick)
                    _apply_truck_status_change(
                        t,
                        "Out Of Service",
                        emit_shop_return_notice=False,
                    )
                    st.session_state[add_mode_key] = False
                    _mark_and_save()
                    st.success(f"Truck {t} added to Out Of Service.")
                    st.rerun()
            else:
                st.session_state[add_mode_key] = False
        elif not oos_add_options:
            st.caption("All fleet trucks are already Out Of Service.")
    elif st.session_state.active_screen == "STATUS_CLEANED":
        render_truck_bubbles(trucks, st.session_state.active_screen)
    elif st.session_state.active_screen == "STATUS_SHOP":
        render_truck_bubbles(trucks, st.session_state.active_screen)
    else:
        # Always show the truck bubbles list
        render_truck_bubbles(trucks, st.session_state.active_screen)

    if st.session_state.active_screen == "STATUS_SHOP" and trucks:
        spare_lines = []
        for t in trucks:
            spare = (st.session_state.shop_spares.get(int(t)) or "").strip()
            if spare:
                spare_lines.append(f"Truck #{int(t)} needs Loaded On #{spare}")
        if spare_lines:
            st.info(" • ".join(spare_lines))

    # If we're on the Loaded status and a specific truck was selected, show an overview below
    if st.session_state.active_screen == "STATUS_LOADED" and st.session_state.selected_truck:
        t = st.session_state.selected_truck
        if t not in st.session_state.loaded_set:
            st.session_state.selected_truck = None
        else:
            st.subheader(f"Loaded — Truck {t}")
            # batch
            batch_id = None
            for bi, b in st.session_state.batches.items():
                if t in b.get("trucks", []):
                    batch_id = bi
                    break
            start_ts = st.session_state.load_start_times.get(t)
            finish_ts = st.session_state.load_finish_times.get(t)
            dur = st.session_state.load_durations.get(t)
            c0, c1, c2, c3 = st.columns([1,1,1,1])
            with c0:
                st.metric("Batch", batch_id if batch_id else "—")
            with c1:
                st.metric("Wearers", int(st.session_state.wearers.get(t,0) or 0))
            with c2:
                st.metric("Load duration", seconds_to_mmss(dur) if dur is not None else "N/A")
            with c3:
                st.write("")
                # placeholder for symmetry
            if start_ts:
                st.write(f"Started: {_format_ts(start_ts)}")
            if finish_ts:
                st.write(f"Finished: {_format_ts(finish_ts)}")
            next_up = st.session_state.get("next_up_truck")
            confirm_for_truck = st.session_state.get("shorts_pending_next_up_confirm_for_truck")
            show_ready_to_begin_prompt = False
            try:
                show_ready_to_begin_prompt = (
                    confirm_for_truck is not None and int(confirm_for_truck) == int(t)
                )
            except Exception:
                show_ready_to_begin_prompt = False

            if confirm_for_truck is not None and not show_ready_to_begin_prompt:
                st.session_state.shorts_pending_next_up_confirm_for_truck = None

            if next_up is not None and not st.session_state.inprog_set:
                st.markdown(
                    (
                        "<div style='text-align:center; margin:8px 0 6px 0;'>"
                        "  <div style='font-size:12px; letter-spacing:0.16em; text-transform:uppercase; opacity:0.75;'>Next Up</div>"
                        f"  <div style='font-size:46px; font-weight:900; line-height:1.0; color:#3b82f6;'>#{int(next_up)}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                if show_ready_to_begin_prompt:
                    st.warning(f"Ready to begin loading?  Next Up: Truck {int(next_up)}")
                else:
                    st.warning(f"Next up: Truck {int(next_up)}. Start loading now?")
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                with c2:
                    if st.button("Yes, start next up", use_container_width=True, key="start_next_up_status_loaded"):
                        st.session_state.shorts_pending_next_up_confirm_for_truck = None
                        if _start_next_up_from_queue_if_possible():
                            st.rerun()
                        st.warning("Next Up truck is no longer available to start.")
                with c3:
                    if st.button("Change Next Up", use_container_width=True, key="change_next_up_status_loaded"):
                        st.session_state.shorts_pending_next_up_confirm_for_truck = None
                        st.session_state.active_screen = "LOAD"
                        _mark_and_save()
                        st.rerun()
                c5, c6, c7 = st.columns([1, 2, 1])
                with c6:
                    if not st.session_state.get("break_used"):
                        if st.button("Start Break", use_container_width=True, key="start_break_status_loaded"):
                            st.session_state.shorts_pending_next_up_confirm_for_truck = None
                            st.session_state.break_start_time = time.time()
                            st.session_state.break_used = True
                            st.session_state.active_screen = "BREAK"
                            _mark_and_save()
                            st.rerun()
            elif show_ready_to_begin_prompt:
                st.session_state.shorts_pending_next_up_confirm_for_truck = None
            st.divider()
            if st.button("Open short sheet", use_container_width=True):
                st.session_state.shorts_pending_next_up_confirm_for_truck = None
                st.session_state.shorts_truck = t
                ensure_shorts_model(t)
                st.session_state.active_screen = "SHORTS"
                _mark_and_save()
                st.rerun()
            if st.button("Go to Unloaded trucks", use_container_width=True):
                st.session_state.shorts_pending_next_up_confirm_for_truck = None
                st.session_state.active_screen = "STATUS_CLEANED"
                _mark_and_save()
                st.rerun()

    if st.session_state.active_screen == "STATUS_CLEANED" and st.session_state.get("pending_oos_route") is not None:
        try:
            route_to_cover = int(st.session_state.get("pending_oos_route"))
        except Exception:
            route_to_cover = None

        if (
            route_to_cover is None
            or route_to_cover not in st.session_state.off_set
            or route_to_cover in off_today
        ):
            st.session_state.pending_oos_route = None
        else:
            assignments_raw = st.session_state.get("oos_spare_assignments") or {}
            assignments: dict[int, int] = {}
            for route_raw, spare_raw in assignments_raw.items():
                try:
                    assignments[int(route_raw)] = int(spare_raw)
                except Exception:
                    continue

            existing_spare = assignments.get(route_to_cover)
            used_spares = {int(spare_num) for route_num, spare_num in assignments.items() if int(route_num) != route_to_cover}
            spare_pool = {int(t) for t in (st.session_state.get("spare_set") or set())}
            spare_candidates = sorted(
                spare_pool
                - set(st.session_state.shop_set)
                - set(st.session_state.off_set)
                - set(st.session_state.inprog_set)
                - set(st.session_state.loaded_set)
                - used_spares
            )
            if existing_spare is not None and existing_spare in spare_pool:
                spare_candidates = sorted(set(spare_candidates) | {int(existing_spare)})

            st.warning(f"Truck {route_to_cover} is OOS. Which spare should load route {route_to_cover}?")
            if spare_candidates:
                spare_pick = render_numeric_truck_buttons(
                    spare_candidates,
                    f"status_cleaned_pick_spare_{int(route_to_cover)}",
                    default_cols=8,
                )
                if spare_pick is not None:
                    chosen_spare = int(spare_pick)
                    prior_spare = assignments.get(route_to_cover)
                    if prior_spare is not None:
                        try:
                            prior_spare = int(prior_spare)
                        except Exception:
                            prior_spare = None

                    if prior_spare is not None and prior_spare != chosen_spare:
                        if (
                            prior_spare not in st.session_state.off_set
                            and prior_spare not in st.session_state.shop_set
                            and prior_spare not in st.session_state.inprog_set
                            and prior_spare not in st.session_state.loaded_set
                        ):
                            st.session_state.cleaned_set.discard(prior_spare)
                            st.session_state.spare_set.add(prior_spare)

                    st.session_state.spare_set.discard(chosen_spare)
                    pending_return = _spares_needing_return_set()
                    if chosen_spare in pending_return:
                        pending_return.discard(chosen_spare)
                        st.session_state.spares_needing_return = pending_return
                    st.session_state.cleaned_set.add(chosen_spare)
                    st.session_state.cleaned_set.discard(route_to_cover)
                    st.session_state.loaded_set.discard(chosen_spare)
                    st.session_state.inprog_set.discard(chosen_spare)
                    st.session_state.special_set.discard(chosen_spare)

                    assignments[route_to_cover] = chosen_spare
                    st.session_state.oos_spare_assignments = assignments
                    st.session_state.pending_oos_route = None
                    st.session_state.pending_start_truck = None
                    st.session_state.selected_truck = chosen_spare
                    _mark_and_save()
                    st.success(f"Spare {chosen_spare} assigned to route {route_to_cover} and moved to Unloaded.")
                    st.rerun()
            else:
                st.info("No spare trucks are currently available for assignment.")

            c1, c2 = st.columns([1, 1])
            with c1:
                if existing_spare is not None:
                    if st.button("Clear assignment", use_container_width=True, key=f"clear_oos_assignment_{int(route_to_cover)}"):
                        cleared_spare = assignments.pop(route_to_cover, None)
                        if cleared_spare is not None:
                            try:
                                cleared_spare = int(cleared_spare)
                            except Exception:
                                cleared_spare = None
                        if (
                            cleared_spare is not None
                            and cleared_spare not in st.session_state.off_set
                            and cleared_spare not in st.session_state.shop_set
                            and cleared_spare not in st.session_state.inprog_set
                            and cleared_spare not in st.session_state.loaded_set
                        ):
                            st.session_state.cleaned_set.discard(cleared_spare)
                            st.session_state.spare_set.add(cleared_spare)
                        if route_to_cover in st.session_state.off_set:
                            st.session_state.cleaned_set.add(route_to_cover)
                        st.session_state.oos_spare_assignments = assignments
                        st.session_state.pending_oos_route = None
                        _mark_and_save()
                        st.rerun()
            with c2:
                if st.button("Cancel", use_container_width=True, key=f"cancel_oos_assignment_{int(route_to_cover)}"):
                    st.session_state.pending_oos_route = None
                    _mark_and_save()
                    st.rerun()

    if st.session_state.active_screen == "STATUS_CLEANED" and st.session_state.get("pending_start_truck"):
        pending_t = int(st.session_state.get("pending_start_truck"))
        assigned_route = None
        for route_raw, spare_raw in (st.session_state.get("oos_spare_assignments") or {}).items():
            try:
                route_num = int(route_raw)
                spare_num = int(spare_raw)
            except Exception:
                continue
            if spare_num == pending_t and route_num in st.session_state.off_set:
                assigned_route = route_num
                break

        if pending_t in st.session_state.shop_set:
            st.warning(f"Truck {pending_t} is marked Shop. Has it returned? Confirm to start loading.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm and start", use_container_width=True, key="confirm_shop_return_start"):
                    mark_return_from_shop(pending_t, "In Progress")
                    if not st.session_state.inprog_set:
                        start_loading_truck(pending_t)
                        st.session_state.active_screen = "IN_PROGRESS"
                    else:
                        st.session_state.start_blocked = True
                        st.session_state.start_blocking_truck = next(iter(st.session_state.inprog_set))
                        st.session_state.start_attempt_truck = pending_t
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()
            with c2:
                if st.button("No, cancel", use_container_width=True, key="cancel_shop_return_start"):
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()
        elif pending_t in off_trucks_for_today():
            st.warning(f"Truck {pending_t} is scheduled Off for the load day. Override and load anyway?")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Override and load", use_container_width=True, key="override_start_load"):
                    if not st.session_state.inprog_set:
                        start_loading_truck(pending_t)
                        st.session_state.active_screen = "IN_PROGRESS"
                    else:
                        st.session_state.start_blocked = True
                        st.session_state.start_blocking_truck = next(iter(st.session_state.inprog_set))
                        st.session_state.start_attempt_truck = pending_t
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()
            with c2:
                if st.button("No, cancel", use_container_width=True, key="cancel_start_load_off"):
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()
        else:
            if assigned_route is not None:
                st.warning(f"Do you want to Load spare truck {pending_t} for OOS route {assigned_route}?")
            else:
                st.warning(f"Do you want to Load truck {pending_t}?")
            c1, c2 = st.columns([1, 1])
            with c1:
                confirm_label = "Yes, start loading spare" if assigned_route is not None else "Yes, start loading"
                if st.button(confirm_label, use_container_width=True, key="confirm_start_load"):
                    if not st.session_state.inprog_set:
                        start_loading_truck(pending_t)
                        st.session_state.active_screen = "IN_PROGRESS"
                    else:
                        st.session_state.start_blocked = True
                        st.session_state.start_blocking_truck = next(iter(st.session_state.inprog_set))
                        st.session_state.start_attempt_truck = pending_t
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()
            with c2:
                if st.button("No, cancel", use_container_width=True, key="cancel_start_load"):
                    st.session_state.pending_start_truck = None
                    _mark_and_save()
                    st.rerun()

    # If a start attempt was blocked by an existing in-progress truck, show a popup
    if st.session_state.active_screen == "STATUS_CLEANED" and st.session_state.get("start_blocked"):
        blocking = st.session_state.get("start_blocking_truck")
        attempt = st.session_state.get("start_attempt_truck")
        st.error(f"Cannot start Truck {attempt}: Truck {blocking} is already in progress. Please complete it first.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Go to in-progress truck", use_container_width=True):
                st.session_state.active_screen = "IN_PROGRESS"
                # clear the flag
                st.session_state.start_blocked = False
                st.session_state.start_blocking_truck = None
                st.session_state.start_attempt_truck = None
                st.rerun()
        with c2:
            if st.button("Dismiss", use_container_width=True):
                st.session_state.start_blocked = False
                st.session_state.start_blocking_truck = None
                st.session_state.start_attempt_truck = None

# --------------------------
# In Progress
# --------------------------
elif st.session_state.active_screen == "IN_PROGRESS":
    st.markdown("<style>h1{display:none;}</style>", unsafe_allow_html=True)
    st.markdown(
        """
        <style>
            [data-testid="stMainBlockContainer"] {
                max-width: 1180px !important;
                width: 100% !important;
                padding-top: 0.05rem !important;
                padding-left: 0.35rem !important;
                padding-right: 0.8rem !important;
            }
            @media (max-width: 980px) {
                [data-testid="stMainBlockContainer"] {
                    max-width: 100% !important;
                    padding-left: 0.25rem !important;
                    padding-right: 0.5rem !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


    reminder = st.session_state.get("daily_notes", "")
    no_notes = "<span style=\"opacity:0.5;\">No notes set.</span>"
    notes_html = _format_note_lines_as_bullets_html(reminder, empty_html=no_notes)
    inprog_col_ratio = [1, 1] if _is_mobile_client() else [0.9, 2.1]
    left_col, center_col = st.columns(inprog_col_ratio, gap="small")
    with left_col:
        st.markdown(
            (
                "<div style='width:100%; margin:0 0 8px 0; position:-webkit-sticky; position:sticky; top:64px; align-self:flex-start; z-index:12;'>"
                "  <div id='daily-notes-box' style='width:100%; min-width:0; max-width:340px; margin:0 auto; box-sizing:border-box; "
                "      border-radius:16px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); "
                "      background:rgba(15,23,42,0.65); box-shadow:0 12px 30px rgba(0,0,0,0.24); max-height:calc(100vh - 110px); display:flex; flex-direction:column;'>"
                "    <div id='daily-notes-bar' style='display:flex; align-items:center; justify-content:center; "
                "        padding:10px 12px; font-weight:900; font-size:18px; letter-spacing:0.16em; text-transform:uppercase; "
                "        background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); cursor:default; position:relative;'>"
                "      <span style='margin:0 auto;'>Daily Notes</span>"
                "    </div>"
                "    <div id='daily-notes-body' style='padding:12px 14px; font-size:25.5px; font-weight:800; line-height:1.3; overflow-y:auto;'>"
                f"      {notes_html}"
                "    </div>"
                "  </div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with center_col:
        if not inprog_truck:
            _empty_l, _empty_mid, _empty_r = st.columns([1, 2, 1])
            with _empty_mid:
                st.markdown(
                    "<div style='width:100%; text-align:center; padding:11px 12px; border-radius:10px; border:1px solid rgba(59,130,246,0.28); background:rgba(30,58,138,0.35); color:#60a5fa; font-weight:700;'>No truck currently in progress.</div>",
                    unsafe_allow_html=True,
                )
                if true_available:
                    if st.button("View Unloaded trucks to start loading", use_container_width=True, key="start_inprog_suggested"):
                        st.session_state.active_screen = "STATUS_CLEANED"
                        _mark_and_save()
                        st.rerun()
                else:
                    st.markdown(
                        "<div style='text-align:center; opacity:0.75; margin-top:6px;'>No available trucks to start loading.</div>",
                        unsafe_allow_html=True,
                    )
        else:
            elapsed = elapsed_seconds()
            avg_all = average_load_time_seconds([])

            def _finish_in_progress_loading(success_message: str):
                t = int(inprog_truck)
                sec = elapsed_seconds()
                st.session_state.load_durations[t] = sec
                append_load_duration(t, sec)
                st.session_state.inprog_start_time = None
                st.session_state.inprog_set.clear()
                st.session_state.loaded_set.add(t)
                st.session_state.load_finish_times[t] = time.time()
                st.session_state.inprog_skip_confirm = False
                _mark_and_save()
                st.success(success_message)
                st.session_state.active_screen = "STATUS_LOADED"
                st.rerun()

            global_note, daily_note, note_text = get_truck_notes(inprog_truck)
            if note_text:
                sections = []
                if global_note:
                    safe_global = html.escape(global_note).replace("\n", "<br>")
                    sections.append(
                        "<div style='padding-bottom:8px; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.18);'>"
                        "  <div style='font-size:14px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7;'>General Notes</div>"
                        f"  <div style='font-size:20px;'>{safe_global}</div>"
                        "</div>"
                    )
                if daily_note:
                    safe_daily = html.escape(daily_note).replace("\n", "<br>")
                    sections.append(
                        "<div>"
                        "  <div style='font-size:14px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7;'>Daily Notes</div>"
                        f"  <div style='font-size:20px;'>{safe_daily}</div>"
                        "</div>"
                    )
                safe_note = "".join(sections)
            st.markdown(
                (
                    "<div style='text-align:center; margin:0 0 2px 0;'>"
                    "  <div style='font-size:22px; letter-spacing:0.22em; text-transform:uppercase; opacity:0.85; font-weight:900;'>Current Truck</div>"
                    f"  <div style='font-size:84px; font-weight:900; line-height:1.0; color:#facc15;'>#{inprog_truck}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                (
                    "<div style='text-align:center; margin:0 0 8px 0; font-size:18px; opacity:0.75;'>"
                    f"Average load time: {seconds_to_mmss(avg_all) if avg_all is not None else 'N/A'}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            if note_text:
                st.markdown(
                    (
                        "<div id='inprog-notes' style='width:520px; max-width:80vw; margin:0 auto 8px auto; border-radius:16px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); background:rgba(15,23,42,0.65); box-shadow:0 12px 30px rgba(0,0,0,0.24);'>"
                        "  <div id='inprog-notes-bar' style='display:flex; align-items:center; justify-content:center; padding:10px 12px; font-weight:900; font-size:18px; letter-spacing:0.16em; text-transform:uppercase; background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); position:relative;'>"
                        "    <span>Notes</span>"
                        "  </div>"
                        "  <div id='inprog-notes-body' style='padding:12px 14px; font-size:20px; line-height:1.25;'>"
                        f"    {safe_note}"
                        "  </div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            # Render elapsed timer into a DOM element that JS will update every second.
            warn_m = int(st.session_state.warn_seconds) // 60 if st.session_state.warn_seconds else None
            warn_visible = 'block' if (st.session_state.warn_seconds and elapsed >= int(st.session_state.warn_seconds)) else 'none'
            warn_text = "Load time exceeded" if warn_m else ""
            init_elapsed = int(elapsed)
            start_epoch = int(st.session_state.inprog_start_time or time.time())
            warn_threshold = int(st.session_state.warn_seconds or 0)
            flash_threshold = 20 * 60
            timer_html = f"""
                    <div style='position:relative; width:100%; margin:0 0 4px 0;'>
                        <style>
                            @keyframes inprogElapsedFlash {{
                                0%, 100% {{ opacity: 1; }}
                                50% {{ opacity: 0.22; }}
                            }}
                            #truck-elapsed.timer-flash {{
                                animation: inprogElapsedFlash 0.8s linear infinite;
                            }}
                        </style>
                        <div id='inprog-timer-box' style='width:640px; max-width:90vw; margin:0 auto; border-radius:22px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); background:rgba(15,23,42,0.65); box-shadow:0 20px 48px rgba(0,0,0,0.28);'>
                            <div id='inprog-timer-bar' style="display:flex; align-items:center; justify-content:center; padding:16px 18px; font-weight:900; font-size:24px; letter-spacing:0.22em; text-transform:uppercase; background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); cursor:default; position:relative; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; color:#fff;">
                                <span style="margin:0 auto; font-weight:900;">ELAPSED TIME</span>
                            </div>
                            <div id='inprog-timer-body' style='padding:20px 24px; font-size:104px; line-height:1.05; text-align:center; font-weight:800; color:{GREEN};'>
                                <span id='truck-elapsed'>{seconds_to_mmss(elapsed)}</span>
                            </div>
                            <div id='truck-elapsed-warn' style='display:{warn_visible}; color:{ORANGE}; font-weight:700; font-size:18px; text-align:center; padding:0 0 12px 0;'>{warn_text}</div>
                        </div>
                    </div>
            <script>
            (function(){{
                try {{
                    const pad = n => String(n).padStart(2,'0');
                    const fmt = s => {{
                        const m = Math.floor(s/60);
                        const sec = s % 60;
                        return pad(m) + ':' + pad(sec);
                    }};
                    const colorFor = (elapsed, warn) => {{
                        if (!warn || warn <= 0) return '{GREEN}';
                        const ratio = elapsed / warn;
                        if (ratio < 0.7) return '{GREEN}';
                        if (ratio < 1) return '{ORANGE}';
                        return '{RED}';
                    }};
                    const startEpoch = {start_epoch};
                    let elapsed = {init_elapsed};
                    const warn = {warn_threshold};
                    const flashAt = {flash_threshold};
                    const tick = () => {{
                        const now = Math.floor(Date.now() / 1000);
                        elapsed = Math.max(0, now - startEpoch);
                        const el = document.getElementById('truck-elapsed');
                        const warnEl = document.getElementById('truck-elapsed-warn');
                        const timerBody = document.getElementById('inprog-timer-body');
                        if (el) {{
                            el.textContent = fmt(elapsed);
                            el.style.color = colorFor(elapsed, warn);
                            if (elapsed >= flashAt) el.classList.add('timer-flash');
                            else el.classList.remove('timer-flash');
                        }}
                        if (warnEl) {{
                            if (warn > 0 && elapsed >= warn) warnEl.style.display = 'block';
                            else warnEl.style.display = 'none';
                        }}
                        if (timerBody) {{
                            if (warn > 0 && elapsed >= warn) {{
                                timerBody.style.boxShadow = '0 0 0 3px rgba(245,158,11,0.25), 0 10px 22px rgba(0,0,0,0.16)';
                            }} else {{
                                timerBody.style.boxShadow = 'none';
                            }}
                        }}
                    }};
                    const sync = () => {{
                        tick();
                        const msToNext = 1000 - (Date.now() % 1000);
                        setTimeout(sync, msToNext);
                    }};
                    sync();

                    const parentWin = window.parent;
                    const parentDoc = parentWin.document;
                    const keepAlive = parentWin.__inprogKeepAlive || (parentWin.__inprogKeepAlive = {{}});
                    keepAlive.lastPing = Date.now();

                    const ensureWake = async () => {{
                        try {{
                            if (!parentWin.navigator || !parentWin.navigator.wakeLock) return;
                            if ((parentDoc.visibilityState || 'visible') !== 'visible') return;
                            if (keepAlive.wakeLockSentinel) return;
                            const sentinel = await parentWin.navigator.wakeLock.request('screen');
                            keepAlive.wakeLockSentinel = sentinel;
                            sentinel.addEventListener('release', () => {{
                                if (keepAlive.wakeLockSentinel === sentinel) keepAlive.wakeLockSentinel = null;
                            }});
                        }} catch (e) {{}}
                    }};

                    const releaseWake = async () => {{
                        try {{
                            if (keepAlive.wakeLockSentinel) await keepAlive.wakeLockSentinel.release();
                        }} catch (e) {{}}
                        keepAlive.wakeLockSentinel = null;
                    }};

                    const ensureMediaPlayback = () => {{
                        try {{
                            const AudioCtx = parentWin.AudioContext || parentWin.webkitAudioContext;
                            if (!keepAlive.audioContext && AudioCtx) {{
                                const ctx = new AudioCtx();
                                const osc = ctx.createOscillator();
                                const gain = ctx.createGain();
                                osc.type = 'sine';
                                osc.frequency.value = 32;
                                gain.gain.value = 0.00001;
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.start();
                                keepAlive.audioContext = ctx;
                                keepAlive.audioOscillator = osc;
                                keepAlive.audioGain = gain;
                            }}
                            if (keepAlive.audioContext && keepAlive.audioContext.state === 'suspended') {{
                                keepAlive.audioContext.resume().catch(() => {{}});
                            }}
                            if (parentWin.navigator && parentWin.navigator.mediaSession) {{
                                parentWin.navigator.mediaSession.playbackState = 'playing';
                            }}
                        }} catch (e) {{}}
                    }};

                    const stopMediaPlayback = () => {{
                        try {{ if (keepAlive.audioOscillator) keepAlive.audioOscillator.stop(0); }} catch (e) {{}}
                        try {{ if (keepAlive.audioOscillator) keepAlive.audioOscillator.disconnect(); }} catch (e) {{}}
                        try {{ if (keepAlive.audioGain) keepAlive.audioGain.disconnect(); }} catch (e) {{}}
                        try {{ if (keepAlive.audioContext) keepAlive.audioContext.close(); }} catch (e) {{}}
                        keepAlive.audioOscillator = null;
                        keepAlive.audioGain = null;
                        keepAlive.audioContext = null;
                        try {{
                            if (parentWin.navigator && parentWin.navigator.mediaSession) {{
                                parentWin.navigator.mediaSession.playbackState = 'none';
                            }}
                        }} catch (e) {{}}
                    }};

                    keepAlive.ensureWake = ensureWake;
                    keepAlive.releaseWake = releaseWake;
                    keepAlive.ensureMediaPlayback = ensureMediaPlayback;
                    keepAlive.stopMediaPlayback = stopMediaPlayback;

                    if (window.__inprogKeepAlivePing) {{
                        clearInterval(window.__inprogKeepAlivePing);
                    }}
                    window.__inprogKeepAlivePing = setInterval(() => {{
                        keepAlive.lastPing = Date.now();
                    }}, 4000);

                    if (!keepAlive.guardInterval) {{
                        keepAlive.guardInterval = parentWin.setInterval(() => {{
                            try {{
                                const lastPing = Number(keepAlive.lastPing || 0);
                                const stale = !lastPing || (Date.now() - lastPing) > 15000;
                                if (stale) {{
                                    keepAlive.releaseWake && keepAlive.releaseWake();
                                    keepAlive.stopMediaPlayback && keepAlive.stopMediaPlayback();
                                    if (keepAlive.guardInterval) {{
                                        parentWin.clearInterval(keepAlive.guardInterval);
                                        keepAlive.guardInterval = null;
                                    }}
                                    return;
                                }}
                                keepAlive.ensureWake && keepAlive.ensureWake();
                                keepAlive.ensureMediaPlayback && keepAlive.ensureMediaPlayback();
                            }} catch (e) {{}}
                        }}, 3000);
                    }}

                    if (!keepAlive.visibilityListenerBound) {{
                        parentDoc.addEventListener('visibilitychange', () => {{
                            if ((parentDoc.visibilityState || 'visible') === 'visible') {{
                                keepAlive.ensureWake && keepAlive.ensureWake();
                                keepAlive.ensureMediaPlayback && keepAlive.ensureMediaPlayback();
                            }}
                        }});
                        keepAlive.visibilityListenerBound = true;
                    }}

                    if (!keepAlive.interactionListenerBound) {{
                        const onInteract = () => {{
                            keepAlive.ensureWake && keepAlive.ensureWake();
                            keepAlive.ensureMediaPlayback && keepAlive.ensureMediaPlayback();
                        }};
                        ['pointerdown', 'touchstart', 'keydown', 'click'].forEach((evt) => {{
                            parentDoc.addEventListener(evt, onInteract);
                        }});
                        keepAlive.interactionListenerBound = true;
                    }}

                    keepAlive.ensureWake && keepAlive.ensureWake();
                    keepAlive.ensureMediaPlayback && keepAlive.ensureMediaPlayback();
                }} catch(e){{console.error(e);}}
            }})();
            </script>
            """
            components.html(timer_html, height=270)

            if st.session_state.get("shorts_disabled"):
                if st.button("Finish Loading", use_container_width=True, key="inprog_finish_loading_top_disabled"):
                    _finish_in_progress_loading(
                        f"Truck {int(inprog_truck)} marked Loaded (shortages handled manually)."
                    )
            else:
                if st.button("Finish Loading", use_container_width=True, key="inprog_finish_loading_top"):
                    st.session_state.shorts_truck = int(inprog_truck)
                    ensure_shorts_model(inprog_truck)
                    st.session_state.shorts_autostart_next_up_for_truck = int(inprog_truck)
                    st.session_state.active_screen = "SHORTS"
                    _mark_and_save()
                    st.rerun()

            _sync_next_up_from_state_file()
            next_up = st.session_state.get("next_up_truck")
            next_up_off_today = {int(t) for t in (off_today or set())}
            next_up_unloaded_candidates = (
                set(st.session_state.get("cleaned_set") or set())
                - set(st.session_state.get("loaded_set") or set())
                - set(st.session_state.get("inprog_set") or set())
                - set(st.session_state.get("shop_set") or set())
                - set(st.session_state.get("off_set") or set())
                - next_up_off_today
            )
            next_up_spare_candidates = (
                set(st.session_state.get("spare_set") or set())
                - set(st.session_state.get("loaded_set") or set())
                - set(st.session_state.get("inprog_set") or set())
                - set(st.session_state.get("shop_set") or set())
                - set(st.session_state.get("off_set") or set())
                - next_up_off_today
            )
            next_up_regular_candidates = sorted(
                {int(t) for t in next_up_unloaded_candidates}
            )
            next_up_spare_only_candidates = sorted(
                {int(t) for t in (next_up_spare_candidates - next_up_unloaded_candidates)}
            )
            next_up_candidates = next_up_regular_candidates + next_up_spare_only_candidates

            assigned_oos_routes_for_spare: dict[int, int] = {}
            for route_raw, spare_raw in (st.session_state.get("oos_spare_assignments") or {}).items():
                try:
                    route_num = int(route_raw)
                    spare_num = int(spare_raw)
                except Exception:
                    continue
                if route_num in st.session_state.off_set:
                    assigned_oos_routes_for_spare[spare_num] = route_num

            if next_up is not None:
                st.markdown(
                    (
                        "<div style='text-align:center; margin:10px 0 2px 0;'>"
                        "  <div style='font-size:18px; letter-spacing:0.16em; text-transform:uppercase; opacity:0.7;'>Next Up</div>"
                        f"  <div style='font-size:72px; font-weight:900; line-height:1.0; color:#3b82f6;'>#{int(next_up)}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                avg_next = average_load_time_seconds([int(next_up)])
                st.markdown(
                    (
                        "<div style='text-align:center; margin-top:2px; font-size:18px; opacity:0.75;'>"
                        f"Avg for next up: {seconds_to_mmss(avg_next) if avg_next is not None else 'N/A'}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                clear_col = st.columns([1, 2, 1])[1]
                with clear_col:
                    if st.button("Clear Next Up", use_container_width=True, key="inprog_next_up_clear"):
                        st.session_state.next_up_truck = None
                        _mark_and_save()
                        st.rerun()
            else:
                if next_up_candidates:
                    candidate_labels = {}
                    for candidate in next_up_candidates:
                        candidate_num = int(candidate)
                        if candidate_num in assigned_oos_routes_for_spare:
                            candidate_labels[candidate_num] = (
                                f"Truck {candidate_num} • OOS route {assigned_oos_routes_for_spare[candidate_num]}"
                            )
                        elif candidate_num in next_up_spare_only_candidates:
                            candidate_labels[candidate_num] = f"Truck {candidate_num} • Spare"
                        else:
                            candidate_labels[candidate_num] = f"Truck {candidate_num}"
                    pick_col, set_col = st.columns([4, 1])
                    with pick_col:
                        picked_next_up = st.selectbox(
                            "Set next up",
                            options=next_up_candidates,
                            format_func=lambda t: candidate_labels.get(int(t), f"Truck {int(t)}"),
                            key="inprog_next_up_pick",
                        )
                    with set_col:
                        st.write("")
                        st.write("")
                        if st.button("Set", use_container_width=True, key="inprog_next_up_set"):
                            st.session_state.next_up_truck = int(picked_next_up)
                            _mark_and_save()
                            st.rerun()
                else:
                    st.selectbox(
                        "Set next up",
                        options=["No available unloaded/spare trucks"],
                        index=0,
                        key="inprog_next_up_empty",
                        disabled=True,
                    )

            st.divider()
            if not st.session_state.get("shorts_disabled"):
                ensure_shorts_model(inprog_truck)
                render_shorts_button_flow(inprog_truck)
                inprog_short_rows = st.session_state.shorts.get(int(inprog_truck), [])
                inprog_short_view = [r for r in inprog_short_rows if (r.get("item") or "").strip() and r.get("item") != "None"]
                if inprog_short_view:
                    st.table(inprog_short_view)

                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("Go To Shortages", use_container_width=True):
                        st.session_state.shorts_truck = int(inprog_truck)
                        ensure_shorts_model(inprog_truck)
                        st.session_state.shorts_autostart_next_up_for_truck = None
                        st.session_state.shorts_pending_next_up_confirm_for_truck = None
                        st.session_state.active_screen = "SHORTS"
                        _mark_and_save()
                        st.rerun()
                with c2:
                    if st.button("Skip Shortages", use_container_width=True):
                        st.session_state.inprog_skip_confirm = True

                if st.session_state.get("inprog_skip_confirm"):
                    st.warning("Skip shortages and stop the timer for this truck?")
                    c3, c4 = st.columns([1, 1])
                    with c3:
                        if st.button("Confirm skip", use_container_width=True):
                            _finish_in_progress_loading(f"Truck {int(inprog_truck)} marked Loaded (shortages skipped).")
                    with c4:
                        if st.button("Cancel", use_container_width=True):
                            st.session_state.inprog_skip_confirm = False
                            st.rerun()

            # Timer runs in the component iframe above.


# --------------------------
# Break
# --------------------------
elif st.session_state.active_screen == "BREAK":
    st.markdown("<style>h1{display:none;}</style>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:44px; font-weight:900; color:#dc2626; margin:0 0 8px 0;'>ON BREAK</div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.break_start_time:
        st.session_state.break_start_time = time.time()

    start_epoch = int(st.session_state.break_start_time or time.time())
    duration = int(st.session_state.break_duration or 1800)
    init_remaining = max(0, duration - int(time.time() - start_epoch))
    next_up = st.session_state.get("next_up_truck")
    can_auto_start = bool(next_up is not None and not st.session_state.inprog_set)
    if (time.time() - start_epoch) >= duration and can_auto_start:
        if int(next_up) in st.session_state.shop_set:
            st.session_state.pending_start_truck = int(next_up)
            st.session_state.break_start_time = None
            st.session_state.active_screen = "STATUS_CLEANED"
            _mark_and_save()
            st.rerun()
        start_loading_truck(int(next_up))
        st.session_state.break_start_time = None
        st.session_state.active_screen = "IN_PROGRESS"
        _mark_and_save()
        st.rerun()
    # Calculate the return time from break in 12hr format
    return_time_epoch = start_epoch + duration
    rounded_return_epoch = int(((return_time_epoch + 59) // 60) * 60)
    return_time_struct = time.localtime(rounded_return_epoch)
    return_hour = return_time_struct.tm_hour
    return_min = return_time_struct.tm_min
    ampm = "AM" if return_hour < 12 else "PM"
    hour12 = return_hour % 12
    hour12 = hour12 if hour12 else 12
    return_time_str = f"{hour12}:{return_min:02d} {ampm}"

    break_html = """
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; margin:0; padding:0;">
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; margin:0;">
        <div id="break-box" style="
            width:min(760px,96vw);
            border-radius:clamp(14px, 4vw, 22px);
            border:2px solid rgba(34,197,94,0.45);
            background:rgba(15,23,42,0.65);
            box-shadow:0 20px 48px rgba(0,0,0,0.28);
            overflow:hidden;
            text-align:center;
            padding:clamp(10px, 3vw, 16px) clamp(10px, 3vw, 16px) clamp(8px, 2.5vw, 14px) clamp(10px, 3vw, 16px);
        ">
          <div style="font-size:clamp(14px, 4.2vw, 22px); letter-spacing:0.18em; text-transform:uppercase; font-weight:900; opacity:0.82; margin:0 0 6px 0; color:#e2e8f0;">
            Break Timer
          </div>
          <div id="break-remaining" style="font-size:clamp(56px, 26vw, 150px); font-weight:900; line-height:0.98; color:#22c55e; margin:0;">__INIT_TEXT__</div>
          <div style="font-size:clamp(12px, 3.3vw, 18px); letter-spacing:0.12em; text-transform:uppercase; opacity:0.72; margin:2px 0 0 0; color:#cbd5e1;">
            Return from break at
          </div>
          <div id="break-return-time" style="font-size:clamp(24px, 11vw, 46px); font-weight:900; line-height:1.05; color:#2563eb; margin:2px 0 2px 0;">__RETURN_TIME__</div>
        </div>
        <div id="break-done" style="display:none; color:#f59e0b; font-weight:800; font-size:clamp(22px, 7vw, 34px); margin:0;">Break complete</div>
        <div id="break-done-time" style="display:none; color:#60a5fa; font-weight:800; font-size:clamp(18px, 6vw, 30px); margin:0;"></div>
      </div>
    </div>
    <script>
    (function(){
        try {
            const pad = n => String(n).padStart(2,'0');
            const fmt = s => {
                const m = Math.floor(s/60);
                const sec = s % 60;
                return pad(m) + ':' + pad(sec);
            };
            const fmt12hr = () => {
                const now = new Date();
                let h = now.getHours();
                let m = now.getMinutes();
                let s = now.getSeconds();
                const ampm = h >= 12 ? 'PM' : 'AM';
                h = h % 12;
                h = h ? h : 12;
                return h + ':' + pad(m) + ':' + pad(s) + ' ' + ampm;
            };

            const fitBreakCard = () => {
                const box = document.getElementById('break-box');
                const timer = document.getElementById('break-remaining');
                const returnTime = document.getElementById('break-return-time');
                if (!box || !timer) return;
                const width = Math.max(220, box.clientWidth || 0);
                const timerPx = Math.max(56, Math.min(150, Math.round(width * 0.27)));
                timer.style.fontSize = timerPx + 'px';
                if (returnTime) {
                    const returnPx = Math.max(24, Math.min(46, Math.round(width * 0.11)));
                    returnTime.style.fontSize = returnPx + 'px';
                }
            };

            const startEpoch = __START__;
            const duration = __DUR__;
            const autoStart = __AUTO__;
            const tick = () => {
                const now = Math.floor(Date.now() / 1000);
                const elapsed = Math.max(0, now - startEpoch);
                const remaining = Math.max(0, duration - elapsed);
                const el = document.getElementById('break-remaining');
                const done = document.getElementById('break-done');
                const doneTime = document.getElementById('break-done-time');
                if (el) el.textContent = fmt(remaining);
                if (done) done.style.display = remaining <= 0 ? 'block' : 'none';
                if (doneTime) {
                    doneTime.style.display = remaining <= 0 ? 'block' : 'none';
                    if (remaining <= 0) {
                        doneTime.textContent = 'Time: ' + fmt12hr();
                    }
                }
                if (autoStart && remaining <= 0 && !window.__breakAutoReloaded) {
                    window.__breakAutoReloaded = true;
                    window.parent.location.reload();
                }
            };
            const sync = () => {
                tick();
                fitBreakCard();
                const msToNext = 1000 - (Date.now() % 1000);
                setTimeout(sync, msToNext);
            };

            fitBreakCard();
            setTimeout(fitBreakCard, 60);
            setTimeout(fitBreakCard, 220);
            window.addEventListener('resize', fitBreakCard);
            sync();
        } catch(e){console.error(e);}
    })();
    </script>
    """
    break_html = (
        break_html
        .replace("__START__", str(start_epoch))
        .replace("__DUR__", str(duration))
        .replace("__AUTO__", str(can_auto_start).lower())
        .replace("__INIT_TEXT__", seconds_to_mmss(init_remaining))
        .replace("__RETURN_TIME__", return_time_str)
    )
    break_component_height = 380 if _is_mobile_client() else 430
    components.html(break_html, height=break_component_height)

    if next_up is not None:
        st.markdown(
            (
                "<div style='text-align:center; margin:6px 0 2px 0;'>"
                "  <div style='font-size:12px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7;'>Next Up</div>"
                f"  <div style='font-size:48px; font-weight:900; line-height:1.0; color:#3b82f6;'>#{int(next_up)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='text-align:center; font-size:13px; margin-top:4px; opacity:0.6;'>Next up: None</div>",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("End Break", use_container_width=True, key="end_break"):
            st.session_state.break_start_time = None
            st.session_state.active_screen = "STATUS_LOADED"
            _mark_and_save()
            st.rerun()
    with c2:
        if st.button("Change Next Up", use_container_width=True, key="break_change_next_up"):
            st.session_state.next_up_return_screen = "BREAK"
            st.session_state.active_screen = "LOAD"
            _mark_and_save()
            st.rerun()


# --------------------------
# Ready Workday
# --------------------------
elif st.session_state.active_screen == "SETUP":
    render_page_heading("Ready Workday")

    run_date = st.date_input(
        "Run date (today)",
        value=st.session_state.run_date or date.today(),
        key="setup_run_date",
    )

    mode = st.radio(
        "What are we loading for?",
        ["Normal (tomorrow only)", "Holiday (multiple load days)"],
        horizontal=True,
        key="setup_mode",
    )

    if mode == "Normal (tomorrow only)":
        ship_dates = [run_date + timedelta(days=1)]
        holiday_selection_valid = True
    else:
        ship_dates, holiday_selection_valid = render_holiday_load_day_picker(run_date, "setup")

    st.divider()

    warn_min = st.number_input(
        "Auto-warning threshold (minutes)",
        min_value=1,
        max_value=240,
        value=max(1, int(st.session_state.warn_seconds // 60)),
        step=1,
        key="warn_minutes",
    )
    st.session_state.warn_seconds = int(warn_min) * 60
    current_shorts_mode = st.session_state.get("shorts_mode")
    if not current_shorts_mode:
        current_shorts_mode = SHORTS_MODE_DISABLE if st.session_state.get("shorts_disabled") else SHORTS_MODE_BUTTONS
    mode_index = SHORTS_MODE_OPTIONS.index(current_shorts_mode) if current_shorts_mode in SHORTS_MODE_OPTIONS else 0
    st.session_state.shorts_mode = st.selectbox(
        "Shortages entry method",
        options=SHORTS_MODE_OPTIONS,
        index=mode_index,
        key="setup_shorts_mode",
    )
    st.session_state.shorts_disabled = st.session_state.shorts_mode == SHORTS_MODE_DISABLE
    st.session_state.batching_disabled = st.checkbox(
        "Disable batching for today (handled manually)",
        value=bool(st.session_state.get("batching_disabled")),
        key="setup_disable_batching",
    )
    daily_notes_prompt = st.checkbox(
        "Do you have any daily specific fleet notes?",
        value=False,
        key="setup_daily_notes_prompt",
    )
    if daily_notes_prompt:
        if st.button("Open Fleet Notes", use_container_width=True, key="setup_open_fleet_notes"):
            st.session_state.sup_manage_pref_action = "Notes"
            st.session_state.sup_manage_truck = None
            st.session_state.sup_manage_action = None
            st.session_state.active_screen = "FLEET"
            _mark_and_save()
            st.rerun()

    st.divider()
    selected_ship_keys = sorted(d.isoformat() for d in ship_dates)
    current_ship_keys = sorted(d.isoformat() for d in (st.session_state.get("ship_dates") or []))
    setup_needs_apply = (
        (not st.session_state.get("setup_done"))
        or (st.session_state.get("run_date_key") != _run_date_key(run_date))
        or (selected_ship_keys != current_ship_keys)
    )
    if setup_needs_apply and holiday_selection_valid:
        apply_run_config(run_date, ship_dates)
        st.session_state.active_screen = "UNLOAD"
        save_state()
        st.rerun()
    elif setup_needs_apply and not holiday_selection_valid:
        st.warning("Pick two different load days to continue holiday setup.")

# --------------------------
# Management page
# --------------------------
elif st.session_state.active_screen == "FLEET":
    st.markdown("<style>h1{display:none;}</style>", unsafe_allow_html=True)
    render_page_heading("Fleet Management")
    render_fleet_management()

# --------------------------
# Management page
elif st.session_state.active_screen == "SUPERVISOR":
    render_page_heading("Management - Admin & Statistics")

    avg_sec = average_load_time_seconds(sorted(st.session_state.loaded_set))
    st.metric("Average load time (today)", seconds_to_mmss(avg_sec) if avg_sec is not None else "N/A")

    c0, c1, c2, c3, c4 = st.columns(5)
    with c0:
        st.metric("Dirty", len(dirty_trucks))
    with c1:
        st.metric("Unloaded", len(cleaned_list))
    with c2:
        st.metric("In Progress", str(inprog_truck) if inprog_truck is not None else "None")
    with c3:
        st.metric("Loaded", len(loaded_list))
    with c4:
        st.metric("Shop", len(shop_list))

    with st.expander("Configure load day", expanded=False):
        run_date = st.date_input("Run date (today)", value=st.session_state.run_date or date.today(), key="sup_run_date")
        mode = st.radio("Mode", ["Normal (tomorrow only)", "Holiday (multiple load days)"], key="sup_mode")
        if mode == "Normal (tomorrow only)":
            ship_dates = [run_date + timedelta(days=1)]
            holiday_selection_valid = True
        else:
            ship_dates, holiday_selection_valid = render_holiday_load_day_picker(run_date, "sup")

        # Global Reminder note editor
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        st.write("#### Daily Notes (visible all day)")
        reminder = st.session_state.get("daily_notes", "")
        new_reminder = st.text_area(
            "Edit daily notes",
            value=reminder,
            height=110,
            key="sup_global_reminder_text",
        )
        if new_reminder != reminder:
            st.session_state["daily_notes"] = new_reminder
            save_state()
            logging.info("Daily notes updated from Management tab.")
            st.success("Daily notes updated.")

        warn_min = st.number_input("Auto-warning threshold (minutes)", min_value=1, max_value=240, value=max(1, int(st.session_state.warn_seconds // 60)), step=1, key="sup_warn_minutes")
        roll_c1, roll_c2 = st.columns(2)
        with roll_c1:
            rollover_prompt_hour = st.number_input(
                "Rollover prompt hour (24h)",
                min_value=0,
                max_value=23,
                value=int(_get_rollover_prompt_hour()),
                step=1,
                key="sup_rollover_prompt_hour",
            )
        with roll_c2:
            rollover_snooze_minutes = st.number_input(
                "Rollover snooze (minutes)",
                min_value=1,
                max_value=240,
                value=int(_get_rollover_snooze_minutes()),
                step=1,
                key="sup_rollover_snooze_minutes",
            )
        current_shorts_mode = st.session_state.get("shorts_mode")
        if not current_shorts_mode:
            current_shorts_mode = SHORTS_MODE_DISABLE if st.session_state.get("shorts_disabled") else SHORTS_MODE_BUTTONS
        mode_index = SHORTS_MODE_OPTIONS.index(current_shorts_mode) if current_shorts_mode in SHORTS_MODE_OPTIONS else 0
        shorts_mode = st.selectbox(
            "Shortages entry method",
            options=SHORTS_MODE_OPTIONS,
            index=mode_index,
            key="sup_shorts_mode",
        )
        disable_batching = st.checkbox(
            "Disable batching for today (handled manually)",
            value=bool(st.session_state.get("batching_disabled")),
            key="sup_disable_batching",
        )
        daily_notes_prompt = st.checkbox(
            "Do you have any daily specific fleet notes?",
            value=False,
            key="sup_daily_notes_prompt",
        )
        if daily_notes_prompt:
            if st.button("Open Fleet Notes", use_container_width=True, key="sup_open_fleet_notes"):
                st.session_state.sup_manage_pref_action = "Notes"
                st.session_state.sup_manage_truck = None
                st.session_state.sup_manage_action = None
                st.session_state.active_screen = "FLEET"
                _mark_and_save()
                st.rerun()

        if st.session_state.get("sup_run_date_last") != run_date:
            st.session_state["sup_run_date_last"] = run_date
            st.session_state.warn_seconds = int(warn_min) * 60
            st.session_state.rollover_prompt_hour = int(rollover_prompt_hour)
            st.session_state.rollover_prompt_snooze_minutes = int(rollover_snooze_minutes)
            st.session_state.shorts_mode = shorts_mode
            st.session_state.shorts_disabled = shorts_mode == SHORTS_MODE_DISABLE
            st.session_state.batching_disabled = bool(disable_batching)
            if holiday_selection_valid:
                apply_run_config(run_date, ship_dates)
                st.rerun()

        with st.expander("Off schedule (Day 1-5)", expanded=False):
            st.markdown("""
            **Day Mapping:**  
            - Day 1 = Monday  
            - Day 2 = Tuesday  
            - Day 3 = Wednesday  
            - Day 4 = Thursday  
            - Day 5 = Friday
            """)
            sched_day = st.selectbox("Schedule day", options=[1, 2, 3, 4, 5], key="sup_sched_day")
            current_sched = st.session_state.off_schedule.get(int(sched_day), []) if st.session_state.off_schedule else []
            if st.session_state.get("sup_sched_day_last") != sched_day:
                st.session_state["sup_sched_pick"] = [int(x) for x in current_sched] if current_sched else []
                st.session_state["sup_sched_day_last"] = sched_day
            sched_pick = st.multiselect(
                "Trucks scheduled Off",
                options=FLEET,
                default=[int(x) for x in current_sched] if current_sched else [],
                key="sup_sched_pick",
            )
        if st.button("Apply management settings", use_container_width=True):
            if not holiday_selection_valid:
                st.error("Select two different load days before saving holiday settings.")
            else:
                if "sup_sched_day" in st.session_state:
                    sd = int(st.session_state.get("sup_sched_day"))
                    pick = st.session_state.get("sup_sched_pick") or []
                    st.session_state.off_schedule[sd] = sorted({int(x) for x in pick})
                st.session_state.warn_seconds = int(warn_min) * 60
                st.session_state.rollover_prompt_hour = int(rollover_prompt_hour)
                st.session_state.rollover_prompt_snooze_minutes = int(rollover_snooze_minutes)
                st.session_state.shorts_mode = shorts_mode
                st.session_state.shorts_disabled = shorts_mode == SHORTS_MODE_DISABLE
                st.session_state.batching_disabled = bool(disable_batching)
                apply_run_config(run_date, ship_dates)
                apply_off_schedule(_previous_ship_day_num(_current_ship_day_num()))
                normalize_states()
                _mark_and_save()
                st.success("Management settings saved.")
                st.rerun()

    with st.expander("App Settings", expanded=False):
        if st.session_state.pop("mgmt_status_badge_reset_pending", False):
            _set_status_badge_picker_values(_get_status_badge_colors())

        tz_options = [
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Phoenix",
            "America/Anchorage",
            "Pacific/Honolulu",
            "UTC",
        ]
        current_tz = st.session_state.get("timezone_key") or "America/New_York"
        tz_index = tz_options.index(current_tz) if current_tz in tz_options else 0
        tz_pick = st.selectbox("Timezone", options=tz_options, index=tz_index, key="mgmt_tz_pick")
        theme_pick = st.selectbox(
            "Theme",
            options=["Dark"],
            index=0,
            key="mgmt_theme_pick",
            disabled=True,
        )
        live_button_styling_pick = st.checkbox(
            "Enable live truck button styling",
            value=bool(st.session_state.get("live_button_styling", True)),
            key="mgmt_live_button_styling_pick",
        )

        current_badge_colors = _get_status_badge_colors()
        st.markdown("##### Status bubble colors")
        c_badge_left, c_badge_right = st.columns(2)
        with c_badge_left:
            badge_dirty_pick = st.color_picker(
                "Dirty",
                value=current_badge_colors["dirty"],
                key="mgmt_badge_color_dirty",
            )
            badge_inprog_pick = st.color_picker(
                "In Progress",
                value=current_badge_colors["in_progress"],
                key="mgmt_badge_color_in_progress",
            )
            badge_loaded_pick = st.color_picker(
                "Loaded",
                value=current_badge_colors["loaded"],
                key="mgmt_badge_color_loaded",
            )
            badge_oos_spare_pick = st.color_picker(
                "OOS/SPARE",
                value=current_badge_colors["oos_spare"],
                key="mgmt_badge_color_oos_spare",
            )
        with c_badge_right:
            badge_shop_pick = st.color_picker(
                "Shop",
                value=current_badge_colors["shop"],
                key="mgmt_badge_color_shop",
            )
            badge_unloaded_pick = st.color_picker(
                "Unloaded",
                value=current_badge_colors["unloaded"],
                key="mgmt_badge_color_unloaded",
            )
            badge_off_pick = st.color_picker(
                "OFF",
                value=current_badge_colors["off"],
                key="mgmt_badge_color_off",
            )

        if st.button("Apply app settings", use_container_width=True, key="mgmt_app_settings_apply"):
            st.session_state.timezone_key = tz_pick
            st.session_state.ui_theme = "Dark"
            st.session_state.live_button_styling = bool(live_button_styling_pick)
            st.session_state.status_badge_colors = {
                "dirty": _normalize_hex_color(badge_dirty_pick, DEFAULT_STATUS_BADGE_COLORS["dirty"]),
                "shop": _normalize_hex_color(badge_shop_pick, DEFAULT_STATUS_BADGE_COLORS["shop"]),
                "in_progress": _normalize_hex_color(badge_inprog_pick, DEFAULT_STATUS_BADGE_COLORS["in_progress"]),
                "unloaded": _normalize_hex_color(badge_unloaded_pick, DEFAULT_STATUS_BADGE_COLORS["unloaded"]),
                "loaded": _normalize_hex_color(badge_loaded_pick, DEFAULT_STATUS_BADGE_COLORS["loaded"]),
                "off": _normalize_hex_color(badge_off_pick, DEFAULT_STATUS_BADGE_COLORS["off"]),
                "oos_spare": _normalize_hex_color(badge_oos_spare_pick, DEFAULT_STATUS_BADGE_COLORS["oos_spare"]),
            }
            save_state()
            st.success("App settings saved.")
            st.rerun()

        if st.button("Reset to defaults color scheme", use_container_width=True, key="mgmt_app_settings_reset_color_defaults"):
            st.session_state.status_badge_colors = dict(DEFAULT_STATUS_BADGE_COLORS)
            st.session_state.mgmt_status_badge_reset_pending = True
            save_state()
            st.success("Status bubble colors reset to defaults.")
            st.rerun()

    st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
    with st.expander("Download PDFs", expanded=False):
        st.write("### Load/Shortages PDF")
        st.download_button(
            "Download load/shortages",
            data=generate_pdf_bytes(),
            file_name=f"truck_readiness_{(st.session_state.run_date.isoformat() if st.session_state.run_date else 'workday')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.write("### Batch cards PDF")
        st.download_button(
            "Download batch cards",
            data=generate_batch_cards_pdf_bytes(),
            file_name=f"batch_cards_{(st.session_state.run_date.isoformat() if st.session_state.run_date else date.today().isoformat())}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.write("### End of day summary PDF")
        st.download_button(
            "Download end of day summary",
            data=generate_end_of_day_pdf_bytes(),
            file_name=f"end_of_day_{(st.session_state.run_date.isoformat() if st.session_state.run_date else date.today().isoformat())}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
    with st.expander("Activity History", expanded=False):
        log = list(reversed(st.session_state.get("activity_log") or []))[:30]
        if not log:
            st.caption("No recent activity.")
        else:
            for entry in log:
                st.markdown(f"<div style='margin:0; padding:0; line-height:1.1;'>- {entry}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
    with st.expander("Reset Workday Data (Management)", expanded=False):
        st.caption("Dangerous: use only if you want to wipe the current day and saved state.")
        if st.button("Reset All Data (DANGEROUS)", key="sup_reset_start"):
            st.session_state.reset_step = 1
            st.rerun()

        rs = st.session_state.get("reset_step")
        if rs == 1:
            st.error("Step 1 — This will clear workday data and remove the saved state file. Continue to final confirmation.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Continue to Final Step", key="sup_reset_step1"):
                    st.session_state.reset_step = 2
                    st.rerun()
            with c2:
                if st.button("Cancel Reset", key="sup_reset_cancel1"):
                    st.session_state.reset_step = None
                    st.rerun()

        if rs == 2:
            st.error("Final Step — This will irreversibly erase all saved data and reset defaults. This cannot be undone.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm Final Reset", key="sup_reset_final"):
                    # Preserve fleet configuration and current-day context
                    preserved_extra = st.session_state.get("extra_fleet", [])
                    preserved_off_schedule = (st.session_state.get("off_schedule") or {}).copy()
                    preserved_activity = st.session_state.get("activity_log", [])
                    preserved_run_date = st.session_state.get("run_date")
                    preserved_ship_dates = list(st.session_state.get("ship_dates") or [])
                    preserved_last_setup_date = st.session_state.get("last_setup_date")
                    preserved_oos = set()
                    for oval in (st.session_state.get("off_set") or set()):
                        try:
                            preserved_oos.add(int(oval))
                        except Exception:
                            continue
                    preserved_spares = set()
                    for sval in (st.session_state.get("spare_set") or set()):
                        try:
                            preserved_spares.add(int(sval))
                        except Exception:
                            continue
                    persistent_spares = {int(t) for t in PERSISTENT_SPARE_TRUCKS}
                    preserved_oos -= persistent_spares
                    preserved_spares |= persistent_spares

                    # Reset session_state keys to defaults, but restore fleet config
                    for k, v in defaults.items():
                        st.session_state[k] = v

                    # Restore the fleet configuration
                    st.session_state["extra_fleet"] = preserved_extra
                    st.session_state["removed_fleet"] = []  # Clear removed list to restore all trucks
                    st.session_state["off_schedule"] = preserved_off_schedule
                    st.session_state["activity_log"] = preserved_activity
                    st.session_state["off_set"] = preserved_oos
                    st.session_state["spare_set"] = preserved_spares

                    # Keep current run-day context so unloaded auto-pull can be reapplied
                    if preserved_run_date:
                        st.session_state["run_date"] = preserved_run_date
                        st.session_state["run_date_key"] = _run_date_key(preserved_run_date)
                        st.session_state["setup_done"] = True
                        st.session_state["last_setup_date"] = preserved_last_setup_date or date.today()
                    if preserved_ship_dates:
                        st.session_state["ship_dates"] = preserved_ship_dates
                    elif st.session_state.get("run_date"):
                        st.session_state["ship_dates"] = [st.session_state["run_date"] + timedelta(days=1)]

                    current_load_day = None
                    if st.session_state.get("ship_dates"):
                        current_load_day = ship_day_number(st.session_state["ship_dates"][0])
                    reset_status_for_new_day(current_load_day)
                    # Ensure OOS/spares persist through the reset helper
                    st.session_state["off_set"] = preserved_oos
                    st.session_state["spare_set"] = preserved_spares

                    # Remove persisted state file
                    try:
                        p = _state_path()
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                    save_state()
                    st.success("Workday data reset. Out Of Service and Spares preserved, with unloaded auto-pull reapplied for the current day.")
                    st.session_state.reset_step = None
                    st.rerun()
            with c2:
                if st.button("Cancel Reset", key="sup_reset_cancel2"):
                    st.session_state.reset_step = None
                    st.rerun()

        st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)
        st.write("### Other resets")

        if st.button("Reset Load Time Data", use_container_width=True, key="sup_reset_load_times_start"):
            st.session_state.reset_load_times_step = True
        if st.session_state.get("reset_load_times_step"):
            st.warning("This clears all load time history and per-truck load time data.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm reset load times", key="sup_reset_load_times_confirm"):
                    st.session_state.load_durations = {}
                    st.session_state.load_start_times = {}
                    st.session_state.load_finish_times = {}
                    try:
                        p = _durations_path()
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                    save_state()
                    st.success("Load time data cleared.")
                    st.session_state.reset_load_times_step = None
            with c2:
                if st.button("Cancel", key="sup_reset_load_times_cancel"):
                    st.session_state.reset_load_times_step = None
                    st.rerun()

        if st.button("Reset Shortages Data", use_container_width=True, key="sup_reset_shorts_start"):
            st.session_state.reset_shorts_step = True
        if st.session_state.get("reset_shorts_step"):
            st.warning("This clears all shortages and initials history for the current workday.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm reset shortages", key="sup_reset_shorts_confirm"):
                    st.session_state.shorts = {}
                    st.session_state.shorts_initials = {}
                    st.session_state.shorts_initials_ts = {}
                    st.session_state.shorts_initials_history = {}
                    save_state()
                    st.success("Shorts data cleared.")
                    st.session_state.reset_shorts_step = None
            with c2:
                if st.button("Cancel", key="sup_reset_shorts_cancel"):
                    st.session_state.reset_shorts_step = None
                    st.rerun()

        if st.button("Reset Quick Amounts", use_container_width=True, key="sup_reset_quick_amounts_start"):
            st.session_state.reset_quick_amounts_step = True
        if st.session_state.get("reset_quick_amounts_step"):
            st.warning("This clears custom quick amount mappings and reverts to default quick amounts.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm reset quick amounts", key="sup_reset_quick_amounts_confirm"):
                    try:
                        with open("shortage_quick_amounts.json", "w") as f:
                            json.dump({}, f)
                    except Exception:
                        pass
                    QUICK_AMOUNTS_MAP = load_quick_amounts()
                    st.success("Quick amounts reset to defaults.")
                    st.session_state.reset_quick_amounts_step = None
                    st.rerun()
            with c2:
                if st.button("Cancel", key="sup_reset_quick_amounts_cancel"):
                    st.session_state.reset_quick_amounts_step = None
                    st.rerun()

        if st.button("Reset Activity History", use_container_width=True, key="sup_reset_activity_start"):
            st.session_state.reset_activity_step = True
        if st.session_state.get("reset_activity_step"):
            st.warning("This clears the activity history list.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm reset activity", key="sup_reset_activity_confirm"):
                    st.session_state.activity_log = []
                    save_state()
                    st.success("Activity history cleared.")
                    st.session_state.reset_activity_step = None
            with c2:
                if st.button("Cancel", key="sup_reset_activity_cancel"):
                    st.session_state.reset_activity_step = None
                    st.rerun()

        if st.button("Reset Break (allow another)", use_container_width=True, key="sup_reset_break_start"):
            st.session_state.reset_break_step = True
        if st.session_state.get("reset_break_step"):
            st.warning("This clears the break timer and allows Start Break again.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm reset break", key="sup_reset_break_confirm"):
                    st.session_state.break_start_time = None
                    st.session_state.break_used = False
                    save_state()
                    st.success("Break reset.")
                    st.session_state.reset_break_step = None
            with c2:
                if st.button("Cancel", key="sup_reset_break_cancel"):
                    st.session_state.reset_break_step = None
                    st.rerun()

# --------------------------
# Unload
# --------------------------
elif st.session_state.active_screen == "UNLOAD":
    st.markdown("<style>h1{display:none;}</style>", unsafe_allow_html=True)
    render_page_heading("Unload Management — Dirty Trucks")
    # Truck selection by clicking bubble, not dropdown
    def render_unload_bubbles(trucks):
        # Render dirty truck bubbles as Streamlit buttons for in-place navigation
        clicked_truck = render_numeric_truck_buttons(trucks, "dirty_truck", default_cols=8)
        if clicked_truck is not None:
            t = int(clicked_truck)
            if st.session_state.get("batching_disabled"):
                post_unload_status = _mark_truck_unloaded_after_batch(int(t))
                st.session_state.pending_unload_truck = None
                st.session_state.unload_inprog_truck = None
                st.session_state.unload_inprog_start_time = None
                st.session_state.unload_inprog_wearers = 0
                try:
                    st.session_state["unload_truck_select"] = None
                except Exception:
                    pass
                _mark_and_save()
                if post_unload_status == "Spare":
                    st.success(f"Truck {t} returned to Spare (batching disabled).")
                else:
                    st.success(f"Truck {t} marked Unloaded (batching disabled).")
                st.rerun()
            else:
                st.session_state["unload_truck_select"] = int(t)
                st.session_state.active_screen = "BATCH"
                _set_query_params(page="BATCH", pick=str(int(t)))
                _mark_and_save()
                st.rerun()
    render_unload_bubbles(dirty_trucks)

    if st.session_state.get("batching_disabled"):
        st.session_state.pending_unload_truck = None
    st.info("Select a truck to begin unloading.")

    # Restore visually awesome batch cards at the bottom
    st.divider()
    cols = st.columns(3)
    for i in range(1, BATCH_COUNT + 1):
        col = cols[(i - 1) % 3]
        if (i - 1) % 3 == 0 and i != 1:
            cols = st.columns(3)
            col = cols[(i - 1) % 3]
        with col:
            with st.container(border=True):
                trucks = st.session_state.batches[i]['trucks']
                total = st.session_state.batches[i]['total']
                # Color logic for wearers
                if total < BATCH_CAP * 0.7:
                    color = GREEN
                elif total < BATCH_CAP * 0.95:
                    color = ORANGE
                else:
                    color = RED
                st.markdown(f"""
                <div style='border-radius:14px; box-shadow:0 2px 12px rgba(0,0,0,0.08); padding:18px 10px 14px 10px; background:rgba(255,255,255,0.08);'>
                    <div style='text-align:center; font-size:20px; font-weight:700; margin-bottom:8px;'>Batch {i}</div>
                    <div style='font-size:15px; margin-bottom:6px;'><b>{trucks}</b></div>
                    <div style='font-size:15px;'>
                        Total wearers: <span style='font-weight:800; color:{color}; font-size:18px;'>{total}</span> / {BATCH_CAP}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.write("### Batch cards PDF")
    st.download_button(
        "Download batch cards",
        data=generate_batch_cards_pdf_bytes(),
        file_name=f"batch_cards_{(st.session_state.run_date.isoformat() if st.session_state.run_date else date.today().isoformat())}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

# --------------------------
# Truck editor page
# --------------------------
elif st.session_state.active_screen == "TRUCK":
    t = st.session_state.selected_truck
    if t is None:
        st.warning("No truck selected.")
    else:
        render_truck_status_card(int(t), compact_top=True)

        # Overview: last duration, current in-progress elapsed, batch and wearers
        last_dur = st.session_state.load_durations.get(t)
        inprog_now = (t in st.session_state.inprog_set)
        live_elapsed = elapsed_seconds() if inprog_now and (next(iter(st.session_state.inprog_set)) == t) else None
        batch_id = None
        for bi, b in st.session_state.batches.items():
            if t in b.get("trucks", []):
                batch_id = bi
                break

        st.write("**Overview**")
        c0, c1, c2, c3 = st.columns([1,1,1,1])
        with c0:
            st.metric("Last load", seconds_to_mmss(last_dur) if last_dur is not None else "N/A")
        with c1:
            st.metric("Current", seconds_to_mmss(live_elapsed) if live_elapsed is not None else ("In progress" if inprog_now else "N/A"))
        with c2:
            st.metric("Batch", batch_id if batch_id else "—")
        with c3:
            st.metric("Wearers", int(st.session_state.wearers.get(t, 0) or 0))

        # additional info
        start_ts = st.session_state.load_start_times.get(t)
        finish_ts = st.session_state.load_finish_times.get(t)
        dur = st.session_state.load_durations.get(t)
        shorts_count = len(st.session_state.shorts.get(t, []))
        initials_ts = st.session_state.shorts_initials_ts.get(t)
        if start_ts:
            st.write(f"Started: {_format_ts(start_ts)}")
        if finish_ts:
            st.write(f"Finished: {_format_ts(finish_ts)}")
        if dur is not None:
            st.write(f"Duration: {seconds_to_mmss(dur)}")
        st.write(f"Shorts: {shorts_count} • Initials: {st.session_state.shorts_initials.get(t,'—')}" + (f" (saved {initials_ts})" if initials_ts else ""))

        st.write("**Current status**")
        status_feedback_key = f"truck_status_feedback_{int(t)}"
        pending_status_feedback = st.session_state.pop(status_feedback_key, None)
        if pending_status_feedback:
            st.success(str(pending_status_feedback))
        # determine current status
        if t in st.session_state.shop_set:
            cur_status = "Shop"
        elif t in st.session_state.inprog_set:
            cur_status = "In Progress"
        elif t in st.session_state.loaded_set:
            cur_status = "Loaded"
        elif t in st.session_state.cleaned_set:
            cur_status = "Unloaded"
        else:
            cur_status = "Dirty"

        st.caption(f"Status: {cur_status}")
        status_options = ["Dirty", "Unloaded", "In Progress", "Loaded", "Shop", "Out Of Service", "Spare", "Special"]
        status_index = status_options.index(cur_status) if cur_status in status_options else 0
        status_sel = st.selectbox("Set status", status_options, index=status_index, key=f"truck_status_select_{t}")
        shop_load_on = ""
        if status_sel == "Shop":
            shop_load_on = st.text_input("Load On? (optional)", key=f"truck_shop_load_on_{t}")
        if st.button("Apply status change", use_container_width=True, key=f"truck_status_apply_{t}"):
            _apply_truck_status_change(int(t), status_sel, shop_load_on=shop_load_on)
            _mark_and_save()
            st.session_state[status_feedback_key] = "Status Applied"
            st.rerun()

        st.divider()
        st.write("**Management notes**")
        global_note, daily_note, _ = get_truck_notes(t)
        note_val_global = st.text_area(
            "General notes (persist across days)",
            value=global_note,
            key=f"truck_note_global_{t}",
            height=100,
        )
        note_val_daily = st.text_area(
            "Daily notes (reset each run day)",
            value=daily_note,
            key=f"truck_note_daily_{t}",
            height=100,
        )
        n1, n2, n3 = st.columns([1, 1, 1])
        with n1:
            if st.button("Save notes", use_container_width=True, key=f"truck_note_save_{t}"):
                st.session_state.sup_notes_global[int(t)] = (note_val_global or "").strip()
                st.session_state.sup_notes_daily[int(t)] = (note_val_daily or "").strip()
                _mark_and_save()
                st.success(f"Notes saved for Truck {t}.")
        with n2:
            if st.button("Clear daily", use_container_width=True, key=f"truck_note_clear_daily_{t}"):
                st.session_state.sup_notes_daily.pop(int(t), None)
                _mark_and_save()
                st.success(f"Daily note cleared for Truck {t}.")
                st.rerun()
        with n3:
            if st.button("Clear global", use_container_width=True, key=f"truck_note_clear_global_{t}"):
                st.session_state.sup_notes_global.pop(int(t), None)
                _mark_and_save()
                st.success(f"General note cleared for Truck {t}.")
                st.rerun()

        st.divider()
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("Open short sheet", use_container_width=True):
                st.session_state.shorts_truck = t
                ensure_shorts_model(t)
                st.session_state.active_screen = "SHORTS"
                _mark_and_save()
                st.rerun()
        with c2:
            if st.button("Open Fleet Management", use_container_width=True):
                st.session_state.sup_manage_truck = t
                st.session_state.sup_manage_action = None
                st.session_state.sup_manage_pref_action = None
                st.session_state.active_screen = "FLEET"
                _mark_and_save()
                st.rerun()

        back_target = getattr(st.session_state, "_from_page", None) or "STATUS_DIRTY"
        if st.button("Back to status", use_container_width=True):
            st.session_state.active_screen = back_target
            _mark_and_save()
            st.rerun()
        

# --------------------------
# Batch page (opened when ?pick= is provided)
# --------------------------
elif st.session_state.active_screen == "BATCH":
    render_page_heading("Batch Assignment")
    t = st.session_state.get("unload_inprog_truck")
    if t is None:
        st.warning("No truck selected for batching.")
    else:
        if st.session_state.get("batching_disabled"):
            st.warning("Batching is disabled for today. Mark this truck Unloaded manually.")
            if st.button("Mark Unloaded (batching disabled)", use_container_width=True):
                post_unload_status = _mark_truck_unloaded_after_batch(int(t))
                st.session_state.unload_inprog_truck = None
                st.session_state.unload_inprog_start_time = None
                st.session_state.unload_inprog_wearers = 0
                try:
                    st.session_state["unload_truck_select"] = None
                except Exception:
                    pass
                st.session_state.active_screen = "UNLOAD"
                _mark_and_save()
                if post_unload_status == "Spare":
                    st.success(f"Truck {int(t)} returned to Spare (batching disabled).")
                else:
                    st.success(f"Truck {int(t)} marked Unloaded (batching disabled).")
                st.rerun()
            st.stop()
        try:
            _set_query_params(page="BATCH", pick=str(int(t)))
        except Exception:
            pass
        badge_bg, badge_border, badge_fg = _truck_status_colors(int(t))
        off_today_set = {int(x) for x in (off_today or set())}
        batch_cue_text = "Back it out" if int(t) in off_today_set else "Pull it up"
        st.markdown(
            f"""
            <div style='text-align:center; font-weight:700; margin-bottom:6px;'>Truck</div>
            <div style='display:flex; justify-content:center; margin:0.1rem 0 0.85rem 0;'>
                <div style='min-width:150px; max-width:230px; width:48%; min-height:76px; border-radius:14px; border:2px solid {badge_border}; background:{badge_bg}; color:{badge_fg}; font-weight:900; text-align:center; box-shadow:0 2px 10px rgba(0,0,0,0.12); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:8px 10px;'>
                    <div style='font-size:32px; line-height:1.0; font-weight:900;'>{int(t)}</div>
                    <div style='font-size:16px; line-height:1.05; font-weight:800; margin-top:4px; letter-spacing:0.02em;'>{batch_cue_text}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div id='batch-wearers'></div>", unsafe_allow_html=True)
        components.html("<script>const el=document.getElementById('batch-wearers'); if(el) el.scrollIntoView({behavior:'smooth'});</script>", height=0)
        wearers_default = st.session_state.get("unload_inprog_wearers", 0)
        try:
            wearers_default = int(wearers_default or 0)
        except Exception:
            wearers_default = 0
        wearers_raw = st.text_input(
            "Wearers",
            value="" if wearers_default <= 0 else str(wearers_default),
            key=f"batch_wearers_{t}",
        )
        components.html(
            f"""
            <script>
            (function(){{
                try {{
                const root = window.parent.document;
                const inputs = root.querySelectorAll('input[aria-label="Wearers"]');
                inputs.forEach((el) => {{
                    el.setAttribute('inputmode', 'numeric');
                    el.setAttribute('pattern', '[0-9]*');
                    el.setAttribute('type', 'tel');
                    el.setAttribute('enterkeyhint', 'done');
                    el.setAttribute('autocapitalize', 'off');
                    el.setAttribute('autocomplete', 'off');
                    el.setAttribute('spellcheck', 'false');
                    if (!el.dataset.batchLiveBound) {{
                        el.dataset.batchLiveBound = '1';
                        el.addEventListener('input', () => {{
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }});
                    }}
                }});

                const target = inputs.length ? inputs[inputs.length - 1] : null;
                const isMobile = {str(_is_mobile_client()).lower()};
                const focusToken = 'batch-wearers-{int(t)}-{int(st.session_state.get("nav_seq") or 0)}';
                if (isMobile && target && window.parent.__wearersFocusToken !== focusToken) {{
                    const openKeyboard = () => {{
                        try {{
                            target.focus({{ preventScroll: true }});
                            target.click();
                            const len = (target.value || '').length;
                            if (target.setSelectionRange) target.setSelectionRange(len, len);
                        }} catch (e) {{}}
                    }};

                    if (!target.dataset.batchTapFocusBound) {{
                        target.dataset.batchTapFocusBound = '1';
                        target.addEventListener('touchstart', openKeyboard, {{ passive: true }});
                        target.addEventListener('click', openKeyboard);
                    }}

                    const attempts = [0, 120, 260, 420, 700, 1100];
                    attempts.forEach((ms) => {{
                        setTimeout(() => {{
                            openKeyboard();
                            try {{
                                if (root.activeElement === target) {{
                                    window.parent.__wearersFocusToken = focusToken;
                                }}
                            }} catch (e) {{}}
                        }}, ms);
                    }});

                    setTimeout(() => {{
                        if (window.parent.__wearersFocusToken !== focusToken) {{
                            window.parent.__wearersFocusToken = focusToken;
                        }}
                    }}, 1400);
                }}
                }} catch (e) {{}}
            }})();
            </script>
            """,
            height=0,
            width=0,
        )
        wearers_text = str(wearers_raw).strip()
        typed_digits = "".join(ch for ch in wearers_text if ch.isdigit())
        if wearers_text.isdigit():
            w = int(wearers_text)
        elif wearers_text == "":
            w = 0
        else:
            w = int(typed_digits) if typed_digits else 0
            st.warning("Wearers must be a whole number.")
        st.session_state.unload_inprog_wearers = int(w)
        if st.button("Skip batching", use_container_width=True):
            post_unload_status = _mark_truck_unloaded_after_batch(int(t))
            st.session_state.unload_inprog_truck = None
            st.session_state.unload_inprog_start_time = None
            st.session_state.unload_inprog_wearers = 0
            try:
                st.session_state["unload_truck_select"] = None
            except Exception:
                pass
            st.session_state.active_screen = "UNLOAD"
            _mark_and_save()
            if post_unload_status == "Spare":
                st.success(f"Truck {int(t)} returned to Spare.")
            st.rerun()
        preview_w = w if w > 0 else 0
        allowed = batch_allowed_ids(preview_w)
        if wearers_text != "" and w > 0:
            st.info(f"Assign **Truck {t}** (wearers: **{w}**) to a batch (≤ {BATCH_CAP}).")
        elif wearers_text != "":
            st.caption("Enter at least 1 wearer before assigning.")
        else:
            st.caption("Enter wearers. Batch options are ready.")

        if not allowed:
            st.error("No batch can accept this truck without exceeding 400.")
        else:
            batch = st.selectbox(
                "Assign to batch",
                allowed,
                format_func=lambda i: f"Batch {i} (current {st.session_state.batches[i]['total']}/{BATCH_CAP})",
                key="batch_assign_select",
            )
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Assign to batch", use_container_width=True):
                    if w <= 0:
                        st.warning("Enter at least 1 wearer before assigning.")
                    else:
                        batch_assign(t, w, batch)
                        st.session_state.wearers[int(t)] = int(w)
                        post_unload_status = _mark_truck_unloaded_after_batch(int(t))
                        st.session_state.unload_inprog_truck = None
                        st.session_state.unload_inprog_start_time = None
                        st.session_state.unload_inprog_wearers = 0
                        _mark_and_save()
                        if post_unload_status == "Spare":
                            st.success(f"Truck {t} assigned to Batch {batch} and returned to Spare.")
                        else:
                            st.success(f"Truck {t} assigned to Batch {batch} and marked Unloaded.")
                        # Clear any pick param/state so we don't reopen BATCH
                        try:
                            st.session_state["unload_truck_select"] = None
                        except Exception:
                            pass
                        st.session_state.active_screen = "UNLOAD"
                        st.rerun()
            with c2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.unload_inprog_truck = None
                    st.session_state.unload_inprog_start_time = None
                    st.session_state.unload_inprog_wearers = 0
                    try:
                        st.session_state["unload_truck_select"] = None
                    except Exception:
                        pass
                    st.session_state.active_screen = "UNLOAD"
                    st.rerun()

        st.divider()
        cols = st.columns(3)
        for i in range(1, BATCH_COUNT + 1):
            col = cols[(i - 1) % 3]
            if (i - 1) % 3 == 0 and i != 1:
                cols = st.columns(3)
                col = cols[(i - 1) % 3]
            with col:
                with st.container(border=True):
                    trucks = st.session_state.batches[i]['trucks']
                    total = st.session_state.batches[i]['total']
                    if total < BATCH_CAP * 0.7:
                        color = GREEN
                    elif total < BATCH_CAP * 0.95:
                        color = ORANGE
                    else:
                        color = RED
                    st.markdown(f"""
                    <div style='border-radius:14px; box-shadow:0 2px 12px rgba(0,0,0,0.08); padding:18px 10px 14px 10px; background:rgba(255,255,255,0.08);'>
                        <div style='text-align:center; font-size:20px; font-weight:700; margin-bottom:8px;'>Batch {i}</div>
                        <div style='font-size:15px; margin-bottom:6px;'><b>{trucks}</b></div>
                        <div style='font-size:15px;'>
                            Total wearers: <span style='font-weight:800; color:{color}; font-size:18px;'>{total}</span> / {BATCH_CAP}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# --------------------------
# Load
# --------------------------
elif st.session_state.active_screen == "LOAD":
    st.markdown("<style>h2{display:none;}</style>", unsafe_allow_html=True)
    render_page_heading("Load")

    off_today_list = sorted({int(t) for t in off_today})
    load_left_col, load_main_col = st.columns([1, 3], gap="medium")

    with load_left_col:
        st.markdown(
            """
            <style>
                [data-testid="stExpander"] details > summary,
                [data-testid="stExpander"] details > summary * {
                    color: #e2e8f0 !important;
                    -webkit-text-fill-color: #e2e8f0 !important;
                    opacity: 1 !important;
                    font-weight: 800 !important;
                }
                [data-testid="stExpander"] details > summary {
                    background: #0f172a !important;
                    border: 1px solid rgba(148, 163, 184, 0.46) !important;
                    border-radius: 10px !important;
                }
                [data-testid="stExpander"] details > summary svg {
                    color: #e2e8f0 !important;
                    fill: #e2e8f0 !important;
                    stroke: #e2e8f0 !important;
                }
                [data-testid="stExpander"] details > div[role="region"] {
                    background: rgba(2, 6, 23, 0.58) !important;
                    border-left: 1px solid rgba(148, 163, 184, 0.28) !important;
                    border-right: 1px solid rgba(148, 163, 184, 0.28) !important;
                    border-bottom: 1px solid rgba(148, 163, 184, 0.28) !important;
                    border-radius: 0 0 10px 10px !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
        day_num = _current_ship_day_num()
        off_header = f"Off Day {int(day_num)}" if day_num else "Off"
        with st.expander(off_header, expanded=True):
            off_rows_html = "".join(
                (
                    f"<tr style='background:{'rgba(148,163,184,0.10)' if idx % 2 == 0 else 'rgba(148,163,184,0.22)'};'>"
                    f"<td style='text-align:center; padding:6px 8px; border:1px solid rgba(148,163,184,0.35); font-weight:700;'>{int(truck)}</td></tr>"
                )
                for idx, truck in enumerate(off_today_list)
            )
            st.markdown(
                (
                    "<table style='width:100%; border-collapse:collapse; table-layout:fixed;'>"
                    "<thead>"
                    "<tr><th style='text-align:center; padding:6px 8px; border:1px solid rgba(148,163,184,0.35); font-weight:800;'>Truck</th></tr>"
                    "</thead>"
                    f"<tbody>{off_rows_html}</tbody>"
                    "</table>"
                ),
                unsafe_allow_html=True,
            )

        completion = current_load_day_completion()
        scheduled_total = int(completion.get("scheduled_total", 0) or 0)
        loaded_count = int(completion.get("loaded_count", 0) or 0)
        remaining_trucks = [int(t) for t in (completion.get("remaining") or [])]
        remaining_count = len(remaining_trucks)
        progress_header = f"Load Day {int(day_num)} Progress" if day_num else "Load Progress"
        with st.expander(progress_header, expanded=True):
            st.markdown(
                (
                    "<div style='display:flex; flex-direction:column; gap:8px;'>"
                    f"  <div style='padding:8px 10px; border-radius:10px; border:1px solid rgba(148,163,184,0.35); background:rgba(15,23,42,0.45);'>"
                    f"    <div style='font-size:13px; opacity:0.78;'>Total scheduled for day</div>"
                    f"    <div style='font-size:24px; font-weight:900; line-height:1.1; text-align:center;'>{scheduled_total}</div>"
                    "  </div>"
                    f"  <div style='padding:8px 10px; border-radius:10px; border:1px solid rgba(148,163,184,0.35); background:rgba(15,23,42,0.45);'>"
                    f"    <div style='font-size:13px; opacity:0.78;'>Remaining to load</div>"
                    f"    <div style='font-size:24px; font-weight:900; line-height:1.1; text-align:center;'>{remaining_count}</div>"
                    f"    <div style='font-size:12px; opacity:0.72; margin-top:2px;'>Loaded: {loaded_count}</div>"
                    "  </div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            if remaining_trucks:
                show_remaining_key = "load_progress_show_remaining_trucks"
                if show_remaining_key not in st.session_state:
                    st.session_state[show_remaining_key] = False
                toggle_label = "Hide remaining" if st.session_state[show_remaining_key] else "Show remaining"
                if st.button(toggle_label, use_container_width=True, key="load_progress_toggle_remaining_btn"):
                    st.session_state[show_remaining_key] = not bool(st.session_state[show_remaining_key])
                    st.rerun()
                if st.session_state.get(show_remaining_key):
                    st.caption(", ".join(f"#{int(t)}" for t in remaining_trucks))
            else:
                st.session_state["load_progress_show_remaining_trucks"] = False
                st.caption("All scheduled trucks are loaded for this day.")

    with load_main_col:
        history = load_duration_history()
        last_sec = int(history[-1].get("seconds")) if history else None
        avg_sec = average_load_time_seconds([])
        c0, c1 = st.columns(2)
        with c0:
            st.metric("Last load duration", seconds_to_mmss(last_sec) if last_sec is not None else "N/A")
        with c1:
            st.metric("Average load duration", seconds_to_mmss(avg_sec) if avg_sec is not None else "N/A")

        st.write("### Start loading")
        if (len(true_available) == 0) or (inprog_truck is not None):
            if inprog_truck is not None:
                st.caption(f"Truck {int(inprog_truck)} is already in progress.")
            elif cleaned_list:
                if off_today_list:
                    st.caption("No available trucks to start. Unloaded trucks are scheduled Off today.")
                else:
                    st.caption("No available trucks to start.")
            else:
                st.caption("No available trucks to start.")
            if cleaned_list:
                if st.button("Go to Unloaded trucks", use_container_width=True, key="load_go_unloaded"):
                    st.session_state.active_screen = "STATUS_CLEANED"
                    _mark_and_save()
                    st.rerun()
        else:
            clicked_truck = render_numeric_truck_buttons(true_available, "load_start", default_cols=8)
            if clicked_truck is not None:
                t = int(clicked_truck)
                if int(t) in st.session_state.shop_set:
                    st.session_state.pending_start_truck = int(t)
                    st.session_state.active_screen = "STATUS_CLEANED"
                    _mark_and_save()
                    st.rerun()
                start_loading_truck(int(t))
                _mark_and_save()
                st.session_state.active_screen = "IN_PROGRESS"
                st.rerun()

        st.divider()
        next_up = st.session_state.get("next_up_truck")
        if next_up is not None and not st.session_state.inprog_set:
            st.info(f"Next up: Truck {int(next_up)}")
            if st.button(f"Start Next Up (Truck {int(next_up)})", use_container_width=True, key="start_next_up_load"):
                if int(next_up) in st.session_state.shop_set:
                    st.session_state.pending_start_truck = int(next_up)
                    st.session_state.active_screen = "STATUS_CLEANED"
                    _mark_and_save()
                    st.rerun()
                start_loading_truck(int(next_up))
                _mark_and_save()
                st.session_state.active_screen = "IN_PROGRESS"
                st.rerun()

        render_next_up_controls("load")

# --------------------------
# Shorts
# --------------------------
elif st.session_state.active_screen == "SHORTS":
    t = st.session_state.shorts_truck
    render_page_heading(f"Shortages — Truck {t}")

    if t is None:
        st.warning("No truck selected for shortages.")
    else:
        # Overview: show duration, live elapsed if in progress, batch, and management notes
        ensure_shorts_model(t)
        last_dur = st.session_state.load_durations.get(t)
        inprog_now = (t in st.session_state.inprog_set)
        live_elapsed = elapsed_seconds() if inprog_now and (next(iter(st.session_state.inprog_set)) == t) else None
        # find batch id
        batch_id = None
        for bi, b in st.session_state.batches.items():
            if t in b.get("trucks", []):
                batch_id = bi
                break

        st.write("**Overview**")
        c0, c1, c2, c3 = st.columns([1,1,1,1])
        with c0:
            st.metric("Last load", seconds_to_mmss(last_dur) if last_dur is not None else "N/A")
        with c1:
            st.metric("Current", seconds_to_mmss(live_elapsed) if live_elapsed is not None else ("In progress" if inprog_now else "N/A"))
        with c2:
            st.metric("Batch", batch_id if batch_id else "—")
        with c3:
            st.metric("Wearers", int(st.session_state.wearers.get(t, 0) or 0))

        # additional info
        start_ts = st.session_state.load_start_times.get(t)
        finish_ts = st.session_state.load_finish_times.get(t)
        dur = st.session_state.load_durations.get(t)
        shorts_count = len(st.session_state.shorts.get(t, []))
        initials_ts = st.session_state.shorts_initials_ts.get(t)
        if start_ts:
            st.write(f"Started: {_format_ts(start_ts)}")
        if finish_ts:
            st.write(f"Finished: {_format_ts(finish_ts)}")
        if dur is not None:
            st.write(f"Duration: {seconds_to_mmss(dur)}")
        st.write(f"Shorts: {shorts_count} • Initials: {st.session_state.shorts_initials.get(t,'—')}" + (f" (saved {initials_ts})" if initials_ts else ""))
        _, _, note_text = get_truck_notes(t)
        if note_text:
            st.divider()
            st.subheader("Notes")
            st.write(note_text)

        shorts_mode = st.session_state.get("shorts_mode") or SHORTS_MODE_BUTTONS
        if st.session_state.get("shorts_disabled"):
            st.info("Shortages are disabled for today (manual input).")

        edited = None
        if shorts_mode == SHORTS_MODE_BUTTONS:
            pending_delete_key = "shorts_pending_delete"
            pending_delete = st.session_state.get(pending_delete_key)
            if not (isinstance(pending_delete, dict) and int(pending_delete.get("truck", -1)) == int(t)):
                pending_delete = None

            render_shorts_button_flow(t)
            rows = st.session_state.shorts.get(t, [])
            indexed_rows = [(idx, r) for idx, r in enumerate(rows) if _short_row_has_item(r)]

            pending_row_idx = None
            if pending_delete is not None:
                try:
                    pending_row_idx = int(pending_delete.get("row_idx"))
                except Exception:
                    pending_row_idx = None
                if pending_row_idx is None or pending_row_idx < 0 or pending_row_idx >= len(rows) or not _short_row_has_item(rows[pending_row_idx]):
                    pending_row_idx = None
                    st.session_state[pending_delete_key] = None

            if pending_row_idx is not None:
                pending_row = rows[pending_row_idx]
                pending_item = str(pending_row.get("item", "")).strip() or "—"
                pending_qty = pending_row.get("qty")
                pending_qty_text = "—" if pending_qty in (None, "") else str(pending_qty)
                pending_note = str(pending_row.get("note", "")).strip() or "—"
                st.warning(f"Confirm delete: {pending_item} • Qty {pending_qty_text} • Note {pending_note}")
                c_del_1, c_del_2 = st.columns([1, 1])
                with c_del_1:
                    if st.button("Confirm delete", key=f"shorts_delete_confirm_{t}_{pending_row_idx}", use_container_width=True):
                        remaining = [r for idx, r in enumerate(rows) if idx != pending_row_idx]
                        remaining = [r for r in remaining if _short_row_has_item(r)]
                        st.session_state.shorts[t] = remaining if remaining else [{"item": "None", "qty": None, "note": ""}]
                        st.session_state[pending_delete_key] = None
                        st.rerun()
                with c_del_2:
                    if st.button("Cancel", key=f"shorts_delete_cancel_{t}", use_container_width=True):
                        st.session_state[pending_delete_key] = None
                        st.rerun()

            if indexed_rows:
                st.caption("Tap ✕, then confirm deletion. To edit, delete it and add the corrected one above.")
                h1, h2, h3, h4 = st.columns([4, 1, 4, 0.6])
                with h1:
                    st.markdown("**Item**")
                with h2:
                    st.markdown("**Qty**")
                with h3:
                    st.markdown("**Note**")
                with h4:
                    st.markdown("**X**")
                for row_idx, row in indexed_rows:
                    item_text = str(row.get("item", "")).strip()
                    qty_text = row.get("qty")
                    note_text = str(row.get("note", "")).strip()
                    c1, c2, c3, c4 = st.columns([4, 1, 4, 0.6])
                    with c1:
                        st.write(item_text if item_text else "—")
                    with c2:
                        st.write("—" if qty_text in (None, "") else str(qty_text))
                    with c3:
                        st.write(note_text if note_text else "—")
                    with c4:
                        is_pending_row = pending_row_idx is not None and int(pending_row_idx) == int(row_idx)
                        delete_label = "⚠" if is_pending_row else "✕"
                        if st.button(delete_label, key=f"shorts_delete_{t}_{row_idx}"):
                            st.session_state[pending_delete_key] = {"truck": int(t), "row_idx": int(row_idx)}
                            st.rerun()
            else:
                st.session_state[pending_delete_key] = None
                st.caption("No shortages recorded yet.")

            # Move initials input here, after button area but before Save & Done
            preset_initials = ["AG", "AH", "EW", "ML", "NC", "PB", "TH", "Other"]
            current_initials = (st.session_state.shorts_initials.get(t, "") or "").strip()
            preset_default = current_initials if current_initials in preset_initials else "Other"
            initials_pick = st.selectbox(
                "Initials (required)",
                options=preset_initials,
                index=preset_initials.index(preset_default),
                key="shorts_initials_select",
            )
            custom_initials = ""
            if initials_pick == "Other":
                custom_initials = st.text_input(
                    "Custom initials",
                    value=current_initials if current_initials not in preset_initials else "",
                    max_chars=5,
                    key="shorts_initials_custom",
                )
            initials = custom_initials if initials_pick == "Other" else initials_pick

            hist = st.session_state.shorts_initials_history.get(t, [])
            if hist:
                initials_list = ", ".join([str(h.get("initials", "")).strip() for h in hist if str(h.get("initials", "")).strip()])
                if initials_list:
                    st.caption(f"All initials: {initials_list}")

            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("Save & Done", use_container_width=True):
                    rows_to_save = st.session_state.shorts.get(t, [{"item": "None", "qty": None, "note": ""}])
                    if save_shorts_stop_timer(t, initials, rows_to_save):
                        _navigate_after_shorts_save(t)
            with c2:
                st.info("Save stops the timer. 'Save & Done' saves shortages, then prompts 'Ready to begin loading?' for Next Up when queued from Finish Loading; otherwise it returns to Load.")
        else:
            edited = st.data_editor(
                st.session_state.shorts.get(t, [{"item": "None", "qty": None, "note": ""}]),
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "item": st.column_config.SelectboxColumn("Item", options=DEFAULT_SHORT_ITEMS, required=False),
                    "qty": st.column_config.NumberColumn("Qty", min_value=0, step=1, required=False),
                    "note": st.column_config.TextColumn("Note (optional)"),
                },
                key="shorts_editor",
            )
            # Initials input stays in original place for non-button mode
            preset_initials = ["AG", "AH", "EW", "ML", "NC", "PB", "TH", "Other"]
            current_initials = (st.session_state.shorts_initials.get(t, "") or "").strip()
            preset_default = current_initials if current_initials in preset_initials else "Other"
            initials_pick = st.selectbox(
                "Initials (required)",
                options=preset_initials,
                index=preset_initials.index(preset_default),
                key="shorts_initials_select",
            )
            custom_initials = ""
            if initials_pick == "Other":
                custom_initials = st.text_input(
                    "Custom initials",
                    value=current_initials if current_initials not in preset_initials else "",
                    max_chars=5,
                    key="shorts_initials_custom",
                )
            initials = custom_initials if initials_pick == "Other" else initials_pick

            hist = st.session_state.shorts_initials_history.get(t, [])
            if hist:
                initials_list = ", ".join([str(h.get("initials", "")).strip() for h in hist if str(h.get("initials", "")).strip()])
                if initials_list:
                    st.caption(f"All initials: {initials_list}")

            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("Save & Done", use_container_width=True):
                    rows_to_save = edited if edited is not None else st.session_state.shorts.get(t, [{"item": "None", "qty": None, "note": ""}])
                    if save_shorts_stop_timer(t, initials, rows_to_save):
                        _navigate_after_shorts_save(t)
            with c2:
                st.info("Save stops the timer. 'Save & Done' saves shortages, then prompts 'Ready to begin loading?' for Next Up when queued from Finish Loading; otherwise it returns to Load.")
