# Yoto Smart Stream Skill

Practical workflows for operating and testing the Yoto Smart Stream service. This skill complements the backend and UI by documenting repeatable steps and code patterns you can copy into tests, scripts, and automation.

## Scope
- Auth & session management (Playwright UI, HTTP API, hybrid) — start here
- (Next) Players & playback controls
- (Next) Library browsing & chapter play
- (Next) MQTT event verification

## Quick Start: Login Options
Below are three reliable ways to authenticate against the live app. Choose the one that best fits your workflow.

- UI with Playwright: Drive the login form like a user (stable selectors).
- API-only: Create a session via `/api/user/login` and reuse the cookie in HTTP calls.
- Hybrid (recommended for E2E): Authenticate via API, persist storage state, launch Playwright already authenticated.

See reference/login_workflows.md for complete, copy-pasteable examples in TypeScript and Python, plus cURL.

## Prerequisites
- Base URL (e.g., https://yoto-smart-stream-develop.up.railway.app)
- Credentials (default seed in dev: admin / yoto)
- Playwright installed (if using UI/hybrid)

## Maintenance Notes
- Session cookie name: `session` (HttpOnly)
- Login endpoint: `POST /api/user/login` with JSON `{ "username": "...", "password": "..." }`
- Session check: `GET /api/user/session` → `{ authenticated: true/false, username?: string }`

When you confirm new behaviors (cookie flags, endpoints, redirects), keep this skill in sync.
