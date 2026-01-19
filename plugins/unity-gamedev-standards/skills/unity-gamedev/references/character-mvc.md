# Character Design Pattern (MVC)

Model-View-Controller separation for robust character systems.

## Architecture Overview

```
┌─────────────┐
│  Controller │ ← Input processing, AI control
└──────┬──────┘
       │ calls
       ▼
┌─────────────┐
│    Model    │ ← Stats, data, business logic
└──────┬──────┘
       │ events
       ▼
┌─────────────┐
│     View    │ ← Animation, effects, UI
└─────────────┘
```

**Dependency Rules:**
- Controller → Model → View (one-way only)
- View and Controller never reference each other
- Each layer has single responsibility

## Model Layer

Holds character state and business logic:

```csharp
using System;
using UnityEngine;

/// <summary>
/// Character data and business logic (Model layer)
/// </summary>
public class CharacterModel : MonoBehaviour
{
    #region Events

    public event Action<float, float> OnHealthChanged;  // (current, max)
    public event Action OnDied;
    public event Action<float> OnStaminaChanged;

    #endregion

    #region Properties

    public float CurrentHealth { get; private set; }
    public float MaxHealth { get; private set; }
    public float CurrentStamina { get; private set; }
    public float MaxStamina { get; private set; }
    public bool IsDead => CurrentHealth <= 0;

    public float MoveSpeed { get; private set; }
    public float SprintMultiplier { get; private set; }
    public bool CanSprint => CurrentStamina > 0 && !IsDead;

    #endregion

    #region Initialization

    public void Initialize(float maxHealth, float maxStamina,
                          float moveSpeed, float sprintMultiplier)
    {
        MaxHealth = maxHealth;
        CurrentHealth = maxHealth;
        MaxStamina = maxStamina;
        CurrentStamina = maxStamina;
        MoveSpeed = moveSpeed;
        SprintMultiplier = sprintMultiplier;
    }

    #endregion

    #region Public Methods

    public void TakeDamage(float amount)
    {
        if (IsDead) return;

        CurrentHealth = Mathf.Max(0, CurrentHealth - amount);
        OnHealthChanged?.Invoke(CurrentHealth, MaxHealth);

        if (IsDead)
        {
            OnDied?.Invoke();
        }
    }

    public void Heal(float amount)
    {
        if (IsDead) return;

        CurrentHealth = Mathf.Min(MaxHealth, CurrentHealth + amount);
        OnHealthChanged?.Invoke(CurrentHealth, MaxHealth);
    }

    public void ConsumeStamina(float amount)
    {
        CurrentStamina = Mathf.Max(0, CurrentStamina - amount);
        OnStaminaChanged?.Invoke(CurrentStamina);
    }

    public void RecoverStamina(float amount)
    {
        CurrentStamina = Mathf.Min(MaxStamina, CurrentStamina + amount);
        OnStaminaChanged?.Invoke(CurrentStamina);
    }

    #endregion
}
```

## Controller Layer

Processes input and commands the Model:

```csharp
using UnityEngine;

/// <summary>
/// Player input processing (Controller layer)
/// </summary>
public class PlayerController : MonoBehaviour
{
    #region Inspector Fields

    [Header("References")]
    [SerializeField] private CharacterModel _model;
    [SerializeField] private Rigidbody _rigidbody;

    [Header("Settings")]
    [SerializeField] private float _staminaDrainRate = 10f;
    [SerializeField] private float _staminaRecoveryRate = 5f;

    #endregion

    #region Private Fields

    private Vector3 _moveInput;
    private bool _isSprintInput;

    #endregion

    #region Unity Lifecycle

    private void Update()
    {
        HandleInput();
        HandleStamina();
    }

    private void FixedUpdate()
    {
        ApplyMovement();
    }

    #endregion

    #region Private Methods

    private void HandleInput()
    {
        if (_model.IsDead) return;

        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");
        _isSprintInput = Input.GetKey(KeyCode.LeftShift);
    }

    private void HandleStamina()
    {
        if (_isSprintInput && _moveInput.magnitude > 0 && _model.CanSprint)
        {
            _model.ConsumeStamina(_staminaDrainRate * Time.deltaTime);
        }
        else if (_model.CurrentStamina < _model.MaxStamina)
        {
            _model.RecoverStamina(_staminaRecoveryRate * Time.deltaTime);
        }
    }

    private void ApplyMovement()
    {
        if (_model.IsDead) return;

        var speed = _model.MoveSpeed;
        if (_isSprintInput && _model.CanSprint)
        {
            speed *= _model.SprintMultiplier;
        }

        var velocity = _moveInput.normalized * speed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }

    #endregion
}
```

## View Layer

Observes Model and updates visuals:

