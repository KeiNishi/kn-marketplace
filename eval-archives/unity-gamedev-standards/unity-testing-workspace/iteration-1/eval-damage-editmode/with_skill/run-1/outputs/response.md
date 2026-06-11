# DamageCalculator — EditMode Tests

## Decision: EditMode

`DamageCalculator` is a **pure C# static class** with no MonoBehaviour,
no UnityEngine lifecycle, and no scene dependency. Per the unity-testing
skill's decision tree:

> Pure C# logic (damage formulas, inventory rules, …, plain classes with
> no UnityEngine lifecycle)? → **EditMode tests**.

EditMode tests are the correct choice. They run without entering Play mode
and are the fastest possible feedback loop.

---

## File layout

```
Assets/_Project/
  Scripts/
    Gameplay/
      DamageCalculator.cs       ← production class (already exists)
      Gameplay.asmdef           ← production assembly
  Tests/
    EditMode/
      EditModeTests.asmdef      ← test assembly (Editor-only, references Gameplay)
      DamageCalculatorTests.cs  ← the tests written below
```

---

## 1. Production stand-in: `DamageCalculator.cs`

The task describes a class that takes **attack power**, **defense**, and a
**critical multiplier**. A faithful implementation (add if the file is
missing or differs):

```csharp
// Assets/_Project/Scripts/Gameplay/DamageCalculator.cs
using System;

namespace Gameplay
{
    public static class DamageCalculator
    {
        /// <param name="attackPower">Raw attack power (>= 0).</param>
        /// <param name="defense">Damage reduction of the target (>= 0).</param>
        /// <param name="criticalMultiplier">
        ///   Multiplier applied after defense reduction (>= 1.0).
        /// </param>
        /// <returns>Final damage, clamped to a minimum of 0.</returns>
        public static float Calculate(float attackPower, float defense, float criticalMultiplier)
        {
            if (attackPower < 0f)
                throw new ArgumentOutOfRangeException(nameof(attackPower),
                    "Attack power must be >= 0.");
            if (defense < 0f)
                throw new ArgumentOutOfRangeException(nameof(defense),
                    "Defense must be >= 0.");
            if (criticalMultiplier < 1f)
                throw new ArgumentOutOfRangeException(nameof(criticalMultiplier),
                    "Critical multiplier must be >= 1.");

            float baseDamage = attackPower - defense;
            float finalDamage = baseDamage * criticalMultiplier;
            return MathF.Max(0f, finalDamage);
        }
    }
}
```

---

## 2. Assembly definition: `Gameplay.asmdef`

```json
{
    "name": "Gameplay",
    "rootNamespace": "Gameplay",
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

---

## 3. Test assembly definition: `EditModeTests.asmdef`

```json
{
    "name": "EditModeTests",
    "rootNamespace": "Tests.EditMode",
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
    "versionDefines": [],
    "noEngineReferences": false
}
```

Key points:
- `"includePlatforms": ["Editor"]` — EditMode tests only compile in the Editor.
- `"overrideReferences": true` + `"precompiledReferences": ["nunit.framework.dll"]` — required for NUnit.
- `references` includes `Gameplay` so the test file can see `DamageCalculator`.

---

## 4. Tests: `DamageCalculatorTests.cs`

```csharp
// Assets/_Project/Tests/EditMode/DamageCalculatorTests.cs
using NUnit.Framework;
using Gameplay;

namespace Tests.EditMode
{
    /// <summary>
    /// EditMode tests for <see cref="DamageCalculator"/>.
    /// Pure C# logic class — no MonoBehaviour, no scene, no frames required.
    /// </summary>
    public class DamageCalculatorTests
    {
        // ------------------------------------------------------------------
        // Normal hit: damage = (attackPower - defense) * criticalMultiplier
        // ------------------------------------------------------------------

        [Test]
        public void Calculate_ReturnsCorrectDamage_WhenAttackExceedsDefense()
        {
            // Arrange
            float attack = 50f;
            float defense = 20f;
            float critMultiplier = 1f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(30f).Within(0.001f));
        }

