# Headless Smoke Test — Verifying the Game Boots Without a Display

## What This Does

A headless smoke test runs your Godot project for a fixed number of process frames without opening a window or requiring a GPU. It proves that the main scene loads, all `_ready()` callbacks fire without script errors, and the engine exits cleanly. It is the correct pre-push sanity check when no editor or display is available.

---

## Minimal Project Scaffold

The stand-in project was created at `/tmp/eval-work/smoke-w/` with this layout:

```
smoke-w/
├── project.godot          # declares main scene = res://scenes/main.tscn
└── scenes/
    ├── main.tscn          # root Node attached to main.gd
    └── main.gd            # prints "Game booted OK" in _ready()
```

**`project.godot`**
```ini
config_version=5

[application]
config/name="SmokeTestGame"
config/features=PackedStringArray("4.3", "GL Compatibility")
run/main_scene="res://scenes/main.tscn"
```

**`scenes/main.gd`**
```gdscript
extends Node

func _ready() -> void:
    print("Game booted OK")
```

---

## The Smoke-Test Command

Per the `godot-testing` skill's [Headless Smoke Test] section, the correct command is:

```bash
godot --headless --path /tmp/eval-work/smoke-w --quit-after 120
```

### What each flag does

| Flag | Purpose |
|---|---|
| `--headless` | No window, no GPU, no display server required — safe on CI or any machine with no display. |
| `--path /tmp/eval-work/smoke-w` | Tells Godot where `project.godot` lives. |
| `--quit-after 120` | Exit after 120 process frames (~2 seconds at 60 FPS). Long enough for `_ready` to run on the full main scene tree; short enough not to hang. |

To smoke-test a specific scene instead of the main scene, append its path:

```bash
godot --headless --path /tmp/eval-work/smoke-w --quit-after 120 res://scenes/main.tscn
```

---

## How to Interpret the Result

After the command runs, check **both** the exit code **and** the console output. Godot can exit 0 even when a script error occurred, so you must scan output explicitly.

### Pass criteria (both must be true)

1. **Exit code is 0**
   ```bash
   echo $?   # must print 0
   ```

2. **No error lines in the output** — scan for:
   ```
   SCRIPT ERROR
   ERROR:
   Parse Error
   ```

   A quick one-liner to capture output and check both at once:
   ```bash
   output=$(godot --headless --path /tmp/eval-work/smoke-w --quit-after 120 2>&1)
   exit_code=$?
   echo "$output"
   if [ $exit_code -ne 0 ] || echo "$output" | grep -qE "SCRIPT ERROR|ERROR:|Parse Error"; then
     echo "SMOKE TEST FAILED"
     exit 1
   else
     echo "SMOKE TEST PASSED"
   fi
   ```

### Expected passing output

```
Godot Engine v4.3.stable - https://godotengine.org
...
Game booted OK
```

### Failure examples

```
SCRIPT ERROR: Parse Error: Expected end of statement after expression, ...
```
→ GDScript syntax error; fix the script and re-run.

```
ERROR: res://scenes/main.tscn: (Resource file not found)
```
→ Scene path in `project.godot` does not match an actual file; fix the path.

Non-zero exit with no output → Godot binary path wrong or project.godot malformed.

---

## Locating the Godot Executable

Godot is **not installed** on this machine. Before the smoke test can run, the binary must be present. Options:

| Platform | How to get it |
|---|---|
| Linux | `apt install godot4` (Ubuntu 24.04+), or download from [godotengine.org/download](https://godotengine.org/download) and extract. The binary may be named `godot4`. |
| macOS | `/Applications/Godot.app/Contents/MacOS/Godot` after dragging the .app to Applications. |
| Windows | Full path, e.g. `C:/Godot/Godot_v4.3-stable_win64.exe`. |

After installing, verify the version:

```bash
godot --version   # must print 4.x
# or
godot4 --version
```

Set `GODOT_BIN` if the binary is not on PATH:

```bash
export GODOT_BIN=/path/to/godot
```

The bundled script (`scripts/run_godot_tests.py`) and GdUnit4's own runners both honor `GODOT_BIN`.

---

## Full Workflow (What Would Execute)

Because Godot is not installed here, the commands below are the exact sequence that would run and the gates that must pass:

```bash
# 1. Confirm Godot 4 is present
godot --version
# Gate: output must match "4.*"

# 2. Run the headless smoke test
output=$(godot --headless --path /tmp/eval-work/smoke-w --quit-after 120 2>&1)
exit_code=$?
echo "$output"

# 3. Gate 1 — clean exit
[ $exit_code -eq 0 ] || { echo "FAIL: non-zero exit ($exit_code)"; exit 1; }

# 4. Gate 2 — no error lines
echo "$output" | grep -qE "SCRIPT ERROR|ERROR:|Parse Error" \
  && { echo "FAIL: error lines found in output"; exit 1; }

echo "SMOKE TEST PASSED — safe to push"
```

Only proceed to `git push` after both gates are green.

---

## When the Smoke Test Is Not Enough

The headless smoke test confirms the engine starts and the main scene loads. It does **not** cover game logic correctness. For that, add GdUnit4 unit tests and run them with:

```bash
python3 /path/to/skill/scripts/run_godot_tests.py --project /tmp/eval-work/smoke-w
```

See the `godot-testing` skill's **Setup (GdUnit4)** section for how to install the test framework and write `GdUnitTestSuite` classes.
