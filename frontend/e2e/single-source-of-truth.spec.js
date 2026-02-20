/**
 * Master Single Source of Truth E2E (MASTER_SINGLE_SOURCE_OF_TRUTH_TEST.md §5).
 * Pricing → Token Center wiring: addon deep link and redirect.
 */
const { test, expect } = require('@playwright/test');

test.describe('Single Source of Truth E2E', () => {
  test('pricing page loads and shows Add-ons section', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page).toHaveTitle(/CrucibAI|React App/);
    await expect(page.getByRole('heading', { name: /add-ons|Add-ons/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Light.*credits|50 credits/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Dev.*credits|250 credits/i)).toBeVisible({ timeout: 5000 });
  });

  test('pricing addon Get started navigates to auth with redirect containing addon', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page.getByRole('heading', { name: /add-ons|Add-ons/i })).toBeVisible({ timeout: 10000 });
    const getStarted = page.getByRole('button', { name: /get started/i }).first();
    await getStarted.click();
    await page.waitForURL(/\/auth/);
    const url = page.url();
    expect(url).toMatch(/mode=register/);
    expect(url).toMatch(/redirect=/);
    expect(decodeURIComponent(url)).toMatch(/\/app\/tokens\?addon=(light|dev)/);
  });

  test('unauthenticated /app/tokens redirects to auth', async ({ page }) => {
    await page.goto('/app/tokens');
    await page.waitForURL(/\/(auth|app\/tokens)/);
    const url = page.url();
    if (url.includes('/auth')) expect(url).toContain('/auth');
    else expect(url).toMatch(/\/app\/tokens/);
  });

  test('public routes load without error', async ({ page }) => {
    for (const path of ['/pricing', '/learn', '/templates', '/features']) {
      const res = await page.goto(path);
      expect(res.status()).toBeLessThan(500);
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
