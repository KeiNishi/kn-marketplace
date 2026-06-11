# kn-gamedev-workflow

Universal game development workflow plugin: structured design documents, implementation plans, progress tracking, and disciplined debugging. Platform and engine agnostic — works with Unity, Godot, Playdate, or any custom engine.

The plugin centers on a `docs_for_ai/` folder in your game project that serves as the single source of truth for any AI agent: modular design and implementation documents plus a compact progress log, so any agent (Claude, Codex, Gemini, ...) can pick up the project cold and continue working.

## Skills

| Skill | Purpose |
|-------|---------|
| `design-workflow` | Guides the design phase of a new game: gathers requirements, asks clarifying questions, then generates modular documentation in `docs_for_ai/` (GameDesignOverview.md, ImplementationPlanOverview.md, and per-system detail files), followed by an iterative design review until approved. |
| `design-change-workflow` | Handles mid-development changes to existing docs: adding, modifying, replacing, or removing features. Classifies the change, clarifies it, schedules it against current progress, updates the affected documents, and re-runs the design review. |
| `implementation-workflow` | Records implementation progress in `docs_for_ai/TaskProgress.md` after each completed task, with a strict compact entry format and status line so any agent can resume work instantly. |
| `gamedev-debugging` | Systematic debugging discipline for game-specific bugs: frame-dependent bugs, physics/timestep issues, async-loading races, state-machine corruption, save/load determinism, platform-specific differences. Enforces reproduce-before-fix, single-hypothesis testing, and root-cause fixes — never workarounds. |

## Commands (Claude Code)

- `/kn-gamedev-workflow:design [game-concept]` — start the design workflow for a new game project.
- `/kn-gamedev-workflow:bugfix [bug-description]` — launch the bug-fixer agent in its own context to investigate and fix a reported bug.

## Agents (Claude Code)

- `design-review` — reviews all `docs_for_ai/` documents for completeness, clarity, consistency, and file integrity; returns APPROVED or NEEDS_REVISION with specific questions.
- `bug-fixer` — dedicated bug-fix specialist that investigates root causes and implements proper fixes under a strict no-workaround policy.

## Quick Start

1. Install the plugin from the KN marketplace.
2. Start a new game project: say "design a game" (or run `/kn-gamedev-workflow:design`), describe your concept, and answer the clarification questions.
3. The workflow creates `docs_for_ai/` with overview documents and per-system detail files, then reviews them iteratively until approved.
4. Implement tasks from the `implementation/` detail files; after each task, say "log progress" to record it in `TaskProgress.md`.
5. When requirements change, say "change the design" to update the documents safely.
6. When something breaks, describe the bug — the `gamedev-debugging` skill enforces reproduce-then-root-cause-then-fix.

## Output Structure

```
project-root/
└── docs_for_ai/
    ├── GameDesignOverview.md          # Concept, world, scope, file manifest
    ├── ImplementationPlanOverview.md  # Phases, structure, dependencies, manifest
    ├── TaskProgress.md                # Compact progress log + status line
    ├── game_design/                   # 01_Player_Design.md, 02_..._Design.md
    └── implementation/                # 01_Player_Implementation.md, ...
```

## Cross-Agent Compatibility

The four skills are written to work in both Claude Code and OpenAI Codex CLI (and other agents that read SKILL.md):

- Skill bodies never require Claude-only tools. Steps that benefit from `AskUserQuestion` or subagents include explicit fallbacks (ask in a plain message; perform the review directly in the conversation).
- All bundled files are referenced by relative paths; no environment-variable substitution.
- All generated documents are plain English Markdown, readable by any agent.
- Commands and agents are Claude Code conveniences only — every workflow is fully completable from the skills alone.

The plugin also integrates with platform-specific skills when available (`unity-gamedev-standards:unity-gamedev`, `godot-gdscript-patterns`, `playdate-gamedev`); when absent, the workflows fall back to general best practices.
