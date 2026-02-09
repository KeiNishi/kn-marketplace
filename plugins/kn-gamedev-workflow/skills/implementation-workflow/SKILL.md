---
name: implementation-workflow
description: This skill activates when implementing tasks from ImplementationPlanOverview.md (or legacy ImplementationPlan.md) in a project with docs_for_ai/ folder. Triggers when completing implementation tasks, finishing a coding task from the plan, or when the user mentions "update progress", "log progress", "record task", "implementation task done", or "mark task complete". Also activates when working on tasks referenced in implementation plan documents.
allowed-tools: Read, Write, Edit, Glob
---

# Implementation Workflow - Progress Tracking

Track implementation progress in `docs_for_ai/TaskProgress.md` for cross-AI context sharing.

## Purpose

Maintain a concise progress log that enables any AI agent (Claude, Codex, Gemini, etc.) to understand:
- Current implementation status
- What has been completed
- What comes next
- Key decisions and issues encountered

## When to Record

Record progress in TaskProgress.md when:
- Completing a task from an implementation detail file
- Finishing a phase milestone
- Making significant technical decisions
- Encountering and resolving issues

## Format Detection

Before recording, determine which document format the project uses:

1. **Modular format**: Check for `docs_for_ai/ImplementationPlanOverview.md`
2. **Legacy format**: Check for `docs_for_ai/ImplementationPlan.md`

## Workflow (Modular Format)

### Step 1: Verify Context

Before recording, confirm:
1. `docs_for_ai/` folder exists
2. `GameDesignOverview.md` and `ImplementationPlanOverview.md` are present
3. Read `ImplementationPlanOverview.md` to identify the Phase Summary and which detail file contains the completed task
4. Read the relevant `implementation/NN_*_Implementation.md` to confirm the Phase/Task reference

### Step 2: Create or Update TaskProgress.md

If `docs_for_ai/TaskProgress.md` does not exist:
1. Create it following `references/taskprogress-template.md`
2. Initialize Status line with current phase info

If it exists:
1. Read current content
2. Add new entry at top of Log section
3. Update Status line

### Step 3: Write Entry

Follow this format strictly:

```markdown
### [YYYY-MM-DD] | [Task Name] [Phase N, Task M]
- **Files**: `file1`, `file2`
- **Done**: [1-2 sentences]
- **Decision**: [Only if significant]
- **Issue**: [Only if problem occurred]
```

**Rules:**
- Task name must match or reference the task in the relevant implementation detail file
- Files: comma-separated, relative paths
- Done: maximum 2 sentences
- Decision/Issue: omit if not applicable

### Step 4: Update Status Line

```markdown
**Status**: Phase [N]/[Total] - [Phase Name] | Next: [Next Task] | Updated: [YYYY-MM-DD]
```

## Workflow (Legacy Format)

### Step 1: Verify Context

1. `docs_for_ai/` folder exists
2. `GameDesign.md` and `ImplementationPlan.md` are present
3. Identify which Phase/Task from ImplementationPlan.md was completed

### Steps 2-4: Same as modular format

Follow the same recording process. Task names reference ImplementationPlan.md directly.

## Recording Guidelines

### Be Concise
- Each entry: 3-5 lines maximum
- No verbose explanations
- Focus on facts, not process description

### Include Only What Matters
**Always include:**
- Task name with phase reference
- Changed files
- Brief completion summary

**Include only when significant:**
- Technical decisions with reasoning
- Problems and their solutions

### Maintain Traceability
- Use exact task names from implementation detail files (or ImplementationPlan.md for legacy) when possible
- Reference Phase and Task numbers: `[Phase 2, Task 3]`
- Keep Status line synchronized with actual progress

## Token Efficiency

Target metrics:
- Per entry: 30-50 words
- 10 completed tasks: ~400-500 words
- Overview files (GameDesignOverview.md + ImplementationPlanOverview.md + TaskProgress.md): <1500 words combined

Detail files are read on-demand, not all at once.

Avoid:
- Repeating information from other docs
- Verbose descriptions of obvious changes
- Recording trivial tasks (typo fixes, formatting)

## Cross-AI Compatibility

The modular docs_for_ai/ structure is designed for multi-AI workflows:
- Any AI reads the overview files for orientation (GameDesignOverview.md, ImplementationPlanOverview.md, TaskProgress.md)
- AI then reads specific detail files as needed for the current task
- English language ensures broad compatibility
- Structured format enables quick parsing
- Status line provides instant orientation

## Reference Template

See `references/taskprogress-template.md` for full template and examples.

## Integration

This skill complements:
- **design-workflow**: Creates GameDesignOverview.md, ImplementationPlanOverview.md, and detail files
- **additional-items-workflow**: Updates documents when adding features mid-development
- **Platform plugins**: Use progress tracking during implementation

Typical flow:
1. design-workflow creates initial modular docs
2. Developer/AI implements tasks from implementation detail files
3. implementation-workflow records progress after each task
4. Any AI can resume work by reading overview files + relevant detail files
