# GameDesignOverview.md Template

Use this template structure when creating `docs_for_ai/GameDesignOverview.md`.

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

## 4. Design File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_Player_Design.md](./game_design/01_Player_Design.md) | Player | [Brief description] |
| 02 | [02_SystemName_Design.md](./game_design/02_SystemName_Design.md) | [Domain] | [Brief description] |

## 5. Cross-Cutting Concerns

### 5.1 [Concern Name]
[Items that span multiple systems - e.g., save system, audio, UI, accessibility]

### 5.2 [Concern Name]
[Additional cross-cutting items as needed]

## 6. Technical Requirements

### 6.1 Performance Targets
- Frame Rate: [e.g., 30/60 FPS]
- Resolution: [e.g., 400x240, 1920x1080]
- Load Time: [Target load times]

### 6.2 Technical Constraints
[Platform limitations, memory budgets, special considerations]

### 6.3 External Dependencies
[Required libraries, assets, services]

## 7. Content Scope Summary

| Category | Count | Details |
|----------|-------|---------|
| Levels/Stages | [N] | [Brief description] |
| Characters/Entities | [N] | [Brief description] |
| Items/Collectibles | [N] | [Brief description] |

## 8. Notes

- Values marked with [EXAMPLE: X] are subject to change during playtesting
- This document provides an overview; see detail files in `game_design/` for specifics
- See ImplementationPlanOverview.md for HOW to build it
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

## 4. Design File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_Player_Design.md](./game_design/01_Player_Design.md) | Player | Player mechanics, controls, progression |
| 02 | [02_LightSystem_Design.md](./game_design/02_LightSystem_Design.md) | Light/Puzzles | Light beams, crystals, mechanisms |
| 03 | [03_LevelContent_Design.md](./game_design/03_LevelContent_Design.md) | Content | Level descriptions, room layouts, collectibles |

## 5. Cross-Cutting Concerns

### 5.1 Checkpoint System
Automatic checkpoints at room entrances. Manual save at crystal pedestals. Applies across all levels and player interactions.

### 5.2 Accessibility
No death mechanic - player respawns at last checkpoint. Colorblind-friendly crystal designs with distinct shapes.

## 6. Technical Requirements

### 6.1 Performance Targets
- Frame Rate: 60 FPS
- Resolution: 1920x1080 (16:9)
- Load Time: < 2 seconds per level

### 6.2 Technical Constraints
Light ray calculations limited to [EXAMPLE: 10] bounces maximum for performance.

### 6.3 External Dependencies
None - using Godot built-in features only.

## 7. Content Scope Summary

| Category | Count | Details |
|----------|-------|---------|
| Levels/Stages | 5 zones, 20 rooms | Tutorial through Ascent |
| Characters/Entities | 1 | Player explorer (no enemies) |
| Items/Collectibles | [EXAMPLE: 20] | Memory Shards (optional lore) |

## 8. Notes

- Values marked with [EXAMPLE: X] are subject to change during playtesting
- This document provides an overview; see detail files in `game_design/` for specifics
- See ImplementationPlanOverview.md for HOW to build it
```

---

## Guidelines

### Keep It High-Level
GameDesignOverview.md answers "What is this game at a high level?" - avoid detailed mechanics descriptions, which belong in detail files.

### File Manifest Is Mandatory
The manifest table must list ALL detail design files. This is the authoritative index for the modular structure.

### Mark Variable Values
Any numeric value that might change during playtesting:
```markdown
- Jump height: [EXAMPLE: 3 tiles]
- Enemy health: [EXAMPLE: 100 HP]
```

### Avoid Duplication
Do not include:
- Detailed mechanics (belongs in detail files under `game_design/`)
- Folder structures (belongs in ImplementationPlanOverview.md)
- Class definitions (belongs in implementation detail files)

### Target Length
Aim for 300-500 words. The overview is an entry point, not a comprehensive document.
