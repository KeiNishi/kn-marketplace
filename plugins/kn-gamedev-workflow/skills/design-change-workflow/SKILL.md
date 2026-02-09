---
name: design-change-workflow
description: This skill should be used when the user wants to modify, add, replace, or remove game design specs or implementation plans during development. Handles adding new features/specs, modifying existing design documents, updating implementation plans, replacing existing features with new ones, removing features, or changing scope. Triggers on phrases like "change design", "modify spec", "update implementation plan", "add new feature", "remove feature", "replace feature", "swap out", "change scope", "revise design", "update docs", "new requirement", "scope change", "expand the game", "new task", "additional spec". Requires existing docs_for_ai/ folder with GameDesignOverview.md and ImplementationPlanOverview.md (or legacy GameDesign.md and ImplementationPlan.md). Also triggers on "/kn-gamedev-workflow:design-change-workflow" command.
allowed-tools: Read, Write, Edit, Glob, Grep, Task
---

# Design Change Workflow

Workflow for handling changes to game design documents and implementation plans during development. This includes adding new features/specs, modifying existing design decisions, replacing existing features with new ones, removing features, updating implementation plans, or restructuring documentation. Use this workflow whenever the user requests changes to existing docs_for_ai/ documentation.

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
   - Read the specific `game_design/NN_*_Design.md` files related to the change
   - Read the specific `implementation/NN_*_Implementation.md` files related to the change
   - Do NOT read all detail files - only the relevant ones based on the manifests

Compare the user's request against existing content and classify the change type:

- **New Addition**: Feature or spec not covered anywhere in existing documents
- **Modification**: Changes to existing design decisions, mechanics, or implementation approach
- **Expansion**: Extension of something already planned (e.g., adding more levels to an existing level system)
- **Removal**: Deleting or deprecating features, specs, or implementation tasks
- **Replacement**: Combination of Removal and New Addition — removing an existing feature and introducing a new one in its place
- **Conflict Resolution**: Resolves contradictions or requires changes to existing design decisions

Present findings to the user:
- What needs to be modified vs. what is new
- Which existing detail files will be affected
- Any overlaps or dependencies with other documented systems
- Impact on already-completed implementation (check TaskProgress.md)
- Any conflicts with current design decisions that need resolution

### Step 2: Clarify Changes

Ask targeted questions about the changes using `AskUserQuestion`. Follow the same style as design-workflow Phase 2 (Clarification).

**For New Additions — Game Design Questions:**
- How does this feature interact with existing mechanics?
- What are the player-facing details (controls, feedback, progression impact)?
- Does this change the content scope (new levels, characters, items)?
- Does this affect win/loss conditions or core loop?
- Which system/domain does this feature belong to? (if not obvious)

**For New Additions — Implementation Questions:**
- What is the priority of this feature (Critical/High/Medium/Low)?
- Are there new classes, modules, or systems needed?
- Are there new asset requirements (graphics, audio)?
- Does this require changes to existing architecture?
- Are there new technical constraints or dependencies?

**For Modifications — Game Design Questions:**
- Which existing design elements need to change?
- How does this modification affect related mechanics/systems?
- Should the old design be replaced entirely or adapted?
- Does this change player-facing behavior or just internal details?
- What dependencies exist with other documented systems?

**For Modifications — Implementation Questions:**
- Which existing classes/modules need to change?
- Should existing tasks be updated or replaced?
- What is the impact on already-completed phases (check TaskProgress.md)?
- Does this change affect testing strategy or dependencies?
- What is the priority of this modification?

**For Removals — Game Design Questions:**
- What is the reason for removing this feature?
- Are there dependencies in other systems that reference this?
- Should anything replace the removed feature?

**For Removals — Implementation Questions:**
- Which phases/tasks should be removed?
- Are there dependencies in other implementation files?
- Should assets or code already created be kept or deleted?

**For Replacements:**
First ask the Removal questions for the feature being replaced, then ask the New Addition questions for the replacement feature. Additionally:
- What aspects of the old feature should the replacement retain (if any)?
- Should the replacement reuse any existing architecture or assets?

Continue asking until the change is fully defined. Omit questions where the answer is obvious from context.

### Step 3: Determine Scheduling

Present current progress context from TaskProgress.md:
- Current phase and task being worked on
- Remaining tasks in the current plan
- Already-completed phases that might be affected

Ask the user about implementation timing using `AskUserQuestion`:

**For New Additions:**
1. **After current plan** - Add as a new phase at the end of the Phase Summary. All existing tasks complete first.
2. **After current phase** - Insert new phase after the current phase completes. Update Phase Summary.
3. **Immediate priority** - Start after the current task completes. Reprioritize remaining work around this addition.

**For Modifications:**
1. **Immediate** - Modify the documents and update affected tasks in current/future phases.
2. **After current phase** - Defer modification until the current phase completes.
3. **Retroactive** - If modification affects already-completed work, ask whether to:
   - Document the change and continue (update design docs, note in TaskProgress.md)
   - Rework completed implementation (update design docs, add rework tasks to current phase)

**For Removals:**
1. **Immediate** - Remove from documents and skip related tasks in current/future phases.
2. **After current phase** - Complete current phase, then remove from remaining phases.
3. **Cleanup required** - If removal affects completed work, ask whether to remove implemented code/assets.

