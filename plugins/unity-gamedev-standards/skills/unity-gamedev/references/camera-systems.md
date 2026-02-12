# Camera Systems

Execution order rules and patterns for Unity camera scripts.

## CRITICAL: Camera Follow MUST Use LateUpdate

### Why LateUpdate Is Required

Unity's per-frame execution order:

```
1. FixedUpdate()       - Physics timestep (0~N times)
2. Physics simulation  - Rigidbody movement, collisions
3. Update()            - Game logic, input
4. Animation update    - Animator (Normal mode)
5. LateUpdate()        - Post-processing (camera, IK)
6. Rendering           - Draw frame
```

If a camera reads the target position in `Update()`, it captures the position **before** other scripts and physics have finished moving the target. This causes a 1-frame positional mismatch, producing visible jitter or stuttering.

`LateUpdate()` runs **after** all `Update()` calls and animation updates, guaranteeing the target is in its final position for the frame.

### BAD vs GOOD

```csharp
// BAD: Camera jitters - reads position before physics/other scripts finish
private void Update()
{
    transform.position = _target.position + _offset;
}

// GOOD: Camera reads final position after all movement is complete
private void LateUpdate()
{
    transform.position = _target.position + _offset;
}
```

## Rigidbody Interpolation Requirement

When following a Rigidbody-based character, the target Rigidbody **MUST** have Interpolation enabled in the Inspector.

Without interpolation, the Rigidbody position updates only at `FixedUpdate` rate (default 50Hz), but rendering runs at frame rate (60-144Hz+). This causes visible stutter even with `LateUpdate()`.

**How to fix**: Set `Rigidbody > Interpolation > Interpolate` in the Unity Inspector on the target GameObject. Do NOT set this value in code.

## Common Camera Patterns

### Follow Camera

```csharp
public class FollowCamera : MonoBehaviour
{
    #region Inspector Fields

    [Header("Target")]
    [Tooltip("Transform to follow")]
    [SerializeField] private Transform _target;

    [Header("Settings")]
    [Tooltip("Offset from target position")]
    [SerializeField] private Vector3 _offset = new(0f, 10f, -10f);

    [Tooltip("Smoothing speed (higher = faster catch-up)")]
    [SerializeField, Range(1f, 20f)] private float _smoothSpeed = 5f;

    #endregion

    #region Unity Lifecycle

    private void LateUpdate()
    {
        if (_target == null) return;

        var desiredPosition = _target.position + _offset;
        transform.position = Vector3.Lerp(
            transform.position,
            desiredPosition,
            _smoothSpeed * Time.deltaTime
        );
        transform.LookAt(_target);
    }

    #endregion
}
```

### Side-Scrolling Camera

```csharp
public class SideScrollCamera : MonoBehaviour
{
    #region Inspector Fields

    [Header("Target")]
    [Tooltip("Transform to follow")]
    [SerializeField] private Transform _target;

    [Header("Settings")]
    [Tooltip("Offset from target position")]
    [SerializeField] private Vector3 _offset = new(0f, 2f, -10f);

    [Tooltip("Smoothing speed")]
    [SerializeField, Range(1f, 20f)] private float _smoothSpeed = 5f;

    [Header("Bounds")]
    [Tooltip("Minimum X position for camera")]
    [SerializeField] private float _minX = float.MinValue;

    [Tooltip("Maximum X position for camera")]
    [SerializeField] private float _maxX = float.MaxValue;

    #endregion

    #region Unity Lifecycle

    private void LateUpdate()
    {
        if (_target == null) return;

        var desiredPosition = _target.position + _offset;
        desiredPosition.x = Mathf.Clamp(desiredPosition.x, _minX, _maxX);
        transform.position = Vector3.Lerp(
            transform.position,
            desiredPosition,
            _smoothSpeed * Time.deltaTime
        );
    }

    #endregion
}
```

### Orbit Camera

