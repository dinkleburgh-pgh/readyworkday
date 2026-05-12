---
name: changelog
description: "Use when: committing changes or updating CHANGELOG.md. Only bumps _APP_BUILD (not _APP_VERSION). Version bumps are reserved for special/major additions and must be explicitly requested by the user."
---

# Changelog & Release Bump

## Version vs Build policy
- **Build** (`_APP_BUILD`): bump on every commit/release. This is the default.
- **Version** (`_APP_VERSION`) and **Date** (`_APP_DATE`): only change when the user explicitly asks for a version bump. Do NOT update these automatically.

Ask the user for:
1. **Release notes** — ordered list of what changed (can paste from Unreleased section)

Then make all of these changes in one pass:

## 1 — `app_unloadv1.7.py`
Increment `_APP_BUILD` by 1 only. Leave `_APP_VERSION` and `_APP_DATE` unchanged.
```python
_APP_BUILD = <current + 1>
```

## 2 — `CHANGELOG.md`
Move any items under `## Unreleased` into a new section keyed by the current version + build, then prepend:

```markdown
## v<current_version> build <new_build> - <YYYY-MM-DD>

Ordered list of final changes included in this release:

1. Bumped build to **<new_build>**.
<additional notes here>
```

Leave `## Unreleased` as an empty section at the top for future work.

## If the user explicitly requests a version bump
Only then also update:
- `_APP_VERSION` in `app_unloadv1.7.py`
- `_APP_DATE` in `app_unloadv1.7.py`
- Image tag in `docker-compose.yml` and `docker-compose.portainer.yml`
- CHANGELOG section header uses `## v<new_version>` format

## Checklist (build-only, default)
- [ ] `_APP_BUILD` incremented in `app_unloadv1.7.py`
- [ ] `_APP_VERSION` and `_APP_DATE` left unchanged
- [ ] Unreleased items moved into new `CHANGELOG.md` section
- [ ] `## Unreleased` left empty at top of `CHANGELOG.md`