**For Replacements:**
Handle as a combined Removal + New Addition. Present scheduling options for both parts together:
1. **Immediate** - Remove old feature from documents and add replacement in one pass.
2. **After current phase** - Complete current phase, then apply removal and addition.
3. **Phased** - Remove first (with optional cleanup), then add replacement as a separate phase.

### Step 4: Update Documents

Update documents based on gathered information. Maintain separation of concerns.

#### 4.1 Update Game Design Documents

Determine if the change fits into an existing detail file or requires a new one:

**For New Additions — fits existing file:**
- Update the appropriate `game_design/NN_*_Design.md` with new mechanics, entities, progression
- Update `GameDesignOverview.md` if Content Scope Summary or Cross-Cutting Concerns change

**For New Additions — requires new detail file:**
- Create a new `game_design/NN_SystemName_Design.md` using the next available number prefix
- Follow the template in `../design-workflow/references/gamedesign-detail-template.md`
- Add the new file to `GameDesignOverview.md`'s File Manifest
- Update Content Scope Summary if applicable

**For Modifications:**
- Update the appropriate `game_design/NN_*_Design.md` with revised mechanics, entities, or progression
- Update cross-references in Dependencies sections if system relationships change
- Update `GameDesignOverview.md` if Content Scope Summary or Cross-Cutting Concerns change

**For Removals:**
- Remove sections from the appropriate `game_design/NN_*_Design.md`
- Check Dependencies sections in ALL related detail files for references to removed content
- Update or remove cross-references that point to removed content
- Update `GameDesignOverview.md` File Manifest if an entire detail file is removed
- Consider whether the detail file should be deleted entirely or just sections removed

**For Replacements:**
- Apply the Removal steps for the old feature first
- Then apply the New Addition steps for the replacement feature
- Ensure cross-references are updated to point to the new feature instead of the removed one

**Rules:**
- Mark variable values with `[EXAMPLE: value]` notation
- Do NOT add implementation details (class names, code structure) to design files
- Keep changes concise and consistent with existing document style
- Maintain Dependencies sections in affected detail files

#### 4.2 Update Implementation Documents

Based on scheduling decision from Step 3:

**For New Additions — fits existing implementation file:**
- Update the appropriate `implementation/NN_*_Implementation.md` with new tasks, architecture
- Update `ImplementationPlanOverview.md` Phase Summary if new phases are added

**For New Additions — requires new implementation file:**
- Create a new `implementation/NN_SystemName_Implementation.md` using the next available number prefix
- Follow the template in `../design-workflow/references/implementation-detail-template.md`
- Add the new file to `ImplementationPlanOverview.md`'s Implementation File Manifest
- Add new phase entries to the Phase Summary table

**For Modifications:**
- Update the appropriate `implementation/NN_*_Implementation.md` with revised architecture or tasks
- Update `ImplementationPlanOverview.md` Phase Summary if phase descriptions or priorities change
- Check Dependencies sections in ALL implementation detail files for affected references
- If retroactive changes affect completed work, coordinate with TaskProgress.md updates

**For Removals:**
- Remove phases/tasks from the appropriate `implementation/NN_*_Implementation.md`
- Update `ImplementationPlanOverview.md` Phase Summary to reflect removed phases
- Update Implementation File Manifest if an entire detail file is removed
- Check Dependencies sections in ALL detail files for references to removed tasks/modules
- If removal affects completed work, coordinate cleanup tasks with user

**For Replacements:**
- Apply the Removal steps for the old feature's implementation first
- Then apply the New Addition steps for the replacement feature's implementation
- Reuse phase slots from the removed feature where appropriate

Also update if needed:
- `ImplementationPlanOverview.md` Section 4 (Key Constants) - new or changed shared constants
- `ImplementationPlanOverview.md` Section 5 (Dependencies) - new or changed external libraries
- `ImplementationPlanOverview.md` Section 6 (Testing Strategy) - new or changed test checkpoints
- System-specific constants in the relevant detail file

**Rules:**
- Do NOT add game design content (world lore, narrative) to implementation files
- Keep changes consistent with existing document style and format
- Maintain Dependencies sections in affected detail files
- Use consistent phase numbering with ImplementationPlanOverview.md

#### 4.3 Update TaskProgress.md

If `docs_for_ai/TaskProgress.md` exists, add a change entry at the top of the Log section:

**For New Additions:**
```markdown
### [YYYY-MM-DD] | Scope Update: [Feature Name]
- **Change**: Added [brief description] to [list of files updated/created]
- **Scheduling**: [After current plan / Inserted at Phase N / Immediate priority]
```

**For Modifications:**
```markdown
### [YYYY-MM-DD] | Design Modification: [Change Description]
- **Change**: Modified [brief description] in [list of files updated]
- **Impact**: [Which phases/tasks affected, retroactive changes if any]
- **Scheduling**: [Immediate / After Phase N / Retroactive rework]
```

**For Removals:**
```markdown
### [YYYY-MM-DD] | Scope Reduction: [Feature/System Removed]
- **Change**: Removed [brief description] from [list of files updated]
- **Impact**: [Which phases/tasks removed, cleanup required if any]
```

**For Replacements:**
```markdown
### [YYYY-MM-DD] | Feature Replacement: [Old Feature] → [New Feature]
- **Removed**: [brief description of what was removed] from [list of files]
- **Added**: [brief description of what was added] to [list of files]
- **Scheduling**: [Immediate / After Phase N / Phased]
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
