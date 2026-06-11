# Play Mode Test: PlayerController.Jump() Moves the Player Upward

## What was asked

Add a test that verifies `PlayerController.Jump()` actually makes the player move upward over the next physics frames. `PlayerController` is a `MonoBehaviour` with a `Rigidbody`; calling `Jump()` should apply an upward force.

---

## Why Play Mode (not Edit Mode)?

| Concern | Edit Mode | Play Mode |
|---|---|---|
| MonoBehaviour lifecycle (`Awake`, `Start`) | Not invoked | Invoked normally |
| Physics engine (`Rigidbody`, `AddForce`) | **Not active** | **Active** |
| Multi-frame simulation | Not possible | `yield return new WaitForFixedUpdate()` |

Because the test needs to observe real Rigidbody motion across multiple `FixedUpdate` frames, **Play Mode** is the only correct choice. An Edit Mode test cannot drive the physics engine and would require mocking the entire Rigidbody — that would test the mock, not the real behaviour.

---

## File layout

```
Assets/
  Scripts/
    PlayerController.cs                      ← production component (stand-in)
  Tests/
    PlayMode/
      PlayerJumpPlayModeTest.cs              ← the new tests
      PlayerJumpPlayModeTest.asmdef          ← assembly definition (required by Unity Test Runner)
```

---

## Production component (stand-in)

`Assets/Scripts/PlayerController.cs`

```csharp
using UnityEngine;

/// <summary>
/// Controls the player character, including jumping via physics.
/// Requires a Rigidbody component on the same GameObject.
/// </summary>
[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    [SerializeField] private float jumpForce = 5f;

    private Rigidbody _rb;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
    }

    /// <summary>
    /// Applies an upward impulse to the Rigidbody, causing the player to jump.
    /// </summary>
    public void Jump()
    {
        _rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
    }
}
```

---

## Assembly definition

`Assets/Tests/PlayMode/PlayerJumpPlayModeTest.asmdef`

```json
{
    "name": "PlayerJumpPlayModeTests",
    "rootNamespace": "",
    "references": [
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

The `asmdef` is mandatory: without it the Unity Test Runner cannot discover Play Mode tests. `autoReferenced: false` and `UNITY_INCLUDE_TESTS` ensure it is only compiled when running tests.

---

## Test file

`Assets/Tests/PlayMode/PlayerJumpPlayModeTest.cs`

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

/// <summary>
/// Play Mode tests for PlayerController.Jump().
///
/// Play Mode tests run inside a live Unity scene with the physics engine active,
/// which lets us observe actual Rigidbody motion across multiple FixedUpdate frames.
/// </summary>
public class PlayerJumpPlayModeTest
{
    // How many physics frames to simulate before sampling the result.
    // Five frames is enough for a single impulse to show measurable upward displacement.
    private const int PhysicsFramesToWait = 5;

    private GameObject _playerGO;
    private PlayerController _player;
    private Rigidbody _rb;

    /// <summary>
    /// Builds a minimal scene: a flat floor so the player has something to stand on,
    /// and a player GameObject with the required components.
    /// </summary>
    [UnitySetUp]
    public IEnumerator SetUp()
    {
        // --- Floor ---
        // Without a floor the player would free-fall from (0,0,0) and the
        // y-position before the jump could already be decreasing, making the
        // assertion unreliable.
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = Vector3.zero;

        // --- Player ---
        _playerGO = new GameObject("Player");
        // Position the player slightly above the floor so it is resting on it
        // after a single physics step (Plane's surface is at y = 0).
        _playerGO.transform.position = new Vector3(0f, 0.5f, 0f);

        _rb = _playerGO.AddComponent<Rigidbody>();
        _rb.useGravity = true;
        _rb.constraints = RigidbodyConstraints.FreezeRotation
                         | RigidbodyConstraints.FreezePositionX
                         | RigidbodyConstraints.FreezePositionZ;

        _player = _playerGO.AddComponent<PlayerController>();

        // Let physics settle for one frame so the player is resting on the floor.
        yield return new WaitForFixedUpdate();
    }

    [TearDown]
    public void TearDown()
    {
        // Destroy every object created during the test.
        Object.Destroy(_playerGO);
        GameObject floor = GameObject.Find("Floor");
        if (floor != null)
            Object.Destroy(floor);
    }

    /// <summary>
    /// After calling Jump(), the player's y-position must be strictly greater than
    /// its pre-jump y-position after PhysicsFramesToWait physics frames.
    /// </summary>
    [UnityTest]
    public IEnumerator Jump_MovesPlayerUpward_OverNextPhysicsFrames()
    {
        // Record position before the jump.
        float yBefore = _playerGO.transform.position.y;

        // Act – trigger the jump.
        _player.Jump();

        // Wait for several physics frames so the impulse has time to move the body.
        for (int i = 0; i < PhysicsFramesToWait; i++)
            yield return new WaitForFixedUpdate();

        float yAfter = _playerGO.transform.position.y;

        Assert.Greater(yAfter, yBefore,
            $"Expected player to move upward after Jump(). " +
            $"y before={yBefore:F4}, y after={yAfter:F4}");
    }

    /// <summary>
    /// Immediately after Jump(), the Rigidbody should have a positive upward velocity,
    /// confirming the impulse was applied in the correct direction.
    /// </summary>
    [UnityTest]
    public IEnumerator Jump_GivesRigidbodyPositiveVerticalVelocity()
    {
        _player.Jump();

        // One FixedUpdate is enough: the impulse is applied instantly.
        yield return new WaitForFixedUpdate();

        Assert.Greater(_rb.linearVelocity.y, 0f,
            $"Expected positive upward velocity after Jump(). " +
            $"Actual velocity.y={_rb.linearVelocity.y:F4}");
    }
}
```

