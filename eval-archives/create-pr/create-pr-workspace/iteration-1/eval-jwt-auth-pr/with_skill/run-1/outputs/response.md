# Create Pull Request - JWT Authentication Feature

## Step 1: Check Current State

Commands run to inspect the repository:

```bash
git status
git diff --stat
git log origin/main..HEAD --oneline
```

### Expected output (hypothetical):

```
# git status
On branch feat/jwt-oauth2-auth
Changes not staged for commit:
  modified:   src/auth/login.ts
  modified:   src/auth/middleware.ts

Untracked files:
  tests/auth.test.ts

# git diff --stat
 src/auth/login.ts      | 87 ++++++++++++++++++++++++++++++++++++++++++++
 src/auth/middleware.ts | 42 ++++++++++++++++++++++++
 tests/auth.test.ts     | 65 +++++++++++++++++++++++++++++++++
 3 files changed, 194 insertions(+)

# git log origin/main..HEAD --oneline
a1b2c3d feat(auth): Add OAuth2 login support and JWT middleware
```

## Step 2: Analyze Changes

- **Type**: `feat` - This is a new feature (OAuth2 login support)
- **Scope**: `auth` - The changes are confined to the auth module (`src/auth/`)
- **Summary**: "Add OAuth2 login support with JWT authentication"
- **Files changed**:
  - `src/auth/login.ts` - OAuth2 login implementation
  - `src/auth/middleware.ts` - JWT authentication middleware
  - `tests/auth.test.ts` - Tests for the auth module

## Step 3: Push Branch

```bash
git push -u origin HEAD
```

## Step 4: Create Pull Request

### PR Title

```
feat(auth): Add OAuth2 login support with JWT authentication
```

**Validation check against pattern** `^(feat|fix|perf|test|docs|refactor|build|ci|chore|revert)(\([a-zA-Z0-9 -]+\))?!?: [A-Z].+[^.]$`:
- Type: `feat` - valid
- Scope: `(auth)` - valid, in parentheses
- No breaking change (`!` not needed)
- Summary starts with capital "A" - valid
- Summary does not end with period - valid

### Full gh CLI Command

```bash
gh pr create --title "feat(auth): Add OAuth2 login support with JWT authentication" --body "$(cat <<'EOF'
## Summary

This PR adds OAuth2 login support to the authentication module and introduces JWT-based middleware for securing API routes.

### Changes

- **`src/auth/login.ts`**: Implemented OAuth2 authorization flow, including token exchange and user profile retrieval from the OAuth2 provider.
- **`src/auth/middleware.ts`**: Added JWT verification middleware that validates Bearer tokens on protected routes, attaches decoded user context to the request object, and returns 401 on invalid or expired tokens.
- **`tests/auth.test.ts`**: Added unit and integration tests covering OAuth2 login flow, JWT token generation, middleware validation (valid token, expired token, missing token).

### How to Test

1. Configure OAuth2 credentials in `.env`:
   ```
   OAUTH2_CLIENT_ID=your_client_id
   OAUTH2_CLIENT_SECRET=your_client_secret
   OAUTH2_REDIRECT_URI=http://localhost:3000/auth/callback
   JWT_SECRET=your_jwt_secret
   ```
2. Start the development server: `npm run dev`
3. Visit `/auth/login` to initiate the OAuth2 flow
4. On successful login, a JWT token is returned and stored in the session
5. Access a protected route (e.g., `GET /api/profile`) with `Authorization: Bearer <token>` header to verify middleware works
6. Run tests: `npm test tests/auth.test.ts`

## Related Issues

<!-- Use "closes #<issue-number>", "fixes #<issue-number>", or "resolves #<issue-number>" to auto-close issues -->

## Checklist

- [x] PR title follows conventional commit format
- [x] Tests included
- [ ] Documentation updated (if applicable)
EOF
)"
```

### PR Body (rendered)

---

## Summary

This PR adds OAuth2 login support to the authentication module and introduces JWT-based middleware for securing API routes.

### Changes

- **`src/auth/login.ts`**: Implemented OAuth2 authorization flow, including token exchange and user profile retrieval from the OAuth2 provider.
- **`src/auth/middleware.ts`**: Added JWT verification middleware that validates Bearer tokens on protected routes, attaches decoded user context to the request object, and returns 401 on invalid or expired tokens.
- **`tests/auth.test.ts`**: Added unit and integration tests covering OAuth2 login flow, JWT token generation, middleware validation (valid token, expired token, missing token).

### How to Test

1. Configure OAuth2 credentials in `.env`:
   ```
   OAUTH2_CLIENT_ID=your_client_id
   OAUTH2_CLIENT_SECRET=your_client_secret
   OAUTH2_REDIRECT_URI=http://localhost:3000/auth/callback
   JWT_SECRET=your_jwt_secret
   ```
2. Start the development server: `npm run dev`
3. Visit `/auth/login` to initiate the OAuth2 flow
4. On successful login, a JWT token is returned and stored in the session
5. Access a protected route (e.g., `GET /api/profile`) with `Authorization: Bearer <token>` header to verify middleware works
6. Run tests: `npm test tests/auth.test.ts`

## Related Issues

<!-- Use "closes #<issue-number>", "fixes #<issue-number>", or "resolves #<issue-number>" to auto-close issues -->

## Checklist

- [x] PR title follows conventional commit format
- [x] Tests included
- [ ] Documentation updated (if applicable)

---

### Expected Output After PR Creation

```
https://github.com/<owner>/<repo>/pull/42
```
