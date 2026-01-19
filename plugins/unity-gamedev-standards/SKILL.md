---
name: unity-gamedev-standards
description: Unity 6ゲーム開発の基本ルールとコーディング規約。新規プロジェクト作成、スクリプト実装、アーキテクチャ設計、パフォーマンス最適化時に使用。2D/3D/VR/ARすべてのジャンルに対応。Use this skill when: (1) setting up a Unity project, (2) creating or editing C# scripts for Unity, (3) user mentions "Unity", ".cs", ".unity", "C#", "MonoBehaviour", "ScriptableObject", or "GameObject", (4) working with Unity APIs, scenes, prefabs, or assets, (5) user says /unity or asks about Unity game development. ECS使用時はreferences/ecs-patterns.md、エディタ拡張はreferences/editor-extensions.md、テストはreferences/testing-standards.mdを参照。このスキルはUnity関連のファイル作成・コード生成・実装計画・コードレビュー時に必ず使用すること。
allowed-tools: Bash(dotnet*), Bash(mkdir*), Bash(ls*), Read, Write, Edit, Glob, Grep, Task
---

# Unity GameDev Standards

Unity 6.3 LTS以降のゲーム開発における基本ルールとベストプラクティス。

## プロジェクト構造

### 推奨フォルダ構成

```
Assets/
├── _Project/                 # プロジェクト固有アセット（先頭_で最上部に表示）
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
│   │   ├── Characters/
│   │   ├── Environment/
│   │   └── UI/
│   ├── Scenes/
│   │   ├── _Init/            # 初期化シーン
│   │   ├── Levels/
│   │   └── UI/
│   ├── ScriptableObjects/
│   │   ├── Configs/
│   │   └── Data/
│   ├── Scripts/
│   │   ├── Core/             # ゲームコアシステム
│   │   ├── Gameplay/         # ゲームプレイロジック
│   │   ├── UI/               # UIスクリプト
│   │   └── Utilities/        # ユーティリティ
│   └── Settings/             # プロジェクト設定
├── Plugins/                  # サードパーティプラグイン
└── Editor/                   # エディタ専用スクリプト
    └── _Project/
```

### アセット命名規則

| 種別 | プレフィックス | 例 |
|------|---------------|-----|
| Prefab | `PFB_` | `PFB_Player.prefab` |
| Material | `MAT_` | `MAT_Ground.mat` |
| Texture | `TEX_` | `TEX_Player_Diffuse.png` |
| Animation | `ANIM_` | `ANIM_Player_Run.anim` |
| AnimatorController | `AC_` | `AC_Player.controller` |
| ScriptableObject | `SO_` | `SO_WeaponData.asset` |
| Scene | `SCN_` | `SCN_Level01.unity` |

---

## コーディングルール

### 命名規則

```csharp
// クラス名: PascalCase
public class PlayerController : MonoBehaviour

// パブリックフィールド: PascalCase（Inspectorで表示）
public float MoveSpeed = 5f;

// プライベートフィールド: _camelCase
private float _currentHealth;
private Rigidbody _rigidbody;

// SerializeField: _camelCase（Inspectorで表示されるがprivate）
[SerializeField] private float _jumpForce = 10f;

// 定数: SCREAMING_SNAKE_CASE
private const int MAX_HEALTH = 100;

// プロパティ: PascalCase
public float CurrentHealth => _currentHealth;

// メソッド: PascalCase
public void TakeDamage(int amount)

// パラメータ・ローカル変数: camelCase
private void ProcessInput(float deltaTime)
{
    var moveDirection = Vector3.zero;
}
```

### Inspectorプロパティのドキュメント

- **TooltipAttribute**: すべてのInspectorプロパティに用途と影響を記載
- **RangeAttribute**: 値に下限・上限がある場合は必ず適切な範囲を設定

```csharp
// Tooltipで用途と影響を説明
[Tooltip("【用途】プレイヤーの移動速度\n【影響】高いほど素早く移動")]
[SerializeField] private float _moveSpeed = 5f;

// Rangeで有効な値範囲を制限（下限・上限がある場合は必須）
[Tooltip("【用途】ジャンプ力\n【影響】高いほど高くジャンプ")]
[SerializeField, Range(1f, 20f)] private float _jumpForce = 10f;

// int型のRange例
[Tooltip("【用途】最大HP\n【影響】耐久力を決定")]
[SerializeField, Range(1, 1000)] private int _maxHealth = 100;
```

