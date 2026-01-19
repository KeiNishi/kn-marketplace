# Coding Rules

Complete C# coding conventions for Unity development.

## Naming Conventions

### Classes and Structs

```csharp
// PascalCase
public class PlayerController : MonoBehaviour { }
public class WeaponData : ScriptableObject { }
public struct DamageInfo { }
```

### Interfaces

```csharp
// PascalCase with I prefix
public interface IDamageable { }
public interface IInteractable { }
```

### Fields

```csharp
public class Example : MonoBehaviour
{
    // Public fields: PascalCase (visible in Inspector)
    public float MoveSpeed = 5f;
    public Transform Target;

    // Private fields: _camelCase
    private float _currentHealth;
    private Rigidbody _rigidbody;
    private List<Enemy> _enemies;

    // SerializeField: _camelCase (visible in Inspector, but private)
    [SerializeField] private float _jumpForce = 10f;
    [SerializeField] private GameObject _bulletPrefab;

    // Static fields: s_camelCase or just _camelCase
    private static int s_instanceCount;

    // Constants: SCREAMING_SNAKE_CASE
    private const int MAX_HEALTH = 100;
    public const string PLAYER_TAG = "Player";
}
```

### Properties

```csharp
// PascalCase
public float CurrentHealth { get; private set; }
public bool IsDead => CurrentHealth <= 0;

// Expression-bodied for simple getters
public float HealthPercent => _currentHealth / _maxHealth;
```

### Methods

```csharp
// PascalCase
public void TakeDamage(int amount) { }
private void HandleInput() { }
protected virtual void OnDeath() { }

// Event handlers: On + EventName
private void OnEnemyDied(Enemy enemy) { }
private void OnButtonClicked() { }
```

### Parameters and Locals

```csharp
// camelCase
private void ProcessInput(float deltaTime, bool isRunning)
{
    var moveDirection = Vector3.zero;
    int enemyCount = _enemies.Count;
}
```

## Inspector Documentation

### Tooltip Attribute

All serialized fields require tooltips:

```csharp
[Tooltip("Movement speed in units per second. Higher values make character faster.")]
[SerializeField] private float _moveSpeed = 5f;

[Tooltip("Prefab to spawn when firing. Must have Bullet component.")]
[SerializeField] private GameObject _bulletPrefab;
```

### Range Attribute

Use when values have logical bounds:

```csharp
[Tooltip("Jump force in Newtons")]
[SerializeField, Range(1f, 20f)] private float _jumpForce = 10f;

[Tooltip("Maximum health points")]
[SerializeField, Range(1, 1000)] private int _maxHealth = 100;

[Tooltip("Attack cooldown in seconds")]
[SerializeField, Range(0.1f, 5f)] private float _attackCooldown = 1f;
```

### Header Attribute

Group related fields:

```csharp
[Header("Movement")]
[SerializeField] private float _moveSpeed = 5f;
[SerializeField] private float _jumpForce = 10f;

[Header("Combat")]
[SerializeField] private int _damage = 10;
[SerializeField] private float _attackRange = 2f;

[Header("References")]
[SerializeField] private Transform _firePoint;
[SerializeField] private Animator _animator;
```

## Code Organization

### Region Structure

```csharp
public class PlayerController : MonoBehaviour
{
    #region Inspector Fields

    [Header("Movement")]
    [SerializeField] private float _moveSpeed = 5f;

    [Header("Combat")]
    [SerializeField] private int _maxHealth = 100;

    #endregion

    #region Private Fields

    private Rigidbody _rigidbody;
    private Vector3 _moveInput;
    private bool _isGrounded;

    #endregion

    #region Properties

    public int CurrentHealth { get; private set; }
    public bool IsDead => CurrentHealth <= 0;

    #endregion

    #region Events

    public event System.Action<int> OnHealthChanged;
    public event System.Action OnDied;

    #endregion

    #region Unity Lifecycle

    private void Awake() { }
    private void OnEnable() { }
    private void OnDisable() { }
    private void Start() { }
    private void Update() { }
    private void FixedUpdate() { }
    private void LateUpdate() { }

    #endregion

    #region Public Methods

    public void TakeDamage(int amount) { }
    public void Heal(int amount) { }

    #endregion

    #region Private Methods

    private void HandleInput() { }
    private void ApplyMovement() { }

    #endregion
}
```

