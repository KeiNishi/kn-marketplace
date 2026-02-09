# ImplementationPlanOverview.md Template

Use this template structure when creating `docs_for_ai/ImplementationPlanOverview.md`.

---

## Template

```markdown
# Implementation Plan: [Project Name]

## 1. Project Structure

### 1.1 Folder Layout

```
ProjectName/
├── [platform-specific structure]
```

### 1.2 Naming Conventions
[File and folder naming rules for the target platform]

## 2. Phase Summary

| Phase | Name | Priority | Detail Files | Status |
|-------|------|----------|-------------|--------|
| 1 | [Phase Name] | Critical | [NN_System_Implementation.md] | Not Started |
| 2 | [Phase Name] | High | [NN_System_Implementation.md] | Not Started |
| 3 | [Phase Name] | Medium | [NN_System_Implementation.md] | Not Started |
| 4 | [Phase Name] | Low | [NN_System_Implementation.md] | Not Started |

## 3. Implementation File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_System_Implementation.md](./implementation/01_System_Implementation.md) | [Domain] | [Brief description] |
| 02 | [02_System_Implementation.md](./implementation/02_System_Implementation.md) | [Domain] | [Brief description] |

## 4. Key Constants (Shared/Global)

| Name | Type | Value | Description |
|------|------|-------|-------------|
| CONST_NAME | type | [EXAMPLE: value] | description |

*Values marked [EXAMPLE] are initial estimates subject to tuning*

## 5. Dependencies

### 5.1 External Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| [name] | [version] | [why needed] |

### 5.2 Development Tools
- [Tool 1]: [Purpose]
- [Tool 2]: [Purpose]

## 6. Testing Strategy

### 6.1 Playtest Checkpoints
- [ ] Phase 1 complete: [Test criteria]
- [ ] Phase 2 complete: [Test criteria]
- [ ] Full game: [Test criteria]

### 6.2 Key Test Cases
- [Test case 1]
- [Test case 2]

## 7. Notes

- Implementation order may be adjusted based on dependencies discovered during development
- See GameDesignOverview.md for game concept and mechanics details
- See detail files in `implementation/` for architecture and task breakdowns
```

---

## Example: Puzzle Platformer (Godot)

```markdown
# Implementation Plan: Crystal Caverns

## 1. Project Structure

### 1.1 Folder Layout

```
CrystalCaverns/
├── project.godot
├── scenes/
│   ├── main.tscn
│   ├── player/
│   ├── objects/
│   ├── levels/
│   └── ui/
├── scripts/
│   ├── player/
│   ├── objects/
│   ├── systems/
│   └── autoload/
├── assets/
│   ├── sprites/
│   ├── audio/
│   └── fonts/
└── docs_for_ai/
    ├── GameDesignOverview.md
    ├── ImplementationPlanOverview.md
    ├── TaskProgress.md
    ├── game_design/
    │   ├── 01_Player_Design.md
    │   ├── 02_LightSystem_Design.md
    │   └── 03_LevelContent_Design.md
    └── implementation/
        ├── 01_Player_Implementation.md
        ├── 02_LightSystem_Implementation.md
        ├── 03_LevelContent_Implementation.md
        └── 04_Polish_Implementation.md
```

### 1.2 Naming Conventions
- Scenes: snake_case.tscn
- Scripts: snake_case.gd
- Classes: PascalCase
- Variables/functions: snake_case
- Constants: SCREAMING_SNAKE_CASE

## 2. Phase Summary

| Phase | Name | Priority | Detail Files | Status |
|-------|------|----------|-------------|--------|
| 1 | Core Movement | Critical | 01_Player_Implementation.md | Not Started |
| 2 | Light System | Critical | 02_LightSystem_Implementation.md | Not Started |
| 3 | Mechanisms | High | 02_LightSystem_Implementation.md | Not Started |
| 4 | Level Content | Medium | 03_LevelContent_Implementation.md | Not Started |
| 5 | Polish | Low | 04_Polish_Implementation.md | Not Started |

## 3. Implementation File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_Player_Implementation.md](./implementation/01_Player_Implementation.md) | Player | Player controller, movement, interaction |
| 02 | [02_LightSystem_Implementation.md](./implementation/02_LightSystem_Implementation.md) | Light/Puzzles | Beams, crystals, mechanisms, color logic |
| 03 | [03_LevelContent_Implementation.md](./implementation/03_LevelContent_Implementation.md) | Content | Level building, room transitions |
| 04 | [04_Polish_Implementation.md](./implementation/04_Polish_Implementation.md) | Polish | UI, audio, particles, checkpoints |

## 4. Key Constants (Shared/Global)

| Name | Type | Value | Description |
|------|------|-------|-------------|
| PLAYER_SPEED | float | [EXAMPLE: 200.0] | Horizontal speed pixels/sec |
| GRAVITY | float | [EXAMPLE: 980.0] | Gravity acceleration |

*Values marked [EXAMPLE] are initial estimates subject to tuning*

## 5. Dependencies

### 5.1 External Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| Godot Engine | 4.2+ | Game engine |

### 5.2 Development Tools
- Aseprite: Pixel art creation
- Audacity: Sound editing

## 6. Testing Strategy

### 6.1 Playtest Checkpoints
- [ ] Phase 1: Movement feels responsive and precise
- [ ] Phase 2: Light beams reflect correctly at all angles
- [ ] Phase 3: Puzzles are solvable and satisfying
- [ ] Phase 4: Level difficulty curve is appropriate
- [ ] Full game: 3-5 hour playtime, no soft-locks

### 6.2 Key Test Cases
- Crystal rotation updates beam path immediately
- Beam color mixing works correctly
- Player cannot get stuck in geometry
- Checkpoints save and restore correctly

## 7. Notes

- Implementation order may be adjusted based on dependencies discovered during development
- See GameDesignOverview.md for game concept and mechanics details
- See detail files in `implementation/` for architecture and task breakdowns
- Phase 1-2 must be solid before adding content in Phase 4
```

---

## Guidelines

### Keep It Strategic
ImplementationPlanOverview.md answers "What is the overall build plan?" - detailed architecture and tasks belong in detail files.

### File Manifest Is Mandatory
The manifest table must list ALL implementation detail files. This is the authoritative index.

### Phase Summary References Detail Files
Each phase row must reference which detail file(s) contain its tasks and architecture. One phase may span multiple detail files, and one detail file may serve multiple phases.

### Shared Constants Only
Only include constants that are shared across multiple systems. System-specific constants belong in detail files.

### Avoid Duplication
Do not include:
- Detailed class/module definitions (belongs in implementation detail files)
- Game mechanics explanations (belongs in GameDesignOverview.md or design detail files)
- Per-system asset lists (belongs in implementation detail files)

### Priority Labels
Use consistent priority labels:
- **Critical**: Must have for playable prototype
- **High**: Core gameplay features
- **Medium**: Content and variety
- **Low**: Polish and extras

### Target Length
Aim for 300-500 words. The overview is an entry point, not a comprehensive document.
