# Setting Up Automated Testing for a Fresh Godot 4 Project

This guide walks you through wiring [GUT (Godot Unit Test)](https://github.com/bitwes/Gut) into a fresh Godot 4 project so tests run from the command line and in CI (GitHub Actions).

---

## What you will end up with

```
.
├── .github/
│   └── workflows/
│       └── tests.yml          # CI pipeline — runs on every push / PR
├── addons/
│   └── gut/                   # GUT addon files (installed once, committed)
├── src/
│   ├── math_utils.gd          # Your game source (example)
│   └── player.gd
├── tests/
│   ├── test_math_utils.gd     # GUT test files
│   └── test_player.gd
├── test-results/              # Generated output — JUnit XML lands here
├── .gitignore
├── .gutconfig.json            # GUT CLI configuration
└── project.godot
```

---

## Step 1 — Install the GUT addon

### Option A: via the Godot Editor (recommended for local dev)

1. Open your project in the Godot editor.
2. Click the **AssetLib** tab (top centre).
3. Search for **"GUT - Godot Unit Testing"**.
4. Click **Download → Install**.
5. Enable it: **Project → Project Settings → Plugins → GUT → Enable**.

GUT is placed at `addons/gut/`.

### Option B: manual download (CI or no editor available)

Run these commands from your project root:

```bash
GUT_VERSION="7.4.2"
wget -q "https://github.com/bitwes/Gut/releases/download/v${GUT_VERSION}/gut_${GUT_VERSION}.zip"
unzip -q "gut_${GUT_VERSION}.zip" -d addons/
rm "gut_${GUT_VERSION}.zip"
```

**Gate:** `addons/gut/gut_cmdln.gd` must exist before proceeding.

> Commit the entire `addons/gut/` directory so CI can use it without a separate download step.

---

## Step 2 — Add `.gutconfig.json`

Create this file at the project root. It tells GUT where to find tests and where to write results.

```json
{
  "dirs": ["res://tests/"],
  "prefix": "test_",
  "suffix": ".gd",
  "gut_on_top": true,
  "log_level": 1,
  "junit_xml_file": "res://test-results/results.xml",
  "junit_xml_timestamp": false,
  "should_exit": true,
  "should_exit_on_success": true,
  "color_output": true
}
```

Key fields:

| Field | Purpose |
|---|---|
| `dirs` | Directories GUT scans for test files |
| `prefix` / `suffix` | File name pattern — only files named `test_*.gd` are picked up |
| `junit_xml_file` | Machine-readable output for CI systems |
| `should_exit` | Makes the process exit (required for headless / CI use) |

---

## Step 3 — Create the `tests/` directory and write your first tests

GUT auto-discovers every `.gd` file in the `dirs` list whose name starts with `test_`. Each test function must start with `test_`.

### `tests/test_math_utils.gd` — pure function tests

```gdscript
## test_math_utils.gd
## Unit tests for MathUtils using GUT.
extends GutTest


func test_add_positive_numbers() -> void:
    assert_eq(MathUtils.add(2, 3), 5, "2 + 3 should equal 5")


func test_add_negative_numbers() -> void:
    assert_eq(MathUtils.add(-1, -4), -5, "-1 + -4 should equal -5")


func test_add_zero() -> void:
    assert_eq(MathUtils.add(7, 0), 7, "adding zero returns original value")


func test_is_even_with_even_number() -> void:
    assert_true(MathUtils.is_even(4), "4 is even")


func test_is_even_with_odd_number() -> void:
    assert_false(MathUtils.is_even(3), "3 is not even")


func test_is_even_with_zero() -> void:
    assert_true(MathUtils.is_even(0), "0 is even")


func test_clamp_value_within_range() -> void:
    assert_eq(MathUtils.clamp_value(5.0, 0.0, 10.0), 5.0)


func test_clamp_value_below_min() -> void:
    assert_eq(MathUtils.clamp_value(-5.0, 0.0, 10.0), 0.0)


func test_clamp_value_above_max() -> void:
    assert_eq(MathUtils.clamp_value(15.0, 0.0, 10.0), 10.0)
```

### `tests/test_player.gd` — node tests with setup/teardown

```gdscript
## test_player.gd
## Unit tests for the Player node using GUT.
extends GutTest


var _player: Player


func before_each() -> void:
    _player = Player.new()
    add_child(_player)


func after_each() -> void:
    _player.queue_free()


# --- health baseline ---

func test_player_starts_at_full_health() -> void:
    assert_eq(_player.health, 100, "player starts at 100 HP")


func test_player_is_not_dead_at_start() -> void:
    assert_false(_player.is_dead(), "player is alive at start")


# --- take_damage ---

func test_take_damage_reduces_health() -> void:
    _player.take_damage(30)
    assert_eq(_player.health, 70)


func test_take_damage_does_not_go_below_zero() -> void:
    _player.take_damage(999)
    assert_eq(_player.health, 0, "health cannot be negative")


func test_player_dies_when_health_reaches_zero() -> void:
    _player.take_damage(100)
    assert_true(_player.is_dead())


# --- heal ---

func test_heal_increases_health() -> void:
    _player.take_damage(50)
    _player.heal(20)
    assert_eq(_player.health, 70)


func test_heal_does_not_exceed_max_health() -> void:
    _player.heal(500)
    assert_eq(_player.health, _player.max_health, "health cannot exceed max")
```

### Writing new tests — pattern

```gdscript
extends GutTest

func test_something() -> void:
    assert_eq(1 + 1, 2, "basic arithmetic works")
```

For tests that need a live node:

```gdscript
var _subject: MyNode

func before_each() -> void:
    _subject = MyNode.new()
    add_child(_subject)

func after_each() -> void:
    _subject.queue_free()
```

---

## Step 4 — Keep `test-results/` in git (the directory, not its contents)

Create a placeholder so the directory exists after a fresh clone:

```bash
mkdir -p test-results
touch test-results/.gitkeep
```

Add to `.gitignore`:

```
# CI artifacts — generated, not committed
test-results/*.xml
test-results/*.log
```

(Keep `.gitkeep` itself tracked.)

---

## Step 5 — Import the project (first run only)

Before tests can run, Godot must build its import cache (`.godot/`):

```bash
godot --headless --editor --quit
```

**Gate:** this may return a non-zero exit code on the very first run — that is a [known Godot behaviour](https://github.com/godotengine/godot/issues). Re-run it once or twice until exit code is 0. The CI workflow (below) handles this automatically with a retry loop.

---

## Step 6 — Run tests locally

```bash
# Full suite
godot --headless -s addons/gut/gut_cmdln.gd -gconfig=.gutconfig.json
```

Exit codes:
- `0` — all tests passed
- `1` — one or more tests failed or errored

```bash
# Single test file
godot --headless -s addons/gut/gut_cmdln.gd \
  -gtest=res://tests/test_math_utils.gd

# Single test function
godot --headless -s addons/gut/gut_cmdln.gd \
  -gtest=res://tests/test_player.gd \
  -gunit_test_name=test_take_damage_reduces_health
```

After a run, `test-results/results.xml` contains JUnit-compatible output readable by most CI systems and IDEs.

---

## Step 7 — CI pipeline (GitHub Actions)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  test:
    name: Run GUT tests (Godot 4)
    runs-on: ubuntu-latest

    steps:
      # ── 1. Checkout ─────────────────────────────────────────────────────────
      - name: Checkout repository
        uses: actions/checkout@v4

      # ── 2. Install Godot 4 ──────────────────────────────────────────────────
      - name: Download Godot 4.3 (headless / Linux)
        run: |
          GODOT_VERSION="4.3"
          GODOT_FILENAME="Godot_v${GODOT_VERSION}-stable_linux.x86_64"
          wget -q "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/${GODOT_FILENAME}.zip"
          unzip -q "${GODOT_FILENAME}.zip"
          mv "${GODOT_FILENAME}" /usr/local/bin/godot
          chmod +x /usr/local/bin/godot

      # ── 3. Cache Godot import cache ─────────────────────────────────────────
      - name: Cache Godot import cache
        uses: actions/cache@v4
        with:
          path: .godot/
          key: godot-import-${{ runner.os }}-${{ hashFiles('**/*.gd', '**/*.tscn', '**/*.tres', 'project.godot') }}
          restore-keys: |
            godot-import-${{ runner.os }}-

      # ── 4. Import project (generates .godot/) ───────────────────────────────
      - name: Import project assets
        run: |
          godot --headless --editor --quit 2>&1 || true
          # The editor import may exit non-zero on first run; that is expected.
          # We loop until the import cache is populated.
          for i in 1 2 3; do
            godot --headless --editor --quit 2>&1 && break || sleep 5
          done

      # ── 5. Verify GUT addon present ─────────────────────────────────────────
      - name: Verify GUT addon
        run: |
          if [ ! -f "addons/gut/gut_cmdln.gd" ]; then
            echo "ERROR: GUT addon not found at addons/gut/gut_cmdln.gd"
            echo "Run the setup instructions in README to install it."
            exit 1
          fi

      # ── 6. Run tests ─────────────────────────────────────────────────────────
      - name: Run GUT test suite
        run: |
          mkdir -p test-results
          godot --headless -s addons/gut/gut_cmdln.gd \
            -gconfig=.gutconfig.json \
            2>&1 | tee test-results/stdout.log
          # gut_cmdln.gd exits with 0 on success, 1 on failure.

      # ── 7. Publish test results ──────────────────────────────────────────────
      - name: Publish JUnit XML results
        if: always()
        uses: mikepenz/action-junit-report@v4
        with:
          report_paths: "test-results/results.xml"
          fail_on_failure: true
          require_tests: true

      # ── 8. Upload artifacts ───────────────────────────────────────────────────
      - name: Upload test artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results/
```

### What each CI step gates on

| Step | Gate condition |
|---|---|
| Checkout | always runs |
| Download Godot 4.3 headless binary | binary must be fetchable from GitHub releases |
| Cache `.godot/` | cache hit skips re-import (speeds up subsequent runs) |
| Import project (`--editor --quit`) | retried up to 3 times with `sleep 5` between attempts; loop exits on first exit-0 |
| Verify `addons/gut/gut_cmdln.gd` | exits 1 immediately if GUT is missing — fail fast before the expensive test run |
| Run GUT test suite | exits 1 if any test fails or errors |
| Publish JUnit XML | always runs (even on failure), so you see results in the GitHub UI |
| Upload `test-results/` artifact | always runs — downloadable for local inspection |

---

## Common GUT assertions reference

| Assertion | Meaning |
|---|---|
| `assert_eq(a, b)` | a == b |
| `assert_ne(a, b)` | a != b |
| `assert_true(expr)` | expr is truthy |
| `assert_false(expr)` | expr is falsy |
| `assert_null(val)` | val == null |
| `assert_not_null(val)` | val != null |
| `assert_almost_eq(a, b, tol)` | \|a-b\| <= tol (use for floats) |
| `assert_gt(a, b)` | a > b |
| `assert_lt(a, b)` | a < b |
| `assert_has(collection, item)` | item in collection |

Full reference: <https://gut.readthedocs.io/en/latest/Asserts-and-Methods.html>

---

## Why Godot is not installed in this environment

The scaffolded project under `/tmp/eval-work/setup-b/` contains all files described above. The actual `godot` binary is not available in this environment, so the commands listed in Steps 2, 5, and 6 cannot be executed here. They would execute exactly as written on any Linux machine with Godot 4.3 installed (or inside the GitHub Actions runner defined in Step 7).

The exact commands that would be run locally, in order:

```bash
# 1. Install GUT (if not already done via editor)
GUT_VERSION="7.4.2"
wget -q "https://github.com/bitwes/Gut/releases/download/v${GUT_VERSION}/gut_${GUT_VERSION}.zip"
unzip -q "gut_${GUT_VERSION}.zip" -d addons/
rm "gut_${GUT_VERSION}.zip"

# 2. Import project assets (may need to run 2-3 times)
godot --headless --editor --quit

# 3. Run the full test suite
godot --headless -s addons/gut/gut_cmdln.gd -gconfig=.gutconfig.json
```

Result gates:
- After step 1: `addons/gut/gut_cmdln.gd` must exist.
- After step 2: `.godot/` directory must exist and be populated; exit code must be 0 (retry if not).
- After step 3: exit code 0 means all tests passed; exit code 1 means failures exist; `test-results/results.xml` contains the JUnit report.
