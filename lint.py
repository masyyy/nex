#!/usr/bin/env python3
"""
Lint script for the Nexus project.
Runs ruff auto fix and mypy strict on specified files or folders.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def run_ruff(paths: List[str], check_only: bool = False) -> int:
    """
    Run ruff on the specified paths.

    Args:
        paths: List of file or directory paths to lint
        check_only: If True, only check for issues without fixing them

    Returns:
        Exit code from ruff
    """
    cmd = ["ruff", "check"]
    if not check_only:
        cmd.append("--fix")
    cmd.extend(paths)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_mypy(paths: List[str]) -> int:
    """
    Run mypy on the specified paths with strict settings.

    Args:
        paths: List of file or directory paths to type check

    Returns:
        Exit code from mypy
    """
    cmd = [
        "mypy",
        "--strict",
        "--ignore-missing-imports",
        "--disallow-untyped-decorators",
        "--disallow-incomplete-defs",
    ]
    cmd.extend(paths)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main() -> int:
    """
    Main entry point for the lint script.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(description="Run linting tools on the codebase")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Paths to lint (files or directories)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, don't auto-fix issues"
    )
    parser.add_argument(
        "--ruff-only",
        action="store_true",
        help="Run only ruff, not mypy"
    )
    parser.add_argument(
        "--mypy-only",
        action="store_true",
        help="Run only mypy, not ruff"
    )

    args = parser.parse_args()

    # Validate paths
    valid_paths = []
    for path_str in args.paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Error: Path does not exist: {path_str}", file=sys.stderr)
            return 1
        valid_paths.append(path_str)

    if not valid_paths:
        print("No valid paths provided", file=sys.stderr)
        return 1

    exit_code = 0

    # Run ruff if requested
    if not args.mypy_only:
        ruff_result = run_ruff(valid_paths, check_only=args.check)
        if ruff_result != 0:
            exit_code = ruff_result
            print("Ruff found issues", file=sys.stderr)

    # Run mypy if requested
    if not args.ruff_only:
        mypy_result = run_mypy(valid_paths)
        if mypy_result != 0:
            exit_code = mypy_result
            print("Mypy found issues", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())