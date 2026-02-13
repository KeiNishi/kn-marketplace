# Save System Pattern

Encrypted save/load system with saveable node component for Godot 4.x.

## SaveManager (Autoload)

```gdscript
# save_manager.gd (Autoload)
extends Node

const SAVE_PATH := "user://savegame.save"
# IMPORTANT: Replace with your own secret key before shipping
const ENCRYPTION_KEY := "your_secret_key_here"

signal save_completed
signal load_completed
signal save_error(message: String)

func save_game(data: Dictionary) -> void:
    var file := FileAccess.open_encrypted_with_pass(
        SAVE_PATH,
        FileAccess.WRITE,
        ENCRYPTION_KEY
    )

    if file == null:
        save_error.emit("Could not open save file")
        return

    var json := JSON.stringify(data)
    file.store_string(json)
    file.close()

    save_completed.emit()

func load_game() -> Dictionary:
    if not FileAccess.file_exists(SAVE_PATH):
        return {}

    var file := FileAccess.open_encrypted_with_pass(
        SAVE_PATH,
        FileAccess.READ,
        ENCRYPTION_KEY
    )

    if file == null:
        save_error.emit("Could not open save file")
        return {}

    var json := file.get_as_text()
    file.close()

    var parsed := JSON.parse_string(json)
    if parsed == null:
        save_error.emit("Could not parse save data")
        return {}

    load_completed.emit()
    return parsed

func delete_save() -> void:
    if FileAccess.file_exists(SAVE_PATH):
        DirAccess.remove_absolute(SAVE_PATH)

func has_save() -> bool:
    return FileAccess.file_exists(SAVE_PATH)
```

## Saveable Component

```gdscript
# saveable.gd (Attach to saveable nodes)
class_name Saveable
extends Node

@export var save_id: String

func _ready() -> void:
    if save_id.is_empty():
        save_id = str(get_path())

func get_save_data() -> Dictionary:
    var parent := get_parent()
    var data := {"id": save_id}

    if parent is Node2D:
        data["position"] = {"x": parent.position.x, "y": parent.position.y}

    if parent.has_method("get_custom_save_data"):
        data.merge(parent.get_custom_save_data())

    return data

func load_save_data(data: Dictionary) -> void:
    var parent := get_parent()

    if data.has("position") and parent is Node2D:
        parent.position = Vector2(data.position.x, data.position.y)

    if parent.has_method("load_custom_save_data"):
        parent.load_custom_save_data(data)
```