```csharp
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Character visuals and feedback (View layer)
/// </summary>
public class CharacterView : MonoBehaviour
{
    #region Inspector Fields

    [Header("References")]
    [SerializeField] private CharacterModel _model;
    [SerializeField] private Animator _animator;
    [SerializeField] private Rigidbody _rigidbody;

    [Header("UI")]
    [SerializeField] private Slider _healthBar;
    [SerializeField] private Slider _staminaBar;

    [Header("VFX")]
    [SerializeField] private ParticleSystem _damageEffect;
    [SerializeField] private ParticleSystem _deathEffect;

    #endregion

    #region Private Fields

    private static readonly int Speed = Animator.StringToHash("Speed");
    private static readonly int IsDead = Animator.StringToHash("IsDead");

    private float _lastHealth;

    #endregion

    #region Unity Lifecycle

    private void OnEnable()
    {
        // Subscribe to Model events
        _model.OnHealthChanged += HandleHealthChanged;
        _model.OnStaminaChanged += HandleStaminaChanged;
        _model.OnDied += HandleDied;
    }

    private void OnDisable()
    {
        // Unsubscribe (prevent memory leaks)
        _model.OnHealthChanged -= HandleHealthChanged;
        _model.OnStaminaChanged -= HandleStaminaChanged;
        _model.OnDied -= HandleDied;
    }

    private void Update()
    {
        UpdateAnimation();
    }

    #endregion

    #region Event Handlers

    private void HandleHealthChanged(float current, float max)
    {
        // Update health bar
        if (_healthBar != null)
        {
            _healthBar.value = current / max;
        }

        // Play damage effect if health decreased
        if (current < _lastHealth && _damageEffect != null)
        {
            _damageEffect.Play();
        }

        _lastHealth = current;
    }

    private void HandleStaminaChanged(float current)
    {
        if (_staminaBar != null)
        {
            _staminaBar.value = current / _model.MaxStamina;
        }
    }

    private void HandleDied()
    {
        _animator.SetBool(IsDead, true);

        if (_deathEffect != null)
        {
            _deathEffect.Play();
        }
    }

    #endregion

    #region Private Methods

    private void UpdateAnimation()
    {
        var speed = _rigidbody.linearVelocity.magnitude;
        _animator.SetFloat(Speed, speed);
    }

    #endregion
}
```

## Bootstrap/Initializer

Wires everything together:

```csharp
using UnityEngine;

/// <summary>
/// Initializes character components
/// </summary>
public class CharacterBootstrap : MonoBehaviour
{
    [Header("Components")]
    [SerializeField] private CharacterModel _model;
    [SerializeField] private PlayerController _controller;
    [SerializeField] private CharacterView _view;

    [Header("Initial Stats")]
    [SerializeField] private float _maxHealth = 100f;
    [SerializeField] private float _maxStamina = 100f;
    [SerializeField] private float _moveSpeed = 5f;
    [SerializeField] private float _sprintMultiplier = 1.5f;

    private void Awake()
    {
        // Initialize Model first
        _model.Initialize(_maxHealth, _maxStamina, _moveSpeed, _sprintMultiplier);
    }
}
```

## AI Controller (Alternative)

Swap Player controller with AI:

```csharp
using UnityEngine;

/// <summary>
/// AI control (Controller layer alternative)
/// </summary>
public class AIController : MonoBehaviour
{
    [SerializeField] private CharacterModel _model;
    [SerializeField] private Rigidbody _rigidbody;
    [SerializeField] private Transform _target;

    [SerializeField] private float _chaseRange = 10f;
    [SerializeField] private float _attackRange = 2f;

    private void FixedUpdate()
    {
        if (_model.IsDead || _target == null) return;

        float distance = Vector3.Distance(transform.position, _target.position);

        if (distance <= _attackRange)
        {
            Attack();
        }
        else if (distance <= _chaseRange)
        {
            ChaseTarget();
        }
        else
        {
            Idle();
        }
    }

    private void ChaseTarget()
    {
        var direction = (_target.position - transform.position).normalized;
        var velocity = direction * _model.MoveSpeed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }

    private void Attack()
    {
        _rigidbody.linearVelocity = Vector3.zero;
        // Perform attack...
    }

    private void Idle()
    {
        _rigidbody.linearVelocity = Vector3.zero;
    }
}
```

## Benefits

### Testability

```csharp
// Test Model independently
[Test]
public void TakeDamage_ReducesHealth()
{
    var model = new GameObject().AddComponent<CharacterModel>();
    model.Initialize(100, 100, 5, 1.5f);

    model.TakeDamage(30);

    Assert.AreEqual(70, model.CurrentHealth);
}
```

### Reusability

- Same Model/View for Player and AI
- Only Controller changes
- Easy to add new control schemes

### Maintainability

- Clear responsibilities
- Changes isolated to single layer
- Easy to debug

### Team Development

- Different developers work on each layer
- Reduced merge conflicts
- Clear interfaces between layers

## Prefab Structure

```
PFB_Character/
├── CharacterBootstrap (component)
├── CharacterModel (component)
├── PlayerController OR AIController (component)
├── CharacterView (component)
├── Rigidbody
├── Collider
└── Visual/
    ├── Model (mesh)
    └── Animator
```

## Extension: State Machine

Add state to Model for complex behaviors:

```csharp
public enum CharacterState
{
    Idle,
    Moving,
    Attacking,
    Stunned,
    Dead
}

public class CharacterModel : MonoBehaviour
{
    public CharacterState CurrentState { get; private set; }
    public event Action<CharacterState> OnStateChanged;

    public void SetState(CharacterState newState)
    {
        if (CurrentState == newState) return;
        CurrentState = newState;
        OnStateChanged?.Invoke(newState);
    }
}
```
