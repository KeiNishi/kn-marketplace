# Implementation Plan: Purrfect Run

## 1. Project Structure

### 1.1 Folder Layout

```
PurrfectRun/
├── Assets/
│   ├── _Project/
│   │   ├── Art/
│   │   │   ├── Animations/        # ANIM_Cat_Run.anim, ANIM_Dog_Walk.anim, etc.
│   │   │   ├── Sprites/           # SPR_Cat.png, SPR_Fish_Small.png, etc.
│   │   │   └── UI/                # SPR_Button_Jump.png, SPR_Star_Full.png, etc.
│   │   ├── Audio/
│   │   │   ├── Music/             # BGM_Level01.mp3, BGM_Level02.mp3, etc.
│   │   │   └── SFX/               # SFX_Jump.wav, SFX_Collect.wav, SFX_Bonk.wav
│   │   ├── Prefabs/
│   │   │   ├── Characters/        # PFB_Cat.prefab, PFB_DogSlow.prefab, etc.
│   │   │   ├── Collectibles/      # PFB_FishSmall.prefab, PFB_FishBig.prefab, etc.
│   │   │   └── Environment/       # PFB_Platform.prefab, PFB_Checkpoint.prefab, etc.
│   │   ├── Scenes/
│   │   │   ├── _Init/             # SCN_Boot.unity, SCN_MainMenu.unity
│   │   │   └── Levels/            # SCN_Level01.unity through SCN_Level05.unity
│   │   ├── ScriptableObjects/
│   │   │   ├── Configs/           # SO_PlayerConfig.asset, SO_FishConfig.asset
│   │   │   └── Data/              # SO_LevelData.asset (per level star thresholds)
│   │   ├── Scripts/
│   │   │   ├── Core/              # GameManager.cs, AudioManager.cs, SaveManager.cs
│   │   │   ├── Gameplay/          # PlayerController.cs, DogAI.cs, FishCollectible.cs
│   │   │   └── UI/                # HUDController.cs, LevelSelectController.cs
│   │   └── Settings/
│   └── Plugins/
├── Packages/
└── docs_for_ai/
    ├── GameDesignOverview.md
    ├── ImplementationPlanOverview.md
    ├── game_design/
    └── implementation/
```

### 1.2 Naming Conventions
- Scripts: `PascalCase.cs` (e.g., `PlayerController.cs`)
- Prefabs: `PFB_Name.prefab` (e.g., `PFB_Cat.prefab`)
- Sprites: `SPR_Name.png` (e.g., `SPR_Fish_Golden.png`)
- Audio clips: `SFX_Name.wav` / `BGM_Name.mp3`
- ScriptableObjects: `SO_Name.asset`
- Scenes: `SCN_Name.unity`
- Constants: `SCREAMING_SNAKE_CASE`
- Private fields: `_camelCase`

## 2. Phase Summary

| Phase | Name | Priority | Detail Files | Status |
|-------|------|----------|-------------|--------|
| 1 | Player Core | Critical | 01_Player_Implementation.md | Not Started |
| 2 | Collectibles | Critical | 02_Collectibles_Implementation.md | Not Started |
| 3 | Enemies | High | 03_Enemies_Implementation.md | Not Started |
| 4 | Level Content | High | 04_LevelContent_Implementation.md | Not Started |
| 5 | UI and Polish | Medium | 05_UIAndPolish_Implementation.md | Not Started |

## 3. Implementation File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_Player_Implementation.md](./implementation/01_Player_Implementation.md) | Player | Cat controller, touch input, animation state machine |
| 02 | [02_Collectibles_Implementation.md](./implementation/02_Collectibles_Implementation.md) | Collectibles | Fish prefabs, scoring, star rating system |
| 03 | [03_Enemies_Implementation.md](./implementation/03_Enemies_Implementation.md) | Enemies | Dog AI patrol, checkpoint system, respawn logic |
| 04 | [04_LevelContent_Implementation.md](./implementation/04_LevelContent_Implementation.md) | Levels | Scene management, level data, camera follow |
| 05 | [05_UIAndPolish_Implementation.md](./implementation/05_UIAndPolish_Implementation.md) | UI/Polish | HUD, level select, audio manager, save system |

## 4. Key Constants (Shared/Global)

| Name | Type | Value | Description |
|------|------|-------|-------------|
| PLAYER_SPEED | float | [EXAMPLE: 6.0f] | Horizontal movement speed (units/sec) |
| JUMP_FORCE | float | [EXAMPLE: 12.0f] | Jump impulse magnitude |
| COYOTE_TIME | float | [EXAMPLE: 0.12f] | Jump grace period after leaving platform (seconds) |
| GRAVITY_SCALE | float | [EXAMPLE: 3.0f] | Rigidbody2D gravity scale multiplier |
| DOG_SLOW_SPEED | float | [EXAMPLE: 2.0f] | Slow dog patrol speed (units/sec) |
| DOG_FAST_SPEED | float | [EXAMPLE: 3.5f] | Fast dog patrol speed (units/sec) |

*Values marked [EXAMPLE] are initial estimates subject to tuning*

## 5. Dependencies

### 5.1 External Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| Unity Engine | 6.3 LTS | Game engine |
| Unity Input System | 1.7+ | Mobile touch input |

### 5.2 Development Tools
- Unity 6.3 LTS: Primary development environment
- Aseprite or similar: 2D sprite creation
- Audacity: SFX editing
- TextMeshPro: In-game UI text (included with Unity)

## 6. Testing Strategy

### 6.1 Playtest Checkpoints
- [ ] Phase 1 complete: Cat moves, jumps, and coyote time feels correct on device
- [ ] Phase 2 complete: Fish collection triggers scoring and star rating calculations work
- [ ] Phase 3 complete: Dogs patrol correctly; respawn to checkpoint functions
- [ ] Phase 4 complete: All 5 levels completable; camera follows player without jitter
- [ ] Full game: Level unlock flow works; save/load persists star ratings

### 6.2 Key Test Cases
- Jump feels responsive with coyote time on mobile touch
- Golden fish scoring edge case: exactly 80% threshold awards 3 stars
- Dog contact resets position to checkpoint, not level start (after checkpoint passed)
- Collected fish are NOT lost on respawn
- Star ratings persist after app restart

## 7. Notes

- Implementation order may be adjusted based on dependencies discovered during development
- See GameDesignOverview.md for game concept and mechanics details
- See detail files in `implementation/` for architecture and task breakdowns
- Unity MVC pattern (Controller/Model/View) applies to Player and Dog characters per unity-gamedev-standards
- All camera updates MUST use `LateUpdate()` to avoid jitter (Unity standard)
- Inspector-configurable values must NOT be overridden in `Awake()`/`Start()`
