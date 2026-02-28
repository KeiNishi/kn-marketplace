# Pull Request: Documentation Update

## PR Title

```
docs: improve installation instructions and add API reference documentation
```

---

## PR Body

```markdown
## Summary

- Updated `README.md` with clearer and more comprehensive installation instructions
- Added `docs/api-reference.md` with full API documentation

## Changes

### README.md
- Rewrote installation instructions for improved clarity and completeness
- Added step-by-step setup guide for new users
- Improved formatting and readability

### docs/api-reference.md
- Created new API reference documentation
- Documented all available endpoints, parameters, and response formats
- Included usage examples for common API operations

## Test plan

- [ ] Verify all links in `README.md` are working
- [ ] Confirm installation steps are accurate and reproducible on a fresh environment
- [ ] Review `docs/api-reference.md` for completeness and accuracy
- [ ] Check that code examples in the API docs are correct

## Notes

This is a documentation-only change with no functional code modifications.
```

---

## Commands to Create the PR

```bash
# 1. Check current git status
git status

# 2. Ensure you are on the correct feature branch (create if needed)
git checkout -b docs/improve-installation-and-api-reference

# 3. Stage the changed files
git add README.md docs/api-reference.md

# 4. Commit the changes
git commit -m "docs: improve installation instructions and add API reference documentation"

# 5. Push the branch to the remote repository
git push -u origin docs/improve-installation-and-api-reference

# 6. Create the pull request using the GitHub CLI
gh pr create \
  --title "docs: improve installation instructions and add API reference documentation" \
  --body "$(cat <<'EOF'
## Summary

- Updated \`README.md\` with clearer and more comprehensive installation instructions
- Added \`docs/api-reference.md\` with full API documentation

## Changes

### README.md
- Rewrote installation instructions for improved clarity and completeness
- Added step-by-step setup guide for new users
- Improved formatting and readability

### docs/api-reference.md
- Created new API reference documentation
- Documented all available endpoints, parameters, and response formats
- Included usage examples for common API operations

## Test plan

- [ ] Verify all links in \`README.md\` are working
- [ ] Confirm installation steps are accurate and reproducible on a fresh environment
- [ ] Review \`docs/api-reference.md\` for completeness and accuracy
- [ ] Check that code examples in the API docs are correct

## Notes

This is a documentation-only change with no functional code modifications.
EOF
)"
```

---

## Expected Output

After running the final `gh pr create` command, the GitHub CLI will return a URL like:

```
https://github.com/<owner>/<repo>/pull/<PR-number>
```
