# State Machine for a Godot 4 CharacterBody2D

This implementation uses the **State design pattern** with a generic `StateMachine` node and a base `State` class. Three concrete states — `Idle`, `Running`, and `Jumping` — handle their own transitions based on velocity and input. The character itself only applies gravity and calls `move_and_slide()`; all game-logic decisions live inside the states.

---

## File overview

| File | Purpose |
|---|---|
| `state.gd` | Abstract base class every state inherits from |
| `state_machine.gd` | Manages the active state; routes `_physics_process`, `_process`, and `_unhandled_input` into it |
| `character.gd` | `CharacterBody2D` script — owns physics constants, applies gravity, hosts the `StateMachine` node |
| `idle_state.gd` | Stands still; transitions to Running on horizontal input or Jumping on jump input |
| `running_state.gd` | Moves horizontally; transitions to Idle when input stops, Jumping on jump input |
| `jumping_state.gd` | Airborne; applies initial impulse, allows air-steering, lands back to Idle or Running |

---

## Scene tree layout

```
Character (CharacterBody2D)   ← character.gd
├── CollisionShape2D
├── Sprite2D
├── AnimationPlayer           ← optional, used for animation calls
└── StateMachine (Node)       ← state_machine.gd
    ├── Idle  (Node)          ← idle_state.gd    (export var character → Character)
    ├── Running (Node)        ← running_state.gd (export var character → Character)
    └── Jumping (Node)        ← jumping_state.gd (export var character → Character)
```

Set the `character` export on each state node to point at the `Character` root node in the Inspector.

---

## state.gd

```gdscript
# state.gd
# Abstract base class for all states
class_name State
extends Node

# Reference back to the state machine that owns this state
var state_machine: StateMachine = null

# Called when entering this state
func enter() -> void:
    pass

# Called when leaving this state
func exit() -> void:
    pass

# Called every physics frame
func physics_update(_delta: float) -> void:
    pass

# Called every render frame
func update(_delta: float) -> void:
    pass

# Called for unhandled input events
func handle_input(_event: InputEvent) -> void:
    pass
```

---

## state_machine.gd

```gdscript
# state_machine.gd
# Base state machine class that manages states and transitions
class_name StateMachine
extends Node

var current_state: State = null
var states: Dictionary = {}

func _ready() -> void:
    # Collect all child State nodes
    for child in get_children():
        if child is State:
            states[child.name] = child
            child.state_machine = self

    # Enter the initial state (first child state)
    if current_state:
        current_state.enter()

func initialize(initial_state: State) -> void:
    current_state = initial_state
    current_state.enter()

func transition_to(state_name: String) -> void:
    if not states.has(state_name):
        push_error("StateMachine: State '%s' not found." % state_name)
        return

    if current_state:
        current_state.exit()

    current_state = states[state_name]
    current_state.enter()

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)

func _unhandled_input(event: InputEvent) -> void:
    if current_state:
        current_state.handle_input(event)
```

---

## character.gd

```gdscript
# character.gd
# CharacterBody2D with an integrated state machine for Idle, Running, and Jumping
extends CharacterBody2D

const SPEED: float = 200.0
const JUMP_VELOCITY: float = -400.0
const GRAVITY: float = 980.0

# Expose the state machine so individual state scripts can reach back into it
@onready var state_machine: StateMachine = $StateMachine

func _ready() -> void:
    # Initialize the state machine with the Idle state as the starting state
    state_machine.initialize(state_machine.states["Idle"])

func _physics_process(delta: float) -> void:
    # Apply gravity when not on the floor
    if not is_on_floor():
        velocity.y += GRAVITY * delta

    move_and_slide()
```

---

## idle_state.gd

```gdscript
# idle_state.gd
# The character is standing still on the ground.
class_name IdleState
extends State

@export var character: CharacterBody2D

func enter() -> void:
    # Stop horizontal movement when entering Idle
    character.velocity.x = 0
    # Play idle animation if an AnimationPlayer is present
    if character.has_node("AnimationPlayer"):
        character.get_node("AnimationPlayer").play("idle")

func physics_update(_delta: float) -> void:
    # If the character leaves the ground (e.g. walks off a ledge), jump to Jumping
    if not character.is_on_floor():
        state_machine.transition_to("Jumping")
        return

    # Check for horizontal movement input
    var direction: float = Input.get_axis("ui_left", "ui_right")
    if direction != 0.0:
        state_machine.transition_to("Running")
        return

func handle_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_accept"):
        state_machine.transition_to("Jumping")
```

