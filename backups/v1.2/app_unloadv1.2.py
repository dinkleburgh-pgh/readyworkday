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
_APP_VERSION = "1.3.0"
_APP_DATE = "19930616"  

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

BATCH_COUNT = 6
BATCH_CAP = 400  # cannot go over

DEFAULT_WARN_MIN = 15  # default 15 minutes

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
        if k in {"cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "spare_set", "special_set"}:
            out[k] = set(map(int, v)) if v else set()
        elif k == "run_date":
            out[k] = date.fromisoformat(v) if v else None
        elif k == "ship_dates":
            out[k] = [date.fromisoformat(s) for s in v] if v else []
        elif k in {"wearers", "shop_notes", "shop_spares", "off_notes", "sup_notes_global", "sup_notes_daily", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule", "shop_prev_status", "shorts_button_state"}:
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
        if k in {"cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "spare_set", "special_set"}:
            data[k] = sorted(list(v))
        elif k == "run_date":
            data[k] = v.isoformat() if v else None
        elif k == "last_setup_date":
            data[k] = v.isoformat() if v else None
        elif k == "ship_dates":
            data[k] = [d.isoformat() for d in v]
        elif k in {"wearers", "shop_notes", "shop_spares", "off_notes", "sup_notes_global", "sup_notes_daily", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule", "shop_prev_status", "shorts_button_state"}:
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
    logging.debug("save_state() called")


def archive_current_state(run_date_key: str | None):
    if not run_date_key:
        return
    path = _history_state_path(run_date_key)
    _write_state_file(path, _serialize_state())


def apply_run_config(run_date: date, ship_dates: list[date]):
    new_key = _run_date_key(run_date)
    old_key = _current_run_date_key()
    if old_key and new_key and old_key != new_key:
        archive_current_state(old_key)
    st.session_state.run_date = run_date
    st.session_state.ship_dates = ship_dates
    st.session_state.setup_done = True
    st.session_state.last_setup_date = date.today()
    st.session_state.run_date_key = new_key
    if old_key != new_key:
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

defaults = {
    # work states
    "cleaned_set": set(),
    "inprog_set": set(),             # max 1
    "loaded_set": set(),

    # management / off + shop
    "off_set": set(),
    "spare_set": set(),
    "off_notes": {},                 # {truck: text}
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

    # unload in-progress (cleaning) state
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
    "next_after_truck": None,
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
    "off_schedule": {i: [] for i in range(1, 6)},

    # in-progress tick (for timer refresh)
    "inprog_last_tick": 0.0,

    # shop notice UI state
    "hide_shop_notice": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        # prefer loaded state when available
        if k in loaded:
            st.session_state[k] = loaded[k]
        else:
            st.session_state[k] = v

# Auto-mark trucks as off for current load day

# Do not auto-update off_set with off_today. Off trucks should not be automatically sent to Out Of Service.

# Force app theme to dark regardless of device preferences.
st.session_state.ui_theme = "Dark"

# Immediately persist any state changes that represent important actions
save_state()

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
                    .stSelectbox, .stSelectbox label, .stSelectbox div, .stSelectbox span,
                    .stTextInput input, .stNumberInput input, .stTextArea textarea,
                    .stRadio div, .stMultiSelect div {
                        color: #0f172a !important;
                    }
                    [data-testid="stSelectbox"] div[role="combobox"],
                    [data-testid="stMultiSelect"] div[role="combobox"],
                    [data-testid="stNumberInput"] input,
                    [data-testid="stTextInput"] input,
                    [data-testid="stTextArea"] textarea {
                        background-color: #ffffff !important;
                        border: 1px solid rgba(15, 23, 42, 0.25) !important;
                    }
                    [data-testid="stSelectbox"] div[role="listbox"],
                    [data-testid="stMultiSelect"] div[role="listbox"] {
                        background-color: #ffffff !important;
                        color: #0f172a !important;
                        border: 1px solid rgba(15, 23, 42, 0.25) !important;
                    }
                    .stMarkdown, .stText, .stCaption, .stMetric, .stSelectbox, .stRadio, .stNumberInput, .stTextInput {
                        color: #0f172a;
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
        .shop-notice {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.65);
            margin: 0 0 2px 0;
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
        .shop-notice.flash {
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35), 0 12px 26px rgba(0, 0, 0, 0.22);
        }
        .shop-notice.flash-collapsed {
            box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.35), 0 10px 20px rgba(0, 0, 0, 0.20);
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
    if force or current != last:
        seq = int(st.session_state.get("nav_seq") or 0) + 1
        st.session_state.nav_seq = seq
        st.session_state.last_screen_for_history = current
        _set_query_params(page=_page_param_for_screen(current), nav=str(seq), truck=None, pick=None, start=None, **{"from": None})

# ==========================================================
# Helpers
# ==========================================================
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
        msg = html.escape(str(entry.get("msg", "")))
        kind = entry.get("kind") or "shop"
        body_style = " style='color:#22c55e; font-weight:700;'" if kind == "return" else ""
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
            const lastId = getStored('shopNoticeLastId', '');
            if (lastId !== id) {
                const wasCollapsed = getStored('shopNoticeCollapsed', '0') === '1';
                setStored('shopNoticeLastId', id);
                setStored('shopNoticeCollapsed', '0');
                notice.classList.remove('collapsed');
                toggle.textContent = 'Collapse';
                notice.classList.remove('flash');
                notice.classList.remove('flash-collapsed');
                void notice.offsetWidth;
                notice.classList.add('flash');
                if (wasCollapsed) {
                    notice.classList.add('flash-collapsed');
                }
                setTimeout(() => {
                    notice.classList.remove('flash');
                    notice.classList.remove('flash-collapsed');
                }, 3600);
            }
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
            applyState();
            if (!bar.dataset.bound) {
                bar.addEventListener('click', function(){
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

def _is_mobile_client() -> bool:
    try:
        ctx = getattr(st, "context", None)
        headers = getattr(ctx, "headers", None) if ctx is not None else None
        user_agent = str(headers.get("user-agent", "")).lower() if headers else ""
    except Exception:
        user_agent = ""
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
    if _is_mobile_client():
        return max(2, min(4, int(default_cols)))
    return max(1, int(default_cols))


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

def render_numeric_truck_buttons(
    trucks: list[int],
    key_prefix: str,
    default_cols: int = 8,
    trailing_button_label: str | None = None,
    trailing_button_value: str | None = None,
    flash_trucks: set[int] | None = None,
    force_text_color: str | None = None,
) -> int | str | None:
    ordered = sorted({int(t) for t in (trucks or [])})
    if not ordered and not trailing_button_label:
        return None

    live_button_styling = bool(st.session_state.get("live_button_styling", True))
    trailing_labels_json = json.dumps([str(trailing_button_label).strip()]) if trailing_button_label else "[]"
    force_text_color_json = json.dumps(_normalize_hex_color(force_text_color, "#000000") if force_text_color else "")

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
    for truck_num in ordered:
        bg, border, text_color = _truck_status_colors(truck_num, status_color_map)
        color_map[str(int(truck_num))] = {"bg": bg, "border": border, "fg": text_color}

    if live_button_styling and (color_map or trailing_button_label):
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
    if trailing_button_label:
        trailing_value = trailing_button_value if trailing_button_value is not None else trailing_button_label
        button_entries.append((str(trailing_button_label), str(trailing_value), False))

    cols_per_row = _truck_grid_columns(default_cols)
    for start in range(0, len(button_entries), cols_per_row):
        row_vals = button_entries[start : start + cols_per_row]
        row_cols = st.columns(cols_per_row)
        for idx, entry in enumerate(row_vals):
            label, value, _is_numeric = entry
            with row_cols[idx]:
                if st.button(label, key=f"{key_prefix}_{value}", use_container_width=True, type="primary"):
                    if _is_numeric:
                        return int(value)
                    return str(value)
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
        st.session_state.cleaned_set.add(t)
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
        st.session_state.off_set.add(t)
    elif status_label == "Spare":
        st.session_state.spare_set.add(t)
    elif status_label == "Special":
        st.session_state.special_set.add(t)

    if was_shop and status_label != "Shop" and emit_shop_return_notice:
        push_shop_notice(f"Returned from shop: #{t} — {status_label}", kind="return")

def render_fleet_management():
    st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Select Truck</div>", unsafe_allow_html=True)
    selected = st.session_state.get("sup_manage_truck")
    if selected is None and st.session_state.get("sup_manage_new_mode"):
        st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Step 2 - Add new truck</div>", unsafe_allow_html=True)
        c_back_new = st.columns(3)[1]
        with c_back_new:
            if st.button("Back to Step 1", use_container_width=True, key="sup_manage_new_back"):
                st.session_state.sup_manage_new_mode = False
                st.rerun()

        st.divider()
        added_truck = _render_add_truck_to_fleet_form(
            number_key="sup_add_truck_num",
            button_key="sup_add_truck_add",
        )
        if added_truck is not None:
            st.session_state.sup_manage_new_mode = False
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
            flash_trucks=flash_trucks,
        )
        if clicked_truck == "__NEW_TRUCK__":
            st.session_state.sup_manage_new_mode = True
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()
        if clicked_truck is not None:
            st.session_state.sup_manage_new_mode = False
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
    st.markdown(
        (
            "<div style='max-width:560px; margin:6px auto 10px auto; padding:18px 12px; "
            "border:2px solid rgba(245,158,11,0.45); border-radius:16px; "
            "background:rgba(15,23,42,0.55); box-shadow:0 12px 28px rgba(0,0,0,0.22);'>"
            "  <div style='text-align:center; font-size:36px; font-weight:900; margin:0; "
            "  color:#f59e0b; text-shadow:-1px 0 #000, 0 1px #000, 1px 0 #000, 0 -1px #000;'>"
            f"  Truck {sel}"
            "  </div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    c_back = st.columns(3)[1]
    with c_back:
        if st.button("Change Truck", use_container_width=True, key="sup_manage_back"):
            st.session_state.sup_manage_truck = None
            st.session_state.sup_manage_new_mode = False
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()

    action = st.session_state.get("sup_manage_action")
    if not action:
        st.markdown("<div style='text-align:center; font-weight:800; font-size:22px;'>Step 2 - Choose option</div>", unsafe_allow_html=True)
        action_labels = ["Shop", "Status", "Notes", "Ran Special", "Add/Remove"]
        cols = st.columns(3)
        for idx, label in enumerate(action_labels):
            col = cols[idx % 3]
            with col:
                if st.button(label, key=f"sup_manage_action_btn_{label}", use_container_width=True):
                    st.session_state.sup_manage_action = label
                    st.rerun()
        return

    c_back_action = st.columns(3)[1]
    with c_back_action:
        if st.button("Back to Step 2", use_container_width=True, key="sup_manage_back_action"):
            st.session_state.sup_manage_action = None
            st.session_state.sup_manage_pref_action = None
            st.rerun()
    st.markdown(f"<div style='text-align:center; font-weight:800; font-size:22px;'>Step 3 - {action}</div>", unsafe_allow_html=True)

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

        fleet_options = sorted({int(t) for t in FLEET} | {sel})
        extra_target_options = [t for t in fleet_options if t != sel]
        target_anchor_key = "sup_manage_status_targets_anchor"
        extra_targets_key = "sup_manage_status_extra_targets"
        if st.session_state.get(target_anchor_key) != sel:
            st.session_state[target_anchor_key] = sel
            st.session_state[extra_targets_key] = []

        extra_targets = st.multiselect(
            "Select more trucks",
            options=extra_target_options,
            key=extra_targets_key,
        )
        target_trucks = sorted({int(sel)} | {int(t) for t in (extra_targets or [])})
        selected_statuses = sorted({current_status_label(t) for t in target_trucks})
        if len(selected_statuses) == 1:
            st.caption(f"Current status for selected: {selected_statuses[0]}")
        else:
            st.caption("Current status for selected: Mixed")

        status_options = ["Dirty", "Unloaded", "In Progress", "Loaded", "Shop", "Out Of Service", "Spare"]
        status_sel = st.selectbox("Status", status_options, index=status_options.index(cur_status) if cur_status in status_options else 0, key="sup_manage_status_sel")
        shop_load_on = ""
        if status_sel == "Shop":
            shop_load_on = st.text_input("Load On? (optional)", key="sup_manage_status_load_on")
        if st.button("Apply status change", key="sup_manage_apply_status"):
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
                    status_feedback = f"Truck {target_trucks[0]} status updated to {status_sel}."
                else:
                    status_feedback = f"Updated {len(target_trucks)} trucks to {status_sel}."
                st.session_state[status_feedback_key] = status_feedback
                st.session_state.sup_pending_status = None
                st.rerun()

    elif action == "Batch":
        st.write("### Batch assignment")
        w = st.number_input("Wearers", min_value=0, step=1, value=int(st.session_state.get("wearers", {}).get(sel, 0)), key="sup_manage_wearers")
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
                        st.session_state.cleaned_set.add(sel)
                        _mark_and_save()
                        st.success(f"Truck {sel} assigned to Batch {pending_a.get('batch')}.")
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
            if sel not in st.session_state.shop_set:
                st.session_state.shop_prev_status[int(sel)] = current_status_label(sel)
            st.session_state.shop_set.add(sel)
            st.session_state.shop_notes[sel] = (reason or "").strip()
            spare_val = (spare or "").strip()
            if spare_val:
                st.session_state.shop_spares[sel] = spare_val
            else:
                st.session_state.shop_spares.pop(sel, None)
            msg = f"Sent to shop: #{sel}" + (f" — {reason}" if reason else "")
            if spare_val:
                msg += f" (Load on: {spare_val})"
            push_shop_notice(msg, kind="shop", notice_type="shop_send", truck=sel)
            log_action(f"Truck {sel} sent to Shop")
            if st.session_state.get("next_up_truck") == sel:
                st.session_state.next_up_truck = None
            st.session_state.cleaned_set.discard(sel)
            st.session_state.inprog_set.discard(sel)
            st.session_state.loaded_set.discard(sel)
            st.session_state.off_set.discard(sel)
            st.session_state.spare_set.discard(sel)
            remove_truck_from_batches(sel)
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
            if sel in st.session_state.shop_set:
                st.session_state.shop_set.discard(sel)
                st.session_state.shop_notes.pop(sel, None)
                st.session_state.shop_spares.pop(sel, None)
                prev = st.session_state.shop_prev_status.pop(int(sel), None)
                if prev == "Loaded":
                    st.session_state.loaded_set.add(sel)
                elif prev == "In Progress":
                    start_loading_truck(sel)
                elif prev == "Out Of Service":
                    st.session_state.off_set.add(sel)
                elif prev == "Spare":
                    st.session_state.spare_set.add(sel)
                elif prev == "Special":
                    st.session_state.special_set.add(sel)
                else:
                    pass
                prev_label = "Dirty" if prev in ("Unloaded", "Off") else prev
                push_shop_notice(
                    f"Returned from shop: #{sel}" + (f" — {prev_label}" if prev_label else ""),
                    kind="return",
                )
                log_action(f"Truck {sel} returned from Shop")
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

def normalize_states():
    # Shop excludes everything else
    st.session_state.cleaned_set -= st.session_state.shop_set
    st.session_state.inprog_set -= st.session_state.shop_set
    st.session_state.loaded_set -= st.session_state.shop_set

    # OOS and Spare exclude active workflow/status sets
    blocked = set(st.session_state.off_set) | set(st.session_state.get("spare_set", set()))
    st.session_state.cleaned_set -= blocked
    st.session_state.inprog_set -= blocked
    st.session_state.loaded_set -= blocked
    st.session_state.shop_set -= blocked
    st.session_state.special_set -= blocked

    # Off trucks persist in off_set until explicitly changed
    # Do NOT auto-move Off trucks to Unloaded or any other status

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
    st.session_state.inprog_set = {t}
    st.session_state.inprog_start_time = time.time()
    st.session_state.load_start_times[t] = st.session_state.inprog_start_time
    st.session_state.load_finish_times.pop(t, None)
    if st.session_state.get("next_up_truck") == t:
        st.session_state.next_up_truck = st.session_state.get("next_after_truck")
        st.session_state.next_after_truck = None
    if st.session_state.get("next_after_truck") == t:
        st.session_state.next_after_truck = None
    log_action(f"Start loading Truck {t}")

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
    next_after = st.session_state.get("next_after_truck")
    off_today = off_trucks_for_today()
    st.write("### Next up queue")
    if current:
        st.info(f"Current next up: Truck {int(current)}")
        if next_after:
            st.caption(f"Current in-progress unload: Truck {int(next_after)}")
    else:
        st.caption("No next-up truck set.")
    if not unloaded:
        st.caption("No Unloaded trucks available.")
        return
    pick = st.selectbox("Select next up", options=unloaded, key=f"next_up_select_{context_key}")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Set Next Up", key=f"next_up_set_{context_key}", use_container_width=True):
            if int(pick) in off_today:
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
                if st.button(off_button_label, key=f"next_after_show_off_{context_key}", use_container_width=True):
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
    preserved_oos = set(st.session_state.get("off_set") or set())
    preserved_spares = set(st.session_state.get("spare_set") or set())
    # Reset all trucks to dirty, preserving shop status, then apply off schedule.
    st.session_state.cleaned_set = set()
    st.session_state.loaded_set = set()
    st.session_state.inprog_set = set()
    st.session_state.special_set = set()
    st.session_state.off_set = preserved_oos
    st.session_state.spare_set = preserved_spares
    st.session_state.off_notes = {}

    st.session_state.inprog_start_time = None
    st.session_state.load_start_times = {}
    st.session_state.load_finish_times = {}
    st.session_state.load_durations = {}
    st.session_state.break_start_time = None
    st.session_state.break_used = False

    st.session_state.next_up_truck = None
    st.session_state.next_after_truck = None
    st.session_state.next_up_return_screen = None
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
    for s in ("cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "spare_set", "special_set"):
        try:
            st.session_state[s].discard(t)
        except Exception:
            pass

    # Remove batch membership
    remove_truck_from_batches(t)

    # Remove wearers and notes
    st.session_state.wearers.pop(t, None)
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
    ensure_shorts_model(t)
    rows = list(st.session_state.shorts.get(t, []))
    rows = [r for r in rows if _short_row_has_item(r)]
    rows.append({"item": label, "qty": int(qty), "note": ""})
    st.session_state.shorts[t] = rows

def render_shorts_button_flow(truck: int):
    t = int(truck)
    state = _get_shorts_button_state(t)
    step = state.get("step") or "category"
    category = state.get("category")
    bulk_group = state.get("bulk_group")
    item = state.get("item")

    st.write("### Select Shortages")
    if step == "category":
        cols = st.columns(len(SHORTS_BUTTON_MAP.keys()) + 1)
        # Category buttons
        for idx, cat in enumerate(SHORTS_BUTTON_MAP.keys()):
            with cols[idx]:
                if st.button(cat, use_container_width=True, key=f"shorts_cat_{t}_{cat}"):
                    next_step = "bulk_group" if cat == "Bulk" else "item"
                    _set_shorts_button_state(t, {"step": next_step, "category": cat, "bulk_group": None, "item": None, "qty": 1})
                    st.rerun()
        # Recents button
        with cols[len(SHORTS_BUTTON_MAP.keys())]:
            if st.button("Recents", use_container_width=True, key=f"shorts_cat_{t}_recents"):
                _set_shorts_button_state(t, {"step": "recents", "category": None, "bulk_group": None, "item": None, "qty": 1})
                st.rerun()

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
        cols = st.columns(3)
        for idx, group in enumerate(groups):
            with cols[idx % 3]:
                if st.button(group, use_container_width=True, key=f"shorts_bulk_{t}_{group}"):
                    _set_shorts_button_state(t, {"step": "item", "category": "Bulk", "bulk_group": group, "item": None, "qty": 1})
                    st.rerun()
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
        cols = st.columns(3)
        for idx, it in enumerate(items):
            with cols[idx % 3]:
                if st.button(it, use_container_width=True, key=f"shorts_item_{t}_{it}"):
                    state = {"step": "qty", "category": category, "bulk_group": bulk_group, "item": it, "qty": 1}
                    _set_shorts_button_state(t, state)
                    st.rerun()
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
        quick_cols = st.columns(len(quick_amounts))
        # Quick-select buttons directly add the item
        for idx, val in enumerate(quick_amounts):
            with quick_cols[idx]:
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

    display_text_json = json.dumps(display_text)
    dot_color_json = json.dumps(_normalize_hex_color(color, "#6b7280"))
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const root = window.parent.document;
                const sidebar = root.querySelector('section[data-testid="stSidebar"]');
                if (!sidebar) return;

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
                const target = normalize({display_text_json});
                const dotColor = {dot_color_json};
                const buttons = sidebar.querySelectorAll('.stButton > button');
                buttons.forEach((btn) => {{
                    const raw = normalize(btn.innerText || btn.textContent || '');
                    if (raw !== target) return;
                    btn.classList.add('status-dot-badge');
                    btn.style.setProperty('--status-dot-color', dotColor);
                }});
            }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

def render_truck_bubbles(trucks: list[int], from_page: str | None = None):
    # This is what you asked for: bubbled lists INSIDE each status link page
    if not trucks:
        st.write("None")
        return

    clicked_truck = render_numeric_truck_buttons(trucks, f"bubble_{from_page}", default_cols=8)
    if clicked_truck is not None:
        t = int(clicked_truck)
        if from_page == "UNLOAD":
            st.session_state["unload_truck_select"] = int(t)
            st.session_state.active_screen = "BATCH"
        elif from_page == "STATUS_CLEANED":
            st.session_state.selected_truck = int(t)
            st.session_state.pending_start_truck = int(t)
        elif from_page == "STATUS_LOADED":
            st.session_state.selected_truck = int(t)
            st.session_state.active_screen = "STATUS_LOADED"
        elif from_page == "STATUS_DIRTY":
            st.session_state["unload_truck_select"] = int(t)
            st.session_state.active_screen = "BATCH"
        elif from_page == "STATUS_SHOP":
            st.session_state.selected_truck = int(t)
            st.session_state.active_screen = "TRUCK"
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

# ==========================================================
# Setup-first enforcement
# ==========================================================

# Auto-advance workday if last_setup_date is not today
if st.session_state.get("last_setup_date") != date.today():
    # Only auto-advance if run_date is not today
    today = date.today()
    # If run_date is not today, set run_date to today and ship_dates to [today+1]
    st.session_state.run_date = today
    st.session_state.ship_dates = [today + timedelta(days=1)]
    st.session_state.run_date_key = today.isoformat()
    st.session_state.setup_done = True
    st.session_state.last_setup_date = today
    save_state()

# Only prompt to configure/start once per calendar day. If the app hasn't
# been setup yet, or the last setup date doesn't match today, force SETUP.
if (not st.session_state.setup_done) or (st.session_state.get("last_setup_date") != date.today()):
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
dirty_trucks = sorted(
    set(FLEET)
    - st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - oos_spare_set
)
cleaned_list = sorted(st.session_state.cleaned_set)
loaded_list = sorted(st.session_state.loaded_set)
shop_list = sorted(st.session_state.shop_set)
inprog_truck = next(iter(st.session_state.inprog_set)) if st.session_state.inprog_set else None
off_today = off_trucks_for_today()

true_available = sorted(
    st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - oos_spare_set
    - off_today
)

# If a start attempt was blocked because another truck is in progress, show
# a global suggestion to navigate to the in-progress page (unless we're
# already on STATUS_CLEANED or IN_PROGRESS which already show the message).
if st.session_state.get("start_blocked") and st.session_state.active_screen not in ("STATUS_CLEANED", "IN_PROGRESS"):
    blocking = st.session_state.get("start_blocking_truck")
    attempt = st.session_state.get("start_attempt_truck")
    st.error(f"Cannot start Truck {attempt}: Truck {blocking} is already in progress. Visit the In Progress page?")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Go to in-progress truck", key="go_to_inprog_from_block"):
            st.session_state.active_screen = "IN_PROGRESS"
            # clear the start-block flags
            st.session_state.start_blocked = False
            st.session_state.start_blocking_truck = None
            st.session_state.start_attempt_truck = None
            st.rerun()
    with c2:
        if st.button("Dismiss", key="dismiss_start_block"):
            st.session_state.start_blocked = False
            st.session_state.start_blocking_truck = None
            st.session_state.start_attempt_truck = None

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
if raw_truck and requested in ("TRUCK", "SHORTS", "IN_PROGRESS"):
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
    if requested != prev_requested or requested == st.session_state.active_screen:
        st.session_state.active_screen = requested
st.session_state.last_requested_page = requested

# When browser Back/Forward changes the URL, force a rerun to refresh the page.
if nav_from_url and requested in valid_pages and requested != st.session_state.active_screen:
    st.session_state.active_screen = requested
    st.rerun()

# If the URL is stale (user navigated via UI), keep the URL page in sync.
if requested and requested == prev_requested and requested != st.session_state.active_screen:
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
cleaned_list_no_oos = [t for t in cleaned_list if t not in oos_spare_set]
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
    st.subheader(title)


    mapping = {
        "STATUS_DIRTY": dirty_trucks,
        "STATUS_CLEANED": cleaned_list,
        "STATUS_LOADED": loaded_list,
        "STATUS_SHOP": shop_list,
        "STATUS_OFF": sorted(list(off_today)),
        "STATUS_OOS": sorted(list(oos_spare_set)),
    }
    trucks = mapping.get(st.session_state.active_screen, [])

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
    else:
        # Always show the truck bubbles list
        st.write("### Trucks")
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
            st.warning(f"Truck {t} is not currently marked Loaded.")
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
                st.warning(f"Next up: Truck {int(next_up)}. Start loading now?")
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                with c2:
                    if st.button("Yes, start next up", use_container_width=True, key="start_next_up_status_loaded"):
                        if int(next_up) in st.session_state.shop_set:
                            st.session_state.pending_start_truck = int(next_up)
                            st.session_state.active_screen = "STATUS_CLEANED"
                            _mark_and_save()
                            st.rerun()
                        start_loading_truck(int(next_up))
                        _mark_and_save()
                        st.session_state.active_screen = "IN_PROGRESS"
                        st.rerun()
                with c3:
                    if st.button("Change Next Up", use_container_width=True, key="change_next_up_status_loaded"):
                        st.session_state.active_screen = "LOAD"
                        _mark_and_save()
                        st.rerun()
                c5, c6, c7 = st.columns([1, 2, 1])
                with c6:
                    if not st.session_state.get("break_used"):
                        if st.button("Start Break", use_container_width=True, key="start_break_status_loaded"):
                            st.session_state.break_start_time = time.time()
                            st.session_state.break_used = True
                            st.session_state.active_screen = "BREAK"
                            _mark_and_save()
                            st.rerun()
            st.divider()
            if st.button("Open short sheet", use_container_width=True):
                st.session_state.shorts_truck = t
                ensure_shorts_model(t)
                st.session_state.active_screen = "SHORTS"
                _mark_and_save()
                st.rerun()
            if st.button("Go to Unloaded trucks", use_container_width=True):
                st.session_state.active_screen = "STATUS_CLEANED"
                _mark_and_save()
                st.rerun()

    if st.session_state.active_screen == "STATUS_CLEANED" and st.session_state.get("pending_start_truck"):
        pending_t = int(st.session_state.get("pending_start_truck"))
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
            st.warning(f"Do you want to Load truck {pending_t}?")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Yes, start loading", use_container_width=True, key="confirm_start_load"):
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
                padding-top: 0.15rem !important;
                padding-left: 0.45rem !important;
                padding-right: 0.9rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


    reminder = st.session_state.get("daily_notes", "")
    safe_reminder = html.escape(reminder).replace("\n", "<br>")
    no_notes = "<span style=\"opacity:0.5;\">No notes set.</span>"
    notes_html = safe_reminder if safe_reminder else no_notes
    left_col, center_col = st.columns([1, 2], gap="small")
    with left_col:
        st.markdown(
            (
                "<div style='width:100%; margin:-4px 0 10px 0; position:-webkit-sticky; position:sticky; top:68px; align-self:flex-start; z-index:20;'>"
                "  <div id='daily-notes-box' style='width:100%; min-width:260px; "
                "      border-radius:24px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); "
                "      background:rgba(15,23,42,0.65); box-shadow:0 20px 48px rgba(0,0,0,0.28); max-height:calc(100vh - 120px); display:flex; flex-direction:column;'>"
                "    <div id='daily-notes-bar' style='display:flex; align-items:center; justify-content:center; "
                "        padding:16px 20px; font-weight:900; font-size:24px; letter-spacing:0.24em; text-transform:uppercase; "
                "        background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); cursor:default; position:relative;'>"
                "      <span style='margin:0 auto;'>Daily Notes</span>"
                "    </div>"
                "    <div id='daily-notes-body' style='padding:20px 24px; font-size:22px; line-height:1.25; overflow-y:auto;'>"
                f"      {notes_html}"
                "    </div>"
                "  </div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with center_col:
        if not inprog_truck:
            st.info("No truck currently in progress.")
            if true_available:
                if st.button("View Unloaded trucks to start loading", use_container_width=True, key="start_inprog_suggested"):
                    st.session_state.active_screen = "STATUS_CLEANED"
                    _mark_and_save()
                    st.rerun()
            else:
                st.caption("No available trucks to start loading.")
        else:
            elapsed = elapsed_seconds()
            global_note, daily_note, note_text = get_truck_notes(inprog_truck)
            if note_text:
                sections = []
                if global_note:
                    safe_global = html.escape(global_note).replace("\n", "<br>")
                    sections.append(
                        "<div style='padding-bottom:12px; margin-bottom:12px; border-bottom:2px solid rgba(255,255,255,0.18);'>"
                        "  <div style='font-size:22px; letter-spacing:0.24em; text-transform:uppercase; opacity:0.7;'>General Notes</div>"
                        f"  <div style='font-size:28px;'>{safe_global}</div>"
                        "</div>"
                    )
                if daily_note:
                    safe_daily = html.escape(daily_note).replace("\n", "<br>")
                    sections.append(
                        "<div>"
                        "  <div style='font-size:22px; letter-spacing:0.24em; text-transform:uppercase; opacity:0.7;'>Daily Notes</div>"
                        f"  <div style='font-size:28px;'>{safe_daily}</div>"
                        "</div>"
                    )
                safe_note = "".join(sections)
                st.markdown(
                    (
                        "<div style='width:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; margin:0;'>"
                        "  <div style='text-align:center; margin:0 0 1px 0;'>"
                        "    <div style='font-size:32px; letter-spacing:0.36em; text-transform:uppercase; opacity:0.85; font-weight:900; margin-bottom:1px;'>Current Truck</div>"
                        f"    <div style='font-size:112px; font-weight:900; line-height:1.0; color:#facc15;'>#{inprog_truck}</div>"
                        "  </div>"
                        "  <div id='inprog-notes' style='width:560px; max-width:80vw; border-radius:24px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); background:rgba(15,23,42,0.65); box-shadow:0 20px 48px rgba(0,0,0,0.28);'>"
                        "    <div id='inprog-notes-bar' style='display:flex; align-items:center; justify-content:space-between; padding:16px 20px; font-weight:900; font-size:24px; letter-spacing:0.24em; text-transform:uppercase; background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); cursor:pointer; position:relative;'>"
                        "      <span style='margin:0 auto;'>Notes</span>"
                        "    </div>"
                        "    <div id='inprog-notes-body' style='padding:20px 24px; font-size:28px; line-height:1.25;'>"
                        f"      {safe_note}"
                        "    </div>"
                        "  </div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    (
                        "<div style='text-align:center; margin:0;'>"
                        "  <div style='font-size:32px; letter-spacing:0.36em; text-transform:uppercase; opacity:0.85; font-weight:900;'>Current Truck</div>"
                        f"  <div style='font-size:112px; font-weight:900; line-height:1.0; color:#facc15;'>#{inprog_truck}</div>"
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
            timer_html = f"""
                    <div style='position:relative; width:100%; margin:0 0 16px 0;'>
                        <div id='inprog-timer-box' style='width:560px; max-width:80vw; margin:0 auto; border-radius:24px; overflow:hidden; border:2px solid rgba(34,197,94,0.45); background:rgba(15,23,42,0.65); box-shadow:0 20px 48px rgba(0,0,0,0.28);'>
                            <div id='inprog-timer-bar' style="display:flex; align-items:center; justify-content:center; padding:16px 20px; font-weight:900; font-size:24px; letter-spacing:0.24em; text-transform:uppercase; background:linear-gradient(90deg, rgba(34,197,94,0.28), rgba(59,130,246,0.26)); cursor:default; position:relative; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; color:#fff;">
                                <span style="margin:0 auto; font-weight:900;">ELAPSED TIME</span>
                            </div>
                            <div id='inprog-timer-body' style='padding:20px 24px; font-size:96px; line-height:1.1; text-align:center; font-weight:800; color:{GREEN};'>
                                <span id='truck-elapsed'>{seconds_to_mmss(elapsed)}</span>
                            </div>
                            <div id='truck-elapsed-warn' style='display:{warn_visible}; color:{ORANGE}; font-weight:700; text-align:center;'>{warn_text}</div>
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
                    const tick = () => {{
                        const now = Math.floor(Date.now() / 1000);
                        elapsed = Math.max(0, now - startEpoch);
                        const el = document.getElementById('truck-elapsed');
                        const warnEl = document.getElementById('truck-elapsed-warn');
                        const timerBody = document.getElementById('inprog-timer-body');
                        if (el) {{
                            el.textContent = fmt(elapsed);
                            el.style.color = colorFor(elapsed, warn);
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
                }} catch(e){{console.error(e);}}
            }})();
            </script>
            """
            components.html(timer_html, height=300)

            avg_all = average_load_time_seconds([])
            st.markdown(
                (
                    "<div style='text-align:center; margin-top:-36px; margin-bottom:24px; font-size:28px; opacity:0.75;'>"
                    f"Average load time: {seconds_to_mmss(avg_all) if avg_all is not None else 'N/A'}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            next_up = st.session_state.get("next_up_truck")
            if next_up is not None:
                st.markdown(
                    (
                        "<div style='text-align:center; margin:32px 0 4px 0;'>"
                        "  <div style='font-size:24px; letter-spacing:0.28em; text-transform:uppercase; opacity:0.7;'>Next Up</div>"
                        f"  <div style='font-size:112px; font-weight:900; line-height:1.0; color:#3b82f6;'>#{int(next_up)}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                avg_next = average_load_time_seconds([int(next_up)])
                st.markdown(
                    (
                        "<div style='text-align:center; margin-top:4px; font-size:28px; opacity:0.75;'>"
                        f"Avg for next up: {seconds_to_mmss(avg_next) if avg_next is not None else 'N/A'}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='text-align:center; font-size:26px; margin-top:8px; opacity:0.6;'>Next up: None</div>",
                    unsafe_allow_html=True,
                )

            st.divider()
            if st.session_state.get("shorts_disabled"):
                if st.button("Mark Loaded (shortages handled manually)", use_container_width=True):
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
                    st.success(f"Truck {t} marked Loaded (shortages handled manually).")
                    st.session_state.active_screen = "STATUS_LOADED"
                    st.rerun()
            else:
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
                        st.session_state.active_screen = "SHORTS"
                        _mark_and_save()
                        st.rerun()
                with c2:
                    if st.button("Skip Shortages", use_container_width=True):
                        st.session_state.inprog_skip_confirm = True
                    if st.button("Finish Loading", use_container_width=True, key="inprog_finish_loading"):
                        _finish_in_progress_loading(f"Truck {int(inprog_truck)} marked Loaded.")

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

            st.divider()
            render_next_up_controls("inprog")

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
    return_time_struct = time.localtime(return_time_epoch)
    return_hour = return_time_struct.tm_hour
    return_min = return_time_struct.tm_min
    return_sec = return_time_struct.tm_sec
    ampm = "AM" if return_hour < 12 else "PM"
    hour12 = return_hour % 12
    hour12 = hour12 if hour12 else 12
    return_time_str = f"{hour12}:{return_min:02d}:{return_sec:02d} {ampm}"

    break_html = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;"
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:2px; margin:0;"
            <div id="break-box" style="
                padding:4px 8px; border-radius:12px; border:1px solid rgba(255,255,255,0.12);
                background:linear-gradient(135deg, rgba(59,130,246,0.18), rgba(16,185,129,0.12));
                box-shadow:0 6px 18px rgba(0,0,0,0.12);"
                <div id="break-remaining" style="font-size:168px; font-weight:900; line-height:1.0; color:#22c55e; margin:0;">__INIT_TEXT__</div>
                <div style="text-align:center; margin:0;"
                    <div style="font-size:22px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7; margin:0;">Return from break at</div>
                    <div style="font-size:48px; font-weight:900; line-height:1.0; color:#2563eb; margin:0;">__RETURN_TIME__</div>
                </div>
            </div>
            <div id="break-done" style="display:none; color:#f59e0b; font-weight:700; font-size:48px; margin:0;">Break complete</div>
            <div id="break-done-time" style="display:none; color:#2563eb; font-weight:700; font-size:48px; margin:0;">Break complete</div>
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
                let ampm = h >= 12 ? 'PM' : 'AM';
                h = h % 12;
                h = h ? h : 12;
                return h + ':' + pad(m) + ':' + pad(s) + ' ' + ampm;
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
                const msToNext = 1000 - (Date.now() % 1000);
                setTimeout(sync, msToNext);
            };
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
    components.html(break_html, height=340)

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
    st.subheader("Ready Workday")

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
    else:
        st.caption("Select 1 or more ship dates we are loading today.")
        start = st.date_input("First ship date", value=run_date + timedelta(days=1), key="setup_ship_start")
        days = st.number_input("How many ship-days are we loading?", min_value=1, max_value=7, value=2, step=1, key="setup_ship_days")
        ship_dates = [start + timedelta(days=i) for i in range(int(days))]

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
    if (st.session_state.get("last_setup_date") != date.today()) or (st.session_state.get("run_date_key") != _run_date_key(run_date)):
        apply_run_config(run_date, ship_dates)
        st.session_state.active_screen = "UNLOAD"
        save_state()
        st.rerun()

# --------------------------
# Management page
# --------------------------
elif st.session_state.active_screen == "FLEET":
    st.markdown("<style>h1{display:none;}</style>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center; margin:0 0 10px 0;'>Fleet Management</h2>", unsafe_allow_html=True)
    render_fleet_management()

# --------------------------
# Management page
elif st.session_state.active_screen == "SUPERVISOR":
    st.subheader("Management - Admin & Statistics")

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
        else:
            start = st.date_input("First ship date", value=run_date + timedelta(days=1), key="sup_ship_start")
            days = st.number_input("How many ship-days?", min_value=1, max_value=7, value=2, step=1, key="sup_ship_days")
            ship_dates = [start + timedelta(days=i) for i in range(int(days))]

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
            st.session_state.shorts_mode = shorts_mode
            st.session_state.shorts_disabled = shorts_mode == SHORTS_MODE_DISABLE
            st.session_state.batching_disabled = bool(disable_batching)
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
            if "sup_sched_day" in st.session_state:
                sd = int(st.session_state.get("sup_sched_day"))
                pick = st.session_state.get("sup_sched_pick") or []
                st.session_state.off_schedule[sd] = sorted({int(x) for x in pick})
            st.session_state.warn_seconds = int(warn_min) * 60
            st.session_state.shorts_mode = shorts_mode
            st.session_state.shorts_disabled = shorts_mode == SHORTS_MODE_DISABLE
            st.session_state.batching_disabled = bool(disable_batching)
            apply_run_config(run_date, ship_dates)
            st.success("Management settings saved.")

    with st.expander("App Settings", expanded=False):
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
            _set_status_badge_picker_values(st.session_state.status_badge_colors)
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
                    preserved_spares = set()
                    for sval in (st.session_state.get("spare_set") or set()):
                        try:
                            preserved_spares.add(int(sval))
                        except Exception:
                            continue

                    # Reset session_state keys to defaults, but restore fleet config
                    for k, v in defaults.items():
                        st.session_state[k] = v

                    # Restore the fleet configuration
                    st.session_state["extra_fleet"] = preserved_extra
                    st.session_state["removed_fleet"] = []  # Clear removed list to restore all trucks
                    st.session_state["off_schedule"] = preserved_off_schedule
                    st.session_state["activity_log"] = preserved_activity
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
                    # Ensure spares persist through the reset helper
                    st.session_state["spare_set"] = preserved_spares

                    # Remove persisted state file
                    try:
                        p = _state_path()
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                    save_state()
                    st.success("Workday data reset. Spares preserved and unloaded auto-pull reapplied for the current day.")
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
    st.subheader("Unload Management — Dirty Trucks")
    # Truck selection by clicking bubble, not dropdown
    sel_truck = st.session_state.get("unload_inprog_truck")
    def render_unload_bubbles(trucks, selected):
        # Render dirty truck bubbles as Streamlit buttons for in-place navigation
        clicked_truck = render_numeric_truck_buttons(trucks, "dirty_truck", default_cols=8)
        if clicked_truck is not None:
            t = int(clicked_truck)
            if st.session_state.get("batching_disabled"):
                st.session_state.pending_unload_truck = int(t)
                st.rerun()
            else:
                st.session_state["unload_truck_select"] = int(t)
                st.session_state.active_screen = "BATCH"
                _mark_and_save()
                st.rerun()
    render_unload_bubbles(dirty_trucks, sel_truck)
    if st.session_state.get("batching_disabled") and st.session_state.get("pending_unload_truck") is not None:
        pending_t = int(st.session_state.get("pending_unload_truck"))
        if st.session_state.get("next_up_truck") and st.session_state.get("next_after_truck") is None:
            st.info(f"Set the current in-progress unload. Use Truck {pending_t}?")
            use_current = st.checkbox("Use this truck as current in-progress unload", value=True, key="next_after_unload_use_current")
            if use_current:
                if st.button(f"Set current in-progress unload to Truck {pending_t}", use_container_width=True, key="next_after_unload_set_current"):
                    st.session_state.next_after_truck = int(pending_t)
                    _mark_and_save()
                    st.success(f"Current in-progress unload set to Truck {pending_t}.")
            else:
                options = [int(t) for t in FLEET if int(t) != int(st.session_state.get("next_up_truck"))]
                if options:
                    pick_after = st.selectbox("Select current in-progress unload", options=options, key="next_after_unload_pick")
                    off_next = off_trucks_for_next_day()
                    if int(pick_after) in off_next:
                        st.warning(f"Truck {int(pick_after)} is scheduled Off next load day.")
                    if int(pick_after) in st.session_state.shop_set:
                        st.warning(f"Truck {int(pick_after)} is marked Shop.")
                    if st.button("Set current in-progress unload", use_container_width=True, key="next_after_unload_set_pick"):
                        st.session_state.next_after_truck = int(pick_after)
                        _mark_and_save()
                        st.success(f"Current in-progress unload set to Truck {int(pick_after)}.")
        st.warning(f"Send Truck {pending_t} to Unloaded?")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Yes, mark Unloaded", use_container_width=True, key="confirm_unload_manual"):
                st.session_state.cleaned_set.add(pending_t)
                st.session_state.pending_unload_truck = None
                _mark_and_save()
                st.success(f"Truck {pending_t} marked Unloaded (batching disabled).")
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="cancel_unload_manual"):
                st.session_state.pending_unload_truck = None
                st.rerun()
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
                    <div style='font-size:15px; margin-bottom:6px;'>Trucks: <b>{trucks}</b></div>
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
        st.subheader(f"Truck {t} — View Only (edit in Management)")

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

        st.write("**Status membership**")
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

        # Editing of truck membership/status is restricted to the Management panel.
        st.info("Truck editing is restricted to the Management page. Open Management to make changes.")

        st.divider()
        st.write("**Management note**")
        _, _, note_text = get_truck_notes(t)
        note = st.text_area("Note", value=note_text, key="truck_note_text", height=120, disabled=True)

        # Quick status adjustments: mark cleaned/dirty
        # Dirty -> offer batch assignment and mark cleaned
        if t in dirty_trucks:
            st.info("Truck is Dirty. Assign to batch to mark Unloaded.")
            wearers_in = st.number_input("Wearers", min_value=0, step=1, key=f"assign_wearers_{t}")
            allowed = batch_allowed_ids(wearers_in)
            if not allowed:
                st.warning("No batch can accept this truck with that many wearers.")
            else:
                batch_pick = st.selectbox("Assign to batch", options=allowed, key=f"assign_batch_{t}", format_func=lambda i: f"Batch {i} (current {st.session_state.batches[i]['total']}/{BATCH_CAP})")
                if st.button("Mark Unloaded & Assign", use_container_width=True, key=f"assign_btn_{t}"):
                    st.session_state.wearers[t] = int(wearers_in)
                    batch_assign(t, wearers_in, int(batch_pick))
                    st.session_state.cleaned_set.add(t)
                    _mark_and_save()
                    st.success(f"Truck {t} marked Unloaded and assigned to Batch {batch_pick}.")
        elif t in st.session_state.cleaned_set:
            # allow toggling back to dirty or starting load
            if st.button("Mark Dirty", use_container_width=True, key=f"mark_dirty_{t}"):
                st.session_state.cleaned_set.discard(t)
                _mark_and_save()
                st.success(f"Truck {t} moved to Dirty.")
            if (t not in st.session_state.inprog_set) and (t not in st.session_state.loaded_set) and (t not in st.session_state.shop_set):
                    if st.button("Start Loading (Management only)", use_container_width=True, key=f"start_load_{t}"):
                        st.warning("Start Loading is only available from the Management page.")

        st.divider()
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("Open in Management for editing", use_container_width=True):
                st.session_state.sup_manage_truck = t
                st.session_state.sup_manage_action = None
                st.session_state.sup_manage_pref_action = None
                st.session_state.active_screen = "FLEET"
                _mark_and_save()
                st.rerun()
        with c2:
            if st.button("Open short sheet", use_container_width=True):
                st.session_state.shorts_truck = t
                ensure_shorts_model(t)
                st.session_state.active_screen = "SHORTS"
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
    st.subheader("Batch Assignment")
    t = st.session_state.get("unload_inprog_truck")
    if t is None:
        st.warning("No truck selected for batching.")
    else:
        if st.session_state.get("batching_disabled"):
            st.warning("Batching is disabled for today. Mark this truck Unloaded manually.")
            if st.button("Mark Unloaded (batching disabled)", use_container_width=True):
                st.session_state.cleaned_set.add(int(t))
                st.session_state.unload_inprog_truck = None
                st.session_state.unload_inprog_start_time = None
                st.session_state.unload_inprog_wearers = 0
                try:
                    st.session_state["unload_truck_select"] = None
                except Exception:
                    pass
                st.session_state.active_screen = "UNLOAD"
                _mark_and_save()
                st.success(f"Truck {int(t)} marked Unloaded (batching disabled).")
                st.rerun()
            st.stop()
        st.write(f"Batching — Truck {t}")
        st.markdown("<div id='batch-wearers'></div>", unsafe_allow_html=True)
        components.html("<script>const el=document.getElementById('batch-wearers'); if(el) el.scrollIntoView({behavior:'smooth'});</script>", height=0)
        wearers_raw = st.text_input(
            "Wearers",
            value=str(int(st.session_state.get("unload_inprog_wearers", 0) or 0)),
            key=f"batch_wearers_{t}",
        )
        components.html(
            """
            <script>
            (function(){
                const root = window.parent.document;
                const inputs = root.querySelectorAll('input[aria-label="Wearers"]');
                inputs.forEach((el) => {
                    el.setAttribute('inputmode', 'numeric');
                    el.setAttribute('pattern', '[0-9]*');
                });
            })();
            </script>
            """,
            height=0,
            width=0,
        )
        if str(wearers_raw).strip().isdigit():
            w = int(wearers_raw)
        elif str(wearers_raw).strip() == "":
            w = 0
        else:
            w = 0
            st.warning("Wearers must be a whole number.")
        st.session_state.unload_inprog_wearers = int(w)
        if st.button("Skip batching", use_container_width=True):
            st.session_state.cleaned_set.add(int(t))
            st.session_state.unload_inprog_truck = None
            st.session_state.unload_inprog_start_time = None
            st.session_state.unload_inprog_wearers = 0
            try:
                st.session_state["unload_truck_select"] = None
            except Exception:
                pass
            st.session_state.active_screen = "UNLOAD"
            _mark_and_save()
            st.rerun()
        if w > 0:
            allowed = batch_allowed_ids(w)
            st.info(f"Assign **Truck {t}** (wearers: **{w}**) to a batch (≤ {BATCH_CAP}).")
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
                        batch_assign(t, w, batch)
                        st.session_state.wearers[int(t)] = int(w)
                        st.session_state.cleaned_set.add(int(t))
                        st.session_state.unload_inprog_truck = None
                        st.session_state.unload_inprog_start_time = None
                        st.session_state.unload_inprog_wearers = 0
                        _mark_and_save()
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

# --------------------------
# Load
# --------------------------
elif st.session_state.active_screen == "LOAD":
    st.markdown("<style>h2{display:none;}</style>", unsafe_allow_html=True)

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
            off_list = sorted(off_today)
            if off_list:
                st.caption("No available trucks to start. Unloaded trucks are scheduled Off today.")
                st.info(f"Off today: {', '.join(str(int(t)) for t in off_list)}")
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
    st.subheader(f"Shortages — Truck {t}")

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
                        next_up = st.session_state.get("next_up_truck")
                        if next_up is not None and not st.session_state.inprog_set:
                            st.session_state.selected_truck = int(t)
                            st.session_state.active_screen = "STATUS_LOADED"
                        else:
                            st.session_state.active_screen = "LOAD"
                        st.rerun()
            with c2:
                st.info("Save stops the timer. 'Save & Done' saves shortages and returns to Load.")
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
                        next_up = st.session_state.get("next_up_truck")
                        if next_up is not None and not st.session_state.inprog_set:
                            st.session_state.selected_truck = int(t)
                            st.session_state.active_screen = "STATUS_LOADED"
                        else:
                            st.session_state.active_screen = "LOAD"
                        st.rerun()
            with c2:
                st.info("Save stops the timer. 'Save & Done' saves shortages and returns to Load.")
