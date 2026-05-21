# Changelog

## Unreleased

## v1.7.5 build 105 - 2026-05-21

1. Bumped build to **105**.
2. **UI / STATUS_OOS**: Added a top-left assignment chip on OOS truck buttons showing the assigned cover truck number when an OOS route has an active spare assignment.
3. **ROUTE COVERAGE LOGIC**: Route swap + OOS cover mappings are now merged through a shared active-coverage helper to avoid double-coverage interpretation and keep route-target/badge behavior consistent.

## v1.7.5 build 104 - 2026-05-21

1. Bumped build to **104**.
2. **FEATURE / BATCH + FLEET + UNLOAD + DIRTY**: Added an **Unfinished** outcome when batching a truck. In Batch Assignment (dialog and fallback flows), operators now have an `Unfinished` action that marks the truck with a dedicated `unfinished_set` status and returns to Unload.
3. **UI**: Unfinished trucks now render with a diagonal split red/green button style in the shared numeric truck button renderer, so the visual appears consistently on Fleet, Unload Management, and Dirty screens.
4. **STATE / MIGRATION**: Added backward-compatible persisted state support for `unfinished_set` (deserialize/serialize/defaults/load migration/sync), and updated related status transitions so unfinished state is cleared when trucks move to Shop, Unloaded, Spare, or In Progress.

## v1.7.5 build 103 - 2026-05-21

1. Bumped build to **103**.
2. **PERF**: Fleet Management multi-select is now significantly more responsive. Truck button clicks in multi-select mode now use a Streamlit `@st.fragment` scoped rerun — only the truck grid re-renders per click instead of the full page, cutting per-click latency. JS button-style retry delays are also reduced from four passes (70/220/450/900 ms) to two (70/200 ms) while in multi-select mode, eliminating unnecessary re-styling since truck colors do not change during selection.

## v1.7.5 build 102 - 2026-05-21

1. Bumped build to **102**.
2. **FEATURE**: "Route Swap Wizard" button added to Run Day Wizard Step 2/4. When unassigned OOS routes exist, a "✨ Route Swap Wizard" button appears above the manual form. Clicking it steps through each unassigned OOS route one by one, showing the AI spare suggestion (from build 101) first — "Yes, use Truck X" assigns immediately, "No, choose different" drops into the numeric truck picker for that route. Skip route and Exit wizard controls are available at each step. Skip/Back/Close buttons always remain accessible at the bottom of the dialog.

## v1.7.5 build 101 - 2026-05-21

1. Bumped build to **101**.
2. **FEATURE**: Smart spare suggestion when assigning a spare to an OOS route. The app now tracks the last 3 trucks used for each route on each load day in `spare_assignment_history.json`. When an OOS route needs a spare, the most frequently used truck for that route/day is presented first with a "Yes, use Truck X / No, choose different" prompt. If no history exists for that specific day, it falls back to the most recently used truck for that route on any day. Declining the suggestion drops through to the regular truck picker.

## v1.7.5 build 100 - 2026-05-20

1. Bumped build to **100**.
2. **IMPROVEMENT**: IN_PROGRESS page now loads immediately after starting a load from Unloaded status. Previously, starting a load triggered two Streamlit reruns (one to update the screen, a second for the URL to catch up). All start-load paths now call `_push_nav_history(force=True)` inline before the final `st.rerun()`, so the URL and screen update atomically in a single rerun. Affects: normal truck click (no dialog), confirm dialog, shop return confirm, off-day override, next-up queue auto-start, break return auto-start, and fleet admin start-load.

## v1.7.5 build 99 - 2026-05-20

1. Bumped build to **99**.
2. **BUG FIX**: Fixed "double-back" regression from build 97 — pressing Back once now navigates to the actual previous page instead of reloading the current page. Root cause: the JS nav block was calling `history.pushState` when in-page sub-params (e.g. truck selection on STATUS_LOADED, fleet sub-mode on FLEET) changed while staying on the same page and nav sequence. These same-page-nav transitions now use `history.replaceState` instead, so they update the URL without creating duplicate history entries.
3. **BUG FIX**: Route assignment card clicks no longer trigger an unintended full page reload. The synthetic `dispatchEvent(new Event('popstate'))` emitted by route assignment JS was being caught by the FORCE_POPSTATE reload listener. Fixed by filtering to only reload on real browser Back/Forward events (`event instanceof PopStateEvent`).

## v1.7.5 build 97 - 2026-05-20

1. Bumped build to **97**.
2. **FEATURE**: Browser Back/Forward navigation now works correctly. Enabled `FORCE_POPSTATE_RELOAD_ENABLED` — when the browser's back or forward button is pressed, the page reloads with the URL that was restored by the browser (e.g. `?page=UNLOAD`), and Streamlit navigates to the correct screen. Auth state is preserved via the server-side session store.

## v1.7.5 build 96 - 2026-05-20

1. Bumped build to **96**.
2. **BUG FIX**: "Select a truck to batch" hint pill was sticking on other pages after navigating away from UNLOAD/BATCH. Added an unconditional DOM cleanup at the universal page-dispatch point that removes the hint element immediately on every render outside those two pages.

## v1.7.5 build 95 - 2026-05-20

1. Bumped build to **95**.
2. **IMPROVEMENT / Auth — Random logout prevention (all three layers)**:
   - **Option 1 — Server-side session store**: After login, a session entry is written to `.truck_sessions.json` and a `truckapp_sid` browser cookie is set (30-day max-age). On every page load, the session store is checked first. Survives server restarts entirely.
   - **Option 2 — Direct JWT decode**: The `streamlit-authenticator` JWT cookie is now read and validated directly via `PyJWT` before falling back to the library's flaky cookie controller. Eliminates the race condition that caused false logouts on page reload.
   - **Option 3 — Tuned retry/grace constants**: Cookie expiry default raised from 7 → 30 days, retry attempts raised from 4 → 10, retry interval lowered from 1.25s → 0.75s, desktop grace from 6h → 24h, mobile grace from 7d → 30d.

## v1.7.5 build 94 - 2026-05-20

1. Bumped build to **94**.
2. **BUG FIX / Run Day Wizard Step 2/4**: OOS routes were blocked from assignment with "Truck is OOS" error, despite that being exactly the scenario requiring spare coverage. Selecting an OOS route now routes through `_assign_truck_to_oos_route` (the spare assignment mechanism) instead of `_apply_manual_route_change` (route swaps). OOS assignments appear in the "Current Assignments" list alongside route swaps and can be cleared with the X button.

