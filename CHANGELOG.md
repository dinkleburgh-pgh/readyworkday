# Changelog

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
