# Godot 4 RPG Save/Load System with Encryption

## Overview

This implementation provides a complete save/load system for a Godot 4 RPG that:
- Saves player stats (health, level, position)
- Saves quest progress
- Works cross-platform using Godot's `user://` path
- Supports AES-256 encryption via Godot's `FileAccess` encryption API

---

## File Structure

```
res://
├── autoload/
│   └── SaveManager.gd       # Singleton managing all save/load logic
├── scripts/
│   ├── PlayerData.gd         # Data container for player stats
│   └── QuestData.gd          # Data container for quest progress
└── player/
    └── Player.gd             # Player node using SaveManager
```

---

## 1. PlayerData Resource (`res://scripts/PlayerData.gd`)

```gdscript
# PlayerData.gd
# A simple data container for player stats.
# Using a plain Dictionary approach for serialization compatibility.
class_name PlayerData

var health: int = 100
var max_health: int = 100
var level: int = 1
var experience: int = 0
var position_x: float = 0.0
var position_y: float = 0.0
var position_z: float = 0.0  # Use for 3D; ignore for 2D

func to_dict() -> Dictionary:
    return {
        "health": health,
        "max_health": max_health,
        "level": level,
        "experience": experience,
        "position_x": position_x,
        "position_y": position_y,
        "position_z": position_z,
    }

func from_dict(data: Dictionary) -> void:
    health = data.get("health", 100)
    max_health = data.get("max_health", 100)
    level = data.get("level", 1)
    experience = data.get("experience", 0)
    position_x = data.get("position_x", 0.0)
    position_y = data.get("position_y", 0.0)
    position_z = data.get("position_z", 0.0)
```

---

## 2. QuestData Container (`res://scripts/QuestData.gd`)

```gdscript
# QuestData.gd
# Tracks the state of all quests.
class_name QuestData

# Quest states
enum QuestState {
    NOT_STARTED,
    IN_PROGRESS,
    COMPLETED,
    FAILED
}

# Dictionary mapping quest_id (String) -> Dictionary with state and objectives
var quests: Dictionary = {}

func set_quest_state(quest_id: String, state: QuestState) -> void:
    if not quests.has(quest_id):
        quests[quest_id] = {"state": state, "objectives": {}}
    else:
        quests[quest_id]["state"] = state

func get_quest_state(quest_id: String) -> QuestState:
    if quests.has(quest_id):
        return quests[quest_id].get("state", QuestState.NOT_STARTED)
    return QuestState.NOT_STARTED

func set_objective_progress(quest_id: String, objective_id: String, progress: int) -> void:
    if not quests.has(quest_id):
        quests[quest_id] = {"state": QuestState.IN_PROGRESS, "objectives": {}}
    quests[quest_id]["objectives"][objective_id] = progress

func get_objective_progress(quest_id: String, objective_id: String) -> int:
    if quests.has(quest_id):
        return quests[quest_id]["objectives"].get(objective_id, 0)
    return 0

func to_dict() -> Dictionary:
    # Convert enum values to int for JSON serialization
    var serialized: Dictionary = {}
    for quest_id in quests:
        var quest = quests[quest_id]
        serialized[quest_id] = {
            "state": int(quest["state"]),
            "objectives": quest["objectives"].duplicate()
        }
    return serialized

func from_dict(data: Dictionary) -> void:
    quests.clear()
    for quest_id in data:
        var quest = data[quest_id]
        quests[quest_id] = {
            "state": quest.get("state", QuestState.NOT_STARTED) as QuestState,
            "objectives": quest.get("objectives", {}).duplicate()
        }
```

---

## 3. SaveManager Autoload (`res://autoload/SaveManager.gd`)

This is the core singleton. Add it to **Project > Project Settings > Autoload** as `SaveManager`.

