---
name: bugfix
description: Start the bug fix workflow. Launches the bug-fixer agent in a separate context to investigate and fix a reported bug while keeping the main conversation clean.
argument-hint: "[bug-description]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion
---

# Bug Fix Workflow Command

Launch the bug-fixer agent to investigate and fix a bug reported by the user.

## Usage

```
/kn-gamedev-workflow:bugfix [optional: bug description]
```

## Arguments

- `$ARGUMENTS` - Optional initial bug description. If provided, the agent begins investigation immediately. If empty, the agent asks the user to describe the bug.

## Workflow

### Step 1: Verify Project Context

Check that `docs_for_ai/` folder exists with game design and implementation documents. The bug-fixer agent requires these documents to understand intended behavior.

If `docs_for_ai/` does not exist, inform the user that project documentation is required and suggest running `/kn-gamedev-workflow:design` first.

### Step 2: Launch Bug-Fixer Agent

Invoke the `bug-fixer` agent with the following context:

- If `$ARGUMENTS` provided: pass the bug description to the agent
- If empty: the agent will ask the user to describe the bug

The bug-fixer agent runs in its own context window to:
- Keep the main conversation free from debugging noise
- Provide a clean workspace for focused investigation
- Save tokens by isolating the bug fix context

### Step 3: Agent Handles the Fix

The bug-fixer agent autonomously:

1. Reads project documentation from `docs_for_ai/`
2. Loads the appropriate platform skill (Unity / Godot / Playdate)
3. Analyzes the bug report and asks clarifying questions
4. Investigates root cause in the codebase
5. Implements a proper fix following coding standards
6. Presents a fix report and asks the user to verify
7. Iterates if the bug persists

### Step 4: Completion

When the user confirms the bug is resolved, the agent:
- Updates its memory with the bug pattern for future reference
- Returns a summary of the fix to the main conversation

## Examples

### With Bug Description

```
/kn-gamedev-workflow:bugfix Player takes double damage when hitting a wall while jumping
```

The agent immediately begins investigating the described bug.

### Without Arguments

```
/kn-gamedev-workflow:bugfix
```

The agent asks the user to describe the bug, reproduction steps, and any relevant details.

## Notes

- The bug-fixer agent operates in a separate context to preserve the main conversation
- The agent only fixes bugs; it does not make design changes
- If a design change is needed to properly fix the bug, the agent will notify the user and stop
- All fixes follow the platform skill's coding conventions
- No lazy fixes allowed: the agent addresses root causes, never symptoms
