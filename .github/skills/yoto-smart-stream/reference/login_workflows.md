# Login Workflows

This guide shows three ways to sign in to Yoto Smart Stream:
- UI with Playwright (drives the login form)
- API-only (HTTP client/cURL)
- Hybrid: API auth → reuse in Playwright (start authenticated)

Use `BASE_URL` resolved dynamically from Railway (don’t hardcode).

### Resolve BASE_URL via Railway
- With the included helper script (recommended):
```bash
python scripts/resolve_base_url.py --env develop
# → prints e.g. https://yoto-smart-stream-develop.up.railway.app
```
You can export it for subsequent commands:
```bash
export BASE_URL="$(python scripts/resolve_base_url.py --env develop)"
```

- Directly with Railway CLI + jq (alternative):
```bash
export BASE_URL=$(railway status --json | jq -r '.. | strings | select(test("\\.up\\.railway\\.app$")) | select(test("develop"))' | head -n1)
```

Note: The Railway MCP Quick Action “Generate Domain” in the Railway skill can also surface the live domain. Prefer develop for testing and production for release checks.

## Endpoints & Session
- POST `/api/user/login` → sets HttpOnly `session` cookie on success
- GET `/api/user/session` → `{ authenticated: boolean, username?: string }`
- POST `/api/user/logout` → clears `session` cookie

---

## 1) UI Login with Playwright

TypeScript (Playwright):
```ts
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL!;

test('login via UI', async ({ page }) => {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('#username', process.env.USERNAME || 'admin');
  await page.fill('#password', process.env.PASSWORD || 'yoto');
  await Promise.all([
    page.waitForURL(`${BASE_URL}/`),
    page.click('#login-button'), // <button type="submit" id="login-button">Sign In</button>
  ]);

  // Validate auth via session endpoint
  const resp = await page.request.get(`${BASE_URL}/api/user/session`);
  const session = await resp.json();
  expect(session.authenticated).toBe(true);
});
```

Python (Playwright):
```py
from playwright.sync_api import sync_playwright, expect
import os

BASE_URL = os.environ.get('BASE_URL')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"{BASE_URL}/login")
    page.fill('#username', os.environ.get('USERNAME', 'admin'))
    page.fill('#password', os.environ.get('PASSWORD', 'yoto'))
    page.click('#login-button')
    page.wait_for_url(f"{BASE_URL}/")

    # Validate session
    resp = page.request.get(f"{BASE_URL}/api/user/session")
    assert resp.json()["authenticated"] is True
    browser.close()
```

---

## 2) API-only Login (no browser)

cURL (persist cookies and reuse):
```bash
# Create session and save cookie jar
curl -sS -c cookies.txt -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"yoto"}' \
  "${BASE_URL}/api/user/login"

# Verify session (sends cookie jar back)
curl -sS -b cookies.txt "${BASE_URL}/api/user/session"
```

TypeScript (Node `fetch` + cookie jar via undici or axios-cookiejar):
```ts
import fetch, { RequestInit } from 'node-fetch';
import tough from 'tough-cookie';
import fetchCookie from 'fetch-cookie';

const BASE_URL = process.env.BASE_URL!;
const CookieJar = new tough.CookieJar();
const cookieFetch = fetchCookie(fetch, CookieJar);

async function login() {
  const res = await cookieFetch(`${BASE_URL}/api/user/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'yoto' }),
  } as RequestInit);
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
}

async function session() {
  const res = await cookieFetch(`${BASE_URL}/api/user/session`);
  return res.json();
}

(async () => {
  await login();
  console.log(await session()); // { authenticated: true, username: 'admin' }
})();
```

Python (requests + cookie jar):
```py
import os, requests

BASE_URL = os.environ['BASE_URL']
s = requests.Session()

r = s.post(f"{BASE_URL}/api/user/login", json={"username":"admin","password":"yoto"})
r.raise_for_status()

print(s.get(f"{BASE_URL}/api/user/session").json())
```

---

## 3) Hybrid: API Auth → Playwright Storage State

Authenticate using Playwright's APIRequestContext (or browser request), save storage state, and launch the browser already authenticated. This avoids typing credentials and speeds up tests.

TypeScript (Playwright):
```ts
import { test, expect, request, chromium } from '@playwright/test';

const BASE_URL = process.env.BASE_URL!;

test('start authenticated via storage state', async () => {
  const requestContext = await request.newContext({ baseURL: BASE_URL });
  const resp = await requestContext.post('/api/user/login', {
    data: { username: 'admin', password: 'yoto' },
  });
  expect(resp.ok()).toBeTruthy();

  // Save storage state (cookies, origins)
  await requestContext.storageState({ path: 'auth.json' });

  const browser = await chromium.launch();
  const context = await browser.newContext({ storageState: 'auth.json', baseURL: BASE_URL });
  const page = await context.newPage();

  await page.goto('/');
  // Confirm already authenticated
  const s = await page.request.get('/api/user/session');
  expect((await s.json()).authenticated).toBe(true);
  await browser.close();
});
```

Python (Playwright):
```py
from playwright.sync_api import sync_playwright
import os

BASE_URL = os.environ.get('BASE_URL')

with sync_playwright() as p:
    req = p.request.new_context(base_url=BASE_URL)
    r = req.post('/api/user/login', data={"username":"admin","password":"yoto"})
    assert r.ok
    req.storage_state(path='auth.json')

    browser = p.chromium.launch()
    context = browser.new_context(storage_state='auth.json', base_url=BASE_URL)
    page = context.new_page()
    page.goto('/')
    s = page.request.get('/api/user/session').json()
    assert s["authenticated"] is True
    browser.close()
```

---

## Tips & Troubleshooting
- Cookie name is `session` (HttpOnly). You won't read it in client JS; rely on HTTP client jars or Playwright storage state.
- Ensure the correct base domain (develop vs production). Session cookies are domain-scoped.
- UI login redirects to `/` on success; guard tests with `page.waitForURL(BASE_URL + '/')`.
- For CI, prefer the hybrid flow to avoid flakiness and speed up runs.
