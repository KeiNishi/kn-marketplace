# ScriptableObject Patterns

Using ScriptableObjects for data-driven game design.

## What Are ScriptableObjects

ScriptableObjects are data containers that:
- Store data independently of scene objects
- Share data between scenes and prefabs
- Reduce memory by avoiding duplicate data
- Enable designer-friendly editing

## Basic Data Container

```csharp
using UnityEngine;

[CreateAssetMenu(fileName = "SO_WeaponData", menuName = "Game/Weapon Data")]
public class WeaponData : ScriptableObject
{
    [Header("Basic Info")]
    [Tooltip("Display name of the weapon")]
    public string WeaponName;

    [Tooltip("Icon for inventory/UI")]
    public Sprite Icon;

    [TextArea(2, 5)]
    [Tooltip("Description shown in UI")]
    public string Description;

    [Header("Combat Stats")]
    [Tooltip("Damage per hit")]
    [Range(1, 100)]
    public int Damage = 10;

    [Tooltip("Attacks per second")]
    [Range(0.1f, 5f)]
    public float AttackSpeed = 1f;

    [Tooltip("Range of attack")]
    [Range(0.5f, 10f)]
    public float Range = 2f;

    [Header("Effects")]
    public GameObject HitEffect;
    public AudioClip AttackSound;
}
```

## Using ScriptableObjects

```csharp
public class Weapon : MonoBehaviour
{
    [SerializeField] private WeaponData _data;

    public void Attack(IDamageable target)
    {
        target.TakeDamage(_data.Damage);

        if (_data.HitEffect != null)
        {
            Instantiate(_data.HitEffect, transform.position, Quaternion.identity);
        }
    }

    public string GetDisplayName() => _data.WeaponName;
    public Sprite GetIcon() => _data.Icon;
}
```

## Configuration Pattern

Single configuration asset for game settings:

```csharp
[CreateAssetMenu(fileName = "SO_GameConfig", menuName = "Game/Game Config")]
public class GameConfig : ScriptableObject
{
    [Header("Player")]
    public float PlayerMoveSpeed = 5f;
    public int PlayerStartHealth = 100;
    public float PlayerJumpForce = 10f;

    [Header("Game")]
    public int StartingLives = 3;
    public float RespawnDelay = 2f;

    [Header("Audio")]
    [Range(0f, 1f)] public float MasterVolume = 1f;
    [Range(0f, 1f)] public float MusicVolume = 0.8f;
    [Range(0f, 1f)] public float SFXVolume = 1f;
}

// Usage
public class GameManager : MonoBehaviour
{
    [SerializeField] private GameConfig _config;

    private void Start()
    {
        AudioListener.volume = _config.MasterVolume;
    }
}
```

## Runtime Data Pattern

ScriptableObjects can hold runtime state (reset on play):

```csharp
[CreateAssetMenu(fileName = "SO_PlayerStats", menuName = "Game/Player Stats")]
public class PlayerStats : ScriptableObject
{
    [Header("Current Values")]
    public int CurrentHealth;
    public int CurrentScore;
    public int CurrentLevel;

    [Header("Defaults")]
    [SerializeField] private int _defaultHealth = 100;
    [SerializeField] private int _defaultScore = 0;
    [SerializeField] private int _defaultLevel = 1;

    public void Reset()
    {
        CurrentHealth = _defaultHealth;
        CurrentScore = _defaultScore;
        CurrentLevel = _defaultLevel;
    }

    private void OnEnable()
    {
        Reset();  // Reset when game starts
    }
}
```

## Event Channel Pattern

Decouple systems using ScriptableObject events:

