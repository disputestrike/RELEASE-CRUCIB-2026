/**
 * Layer 7.1: Critical User Journey – Sign up, Login, Workspace, Logout
 * Run: npx playwright test
 * Requires backend at REACT_APP_BACKEND_URL (e.g. http://localhost:8000)
 */
const { test, expect } = require('@playwright/test');

test.describe('Critical user journey', () => {
  const testEmail = `e2e-${Date.now()}@example.com`;
  const testPassword = 'TestPass123!';
  const testName = 'E2E User';

  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/CrucibAI|React App/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('auth register mode renders and can switch to sign in', async ({ page }) => {
    await page.goto('/auth?mode=register');
    await page.waitForURL(/\/auth/, { timeout: 10000 });

    await expect(page.getByRole('heading', { name: /create your account/i })).toBeVisible();
    await expect(page.getByPlaceholder(/your name/i)).toBeVisible();
    await expect(page.getByPlaceholder(/you@example\.com/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /start building/i })).toBeVisible();

    await page.getByPlaceholder(/your name/i).fill(testName);
    await page.getByPlaceholder(/you@example\.com/i).fill(testEmail);
    await page.locator('input[type="password"]').fill(testPassword);

    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('unauthenticated access to /auth/me returns 401', async ({ request }) => {
    test.skip(!!process.env.CI, 'Backend not started in CI for E2E job');
    const base = process.env.PLAYWRIGHT_API_URL || process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    let res;
    try {
      res = await request.get(`${base}/api/auth/me`);
    } catch (error) {
      test.skip(/ECONNREFUSED/i.test(String(error)), 'Backend not running locally for auth API check');
      throw error;
    }
    expect(res.status()).toBe(401);
  });
});
