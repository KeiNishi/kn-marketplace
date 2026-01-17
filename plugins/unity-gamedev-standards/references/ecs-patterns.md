# ECS/DOTS Patterns

Unity 6 DOTS（Data-Oriented Technology Stack）使用時のパターンとベストプラクティス。

## 目次

1. [基本構造](#基本構造)
2. [Componentパターン](#componentパターン)
3. [Systemパターン](#systemパターン)
4. [Burst Compiler](#burst-compiler)
5. [Jobs System](#jobs-system)
6. [MonoBehaviourとの連携](#monobehaviourとの連携)

---

## 基本構造

### Entity/Component/System アーキテクチャ

```
Entity: 一意のID（データを持たない）
Component: 純粋なデータ（ロジックを持たない）
System: ロジック（データを処理）
```

### プロジェクト構造

```
Assets/_Project/Scripts/
├── ECS/
│   ├── Components/           # IComponentData定義
│   ├── Systems/              # SystemBase/ISystem実装
│   ├── Authoring/            # Baker/Authoring MonoBehaviour
│   └── Aspects/              # Aspect定義
```

---

## Componentパターン

### 基本Component

```csharp
using Unity.Entities;
using Unity.Mathematics;

/// <summary>
/// 移動速度コンポーネント
/// </summary>
public struct MoveSpeed : IComponentData
{
    public float Value;
}

/// <summary>
/// 位置コンポーネント（float3を使用）
/// </summary>
public struct Position : IComponentData
{
    public float3 Value;
}

/// <summary>
/// タグコンポーネント（データなし、フィルタリング用）
/// </summary>
public struct PlayerTag : IComponentData { }
```

### Buffer Component

```csharp
using Unity.Entities;

/// <summary>
/// ダメージログをバッファとして保持
/// </summary>
[InternalBufferCapacity(8)]
public struct DamageBuffer : IBufferElementData
{
    public int Value;
    public float Timestamp;
}
```

### Enableable Component

```csharp
using Unity.Entities;

/// <summary>
/// 有効/無効を切り替え可能なコンポーネント
/// </summary>
public struct Stunned : IComponentData, IEnableableComponent
{
    public float Duration;
}
```

---

## Systemパターン

### ISystem（推奨、Burst対応）

```csharp
using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;

/// <summary>
/// 移動処理システム（Burst Compiled）
/// </summary>
[BurstCompile]
public partial struct MoveSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // MoveSpeedを持つEntityが存在する場合のみ実行
        state.RequireForUpdate<MoveSpeed>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var deltaTime = SystemAPI.Time.DeltaTime;
        
        // IJobEntityを使用した並列処理
        new MoveJob { DeltaTime = deltaTime }.ScheduleParallel();
    }
}

[BurstCompile]
public partial struct MoveJob : IJobEntity
{
    public float DeltaTime;
    
    private void Execute(ref LocalTransform transform, in MoveSpeed speed)
    {
        transform.Position.y += speed.Value * DeltaTime;
    }
}
```

### SystemBase（Managed対応が必要な場合）

```csharp
using Unity.Entities;

/// <summary>
/// Managedリソースにアクセスが必要な場合のみ使用
/// </summary>
public partial class AudioSystem : SystemBase
{
    protected override void OnUpdate()
    {
        // Managed APIへのアクセスが可能
        Entities
            .WithoutBurst()
            .ForEach((in AudioRequest request) =>
            {
                // AudioSource.PlayOneShot等のManaged API呼び出し
            })
            .Run();
    }
}
```

---

## Burst Compiler

### Burst最適化ルール

```csharp
using Unity.Burst;
using Unity.Collections;

[BurstCompile]
public partial struct OptimizedJob : IJobEntity
{
    // ✅ 良い例：Burstで使用可能
    public float DeltaTime;
    public NativeArray<int> Results;
    
    // ❌ 悪い例：Burstでは使用不可
    // public string Name;           // Managed型
    // public List<int> Items;       // Managed Collection
    // public System.Action Callback; // Delegate

    private void Execute(ref LocalTransform transform)
    {
        // ✅ Unity.Mathematics を使用
        var pos = transform.Position;
        pos.y = math.sin(DeltaTime);
        
        // ❌ System.Math は使用しない
        // pos.y = (float)System.Math.Sin(DeltaTime);
    }
}
```

### FloatMode/FloatPrecision

```csharp
// 精度よりパフォーマンス優先
[BurstCompile(FloatMode = FloatMode.Fast, FloatPrecision = FloatPrecision.Low)]
public partial struct FastMathJob : IJobEntity { }

// 高精度が必要な場合
[BurstCompile(FloatMode = FloatMode.Strict)]
public partial struct PreciseMathJob : IJobEntity { }
```

---

## Jobs System

### IJobEntity（推奨）

```csharp
using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;

[BurstCompile]
public partial struct EnemyAIJob : IJobEntity
{
    public float3 PlayerPosition;
    public float DeltaTime;
    
    // Queryは自動生成される
    private void Execute(
        ref LocalTransform transform,
        in MoveSpeed speed,
        in EnemyTag tag)  // タグでフィルタリング
    {
        var direction = math.normalize(PlayerPosition - transform.Position);
        transform.Position += direction * speed.Value * DeltaTime;
    }
}
```

### Job Dependencies

```csharp
[BurstCompile]
public partial struct DependencyExampleSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        // Job1の完了を待ってからJob2を実行
        var handle1 = new FirstJob().Schedule(state.Dependency);
        var handle2 = new SecondJob().Schedule(handle1);
        
        state.Dependency = handle2;
    }
}
```

---

## MonoBehaviourとの連携

### Baking（Authoring → Entity変換）

```csharp
using Unity.Entities;
using UnityEngine;

/// <summary>
/// MonoBehaviour Authoring（Editorで設定）
/// </summary>
public class EnemyAuthoring : MonoBehaviour
{
    [Tooltip("【用途】移動速度\n【影響】高いほど素早く移動")]
    public float MoveSpeed = 5f;
    
    [Tooltip("【用途】最大HP\n【影響】耐久力")]
    public int MaxHealth = 100;
}

/// <summary>
/// Baker（AuthoringをEntityに変換）
/// </summary>
public class EnemyBaker : Baker<EnemyAuthoring>
{
    public override void Bake(EnemyAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.Dynamic);
        
        AddComponent(entity, new MoveSpeed { Value = authoring.MoveSpeed });
        AddComponent(entity, new Health { Current = authoring.MaxHealth, Max = authoring.MaxHealth });
        AddComponent<EnemyTag>(entity);
    }
}
```

### Managed World Access

```csharp
using Unity.Entities;
using UnityEngine;

/// <summary>
/// MonoBehaviourからECS Worldにアクセス
/// </summary>
public class GameManager : MonoBehaviour
{
    private EntityManager _entityManager;
    private EntityQuery _playerQuery;
    
    private void Start()
    {
        var world = World.DefaultGameObjectInjectionWorld;
        _entityManager = world.EntityManager;
        
        // Queryをキャッシュ
        _playerQuery = _entityManager.CreateEntityQuery(
            ComponentType.ReadOnly<PlayerTag>(),
            ComponentType.ReadOnly<LocalTransform>()
        );
    }
    
    public Vector3 GetPlayerPosition()
    {
        if (_playerQuery.IsEmpty) return Vector3.zero;
        
        var entity = _playerQuery.GetSingletonEntity();
        var transform = _entityManager.GetComponentData<LocalTransform>(entity);
        return transform.Position;
    }
}
```

---

## ベストプラクティス

### Do's

- **ISystemを優先使用** - Burst対応でパフォーマンス最大化
- **Unity.Mathematicsを使用** - float3, quaternion, math.*
- **NativeContainerを使用** - NativeArray, NativeList, NativeHashMap
- **Queryをキャッシュ** - SystemAPI.QueryBuilderを活用
- **Job依存関係を正しく設定** - Race Condition防止

### Don'ts

- **SystemBaseを乱用しない** - Managed必須時のみ使用
- **Entities.ForEachを避ける** - IJobEntityを優先
- **Managed型をJobで使用しない** - Burst非対応
- **同期実行（.Run()）を多用しない** - 並列化の恩恵を失う
