# Godot 4 RPG Save/Load System

A complete save/load system for a Godot 4 RPG supporting player stats (health, level, position), quest progress, encrypted saves, and multi-platform compatibility.

---

## Overview

The system is built from three parts:

1. **`SaveManager`** - Autoload singleton that handles file I/O with encryption
2. **`Saveable`** - Component node attached to any scene that needs saving
3. **`Player` / `QuestManager`** - Game objects that implement `get_custom_save_data()` / `load_custom_save_data()`

`user://` paths are used throughout. Godot automatically maps `user://` to the correct platform-specific directory (Windows AppData, macOS Application Support, Linux ~/.local/share, Android/iOS sandboxed storage), giving full cross-platform compatibility for free.

---

## Project Setup

In **Project Settings > Autoload**, add:

| Name | Path |
|------|------|
| `SaveManager` | `res://autoload/save_manager.gd` |
| `QuestManager` | `res://autoload/quest_manager.gd` |

---

## 1. SaveManager (Autoload)

```gdscript
# res://autoload/save_manager.gd
extends Node

# user:// resolves to the correct platform path automatically:
#   Windows : %APPDATA%\Godot\app_userdata\<project>\
#   macOS   : ~/Library/Application Support/Godot/<project>/
#   Linux   : ~/.local/share/godot/app_userdata/<project>/
#   Android : /data/data/<package>/files/
#   iOS     : <app>/Documents/
const SAVE_PATH := "user://savegame.save"

# IMPORTANT: Replace with your own secret before shipping.
# Consider reading this from an environment variable or a compiled constant.
const ENCRYPTION_KEY := "your_secret_key_here"

signal save_completed
signal load_completed
signal save_error(message: String)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

func save_game() -> void:
    var data := _collect_save_data()

    var file := FileAccess.open_encrypted_with_pass(
        SAVE_PATH,
        FileAccess.WRITE,
        ENCRYPTION_KEY
    )

    if file == null:
        save_error.emit("Could not open save file for writing: %s" % SAVE_PATH)
        return

    file.store_string(JSON.stringify(data))
    file.close()

    save_completed.emit()
    print("[SaveManager] Game saved.")

func load_game() -> void:
    if not FileAccess.file_exists(SAVE_PATH):
        print("[SaveManager] No save file found.")
        return

    var file := FileAccess.open_encrypted_with_pass(
        SAVE_PATH,
        FileAccess.READ,
        ENCRYPTION_KEY
    )

    if file == null:
        save_error.emit("Could not open save file for reading: %s" % SAVE_PATH)
        return

    var raw := file.get_as_text()
    file.close()

    var parsed: Variant = JSON.parse_string(raw)
    if parsed == null or not parsed is Dictionary:
        save_error.emit("Save data is corrupted or unreadable.")
        return

    _distribute_save_data(parsed as Dictionary)
    load_completed.emit()
    print("[SaveManager] Game loaded.")

func delete_save() -> void:
    if FileAccess.file_exists(SAVE_PATH):
        DirAccess.remove_absolute(SAVE_PATH)
        print("[SaveManager] Save file deleted.")

func has_save() -> bool:
    return FileAccess.file_exists(SAVE_PATH)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

## Collect save data from every node in the "saveable" group.
func _collect_save_data() -> Dictionary:
    var data: Dictionary = {}
    for node in get_tree().get_nodes_in_group("saveable"):
        var saveable := node.get_node_or_null("Saveable") as Saveable
        if saveable:
            var entry := saveable.get_save_data()
            data[entry["id"]] = entry
    return data

## Push loaded data back to every saveable node.
func _distribute_save_data(data: Dictionary) -> void:
    for node in get_tree().get_nodes_in_group("saveable"):
        var saveable := node.get_node_or_null("Saveable") as Saveable
        if saveable and data.has(saveable.save_id):
            saveable.load_save_data(data[saveable.save_id])
```

---

## 2. Saveable Component

```gdscript
# res://components/saveable.gd
class_name Saveable
extends Node

## Unique identifier for this object in the save file.
## If left blank, the node's full scene-tree path is used.
@export var save_id: String

func _ready() -> void:
    if save_id.is_empty():
        save_id = str(get_path())

## Gather all save data from the parent node.
func get_save_data() -> Dictionary:
    var parent := get_parent()
    var data: Dictionary = {"id": save_id}

    # Automatically capture 2D position if the parent is a Node2D.
    if parent is Node2D:
        data["position"] = {"x": parent.position.x, "y": parent.position.y}

    # Let the parent supply game-specific data.
    if parent.has_method("get_custom_save_data"):
        data.merge(parent.get_custom_save_data())

    return data

## Restore save data into the parent node.
func load_save_data(data: Dictionary) -> void:
    var parent := get_parent()

    if data.has("position") and parent is Node2D:
        parent.position = Vector2(data["position"]["x"], data["position"]["y"])

    if parent.has_method("load_custom_save_data"):
        parent.load_custom_save_data(data)
```

---

## 3. Player (implements the saveable interface)