### MonoBehaviourパターン

```csharp
using UnityEngine;

/// <summary>
/// プレイヤーの移動と入力処理を担当
/// </summary>
public class PlayerController : MonoBehaviour
{
    #region Inspector Fields
    
    [Header("Movement")]
    [Tooltip("【用途】移動速度\n【影響】高いほど素早く移動")]
    [SerializeField] private float _moveSpeed = 5f;
    
    [Tooltip("【用途】ジャンプ力\n【影響】高いほど高くジャンプ")]
    [SerializeField, Range(1f, 20f)] private float _jumpForce = 10f;
    
    #endregion
    
    #region Private Fields
    
    private Rigidbody _rigidbody;
    private Vector3 _moveInput;
    private bool _isGrounded;
    
    #endregion
    
    #region Events
    
    // C# eventsを使用（パフォーマンスと型安全性が高い）
    public event System.Action<float> OnHealthChanged;
    public event System.Action OnDied;
    
    #endregion
    
    #region Unity Lifecycle
    
    private void Awake()
    {
        // コンポーネント参照の取得
        _rigidbody = GetComponent<Rigidbody>();
    }
    
    private void OnEnable()
    {
        // イベント購読
    }
    
    private void OnDisable()
    {
        // イベント購読解除（メモリリーク防止）
    }
    
    private void Update()
    {
        // 入力処理・非物理系更新
        HandleInput();
    }
    
    private void FixedUpdate()
    {
        // 物理演算
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

### 非同期処理（UniTask）

#### UniTaskのインストール

Package Managerから以下のURLでインストール:
```
https://github.com/Cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask
```

または`manifest.json`に追加:
```json
{
  "dependencies": {
    "com.cysharp.unitask": "https://github.com/Cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask"
  }
}
```

#### 基本的な使い方

```csharp
using Cysharp.Threading.Tasks;
using UnityEngine;

public class AsyncExample : MonoBehaviour
{
    // UniTaskを使用（GCアロケーションがゼロ）
    private async UniTask LoadLevelAsync()
    {
        // フレーム待機
        await UniTask.Yield();

        // 時間待機
        await UniTask.Delay(System.TimeSpan.FromSeconds(1f));

        // 次のフレームまで待機
        await UniTask.NextFrame();

        // バックグラウンドスレッドで実行
        await UniTask.SwitchToThreadPool();

        // メインスレッドに戻る
        await UniTask.SwitchToMainThread();
    }

    // CancellationTokenでキャンセル可能に
    private async UniTask FetchDataAsync(CancellationToken token)
    {
        await UniTask.Delay(System.TimeSpan.FromSeconds(2f), cancellationToken: token);
    }

    private void OnDestroy()
    {
        // コンポーネント破棄時にdestroyCancellationTokenが自動キャンセル
    }

    private async void Start()
    {
        // this.GetCancellationTokenOnDestroy()でオブジェクト破棄時に自動キャンセル
        await FetchDataAsync(this.GetCancellationTokenOnDestroy());
    }
}
```

#### UniTaskの便利な機能

```csharp
using Cysharp.Threading.Tasks;
using UnityEngine;

public class UniTaskFeatures : MonoBehaviour
{
    // 複数の非同期処理を並列実行
    private async UniTaskVoid ParallelExample()
    {
        var (result1, result2, result3) = await UniTask.WhenAll(
            FetchData1Async(),
            FetchData2Async(),
            FetchData3Async()
        );
    }

    // タイムアウト処理
    private async UniTask TimeoutExample()
    {
        var cts = new CancellationTokenSource();
        cts.CancelAfterSlim(System.TimeSpan.FromSeconds(5f)); // 5秒でタイムアウト

        try
        {
            await LongRunningTaskAsync(cts.Token);
        }
        catch (System.OperationCanceledException)
        {
            Debug.Log("Timeout!");
        }
    }

    // Coroutineとの相互運用
    private async UniTask CoroutineInterop()
    {
        // CoroutineをUniTaskに変換
        await SomeCoroutine().ToUniTask();
    }

    private System.Collections.IEnumerator SomeCoroutine()
    {
        yield return new WaitForSeconds(1f);
    }

