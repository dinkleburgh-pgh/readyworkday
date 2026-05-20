# Fix: Mobile STATUS_UNLOADED Button Grid Malformation (Build 79)

## Symptom

On mobile, the truck buttons on the **Unloaded** status page rendered in a staggered layout:

```
[ Truck 51 ]  [  empty   ]
[  empty   ]  [ Truck 52 ]
[ Truck 53 ]  [ Truck 54 ]
[ Truck 55 ]  [ Truck 56 ]
...
```

Only visible when a route card (OOS/spare assignments) was rendered above the truck buttons — i.e. when `_render_route_card()` produced visible output.

---

## Root Cause

`render_page_heading("Unloaded")` calls `_compress_mobile_fleet_like_status_heading_gap("unloaded")`.

This function injects JS that:
1. Finds `firstButton` — the `<button>` element of the first truck (truck 51).
2. Resolves `firstButtonHost` — `firstButton.closest('[data-testid="element-container"]')` — the element-container wrapping truck 51's button. This element sits **inside column 0** of the first `stHorizontalBlock` grid row.
3. Resolves `rowHost` — `firstButtonHost.closest('[data-testid="stHorizontalBlock"]')` — the row container that parents **both** columns.
4. Measures the visual gap between the heading chip and the first button.
5. Applies `margin-top: -Npx` (where N ≈ 190–290 px when a route card is present) to `firstButtonHost`.

Applying the negative margin to `firstButtonHost` moves **only column 0's element-container** upward out of its grid cell. Column 1 (truck 52) is not a descendant of `firstButtonHost` and remains at its natural position. The CSS grid cell for column 0 retains its reserved space, so the layout reads as an empty left cell followed by truck 52 in the right cell.

**Affected code** — `_compress_mobile_fleet_like_status_heading_gap`, inside the `apply()` callback:

```javascript
// BEFORE (buggy)
if (currentGap > 10 && currentGap < 700) {
    const desiredGapUnderHeader = 10;
    const reduceBy = Math.min(Math.max(0, currentGap - desiredGapUnderHeader), 420);
    firstButtonHost.style.setProperty('margin-top', `${-reduceBy}px`, 'important');
}
```

---

## Fix

Target `rowHost` (the `stHorizontalBlock` row container) instead of `firstButtonHost`. The entire first row — both columns — shifts up together, keeping the 2-column grid intact.

```javascript
// AFTER (fixed)
if (currentGap > 10 && currentGap < 700) {
    const desiredGapUnderHeader = 10;
    const reduceBy = Math.min(Math.max(0, currentGap - desiredGapUnderHeader), 420);
    // Apply to rowHost so both grid columns move together.
    (rowHost || firstButtonHost).style.setProperty('margin-top', `${-reduceBy}px`, 'important');
}
```

`rowHost` falls back to `firstButtonHost` when no `stHorizontalBlock` ancestor is found (e.g. a single-column layout), so there is no regression for those cases.

---

## DOM Hierarchy (mobile, STATUS_UNLOADED)

```
stHorizontalBlock  ← rowHost
├── stColumn (col 0)
│   └── element-container  ← firstButtonHost
│       └── stButton > <button>  ← firstButton  (Truck 51)
└── stColumn (col 1)
    └── element-container
        └── stButton > <button>  (Truck 52)
```

Applying `margin-top` to `stHorizontalBlock` moves both columns as one unit.

---

## Why the gap is large on mobile

On desktop, `STATUS_UNLOADED` uses `st.columns([1.2, 2.8])` — the route card is in a left column and truck buttons are in a right column, so they are vertically aligned from the start.

On mobile, `status_unloaded_left_col = st.container()` and `status_unloaded_main_col = st.container()` are stacked vertically. The route card occupies its own container above the truck buttons, adding ~200–300 px of vertical space between the heading and the first truck row. The gap-compression function exists to reclaim that space — it just needed to target the right DOM node.

---

## File & Line Reference

- **Function**: `_compress_mobile_fleet_like_status_heading_gap` in `app_unloadv1.7.py`
- **Changed line** (build 79): the `margin-top` application inside the `apply()` callback's gap-calculation block.
- **Note**: There is a separate, similar function for the Fleet Management heading (also in `app_unloadv1.7.py`) that uses `firstButtonHost` for its gap target — that one is intentionally unchanged because the Fleet page uses a single-column button layout where `rowHost === firstButtonHost`.
