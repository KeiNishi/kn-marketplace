# Testing Standards

Unity Test Framework（Edit Mode / Play Mode）のルールとベストプラクティス。

## 目次

1. [フォルダ構造](#フォルダ構造)
2. [Edit Mode Test](#edit-mode-test)
3. [Play Mode Test](#play-mode-test)
4. [命名規則](#命名規則)
5. [Arrange-Act-Assert](#arrange-act-assert)
6. [Mock/Stub](#mockstub)
7. [非同期テスト](#非同期テスト)

---

## フォルダ構造

```
Assets/
├── _Project/
│   └── Scripts/
│       └── ...
└── Tests/
    ├── EditMode/
    │   ├── Tests.EditMode.asmdef    # Edit Mode Test用Assembly
    │   ├── Core/
    │   │   └── HealthSystemTests.cs
    │   └── Utilities/
    │       └── MathUtilsTests.cs
    └── PlayMode/
        ├── Tests.PlayMode.asmdef    # Play Mode Test用Assembly
        ├── Integration/
        │   └── PlayerMovementTests.cs
        └── UI/
            └── MenuNavigationTests.cs
```

### Assembly Definition設定

**Tests.EditMode.asmdef:**
```json
{
    "name": "Tests.EditMode",
    "rootNamespace": "Tests.EditMode",
    "references": [
        "GUID:<プロジェクトのAssembly GUID>"
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

**Tests.PlayMode.asmdef:**
```json
{
    "name": "Tests.PlayMode",
    "rootNamespace": "Tests.PlayMode",
    "references": [
        "GUID:<プロジェクトのAssembly GUID>"
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

---

## Edit Mode Test

### ロジックのユニットテスト

```csharp
using NUnit.Framework;

namespace Tests.EditMode.Core
{
    /// <summary>
    /// HealthSystemのユニットテスト
    /// </summary>
    [TestFixture]
    public class HealthSystemTests
    {
        private HealthSystem _healthSystem;
        
        [SetUp]
        public void SetUp()
        {
            // 各テスト前に初期化
            _healthSystem = new HealthSystem(maxHealth: 100);
        }
        
        [TearDown]
        public void TearDown()
        {
            // 各テスト後にクリーンアップ
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
            
            // Act & Assert
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

### ScriptableObjectのテスト

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

---

## Play Mode Test

### GameObjectを使ったテスト

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
            // プレイヤーオブジェクトを作成
            _playerObject = new GameObject("TestPlayer");
            _playerObject.AddComponent<Rigidbody>();
            _playerController = _playerObject.AddComponent<PlayerController>();
        }
        
        [TearDown]
        public void TearDown()
        {
            // クリーンアップ
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
            
            // Act - 入力をシミュレート（1フレーム待機）
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

### シーンロードテスト

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
            // Act
            var startButton = GameObject.Find("StartButton");
            
            // Assert
            Assert.IsNotNull(startButton, "Start button should exist in MainMenu scene");
            yield return null;
        }
    }
}
```

---

## 命名規則

### テストメソッド命名

```
[テスト対象メソッド]_[条件/シナリオ]_[期待される結果]
```

| 例 | 説明 |
|----|------|
| `TakeDamage_WhenDamageIsPositive_ReducesHealth` | ダメージが正の値の時、HPが減少する |
| `Jump_WhenNotGrounded_DoesNothing` | 地面にいない時、ジャンプしない |
| `GetItem_WhenInventoryFull_ReturnsFalse` | インベントリ満杯時、falseを返す |

### テストクラス命名

```
[テスト対象クラス名]Tests
```

例：`PlayerControllerTests`, `InventorySystemTests`, `WeaponDataTests`

---

## Arrange-Act-Assert

### 基本パターン

```csharp
[Test]
public void MethodName_Scenario_ExpectedResult()
{
    // Arrange - テストの準備
    var target = new TargetClass();
    var input = CreateTestInput();
    
    // Act - テスト対象の実行
    var result = target.MethodUnderTest(input);
    
    // Assert - 結果の検証
    Assert.AreEqual(expectedValue, result);
}
```

### 複数のAssert

```csharp
[Test]
public void CreatePlayer_WithValidData_InitializesCorrectly()
{
    // Arrange
    var data = new PlayerData { Name = "Hero", Level = 1, MaxHealth = 100 };
    
    // Act
    var player = PlayerFactory.Create(data);
    
    // Assert - 関連する複数の検証をグループ化
    Assert.Multiple(() =>
    {
        Assert.AreEqual("Hero", player.Name);
        Assert.AreEqual(1, player.Level);
        Assert.AreEqual(100, player.MaxHealth);
        Assert.AreEqual(100, player.CurrentHealth);
    });
}
```

---

## Mock/Stub

### インターフェースを使ったテスト可能設計

```csharp
// プロダクションコード
public interface IDamageCalculator
{
    int Calculate(int baseDamage, float multiplier);
}

public class CombatSystem
{
    private readonly IDamageCalculator _damageCalculator;
    
    public CombatSystem(IDamageCalculator damageCalculator)
    {
        _damageCalculator = damageCalculator;
    }
    
    public void Attack(IHealth target, int baseDamage, float multiplier)
    {
        var damage = _damageCalculator.Calculate(baseDamage, multiplier);
        target.TakeDamage(damage);
    }
}
```

```csharp
// テストコード
namespace Tests.EditMode.Combat
{
    // シンプルなMock実装
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
    
    public class MockHealth : IHealth
    {
        public int LastDamageTaken { get; private set; }
        
        public void TakeDamage(int damage)
        {
            LastDamageTaken = damage;
        }
    }
    
    [TestFixture]
    public class CombatSystemTests
    {
        [Test]
        public void Attack_UsesDamageCalculator_AndAppliesDamageToTarget()
        {
            // Arrange
            var mockCalculator = new MockDamageCalculator { ReturnValue = 25 };
            var mockTarget = new MockHealth();
            var combatSystem = new CombatSystem(mockCalculator);
            
            // Act
            combatSystem.Attack(mockTarget, baseDamage: 10, multiplier: 2.5f);
            
            // Assert
            Assert.AreEqual(10, mockCalculator.LastBaseDamage);
            Assert.AreEqual(2.5f, mockCalculator.LastMultiplier);
            Assert.AreEqual(25, mockTarget.LastDamageTaken);
        }
    }
}
```

---

## 非同期テスト

### UnityTest（Coroutine）

```csharp
[UnityTest]
public IEnumerator AsyncOperation_WhenCompleted_ReturnsResult()
{
    // Arrange
    var operation = new AsyncGameOperation();
    
    // Act
    operation.Start();
    
    // 完了まで待機
    while (!operation.IsCompleted)
    {
        yield return null;
    }
    
    // Assert
    Assert.IsTrue(operation.IsSuccess);
}
```

### タイムアウト付きテスト

```csharp
[UnityTest]
[Timeout(5000)]  // 5秒でタイムアウト
public IEnumerator LongOperation_CompletesWithinTimeout()
{
    // Arrange
    var operation = new LongRunningOperation();
    
    // Act
    operation.Start();
    yield return new WaitUntil(() => operation.IsCompleted);
    
    // Assert
    Assert.IsTrue(operation.IsSuccess);
}
```

---

## ベストプラクティス

### Do's

- **1テスト1検証** - 失敗原因を特定しやすくする
- **独立したテスト** - テスト間の依存を排除
- **高速なテスト** - Edit Modeテストを優先
- **意味のある名前** - 何をテストしているか明確に
- **SetUp/TearDown活用** - 初期化/クリーンアップを共通化

### Don'ts

- **テスト間の状態共有** - 不安定なテストの原因
- **外部リソース依存** - ネットワーク、ファイルI/O
- **Sleep/固定待機** - WaitUntil/WaitForを使用
- **過度なMock** - 本当に必要な箇所のみ
- **テストのテスト** - テストコードのテストは不要
