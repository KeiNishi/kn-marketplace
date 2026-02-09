# ImplementationPlan.md Template (Legacy Single-File Format)

> **Note**: This is the legacy single-file format. For new projects, prefer the modular format using `implementation-overview-template.md` and `implementation-detail-template.md` instead. The single-file format is retained for very small games (1-2 systems, under 500 words total) and backward compatibility with existing projects.

Use this template structure when creating `docs_for_ai/ImplementationPlan.md`.

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

## 2. Implementation Phases

### Phase 1: [Phase Name] (Priority: Critical)

**Goal**: [What this phase achieves]

**Tasks**:
- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

**Deliverables**:
- [What is playable/testable after this phase]

---

### Phase 2: [Phase Name] (Priority: High)

**Goal**: [What this phase achieves]

**Tasks**:
- [ ] [Task 1]
- [ ] [Task 2]

**Deliverables**:
- [What is playable/testable after this phase]

---

### Phase 3: [Phase Name] (Priority: Medium)
[Continue pattern...]

---

### Phase 4: [Phase Name] (Priority: Low)
[Continue pattern...]

## 3. Architecture

### 3.1 Core Classes/Modules

#### [ClassName]
```
Purpose: [What this class does]

Properties:
- property_name: type - description

Methods:
- method_name(params): return_type - description
```

#### [ClassName]
[Continue pattern...]

### 3.2 State Management

```
[State diagram or description]
State1 → State2 → State3
           ↓
        State4
```

### 3.3 Data Flow
[How data moves between components]

## 4. Key Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| CONST_NAME | type | [EXAMPLE: value] | description |

*Values marked [EXAMPLE] are initial estimates subject to tuning*

## 5. Asset Requirements

### 5.1 Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| asset_name | PNG/SVG | WxH | P1/P2/P3 |

### 5.2 Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| asset_name | SFX/BGM | WAV/MP3 | P1/P2/P3 |

## 6. Testing Strategy

### 6.1 Playtest Checkpoints
- [ ] Phase 1 complete: [Test criteria]
- [ ] Phase 2 complete: [Test criteria]
- [ ] Full game: [Test criteria]

### 6.2 Key Test Cases
- [Test case 1]
- [Test case 2]

## 7. Dependencies

### 7.1 External Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| [name] | [version] | [why needed] |

### 7.2 Development Tools
- [Tool 1]: [Purpose]
- [Tool 2]: [Purpose]

## 8. Notes

- Implementation order may be adjusted based on dependencies discovered during development
- See GameDesign.md for game concept and mechanics details
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
│   │   └── player.tscn
│   ├── objects/
│   │   ├── crystal.tscn
│   │   ├── light_source.tscn
│   │   └── mechanism.tscn
│   ├── levels/
│   │   ├── tutorial_01.tscn
│   │   └── ...
│   └── ui/
│       ├── hud.tscn
│       └── pause_menu.tscn
├── scripts/
│   ├── player/
│   │   └── player_controller.gd
│   ├── objects/
│   │   ├── crystal.gd
│   │   ├── light_beam.gd
│   │   └── mechanism.gd
│   ├── systems/
│   │   ├── game_manager.gd
│   │   └── checkpoint_manager.gd
│   └── autoload/
│       └── globals.gd
├── assets/
│   ├── sprites/
│   ├── audio/
│   └── fonts/
└── docs_for_ai/
    ├── GameDesign.md
    └── ImplementationPlan.md
```

### 1.2 Naming Conventions
- Scenes: snake_case.tscn
- Scripts: snake_case.gd
- Classes: PascalCase
- Variables/functions: snake_case
- Constants: SCREAMING_SNAKE_CASE

## 2. Implementation Phases

### Phase 1: Core Movement (Priority: Critical)

**Goal**: Playable character with basic platforming

**Tasks**:
- [ ] Create player scene with CharacterBody2D
- [ ] Implement horizontal movement
- [ ] Implement jump with coyote time
- [ ] Create test level with platforms
- [ ] Add basic camera follow

**Deliverables**:
- Player can move and jump in test environment

---

### Phase 2: Light System (Priority: Critical)

**Goal**: Functional light beam and crystal interaction

**Tasks**:
- [ ] Create light source that emits beam
- [ ] Implement RayCast2D for beam detection
- [ ] Create crystal with rotation interaction
- [ ] Implement beam reflection logic
- [ ] Add visual beam rendering (Line2D)

**Deliverables**:
- Light beams reflect off rotatable crystals

---

### Phase 3: Mechanisms (Priority: High)

**Goal**: Puzzles that respond to light

**Tasks**:
- [ ] Create mechanism base class
- [ ] Implement color detection for mechanisms
- [ ] Add door/gate that opens when activated
- [ ] Create colored crystal filters
- [ ] Build first complete puzzle room

**Deliverables**:
- Complete puzzle: direct light to mechanism to open door

---

### Phase 4: Level Content (Priority: Medium)

**Tasks**:
- [ ] Design and build Tutorial Cavern (3 rooms)
- [ ] Design and build Crystal Depths (5 rooms)
- [ ] Design and build Prismatic Chamber (5 rooms)
- [ ] Design and build Ancient Core (4 rooms)
- [ ] Design and build Ascent (3 rooms)

**Deliverables**:
- All 20 rooms playable

---

### Phase 5: Polish (Priority: Low)

**Tasks**:
- [ ] Add particle effects for crystals
- [ ] Implement checkpoint system
- [ ] Add pause menu
- [ ] Integrate audio (BGM, SFX)
- [ ] Add Memory Shard collectibles
- [ ] Screen transitions between rooms

**Deliverables**:
- Complete, polished game

## 3. Architecture

### 3.1 Core Classes/Modules

#### PlayerController
```
Purpose: Handle player input and movement

