---
name: changelog
description: "Use when: bumping the app version, cutting a release, or updating CHANGELOG.md. Prompts for version and date, updates _APP_VERSION/_APP_DATE in app_unloadv1.7.py, image tags in compose files, and prepends the release entry to CHANGELOG.md."
---

# Changelog & Release Bump

Ask the user for:
1. **New version** (e.g. `1.8.0`)
2. **Release date** in `YYYYMMDD` format (default: today)
3. **Release notes** — ordered list of what changed (can paste from Unreleased section)

Then make all of these changes in one pass:

## 1 — `app_unloadv1.7.py` (lines ~35-36)
```python
_APP_VERSION = "<new_version>"
_APP_DATE = "<YYYYMMDD>"
```

## 2 — `docker-compose.yml` and `docker-compose.portainer.yml`
```yaml
image: ghcr.io/dinkleburgh-pgh/readyworkday:v<new_version>
```

## 3 — `CHANGELOG.md`
Move any items under `## Unreleased` into the new versioned section, then prepend:

```markdown
## v<new_version> - <YYYY-MM-DD>

Ordered list of final changes included in this release:

1. Updated app metadata release to **v<new_version>** with release date **<YYYYMMDD>**.
2. Updated deployment image references in compose files to **v<new_version>**.
<additional notes here>
```

Leave `## Unreleased` as an empty section at the top for future work.

## Checklist
- [ ] `_APP_VERSION` updated in `app_unloadv1.7.py`
- [ ] `_APP_DATE` updated in `app_unloadv1.7.py`
- [ ] Image tag updated in `docker-compose.yml`
- [ ] Image tag updated in `docker-compose.portainer.yml`
- [ ] Unreleased items moved into new `CHANGELOG.md` section
- [ ] `## Unreleased` left empty at top of `CHANGELOG.md`
