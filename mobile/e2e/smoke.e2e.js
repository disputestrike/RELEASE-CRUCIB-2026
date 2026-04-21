/* CF26 mobile smoke — skipped unless DETOX_E2E=1 */
const describeIf = (cond) => (cond ? describe : describe.skip);

describeIf(process.env.DETOX_E2E === '1')('CrucibAI mobile smoke', () => {
  // eslint-disable-next-line no-undef
  beforeAll(async () => { await device.launchApp({ newInstance: true }); });

  it('shows the login screen', async () => {
    // eslint-disable-next-line no-undef
    await expect(element(by.id('login-screen'))).toBeVisible();
  });

  it('can reach onboarding role picker', async () => {
    // eslint-disable-next-line no-undef
    await element(by.id('start-onboarding')).tap();
    // eslint-disable-next-line no-undef
    await expect(element(by.id('onboarding-developer'))).toBeVisible();
    // eslint-disable-next-line no-undef
    await expect(element(by.id('onboarding-simple'))).toBeVisible();
  });
});

if (process.env.DETOX_E2E !== '1') {
  test('mobile smoke is skipped in offline/CI environment', () => {
    expect(true).toBe(true);
  });
}
