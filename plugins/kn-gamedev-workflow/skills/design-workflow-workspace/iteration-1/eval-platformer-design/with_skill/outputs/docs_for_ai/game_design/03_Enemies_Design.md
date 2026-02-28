> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Enemies Design: Purrfect Run

## Overview
Dogs are the only enemy type. They patrol defined segments of each level and send the cat back to the last checkpoint on contact. Their comedic bumbling character matches the light tone of the game.

## Mechanics

### Dog Patrol Behavior
Dogs walk back and forth along a fixed horizontal patrol path. When reaching a patrol boundary (a wall or an invisible waypoint), they turn around and continue walking. They do not chase the player.

- Dog walk speed: [EXAMPLE: 2.5 units/sec]
- Patrol range: defined per dog instance in level design

### Contact Resolution
When the cat's collider touches a dog's collider:
1. Play "bonk" sound effect and brief screen shake
2. Cat sprite flashes and plays a "hurt" animation
3. Cat is reset to the nearest checkpoint (or level start if no checkpoint passed)
4. Dog continues patrol uninterrupted

There is no health system — a single contact triggers the reset. This keeps the mechanic simple and readable.

### Dog Variants

| Variant | Speed | Patrol Style | Introduced |
|---------|-------|-------------|------------|
| Slow Dog | [EXAMPLE: 2.0 units/sec] | Short patrol, predictable | Level 1 |
| Fast Dog | [EXAMPLE: 3.5 units/sec] | Longer patrol, faster turnaround | Level 3 |
| Big Dog | [EXAMPLE: 2.5 units/sec] | Wide body, harder to jump over | Level 4 |

### Checkpoints
Checkpoints are flag objects placed mid-level. When the cat passes through a checkpoint, it becomes the new respawn point. Checkpoints are visible and clearly indicated (flag pops up).

- Checkpoints do not reset on respawn — the player keeps progress from the last checkpoint
- Fish already collected are NOT lost on respawn

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| Slow Dog | Small brown terrier | Patrols slowly, short range |
| Fast Dog | Medium grey dog | Patrols quickly, longer range |
| Big Dog | Large cartoon bulldog | Wide body; intimidating but slow |
| Checkpoint Flag | Green flag post | Saves respawn position when player passes |

## Progression
- Level 1: One slow dog — introduces the avoidance mechanic
- Level 2: Two slow dogs with overlapping patrols
- Level 3: First fast dog introduced
- Level 4: Mix of fast dogs and big dog blocking platforms
- Level 5: Three dog types combined; requires timing and planning

## Dependencies
- **Related Design**: [01_Player_Design.md](./01_Player_Design.md) - Cat contact with dog triggers respawn
- **Related Design**: [04_LevelContent_Design.md](./04_LevelContent_Design.md) - Dog patrol positions defined per level
- **Implementation**: [03_Enemies_Implementation.md](../implementation/03_Enemies_Implementation.md) - Architecture for enemy and checkpoint systems
