# Performance Optimization

Comprehensive performance optimization techniques for Unity games.

## GC Allocation Reduction

### Avoid Allocations in Update

```csharp
// BAD: Allocations every frame
private void Update()
{
    var enemies = FindObjectsOfType<Enemy>();           // Array allocation
    var message = "Score: " + _score;                   // String allocation
    var positions = new List<Vector3>();                // List allocation
}

// GOOD: Pre-allocate and reuse
private readonly List<Enemy> _enemies = new();
private readonly StringBuilder _sb = new();
private readonly List<Vector3> _positions = new();

private void Update()
{
    _enemies.Clear();
    FindObjectsByType<Enemy>(FindObjectsSortMode.None, _enemies);

    _sb.Clear();
    _sb.Append("Score: ").Append(_score);

    _positions.Clear();
    // Populate _positions...
}
```

### String Operations

```csharp
// BAD: Concatenation in hot paths
private void Update()
{
    _text.text = "Health: " + _health + "/" + _maxHealth;  // 3 allocations
}

// GOOD: StringBuilder or string interpolation (cached)
private static readonly StringBuilder _healthSb = new();

private void UpdateHealthText()  // Call only when health changes
{
    _healthSb.Clear();
    _healthSb.Append("Health: ").Append(_health).Append("/").Append(_maxHealth);
    _text.text = _healthSb.ToString();
}
```

### LINQ Avoidance

```csharp
// BAD: LINQ allocates
var activeEnemies = _enemies.Where(e => e.IsActive).ToList();
var totalDamage = _weapons.Sum(w => w.Damage);

// GOOD: Manual iteration
int totalDamage = 0;
foreach (var weapon in _weapons)
{
    totalDamage += weapon.Damage;
}

// Or cache results
private readonly List<Enemy> _activeEnemies = new();
private void UpdateActiveEnemies()
{
    _activeEnemies.Clear();
    foreach (var enemy in _enemies)
    {
        if (enemy.IsActive)
            _activeEnemies.Add(enemy);
    }
}
```

## Component Caching

### GetComponent Caching

```csharp
// BAD: GetComponent every frame
private void Update()
{
    GetComponent<Rigidbody>().AddForce(Vector3.up);
}

// GOOD: Cache in Awake
private Rigidbody _rigidbody;

private void Awake()
{
    _rigidbody = GetComponent<Rigidbody>();
}

private void Update()
{
    _rigidbody.AddForce(Vector3.up);
}
```

### Find Caching

```csharp
// BAD: Find every frame
private void Update()
{
    var player = GameObject.FindWithTag("Player");
    _distance = Vector3.Distance(transform.position, player.transform.position);
}

// GOOD: Cache reference
private Transform _playerTransform;

private void Start()
{
    _playerTransform = GameObject.FindWithTag("Player").transform;
}

private void Update()
{
    _distance = Vector3.Distance(transform.position, _playerTransform.position);
}
```

## Object Pooling

### Built-in ObjectPool

```csharp
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

### Simple Manual Pool

```csharp
public class SimplePool<T> where T : Component
{
    private readonly T _prefab;
    private readonly Queue<T> _pool = new();
    private readonly Transform _parent;

    public SimplePool(T prefab, int initialSize, Transform parent = null)
    {
        _prefab = prefab;
        _parent = parent;

        for (int i = 0; i < initialSize; i++)
        {
            var obj = Object.Instantiate(prefab, parent);
            obj.gameObject.SetActive(false);
            _pool.Enqueue(obj);
        }
    }

    public T Get()
    {
        T obj = _pool.Count > 0
            ? _pool.Dequeue()
            : Object.Instantiate(_prefab, _parent);

        obj.gameObject.SetActive(true);
        return obj;
    }

    public void Return(T obj)
    {
        obj.gameObject.SetActive(false);
        _pool.Enqueue(obj);
    }
}
```

## Update Optimization

### Disable When Not Needed

```csharp
// Disable when off-screen
private void OnBecameInvisible()
{
    enabled = false;
}

private void OnBecameVisible()
{
    enabled = true;
}

// Disable when far from player
private void Update()
{
    if (_distanceToPlayer > _disableDistance)
    {
        enabled = false;
        return;
    }
    // Normal update...
}
```

### Throttled Updates

```csharp
// Update every N frames
private int _frameCount;
private const int UPDATE_INTERVAL = 3;

private void Update()
{
    _frameCount++;
    if (_frameCount % UPDATE_INTERVAL != 0) return;

    // Heavy calculations here
    CalculateAI();
}

