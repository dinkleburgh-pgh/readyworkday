# Changelog

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