## v1.7.5 build 93 - 2026-05-20

1. Bumped build to **93**.
2. **IMPROVEMENT / Run Day Wizard Step 2/4**: Renamed first dropdown label from "Truck" to "Route". OOS routes (trucks in the off set) now appear at the top of the dropdown list, labeled with `[OOS]`, so operators can quickly identify which routes are out of service when setting up route swaps. - 2026-05-19

1. Bumped build to **92**.
2. **BUG FIX / IN_PROGRESS**: `_apply_soft_auto_refresh` had an inverted guard condition for the IN_PROGRESS screen — it was skipping auto-refresh when a truck **was** active, but firing a 5-second rerun when **no truck** was active. This caused the IN_PROGRESS page to visibly flash/rerun every 5 seconds while the user was between trucks ("No truck currently in progress" state), perceived as an auto-redirect. Fixed by skipping auto-refresh on IN_PROGRESS entirely (the elapsed-time timer is client-side JS and does not require server reruns).

## v1.7.5 build 88 - 2026-05-20

1. Bumped build to **88**.

## v1.7.5 build 87 - 2026-05-20

1. Bumped build to **87**.
2. **BUG FIX**: `_get_truck_type()` was silently returning the default type for fleet-managed spare trucks because `truck_types` loaded from the JSON state file has string keys (JSON deserializes all keys as strings), while the lookup used `int`. Fixed with `types.get(t) or types.get(str(t))`.

## v1.7.5 build 86 - 2026-05-20

1. Bumped build to **86**.
2. **BUG FIX / LOAD + UNLOAD**: Trucks with type "Spare" set via fleet management (e.g. truck 1) were incorrectly counted as scheduled route trucks and appeared in the Unload Dirty list. Fixed three locations:
   - `_persistent_spares_seeded` block now runs after `_sync_next_up_from_state_file()` and includes fleet-managed spare-type trucks (via `load_truck_types()`) in the `spare_set` seed, not just the hardcoded `PERSISTENT_SPARE_TRUCKS = {10-17}`.
   - `scheduled_trucks_for_current_load_day()` now excludes any truck whose type is `TRUCK_TYPE_SPARE` via `_get_truck_type()`, not just those in the hardcoded set.
   - Sidebar unload total uses the same `_get_truck_type()` check instead of the hardcoded set.


1. Bumped build to **84**.
2. **UI / LOAD**: Replaced the large collapsible pace card on Load Management desktop with a unified 2×2 "Trucks Left" card grid shown on both desktop and mobile. Cards show Dusts Left, Uniforms Left, Spares Left, and Total Left counts. Clicking any card opens a modal dialog listing the route numbers in that category.
3. **UI / SIDEBAR**: Unload progress bar total now derived from the Day-Of Mapping (`off_schedule`) for the previous load day, instead of the `truck_load_day_by_truck` assignment map. Load and Unload totals now both reflect the scheduled truck count based on the Day 1–5 off-schedule.

## v1.7.5 build 82 - 2026-05-19

1. Bumped build to **82**.
2. **UI / SIDEBAR**: Fixed Load/Unload progress bar to use schedule-driven counts. Load total and remaining list now come from `current_load_day_completion()` (scheduled routes = fleet minus off-today minus persistent spares). Unload total and done count use `unload_trucks_for_current_day()` with set-arithmetic against cleaned/loaded/inprog/shop sets.

## v1.7.5 build 81 - 2026-05-19

1. Bumped build to **81**.
2. **UI / SIDEBAR**: Rewrote `_render_sidebar_load_unload_progress_card()` to derive counts directly from the same session-state sets used by the Live Status buttons, removing all prior-day run-mapping and route-inference fallback logic. **Unload** bar = (unloaded + in-progress + loaded + shop) / (dirty + unloaded + in-progress + loaded + shop). **Load** bar = loaded / (unloaded + in-progress + loaded). All counts exclude OOS/spare trucks, mirroring the Live Status display.

## v1.7.5 build 80 - 2026-05-19

1. Bumped build to **80**.
2. **UI / UNLOAD**: Applied updated button styling to the Unload Management mobile matrix. Buttons now match the Build 77 desktop/mobile unified look: gradient fill (`linear-gradient(170deg, ...)`), `1.5px` border, stronger box-shadow (`0 3px 10px rgba(0,0,0,0.45), inset 0 1.5px 0 rgba(255,255,255,0.13)`), `0.75px` text-stroke, `1.75rem` font-size, and stronger text-shadow (`0 1px 3px rgba(0,0,0,0.92), 0 0 6px rgba(0,0,0,0.6)`).

## v1.7.5 build 79 - 2026-05-19

1. Bumped build to **79**.
2. **UI / MOBILE — STATUS_UNLOADED button grid malformation**: Fixed a layout defect on mobile where the first two truck buttons in the Unloaded status list appeared staggered: truck 51 alone on the left with an empty right slot, then truck 52 alone on the right with an empty left slot, before the remaining trucks paired up correctly.

   **Root cause**: `_compress_mobile_fleet_like_status_heading_gap("unloaded")` runs JS to collapse the large visual gap between the "Unloaded" heading chip and the first truck button row (gap inflated by the route card rendered above on mobile). The JS measured the gap (~200–300 px when a route card is present) and applied `margin-top: -Npx` to `firstButtonHost` — the `element-container` wrapping truck 51's button, which lives **inside column 0** of the first `stHorizontalBlock` CSS grid row. That pulled only column 0 upward while column 1 (truck 52) stayed at its original DOM position, creating the empty-slot stagger.

   **Fix**: Changed the margin target from `firstButtonHost` (individual grid cell) to `rowHost || firstButtonHost` — where `rowHost` is resolved via `firstButtonHost.closest('[data-testid="stHorizontalBlock"]')`. Applying the negative margin to the row container shifts both columns as a unit, preserving the 2-column grid layout. See [`.github/fixes/build-79-mobile-unloaded-grid.md`](.github/fixes/build-79-mobile-unloaded-grid.md) for the full analysis.

## v1.7.5 build 78 - 2026-05-19

1. Bumped build to **78**.
2. **UI / UNLOAD**: "Select a truck to batch" bottom-pill is now cleared from the DOM immediately when navigating to any page other than STATUS_DIRTY, UNLOAD, or BATCH. Previously the pill lingered for up to 8 seconds after leaving those pages.

