import { test, expect, chromium, request as pwRequest } from '@playwright/test';

const USERNAME = process.env.USERNAME || 'admin';
const PASSWORD = process.env.PASSWORD || 'yoto';

// 1) UI login via the form using stable selectors
// - #username, #password, #login-button
// - Redirects to '/'
// - Verifies session with GET /api/user/session

test('login via UI', async ({ page, request, baseURL }) => {
  test.skip(!baseURL, 'baseURL must be resolved');
  await page.goto('/login');
  await page.fill('#username', USERNAME);
  await page.fill('#password', PASSWORD);
  await Promise.all([
    page.waitForURL((baseURL || '') + '/'),
    page.click('#login-button')
  ]);
  const resp = await request.get('/api/user/session');
  const session = await resp.json();
  expect(session.authenticated).toBe(true);
});

// 2) Hybrid: Authenticate via API, then start a context with that storage state

test('start authenticated via API + storage state', async ({ browser, request, baseURL }) => {
  test.skip(!baseURL, 'baseURL must be resolved');
  const res = await request.post('/api/user/login', {
    data: { username: USERNAME, password: PASSWORD }
  });
  expect(res.ok()).toBeTruthy();

  const storage = await request.storageState();
  const context = await browser.newContext({ storageState: storage, baseURL });
  const page = await context.newPage();
  await page.goto('/');

  const s = await page.request.get('/api/user/session');
  const data = await s.json();
  expect(data.authenticated).toBe(true);
  await context.close();
});
