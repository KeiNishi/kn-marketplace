> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Collectibles Design: Purrfect Run

## Overview
Fish collectibles are the primary reward in each level. Three fish tiers offer different point values and placement challenge. Score drives the star-rating system at level end.

## Mechanics

### Fish Collection
The cat auto-collects a fish when its collider overlaps the fish trigger zone. No button press required. A brief visual and audio effect plays on collection.

### Fish Tiers

| Type | Sprite | Points | Placement |
|------|--------|--------|-----------|
| Small Fish | Small silver fish | [EXAMPLE: 1 pt] | Abundant, easy to reach |
| Big Fish | Large blue fish | [EXAMPLE: 3 pt] | Moderate risk — require detour |
| Golden Fish | Glowing gold fish | [EXAMPLE: 5 pt] | High risk — near dogs or difficult platforms |

### Scoring and Star Rating
At level end, total fish points collected determine the star rating:

| Stars | Condition |
|-------|-----------|
| 1 star | Reached the goal (any score) |
| 2 stars | Collected [EXAMPLE: 50%] of available fish points |
| 3 stars | Collected [EXAMPLE: 80%] of available fish points |

Stars are displayed on the level select screen and saved persistently.

### Fish Placement Philosophy
- Small fish form natural "safe" paths guiding the player forward
- Big fish are placed on slightly elevated or offset platforms
- Golden fish appear in high-difficulty spots (near patrolling dogs, at the edge of a jump gap)
- No fish is placed in an unreachable location

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| Small Fish | Silver collectible | Static, disappears on collection with sparkle effect |
| Big Fish | Blue collectible | Static, disappears on collection with splash effect |
| Golden Fish | Glowing gold collectible | Bobs up and down slightly; disappears with star burst effect |

## Progression
- Level 1: Only small and big fish — introduce collection loop
- Levels 2-3: Golden fish introduced in safer positions
- Levels 4-5: Golden fish placed in high-risk spots near dog patrols

## Dependencies
- **Related Design**: [01_Player_Design.md](./01_Player_Design.md) - Player auto-collects fish on overlap
- **Related Design**: [04_LevelContent_Design.md](./04_LevelContent_Design.md) - Fish placement within level layouts
- **Implementation**: [02_Collectibles_Implementation.md](../implementation/02_Collectibles_Implementation.md) - Architecture for collectible system
