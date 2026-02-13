---
name: godot-gdscript-patterns
description: This skill should be used when working with Godot 4 GDScript patterns and best practices. Covers state machines, autoload singletons, event bus, resource-based data, object pooling, component systems (health, hitbox, hurtbox), scene management with async loading, save systems, node alternatives (Object, RefCounted, Resource vs Node), duck typing and interface patterns, and node lifecycle notifications. Use for questions like "how to implement a state machine in GDScript", "Godot signal patterns", "when to use RefCounted vs Node", "GDScript object pooling", "Godot save system", or "node lifecycle order in Godot 4".
---

# Godot GDScript Patterns

Production patterns for Godot 4.x game development with GDScript, covering architecture, signals, scenes, and optimization.

## When to Use This Skill

- Building games with Godot 4
- Implementing game systems in GDScript
- Designing scene architecture
- Managing game state
- Optimizing GDScript performance
- Learning Godot best practices
- Choosing between Node, RefCounted, Resource, and Object
- Understanding node lifecycle and notifications
- Implementing duck typing and interface patterns

## Core Concepts

### 1. Godot Architecture

```
Node: Base building block
├── Scene: Reusable node tree (saved as .tscn)
├── Resource: Data container (saved as .tres)
├── Signal: Event communication
└── Group: Node categorization
```

### 2. GDScript Basics

```gdscript
class_name Player
extends CharacterBody2D

# Signals
signal health_changed(new_health: int)
signal died

# Exports (Inspector-editable)
@export var speed: float = 200.0
@export var max_health: int = 100
@export_range(0, 1) var damage_reduction: float = 0.0
@export_group("Combat")
@export var attack_damage: int = 10
@export var attack_cooldown: float = 0.5

# Onready (initialized when ready)
@onready var sprite: Sprite2D = $Sprite2D
@onready var animation: AnimationPlayer = $AnimationPlayer
@onready var hitbox: Area2D = $Hitbox

# Private variables (convention: underscore prefix)
var _health: int
var _can_attack: bool = true

func _ready() -> void:
    _health = max_health

func _physics_process(delta: float) -> void:
    var direction := Input.get_vector("left", "right", "up", "down")
    velocity = direction * speed
    move_and_slide()

func take_damage(amount: int) -> void:
    var actual_damage := int(amount * (1.0 - damage_reduction))
    _health = max(_health - actual_damage, 0)
    health_changed.emit(_health)

    if _health <= 0:
        died.emit()
```

## Available Patterns

This skill provides 10 production-ready patterns. Each pattern is documented in detail in the `references/` directory.

| Pattern | File | Description |
|---------|------|-------------|
| State Machine | `references/state-machine.md` | Generic state machine with transitions |
| Autoload Singletons | `references/autoload-singletons.md` | Game manager and event bus |
| Resource-based Data | `references/resource-data.md` | Data containers with Resources |
| Object Pooling | `references/object-pooling.md` | Efficient object reuse |
| Component System | `references/component-system.md` | Health, hitbox, hurtbox components |
| Scene Management | `references/scene-management.md` | Async scene loading with transitions |
| Save System | `references/save-system.md` | Encrypted save/load with saveable nodes |
| Node Alternatives | `references/node-alternatives.md` | Object, RefCounted, Resource vs Node |
| Godot Interfaces | `references/godot-interfaces.md` | Duck typing, references, type-safe access |
| Notifications & Lifecycle | `references/notifications-lifecycle.md` | Node lifecycle, process methods, input flow |

## Performance Tips

```gdscript
# 1. Cache node references
@onready var sprite := $Sprite2D  # Good
# $Sprite2D in _process()  # Bad - repeated lookup

# 2. Use object pooling for frequent spawning
# See references/object-pooling.md

# 3. Avoid allocations in hot paths
var _reusable_array: Array = []

func _process(_delta: float) -> void:
    _reusable_array.clear()  # Reuse instead of creating new

# 4. Use static typing
func calculate(value: float) -> float:  # Good
    return value * 2.0

# 5. Disable processing when not needed
func _on_off_screen() -> void:
    set_process(false)
    set_physics_process(false)
```

## Scenes vs Scripts

Choose based on what you're creating:

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

## Logic Preferences

### Preload vs Load

```gdscript
# preload() - compile-time, blocking, instant access
# Use for: small/essential resources always needed
const BulletScene := preload("res://scenes/bullet.tscn")
const HitEffect := preload("res://effects/hit.tscn")

# load() / ResourceLoader - runtime, can be deferred
# Use for: large resources, optional content
func _load_level(path: String) -> void:
    var scene := load(path) as PackedScene  # Blocks until loaded

# ResourceLoader - async loading for large assets
func _load_level_async(path: String) -> void:
    ResourceLoader.load_threaded_request(path)
    # Check progress in _process or await
```

### Node Setup Order

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

### Static vs Dynamic Levels

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

## Best Practices

### Do's
- **Use signals for decoupling** - Avoid direct references
- **Type everything** - Static typing catches errors
- **Use resources for data** - Separate data from logic
- **Pool frequently spawned objects** - Avoid GC hitches
- **Use Autoloads sparingly** - Only for truly global systems
- **Use `_unhandled_input` for gameplay** - Don't steal input from UI
- **Choose the right base class** - Not everything needs to be a Node (see `references/node-alternatives.md`)
- **Use groups as interfaces** - `is_in_group()` for duck typing (see `references/godot-interfaces.md`)

### Don'ts
- **Don't use `get_node()` in loops** - Cache references
- **Don't couple scenes tightly** - Use signals
- **Don't put logic in resources** - Keep them data-only
- **Don't ignore the Profiler** - Monitor performance
- **Don't fight the scene tree** - Work with Godot's design
- **Don't do heavy work in `_init()`** - No scene tree access yet
- **Don't use Node for pure data** - Use RefCounted or Resource instead

## Additional Resources

### External Links

- [Godot Documentation](https://docs.godotengine.org/en/stable/)
- [GDQuest Tutorials](https://www.gdquest.com/)
- [Godot Recipes](https://kidscancode.org/godot_recipes/)
