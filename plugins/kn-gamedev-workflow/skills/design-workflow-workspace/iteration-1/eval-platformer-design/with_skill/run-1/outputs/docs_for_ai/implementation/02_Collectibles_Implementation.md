> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Collectibles Implementation: Purrfect Run

## Architecture

### FishCollectible
```
Purpose: MonoBehaviour on each fish prefab; handles overlap detection and scoring

Properties:
- _fishData: FishData (ScriptableObject) - type, points, effects
- _collected: bool - guard flag to prevent double-collection

Methods:
- Awake(): void - cache components
- OnTriggerEnter2D(Collider2D other): void - detect player overlap
- Collect(): void - notify ScoreManager, play effects, deactivate self
```

### FishData (ScriptableObject)
```
Purpose: Data container for fish type configuration

Fields:
- FishType: FishType (enum: Small, Big, Golden)
- PointValue: int - score awarded on collection
- CollectEffect: ParticleSystem (prefab reference) - visual on collect
- CollectSound: AudioClip - sound on collect
```

### ScoreManager
```
Purpose: Singleton; tracks score for the current level and computes star rating

Properties:
- _currentScore: int
- _levelData: LevelData (ScriptableObject) - star thresholds
- CurrentScore: int (readonly property)

Events:
- OnScoreChanged: System.Action<int> - notifies HUD on update

Methods:
- Awake(): void - register singleton, reset score
- AddScore(int points): void - increment score, fire event
- GetStarRating(): int - compare score to LevelData thresholds; return 1-3
- ResetScore(): void - called on level restart
```

### LevelData (ScriptableObject)
```
Purpose: Per-level configuration for star thresholds and total available fish points

Fields:
- LevelName: string
- TotalFishPoints: int - maximum collectable points in level
- TwoStarThresholdPercent: float - [EXAMPLE: 0.50f]
- ThreeStarThresholdPercent: float - [EXAMPLE: 0.80f]
```

## Tasks

### Phase 2: Collectibles (Priority: Critical)

**Goal**: All three fish types collectible with scoring and star rating calculation

- [ ] Create `FishData` ScriptableObject class and three asset instances (Small, Big, Golden)
- [ ] Create `FishCollectible.cs` MonoBehaviour with trigger detection
- [ ] Create `PFB_FishSmall.prefab`, `PFB_FishBig.prefab`, `PFB_FishGolden.prefab`
- [ ] Add bobbing idle animation to Golden fish (simple Animator or LeanTween)
- [ ] Implement `ScoreManager.cs` singleton with `AddScore` and `GetStarRating`
- [ ] Create `LevelData` ScriptableObject class and one asset per level (5 total)
- [ ] Wire `ScoreManager.OnScoreChanged` to HUD fish count display (stub HUD OK for now)
- [ ] Verify `GetStarRating()` returns correct values at boundary percentages

**Deliverables**:
- Player collects fish, score increments; end-of-level star rating calculated correctly

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| FISH_SMALL_POINTS | int | [EXAMPLE: 1] | Points for small fish |
| FISH_BIG_POINTS | int | [EXAMPLE: 3] | Points for big fish |
| FISH_GOLDEN_POINTS | int | [EXAMPLE: 5] | Points for golden fish |
| TWO_STAR_THRESHOLD | float | [EXAMPLE: 0.50f] | Fraction of total fish for 2 stars |
| THREE_STAR_THRESHOLD | float | [EXAMPLE: 0.80f] | Fraction of total fish for 3 stars |
| GOLDEN_BOB_SPEED | float | [EXAMPLE: 1.5f] | Golden fish vertical bob frequency |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| SPR_Fish_Small | PNG | [EXAMPLE: 32x32] | P1 |
| SPR_Fish_Big | PNG | [EXAMPLE: 48x32] | P1 |
| SPR_Fish_Golden | PNG | [EXAMPLE: 48x32] | P1 |
| FX_Collect_Small | PNG (particle sheet) | [EXAMPLE: 32x32] | P2 |
| FX_Collect_Golden | PNG (particle sheet) | [EXAMPLE: 64x64] | P2 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| SFX_Collect_Small | SFX | WAV | P1 |
| SFX_Collect_Big | SFX | WAV | P1 |
| SFX_Collect_Golden | SFX | WAV | P1 |

## Dependencies
- **Design**: [02_Collectibles_Design.md](../game_design/02_Collectibles_Design.md) - Fish types, scoring, star rating rules
- **Related Implementation**: [01_Player_Implementation.md](./01_Player_Implementation.md) - Player collider triggers fish collection
- **Related Implementation**: [05_UIAndPolish_Implementation.md](./05_UIAndPolish_Implementation.md) - HUD displays current score; end screen shows star rating