## v1.7.5 build 77 - 2026-05-19

1. Bumped build to **77**.
2. **UI / MOBILE BUTTONS**: Unified truck button text styling across all viewport sizes — mobile now uses the same font size (28px), text-stroke (0.75px), and text-shadow strength as desktop. Also applies gradient fill, `box-shadow`, and `1.5px` border to dialog/confirmation buttons on mobile (previously those only had a flat solid colour).

## v1.7.5 build 76 - 2026-05-19

1. Bumped build to **76**.
2. **UI / STATUS_UNLOADED**: Fixed ghost-click regression where mobile browsers fire synthetic `mousedown`/`click` events ~300 ms after a navigation touchend, causing a truck to start unintentionally. Added a 520 ms CSS `pointer-events: none` guard on all primary buttons when STATUS_UNLOADED renders so phantom events are absorbed before user interaction is enabled.
3. **UI**: Cleaned up any leftover `#truckapp-start-overlay` DOM elements from older builds still lingering in the browser.
4. **UI**: Added `display: none !important` to `[data-testid="stSkeleton"]` / `.stSkeleton` inside `[class*="_auto_refresh"]` containers to prevent skeleton flash on IN_PROGRESS and other auto-refresh pages.



1. Bumped build to **51**.
2. **MANAGEMENT / RUN DAY**: Fixed Run Day dialog stepper so all 4 steps (Dust Clothes, Spares/Swaps, Specials, Daily Notes) now complete in sequence before ending the flow. Dialog no longer stalls after step 1/4.

## Unreleased

## v1.7.5 build 75 - 2026-05-19

1. Bumped build to **75**.
2. **UI / BUTTONS**: Increased truck number font size (28px desktop / 1.48rem mobile for uniform pages, proportionally larger for non-uniform), added proper drop-shadow (`0 1px 3px rgba(0,0,0,0.92), 0 0 6px rgba(0,0,0,0.6)`), and slightly thickened `-webkit-text-stroke` (0.75px desktop / 0.48px mobile) for bold bright-white numerals that are highly readable on the gradient backgrounds.

## v1.7.5 build 74 - 2026-05-19

1. Bumped build to **74**.
2. **UI / MOBILE**: Removed spammy trend-page toasts ("Load pace trend is live", "Unload throughput trends", "Status mix trends") that fired on every render of the Trends page due to the global `st.info`/`st.success` toast override.
3. **UI / BUTTONS**: Polished truck button appearance — gradient fill (lighter top → base → darker bottom), `box-shadow` depth layer, `1.5px` border, `14px` border-radius, and smooth `filter: brightness` hover/active transitions via global CSS.

## v1.7.5 build 73 - 2026-05-20

1. Bumped build to **73**.
2. **PERFORMANCE / LOAD START**: Starting a load from Load Management (Status: Unloaded) now starts immediately for normal trucks, skipping the "Load truck X?" confirmation dialog. Edge cases (shop return, off-day override, spare route assignment, holiday multi-day) still show their confirmation prompts. This eliminates one full rerun cycle (~2–3s saved per load start).

## v1.7.5 build 72 - 2026-05-19

1. Bumped build to **72**.
2. **UNLOAD UI**: Replaced "Select a truck to begin unloading." top-right toast with a fixed center-bottom pill reading "Select a truck to batch" on the Unload Management page.
3. **UI**: Suppressed skeleton loader bars from `streamlit_autorefresh` timer components via global CSS targeting `[class*="_auto_refresh"]`, covering all pages including Communications.
4. **UI / NOTICES**: Added 2.75rem top margin to the pill page heading so it clears the collapsed Notices bar and does not overlap.

## v1.7.5 build 71 - 2026-05-19

1. Bumped build to **71**.
2. **NAVIGATION**: Fixed "Go to Unloaded" button on the STATUS LOADED page not navigating — the STATUS_* guard was snapping active_screen back to STATUS_LOADED on every stale-URL rerun. Guard now requires `url_nav_triggered` so it only fires on intentional URL-based navigation (status badges, direct URL), not on button-based STATUS→STATUS transitions.

## v1.7.5 build 70 - 2026-05-19

1. Bumped build to **70**.
2. **AUTH STABILITY**: Hardened session persistence to prevent random sign-outs by preserving last verified identity through transient cookie/authenticator misses.
3. **AUTH STABILITY**: Extended restore grace windows (desktop and mobile), stamped verification metadata immediately after successful portal login, and reset sticky metadata on explicit logout.

## v1.7.5 build 69 - 2026-05-18

1. Bumped build to **69**.
2. **AUTH / MOBILE**: Increased mobile auth restore grace window to reduce accidental fallback to Guest during transient cookie/session restore hiccups.
3. **MOBILE UI**: Hid pace-card surfaces on mobile (including Load pace card wrappers) to declutter the small-screen flow.
4. **STATUS LOADED**: Hardened the **Go to Unloaded** action with an explicit button key and constant-based target screen assignment.

## v1.7.5 build 68 - 2026-05-18

1. Bumped build to **68**.
2. **MANAGEMENT / ROUTE CHANGE**: Added a direct **Reset Swap** action in the Route Change panel so incorrect route swaps can be reverted immediately from the same workflow.
3. **MANAGEMENT / RUN DAY**: Hardened wizard step state transitions (Step 1-4) so dialogs stay in sync and are less likely to stall or end in partial state.
4. **RESPONSIVENESS**: Reduced repeat JSON disk reads during reruns by adding session-level mtime caches for communications, auth users/requests, audit history, and batch history.

## v1.7.5 build 67 - 2026-05-18

1. Bumped build to **67**.
2. Corrected app metadata build sequencing so repository build is ahead of production build 63.

## v1.7.5 build 61 - 2026-05-17

1. Bumped build to **61**.
2. **TRACKED ITEMS**: Removed Browns, 2x3, and Red/Red Shop from all tracking categories (Brown HW in Paper preserved).
3. **MANAGEMENT / RUN DAY**: Step 2/4 now shows a visible list of active route swaps (OOS + swap assignments) with Edit and Remove (×) actions.
4. **MANAGEMENT / RUN DAY**: Edit button and Load On token now display on the same horizontal line instead of stacking vertically.
5. **MANAGEMENT / RUN DAY**: Fixed delete (×) failing for OOS entries due to validation order.
6. **MANAGEMENT / RUN DAY**: Load On dropdown now starts blank (no auto-fill) and lists routes first.
7. **TRUCK BUTTONS**: Route badges on truck buttons are now consistently blue.
8. **PWA / MOBILE**: Removed the iOS install prompt (Add to Home Screen banner).