    private async UniTask<int> FetchData1Async() => await UniTask.Delay(100).ContinueWith(() => 1);
    private async UniTask<int> FetchData2Async() => await UniTask.Delay(200).ContinueWith(() => 2);
    private async UniTask<int> FetchData3Async() => await UniTask.Delay(300).ContinueWith(() => 3);
    private async UniTask LongRunningTaskAsync(CancellationToken token) => await UniTask.Delay(10000, cancellationToken: token);
}
```

---

## Animationと更新処理のタイミング

### Unityの更新処理順序

Unityのフレーム内の実行順序を理解することが重要です。以下は1フレーム内の主要な実行順序:

```
1. FixedUpdate()                          - 固定タイムステップで実行（0回、1回、または複数回）
2. Internal physics update                - 物理演算の更新
3. Internal animation update              - Animator Update Modeが"Animate Physics"の場合
4. OnTriggerXxx / OnCollisionXxx          - 物理コールバック
5. Update()                               - 毎フレーム1回実行（入力処理、状態管理）
6. Internal animation update              - Animator Update Modeが"Normal"の場合
7. LateUpdate()                           - Updateの後に実行（カメラ追従など）
8. Rendering                              - レンダリング処理
```

**重要なポイント:**
- **FixedUpdate**は固定時間間隔（デフォルト0.02秒 = 50Hz）で実行されるため、フレームレートに応じて0回以上実行される可能性があります
- 高フレームレート時（例：120fps）: FixedUpdateが実行されないフレームが存在
- 低フレームレート時（例：30fps）: 1フレーム内でFixedUpdateが複数回実行される
- **物理演算**はFixedUpdateの直後に実行されるため、物理的な力の適用はFixedUpdate内で行う
- **Animator**の更新タイミングはUpdate Modeによって変わる（後述）

### Animator Update Mode

Animatorコンポーネントの`Update Mode`設定によってアニメーション更新タイミングが変わる:

| Update Mode | 更新タイミング | 用途 |
|-------------|---------------|------|
| **Normal** | Update()の後 | 通常のキャラクター |
| **Animate Physics** | FixedUpdate()の後 | 物理演算と連動するキャラクター |
| **Unscaled Time** | Update()の後（Time.timeScaleを無視） | ポーズメニューなど |

### 標準的な移動・アニメーション処理

```csharp
using UnityEngine;

/// <summary>
/// 標準的な移動とアニメーション処理の例
/// </summary>
public class CharacterMovement : MonoBehaviour
{
    [SerializeField] private float _moveSpeed = 5f;
    [SerializeField] private Animator _animator;

    private Rigidbody _rigidbody;
    private Vector3 _moveInput;

    // Animator Parameters（ハッシュ化でパフォーマンス向上）
    private static readonly int Speed = Animator.StringToHash("Speed");
    private static readonly int IsGrounded = Animator.StringToHash("IsGrounded");

    private void Awake()
    {
        _rigidbody = GetComponent<Rigidbody>();
    }

    private void Update()
    {
        // 入力処理（Update内で実行）
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");

        // Animatorパラメータ更新（Update内で実行）
        // ※ Animator Update Modeが"Normal"の場合、Updateの後にアニメーションが更新される
        var speed = _moveInput.magnitude * _moveSpeed;
        _animator.SetFloat(Speed, speed);
        _animator.SetBool(IsGrounded, IsGrounded());
    }

    private void FixedUpdate()
    {
        // 物理移動処理（FixedUpdate内で実行）
        // ※ FixedUpdateはUpdateより前に実行される可能性があるため、
        //    前フレームの入力値を使用することに注意
        var velocity = _moveInput.normalized * _moveSpeed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }

    private bool IsGrounded()
    {
        return Physics.Raycast(transform.position, Vector3.down, 1.1f);
    }
}
```

### 物理演算と連動するキャラクター

Rigidbodyを使用し、アニメーションが物理に影響を与える場合:

```csharp
using UnityEngine;

/// <summary>
/// 物理演算と連動するキャラクター
/// Animator Update Mode: "Animate Physics"
/// </summary>
public class PhysicsCharacter : MonoBehaviour
{
    [SerializeField] private Animator _animator;
    [SerializeField] private Rigidbody _rigidbody;

