# Debugging: Player Falls Through Thin Platforms (FPS-Dependent)

## Phase 1: Reproduce — Establishing the Root Cause First

Before writing a single line of fix code, the Iron Law requires reproducing the bug on demand and stating the root cause as a specific, evidence-backed sentence.

**Your suggestion to "add a thicker collider" is a workaround, not a fix.** It treats the symptom (the collider being "too thin to catch") rather than the cause (why does the physics check miss the collider at all?). Making colliders thicker would mask the bug for some speeds but fail again for faster objects or thinner platforms — and it would not help you understand when or why it breaks.

---

## Root Cause Analysis

The symptom pattern you described matches a textbook tunneling / per-frame collision check failure:

> **"Worse at low FPS, fast objects pass through walls / thin platforms"**
> → *Missing continuous collision detection, or movement applied outside `FixedUpdate`, causing a discrete per-frame sweep that skips over thin geometry when the frame delta is large.*

### Why this happens

Unity's default physics uses **discrete collision detection**. Each physics step, the engine places the rigidbody at its new position and checks for overlaps. It does **not** sweep the path between the old and new position.

On a fast machine (high FPS), each frame moves the player a small distance. On a slow machine (low FPS), each frame moves the player a large distance — sometimes larger than the platform's thickness. The collider literally jumps over the platform between two consecutive frames, so no collision is ever detected.

A thicker collider raises the threshold at which tunneling begins, but the same physics step will eventually tunnel through it at sufficiently low FPS or high speed. The root cause is unchanged.

---

## Phase 2: Reproduction Steps (What to Run)

Because a game engine is not installed in this environment, I am describing exactly what to run and what the "go / no-go" gate is at each step.

### Step 1 — Force Low FPS to Make the Bug Deterministic

In your Unity project, open the scene with the thin platforms and add a temporary script to cap frame rate:

```csharp
// DebugFPSCap.cs  — attach to any GameObject; REMOVE before shipping
using UnityEngine;

public class DebugFPSCap : MonoBehaviour
{
    [SerializeField] private int targetFPS = 10;

    private void Awake()
    {
        Application.targetFrameRate = targetFPS;
        QualitySettings.vSyncCount  = 0;
    }
}
```

**Gate:** At 10 FPS, walk the player into a thin platform from above. The fall-through should now happen on every attempt on every machine.
If it does not happen even at 10 FPS, lower `targetFPS` to 5, or increase the player's fall speed temporarily.

### Step 2 — Confirm the Hypothesis with a Log

Add a log to your player movement script that prints the distance moved per physics step:

```csharp
// Inside FixedUpdate (or wherever you apply velocity/transform)
float distanceThisStep = velocity.magnitude * Time.fixedDeltaTime;
Debug.Log($"[Frame {Time.frameCount}] move distance: {distanceThisStep:F4}  platform thickness: <YOUR_VALUE>");
```

**Gate:** In the log, you should see `distanceThisStep` exceed the platform's collider thickness on the frames where fall-through occurs. This is the evidence-backed confirmation of the root cause.

### Step 3 — Bisect: Is Movement Applied in `Update` or `FixedUpdate`?

If the player uses `transform.position +=` or `rb.MovePosition()` inside `Update` instead of `FixedUpdate`, the physics engine never sees a coherent velocity — it just sees the object teleporting. Check your player controller for:

```csharp
void Update()   // ← BAD for physics movement
{
    transform.position += velocity * Time.deltaTime;
}
```

vs.

```csharp
void FixedUpdate()   // ← CORRECT for physics movement
{
    rb.MovePosition(rb.position + velocity * Time.fixedDeltaTime);
}
```

**Gate:** If movement is in `Update`, moving it to `FixedUpdate` is a required prerequisite to the actual fix below.

---

## Phase 3: Confirmed Root Cause

> **Root cause:** Unity's discrete collision detection skips geometry thinner than the distance the Rigidbody travels in a single physics step. At low FPS the step is larger, making the skip more likely. The fix is to enable Continuous Collision Detection (CCD) on the Rigidbody, which sweeps the motion path rather than checking only the endpoint.

This is a specific, disprove-able statement: "If I switch the Rigidbody's Collision Detection to Continuous, the platform thickness will no longer matter and fall-through will stop."

---

## Phase 4: Fix

### Fix A — Enable Continuous Collision Detection (Primary Fix)

In the Unity Editor:

