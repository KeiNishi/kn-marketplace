---
name: unity-gamedev-standards
description: This skill should be used when the user asks to "create a Unity project", "write C# scripts for Unity", "implement MonoBehaviour", mentions "Unity", ".cs", ".unity", "C#", "MonoBehaviour", "ScriptableObject", "GameObject", or works with Unity APIs, scenes, prefabs, or assets. Also triggers on "/unity" command or questions about Unity game development patterns. For ECS/DOTS, see references/ecs-patterns.md. For testing, see references/testing-standards.md. For editor extensions, see references/editor-extensions.md.
allowed-tools: Bash(dotnet*), Bash(mkdir*), Bash(ls*), Read, Write, Edit, Glob, Grep, Task
---

# Unity GameDev Standards

Comprehensive guide for Unity 6.3 LTS+ game development. Covers project structure, coding conventions, MonoBehaviour patterns, performance optimization, and character design patterns.

## Project Structure

### Recommended Folder Layout

```
Assets/
├── _Project/                 # Project-specific assets (underscore for top)
│   ├── Art/
│   │   ├── Animations/
│   │   ├── Materials/
│   │   ├── Models/
│   │   ├── Sprites/
│   │   └── UI/
│   ├── Audio/
│   │   ├── Music/
│   │   └── SFX/
│   ├── Prefabs/
│   ├── Scenes/
│   ├── ScriptableObjects/
│   ├── Scripts/
│   │   ├── Core/             # Core systems
│   │   ├── Gameplay/         # Gameplay logic
│   │   ├── UI/               # UI scripts
│   │   └── Utilities/        # Utilities
│   └── Settings/
├── Plugins/                  # Third-party plugins
└── Editor/                   # Editor-only scripts
```

For detailed structure and asset naming conventions, see `references/project-structure.md`.

## Coding Standards

### Naming Conventions

```csharp
// Class: PascalCase
public class PlayerController : MonoBehaviour

// Public fields: PascalCase (Inspector visible)
public float MoveSpeed = 5f;

// Private fields: _camelCase
private float _currentHealth;
private Rigidbody _rigidbody;

// SerializeField: _camelCase (Inspector visible but private)
[SerializeField] private float _jumpForce = 10f;

// Constants: SCREAMING_SNAKE_CASE
private const int MAX_HEALTH = 100;

// Properties: PascalCase
public float CurrentHealth => _currentHealth;

// Methods: PascalCase
public void TakeDamage(int amount)

// Parameters/locals: camelCase
private void ProcessInput(float deltaTime)
{
    var moveDirection = Vector3.zero;
}
```

### Inspector Documentation

All Inspector properties require documentation:

```csharp
[Tooltip("Movement speed in units per second")]
[SerializeField] private float _moveSpeed = 5f;

[Tooltip("Jump force applied when jumping")]
[SerializeField, Range(1f, 20f)] private float _jumpForce = 10f;
```

For complete coding rules, see `references/coding-rules.md`.

## MonoBehaviour Pattern

```csharp
public class PlayerController : MonoBehaviour
{
    #region Inspector Fields

    [Header("Movement")]
    [SerializeField] private float _moveSpeed = 5f;

    #endregion

    #region Private Fields

    private Rigidbody _rigidbody;
    private Vector3 _moveInput;

    #endregion

    #region Events

    public event System.Action<float> OnHealthChanged;

    #endregion

    #region Unity Lifecycle

    private void Awake()
    {
        _rigidbody = GetComponent<Rigidbody>();
    }

    private void OnEnable()
    {
        // Subscribe to events
    }

    private void OnDisable()
    {
        // Unsubscribe (prevent memory leaks)
    }

    private void Update()
    {
        HandleInput();
    }

    private void FixedUpdate()
    {
        ApplyMovement();
    }

    #endregion

    #region Private Methods

    private void HandleInput()
    {
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");
    }

    private void ApplyMovement()
    {
        var velocity = _moveInput.normalized * _moveSpeed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }

    #endregion
}
```

## Animation Timing

### Update Order (per frame)

