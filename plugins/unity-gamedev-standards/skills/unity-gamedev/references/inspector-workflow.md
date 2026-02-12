# Inspector Workflow

Rules for respecting Unity's Inspector-driven configuration. Code must NOT override values that belong in the Inspector or asset files.

## CRITICAL: Never Hardcode Inspector-Configurable Values in Code

### The Rule

Values that are configurable in the Unity Inspector (component properties, asset settings, material properties, physics material properties) **MUST** be set via the Inspector or asset files. Code **MUST NOT** override these values in `Awake()`, `Start()`, or any initialization method.

### Why This Matters

- **Invisible override**: Code-set values in `Awake()`/`Start()` silently override Inspector values with no visual indication
- **Broken workflow**: Changes made in the Inspector have no effect at runtime, confusing developers and designers
- **Debugging nightmare**: The Inspector shows one value, but runtime uses a completely different value
- **Lost collaboration**: Designers cannot tune values without modifying code

## What Awake() Is For

### ALLOWED in Awake()

```csharp
private void Awake()
{
    // 1. GetComponent caching - OK
    _rigidbody = GetComponent<Rigidbody>();
    _animator = GetComponent<Animator>();
    _collider = GetComponent<Collider>();

    // 2. Internal state initialization from SerializeField values - OK
    _currentHealth = _maxHealth;  // _maxHealth is set via Inspector
    _isAlive = true;

    // 3. Collection initialization - OK
    _enemies = new List<Enemy>();
    _pool = new ObjectPool<Bullet>(...);
}
```

### PROHIBITED in Awake() / Start()

```csharp
// BAD: Overriding Rigidbody properties that should be set in Inspector
private void Awake()
{
    _rigidbody = GetComponent<Rigidbody>();
    _rigidbody.mass = 2f;                          // VIOLATION
    _rigidbody.linearDamping = 0.5f;               // VIOLATION
    _rigidbody.angularDamping = 0.05f;             // VIOLATION
    _rigidbody.interpolation =
        RigidbodyInterpolation.Interpolate;        // VIOLATION
    _rigidbody.collisionDetectionMode =
        CollisionDetectionMode.Continuous;          // VIOLATION
}

// BAD: Creating assets in code that should be project assets
private void Awake()
{
    var physicsMaterial = new PhysicsMaterial("PlayerPhysics");  // VIOLATION
    physicsMaterial.dynamicFriction = 0f;
    physicsMaterial.staticFriction = 0f;
    physicsMaterial.bounciness = 0f;
    physicsMaterial.frictionCombine = PhysicsMaterialCombine.Minimum;
    _collider.material = physicsMaterial;
}

// BAD: Overriding Collider properties
private void Start()
{
    _collider.isTrigger = true;                    // VIOLATION
}
```

## Correct Approach for Value Configuration

### Option 1: Inspector Configuration (Preferred)

Set values directly on the component in the Unity Inspector. If the script needs to reference the value, use `[SerializeField]`:

```csharp
// Script exposes its own parameters via Inspector
[Header("Movement")]
[Tooltip("Movement speed in units per second")]
[SerializeField] private float _moveSpeed = 5f;

// Rigidbody mass, drag, interpolation etc. are set
// directly on the Rigidbody component in Inspector
// Do NOT duplicate them in script
```

### Option 2: ScriptableObject Configuration

For shared configuration across multiple objects:

```csharp
[CreateAssetMenu(fileName = "SO_PhysicsConfig", menuName = "Game/Physics Config")]
public class PhysicsConfig : ScriptableObject
{
    [Header("Movement")]
    public float MoveSpeed = 5f;
    public float JumpForce = 10f;

    [Header("References")]
    public PhysicsMaterial PlayerPhysicsMaterial;
}
```

The ScriptableObject references project assets (like PhysicsMaterial) that are created in the Unity Editor.

### Option 3: Instruct User to Change Inspector Values

When fixing a bug that requires changing an Inspector value:

1. **Tell the user exactly what to change**: "Set Rigidbody > Interpolation to Interpolate on the Player GameObject in the Inspector"
2. **Or use MCP tools** to modify the scene/prefab file directly if available
3. **Or create a ScriptableObject asset** with the correct values

**Never** add code to set the value programmatically as a "fix".

## Assets That Must Be Project Assets

The following should **ALWAYS** be created as project assets via the Unity Editor, **NOT** instantiated in code:

| Asset Type | Create Via |
|-----------|-----------|
| PhysicsMaterial / PhysicsMaterial2D | Assets > Create > Physics Material |
| Material | Assets > Create > Material |
| AnimatorController | Assets > Create > Animator Controller |
| AudioMixer / AudioMixerGroup | Assets > Create > Audio Mixer |
| RenderTexture | Assets > Create > Render Texture |
| ScriptableObject instances | Assets > Create > [custom menu] |

If a script needs one of these assets, reference it via `[SerializeField]` and assign it in the Inspector:

```csharp
[Header("Physics")]
[Tooltip("Physics material for player collider - assign in Inspector")]
[SerializeField] private PhysicsMaterial _physicsMaterial;
```

## Exception: Runtime-Only Dynamic Values

Setting component values in code **IS** acceptable when:

- The value is computed dynamically at runtime (e.g., AI-calculated speed)
- The value is loaded from save data
- The value changes every frame as part of gameplay logic
- The component is on a runtime-instantiated object with no prefab

```csharp
// OK: Dynamic runtime value - changes every frame
private void FixedUpdate()
{
    _rigidbody.linearVelocity = _moveDirection * _currentSpeed;
}

// OK: Applying save data at load time
private void LoadFromSave(SaveData data)
{
    transform.position = data.Position;
    _currentHealth = data.Health;
}

// OK: Runtime-instantiated object with computed values
private Bullet CreateBullet(Vector3 direction, float speed)
{
    var bullet = _pool.Get();
    bullet.Rigidbody.linearVelocity = direction * speed;
    return bullet;
}
```

## AI Agent Guidelines

When working on Unity code as an AI agent (including bug-fixer agents):

1. **Bug caused by wrong Inspector value** (e.g., Rigidbody mass is too high, Interpolation is off):
   - Tell the user to fix it in the Inspector
   - Or use MCP tools to modify the scene/prefab file
   - **NEVER** add code to set the value in Awake()/Start()

2. **Need a PhysicsMaterial or similar asset**:
   - Tell the user to create it in Unity Editor (Assets > Create > ...)
   - Or use MCP tools to create the asset file
   - **NEVER** use `new PhysicsMaterial()` in code

3. **Need to change Rigidbody/Collider/Renderer settings**:
   - Tell the user to change it in the Inspector
   - Or use MCP tools to modify the component settings
   - **NEVER** set these properties in Awake()/Start()

4. **If MCP tools are available for Unity scene/asset editing**:
   - Prefer using MCP tools to make the change directly
   - This is equivalent to the user changing it in the Inspector
