# DamageCalculator – EditMode Tests

## What was produced

A faithful stand-in of the Unity project was created under `/tmp/eval-work/dmg-b/` with the following layout:

```
Assets/
  _Project/
    Scripts/
      Gameplay/
        DamageCalculator.cs          ← implementation (stand-in)
        Gameplay.asmdef              ← assembly definition
    Tests/
      EditMode/
        DamageCalculatorTests.cs     ← NUnit test file (18 tests)
        Project.Gameplay.Tests.asmdef
```

---

## DamageCalculator.cs (stand-in implementation)

The class is placed in namespace `Project.Gameplay`.  
The single public method is:

```csharp
public float Calculate(float attackPower, float defense, float criticalMultiplier = 1f)
```

**Logic:**

1. Guard all inputs (throws `ArgumentOutOfRangeException` for negative attack/defense, or `criticalMultiplier < 1`).
2. `raw = attackPower - defense`
3. `clamped = Math.Max(0f, raw)` — damage is never negative.
4. `return clamped * criticalMultiplier`

---

## Assembly definition files

### `Gameplay.asmdef`

```json
{
    "name": "Project.Gameplay",
    "rootNamespace": "Project.Gameplay",
    "references": [],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": [],
    "versionDefines": [],
    "noEngineReferences": false
}
```

### `Project.Gameplay.Tests.asmdef`

```json
{
    "name": "Project.Gameplay.Tests",
    "rootNamespace": "Project.Gameplay.Tests",
    "references": [
        "Project.Gameplay",
        "UnityEngine.TestRunner",
        "UnityEditor.TestRunner"
    ],
    "includePlatforms": ["Editor"],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": true,
    "precompiledReferences": ["nunit.framework.dll"],
    "autoReferenced": false,
    "defineConstraints": ["UNITY_INCLUDE_TESTS"],
    "versionDefines": [],
    "noEngineReferences": false
}
```

Key points:
- `includePlatforms: ["Editor"]` — restricts to EditMode only, so PlayMode runner never picks these up.
- `autoReferenced: false` + `UNITY_INCLUDE_TESTS` guard — test assembly is stripped from non-test builds.
- `overrideReferences: true` + explicit `nunit.framework.dll` — ensures NUnit is linked in older Unity versions where it isn't auto-linked.

---

## DamageCalculatorTests.cs (full file)

