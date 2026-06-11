# create-pr

Creates GitHub pull requests with conventional commit-style titles for a
consistent, readable PR history.

## What it does

When you ask the agent to create a pull request (or mention `/pr`), this
skill guides it to:

1. Inspect the current branch state (`git status`, `git diff`, `git log`)
2. Derive a conventional commit title: `<type>(<scope>): <summary>`
3. Push the branch to the remote
4. Open the PR with `gh pr create`, using a structured body
   (Summary / Related Issues / Checklist)
5. Verify the result against a checklist before reporting success

## PR title format

```
<type>(<scope>): <summary>
```

- **Types**: `feat`, `fix`, `perf`, `test`, `docs`, `refactor`, `build`,
  `ci`, `chore`, `revert`
- **Scope**: optional module/area in parentheses (e.g. `feat(auth): ...`)
- **Breaking changes**: add `!` before the colon (`feat(api)!: ...`)
- **Summary**: imperative present tense, capitalized, no trailing period

Examples:

```
feat(auth): Add OAuth2 login support
fix(api): Resolve timeout on large file uploads
chore: Update dependencies to latest versions
```

## Requirements

- `git` and a GitHub remote
- [GitHub CLI (`gh`)](https://cli.github.com/), authenticated via `gh auth login`.
  `gh` works identically on Windows, macOS, and Linux.
- If `gh` is unavailable, the skill falls back gracefully: it pushes the
  branch and gives you the GitHub compare URL plus the prepared title and
  body so you can open the PR in the browser.

## Compatibility

The skill body is portable: it relies only on `git` and `gh`, so it works in
both Claude Code and OpenAI Codex CLI, on all platforms.

## Contents

- `skills/create-pr/SKILL.md` - the skill instructions
- `skills/create-pr/evals/evals.json` - evaluation scenarios
