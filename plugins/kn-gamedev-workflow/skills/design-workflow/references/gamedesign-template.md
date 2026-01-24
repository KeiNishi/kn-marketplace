# GameDesign.md Template

Use this template structure when creating `docs_for_ai/GameDesign.md`.

---

## Template

```markdown
# Game Design Document: [Project Name]

## 1. Game Overview

| Field | Value |
|-------|-------|
| **Title** | [Game Name] |
| **Genre** | [e.g., Action, Puzzle, RPG, Platformer] |
| **Platform** | [e.g., PC, Mobile, Playdate, Web] |
| **Engine/Framework** | [e.g., Unity, Godot, Playdate SDK, Custom] |
| **Target Audience** | [Age group, player preferences] |
| **Estimated Playtime** | [e.g., 10-20 hours, 5-minute sessions] |

## 2. Core Concept

### 2.1 Elevator Pitch
[1-2 sentence description capturing the essence of the game]

### 2.2 Unique Selling Points
- [USP 1]
- [USP 2]
- [USP 3]

### 2.3 Inspiration/References
[List similar games or media that inspired this design]

## 3. World and Setting

### 3.1 Setting Overview
[Brief description of the game world, time period, atmosphere]

### 3.2 Visual Style
[Art direction: pixel art, 3D realistic, cartoon, minimalist, etc.]

### 3.3 Audio Direction
[Music style, sound design approach, ambient sounds]

## 4. Game Mechanics

### 4.1 Core Loop
[Describe the primary gameplay loop the player repeats]

### 4.2 Player Actions

| Action | Description | Input |
|--------|-------------|-------|
| [Move] | [Movement description] | [D-pad/WASD] |
| [Jump] | [Jump description] | [A button/Space] |
| [Attack] | [Attack description] | [B button/Click] |

### 4.3 Progression System
[How the player advances: levels, upgrades, story progression, etc.]

### 4.4 Win/Loss Conditions
- **Victory**: [What constitutes winning]
- **Failure**: [What causes game over]

## 5. Game Systems

### 5.1 [System Name]
[Description of major game systems: combat, crafting, dialogue, etc.]

### 5.2 [System Name]
[Additional systems as needed]

## 6. Technical Requirements

### 6.1 Performance Targets
- Frame Rate: [e.g., 30/60 FPS]
- Resolution: [e.g., 400x240, 1920x1080]
- Load Time: [Target load times]

### 6.2 Technical Constraints
[Platform limitations, memory budgets, special considerations]

### 6.3 External Dependencies
[Required libraries, assets, services]

## 7. Content Scope

### 7.1 Levels/Stages
[Number of levels, their themes or descriptions]

### 7.2 Characters/Entities
[List of player characters, enemies, NPCs]

### 7.3 Items/Collectibles
[Power-ups, inventory items, collectibles]

## 8. Notes

- Values marked with [EXAMPLE: X] are subject to change during playtesting
- This document describes WHAT the game is; see ImplementationPlan.md for HOW to build it
```

---

## Example: Puzzle Platformer

```markdown
# Game Design Document: Crystal Caverns

## 1. Game Overview

| Field | Value |
|-------|-------|
| **Title** | Crystal Caverns |
| **Genre** | Puzzle Platformer |
| **Platform** | PC (Windows, macOS, Linux) |
| **Engine/Framework** | Godot 4 |
| **Target Audience** | Casual gamers, ages 10+ |
| **Estimated Playtime** | 3-5 hours |

## 2. Core Concept

### 2.1 Elevator Pitch
A puzzle platformer where players manipulate light beams to activate ancient mechanisms and escape mysterious underground caverns filled with glowing crystals.

### 2.2 Unique Selling Points
- Light-based puzzle mechanics with crystal refraction
- Atmospheric underground exploration
- Non-violent, relaxing gameplay

### 2.3 Inspiration/References
- The Witness (puzzle design)
- Celeste (tight platforming feel)
- Hollow Knight (atmospheric exploration)

## 3. World and Setting

### 3.1 Setting Overview
Deep underground cavern system filled with luminescent crystals. Ancient civilization left behind mechanisms that respond to light. Peaceful, mysterious atmosphere.

### 3.2 Visual Style
2D pixel art with dynamic lighting effects. Dark backgrounds with vibrant crystal colors (blue, purple, amber). Parallax scrolling for depth.

### 3.3 Audio Direction
Ambient cave sounds (dripping water, echoes). Soft, ethereal music. Crystal interaction sounds (chimes, resonance).

## 4. Game Mechanics

### 4.1 Core Loop
Explore room → Discover light puzzle → Manipulate crystals to direct light beam → Activate mechanism → Unlock path → Progress deeper

### 4.2 Player Actions

| Action | Description | Input |
|--------|-------------|-------|
| Move | Walk left/right | Arrow keys / A,D |
| Jump | Standard jump | Space |
| Interact | Rotate crystals, activate switches | E |
| Grab | Pick up movable crystals | Shift + E |

### 4.3 Progression System
Linear level progression with optional collectibles. No upgrades or abilities - pure puzzle solving.

### 4.4 Win/Loss Conditions
- **Victory**: Reach the surface exit in each level
- **Failure**: No death - player respawns at last checkpoint

## 5. Game Systems

### 5.1 Light Beam System
Light sources emit beams that travel in straight lines. Crystals can reflect or refract beams. Colored crystals filter light color. Mechanisms activate when receiving correct light color.

### 5.2 Checkpoint System
Automatic checkpoints at room entrances. Manual save at crystal pedestals.

## 6. Technical Requirements

### 6.1 Performance Targets
- Frame Rate: 60 FPS
- Resolution: 1920x1080 (16:9)
- Load Time: < 2 seconds per level

### 6.2 Technical Constraints
Light ray calculations limited to [EXAMPLE: 10] bounces maximum for performance.

### 6.3 External Dependencies
None - using Godot built-in features only.

## 7. Content Scope

### 7.1 Levels/Stages
- Tutorial Cavern (3 rooms)
- Crystal Depths (5 rooms)
- Prismatic Chamber (5 rooms)
- Ancient Core (4 rooms)
- Ascent (3 rooms)

### 7.2 Characters/Entities
- Player character (small explorer)
- No enemies

### 7.3 Items/Collectibles
- Memory Shards (optional lore collectibles, [EXAMPLE: 20] total)

## 8. Notes

- Values marked with [EXAMPLE: X] are subject to change during playtesting
- This document describes WHAT the game is; see ImplementationPlan.md for HOW to build it
```

---

## Guidelines

### Keep It Focused
GameDesign.md answers "What is this game?" - avoid implementation details like class names or code structure.

### Mark Variable Values
Any numeric value that might change during playtesting:
```markdown
- Jump height: [EXAMPLE: 3 tiles]
- Enemy health: [EXAMPLE: 100 HP]
```

### Avoid Duplication
Do not include:
- Folder structures (belongs in ImplementationPlan.md)
- Class definitions (belongs in ImplementationPlan.md)
- Build instructions (belongs in ImplementationPlan.md)

### Target Length
Aim for 500-1000 words. If exceeding this, consider whether all content is necessary.
