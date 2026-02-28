> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Enemies Implementation: Purrfect Run

## Architecture

### DogController
```
Purpose: MonoBehaviour driving dog patrol AI and player contact handling

Properties:
- _dogData: DogData (ScriptableObject) - speed, patrol distance
- _patrolLeft: Transform - left patrol waypoint
- _patrolRight: Transform - right patrol waypoint
- _facingRight: bool - current facing direction
- _spriteRenderer: SpriteRenderer - for direction flip
- _animator: Animator - walk animation

Methods:
- Awake(): void - cache references, set initial direction
- Update(): void - move toward current waypoint; flip on arrival
- OnTriggerEnter2D(Collider2D other): void - detect player contact
- FlipDirection(): void - reverse facing and swap waypoint target
```

### DogData (ScriptableObject)
```
Purpose: Configuration for each dog variant

Fields:
- DogType: DogType (enum: Slow, Fast, Big)
- PatrolSpeed: float - walk speed units/sec
- BodyWidth: float - collider width reference (set in Inspector)
```

### CheckpointSystem
```
Purpose: MonoBehaviour on Checkpoint prefab; registers with CheckpointManager on trigger

Methods:
- OnTriggerEnter2D(Collider2D other): void - notify CheckpointManager if player
```

### CheckpointManager
```
Purpose: Singleton; tracks the active checkpoint and handles player respawn

Properties:
- _currentCheckpoint: Vector3 - world position for respawn
- _player: Transform - player reference

Methods:
- Awake(): void - register singleton, set default respawn to level start
- RegisterCheckpoint(Vector3 position): void - update active respawn position
- RespawnPlayer(): void - teleport player to _currentCheckpoint, call PlayerView.PlayHurtEffect()
```

## State Management (Dog)

```
DogAI:
  PATROL_RIGHT ──(reach right waypoint)──► PATROL_LEFT
       ▲                                          │
       └───────(reach left waypoint)──────────────┘

Contact with player → fires event → CheckpointManager.RespawnPlayer()
Dog itself does NOT change state on contact
```

## Tasks

### Phase 3: Enemies (Priority: High)

**Goal**: Dogs patrol correctly; player respawns to checkpoint on contact

- [ ] Create `DogData` ScriptableObject class and three variant assets (Slow, Fast, Big)
- [ ] Implement `DogController.cs` with waypoint-based patrol movement
- [ ] Add sprite flip when dog reverses direction
- [ ] Implement `OnTriggerEnter2D` to detect player layer; fire respawn event
- [ ] Create `PFB_DogSlow.prefab`, `PFB_DogFast.prefab`, `PFB_DogBig.prefab`
- [ ] Implement `CheckpointManager.cs` singleton
- [ ] Implement `CheckpointSystem.cs` MonoBehaviour on checkpoint prefab
- [ ] Create `PFB_Checkpoint.prefab` (flag sprite, trigger collider)
- [ ] Test: verify fish collected before checkpoint are NOT lost on respawn
- [ ] Test: verify respawn position updates correctly when multiple checkpoints are passed

**Deliverables**:
- Dogs patrol between waypoints; touching dog resets cat to last checkpoint; checkpoint flag activates on pass

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| DOG_SLOW_SPEED | float | [EXAMPLE: 2.0f] | Slow dog patrol speed (units/sec) |
| DOG_FAST_SPEED | float | [EXAMPLE: 3.5f] | Fast dog patrol speed (units/sec) |
| DOG_BIG_SPEED | float | [EXAMPLE: 2.5f] | Big dog patrol speed (units/sec) |
| RESPAWN_INVINCIBILITY_TIME | float | [EXAMPLE: 1.5f] | Seconds of invincibility after respawn |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| SPR_Dog_Slow_Walk | PNG (sprite sheet) | [EXAMPLE: 64x64, 4 frames] | P1 |
| SPR_Dog_Fast_Walk | PNG (sprite sheet) | [EXAMPLE: 64x64, 4 frames] | P1 |
| SPR_Dog_Big_Walk | PNG (sprite sheet) | [EXAMPLE: 96x96, 4 frames] | P1 |
| SPR_Checkpoint_Idle | PNG | [EXAMPLE: 32x64] | P1 |
| SPR_Checkpoint_Active | PNG | [EXAMPLE: 32x64] | P1 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| SFX_Bonk | SFX | WAV | P1 |
| SFX_Checkpoint | SFX | WAV | P2 |

## Dependencies
- **Design**: [03_Enemies_Design.md](../game_design/03_Enemies_Design.md) - Dog behavior, variants, checkpoint rules
- **Related Implementation**: [01_Player_Implementation.md](./01_Player_Implementation.md) - PlayerView.PlayHurtEffect() called on respawn; player layer used for detection
- **Related Implementation**: [04_LevelContent_Implementation.md](./04_LevelContent_Implementation.md) - Dog waypoints and checkpoint positions placed in level scenes
