"""
FastAPI REST server for TruckApp state management.
Runs on port 8787, serves JSON state to Android clients and external integrations.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn


# ============================================================================
# CONFIG & STATE LOADING
# ============================================================================

app = FastAPI()

# Read API keys from environment
API_KEY_READ = os.getenv("TRUCKAPP_API_KEY_READ", "change-me-read-key")
API_KEY_WRITE = os.getenv("TRUCKAPP_API_KEY_WRITE", "change-me-write-key")

# Data directory (where .truck_state.json and truck_fleet.json live)
DATA_DIR = Path(os.getenv("TRUCKAPP_DATA_DIR", "."))
STATE_FILE = DATA_DIR / ".truck_state.json"
FLEET_FILE = DATA_DIR / "truck_fleet.json"


def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON file, return empty dict if missing."""
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}


def save_json(filepath: Path, data: Dict[str, Any]) -> None:
    """Save JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def verify_api_key(auth_header: Optional[str], required_level: str) -> bool:
    """
    Verify API key from Authorization header.
    required_level: "read" or "write"
    - Read accepts read OR write key
    - Write accepts only write key
    """
    if not auth_header:
        return False

    # Extract Bearer token
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False

    token = parts[1]

    if required_level == "read":
        # Read accepts either read or write key
        return token in (API_KEY_READ, API_KEY_WRITE)
    elif required_level == "write":
        # Write accepts only write key
        return token == API_KEY_WRITE

    return False


# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================


@app.get("/health")
async def health():
    """Health check — no auth required."""
    return {"status": "ok"}


# ============================================================================
# READ ENDPOINTS (GET)
# ============================================================================


@app.get("/api/v1/state")
async def get_state(authorization: Optional[str] = Header(None)):
    """Get full .truck_state.json."""
    if not verify_api_key(authorization, "read"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    return load_json(STATE_FILE)


@app.get("/api/v1/fleet")
async def get_fleet(authorization: Optional[str] = Header(None)):
    """Get truck_fleet.json."""
    if not verify_api_key(authorization, "read"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    return load_json(FLEET_FILE)


@app.get("/api/v1/assignments")
async def get_assignments(authorization: Optional[str] = Header(None)):
    """Get route_swaps and oos_spares from state."""
    if not verify_api_key(authorization, "read"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    state = load_json(STATE_FILE)
    return {
        "route_swaps": state.get("route_swaps", {}),
        "oos_spares": state.get("oos_spares", {})
    }


# ============================================================================
# WRITE ENDPOINTS (PUT)
# ============================================================================


@app.put("/api/v1/state")
async def put_state(data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    """Replace full .truck_state.json."""
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    save_json(STATE_FILE, data)
    return {"message": "State updated"}


@app.put("/api/v1/fleet")
async def put_fleet(data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    """Replace truck_fleet.json."""
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    save_json(FLEET_FILE, data)
    return {"message": "Fleet updated"}


# ============================================================================
# TARGETED ASSIGNMENT ENDPOINTS
# ============================================================================


@app.put("/api/v1/assignments/route-swaps/{route}")
async def put_route_swap(route: str, data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    """
    Set route swap: {route: {"swap_from": "...", "swap_to": "..."}}
    Enforces one-to-one assignment (removes conflicting swaps).
    """
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    state = load_json(STATE_FILE)
    if "route_swaps" not in state:
        state["route_swaps"] = {}
    
    # Remove conflicts
    swap_from = data.get("swap_from")
    swap_to = data.get("swap_to")
    
    if swap_from:
        state["route_swaps"] = {k: v for k, v in state["route_swaps"].items() if v.get("swap_from") != swap_from}
    if swap_to:
        state["route_swaps"] = {k: v for k, v in state["route_swaps"].items() if v.get("swap_to") != swap_to}
    
    # Set new swap
    state["route_swaps"][route] = data
    
    save_json(STATE_FILE, state)
    return {"message": f"Route swap {route} updated"}


@app.delete("/api/v1/assignments/route-swaps/{route}")
async def delete_route_swap(route: str, authorization: Optional[str] = Header(None)):
    """Remove route swap."""
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    state = load_json(STATE_FILE)
    if "route_swaps" in state:
        state["route_swaps"].pop(route, None)
    
    save_json(STATE_FILE, state)
    return {"message": f"Route swap {route} deleted"}


@app.put("/api/v1/assignments/oos-spares/{route}")
async def put_oos_spare(route: str, data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    """
    Set OOS spare: {route: {"truck": "..."}}
    Enforces one-to-one assignment (removes conflicting spares).
    """
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    state = load_json(STATE_FILE)
    if "oos_spares" not in state:
        state["oos_spares"] = {}
    
    # Remove conflicts
    truck = data.get("truck")
    if truck:
        state["oos_spares"] = {k: v for k, v in state["oos_spares"].items() if v.get("truck") != truck}
    
    # Set new spare
    state["oos_spares"][route] = data
    
    save_json(STATE_FILE, state)
    return {"message": f"OOS spare {route} updated"}


@app.delete("/api/v1/assignments/oos-spares/{route}")
async def delete_oos_spare(route: str, authorization: Optional[str] = Header(None)):
    """Remove OOS spare."""
    if not verify_api_key(authorization, "write"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    state = load_json(STATE_FILE)
    if "oos_spares" in state:
        state["oos_spares"].pop(route, None)
    
    save_json(STATE_FILE, state)
    return {"message": f"OOS spare {route} deleted"}


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("RUST_API_PORT", 8787))
    print(f"Starting TruckApp REST API on port {port}")
    print(f"Data dir: {DATA_DIR.resolve()}")
    print(f"Read key: {API_KEY_READ}")
    print(f"Write key: {API_KEY_WRITE}")
    uvicorn.run(app, host="0.0.0.0", port=port)
