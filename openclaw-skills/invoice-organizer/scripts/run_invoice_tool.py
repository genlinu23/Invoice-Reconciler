#!/usr/bin/env python3
"""Thin wrapper for the repository's existing invoice app."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def resolve_repo_root(script_path: Path) -> Path:
    env_root = os.environ.get("INVOICE_TOOL_REPO")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if (p / "app.py").exists():
            return p

    candidates = [
        script_path.parents[2],
        Path("/workspace/Invoice-Reconciler"),
        Path("/workspace/skills/发票整理工具"),
    ]
    for p in candidates:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if (rp / "app.py").exists():
            return rp

    raise FileNotFoundError("Could not locate repository root containing app.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run invoice organizer via repository app.py")
    parser.add_argument("input_folder", help="Folder containing invoices")
    parser.add_argument("output_folder", nargs="?", default="", help="Optional output folder")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = resolve_repo_root(script_path)
    app_py = repo_root / "app.py"

    cmd = [sys.executable, str(app_py), args.input_folder]
    if args.output_folder:
        cmd.append(args.output_folder)

    env = os.environ.copy()
    return subprocess.call(cmd, cwd=str(repo_root), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
