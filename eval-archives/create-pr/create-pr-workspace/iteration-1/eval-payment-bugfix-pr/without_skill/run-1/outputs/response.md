# PR: Fix Payment API 500 Error on Large File Uploads (>10MB)

## PR Title

```
fix: resolve 500 error in payment API for large file uploads over 10MB
```

## PR Body

```markdown
## Summary

Fixes a bug where the payment API was returning a 500 Internal Server Error when processing file uploads larger than 10MB. The root cause was missing chunked upload handling in the payment endpoint.

## Changes

- `api/payment.py`: Added proper chunked upload handling to support files over 10MB

## Problem

When a file upload exceeding 10MB was submitted to the payment API, the server would return a 500 error. This was caused by the API attempting to read the entire file into memory at once rather than processing it in chunks.

## Solution

Implemented chunked upload handling in `api/payment.py` so that large files are read and processed in manageable chunks rather than loaded entirely into memory. This prevents memory exhaustion and timeout issues that caused the 500 error.

## Testing

- [ ] Tested with files under 10MB (existing behavior preserved)
- [ ] Tested with files exactly at 10MB boundary
- [ ] Tested with files over 10MB (previously failing, now working)
- [ ] Verified no regression in payment processing for normal uploads
- [ ] Checked error handling for invalid/corrupt file uploads

## Related Issues

Closes #<issue-number> (if applicable)
```

## Commands to Create the PR

### Step 1: Check git status and ensure on correct branch

```bash
git status
git log --oneline -5
```

### Step 2: Create and switch to a feature branch (if not already on one)

```bash
git checkout -b fix/payment-api-large-file-upload-500-error
```

### Step 3: Stage and commit the fix

```bash
git add api/payment.py
git commit -m "fix: resolve 500 error in payment API for large file uploads over 10MB

Added proper chunked upload handling in api/payment.py to support
file uploads larger than 10MB. Previously, the payment API would
return a 500 Internal Server Error when attempting to process files
over this size limit due to missing chunked upload support."
```

### Step 4: Push the branch to remote

```bash
git push -u origin fix/payment-api-large-file-upload-500-error
```

### Step 5: Create the PR using GitHub CLI

```bash
gh pr create \
  --title "fix: resolve 500 error in payment API for large file uploads over 10MB" \
  --body "$(cat <<'EOF'
## Summary

Fixes a bug where the payment API was returning a 500 Internal Server Error when processing file uploads larger than 10MB. The root cause was missing chunked upload handling in the payment endpoint.

## Changes

- `api/payment.py`: Added proper chunked upload handling to support files over 10MB

## Problem

When a file upload exceeding 10MB was submitted to the payment API, the server would return a 500 error. This was caused by the API attempting to read the entire file into memory at once rather than processing it in chunks.

## Solution

Implemented chunked upload handling in `api/payment.py` so that large files are read and processed in manageable chunks rather than loaded entirely into memory. This prevents memory exhaustion and timeout issues that caused the 500 error.

## Testing

- [ ] Tested with files under 10MB (existing behavior preserved)
- [ ] Tested with files exactly at 10MB boundary
- [ ] Tested with files over 10MB (previously failing, now working)
- [ ] Verified no regression in payment processing for normal uploads
- [ ] Checked error handling for invalid/corrupt file uploads

## Related Issues

Closes #<issue-number> (if applicable)
EOF
)" \
  --base main
```
