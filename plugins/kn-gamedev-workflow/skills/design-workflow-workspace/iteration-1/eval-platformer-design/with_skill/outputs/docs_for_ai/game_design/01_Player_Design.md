> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Player Design: Purrfect Run

## Overview
Player mechanics covering movement, jump physics, and touch controls for the cat protagonist navigating 2D platformer stages on mobile.

## Mechanics

### Horizontal Movement
The cat runs left and right at a constant speed. On mobile, two virtual buttons (Left arrow, Right arrow) control direction. The cat does not decelerate gradually — stopping input stops movement immediately for tight, responsive feel.

- Move speed: [EXAMPLE: 6.0 units/sec]
- No acceleration ramp — instant velocity for mobile usability

### Jumping
Single jump with a fixed impulse. Coyote time is granted so players can jump shortly after walking off a platform edge. Jump is triggered by a dedicated virtual button.

- Jump force: [EXAMPLE: 12.0 units]
- Coyote time window: [EXAMPLE: 0.12 seconds]
- No double jump — keeps skill ceiling accessible for casual players

### Touch Controls
On-screen virtual buttons displayed in the lower corners of the screen:
- Bottom-left: Left / Right directional arrows
- Bottom-right: Jump button

Controls scale to screen size. Transparent overlay buttons with clear iconography.

### Cat Animation States
The cat has distinct animation states that respond to input and physics:
- Idle: sitting pose when no input
- Run: looping run cycle
- Jump: stretched launch frame
- Fall: compressed falling frame
- Land: brief squash frame on landing

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| Cat (Player) | Orange tabby cat | Controlled by touch input; runs, jumps, collects fish |

## Player Actions

| Action | Description | Input |
|--------|-------------|-------|
| Move Left | Walk/run leftward | Left virtual button |
| Move Right | Walk/run rightward | Right virtual button |
| Jump | Leap upward | Jump virtual button |
| Collect Fish | Auto-collect on overlap | No input required (trigger) |

## Progression
The cat's moveset remains constant across all 5 levels — no unlocks or upgrades. Difficulty increases solely through level design: tighter platforms, more dogs, and more complex fish placement.

## Dependencies
- **Related Design**: [02_Collectibles_Design.md](./02_Collectibles_Design.md) - Cat auto-collects fish on overlap
- **Related Design**: [03_Enemies_Design.md](./03_Enemies_Design.md) - Contact with dog triggers death/reset
- **Related Design**: [04_LevelContent_Design.md](./04_LevelContent_Design.md) - Player navigates through all level layouts
- **Implementation**: [01_Player_Implementation.md](../implementation/01_Player_Implementation.md) - Architecture for player system