---

## Design decisions explained

### `[UnitySetUp]` returns `IEnumerator`

`[UnitySetUp]` (not `[SetUp]`) is used because setup itself needs to `yield` one `WaitForFixedUpdate` to let the physics engine settle the player onto the floor before recording the baseline `y` position. A standard `[SetUp]` cannot `yield`.

### Two tests, not one

| Test | What it verifies |
|---|---|
| `Jump_MovesPlayerUpward_OverNextPhysicsFrames` | The **result** — position has increased after several frames. This is the primary behaviour requirement. |
| `Jump_GivesRigidbodyPositiveVerticalVelocity` | The **mechanism** — the impulse direction is correct. Catches bugs like a negative or horizontal force vector even before displacement is measurable. |

Having both means a regression shows immediately whether the force direction is wrong or whether the magnitude is too small to overcome gravity within the sampled window.

### Floor + `FreezePositionX/Z`

The `Plane` collider keeps the player at a stable `y` before the jump. Without it, the player free-falls during `SetUp` so `yBefore` is already decreasing. Freezing X/Z constrains lateral drift from floating-point physics noise — the test only cares about the Y axis.

### `ForceMode.Impulse`

An impulse applies the full force in a single physics step, which is the standard approach for jump mechanics and makes the test deterministic: there is no ramp-up period to wait for.

### `[TearDown]` not `[UnityTearDown]`

Teardown does not need to `yield`, so the simpler `[TearDown]` attribute is correct. Using `Object.Destroy` (not `DestroyImmediate`) is correct in Play Mode.

---

## How to run (Unity is required)

### From the Unity Editor

1. Open the project in Unity 2021.3 LTS or later (the project targets the `Rigidbody.linearVelocity` API available since Unity 6; for older versions replace `_rb.linearVelocity` with `_rb.velocity`).
2. Open **Window → General → Test Runner**.
3. Select the **PlayMode** tab.
4. Click **Run All** (or right-click `PlayerJumpPlayModeTest` → **Run Selected**).

Expected output:
```
PlayerJumpPlayModeTest
  ✓ Jump_MovesPlayerUpward_OverNextPhysicsFrames (0.XXs)
  ✓ Jump_GivesRigidbodyPositiveVerticalVelocity (0.XXs)
```

### From the command line (CI)

```bash
/path/to/Unity \
  -batchmode \
  -runTests \
  -testPlatform PlayMode \
  -projectPath /path/to/project \
  -testResults TestResults-PlayMode.xml \
  -logFile unity-playmode.log
```

**Gate**: the command exits with code `0` on success, non-zero on any test failure. In CI, assert `$? -eq 0` after the command.

### Compatibility note for Unity versions before 6

Unity renamed `Rigidbody.velocity` to `Rigidbody.linearVelocity` in Unity 6. If you are on Unity 2022 or 2021, change the reference in the second test:

```csharp
// Unity 2021 / 2022 / 2023
Assert.Greater(_rb.velocity.y, 0f, ...);

// Unity 6+
Assert.Greater(_rb.linearVelocity.y, 0f, ...);
```

Everything else in the test is version-agnostic.
