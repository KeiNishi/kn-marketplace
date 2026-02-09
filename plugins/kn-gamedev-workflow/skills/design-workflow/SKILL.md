---
name: design-workflow
description: This skill should be used when the user asks to "create a game", "design a game", "start a new game project", "plan a game", "create a GDD", "write game design document", "create implementation plan", "plan game development", mentions "game design document", "game planning", "docs_for_ai", or wants to plan the design phase of game development. Also triggers on "/kn-gamedev-workflow:design" command.
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Game Development Design Workflow

Universal game development design workflow for creating AI-friendly modular documentation. Platform and engine agnostic - works with Unity, Godot, Playdate, or any other game development environment.

## Purpose

Guide the design phase of game development by creating structured modular documentation in `docs_for_ai/` folder:
- **GameDesignOverview.md** - High-level game concept, world, and technical requirements
- **game_design/NN_System_Design.md** - Detailed design per system/domain
- **ImplementationPlanOverview.md** - Phase summary, project structure, and shared config
- **implementation/NN_System_Implementation.md** - Architecture and tasks per system/domain

## Workflow Phases

### Phase 1: Gather Initial Requirements

Collect information from the user about their game concept:
- Game overview (title, genre, platform, target audience)
- Core concept and unique selling points
- World and setting
- Core mechanics and gameplay loop
- Technical constraints or preferences

If the user provides partial information, proceed to Phase 2 to clarify missing details.

### Phase 2: Clarification

Ask targeted questions to clarify:

**Game Design Questions:**
- Target platform and engine (if not specified)
- Scope and scale (playtime, content amount)
- Art style and visual direction
- Core gameplay loop details
- Win/loss conditions

**Implementation Questions:**
- Priority features vs. nice-to-have
- Technical constraints (performance, memory)
- External dependencies
- Timeline considerations

**System Decomposition Questions:**
- What are the major game systems/domains? (e.g., player, combat, inventory, level design)
- Which systems are independent vs. tightly coupled?
- Are there any cross-cutting concerns? (e.g., save system, audio, UI)

Use `AskUserQuestion` tool to present questions clearly. Continue until both game design and implementation priorities are fully defined.

### Phase 3: Create Documentation

Create the `docs_for_ai/` folder with subdirectories and generate modular documents.

#### 3.1 Determine File Decomposition

Based on Phase 2 answers, determine the detail file split:

1. Identify major systems/domains from the game mechanics and systems discussed
2. Each system with significant complexity (estimated >150 words of design content) gets its own detail file
3. Assign numbered prefixes in order of creation: `01_`, `02_`, `03_`, etc.
4. Simple systems can be combined into a single detail file (e.g., `04_UIAndAudio_Design.md`)

**Soft cap: 20 detail files per document type.** If approaching this limit, consolidate related systems.

**Small game exception:** For very simple games (1-2 systems, estimated total content under 500 words), use the legacy single-file format per `references/gamedesign-template.md` and `references/implementation-template.md` instead of the modular structure.

#### 3.2 Create Directory Structure

```
docs_for_ai/
├── game_design/      # Detail design files
└── implementation/   # Detail implementation files
```

#### 3.3 Create GameDesignOverview.md

Follow the template structure in `references/gamedesign-overview-template.md`.

Place in `docs_for_ai/GameDesignOverview.md`.

**Key principles:**
- Write in English for AI readability
- Include the File Manifest listing all detail design files
- Keep high-level: concept, world, technical requirements, content scope summary
- Mark variable values as `[EXAMPLE: value]`
- Target: ~300-500 words

#### 3.4 Create Game Design Detail Files

Follow the template structure in `references/gamedesign-detail-template.md`.

Place in `docs_for_ai/game_design/NN_SystemName_Design.md`.

**Key principles:**
- Each file covers ONE domain/system
- Start with back-link to GameDesignOverview.md
- End with Dependencies section
- Focus on "what" the game mechanics are
- Target: ~200-500 words per file

#### 3.5 Create ImplementationPlanOverview.md

Follow the template structure in `references/implementation-overview-template.md`.

Place in `docs_for_ai/ImplementationPlanOverview.md`.

**Key principles:**
- Write in English for AI readability
- Include Phase Summary table referencing detail files
- Include Implementation File Manifest
- Shared constants, dependencies, testing strategy
- Target: ~300-500 words

#### 3.6 Create Implementation Detail Files

Follow the template structure in `references/implementation-detail-template.md`.

Place in `docs_for_ai/implementation/NN_SystemName_Implementation.md`.

