# WeaponData ScriptableObject

## WeaponData.cs

```csharp
using UnityEngine;

[CreateAssetMenu(fileName = "SO_WeaponData", menuName = "Game/Weapon Data")]
public class WeaponData : ScriptableObject
{
    [Header("Basic Info")]

    [Tooltip("Display name of the weapon shown in UI and inventory")]
    public string WeaponName;

    [Tooltip("Icon sprite used in inventory and HUD")]
    public Sprite Icon;

    [Header("Combat Stats")]

    [Tooltip("Damage dealt per hit")]
    [Range(1, 100)]
    public int Damage = 10;

    [Tooltip("Number of attacks per second")]
    [Range(0.1f, 5f)]
    public float AttackSpeed = 1f;

    [Tooltip("Maximum attack range in world units")]
    [Range(0.5f, 20f)]
    public float Range = 2f;
}
```

## WeaponController.cs (MonoBehaviour usage example)

```csharp
using UnityEngine;

public class WeaponController : MonoBehaviour
{
    #region Inspector Fields

    [Header("Weapon Configuration")]
    [Tooltip("ScriptableObject containing weapon stats and settings")]
    [SerializeField] private WeaponData _weaponData;

    [Header("References")]
    [Tooltip("Transform point from which attacks originate")]
    [SerializeField] private Transform _attackOrigin;

    #endregion

    #region Private Fields

    private float _attackCooldown;
    private float _lastAttackTime;

    #endregion

    #region Unity Lifecycle

    private void Awake()
    {
        if (_weaponData == null)
        {
            Debug.LogError($"[WeaponController] WeaponData is not assigned on {gameObject.name}.");
            return;
        }

        _attackCooldown = 1f / _weaponData.AttackSpeed;
    }

    private void Update()
    {
        HandleAttackInput();
    }

    #endregion

    #region Public Methods

    public string GetWeaponName() => _weaponData != null ? _weaponData.WeaponName : string.Empty;

    public Sprite GetIcon() => _weaponData != null ? _weaponData.Icon : null;

    #endregion

    #region Private Methods

    private void HandleAttackInput()
    {
        if (Input.GetButtonDown("Fire1") && CanAttack())
        {
            PerformAttack();
        }
    }

    private bool CanAttack()
    {
        return Time.time >= _lastAttackTime + _attackCooldown;
    }

    private void PerformAttack()
    {
        _lastAttackTime = Time.time;

        var hits = Physics.SphereCastAll(
            _attackOrigin.position,
            0.5f,
            _attackOrigin.forward,
            _weaponData.Range
        );

        foreach (var hit in hits)
        {
            if (hit.collider.TryGetComponent<IDamageable>(out var damageable))
            {
                damageable.TakeDamage(_weaponData.Damage);
            }
        }

        Debug.Log($"[WeaponController] Attacked with {_weaponData.WeaponName} for {_weaponData.Damage} damage.");
    }

    #endregion
}
```

## IDamageable.cs (Interface)

```csharp
public interface IDamageable
{
    void TakeDamage(int amount);
}
```

## How to Use

### Creating the Asset

1. In the Unity Project window, right-click the `Assets/_Project/ScriptableObjects/` folder.
2. Select **Game > Weapon Data**.
3. A new file named `SO_WeaponData.asset` is created.
4. Rename it following the convention: `SO_WeaponData_Sword.asset`.
5. Fill in WeaponName, Icon, Damage, AttackSpeed, and Range in the Inspector.

### Wiring in the Scene

1. Add a `WeaponController` component to your player or weapon GameObject.
2. Drag the `SO_WeaponData_Sword.asset` into the **Weapon Data** field.
3. Assign a Transform for **Attack Origin** (e.g., the weapon tip).
4. Press Play — the weapon reads all stats directly from the asset.

### Asset Naming Convention

```
SO_WeaponData_<Name>.asset
```

Examples:
- `SO_WeaponData_Sword.asset`
- `SO_WeaponData_Bow.asset`
- `SO_WeaponData_Staff.asset`
```
