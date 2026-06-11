# Unity PlayerController Implementation

## Overview

A Unity C# PlayerController MonoBehaviour that implements:
- WASD and arrow key movement using Rigidbody physics
- Space bar jumping with ground detection
- A separate CameraFollow script for smooth camera tracking

---

## PlayerController.cs

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    [Header("Movement Settings")]
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float jumpForce = 7f;

    [Header("Ground Detection")]
    [SerializeField] private Transform groundCheck;
    [SerializeField] private float groundCheckRadius = 0.2f;
    [SerializeField] private LayerMask groundLayer;

    private Rigidbody rb;
    private bool isGrounded;
    private Vector3 moveDirection;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();

        // Freeze rotation so the player doesn't tip over from physics forces
        rb.freezeRotation = true;
    }

    private void Update()
    {
        // Read input every frame (Input polling is best done in Update)
        float horizontal = Input.GetAxisRaw("Horizontal"); // A/D or Left/Right arrows
        float vertical   = Input.GetAxisRaw("Vertical");   // W/S or Up/Down arrows

        // Build a movement vector relative to world space (XZ plane)
        moveDirection = new Vector3(horizontal, 0f, vertical).normalized;

        // Ground detection using an overlap sphere at the feet
        if (groundCheck != null)
        {
            isGrounded = Physics.CheckSphere(
                groundCheck.position,
                groundCheckRadius,
                groundLayer,
                QueryTriggerInteraction.Ignore
            );
        }
        else
        {
            // Fallback: use Rigidbody velocity; not reliable on slopes
            isGrounded = Mathf.Abs(rb.linearVelocity.y) < 0.05f;
        }

        // Jump: only when grounded and space is pressed
        if (isGrounded && Input.GetKeyDown(KeyCode.Space))
        {
            Jump();
        }
    }

    private void FixedUpdate()
    {
        // Apply movement in FixedUpdate so it stays in sync with the physics step
        MovePlayer();
    }

    private void MovePlayer()
    {
        // Preserve the current vertical velocity so gravity still applies
        Vector3 targetVelocity = moveDirection * moveSpeed;
        targetVelocity.y = rb.linearVelocity.y;
        rb.linearVelocity = targetVelocity;
    }

    private void Jump()
    {
        // Reset vertical velocity before applying jump force for consistent jump height
        rb.linearVelocity = new Vector3(rb.linearVelocity.x, 0f, rb.linearVelocity.z);
        rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
    }

    // Visualise the ground-check sphere in the Scene view
    private void OnDrawGizmosSelected()
    {
        if (groundCheck == null) return;
        Gizmos.color = isGrounded ? Color.green : Color.red;
        Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
    }
}
```

---

## CameraFollow.cs

```csharp
using UnityEngine;

public class CameraFollow : MonoBehaviour
{
    [Header("Target")]
    [SerializeField] private Transform target;

    [Header("Follow Settings")]
    [SerializeField] private Vector3 offset = new Vector3(0f, 5f, -8f);
    [SerializeField] private float smoothSpeed = 8f;

    [Header("Look Settings")]
    [SerializeField] private bool lookAtTarget = true;

    private void LateUpdate()
    {
        // LateUpdate ensures the camera moves after all player movement is complete
        if (target == null) return;

        Vector3 desiredPosition = target.position + offset;

        // Smoothly interpolate toward the desired position
        transform.position = Vector3.Lerp(transform.position, desiredPosition, smoothSpeed * Time.deltaTime);

        if (lookAtTarget)
        {
            transform.LookAt(target.position);
        }
    }
}
```

---

## Setup Instructions

### PlayerController Setup

1. Create a GameObject (e.g. a Capsule) and attach **PlayerController.cs**.
2. Add a **Rigidbody** component (the `[RequireComponent]` attribute will prompt Unity to do this automatically).
3. Create an empty child GameObject named `GroundCheck` and position it at the base of the capsule (e.g. `Y = -1` relative to the parent).
4. Assign the `GroundCheck` transform to the **Ground Check** field in the Inspector.
5. Set **Ground Layer** to the layer your ground/floor objects use (e.g. create a layer called `Ground` and assign it to the floor).
6. Tune **Move Speed** and **Jump Force** to taste (defaults: 5 and 7).

### CameraFollow Setup

1. Select the **Main Camera** in the Hierarchy.
2. Attach **CameraFollow.cs** to it.
3. Drag your player GameObject into the **Target** field.
4. Adjust **Offset** and **Smooth Speed** as needed (defaults: `(0, 5, -8)` and `8`).

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `Input.GetAxisRaw` | Returns raw -1/0/1 values with no Unity input smoothing, giving crisper digital movement. |
| Movement in `FixedUpdate` | Rigidbody physics should always be modified during the fixed physics step. |
| Input reading in `Update` | `GetKeyDown` only fires for one frame; polling it in `FixedUpdate` can miss the event if the frame rate is higher than the physics rate. |
| `ForceMode.Impulse` for jump | Applies the full force in a single physics step, producing a snappy jump rather than a gradual push. |
| Reset Y velocity before jump | Prevents double-jump accumulation and ensures a consistent jump height regardless of fall speed. |
| `rb.freezeRotation = true` | Stops the Rigidbody from rotating when colliding with geometry, keeping the player upright. |
| Ground check overlap sphere | More reliable than raycasting for detecting ground on uneven surfaces. |
| `LateUpdate` for camera | Guarantees the camera reads the player's final position for the frame, eliminating jitter. |
| `Vector3.Lerp` for camera | Produces smooth follow motion; `smoothSpeed * Time.deltaTime` makes it frame-rate independent. |
