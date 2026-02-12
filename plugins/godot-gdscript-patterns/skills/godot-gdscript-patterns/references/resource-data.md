# Resource-based Data Pattern

Using Godot Resources as data containers for game configuration in Godot 4.x.

## WeaponData Resource

```gdscript
# weapon_data.gd
class_name WeaponData
extends Resource

@export var name: StringName
@export var damage: int
@export var attack_speed: float
@export var range: float
@export_multiline var description: String
@export var icon: Texture2D
@export var projectile_scene: PackedScene
@export var sound_attack: AudioStream
```

## CharacterStats Resource

```gdscript
# character_stats.gd
class_name CharacterStats
extends Resource

signal stat_changed(stat_name: StringName, new_value: float)

@export var max_health: float = 100.0
@export var attack: float = 10.0
@export var defense: float = 5.0
@export var speed: float = 200.0

# Runtime values (not saved)
var _current_health: float

func _init() -> void:
    _current_health = max_health

func get_current_health() -> float:
    return _current_health

func take_damage(amount: float) -> float:
    var actual_damage := maxf(amount - defense, 1.0)
    _current_health = maxf(_current_health - actual_damage, 0.0)
    stat_changed.emit("health", _current_health)
    return actual_damage

func heal(amount: float) -> void:
    _current_health = minf(_current_health + amount, max_health)
    stat_changed.emit("health", _current_health)

func duplicate_for_runtime() -> CharacterStats:
    var copy := duplicate() as CharacterStats
    copy._current_health = copy.max_health
    return copy
```

## Using Resources in Characters

```gdscript
# Using resources
class_name Character
extends CharacterBody2D

@export var base_stats: CharacterStats
@export var weapon: WeaponData

var stats: CharacterStats

func _ready() -> void:
    # Create runtime copy to avoid modifying the resource
    stats = base_stats.duplicate_for_runtime()
    stats.stat_changed.connect(_on_stat_changed)

func attack() -> void:
    if weapon:
        print("Attacking with %s for %d damage" % [weapon.name, weapon.damage])

func _on_stat_changed(stat_name: StringName, value: float) -> void:
    if stat_name == "health" and value <= 0:
        die()
```
