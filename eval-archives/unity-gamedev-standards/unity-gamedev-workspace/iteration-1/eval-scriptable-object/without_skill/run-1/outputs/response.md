# WeaponData ScriptableObject - Unity Implementation

## Overview

This implementation creates a `WeaponData` ScriptableObject to store weapon configuration data in Unity. It includes the weapon stats (name, damage, attack speed, range, and sprite icon) and demonstrates how to use it in a MonoBehaviour-based weapon system.

---

## 1. WeaponData ScriptableObject

```csharp
// WeaponData.cs
// Place in: Assets/Scripts/Weapons/WeaponData.cs

using UnityEngine;

[CreateAssetMenu(fileName = "NewWeapon", menuName = "Weapons/Weapon Data", order = 0)]
public class WeaponData : ScriptableObject
{
    [Header("Basic Info")]
    [Tooltip("Display name of the weapon.")]
    public string weaponName = "Unnamed Weapon";

    [Header("Stats")]
    [Tooltip("Damage dealt per hit.")]
    [Min(0f)]
    public float damage = 10f;

    [Tooltip("Number of attacks per second.")]
    [Min(0.01f)]
    public float attackSpeed = 1f;

    [Tooltip("Maximum attack range in world units.")]
    [Min(0f)]
    public float range = 2f;

    [Header("Visuals")]
    [Tooltip("Icon displayed in the UI inventory or HUD.")]
    public Sprite icon;

    /// <summary>
    /// Returns the time in seconds between each attack, derived from attackSpeed.
    /// </summary>
    public float AttackInterval => 1f / attackSpeed;
}
```

### How to Create an Asset in the Editor

1. Right-click in the **Project** window.
2. Navigate to **Create > Weapons > Weapon Data**.
3. Name the new asset (e.g., `Sword`, `Bow`, `FireStaff`).
4. Fill in the fields in the **Inspector**.

---

## 2. WeaponController MonoBehaviour

This component reads from a `WeaponData` asset and drives attack logic at runtime.

```csharp
// WeaponController.cs
// Place in: Assets/Scripts/Weapons/WeaponController.cs

using UnityEngine;

/// <summary>
/// Drives weapon behavior at runtime using a WeaponData ScriptableObject.
/// Attach to a weapon GameObject (e.g., the player's hand or weapon slot).
/// </summary>
public class WeaponController : MonoBehaviour
{
    [Header("Weapon Configuration")]
    [Tooltip("Assign a WeaponData asset to configure this weapon.")]
    [SerializeField] private WeaponData weaponData;

    private float _attackCooldown;
    private float _timeSinceLastAttack;

    private void Start()
    {
        if (weaponData == null)
        {
            Debug.LogError($"[WeaponController] No WeaponData assigned on {gameObject.name}!");
            enabled = false;
            return;
        }

        _attackCooldown = weaponData.AttackInterval;
        _timeSinceLastAttack = _attackCooldown; // ready to attack immediately

        Debug.Log($"[WeaponController] Equipped: {weaponData.weaponName} " +
                  $"| Damage: {weaponData.damage} " +
                  $"| Attack Speed: {weaponData.attackSpeed}/s " +
                  $"| Range: {weaponData.range}m");
    }

    private void Update()
    {
        _timeSinceLastAttack += Time.deltaTime;

        // Example: attack on left mouse button / fire button
        if (Input.GetButton("Fire1") && CanAttack())
        {
            PerformAttack();
        }
    }

    /// <summary>
    /// Returns true if enough time has passed since the last attack.
    /// </summary>
    private bool CanAttack()
    {
        return _timeSinceLastAttack >= _attackCooldown;
    }

    /// <summary>
    /// Executes an attack: raycasts within range and applies damage.
    /// </summary>
    private void PerformAttack()
    {
        _timeSinceLastAttack = 0f;

        Debug.Log($"[WeaponController] {weaponData.weaponName} attacks for {weaponData.damage} damage!");

        // Raycast-based hit detection (2D example using the weapon's forward direction)
        RaycastHit2D hit = Physics2D.Raycast(
            transform.position,
            transform.right,
            weaponData.range
        );

        if (hit.collider != null)
        {
            // Try to find a health component and apply damage
            IDamageable damageable = hit.collider.GetComponent<IDamageable>();
            if (damageable != null)
            {
                damageable.TakeDamage(weaponData.damage);
                Debug.Log($"[WeaponController] Hit {hit.collider.name} for {weaponData.damage} damage.");
            }
        }
    }

    /// <summary>
    /// Hot-swaps the weapon data at runtime (e.g., picking up a new weapon).
    /// </summary>
    public void EquipWeapon(WeaponData newWeaponData)
    {
        if (newWeaponData == null)
        {
            Debug.LogWarning("[WeaponController] Tried to equip a null WeaponData.");
            return;
        }

        weaponData = newWeaponData;
        _attackCooldown = weaponData.AttackInterval;
        _timeSinceLastAttack = _attackCooldown;

        Debug.Log($"[WeaponController] Switched to: {weaponData.weaponName}");
    }

    /// <summary>
    /// Exposes the current weapon data (e.g., for UI to read the icon and name).
    /// </summary>
    public WeaponData CurrentWeaponData => weaponData;
}
```

