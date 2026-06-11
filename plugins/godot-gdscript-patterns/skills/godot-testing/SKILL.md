---
name: godot-testing
description: This skill should be used when writing or running tests for a Godot 4 project, setting up GdUnit4 or GUT, verifying a Godot game headlessly, or when the user asks to test or verify Godot code, run the game without the editor, set up CI for Godot, or mentions GdUnit4, GUT, GdUnitTestSuite, "godot --headless", smoke-testing a .tscn scene, or unit-testing .gd scripts.
---

# Godot Testing and Headless Verification

Automated testing and headless verification for Godot 4 projects. Never
declare Godot code working without running it: write tests, execute them
headless, and iterate until green.

All paths below are relative to this skill's directory — locate the installed
skill directory once before running bundled scripts.

## Quick Start

If the project already has GdUnit4 tests, run them headless:

```
python3 scripts/run_godot_tests.py --project <project-dir>
```

(on Windows, use `py -3` if `python3` is unavailable)

The script locates the Godot executable (`--godot-bin` argument, then the
`GODOT_BIN` environment variable, then `godot`/`godot4` on PATH), runs the
GdUnit4 suite headless, and prints a pass/fail summary. Exit code 0 means
green; anything else means fix and re-run.

## Decision Tree

- No test framework in the project yet? → [Setup](#setup-gdunit4) — install
  GdUnit4 (default; use GUT only if the project already uses it).
- Unit-testing GDScript logic (inventory, damage math, state machines)? →
  write a `GdUnitTestSuite` per class under `test/`, then run headless.
- Verifying scenes load and the game boots? →
  [Headless smoke run](#headless-smoke-test).
- Setting up CI? → use the same headless commands; they need no display
  server.

## The Core Feedback Loop

Follow this loop for every change; do not skip the run step:

1. Implement or modify code.
2. Run the tests headless (`python3 scripts/run_godot_tests.py --project .`).
3. Read failures from the output and the JUnit report; fix the root cause.
4. Re-run. **Only proceed when the run is green (exit code 0).**

Writing tests without executing them verifies nothing. If no display is
available, headless mode is always sufficient for logic and scene-load tests.

## Running Godot Headless

Godot runs without a window or GPU via `--headless`:

```
godot --headless --path <project-dir> [args]
```

Locating the executable:

- **Windows**: Godot is a portable .exe, usually not on PATH. Use the full
  path with forward slashes, e.g. `C:/Godot/Godot_v4.3-stable_win64.exe`.
- **Linux**: package managers often name the binary `godot4`; a manual
  download is `godot`.
- **macOS**: `/Applications/Godot.app/Contents/MacOS/Godot`.
- Set `GODOT_BIN` to the executable path once per machine; the bundled script
  and GdUnit4's own runners both honor it.

Verify the executable and version first: `godot --version` must print `4.x`.

## Setup (GdUnit4)

Default to **GdUnit4**. Install into the project:

1. Get the addon: Godot editor AssetLib (search "GdUnit4"), or
   `git clone https://github.com/MikeSchulze/gdUnit4 addons/gdUnit4`
   (then delete its nested `.git`).
2. Enable the plugin: Project Settings > Plugins > GdUnit4, or add
   `enabled=PackedStringArray("res://addons/gdUnit4/plugin.cfg")` under
   `[editor_plugins]` in `project.godot`.
3. Create a `test/` directory mirroring the source layout.

A minimal test suite:

```gdscript
# test/inventory_test.gd
class_name InventoryTest
extends GdUnitTestSuite

func test_add_item() -> void:
    var inventory := Inventory.new()
    inventory.add_item("sword", 1)
    assert_int(inventory.count("sword")).is_equal(1)

func test_remove_missing_item_fails() -> void:
    var inventory := Inventory.new()
    assert_bool(inventory.remove_item("axe")).is_false()
```

**Escape hatch — GUT**: if the project already contains `addons/gut`, keep
GUT instead of converting. Run it headless with:

```
godot --headless --path <project-dir> -s addons/gut/gut_cmdln.gd -gdir=res://test -ginclude_subdirs -gexit
```

## GdUnit4 CLI Invocation

Prefer `scripts/run_godot_tests.py`, which wraps this exact command
(GdUnit4 v4.x for Godot 4.2+):

```
<godot> --headless --path <project-dir> -d -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a <test-dir> -c --ignoreHeadlessMode
```

- `-a <test-dir>` adds a test directory or file (e.g. `test`).
- `-c` continues past failures so the full suite reports.
- `--ignoreHeadlessMode` is required: GdUnit4 otherwise refuses to run
  headless (input-simulation tests cannot work without a display).
- The same command is what the bundled `addons/gdUnit4/runtest.sh|.cmd`
  wrappers execute.

## Parsing Results

- **Exit code**: 0 = all green; non-zero = failures or setup errors.
- **JUnit XML**: GdUnit4 writes `reports/report_<N>/results.xml` under the
  project root (highest `<N>` is the latest run). Read `testsuite` attributes
  `tests`, `failures`, `errors`, `skipped`, and each `<failure>` message for
  the failing assertion. The bundled script summarizes this automatically.
- An HTML report sits next to the XML for human review.

## Headless Smoke Test

To verify the game boots and scenes instantiate without a test framework,
run the main scene for a fixed number of frames:

```
godot --headless --path <project-dir> --quit-after 120
```

`--quit-after 120` exits after 120 process frames (~2 seconds at 60 FPS —
enough for `_ready` of the main scene tree and a few full frames). A specific
scene can be smoke-tested by appending its path:

```
godot --headless --path <project-dir> --quit-after 120 res://scenes/level_1.tscn
```

Treat the smoke test as failed if either:

- the exit code is non-zero, or
- the output contains `SCRIPT ERROR`, `ERROR:`, or `Parse Error` lines
  (Godot can exit 0 despite script errors, so always scan the output).

## Verification Checklist

Before declaring Godot work complete, confirm every item:

- [ ] Tests exist for the changed logic (one `GdUnitTestSuite` per class)
- [ ] The full suite was actually executed headless, not just written
- [ ] Latest run exited 0 and the JUnit report shows 0 failures/errors
- [ ] A headless smoke run of the affected scene(s) produced no
      `SCRIPT ERROR`/`ERROR:` output
- [ ] Tests use static typing and Godot 4 syntax (no `yield`)
- [ ] Commands documented for the user use forward slashes and work without
      the editor open