```csharp
// Event channel
[CreateAssetMenu(fileName = "SO_GameEvent", menuName = "Events/Game Event")]
public class GameEvent : ScriptableObject
{
    private readonly List<GameEventListener> _listeners = new();

    public void Raise()
    {
        for (int i = _listeners.Count - 1; i >= 0; i--)
        {
            _listeners[i].OnEventRaised();
        }
    }

    public void RegisterListener(GameEventListener listener)
    {
        _listeners.Add(listener);
    }

    public void UnregisterListener(GameEventListener listener)
    {
        _listeners.Remove(listener);
    }
}

// Listener component
public class GameEventListener : MonoBehaviour
{
    [SerializeField] private GameEvent _event;
    [SerializeField] private UnityEvent _response;

    private void OnEnable() => _event.RegisterListener(this);
    private void OnDisable() => _event.UnregisterListener(this);

    public void OnEventRaised() => _response.Invoke();
}

// Usage - Raise event
public class Player : MonoBehaviour
{
    [SerializeField] private GameEvent _onPlayerDied;

    private void Die()
    {
        _onPlayerDied.Raise();
    }
}
```

## Event with Data

```csharp
// Generic event with data
public abstract class GameEvent<T> : ScriptableObject
{
    private readonly List<IGameEventListener<T>> _listeners = new();

    public void Raise(T value)
    {
        for (int i = _listeners.Count - 1; i >= 0; i--)
        {
            _listeners[i].OnEventRaised(value);
        }
    }

    public void RegisterListener(IGameEventListener<T> listener) =>
        _listeners.Add(listener);

    public void UnregisterListener(IGameEventListener<T> listener) =>
        _listeners.Remove(listener);
}

public interface IGameEventListener<T>
{
    void OnEventRaised(T value);
}

// Concrete event
[CreateAssetMenu(fileName = "SO_IntEvent", menuName = "Events/Int Event")]
public class IntEvent : GameEvent<int> { }

// Usage
public class ScoreManager : MonoBehaviour
{
    [SerializeField] private IntEvent _onScoreChanged;

    private int _score;

    public void AddScore(int points)
    {
        _score += points;
        _onScoreChanged.Raise(_score);
    }
}
```

## Variable Pattern

Runtime variables as assets:

```csharp
// Base variable
public abstract class Variable<T> : ScriptableObject
{
    [SerializeField] private T _value;

    public T Value
    {
        get => _value;
        set => _value = value;
    }
}

// Concrete variables
[CreateAssetMenu(fileName = "SO_IntVariable", menuName = "Variables/Int")]
public class IntVariable : Variable<int> { }

[CreateAssetMenu(fileName = "SO_FloatVariable", menuName = "Variables/Float")]
public class FloatVariable : Variable<float> { }

// Usage
public class HealthDisplay : MonoBehaviour
{
    [SerializeField] private IntVariable _playerHealth;
    [SerializeField] private TMP_Text _healthText;

    private void Update()
    {
        _healthText.text = $"Health: {_playerHealth.Value}";
    }
}
```

## Database Pattern

Collection of related data:

```csharp
[CreateAssetMenu(fileName = "SO_ItemDatabase", menuName = "Game/Item Database")]
public class ItemDatabase : ScriptableObject
{
    [SerializeField] private List<ItemData> _items = new();

    private Dictionary<string, ItemData> _itemLookup;

    private void OnEnable()
    {
        BuildLookup();
    }

    private void BuildLookup()
    {
        _itemLookup = new Dictionary<string, ItemData>();
        foreach (var item in _items)
        {
            _itemLookup[item.ID] = item;
        }
    }

    public ItemData GetItem(string id)
    {
        return _itemLookup.TryGetValue(id, out var item) ? item : null;
    }

    public IReadOnlyList<ItemData> GetAllItems() => _items;
}
```

## Best Practices

### Do's

- Use `CreateAssetMenu` for easy creation
- Add `[Header]` and `[Tooltip]` for designer clarity
- Use `[Range]` to prevent invalid values
- Reset runtime data in `OnEnable()`
- Use for configuration, not complex logic

### Don'ts

- Don't store scene references (they break on load)
- Don't use for highly dynamic data
- Don't forget runtime values persist in editor
- Don't put heavy logic in ScriptableObjects

## Naming Convention

```
SO_[Type]_[Name].asset
```

Examples:
- `SO_WeaponData_Sword.asset`
- `SO_GameConfig.asset`
- `SO_Event_PlayerDied.asset`
- `SO_Variable_PlayerHealth.asset`
