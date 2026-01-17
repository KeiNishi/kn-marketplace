---
name: unity-gamedev-standards
description: Unity 6ゲーム開発の基本ルールとコーディング規約。新規プロジェクト作成、スクリプト実装、アーキテクチャ設計、パフォーマンス最適化時に使用。2D/3D/VR/ARすべてのジャンルに対応。ECS使用時はreferences/ecs-patterns.md、エディタ拡張はreferences/editor-extensions.md、テストはreferences/testing-standards.mdを参照。
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

### 非同期処理（Unity 6 Awaitable）

```csharp
using UnityEngine;

public class AsyncExample : MonoBehaviour
{
    // Unity 6のAwaitableを使用（GCアロケーションが少ない）
    private async Awaitable LoadLevelAsync()
    {
        // フレーム待機
        await Awaitable.NextFrameAsync();
        
        // 時間待機
        await Awaitable.WaitForSecondsAsync(1f);
        
        // メインスレッドに戻る
        await Awaitable.MainThreadAsync();
        
        // バックグラウンドスレッドで実行
        await Awaitable.BackgroundThreadAsync();
    }
    
    // CancellationTokenでキャンセル可能に
    private async Awaitable FetchDataAsync(CancellationToken token)
    {
        await Awaitable.WaitForSecondsAsync(2f, token);
    }
    
    private void OnDestroy()
    {
        // コンポーネント破棄時にdestroyCancellationTokenが自動キャンセル
    }
    
    private async void Start()
    {
        // destroyCancellationTokenを渡してオブジェクト破棄時に自動キャンセル
        await FetchDataAsync(destroyCancellationToken);
    }
}
```

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
