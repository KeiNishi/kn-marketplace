---
name: additional-items-workflow
description: This skill should be used when the user wants to add new features, implementation items, additional specs, change scope, expand the game, add unplanned tasks, or modify the existing game plan during implementation. Triggers on phrases like "add new feature", "new implementation item", "additional spec", "change scope", "add to plan", "new requirement", "scope change", "expand the game", "new task", "unplanned feature". Requires existing docs_for_ai/ folder with GameDesignOverview.md and ImplementationPlanOverview.md (or legacy GameDesign.md and ImplementationPlan.md). Also triggers on "/kn-gamedev-workflow:additional-items-workflow" command.
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Additional Items Workflow

Workflow for handling new implementation items, features, or specs that were not part of the original game design plan. This workflow is used during the implementation phase when the user brings up unplanned additions.

## Prerequisite

Before starting this workflow, verify:
1. `docs_for_ai/` folder exists at the project root
2. Design documents exist (either modular or legacy format)

**Modular format detection:**
- `docs_for_ai/GameDesignOverview.md` exists → modular format
- `docs_for_ai/GameDesign.md` exists (without GameDesignOverview.md) → legacy format

If no design documents exist, direct the user to run the design-workflow first.

## Workflow Steps (Modular Format)

### Step 1: Identify Scope of Change

Read the existing documents to understand current state:

1. Read `docs_for_ai/GameDesignOverview.md` - get the File Manifest and high-level design
2. Read `docs_for_ai/ImplementationPlanOverview.md` - get Phase Summary and Implementation File Manifest
3. Read `docs_for_ai/TaskProgress.md` (if exists) - current implementation progress
4. Based on the user's request, identify which detail files are relevant and read them:
   - Read the specific `game_design/NN_*_Design.md` files related to the new feature
   - Read the specific `implementation/NN_*_Implementation.md` files related to the new feature
   - Do NOT read all detail files - only the relevant ones based on the manifests

Compare the user's request against existing content and classify:

- **New item**: Feature or spec not covered anywhere in existing documents
- **Expansion**: Extension of something already planned (e.g., adding more levels to an existing level system)
- **Conflict**: Contradicts or requires changes to existing design decisions

Present findings to the user:
- What is genuinely new vs. what already exists
- Any overlaps or partial coverage in existing documents
- Any conflicts with current design decisions that need resolution
- Which existing detail files are affected

### Step 2: Clarify New Items

Ask targeted questions about the new items using `AskUserQuestion`. Follow the same style as design-workflow Phase 2 (Clarification).

**Game Design Questions** (for design document updates):
- How does this feature interact with existing mechanics?
- What are the player-facing details (controls, feedback, progression impact)?
- Does this change the content scope (new levels, characters, items)?
- Does this affect win/loss conditions or core loop?
- Which system/domain does this feature belong to? (if not obvious)

**Implementation Questions** (for implementation document updates):
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

1. **After current plan** - Add as a new phase at the end of the Phase Summary. All existing tasks complete first.
2. **After current phase** - Insert new phase after the current phase completes. Update Phase Summary.
3. **Immediate priority** - Start after the current task completes. Reprioritize remaining work around this addition.

### Step 4: Update Documents

Update documents based on gathered information. Maintain separation of concerns.

#### 4.1 Update Game Design Documents

Determine if the feature fits into an existing detail file or requires a new one:

**Fits existing file:**
- Update the appropriate `game_design/NN_*_Design.md` with new mechanics, entities, progression
- Update `GameDesignOverview.md` if Content Scope Summary or Cross-Cutting Concerns change

**Requires new detail file:**
- Create a new `game_design/NN_SystemName_Design.md` using the next available number prefix
- Follow the template in `../design-workflow/references/gamedesign-detail-template.md`
- Add the new file to `GameDesignOverview.md`'s File Manifest
- Update Content Scope Summary if applicable

**Rules:**
- Mark variable values with `[EXAMPLE: value]` notation
- Do NOT add implementation details (class names, code structure) to design files
- Keep additions concise and consistent with existing document style
- Maintain Dependencies sections in affected detail files

#### 4.2 Update Implementation Documents