Properties:
- speed: float - horizontal movement speed
- jump_force: float - jump velocity
- coyote_time: float - grace period after leaving platform

Methods:
- _physics_process(delta): void - movement logic
- handle_input(): void - read input state
- apply_gravity(delta): void - apply gravity
```

#### LightBeam
```
Purpose: Represent a light ray segment

Properties:
- origin: Vector2 - start position
- direction: Vector2 - normalized direction
- color: Color - beam color
- max_bounces: int - reflection limit

Methods:
- cast(): Array[RayResult] - trace beam path
- render(): void - draw beam visuals
```

#### Crystal
```
Purpose: Interactive crystal that reflects light

Properties:
- rotation_angle: float - current rotation (0-360)
- crystal_type: Enum - REFLECT, REFRACT, FILTER

Methods:
- rotate(degrees): void - rotate crystal
- get_reflection_direction(incoming): Vector2 - calculate outgoing beam
```

#### Mechanism
```
Purpose: Base class for light-activated objects

Properties:
- required_color: Color - activation color
- is_activated: bool - current state

Methods:
- receive_light(color): void - check activation
- on_activate(): void - virtual, override in subclasses
- on_deactivate(): void - virtual, override in subclasses
```

### 3.2 State Management

```
GameState:
  PLAYING → PAUSED → PLAYING
      ↓
  TRANSITIONING (room change)
      ↓
  PLAYING
```

### 3.3 Data Flow
1. Player rotates crystal
2. LightBeam recalculates path via RayCast2D
3. Beam hits Mechanism
4. Mechanism checks color match
5. If match: trigger activation (open door, etc.)

## 4. Key Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| PLAYER_SPEED | float | [EXAMPLE: 200.0] | Horizontal speed pixels/sec |
| JUMP_FORCE | float | [EXAMPLE: -400.0] | Jump velocity |
| GRAVITY | float | [EXAMPLE: 980.0] | Gravity acceleration |
| MAX_BEAM_BOUNCES | int | [EXAMPLE: 10] | Max light reflections |
| COYOTE_TIME | float | [EXAMPLE: 0.1] | Jump grace period seconds |

*Values marked [EXAMPLE] are initial estimates subject to tuning*

## 5. Asset Requirements

### 5.1 Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| player_spritesheet | PNG | 64x64 per frame | P1 |
| crystal_sprites | PNG | 32x32 | P1 |
| tileset_cavern | PNG | 16x16 tiles | P1 |
| light_beam_texture | PNG | 8x8 | P1 |
| ui_elements | PNG | various | P2 |

### 5.2 Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| ambient_cave | BGM | OGG | P2 |
| crystal_rotate | SFX | WAV | P2 |
| mechanism_activate | SFX | WAV | P2 |
| player_footstep | SFX | WAV | P3 |

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

## 7. Dependencies

### 7.1 External Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| Godot Engine | 4.2+ | Game engine |

### 7.2 Development Tools
- Aseprite: Pixel art creation
- Audacity: Sound editing

## 8. Notes

- Implementation order may be adjusted based on dependencies discovered during development
- See GameDesign.md for game concept and mechanics details
- Phase 1-2 must be solid before adding content in Phase 4
```

---

## Guidelines

### Keep It Technical
ImplementationPlan.md answers "How do we build this?" - focus on architecture, structure, and concrete tasks.

### Avoid Duplication
Do not repeat game design content:
- Game mechanics explanation (in GameDesign.md)
- World/story details (in GameDesign.md)
- Art/audio direction (in GameDesign.md)

### Prioritize Clearly
Use consistent priority labels:
- **Critical**: Must have for playable prototype
- **High**: Core gameplay features
- **Medium**: Content and variety
- **Low**: Polish and extras

### Mark Variable Values
```markdown
| PLAYER_SPEED | float | [EXAMPLE: 200.0] | ... |
```

### Target Length
Aim for 800-1500 words. Complex projects may need more, but keep it scannable.
