# SYNCHRO — Security Runbook

## Scope

Covers the SYNCHRO cloud backend (`SYNCHRO/backend`). The local MT4/MT5 EA and
desktop app are out of scope until their development phases begin.

## Implemented controls

| Control | Implementation | Tests |
|---|---|---|
| Password hashing | bcrypt (salted, constant-time verify) | `test_auth.py` |
| Brute force (per-IP) | sliding-window rate limits on register/login/refresh | `test_rate_limit_lockout_registry.py` |
| Brute force (per-account) | escalating lockout: 3 fails → 30s, doubling to 15min max | same |
| Token model | short-lived access JWT (30 min) + rotating refresh (14 d) with family lineage | `test_session_security.py` |
| **Refresh-reuse kill switch** | replaying a rotated refresh token revokes the entire session family | same |
| Logout / password rotation | kills current family / all families for the user | same |
| Secrets at rest | AES-256-GCM (`cryptography`), auto-fallback to stdlib HMAC-SHA256 AEAD; versioned `v1.` blobs; tamper → hard fail | `test_crypto.py` |
| Security headers | nosniff, DENY framing, CSP, Referrer-Policy, Permissions-Policy; HSTS in prod | `test_security_headers.py` |
| CORS | strict origin allowlist from settings | same |
| Prod config guard | refuses to boot in production with default JWT secret, debug on, or missing encryption key | same |
| Payload abuse | 1 MiB body cap (413) | same |
| Log hygiene | formatter redacts `Bearer …` and `pat_…` tokens from every log line | `test_platform_security.py` |
| Trade-surface safety | symbol whitelist (`domain/market_symbols.py`) gates any future order path | same |
| Dependency audit | `pip-audit` runs in CI (non-blocking while pre-beta) | `.github/workflows/ci.yml` |

## Key management

- `JWT_SECRET_KEY` — signs access/refresh tokens. Rotate by changing it; all
  sessions invalidate (users must log in again). Never rotate during trading hours.
- `ENCRYPTION_KEY` — derives the AES key for broker tokens at rest.
  **Rotation procedure:** decrypt all `api_credentials.deriv_token_encrypted`
  values with old key → re-encrypt with new key inside one transaction. A helper
  CLI will be added with the billing phase; until then do it via a script review
  request.
- Both keys come from environment only. Defaults are rejected in production.

## Deriv token hygiene

1. Users provide PATs scoped minimally (read first; trade only when execution ships).
2. Tokens are encrypted before touching the database; plaintext never logged
   (scrubber enforces `pat_` redaction as backstop).
3. Compromise response: revoke the token in the user's Deriv dashboard, delete
   the `api_credentials` row, issue new token.

## Incident response (quick steps)

1. Kill switch: set user's `is_active=false` → all auth fails immediately.
2. Global stop: shut down gateway process; EA heartbeats put terminals into protective-only mode within 60s (Commandment II holds offline).
3. Rotate `JWT_SECRET_KEY` to invalidate every issued token.
4. Inspect `audit_log` (actor/action/created_at indexed) for the blast radius.
5. Rotate `ENCRYPTION_KEY` only if DB access is suspected (use procedure above).

## Known limitations (pre-beta)

- Rate limiter, login guard and token registry are **in-memory**: restart clears
  them, and multi-process deployments need the Redis backend (planned with the
  Docker phase). Acceptable for single-user local dev; NOT for prod scale-out.
- Refresh-family registry is in-memory too — restart logs everyone out (safe
  failure mode).
- Email verification / MFA not yet implemented (roadmap Phase 4).
