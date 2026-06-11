#!/usr/bin/env python3
"""Run GdUnit4 tests for a Godot 4 project headless and summarize the result.

Invocation used (GdUnit4 v4.x for Godot 4.2+; this is the same command the
bundled addons/gdUnit4/runtest.sh|.cmd wrappers execute, plus --headless and
--ignoreHeadlessMode, which GdUnit4 requires to run without a display):

    <godot> --headless --path <project> -d -s addons/gdUnit4/bin/GdUnitCmdTool.gd \
        -a <tests> -c --ignoreHeadlessMode

Pure Python stdlib. Works on Windows, macOS, and Linux.

Usage:
    python3 run_godot_tests.py --project <path> [--tests test] [--godot-bin <exe>]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NoReturn

# Godot executable names tried on PATH, in order. "godot4" covers Linux
# package managers (apt/dnf) that suffix the major version; shutil.which
# resolves ".exe" automatically on Windows via PATHEXT, but the explicit
# entries cost nothing and help when PATHEXT is misconfigured.
GODOT_CANDIDATES = ("godot", "godot4", "godot.exe", "godot4.exe")

# 600 s default: enough for CI-scale suites including engine startup and
# import; override with --timeout for very large projects.
DEFAULT_TIMEOUT = 600


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def find_godot(cli_value: str | None) -> str:
    """Locate the Godot executable: --godot-bin, then GODOT_BIN, then PATH."""
    if cli_value:
        resolved = shutil.which(cli_value) or (
            cli_value if Path(cli_value).is_file() else None
        )
        if not resolved:
            fail(f"--godot-bin '{cli_value}' is not an existing executable.")
        return resolved

    env_value = os.environ.get("GODOT_BIN")
    if env_value:
        resolved = shutil.which(env_value) or (
            env_value if Path(env_value).is_file() else None
        )
        if not resolved:
            fail(
                f"GODOT_BIN is set to '{env_value}' but no executable exists "
                "there. Fix or unset GODOT_BIN."
            )
        return resolved

    for name in GODOT_CANDIDATES:
        resolved = shutil.which(name)
        if resolved:
            return resolved

    fail(
        "Godot executable not found. Pass --godot-bin <path>, set the "
        "GODOT_BIN environment variable, or add the Godot 4 binary to PATH "
        "(it may be named 'godot4' on Linux; on Windows use the full path, "
        "e.g. C:/Godot/Godot_v4.3-stable_win64.exe)."
    )


def latest_results_xml(project: Path) -> Path | None:
    """Return the results.xml of the newest reports/report_<N> directory."""
    reports = project / "reports"
    if not reports.is_dir():
        return None
    candidates = [
        d / "results.xml"
        for d in reports.glob("report_*")
        if (d / "results.xml").is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def summarize_xml(xml_path: Path) -> str | None:
    """Aggregate JUnit XML testsuite counters into a one-line summary."""
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        print(f"WARNING: could not parse {xml_path}: {exc}", file=sys.stderr)
        return None
    suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
    tests = failures = errors = skipped = 0
    for suite in suites:
        tests += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
    return (
        f"{tests} tests: {tests - failures - errors - skipped} passed, "
        f"{failures} failed, {errors} errors, {skipped} skipped "
        f"(report: {xml_path})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run GdUnit4 tests headless and print a pass/fail summary."
    )
    parser.add_argument(
        "--project", default=".", help="Godot project directory (contains project.godot)"
    )
    parser.add_argument(
        "--tests",
        default="test",
        help="Test suite directory or file, relative to the project root "
        "or as a res:// path (default: test)",
    )
    parser.add_argument(
        "--godot-bin", default=None, help="Path to the Godot 4 executable"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Seconds before the run is killed (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not (project / "project.godot").is_file():
        fail(
            f"No project.godot found in {project.as_posix()}. Pass the Godot "
            "project root with --project."
        )

    cmd_tool = project / "addons" / "gdUnit4" / "bin" / "GdUnitCmdTool.gd"
    if not cmd_tool.is_file():
        fail(
            "GdUnit4 not found at addons/gdUnit4 — install it via the Godot "
            "AssetLib (search 'GdUnit4') or "
            "`git clone https://github.com/MikeSchulze/gdUnit4 addons/gdUnit4` "
            "inside the project, then enable the plugin in "
            "Project Settings > Plugins."
        )

    tests_arg = args.tests
    tests_rel = tests_arg[len("res://"):] if tests_arg.startswith("res://") else tests_arg
    if not (project / tests_rel).exists():
        fail(
            f"Test path '{tests_arg}' does not exist under "
            f"{project.as_posix()}. Create the directory or pass --tests."
        )

    godot = find_godot(args.godot_bin)
    cmd = [
        godot,
        "--headless",
        "--path",
        str(project),
        "-d",
        "-s",
        "addons/gdUnit4/bin/GdUnitCmdTool.gd",
        "-a",
        tests_arg,
        "-c",
        "--ignoreHeadlessMode",
    ]
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        fail(
            f"Test run exceeded {args.timeout}s and was killed. A test is "
            "likely awaiting a signal/frame that never arrives headless; "
            "re-run with --timeout <seconds> only if the suite is genuinely "
            "that large."
        )

    summary = None
    xml_path = latest_results_xml(project)
    if xml_path:
        summary = summarize_xml(xml_path)

    if result.returncode == 0:
        print(f"PASS: {summary or 'GdUnit4 exited 0 (no JUnit report found).'}")
        return 0

    print(
        f"FAIL (exit code {result.returncode}): "
        f"{summary or 'no JUnit report found.'}",
        file=sys.stderr,
    )
    print(
        "Fix the failing tests and re-run; only proceed when this script "
        "exits 0.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
