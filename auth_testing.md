# Helix Auth Testing Playbook

## Test Accounts (seeded)
See `/app/memory/test_credentials.md` for fresh credentials.

Authentication supports two flows:
1. Email + password (JWT) — `POST /api/auth/login` returns `{ access_token, user }`. Send as `Authorization: Bearer <token>`.
2. Emergent Google OAuth — session_id in URL fragment → `POST /api/auth/emergent/session` → httpOnly `session_token` cookie (7 days).

## Backend uses EITHER:
- `Authorization: Bearer <JWT>` header, OR
- `session_token` cookie (Emergent), OR
- `Authorization: Bearer <session_token>` (fallback for Emergent)

Any of the three resolves the current user via `get_current_user` dependency.

## Quick test (JWT)
```bash
TOKEN=$(curl -s -X POST $BASE/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@helix.com","password":"Helix@123"}' | jq -r .access_token)
curl -s $BASE/api/auth/me -H "Authorization: Bearer $TOKEN"
```

## Roles
- `exporter` — can list products, receive orders, withdraw
- `buyer` — can submit RFQs, confirm orders, pay
- `admin` / `super_admin` — KYC/KYB queue, disputes, transactions overview

## Anchor is MOCKED in sandbox
- `ANCHOR_ENV=sandbox_mock` in backend/.env means all Anchor API calls are simulated and clearly marked with `[MOCK]` in logs.
- Flip to `ANCHOR_ENV=sandbox` + set `ANCHOR_API_KEY` to enable real calls later.
