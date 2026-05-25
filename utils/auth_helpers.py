"""utils/auth_helpers.py

Pure, stateless authentication utility functions extracted from app_unloadv1.7.py.
No Streamlit or app-state imports — safe to import at module load time.
"""
import hashlib


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def to_bool(value, default: bool = True) -> bool:
    """Coerce a loosely-typed value to bool with an explicit *default* fallback."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


# ---------------------------------------------------------------------------
# Auth-specific helpers
# ---------------------------------------------------------------------------

def is_bcrypt_hash(value: str) -> bool:
    """Return True when *value* looks like a bcrypt hash ($2a$, $2b$, or $2y$)."""
    raw = str(value or "").strip()
    return raw.startswith("$2a$") or raw.startswith("$2b$") or raw.startswith("$2y$")


def normalize_auth_cookie_key(raw_key: str) -> str:
    """Return a cookie signing key that is at least 32 bytes long.

    If the raw key is already ≥ 32 UTF-8 bytes it is returned as-is.
    Otherwise a SHA-256 digest of the key is used to satisfy RFC 7518.
    """
    key = str(raw_key or "").strip()
    if not key:
        key = "truckapp_cookie_key_change_me_please_override_in_env"
    try:
        if len(key.encode("utf-8")) >= 32:
            return key
    except Exception:
        if len(key) >= 32:
            return key
    try:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
    except Exception:
        return "truckapp_cookie_key_fallback_value_please_set_env_var"


# Role string literals (must stay in sync with AUTH_ROLE_* constants in the main app).
_ROLE_FLEET = "fleet"
_ROLE_ATL = "atl"
_ROLE_SUPERVISOR = "supervisor"
_ROLE_LEAD = "lead"
_ROLE_LOADER = "loader"
_ROLE_UNLOADER = "unloader"
_ROLE_GUEST = "guest"

_LEGACY_ROLE_MAP: dict[str, str] = {
    "admin":      _ROLE_FLEET,
    "fleet":      _ROLE_FLEET,
    "atl":        _ROLE_ATL,
    "supervisor": _ROLE_SUPERVISOR,
    "lead":       _ROLE_LEAD,
    "management": _ROLE_FLEET,
    "manager":    _ROLE_FLEET,
    "load":       _ROLE_LOADER,
    "loader":     _ROLE_LOADER,
    "operator":   _ROLE_UNLOADER,
    "unloader":   _ROLE_UNLOADER,
    "viewer":     _ROLE_GUEST,
    "guest":      _ROLE_GUEST,
}


def normalize_auth_role(role_value) -> str:
    """Normalise a role string to one of the canonical AUTH_ROLE_* values.

    Unknown / empty values fall back to *guest*.
    """
    role = str(role_value or "").strip().lower()
    return _LEGACY_ROLE_MAP.get(role, _ROLE_GUEST)


def normalize_auth_users(raw_users) -> dict[str, dict]:
    """Normalise a raw users dict (or a ``{"users": {...}}`` wrapper) into a
    canonical ``{username: {name, password, role, enabled}}`` mapping."""
    users_block = raw_users
    if isinstance(raw_users, dict) and isinstance(raw_users.get("users"), dict):
        users_block = raw_users.get("users")

    if not isinstance(users_block, dict):
        return {}

    normalized: dict[str, dict] = {}
    for username_raw, user_raw in users_block.items():
        username_original = str(username_raw or "").strip()
        username = username_original.lower()
        if not username or not isinstance(user_raw, dict):
            continue

        password_value = str(user_raw.get("password") or "").strip()
        if not password_value:
            continue

        display_name = str(user_raw.get("name") or username_original or username).strip() or username

        normalized[username] = {
            "name": display_name,
            "password": password_value,
            "role": normalize_auth_role(user_raw.get("role")),
            "enabled": to_bool(user_raw.get("enabled"), True),
        }

    return normalized


def normalize_auth_requests(raw_requests) -> dict[str, dict]:
    """Normalise a raw account-request dict (or a ``{"requests": {...}}`` wrapper)
    into a canonical mapping keyed by username."""
    requests_block = raw_requests
    if isinstance(raw_requests, dict) and isinstance(raw_requests.get("requests"), dict):
        requests_block = raw_requests.get("requests")

    if not isinstance(requests_block, dict):
        return {}

    normalized: dict[str, dict] = {}
    for username_raw, request_raw in requests_block.items():
        username = str(username_raw or "").strip()
        if not username or " " in username or not isinstance(request_raw, dict):
            continue

        status_value = str(request_raw.get("status") or "pending").strip().lower()
        if status_value not in {"pending", "approved", "rejected"}:
            status_value = "pending"

        password_value = str(request_raw.get("password") or "").strip()
        if status_value == "pending" and not password_value:
            continue

        normalized[username] = {
            "username": username,
            "name": username,
            "password": password_value,
            "requested_role": normalize_auth_role(
                request_raw.get("requested_role")
                if request_raw.get("requested_role") is not None
                else request_raw.get("role")
            ),
            "status": status_value,
            "requested_at": str(request_raw.get("requested_at") or ""),
            "reviewed_at": str(request_raw.get("reviewed_at") or ""),
            "reviewed_by": str(request_raw.get("reviewed_by") or ""),
            "notes": str(request_raw.get("notes") or "").strip(),
        }

    return normalized
