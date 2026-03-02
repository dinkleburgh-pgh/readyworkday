#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REAL_APP = "app_unloadv1.1.py"

SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
}

TEXT_EXTS = {".py", ".env", ".txt", ".md", ".toml", ".ini", ".cfg", ".yaml", ".yml", ".json"}

def iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p

def read_text(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def json_walk(obj: Any, fn) -> Any:
    if isinstance(obj, dict):
        return {k: json_walk(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_walk(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj

def looks_like_windows_abs(s: str) -> bool:
    # Drive letter + backslash, e.g. C:\...
    return len(s) >= 3 and s[1:3] == ":\\" and s[0].isalpha()

def replace_bad_strings(s: str, repo_root: Path) -> str:
    # If code/config points at the old backup filename, point at the real entrypoint (repo-relative).
    if "app_unloadv1.1.py" in s:
        s = s.replace("app_unloadv1.1.py", REAL_APP)

    # If it contains a Windows absolute path under TruckApp, replace with repo root.
    # We do not attempt to rewrite arbitrary Windows paths; only those that include TruckApp.
    if "TruckApp" in s and looks_like_windows_abs(s):
        # Example: C:\Users\...\TruckApp\something -> <repo_root>\something
        idx = s.lower().find("truckapp")
        if idx != -1:
            tail = s[idx + len("TruckApp") :].lstrip("\\/")
            s = str(repo_root / tail)

    return s

def main() -> int:
    ap = argparse.ArgumentParser(description="Fix TruckApp Windows-path issues (portable)")
    ap.add_argument("--root", default=".", help="Repo/project root directory")
    ap.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    ap.add_argument("--delete-state", action="store_true", default=True, help="Delete cached state files (default on)")
    args = ap.parse_args()

    repo_root = Path(args.root).resolve()
    if not repo_root.exists():
        print(f"ERROR: root not found: {repo_root}", file=sys.stderr)
        return 2

    apply = args.apply

    # 1) Delete cached state files that can persist old absolute paths
    state_names = {".truck_state.json", "truck_state.json"}
    found_state = []
    deleted_state = []
    if args.delete_state:
        for p in iter_files(repo_root):
            if p.name in state_names:
                found_state.append(p)
                if apply:
                    try:
                        p.unlink()
                        deleted_state.append(p)
                    except Exception as e:
                        print(f"WARN: failed to delete {p}: {e}", file=sys.stderr)

    # 2) Ensure .data directory exists (portable state/logs)
    data_dir = repo_root / ".data"
    if apply:
        data_dir.mkdir(parents=True, exist_ok=True)

    # 3) Scan & patch config/text/json for the backup filename / Windows absolute TruckApp paths
    hits = []
    patched = []

    for p in iter_files(repo_root):
        if p.suffix.lower() not in TEXT_EXTS and p.name != ".env":
            continue

        txt = read_text(p)
        if txt is None:
            continue

        # Heuristic: only touch files that mention TruckApp or the old backup name
        if ("TruckApp" not in txt) and ("app_unloadv1.1.py" not in txt):
            continue

        hits.append(p)
        new_txt = txt

        if p.suffix.lower() == ".json":
            try:
                obj = json.loads(txt)
                obj2 = json_walk(obj, lambda s: replace_bad_strings(s, repo_root))
                new_txt = json.dumps(obj2, indent=2, ensure_ascii=False) + "\n"
            except Exception:
                new_txt = "\n".join(replace_bad_strings(line, repo_root) for line in txt.splitlines()) + ("\n" if txt.endswith("\n") else "")
        else:
            new_txt = "\n".join(replace_bad_strings(line, repo_root) for line in txt.splitlines()) + ("\n" if txt.endswith("\n") else "")

        if new_txt != txt:
            patched.append(p)
            if apply:
                try:
                    write_text(p, new_txt)
                except Exception as e:
                    print(f"WARN: failed patching {p}: {e}", file=sys.stderr)

    # Report
    print("\n=== TruckApp path-fix report ===")
    print(f"Repo root: {repo_root}")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print(f"Expected main file: {REAL_APP}")
    print(f".data dir: {data_dir}")

    if found_state:
        print("\nState files found:")
        for p in found_state:
            mark = " (deleted)" if p in deleted_state else ""
            print(f"  - {p}{mark}")
    else:
        print("\nNo state files found (.truck_state.json / truck_state.json).")

    if hits:
        print("\nFiles scanned (contained TruckApp or old backup name):")
        for p in hits:
            print(f"  - {p}")
    else:
        print("\nNo files contained TruckApp or app_unloadv1.1.py (nothing to scan).")

    if patched:
        print("\nFiles changed:")
        for p in patched:
            print(f"  - {p}")
    else:
        print("\nNo changes needed (or paths are generated at runtime in code).")

    print("\nNext:")
    print("1) Make sure your app entrypoint exists:")
    print(f"   dir {REAL_APP}")
    print("2) Start your app using the real entrypoint (not a backup path).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