---

## running_state.gd

```gdscript
# running_state.gd
# The character is moving horizontally on the ground.
class_name RunningState
extends State

@export var character: CharacterBody2D

func enter() -> void:
    if character.has_node("AnimationPlayer"):
        character.get_node("AnimationPlayer").play("run")

func physics_update(_delta: float) -> void:
    # If the character leaves the floor (walked off a ledge), switch to Jumping
    if not character.is_on_floor():
        state_machine.transition_to("Jumping")
        return

    var direction: float = Input.get_axis("ui_left", "ui_right")

    if direction != 0.0:
        character.velocity.x = direction * character.SPEED
        # Flip sprite to face movement direction
        if character.has_node("Sprite2D"):
            character.get_node("Sprite2D").flip_h = direction < 0
    else:
        # No input — decelerate and return to Idle
        character.velocity.x = move_toward(character.velocity.x, 0.0, character.SPEED)
        if character.velocity.x == 0.0:
            state_machine.transition_to("Idle")

func handle_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_accept"):
        state_machine.transition_to("Jumping")
```

---

## jumping_state.gd

```gdscript
# jumping_state.gd
# The character is airborne (either jumping or falling).
class_name JumpingState
extends State

@export var character: CharacterBody2D

func enter() -> void:
    # Apply jump impulse only if we were on the floor when the state was entered
    # (i.e. an intentional jump rather than walking off a ledge already in the air).
    # We check velocity.y to avoid double-jumping when falling off a ledge.
    if character.is_on_floor() or character.velocity.y == 0.0:
        character.velocity.y = character.JUMP_VELOCITY

    if character.has_node("AnimationPlayer"):
        character.get_node("AnimationPlayer").play("jump")

func physics_update(_delta: float) -> void:
    # Allow limited horizontal control in the air
    var direction: float = Input.get_axis("ui_left", "ui_right")
    if direction != 0.0:
        character.velocity.x = direction * character.SPEED
        if character.has_node("Sprite2D"):
            character.get_node("Sprite2D").flip_h = direction < 0
    else:
        # Gradually slow horizontal movement while airborne
        character.velocity.x = move_toward(character.velocity.x, 0.0, character.SPEED * 0.1)

    # Detect landing
    if character.is_on_floor():
        var horizontal_moving: bool = abs(character.velocity.x) > 1.0
        if horizontal_moving:
            state_machine.transition_to("Running")
        else:
            state_machine.transition_to("Idle")

func exit() -> void:
    # Switch to fall animation if available and still rising
    if character.velocity.y > 0 and character.has_node("AnimationPlayer"):
        character.get_node("AnimationPlayer").play("fall")
```

---

## Transition diagram

```
          no input / velocity.x == 0
 ┌──────────────────────────────────────┐
 │                                      ▼
Idle ──── horizontal input ────► Running
 │                                      │
 │  jump key                  jump key  │
 └──────────────► Jumping ◄─────────────┘
                     │
          land with    land without
          movement     movement
              │            │
              ▼            ▼
           Running        Idle
```

---

## Key design decisions

**Why `_unhandled_input` for jump detection?**
Using `handle_input` (routed from `_unhandled_input`) ensures the jump action is processed once per press and does not fight with UI or other input consumers.

**Why does `character.gd` own gravity and `move_and_slide`?**
Gravity is a physics constant that must apply in every state. Keeping it in the character node avoids code duplication across states and ensures the physics body always updates correctly. States only adjust `velocity.x` (and `velocity.y` on jump entry); the character applies the result.

**Walking off a ledge**
Both `IdleState` and `RunningState` check `is_on_floor()` at the start of `physics_update`. If the character walks off a platform without pressing jump, they still transition to `JumpingState`. In `JumpingState.enter()` the impulse is guarded: when `velocity.y` is already negative (falling) the impulse is skipped, so no unwanted upward kick happens.

**Air control**
In `JumpingState`, horizontal input sets speed normally so the character steers mid-air. When there is no input, `move_toward` applies a small deceleration factor (`SPEED * 0.1`) to preserve momentum while still slowing down over time.
