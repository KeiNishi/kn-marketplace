# Testing Standards

Unity Test Framework rules and best practices for Edit Mode and Play Mode testing.

## Folder Structure

```
Assets/
├── _Project/
│   └── Scripts/
└── Tests/
    ├── EditMode/
    │   ├── Tests.EditMode.asmdef
    │   ├── Core/
    │   │   └── HealthSystemTests.cs
    │   └── Utilities/
    │       └── MathUtilsTests.cs
    └── PlayMode/
        ├── Tests.PlayMode.asmdef
        ├── Integration/
        │   └── PlayerMovementTests.cs
        └── UI/
            └── MenuNavigationTests.cs
```

## Assembly Definitions

### Edit Mode (Tests.EditMode.asmdef)

```json
{
    "name": "Tests.EditMode",
    "rootNamespace": "Tests.EditMode",
    "references": [
        "GUID:<project-assembly-guid>"
    ],
    "includePlatforms": [
        "Editor"
    ],
    "defineConstraints": [
        "UNITY_INCLUDE_TESTS"
    ],
    "optionalUnityReferences": [
        "TestAssemblies"
    ]
}
```

### Play Mode (Tests.PlayMode.asmdef)

```json
{
    "name": "Tests.PlayMode",
    "rootNamespace": "Tests.PlayMode",
    "references": [
        "GUID:<project-assembly-guid>"
    ],
    "includePlatforms": [],
    "defineConstraints": [
        "UNITY_INCLUDE_TESTS"
    ],
    "optionalUnityReferences": [
        "TestAssemblies"
    ]
}
```

## Edit Mode Tests

### Basic Unit Test

```csharp
using NUnit.Framework;

namespace Tests.EditMode.Core
{
    [TestFixture]
    public class HealthSystemTests
    {
        private HealthSystem _healthSystem;

        [SetUp]
        public void SetUp()
        {
            _healthSystem = new HealthSystem(maxHealth: 100);
        }

        [TearDown]
        public void TearDown()
        {
            _healthSystem = null;
        }

        [Test]
        public void TakeDamage_WhenDamageIsPositive_ReducesHealth()
        {
            // Arrange
            var initialHealth = _healthSystem.CurrentHealth;
            var damage = 30;

            // Act
            _healthSystem.TakeDamage(damage);

            // Assert
            Assert.AreEqual(initialHealth - damage, _healthSystem.CurrentHealth);
        }

        [Test]
        public void TakeDamage_WhenDamageExceedsHealth_SetsHealthToZero()
        {
            // Arrange & Act
            _healthSystem.TakeDamage(150);

            // Assert
            Assert.AreEqual(0, _healthSystem.CurrentHealth);
        }

        [Test]
        public void IsDead_WhenHealthIsZero_ReturnsTrue()
        {
            // Arrange
            _healthSystem.TakeDamage(100);

            // Assert
            Assert.IsTrue(_healthSystem.IsDead);
        }

        [TestCase(0)]
        [TestCase(-10)]
        public void TakeDamage_WhenDamageIsZeroOrNegative_DoesNotChangeHealth(int damage)
        {
            // Arrange
            var initialHealth = _healthSystem.CurrentHealth;

            // Act
            _healthSystem.TakeDamage(damage);

            // Assert
            Assert.AreEqual(initialHealth, _healthSystem.CurrentHealth);
        }
    }
}
```

### ScriptableObject Test

```csharp
using NUnit.Framework;
using UnityEngine;

namespace Tests.EditMode.Data
{
    [TestFixture]
    public class WeaponDataTests
    {
        [Test]
        public void WeaponData_WhenCreated_HasValidDefaults()
        {
            // Arrange & Act
            var weaponData = ScriptableObject.CreateInstance<WeaponData>();

            // Assert
            Assert.IsNotNull(weaponData);
            Assert.GreaterOrEqual(weaponData.Damage, 0);
            Assert.Greater(weaponData.AttackSpeed, 0f);

            // Cleanup
            Object.DestroyImmediate(weaponData);
        }
    }
}
```

## Play Mode Tests

