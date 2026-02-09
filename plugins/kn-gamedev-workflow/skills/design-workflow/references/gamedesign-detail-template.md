# Game Design Detail File Template

Use this template structure when creating detail design files in `docs_for_ai/game_design/`.

**Naming convention**: `NN_SystemName_Design.md` (e.g., `01_Player_Design.md`, `02_Enemy_Design.md`)

---

## Template

```markdown
> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# [Domain Name] Design: [Project Name]

## Overview
[1-2 sentence summary of what this domain covers]

## Mechanics

### [Mechanic Name]
[Description of the mechanic, including player-facing behavior]

### [Mechanic Name]
[Additional mechanics as needed]

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| [Name] | [What it is] | [What it does] |

## Player Actions

| Action | Description | Input |
|--------|-------------|-------|
| [Action] | [Description] | [Control input] |

## Progression
[How this domain's elements evolve or scale throughout the game]

## Dependencies
- **Related Design**: [NN_OtherSystem_Design.md](./NN_OtherSystem_Design.md) - [How they interact]
- **Implementation**: [NN_SystemName_Implementation.md](../implementation/NN_SystemName_Implementation.md) - Architecture for this system
```

---

## Example: Player Design

```markdown
> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Player Design: Crystal Caverns

## Overview
Player mechanics covering movement, interaction, and progression for the explorer character navigating crystal caverns.

## Mechanics

### Movement
Standard platformer movement: walk left/right with variable speed, single jump with coyote time for forgiving input. No wall jump or dash - keeping controls simple.

### Crystal Interaction
Player can rotate crystals by standing next to them and pressing interact. Movable crystals can be grabbed and repositioned within the current room.

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| Player | Small explorer character | Controlled by player input |

## Player Actions

| Action | Description | Input |
|--------|-------------|-------|
| Move | Walk left/right | Arrow keys / A,D |
| Jump | Standard jump | Space |
| Interact | Rotate crystals, activate switches | E |
| Grab | Pick up movable crystals | Shift + E |

## Progression
Linear level progression with optional collectibles (Memory Shards). No upgrades or abilities - pure puzzle solving. Difficulty increases through more complex light puzzles, not through new player abilities.

## Dependencies
- **Related Design**: [02_LightSystem_Design.md](./02_LightSystem_Design.md) - Player interacts with crystals and light beams
- **Related Design**: [03_LevelContent_Design.md](./03_LevelContent_Design.md) - Player navigates level layouts
- **Implementation**: [01_Player_Implementation.md](../implementation/01_Player_Implementation.md) - Architecture for player system
```

---

## Example: Light System Design

```markdown
> Part of [GameDesignOverview.md](../GameDesignOverview.md)

# Light System Design: Crystal Caverns

## Overview
Core puzzle system based on manipulating light beams through crystals to activate ancient mechanisms.

## Mechanics

### Light Beam Emission
Light sources emit beams that travel in straight lines. Beams are visible as colored lines. Each light source has a fixed position and initial direction.

### Crystal Reflection
Crystals can reflect light beams at angles determined by crystal rotation. Player rotates crystals to redirect beams.

### Color Filtering
Colored crystals filter light color. Mechanisms activate only when receiving the correct light color. Color mixing: Red + Blue = Purple, etc.

### Mechanism Activation
Mechanisms (doors, platforms, bridges) activate when receiving the correct light color. Some require sustained light, others toggle on/off.

## Entities

| Entity | Description | Behavior |
|--------|-------------|----------|
| Light Source | Fixed emitter | Emits colored beam in one direction |
| Crystal (Reflect) | Rotatable mirror | Reflects beam at rotation angle |
| Crystal (Filter) | Colored crystal | Filters beam to specific color |
| Crystal (Movable) | Grabbable crystal | Player can reposition within room |
| Mechanism | Light receiver | Activates when receiving correct color |
| Door/Gate | Blocking path | Opens when linked mechanism activates |

## Progression
- Tutorial: Single beam, single crystal, one reflection
- Mid-game: Multiple beams, color filtering, chain reflections
- Late-game: Color mixing, movable crystals, multi-step puzzles with [EXAMPLE: 5-8] crystals per room

## Dependencies
- **Related Design**: [01_Player_Design.md](./01_Player_Design.md) - Player interaction controls
- **Related Design**: [03_LevelContent_Design.md](./03_LevelContent_Design.md) - Puzzle placement in levels
- **Implementation**: [02_LightSystem_Implementation.md](../implementation/02_LightSystem_Implementation.md) - Architecture for light system
```

---

## Guidelines

### Section Flexibility
Not all sections are required for every detail file. Use only the sections that apply:
- A combat system file needs Entities and Player Actions
- A narrative system file may only need Mechanics and Progression
- A content file (levels/stages) may need custom sections (Room Layouts, etc.)

### Back-Link Is Required
Every detail file MUST start with:
```markdown
> Part of [GameDesignOverview.md](../GameDesignOverview.md)
```

### Dependencies Are Required
Every detail file MUST end with a Dependencies section listing:
- Related design files it interacts with
- Corresponding implementation file

### Focus on Domain
Each file covers ONE domain. Avoid repeating information from other detail files - reference them instead.

### Mark Variable Values
```markdown
- Beam bounce limit: [EXAMPLE: 10]
- Crystal rotation step: [EXAMPLE: 15 degrees]
```

### Target Length
Aim for 200-500 words per detail file. If exceeding 500 words, consider splitting into sub-domains.

### Maximum Files
Soft cap of 20 detail design files per project. If approaching this limit, consider consolidating related systems.
