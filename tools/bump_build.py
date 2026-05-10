#!/usr/bin/env python3
"""Increment TruckApp build number in app metadata and .env before each commit."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_FILE = ROOT / "app_unloadv1.7.py"
ENV_FILE = ROOT / ".env"

BUILD_PATTERN = re.compile(r"(?m)^_APP_BUILD\s*=\s*(\d+)\s*$")
ENV_BUILD_PATTERN = re.compile(r"(?m)^APP_BUILD\s*=\s*(\d+)\s*$")


def bump_app_build(text: str) -> tuple[str, int]:
    match = BUILD_PATTERN.search(text)
    if not match:
        raise RuntimeError("Could not find _APP_BUILD in app_unloadv1.7.py")
    current = int(match.group(1))
    nxt = current + 1
    updated = BUILD_PATTERN.sub(f"_APP_BUILD = {nxt}", text, count=1)
    return updated, nxt


def bump_env_build(text: str, nxt: int) -> str:
    if ENV_BUILD_PATTERN.search(text):
        return ENV_BUILD_PATTERN.sub(f"APP_BUILD={nxt}", text, count=1)

    lines = text.splitlines()
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("APP_VERSION="):
            insert_at = idx + 1
            break
    lines.insert(insert_at, f"APP_BUILD={nxt}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> int:
    app_text = APP_FILE.read_text(encoding="utf-8")
    updated_app, nxt = bump_app_build(app_text)
    if updated_app != app_text:
        APP_FILE.write_text(updated_app, encoding="utf-8")

    if ENV_FILE.exists():
        env_text = ENV_FILE.read_text(encoding="utf-8")
        updated_env = bump_env_build(env_text, nxt)
        if updated_env != env_text:
            ENV_FILE.write_text(updated_env, encoding="utf-8")

    print(f"[build-bump] _APP_BUILD -> {nxt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
