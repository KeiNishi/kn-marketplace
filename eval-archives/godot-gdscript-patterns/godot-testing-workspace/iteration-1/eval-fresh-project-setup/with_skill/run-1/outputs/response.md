# Setting Up Automated Testing for a Fresh Godot 4 Project

This guide sets up GdUnit4 as the test framework and shows you how to run tests headlessly from the command line and in CI.

---

## Overview

Because this is a fresh project with no tests, the recommended path is:

1. Install the GdUnit4 addon into the project.
2. Enable the plugin in `project.godot`.
3. Create a `test/` directory and write test suites.
4. Run headless via the bundled Python runner or directly via the Godot CLI.

Godot is not installed in the current environment, so the exact commands are documented below with notes on what gates each step.

---

## Step 1 — Install GdUnit4

Clone GdUnit4 into your project's `addons/` folder:

```bash
cd /tmp/eval-work/setup-w
git clone https://github.com/MikeSchulze/gdUnit4 addons/gdUnit4
rm -rf addons/gdUnit4/.git        # drop the nested repo
```

**Gate**: the file `addons/gdUnit4/bin/GdUnitCmdTool.gd` must exist after this step. The Python runner (`run_godot_tests.py`) checks for it and exits with an actionable error if it is missing.

Alternative (no git): open the Godot editor, go to **AssetLib**, search **GdUnit4**, and install. This writes the same file tree.

---

## Step 2 — Enable the Plugin in `project.godot`

Add or ensure the `[editor_plugins]` section in `project.godot` contains the GdUnit4 entry:

```ini
[editor_plugins]

enabled=PackedStringArray("res://addons/gdUnit4/plugin.cfg")
```

The scaffolded `project.godot` at `/tmp/eval-work/setup-w/project.godot` already contains this block.

---

## Step 3 — Create the `test/` Directory

Mirror the source layout under `test/`. A minimal first test suite:

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

This file has been scaffolded at `/tmp/eval-work/setup-w/test/inventory_test.gd`.

Rules for all test files:
- Extend `GdUnitTestSuite` (not `Node`).
- Prefix every test method with `test_`.
- Use static typing and Godot 4 syntax — no `yield`.

---

## Step 4 — Verify the Godot Binary

Before running tests, confirm you have Godot 4 available:

```bash
godot --version   # must print 4.x; on Linux may be "godot4"
```

If Godot is not on PATH, set the environment variable once:

```bash
export GODOT_BIN=/path/to/Godot_v4.3-stable_linux.x86_64
```

Platform notes:
- **Linux**: package managers (apt/dnf) name it `godot4`; a manual download is `godot`.
- **Windows**: use the full path, e.g. `C:/Godot/Godot_v4.3-stable_win64.exe`.
- **macOS**: `/Applications/Godot.app/Contents/MacOS/Godot`.

**Gate**: `godot --version` (or `$GODOT_BIN --version`) must print `4.x` before proceeding.

---

## Step 5 — Run Tests Headlessly (Local)

Use the bundled Python runner (pure stdlib, no pip required):

```bash
python3 /home/user/kn-marketplace/plugins/godot-gdscript-patterns/skills/godot-testing/scripts/run_godot_tests.py \
    --project /tmp/eval-work/setup-w
```

Or copy `run_godot_tests.py` next to the project and run from there:

```bash
cp /home/user/kn-marketplace/plugins/godot-gdscript-patterns/skills/godot-testing/scripts/run_godot_tests.py /tmp/eval-work/setup-w/
python3 /tmp/eval-work/setup-w/run_godot_tests.py --project /tmp/eval-work/setup-w
```

The script:
1. Locates the Godot executable (via `--godot-bin`, then `GODOT_BIN`, then PATH).
2. Runs the exact GdUnit4 CLI command:
   ```
   <godot> --headless --path <project> -d -s addons/gdUnit4/bin/GdUnitCmdTool.gd \
       -a test -c --ignoreHeadlessMode
   ```
3. Parses the JUnit XML report at `reports/report_<N>/results.xml`.
4. Prints a summary: `N tests: X passed, Y failed, Z errors`.
5. Exits 0 on full green; non-zero on any failure.

**Gate**: the runner must exit 0 before you consider the suite passing. Do not skip this step.

If you need to run a specific test file:

```bash
python3 run_godot_tests.py --project /tmp/eval-work/setup-w --tests test/inventory_test.gd
```

---

## Step 6 — Headless Smoke Test (Boot Check)

To verify the game itself boots (separate from unit tests):

```bash
godot --headless --path /tmp/eval-work/setup-w --quit-after 120
```

`--quit-after 120` exits after 120 process frames (~2 s at 60 FPS). The command succeeds when:
- Exit code is 0, **and**
- Output contains no `SCRIPT ERROR`, `ERROR:`, or `Parse Error` lines.

Always scan the output even if the exit code is 0 — Godot can exit 0 despite script errors.

---

## Step 7 — CI Setup

The same headless commands require no display server, so they run directly in any CI environment (GitHub Actions, GitLab CI, etc.).

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Godot Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Godot 4
        run: |
          wget -q https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip
          unzip -q Godot_v4.3-stable_linux.x86_64.zip
          echo "GODOT_BIN=$(pwd)/Godot_v4.3-stable_linux.x86_64" >> $GITHUB_ENV

      - name: Install GdUnit4
        run: |
          git clone --depth 1 https://github.com/MikeSchulze/gdUnit4 addons/gdUnit4
          rm -rf addons/gdUnit4/.git

      - name: Run tests
        run: |
          python3 run_godot_tests.py --project .

      - name: Upload JUnit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-report
          path: reports/
```

Key points:
- No `Xvfb` or display server is needed — `--headless` handles everything.
- The `GODOT_BIN` environment variable is set so the Python runner can find the binary.
- The JUnit XML at `reports/report_*/results.xml` integrates with GitHub's test-report UI via the upload artifact step (or use a dedicated JUnit action).

---

## Scaffolded File Tree

```
/tmp/eval-work/setup-w/
├── project.godot                          # Godot project file with GdUnit4 plugin enabled
├── run_godot_tests.py                     # Bundled test runner (copy from skill scripts/)
├── addons/
│   └── gdUnit4/                           # Clone from GitHub (not present until Step 1)
│       └── bin/
│           └── GdUnitCmdTool.gd           # Gate: must exist before running tests
└── test/
    └── inventory_test.gd                  # Example test suite (replace with your own)
```

---

## The Core Feedback Loop

Follow this loop for every change:

1. Implement or modify a class.
2. Write or update the corresponding `GdUnitTestSuite` in `test/`.
3. Run: `python3 run_godot_tests.py --project .`
4. Read failures from the output and the JUnit report; fix the root cause.
5. Re-run. **Only proceed when exit code is 0.**

Writing tests without executing them verifies nothing. Headless mode is always sufficient for logic and scene-load tests.

---

## Verification Checklist

- [ ] `addons/gdUnit4/bin/GdUnitCmdTool.gd` exists
- [ ] `[editor_plugins]` in `project.godot` enables `res://addons/gdUnit4/plugin.cfg`
- [ ] `test/` directory exists with at least one `*_test.gd` extending `GdUnitTestSuite`
- [ ] `godot --version` prints `4.x`
- [ ] `python3 run_godot_tests.py --project .` exits 0
- [ ] JUnit report at `reports/report_*/results.xml` shows 0 failures and 0 errors
- [ ] Headless smoke run exits 0 with no `SCRIPT ERROR`/`ERROR:` lines
