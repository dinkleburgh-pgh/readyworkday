---
name: json-migrate
description: "Use when: adding, renaming, or removing keys in any JSON state file (.truck_state.json, truck_fleet.json, auth_users.json, etc.) to ensure backward compatibility with existing saved data."
---

# JSON Key Migration

When a JSON persistence key is added, renamed, or removed, existing files on disk won't have the new shape. Use one of the patterns below inside the relevant `load_*` function.

## Adding a new key (most common)

Use `.get()` with a safe default so old files without the key still load:

```python
def load_state() -> dict:
    # ... existing load logic ...
    data = _deserialize_state_payload(raw)

    # Migration: added in v1.X.0
    data.setdefault("new_key", <default_value>)

    return data
```

## Renaming a key

```python
    # Migration: renamed old_key → new_key in v1.X.0
    if "old_key" in data and "new_key" not in data:
        data["new_key"] = data.pop("old_key")
```

## Removing a key (clean up stale data)

```python
    # Migration: removed stale_key in v1.X.0
    data.pop("stale_key", None)
```

## Rules
- Always put migrations **after** the initial load/deserialize, before returning.
- Tag each migration with a `# Migration: ...` comment and version.
- Never change the on-disk format without a corresponding migration in `load_*`.
- If the key appears in `defaults` (the session_state defaults dict), add it there too so fresh sessions get the right default.
- Test by: deleting the key from a local copy of the JSON file and confirming the app loads without error.
