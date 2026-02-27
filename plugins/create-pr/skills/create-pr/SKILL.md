---
name: create-pr
description: Creates GitHub pull requests with conventional commit titles. Use when creating PRs, submitting changes for review, or when the user says /pr or asks to create a pull request.
allowed-tools: Bash(git status*), Bash(git diff*), Bash(git log*), Bash(git push -u origin*), Bash(gh pr create*), Bash(gh pr view*), Read, Grep, Glob
disable-model-invocation: true
---

# Create Pull Request

Creates GitHub PRs with conventional commit-style titles for consistent, readable PR history.

## PR Title Format

```
<type>(<scope>): <summary>
```

### Types (required)

| Type       | Description                         |
|------------|-------------------------------------|
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `perf`     | Performance improvement             |
| `test`     | Adding/correcting tests             |
| `docs`     | Documentation only                  |
| `refactor` | Code change (no bug fix or feature) |
| `build`    | Build system or dependencies        |
| `ci`       | CI configuration                    |
| `chore`    | Routine tasks, maintenance          |
| `revert`   | Reverting a previous change         |

### Scopes (optional but recommended)

Use scopes to indicate the area of the codebase affected:

- Module or package name (e.g., `auth`, `api`, `ui`)
- Layer name (e.g., `core`, `frontend`, `backend`)
- Feature area (e.g., `login`, `dashboard`, `settings`)

### Summary Rules

- Use imperative present tense: "Add" not "Added"
- Capitalize first letter
- No period at the end
- Keep concise (under 72 characters total)

## Steps

1. **Check current state**:
   ```bash
   git status
   git diff --stat
   git log origin/main..HEAD --oneline
   ```

2. **Analyze changes** to determine:
   - Type: What kind of change is this?
   - Scope: Which module/area is affected?
   - Summary: What does the change do?

3. **Push branch if needed**:
   ```bash
   git push -u origin HEAD
   ```

4. **Create PR** using gh CLI:
   ```bash
   gh pr create --title "<type>(<scope>): <summary>" --body "$(cat <<'EOF'
   ## Summary

   <Describe what the PR does and how to test.>

   ## Related Issues

   <!-- Use "closes #<issue-number>", "fixes #<issue-number>", or "resolves #<issue-number>" to auto-close issues -->

   ## Checklist

   - [ ] PR title follows conventional commit format
   - [ ] Tests included
   - [ ] Documentation updated (if applicable)
   EOF
   )"
   ```

## PR Body Guidelines

### Summary Section
- Describe what the PR does
- Explain how to test the changes
- Include screenshots/videos for UI changes

### Related Issues Section
- Link to GitHub issues using keywords to auto-close:
  - `closes #123` / `fixes #123` / `resolves #123`

### Checklist
- PR title follows conventional commit format
- Tests included where applicable
- Documentation updated if needed

## Examples

### New feature
```
feat(auth): Add OAuth2 login support
```

### Bug fix
```
fix(api): Resolve timeout on large file uploads
```

### Breaking change (add exclamation mark before colon)
```
feat(api)!: Remove deprecated v1 endpoints
```

### No scope (affects multiple areas)
```
chore: Update dependencies to latest versions
```

### Refactoring
```
refactor(core): Simplify error handling pipeline
```

## Validation

The PR title should match this pattern:
```
^(feat|fix|perf|test|docs|refactor|build|ci|chore|revert)(\([a-zA-Z0-9 -]+\))?!?: [A-Z].+[^.]$
```

Key validation rules:
- Type must be one of the allowed types
- Scope is optional but must be in parentheses if present
- Exclamation mark for breaking changes goes before the colon
- Summary must start with a capital letter
- Summary must not end with a period
