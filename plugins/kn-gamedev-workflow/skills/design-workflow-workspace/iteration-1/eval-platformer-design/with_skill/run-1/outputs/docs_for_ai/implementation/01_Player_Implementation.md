> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Player Implementation: Purrfect Run

## Architecture

### PlayerController
```
Purpose: Handle touch input reading and drive the PlayerModel state machine

Properties:
- _model: PlayerModel - reference to the data/logic layer
- _view: PlayerView - reference to the animation/visual layer
- _jumpBuffer: float - time remaining in jump buffer window

Methods:
- Awake(): void - cache component references
- Update(): void - read touch input, manage jump buffer
- FixedUpdate(): void - delegate movement to PlayerModel
- OnEnable(): void - subscribe to input events
- OnDisable(): void - unsubscribe from input events
```

### PlayerModel
```
Purpose: Physics logic, velocity management, ground detection

Properties:
- _rigidbody: Rigidbody2D - physics component
- _groundCheck: Transform - point used for ground overlap detection
- _groundLayer: LayerMask - layers considered ground
- _coyoteTimer: float - countdown after leaving ground
- IsGrounded: bool (readonly property)

Methods:
- Move(float direction): void - apply horizontal velocity
- Jump(): void - apply jump impulse if grounded or coyote active
- ApplyGravity(): void - adjust fall speed for feel (FixedUpdate)
- CheckGround(): void - overlap circle check for ground contact
```

### PlayerView
```
Purpose: Manage animator and sprite facing direction

Properties:
- _animator: Animator - reference to Animator component
- _spriteRenderer: SpriteRenderer - for facing flip

Methods:
- SetRunning(bool isRunning): void - set Animator "IsRunning" bool
- SetGrounded(bool isGrounded): void - set Animator "IsGrounded" bool
- SetFacingDirection(float horizontal): void - flip sprite on X axis
- PlayHurtEffect(): void - trigger "Hurt" animator trigger + flash coroutine
```

### TouchInputHandler
```
Purpose: Translate mobile touch/virtual button events to game input events

Properties:
- LeftButton: Button (UI)
- RightButton: Button (UI)
- JumpButton: Button (UI)

Events:
- OnMoveLeft: System.Action<bool>
- OnMoveRight: System.Action<bool>
- OnJump: System.Action

Methods:
- Awake(): void - bind button press/release events
```

## State Management

```
PlayerState:
  IDLE   <─── Land ─── FALLING
    │                     ▲
  Move                    │
    │                   Jump / Coyote
    ▼                     │
  RUNNING ──── Jump ──► JUMPING ──► FALLING
    │
  Stop
    │
  IDLE

HURT: triggered from any state → brief flash → return to previous state
```

## Tasks

### Phase 1: Player Core (Priority: Critical)

**Goal**: Playable cat with mobile touch movement and jump on a test level

- [ ] Create `PFB_Cat.prefab` with `Rigidbody2D`, `BoxCollider2D`, `Animator`, `SpriteRenderer`
- [ ] Implement `PlayerModel.cs` with horizontal movement and jump impulse
- [ ] Implement ground check using `Physics2D.OverlapCircle`
- [ ] Add coyote time countdown in `PlayerModel`
- [ ] Implement `PlayerView.cs` with animator parameter updates and sprite flip
- [ ] Implement `PlayerController.cs` wiring Model and View
- [ ] Implement `TouchInputHandler.cs` with on-screen virtual buttons
- [ ] Create test scene with platforms to validate movement feel
- [ ] Add camera follow (see LevelContent implementation)

**Deliverables**:
- Cat moves left/right and jumps using on-screen buttons on a mobile device

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| PLAYER_SPEED | float | [EXAMPLE: 6.0f] | Horizontal speed (units/sec) |
| JUMP_FORCE | float | [EXAMPLE: 12.0f] | Jump impulse (Rigidbody2D.AddForce Impulse) |
| COYOTE_TIME | float | [EXAMPLE: 0.12f] | Grace window after leaving platform (seconds) |
| JUMP_BUFFER_TIME | float | [EXAMPLE: 0.1f] | Pre-ground jump input buffering (seconds) |
| GROUND_CHECK_RADIUS | float | [EXAMPLE: 0.1f] | Overlap circle radius for ground detection |
| FALL_GRAVITY_MULTIPLIER | float | [EXAMPLE: 1.5f] | Extra gravity when falling for snappy feel |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| SPR_Cat_Idle | PNG (sprite sheet) | [EXAMPLE: 64x64 per frame] | P1 |
| SPR_Cat_Run | PNG (sprite sheet) | [EXAMPLE: 64x64 per frame, 8 frames] | P1 |
| SPR_Cat_Jump | PNG (sprite sheet) | [EXAMPLE: 64x64 per frame, 3 frames] | P1 |
| SPR_Cat_Fall | PNG (sprite sheet) | [EXAMPLE: 64x64 per frame, 2 frames] | P1 |
| SPR_Cat_Hurt | PNG (sprite sheet) | [EXAMPLE: 64x64 per frame, 2 frames] | P2 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| SFX_Jump | SFX | WAV | P1 |
| SFX_Land | SFX | WAV | P2 |

## Dependencies
- **Design**: [01_Player_Design.md](../game_design/01_Player_Design.md) - Player mechanics and touch controls
- **Related Implementation**: [03_Enemies_Implementation.md](./03_Enemies_Implementation.md) - PlayerView.PlayHurtEffect() called on dog contact
- **Related Implementation**: [04_LevelContent_Implementation.md](./04_LevelContent_Implementation.md) - Camera follows player; level defines ground layer
