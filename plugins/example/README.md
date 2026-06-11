# example

A **template plugin** for the KN Marketplace. It exists as a copyable
reference for creating new plugins - it is **not intended for installation**
as a working tool.

## What it demonstrates

- The standard plugin directory layout (`.claude-plugin/plugin.json`,
  `skills/<name>/SKILL.md`, optional `references/`, `scripts/`, `commands/`,
  `agents/`, `hooks/`)
- The portable frontmatter core (`name` + `description`) that works in both
  Claude Code and OpenAI Codex CLI
- This marketplace's cross-agent and Windows authoring rules (relative paths
  from the skill directory, `python3` / `py -3` invocation, UTF-8 without
  BOM, forward slashes)

## How to use it

1. Copy `plugins/example/` to `plugins/<your-plugin-name>/`
2. Rename the skill directory and update `name` in both `plugin.json` and
   `SKILL.md` to match the new directory names
3. Replace the skill body with your instructions
4. Register the plugin in `.claude-plugin/marketplace.json`
5. Validate: `claude plugin validate --strict ./plugins/<your-plugin-name>`

## Full standard

See `docs/SKILL-AUTHORING.md` at the repository root for the complete,
binding authoring standard (frontmatter rules, cross-agent portability,
Windows compatibility, structure, and evaluation requirements).
