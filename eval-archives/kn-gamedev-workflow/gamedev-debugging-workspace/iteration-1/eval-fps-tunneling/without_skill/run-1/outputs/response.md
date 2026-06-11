# Fixing "Fall-Through Platforms" in Unity (Tunneling Bug)

## Root Cause — Not a Collider Thickness Problem

The symptom (only reproducible on slower machines) is the canonical sign of **physics tunneling** caused by **Discrete collision detection** on the player's `Rigidbody2D`.

### What actually happens

Unity's physics runs on a fixed timestep (`Time.fixedDeltaTime`, default 0.02 s = 50 Hz).
Between two consecutive physics frames the player's position jumps by:

```
Δy = velocity_y × fixedDeltaTime
```

On a fast machine, the game loop keeps up with the fixed timestep, so Δy is small.
On a slow machine (or during a frame spike), Unity may run **multiple fixed-update steps
in a single rendered frame**, but each individual step still moves the player by the
same Δy. If Δy > platform thickness, the player's collider is on one side of the platform
at frame N and on the other side at frame N+1 — the physics engine never saw a collision.

### Why "thicker collider" is a workaround, not a fix

Making the collider taller hides the symptom on mild hardware differences, but the
fundamental problem remains: at a high enough falling speed (longer drop, or higher gravity)
or a severe enough frame spike, tunneling will happen again. The root problem is that
**Discrete mode only checks the collider's position, not the swept path**.

---

## The Correct Fix: Enable Continuous Collision Detection

### Step 1 — Inspector change (most important)

1. Select the **Player** GameObject.
2. In the **Rigidbody2D** component, change **Collision Detection** from `Discrete` to **`Continuous`**.

`Continuous` mode sweeps a shape along the path of motion between physics steps,
so no matter how fast the player is falling or how thin the platform is, the collision
is detected correctly.

> **Note on performance:** `Continuous` is slightly more expensive than `Discrete`.
> For a single player character the overhead is negligible; only avoid it on hundreds
> of simultaneous dynamic bodies.

### Step 2 — Apply the PlayerMovement script

The script below replaces (or refactors) your existing movement code. Key differences
from a typical starter script:

| Change | Reason |
|--------|--------|
| Awake() asserts `CollisionDetectionMode2D.Continuous` | Catches accidental resets (e.g. prefab override) |
| `OverlapBox` ground check instead of single raycast | Reliable edge detection; prevents missed jumps |
| Clamp vertical velocity to 0 before jump impulse | Prevents "weak jump" when already falling |

```csharp
// File: Assets/Scripts/PlayerMovement.cs
using UnityEngine;

[RequireComponent(typeof(Rigidbody2D))]
public class PlayerMovement : MonoBehaviour
{
    [Header("Movement")]
    public float moveSpeed = 8f;

    [Header("Jump")]
    public float jumpForce = 16f;

    [Header("Ground Detection")]
    public LayerMask groundLayer;
    public Vector2 groundCheckSize   = new Vector2(0.45f, 0.05f);
    public Vector2 groundCheckOffset = new Vector2(0f, -0.51f);

    private Rigidbody2D _rb;
    private bool _isGrounded;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody2D>();

        if (_rb.collisionDetectionMode != CollisionDetectionMode2D.Continuous)
        {
            Debug.LogWarning(
                "[PlayerMovement] Rigidbody2D is not Continuous — forcing it now. " +
                "Please fix this in the Inspector.");
            _rb.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
        }
    }

    private void Update()
    {
        CheckGround();
        HandleJump();
        HandleHorizontalMovement();
    }

    private void CheckGround()
    {
        Vector2 checkPos = (Vector2)transform.position + groundCheckOffset;
        _isGrounded = Physics2D.OverlapBox(checkPos, groundCheckSize, 0f, groundLayer);
    }

    private void HandleJump()
    {
        if (_isGrounded && Input.GetButtonDown("Jump"))
        {
            _rb.linearVelocity = new Vector2(_rb.linearVelocity.x, 0f);
            _rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
        }
    }

    private void HandleHorizontalMovement()
    {
        float horizontal = Input.GetAxisRaw("Horizontal");
        _rb.linearVelocity = new Vector2(horizontal * moveSpeed, _rb.linearVelocity.y);
    }

#if UNITY_EDITOR
    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.green;
        Vector2 pos = (Vector2)transform.position + groundCheckOffset;
        Gizmos.DrawWireCube(pos, groundCheckSize * 2f);
    }
#endif
}
```

