# Godot 4 Architecture Refactor

Your current code has two architectural problems that violate Godot best practices. Here is what is wrong and how to fix both.

---

## Problem 1: `get_parent().get_parent().get_node("UI/HealthBar")` in Enemy script

**Why it is wrong**

This breaks Rule 1 ("Signals up, calls down") and Rule 6 ("No `get_node()` string paths across scene boundaries"). The Enemy node reaches upward and sideways through the tree to grab a UI node it has no business knowing about. The moment you move the Enemy into a different scene, or rename `UI/HealthBar`, or reuse the Enemy scene, the call fails at runtime with no warning at parse time.

**The fix: emit a signal from Enemy; let the scene root wire it to the UI**

The Enemy emits `damaged`; the root scene (or a HealthComponent) connects that signal to the HealthBar. The Enemy knows nothing about UI.

```gdscript
# enemy.gd
class_name Enemy
extends CharacterBody2D

signal damaged(amount: int)

@export var max_health: int = 100

@onready var health_component: HealthComponent = $HealthComponent

func _ready() -> void:
    health_component.health_changed.connect(_on_health_changed)
    health_component.died.connect(_on_died)

func take_hit(amount: int) -> void:
    health_component.take_damage(amount)

func _on_health_changed(current: int, _maximum: int) -> void:
    damaged.emit(current)

func _on_died() -> void:
    queue_free()
```

```gdscript
# health_component.gd  (place as a child node of Enemy)
class_name HealthComponent
extends Node

signal health_changed(current: int, maximum: int)
signal died

@export var max_health: int = 100

var current_health: int:
    set(value):
        var old := current_health
        current_health = clampi(value, 0, max_health)
        if current_health != old:
            health_changed.emit(current_health, max_health)

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    current_health -= amount
    if current_health <= 0:
        died.emit()
```

In the scene that contains both the Enemy and the UI, wire the signal — either in `_ready()` or in the scene editor:

```gdscript
# main_scene.gd  (or level.gd — the scene that owns both Enemy and HealthBar)
class_name MainScene
extends Node2D

@onready var enemy: Enemy = $Enemy
@onready var health_bar: HealthBar = $UI/HealthBar

func _ready() -> void:
    enemy.damaged.connect(health_bar.update_value)
```

The HealthBar's `update_value` just accepts an `int`:

```gdscript
# health_bar.gd
class_name HealthBar
extends TextureProgressBar

func update_value(new_health: int) -> void:
    value = new_health
```

Signal flows up from Enemy → parent scene receives it → calls down into UI. The Enemy scene is now fully self-contained and reusable.

---

## Problem 2: Item definitions stored as Nodes under a hidden `ItemDatabase` node

**Why it is wrong**

This breaks Rule 3 ("Resource for data, Node for behavior"). Nodes carry scene-tree overhead (process callbacks, transforms, parent/child linkage) and cannot be saved or edited cleanly as standalone assets. A hidden Node tree is also invisible to the Inspector and cannot be serialized to `.tres` files.

**The fix: extend `Resource` for each item type; load them with `preload`**

```gdscript
# item_data.gd
class_name ItemData
extends Resource

@export var id: StringName
@export var display_name: String
@export var description: String
@export var icon: Texture2D
@export var max_stack: int = 1
@export var value: int = 0
```

Create one `.tres` file per item in the editor (right-click in FileSystem → New Resource → ItemData). For example, `res://items/sword.tres`:

```
[gd_resource type="Resource" script_class="ItemData" ...]
[resource]
script = ExtResource("item_data.gd")
id = &"sword"
display_name = "Iron Sword"
description = "A basic iron sword."
max_stack = 1
value = 50
```

Then replace the hidden Node database with a typed `ItemDatabase` autoload (or a plain Resource) that holds an array:

```gdscript
# item_database.gd  (Project Settings > Autoload as "ItemDatabase")
class_name ItemDatabaseAutoload
extends Node

# Populate these in the Inspector after adding as Autoload,
# or use preload for a fully code-driven approach.
@export var items: Array[ItemData] = []

var _index: Dictionary = {}   # StringName -> ItemData

func _ready() -> void:
    for item: ItemData in items:
        _index[item.id] = item

func get_item(id: StringName) -> ItemData:
    return _index.get(id, null)
```

Any script that needs item data asks the autoload directly — no scene-tree path needed:

```gdscript
# inventory.gd
class_name Inventory
extends Node

func add_item(id: StringName) -> void:
    var data: ItemData = ItemDatabase.get_item(id)
    if data == null:
        push_error("Unknown item id: %s" % id)
        return
    # ... inventory logic using data.display_name, data.icon, etc.
```

---

## Summary of what changed and why

| Before | After | Rule fixed |
|---|---|---|
| `get_parent().get_parent().get_node("UI/HealthBar").update_value()` inside Enemy | Enemy emits `damaged` signal; scene root connects it to HealthBar | Rule 1, Rule 6 |
| Item definitions as child Nodes of a hidden `ItemDatabase` node in the main scene | `ItemData` extends `Resource`, stored as `.tres` files; accessed via autoload | Rule 3 |
| No HealthComponent — health logic inline in Enemy | `HealthComponent` child node handles health, signals, and death | Rule 4 (composition) |

Both changes make your scenes independently reusable: the Enemy can be dropped into any scene without carrying knowledge of the UI tree, and items are now serializable `.tres` assets that work in the Inspector, in the editor, and across any scene.
