#!/usr/bin/env python3
"""Thin wrapper for the repository's existing invoice app."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run invoice organizer via repository app.py")
    parser.add_argument("input_folder", help="Folder containing invoices/receipts")
    parser.add_argument("output_folder", nargs="?", default="", help="Optional output folder")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    app_py = repo_root / "app.py"

    cmd = [sys.executable, str(app_py), args.input_folder]
    if args.output_folder:
        cmd.append(args.output_folder)

    env = os.environ.copy()
    return subprocess.call(cmd, cwd=str(repo_root), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