### Step 3 (Optional but Recommended) — Cap maximum fall speed

Even with Continuous mode, extremely high speeds can stress the swept-shape solver.
Add a terminal velocity clamp in `FixedUpdate`:

```csharp
[Header("Physics")]
public float maxFallSpeed = 30f; // world units/sec

private void FixedUpdate()
{
    if (_rb.linearVelocity.y < -maxFallSpeed)
        _rb.linearVelocity = new Vector2(_rb.linearVelocity.x, -maxFallSpeed);
}
```

### Step 4 (Optional) — Minimum safe platform thickness formula

If you want to know the theoretical minimum safe thickness for Discrete mode (as a backup):

```
min_thickness > |velocity_y_max| × Time.fixedDeltaTime
             > 30 × 0.02
             > 0.6 world units
```

That is quite thick for a thin platform. The Continuous solution removes this constraint
entirely.

---

## Validation Helper Script

Attach this to any platform to audit its setup from the context menu
(**right-click the component → Validate Platform Setup**):

```csharp
// File: Assets/Scripts/Editor/PlatformSetupValidator.cs
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

public class PlatformSetupValidator : MonoBehaviour
{
    public float minSafeThickness = 0.2f;

#if UNITY_EDITOR
    [ContextMenu("Validate Platform Setup")]
    public void Validate()
    {
        bool ok = true;
        var col2d = GetComponent<Collider2D>();
        if (col2d == null)
        {
            Debug.LogError($"[PlatformValidator] {name}: No Collider2D found.", this);
            return;
        }

        if (col2d.isTrigger)
        {
            Debug.LogError($"[PlatformValidator] {name}: isTrigger is ON — player will fall through!", this);
            ok = false;
        }

        if (col2d is BoxCollider2D box)
        {
            float worldHeight = box.size.y * transform.lossyScale.y;
            if (worldHeight < minSafeThickness)
            {
                Debug.LogWarning(
                    $"[PlatformValidator] {name}: height {worldHeight:F3} u < {minSafeThickness} u threshold.", this);
                ok = false;
            }
        }

        if (ok) Debug.Log($"[PlatformValidator] {name}: All checks passed.", this);
    }
#endif
}
```

---

## Summary of Changes

| What | Where | Why |
|------|-------|-----|
| Set **Collision Detection = Continuous** | Player Rigidbody2D (Inspector) | Sweeps the shape between frames — eliminates tunneling regardless of frame rate |
| `Awake()` assertion | `PlayerMovement.cs` | Catches accidental Inspector resets before they reach players |
| `OverlapBox` ground check | `PlayerMovement.cs` | More reliable than a point-raycast at platform edges |
| Terminal velocity cap | `FixedUpdate()` | Reduces continuous-mode solver cost; also improves game feel |
| `PlatformSetupValidator` | Editor utility | Audits each platform collider for common misconfigurations |

The thicker collider suggestion would have reduced the *frequency* of the bug on your dev machine
but would not have fixed it — a large enough frame spike or a fast enough fall would still
tunnel through. The correct fix is Continuous collision detection, which has no thickness
constraint.

---

## What to Run / Test

Since Unity is not installed in this environment, the C# files are provided ready to drop in.
To verify the fix:

1. Open your Unity project.
2. Copy `PlayerMovement.cs` to `Assets/Scripts/`.
3. Select the Player prefab → Rigidbody2D → set **Collision Detection** to **Continuous**.
4. Enter Play mode and use **Window → Analysis → Physics Debugger** to visualise swept shapes.
5. To simulate a slow machine: in **Edit → Project Settings → Time**, temporarily raise
   `Fixed Timestep` to `0.05` (20 Hz) and confirm the player still lands correctly on thin
   platforms at max fall speed.
6. Revert the timestep before shipping.