---

## 3. IDamageable Interface

A simple interface so the weapon system is decoupled from specific enemy types.

```csharp
// IDamageable.cs
// Place in: Assets/Scripts/Interfaces/IDamageable.cs

/// <summary>
/// Any GameObject that can receive damage should implement this interface.
/// </summary>
public interface IDamageable
{
    void TakeDamage(float amount);
}
```

---

## 4. Example Enemy Implementation

```csharp
// EnemyHealth.cs
// Place in: Assets/Scripts/Enemies/EnemyHealth.cs

using UnityEngine;

public class EnemyHealth : MonoBehaviour, IDamageable
{
    [SerializeField] private float maxHealth = 100f;
    private float _currentHealth;

    private void Awake()
    {
        _currentHealth = maxHealth;
    }

    public void TakeDamage(float amount)
    {
        _currentHealth -= amount;
        Debug.Log($"[EnemyHealth] {gameObject.name} took {amount} damage. HP: {_currentHealth}/{maxHealth}");

        if (_currentHealth <= 0f)
        {
            Die();
        }
    }

    private void Die()
    {
        Debug.Log($"[EnemyHealth] {gameObject.name} died.");
        Destroy(gameObject);
    }
}
```

---

## 5. Example UI Integration

Reading the weapon icon and name to display in a HUD:

```csharp
// WeaponHUD.cs
// Place in: Assets/Scripts/UI/WeaponHUD.cs

using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class WeaponHUD : MonoBehaviour
{
    [SerializeField] private WeaponController weaponController;
    [SerializeField] private Image weaponIconImage;
    [SerializeField] private TextMeshProUGUI weaponNameText;

    private void Update()
    {
        WeaponData data = weaponController.CurrentWeaponData;
        if (data == null) return;

        weaponIconImage.sprite = data.icon;
        weaponNameText.text = data.weaponName;
    }
}
```

---

## 6. Folder Structure

```
Assets/
  Scripts/
    Interfaces/
      IDamageable.cs
    Weapons/
      WeaponData.cs          <-- ScriptableObject definition
      WeaponController.cs    <-- MonoBehaviour using the SO
    Enemies/
      EnemyHealth.cs
    UI/
      WeaponHUD.cs
  ScriptableObjects/
    Weapons/
      Sword.asset            <-- WeaponData asset instance
      Bow.asset
      FireStaff.asset
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| `ScriptableObject` for data | Decouples data from runtime logic; assets are shareable across scenes and prefabs |
| `[CreateAssetMenu]` attribute | Enables right-click creation in the Unity Editor without scripting |
| `AttackInterval` computed property | Keeps data consistent; no need to store both speed and interval |
| `IDamageable` interface | Weapon system does not depend on concrete enemy types (open/closed principle) |
| `[Min(...)]` attribute | Prevents invalid values (negative damage, zero attack speed) directly in the Inspector |
| `[Header]` and `[Tooltip]` | Improves editor usability for designers tweaking values |
