# Running Unity Tests in CI Without the Editor (Batch Mode)

## Overview

Unity's `-batchmode -runTests` flags let you execute your test suite headlessly — no GPU, no display server, no interactive editor needed. The approach used here wraps those flags inside the **game-ci/unity-test-runner** GitHub Actions action, which handles licence activation, NUnit result parsing, and exit-code propagation automatically.

---

## Prerequisites

### 1. Unity version pin

Open `ProjectSettings/ProjectVersion.txt` and note the exact version string, e.g.:

```
m_EditorVersion: 2022.3.20f1
```

Replace every occurrence of `2022.3.20f1` in the files below with your actual version.

### 2. Repository secrets (GitHub → Settings → Secrets → Actions)

| Secret name      | Value |
|------------------|-------|
| `UNITY_LICENSE`  | Contents of your `.ulf` licence file (Personal) *or* the serial key approach for Pro. See [game-ci licence docs](https://game-ci.com/docs/github/activation). |
| `UNITY_EMAIL`    | Unity account e-mail |
| `UNITY_PASSWORD` | Unity account password |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — you do not need to create it.

---

## File layout to add to your project

```
Assets/
  Tests/
    Editor/
      SampleTest.cs          ← example EditMode test
      SampleTest.asmdef      ← assembly definition (marks as test assembly)
Packages/
  manifest.json              ← ensures com.unity.test-framework is listed
.github/
  workflows/
    unity-tests.yml          ← CI workflow (the key file)
run-tests-local.sh           ← helper for running the same command locally
```

---

## `.github/workflows/unity-tests.yml`

```yaml
name: Unity Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    name: Run Unity Tests (EditMode + PlayMode)
    runs-on: ubuntu-latest

    steps:
      # ── 1. Checkout ──────────────────────────────────────────────────────────
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          lfs: true

      # ── 2. Cache Library folder ───────────────────────────────────────────────
      # The Library folder is re-generated on first import and can be large.
      # Caching it dramatically speeds up subsequent runs.
      - name: Cache Unity Library
        uses: actions/cache@v4
        with:
          path: Library
          key: Library-${{ runner.os }}-${{ hashFiles('Assets/**', 'Packages/**', 'ProjectSettings/**') }}
          restore-keys: |
            Library-${{ runner.os }}-
            Library-

      # ── 3. Run Unity tests in batch mode ────────────────────────────────────
      # game-ci/unity-test-runner wraps `Unity -batchmode -runTests` for you.
      # It handles licence activation, result parsing and exit-code propagation.
      - name: Run EditMode tests
        id: editmode_tests
        uses: game-ci/unity-test-runner@v4
        env:
          UNITY_LICENSE: ${{ secrets.UNITY_LICENSE }}
          UNITY_EMAIL:   ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
        with:
          # Pin the Unity version that matches your ProjectSettings/ProjectVersion.txt
          unityVersion: 2022.3.20f1
          testMode: EditMode
          # Write NUnit XML results here so we can upload them as artefacts
          artifactsPath: test-results/editmode
          # Fail this step (and therefore the job) when any test fails
          githubToken: ${{ secrets.GITHUB_TOKEN }}
          checkName: EditMode Test Results

      - name: Run PlayMode tests
        id: playmode_tests
        uses: game-ci/unity-test-runner@v4
        env:
          UNITY_LICENSE: ${{ secrets.UNITY_LICENSE }}
          UNITY_EMAIL:   ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
        with:
          unityVersion: 2022.3.20f1
          testMode: PlayMode
          artifactsPath: test-results/playmode
          githubToken: ${{ secrets.GITHUB_TOKEN }}
          checkName: PlayMode Test Results

      # ── 4. Upload result XML as artefacts ────────────────────────────────────
      # Available even when tests fail so you can inspect the report.
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unity-test-results
          path: test-results/
          retention-days: 14
```

### Why the build fails when a test fails

`game-ci/unity-test-runner` reads the NUnit XML produced by `-testResults` and exits with a non-zero code when any `<test-case result="Failed">` element is present. GitHub Actions marks the step — and therefore the entire job — as failed, blocking merges that require passing status checks.

---

## `Assets/Tests/Editor/SampleTest.asmdef`

Every test script must belong to an Assembly Definition that opts in to the test framework. The critical field is `"optionalUnityReferences": ["TestAssemblies"]`.

```json
{
    "name": "MyGame.Tests.Editor",
    "rootNamespace": "MyGame.Tests.Editor",
    "references": [],
    "includePlatforms": ["Editor"],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": false,
    "defineConstraints": [],
    "versionDefines": [],
    "noEngineReferences": false,
    "optionalUnityReferences": ["TestAssemblies"]
}
```

For PlayMode tests, create a separate `.asmdef` in `Assets/Tests/PlayMode/` with `"includePlatforms": []` (empty = all platforms) and the same `optionalUnityReferences` entry.

---

## `Assets/Tests/Editor/SampleTest.cs`

```csharp
using NUnit.Framework;

namespace MyGame.Tests.Editor
{
    public class SampleTest
    {
        [Test]
        public void Addition_ReturnsCorrectResult()
        {
            Assert.AreEqual(4, 2 + 2);
        }

        [Test]
        public void Subtraction_ReturnsCorrectResult()
        {
            Assert.AreEqual(0, 2 - 2);
        }
    }
}
```

---

## `Packages/manifest.json` (minimum addition)

Make sure `com.unity.test-framework` is explicitly listed so the package is always present in CI:

```json
{
  "dependencies": {
    "com.unity.test-framework": "1.3.9"
  }
}
```

Use whatever version your project already has; do not downgrade.

---

## `run-tests-local.sh` — run the same command locally

```bash
#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run-tests-local.sh
# Run Unity tests in batch mode without opening the editor.
# Mirrors exactly what the CI workflow does, useful for local verification.
#
# Usage:
#   UNITY_PATH=/Applications/Unity/Hub/Editor/2022.3.20f1/Unity.app/Contents/MacOS/Unity \
#   ./run-tests-local.sh
#
# On Linux the binary is usually at:
#   /opt/unity/Editor/Unity
# ---------------------------------------------------------------------------
set -euo pipefail

UNITY="${UNITY_PATH:-/opt/unity/Editor/Unity}"
PROJECT_PATH="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="${PROJECT_PATH}/test-results"

mkdir -p "${RESULTS_DIR}/editmode" "${RESULTS_DIR}/playmode"

echo "==> Running EditMode tests"
"${UNITY}" \
  -batchmode \
  -nographics \
  -projectPath "${PROJECT_PATH}" \
  -runTests \
  -testPlatform EditMode \
  -testResults "${RESULTS_DIR}/editmode/results.xml" \
  -logFile "${RESULTS_DIR}/editmode/unity.log"

EDIT_EXIT=$?

echo "==> Running PlayMode tests"
"${UNITY}" \
  -batchmode \
  -nographics \
  -projectPath "${PROJECT_PATH}" \
  -runTests \
  -testPlatform PlayMode \
  -testResults "${RESULTS_DIR}/playmode/results.xml" \
  -logFile "${RESULTS_DIR}/playmode/unity.log"

PLAY_EXIT=$?

# Propagate failure so the calling process (CI or shell) sees a non-zero exit.
if [ "${EDIT_EXIT}" -ne 0 ] || [ "${PLAY_EXIT}" -ne 0 ]; then
  echo "ERROR: One or more test suites failed."
  exit 1
fi

echo "All tests passed."
```

---

## Key Unity CLI flags explained

| Flag | Purpose |
|------|---------|
| `-batchmode` | Suppress all UI; mandatory for headless execution. |
| `-nographics` | Skip GPU initialisation; required on machines without a display (most CI agents). |
| `-runTests` | Activate the Test Runner instead of a normal build. |
| `-testPlatform EditMode\|PlayMode` | Select the test domain. Run both separately to get full coverage. |
| `-testResults <path>` | Write NUnit-compatible XML; exit code is non-zero when any test fails. |
| `-logFile <path>` | Capture the editor log for post-mortem inspection. Omit or set to `-` to print to stdout. |
| `-projectPath <path>` | Absolute path to the Unity project root (the folder containing `Assets/`). |

---

## Result gates — what must pass for CI to go green

1. **Unity process exit code = 0** — non-zero means at least one test failed or the editor crashed.
2. **NUnit XML `<test-suite result="...">` attribute** — `game-ci/unity-test-runner` parses this and fails the step when the value is not `"Passed"`.
3. **Both EditMode and PlayMode steps** must succeed; a failure in either blocks the job.

The uploaded `unity-test-results` artefact contains the XML and editor log regardless of outcome (`if: always()`), so you can diagnose failures without re-running.

---

## Protecting branches

In GitHub → Settings → Branches → Branch protection rules for `main`/`develop`:

- Enable **Require status checks to pass before merging**.
- Add `EditMode Test Results` and `PlayMode Test Results` as required checks (these names match the `checkName` fields in the workflow).

Pull requests that have any failing test will be blocked from merging automatically.
