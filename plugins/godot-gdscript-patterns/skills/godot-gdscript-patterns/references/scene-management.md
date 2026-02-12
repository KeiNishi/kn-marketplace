# Scene Management Pattern

Async scene loading with transitions for Godot 4.x.

## SceneManager (Autoload)

```gdscript
# scene_manager.gd (Autoload)
extends Node

signal scene_loading_started(scene_path: String)
signal scene_loading_progress(progress: float)
signal scene_loaded(scene: Node)
signal transition_started
signal transition_finished

@export var transition_scene: PackedScene
@export var loading_scene: PackedScene

var _current_scene: Node
var _transition: CanvasLayer
var _loader: ResourceLoader

func _ready() -> void:
    _current_scene = get_tree().current_scene

    if transition_scene:
        _transition = transition_scene.instantiate()
        add_child(_transition)
        _transition.visible = false

func change_scene(scene_path: String, with_transition: bool = true) -> void:
    if with_transition:
        await _play_transition_out()

    _load_scene(scene_path)

func change_scene_packed(scene: PackedScene, with_transition: bool = true) -> void:
    if with_transition:
        await _play_transition_out()

    _swap_scene(scene.instantiate())

func _load_scene(path: String) -> void:
    scene_loading_started.emit(path)

    # Check if already loaded
    if ResourceLoader.has_cached(path):
        var scene := load(path) as PackedScene
        _swap_scene(scene.instantiate())
        return

    # Async loading
    ResourceLoader.load_threaded_request(path)

    while true:
        var progress := []
        var status := ResourceLoader.load_threaded_get_status(path, progress)

        match status:
            ResourceLoader.THREAD_LOAD_IN_PROGRESS:
                scene_loading_progress.emit(progress[0])
                await get_tree().process_frame
            ResourceLoader.THREAD_LOAD_LOADED:
                var scene := ResourceLoader.load_threaded_get(path) as PackedScene
                _swap_scene(scene.instantiate())
                return
            _:
                push_error("Failed to load scene: %s" % path)
                return

func _swap_scene(new_scene: Node) -> void:
    if _current_scene:
        _current_scene.queue_free()

    _current_scene = new_scene
    get_tree().root.add_child(_current_scene)
    get_tree().current_scene = _current_scene

    scene_loaded.emit(_current_scene)
    await _play_transition_in()

func _play_transition_out() -> void:
    if not _transition:
        return

    transition_started.emit()
    _transition.visible = true

    if _transition.has_method("transition_out"):
        await _transition.transition_out()
    else:
        await get_tree().create_timer(0.3).timeout

func _play_transition_in() -> void:
    if not _transition:
        transition_finished.emit()
        return

    if _transition.has_method("transition_in"):
        await _transition.transition_in()
    else:
        await get_tree().create_timer(0.3).timeout

    _transition.visible = false
    transition_finished.emit()
```
