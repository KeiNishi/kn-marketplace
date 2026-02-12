---
name: godot-gdscript-patterns
description: Master Godot 4 GDScript patterns including signals, scenes, state machines, and optimization. Use when building Godot games, implementing game systems, or learning GDScript best practices.
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

This skill provides 7 production-ready patterns. Each pattern is documented in detail in the `references/` directory.

| Pattern | File | Description |
|---------|------|-------------|
| State Machine | `references/state-machine.md` | Generic state machine with transitions |
| Autoload Singletons | `references/autoload-singletons.md` | Game manager and event bus |
| Resource-based Data | `references/resource-data.md` | Data containers with Resources |
| Object Pooling | `references/object-pooling.md` | Efficient object reuse |
| Component System | `references/component-system.md` | Health, hitbox, hurtbox components |
| Scene Management | `references/scene-management.md` | Async scene loading with transitions |
| Save System | `references/save-system.md` | Encrypted save/load with saveable nodes |

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

## Best Practices

### Do's
- **Use signals for decoupling** - Avoid direct references
- **Type everything** - Static typing catches errors
- **Use resources for data** - Separate data from logic
- **Pool frequently spawned objects** - Avoid GC hitches
- **Use Autoloads sparingly** - Only for truly global systems

### Don'ts
- **Don't use `get_node()` in loops** - Cache references
- **Don't couple scenes tightly** - Use signals
- **Don't put logic in resources** - Keep them data-only
- **Don't ignore the Profiler** - Monitor performance
- **Don't fight the scene tree** - Work with Godot's design

## Additional Resources

### Reference Files

Detailed pattern implementations in `references/`:
- **`state-machine.md`** - StateMachine, State base class, usage example
- **`autoload-singletons.md`** - GameManager, EventBus patterns
- **`resource-data.md`** - WeaponData, CharacterStats, runtime copies
- **`object-pooling.md`** - ObjectPool, PooledBullet examples
- **`component-system.md`** - HealthComponent, HitboxComponent, HurtboxComponent
- **`scene-management.md`** - Async loading, transitions, SceneManager
- **`save-system.md`** - Encrypted save/load, Saveable component

### External Links

- [Godot Documentation](https://docs.godotengine.org/en/stable/)
- [GDQuest Tutorials](https://www.gdquest.com/)
- [Godot Recipes](https://kidscancode.org/godot_recipes/)