### GameObject Test

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Tests.PlayMode.Integration
{
    [TestFixture]
    public class PlayerMovementTests
    {
        private GameObject _playerObject;
        private PlayerController _playerController;

        [SetUp]
        public void SetUp()
        {
            _playerObject = new GameObject("TestPlayer");
            _playerObject.AddComponent<Rigidbody>();
            _playerController = _playerObject.AddComponent<PlayerController>();
        }

        [TearDown]
        public void TearDown()
        {
            if (_playerObject != null)
            {
                Object.Destroy(_playerObject);
            }
        }

        [UnityTest]
        public IEnumerator Move_WhenInputApplied_ChangesPosition()
        {
            // Arrange
            var initialPosition = _playerObject.transform.position;

            // Act
            _playerController.SetMoveInput(Vector3.forward);
            yield return new WaitForFixedUpdate();
            yield return new WaitForFixedUpdate();

            // Assert
            Assert.AreNotEqual(initialPosition, _playerObject.transform.position);
        }

        [UnityTest]
        public IEnumerator Jump_WhenGrounded_AppliesUpwardForce()
        {
            // Arrange
            _playerController.SetGrounded(true);
            var rb = _playerObject.GetComponent<Rigidbody>();

            // Act
            _playerController.Jump();
            yield return new WaitForFixedUpdate();

            // Assert
            Assert.Greater(rb.linearVelocity.y, 0f);
        }
    }
}
```

### Scene Load Test

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Tests.PlayMode.Scenes
{
    [TestFixture]
    public class MainMenuSceneTests
    {
        [UnitySetUp]
        public IEnumerator SetUp()
        {
            yield return SceneManager.LoadSceneAsync("MainMenu");
        }

        [UnityTest]
        public IEnumerator MainMenu_WhenLoaded_HasStartButton()
        {
            var startButton = GameObject.Find("StartButton");

            Assert.IsNotNull(startButton, "Start button should exist");
            yield return null;
        }
    }
}
```

## Naming Conventions

### Test Method Naming

```
[MethodUnderTest]_[Scenario]_[ExpectedResult]
```

Examples:
- `TakeDamage_WhenDamageIsPositive_ReducesHealth`
- `Jump_WhenNotGrounded_DoesNothing`
- `GetItem_WhenInventoryFull_ReturnsFalse`

### Test Class Naming

```
[ClassUnderTest]Tests
```

Examples: `PlayerControllerTests`, `InventorySystemTests`

## Arrange-Act-Assert Pattern

```csharp
[Test]
public void MethodName_Scenario_ExpectedResult()
{
    // Arrange - Set up test
    var target = new TargetClass();
    var input = CreateTestInput();

    // Act - Execute test
    var result = target.MethodUnderTest(input);

    // Assert - Verify result
    Assert.AreEqual(expectedValue, result);
}
```

### Multiple Assertions

```csharp
[Test]
public void CreatePlayer_WithValidData_InitializesCorrectly()
{
    // Arrange
    var data = new PlayerData { Name = "Hero", Level = 1, MaxHealth = 100 };

    // Act
    var player = PlayerFactory.Create(data);

    // Assert
    Assert.Multiple(() =>
    {
        Assert.AreEqual("Hero", player.Name);
        Assert.AreEqual(1, player.Level);
        Assert.AreEqual(100, player.MaxHealth);
    });
}
```

## Mocking

### Simple Mock Implementation

```csharp
public interface IDamageCalculator
{
    int Calculate(int baseDamage, float multiplier);
}

public class MockDamageCalculator : IDamageCalculator
{
    public int ReturnValue { get; set; } = 10;
    public int LastBaseDamage { get; private set; }
    public float LastMultiplier { get; private set; }

    public int Calculate(int baseDamage, float multiplier)
    {
        LastBaseDamage = baseDamage;
        LastMultiplier = multiplier;
        return ReturnValue;
    }
}

[Test]
public void Attack_UsesDamageCalculator()
{
    // Arrange
    var mockCalculator = new MockDamageCalculator { ReturnValue = 25 };
    var combat = new CombatSystem(mockCalculator);

    // Act
    combat.Attack(target, baseDamage: 10, multiplier: 2.5f);

    // Assert
    Assert.AreEqual(10, mockCalculator.LastBaseDamage);
    Assert.AreEqual(2.5f, mockCalculator.LastMultiplier);
}
```

## Async Testing

### With Timeout

```csharp
[UnityTest]
[Timeout(5000)]  // 5 second timeout
public IEnumerator LongOperation_CompletesWithinTimeout()
{
    var operation = new LongRunningOperation();
    operation.Start();

    yield return new WaitUntil(() => operation.IsCompleted);

    Assert.IsTrue(operation.IsSuccess);
}
```

## Best Practices

### Do's

- One assertion per test (ideally)
- Independent tests (no shared state)
- Fast tests (prefer Edit Mode)
- Meaningful names
- Use SetUp/TearDown

### Don'ts

- Don't share state between tests
- Don't depend on external resources
- Don't use fixed Sleep/delays (use WaitUntil)
- Don't over-mock
- Don't test framework code
