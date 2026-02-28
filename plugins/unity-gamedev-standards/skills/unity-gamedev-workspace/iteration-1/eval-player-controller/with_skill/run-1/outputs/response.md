# PlayerController - Unity C# Implementation

Below is the complete Unity C# implementation for a `PlayerController` MonoBehaviour. It includes WASD/arrow key movement, space bar jumping, and a separate `PlayerFollowCamera` component for camera follow using `LateUpdate()`. All conventions from the unity-gamedev-standards skill are applied.

---

## PlayerController.cs

Place this script on the player GameObject. The GameObject requires a `Rigidbody` component. Set `Rigidbody > Interpolation > Interpolate` in the Inspector to prevent camera stutter.

```csharp
using UnityEngine;

/// <summary>
/// Handles player movement and jumping using Rigidbody physics.
/// Requires a Rigidbody component on the same GameObject.
/// NOTE: Set Rigidbody > Interpolation > Interpolate in the Inspector
///       to prevent camera stutter when using PlayerFollowCamera.
/// </summary>
[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    #region Inspector Fields

    [Header("Movement")]
    [Tooltip("Horizontal movement speed in units per second.")]
    [SerializeField, Range(1f, 20f)] private float _moveSpeed = 5f;

    [Header("Jumping")]
    [Tooltip("Impulse force applied upward when the player jumps.")]
    [SerializeField, Range(1f, 30f)] private float _jumpForce = 10f;

    [Tooltip("Maximum distance from the ground to allow jumping.")]
    [SerializeField, Range(0.1f, 1f)] private float _groundCheckDistance = 0.2f;

    [Tooltip("Layer mask used to detect ground surfaces.")]
    [SerializeField] private LayerMask _groundLayerMask = ~0;

    #endregion

    #region Private Fields

    private Rigidbody _rigidbody;
    private Vector3 _moveInput;
    private bool _jumpRequested;
    private bool _isGrounded;

    #endregion

    #region Properties

    /// <summary>Whether the player is currently touching the ground.</summary>
    public bool IsGrounded => _isGrounded;

    #endregion

    #region Events

    /// <summary>Raised when the player leaves the ground.</summary>
    public event System.Action OnJumped;

    /// <summary>Raised when the player lands on the ground.</summary>
    public event System.Action OnLanded;

    #endregion

    #region Unity Lifecycle

    private void Awake()
    {
        _rigidbody = GetComponent<Rigidbody>();
    }

    private void OnEnable()
    {
        // Reserved for future event subscriptions.
    }

    private void OnDisable()
    {
        // Unsubscribe all listeners to prevent memory leaks.
        OnJumped = null;
        OnLanded = null;
    }

    private void Update()
    {
        HandleMovementInput();
        HandleJumpInput();
        CheckGrounded();
    }

    private void FixedUpdate()
    {
        ApplyMovement();
        ApplyJump();
    }

    #endregion

    #region Private Methods

    private void HandleMovementInput()
    {
        _moveInput.x = Input.GetAxisRaw("Horizontal"); // A/D or Left/Right arrows
        _moveInput.z = Input.GetAxisRaw("Vertical");   // W/S or Up/Down arrows
    }

    private void HandleJumpInput()
    {
        if (Input.GetKeyDown(KeyCode.Space) && _isGrounded)
        {
            _jumpRequested = true;
        }
    }

    private void CheckGrounded()
    {
        var wasGrounded = _isGrounded;
        _isGrounded = Physics.Raycast(
            transform.position,
            Vector3.down,
            _groundCheckDistance + 0.01f,
            _groundLayerMask
        );

        if (!wasGrounded && _isGrounded)
        {
            OnLanded?.Invoke();
        }
    }

    private void ApplyMovement()
    {
        var horizontalVelocity = _moveInput.normalized * _moveSpeed;
        var velocity = new Vector3(horizontalVelocity.x, _rigidbody.linearVelocity.y, horizontalVelocity.z);
        _rigidbody.linearVelocity = velocity;
    }

    private void ApplyJump()
    {
        if (!_jumpRequested) return;

        _jumpRequested = false;
        // Zero out vertical velocity before applying jump for consistent jump height.
        _rigidbody.linearVelocity = new Vector3(_rigidbody.linearVelocity.x, 0f, _rigidbody.linearVelocity.z);
        _rigidbody.AddForce(Vector3.up * _jumpForce, ForceMode.Impulse);
        OnJumped?.Invoke();
    }

    #endregion
}
```

