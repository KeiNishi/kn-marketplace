# State Machine Implementation for Godot 4 CharacterBody2D

This implementation provides a complete state machine for a character with Idle, Running, and Jumping states using the node-based state machine pattern from the godot-gdscript-patterns skill.

## Scene Structure

```
Player (CharacterBody2D)
└── StateMachine (Node)
    ├── Idle (State)
    ├── Running (State)
    └── Jumping (State)
```

## Files

### state.gd — Base State Class

```gdscript
# state.gd
class_name State
extends Node

var state_machine: StateMachine

func enter(_msg: Dictionary = {}) -> void:
    pass

func exit() -> void:
    pass

func update(_delta: float) -> void:
    pass

func physics_update(_delta: float) -> void:
    pass

func handle_input(_event: InputEvent) -> void:
    pass
```

### state_machine.gd — State Machine Controller

```gdscript
# state_machine.gd
class_name StateMachine
extends Node

signal state_changed(from_state: StringName, to_state: StringName)

@export var initial_state: State

var current_state: State
var states: Dictionary = {}

func _ready() -> void:
    # Register all State children
    for child in get_children():
        if child is State:
            states[child.name] = child
            child.state_machine = self
            child.process_mode = Node.PROCESS_MODE_DISABLED

    # Start initial state
    if initial_state:
        current_state = initial_state
        current_state.process_mode = Node.PROCESS_MODE_INHERIT
        current_state.enter()

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)

func _unhandled_input(event: InputEvent) -> void:
    if current_state:
        current_state.handle_input(event)

func transition_to(state_name: StringName, msg: Dictionary = {}) -> void:
    if not states.has(state_name):
        push_error("State '%s' not found" % state_name)
        return

    var previous_state := current_state
    previous_state.exit()
    previous_state.process_mode = Node.PROCESS_MODE_DISABLED

    current_state = states[state_name]
    current_state.process_mode = Node.PROCESS_MODE_INHERIT
    current_state.enter(msg)

    state_changed.emit(previous_state.name, current_state.name)
```

### player.gd — Player CharacterBody2D

```gdscript
# player.gd
class_name Player
extends CharacterBody2D

signal state_changed(from_state: StringName, to_state: StringName)

const GRAVITY: float = 980.0
const JUMP_VELOCITY: float = -400.0

@export var speed: float = 200.0

@onready var animation: AnimationPlayer = $AnimationPlayer
@onready var state_machine: StateMachine = $StateMachine

func _ready() -> void:
    state_machine.state_changed.connect(_on_state_changed)

func _on_state_changed(from_state: StringName, to_state: StringName) -> void:
    state_changed.emit(from_state, to_state)

func apply_gravity(delta: float) -> void:
    if not is_on_floor():
        velocity.y += GRAVITY * delta

func move() -> void:
    move_and_slide()

func get_move_direction() -> float:
    return Input.get_axis("ui_left", "ui_right")

func is_jump_requested() -> bool:
    return Input.is_action_just_pressed("ui_accept")

func is_moving() -> bool:
    return abs(velocity.x) > 1.0

func flip_sprite(direction: float) -> void:
    if direction != 0.0:
        $Sprite2D.scale.x = sign(direction)
```

### states/player_idle.gd — Idle State

```gdscript
# states/player_idle.gd
class_name PlayerIdle
extends State

@export var player: Player

func enter(_msg: Dictionary = {}) -> void:
    player.velocity.x = 0.0
    player.animation.play("idle")

func exit() -> void:
    pass

func physics_update(delta: float) -> void:
    # Apply gravity so the character sticks to the floor
    player.apply_gravity(delta)
    player.move()

    # Transition: fall off ledge -> Jumping (airborne without jump input)
    if not player.is_on_floor():
        state_machine.transition_to(&"Jumping", {"jumped": false})
        return

    # Transition: movement input -> Running
    var direction := player.get_move_direction()
    if direction != 0.0:
        state_machine.transition_to(&"Running")
        return

func handle_input(event: InputEvent) -> void:
    # Transition: jump input -> Jumping
    if event.is_action_pressed("ui_accept"):
        state_machine.transition_to(&"Jumping", {"jumped": true})
```

### states/player_running.gd — Running State