```gdscript
# res://characters/player.gd
class_name Player
extends CharacterBody2D

# --- Stats ---
@export var max_health: int = 100
var current_health: int
var level: int = 1
var experience: int = 0

signal health_changed(new_health: int)
signal level_up(new_level: int)

func _ready() -> void:
    current_health = max_health
    # Register with the saveable group so SaveManager can find this node.
    add_to_group("saveable")

# ---------------------------------------------------------------------------
# Saveable interface
# ---------------------------------------------------------------------------

## Called by Saveable.get_save_data() to add player-specific fields.
func get_custom_save_data() -> Dictionary:
    return {
        "health":     current_health,
        "max_health": max_health,
        "level":      level,
        "experience": experience,
    }

## Called by Saveable.load_save_data() to restore player-specific fields.
func load_custom_save_data(data: Dictionary) -> void:
    if data.has("health"):
        current_health = data["health"]
        health_changed.emit(current_health)
    if data.has("max_health"):
        max_health = data["max_health"]
    if data.has("level"):
        level = data["level"]
    if data.has("experience"):
        experience = data["experience"]

# ---------------------------------------------------------------------------
# Gameplay methods
# ---------------------------------------------------------------------------

func take_damage(amount: int) -> void:
    current_health = maxi(current_health - amount, 0)
    health_changed.emit(current_health)
    if current_health == 0:
        _die()

func heal(amount: int) -> void:
    current_health = mini(current_health + amount, max_health)
    health_changed.emit(current_health)

func gain_experience(amount: int) -> void:
    experience += amount
    var xp_needed := level * 100
    if experience >= xp_needed:
        experience -= xp_needed
        level += 1
        level_up.emit(level)

func _die() -> void:
    print("Player died!")
```

**Player scene structure (Player.tscn):**

```
Player (CharacterBody2D) <- player.gd
└── Saveable (Node)      <- saveable.gd  [save_id: "player"]
```

---

## 4. QuestManager (Autoload — handles quest progress)

```gdscript
# res://autoload/quest_manager.gd
extends Node

signal quest_started(quest_id: String)
signal quest_completed(quest_id: String)
signal objective_updated(quest_id: String, objective_id: String, progress: int)

# quest_id -> { "status": "active"|"completed"|"failed", "objectives": { obj_id: progress } }
var _quests: Dictionary = {}

func _ready() -> void:
    # QuestManager acts as its own saveable via SaveManager signals.
    SaveManager.save_completed.connect(_on_save_completed)  # optional hook
    add_to_group("saveable")

# ---------------------------------------------------------------------------
# Quest logic
# ---------------------------------------------------------------------------

func start_quest(quest_id: String) -> void:
    if _quests.has(quest_id):
        return
    _quests[quest_id] = {"status": "active", "objectives": {}}
    quest_started.emit(quest_id)

func complete_quest(quest_id: String) -> void:
    if not _quests.has(quest_id):
        return
    _quests[quest_id]["status"] = "completed"
    quest_completed.emit(quest_id)

func update_objective(quest_id: String, objective_id: String, progress: int) -> void:
    if not _quests.has(quest_id):
        return
    _quests[quest_id]["objectives"][objective_id] = progress
    objective_updated.emit(quest_id, objective_id, progress)

func is_quest_active(quest_id: String) -> bool:
    return _quests.get(quest_id, {}).get("status", "") == "active"

func is_quest_completed(quest_id: String) -> bool:
    return _quests.get(quest_id, {}).get("status", "") == "completed"

func get_objective_progress(quest_id: String, objective_id: String) -> int:
    return _quests.get(quest_id, {}).get("objectives", {}).get(objective_id, 0)

# ---------------------------------------------------------------------------
# Saveable interface
# (QuestManager is an autoload, so it uses a manual approach rather than
#  a child Saveable node — it registers directly with SaveManager.)
# ---------------------------------------------------------------------------

func get_custom_save_data() -> Dictionary:
    return {"quests": _quests}

func load_custom_save_data(data: Dictionary) -> void:
    if data.has("quests"):
        _quests = data["quests"]

# Provide an ID so SaveManager._collect_save_data() can key this entry.
# We expose a fake "Saveable" sub-node via a helper below, OR we integrate
# QuestManager directly in SaveManager._collect_save_data().
# The simplest approach: give QuestManager a Saveable child node in the scene.
func _on_save_completed() -> void:
    pass  # hook for additional logic after save
```

**Integrating QuestManager with SaveManager:**

Because `QuestManager` is an Autoload (not a scene node with children), the cleanest approach is to extend `_collect_save_data` and `_distribute_save_data` in `SaveManager` to handle it explicitly:

```gdscript
# In save_manager.gd — replace _collect_save_data and _distribute_save_data:

func _collect_save_data() -> Dictionary:
    var data: Dictionary = {}

    # Saveable nodes (Player, NPCs, chests, etc.)
    for node in get_tree().get_nodes_in_group("saveable"):
        var saveable := node.get_node_or_null("Saveable") as Saveable
        if saveable:
            var entry := saveable.get_save_data()
            data[entry["id"]] = entry

    # QuestManager (autoload — no Saveable child node needed)
    data["quest_manager"] = QuestManager.get_custom_save_data()

    return data

func _distribute_save_data(data: Dictionary) -> void:
    for node in get_tree().get_nodes_in_group("saveable"):
        var saveable := node.get_node_or_null("Saveable") as Saveable
        if saveable and data.has(saveable.save_id):
            saveable.load_save_data(data[saveable.save_id])

    if data.has("quest_manager"):
        QuestManager.load_custom_save_data(data["quest_manager"])
```

---

## 5. Save UI / Triggering Saves

```gdscript
# res://ui/save_menu.gd
extends Control

@onready var save_button: Button = $SaveButton
@onready var load_button: Button = $LoadButton
@onready var status_label: Label = $StatusLabel

func _ready() -> void:
    save_button.pressed.connect(_on_save_pressed)
    load_button.pressed.connect(_on_load_pressed)
    load_button.disabled = not SaveManager.has_save()

    SaveManager.save_completed.connect(_on_save_completed)
    SaveManager.load_completed.connect(_on_load_completed)
    SaveManager.save_error.connect(_on_save_error)

func _on_save_pressed() -> void:
    SaveManager.save_game()

func _on_load_pressed() -> void:
    SaveManager.load_game()

func _on_save_completed() -> void:
    status_label.text = "Game saved!"

func _on_load_completed() -> void:
    status_label.text = "Game loaded!"
    load_button.disabled = false

func _on_save_error(message: String) -> void:
    status_label.text = "Error: " + message
    push_error("[SaveManager] " + message)
```

---

## 6. Example: Chest (Saveable Non-Player Object)

Any scene can become saveable by adding a `Saveable` child node and implementing the two methods.

```gdscript
# res://objects/chest.gd
class_name Chest
extends StaticBody2D

var is_open: bool = false

signal opened

func _ready() -> void:
    add_to_group("saveable")

func open() -> void:
    if is_open:
        return
    is_open = true
    opened.emit()
    $AnimationPlayer.play("open")

func get_custom_save_data() -> Dictionary:
    return {"is_open": is_open}

func load_custom_save_data(data: Dictionary) -> void:
    if data.get("is_open", false):
        # Restore opened state without animation
        is_open = true
        $AnimationPlayer.play("open_idle")
```

**Chest scene structure (Chest.tscn):**

```
Chest (StaticBody2D) <- chest.gd
└── Saveable (Node)  <- saveable.gd  [save_id: "chest_forest_01"]
```

---

## 7. Example Save File Structure (JSON, before encryption)

```json
{
  "player": {
    "id": "player",
    "position": { "x": 320.0, "y": 240.0 },
    "health": 75,
    "max_health": 100,
    "level": 5,
    "experience": 230
  },
  "chest_forest_01": {
    "id": "chest_forest_01",
    "position": { "x": 640.0, "y": 128.0 },
    "is_open": true
  },
  "quest_manager": {
    "quests": {
      "main_quest_01": {
        "status": "active",
        "objectives": {
          "kill_wolves": 3,
          "find_herb": 1
        }
      },
      "side_quest_02": {
        "status": "completed",
        "objectives": {}
      }
    }
  }
}
```

---

## Platform Compatibility Notes

| Platform | `user://` resolves to |
|----------|-----------------------|
| Windows | `%APPDATA%\Godot\app_userdata\<project name>\` |
| macOS | `~/Library/Application Support/Godot/<project name>/` |
| Linux | `~/.local/share/godot/app_userdata/<project name>/` |
| Android | `/data/data/<package name>/files/` |
| iOS | `<app bundle>/Documents/` |
| HTML5/Web | Persistent storage via IndexedDB (Godot handles automatically) |

Using `user://` instead of `res://` or absolute paths is the key to platform compatibility — Godot handles path translation automatically.

---

## Security Notes

- `FileAccess.open_encrypted_with_pass()` uses AES-256-CBC encryption internally.
- Replace `ENCRYPTION_KEY` with a unique string before shipping — do not use the placeholder.
- For additional security, consider storing the key as a compiled constant (using a build script) rather than a plain string literal.
- Encrypted saves will be unreadable (and unmodifiable) by players without the key.
- The JSON structure inside is still human-readable if decrypted — do not store sensitive real-world data in save files.

---

## Quick Reference Checklist

- [ ] `save_manager.gd` added to Autoload as `SaveManager`
- [ ] `quest_manager.gd` added to Autoload as `QuestManager`
- [ ] `Saveable` child node added to every scene that needs saving
- [ ] Each saveable scene calls `add_to_group("saveable")` in `_ready()`
- [ ] Each saveable scene implements `get_custom_save_data()` and `load_custom_save_data()`
- [ ] `ENCRYPTION_KEY` replaced with a unique secret before release
- [ ] `SaveManager.save_error` signal connected to display errors to the player
