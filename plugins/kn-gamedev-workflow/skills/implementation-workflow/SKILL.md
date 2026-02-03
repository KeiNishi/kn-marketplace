---
name: implementation-workflow
description: This skill activates when implementing tasks from ImplementationPlan.md in a project with docs_for_ai/ folder. Triggers when completing implementation tasks, finishing a coding task from the plan, or when the user mentions "update progress", "log progress", "record task", "implementation task done", or "mark task complete". Also activates when working on tasks referenced in ImplementationPlan.md.
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
- Completing a task from ImplementationPlan.md
- Finishing a phase milestone
- Making significant technical decisions
- Encountering and resolving issues

## Workflow

### Step 1: Verify Context

Before recording, confirm:
1. `docs_for_ai/` folder exists
2. `GameDesign.md` and `ImplementationPlan.md` are present
3. Identify which Phase/Task from ImplementationPlan.md was completed

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
- Task name must match or reference ImplementationPlan.md
- Files: comma-separated, relative paths
- Done: maximum 2 sentences
- Decision/Issue: omit if not applicable

### Step 4: Update Status Line

```markdown
**Status**: Phase [N]/[Total] - [Phase Name] | Next: [Next Task] | Updated: [YYYY-MM-DD]
```

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
- Use exact task names from ImplementationPlan.md when possible
- Reference Phase and Task numbers: `[Phase 2, Task 3]`
- Keep Status line synchronized with actual progress

## Token Efficiency

Target metrics:
- Per entry: 30-50 words
- 10 completed tasks: ~400-500 words
- Combined docs_for_ai/ (3 files): <2500 words

Avoid:
- Repeating information from other docs
- Verbose descriptions of obvious changes
- Recording trivial tasks (typo fixes, formatting)

## Cross-AI Compatibility

TaskProgress.md is designed for multi-AI workflows:
- Any AI can read the 3 docs_for_ai/ files to understand project context
- English language ensures broad compatibility
- Structured format enables quick parsing
- Status line provides instant orientation

## Reference Template

See `references/taskprogress-template.md` for full template and examples.

## Integration

This skill complements:
- **design-workflow**: Creates GameDesign.md and ImplementationPlan.md
- **Platform plugins**: Use progress tracking during implementation

Typical flow:
1. design-workflow creates initial docs
2. Developer/AI implements tasks from ImplementationPlan.md
3. implementation-workflow records progress after each task
4. Any AI can resume work by reading all 3 docs
