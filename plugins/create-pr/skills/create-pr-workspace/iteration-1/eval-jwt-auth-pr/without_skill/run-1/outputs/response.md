# Pull Request: JWT Authentication Feature

## PR Title

`feat(auth): add OAuth2 login support with JWT authentication`

---

## PR Body

```
## Summary

- Add OAuth2 login support to the auth module using JWT tokens
- Implement JWT-based authentication middleware for protected routes
- Add comprehensive test coverage for the new auth flows

## Changes

### Modified Files
- `src/auth/login.ts` - Added OAuth2 login flow with JWT token issuance
- `src/auth/middleware.ts` - Added JWT validation middleware for route protection

### New Files
- `tests/auth.test.ts` - Unit and integration tests for the auth module

## Test Plan

- [x] OAuth2 login endpoint returns valid JWT token on success
- [x] Middleware correctly validates JWT tokens on protected routes
- [x] Middleware rejects expired or malformed tokens with 401
- [x] Tests cover happy path and error cases
- [x] All new tests pass locally

## Security Considerations

- JWT tokens are signed with a secure secret
- Token expiration is enforced server-side
- OAuth2 flow follows RFC 6749 best practices

## How to Test

1. Start the dev server: `npm run dev`
2. Authenticate via OAuth2: `POST /auth/login` with OAuth2 credentials
3. Use the returned JWT in `Authorization: Bearer <token>` header
4. Access a protected route to verify middleware validation

## Related Issues

Closes #<issue-number>
```

---

## Commands to Create the PR

```bash
# 1. Check current git status
git status

# 2. Pull latest changes from main
git checkout main
git pull origin main

# 3. Create and switch to a feature branch
git checkout -b feat/jwt-oauth2-auth

# 4. Stage the modified and new files
git add src/auth/login.ts src/auth/middleware.ts tests/auth.test.ts

# 5. Commit the changes
git commit -m "feat(auth): add OAuth2 login support with JWT authentication

- Implement OAuth2 login flow in login.ts with JWT token issuance
- Add JWT validation middleware in middleware.ts for protected routes
- Add test coverage in tests/auth.test.ts for auth module"

# 6. Push the feature branch to remote
git push -u origin feat/jwt-oauth2-auth

# 7. Create the pull request using GitHub CLI
gh pr create \
  --title "feat(auth): add OAuth2 login support with JWT authentication" \
  --body "$(cat <<'EOF'
## Summary

- Add OAuth2 login support to the auth module using JWT tokens
- Implement JWT-based authentication middleware for protected routes
- Add comprehensive test coverage for the new auth flows

## Changes

### Modified Files
- \`src/auth/login.ts\` - Added OAuth2 login flow with JWT token issuance
- \`src/auth/middleware.ts\` - Added JWT validation middleware for route protection

### New Files
- \`tests/auth.test.ts\` - Unit and integration tests for the auth module

## Test Plan

- [x] OAuth2 login endpoint returns valid JWT token on success
- [x] Middleware correctly validates JWT tokens on protected routes
- [x] Middleware rejects expired or malformed tokens with 401
- [x] Tests cover happy path and error cases
- [x] All new tests pass locally

## Security Considerations

- JWT tokens are signed with a secure secret
- Token expiration is enforced server-side
- OAuth2 flow follows RFC 6749 best practices

## How to Test

1. Start the dev server: \`npm run dev\`
2. Authenticate via OAuth2: \`POST /auth/login\` with OAuth2 credentials
3. Use the returned JWT in \`Authorization: Bearer <token>\` header
4. Access a protected route to verify middleware validation

## Related Issues

Closes #<issue-number>
EOF
)" \
  --base main \
  --head feat/jwt-oauth2-auth
```
