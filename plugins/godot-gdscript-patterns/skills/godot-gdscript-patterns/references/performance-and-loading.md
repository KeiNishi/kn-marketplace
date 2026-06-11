# Performance and Loading Pattern

Performance habits, resource loading strategies, and structural choices for
Godot 4.x.

## Contents

- [Performance Tips](#performance-tips)
- [Preload vs Load](#preload-vs-load)
- [Node Setup Order](#node-setup-order)
- [Scenes vs Scripts](#scenes-vs-scripts)
- [Static vs Dynamic Levels](#static-vs-dynamic-levels)

## Performance Tips

```gdscript
# 1. Cache node references
@onready var sprite := $Sprite2D  # Good
# $Sprite2D in _process()  # Bad - repeated tree lookup every frame

# 2. Use object pooling for frequent spawning
# See object-pooling.md

# 3. Avoid allocations in hot paths
var _reusable_array: Array = []

func _process(_delta: float) -> void:
    _reusable_array.clear()  # Reuse instead of creating new

# 4. Use static typing - parse-time checks and faster execution
func calculate(value: float) -> float:
    return value * 2.0

# 5. Disable processing when not needed
func _on_off_screen() -> void:
    set_process(false)
    set_physics_process(false)
```

Profile before optimizing: use the built-in Profiler (Debugger > Profiler)
to find actual hot spots instead of guessing.

## Preload vs Load

```gdscript
# preload() - compile-time, blocking, instant access
# Use for: small/essential resources always needed
const BulletScene := preload("res://scenes/bullet.tscn")
const HitEffect := preload("res://effects/hit.tscn")

# load() - runtime, blocking
# Use for: resources chosen at runtime that are acceptable to block on
func _load_level(path: String) -> void:
    var scene := load(path) as PackedScene  # Blocks until loaded

# ResourceLoader threaded API - async loading for large assets
func _load_level_async(path: String) -> void:
    ResourceLoader.load_threaded_request(path)
    # Poll load_threaded_get_status() in _process, then load_threaded_get()
    # See scene-management.md for a complete implementation
```

## Node Setup Order

```gdscript
# GOOD: Configure before adding to tree (fewer notifications)
var enemy := EnemyScene.instantiate()
enemy.position = spawn_point.position
enemy.speed = 150.0
add_child(enemy)

# LESS IDEAL: Adding then configuring (triggers extra updates)
var enemy2 := EnemyScene.instantiate()
add_child(enemy2)
enemy2.position = spawn_point.position  # Triggers transform update
enemy2.speed = 150.0
```

## Scenes vs Scripts

Choose based on what is being created:

| Use Scenes When | Use Scripts When |
|-----------------|------------------|
| Reusable visual objects (enemies, items, UI) | Pure logic or behavior on existing nodes |
| Multiple nodes with hierarchy | Simple data types without visual representation |
| Need instancing across project | Lightweight, anonymous types |
| Named types with visual composition | Extending built-in node behavior |

```gdscript
# Named type (Scene + Script) - for reusable game objects
# Player.tscn with player.gd attached to root

# Anonymous type (Script only) - for logic/utilities
class_name DamageCalculator
extends RefCounted

static func calculate(base: int, multiplier: float) -> int:
    return int(base * multiplier)
```

## Static vs Dynamic Levels

```gdscript
# Static: Entire level pre-built in editor
# + Easy to design, visual editing, no runtime cost
# - High memory usage, long load times for large levels

# Dynamic: Stream/generate content at runtime
# + Low memory, infinite worlds possible
# - More complex code, potential hitches

# Hybrid approach: chunk-based loading
func _load_chunk(chunk_pos: Vector2i) -> void:
    var path := "res://levels/chunk_%d_%d.tscn" % [chunk_pos.x, chunk_pos.y]
    if ResourceLoader.exists(path):
        ResourceLoader.load_threaded_request(path)
```
