---
name: design
description: Start the game development design workflow. Creates modular design documentation (GameDesignOverview.md, ImplementationPlanOverview.md, and detail files) in docs_for_ai/ folder with iterative review process.
argument-hint: "[game-concept-description]"
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Game Design Workflow Command

Start the game development design workflow to create comprehensive modular design documentation for a new game project.

## Usage

```
/kn-gamedev-workflow:design [optional: initial game concept]
```

## Arguments

- `$ARGUMENTS` - Optional initial game concept description. If provided, skip directly to clarification questions. If empty, prompt user for game concept first.

## Workflow

### Step 1: Check Existing Documentation

First, check if `docs_for_ai/` folder already exists:

```
Look for docs_for_ai/GameDesignOverview.md and docs_for_ai/ImplementationPlanOverview.md
```

If modular documents exist, ask user:
- Continue editing existing documents?
- Start fresh (overwrite)?
- Cancel?

If legacy format exists (`GameDesign.md` / `ImplementationPlan.md` without overview files), ask user:
- Migrate to modular format?
- Continue with legacy format?
- Start fresh (overwrite)?
- Cancel?

### Step 2: Invoke Design Workflow Skill

The design-workflow skill handles the complete workflow:

1. **Gather Requirements**
   - If `$ARGUMENTS` provided: use as initial concept
   - If empty: ask user for game concept, genre, platform preferences

2. **Clarification Phase**
   - Ask targeted questions about game design
   - Ask about implementation priorities
   - Ask about system decomposition (major systems/domains)
   - Continue until design is clear

3. **Document Creation**
   - Create `docs_for_ai/` folder with `game_design/` and `implementation/` subdirectories
   - Generate `GameDesignOverview.md` with file manifest
   - Generate detail design files in `game_design/` (e.g., `01_Player_Design.md`)
   - Generate `ImplementationPlanOverview.md` with phase summary and file manifest
   - Generate detail implementation files in `implementation/` (e.g., `01_Player_Implementation.md`)

4. **Review Cycle**
   - Invoke design-review agent to review all documents
   - If NEEDS_REVISION: present questions to user, update docs, re-review
   - Repeat until APPROVED

5. **Completion**
   - Confirm documents are ready
   - Suggest next steps (implementation with platform-specific plugins)

## Output

Documents created in project root:

```
docs_for_ai/
├── GameDesignOverview.md              # High-level game concept, world, scope
├── ImplementationPlanOverview.md      # Phases, project structure, dependencies
├── game_design/
│   ├── 01_Player_Design.md            # Player mechanics detail
│   ├── 02_SystemName_Design.md        # System-specific design detail
│   └── ...
└── implementation/
    ├── 01_Player_Implementation.md    # Player architecture and tasks
    ├── 02_SystemName_Implementation.md # System-specific architecture and tasks
    └── ...
```

## Examples

### With Initial Concept

```
/kn-gamedev-workflow:design A roguelike dungeon crawler with deck-building mechanics
```

The workflow will use this concept as a starting point and ask clarifying questions.

### Without Arguments

```
/kn-gamedev-workflow:design
```

The workflow will first ask the user to describe their game concept before proceeding.

## Notes

- Documents are written in English for optimal AI processing
- Variable values are marked with [EXAMPLE: value] notation
- The design-review agent validates all documents before completion
- This workflow focuses on the design phase only; use platform-specific plugins for implementation
- Detail files use numbered prefixes (01_, 02_, etc.) for ordering
- For very small games (1-2 systems), the workflow may use legacy single-file format instead
