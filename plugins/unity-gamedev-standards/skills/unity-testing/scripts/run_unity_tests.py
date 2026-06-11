#!/usr/bin/env python3
"""Run Unity Test Framework tests in batchmode and summarize the results.

Locates the Unity editor binary (--unity-bin, then UNITY_PATH env var, then
default Unity Hub install directories for the current OS), runs the requested
test platform, parses the NUnit results XML, and prints a concise pass/fail
summary. Exits 0 only when every test passed.

Standard library only; works on Windows, macOS, and Linux.

Usage:
  python3 run_unity_tests.py --project-path <unity-project> [--test-platform EditMode|PlayMode]
                             [--unity-bin <path-to-unity>] [--results <results.xml>]
                             [--timeout <seconds>]
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Unity test runs include domain reloads and (for PlayMode) player startup;
# 30 minutes covers large suites on slow CI machines while still failing a
# hung editor in finite time. Override with --timeout.
DEFAULT_TIMEOUT_SECONDS = 1800


def fail(message):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def read_project_version(project_path):
    """Return m_EditorVersion from ProjectSettings/ProjectVersion.txt, or None."""
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.is_file():
        return None
    match = re.search(r"m_EditorVersion:\s*(\S+)",
                      version_file.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def hub_editor_roots():
    """Default Unity Hub editor install roots for the current OS."""
    if sys.platform.startswith("win"):
        roots = []
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(env)
            if base:
                roots.append(Path(base) / "Unity" / "Hub" / "Editor")
        if not roots:
            roots.append(Path("C:/Program Files/Unity/Hub/Editor"))
        return roots
    if sys.platform == "darwin":
        return [Path("/Applications/Unity/Hub/Editor")]
    return [Path.home() / "Unity" / "Hub" / "Editor"]


def binary_in_version_dir(version_dir):
    """Return the Unity binary path inside one Hub <version> directory, or None."""
    if sys.platform.startswith("win"):
        candidate = version_dir / "Editor" / "Unity.exe"
    elif sys.platform == "darwin":
        candidate = version_dir / "Unity.app" / "Contents" / "MacOS" / "Unity"
    else:
        candidate = version_dir / "Editor" / "Unity"
    return candidate if candidate.is_file() else None


def find_unity(explicit_bin, project_path):
    """Resolve the Unity binary: --unity-bin > UNITY_PATH > Hub scan."""
    if explicit_bin:
        path = Path(explicit_bin)
        if not path.is_file():
            fail("--unity-bin does not exist or is not a file: " + str(path))
        return path

    env_path = os.environ.get("UNITY_PATH")
    if env_path:
        path = Path(env_path)
        if not path.is_file():
            fail("UNITY_PATH is set but does not point to a file: " + env_path
                 + ". Fix the variable or pass --unity-bin.")
        return path

    project_version = read_project_version(project_path)
    fallbacks = []
    for root in hub_editor_roots():
        if not root.is_dir():
            continue
        for version_dir in sorted(root.iterdir()):
            binary = binary_in_version_dir(version_dir)
            if binary is None:
                continue
            if project_version and version_dir.name == project_version:
                return binary  # exact match for the project's editor version
            fallbacks.append(binary)

    if fallbacks:
        chosen = fallbacks[-1]  # highest version by sorted directory name
        if project_version:
            print("WARNING: Unity {0} (from ProjectVersion.txt) not installed; "
                  "using {1}".format(project_version, chosen))
        return chosen

    fail("Unity editor not found. Pass --unity-bin <path-to-Unity-executable> "
         "or set the UNITY_PATH environment variable. Default Hub locations "
         "checked: " + ", ".join(str(r) for r in hub_editor_roots()))


def validate_project(project_path):
    if not project_path.is_dir():
        fail("Project path does not exist: " + str(project_path))
    if not (project_path / "Packages" / "manifest.json").is_file():
        fail("Not a Unity project (no Packages/manifest.json): "
             + str(project_path)
             + ". Pass the project root, the folder that contains Assets/ "
             "and Packages/.")


def run_tests(unity_bin, project_path, platform, results_path, timeout):
    command = [
        str(unity_bin),
        "-batchmode",
        "-projectPath", str(project_path),
        "-runTests",
        "-testPlatform", platform,
        "-testResults", str(results_path),
        "-logFile", "-",
    ]
    print("Running: " + " ".join(command))
    try:
        completed = subprocess.run(command, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail("Unity did not finish within {0}s. The editor may be hung or the "
             "suite may need a longer --timeout. Check whether another Unity "
             "instance has the project open.".format(timeout))
    except FileNotFoundError:
        fail("Could not execute Unity binary: " + str(unity_bin))
    return completed.returncode


def summarize_results(results_path):
    """Parse NUnit XML, print a failure summary. Return number of failures."""
    try:
        root = ET.parse(str(results_path)).getroot()
    except ET.ParseError as error:
        fail("Results file is not valid XML ({0}): {1}".format(error, results_path))

    total = root.get("total", "?")
    passed = root.get("passed", "?")
    failed = int(root.get("failed", 0) or 0)
    skipped = root.get("skipped", "0")
    print("\n=== Unity test results ===")
    print("total={0} passed={1} failed={2} skipped={3}".format(
        total, passed, failed, skipped))

    failures = [tc for tc in root.iter("test-case")
                if tc.get("result") == "Failed"]
    for test_case in failures:
        name = test_case.get("fullname") or test_case.get("name", "<unknown>")
        message = test_case.findtext("failure/message", default="").strip()
        print("\nFAILED: " + name)
        if message:
            print("  " + "\n  ".join(message.splitlines()))
    return max(failed, len(failures))


def main():
    parser = argparse.ArgumentParser(
        description="Run Unity Test Framework tests in batchmode.")
    parser.add_argument("--project-path", required=True,
                        help="Unity project root (contains Assets/ and Packages/)")
    parser.add_argument("--test-platform", default="EditMode",
                        choices=["EditMode", "PlayMode"],
                        help="Test platform to run (default: EditMode)")
    parser.add_argument("--unity-bin",
                        help="Path to the Unity editor executable")
    parser.add_argument("--results",
                        help="Where to write the NUnit results XML "
                             "(default: a temp file)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="Seconds before the run is aborted "
                             "(default: {0})".format(DEFAULT_TIMEOUT_SECONDS))
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    validate_project(project_path)
    unity_bin = find_unity(args.unity_bin, project_path)

    if args.results:
        results_path = Path(args.results).resolve()
        results_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        results_path = Path(tempfile.gettempdir()) / (
            "unity_test_results_" + args.test_platform + ".xml")
    if results_path.exists():
        results_path.unlink()  # ensure a stale file is never parsed

    exit_code = run_tests(unity_bin, project_path, args.test_platform,
                          results_path, args.timeout)

    if not results_path.is_file():
        fail("Unity exited with code {0} and wrote no results file. This "
             "usually means compile errors, a project lock (close any open "
             "Unity editor on this project), or a license problem. Scroll up "
             "through the streamed editor log for the first error.".format(exit_code))

    failed = summarize_results(results_path)
    if failed:
        print("\n{0} test(s) failed. Fix the failures above and re-run; only "
              "proceed when the run is green.".format(failed), file=sys.stderr)
        sys.exit(1)
    print("\nAll tests passed. Results XML: " + str(results_path))


if __name__ == "__main__":
    main()
