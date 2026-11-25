#!/usr/bin/env python3
"""Install bundled skills into the active Hermes home without overwriting by default."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hermes-skills" / "industrial"


def hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".hermes"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, help="Target Hermes home; defaults to HERMES_HOME or ~/.hermes")
    parser.add_argument("--force", action="store_true", help="Replace existing package directories")
    args = parser.parse_args()
    target_root = (args.home.expanduser().resolve() if args.home else hermes_home()) / "skills" / "industrial"
    names = ["industrial-article-generation", "industrial-cms-publishing", "industrial-content-standard"]
    if not SOURCE.is_dir():
        print(f"missing bundled skills: {SOURCE}", file=sys.stderr)
        return 2
    target_root.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = SOURCE / name
        target = target_root / name
        if target.exists():
            if not args.force:
                print(f"refusing to overwrite: {target}; re-run with --force", file=sys.stderr)
                return 3
            shutil.rmtree(target)
        shutil.copytree(source, target)
        print(f"installed {name} -> {target}")
    print("Restart Hermes or begin a new session so it refreshes its skill catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
