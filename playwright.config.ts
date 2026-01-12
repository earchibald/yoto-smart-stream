import { defineConfig } from '@playwright/test';
import { execSync } from 'node:child_process';
import path from 'node:path';

function resolveBaseURL(): string {
  const envName = process.env.RAILWAY_ENV || 'develop';
  const override = process.env.BASE_URL;
  if (override) return override;
  try {
    const script = path.resolve(__dirname, 'scripts/resolve_base_url.py');
    const out = execSync(`python3 ${script} --env ${envName}`, {
      stdio: ['ignore', 'pipe', 'ignore']
    }).toString().trim();
    if (!out) throw new Error('Empty resolver output');
    return out;
  } catch (err) {
    // Fallback to localhost for local dev
    return 'http://localhost:8000';
  }
}

const baseURL = resolveBaseURL();

export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    trace: 'on-first-retry'
  },
  reporter: [['list']]
});
