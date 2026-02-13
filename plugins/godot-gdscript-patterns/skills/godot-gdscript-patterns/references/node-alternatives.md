# Node Alternatives Pattern

When and how to avoid using nodes for everything in Godot 4.x. Use lightweight base classes for data and logic that don't need the scene tree.

## Class Hierarchy

```
Object (manual memory management)
├── RefCounted (automatic reference counting)
│   └── Resource (serializable, Inspector-editable)
└── Node (scene tree integration)
    ├── Node2D, Node3D, Control...
    └── Full lifecycle (_ready, _process, etc.)
```

## When to Use Each Base Class

| Base Class | Use When | Memory | Inspector | Serialization |
|------------|----------|--------|-----------|---------------|
| `Object` | Ultra-lightweight, short-lived | Manual (`free()`) | No | No |
| `RefCounted` | Data/logic without scene tree | Automatic (ref count) | No | No |
| `Resource` | Saveable data, editor-editable | Automatic (ref count) | Yes | Yes (.tres) |
| `Node` | Needs scene tree, lifecycle, signals tree | Automatic (tree owns) | Yes | Yes (.tscn) |

## RefCounted for Game Logic

Use `RefCounted` for objects that hold data or logic but don't need the scene tree. They are automatically freed when no references remain.

```gdscript
# inventory_item.gd
class_name InventoryItem
extends RefCounted

var id: StringName
var display_name: String
var icon: Texture2D
var stack_size: int = 1
var quantity: int = 1
var properties: Dictionary = {}

func can_stack_with(other: InventoryItem) -> bool:
    return id == other.id and quantity + other.quantity <= stack_size

func split(amount: int) -> InventoryItem:
    amount = mini(amount, quantity - 1)
    if amount <= 0:
        return null
    quantity -= amount
    var new_item := InventoryItem.new()
    new_item.id = id
    new_item.display_name = display_name
    new_item.icon = icon
    new_item.stack_size = stack_size
    new_item.quantity = amount
    return new_item
```

```gdscript
# skill_data.gd
class_name SkillData
extends RefCounted

var name: StringName
var cooldown: float
var damage: int
var mana_cost: int
var _cooldown_remaining: float = 0.0

func is_ready() -> bool:
    return _cooldown_remaining <= 0.0

func use() -> void:
    _cooldown_remaining = cooldown

func tick(delta: float) -> void:
    _cooldown_remaining = maxf(_cooldown_remaining - delta, 0.0)
```

## Object for Ultra-Lightweight Data

Use `Object` when you need maximum performance and will manage memory manually. Suitable for pooled or short-lived objects.

```gdscript
# command.gd - Command pattern without scene tree overhead
class_name Command
extends Object

func execute() -> void:
    pass

func undo() -> void:
    pass
```

```gdscript
# move_command.gd
class_name MoveCommand
extends Command

var _entity: Node2D
var _from: Vector2
var _to: Vector2

func _init(entity: Node2D, from: Vector2, to: Vector2) -> void:
    _entity = entity
    _from = from
    _to = to

func execute() -> void:
    _entity.position = _to

func undo() -> void:
    _entity.position = _from
```

**Important**: Always call `free()` on `Object` instances when done, or use a manager to track them.

```gdscript
# command_history.gd - Manager that owns Object instances
class_name CommandHistory
extends RefCounted

var _commands: Array[Command] = []
var _index: int = -1

func execute(command: Command) -> void:
    # Remove undone commands
    while _commands.size() > _index + 1:
        _commands.pop_back().free()
    _commands.append(command)
    _index += 1
    command.execute()

func undo() -> void:
    if _index >= 0:
        _commands[_index].undo()
        _index -= 1

func clear() -> void:
    for cmd in _commands:
        cmd.free()
    _commands.clear()
    _index = -1
```

## Resource vs RefCounted

Choose `Resource` over `RefCounted` when you need:
- Editor Inspector editing (`@export`)
- Saving/loading to `.tres` files
- Sharing data across scenes via the filesystem

Choose `RefCounted` over `Resource` when:
- Data is runtime-only (not saved to disk)
- No need for Inspector editing
- You want minimal overhead

```gdscript
# Use Resource for designer-editable data
# weapon_data.gd
class_name WeaponData
extends Resource

@export var name: StringName
@export var damage: int
@export var attack_speed: float
@export var icon: Texture2D

# Use RefCounted for runtime-only state
# weapon_instance.gd
class_name WeaponInstance
extends RefCounted

var data: WeaponData
var durability: int
var enchantments: Array[StringName] = []

func _init(weapon_data: WeaponData) -> void:
    data = weapon_data
    durability = 100
```

## Anti-Patterns

```gdscript
# BAD: Using Node for pure data
class_name ItemNode
extends Node  # Unnecessary scene tree overhead
var item_name: String
var value: int

# GOOD: Use RefCounted instead
class_name Item
extends RefCounted
var item_name: String
var value: int

# BAD: Thousands of nodes for non-visual objects
for i in 1000:
    var node := ItemNode.new()
    add_child(node)  # Heavy - adds to scene tree

# GOOD: Lightweight objects in an array
var items: Array[Item] = []
for i in 1000:
    items.append(Item.new())  # Light - no scene tree
```