    private Vector3 _moveInput;
    private static readonly int MoveX = Animator.StringToHash("MoveX");
    private static readonly int MoveZ = Animator.StringToHash("MoveZ");

    private void Update()
    {
        // 入力処理（Update）
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");

        // Animatorパラメータを更新
        _animator.SetFloat(MoveX, _moveInput.x);
        _animator.SetFloat(MoveZ, _moveInput.z);
    }

    private void FixedUpdate()
    {
        // 物理処理（FixedUpdate内で実行）
        // ※ Animator Update Modeが"Animate Physics"の場合、
        //    FixedUpdateの後、物理演算の更新の後にアニメーションが更新される
        //    そのため、物理的な力の適用はここで行う

        // 追加の物理処理があればここに記述
    }
}
```

### RootMotion対応

Root MotionはAnimatorが直接Transformを制御する機能。`OnAnimatorMove()`で処理:

```csharp
using UnityEngine;

/// <summary>
/// Root Motion対応キャラクター
/// Animator設定: Apply Root Motion = true
/// Animator Update Mode: "Animate Physics"（物理使用時）
/// </summary>
public class RootMotionCharacter : MonoBehaviour
{
    [Header("Components")]
    [SerializeField] private Animator _animator;
    [SerializeField] private Rigidbody _rigidbody;

    [Header("Settings")]
    [SerializeField] private bool _usePhysics = true;

    private Vector3 _moveInput;
    private static readonly int MoveX = Animator.StringToHash("MoveX");
    private static readonly int MoveZ = Animator.StringToHash("MoveZ");

    private void Update()
    {
        // 入力処理（Update）
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");

        // Animatorに入力を渡す
        _animator.SetFloat(MoveX, _moveInput.x);
        _animator.SetFloat(MoveZ, _moveInput.z);
    }

    /// <summary>
    /// Root Motionの移動・回転を処理
    /// Animatorの更新後、LateUpdate前に呼ばれる
    /// </summary>
    private void OnAnimatorMove()
    {
        if (!_animator) return;

        if (_usePhysics)
        {
            // 物理演算を使用する場合
            // Root Motionの移動量をRigidbodyに適用
            var deltaPosition = _animator.deltaPosition;

            // Y軸は物理エンジンに任せる（重力など）
            deltaPosition.y = _rigidbody.linearVelocity.y * Time.deltaTime;

            // 速度として適用（Time.deltaTimeで除算）
            _rigidbody.linearVelocity = deltaPosition / Time.deltaTime;

            // Root Motionの回転をRigidbodyに適用
            var deltaRotation = _animator.deltaRotation;
            _rigidbody.MoveRotation(_rigidbody.rotation * deltaRotation);
        }
        else
        {
            // 物理演算を使用しない場合（Transformに直接適用）
            transform.position += _animator.deltaPosition;
            transform.rotation *= _animator.deltaRotation;
        }
    }
}
```

### Root Motion + 外部制御のハイブリッド

Root Motionと外部制御を組み合わせる例（回転のみ外部制御など）:

```csharp
using UnityEngine;

/// <summary>
/// Root Motionと外部制御のハイブリッド
/// 移動はRoot Motion、回転は外部制御
/// </summary>
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
        // 入力処理
        _moveInput.x = Input.GetAxisRaw("Horizontal");
        _moveInput.z = Input.GetAxisRaw("Vertical");

        // カメラ基準の移動方向を計算
        var cameraForward = Vector3.Scale(_cameraTransform.forward, new Vector3(1, 0, 1)).normalized;
        var cameraRight = Vector3.Scale(_cameraTransform.right, new Vector3(1, 0, 1)).normalized;
        var moveDirection = (cameraForward * _moveInput.z + cameraRight * _moveInput.x).normalized;

        // Animatorに速度を渡す
        _animator.SetFloat(Speed, moveDirection.magnitude);

        // 目標回転を計算（外部制御）
        if (moveDirection != Vector3.zero)
        {
            _targetRotation = Quaternion.LookRotation(moveDirection);
        }
    }

    private void OnAnimatorMove()
    {
        if (!_animator) return;

        // Root Motionの移動量を適用
        var deltaPosition = _animator.deltaPosition;
        deltaPosition.y = _rigidbody.linearVelocity.y * Time.deltaTime;
        _rigidbody.linearVelocity = deltaPosition / Time.deltaTime;

        // 回転は外部制御（Root Motionの回転は無視）
        var rotation = Quaternion.RotateTowards(
            _rigidbody.rotation,
            _targetRotation,
            _rotationSpeed * Time.deltaTime
        );
        _rigidbody.MoveRotation(rotation);
    }
}
```

### ベストプラクティス

#### Do's

- **Animatorパラメータはハッシュ化** - `Animator.StringToHash()`でパフォーマンス向上
- **Update Modeを適切に設定** - 物理使用時は"Animate Physics"
- **Root Motion使用時はOnAnimatorMove()を実装** - デフォルト動作を上書き
- **Y軸移動は物理エンジンに任せる** - 重力やジャンプと競合しないように

#### Don'ts

- **LateUpdate()で移動処理をしない** - カメラ追従などのみ
- **Root Motionと手動移動を混在させない** - どちらかに統一するか、明確に役割を分ける
- **毎フレームGetComponent<Animator>()しない** - Awake/Startでキャッシュ

---

## ScriptableObject

### データコンテナとしての使用

```csharp
using UnityEngine;

