"""SessionStart guard for the audio-asset-pipeline.

Warns when secrets (HF_TOKEN and friends) or a multi-gigabyte Hugging Face
model cache live inside the current git repository. Everything this plugin
needs privately belongs under ~/.claude/audio-pipeline/.

Set DISABLE_AUDIO_PIPELINE_HOOKS=1 to silence it.
"""

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


def hf_home_inside(root):
    """True when HF_HOME points into the repo, i.e. weights would be committed."""
    raw = os.environ.get("HF_HOME", "").strip()
    if not raw:
        return None
    hf_home = pathlib.Path(os.path.expanduser(raw)).resolve(strict=False)
    try:
        hf_home.relative_to(root)
    except ValueError:
        return None
    return hf_home


def emit_warning(lines):
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
    if env_flag_enabled("DISABLE_AUDIO_PIPELINE_HOOKS"):
        return 0
    cwd = load_event_cwd()
    root = repo_root(cwd)
    if root is None:
        return 0

    lines = []
    env_files = find_env_files(root)
    if env_files:
        lines.append(
            "audio-asset-pipeline security warning: .env-like files exist inside this repository."
        )
        lines.append(
            "Tokens for this plugin (for example HF_TOKEN for gated model weights) belong "
            "only in ~/.claude/audio-pipeline/.env."
        )
        lines.append("Detected files:")
        for rel_path in env_files:
            lines.append("- " + rel_path.as_posix() + " (" + gitignore_status(root, rel_path) + ")")

    hf_home = hf_home_inside(root)
    if hf_home is not None:
        if lines:
            lines.append("")
        lines.append(
            "audio-asset-pipeline warning: HF_HOME points inside this repository ("
            + hf_home.as_posix()
            + ")."
        )
        lines.append(
            "Model weights are tens of gigabytes; move HF_HOME outside the repository "
            "before generating audio."
        )

    if lines:
        emit_warning(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
