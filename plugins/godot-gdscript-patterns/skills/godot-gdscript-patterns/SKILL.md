---
name: godot-gdscript-patterns
description: This skill should be used when writing or reviewing GDScript for Godot 4.x — .gd scripts, .tscn scenes, .tres resources — or designing Godot game architecture. Covers state machines, autoload singletons and event buses, signals, @export/@onready annotations, _ready/_process lifecycle, CharacterBody2D/CharacterBody3D movement, Resource-based data, object pooling, component systems (health/hitbox/hurtbox), scene tree and async scene loading, save systems, and Node vs RefCounted vs Resource choices. Use when the user mentions Godot, GDScript, autoload, signal, scene tree, "state machine in Godot", "RefCounted vs Node", "Godot save system", or asks how to structure, refactor, or optimize a Godot project.
---

# Godot GDScript Patterns

Production architecture patterns for Godot 4.x GDScript. Apply the rules below
to every line of GDScript produced, and load the matching reference file
before implementing a pattern.

## Non-Negotiable Rules

1. **Signals up, calls down.** A node may call methods on its children; it
   must never reach up or sideways with `get_parent()` or `$"../.."` — emit a
   signal instead. WHY: upward coupling breaks the moment a scene is reused or
   rearranged.
2. **Type everything.** Every variable, parameter, and return value
   (`var speed: float = 200.0`, `-> void`, `:=` inference). WHY: typed
   GDScript catches errors at parse time and executes faster.
3. **Resource for data, Node for behavior.** Stats, items, and configs extend
   `Resource` (saved as `.tres`); never model pure data as Nodes. WHY:
   Resources serialize, edit in the Inspector, and have no scene-tree cost.
4. **Composition over inheritance.** Build entities from component child
   nodes (HealthComponent, Hitbox) instead of deep class hierarchies. WHY:
   deep `extends` chains make behavior impossible to mix and match.
5. **Godot 4 syntax only.** `await` not `yield`; `signal_name.connect(callable)`
   not string-based `connect`; `@export`/`@onready` annotations. WHY: Godot 3
   idioms fail to parse or silently misbehave in Godot 4.
6. **No `get_node()` string paths across scene boundaries.** Inside one scene,
   `$Path` and `%UniqueName` are fine; across scenes use `@export var`
   references, signals, or groups. WHY: string paths into another scene break
   on any rearrangement and fail only at runtime.
7. **Cache node references with `@onready`.** Never call `$Sprite2D` or
   `get_node()` inside `_process()`. WHY: per-frame tree lookups are a hidden
   hot-path cost.
8. **Use `_unhandled_input()` for gameplay input**, `_input()` only when input
   must preempt UI. WHY: `_input()` steals events before Control nodes see them.
9. **Autoloads only for truly global systems** (scene manager, save manager,
   event bus) — never as a junk drawer of shared variables. WHY: global state
   couples everything to everything.
10. **Configure nodes before `add_child()`.** Set position and properties on
    the instance first. WHY: configuring after entering the tree fires extra
    notifications and transform updates.

## Decision Tree

- Building player/enemy behavior with distinct modes (idle/run/attack)?
  → `references/state-machine.md`
- Sharing data or broadcasting events between scenes (game manager, event bus)?
  → `references/autoload-singletons.md`
- Defining game data (weapons, items, stats, configs)?
  → `references/resource-data.md`
- Spawning bullets/particles/enemies frequently?
  → `references/object-pooling.md`
- Reusing health/hitbox/hurtbox behavior across entities?
  → `references/component-system.md`
- Switching levels, loading screens, async loading?
  → `references/scene-management.md`
- Saving/loading player progress?
  → `references/save-system.md`
- Writing a class that never needs the scene tree?
  → `references/node-alternatives.md`
- Needing interfaces/polymorphism (duck typing, groups, `has_method`)?
  → `references/godot-interfaces.md`
- Confused about `_init` vs `_ready` vs `_enter_tree`, or input order?
  → `references/notifications-lifecycle.md`
- Optimizing performance, choosing preload vs load, scenes vs scripts?
  → `references/performance-and-loading.md`

## Canonical Style

Every GDScript file follows this shape:

```gdscript
class_name Player
extends CharacterBody2D

signal health_changed(new_health: int)
signal died

@export var speed: float = 200.0
@export var max_health: int = 100

@onready var sprite: Sprite2D = $Sprite2D
@onready var animation: AnimationPlayer = $AnimationPlayer

var _health: int  # Private: underscore prefix

func _ready() -> void:
    _health = max_health

func _physics_process(_delta: float) -> void:
    var direction := Input.get_vector("left", "right", "up", "down")
    velocity = direction * speed
    move_and_slide()

func take_damage(amount: int) -> void:
    _health = maxi(_health - amount, 0)
    health_changed.emit(_health)
    if _health <= 0:
        died.emit()
```

Order: `class_name` → `extends` → signals → `@export` → `@onready` → variables
→ lifecycle methods → public methods → private methods.

## Verification Checklist

Before declaring GDScript work complete, confirm every item:

- [ ] All variables, parameters, and return types are statically typed
- [ ] No Godot 3 syntax (`yield`, `export`/`onready` without `@`,
      `connect("sig", self, "method")`)
- [ ] No `get_node()`/`$` string paths crossing scene boundaries; no logic
      calls through `get_parent()`
- [ ] Signals flow up, method calls flow down
- [ ] Signal connections are consistent — connected in code OR in the scene
      editor, not a mix for the same system
- [ ] Pure data types extend `Resource` or `RefCounted`, not `Node`
- [ ] No allocations or node lookups inside `_process`/`_physics_process`
- [ ] Frequently spawned objects are pooled

## Additional Resources

- [Godot Documentation](https://docs.godotengine.org/en/stable/)
- [GDQuest Tutorials](https://www.gdquest.com/)
- [Godot Recipes](https://kidscancode.org/godot_recipes/)