/// <summary>
/// 武器データを定義するScriptableObject
/// </summary>
[CreateAssetMenu(fileName = "SO_WeaponData", menuName = "Game/Weapon Data")]
public class WeaponData : ScriptableObject
{
    [Header("Basic Info")]
    [Tooltip("【用途】武器名\n【影響】UI表示に使用")]
    public string WeaponName;
    
    [Tooltip("【用途】武器アイコン\n【影響】UI表示に使用")]
    public Sprite Icon;
    
    [Header("Combat Stats")]
    [Tooltip("【用途】攻撃力\n【影響】与えるダメージ量")]
    [Range(1, 100)] public int Damage = 10;
    
    [Tooltip("【用途】攻撃速度\n【影響】攻撃間隔（秒）")]
    [Range(0.1f, 3f)] public float AttackSpeed = 1f;
}
```

```csharp
// 使用例
public class Weapon : MonoBehaviour
{
    [SerializeField] private WeaponData _weaponData;
    
    public void Attack(IDamageable target)
    {
        target.TakeDamage(_weaponData.Damage);
    }
}
```

---

## パフォーマンス最適化

### GCアロケーション削減

```csharp
// ❌ 悪い例：毎フレームアロケーション
private void Update()
{
    var enemies = FindObjectsOfType<Enemy>();  // GCアロケーション発生
    var message = "Score: " + score;           // 文字列結合でアロケーション
}

// ✅ 良い例：事前キャッシュ
private List<Enemy> _enemies = new();
private StringBuilder _stringBuilder = new();

private void Update()
{
    // リストを再利用
    _enemies.Clear();
    FindObjectsByType<Enemy>(FindObjectsSortMode.None, _enemies);
    
    // StringBuilderを再利用
    _stringBuilder.Clear();
    _stringBuilder.Append("Score: ").Append(score);
}
```

### Update最適化

```csharp
// ❌ 悪い例：毎フレーム検索
private void Update()
{
    var player = GameObject.FindWithTag("Player");
}

// ✅ 良い例：Awakeでキャッシュ
private Transform _playerTransform;

private void Awake()
{
    _playerTransform = GameObject.FindWithTag("Player").transform;
}

// ✅ 良い例：処理が不要なときは無効化
private void OnBecameInvisible()
{
    enabled = false;
}

private void OnBecameVisible()
{
    enabled = true;
}
```

### オブジェクトプール

```csharp
using UnityEngine;
using UnityEngine.Pool;

public class BulletSpawner : MonoBehaviour
{
    [SerializeField] private Bullet _bulletPrefab;
    
    private ObjectPool<Bullet> _pool;
    
    private void Awake()
    {
        _pool = new ObjectPool<Bullet>(
            createFunc: () => Instantiate(_bulletPrefab),
            actionOnGet: bullet => bullet.gameObject.SetActive(true),
            actionOnRelease: bullet => bullet.gameObject.SetActive(false),
            actionOnDestroy: bullet => Destroy(bullet.gameObject),
            collectionCheck: false,
            defaultCapacity: 20,
            maxSize: 100
        );
    }
    
    public Bullet SpawnBullet(Vector3 position, Quaternion rotation)
    {
        var bullet = _pool.Get();
        bullet.transform.SetPositionAndRotation(position, rotation);
        bullet.Initialize(_pool);
        return bullet;
    }
}

