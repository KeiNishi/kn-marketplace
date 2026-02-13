# Godot Interfaces Pattern

Duck typing, node references, and type-safe access patterns in Godot 4.x. Godot uses composition and duck typing instead of traditional interfaces.

## Acquiring Node References

### Direct References

```gdscript
# @onready - resolved when _ready() is called
@onready var sprite: Sprite2D = $Sprite2D
@onready var health: HealthComponent = $HealthComponent
@onready var timer: Timer = $Timers/AttackCooldown

# @export - set in Inspector, works across scenes
@export var target: Node2D
@export var weapon_data: WeaponData
@export var spawn_point: Marker2D
```

### Finding Nodes

```gdscript
# By path (relative to current node)
var child := get_node("Child/GrandChild")

# By unique name (scene-wide, prefixed with %)
# Mark a node as "unique name" in the editor
@onready var player: Player = %Player  # Anywhere in same scene

# By group
var enemies := get_tree().get_nodes_in_group("enemies")
for enemy in enemies:
    enemy.take_damage(10)

# By class
var cameras := get_tree().get_nodes_in_group("cameras")
# Or iterate children:
for child in get_children():
    if child is Camera2D:
        child.enabled = false
```

### Owner vs Parent

```gdscript
# get_parent() - direct parent in scene tree
var parent := get_parent()

# owner - root node of the scene this node belongs to
# Useful for finding the "main" node of a scene
var scene_root := owner  # e.g., Player node for Player scene
```

## Duck Typing

Godot supports duck typing: check if an object has a method or property before calling it, instead of requiring a specific type.

### has_method() Pattern

```gdscript
# Apply damage to anything that can take it
func deal_damage_to(target: Node, amount: int) -> void:
    if target.has_method("take_damage"):
        target.take_damage(amount)

# Interact with anything interactable
func interact_with(target: Node) -> void:
    if target.has_method("interact"):
        target.interact(self)

# Save any saveable node
func save_node(node: Node) -> Dictionary:
    if node.has_method("save"):
        return node.save()
    return {}
```

### has_signal() Pattern

```gdscript
# Connect to a signal only if it exists
func setup_connection(target: Node) -> void:
    if target.has_signal("health_changed"):
        target.health_changed.connect(_on_target_health_changed)
```

### Group-Based Interface

Groups act as a lightweight tagging system, similar to interfaces.

```gdscript
# In the damageable nodes, add to group "damageable"
func _ready() -> void:
    add_to_group("damageable")

# Caller checks group membership
func explode(radius: float) -> void:
    for body in $ExplosionArea.get_overlapping_bodies():
        if body.is_in_group("damageable"):
            body.take_damage(explosion_damage)

# Broadcast to all members of a group
func alert_all_enemies() -> void:
    get_tree().call_group("enemies", "alert", player.position)
```

## Type-Safe Access

### is Keyword (Type Checking)

```gdscript
func _on_body_entered(body: Node2D) -> void:
    if body is Player:
        # body is now known to be Player
        body.collect_coin(value)

    elif body is Enemy:
        body.take_damage(spike_damage)
```

### as Keyword (Safe Casting)

```gdscript
func _on_area_entered(area: Area2D) -> void:
    # Returns null if cast fails (instead of error)
    var hurtbox := area as HurtboxComponent
    if hurtbox:
        hurtbox.receive_hit(self)
```

### Combining Type Safety with Duck Typing

```gdscript
# Prefer type checking when you know the expected type
func _on_body_entered(body: Node2D) -> void:
    if body is Player:
        body.add_score(points)
        queue_free()

# Use duck typing when multiple unrelated types share behavior
func apply_status_effect(target: Node) -> void:
    if target.has_method("add_status"):
        target.add_status("poison", 5.0)
```

## Callable Pattern

Use `Callable` for flexible function references without coupling to specific types.

```gdscript
# Deferred actions
var _on_complete: Callable

func start_action(callback: Callable) -> void:
    _on_complete = callback
    # ... do work ...

func _finish() -> void:
    if _on_complete.is_valid():
        _on_complete.call()

# Usage
enemy.start_action(func(): print("Action done"))
enemy.start_action(player.on_enemy_defeated)
```

## Best Practices

### Do's
- **Use `@export` for cross-scene references** — Set in Inspector, visible and editable
- **Use groups for broadcast communication** — `call_group()` is clean and decoupled
- **Use `%` unique names for intra-scene references** — More robust than path-based `$`
- **Prefer type checking (`is`) when types are known** — Catches errors at parse time

### Don'ts
- **Don't use `get_node()` with long paths** — Fragile, breaks on renames
- **Don't over-use duck typing** — If you always expect a Player, type it as Player
- **Don't store references to freed nodes** — Use `is_instance_valid()` to check
- **Don't connect signals to freed nodes** — Disconnect in `_exit_tree()`

```gdscript
# Always validate external references
func _process(_delta: float) -> void:
    if is_instance_valid(target):
        look_at(target.global_position)
    else:
        target = null
```