        [Test]
        public void Calculate_ReturnsZero_WhenDefenseEqualsAttack()
        {
            // Arrange
            float attack = 40f;
            float defense = 40f;
            float critMultiplier = 1f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        public void Calculate_ReturnsZero_WhenDefenseExceedsAttack()
        {
            // Arrange: defense > attack => base damage would be negative
            float attack = 10f;
            float defense = 50f;
            float critMultiplier = 1f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert: clamped to 0, never negative
            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        // ------------------------------------------------------------------
        // Critical hit scaling
        // ------------------------------------------------------------------

        [Test]
        public void Calculate_ScalesDamageByCriticalMultiplier_WhenCriticalHit()
        {
            // Arrange
            float attack = 100f;
            float defense = 0f;
            float critMultiplier = 2f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert: 100 * 2 = 200
            Assert.That(result, Is.EqualTo(200f).Within(0.001f));
        }

        [Test]
        public void Calculate_AppliesMultiplierAfterDefenseReduction()
        {
            // Arrange: base damage = 80 - 20 = 60; critical doubles it -> 120
            float attack = 80f;
            float defense = 20f;
            float critMultiplier = 2f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(120f).Within(0.001f));
        }

        [Test]
        public void Calculate_ReturnsZero_WhenHighDefenseAndCriticalHit()
        {
            // Arrange: base damage < 0 even with crit multiplier; should still clamp to 0
            float attack = 10f;
            float defense = 100f;
            float critMultiplier = 3f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        // ------------------------------------------------------------------
        // Zero / boundary inputs
        // ------------------------------------------------------------------

        [Test]
        public void Calculate_ReturnsZero_WhenAttackIsZero()
        {
            // Arrange
            float attack = 0f;
            float defense = 0f;
            float critMultiplier = 1f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        public void Calculate_ReturnsAttackValue_WhenDefenseIsZero()
        {
            // Arrange
            float attack = 75f;
            float defense = 0f;
            float critMultiplier = 1f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(75f).Within(0.001f));
        }

        // ------------------------------------------------------------------
        // Fractional / floating-point inputs
        // ------------------------------------------------------------------

        [Test]
        public void Calculate_HandlesFloatingPointValues()
        {
            // Arrange: (10.5 - 3.5) * 1.5 = 7 * 1.5 = 10.5
            float attack = 10.5f;
            float defense = 3.5f;
            float critMultiplier = 1.5f;

            // Act
            float result = DamageCalculator.Calculate(attack, defense, critMultiplier);

            // Assert
            Assert.That(result, Is.EqualTo(10.5f).Within(0.001f));
        }

        // ------------------------------------------------------------------
        // Guard-clause: invalid arguments
        // ------------------------------------------------------------------

        [Test]
        public void Calculate_ThrowsArgumentOutOfRangeException_WhenAttackIsNegative()
        {
            Assert.That(
                () => DamageCalculator.Calculate(-1f, 0f, 1f),
                Throws.TypeOf<System.ArgumentOutOfRangeException>());
        }

        [Test]
        public void Calculate_ThrowsArgumentOutOfRangeException_WhenDefenseIsNegative()
        {
            Assert.That(
                () => DamageCalculator.Calculate(50f, -5f, 1f),
                Throws.TypeOf<System.ArgumentOutOfRangeException>());
        }

        [Test]
        public void Calculate_ThrowsArgumentOutOfRangeException_WhenCriticalMultiplierBelowOne()
        {
            Assert.That(
                () => DamageCalculator.Calculate(50f, 0f, 0.5f),
                Throws.TypeOf<System.ArgumentOutOfRangeException>());
        }
    }
}
```

### What each group covers

| Group | Tests | What is verified |
|---|---|---|
| Normal hit | `WhenAttackExceedsDefense`, `WhenDefenseEqualsAttack`, `WhenDefenseExceedsAttack` | Base formula and zero-clamp |
| Critical hit scaling | `WhenCriticalHit`, `AppliesMultiplierAfterDefenseReduction`, `WhenHighDefenseAndCriticalHit` | Multiplier applies after defense; clamp still works with crit |
| Zero/boundary | `WhenAttackIsZero`, `WhenDefenseIsZero` | Edge values produce correct results |
| Floating point | `HandlesFloatingPointValues` | Non-integer inputs are handled correctly |
| Guard clauses | Three `Throws` tests | Invalid inputs are rejected with `ArgumentOutOfRangeException` |

Total: **11 tests**, all `[Test]` (synchronous), all Arrange-Act-Assert,
all using NUnit constraint syntax (`Assert.That`, `Is.EqualTo`, `Throws.TypeOf`).

---

## 5. Running the tests

With Unity installed, run from the repo root:

```bash
python3 scripts/run_unity_tests.py \
    --project-path /path/to/your-unity-project \
    --test-platform EditMode
```

The script:
1. Reads `ProjectSettings/ProjectVersion.txt` to locate the matching Unity
   binary under `~/Unity/Hub/Editor/<version>/Editor/Unity`.
2. Runs:
   ```
   Unity -batchmode -projectPath <path> -runTests -testPlatform EditMode \
         -testResults /tmp/unity_test_results_EditMode.xml -logFile -
   ```
3. Parses the NUnit XML and prints a pass/fail summary.
4. Exits non-zero if any test failed.

**Gate**: only proceed (e.g. merge, continue development) when the run
reports `failed=0`. If Unity exits without writing a results file, scroll
up through the streamed editor log for compile errors and fix them first.

---

## Verification checklist

- [x] Tests live under `Assets/_Project/Tests/EditMode/` with a proper
      `EditModeTests.asmdef` that references `Gameplay` and `nunit.framework.dll`.
- [x] `"includePlatforms": ["Editor"]` is set — EditMode only.
- [x] `DamageCalculator` is pure C# with no UnityEngine lifecycle — EditMode
      is the correct choice per the decision tree.
- [x] All 11 tests use Arrange-Act-Assert with descriptive
      `Method_ExpectedBehavior_WhenCondition` names and NUnit constraint asserts.
- [ ] Full batchmode run must be executed once Unity is available and
      confirmed green (0 failures) before declaring done. Unity is not
      installed in this environment; the command above is exact.
- [x] No test is skipped, ignored, or deleted.
