import json
import os
import pathlib
import re
import subprocess
import sys


SECRET_PATTERNS = [
    (
        re.compile(r"(?i)\bOPENAI_API_KEY\s*=\s*[\"']?sk-[A-Za-z0-9_-]{20,}"),
        "an OpenAI-style API key assignment",
    ),
    (
        re.compile(r"(?i)\bREPLICATE_API_TOKEN\s*=\s*[\"']?r8_[A-Za-z0-9]{30,}"),
        "a Replicate API token assignment",
    ),
    (
        re.compile(r"(?i)\bMESHY_API_KEY\s*=\s*[\"']?msy_[A-Za-z0-9]{20,}"),
        "a Meshy API key assignment",
    ),
    (
        re.compile(r"(?i)\bTRIPO_API_KEY\s*=\s*[\"']?tsk_[A-Za-z0-9]{20,}"),
        "a Tripo API key assignment",
    ),
    (
        re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
        "a generic sk-prefixed API key",
    ),
    (
        re.compile(r"(?i)(api[_-]?key|secret|token)[\"' :=]+[A-Za-z0-9_\-]{24,}"),
        "a generic high-entropy secret assignment",
    ),
]


def log(message):
    print("block_secret_writes.py: " + message, file=sys.stderr)


def fail_open(message):
    # Hooks should not interrupt normal edits when their input or environment is unavailable.
    log(message)
    return 0


def env_flag_enabled(name):
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES"}


def running_under_cursor_agent():
    # cursor-agent exports these on every command hook. Claude Code does not.
    return bool(os.environ.get("CURSOR_PLUGIN_ROOT") or os.environ.get("CURSOR_VERSION"))


def load_event():
    raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail_open("malformed hook JSON; allowing write (" + str(exc) + ")")
        return None


def resolve_target(file_path, cwd):
    if not isinstance(file_path, str) or not file_path:
        return None
    path = pathlib.Path(file_path).expanduser()
    if not path.is_absolute():
        path = pathlib.Path(cwd) / path
    return path.resolve(strict=False)


def existing_git_cwd(path, fallback_cwd):
    current = path.parent if path.suffix or not path.exists() else path
    while not current.exists() and current != current.parent:
        current = current.parent
    if current.exists():
        return current
    return pathlib.Path(fallback_cwd).resolve(strict=False)


def repo_root_for(path, cwd):
    git_cwd = existing_git_cwd(path, cwd)
    try:
        result = subprocess.run(
            ["git", "-C", str(git_cwd), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        log("git is not installed; allowing write")
        return None
    if result.returncode != 0:
        return None
    root_text = result.stdout.strip()
    if not root_text:
        return None
    return pathlib.Path(root_text).resolve(strict=False)


def is_inside(path, root):
    try:
        common = os.path.commonpath([os.path.normcase(str(path)), os.path.normcase(str(root))])
    except ValueError:
        return False
    return common == os.path.normcase(str(root))


def extract_write_checks(event):
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        fail_open("missing or invalid tool_input; allowing write")
        return []

    checks = []
    if tool_name == "Write":
        checks.append((tool_input.get("file_path"), tool_input.get("content")))
    elif tool_name == "Edit":
        checks.append((tool_input.get("file_path"), tool_input.get("new_string")))
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            fail_open("missing or invalid MultiEdit edits; allowing write")
            return []
        for edit in edits:
            if isinstance(edit, dict):
                checks.append((edit.get("file_path") or tool_input.get("file_path"), edit.get("new_string")))
    else:
        return []
    return checks


def classify_secret(content):
    if not isinstance(content, str):
        return None
    for pattern, category in SECRET_PATTERNS:
        if pattern.search(content):
            return category
    return None


def emit_deny(category):
    reason = (
        "Blocked a repository write containing "
        + category
        + ". Store API keys in ~/.claude/3d-pipeline/.env instead."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")


def main():
    if env_flag_enabled("DISABLE_3D_PIPELINE_HOOKS"):
        return fail_open("DISABLE_3D_PIPELINE_HOOKS is set; allowing write")
    if running_under_cursor_agent():
        return fail_open("cursor-agent host detected; allowing write")
    event = load_event()
    if event is None:
        return 0
    if not isinstance(event, dict):
        return fail_open("hook JSON was not an object; allowing write")

    cwd = event.get("cwd") or os.getcwd()
    checks = extract_write_checks(event)
    for file_path, content in checks:
        target = resolve_target(file_path, cwd)
        if target is None:
            continue
        repo_root = repo_root_for(target, cwd)
        if repo_root is None or not is_inside(target, repo_root):
            continue
        category = classify_secret(content)
        if category:
            emit_deny(category)
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
