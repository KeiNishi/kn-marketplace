# Godot 4 Architecture Refactor: Enemy Scene & Item Database

Your current setup has two architectural problems worth addressing properly:

1. **Fragile scene-tree traversal**: `get_parent().get_parent().get_node("UI/HealthBar")` is tightly coupled to a specific scene hierarchy. Rename a node, restructure the tree, or reuse the Enemy in another scene and it breaks silently at runtime.

2. **Nodes as data containers**: Using Nodes with exported fields under a hidden `ItemDatabase` node conflates scene/gameplay objects with pure data. Nodes carry rendering, physics, and signal overhead that item definitions don't need, and the data lives in the scene tree making it hard to serialize, version, or load dynamically.

Below are the corrected patterns for both.

---

## 1. Decoupling the Enemy from the UI: use a Signal

Instead of reaching up the tree, the Enemy emits a signal. Whatever owns the `HealthBar` connects to it — the Enemy never needs to know the UI exists.

### `enemy.gd`

```gdscript
extends CharacterBody2D

signal health_changed(new_health: int, max_health: int)

@export var max_health: int = 100
var current_health: int

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    current_health = clamp(current_health - amount, 0, max_health)
    health_changed.emit(current_health, max_health)
    if current_health == 0:
        die()

func die() -> void:
    queue_free()
```

### `health_bar.gd`

```gdscript
extends ProgressBar

func _ready() -> void:
    # Connection is wired in the scene or by the owning script — not by Enemy.
    pass

func update_value(new_health: int, max_health: int) -> void:
    max_value = max_health
    value = new_health
```

### Connecting them (e.g. in `game.gd` or the Enemy's parent scene)

```gdscript
extends Node

@onready var enemy: Enemy = $Enemy
@onready var health_bar: HealthBar = $UI/HealthBar

func _ready() -> void:
    enemy.health_changed.connect(health_bar.update_value)
```

The Enemy emits data; the scene that owns both the Enemy and the UI wires them together. Restructuring the UI or reusing the Enemy in a different scene requires no changes to `enemy.gd`.

---

## 2. Replacing Node-based item definitions with Resources

`Resource` is Godot's built-in lightweight data container. It has no transform, no physics, no rendering — just fields and methods. Item definitions are saved as `.tres` or `.res` files on disk, loaded on demand, and fully serializable.

### `item_definition.gd` — define the data schema once

```gdscript
class_name ItemDefinition
extends Resource

@export var id: StringName = ""
@export var display_name: String = ""
@export var description: String = ""
@export var icon: Texture2D
@export var max_stack: int = 1
@export var base_value: int = 0
```

Create individual items in the Godot editor: **Resource → New Resource → ItemDefinition**, fill in the fields, and save each as e.g. `res://items/sword.tres`.

### `item_database.gd` — an Autoload singleton that owns all definitions

```gdscript
class_name ItemDatabase
extends Node

# Drag-and-drop your .tres files here in the Inspector, or load them at runtime.
@export var items: Array[ItemDefinition] = []

# Internal lookup table built at startup.
var _by_id: Dictionary = {}

func _ready() -> void:
    for item in items:
        if item.id == "":
            push_warning("ItemDatabase: item with empty id skipped.")
            continue
        _by_id[item.id] = item

func get_item(id: StringName) -> ItemDefinition:
    if not _by_id.has(id):
        push_error("ItemDatabase: unknown item id '%s'" % id)
        return null
    return _by_id[id]

func all_items() -> Array[ItemDefinition]:
    return items
```

Register `item_database.gd` as an **Autoload** in Project → Project Settings → Autoload (name it `ItemDatabase`). Now any script can call:

```gdscript
var sword: ItemDefinition = ItemDatabase.get_item(&"sword")
```

No scene-tree traversal, no hidden nodes, no coupling to where the database lives in the hierarchy.

---

## Why these changes are not workarounds

| Old approach | Problem | New approach | Why it's a root fix |
|---|---|---|---|
| `get_parent().get_parent().get_node(...)` | Hardcodes scene structure; breaks on any rename or move | Signal emitted by Enemy, connected by the owning scene | Enemy has zero knowledge of UI; connection point is the scene that owns both |
| Node with exported fields under a hidden scene node | Conflates scene objects with data; fragile reference, not serializable | `Resource` subclass + Autoload singleton | Data is pure, versioned as files, loadable from anywhere, no tree dependency |

Both fixes address the structural cause — tight coupling — rather than papering over it.
