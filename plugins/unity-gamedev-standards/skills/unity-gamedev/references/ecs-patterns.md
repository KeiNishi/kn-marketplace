# ECS/DOTS Patterns

Unity 6 DOTS (Data-Oriented Technology Stack) patterns and best practices.

## Architecture Overview

```
Entity: Unique ID (no data)
Component: Pure data (no logic)
System: Logic (processes data)
```

## Project Structure

```
Assets/_Project/Scripts/
├── ECS/
│   ├── Components/           # IComponentData definitions
│   ├── Systems/              # SystemBase/ISystem implementations
│   ├── Authoring/            # Baker/Authoring MonoBehaviours
│   └── Aspects/              # Aspect definitions
```

## Component Patterns

### Basic Component

```csharp
using Unity.Entities;
using Unity.Mathematics;

public struct MoveSpeed : IComponentData
{
    public float Value;
}

public struct Position : IComponentData
{
    public float3 Value;
}

// Tag component (no data, for filtering)
public struct PlayerTag : IComponentData { }
```

### Buffer Component

```csharp
[InternalBufferCapacity(8)]
public struct DamageBuffer : IBufferElementData
{
    public int Value;
    public float Timestamp;
}
```

### Enableable Component

```csharp
public struct Stunned : IComponentData, IEnableableComponent
{
    public float Duration;
}
```

## System Patterns

### ISystem (Recommended, Burst-Compatible)

```csharp
using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;

[BurstCompile]
public partial struct MoveSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        state.RequireForUpdate<MoveSpeed>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var deltaTime = SystemAPI.Time.DeltaTime;
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

### SystemBase (For Managed Access)

```csharp
public partial class AudioSystem : SystemBase
{
    protected override void OnUpdate()
    {
        Entities
            .WithoutBurst()
            .ForEach((in AudioRequest request) =>
            {
                // Managed API access
            })
            .Run();
    }
}
```

## Burst Compiler

### Optimization Rules

```csharp
[BurstCompile]
public partial struct OptimizedJob : IJobEntity
{
    // OK: Unmanaged types
    public float DeltaTime;
    public NativeArray<int> Results;

    // NOT OK: Managed types
    // public string Name;
    // public List<int> Items;

    private void Execute(ref LocalTransform transform)
    {
        // Use Unity.Mathematics
        var pos = transform.Position;
        pos.y = math.sin(DeltaTime);

        // Not System.Math
        // pos.y = (float)System.Math.Sin(DeltaTime);
    }
}
```

### Float Precision

```csharp
// Performance over precision
[BurstCompile(FloatMode = FloatMode.Fast, FloatPrecision = FloatPrecision.Low)]
public partial struct FastMathJob : IJobEntity { }

// High precision when needed
[BurstCompile(FloatMode = FloatMode.Strict)]
public partial struct PreciseMathJob : IJobEntity { }
```

## Jobs System

### IJobEntity (Recommended)

```csharp
[BurstCompile]
public partial struct EnemyAIJob : IJobEntity
{
    public float3 PlayerPosition;
    public float DeltaTime;

    private void Execute(
        ref LocalTransform transform,
        in MoveSpeed speed,
        in EnemyTag tag)  // Tag for filtering
    {
        var direction = math.normalize(PlayerPosition - transform.Position);
        transform.Position += direction * speed.Value * DeltaTime;
    }
}
```

### Job Dependencies

```csharp
[BurstCompile]
public partial struct DependencySystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var handle1 = new FirstJob().Schedule(state.Dependency);
        var handle2 = new SecondJob().Schedule(handle1);
        state.Dependency = handle2;
    }
}
```

## Authoring and Baking

### Authoring Component

```csharp
public class EnemyAuthoring : MonoBehaviour
{
    [Tooltip("Movement speed")]
    public float MoveSpeed = 5f;

    [Tooltip("Maximum HP")]
    public int MaxHealth = 100;
}
```

### Baker

```csharp
public class EnemyBaker : Baker<EnemyAuthoring>
{
    public override void Bake(EnemyAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.Dynamic);

        AddComponent(entity, new MoveSpeed { Value = authoring.MoveSpeed });
        AddComponent(entity, new Health {
            Current = authoring.MaxHealth,
            Max = authoring.MaxHealth
        });
        AddComponent<EnemyTag>(entity);
    }
}
```

## Managed World Access

```csharp
public class GameManager : MonoBehaviour
{
    private EntityManager _entityManager;
    private EntityQuery _playerQuery;

    private void Start()
    {
        var world = World.DefaultGameObjectInjectionWorld;
        _entityManager = world.EntityManager;

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

## Best Practices

### Do's

- Prefer ISystem over SystemBase
- Use Unity.Mathematics (float3, quaternion, math.*)
- Use NativeContainers (NativeArray, NativeList)
- Cache EntityQueries
- Set job dependencies correctly

### Don'ts

- Don't overuse SystemBase (Burst incompatible)
- Avoid Entities.ForEach (prefer IJobEntity)
- Don't use managed types in Jobs
- Avoid synchronous execution (.Run()) when possible