## v1.7.5 build 49 - 2026-05-14

1. Bumped build to **49**.
2. **MANAGEMENT / RUN DAY**: Fixed a crash on all devices by removing an invalid call to `_render_sup_run_day_specials_dialog` in the Step 3 flow path.
3. **LOAD / UNLOAD PROGRESS**: Fixed off-by-one route totals by treating runtime spare exclusions against the live route-capable fleet instead of the static default-fleet constant.
4. **LOAD MANAGEMENT CARDS**: Restored route-level remaining counts so Dust/Uniform/Spare/Total cards stay in sync with sidebar progress totals.

## v1.7.5 build 48 - 2026-05-14

1. Bumped build to **48**.
2. **LOAD / UNLOAD COUNTS**: Fixed sidebar progress to use stable current-day totals even when day mapping is partial, while still excluding non-route spare trucks from route totals.
3. **LOAD MANAGEMENT**: Restored original remaining-card logic (Dusts/Uniforms/Spares/Total Left) with reliable countdown values.
4. **AUDIT FLEET (MOBILE)**: Removed duplicate truck header, kept the existing Auditing Truck pill heading, and added positioning protection so it is not hidden by the Notices overlay.
5. **AUDIT FLEET (MOBILE)**: Grouped the Bulk category button with the other category buttons by removing the separate spacer/wrapper behavior.

## v1.7.5 build 44 - 2026-05-13

1. Bumped build to **44**.
2. **PWA / MOBILE**: Added a branded iOS install prompt with Add to Home Screen steps for iPhone and iPad browsers.
3. **PWA / MOBILE**: Reused the same install banner surface for native browser install prompts where supported and added prompt snoozing so it does not keep nagging users.

## v1.7.5 build 43 - 2026-05-13

1. Bumped build to **43**.
2. **STATUS DIRTY**: Fixed the mobile Dirty page spacing so the truck grid sits correctly under the page heading like the Unloaded page.
3. **STATUS DIRTY**: Replaced the repeated dirty-page batching hint toast with a quiet caption so mobile navigation no longer gets spammed.

## v1.7.5 build 42 - 2026-05-13

1. Bumped build to **42**.
2. **TRENDS**: Stopped the mobile trends screen from repeatedly surfacing selection-detail toast popups while navigating the page.
3. **MANAGEMENT / RUN DAY**: Added an explicit **Reset Swap** action to the route-change workflow so a single route swap can be cleared directly from fleet management or Run Day.

## v1.7.5 build 40 - 2026-05-13

1. Bumped build to **40**.
2. **UNLOAD**: Removed the mobile pace card from the Unload/Management flow so it no longer blocks the screen on mobile.
3. **MANAGEMENT / RUN DAY**: Exposed OOS trucks in the route-swap Truck dropdown, including the Run Day step 2/4 dialog, and labeled them clearly.
4. Kept the route-swap picker ordering stable so OOS trucks appear first in the list.

## v1.7.5 build 39 - 2026-05-13

1. Bumped build to **39**.
2. **AUDIT FLEET**: Replaced the mobile Auditing badge with an `Auditing Truck #` heading when a truck is open, and kept Change Truck directly below it.
3. **AUDIT FLEET**: Prioritized OOS routes first in the step 2/4 route selector so the most important assignments are shown first.
4. Preserved the mobile audit button grid layout and spacing so the option buttons remain unobstructed.

## v1.7.5 build 36 - 2026-05-13

