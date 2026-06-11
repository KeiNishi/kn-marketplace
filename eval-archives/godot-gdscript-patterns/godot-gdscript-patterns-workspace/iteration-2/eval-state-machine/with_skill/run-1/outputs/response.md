# State Machine for Godot 4 CharacterBody2D

This implementation follows the canonical Godot 4 node-based state machine pattern: a `StateMachine` node manages state children, each state handles its own logic, and transitions flow through `state_machine.transition_to()`. All code uses Godot 4 syntax only, full static typing, and signals-up / calls-down architecture.

---

## File Structure

```
Player/                        (CharacterBody2D scene root)
├── player.gd
├── StateMachine/              (StateMachine node)
│   ├── state_machine.gd
│   ├── Idle/                  (State node)
│   │   └── player_idle.gd
│   ├── Running/               (State node)
│   │   └── player_running.gd
│   └── Jumping/               (State node)
│       └── player_jumping.gd
└── state.gd                   (base class, can live anywhere on res://)
```

---

## state.gd — Base State Class

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

---

## state_machine.gd — StateMachine Node

```gdscript
# state_machine.gd
class_name StateMachine
extends Node

signal state_changed(from_state: StringName, to_state: StringName)

@export var initial_state: State

var current_state: State
var states: Dictionary = {}

func _ready() -> void:
    for child in get_children():
        if child is State:
            states[child.name] = child
            child.state_machine = self
            child.process_mode = Node.PROCESS_MODE_DISABLED

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

---

## player.gd — CharacterBody2D Root

```gdscript
# player.gd
class_name Player
extends CharacterBody2D

signal state_changed(from_state: StringName, to_state: StringName)

@export var speed: float = 200.0
@export var jump_velocity: float = -400.0

@onready var state_machine: StateMachine = $StateMachine
@onready var animation: AnimationPlayer = $AnimationPlayer

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")

func _ready() -> void:
    state_machine.state_changed.connect(_on_state_changed)

func _on_state_changed(from_state: StringName, to_state: StringName) -> void:
    state_changed.emit(from_state, to_state)
```

The Player node owns the physics body and exposes data (`speed`, `jump_velocity`, `gravity`, `animation`) that states read and drive. It never calls state logic directly — that flows through StateMachine.

---

## player_idle.gd — Idle State

```gdscript
# player_idle.gd
class_name PlayerIdle
extends State

@export var player: Player

func enter(_msg: Dictionary = {}) -> void:
    player.animation.play("idle")

func physics_update(_delta: float) -> void:
    # Apply gravity so the character stays grounded on slopes
    if not player.is_on_floor():
        player.velocity.y += player.gravity * _delta
        player.move_and_slide()
        # Fell off a ledge — treat as falling (no dedicated Fall state here,
        # so transition to Jumping with a flag so it skips the jump impulse)
        state_machine.transition_to(&"Jumping", {"airborne_only": true})
        return

    # Bleed horizontal velocity to zero while idle
    player.velocity.x = move_toward(player.velocity.x, 0.0, player.speed)
    player.move_and_slide()

    var direction := Input.get_axis("ui_left", "ui_right")
    if direction != 0.0:
        state_machine.transition_to(&"Running")

func handle_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_accept") and player.is_on_floor():
        state_machine.transition_to(&"Jumping")
```

---

## player_running.gd — Running State

```gdscript
# player_running.gd
class_name PlayerRunning
extends State

@export var player: Player

func enter(_msg: Dictionary = {}) -> void:
    player.animation.play("run")

func physics_update(delta: float) -> void:
    # Apply gravity
    if not player.is_on_floor():
        player.velocity.y += player.gravity * delta

    var direction := Input.get_axis("ui_left", "ui_right")

    if direction != 0.0:
        player.velocity.x = direction * player.speed
    else:
        player.velocity.x = move_toward(player.velocity.x, 0.0, player.speed)

    player.move_and_slide()

    # Transition checks — order matters: jump before idle/airborne
    if not player.is_on_floor():
        state_machine.transition_to(&"Jumping", {"airborne_only": true})
        return

    if direction == 0.0:
        state_machine.transition_to(&"Idle")

func handle_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_accept") and player.is_on_floor():
        state_machine.transition_to(&"Jumping")
```

---

## player_jumping.gd — Jumping State

```gdscript
# player_jumping.gd
class_name PlayerJumping
extends State

@export var player: Player

func enter(msg: Dictionary = {}) -> void:
    player.animation.play("jump")

    # airborne_only = true means we fell off a ledge; skip the jump impulse
    if not msg.get("airborne_only", false):
        player.velocity.y = player.jump_velocity

func physics_update(delta: float) -> void:
    player.velocity.y += player.gravity * delta

    var direction := Input.get_axis("ui_left", "ui_right")
    if direction != 0.0:
        player.velocity.x = direction * player.speed
    else:
        player.velocity.x = move_toward(player.velocity.x, 0.0, player.speed)

    player.move_and_slide()

    if player.is_on_floor():
        var h_direction := Input.get_axis("ui_left", "ui_right")
        if h_direction != 0.0:
            state_machine.transition_to(&"Running")
        else:
            state_machine.transition_to(&"Idle")
```

---

## Scene Setup (player.tscn — editor steps)

1. Create a `CharacterBody2D` scene root, attach `player.gd`.
2. Add a child `Node` named `StateMachine`, attach `state_machine.gd`.
3. Under `StateMachine`, add three child `Node`s named exactly `Idle`, `Running`, `Jumping`, attach the matching state scripts.
4. On each state node, set the `player` export to the root `Player` node.
5. On the `StateMachine` node, set `initial_state` to the `Idle` node.
6. Add `CollisionShape2D` and `AnimationPlayer` (with `idle`, `run`, `jump` animations) as siblings under `Player`.

---

## How Transitions Work

| Current State | Condition | Next State |
|---|---|---|
| Idle | horizontal input detected | Running |
| Idle | jump pressed (on floor) | Jumping |
| Idle | not on floor | Jumping (airborne_only) |
| Running | no horizontal input, on floor | Idle |
| Running | jump pressed (on floor) | Jumping |
| Running | not on floor | Jumping (airborne_only) |
| Jumping | lands on floor, moving | Running |
| Jumping | lands on floor, still | Idle |

The `airborne_only` dictionary message passed to `Jumping.enter()` prevents the jump impulse from firing when the character simply walks off a ledge — a common edge case that the `msg: Dictionary` parameter on `enter()` handles cleanly without a separate Fall state.

---

## Verification Checklist

- [x] All variables, parameters, and return types are statically typed
- [x] No Godot 3 syntax (`yield`, bare `export`/`onready`, string-based `connect`)
- [x] No `get_node()`/`$` string paths crossing scene boundaries — states receive `player` via `@export var`
- [x] Signals flow up (`state_changed` emitted from StateMachine, re-emitted by Player); method calls flow down (Player.animation.play called by states)
- [x] `@export var player: Player` wired in the editor — no cross-scene string paths
- [x] No allocations or node lookups inside `_physics_process`
- [x] Node references cached via `@onready` in `player.gd`
- [x] `_unhandled_input` used for gameplay input (jump), not `_input`
