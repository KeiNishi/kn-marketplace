---
name: example
description: Demonstrates the standard plugin and skill structure for this marketplace. Use as a reference when creating a new plugin or skill, or when the user asks for a template, an example skill, or how plugins are structured.
---

# Example Skill

This is a template skill demonstrating the standard plugin structure and this
marketplace's cross-agent (Claude Code + OpenAI Codex CLI) and Windows
authoring rules. See `docs/SKILL-AUTHORING.md` at the repository root for the
full standard.

## How to Create a New Skill

1. Create a directory: `skills/<skill-name>/`
2. Add a skill file: `skills/<skill-name>/SKILL.md`
3. Include YAML frontmatter with `name` and `description`
4. Write skill instructions in Markdown below the frontmatter
5. Save the file as UTF-8 **without BOM** (Codex skips files with a BOM)

## Skill File Structure

A skill directory can contain:

- **`SKILL.md`** (required) - Main instructions with YAML frontmatter
- **`references/`** (optional) - Supporting reference documents
- **`scripts/`** (optional) - Utility scripts

## Frontmatter: the portable core

```yaml
---
name: my-skill
description: What this skill does and when to use it (third person, with triggers)
allowed-tools: Read, Grep, Glob   # Claude-only extension
---
```

Codex reads only `name` and `description`. All other fields
(`allowed-tools`, `disable-model-invocation`, `argument-hint`, ...) are
Claude Code extensions: they may be present, but the skill must remain fully
functional when they are ignored. Never rely on them for correctness.

- `name` - lowercase letters, numbers, hyphens; must match the directory name
- `description` - third person; states what the skill does AND the trigger
  words/phrases a user would naturally say

## Cross-agent and Windows rules

- Reference bundled files by **relative path from the skill directory**
  ("Run `scripts/check.py`"). Never use `${CLAUDE_PLUGIN_ROOT}` or
  `${CLAUDE_SKILL_DIR}` in skill bodies - they only substitute in Claude Code.
- Invoke Python as `python3 scripts/x.py` with the standing note
  "(on Windows, use `py -3` if `python3` is not available)". Put OS branching
  inside scripts, never in the instructions.
- Use forward slashes in all paths; no `.sh`-only helpers, no `chmod +x`
  steps, no hardcoded `/tmp` or `/home/...` paths.

## Plugin Directory Layout

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata (name, version, description)
├── skills/
│   └── my-skill/
│       ├── SKILL.md          # Main skill file
│       └── references/       # Optional reference docs
├── commands/                 # Optional command files
├── agents/                   # Optional subagent files
└── hooks/                    # Optional hook configurations
```

Commands, agents, and hooks are Claude Code plugin-layer extras - the skill
body must describe the workflow so any agent can follow it without them.

## Notes

- Keep `SKILL.md` under 500 lines; move detailed content to `references/`
- Write all skill content in English
- Register the plugin in `marketplace.json` to distribute it
- Sync version numbers between `plugin.json` and `marketplace.json`
- Run `claude plugin validate --strict <plugin-dir>` before committing