```
1. FixedUpdate()           - Fixed timestep (0~N times)
2. Physics update          - Internal physics
3. Animation (Physics)     - If Animator Mode = "Animate Physics"
4. OnTrigger/OnCollision   - Physics callbacks
5. Update()                - Once per frame
6. Animation (Normal)      - If Animator Mode = "Normal"
7. LateUpdate()            - After Update
8. Rendering
```

For detailed animation timing and Root Motion handling, see `references/animation-timing.md`.

## ScriptableObject

Data containers for game configuration:

```csharp
[CreateAssetMenu(fileName = "SO_WeaponData", menuName = "Game/Weapon Data")]
public class WeaponData : ScriptableObject
{
    [Header("Basic Info")]
    public string WeaponName;
    public Sprite Icon;

    [Header("Combat Stats")]
    [Range(1, 100)] public int Damage = 10;
    [Range(0.1f, 3f)] public float AttackSpeed = 1f;
}
```

For ScriptableObject patterns, see `references/scriptable-objects.md`.

## Performance Optimization

### GC Allocation Reduction

```csharp
// BAD: Allocation every frame
private void Update()
{
    var enemies = FindObjectsOfType<Enemy>();  // GC allocation
}

// GOOD: Cache and reuse
private List<Enemy> _enemies = new();
private void Update()
{
    _enemies.Clear();
    FindObjectsByType<Enemy>(FindObjectsSortMode.None, _enemies);
}
```

### Object Pooling

```csharp
using UnityEngine.Pool;

private ObjectPool<Bullet> _pool;

private void Awake()
{
    _pool = new ObjectPool<Bullet>(
        createFunc: () => Instantiate(_bulletPrefab),
        actionOnGet: b => b.gameObject.SetActive(true),
        actionOnRelease: b => b.gameObject.SetActive(false),
        defaultCapacity: 20,
        maxSize: 100
    );
}
```

For comprehensive performance optimization, see `references/performance.md`.

## Character Design (MVC Pattern)

Separate characters into Controller, Model, and View layers:

```
Controller → Model → View (one-way dependency)
```

- **Model**: Stats, data, business logic
- **Controller**: Input processing, AI control
- **View**: Animation, effects, UI

This enables:
- Swapping Player/AI controllers on same Model/View
- Independent testing of each layer
- Team parallel development

For complete MVC implementation, see `references/character-mvc.md`.

## Async with UniTask

UniTask provides zero-allocation async/await for Unity:

```csharp
using Cysharp.Threading.Tasks;

private async UniTask LoadLevelAsync()
{
    await UniTask.Delay(TimeSpan.FromSeconds(1f));
    await UniTask.NextFrame();
}

// Auto-cancel on destroy
private async void Start()
{
    await FetchDataAsync(this.GetCancellationTokenOnDestroy());
}
```

For UniTask installation and patterns, see `references/async-unitask.md`.

## Best Practices

### Do's

- Use `[Tooltip]` on all Inspector properties
- Use `[Range]` when values have bounds
- Cache component references in `Awake()`
- Unsubscribe events in `OnDisable()`
- Use object pooling for frequent instantiation
- Hash Animator parameter names: `Animator.StringToHash("Speed")`
- Use `TryGetComponent<T>()` instead of `GetComponent<T>() != null`

### Don'ts

- Don't use `FindObjectOfType` every frame
- Don't allocate in Update loops
- Don't use string concatenation in hot paths
- Don't skip null checks on external references
- Don't mix physics in Update (use FixedUpdate)
- Don't forget to unsubscribe from events

## Additional Resources

### Reference Files

Detailed documentation in `references/`:
- **`project-structure.md`** - Folder layout, asset naming
- **`coding-rules.md`** - Complete coding conventions
- **`animation-timing.md`** - Update order, Root Motion
- **`scriptable-objects.md`** - ScriptableObject patterns
- **`performance.md`** - Optimization techniques
- **`character-mvc.md`** - MVC character design
- **`async-unitask.md`** - UniTask async patterns
- **`git-management.md`** - .gitignore, Git LFS
- **`ecs-patterns.md`** - ECS/DOTS patterns
- **`testing-standards.md`** - Unit/Play Mode testing
- **`editor-extensions.md`** - Custom editors, drawers
