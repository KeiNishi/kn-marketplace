# Notifications and Lifecycle Pattern

Node lifecycle order, virtual method callbacks, and notification handling in Godot 4.x.

## Node Lifecycle Order

```
1. _init()                    — Object constructed (no scene tree yet)
2. NOTIFICATION_PARENTED      — Added as child of another node
3. _enter_tree()              — Entering the scene tree
4. NOTIFICATION_POST_ENTER_TREE
5. _ready()                   — All children are ready (called once)
6. _process(delta)            — Every frame (if enabled)
   _physics_process(delta)    — Every physics tick (if enabled)
   _input(event)              — Every input event
   _unhandled_input(event)    — Unhandled input events
7. _exit_tree()               — Leaving the scene tree
8. NOTIFICATION_UNPARENTED    — Removed from parent
9. _notification(NOTIFICATION_PREDELETE) — About to be freed
```

## Virtual Method Callbacks

### _init vs _ready

```gdscript
class_name Enemy
extends CharacterBody2D

@export var speed: float = 100.0
@export var health_component: HealthComponent

var _velocity: Vector2 = Vector2.ZERO

# _init: Called when object is created (new() or instantiation)
# - No scene tree access
# - No child nodes available
# - No @onready variables
# - Use for: default values, non-node setup
func _init() -> void:
    _velocity = Vector2.ZERO

# _ready: Called once after all children are ready
# - Scene tree is available
# - @onready variables are set
# - Child nodes are accessible
# - Use for: connecting signals, caching references, initial state
func _ready() -> void:
    health_component.died.connect(_on_died)
```

### _enter_tree vs _ready

```gdscript
# _enter_tree: Called EVERY time the node enters the scene tree
# - Children may not be ready yet
# - Use for: registering with managers, scene tree queries
func _enter_tree() -> void:
    add_to_group("enemies")
    GameManager.register_enemy(self)

# _exit_tree: Called when leaving the scene tree
# - Use for: cleanup, unregistering
func _exit_tree() -> void:
    GameManager.unregister_enemy(self)

# _ready: Called ONCE (unless request_ready() is called)
# - All children are guaranteed ready
# - Use for: one-time initialization
func _ready() -> void:
    _setup_ai()
```

## Process Methods

### _process vs _physics_process

```gdscript
# _process(delta): Called every rendered frame
# - Frame rate dependent (varies with performance)
# - Use for: visuals, animations, UI updates, non-physics logic
func _process(delta: float) -> void:
    sprite.rotation += rotation_speed * delta
    update_health_bar()

# _physics_process(delta): Called every physics tick (default 60/sec)
# - Fixed time step (consistent regardless of frame rate)
# - Use for: movement, collision, physics queries
func _physics_process(delta: float) -> void:
    velocity = direction * speed
    move_and_slide()
```

### Enabling/Disabling Processing

```gdscript
# Disable processing for inactive objects (performance)
func deactivate() -> void:
    set_process(false)
    set_physics_process(false)
    set_process_input(false)

func activate() -> void:
    set_process(true)
    set_physics_process(true)
    set_process_input(true)

# Check if processing is enabled
func is_active() -> bool:
    return is_processing()
```

## Input Methods

### Input Propagation Order

```
InputEvent arrives
    ↓
1. Node._input()              — Top-down, all nodes
    ↓ (if not consumed)
2. Control._gui_input()       — UI nodes (bottom-up in tree)
    ↓ (if not consumed)
3. Node._unhandled_input()    — Game input (top-down)
    ↓ (if not consumed)
4. Node._unhandled_key_input() — Remaining key events
```

### Choosing the Right Input Method

```gdscript
# _input: Receives ALL input events first
# - Use for: global shortcuts, pause menu, debug controls
# - Call get_viewport().set_input_as_handled() to consume
func _input(event: InputEvent) -> void:
    if event.is_action_pressed("pause"):
        get_tree().paused = !get_tree().paused
        get_viewport().set_input_as_handled()

# _gui_input: For Control nodes only (UI)
# - Receives input when mouse/touch is over the control
# - Use for: custom UI interactions
# - Call accept_event() to consume
func _gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        _on_clicked()
        accept_event()

# _unhandled_input: Receives input NOT consumed by _input or GUI
# - Use for: gameplay input (movement, actions, camera)
# - Preferred for game logic — doesn't interfere with UI
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("attack"):
        perform_attack()

# _unhandled_key_input: Only key events not consumed above
# - Use for: keyboard shortcuts that shouldn't override UI
func _unhandled_key_input(event: InputEvent) -> void:
    if event.is_action_pressed("inventory"):
        toggle_inventory()
```

### Input vs Polling

```gdscript
# Event-based (in _input/_unhandled_input) — for discrete actions
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("jump"):  # Single press detection
        jump()

# Polling (in _process/_physics_process) — for continuous input
func _physics_process(delta: float) -> void:
    var direction := Input.get_vector("left", "right", "up", "down")
    velocity = direction * speed  # Continuous movement
    move_and_slide()
```

## Custom Notifications

```gdscript
# Define custom notification constants
const NOTIFICATION_WAVE_STARTED = 1001
const NOTIFICATION_WAVE_ENDED = 1002

func _notification(what: int) -> void:
    match what:
        NOTIFICATION_READY:
            _setup()
        NOTIFICATION_PARENTED:
            _register_with_parent()
        NOTIFICATION_UNPARENTED:
            _unregister_from_parent()
        NOTIFICATION_WAVE_STARTED:
            _on_wave_started()

# Propagate custom notifications to children
func start_wave() -> void:
    propagate_notification(NOTIFICATION_WAVE_STARTED)
```

## Best Practices

- **Use `_unhandled_input` for gameplay** — Prevents stealing input from UI
- **Use `_physics_process` for movement** — Consistent physics behavior
- **Use `_process` for visuals** — Smooth rendering at any frame rate
- **Disable processing when not needed** — `set_process(false)` saves CPU
- **Prefer `_ready` over `_enter_tree`** — Unless you need re-entry logic
- **Don't do heavy work in `_init`** — No scene tree access, keep it minimal
- **Use `Input.get_vector()` over manual axis reading** — Cleaner, handles deadzones