public class Bullet : MonoBehaviour
{
    private ObjectPool<Bullet> _pool;
    
    public void Initialize(ObjectPool<Bullet> pool)
    {
        _pool = pool;
    }
    
    public void ReturnToPool()
    {
        _pool.Release(this);
    }
}
```

---

## Character設計パターン（MVC分離）

### 設計思想

キャラクターを**Controller層（入力処理）**、**View層（見た目・アニメーション）**、**Model層（ステータス・データ）**に分離することで、堅牢で拡張しやすい構造を実現します。

```
┌─────────────┐
│  Controller │ ← 入力処理・AI制御
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Model    │ ← ステータス・データ・ロジック
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     View    │ ← アニメーション・エフェクト・UI
└─────────────┘
```

**依存関係のルール:**
- Controller → Model → View（一方向のみ）
- View/Controllerは相互に依存しない
- 各層は単一責任の原則に従う

### Model層（ステータス・データ）

キャラクターのデータとビジネスロジックを保持。

```csharp
using System;
using UnityEngine;

/// <summary>
/// キャラクターのステータスとデータを管理（Model層）
/// </summary>
public class CharacterModel : MonoBehaviour
{
    #region Events

    // Model層からのイベント通知（Viewが購読）
    public event Action<float, float> OnHealthChanged;  // (current, max)
    public event Action OnDied;
    public event Action<float> OnStaminaChanged;        // (current)

    #endregion

    #region Properties

    public float CurrentHealth { get; private set; }
    public float MaxHealth { get; private set; }
    public float CurrentStamina { get; private set; }
    public float MaxStamina { get; private set; }
    public bool IsDead => CurrentHealth <= 0;

    // 移動関連のステータス
    public float MoveSpeed { get; private set; }
    public float SprintMultiplier { get; private set; }
    public bool CanSprint => CurrentStamina > 0 && !IsDead;

    #endregion

    #region Initialization

