---
name: design
description: Start the game development design workflow. Creates GameDesign.md and ImplementationPlan.md in docs_for_ai/ folder with iterative review process.
argument-hint: "[game-concept-description]"
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Game Design Workflow Command

Start the game development design workflow to create comprehensive design documentation for a new game project.

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
Look for docs_for_ai/GameDesign.md and docs_for_ai/ImplementationPlan.md
```

If documents exist, ask user:
- Continue editing existing documents?
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
   - Continue until design is clear

3. **Document Creation**
   - Create `docs_for_ai/` folder
   - Generate `GameDesign.md` from template
   - Generate `ImplementationPlan.md` from template

4. **Review Cycle**
   - Invoke design-review agent
   - If NEEDS_REVISION: present questions to user, update docs, re-review
   - Repeat until APPROVED (max 3 iterations)

5. **Completion**
   - Confirm documents are ready
   - Suggest next steps (implementation with platform-specific plugins)

## Output

Documents created in project root:

```
docs_for_ai/
├── GameDesign.md          # Game concept, mechanics, world
└── ImplementationPlan.md  # Architecture, tasks, structure
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
- The design-review agent validates documents before completion
- This workflow focuses on the design phase only; use platform-specific plugins for implementation
