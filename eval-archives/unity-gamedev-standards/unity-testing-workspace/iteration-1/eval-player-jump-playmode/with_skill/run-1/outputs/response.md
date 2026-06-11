# Adding a PlayMode Jump Test for PlayerController

## Decision: PlayMode test with `[UnityTest]`

`PlayerController` is a `MonoBehaviour` that drives a `Rigidbody` — its
behaviour spans physics frames and depends on `Awake()` initialisation. Per
the decision tree in the unity-testing skill, **anything that requires
MonoBehaviour lifecycle or physics frames goes in a PlayMode test** written as
a `[UnityTest]` coroutine.

---

## Files created / modified

### 1. Production stand-in (already assumed to exist in your project)

`Assets/_Project/Scripts/Gameplay/PlayerController.cs`

```csharp
using UnityEngine;

namespace Gameplay
{
    [RequireComponent(typeof(Rigidbody))]
    public class PlayerController : MonoBehaviour
    {
        [SerializeField] private float jumpForce = 5f;

        private Rigidbody _rb;

        private void Awake()
        {
            _rb = GetComponent<Rigidbody>();
        }

        public void Jump()
        {
            _rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
        }
    }
}
```

`Assets/_Project/Scripts/Gameplay/Gameplay.asmdef`

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

> If `Gameplay.asmdef` does not yet exist, add it — the test assembly must
> reference a named production assembly; it cannot reference code that lives
> in the implicit default assembly.

---

### 2. New: PlayMode test assembly definition

`Assets/_Project/Tests/PlayMode/PlayModeTests.asmdef`

```json
{
    "name": "PlayModeTests",
    "rootNamespace": "Tests.PlayMode",
    "references": [
        "Gameplay",
        "UnityEngine.TestRunner",
        "UnityEditor.TestRunner"
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
    "versionDefines": [],
    "noEngineReferences": false
}
```

Key points:
- `overrideReferences: true` + `precompiledReferences: ["nunit.framework.dll"]`
  — required so NUnit attributes resolve.
- No `includePlatforms` restriction (PlayMode tests run on-device or in the
  editor in Play mode, not Editor-only).
- References `Gameplay` by name so the test can see `PlayerController`.

---

### 3. New: the test itself

`Assets/_Project/Tests/PlayMode/PlayerControllerJumpTests.cs`

```csharp
using System.Collections;
using Gameplay;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Tests.PlayMode
{
    public class PlayerControllerJumpTests
    {
        /// <summary>
        /// Verifies that calling Jump() on a PlayerController causes the
        /// attached Rigidbody to move upward over subsequent physics frames.
        /// </summary>
        [UnityTest]
        public IEnumerator Jump_MovesPlayerUpward_OverPhysicsFrames()
        {
            // Arrange
            var go = new GameObject("Player");
            var rb = go.AddComponent<Rigidbody>();
            var player = go.AddComponent<PlayerController>();

            // Disable gravity so the only upward force is from Jump()
            rb.useGravity = false;

            // Wait one frame so Awake() runs and the component is initialised
            yield return null;

            float startY = go.transform.position.y;

            // Act
            player.Jump();

            // Wait for two fixed-update physics steps so the impulse is applied
            yield return new WaitForFixedUpdate();
            yield return new WaitForFixedUpdate();

            // Assert
            Assert.That(
                go.transform.position.y,
                Is.GreaterThan(startY),
                "PlayerController.Jump() should move the Rigidbody upward.");

            // Cleanup
            Object.Destroy(go);
        }
    }
}
```

#### Design notes

| Decision | Reason |
|---|---|
| `[UnityTest]` / `IEnumerator` | Physics impulse is applied across fixed-update steps; a synchronous `[Test]` sees the object before any frame has advanced. |
| `rb.useGravity = false` | Isolates the upward impulse. With gravity on, a very small `jumpForce` could be beaten by gravity in two ticks, making the assertion flaky. Disabling gravity means the only velocity the Rigidbody can have after `Jump()` is upward. |
| `yield return null` before recording `startY` | Ensures `Awake()` has run and `_rb` is assigned before `Jump()` is called. |
| Two `WaitForFixedUpdate` yields | One tick is enough for `AddForce(ForceMode.Impulse)` to affect velocity; two ticks guarantees the transform has been integrated. |
| `Object.Destroy(go)` at the end | Keeps tests independent — the spawned GameObject is removed before the next test runs. |
| `Is.GreaterThan(startY)` with a message | NUnit constraint syntax; the message surfaces clearly on failure without having to read a stack trace. |

---

## How to run

```bash
# From the repo root (or any directory — the script resolves paths)
python3 scripts/run_unity_tests.py \
    --project-path /path/to/your/unity/project \
    --test-platform PlayMode
```

What the script does internally:

1. Reads `ProjectSettings/ProjectVersion.txt` to find `m_EditorVersion`
   (e.g. `2022.3.20f1`).
2. Locates the Unity binary under the Unity Hub editor install directory for
   that version.
3. Runs:
   ```
   <Unity> -batchmode \
           -projectPath /path/to/your/unity/project \
           -runTests \
           -testPlatform PlayMode \
           -testResults /tmp/results-playmode.xml \
           -logFile -
   ```
4. Parses the NUnit XML (`<test-run result="..." failed="...">`) and prints a
   summary of any failures.

**Progress gate**: the run is only considered successful when the script
reports `0 failed`. If Unity exits with compile errors, the log (streamed to
stdout via `-logFile -`) will contain `error CS…` lines — fix those first,
then re-run.

---

## Verification checklist

- [x] Test lives under `PlayModeTests.asmdef` which references `Gameplay` and
      `nunit.framework.dll`.
- [x] PlayMode chosen because the behavior spans physics frames and requires
      `MonoBehaviour` lifecycle (`Awake`).
- [x] Test is Arrange-Act-Assert with a descriptive name
      (`Jump_MovesPlayerUpward_OverPhysicsFrames`) and NUnit constraint assert.
- [ ] Full suite executed via batchmode — **run the command above and confirm
      0 failures before closing this task**.
- [x] No test skipped, ignored, or deleted.