1. Select the Player GameObject.
2. In the Inspector, find the **Rigidbody** component.
3. Change **Collision Detection** from `Discrete` to **`Continuous`** (or `Continuous Dynamic` if the platform also moves).

Or in code (e.g. in `Awake`):

```csharp
// PlayerPhysicsSetup.cs
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PlayerPhysicsSetup : MonoBehaviour
{
    private void Awake()
    {
        var rb = GetComponent<Rigidbody>();
        // Continuous: player (dynamic) vs static colliders — correct for stationary platforms
        // ContinuousDynamic: player vs other moving rigidbodies as well
        rb.collisionDetectionMode = CollisionDetectionMode.Continuous;
    }
}
```

For **2D physics** (`Rigidbody2D`):

```csharp
var rb2d = GetComponent<Rigidbody2D>();
rb2d.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
```

**Why this is the root-cause fix and not a workaround:** CCD sweeps the entire path of motion between physics steps, so the engine checks whether the collider's path intersects any geometry — it is never possible for the object to "skip over" a collider regardless of frame rate or platform thickness.

### Fix B — Ensure Movement Stays in FixedUpdate (Prerequisite if Needed)

If Step 2 in Phase 2 revealed movement in `Update`, refactor it:

```csharp
// PlayerController.cs — corrected excerpt
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float jumpForce = 8f;

    private Rigidbody _rb;
    private float _horizontalInput;
    private bool  _jumpQueued;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _rb.collisionDetectionMode = CollisionDetectionMode.Continuous;
    }

    // Input is read in Update (correct — Input system is per-render-frame)
    private void Update()
    {
        _horizontalInput = Input.GetAxis("Horizontal");
        if (Input.GetButtonDown("Jump"))
            _jumpQueued = true;
    }

    // Physics is applied in FixedUpdate (correct — physics runs on fixed timestep)
    private void FixedUpdate()
    {
        var vel = _rb.linearVelocity;
        vel.x = _horizontalInput * moveSpeed;

        if (_jumpQueued)
        {
            vel.y = jumpForce;
            _jumpQueued = false;
        }

        _rb.linearVelocity = vel;
    }
}
```

Key points:
- Input is sampled in `Update` because the Input system fires events per render frame.
- Physics velocity is applied in `FixedUpdate` so Unity's physics integrator sees a consistent velocity.
- A `bool _jumpQueued` flag bridges the two loops correctly without dropping inputs.

---

## Verification Checklist

Before closing this bug, confirm ALL of the following:

- [ ] Bug reproduced on demand at forced 10 FPS (Phase 1 complete) before any fix was applied
- [ ] Log confirms `distanceThisStep > platform thickness` on failing frames (evidence-backed root cause)
- [ ] `CollisionDetectionMode.Continuous` set on the player Rigidbody
- [ ] Player movement confirmed to be in `FixedUpdate`, not `Update`
- [ ] Re-run the exact reproduction (10 FPS cap, same thin platform, same fall speed) — fall-through must not occur
- [ ] Remove `DebugFPSCap.cs` and re-run at normal FPS on a slow machine or with `Application.targetFrameRate = -1`
- [ ] Test with all other systems re-enabled (AI, particles, etc.)
- [ ] Frame-rate sensitivity re-checked: test at 10 FPS, 60 FPS, and uncapped
- [ ] No collider resizing was used as part of the fix
- [ ] Temporary debug scripts (`DebugFPSCap.cs`, log lines) removed from the project

---

## What NOT to Do

| Tempting workaround | Why it is wrong |
|---|---|
| Make the collider thicker | Raises the threshold but doesn't close the gap; fails again at lower FPS or higher speed |
| Add `Physics.IgnoreLayerCollision` exceptions | Unrelated to the cause |
| Add a `sleep` / frame delay around the jump | A delay shrinks a race window; it never closes it |
| Clamp the player's fall speed | Hides the evidence; the underlying discrete check is still broken, and a sufficiently fast object will still tunnel |
| Change five things at once and see if it stops | You would not know which change mattered or what the other four broke |

---

## Summary

The bug is **physics tunneling caused by Unity's discrete collision detection mode**. At low FPS, the player Rigidbody travels a large distance per physics step and jumps over geometry thinner than that distance. The fix is to set `CollisionDetectionMode.Continuous` on the player Rigidbody. This is verified by first reproducing the bug deterministically at forced 10 FPS, confirming via logs that the per-step distance exceeds platform thickness, applying the single-line CCD change, and confirming the reproduction no longer fires.