### Unity Lifecycle Order

```csharp
// Initialization
private void Awake()      // Called first, before Start
private void OnEnable()   // Called when enabled
private void Start()      // Called before first Update

// Update loop
private void FixedUpdate()  // Fixed timestep (physics)
private void Update()       // Every frame
private void LateUpdate()   // After all Updates

// Cleanup
private void OnDisable()  // Called when disabled
private void OnDestroy()  // Called when destroyed
```

## Events

### C# Events (Preferred)

```csharp
// Declaration
public event System.Action OnDied;
public event System.Action<int> OnHealthChanged;
public event System.Action<float, float> OnHealthChangedWithMax;

// Invoking
OnHealthChanged?.Invoke(_currentHealth);
OnDied?.Invoke();

// Subscribing
private void OnEnable()
{
    _health.OnDied += HandleDeath;
}

private void OnDisable()
{
    _health.OnDied -= HandleDeath;  // Always unsubscribe!
}
```

### UnityEvents (For Inspector)

```csharp
using UnityEngine.Events;

[SerializeField] private UnityEvent _onDied;
[SerializeField] private UnityEvent<int> _onScoreChanged;

// Invoking
_onDied.Invoke();
_onScoreChanged.Invoke(score);
```

## Null Handling

### Null Checks

```csharp
// Unity null check (checks both C# null and destroyed)
if (_rigidbody != null)
{
    _rigidbody.AddForce(force);
}

// Null-conditional (C# null only, not Unity-safe for MonoBehaviour)
_rigidbody?.AddForce(force);  // Careful with Unity objects!

// Pattern for Unity objects
if (_target != null)
{
    Vector3 direction = (_target.position - transform.position).normalized;
}
```

### TryGetComponent

```csharp
// Preferred over GetComponent + null check
if (collision.gameObject.TryGetComponent<IDamageable>(out var damageable))
{
    damageable.TakeDamage(_damage);
}

// Instead of
var damageable = collision.gameObject.GetComponent<IDamageable>();
if (damageable != null)
{
    damageable.TakeDamage(_damage);
}
```

## String Handling

### Cached Strings

```csharp
// BAD: String allocation every frame
private void Update()
{
    _animator.SetBool("IsRunning", _isRunning);  // String lookup
}

// GOOD: Cached hash
private static readonly int IsRunning = Animator.StringToHash("IsRunning");

private void Update()
{
    _animator.SetBool(IsRunning, _isRunning);  // Hash lookup
}
```

### String Interpolation vs Concatenation

```csharp
// Prefer interpolation for readability
string message = $"Player {playerName} scored {score} points";

// Avoid concatenation in hot paths
string bad = "Player " + playerName + " scored " + score + " points";  // GC allocations

// For frequent updates, use StringBuilder
private StringBuilder _sb = new();

private void UpdateUI()
{
    _sb.Clear();
    _sb.Append("Score: ").Append(_score);
    _scoreText.text = _sb.ToString();
}
```

## Best Practices

### Do's

- Use `[SerializeField]` instead of public fields
- Cache component references in `Awake()`
- Use `const` for compile-time constants
- Use `readonly` for runtime constants
- Implement `IDisposable` for cleanup when needed
- Use `nameof()` for string references to members

### Don'ts

- Don't use `GameObject.Find()` in Update
- Don't use `GetComponent<T>()` every frame
- Don't use string concatenation in Update
- Don't ignore compiler warnings
- Don't leave empty Unity callbacks (they still have overhead)
- Don't use `public` fields when `[SerializeField] private` suffices
