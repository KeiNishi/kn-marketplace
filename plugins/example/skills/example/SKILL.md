---
name: example
description: Example skill demonstrating the standard plugin structure. Use this as a reference when creating new skills.
---

# Example Skill

This is a template skill demonstrating the standard Claude Code plugin structure.

## How to Create a New Skill

1. Create a directory: `skills/<skill-name>/`
2. Add a skill file: `skills/<skill-name>/SKILL.md`
3. Include YAML frontmatter with `name` and `description`
4. Write skill instructions in Markdown below the frontmatter

## Skill File Structure

A skill directory can contain:

- **`SKILL.md`** (required) - Main instructions with YAML frontmatter
- **`references/`** (optional) - Supporting reference documents
- **`scripts/`** (optional) - Utility scripts

## Frontmatter Fields

```yaml
---
name: my-skill
description: What this skill does and when to use it
allowed-tools: Read, Grep, Glob
---
```

Key fields:
- `name` - Skill identifier (lowercase, hyphens)
- `description` - When Claude should use this skill
- `allowed-tools` - Tools permitted without asking (optional)
- `disable-model-invocation` - Set `true` for manual-only invocation (optional)
- `argument-hint` - Hint for expected arguments (optional)

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

## Notes

- Keep `SKILL.md` under 500 lines; move detailed content to `references/`
- Write all skill content in English for optimal AI processing
- Register the plugin in `marketplace.json` to distribute it
- Sync version numbers between `plugin.json` and `marketplace.json`
