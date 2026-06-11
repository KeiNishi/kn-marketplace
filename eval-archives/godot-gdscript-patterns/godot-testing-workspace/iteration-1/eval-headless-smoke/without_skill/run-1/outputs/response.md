# Headless Boot Smoke Test for Godot 4

## Goal

Verify that a Godot 4 project still boots and the main scene runs without errors, without needing the editor or a display.

---

## How it works

Godot 4 ships with a `--headless` flag that runs the engine without any display server or audio driver — ideal for CI machines and servers with no monitor.

The test strategy is:

1. Launch Godot with `--headless --path <project-dir>`
2. The main scene's `_ready()` calls `get_tree().quit(0)` immediately after printing a success message, so the process exits cleanly on its own.
3. Capture stdout + stderr and check:
   - The process exit code is `0`
   - The log contains no `ERROR:`, `SCRIPT ERROR:`, or `FATAL:` lines
4. A `timeout` wrapper ensures the process never hangs indefinitely.

---

## Scaffold created at `/tmp/eval-work/smoke-b/`

### `project.godot`

```ini
; Engine configuration file.
config_version=5

[application]

config/name="SmokeTestProject"
config/description="Minimal stand-in project for headless smoke test"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.2", "Forward Plus")
config/icon="res://icon.svg"

[rendering]

renderer/rendering_method="forward_plus"
```

### `main.gd`

```gdscript
extends Node

func _ready() -> void:
    print("Main scene loaded successfully.")
    # In a real smoke test you might check critical singletons, scenes, etc.
    # Quit immediately so the headless process exits cleanly.
    get_tree().quit(0)
```

### `main.tscn`

```
[gd_scene load_steps=2 format=3 uid="uid://smoke_main"]

[ext_resource type="Script" path="res://main.gd" id="1_main"]

[node name="Main" type="Node"]
script = ExtResource("1_main")
```

### `smoke_test.sh`

```bash
#!/usr/bin/env bash
# smoke_test.sh — Headless boot smoke test for a Godot 4 project.
# Usage: ./smoke_test.sh [path-to-godot-binary]
#
# Prerequisites:
#   - Godot 4 binary (headless build or standard build with --headless flag)
#   - No display required when using --headless
#
# Exit codes:
#   0  — Godot launched, main scene ran, and quit cleanly (exit 0)
#   1  — Godot exited with a non-zero code (crash / error)
#   2  — Timeout: Godot did not exit within the allowed window
#   3  — Godot binary not found

set -euo pipefail

GODOT_BIN="${1:-godot}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMEOUT_SECONDS=30
LOG_FILE="${PROJECT_DIR}/smoke_output.log"

# 1. Locate binary
if ! command -v "$GODOT_BIN" &>/dev/null; then
    echo "[SMOKE] ERROR: Godot binary not found: $GODOT_BIN" >&2
    exit 3
fi

echo "[SMOKE] Using Godot: $(command -v "$GODOT_BIN")"
echo "[SMOKE] Project:     $PROJECT_DIR"
echo "[SMOKE] Log:         $LOG_FILE"

# 2. Run headless
timeout "$TIMEOUT_SECONDS" "$GODOT_BIN" \
    --headless \
    --path "$PROJECT_DIR" \
    2>&1 | tee "$LOG_FILE"
EXIT_CODE="${PIPESTATUS[0]}"

# 3. Evaluate process exit code
if [ "$EXIT_CODE" -eq 124 ]; then
    echo "[SMOKE] FAIL — timed out after ${TIMEOUT_SECONDS}s" >&2
    exit 2
elif [ "$EXIT_CODE" -ne 0 ]; then
    echo "[SMOKE] FAIL — Godot exited with code $EXIT_CODE" >&2
    exit 1
fi

# 4. Grep log for known error indicators
if grep -qE '^\s*(ERROR:|SCRIPT ERROR:|FATAL:)' "$LOG_FILE"; then
    echo "[SMOKE] FAIL — errors detected in Godot output:" >&2
    grep -E '^\s*(ERROR:|SCRIPT ERROR:|FATAL:)' "$LOG_FILE" >&2
    exit 1
fi

echo "[SMOKE] PASS — main scene booted and exited cleanly."
exit 0
```

---

## Exact commands that would be executed

```bash
# Step 1 — navigate to the project directory
cd /tmp/eval-work/smoke-b

# Step 2 — run the smoke test (replace 'godot' with the actual binary path if needed)
./smoke_test.sh godot

# Equivalent expanded command:
timeout 30 godot \
    --headless \
    --path /tmp/eval-work/smoke-b \
    2>&1 | tee /tmp/eval-work/smoke-b/smoke_output.log
```

---

## What gates progress (pass/fail criteria)

| Gate | Condition | Meaning |
|------|-----------|---------|
| Binary found | `command -v godot` succeeds | Godot 4 is installed and on PATH |
| Process exit 0 | `${PIPESTATUS[0]} -eq 0` | Engine did not crash |
| No timeout | exit code is not `124` | Main scene did not hang (> 30 s) |
| Clean log | No `ERROR:` / `SCRIPT ERROR:` / `FATAL:` lines in stdout+stderr | No GDScript errors or engine errors during boot |

All four gates must pass for the smoke test to report `[SMOKE] PASS`.

---

## Why Godot could not be run on this machine

```
$ which godot
NOT_FOUND

$ which godot4
NOT_FOUND
```

Godot is not installed in this environment. The scaffold files have been created and are ready; the test can be executed as soon as a Godot 4 binary is available.

### Installing Godot 4 (headless, no display needed)

```bash
# Option A — Official headless export template (Linux server)
wget https://github.com/godotengine/godot/releases/download/4.2.2-stable/Godot_v4.2.2-stable_linux.x86_64.zip
unzip Godot_v4.2.2-stable_linux.x86_64.zip
mv Godot_v4.2.2-stable_linux.x86_64 /usr/local/bin/godot
chmod +x /usr/local/bin/godot

# Then run the smoke test
cd /tmp/eval-work/smoke-b
./smoke_test.sh
```

---

## Applying this to your real project

Copy `smoke_test.sh` into your project root. The only requirement is that `project.godot` and your main scene are already there. No changes to `main.gd` or `main.tscn` are needed unless you want the same instant-quit pattern; if your main scene has real game logic, the script's `get_tree().quit()` call in `_ready()` should be removed from production code and the smoke test should instead rely solely on the exit code and log grep.

For CI (GitHub Actions example):

```yaml
- name: Headless smoke test
  run: |
    ./smoke_test.sh /path/to/godot
  # Exits non-zero on failure, which fails the CI job automatically
```
