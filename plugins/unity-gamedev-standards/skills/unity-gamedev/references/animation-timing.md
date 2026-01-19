# Animation and Update Timing

Understanding Unity's execution order for proper animation and physics integration.

## Unity Update Order (Per Frame)

```
1. FixedUpdate()                 - Fixed timestep (0, 1, or multiple times)
2. Internal physics update       - Physics simulation
3. Animation update (Physics)    - If Animator Mode = "Animate Physics"
4. OnTriggerXxx / OnCollisionXxx - Physics callbacks
5. Update()                      - Once per frame
6. Animation update (Normal)     - If Animator Mode = "Normal"
7. LateUpdate()                  - After all Updates
8. Rendering                     - Draw frame
```

## FixedUpdate Timing

FixedUpdate runs at fixed intervals (default 0.02s = 50Hz):

- **High FPS (120fps)**: FixedUpdate may not run every frame
- **Low FPS (30fps)**: FixedUpdate may run multiple times per frame
- **Physics**: Always use FixedUpdate for Rigidbody operations

```csharp
// Physics movement in FixedUpdate
private void FixedUpdate()
{
    _rigidbody.linearVelocity = _moveDirection * _moveSpeed;
}

// Input in Update (responds every frame)
private void Update()
{
    _moveDirection.x = Input.GetAxisRaw("Horizontal");
    _moveDirection.z = Input.GetAxisRaw("Vertical");
}
```

## Animator Update Modes

| Mode | Update Timing | Use Case |
|------|---------------|----------|
| Normal | After Update() | Most characters |
| Animate Physics | After FixedUpdate() | Physics-driven characters |
| Unscaled Time | After Update() (ignores Time.timeScale) | Pause menus |

### Normal Mode

```csharp
// Animator updates after Update()
private void Update()
{
    // Input
    _moveInput = new Vector3(
        Input.GetAxisRaw("Horizontal"),
        0,
        Input.GetAxisRaw("Vertical")
    );

    // Set animator parameters
    _animator.SetFloat(Speed, _moveInput.magnitude * _moveSpeed);
}

private void FixedUpdate()
{
    // Physics movement
    var velocity = _moveInput.normalized * _moveSpeed;
    velocity.y = _rigidbody.linearVelocity.y;
    _rigidbody.linearVelocity = velocity;
}
```

### Animate Physics Mode

For characters where animation affects physics:

```csharp
// Set Animator Update Mode = "Animate Physics"
// Animation updates after FixedUpdate

private void Update()
{
    _moveInput.x = Input.GetAxisRaw("Horizontal");
    _moveInput.z = Input.GetAxisRaw("Vertical");

    _animator.SetFloat(MoveX, _moveInput.x);
    _animator.SetFloat(MoveZ, _moveInput.z);
}
```

## Animator Parameter Hashing

Always hash animator parameters:

```csharp
// Static readonly for hashed parameters
private static readonly int Speed = Animator.StringToHash("Speed");
private static readonly int IsGrounded = Animator.StringToHash("IsGrounded");
private static readonly int Jump = Animator.StringToHash("Jump");
private static readonly int Attack = Animator.StringToHash("Attack");

private void Update()
{
    _animator.SetFloat(Speed, _currentSpeed);
    _animator.SetBool(IsGrounded, _isGrounded);

    if (Input.GetButtonDown("Jump"))
    {
        _animator.SetTrigger(Jump);
    }
}
```

## Root Motion

Root Motion lets animations drive character movement.

### Basic Root Motion

