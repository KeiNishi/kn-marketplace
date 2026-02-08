---
name: additional-items-workflow
description: This skill should be used when the user wants to add new features, implementation items, additional specs, change scope, expand the game, add unplanned tasks, or modify the existing game plan during implementation. Triggers on phrases like "add new feature", "new implementation item", "additional spec", "change scope", "add to plan", "new requirement", "scope change", "expand the game", "new task", "unplanned feature". Requires existing docs_for_ai/ folder with GameDesign.md and ImplementationPlan.md already created. Also triggers on "/kn-gamedev-workflow:additional-items-workflow" command.
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Additional Items Workflow

Workflow for handling new implementation items, features, or specs that were not part of the original game design plan. This workflow is used during the implementation phase when the user brings up unplanned additions.

## Prerequisite

Before starting this workflow, verify:
1. `docs_for_ai/` folder exists at the project root
2. `docs_for_ai/GameDesign.md` exists (created by design-workflow)
3. `docs_for_ai/ImplementationPlan.md` exists (created by design-workflow)

If these do not exist, direct the user to run the design-workflow first.

## Workflow Steps

### Step 1: Identify Scope of Change

Read the existing documents to understand current state:

1. Read `docs_for_ai/GameDesign.md` - current game design
2. Read `docs_for_ai/ImplementationPlan.md` - current implementation plan and phases
3. Read `docs_for_ai/TaskProgress.md` (if exists) - current implementation progress

Compare the user's request against existing content and classify:

- **New item**: Feature or spec not covered anywhere in existing documents
- **Expansion**: Extension of something already planned (e.g., adding more levels to an existing level system)
- **Conflict**: Contradicts or requires changes to existing design decisions

Present findings to the user:
- What is genuinely new vs. what already exists
- Any overlaps or partial coverage in existing documents
- Any conflicts with current design decisions that need resolution

### Step 2: Clarify New Items

Ask targeted questions about the new items using `AskUserQuestion`. Follow the same style as design-workflow Phase 2 (Clarification).

**Game Design Questions** (for GameDesign.md updates):
- How does this feature interact with existing mechanics?
- What are the player-facing details (controls, feedback, progression impact)?
- Does this change the content scope (new levels, characters, items)?
- Does this affect win/loss conditions or core loop?

**Implementation Questions** (for ImplementationPlan.md updates):
- What is the priority of this feature (Critical/High/Medium/Low)?
- Are there new classes, modules, or systems needed?
- Are there new asset requirements (graphics, audio)?
- Does this require changes to existing architecture?
- Are there new technical constraints or dependencies?

Continue asking until the new feature is fully defined. Omit questions where the answer is obvious from context.

### Step 3: Determine Scheduling

Present current progress context from TaskProgress.md:
- Current phase and task being worked on
- Remaining tasks in the current plan

Ask the user about implementation timing using `AskUserQuestion` with these options:

1. **After current plan** - Add as a new phase at the end of ImplementationPlan.md. All existing tasks complete first.
2. **After current phase** - Insert new phase after the current phase completes. Renumber subsequent phases.
3. **Immediate priority** - Start after the current task completes. Reprioritize remaining work around this addition.

### Step 4: Update Documents

Update documents based on gathered information. Maintain separation of concerns.

#### 4.1 Update GameDesign.md

Add new content to appropriate sections:
- New mechanics → Section 4 (Game Mechanics) or new subsection
- New systems → Section 5 (Game Systems) or new subsection
- New content → Section 7 (Content Scope)
- New technical requirements → Section 6 (Technical Requirements)

**Rules:**
- Mark variable values with `[EXAMPLE: value]` notation
- Do NOT add implementation details (class names, code structure) to GameDesign.md
- Keep additions concise and consistent with existing document style

#### 4.2 Update ImplementationPlan.md

Based on scheduling decision from Step 3:

- **After current plan**: Append a new Phase section at the end, following the existing template pattern (Goal, Tasks with checkboxes, Deliverables, Priority)
- **After current phase**: Insert new Phase at the chosen position. Renumber all subsequent phases.
- **Immediate priority**: Insert or append tasks based on context. Renumber if needed.

Also update if needed:
- Section 3 (Architecture) - new classes/modules with Purpose, Properties, Methods
- Section 4 (Key Constants) - new constants with `[EXAMPLE]` markers
- Section 5 (Asset Requirements) - new asset entries
- Section 6 (Testing Strategy) - new test checkpoints

**Rules:**
- Do NOT add game design content (world lore, narrative) to ImplementationPlan.md
- Keep additions consistent with existing document style and format

#### 4.3 Update TaskProgress.md

If `docs_for_ai/TaskProgress.md` exists, add a scope-change entry at the top of the Log section:

```markdown
### [YYYY-MM-DD] | Scope Update: [Feature Name]
- **Change**: Added [brief description] to GameDesign.md and ImplementationPlan.md
- **Scheduling**: [After current plan / Inserted at Phase N / Immediate priority]
```

Update the Status line if the total phase count changed.

### Step 5: Design Review

Invoke the `design-review` subagent to validate the updated documents:

```
Use the design-review agent to review docs_for_ai/GameDesign.md and docs_for_ai/ImplementationPlan.md
```

This step is **mandatory** and cannot be skipped.

- If **APPROVED**: Workflow complete. Inform the user that documents are updated and reviewed.
- If **NEEDS_REVISION**:
  1. Present the questions/issues to the user using `AskUserQuestion`
  2. Update the documents based on user responses
  3. Re-invoke design-review agent
  4. Repeat until **APPROVED**

## Document Reference

This workflow updates documents that follow the templates defined in the design-workflow skill:
- **GameDesign.md** structure: see `../design-workflow/references/gamedesign-template.md`
- **ImplementationPlan.md** structure: see `../design-workflow/references/implementation-template.md`
- **TaskProgress.md** structure: see `../implementation-workflow/references/taskprogress-template.md`