**Key principles:**
- Each file covers architecture and tasks for ONE system/domain
- Start with back-link to ImplementationPlanOverview.md
- End with Dependencies section
- Define concrete class/module structures
- Group tasks by phase with consistent phase numbering
- Target: ~200-500 words per file

### Phase 4: Design Review

Invoke the `design-review` subagent to review all created documents:

```
Use the design-review agent to review all documents in docs_for_ai/. Start with GameDesignOverview.md and ImplementationPlanOverview.md to discover file manifests, then review all detail files listed in the manifests.
```

The design-review agent will return one of:
- **APPROVED** - Documents are complete and ready
- **NEEDS_REVISION** - Questions or issues that need user clarification

### Phase 5: Iteration

If design-review returns NEEDS_REVISION:

1. Present the questions/issues to the user using `AskUserQuestion`
2. Update the documents based on user responses
3. Re-invoke design-review agent
4. Repeat until APPROVED

## Document Guidelines

### Language
All documents must be written in English for optimal AI processing.

### Separation of Concerns
- **GameDesignOverview.md** - High-level WHAT (concept, world, scope)
- **game_design/*.md** - Detailed WHAT per system (mechanics, entities, progression)
- **ImplementationPlanOverview.md** - High-level HOW (phases, structure, dependencies)
- **implementation/*.md** - Detailed HOW per system (architecture, tasks, assets)

Avoid duplicating information between documents.

### Variable Values
Values that may change during playtesting should be marked:

```markdown
- Player speed: [EXAMPLE: 5.0 units/sec]
- Enemy spawn rate: [EXAMPLE: every 3 seconds]
```

This indicates to future AI agents that these values are initial estimates.

### Conciseness
Keep documents focused and scannable:
- Use bullet points and tables
- Avoid verbose descriptions
- Include only necessary details
- Target: Overview files ~300-500 words, Detail files ~200-500 words each

### Numbered Prefixes
Detail files use numbered prefixes for ordering:
- Format: `NN_SystemName_Design.md` / `NN_SystemName_Implementation.md`
- Assign in creation order: `01_`, `02_`, `03_`, etc.
- When adding new files, use the next available number
- Do NOT renumber existing files when adding or removing

## Output Structure

```
project-root/
└── docs_for_ai/
    ├── GameDesignOverview.md
    ├── ImplementationPlanOverview.md
    ├── game_design/
    │   ├── 01_Player_Design.md
    │   ├── 02_SystemName_Design.md
    │   └── ...
    └── implementation/
        ├── 01_Player_Implementation.md
        ├── 02_SystemName_Implementation.md
        └── ...
```

## Reference Templates

Consult these templates for document structure:
- **`references/gamedesign-overview-template.md`** - GameDesignOverview.md structure and examples
- **`references/gamedesign-detail-template.md`** - Detail design file structure and examples
- **`references/implementation-overview-template.md`** - ImplementationPlanOverview.md structure and examples
- **`references/implementation-detail-template.md`** - Detail implementation file structure and examples

### Legacy Templates (for small games)
- **`references/gamedesign-template.md`** - Single-file GameDesign.md (legacy format)
- **`references/implementation-template.md`** - Single-file ImplementationPlan.md (legacy format)

## Technology Stack Skills Integration

When creating implementation documents, you **MUST** use the appropriate technology stack skill to ensure platform-specific best practices, project structure, and architecture patterns are correctly reflected in the plan.

| Platform / Engine | Skill to Use |
|-------------------|-------------|
| Unity | `unity-gamedev-standards:unity-gamedev` |
| Godot (GDScript) | `godot-gdscript-patterns` |
| Playdate (C) | `playdate-gamedev` |

**How to apply:**
1. Once the target platform/engine is determined (Phase 1 or Phase 2), invoke the corresponding skill listed above.
2. Use the skill's guidance for project structure, naming conventions, architecture patterns, and coding standards when writing implementation documents.
3. If no matching skill exists for the chosen platform, proceed without a technology stack skill and follow general best practices.

## Integration with Other Plugins

This workflow is designed to work alongside platform-specific plugins:
- The technology stack skills above provide platform-specific standards during planning
- The `docs_for_ai/` folder serves as the single source of truth for AI agents
- Update documents when significant design changes occur during implementation

## Backward Compatibility

If the user has an existing project with legacy single-file format (`GameDesign.md` / `ImplementationPlan.md` instead of the modular structure), detect and work with that format. Offer migration to the modular format if the documents are growing large.