Based on scheduling decision from Step 3:

**Fits existing implementation file:**
- Update the appropriate `implementation/NN_*_Implementation.md` with new tasks, architecture
- Update `ImplementationPlanOverview.md` Phase Summary if new phases are added

**Requires new implementation file:**
- Create a new `implementation/NN_SystemName_Implementation.md` using the next available number prefix
- Follow the template in `../design-workflow/references/implementation-detail-template.md`
- Add the new file to `ImplementationPlanOverview.md`'s Implementation File Manifest
- Add new phase entries to the Phase Summary table

Also update if needed:
- `ImplementationPlanOverview.md` Section 4 (Key Constants) - new shared constants
- `ImplementationPlanOverview.md` Section 5 (Dependencies) - new external libraries
- `ImplementationPlanOverview.md` Section 6 (Testing Strategy) - new test checkpoints
- System-specific constants in the relevant detail file

**Rules:**
- Do NOT add game design content (world lore, narrative) to implementation files
- Keep additions consistent with existing document style and format
- Maintain Dependencies sections in affected detail files
- Use consistent phase numbering with ImplementationPlanOverview.md

#### 4.3 Update TaskProgress.md

If `docs_for_ai/TaskProgress.md` exists, add a scope-change entry at the top of the Log section:

```markdown
### [YYYY-MM-DD] | Scope Update: [Feature Name]
- **Change**: Added [brief description] to [list of files updated/created]
- **Scheduling**: [After current plan / Inserted at Phase N / Immediate priority]
```

Update the Status line if the total phase count changed.

### Step 5: Design Review

Invoke the `design-review` subagent to validate the updated documents:

```
Use the design-review agent to review all documents in docs_for_ai/. Start with GameDesignOverview.md and ImplementationPlanOverview.md to discover file manifests, then review all detail files listed in the manifests.
```

This step is **mandatory** and cannot be skipped.

- If **APPROVED**: Workflow complete. Inform the user that documents are updated and reviewed.
- If **NEEDS_REVISION**:
  1. Present the questions/issues to the user using `AskUserQuestion`
  2. Update the documents based on user responses
  3. Re-invoke design-review agent
  4. Repeat until **APPROVED**

## Workflow Steps (Legacy Format)

If legacy format is detected (`GameDesign.md` / `ImplementationPlan.md`):

1. Follow the same 5-step workflow, but operate on the two monolithic files instead
2. Read `docs_for_ai/GameDesign.md`, `docs_for_ai/ImplementationPlan.md`, and `docs_for_ai/TaskProgress.md` (if exists)
3. Update the appropriate sections within the single files
4. For design review, invoke the agent which will auto-detect the legacy format

## Technology Stack Skills Integration

When updating implementation documents, you **MUST** use the appropriate technology stack skill to ensure platform-specific best practices are maintained. Check the existing documents to identify the target platform/engine, then invoke the corresponding skill.

| Platform / Engine | Skill to Use |
|-------------------|-------------|
| Unity | `unity-gamedev-standards:unity-gamedev` |
| Godot (GDScript) | `godot-gdscript-patterns` |
| Playdate (C) | `playdate-gamedev` |

**How to apply:**
1. Identify the target platform/engine from the existing GameDesignOverview.md (or legacy GameDesign.md).
2. Invoke the corresponding skill listed above before updating implementation documents.
3. Ensure new phases, classes, and architecture additions follow the platform-specific patterns and conventions provided by the skill.
4. If no matching skill exists for the chosen platform, proceed without a technology stack skill and follow general best practices.

## Document Reference

This workflow updates documents that follow the templates defined in the design-workflow skill:
- **GameDesignOverview.md** structure: see `../design-workflow/references/gamedesign-overview-template.md`
- **Game Design Detail** structure: see `../design-workflow/references/gamedesign-detail-template.md`
- **ImplementationPlanOverview.md** structure: see `../design-workflow/references/implementation-overview-template.md`
- **Implementation Detail** structure: see `../design-workflow/references/implementation-detail-template.md`
- **TaskProgress.md** structure: see `../implementation-workflow/references/taskprogress-template.md`
