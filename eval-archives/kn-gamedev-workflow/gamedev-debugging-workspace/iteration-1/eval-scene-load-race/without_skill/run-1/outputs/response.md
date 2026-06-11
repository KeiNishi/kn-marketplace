# Do Not Keep the 0.5-Second Wait — Here Is the Real Fix

**Short answer: No.** The `await get_tree().create_timer(0.5).timeout` workaround is a classic race-condition band-aid. It passes most of the time because 0.5 s is usually longer than the load, but on a slow device, a large scene, or under memory pressure the crash will return. The correct fix is to synchronize on the actual readiness event, not on wall-clock time.

---

## Why the Crash Happens

When you call `get_tree().change_scene_to_file(path)` (Godot 4) or `get_tree().change_scene(path)` (Godot 3), Godot queues the scene swap. The new scene's root node and all its children go through `_enter_tree()` → `_ready()` in the **next processing frame** (or later, if the load is deferred). Any code that runs in the **same frame** right after `change_scene_to_file` may find:

- child nodes not yet added to the tree (`null` when accessed via `$NodePath`)
- `_ready()` not yet called, so exported variables / autoload references inside the new scene are uninitialized
- `NavigationAgent`, `AnimationPlayer`, physics bodies, etc. whose internal state is not yet set

The 0.5 s timer "works" because it accidentally skips past the frame(s) where the scene is still loading. That is a coincidence, not a guarantee.

---

## Fix 1 — `await` the Scene Tree Signal (Godot 4)

This is the simplest targeted fix if the spawning code lives in the scene manager or a singleton.

```gdscript
# SceneManager.gd
extends Node

func change_scene_and_spawn(path: String) -> void:
    get_tree().change_scene_to_file(path)

    # tree_changed fires after the old scene is freed and the new
    # scene's _ready() chain has completed.
    await get_tree().tree_changed

    # Safe to access the new scene now.
    spawn_enemies()
```

> **Godot 3 equivalent:** `await` does not exist; use `yield(get_tree(), "idle_frame")` once or twice, or connect to `SceneTree.node_added`.

---

## Fix 2 — `call_deferred` on Post-Load Work

If you cannot `await` (e.g., you are in a non-async context), push the work one frame forward with `call_deferred`.

```gdscript
# EnemySpawner.gd
extends Node

@export var enemy_scene: PackedScene

func spawn_enemies() -> void:
    for i in range(5):
        var enemy = enemy_scene.instantiate()
        add_child(enemy)
        # _ready() runs synchronously inside add_child().
        # call_deferred schedules setup_navigation for AFTER
        # the current frame's _ready() propagation finishes.
        enemy.call_deferred("setup_navigation")

# Enemy.gd
func setup_navigation() -> void:
    # NavigationAgent3D is guaranteed initialized by now.
    $NavigationAgent3D.target_position = Vector3.ZERO
```

---

## Fix 3 — Emit a Signal from `_ready()` (Recommended for Larger Projects)

The cleanest and most decoupled pattern: have the enemy announce its own readiness.

```gdscript
# Enemy.gd
extends CharacterBody3D

signal ready_for_use

func _ready() -> void:
    # All child nodes are fully initialized inside _ready().
    $NavigationAgent3D.target_position = Vector3.ZERO
    ready_for_use.emit()


# EnemySpawner.gd
extends Node

@export var enemy_scene: PackedScene

func spawn_and_configure() -> void:
    var enemy = enemy_scene.instantiate()
    # Connect BEFORE add_child so the signal isn't missed.
    enemy.ready_for_use.connect(_on_enemy_ready.bind(enemy), CONNECT_ONE_SHOT)
    add_child(enemy)   # triggers _ready() → emits ready_for_use

func _on_enemy_ready(enemy: Node) -> void:
    # Runs after Enemy._ready() — fully safe.
    pass
```

---

## Which Fix to Choose

| Situation | Recommended fix |
|---|---|
| Simple project, one place that switches scenes | Fix 1: `await get_tree().tree_changed` |
| Cannot `await` (callback-style code) | Fix 2: `call_deferred` |
| Enemies have complex multi-step init or are spawned from many places | Fix 3: `ready_for_use` signal |

---

## What to Verify After the Fix

1. Remove the `await get_tree().create_timer(0.5).timeout` line entirely.
2. Run the scene-switch 50+ times in a row (a simple loop in a test script, or use Godot's built-in profiler).
3. Confirm no null-instance errors appear in the Output panel.
4. Test on a target device (mobile / lower-end hardware) where load times are longer — this is where the 0.5 s timer would have eventually failed.

Because Godot's `_ready()` is synchronous within `add_child`, Fix 2 and Fix 3 are deterministic and do not depend on timing at all. Fix 1 is also deterministic because `tree_changed` is a real completion event, not a timeout.