// Time-based throttle
private float _lastUpdateTime;
private const float UPDATE_RATE = 0.1f;  // 10 times per second

private void Update()
{
    if (Time.time - _lastUpdateTime < UPDATE_RATE) return;
    _lastUpdateTime = Time.time;

    // Heavy calculations here
}
```

### Job System for Heavy Work

```csharp
using Unity.Jobs;
using Unity.Collections;

public struct DistanceJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<Vector3> Positions;
    public Vector3 TargetPosition;
    public NativeArray<float> Distances;

    public void Execute(int index)
    {
        Distances[index] = Vector3.Distance(Positions[index], TargetPosition);
    }
}

// Usage
private void CalculateDistancesParallel()
{
    var positions = new NativeArray<Vector3>(_count, Allocator.TempJob);
    var distances = new NativeArray<float>(_count, Allocator.TempJob);

    // Fill positions...

    var job = new DistanceJob
    {
        Positions = positions,
        TargetPosition = _target.position,
        Distances = distances
    };

    JobHandle handle = job.Schedule(_count, 64);
    handle.Complete();

    // Use distances...

    positions.Dispose();
    distances.Dispose();
}
```

## Physics Optimization

### Layer-Based Collision

```csharp
// Set up collision matrix in Project Settings > Physics
// Only check necessary layers

// Or use layer masks in code
[SerializeField] private LayerMask _enemyLayer;

private void CheckForEnemies()
{
    var hits = Physics.OverlapSphere(transform.position, _range, _enemyLayer);
}
```

### Physics Settings

- Reduce **Fixed Timestep** if acceptable (0.02 → 0.03)
- Use **Solver Iteration Count** appropriate for game
- Enable **Auto Sync Transforms** only if needed
- Use simple colliders (box/sphere) over mesh colliders

### Raycast Optimization

```csharp
// BAD: Multiple raycasts
for (int i = 0; i < 100; i++)
{
    Physics.Raycast(origin, directions[i], out hit);
}

// GOOD: Batch with RaycastCommand (Jobs)
using Unity.Collections;
using Unity.Jobs;

var commands = new NativeArray<RaycastCommand>(100, Allocator.TempJob);
var results = new NativeArray<RaycastHit>(100, Allocator.TempJob);

for (int i = 0; i < 100; i++)
{
    commands[i] = new RaycastCommand(origin, directions[i], QueryParameters.Default);
}

JobHandle handle = RaycastCommand.ScheduleBatch(commands, results, 32);
handle.Complete();

// Process results...

commands.Dispose();
results.Dispose();
```

## Rendering Optimization

### Static Batching

- Mark non-moving objects as **Static**
- Combines meshes at build time
- Reduces draw calls

### LOD Groups

```csharp
// Set up LOD Group component on complex objects
// LOD0: Full detail (close)
// LOD1: Medium detail (mid)
// LOD2: Low detail (far)
// Culled: Not rendered
```

### Occlusion Culling

- Enable in Window > Rendering > Occlusion Culling
- Bake occlusion data
- Prevents rendering of hidden objects

### GPU Instancing

```csharp
// Enable GPU Instancing on materials
// For many identical objects (trees, grass, etc.)

// Or use Graphics.DrawMeshInstanced
Graphics.DrawMeshInstanced(mesh, 0, material, matrices);
```

## Memory Management

### Addressables

```csharp
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;

// Load async
AsyncOperationHandle<GameObject> handle = Addressables.LoadAssetAsync<GameObject>("Prefabs/Enemy");
handle.Completed += OnEnemyLoaded;

// Unload when done
Addressables.Release(handle);
```

### Texture Compression

- Use appropriate compression formats
- Lower resolution for distant objects
- Use texture atlases
- Enable **Generate Mipmaps** for 3D

## Profiling

### Unity Profiler

```csharp
using UnityEngine.Profiling;

private void Update()
{
    Profiler.BeginSample("MyHeavyOperation");
    HeavyOperation();
    Profiler.EndSample();
}
```

### Frame Debugger

- Window > Analysis > Frame Debugger
- See every draw call
- Identify batching issues

### Memory Profiler

- Window > Analysis > Memory Profiler
- Take snapshots
- Compare memory usage

## Checklist

- [ ] No allocations in Update loops
- [ ] Components cached in Awake
- [ ] Object pooling for frequently spawned objects
- [ ] Physics on appropriate layers only
- [ ] Static objects marked as Static
- [ ] LODs for complex meshes
- [ ] Profiler shows no spikes
- [ ] Memory usage is stable
