import json
import os
import pathlib
import subprocess
import sys


ENV_NAMES = {".env", ".env.local"}


def log(message):
    print("warn_repo_env.py: " + message, file=sys.stderr)


def load_event_cwd():
    raw = sys.stdin.read()
    if not raw.strip():
        return os.getcwd()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        log("malformed hook JSON; using process cwd (" + str(exc) + ")")
        return os.getcwd()
    if isinstance(event, dict) and isinstance(event.get("cwd"), str) and event.get("cwd"):
        return event.get("cwd")
    return os.getcwd()


def repo_root(cwd):
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    root_text = result.stdout.strip()
    if not root_text:
        return None
    return pathlib.Path(root_text).resolve(strict=False)


def is_env_name(name):
    return name in ENV_NAMES or name.startswith(".env.")


def is_excluded(path):
    parts = [part.lower() for part in path.parts]
    return ".git" in parts or "node_modules" in parts or "upstream" in parts


def find_env_files(root):
    files = []
    for path in root.rglob(".env*"):
        if not path.is_file():
            continue
        if not is_env_name(path.name):
            continue
        rel = path.relative_to(root)
        if is_excluded(rel):
            continue
        files.append(rel)
    return sorted(files, key=lambda item: item.as_posix().lower())


def gitignore_status(root, rel_path):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", rel_path.as_posix()],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "gitignore check unavailable"
    if result.returncode == 0:
        return "gitignored"
    if result.returncode == 1:
        return "NOT gitignored - high risk"
    return "gitignore check failed - review manually"


def emit_warning(items):
    lines = [
        "3d-asset-pipeline security warning: .env-like files exist inside this repository.",
        "API keys for this plugin should be stored only in ~/.claude/3d-pipeline/.env.",
        "Detected files:",
    ]
    for rel_path, status in items:
        lines.append("- " + rel_path.as_posix() + " (" + status + ")")
    message = "\n".join(lines)
    output = {
        "systemMessage": message,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        },
    }
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")


def env_flag_enabled(name):
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES"}


def main():
    if env_flag_enabled("DISABLE_3D_PIPELINE_HOOKS"):
        return 0
    cwd = load_event_cwd()
    root = repo_root(cwd)
    if root is None:
        return 0
    env_files = find_env_files(root)
    if not env_files:
        return 0
    items = [(rel_path, gitignore_status(root, rel_path)) for rel_path in env_files]
    emit_warning(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