```csharp
using System;
using NUnit.Framework;
using Project.Gameplay;

namespace Project.Gameplay.Tests
{
    /// <summary>
    /// EditMode tests for DamageCalculator.
    /// No MonoBehaviour or scene loading required — pure C# logic.
    /// Run via: Unity Test Runner → EditMode, or CLI below.
    ///
    /// CLI (batch mode, no display):
    ///   Unity.exe -batchmode -runTests -testPlatform EditMode \
    ///             -projectPath /tmp/eval-work/dmg-b \
    ///             -testResults /tmp/eval-work/dmg-b/TestResults.xml \
    ///             -logFile /tmp/eval-work/dmg-b/unity.log
    ///
    /// Progress gate: exit code 0 + TestResults.xml shows all tests passed.
    /// </summary>
    [TestFixture]
    public class DamageCalculatorTests
    {
        private DamageCalculator _calc;

        [SetUp]
        public void SetUp()
        {
            _calc = new DamageCalculator();
        }

        // ------------------------------------------------------------------ //
        // Happy-path tests
        // ------------------------------------------------------------------ //

        [Test]
        [Description("Standard hit: attack exceeds defense, no crit.")]
        public void Calculate_AttackExceedsDefense_ReturnsPositiveDamage()
        {
            float result = _calc.Calculate(attackPower: 100f, defense: 40f, criticalMultiplier: 1f);

            Assert.That(result, Is.EqualTo(60f).Within(0.001f));
        }

        [Test]
        [Description("Defense equals attack — result is exactly 0, not negative.")]
        public void Calculate_DefenseEqualsAttack_ReturnsZero()
        {
            float result = _calc.Calculate(attackPower: 50f, defense: 50f, criticalMultiplier: 1f);

            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        [Description("Defense higher than attack — result clamped to 0, never negative.")]
        public void Calculate_DefenseExceedsAttack_ReturnsZero()
        {
            float result = _calc.Calculate(attackPower: 30f, defense: 80f, criticalMultiplier: 1f);

            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        [Description("Critical multiplier scales damage correctly.")]
        public void Calculate_CriticalMultiplier_ScalesDamage()
        {
            float result = _calc.Calculate(attackPower: 100f, defense: 40f, criticalMultiplier: 2f);

            // (100 - 40) * 2 = 120
            Assert.That(result, Is.EqualTo(120f).Within(0.001f));
        }

        [Test]
        [Description("Fractional critical multiplier (1.5x) produces expected result.")]
        public void Calculate_FractionalCriticalMultiplier_ReturnsCorrectDamage()
        {
            float result = _calc.Calculate(attackPower: 80f, defense: 20f, criticalMultiplier: 1.5f);

            // (80 - 20) * 1.5 = 90
            Assert.That(result, Is.EqualTo(90f).Within(0.001f));
        }

        [Test]
        [Description("Zero attack power with zero defense returns 0.")]
        public void Calculate_ZeroAttackAndZeroDefense_ReturnsZero()
        {
            float result = _calc.Calculate(attackPower: 0f, defense: 0f, criticalMultiplier: 1f);

            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        [Description("Zero attack power with any defense returns 0.")]
        public void Calculate_ZeroAttackNonZeroDefense_ReturnsZero()
        {
            float result = _calc.Calculate(attackPower: 0f, defense: 100f, criticalMultiplier: 3f);

            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        [Description("Critical multiplier applied only to non-negative pre-clamp damage.")]
        public void Calculate_CritWithDefenseExceedingAttack_ReturnsZero()
        {
            // Even a large crit cannot amplify a negative raw result — clamp wins first.
            float result = _calc.Calculate(attackPower: 10f, defense: 50f, criticalMultiplier: 10f);

            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        // ------------------------------------------------------------------ //
        // Parameterised boundary tests
        // ------------------------------------------------------------------ //

        [TestCase(0f,   0f,  1f,   0f,   TestName = "Boundary_AllZero")]
        [TestCase(1f,   0f,  1f,   1f,   TestName = "Boundary_MinimalAttack")]
        [TestCase(0f,   1f,  1f,   0f,   TestName = "Boundary_MinimalDefense")]
        [TestCase(100f, 99f, 1f,   1f,   TestName = "Boundary_AttackOneMoreThanDefense")]
        [TestCase(100f, 0f,  10f,  1000f,TestName = "Boundary_LargeCrit")]
        [Description("Parameterised set of boundary/edge values.")]
        public void Calculate_BoundaryValues_ReturnExpectedDamage(
            float attack, float defense, float crit, float expected)
        {
            float result = _calc.Calculate(attack, defense, crit);

            Assert.That(result, Is.EqualTo(expected).Within(0.001f));
        }

        // ------------------------------------------------------------------ //
        // Guard / validation tests
        // ------------------------------------------------------------------ //

        [Test]
        [Description("Negative attack power throws ArgumentOutOfRangeException.")]
        public void Calculate_NegativeAttackPower_ThrowsArgumentOutOfRange()
        {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: -1f, defense: 0f, criticalMultiplier: 1f));
        }

        [Test]
        [Description("Negative defense throws ArgumentOutOfRangeException.")]
        public void Calculate_NegativeDefense_ThrowsArgumentOutOfRange()
        {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: 10f, defense: -5f, criticalMultiplier: 1f));
        }

        [Test]
        [Description("Critical multiplier below 1 (e.g. 0.5) throws ArgumentOutOfRangeException.")]
        public void Calculate_CriticalMultiplierBelowOne_ThrowsArgumentOutOfRange()
        {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: 10f, defense: 0f, criticalMultiplier: 0.5f));
        }

        [Test]
        [Description("Critical multiplier of exactly 0 throws ArgumentOutOfRangeException.")]
        public void Calculate_ZeroCriticalMultiplier_ThrowsArgumentOutOfRange()
        {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: 10f, defense: 0f, criticalMultiplier: 0f));
        }

        [Test]
        [Description("Verify exception parameter name for attackPower guard.")]
        public void Calculate_NegativeAttackPower_ExceptionNamesCorrectParameter()
        {
            var ex = Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: -10f, defense: 0f, criticalMultiplier: 1f));

            Assert.That(ex.ParamName, Is.EqualTo("attackPower"));
        }

        [Test]
        [Description("Verify exception parameter name for defense guard.")]
        public void Calculate_NegativeDefense_ExceptionNamesCorrectParameter()
        {
            var ex = Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: 10f, defense: -1f, criticalMultiplier: 1f));

            Assert.That(ex.ParamName, Is.EqualTo("defense"));
        }

        [Test]
        [Description("Verify exception parameter name for criticalMultiplier guard.")]
        public void Calculate_LowCritMultiplier_ExceptionNamesCorrectParameter()
        {
            var ex = Assert.Throws<ArgumentOutOfRangeException>(
                () => _calc.Calculate(attackPower: 10f, defense: 0f, criticalMultiplier: 0.9f));

            Assert.That(ex.ParamName, Is.EqualTo("criticalMultiplier"));
        }

        // ------------------------------------------------------------------ //
        // Default-parameter tests
        // ------------------------------------------------------------------ //

        [Test]
        [Description("Calling without criticalMultiplier defaults to 1 (no crit).")]
        public void Calculate_DefaultCritMultiplier_TreatedAsOne()
        {
            float withDefault  = _calc.Calculate(attackPower: 60f, defense: 20f);
            float withExplicit = _calc.Calculate(attackPower: 60f, defense: 20f, criticalMultiplier: 1f);

            Assert.That(withDefault, Is.EqualTo(withExplicit).Within(0.001f));
        }
    }
}
```

