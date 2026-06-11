# Godot 4 State Machine for CharacterBody2D

## Overview

This implementation provides a clean, extensible state machine for a Godot 4 `CharacterBody2D` character with three states: **Idle**, **Running**, and **Jumping**.

The design uses an enum to represent states and a dedicated handler method per state, which is idiomatic GDScript and easy to read without requiring separate class files.

---

## File Structure

```
res://
├── characters/
│   ├── player.gd          # Main character script (attached to CharacterBody2D)
│   └── player.tscn        # Scene (CharacterBody2D + CollisionShape2D + AnimatedSprite2D)
```

---

## Implementation

### `player.gd`

```gdscript
extends CharacterBody2D

# ─── Constants ────────────────────────────────────────────────────────────────
const SPEED        : float = 200.0
const JUMP_VELOCITY: float = -400.0
const GRAVITY      : float = 980.0   # pixels per second squared

# ─── State Enum ───────────────────────────────────────────────────────────────
enum State {
    IDLE,
    RUNNING,
    JUMPING,
}

# ─── State Variables ──────────────────────────────────────────────────────────
var current_state: State = State.IDLE
var previous_state: State = State.IDLE

# ─── Node References ──────────────────────────────────────────────────────────
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D

# ─── Built-in Callbacks ───────────────────────────────────────────────────────

func _ready() -> void:
    _enter_state(State.IDLE)


func _physics_process(delta: float) -> void:
    _apply_gravity(delta)
    _process_state(delta)
    move_and_slide()
    _evaluate_transitions()


# ─── Gravity ──────────────────────────────────────────────────────────────────

func _apply_gravity(delta: float) -> void:
    if not is_on_floor():
        velocity.y += GRAVITY * delta


# ─── State Machine Core ───────────────────────────────────────────────────────

## Called once whenever a new state is entered.
func _enter_state(new_state: State) -> void:
    previous_state = current_state
    current_state  = new_state

    match current_state:
        State.IDLE:
            animated_sprite.play("idle")

        State.RUNNING:
            animated_sprite.play("run")

        State.JUMPING:
            velocity.y = JUMP_VELOCITY
            animated_sprite.play("jump")


## Called every physics frame to handle input/logic for the active state.
func _process_state(delta: float) -> void:
    match current_state:
        State.IDLE:
            _state_idle(delta)

        State.RUNNING:
            _state_running(delta)

        State.JUMPING:
            _state_jumping(delta)


## Called every physics frame (after move_and_slide) to check for transitions.
func _evaluate_transitions() -> void:
    match current_state:
        State.IDLE:
            if not is_on_floor():
                _enter_state(State.JUMPING)
            elif _get_horizontal_input() != 0.0:
                _enter_state(State.RUNNING)
            elif Input.is_action_just_pressed("jump"):
                _enter_state(State.JUMPING)

        State.RUNNING:
            if not is_on_floor():
                _enter_state(State.JUMPING)
            elif Input.is_action_just_pressed("jump"):
                _enter_state(State.JUMPING)
            elif _get_horizontal_input() == 0.0:
                _enter_state(State.IDLE)

        State.JUMPING:
            if is_on_floor():
                if _get_horizontal_input() != 0.0:
                    _enter_state(State.RUNNING)
                else:
                    _enter_state(State.IDLE)


# ─── Per-state Logic ──────────────────────────────────────────────────────────

func _state_idle(_delta: float) -> void:
    # Decelerate horizontal velocity to zero while idle.
    velocity.x = move_toward(velocity.x, 0.0, SPEED)


func _state_running(_delta: float) -> void:
    var direction: float = _get_horizontal_input()
    velocity.x = direction * SPEED

    # Flip sprite to match movement direction.
    if direction != 0.0:
        animated_sprite.flip_h = direction < 0.0


func _state_jumping(_delta: float) -> void:
    # Allow air-strafing: player retains horizontal control in the air.
    var direction: float = _get_horizontal_input()
    if direction != 0.0:
        velocity.x = move_toward(velocity.x, direction * SPEED, SPEED * 2.0 * _delta)
        animated_sprite.flip_h = direction < 0.0
    else:
        velocity.x = move_toward(velocity.x, 0.0, SPEED * _delta)


# ─── Helpers ──────────────────────────────────────────────────────────────────

## Returns -1.0, 0.0, or 1.0 based on left/right input.
func _get_horizontal_input() -> float:
    return Input.get_axis("move_left", "move_right")
```

---

## Input Map Setup (Project > Project Settings > Input Map)

| Action       | Key           |
|--------------|---------------|
| `move_left`  | Arrow Left / A |
| `move_right` | Arrow Right / D |
| `jump`       | Space / Arrow Up |

---

## Scene Setup

1. Create a new scene with root node `CharacterBody2D`.
2. Add child nodes:
   - `CollisionShape2D` (assign a `CapsuleShape2D` or `RectangleShape2D`).
   - `AnimatedSprite2D` (add animation frames for `idle`, `run`, `jump`).
3. Attach `player.gd` to the root `CharacterBody2D` node.
4. Add a `StaticBody2D` with `CollisionShape2D` as the floor.

---

## State Transition Diagram

```
          ┌──────────────────────────────────────────────────────────┐
          │                                                          │
          ▼                     input != 0                           │
       ┌──────┐  ─────────────────────────────────────────►  ┌─────────┐
       │      │                                                │         │
       │ IDLE │◄───────────────────────────────────────────── │ RUNNING │
       │      │                  input == 0                    │         │
       └──────┘                                                └─────────┘
          │  ▲                                                    │  ▲
          │  │   land (input == 0)                 land (input != 0) │
   jump   │  └──────────────────────┐  ┌────────────────────────────┘
   press  │                         │  │
          ▼                         │  │
       ┌────────┐                   │  │
       │        │ ◄─────────────────┘  │
       │JUMPING │                      │
       │        │ ─────────────────────┘
       └────────┘
         (also entered when not is_on_floor from IDLE or RUNNING)
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Enum-based states | Type-safe, autocompleted in the Godot editor, no magic strings |
| `_enter_state()` for side effects | Animation changes and velocity impulses happen exactly once on transition |
| `_evaluate_transitions()` after `move_and_slide()` | `is_on_floor()` is accurate only after the physics step |
| Gravity applied unconditionally | Keeps gravity logic in one place; `is_on_floor()` naturally zeroes out floor-bound velocity |
| Air strafing in JUMPING | Common in platformers; gives the player responsive feel mid-air |

---

## Extension Points

- **Attack / Dash states**: Add new `State` enum values and corresponding `_state_*` / `_enter_state` branches.
- **Coyote time**: Track `time_since_left_floor` and allow jumps for a brief window after walking off an edge.
- **Double jump**: Add a `jump_count` variable and check it in the JUMPING transition guard.
- **Separate state classes**: For very large games, each state can be extracted into its own `Resource` or `Node` subclass, following the State design pattern.