```gdscript
# states/player_running.gd
class_name PlayerRunning
extends State

@export var player: Player

func enter(_msg: Dictionary = {}) -> void:
    player.animation.play("run")

func exit() -> void:
    pass

func physics_update(delta: float) -> void:
    # Apply gravity so the character sticks to the floor
    player.apply_gravity(delta)

    var direction := player.get_move_direction()
    player.velocity.x = direction * player.speed
    player.flip_sprite(direction)
    player.move()

    # Transition: left the floor without jumping -> Jumping (walked off ledge)
    if not player.is_on_floor():
        state_machine.transition_to(&"Jumping", {"jumped": false})
        return

    # Transition: no movement input -> Idle
    if direction == 0.0:
        state_machine.transition_to(&"Idle")
        return

func handle_input(event: InputEvent) -> void:
    # Transition: jump input -> Jumping
    if event.is_action_pressed("ui_accept"):
        state_machine.transition_to(&"Jumping", {"jumped": true})
```

### states/player_jumping.gd — Jumping State

```gdscript
# states/player_jumping.gd
class_name PlayerJumping
extends State

@export var player: Player

func enter(msg: Dictionary = {}) -> void:
    # Apply upward velocity only when triggered by a jump input
    if msg.get("jumped", false):
        player.velocity.y = Player.JUMP_VELOCITY
    player.animation.play("jump")

func exit() -> void:
    pass

func physics_update(delta: float) -> void:
    # Apply gravity every frame
    player.apply_gravity(delta)

    # Allow horizontal control in the air
    var direction := player.get_move_direction()
    player.velocity.x = direction * player.speed
    player.flip_sprite(direction)
    player.move()

    # Transition: landed on the floor
    if player.is_on_floor():
        var move_direction := player.get_move_direction()
        if move_direction != 0.0:
            state_machine.transition_to(&"Running")
        else:
            state_machine.transition_to(&"Idle")
        return
```

## How State Transitions Work

```
Idle  ──── move input ──────────────────► Running
Idle  ──── jump pressed / fell off ledge ► Jumping

Running ── no input ───────────────────► Idle
Running ── jump pressed / fell off ledge ► Jumping

Jumping ── landed + no input ──────────► Idle
Jumping ── landed + move input ─────────► Running
```

### Key Design Decisions

1. **`process_mode` toggle** — Only the active state's `_process` / `_physics_process` / `_unhandled_input` are active; all others are set to `PROCESS_MODE_DISABLED`. This is more efficient than a large `match` block and avoids accidental double-processing.

2. **`StringName` literals (`&"..."`)** — Used for state names in `transition_to()` calls to avoid repeated String-to-StringName conversions at runtime.

3. **Static typing throughout** — All variables, parameters, and return types are explicitly typed so the GDScript type checker can catch errors at parse time.

4. **Gravity handled per-state** — Idle and Running apply gravity so the character stays grounded when on a slope; Jumping applies gravity to produce an arc. This keeps each state self-contained.

5. **Fell-off-ledge detection** — Both Idle and Running check `is_on_floor()` every physics frame and transition to Jumping (with `{"jumped": false}`) so the character enters the correct animation without getting an extra upward impulse.

6. **Signal forwarding** — `Player` re-emits the `StateMachine.state_changed` signal under its own `state_changed` signal, so external nodes (e.g. a UI or audio manager) only need to connect to `player.state_changed`.

## Setup Instructions

1. Create a `Player.tscn` scene with a `CharacterBody2D` root node.
2. Attach `player.gd` to the root.
3. Add child nodes: `CollisionShape2D`, `Sprite2D`, `AnimationPlayer`.
4. Add a `StateMachine` node (attach `state_machine.gd`).
5. Under `StateMachine`, add three nodes named exactly `Idle`, `Running`, `Jumping` with `player_idle.gd`, `player_running.gd`, and `player_jumping.gd` respectively.
6. In the Inspector for each state node, set the `Player` export to the root `Player` node.
7. Set the `StateMachine`'s `Initial State` export to the `Idle` node.
8. Make sure your project's Input Map contains `ui_left`, `ui_right`, and `ui_accept` actions (these are built-in defaults in Godot 4).
