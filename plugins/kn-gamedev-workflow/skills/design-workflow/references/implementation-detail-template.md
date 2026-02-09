# Implementation Detail File Template

Use this template structure when creating detail implementation files in `docs_for_ai/implementation/`.

**Naming convention**: `NN_SystemName_Implementation.md` (e.g., `01_Player_Implementation.md`, `02_LightSystem_Implementation.md`)

---

## Template

```markdown
> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# [Domain Name] Implementation: [Project Name]

## Architecture

### [ClassName/ModuleName]
```
Purpose: [What this class/module does]

Properties:
- property_name: type - description

Methods:
- method_name(params): return_type - description
```

### [ClassName/ModuleName]
[Continue pattern for additional classes/modules]

## State Management

```
[State diagram or description]
State1 → State2 → State3
```

## Tasks

### Phase [N]: [Phase Name] (Priority: [Critical/High/Medium/Low])

**Goal**: [What this phase achieves for this system]

- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

**Deliverables**:
- [What is playable/testable after these tasks]

### Phase [M]: [Phase Name] (Priority: [Level])
[Additional phases that involve this system]

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| CONST_NAME | type | [EXAMPLE: value] | description |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| asset_name | PNG/SVG | WxH | P1/P2/P3 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| asset_name | SFX/BGM | WAV/MP3 | P1/P2/P3 |

## Dependencies
- **Design**: [NN_SystemName_Design.md](../game_design/NN_SystemName_Design.md) - Game design for this system
- **Related Implementation**: [NN_OtherSystem_Implementation.md](./NN_OtherSystem_Implementation.md) - [How they interact]
```

---

## Example: Player Implementation

```markdown
> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Player Implementation: Crystal Caverns

## Architecture

### PlayerController
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

## State Management

```
PlayerState:
  IDLE → MOVING → IDLE
    ↓       ↓
  JUMPING → FALLING → IDLE
    ↓
  INTERACTING → IDLE
```

## Tasks

### Phase 1: Core Movement (Priority: Critical)

**Goal**: Playable character with basic platforming

- [ ] Create player scene with CharacterBody2D
- [ ] Implement horizontal movement
- [ ] Implement jump with coyote time
- [ ] Create test level with platforms
- [ ] Add basic camera follow

**Deliverables**:
- Player can move and jump in test environment

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| PLAYER_SPEED | float | [EXAMPLE: 200.0] | Horizontal speed pixels/sec |
| JUMP_FORCE | float | [EXAMPLE: -400.0] | Jump velocity |
| COYOTE_TIME | float | [EXAMPLE: 0.1] | Jump grace period seconds |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| player_spritesheet | PNG | 64x64 per frame | P1 |

## Dependencies
- **Design**: [01_Player_Design.md](../game_design/01_Player_Design.md) - Player mechanics and controls
- **Related Implementation**: [02_LightSystem_Implementation.md](./02_LightSystem_Implementation.md) - Player interacts with crystals
```

---

## Example: Light System Implementation

```markdown
> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# Light System Implementation: Crystal Caverns

## Architecture

### LightBeam
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

### Crystal
```
Purpose: Interactive crystal that reflects light

Properties:
- rotation_angle: float - current rotation (0-360)
- crystal_type: Enum - REFLECT, REFRACT, FILTER

Methods:
- rotate(degrees): void - rotate crystal
- get_reflection_direction(incoming): Vector2 - calculate outgoing beam
```

### Mechanism
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

## Data Flow

1. Player rotates crystal
2. LightBeam recalculates path via RayCast2D
3. Beam hits Mechanism
4. Mechanism checks color match
5. If match: trigger activation (open door, etc.)

## Tasks

### Phase 2: Light System (Priority: Critical)

**Goal**: Functional light beam and crystal interaction

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

- [ ] Create mechanism base class
- [ ] Implement color detection for mechanisms
- [ ] Add door/gate that opens when activated
- [ ] Create colored crystal filters
- [ ] Build first complete puzzle room

**Deliverables**:
- Complete puzzle: direct light to mechanism to open door

## System-Specific Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| MAX_BEAM_BOUNCES | int | [EXAMPLE: 10] | Max light reflections |
| CRYSTAL_ROTATE_STEP | float | [EXAMPLE: 15.0] | Degrees per rotation input |

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| crystal_sprites | PNG | 32x32 | P1 |
| light_beam_texture | PNG | 8x8 | P1 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| crystal_rotate | SFX | WAV | P2 |
| mechanism_activate | SFX | WAV | P2 |

## Dependencies
- **Design**: [02_LightSystem_Design.md](../game_design/02_LightSystem_Design.md) - Light system game design
- **Related Implementation**: [01_Player_Implementation.md](./01_Player_Implementation.md) - Player interaction with crystals
- **Related Implementation**: [03_LevelContent_Implementation.md](./03_LevelContent_Implementation.md) - Puzzle placement in levels
```

---

## Guidelines

### Back-Link Is Required
Every detail file MUST start with:
```markdown
> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)
```

### Dependencies Are Required
Every detail file MUST end with a Dependencies section listing:
- Corresponding design file
- Related implementation files it interacts with

### One Domain Per File
Each file covers the architecture and tasks for ONE system/domain. Reference other files for cross-system interactions.

### Tasks Grouped by Phase
If a system spans multiple phases, include all relevant phase sections with their tasks. Use the same phase numbering as ImplementationPlanOverview.md.

### Section Flexibility
Not all sections are required for every detail file:
- A polish file may skip State Management
- A content file may have custom sections (Level Layout, Room Transitions)
- Asset Requirements can be omitted if the system has no assets

### Mark Variable Values
```markdown
| PLAYER_SPEED | float | [EXAMPLE: 200.0] | ... |
```

### Target Length
Aim for 200-500 words per detail file. If exceeding 500 words, consider splitting into sub-domains.

### Maximum Files
Soft cap of 20 implementation detail files per project. If approaching this limit, consider consolidating related systems.
