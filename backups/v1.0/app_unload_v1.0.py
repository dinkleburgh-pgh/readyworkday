import streamlit as st # type: ignore
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component
from datetime import date, timedelta, datetime
import time
from io import BytesIO
import json
import html
import os
import streamlit.components.v1 as components
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# PDF (ReportLab)
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.pdfgen import canvas # type: ignore

st.set_page_config(page_title="Load Management", layout="wide")
st.title("Load Management")

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
    "Towels",
    "Toilet Paper",
    "Paper Towels",
    "Soap",
    "Trash Bags",
    "Gloves",
    "Aprons",
    "Chemicals",
    "Mats",
    "Other",
]

# Badge colors
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#f59e0b"

# ==========================================================
# STATE
# ==========================================================
STATE_FILE = ".truck_state.json"
FLEET_FILE = "truck_fleet.json"


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


def load_state() -> dict:
    path = _state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    out = {}
    for k, v in data.items():
        if k in {"cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "special_set"}:
            out[k] = set(map(int, v)) if v else set()
        elif k == "run_date":
            out[k] = date.fromisoformat(v) if v else None
        elif k == "ship_dates":
            out[k] = [date.fromisoformat(s) for s in v] if v else []
        elif k in {"wearers", "shop_notes", "off_notes", "sup_notes", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule"}:
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
        elif k == "last_setup_date":
            out[k] = date.fromisoformat(v) if v else None
        else:
            out[k] = v
    return out


def save_state():
    path = _state_path()
    try:
        data = {}
        keys = list(defaults.keys())
        for k in keys:
            v = st.session_state.get(k, defaults.get(k))
            if k in {"cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "special_set"}:
                data[k] = sorted(list(v))
            elif k == "run_date":
                data[k] = v.isoformat() if v else None
            elif k == "last_setup_date":
                data[k] = v.isoformat() if v else None
            elif k == "ship_dates":
                data[k] = [d.isoformat() for d in v]
            elif k in {"wearers", "shop_notes", "off_notes", "sup_notes", "shorts_initials", "load_durations", "shorts", "batches", "off_schedule"}:
                ser = {}
                for kk, vv in (v or {}).items():
                    ser[str(kk)] = vv
                data[k] = ser
            else:
                data[k] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


loaded = load_state()

defaults = {
    # work states
    "cleaned_set": set(),
    "inprog_set": set(),             # max 1
    "loaded_set": set(),

    # supervisor / off + shop
    "off_set": set(),
    "off_notes": {},                 # {truck: text}
    "shop_set": set(),
    "shop_notes": {},                # {truck: text}
    "shop_notice_ts": None,
    "shop_notice_log": [],
    "special_set": set(),

    # supervisor per-truck notes
    "sup_notes": {},                 # {truck: text}

    # batching
    "wearers": {},                   # {truck:int}
    "batches": {i: {"trucks": [], "total": 0} for i in range(1, BATCH_COUNT + 1)},
    "pending_batch_truck": None,
    "pending_batch_wearers": 0,

    # unload in-progress (cleaning) state
    "unload_inprog_truck": None,
    "unload_inprog_start_time": None,
    "unload_inprog_wearers": 0,
    "unload_durations": {},

    # setup / workday
    "setup_done": False,
    "run_date": None,
    "last_setup_date": None,
    "ship_dates": [],

    # navigation
    "active_screen": "SETUP",        # SETUP | UNLOAD | LOAD | SHORTS | STATUS_* | IN_PROGRESS
    "shorts_truck": None,
    # selected truck (for TRUCK edit view)
    "selected_truck": None,
    # queued next-up truck (Unloaded)
    "next_up_truck": None,
    # track last requested page from URL to avoid stale query param lock-in
    "last_requested_page": None,
    # navigation history for browser back
    "nav_seq": 0,
    "last_screen_for_history": None,
    "last_nav_seen": None,

    # timing
    "inprog_start_time": None,       # epoch seconds
    "load_durations": {},            # {truck:int_seconds}
    "load_start_times": {},          # {truck: epoch}
    "load_finish_times": {},         # {truck: epoch}

    # shorts
    "shorts": {},                    # {truck: [ {item, qty, note}, ... ]}
    "shorts_initials": {},           # {truck: "AB"}
    "shorts_initials_ts": {},        # {truck: iso_timestamp}
    "shorts_initials_history": {},   # {truck: [ {initials, ts}, ... ]}

    # warning threshold
    "warn_seconds": DEFAULT_WARN_MIN * 60,

    # activity log
    "activity_log": [],

    # Any additional trucks added by supervisor (persisted)
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

# Immediately persist any state changes that represent important actions
save_state()

# If the supervisor has previously added trucks, merge them into the runtime FLEET
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
except Exception:
    pass

# ==========================================================
# CSS (bubbled truck lists on status pages)
# ==========================================================
st.markdown(
    """
    <style>
      .truck-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 8px;
      }
      .truck-bubble {
        width: 58px;
        height: 58px;
        border-radius: 10px; /* nice square bubble */
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 18px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(255,255,255,0.06);
        user-select: none;
      }
            button[kind="primary"] {
                width: 58px !important;
                height: 58px !important;
                min-width: 58px !important;
                min-height: 58px !important;
                padding: 0 !important;
                border-radius: 10px !important;
                font-weight: 900 !important;
                font-size: 18px !important;
                line-height: 1 !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                white-space: nowrap !important;
                background: rgba(255,255,255,0.06) !important;
                border: 1px solid rgba(255,255,255,0.14) !important;
                color: inherit !important;
            }
            .shop-notice {
                position: fixed;
                top: 64px;
                right: 16px;
                z-index: 99999;
                width: 520px;
                max-width: 90vw;
                padding: 18px 20px;
                border-radius: 12px;
                border: 1px solid rgba(220, 38, 38, 0.4);
                background: rgba(153, 27, 27, 0.92);
                color: #fef2f2;
                box-shadow: 0 10px 30px rgba(0,0,0,0.25);
                font-size: 17px;
                line-height: 1.4;
                backdrop-filter: blur(4px);
            }
            .shop-notice .notice-close {
                position: absolute;
                top: 6px;
                right: 10px;
                font-weight: 800;
                font-size: 16px;
                color: #fee2e2;
                text-decoration: none;
                padding: 2px 6px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.2);
                background: rgba(0,0,0,0.15);
            }
            .shop-notice .notice-close:hover {
                background: rgba(0,0,0,0.25);
            }
            .shop-notice .notice-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding-bottom: 6px;
                margin-bottom: 6px;
                border-bottom: 1px solid rgba(255,255,255,0.15);
                cursor: pointer;
            }
            .shop-notice .notice-bar-title {
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                font-size: 16px;
                color: #fee2e2;
            }
            .shop-notice .notice-bar-toggle {
                font-weight: 700;
                font-size: 12px;
                opacity: 0.9;
                border: 1px solid rgba(255,255,255,0.2);
                padding: 2px 6px;
                border-radius: 6px;
            }
            .shop-notice-collapsed {
                position: fixed;
                top: 64px;
                right: 16px;
                z-index: 99999;
                padding: 8px 12px;
                border-radius: 10px;
                border: 1px solid rgba(220, 38, 38, 0.4);
                background: rgba(153, 27, 27, 0.92);
                color: #fef2f2;
                font-size: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            }
            .shop-notice {
                cursor: pointer;
            }
            .shop-notice.collapsed {
                padding: 10px 14px;
            }
            .shop-notice.collapsed .notice-item {
                display: none;
            }
            .shop-notice .body {
                font-weight: 600;
                text-align: center;
            }
            .shop-notice .timestamp {
                font-size: 14px;
                opacity: 0.85;
            }
            .shop-notice .notice-item {
                padding: 4px 0;
                border-top: 1px solid rgba(255,255,255,0.12);
                display: flex;
                align-items: baseline;
                justify-content: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .shop-notice .notice-item:first-of-type {
                border-top: none;
                padding-top: 0;
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
    st.query_params.update(kwargs)

def _push_nav_history(force: bool = False):
    current = st.session_state.get("active_screen")
    if not current:
        return
    last = st.session_state.get("last_screen_for_history")
    if force or current != last:
        seq = int(st.session_state.get("nav_seq") or 0) + 1
        st.session_state.nav_seq = seq
        st.session_state.last_screen_for_history = current
        _set_query_params(page=current, nav=str(seq))

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

def log_action(message: str):
    try:
        now_ts = datetime.now(ZoneInfo("America/New_York")) if ZoneInfo else datetime.now()
    except Exception:
        now_ts = datetime.now()
    stamp = f"{now_ts.month}/{now_ts.day} {now_ts.strftime('%I:%M %p')}"
    entry = f"{stamp} - {message}"
    log = list(st.session_state.get("activity_log") or [])
    log.append(entry)
    st.session_state.activity_log = log[-50:]

def render_shop_notice():
    shop_trucks = sorted(st.session_state.shop_set)
    log = list(st.session_state.get("shop_notice_log") or [])
    if not log and not shop_trucks:
        return
    if not log and shop_trucks:
        now_ts = time.time()
        safe_items = ", ".join(f"#{t}" for t in shop_trucks)
        log.append({"ts": now_ts, "msg": f"Sent to shop: {safe_items}"})
        st.session_state.shop_notice_log = log
        save_state()

    recent = log[-4:]
    lines = []
    for entry in reversed(recent):
        try:
            ts_dt = datetime.fromtimestamp(entry.get("ts", time.time()), tz=ZoneInfo("America/New_York")) if ZoneInfo else datetime.fromtimestamp(entry.get("ts", time.time()))
        except Exception:
            ts_dt = datetime.fromtimestamp(entry.get("ts", time.time()))
        stamp = f"{ts_dt.month}/{ts_dt.day} @ {ts_dt.strftime('%I:%M %p')}"
        msg = html.escape(str(entry.get("msg", "")))
        lines.append(
            "<div class='notice-item'>"
            f"  <span class='timestamp'>{stamp}</span>"
            f"  <span class='body'>{msg}</span>"
            "</div>"
        )
    notice_id = str(log[-1].get("ts", time.time()))
    st.markdown(
        (
            f"<div id='shop-notice' class='shop-notice' data-notice-id='{notice_id}'>"
            "  <div id='shop-notice-bar' class='notice-bar'>"
            "    <span class='notice-bar-title'>Notice</span>"
            "    <span id='shop-notice-toggle' class='notice-bar-toggle'>Collapse</span>"
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
            const notice = root.getElementById('shop-notice');
            const bar = root.getElementById('shop-notice-bar');
            const toggle = root.getElementById('shop-notice-toggle');
            if (!notice || !bar || !toggle) return;
            const id = notice.getAttribute('data-notice-id') || '';
            const lastId = localStorage.getItem('shopNoticeLastId');
            if (lastId !== id) {
                localStorage.setItem('shopNoticeLastId', id);
                localStorage.setItem('shopNoticeCollapsed', '0');
            }
            const applyState = () => {
                const collapsed = localStorage.getItem('shopNoticeCollapsed') === '1';
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
                    localStorage.setItem('shopNoticeCollapsed', collapsed ? '0' : '1');
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

def render_fleet_management():
    st.write("### Step 1 - Select truck")
    manage_truck = st.selectbox("Select truck", options=FLEET, key="sup_manage_truck_select")
    sel = int(st.session_state.get("sup_manage_truck", manage_truck))
    st.markdown(
        (
            "<div style='font-size:36px; font-weight:900; margin:4px 0 8px 0; "
            "color:#f59e0b; text-shadow:-1px 0 #000, 0 1px #000, 1px 0 #000, 0 -1px #000;'>"
            f"Truck {sel}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.write("### Step 2 - Choose option")
    action = st.session_state.get("sup_manage_action") or "Status"
    st.caption(f"Selected: {action}")
    action_labels = ["Status", "Notes", "Batch", "Off", "Shop", "Ran Special", "Add/Remove"]
    cols = st.columns(3)
    for idx, label in enumerate(action_labels):
        col = cols[idx % 3]
        with col:
            if st.button(label, key=f"sup_manage_action_btn_{label}", use_container_width=True):
                st.session_state.sup_manage_action = label
                action = label

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
        note_val = st.text_area(
            "Notes (shown on In Progress + printed on PDF)",
            value=st.session_state.sup_notes.get(int(sel), ""),
            height=120,
            key="sup_manage_note_text",
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save note", use_container_width=True, key="sup_manage_save_note"):
                st.session_state.sup_notes[int(sel)] = (note_val or "").strip()
                st.success("Note saved.")
                save_state()
        with c2:
            if st.button("Clear note", use_container_width=True, key="sup_manage_clear_note"):
                st.session_state.sup_notes.pop(int(sel), None)
                st.success("Note cleared.")
                save_state()

    elif action == "Status":
        st.write("### Status")
        if sel in st.session_state.shop_set:
            cur_status = "Shop"
        elif sel in st.session_state.off_set:
            cur_status = "Off"
        elif sel in st.session_state.inprog_set:
            cur_status = "In Progress"
        elif sel in st.session_state.loaded_set:
            cur_status = "Loaded"
        elif sel in st.session_state.cleaned_set:
            cur_status = "Unloaded"
        else:
            cur_status = "Dirty"

        status_options = ["Dirty", "Unloaded", "In Progress", "Loaded", "Off", "Shop"]
        status_sel = st.selectbox("Status", status_options, index=status_options.index(cur_status), key="sup_manage_status_sel")
        if st.button("Apply status change", key="sup_manage_apply_status"):
            st.session_state.sup_pending_status = {"truck": sel, "status": status_sel}

        pending = st.session_state.get("sup_pending_status")
        if pending and pending.get("truck") == sel:
            st.warning(f"Confirm change Truck {sel} -> {pending.get('status')}")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Confirm status change", key="sup_manage_confirm_status"):
                    st.session_state.cleaned_set.discard(sel)
                    st.session_state.loaded_set.discard(sel)
                    st.session_state.inprog_set.discard(sel)
                    st.session_state.shop_set.discard(sel)
                    st.session_state.off_set.discard(sel)
                    if pending.get("status") == "Dirty":
                        pass
                    elif pending.get("status") == "Unloaded":
                        st.session_state.cleaned_set.add(sel)
                    elif pending.get("status") == "In Progress":
                        start_loading_truck(sel)
                    elif pending.get("status") == "Loaded":
                        st.session_state.loaded_set.add(sel)
                        st.session_state.load_finish_times[sel] = time.time()
                    elif pending.get("status") == "Off":
                        st.session_state.off_set.add(sel)
                    elif pending.get("status") == "Shop":
                        st.session_state.shop_set.add(sel)
                    _mark_and_save()
                    st.success(f"Truck {sel} status updated to {pending.get('status')}.")
                    st.session_state.sup_pending_status = None
            with c2:
                if st.button("Cancel", key="sup_manage_cancel_status"):
                    st.session_state.sup_pending_status = None

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

    elif action == "Off":
        st.write("### Off")
        off_reason = st.text_input("Off reason (optional)", key="sup_manage_off_reason")
        if st.button("Send to Off", use_container_width=True, key="sup_manage_send_off"):
            st.session_state.off_set.add(sel)
            st.session_state.off_notes[sel] = (off_reason or "").strip()
            log_action(f"Truck {sel} sent to Off")
            if st.session_state.get("next_up_truck") == sel:
                st.session_state.next_up_truck = None
            st.session_state.cleaned_set.discard(sel)
            st.session_state.inprog_set.discard(sel)
            st.session_state.loaded_set.discard(sel)
            st.session_state.shop_set.discard(sel)
            remove_truck_from_batches(sel)
            _mark_and_save()
            st.success(f"Truck {sel} sent to Off.")
            st.rerun()

    elif action == "Shop":
        st.write("### Shop")
        shop_reason = st.text_input("Shop reason (optional)", key="sup_manage_shop_reason")
        if st.button("Send to Shop", use_container_width=True, key="sup_manage_send_shop"):
            st.session_state.shop_set.add(sel)
            st.session_state.shop_notes[sel] = (shop_reason or "").strip()
            now_ts = time.time()
            msg = f"Sent to shop: #{sel}" + (f" — {shop_reason}" if shop_reason else "")
            log = list(st.session_state.get("shop_notice_log") or [])
            log.append({"ts": now_ts, "msg": msg})
            st.session_state.shop_notice_log = log[-20:]
            st.session_state.hide_shop_notice = False
            log_action(f"Truck {sel} sent to Shop")
            if st.session_state.get("next_up_truck") == sel:
                st.session_state.next_up_truck = None
            st.session_state.cleaned_set.discard(sel)
            st.session_state.inprog_set.discard(sel)
            st.session_state.loaded_set.discard(sel)
            st.session_state.off_set.discard(sel)
            remove_truck_from_batches(sel)
            _mark_and_save()
            st.success(f"Truck {sel} sent to Shop.")
            st.rerun()

    elif action == "Ran Special":
        st.write("### Ran Special")
        special_note = st.text_input("Special note (optional)", key="sup_manage_special_note")
        if st.button("Mark Ran Special", use_container_width=True, key="sup_manage_special"):
            st.session_state.special_set.add(sel)
            if st.session_state.get("next_up_truck") == sel:
                st.session_state.next_up_truck = None
            st.session_state.cleaned_set.discard(sel)
            st.session_state.inprog_set.discard(sel)
            st.session_state.loaded_set.discard(sel)
            st.session_state.off_set.discard(sel)
            st.session_state.shop_set.discard(sel)
            remove_truck_from_batches(sel)
            now_ts = time.time()
            msg = f"Ran special: #{sel} needs unload" + (f" — {special_note}" if special_note else "")
            log = list(st.session_state.get("shop_notice_log") or [])
            log.append({"ts": now_ts, "msg": msg})
            st.session_state.shop_notice_log = log[-20:]
            st.session_state.hide_shop_notice = False
            log_action(f"Truck {sel} ran special (needs unload)")
            _mark_and_save()
            st.success(f"Truck {sel} marked Ran Special (needs unload).")
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
                    remove_truck_entirely(t)
                    try:
                        FLEET[:] = sorted(set(FLEET) - {t})
                    except Exception:
                        pass
                    save_fleet_file(FLEET)
                    _mark_and_save()
                    st.success(f"Truck {t} removed from fleet.")
                    st.session_state.sup_pending_remove = None
                    st.rerun()
            with c2:
                if st.button("Cancel removal", key="sup_manage_cancel_remove"):
                    st.session_state.sup_pending_remove = None

        st.divider()
        st.write("### Add truck to fleet")
        try:
            suggested = max(FLEET) + 1 if FLEET else FLEET_MAX + 1
        except Exception:
            suggested = FLEET_MAX + 1
        new_truck = st.number_input("Truck number to add", min_value=1, max_value=9999, value=int(suggested), step=1, key="sup_add_truck_num")
        if st.button("Add truck to fleet", key="sup_add_truck_add"):
            t = int(new_truck)
            if t in FLEET:
                st.warning(f"Truck {t} already exists in fleet.")
            else:
                extras = list(st.session_state.get("extra_fleet") or [])
                try:
                    extras = [int(x) for x in extras]
                except Exception:
                    extras = extras
                extras.append(t)
                extras = sorted(set(extras))
                st.session_state["extra_fleet"] = extras
                try:
                    FLEET[:] = sorted(set(FLEET) | {t})
                except Exception:
                    pass
                save_fleet_file(FLEET)
                _mark_and_save()
                st.success(f"Truck {t} added to fleet.")
                st.rerun()


def average_load_time_seconds(trucks: list[int]) -> int | None:
    durations = [
        st.session_state.load_durations.get(t)
        for t in trucks
        if st.session_state.load_durations.get(t) is not None
    ]
    if not durations:
        return None
    return int(sum(durations) / len(durations))

def normalize_states():
    # Off/Shop excludes everything else
    st.session_state.cleaned_set -= st.session_state.shop_set
    st.session_state.cleaned_set -= st.session_state.off_set
    st.session_state.inprog_set -= st.session_state.shop_set
    st.session_state.inprog_set -= st.session_state.off_set
    st.session_state.loaded_set -= st.session_state.shop_set
    st.session_state.loaded_set -= st.session_state.off_set

    # Shop and Off should not overlap
    st.session_state.off_set -= st.session_state.shop_set

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
        st.session_state.next_up_truck = None
    log_action(f"Start loading Truck {t}")

def render_next_up_controls(context_key: str):
    unloaded = sorted(st.session_state.cleaned_set)
    current = st.session_state.get("next_up_truck")
    st.write("### Next up queue")
    if current:
        st.info(f"Current next up: Truck {int(current)}")
    else:
        st.caption("No next-up truck set.")
    if not unloaded:
        st.caption("No Unloaded trucks available.")
        return
    pick = st.selectbox("Select next up", options=unloaded, key=f"next_up_select_{context_key}")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Set Next Up", key=f"next_up_set_{context_key}", use_container_width=True):
            st.session_state.next_up_truck = int(pick)
            _mark_and_save()
            st.success(f"Next up set to Truck {int(pick)}.")
            st.rerun()
    with c2:
        if st.button("Clear Next Up", key=f"next_up_clear_{context_key}", use_container_width=True):
            st.session_state.next_up_truck = None
            _mark_and_save()
            st.success("Next up cleared.")
            st.rerun()

def remove_truck_from_batches(truck: int):
    t = int(truck)
    for i in range(1, BATCH_COUNT + 1):
        if t in st.session_state.batches[i]["trucks"]:
            st.session_state.batches[i]["trucks"].remove(t)
            st.session_state.batches[i]["total"] -= int(st.session_state.wearers.get(t, 0))

def apply_off_schedule(day_num: int | None):
    if not day_num:
        return
    schedule = st.session_state.get("off_schedule") or {}
    raw = schedule.get(int(day_num), []) or []
    try:
        scheduled = sorted({int(x) for x in raw})
    except Exception:
        scheduled = []
    for t in scheduled:
        if t in st.session_state.shop_set:
            continue
        st.session_state.off_set.add(t)
        st.session_state.cleaned_set.discard(t)
        st.session_state.inprog_set.discard(t)
        st.session_state.loaded_set.discard(t)
        remove_truck_from_batches(t)


def remove_truck_entirely(truck: int):
    """Remove any references to a truck across session state (but does not
    modify persisted extra/removed lists)."""
    t = int(truck)
    # Remove from membership sets
    for s in ("cleaned_set", "inprog_set", "loaded_set", "shop_set", "off_set", "special_set"):
        try:
            st.session_state[s].discard(t)
        except Exception:
            pass

    # Remove batch membership
    remove_truck_from_batches(t)

    # Remove wearers and notes
    st.session_state.wearers.pop(t, None)
    st.session_state.shop_notes.pop(t, None)
    st.session_state.off_notes.pop(t, None)
    st.session_state.sup_notes.pop(t, None)

    # Remove timing data
    st.session_state.load_durations.pop(t, None)
    st.session_state.load_start_times.pop(t, None)
    st.session_state.load_finish_times.pop(t, None)

    # Remove shorts data
    st.session_state.shorts.pop(t, None)
    st.session_state.shorts_initials.pop(t, None)
    st.session_state.shorts_initials_ts.pop(t, None)
    st.session_state.shorts_initials_history.pop(t, None)

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
        st.session_state.shorts[t] = [{"item": DEFAULT_SHORT_ITEMS[0], "qty": 1, "note": ""}]

def go(screen: str):
    st.session_state.active_screen = screen
    _push_nav_history(force=True)
    st.rerun()


def _mark_and_save():
    normalize_states()
    save_state()


def sidebar_badge_link(label: str, value: str | int, color: str, target_page: str):
    # Try to use the local badge component (no full reload) and fall back to
    # a simple button if components aren't available.
    try:
        comp = declare_component("badge_component", path="components/badge_component/frontend")
        # Call the component; it should return a dict like {target:..., clicked: True}
        res = comp(label=label, value=str(value), color=color, target=target_page, key=f"badge_{target_page}")
        if isinstance(res, dict) and res.get("clicked"):
            st.session_state.active_screen = res.get("target") or target_page
            _mark_and_save()
            st.rerun()
    except Exception:
        # Fallback UI
        container = st.sidebar.container()
        sval = str(value)
        safe_color = color or "#cccccc"
        c0, c1 = container.columns([1, 6])
        with c0:
            st.markdown(f"<div style='width:28px; height:28px; border-radius:50%; background:{safe_color};'></div>", unsafe_allow_html=True)
        with c1:
            if st.button(f"{label}  •  {value}", key=f"sidebar_badge_{target_page}", use_container_width=True):
                st.session_state.active_screen = target_page
                _mark_and_save()
                st.rerun()

def render_truck_bubbles(trucks: list[int], from_page: str | None = None):
    # This is what you asked for: bubbled lists INSIDE each status link page
    if not trucks:
        st.write("None")
        return
    
    # Create a grid of bubble buttons that navigate in-place without opening new tabs
    cols = st.columns(8)
    for idx, t in enumerate(trucks):
        col = cols[idx % 8]
        with col:
            if st.button(str(int(t)), key=f"bubble_{from_page}_{t}", use_container_width=False, type="primary"):
                # Navigate based on the page context
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
                elif from_page in ("STATUS_SHOP", "STATUS_OFF"):
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

    draw("Truck Readiness — End of Day (Compile Anytime)", bold=True)
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
                table_w = item_w + col_w * len(trucks_chunk)
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
        now_ts = datetime.now(tz=ZoneInfo('America/New_York')).isoformat()
    except Exception:
        now_ts = datetime.now().isoformat()
    st.session_state.shorts_initials_ts[t] = now_ts
    hist = st.session_state.shorts_initials_history.get(t, [])
    hist.append({"initials": ini, "ts": now_ts})
    st.session_state.shorts_initials_history[t] = hist

    if st.session_state.inprog_start_time:
        sec = elapsed_seconds()
        st.session_state.load_durations[t] = sec
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
dirty_trucks = sorted(
    set(FLEET)
    - st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - st.session_state.off_set
)
cleaned_list = sorted(st.session_state.cleaned_set)
loaded_list = sorted(st.session_state.loaded_set)
shop_list = sorted(st.session_state.shop_set)
off_list = sorted(st.session_state.off_set)
inprog_truck = next(iter(st.session_state.inprog_set)) if st.session_state.inprog_set else None

true_available = sorted(
    st.session_state.cleaned_set
    - st.session_state.loaded_set
    - st.session_state.inprog_set
    - st.session_state.shop_set
    - st.session_state.off_set
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
    "SETUP", "UNLOAD", "LOAD", "SHORTS",
    "STATUS_DIRTY", "STATUS_CLEANED", "STATUS_LOADED", "STATUS_SHOP", "STATUS_OFF",
    "TRUCK", "SUPERVISOR",
    "IN_PROGRESS",
    "BATCH",
}
prev_requested = st.session_state.get("last_requested_page")
if requested in valid_pages:
    # Only honor a query-param page change when it changes from the last URL
    # value (prevents stale URLs from overriding in-app navigation).
    if requested != prev_requested or requested == st.session_state.active_screen:
        st.session_state.active_screen = requested
st.session_state.last_requested_page = requested

# If the URL is stale (user navigated via UI), keep the URL page in sync.
if requested and requested == prev_requested and requested != st.session_state.active_screen:
    _set_query_params(page=st.session_state.active_screen)

# If a pick param was provided, open the BATCH page for that truck
if st.session_state.active_screen == "BATCH" and st.session_state.get("unload_truck_select") is not None:
    try:
        p = int(st.session_state.get("unload_truck_select"))
        st.session_state.unload_inprog_truck = p
        st.session_state.unload_inprog_start_time = None
        st.session_state.unload_inprog_wearers = 0
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

# Global notice for supervisor Shop assignments
render_shop_notice()

# ==========================================================
# SIDEBAR
# ==========================================================
st.sidebar.header("Navigation")
# Current time (EST)
try:
    if ZoneInfo is not None:
        now_est = datetime.now(ZoneInfo("America/New_York"))
        tzname = now_est.tzname() or "EST"
    else:
        now_est = datetime.utcnow()
        tzname = "UTC"
except Exception:
    now_est = datetime.utcnow()
    tzname = "UTC"
st.sidebar.markdown(f"**Time ({tzname}):** {now_est.strftime('%I:%M %p')}")

# Unload at top, Load middle
if st.sidebar.button("Unload", use_container_width=True):
    st.session_state.active_screen = "UNLOAD"
    _mark_and_save()
    st.rerun()

if st.sidebar.button("Load", use_container_width=True):
    st.session_state.active_screen = "LOAD"
    _mark_and_save()
    st.rerun()

if st.session_state.setup_done:
    st.sidebar.divider()
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
    st.sidebar.markdown(
        f"<div style='margin:0; padding:0; font-size:0.9rem; line-height:1.1;'>"
        f"<div style='margin:0; padding:0;'><b>Workday:</b> {current_day}</div>"
        f"<div style='margin:0; padding:0;'><b>Load:</b> {load_day}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ---- REVERTED STATUS BAR LOOK (single card) ----
st.sidebar.divider()
st.sidebar.header("Live status")
sidebar_badge_link("Dirty", len(dirty_trucks), RED, "STATUS_DIRTY")
sidebar_badge_link("Off", len(off_list), RED, "STATUS_OFF")
sidebar_badge_link("Shop", len(shop_list), RED, "STATUS_SHOP")
sidebar_badge_link("In Progress", str(inprog_truck) if inprog_truck is not None else "None", ORANGE, "IN_PROGRESS")
sidebar_badge_link("Unloaded", len(cleaned_list), GREEN, "STATUS_CLEANED")
sidebar_badge_link("Loaded", len(loaded_list), GREEN, "STATUS_LOADED")

if st.session_state.setup_done:
    st.sidebar.divider()
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

    # Supervisor button at bottom of nav
    st.sidebar.divider()
    if st.sidebar.button("Supervisor", use_container_width=True):
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
    if title == "Off":
        title = "Off"
    if title == "Cleaned":
        title = "Unloaded"
    st.subheader(title)

    mapping = {
        "STATUS_DIRTY": dirty_trucks,
        "STATUS_CLEANED": cleaned_list,
        "STATUS_LOADED": loaded_list,
        "STATUS_SHOP": shop_list,
        "STATUS_OFF": off_list,
    }
    trucks = mapping.get(st.session_state.active_screen, [])

    # Always show the truck bubbles list
    st.write("### Trucks")
    render_truck_bubbles(trucks, st.session_state.active_screen)

    # If we're on the Loaded status and a specific truck was selected, show an overview below
    if st.session_state.active_screen == "STATUS_LOADED" and st.session_state.selected_truck:
        t = st.session_state.selected_truck
        if t not in st.session_state.loaded_set:
            st.warning(f"Truck {t} is not currently marked Loaded.")
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
                st.write(f"Started: {datetime.fromtimestamp(start_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
            if finish_ts:
                st.write(f"Finished: {datetime.fromtimestamp(finish_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
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

            next_up = st.session_state.get("next_up_truck")
            if next_up is not None and not st.session_state.inprog_set:
                st.warning(f"Next up: Truck {int(next_up)}. Start loading now?")
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("Yes, start next up", use_container_width=True, key="start_next_up_status_loaded"):
                        start_loading_truck(int(next_up))
                        _mark_and_save()
                        st.session_state.active_screen = "IN_PROGRESS"
                        st.rerun()
                with c2:
                    if st.button("No, not yet", use_container_width=True, key="cancel_next_up_status_loaded"):
                        pass

    if st.session_state.active_screen == "STATUS_CLEANED" and st.session_state.get("pending_start_truck"):
        pending_t = int(st.session_state.get("pending_start_truck"))
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
    st.markdown("<h3 style='text-align:center; margin:0 0 6px 0;'>IN PROGRESS</h3>", unsafe_allow_html=True)

    if not inprog_truck:
        st.info("No truck currently in progress.")
    else:
        elapsed = elapsed_seconds()
        st.markdown(
            (
                "<div style='text-align:center; margin:0 0 2px 0;'>"
                "  <div style='font-size:12px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7;'>Current Truck</div>"
                f"  <div style='font-size:56px; font-weight:900; line-height:1.0; color:#facc15;'>#{inprog_truck}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        # Render elapsed timer into a DOM element that JS will update every second.
        warn_m = int(st.session_state.warn_seconds) // 60 if st.session_state.warn_seconds else None
        warn_visible = 'block' if (st.session_state.warn_seconds and elapsed >= int(st.session_state.warn_seconds)) else 'none'
        warn_text = f"Load time exceeded the warning threshold ({warn_m} minutes)." if warn_m else ""
        # Render the timer entirely inside a component iframe so JS can update it.
        init_elapsed = int(elapsed)
        start_epoch = int(st.session_state.inprog_start_time or time.time())
        warn_threshold = int(st.session_state.warn_seconds or 0)
        timer_html = """
        <div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;\">
                    <div id=\"timer-card\" style=\"
                            display:flex; align-items:center; justify-content:center; gap:16px; margin:8px 0 4px 0;\">
            <div id=\"timer-box\" style=\"
                padding:12px 16px; border-radius:12px; border:1px solid rgba(255,255,255,0.12);
                background:linear-gradient(135deg, rgba(22,163,74,0.18), rgba(245,158,11,0.12));
                box-shadow:0 6px 18px rgba(0,0,0,0.12);\">
              <div id=\"truck-elapsed\" style=\"font-size:34px; font-weight:800; line-height:1.1; color:__COLOR_GOOD__;\">__INIT_TEXT__</div>
            </div>
            <div id=\"truck-elapsed-warn\" style=\"display:__WARN_DISPLAY__; color:__WARN_COLOR__; font-weight:700;\">__WARN_TEXT__</div>
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
                const colorFor = (elapsed, warn) => {
                    if (!warn || warn <= 0) return '__COLOR_GOOD__';
                    const ratio = elapsed / warn;
                    if (ratio < 0.7) return '__COLOR_GOOD__';
                    if (ratio < 1) return '__COLOR_WARN__';
                    return '__COLOR_ALERT__';
                };
                const startEpoch = __START__;
                let elapsed = __INIT__;
                const warn = __WARN__;
                const tick = () => {
                    const now = Math.floor(Date.now() / 1000);
                    elapsed = Math.max(0, now - startEpoch);
                    const el = document.getElementById('truck-elapsed');
                    const warnEl = document.getElementById('truck-elapsed-warn');
                    const box = document.getElementById('timer-box');
                    if (el) {
                        el.textContent = fmt(elapsed);
                        el.style.color = colorFor(elapsed, warn);
                    }
                    if (warnEl) {
                        if (warn > 0 && elapsed >= warn) warnEl.style.display = 'block';
                        else warnEl.style.display = 'none';
                    }
                    if (box) {
                        if (warn > 0 && elapsed >= warn) {
                            box.style.boxShadow = '0 0 0 3px rgba(245,158,11,0.25), 0 10px 22px rgba(0,0,0,0.16)';
                        } else {
                            box.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
                        }
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
        timer_html = (
            timer_html
            .replace("__INIT__", str(init_elapsed))
            .replace("__START__", str(start_epoch))
            .replace("__WARN__", str(warn_threshold))
            .replace("__INIT_TEXT__", seconds_to_mmss(elapsed))
            .replace("__WARN_DISPLAY__", warn_visible)
            .replace("__WARN_COLOR__", ORANGE)
            .replace("__WARN_TEXT__", warn_text)
            .replace(
                "display:flex; align-items:center; justify-content:center; gap:16px; margin:8px 0 4px 0;",
                "display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; margin:8px 0 4px 0;",
            )
            .replace("font-weight:700;\">__WARN_TEXT__", "font-weight:700; text-align:center;\">__WARN_TEXT__")
            .replace("__COLOR_GOOD__", GREEN)
            .replace("__COLOR_WARN__", ORANGE)
            .replace("__COLOR_ALERT__", RED)
        )
        components.html(timer_html, height=110)

        next_up = st.session_state.get("next_up_truck")
        if next_up is not None:
            st.markdown(
                (
                    "<div style='text-align:center; margin:6px 0 2px 0;'>"
                    "  <div style='font-size:12px; letter-spacing:0.14em; text-transform:uppercase; opacity:0.7;'>Next Up</div>"
                    f"  <div style='font-size:56px; font-weight:900; line-height:1.0; color:#3b82f6;'>#{int(next_up)}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='text-align:center; font-size:13px; margin-top:4px; opacity:0.6;'>Next up: None</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        render_next_up_controls("inprog")

        note_text = (st.session_state.sup_notes.get(inprog_truck) or "").strip()
        if note_text:
            st.subheader("Notes")
            st.write(note_text)

        st.divider()
        st.subheader("Shortages (while in progress)")
        st.caption("Saving here stops the timer.")

        ensure_shorts_model(inprog_truck)
        initials = st.text_input(
            "Initials (required)",
            value=st.session_state.shorts_initials.get(inprog_truck, ""),
            max_chars=5,
            key="inprog_short_initials",
        )

        edited = st.data_editor(
            st.session_state.shorts.get(inprog_truck, [{"item": DEFAULT_SHORT_ITEMS[0], "qty": 1, "note": ""}]),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item": st.column_config.SelectboxColumn("Item", options=DEFAULT_SHORT_ITEMS, required=True),
                "qty": st.column_config.NumberColumn("Qty", min_value=0, step=1, required=True),
                "note": st.column_config.TextColumn("Note (optional)"),
            },
            key="inprog_shorts_editor",
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save shortages (stop timer)", use_container_width=True):
                if save_shorts_stop_timer(inprog_truck, initials, edited):
                    st.success("Saved (timer stopped).")
                    st.session_state.selected_truck = int(inprog_truck)
                    st.session_state.active_screen = "STATUS_LOADED"
                    _mark_and_save()
                    st.rerun()
        with c2:
            if st.button("Go to Load", use_container_width=True):
                # Save shortages (stop timer) and auto-mark loaded, then return to LOAD
                if save_shorts_stop_timer(inprog_truck, initials, edited):
                    t = int(inprog_truck)
                    st.session_state.inprog_set.clear()
                    st.session_state.loaded_set.add(t)
                    st.session_state.shorts_truck = t
                    ensure_shorts_model(t)
                    _mark_and_save()
                    st.success(f"Truck {t} marked Loaded.")
                    st.session_state.active_screen = "LOAD"
                    st.rerun()

        # Timer runs in the component iframe above.


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

    st.divider()
    if st.button("Start/Update Workday", use_container_width=True):
        st.session_state.run_date = run_date
        st.session_state.ship_dates = ship_dates
        st.session_state.setup_done = True
        st.session_state.last_setup_date = date.today()
        day_num = ship_day_number(ship_dates[0]) if ship_dates else None
        apply_off_schedule(day_num)
        st.session_state.active_screen = "UNLOAD"
        _mark_and_save()
        st.rerun()

# --------------------------
# Supervisor page
# --------------------------
elif st.session_state.active_screen == "SUPERVISOR":
    st.subheader("Supervisor - Admin & Statistics")

    avg_sec = average_load_time_seconds(sorted(st.session_state.loaded_set))
    st.metric("Average load time (today)", seconds_to_mmss(avg_sec) if avg_sec is not None else "N/A")

    c0, c1, c2, c3, c4, c5 = st.columns(6)
    with c0:
        st.metric("Dirty", len(dirty_trucks))
    with c1:
        st.metric("Unloaded", len(cleaned_list))
    with c2:
        st.metric("In Progress", str(inprog_truck) if inprog_truck is not None else "None")
    with c3:
        st.metric("Loaded", len(loaded_list))
    with c4:
        st.metric("Off", len(off_list))
    with c5:
        st.metric("Shop", len(shop_list))

    st.markdown("<h3 style='text-align:center; margin:0 0 8px 0;'>Configure run day and ship dates</h3>", unsafe_allow_html=True)
    run_date = st.date_input("Run date (today)", value=st.session_state.run_date or date.today(), key="sup_run_date")
    mode = st.radio("Mode", ["Normal (tomorrow only)", "Holiday (multiple load days)"], key="sup_mode")
    if mode == "Normal (tomorrow only)":
        ship_dates = [run_date + timedelta(days=1)]
    else:
        start = st.date_input("First ship date", value=run_date + timedelta(days=1), key="sup_ship_start")
        days = st.number_input("How many ship-days?", min_value=1, max_value=7, value=2, step=1, key="sup_ship_days")
        ship_dates = [start + timedelta(days=i) for i in range(int(days))]

    warn_min = st.number_input("Auto-warning threshold (minutes)", min_value=1, max_value=240, value=max(1, int(st.session_state.warn_seconds // 60)), step=1, key="sup_warn_minutes")

    if st.session_state.get("sup_run_date_last") != run_date:
        st.session_state["sup_run_date_last"] = run_date
        st.session_state.run_date = run_date
        st.session_state.ship_dates = ship_dates
        st.session_state.warn_seconds = int(warn_min) * 60
        st.session_state.setup_done = True
        st.session_state.last_setup_date = date.today()
        day_num = ship_day_number(ship_dates[0]) if ship_dates else None
        apply_off_schedule(day_num)
        _mark_and_save()
        st.rerun()

    with st.expander("Off schedule (Day 1-5)", expanded=False):
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
    if st.button("Apply & Save", use_container_width=True):
        if "sup_sched_day" in st.session_state:
            sd = int(st.session_state.get("sup_sched_day"))
            pick = st.session_state.get("sup_sched_pick") or []
            st.session_state.off_schedule[sd] = sorted({int(x) for x in pick})
        st.session_state.run_date = run_date
        st.session_state.ship_dates = ship_dates
        st.session_state.warn_seconds = int(warn_min) * 60
        st.session_state.setup_done = True
        st.session_state.last_setup_date = date.today()
        day_num = ship_day_number(ship_dates[0]) if ship_dates else None
        apply_off_schedule(day_num)
        _mark_and_save()
        st.success("Supervisor settings saved.")

    st.divider()
    st.markdown("<h3 style='text-align:center; margin:0 0 8px 0;'>Fleet Management</h3>", unsafe_allow_html=True)
    render_fleet_management()
    st.divider()
    with st.expander("Activity History", expanded=False):
        log = list(reversed(st.session_state.get("activity_log") or []))[:15]
        if not log:
            st.caption("No recent activity.")
        else:
            for entry in log:
                st.markdown(f"<div style='margin:0; padding:0; line-height:1.1;'>- {entry}</div>", unsafe_allow_html=True)
    st.write("### End of day PDF (compile anytime)")
    st.download_button(
        "Download PDF",
        data=generate_pdf_bytes(),
        file_name=f"truck_readiness_{(st.session_state.run_date.isoformat() if st.session_state.run_date else 'workday')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.divider()
    st.markdown("### Reset Workday Data (Supervisor)")
    st.caption("Dangerous: use only if you want to wipe the current day and saved state.")
    if st.button("Reset All Data (DANGEROUS)", key="sup_reset_start"):
        st.session_state.reset_step = 1

    rs = st.session_state.get("reset_step")
    if rs == 1:
        st.error("Step 1 — This will clear the in-memory session state for the app. Continue to step 2 to also delete the saved file.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Confirm Step 1", key="sup_reset_step1"):
                st.session_state.reset_step = 2
        with c2:
            if st.button("Cancel Reset", key="sup_reset_cancel1"):
                st.session_state.reset_step = None

    if rs == 2:
        st.error("Step 2 — This will delete the persisted state file on disk. Continue to step 3 to perform final erase.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Confirm Step 2", key="sup_reset_step2"):
                st.session_state.reset_step = 3
        with c2:
            if st.button("Cancel Reset", key="sup_reset_cancel2"):
                st.session_state.reset_step = None

    if rs == 3:
        st.error("Final Step — This will irreversibly erase all saved data and reset defaults. This cannot be undone.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Confirm Final Reset", key="sup_reset_final"):
                # Preserve fleet configuration (added and removed trucks)
                preserved_extra = st.session_state.get("extra_fleet", [])
                preserved_off_schedule = st.session_state.get("off_schedule", {}).copy()
                preserved_activity = st.session_state.get("activity_log", [])
                # Reset session_state keys to defaults, but restore fleet config
                for k, v in defaults.items():
                    st.session_state[k] = v
                # Restore the fleet configuration
                st.session_state["extra_fleet"] = preserved_extra
                st.session_state["removed_fleet"] = []  # Clear removed list to restore all trucks
                st.session_state["off_schedule"] = preserved_off_schedule
                st.session_state["activity_log"] = preserved_activity
                # Remove persisted state file
                try:
                    p = _state_path()
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
                save_state()
                st.success("Workday data reset to defaults. Fleet configuration preserved.")
                st.session_state.reset_step = None
                st.rerun()
        with c2:
            if st.button("Cancel Reset", key="sup_reset_cancel3"):
                st.session_state.reset_step = None

# --------------------------
# Unload
# --------------------------
elif st.session_state.active_screen == "UNLOAD":

    st.subheader("Unload")
    st.write("## Dirty trucks to clean")
    # Truck selection by clicking bubble, not dropdown
    sel_truck = st.session_state.get("unload_inprog_truck")
    def render_unload_bubbles(trucks, selected):
        # Render dirty truck bubbles as Streamlit buttons for in-place navigation
        cols = st.columns(8)
        for idx, t in enumerate(trucks):
            col = cols[idx % 8]
            with col:
                if st.button(str(int(t)), key=f"dirty_truck_{t}", use_container_width=False, type="primary"):
                    st.session_state["unload_truck_select"] = int(t)
                    st.session_state.active_screen = "BATCH"
                    _mark_and_save()
                    st.rerun()
    render_unload_bubbles(dirty_trucks, sel_truck)
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

# --------------------------
# Truck editor page
# --------------------------
elif st.session_state.active_screen == "TRUCK":
    t = st.session_state.selected_truck
    if t is None:
        st.warning("No truck selected.")
    else:
        st.subheader(f"Truck {t} — View Only (edit in Supervisor)")

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
            st.write(f"Started: {datetime.fromtimestamp(start_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        if finish_ts:
            st.write(f"Finished: {datetime.fromtimestamp(finish_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        if dur is not None:
            st.write(f"Duration: {seconds_to_mmss(dur)}")
        st.write(f"Shorts: {shorts_count} • Initials: {st.session_state.shorts_initials.get(t,'—')}" + (f" (saved {initials_ts})" if initials_ts else ""))

        st.write("**Status membership**")
        # determine current status
        if t in st.session_state.shop_set:
            cur_status = "Shop"
        elif t in st.session_state.off_set:
            cur_status = "Off"
        elif t in st.session_state.inprog_set:
            cur_status = "In Progress"
        elif t in st.session_state.loaded_set:
            cur_status = "Loaded"
        elif t in st.session_state.cleaned_set:
            cur_status = "Unloaded"
        else:
            cur_status = "Dirty"

        # Editing of truck membership/status is restricted to the Supervisor panel.
        st.info("Truck editing is restricted to the Supervisor page. Open Supervisor to make changes.")

        st.divider()
        st.write("**Supervisor note**")
        note = st.text_area("Note", value=st.session_state.sup_notes.get(t, ""), key="truck_note_text", height=120, disabled=True)

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
                    st.session_state.pending_batch_truck = None
                    st.session_state.pending_batch_wearers = 0
                    _mark_and_save()
                    st.success(f"Truck {t} marked Unloaded and assigned to Batch {batch_pick}.")
        elif t in st.session_state.cleaned_set:
            # allow toggling back to dirty or starting load
            if st.button("Mark Dirty", use_container_width=True, key=f"mark_dirty_{t}"):
                st.session_state.cleaned_set.discard(t)
                _mark_and_save()
                st.success(f"Truck {t} moved to Dirty.")
            if (t not in st.session_state.inprog_set) and (t not in st.session_state.loaded_set) and (t not in st.session_state.shop_set) and (t not in st.session_state.off_set):
                    if st.button("Start Loading (Supervisor only)", use_container_width=True, key=f"start_load_{t}"):
                        st.warning("Start Loading is only available from the Supervisor page.")

        st.divider()
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("Open in Supervisor for editing", use_container_width=True):
                st.session_state.sup_edit_truck = t
                st.session_state.active_screen = "SUPERVISOR"
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
        st.write(f"Batching — Truck {t}")
        st.markdown("<div id='batch-wearers'></div>", unsafe_allow_html=True)
        components.html("<script>const el=document.getElementById('batch-wearers'); if(el) el.scrollIntoView({behavior:'smooth'});</script>", height=0)
        w = st.number_input("Wearers", min_value=0, step=1, value=int(st.session_state.get('unload_inprog_wearers',0)), key=f"batch_wearers_{t}")
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
    st.subheader("Load")

    next_up = st.session_state.get("next_up_truck")
    if next_up is not None and not st.session_state.inprog_set:
        st.info(f"Next up: Truck {int(next_up)}")
        if st.button(f"Start Next Up (Truck {int(next_up)})", use_container_width=True, key="start_next_up_load"):
            start_loading_truck(int(next_up))
            _mark_and_save()
            st.session_state.active_screen = "IN_PROGRESS"
            st.rerun()

    render_next_up_controls("load")
    st.divider()

    st.write("### Start loading")
    start_truck = st.selectbox("Available trucks", true_available if true_available else ["(none)"], key="load_start_select")

    st.write("")
    start_disabled = (len(true_available) == 0) or (inprog_truck is not None)
    if st.button("Start", use_container_width=True, disabled=start_disabled):
        t = int(start_truck)
        start_loading_truck(t)
        _mark_and_save()
        st.session_state.active_screen = "IN_PROGRESS"
        st.rerun()

# --------------------------r
# Shorts
# --------------------------
elif st.session_state.active_screen == "SHORTS":
    t = st.session_state.shorts_truck
    st.subheader(f"Shortages — Truck {t}")

    if t is None:
        st.warning("No truck selected for shortages.")
    else:
        # Overview: show duration, live elapsed if in progress, batch, and supervisor notes
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
            st.write(f"Started: {datetime.fromtimestamp(start_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        if finish_ts:
            st.write(f"Finished: {datetime.fromtimestamp(finish_ts).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        if dur is not None:
            st.write(f"Duration: {seconds_to_mmss(dur)}")
        st.write(f"Shorts: {shorts_count} • Initials: {st.session_state.shorts_initials.get(t,'—')}" + (f" (saved {initials_ts})" if initials_ts else ""))
        note_text = (st.session_state.sup_notes.get(t) or "").strip()
        if note_text:
            st.divider()
            st.subheader("Notes")
            st.write(note_text)

        initials = st.text_input(
            "Initials (required)",
            value=st.session_state.shorts_initials.get(t, ""),
            max_chars=5,
            key="shorts_initials_input",
        )

        edited = st.data_editor(
            st.session_state.shorts.get(t, [{"item": DEFAULT_SHORT_ITEMS[0], "qty": 1, "note": ""}]),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item": st.column_config.SelectboxColumn("Item", options=DEFAULT_SHORT_ITEMS, required=True),
                "qty": st.column_config.NumberColumn("Qty", min_value=0, step=1, required=True),
                "note": st.column_config.TextColumn("Note (optional)"),
            },
            key="shorts_editor",
        )

        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("Save & Done", use_container_width=True):
                if save_shorts_stop_timer(t, initials, edited):
                    next_up = st.session_state.get("next_up_truck")
                    if next_up is not None and not st.session_state.inprog_set:
                        st.session_state.selected_truck = int(t)
                        st.session_state.active_screen = "STATUS_LOADED"
                    else:
                        st.session_state.active_screen = "LOAD"
                    st.rerun()
        with c2:
            st.info("Save stops the timer. 'Save & Done' saves shortages and returns to Load.")
