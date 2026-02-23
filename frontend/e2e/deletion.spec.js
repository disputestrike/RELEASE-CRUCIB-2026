/**
 * Phase 11: Deletion flows – delete project, delete account (UI presence).
 * Run: npx playwright test e2e/deletion.spec.js
 */
const { test, expect } = require('@playwright/test');

test.describe('Deletion flows', () => {
  test('Settings page shows Delete Account section', async ({ page }) => {
    await page.goto('/app/settings');
    await expect(page.locator('body')).toBeVisible();
    await expect(page.getByText(/delete account|delete your account|remove account/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('unauthenticated GET /api/projects returns 401', async ({ request }) => {
    const base = process.env.PLAYWRIGHT_API_URL || process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    const res = await request.get(`${base}/api/projects`);
    expect(res.status()).toBe(401);
  });
});
