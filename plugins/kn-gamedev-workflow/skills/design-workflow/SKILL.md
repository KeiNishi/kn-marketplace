---
name: design-workflow
description: This skill should be used when the user asks to "create a game", "design a game", "start a new game project", "plan a game", "create a GDD", "write game design document", "create implementation plan", "plan game development", mentions "game design document", "game planning", "docs_for_ai", or wants to plan the design phase of game development. Also triggers on "/kn-gamedev-workflow:design" command.
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Game Development Design Workflow

Universal game development design workflow for creating AI-friendly documentation. Platform and engine agnostic - works with Unity, Godot, Playdate, or any other game development environment.

## Purpose

Guide the design phase of game development by creating structured documentation in `docs_for_ai/` folder:
- **GameDesign.md** - Game concept, mechanics, world, and technical requirements
- **ImplementationPlan.md** - Prioritized tasks, architecture, and implementation details

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

Use `AskUserQuestion` tool to present questions clearly. Continue until both game design and implementation priorities are fully defined.

### Phase 3: Create Documentation

Create the `docs_for_ai/` folder at the project root and generate two documents.

#### 3.1 Create GameDesign.md

Follow the template structure in `references/gamedesign-template.md`.

**Key principles:**
- Write in English for AI readability
- Keep descriptions clear and concise
- Mark variable values as `[EXAMPLE: value]` when subject to playtesting changes
- Focus on "what" the game is, not "how" to build it

#### 3.2 Create ImplementationPlan.md

Follow the template structure in `references/implementation-template.md`.

**Key principles:**
- Write in English for AI readability
- Define concrete class/module structures
- Specify folder layout for the target platform
- Prioritize implementation phases clearly
- Focus on "how" to build, not "what" to build
- No duplication with GameDesign.md content

### Phase 4: Design Review

Invoke the `design-review` subagent to review the created documents:

```
Use the design-review agent to review docs_for_ai/GameDesign.md and docs_for_ai/ImplementationPlan.md
```

The design-review agent will return one of:
- **APPROVED** - Documents are complete and ready
- **NEEDS_REVISION** - Questions or issues that need user clarification

### Phase 5: Iteration

If design-review returns NEEDS_REVISION:

1. Present the questions/issues to the user using `AskUserQuestion`
2. Update the documents based on user responses
3. Re-invoke design-review agent
4. Repeat until APPROVED (maximum 3 iterations)

If maximum iterations reached, notify the user and proceed with current documents.

## Document Guidelines

### Language
All documents must be written in English for optimal AI processing.

### Separation of Concerns
- **GameDesign.md** - Describes WHAT the game is (concept, mechanics, world)
- **ImplementationPlan.md** - Describes HOW to build it (architecture, tasks, structure)

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
- Target: GameDesign.md ~500-1000 words, ImplementationPlan.md ~800-1500 words

## Output Structure

```
project-root/
└── docs_for_ai/
    ├── GameDesign.md
    └── ImplementationPlan.md
```

## Reference Templates

Consult these templates for document structure:
- **`references/gamedesign-template.md`** - GameDesign.md structure and examples
- **`references/implementation-template.md`** - ImplementationPlan.md structure and examples

## Integration with Other Plugins

This workflow is designed to work alongside platform-specific plugins:
- After design phase, use platform plugins (playdate-gamedev, unity-gamedev-standards, etc.) for implementation
- The `docs_for_ai/` folder serves as the single source of truth for AI agents
- Update documents when significant design changes occur during implementation