    public void Initialize(float maxHealth, float maxStamina, float moveSpeed, float sprintMultiplier)
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

### Controller層（入力処理）

入力を受け取り、Modelを操作する。

```csharp
using UnityEngine;

/// <summary>
/// プレイヤーの入力を処理（Controller層）
/// </summary>
public class PlayerController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private CharacterModel _model;
    [SerializeField] private Rigidbody _rigidbody;

    [Header("Settings")]
    [SerializeField] private float _staminaDrainRate = 10f;
    [SerializeField] private float _staminaRecoveryRate = 5f;

    private Vector3 _moveInput;
    private bool _isSprintInput;

    #region Unity Lifecycle

    private void Update()
    {
        // 入力処理
        HandleInput();

        // スタミナ管理
        HandleStamina();
    }

    private void FixedUpdate()
    {
        // 物理移動処理
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
            // スプリント中はスタミナ消費
            _model.ConsumeStamina(_staminaDrainRate * Time.deltaTime);
        }
        else if (_model.CurrentStamina < _model.MaxStamina)
        {
            // スプリント中でなければスタミナ回復
            _model.RecoverStamina(_staminaRecoveryRate * Time.deltaTime);
        }
    }

    private void ApplyMovement()
    {
        if (_model.IsDead) return;

        // スプリント判定
        var speed = _model.MoveSpeed;
        if (_isSprintInput && _model.CanSprint)
        {
            speed *= _model.SprintMultiplier;
        }

        // 移動適用
        var velocity = _moveInput.normalized * speed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }

    #endregion
}
```

### View層（見た目・アニメーション）

Modelの状態を監視し、ビジュアルを更新する。

```csharp
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// キャラクターの見た目を管理（View層）
/// </summary>
public class CharacterView : MonoBehaviour
{
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

    // Animator Parameters（ハッシュ化）
    private static readonly int Speed = Animator.StringToHash("Speed");
    private static readonly int IsDead = Animator.StringToHash("IsDead");

    #region Unity Lifecycle

    private void OnEnable()
    {
        // Modelのイベントを購読
        _model.OnHealthChanged += HandleHealthChanged;
        _model.OnStaminaChanged += HandleStaminaChanged;
        _model.OnDied += HandleDied;
    }

    private void OnDisable()
    {
        // イベント購読解除（メモリリーク防止）
        _model.OnHealthChanged -= HandleHealthChanged;
        _model.OnStaminaChanged -= HandleStaminaChanged;
        _model.OnDied -= HandleDied;
    }

    private void Update()
    {
        // アニメーションパラメータ更新
        UpdateAnimation();
    }

    #endregion

    #region Event Handlers

    private void HandleHealthChanged(float current, float max)
    {
        // HPバー更新
        if (_healthBar != null)
        {
            _healthBar.value = current / max;
        }

        // ダメージエフェクト
        if (_damageEffect != null && current < max)
        {
            _damageEffect.Play();
        }
    }

    private void HandleStaminaChanged(float current)
    {
        // スタミナバー更新
        if (_staminaBar != null)
        {
            _staminaBar.value = current / _model.MaxStamina;
        }
    }

    private void HandleDied()
    {
        // 死亡アニメーション
        _animator.SetBool(IsDead, true);

        // 死亡エフェクト
        if (_deathEffect != null)
        {
            _deathEffect.Play();
        }
    }

    #endregion

    #region Private Methods

    private void UpdateAnimation()
    {
        // 移動速度に応じてアニメーション更新
        var speed = _rigidbody.linearVelocity.magnitude;
        _animator.SetFloat(Speed, speed);
    }

    #endregion
}
```

### 使用例（統合）

3つの層を1つのPrefabにアタッチして使用:

```csharp
using UnityEngine;

/// <summary>
/// キャラクター全体の初期化を管理
/// </summary>
public class CharacterBootstrap : MonoBehaviour
{
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
        // Model初期化（最初に実行）
        _model.Initialize(_maxHealth, _maxStamina, _moveSpeed, _sprintMultiplier);
    }
}
```

### MVC分離のメリット

1. **テスタビリティ向上** - 各層を独立してテスト可能
2. **再利用性** - Controller層を差し替えてAI/Player切り替え可能
3. **拡張性** - 新機能追加時に影響範囲が明確
4. **デバッグしやすい** - 責務が明確なので問題箇所を特定しやすい
5. **チーム開発** - 各層を異なるメンバーが並行開発可能

### AI切り替え例

Player ControllerとAI Controllerを切り替える:

```csharp
/// <summary>
/// AI制御（Controller層の別実装）
/// </summary>
public class AIController : MonoBehaviour
{
    [SerializeField] private CharacterModel _model;
    [SerializeField] private Rigidbody _rigidbody;
    [SerializeField] private Transform _target;

    private void FixedUpdate()
    {
        if (_model.IsDead) return;

        // ターゲットに向かって移動
        var direction = (_target.position - transform.position).normalized;
        var velocity = direction * _model.MoveSpeed;
        velocity.y = _rigidbody.linearVelocity.y;
        _rigidbody.linearVelocity = velocity;
    }
}
```

同じModel・ViewをPlayer/AI両方で使用可能。Controllerのみ切り替え。

---

## Git管理

### .gitignore

```gitignore
# Unity generated
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
[Mm]emoryCaptures/
[Rr]ecordings/

# Asset meta data
*.pidb.meta
*.pdb.meta
*.mdb.meta

# Unity3D generated assemblies
Assembly-CSharp*.csproj
*.sln
*.suo
*.tmp
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db

# Builds
*.apk
*.aab
*.unitypackage
*.app

# Crashlytics
crashlytics-build.properties

# IDE
.idea/
.vs/
.vscode/
*.code-workspace

# OS
.DS_Store
Thumbs.db
```

### Git LFS設定（.gitattributes）

```gitattributes
# Images
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.tif filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text

# 3D Models
*.fbx filter=lfs diff=lfs merge=lfs -text
*.obj filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text

# Fonts
*.ttf filter=lfs diff=lfs merge=lfs -text
*.otf filter=lfs diff=lfs merge=lfs -text

# Unity specific
*.unitypackage filter=lfs diff=lfs merge=lfs -text
```

---

## 参照ファイル

| 用途 | ファイル |
|------|---------|
| ECS/DOTS使用時 | [ecs-patterns.md](references/ecs-patterns.md) |
| エディタ拡張実装時 | [editor-extensions.md](references/editor-extensions.md) |
| テスト実装時 | [testing-standards.md](references/testing-standards.md) |