---

## PlayerFollowCamera.cs

Place this script on the Camera GameObject. Assign the player's `Transform` to the `_target` field in the Inspector. Camera position is updated exclusively in `LateUpdate()` to prevent jitter.

```csharp
using UnityEngine;

/// <summary>
/// Smooth follow camera that tracks a target Transform.
/// MUST use LateUpdate to read the target's final position after all movement is complete.
/// </summary>
[DefaultExecutionOrder(100)] // Ensures this runs after all default-order scripts in LateUpdate.
public class PlayerFollowCamera : MonoBehaviour
{
    #region Inspector Fields

    [Header("Target")]
    [Tooltip("The Transform this camera will follow. Assign the player's Transform.")]
    [SerializeField] private Transform _target;

    [Header("Position Settings")]
    [Tooltip("Offset applied to the target's position to determine the desired camera position.")]
    [SerializeField] private Vector3 _offset = new(0f, 5f, -8f);

    [Tooltip("Camera position smoothing speed. Higher values produce faster catch-up.")]
    [SerializeField, Range(1f, 30f)] private float _positionSmoothSpeed = 8f;

    [Header("Look Settings")]
    [Tooltip("If true, the camera will look at the target each frame.")]
    [SerializeField] private bool _lookAtTarget = true;

    [Tooltip("Smooth speed for camera rotation toward the target.")]
    [SerializeField, Range(1f, 30f)] private float _rotationSmoothSpeed = 10f;

    #endregion

    #region Unity Lifecycle

    private void OnEnable()
    {
        // Reserved for future event subscriptions.
    }

    private void OnDisable()
    {
        // Reserved for future event unsubscriptions.
    }

    /// <summary>
    /// Camera position and rotation MUST be updated in LateUpdate.
    /// Using Update() causes 1-frame jitter because it reads the target's position
    /// before physics and other scripts have finalized it.
    /// </summary>
    private void LateUpdate()
    {
        if (_target == null) return;

        UpdateCameraPosition();

        if (_lookAtTarget)
        {
            UpdateCameraRotation();
        }
    }

    #endregion

    #region Private Methods

    private void UpdateCameraPosition()
    {
        var desiredPosition = _target.position + _offset;
        transform.position = Vector3.Lerp(
            transform.position,
            desiredPosition,
            _positionSmoothSpeed * Time.deltaTime
        );
    }

    private void UpdateCameraRotation()
    {
        var desiredRotation = Quaternion.LookRotation(_target.position - transform.position);
        transform.rotation = Quaternion.Slerp(
            transform.rotation,
            desiredRotation,
            _rotationSmoothSpeed * Time.deltaTime
        );
    }

    #endregion
}
```

---

## Setup Instructions

1. **Player GameObject**
   - Add a `Rigidbody` component.
   - Set `Rigidbody > Interpolation` to **Interpolate** in the Inspector (prevents camera stutter at high frame rates).
   - Set `Rigidbody > Freeze Rotation > X, Y, Z` to prevent physics-driven tipping.
   - Attach `PlayerController.cs`.
   - Configure `_moveSpeed`, `_jumpForce`, `_groundCheckDistance`, and `_groundLayerMask` in the Inspector.

2. **Camera GameObject**
   - Attach `PlayerFollowCamera.cs`.
   - Drag the player's `Transform` into the `_target` field in the Inspector.
   - Adjust `_offset`, `_positionSmoothSpeed`, and `_rotationSmoothSpeed` to taste.

3. **Ground Layer**
   - Assign the ground objects to a named layer (e.g., `Ground`).
   - Set `_groundLayerMask` on the `PlayerController` to that layer.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `_jumpRequested` flag | Jump input read in `Update()`, applied in `FixedUpdate()` — avoids missing a frame |
| Zero vertical velocity before jump | Ensures consistent jump height regardless of prior vertical speed |
| `LateUpdate()` for camera | Reads target's final position after all `Update()` and physics callbacks are complete |
| `[DefaultExecutionOrder(100)]` on camera | Guarantees camera `LateUpdate()` runs after any other scripts at default order |
| `RequireComponent(typeof(Rigidbody))` | Prevents missing component errors at runtime |
| No `Rigidbody` property overrides in `Awake()` | Inspector is the source of truth for `mass`, `drag`, `constraints`, etc. |