```csharp
public class OrbitCamera : MonoBehaviour
{
    #region Inspector Fields

    [Header("Target")]
    [Tooltip("Transform to orbit around")]
    [SerializeField] private Transform _target;

    [Header("Orbit Settings")]
    [Tooltip("Distance from target")]
    [SerializeField, Range(1f, 50f)] private float _distance = 10f;

    [Tooltip("Horizontal rotation speed")]
    [SerializeField, Range(50f, 500f)] private float _horizontalSpeed = 120f;

    [Tooltip("Vertical rotation speed")]
    [SerializeField, Range(50f, 500f)] private float _verticalSpeed = 120f;

    [Tooltip("Minimum vertical angle")]
    [SerializeField, Range(-89f, 0f)] private float _minVerticalAngle = -20f;

    [Tooltip("Maximum vertical angle")]
    [SerializeField, Range(0f, 89f)] private float _maxVerticalAngle = 80f;

    #endregion

    #region Private Fields

    private float _horizontalAngle;
    private float _verticalAngle = 30f;

    #endregion

    #region Unity Lifecycle

    private void Update()
    {
        // Input in Update (not camera position)
        _horizontalAngle += Input.GetAxis("Mouse X") * _horizontalSpeed * Time.deltaTime;
        _verticalAngle -= Input.GetAxis("Mouse Y") * _verticalSpeed * Time.deltaTime;
        _verticalAngle = Mathf.Clamp(_verticalAngle, _minVerticalAngle, _maxVerticalAngle);
    }

    private void LateUpdate()
    {
        if (_target == null) return;

        // Camera position calculated in LateUpdate
        var rotation = Quaternion.Euler(_verticalAngle, _horizontalAngle, 0f);
        var position = _target.position + rotation * new Vector3(0f, 0f, -_distance);

        transform.position = position;
        transform.LookAt(_target);
    }

    #endregion
}
```

**Key pattern**: Input reading happens in `Update()`, but camera position/rotation is applied in `LateUpdate()`.

## Camera + Physics Interaction

### Execution Order for Camera Use

| Method | Timing | Camera Position | Camera Input |
|--------|--------|----------------|-------------|
| FixedUpdate() | Before physics | NEVER | NEVER |
| Update() | After physics callbacks | NEVER | YES (read input) |
| LateUpdate() | After all Updates | YES (apply position) | NO |

### Camera Raycasting

Camera raycasts for gameplay interaction (click-to-select, aim assist) should happen in `Update()` since they are input-driven, not position-driven. Only camera **position/rotation** updates go in `LateUpdate()`.

```csharp
private void Update()
{
    // Input-driven raycast in Update - OK
    if (Input.GetMouseButtonDown(0))
    {
        var ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        if (Physics.Raycast(ray, out var hit))
        {
            // Handle hit
        }
    }
}

private void LateUpdate()
{
    // Camera position update - ONLY here
    transform.position = _target.position + _offset;
}
```

## Script Execution Order

For advanced setups with multiple camera-related scripts, use `[DefaultExecutionOrder]` to ensure camera scripts run after all gameplay scripts:

```csharp
[DefaultExecutionOrder(100)] // Runs after default (0) scripts
public class FollowCamera : MonoBehaviour
{
    private void LateUpdate()
    {
        // Guaranteed to run after other LateUpdate calls at default order
    }
}
```

Alternatively, configure via **Edit > Project Settings > Script Execution Order** in the Unity Editor.

## Common Mistakes

### Mistake 1: Camera Follow in Update()

**Symptom**: Target character visually jitters or stutters while the camera follows.
**Cause**: Camera reads position before physics and other scripts finalize movement.
**Fix**: Move all camera position/rotation logic to `LateUpdate()`.

### Mistake 2: Missing Rigidbody Interpolation on Target

**Symptom**: Character movement appears choppy when viewed through the camera, even with `LateUpdate()`.
**Cause**: Rigidbody updates at fixed timestep (50Hz) while rendering at higher frame rate.
**Fix**: Enable `Interpolation` on the target's Rigidbody in the Inspector.

### Mistake 3: Cinemachine Conflict

**Symptom**: Camera behaves erratically with Cinemachine/Unity Camera System installed.
**Cause**: Manual camera scripts conflict with Cinemachine's own camera management.
**Fix**: When using Cinemachine, use its built-in Follow and Aim behaviors. Do NOT add manual `LateUpdate()` camera scripts alongside Cinemachine virtual cameras.

### Mistake 4: Smoothing with Time.deltaTime in LateUpdate

`Time.deltaTime` in `LateUpdate()` returns the same value as in `Update()` (frame delta time), so using it for smoothing is correct:

```csharp
// This is correct - Time.deltaTime works properly in LateUpdate
private void LateUpdate()
{
    transform.position = Vector3.Lerp(
        transform.position,
        _target.position + _offset,
        _smoothSpeed * Time.deltaTime
    );
}
```
