# Changelog

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
