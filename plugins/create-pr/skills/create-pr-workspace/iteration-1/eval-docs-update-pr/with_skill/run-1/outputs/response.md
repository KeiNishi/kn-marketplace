# Create Pull Request - Documentation Update

## Step 1: Check Current State

Commands I would run to check the current state:

```bash
git status
git diff --stat
git log origin/main..HEAD --oneline
```

Expected output (hypothetical):
```
On branch docs/update-readme-and-api-reference
Your branch is ahead of 'origin/docs/update-readme-and-api-reference' by 2 commits.

 README.md          | 45 +++++++++++++++++++++++++++++++++++++++++++++
 docs/api-reference.md | 120 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 165 insertions(+), 8 deletions(-)

abc1234 docs: Improve README installation instructions
def5678 docs: Add API reference documentation
```

## Step 2: Analyze Changes

- **Type**: `docs` — Both changes are documentation-only updates (README.md and API reference)
- **Scope**: Not a single module; affects general docs. Could use `docs` or omit scope since it spans multiple documentation files.
- **Summary**: "Update README installation instructions and add API reference"

## Step 3: Push Branch

```bash
git push -u origin HEAD
```

## Step 4: Create PR

### PR Title

```
docs: Update README installation instructions and add API reference
```

Validation check against pattern `^(feat|fix|perf|test|docs|refactor|build|ci|chore|revert)(\([a-zA-Z0-9 -]+\))?!?: [A-Z].+[^.]$`:
- Type: `docs` - valid
- Scope: omitted (changes span multiple doc files) - valid
- Summary starts with capital "U" - valid
- Summary does not end with a period - valid

### PR Body

```
## Summary

This PR improves project documentation in two ways:

1. **README.md** - Rewrote the installation instructions section with clearer step-by-step guidance, making it easier for new users to get started quickly.
2. **docs/api-reference.md** - Added comprehensive API documentation covering all available endpoints, request/response formats, and example usage.

To verify these changes, review the updated README.md for improved clarity and check docs/api-reference.md for the new API documentation content.

## Related Issues

<!-- Use "closes #<issue-number>", "fixes #<issue-number>", or "resolves #<issue-number>" to auto-close issues -->

## Checklist

- [x] PR title follows conventional commit format
- [ ] Tests included
- [x] Documentation updated (if applicable)
```

### Full gh Command

```bash
gh pr create --title "docs: Update README installation instructions and add API reference" --body "$(cat <<'EOF'
## Summary

This PR improves project documentation in two ways:

1. **README.md** - Rewrote the installation instructions section with clearer step-by-step guidance, making it easier for new users to get started quickly.
2. **docs/api-reference.md** - Added comprehensive API documentation covering all available endpoints, request/response formats, and example usage.

To verify these changes, review the updated README.md for improved clarity and check docs/api-reference.md for the new API documentation content.

## Related Issues

<!-- Use "closes #<issue-number>", "fixes #<issue-number>", or "resolves #<issue-number>" to auto-close issues -->

## Checklist

- [x] PR title follows conventional commit format
- [ ] Tests included
- [x] Documentation updated (if applicable)
EOF
)"
```