```gdscript
# SaveManager.gd
# Autoload singleton for saving and loading game data.
# Supports encrypted saves using Godot 4's FileAccess API.
extends Node

# --- Configuration ---
const SAVE_DIR: String = "user://saves/"
const SAVE_FILE: String = "save_slot_{slot}.sav"
const MAX_SLOTS: int = 3

# IMPORTANT: In production, derive this key from a secure source.
# Do NOT hardcode sensitive keys in shipped games.
# Consider using OS.get_unique_id() combined with a build secret,
# or prompting the user for a password and deriving a key with PBKDF2.
const ENCRYPTION_KEY: String = "MySecretKey12345"  # Must be <= 32 chars for AES-256

# Signals
signal save_completed(slot: int)
signal load_completed(slot: int)
signal save_failed(slot: int, error: String)
signal load_failed(slot: int, error: String)

# --- Public API ---

## Save game data to a specific slot (0-indexed).
## player_data: PlayerData instance
## quest_data: QuestData instance
func save_game(slot: int, player_data: PlayerData, quest_data: QuestData) -> bool:
    if slot < 0 or slot >= MAX_SLOTS:
        push_error("SaveManager: Invalid save slot %d" % slot)
        emit_signal("save_failed", slot, "Invalid slot")
        return false

    _ensure_save_dir()

    var save_payload: Dictionary = {
        "version": 1,  # Schema version for future migration
        "timestamp": Time.get_unix_time_from_system(),
        "player": player_data.to_dict(),
        "quests": quest_data.to_dict(),
    }

    var json_string: String = JSON.stringify(save_payload)
    var file_path: String = _get_save_path(slot)

    var result: bool = _write_encrypted(file_path, json_string)
    if result:
        print("SaveManager: Game saved to slot %d at %s" % [slot, file_path])
        emit_signal("save_completed", slot)
    else:
        emit_signal("save_failed", slot, "Write error")
    return result


## Load game data from a specific slot.
## Returns a Dictionary with keys "player" (PlayerData) and "quests" (QuestData),
## or an empty Dictionary on failure.
func load_game(slot: int) -> Dictionary:
    if slot < 0 or slot >= MAX_SLOTS:
        push_error("SaveManager: Invalid save slot %d" % slot)
        emit_signal("load_failed", slot, "Invalid slot")
        return {}

    var file_path: String = _get_save_path(slot)

    if not FileAccess.file_exists(file_path):
        push_warning("SaveManager: No save file found at %s" % file_path)
        emit_signal("load_failed", slot, "File not found")
        return {}

    var json_string: String = _read_encrypted(file_path)
    if json_string.is_empty():
        emit_signal("load_failed", slot, "Read error or empty file")
        return {}

    var json = JSON.new()
    var parse_result: Error = json.parse(json_string)
    if parse_result != OK:
        push_error("SaveManager: JSON parse error: %s" % json.get_error_message())
        emit_signal("load_failed", slot, "JSON parse error")
        return {}

    var data: Dictionary = json.get_data()

    # Version migration hook
    data = _migrate_save_data(data)

    var player_data := PlayerData.new()
    player_data.from_dict(data.get("player", {}))

    var quest_data := QuestData.new()
    quest_data.from_dict(data.get("quests", {}))

    print("SaveManager: Game loaded from slot %d" % slot)
    emit_signal("load_completed", slot)

    return {
        "player": player_data,
        "quests": quest_data,
    }


## Delete a save slot.
func delete_save(slot: int) -> bool:
    var file_path: String = _get_save_path(slot)
    if FileAccess.file_exists(file_path):
        var err: Error = DirAccess.remove_absolute(file_path)
        if err == OK:
            print("SaveManager: Deleted save slot %d" % slot)
            return true
        else:
            push_error("SaveManager: Failed to delete slot %d (error %d)" % [slot, err])
            return false
    return true  # Nothing to delete


## Check if a save slot has data.
func slot_has_save(slot: int) -> bool:
    return FileAccess.file_exists(_get_save_path(slot))


## Get metadata for a save slot without fully loading it.
## Returns a Dictionary with "timestamp" and "level", or empty on failure.
func get_save_metadata(slot: int) -> Dictionary:
    if not slot_has_save(slot):
        return {}

    var file_path: String = _get_save_path(slot)
    var json_string: String = _read_encrypted(file_path)
    if json_string.is_empty():
        return {}

    var json = JSON.new()
    if json.parse(json_string) != OK:
        return {}

    var data: Dictionary = json.get_data()
    return {
        "timestamp": data.get("timestamp", 0),
        "level": data.get("player", {}).get("level", 1),
    }


# --- Private Helpers ---

func _get_save_path(slot: int) -> String:
    return SAVE_DIR + SAVE_FILE.format({"slot": slot})


func _ensure_save_dir() -> void:
    if not DirAccess.dir_exists_absolute(SAVE_DIR):
        var err: Error = DirAccess.make_dir_recursive_absolute(SAVE_DIR)
        if err != OK:
            push_error("SaveManager: Could not create save directory: %s" % SAVE_DIR)


func _write_encrypted(path: String, content: String) -> bool:
    # FileAccess.open_encrypted_with_pass uses AES-256-CBC
    var file: FileAccess = FileAccess.open_encrypted_with_pass(
        path,
        FileAccess.WRITE,
        ENCRYPTION_KEY
    )
    if file == null:
        push_error("SaveManager: Failed to open file for writing: %s (error: %d)" % [
            path, FileAccess.get_open_error()
        ])
        return false

    file.store_string(content)
    file.close()
    return true


func _read_encrypted(path: String) -> String:
    var file: FileAccess = FileAccess.open_encrypted_with_pass(
        path,
        FileAccess.READ,
        ENCRYPTION_KEY
    )
    if file == null:
        push_error("SaveManager: Failed to open file for reading: %s (error: %d)" % [
            path, FileAccess.get_open_error()
        ])
        return ""

    var content: String = file.get_as_text()
    file.close()
    return content


## Handle save data migration between schema versions.
func _migrate_save_data(data: Dictionary) -> Dictionary:
    var version: int = data.get("version", 0)

    # Example: migrate from version 0 (no version field) to version 1
    if version < 1:
        # Provide defaults for any missing fields introduced in v1
        if not data.has("quests"):
            data["quests"] = {}
        data["version"] = 1

    # Future migrations: if version < 2: ...

    return data
```

---

## 4. Player Integration (`res://player/Player.gd`)

