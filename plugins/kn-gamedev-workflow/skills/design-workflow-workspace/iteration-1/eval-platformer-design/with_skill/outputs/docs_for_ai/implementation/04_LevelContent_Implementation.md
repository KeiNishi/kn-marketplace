> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Level Content Implementation: Purrfect Run

## Architecture

### LevelManager
```
Purpose: Singleton; manages level state, goal detection, and scene transitions

Properties:
- _levelData: LevelData - current level configuration (injected from scene)
- _isLevelComplete: bool

Events:
- OnLevelComplete: System.Action<int> - passes star rating to UI

Methods:
- Awake(): void - register singleton
- OnGoalReached(): void - called by GoalTrigger; compute stars, fire event
- RestartLevel(): void - reload current scene via SceneLoader
- LoadNextLevel(): void - advance to next scene via SceneLoader
```

### GoalTrigger
```
Purpose: MonoBehaviour on the goal post collider

Methods:
- OnTriggerEnter2D(Collider2D other): void - detect player; call LevelManager.OnGoalReached()
```

### CameraFollow
```
Purpose: Smooth camera follow constrained within level bounds

Properties:
- _target: Transform - player transform
- _levelBoundsMin: Vector2 - left/bottom camera boundary
- _levelBoundsMax: Vector2 - right/top camera boundary
- _smoothTime: float - SmoothDamp time

Methods:
- LateUpdate(): void - SmoothDamp toward target X, clamp to bounds
```

### SceneLoader
```
Purpose: Centralized scene loading utility (static helper class)

Methods:
- LoadScene(string sceneName): void - async scene load with loading screen
- ReloadCurrentScene(): void - shorthand for current scene reload
```

### MovingPlatform
```
Purpose: MonoBehaviour for oscillating platforms in Levels 4-5

Properties:
- _pointA: Transform - start position waypoint
- _pointB: Transform - end position waypoint
- _speed: float - movement speed
- _moveDirection: int - +1 or -1

Methods:
- Update(): void - move between _pointA and _pointB; reverse on arrival
- OnDisable(): void - stop movement (edge case safety)
```

## Level Scene Setup

Each level scene (`SCN_Level01.unity` through `SCN_Level05.unity`) contains:
- Tilemap or platform prefabs composing the level layout
- `PFB_Cat.prefab` at spawn position
- Dog prefabs with `_patrolLeft` and `_patrolRight` waypoints as child Transforms
- Fish prefabs placed per design document
- Checkpoint prefabs at mid-level positions
- `GoalTrigger` prefab at end of level
- `LevelData` ScriptableObject assigned to `LevelManager` in Inspector
- Camera with `CameraFollow` component with bounds set in Inspector

## Tasks

### Phase 4: Level Content (Priority: High)

**Goal**: All 5 levels playable from start to goal with correct camera behavior

- [ ] Implement `LevelManager.cs` singleton with goal detection and scene transition
- [ ] Implement `GoalTrigger.cs` MonoBehaviour
- [ ] Implement `CameraFollow.cs` using `LateUpdate()` with SmoothDamp and clamped bounds
- [ ] Implement `SceneLoader.cs` static helper
- [ ] Implement `MovingPlatform.cs` for Levels 4-5
- [ ] Build Level 1 (Backyard): platforms, 1 slow dog, small/big fish, goal post
- [ ] Build Level 2 (Fish Market): 2 dogs with overlapping patrols, first checkpoint
- [ ] Build Level 3 (Alleyway): vertical platforms, fast dog, steeper gaps
- [ ] Build Level 4 (Rooftop): moving platforms, big dog, aerial golden fish
- [ ] Build Level 5 (Park): all dog types, tightest layout, all fish types
- [ ] Add level-unlock logic: next level unlocks when previous completed with 1+ star

**Deliverables**:
- All 5 levels completable; camera follows correctly; level unlock flow functional

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| CAMERA_SMOOTH_TIME | float | [EXAMPLE: 0.2f] | SmoothDamp time for camera follow |
| MOVING_PLATFORM_SPEED | float | [EXAMPLE: 2.0f] | Speed of moving platforms |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| SPR_Tileset_Backyard | PNG (atlas) | [EXAMPLE: 512x512] | P1 |
| SPR_Tileset_FishMarket | PNG (atlas) | [EXAMPLE: 512x512] | P2 |
| SPR_Tileset_Alleyway | PNG (atlas) | [EXAMPLE: 512x512] | P2 |
| SPR_Tileset_Rooftop | PNG (atlas) | [EXAMPLE: 512x512] | P2 |
| SPR_Tileset_Park | PNG (atlas) | [EXAMPLE: 512x512] | P2 |
| SPR_GoalPost | PNG | [EXAMPLE: 64x128] | P1 |
| SPR_Background_Parallax | PNG (per level) | [EXAMPLE: 1024x256] | P3 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| BGM_Level01 | BGM | MP3 | P2 |
| BGM_Level02 | BGM | MP3 | P2 |
| BGM_Level03 | BGM | MP3 | P2 |
| BGM_Level04 | BGM | MP3 | P2 |
| BGM_Level05 | BGM | MP3 | P2 |
| SFX_LevelComplete | SFX | WAV | P1 |

## Dependencies
- **Design**: [04_LevelContent_Design.md](../game_design/04_LevelContent_Design.md) - Level themes, layouts, progression
- **Related Implementation**: [01_Player_Implementation.md](./01_Player_Implementation.md) - Player spawn in scene; camera target
- **Related Implementation**: [03_Enemies_Implementation.md](./03_Enemies_Implementation.md) - Dog and checkpoint prefabs placed in levels
- **Related Implementation**: [05_UIAndPolish_Implementation.md](./05_UIAndPolish_Implementation.md) - LevelManager fires OnLevelComplete to UI; SceneLoader used by menu buttons