1. Bumped build to **36**.
2. **AUDIT FLEET**: Enhanced mobile audit layout with orange truck header styling (background #f59e0b, font-size 1.32rem).
3. Improved: Centered "Change Truck" button below truck header with adjusted spacing.
4. Refined: Mobile audit category buttons rendered in responsive 2x2 grid (3x10, 3x5, 4x6, Paper) with Bulk button for full-width selection.
5. Updated: Reduced spacing and margins throughout audit panel for cleaner mobile appearance.

## v1.7.5 build 34 - 2026-05-12

1. Bumped build to **34**.
2. **FIXED**: Login dialog now closes immediately after successful authentication and redirects to the authenticated page.
3. Improved: Explicit authentication state synchronization ensures proper session state on login redirect.

## v1.7.5 build 32 - 2026-05-12

1. Bumped build to **32**.
2. **CRITICAL FIX**: Added auth_users.json and auth_user_requests.json to git repo (removed from .gitignore) so login credentials are deployed with the Docker image.
3. Created data/ directory structure in git repo to match docker-compose volume mount point (/app/data) for proper credential and state file persistence in containerized environments.
4. Fixed startup timing: moved version banner to execute immediately on app load instead of waiting for first client connection.

## v1.7.5 build 30 - 2026-05-12

1. Bumped build to **30**.
2. Added green highlight (checked state) to Step 1/4 Run Day dust garment checkboxes, matching the Step 3/4 bubble style.
3. Fixed `DUST_GARMENT_TRUCK_OPTIONS` fallback to exclude truck 90 (not in fleet) in addition to 91.
4. Updated changelog skill to default to build-only bumps; version changes now require explicit user request.

## v1.7.5 - 2026-05-12

1. Updated app metadata release to **v1.7.5** with release date **20260512**.
2. Hardened refresh auth persistence across desktop/mobile by adding bounded silent cookie rehydrate retries, a short post-login cookie-commit delay before rerun, and lowercase username normalization for authenticator token consistency.
3. Fixed login failure for users whose username was stored with mixed case by normalizing cookie lookup to lowercase.
4. Renamed "Save Dust Clothes" button to **Save Garments** with green styling; updated caption to "Select FS (Dust) garments for this load day".
5. Changed OFF status badge color from red to pink.
6. Condensed user directory card layout: compact single-row format with repositioned edit button.
7. Updated Run Day Step 2/4 dialog: all buttons scaled 25% larger.
8. Updated Run Day Step 3/4 dialog: renamed instruction text to "What trucks are NOT here to start the day?", added helper sub-text, and scaled truck bubbles to 65×65 px with centered labels and green checked state.
9. Fixed `DUST_GARMENT_TRUCK_OPTIONS` fallback to exclude truck 90 (not in fleet) in addition to 91; dust garment dialogs now correctly filter to Dust-type trucks only.

## v1.7.4 - 2026-05-12

1. Updated app metadata release to **v1.7.4** with release date **20260512**.
2. Fixed random sign-outs on page refresh: added explicit `cookie_controller.get_cookie()` call (streamlit-authenticator 0.4.x) and increased silent cookie retry attempts from 2 to 5.
3. Refactored `_current_load_day_remaining_breakdown()` to classify remaining trucks by the new truck-type system (`_get_truck_type()`) instead of the day's dust-garment selection.
4. Added Dust / Uniform / Spare remaining-trucks counter to the LOAD page main column, updating dynamically as trucks are loaded.
5. Added editable truck type (Uniform/Dust/Spare) to Management → Manage Fleet with per-truck Save/Reset, persisted in `truck_fleet.json`.
6. Fixed mobile LOAD page: moved Audit button to last position to reduce accidental taps; added 80 px spacer so the fixed pace bar no longer covers truck buttons.

## v1.7.3 - 2026-05-11

1. Updated app metadata release to **v1.7.3** with release date **20260511** and build 14.
2. Updated deployment image references in compose files to **v1.7.3**.
3. Updated README release references and `requirements.txt` baseline label to **v1.7.3**.
4. Rewrote sidebar bouncer toggle button (v3): fixed jitter caused by watching CSS `style` mutations, added 80ms debounced sync, reduced DOM writes, bumped poll interval to 1500ms, and widened button to 26px.
5. Improved Run Day dialogs (Steps 1-4): renamed Step 1 to "Select Dust Garments" with purple centered header; standardized button order (Save/Continue -> Skip -> Back -> Close) and colors (green/amber/blue/red) across all steps; removed Skip from Step 4.
6. Fixed truck-number checkbox labels in Step 1 so numbers no longer wrap on mobile (added `white-space:nowrap`).
7. Added initial Progressive Web App support for mobile/tablet installability, including manifest, service worker/offline fallback, and mobile web app meta tag bootstrap in the main app shell.
8. Removed manual load-day switching controls from Management and standardized automatic load-day rollover to 6:00 AM.
9. Updated shift handoff/snooze state handling to be user-scoped so one signed-in user's shift actions no longer affect other users.

## v1.7.2 - 2026-05-10

1. Fixed invalid escape sequences in JavaScript code to resolve SyntaxWarning messages.
2. Updated app metadata release to **v1.7.2** with release date **20260510**.
3. Ensured backward compatibility for state management and navigation fixes.
4. Updated deployment defaults/tags to **v1.7.2** in `docker-compose.yml`, `docker-compose.portainer.yml`, and `docker-entrypoint.sh`.
5. Updated README release/deployment references and `requirements.txt` baseline label to **v1.7.2**.

## v1.7.1 - 2026-04-07

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.7.1** with release date **20260407**.
2. Added mobile gesture support for the sidebar: swipe-left closes, and left-edge swipe-right opens.
3. Improved mobile sidebar swipe reliability (wider edge capture, tolerant thresholds, and drag-open handling).
4. Prevented immediate sidebar re-close after swipe-open by adding a short outside-tap suppression window.
5. Updated mobile dock cards so expanded state is opaque and collapsed state is transparent.
6. Updated deployment defaults/tags to **v1.7.1** in `docker-compose.yml`, `docker-compose.portainer.yml`, and `docker-entrypoint.sh`.
7. Updated README release/deployment references and `requirements.txt` baseline label to **v1.7.1**.

## v1.7.0 - 2026-04-06

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.7.0** with release date **20260406**.
2. Fixed soft workday reset behavior to preserve Off/OOS, Spare, Shop, and Special states while preventing excessive Dirty/Unloaded misclassification.
3. Corrected load-day initialization behavior for management load-date changes so day-based configuration is applied without restoring stale archived status distributions.
4. Updated STATUS_UNLOADED desktop shell widths so the left rail route card has more usable space and the right off-schedule rail is narrower.
5. Enhanced STATUS_SHOP rail UX by adding clear active-mode highlighting for **Send** vs **Return**, removing extra separators, and aligning button block vertical start with the route card.
6. Updated deployment defaults/tags to **v1.7.0** in `docker-compose.yml`, `docker-compose.portainer.yml`, and `docker-entrypoint.sh`.
7. Updated README release, deployment, and pinned-image references to **v1.7.0**.
8. Promoted `app_unloadv1.7.py` as the main app entry file and moved previous root app version files into `backups/` to prevent runtime file-selection confusion.

## v1.6.9 - 2026-03-20

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.6.9** with release date **20260320**.
2. Updated deployment image references in compose files to **v1.6.9**.
3. Updated README release and deployment tag references to **v1.6.9**.

## v1.6.7 - 2026-03-18

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.6.7** with release date **20260318**.
2. Removed the legacy **Current** pace shift option and standardized pace views to explicit **1st Shift / 2nd Shift / 3rd Shift** selection with live auto-default behavior.
3. Updated Load Pace **Ahead/Behind** calculations to compare projected finish time against the selected shift end time so each shift view reports independently.
4. Added a shared pace-shift selection resolver so pace cards auto-follow the live shift by default while preserving manual shift overrides.
5. Integrated compact shift selectors directly into the header area of sidebar Mini Pace, In Progress Mini Pace, and Load Pace cards.

## v1.6.6 - 2026-03-17

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.6.6** with release date **20260317**.
2. Added migration hardening so legacy manual pace overrides (`60` seconds) are normalized once to the current 10-minute default and tracked by migration version.
3. Fixed previous-load-day OFF auto-pull reliability so day changes immediately move eligible trucks to **Unloaded** while excluding trucks used for route coverage or OOS spare assignments.
4. Added an **Archive Calendar** under Configure Load Day that only lists dates with saved `state_history` snapshots and opens that archived day directly.
5. Restyled the sidebar **Signed In** identity area into a clearer visual card with name and role presentation.
6. Pinned compose image/version settings to **v1.6.6** in tracked deployment files to prevent stale launches from external `latest` or older env overrides.
7. Updated GitHub Docker publish workflow to also push a versioned image tag (`vX.Y.Z`) from app metadata so compose releases pinned to `v1.6.6` can be deployed directly.
8. Added configurable loader-based pace scaling (active vs baseline loaders) so staffing materially changes Mini Pace, In Progress pace, and Load Pace finish estimates.

## v1.6.5 - 2026-03-16

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.6.5** with release date **20260316**.
2. Added signed **Time Saved** metrics (+ green / - red) to the `STATUS_LOADED` overview card based on average load-time comparison.
3. Added LOAD pace **shift-view** controls (`Current`, `1st Shift`, `2nd Shift`, `3rd Shift`) with selector placement inside the pace card.
4. Pace card estimate behavior now shows a retrospective finish projection even after a selected shift has ended.
5. Reworked LOAD next-up flow by removing the bottom queue panel and adding a **Set Next Up** dialog with ready-truck dropdown.
6. Moved LOAD **Start loading** controls above the pace card for faster access during active operations.
7. LOAD Off Day schedule expander now defaults to collapsed on mobile devices.
8. Hardened rerun behavior by skipping no-op query-param writes to reduce unnecessary app rerenders.
9. Reduced client-side UI script load by trimming persistent observers/timers and skipping mobile-only grid enforcement on desktop.
10. Added session-level cache/invalidation for load-duration history reads and writes.
11. Added reusable batch-card PDF byte caching to avoid expensive regeneration on repeated reruns.
12. Updated SHORTS overview layout for even card fill and removed long helper text under the Save & Done area.
13. Hardened frontend overlay/observer behavior to reduce occasional blank-page incidents (safer notice host mounting, throttled resize handling, and auto-expiring sidebar/dropdown MutationObservers).
14. Disabled custom top-overlay Shop notices in favor of native Streamlit Notices rendering for improved page stability under reruns/navigation.
15. Added a global stability mode that disables nonessential parent-DOM enhancement scripts and forced popstate reloads to prioritize page-render reliability.
16. Added a guarded blank-page watchdog that detects prolonged empty-main render stalls, performs limited auto-recovery reloads, and shows a manual hard-refresh hint if recovery limit is reached.
17. Restored live fleet/status truck-button colors by separating color-styling scripts from the broader DOM-enhancement stability toggle.
18. Restored Live Status sidebar visuals and truck decoration features via targeted toggles, while keeping higher-risk mobile grid and dropdown-lock DOM hooks disabled.
19. Set Dust Clothes controls now hide after garments are marked set for the current load day (Load + Management views), preventing redundant re-prompting.
20. Replaced date-only rollover banner with shift/day dialogs: 2nd-shift day-start prompt (Continue Load Day or Start Load Day), 3rd-shift handoff prompt (Continue Load Day or Start Next Load Day), and all-loaded End-of-Day prompt (Download End Of Day PDF, Snooze Day Change 1hr, Start Next Load Day).
21. Updated LOAD pace-card "Ahead/Behind by" math so non-Current shift views are based on that full shift's work-hour capacity instead of live time-left.
22. Restored the top overlay Notices bar as default behavior so shop notice collapse/expand and flash acknowledgment run in the original overlay workflow again.
23. Reorganized Management page flow into clearer section headers (Operations, Access and Preferences, Reporting, Advanced and Reset) to improve scanability.
24. Moved Management **Set Dust Clothes** into a dedicated dialog workflow while keeping day-scoped completion behavior intact.
25. Refined **Communication Settings** by flattening nested dropdowns and moving message-history review into a dedicated dialog.
26. Converted Management PDF downloads into a focused report-download dialog with grouped load/shortages, batch-cards, and end-of-day actions.
27. Added a Fleet-specific lightweight mode for sidebar Live Status button decorations (dots/corner badges/nav outlines): styling stays on, but observer/retry work is reduced while on Fleet to cut UI hangs.
28. Optimized truck-button styling scripts by reducing Fleet retry passes, short-circuiting repeated style writes, and avoiding redundant badge re-creation when content is unchanged.
29. Expanded lightweight styling mode to include UNLOAD/BATCH pages so Live Status and truck-button visuals stay enabled while reducing observer/retry pressure where hangs were also observed.
30. Further reduced UNLOAD/FLEET DOM pressure by trimming heavy-page truck-button retry passes, disabling heavy-page resize restyling, and simplifying lightweight sidebar re-apply behavior to a single delayed pass.
31. Added emergency heavy-page stabilization: disabled soft auto-refresh on Fleet/Unload/Batch and turned off expensive truck-decoration DOM scripts on those pages while keeping button color styling and sidebar Live Status styling active.
32. Styled **Ran Special** notices in the Notices dropdown/overlay with an accent highlight (pink + bold) so they are no longer rendered as plain white text.
33. Made **Ran Special** chips in the UNLOAD Route Card clickable to open the truck directly into batch/unload flow from the watch panel.
34. Updated Fleet truck buttons so **Shop** trucks render in a light red style and automatically show a **SHOP** chip badge.
35. Expanded the UNLOAD Route Card interaction so the entire **Ran Special** row is clickable, and standardized Shop truck buttons across all numeric-button pages to gray with white text plus a light-red **SHOP** chip.
36. Updated **Special** truck buttons to use the same base styling as Dirty on all numeric-button pages, and added a purple **SPECIAL** clip badge for clear visibility.
37. Updated unload completion behavior so trucks marked **Special** are cleared from the Route Card watch list after they are unloaded.
38. Restored **Shop** truck button and live-status color styling to purple (with white text on Shop buttons) while retaining the SHOP clip badge behavior.
39. Restored missing **OOS** truck indicators on button pages by re-enabling OOS/OFF clip rendering in lightweight mode and restoring the OOS red-X overlay.
40. Added Development import tools to upload archived `load_durations` JSON (append or replace) and upload one-or-many `state_history` JSON files with optional overwrite for matching dates.
41. Added a one-file **History Backup Package** workflow in Development to export/import both `load_durations` and archived `state_history` together for easier app-version migrations.
42. Applied route clip badges to OFF-route cover trucks on **Unloaded** so spare/cover trucks assigned to a route show their `R#` clip in the bubble grid.
43. Updated LOAD Dust Clothes control to stay visible after set and switch button text to **Edit Dust Garments** instead of disappearing.
44. Removed the LOAD caption text **"Dust Clothes set for this load day."** while keeping the Dust Garments button behavior unchanged.
45. Fixed a LOAD dialog-state bug where **Edit Dust Garments** could immediately close; the button now consistently opens the Dust Clothes editor for updates.
46. Improved Dust Clothes truck selection ergonomics for mobile/fat-finger use by enlarging checkbox tap targets and reducing selection grid density in both LOAD and Management dialogs.
47. Fixed Dust Clothes dialog mobile layout collapsing to one column by forcing a two-column checkbox grid on phone widths in both LOAD and Management dialogs.
48. Removed Dust Clothes helper captions from LOAD and Management, kept the Dust Clothes button always visible as **Set Dust Clothes / Edit Dust Garments**, and moved the Management Dust button directly below **Open Shift Handoff**.
49. Removed the Configure Load Day summary text block above **Open Shift Handoff** in Management for a cleaner top-of-section layout.
50. Added a flashing blue outline prompt to LOAD **Set Next Up** when no Next Up truck is set but ready/unloaded trucks are available.
51. Reworked IN_PROGRESS layout so **Current Truck** renders at the top-left column, while **Elapsed Time**, **Finish Loading**, and **Next Up** controls render in the right column.
52. Refined IN_PROGRESS column presentation by centering the **Current Truck** label/number stack above Daily Notes and adding desktop equal-height balancing so left/right columns match height.
53. Fixed Fleet status-apply reliability: previous-day off auto-promote to **Unloaded** now runs once per load day (not on every edit), and status feedback now reports the truck’s final applied status after normalization.

## v1.6.2 - 2026-03-13

Ordered list of final changes included in this release:

1. Updated app metadata release to **v1.6.2** with release date **20260313**.
2. Fleet Step 2 now includes an **Assign** option when a selected truck requires route assignment.
3. OOS spare-assignment flow on `STATUS_CLEANED` now includes route dropdown selection with OFF routes first, then In Service routes.
4. OOS route dropdown placement was adjusted to render below spare buttons and above the clear/cancel bar, with helper label text removed.
5. Added guardrails preventing unloaded persistent spares from starting load until they have an assigned route.
6. Guardrails were applied consistently across start paths (Status Cleaned confirm, Next Up start, break auto-start, load-page start, and URL start).
7. Sidebar Live Status for Guest role now shows all status badges while only **In Progress** remains accessible.
8. Fleet truck buttons now display **OFF** clip badges for OOS and scheduled-off trucks.
9. Fleet OOS red-X rendering was stabilized when badges are present, with thinner stroke width for cleaner readability.
10. Truck-button badge rendering/positioning was hardened so badge chips stay top-right without displacing centered truck numbers.
11. Increased truck-number font sizing on numeric truck buttons for better visibility.
12. Added a new **Development** section in Management with download actions for `load_durations.json` and current-day state-history JSON.

## v1.6.1 - 2026-03-12

Ordered list of final changes included in this release:

1. `STATUS_LOADED` selected-truck panel was de-duplicated by removing repeated stats/details under the overview card.
2. Finishing load from In Progress now auto-selects that truck on `STATUS_LOADED` so the overview card appears immediately.
3. Fixed `STATUS_LOADED` card refresh-on-click by syncing loaded-truck bubble selection with URL query params.
4. Route swap badges were enlarged and repositioned for improved readability near the upper-right of truck buttons.
5. Route/assignment badges now render outside button bounds without clipping by correcting overflow handling on host wrappers.
6. Admin role display wording was updated from **Management** to **Fleet** for role labels and related helper text.
7. Route Card swap rows now use a consistent route-side **SWAP** tag while still showing the assigned truck’s live status on the truck side.
8. Route Card was added to Fleet and moved to left-panel placement on desktop, including matching left/main column structure on Unloaded.
9. Route Card collapse UI was redesigned to match the Load-page pace-card interaction pattern (header toggle, chevron, animated collapse, persisted state).
10. Route Card row/chip sizing and wrapping were tuned to prevent status-tag edge clipping (including long tags such as **LOADED**).

## v1.6.0 - 2026-03-11

Ordered list of final changes included in this release:

1. Promoted `app_unloadv1.6.py` as the primary app entry file while retaining `app_unloadv1.5.py` as the prior release entry file.
2. Updated app metadata release date to **20260311** with app version **1.6**.
3. Route badge rendering was stabilized across pages with in-button chips, improved scope/refresh behavior, and badge layering above OOS indicators.
4. Added OOS load-on badge visibility so OOS routes show the truck loading for them (including Fleet and route-badge views).
5. Updated pace math and wording to be time-based (instead of truck deltas) with 30-minute break-adjusted shift calculations (7h30 effective).
6. Main Load pace card now live-updates client-side and includes the new **Last Truck (#)** tile with added/saved time indicators.
7. `STATUS_LOADED` metrics were redesigned into richer visual tiles with additional operational context (route/source, pace impact, averages, finish age, and load order data).
8. Started/Finished timestamps were moved into loaded-truck card tiles and removed from plain text blocks on TRUCK/SHORTS pages.
9. Fleet route assignment tools now support one-way assignment and clear-assignment actions while preserving two-way swap.
10. Authentication UX was refined to reduce login popup interruptions on navigation/back using improved silent cookie re-auth handling.
11. Updated default persisted fleet/state baseline files to match the approved current configuration (`.truck_state.json`, `truck_fleet.json`, `off_schedule_defaults.json`).
12. Updated runner/container defaults to v1.6 (`run_streamlit.sh`, `docker-entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, `docker-compose.portainer.yml`).
13. Updated README release docs and command examples to v1.6 defaults.

## v1.5.0 - 2026-03-10

Ordered list of final changes included in this release:

1. Promoted `app_unloadv1.5.py` as the primary app entry file while retaining `app_unloadv1.4.py` as the prior release file.
2. Updated app metadata release date to **20260310** with app version **1.5**.
3. In Progress and Load layouts now stack for mobile to prevent clipped side-by-side rendering.
4. Added state-history load-day metadata fields to archived JSON payloads (`history_run_date_key`, `history_ship_date`, `history_load_day_num`, `history_load_day_label`).
5. Management (Supervisor) screen top statistics strip was removed for a cleaner admin view.
6. User Management now shows a green confirmation dialog after **Create user** and **Save user changes**.
7. User picker labels now include role before enabled state (`username (Role • Enabled/Disabled)`).
8. Updated runner/container defaults to v1.5 (`run_streamlit.sh`, `docker-entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, `docker-compose.portainer.yml`).
9. Updated README release docs and command examples to v1.5 defaults.
10. Refreshed `requirements.txt` for v1.5 release baseline.

## v1.4.0 - 2026-03-09

Ordered list of final changes included in this release:

1. Promoted `app_unloadv1.4.py` as the primary app entry file and updated app metadata version to **1.4.0**.
2. Added `backups/v1.3/` snapshot with `app_unloadv1.3.py` and the prior `CHANGELOG.md`.
3. In Progress layout was rebalanced to follow the centered status-page style while preserving the large timer-focused display.
4. In Progress Daily Notes now render as bullets per line with larger, bolder text for display readability.
5. In Progress empty-state messaging/buttons were resized and centered for better proportional spacing.
6. Added In Progress keep-awake behavior using Screen Wake Lock with media/session fallback and auto-reacquire logic.
7. Improved mobile wearers keypad reliability on unload batching with stronger focus retries and touch/click focus hooks.
8. Shop workflow on `STATUS_SHOP` was simplified to reduce clutter: page now shows current shop trucks with concise **Send** and **Return** controls.
9. Added shared helper functions for send/return shop transitions to keep Fleet and Status-Shop behavior consistent.
10. Added Load-page **Load Progress** dropdown under Off Day showing scheduled total, remaining-to-load, and loaded count.
11. Replaced always-visible remaining list with `Show remaining` / `Hide remaining` toggle in the Load Progress dropdown.
12. Centered numeric totals in the Load Progress cards for clearer visual balance on wall/display screens.
13. Updated runner/container defaults to v1.4 (`run_streamlit.sh`, `docker-entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, `docker-compose.portainer.yml`).
14. Updated README release docs and command examples to v1.4 defaults.
15. Updated `requirements.txt` with explicit minimum dependency versions.

## v1.3.1 - 2026-03-06

Ordered list of final changes included in this release:

1. In Progress elapsed timer now starts flashing at **20:00** (20 minutes).
2. On Unloaded, once an OOS route is assigned a spare, that OOS route is removed from Unloaded to prevent double loading.
3. Normalization and derived-list logic now keeps assigned OOS routes excluded from Unloaded until assignment is cleared.
4. Fresh-slate data reset applied to repository runtime data:
	- cleared `load_durations.json`
	- cleared `.truck_state.json` OOS/spare state and OOS→spare assignments
	- cleared persisted in-progress timing/duration maps in `.truck_state.json`

Notes:
- This release focuses on cleaner OOS loading workflow behavior and a fresh baseline dataset.

## v1.3.0 - 2026-03-05

Ordered list of final changes included in this release:

1. In Progress page now keeps **Daily Notes** sticky while scrolling, with constrained viewport height and internal notes scrolling.
2. In Progress layout was tightened and centered so **Current Truck** and timer alignment are consistent with reduced top/side spacing.
3. Timer warning copy was simplified to **"Load time exceeded"**.
4. Added configurable **Status bubble colors** in App Settings with live persistence to state.
5. Added **Reset to defaults color scheme** action under App Settings and synchronized picker values after reset/apply.
6. Truck status-button rendering now consumes configured status colors (bubble-to-button color mapping).
7. Sidebar live-status controls were reverted from colored backgrounds to default buttons and now show a color dot indicator only.
8. Truck number text color is now forced black across pages except OOS/Spare (white on grey) for readability consistency.
9. OOS workflow was improved by moving the **Add** action into the OOS truck grid as a trailing slot.
10. SHORTS button-mode delete now uses two-step confirmation (✕ then Confirm delete/Cancel).
11. SHORTS category helper text was removed and **Recents** label centering was improved on In Progress.
12. App metadata version was updated to **1.3.0**.
13. Promoted `app_unloadv1.3.py` as the primary app entry file for v1.3 release usage.
14. Updated startup defaults to v1.3 in shell runner and container environment (`APP_FILE`).
15. Added first-class containerization assets: `Dockerfile`, `docker-compose.yml`, and `.dockerignore`.
16. Added README deployment guidance for Docker Compose and Portainer Git-stack deployment.
17. Added `docker-compose.portainer.yml` image-only stack file to bypass Portainer compose-build permission issues.
18. Added GitHub Actions workflow (`.github/workflows/docker-publish.yml`) to publish container images to GHCR.
19. Expanded README Portainer section with build vs no-build deployment paths and required environment variables.

Notes:
- This release focuses on In Progress UX polish, status-color control reliability, and safer/clearer SHORTS interactions.

## v1.2.1 - 2026-03-04

Ordered list of final changes included in this release:

1. Fleet Management now always opens on the refreshed truck picker when entering Fleet from navigation.
2. Fleet Step 1 heading was simplified to "Select Truck" and helper text under the picker was removed.
3. Fleet status updates now force an immediate rerun so live sidebar badges (including Shop) refresh instantly.
4. Fleet status update success messaging now persists across rerun for consistent feedback.
5. Out Of Service status page was split into two sections: "Spare" and "Out Of Service".
6. Loaded and Shop visual status colors were aligned across badges and truck buttons (Loaded = blue, Shop = purple).
7. Sidebar live-status badges now correctly apply the passed color style.
8. Fleet truck picker highlights in-progress trucks with a flashing button treatment.
9. Fleet remove-truck confirmation now returns users to the refreshed Fleet picker view after successful removal.
10. Fleet "New" trailing button text was centered.
11. Truck button auto-fit sizing was tuned to render three-digit truck numbers larger.
12. Shorts entry view in button mode was simplified to compact rows with per-row delete (✕), replacing the heavier inline editor approach.

Notes:
- This release focuses on Fleet UX flow, status visibility consistency, and shorts-entry usability refinements.

## v1.2.0 - 2026-03-04

Ordered list of final changes included in this release:

1. Fleet Management status tools were expanded to support bulk status updates for multiple selected trucks in one action.
2. Added guardrails for bulk updates so "In Progress" can only be assigned to one truck at a time.
3. Hardened pending Fleet Management status payload handling to avoid stale/malformed session-state failures.
4. Repaired shop notice UI behavior (rendering, collapse/expand behavior, and notice targeting reliability).
5. Updated Fleet Management selected-truck presentation to a larger boxed header while preserving text styling.
6. Renamed Fleet Management navigation button text from "Back to Step 1" to "Change Truck".
7. Added shared truck-button status coloring logic so truck buttons reflect live status without breaking click behavior.
8. Updated truck-button styling for improved readability: bold text, black label color, and dynamic size fitting/centering per button.
9. Added Step 1 Fleet Management trailing action button labeled "New" as the final button in the truck picker grid.
10. Added "New" route flow in Fleet Management to open a dedicated add-truck screen and persist newly added trucks.
11. Removed white text outline from truck-button labels per final UI preference.

Notes:
- This changelog captures feature-level final changes for v1.2.0.
- Runtime-generated state/log artifacts are not considered release features.