```csharp
/// <summary>
/// Root Motion character
/// Animator: Apply Root Motion = true
/// Update Mode: Animate Physics (if using Rigidbody)
/// </summary>
public class RootMotionCharacter : MonoBehaviour
{
    [SerializeField] private Animator _animator;
    [SerializeField] private Rigidbody _rigidbody;

    private static readonly int Speed = Animator.StringToHash("Speed");

    private void Update()
    {
        float input = Input.GetAxisRaw("Vertical");
        _animator.SetFloat(Speed, input);
    }

    /// <summary>
    /// Called after Animator update, before LateUpdate
    /// </summary>
    private void OnAnimatorMove()
    {
        // Get root motion delta from animator
        Vector3 deltaPosition = _animator.deltaPosition;
        Quaternion deltaRotation = _animator.deltaRotation;

        // Apply to rigidbody (preserve Y velocity for gravity)
        deltaPosition.y = _rigidbody.linearVelocity.y * Time.deltaTime;
        _rigidbody.linearVelocity = deltaPosition / Time.deltaTime;
        _rigidbody.MoveRotation(_rigidbody.rotation * deltaRotation);
    }
}
```

### Hybrid Root Motion

Root Motion for movement, external control for rotation:

```csharp
public class HybridRootMotion : MonoBehaviour
{
    [SerializeField] private Animator _animator;
    [SerializeField] private Rigidbody _rigidbody;
    [SerializeField] private Transform _cameraTransform;
    [SerializeField] private float _rotationSpeed = 720f;

    private Vector3 _moveInput;
    private Quaternion _targetRotation;
    private static readonly int Speed = Animator.StringToHash("Speed");

    private void Update()
    {
        // Input
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");

        // Camera-relative direction
        var camForward = Vector3.Scale(_cameraTransform.forward, new Vector3(1, 0, 1)).normalized;
        var camRight = Vector3.Scale(_cameraTransform.right, new Vector3(1, 0, 1)).normalized;
        var moveDir = (camForward * _moveInput.z + camRight * _moveInput.x).normalized;

        // Animator
        _animator.SetFloat(Speed, moveDir.magnitude);

        // Target rotation (external control)
        if (moveDir != Vector3.zero)
        {
            _targetRotation = Quaternion.LookRotation(moveDir);
        }
    }

    private void OnAnimatorMove()
    {
        // Root motion for position
        var delta = _animator.deltaPosition;
        delta.y = _rigidbody.linearVelocity.y * Time.deltaTime;
        _rigidbody.linearVelocity = delta / Time.deltaTime;

        // External control for rotation (ignore animator rotation)
        var rotation = Quaternion.RotateTowards(
            _rigidbody.rotation,
            _targetRotation,
            _rotationSpeed * Time.deltaTime
        );
        _rigidbody.MoveRotation(rotation);
    }
}
```

## LateUpdate Use Cases

LateUpdate runs after all Update calls:

```csharp
// Camera follow (after character moves)
private void LateUpdate()
{
    transform.position = _target.position + _offset;
}

// Look-at after animation
private void LateUpdate()
{
    _headBone.LookAt(_lookTarget);
}

// UI that follows world objects
private void LateUpdate()
{
    _worldSpaceUI.position = Camera.main.WorldToScreenPoint(_targetObject.position);
}
```

## Common Mistakes

### Input in FixedUpdate

```csharp
// BAD: May miss input
private void FixedUpdate()
{
    if (Input.GetButtonDown("Jump"))  // Can be missed!
    {
        Jump();
    }
}

// GOOD: Capture in Update, apply in FixedUpdate
private bool _jumpRequested;

private void Update()
{
    if (Input.GetButtonDown("Jump"))
    {
        _jumpRequested = true;
    }
}

private void FixedUpdate()
{
    if (_jumpRequested)
    {
        Jump();
        _jumpRequested = false;
    }
}
```

### Physics in Update

```csharp
// BAD: Physics in Update
private void Update()
{
    _rigidbody.AddForce(Vector3.up * 10f);  // Inconsistent
}

// GOOD: Physics in FixedUpdate
private void FixedUpdate()
{
    _rigidbody.AddForce(Vector3.up * 10f);
}
```

### Animation in LateUpdate

```csharp
// BAD: Setting animator in LateUpdate
private void LateUpdate()
{
    _animator.SetFloat(Speed, _speed);  // May not work correctly
}

// GOOD: Set animator in Update
private void Update()
{
    _animator.SetFloat(Speed, _speed);
}
```
