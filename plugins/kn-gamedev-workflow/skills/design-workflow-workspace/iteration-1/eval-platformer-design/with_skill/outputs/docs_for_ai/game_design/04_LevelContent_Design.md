> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Level Content Design: Purrfect Run

## Overview
Five hand-crafted levels with distinct visual themes. Each level introduces or escalates a design concept. All levels scroll horizontally from left to right, ending at a goal post.

## Level Themes and Goals

| Level | Name | Theme | New Element |
|-------|------|-------|-------------|
| 1 | Backyard Stroll | Sunny backyard with fences and flowerpots | Tutorial: movement, jump, first slow dog |
| 2 | Fish Market | Colorful market stalls and crates | Two dogs with overlapping patrols |
| 3 | Alleyway Chase | Dark alley, dumpsters, fire escapes | Fast dog introduced; vertical platforming |
| 4 | Rooftop Leap | City rooftops, chimneys, antenna towers | Big dog; wide gaps; aerial fish |
| 5 | Park Finale | Lush green park, fountains, benches | All dog types combined; tightest fish placement |

## Level Structure

Each level follows this general flow:
1. **Opening** - Safe section: introduce the environment, first few small fish
2. **Mid-section** - Obstacle escalation: dogs and bigger gaps
3. **Challenge peak** - Hardest stretch: golden fish near danger
4. **Goal** - Visible goal post (flag or finish line); level complete trigger

### Level Dimensions (approximate)
- Width: [EXAMPLE: 80 tiles] horizontal scrolling
- Height: [EXAMPLE: 15 tiles] vertical range
- Tile size: [EXAMPLE: 1 unit = 64px]

## Platform Types

| Platform | Description | First Appears |
|----------|-------------|---------------|
| Ground | Solid floor, runs full width sections | Level 1 |
| Fence/Ledge | Short fixed platform | Level 1 |
| Crate Stack | Taller platform group | Level 2 |
| Fire Escape | Vertical step platforms | Level 3 |
| Rooftop Edge | Narrow platforms, small gaps | Level 4 |
| Moving Platform | Horizontal or vertical oscillating platform | Level 4 |

## Goal and Completion

When the cat reaches the goal post:
1. Level complete fanfare plays
2. Fish collected and time elapsed are tallied
3. Star rating (1-3) is displayed
4. "Next Level" button unlocks (or returns to level select for replay)

## Checkpoint Placement
- Level 1: No checkpoint (short level)
- Levels 2-5: [EXAMPLE: 1-2 checkpoints] per level placed at natural midpoints before difficult sections

## Progression
Each new level unlocks after completing the previous with at least 1 star. Players can replay any unlocked level for higher star ratings.

## Dependencies
- **Related Design**: [01_Player_Design.md](./01_Player_Design.md) - Player traverses level layouts
- **Related Design**: [02_Collectibles_Design.md](./02_Collectibles_Design.md) - Fish placement per level
- **Related Design**: [03_Enemies_Design.md](./03_Enemies_Design.md) - Dog patrol positions per level
- **Implementation**: [04_LevelContent_Implementation.md](../implementation/04_LevelContent_Implementation.md) - Architecture for level building and scene management