```gdscript
# Player.gd
extends CharacterBody3D  # Use CharacterBody2D for 2D games

var player_data := PlayerData.new()
var quest_data := QuestData.new()

const DEFAULT_SAVE_SLOT: int = 0

func _ready() -> void:
    # Attempt to load existing save on startup
    _load_or_initialize()

func _load_or_initialize() -> void:
    if SaveManager.slot_has_save(DEFAULT_SAVE_SLOT):
        var loaded: Dictionary = SaveManager.load_game(DEFAULT_SAVE_SLOT)
        if not loaded.is_empty():
            player_data = loaded["player"]
            quest_data = loaded["quests"]
            _apply_player_data()
        else:
            push_warning("Player: Load failed, using defaults.")
            _initialize_defaults()
    else:
        _initialize_defaults()

func _initialize_defaults() -> void:
    player_data = PlayerData.new()
    quest_data = QuestData.new()
    global_position = Vector3(0, 1, 0)  # Spawn point

func _apply_player_data() -> void:
    global_position = Vector3(
        player_data.position_x,
        player_data.position_y,
        player_data.position_z
    )
    # Apply health, level, etc. to your game systems here
    print("Player loaded: Level %d, HP %d/%d" % [
        player_data.level, player_data.health, player_data.max_health
    ])

## Call this to save the game (e.g., at checkpoints or on pause menu).
func save_game(slot: int = DEFAULT_SAVE_SLOT) -> void:
    # Capture current position before saving
    player_data.position_x = global_position.x
    player_data.position_y = global_position.y
    player_data.position_z = global_position.z

    var success: bool = SaveManager.save_game(slot, player_data, quest_data)
    if success:
        print("Game saved successfully.")
    else:
        print("Failed to save game.")

## Example: update a quest from game logic
func complete_quest(quest_id: String) -> void:
    quest_data.set_quest_state(quest_id, QuestData.QuestState.COMPLETED)
    print("Quest completed: %s" % quest_id)

## Example: track objective progress
func update_objective(quest_id: String, objective_id: String, amount: int) -> void:
    quest_data.set_objective_progress(quest_id, objective_id, amount)
```

---

## 5. Save Slot UI Example

```gdscript
# SaveSlotButton.gd - Attach to a Button node in your save/load menu
extends Button

@export var slot: int = 0

func _ready() -> void:
    _refresh_label()
    SaveManager.save_completed.connect(_on_save_completed)
    SaveManager.load_completed.connect(_on_load_completed)

func _refresh_label() -> void:
    if SaveManager.slot_has_save(slot):
        var meta: Dictionary = SaveManager.get_save_metadata(slot)
        var dt: Dictionary = Time.get_datetime_dict_from_unix_time(meta.get("timestamp", 0))
        text = "Slot %d - Level %d\n%04d/%02d/%02d %02d:%02d" % [
            slot + 1,
            meta.get("level", 1),
            dt.year, dt.month, dt.day, dt.hour, dt.minute
        ]
    else:
        text = "Slot %d - Empty" % (slot + 1)

func _on_save_completed(saved_slot: int) -> void:
    if saved_slot == slot:
        _refresh_label()

func _on_load_completed(loaded_slot: int) -> void:
    pass  # Handle UI feedback if needed
```

---

## Platform Compatibility Notes

| Platform     | `user://` Path                                         |
|--------------|--------------------------------------------------------|
| Windows      | `%APPDATA%\Godot\app_userdata\<ProjectName>\`          |
| macOS        | `~/Library/Application Support/Godot/<ProjectName>/`  |
| Linux        | `~/.local/share/godot/app_userdata/<ProjectName>/`    |
| Android      | Internal storage (app-private, managed by OS)          |
| iOS          | App sandbox Documents directory                        |
| HTML5/Web    | IndexedDB (persistent if user grants permission)       |

Godot automatically resolves `user://` to the correct platform path. No extra platform handling is needed.

---

## Encryption Details

- `FileAccess.open_encrypted_with_pass()` uses **AES-256-CBC** with the provided passphrase.
- The key is hashed internally by Godot so any string length is acceptable, but keeping it <= 32 chars is conventional.
- **Security warning**: Hardcoded keys in exported games can be extracted via binary inspection. For better security:
  - Derive the key from `OS.get_unique_id()` + a build secret.
  - Or use a user-provided password (e.g., for cloud sync scenarios).

---

## Autoload Setup

1. Open **Project > Project Settings > Autoload**.
2. Click the folder icon and select `res://autoload/SaveManager.gd`.
3. Set the Node Name to `SaveManager`.
4. Enable the **Singleton** toggle (it is enabled by default).

---

## Quick Usage Summary

```gdscript
# Save
SaveManager.save_game(0, player_data, quest_data)

# Load
var result = SaveManager.load_game(0)
if not result.is_empty():
    player_data = result["player"]
    quest_data  = result["quests"]

# Check slot
if SaveManager.slot_has_save(0):
    print("Slot 0 has data")

# Delete
SaveManager.delete_save(0)

# Metadata only (for UI)
var meta = SaveManager.get_save_metadata(0)
print("Level: ", meta.get("level"))
```
