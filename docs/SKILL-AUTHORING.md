# KN Marketplace Skill Authoring Standards

Authoring standards for every skill and plugin in this marketplace. These rules
combine the Agent Skills open specification (agentskills.io), Anthropic's
skill-authoring best practices, and OpenAI Codex skill compatibility
requirements. All plugin content MUST be written in English.

Every skill in this marketplace MUST work in **both Claude Code and OpenAI
Codex CLI**, and on **Windows** as well as macOS/Linux.

## 1. Frontmatter: the portable core

Codex reads only `name` and `description` from SKILL.md frontmatter. All other
fields are Claude Code extensions — they may be present, but the skill MUST
remain fully functional when they are ignored.

```yaml
---
name: my-skill            # REQUIRED. Must equal the directory name.
description: ...          # REQUIRED. See rules below.
allowed-tools: ...        # Claude-only extension. Never rely on it for safety.
argument-hint: ...        # Claude-only extension.
---
```

Rules:

- `name`: max 64 chars; lowercase letters, numbers, and hyphens only; no
  leading/trailing/consecutive hyphens; MUST match the parent directory name.
- `description`: non-empty, max 1024 chars, written in **third person**, and
  containing BOTH what the skill does AND an explicit trigger inventory — the
  words, phrases, and file extensions a user would naturally say
  ("Use when ... or when the user mentions ...").
- Never depend on Claude-only fields for correctness: `allowed-tools` is a
  permission optimization, not a behavior contract; `disable-model-invocation`,
  `context`, `model`, and hooks-related fields do not exist in Codex.
- Save SKILL.md as UTF-8 **without BOM** (Codex skips files with a BOM).

## 2. Cross-agent portability (Claude Code + Codex)

- Reference bundled files by **relative path from the skill directory**
  ("Run `scripts/check.py`", "See `references/api.md`"). Never use
  `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_SKILL_DIR}` in skill bodies — those
  variables substitute only in Claude Code. Plugin-level files outside the
  skill directory (e.g. shared `scripts/` at plugin root) may be referenced as
  paths relative to the plugin root, with a one-line note telling the agent to
  locate the installed plugin/skill directory first.
- Do not require Claude-specific tools by name. If a step benefits from
  `AskUserQuestion`, `Task` (subagents), or `TodoWrite`, phrase it with a
  fallback, e.g.:
  > Ask the user which option to use (use the AskUserQuestion tool if
  > available; otherwise ask in a plain message and wait for the reply).
  > Launch parallel subagents if the environment supports them; otherwise
  > perform the steps sequentially.
- No `$ARGUMENTS`, `$1`/`$2`, or `` !`command` `` dynamic injection inside
  portable skill bodies. Treat user input as plain conversation. Slash-command
  invocation hints belong in the description ("Also triggers on /cmd"), never
  as a required entry point.
- Hooks, MCP servers, and slash commands are Claude Code plugin-layer sugar.
  They may enhance a plugin, but the skill body must describe the workflow so
  any agent can follow it without them.

## 3. Windows compatibility

- Always use forward slashes in paths, even when describing Windows usage.
- Invoke Python as: `python3 scripts/x.py` with the standing note
  "(on Windows, use `py -3` if `python3` is not available)". Put OS branching
  *inside* scripts (`sys.platform`, `pathlib`, `os.path.expanduser`,
  `tempfile`) — never in the instructions.
- Bundled scripts: Python (stdlib-preferred) or Node. No `.sh`-only helpers,
  no `chmod +x` setup steps, no symlinks, no hardcoded `/tmp` or `/home/...`
  paths.
- When an instruction must differ per shell (PowerShell vs bash), show the
  default once and put the variant in a short parenthetical or a references
  file — do not fork the whole workflow.

## 4. Structure and progressive disclosure

- SKILL.md body under 500 lines; ideal is far less. Challenge every
  paragraph's token cost — the body stays in context for the whole session.
- Three-level loading: frontmatter (always) → body (on trigger) →
  `references/` and `scripts/` (on demand). Keep references **one level deep**
  from SKILL.md; never chain reference → reference.
- Split `references/` by domain with descriptive file names. Reference files
  over 100 lines start with a table of contents.
- Make execution intent explicit: "Run `scripts/x.py`" (execute) vs
  "See `scripts/x.py` for the algorithm" (read).
- Scripts "solve, don't punt": handle errors explicitly, justify every
  constant, exit non-zero on failure with an actionable message.

## 5. Content patterns that measurably help

Borrowed from the highest-rated public skills (anthropics/skills pdf/docx,
obra/superpowers):

- **Quick Start first**: the most common path in the first screen of the body.
- **Decision tree** when the skill covers multiple modes
  ("Creating new? → ... Editing existing? → ...").
- **One default with an escape hatch** instead of a menu of options
  ("Use X. For <edge case>, use Y instead.").
- **Verification checklist** the agent must satisfy before declaring success.
- **Feedback loop**: validate → fix → re-validate; "only proceed when
  validation passes."
- **Red flags / STOP list** for discipline skills: signs the agent is about to
  rationalize its way around the rules, and what to do instead.
- Consistent terminology (pick one term per concept) and no time-sensitive
  content ("before 2025 use the old API" — keep only the current method).

## 6. Evaluation

- Each substantive skill ships `evals/evals.json` with at least 3 scenarios:
  `{skill, query, expected_behavior[]}`.
- New skills and significantly rewritten skills MUST be benchmarked
  with-skill vs without-skill (skill-creator methodology) before release, and
  results recorded under `eval-archives/<plugin>/` at the repository root.
  Eval run artifacts never ship inside `plugins/`.

## 7. Plugin metadata and versioning

- `plugin.json` `name` is kebab-case and must match the directory and the
  marketplace entry. Component directories (`skills/`, `commands/`, `agents/`,
  `hooks/`) live at the plugin root, NOT inside `.claude-plugin/`.
- Version sync: bump `plugin.json` `version` AND the matching entry in
  `.claude-plugin/marketplace.json` on every content change
  (PATCH = small fix, MINOR = feature/structure change, MAJOR = breaking —
  MAJOR requires explicit user approval). The version field is the update
  cache key: no bump means users never receive the change.
- Run `claude plugin validate --strict <plugin-dir>` before committing.
