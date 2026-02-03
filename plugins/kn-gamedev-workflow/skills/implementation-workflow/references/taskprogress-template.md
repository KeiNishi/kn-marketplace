# TaskProgress.md Template

Use this template structure when creating or updating `docs_for_ai/TaskProgress.md`.

---

## Template

```markdown
# Task Progress

**Status**: Phase [N]/[Total] - [Phase Name] | Next: [Next Task] | Updated: [YYYY-MM-DD]

---

## Log

### [YYYY-MM-DD] | [Task Name] [Phase N, Task M]
- **Files**: `path/to/file1`, `path/to/file2`
- **Done**: [1-2 sentences describing what was accomplished]
- **Decision**: [Optional - only if significant technical decision was made]
- **Issue**: [Optional - only if problem occurred, include solution]

### [Earlier Date] | [Task Name] [Phase N, Task M]
- **Files**: `path/to/file`
- **Done**: [Brief summary]
```

---

## Example: Crystal Caverns Implementation

```markdown
# Task Progress

**Status**: Phase 2/5 - Light System | Next: Implement crystal rotation | Updated: 2026-02-03

---

## Log

### 2026-02-03 | Implement light beam emission [Phase 2, Task 1]
- **Files**: `scripts/objects/light_beam.gd`, `scenes/objects/light_source.tscn`
- **Done**: Created LightBeam class with RayCast2D for beam detection. Beam renders via Line2D with gradient.
- **Decision**: Used Line2D over custom shader for simplicity and debuggability.

### 2026-02-02 | Add camera follow [Phase 1, Task 5]
- **Files**: `scripts/player/camera_controller.gd`
- **Done**: Implemented smooth camera follow with movement direction look-ahead.

### 2026-02-02 | Implement jump with coyote time [Phase 1, Task 3]
- **Files**: `scripts/player/player_controller.gd`
- **Done**: Added coyote_time buffer for forgiving jump input. Jump feels responsive.
- **Issue**: Initial 0.05s felt unforgiving -> increased to 0.1s after testing.

### 2026-02-01 | Create player movement [Phase 1, Task 1]
- **Files**: `scripts/player/player_controller.gd`, `scenes/player/player.tscn`
- **Done**: Basic horizontal movement with acceleration/deceleration. CharacterBody2D setup complete.

### 2026-02-01 | Set up project structure [Phase 1, Task 0]
- **Files**: `project.godot`, folder structure
- **Done**: Initialized Godot project with folder structure per ImplementationPlan.md.
```

---

## Guidelines

### Keep It Compact
- Each task entry: 3-5 lines maximum
- **Files**: List changed files on one line, comma-separated
- **Done**: 1-2 sentences only
- **Decision/Issue**: Include only when significant

### Reverse Chronological Order
- Latest entry at top
- Older entries naturally scroll out of immediate view
- Keeps current context prominent

### Optional Fields
Only include when relevant:
- **Decision**: Significant architectural or technical choices
- **Issue**: Problems encountered and their solutions

### Status Line Format
```
Phase [current]/[total] - [Phase Name] | Next: [Next Task Name] | Updated: [Date]
```
This single line enables quick status comprehension.

### Cross-Reference
- Task names should match ImplementationPlan.md tasks
- Phase numbers should align with ImplementationPlan.md phases
- Use `[Phase N, Task M]` notation for traceability

### Token Efficiency Target
- ~30-50 words per task entry
- Full log with 10 tasks: ~400-500 words
- Combined with GameDesign.md + ImplementationPlan.md: <2500 words total