---

## Test coverage summary (18 tests)

| Category | Tests | What is covered |
|---|---|---|
| Happy-path | 8 | attack > defense (no crit), attack = defense, attack < defense (clamp), crit ×2, crit ×1.5, zero attack with zero defense, zero attack with nonzero defense, crit cannot amplify clamped-to-zero result |
| Parameterised boundary | 5 (1 method × 5 cases) | all-zero, minimal attack, minimal defense, attack one above defense, large crit multiplier |
| Guard / exception | 4 | negative attack, negative defense, crit < 1, crit = 0 |
| Exception param name | 3 | `ParamName` on each guard confirms the right argument is named |
| Default parameter | 1 | omitting `criticalMultiplier` behaves identically to passing `1f` |

---

## How to run (Unity not installed in this environment)

```bash
# Replace <UnityVersion> with the version in your ProjectSettings/ProjectVersion.txt
/Applications/Unity/Hub/Editor/<UnityVersion>/Unity.app/Contents/MacOS/Unity \
  -batchmode \
  -runTests \
  -testPlatform EditMode \
  -projectPath /tmp/eval-work/dmg-b \
  -testResults /tmp/eval-work/dmg-b/TestResults.xml \
  -logFile /tmp/eval-work/dmg-b/unity.log \
  -quit
```

**Progress gate:** The command must exit with code `0`. Open `TestResults.xml` and confirm every `<test-case>` element carries `result="Passed"`. Any failure there is a regression that must be fixed before shipping.

When copying these files into your real project:

1. Drop `DamageCalculatorTests.cs` and `Project.Gameplay.Tests.asmdef` into `Assets/_Project/Tests/EditMode/`.
2. Open Unity → Window → General → Test Runner → EditMode tab.
3. Click **Run All** — all 18 tests should be green.

If your real `DamageCalculator` does not yet throw `ArgumentOutOfRangeException` on bad inputs, either add those guards or delete the four guard tests and the three param-name tests and rely solely on the happy-path and boundary tests.
