# Setting Up Automated Unity Test Runs in CI (Batchmode)

This guide sets up headless Unity test execution in CI so **any test failure fails the build**. Unity never opens an editor window; all tests run via `-batchmode`.

---

## What the CI workflow does

1. Activates a Unity license on the CI machine.
2. Runs **EditMode** tests (pure C# logic — fast, no Play mode).
3. Runs **PlayMode** tests (MonoBehaviour, physics, coroutines — needs the player runtime).
4. Uploads the NUnit results XML as an artifact (even on failure, so you can inspect it).
5. Returns the Unity license.

Each test step uses `scripts/run_unity_tests.py`, which:
- Reads `ProjectSettings/ProjectVersion.txt` to auto-locate the matching Unity binary.
- Invokes Unity with `-batchmode -runTests -testPlatform <platform> -testResults <file> -logFile -`.
- Parses the NUnit XML and prints a failure summary.
- **Exits non-zero when any test fails**, causing the CI job to fail.

---

## File layout

```
MyUnityProject/
  scripts/
    run_unity_tests.py              # the runner (from the unity-testing skill)
  .github/
    workflows/
      unity-tests.yml               # CI workflow (below)
  Assets/_Project/
    Scripts/
      Gameplay/
        Gameplay.asmdef             # production asmdef
        Health.cs                   # example production class
    Tests/
      EditMode/
        EditModeTests.asmdef        # Editor-only test assembly
        HealthTests.cs              # [Test] NUnit tests
      PlayMode/
        PlayModeTests.asmdef        # test assembly (all platforms)
        PlayerFallTests.cs          # [UnityTest] coroutine tests
  Packages/
    manifest.json                   # must list com.unity.test-framework
  ProjectSettings/
    ProjectVersion.txt              # m_EditorVersion: 2022.3.20f1
```

---

## 1. GitHub Actions workflow — `.github/workflows/unity-tests.yml`

```yaml
name: Unity Tests

on:
  push:
    branches: [ "**" ]
  pull_request:
    branches: [ "**" ]

jobs:
  test:
    name: Run Unity Tests (batchmode)
    # Use ubuntu-latest when your CI image includes Unity;
    # swap for a self-hosted runner that has Unity pre-installed.
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Activate Unity license (personal)
        # Personal licenses: set UNITY_LICENSE secret to the .ulf file contents,
        # or use UNITY_EMAIL + UNITY_PASSWORD + UNITY_SERIAL for a pro/plus seat.
        run: |
          "$UNITY_PATH" -batchmode -nographics -quit \
            -username "${{ secrets.UNITY_EMAIL }}" \
            -password "${{ secrets.UNITY_PASSWORD }}" \
            -serial   "${{ secrets.UNITY_SERIAL }}"
        env:
          UNITY_PATH: ${{ secrets.UNITY_PATH }}
        # Remove this step if your runner uses a pre-activated floating license.

      - name: Run EditMode tests
        run: |
          python3 scripts/run_unity_tests.py \
            --project-path . \
            --test-platform EditMode \
            --results /tmp/unity-results-editmode.xml
        env:
          UNITY_PATH: ${{ secrets.UNITY_PATH }}
        # Non-zero exit on any test failure → job fails here.

      - name: Run PlayMode tests
        run: |
          python3 scripts/run_unity_tests.py \
            --project-path . \
            --test-platform PlayMode \
            --results /tmp/unity-results-playmode.xml
        env:
          UNITY_PATH: ${{ secrets.UNITY_PATH }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: unity-test-results
          path: |
            /tmp/unity-results-editmode.xml
            /tmp/unity-results-playmode.xml
          retention-days: 14

      - name: Return Unity license
        if: always()
        run: |
          "$UNITY_PATH" -batchmode -quit -returnlicense
        env:
          UNITY_PATH: ${{ secrets.UNITY_PATH }}
        # Remove if using a floating / server license.
```

**Required repository secrets:**

| Secret | Value |
|---|---|
| `UNITY_PATH` | Full path to Unity binary on the runner, e.g. `/home/runner/Unity/Hub/Editor/2022.3.20f1/Editor/Unity` |
| `UNITY_EMAIL` | Unity account email |
| `UNITY_PASSWORD` | Unity account password |
| `UNITY_SERIAL` | Unity license serial (Pro/Plus) — omit for personal/file-based licenses |

---

## 2. The test runner script — `scripts/run_unity_tests.py`

Place this file at `scripts/run_unity_tests.py` in your project root. It is provided by the `unity-testing` skill and requires only the Python standard library.

**What it does:**

```
python3 scripts/run_unity_tests.py --project-path <unity-project> --test-platform EditMode
```

1. Validates the project path (checks for `Packages/manifest.json`).
2. Locates Unity: `--unity-bin` > `UNITY_PATH` env var > Unity Hub default paths.
3. Reads `ProjectSettings/ProjectVersion.txt` to find the exact editor version.
4. Runs the exact Unity command:
   ```
   <UnityBin> -batchmode -projectPath <path> -runTests -testPlatform EditMode \
               -testResults /tmp/unity_test_results_EditMode.xml -logFile -
   ```
5. Parses the NUnit XML: prints `total=N passed=N failed=N skipped=N`.
6. Prints each failed test's `fullname` and `failure/message`.
7. **Exits 1 if any test failed; exits 0 only when all pass.**

Key flags explained:
- `-batchmode` — no GUI, required for CI
- `-runTests` — activates the Test Framework; do **not** combine with `-quit`
- `-testPlatform EditMode|PlayMode` — which suite to run
- `-testResults <absolute-path>` — where to write the NUnit XML
- `-logFile -` — stream editor log to stdout (shows compile errors)

If Unity exits but writes no results file (compile errors, license failure, project lock), the script prints a diagnostic and exits 1.

---

## 3. Assembly definitions

### Production code — `Assets/_Project/Scripts/Gameplay/Gameplay.asmdef`

```json
{
    "name": "Gameplay",
    "rootNamespace": "MyGame.Gameplay",
    "references": [],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": [],
    "versionDefines": []
}
```

Production code **must** be in its own asmdef so the test asmdefs can reference it by name.

### EditMode tests — `Assets/_Project/Tests/EditMode/EditModeTests.asmdef`

```json
{
    "name": "EditModeTests",
    "rootNamespace": "MyGame.Tests.EditMode",
    "references": [
        "Gameplay",
        "UnityEngine.TestRunner",
        "UnityEditor.TestRunner"
    ],
    "includePlatforms": [
        "Editor"
    ],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": true,
    "precompiledReferences": [
        "nunit.framework.dll"
    ],
    "autoReferenced": false,
    "defineConstraints": [
        "UNITY_INCLUDE_TESTS"
    ],
    "versionDefines": []
}
```

`"includePlatforms": ["Editor"]` restricts this assembly to the Editor only.  
`"overrideReferences": true` + `"precompiledReferences": ["nunit.framework.dll"]` gives you NUnit.

### PlayMode tests — `Assets/_Project/Tests/PlayMode/PlayModeTests.asmdef`

```json
{
    "name": "PlayModeTests",
    "rootNamespace": "MyGame.Tests.PlayMode",
    "references": [
        "Gameplay",
        "UnityEngine.TestRunner"
    ],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": true,
    "precompiledReferences": [
        "nunit.framework.dll"
    ],
    "autoReferenced": false,
    "defineConstraints": [
        "UNITY_INCLUDE_TESTS"
    ],
    "versionDefines": []
}
```

No `includePlatforms` restriction — PlayMode tests run in a player context.  
Note: `UnityEditor.TestRunner` is **not** listed here (not available in player builds).

---

## 4. Example tests

### EditMode — `Assets/_Project/Tests/EditMode/HealthTests.cs`

```csharp
using NUnit.Framework;
using MyGame.Gameplay;

namespace MyGame.Tests.EditMode
{
    public class HealthTests
    {
        [Test]
        public void TakeDamage_ReducesHealthByAmount()
        {
            // Arrange
            var health = new Health(maxHealth: 100);
            // Act
            health.TakeDamage(30);
            // Assert
            Assert.That(health.Current, Is.EqualTo(70));
        }

        [Test]
        public void TakeDamage_ClampedAtZero_WhenDamageExceedsHealth()
        {
            var health = new Health(maxHealth: 50);
            health.TakeDamage(200);
            Assert.That(health.Current, Is.EqualTo(0));
        }

        [Test]
        public void Heal_RestoresHealth_UpToMax()
        {
            var health = new Health(maxHealth: 100);
            health.TakeDamage(40);
            health.Heal(20);
            Assert.That(health.Current, Is.EqualTo(80));
        }

        [Test]
        public void Heal_DoesNotExceedMax()
        {
            var health = new Health(maxHealth: 100);
            health.Heal(50);
            Assert.That(health.Current, Is.EqualTo(100));
        }
    }
}
```

Use `[Test]` for all pure C# logic. Arrange-Act-Assert. NUnit constraint syntax.

### PlayMode — `Assets/_Project/Tests/PlayMode/PlayerFallTests.cs`

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace MyGame.Tests.PlayMode
{
    public class PlayerFallTests
    {
        [UnityTest]
        public IEnumerator Player_FallsUnderGravity()
        {
            // Arrange
            var go = new GameObject("player", typeof(Rigidbody));
            float startY = go.transform.position.y;

            // Act - advance two physics frames
            yield return new WaitForFixedUpdate();
            yield return new WaitForFixedUpdate();

            // Assert
            Assert.That(go.transform.position.y, Is.LessThan(startY));

            // Cleanup
            Object.Destroy(go);
        }
    }
}
```

Use `[UnityTest]` returning `IEnumerator` for anything that needs frames, physics, or coroutines. Always `Object.Destroy` spawned GameObjects to keep tests independent.

### Example production class — `Assets/_Project/Scripts/Gameplay/Health.cs`

```csharp
namespace MyGame.Gameplay
{
    public class Health
    {
        public int Current { get; private set; }
        public int Max { get; }

        public Health(int maxHealth)
        {
            Max = maxHealth;
            Current = maxHealth;
        }

        public void TakeDamage(int amount)
        {
            Current -= amount;
            if (Current < 0) Current = 0;
        }

        public void Heal(int amount)
        {
            Current += amount;
            if (Current > Max) Current = Max;
        }
    }
}
```

---

## 5. `Packages/manifest.json` — require the Test Framework

```json
{
  "dependencies": {
    "com.unity.test-framework": "1.3.9"
  }
}
```

---

## How the build fails on test failure

The runner script exits with code 1 when any test fails. GitHub Actions (and every major CI system) treats a non-zero exit code as a step failure, which marks the job as failed and blocks the branch from merging (when branch protection rules are configured).

Output when tests fail:

```
Running: /home/runner/Unity/.../Unity -batchmode -projectPath . -runTests \
    -testPlatform EditMode -testResults /tmp/unity-results-editmode.xml -logFile -

=== Unity test results ===
total=4 passed=3 failed=1 skipped=0

FAILED: MyGame.Tests.EditMode.HealthTests.TakeDamage_ReducesHealthByAmount
  Expected: 70
  But was:  75

1 test(s) failed. Fix the failures above and re-run; only proceed when the run is green.
```

Output when all tests pass:

```
=== Unity test results ===
total=4 passed=4 failed=0 skipped=0

All tests passed. Results XML: /tmp/unity-results-editmode.xml
```

---

## Running locally

```bash
# EditMode
python3 scripts/run_unity_tests.py --project-path . --test-platform EditMode

# PlayMode
python3 scripts/run_unity_tests.py --project-path . --test-platform PlayMode

# Explicit Unity binary (bypass auto-detection)
python3 scripts/run_unity_tests.py \
  --project-path . \
  --test-platform EditMode \
  --unity-bin "/Applications/Unity/Hub/Editor/2022.3.20f1/Unity.app/Contents/MacOS/Unity"

# Via environment variable
UNITY_PATH="/home/you/Unity/Hub/Editor/2022.3.20f1/Editor/Unity" \
  python3 scripts/run_unity_tests.py --project-path . --test-platform EditMode
```

**What gates progress:**

| Gate | Condition |
|---|---|
| Script validates project | `Packages/manifest.json` must exist |
| Unity finds license | Must be activated before `-batchmode` |
| Unity compiles | No compile errors — log output shows them if this gate fails |
| Tests run | Results XML is written |
| All tests pass | Script exits 0; CI step succeeds |

---

## Verification checklist

- [ ] `scripts/run_unity_tests.py` is committed to the repository root.
- [ ] `.github/workflows/unity-tests.yml` is committed.
- [ ] Production code is in `Gameplay.asmdef` (tests reference it by name).
- [ ] `EditModeTests.asmdef` has `"includePlatforms": ["Editor"]`, `"overrideReferences": true`, and `nunit.framework.dll` in `precompiledReferences`.
- [ ] `PlayModeTests.asmdef` has no platform restriction and does **not** reference `UnityEditor.TestRunner`.
- [ ] All tests use Arrange-Act-Assert and NUnit constraint syntax (`Assert.That(x, Is.EqualTo(y))`).
- [ ] PlayMode tests `Object.Destroy` all spawned GameObjects.
- [ ] `UNITY_PATH`, `UNITY_EMAIL`, `UNITY_PASSWORD`, `UNITY_SERIAL` are set as repository secrets.
- [ ] Branch protection rules are configured to require the `test` job to pass before merging.
