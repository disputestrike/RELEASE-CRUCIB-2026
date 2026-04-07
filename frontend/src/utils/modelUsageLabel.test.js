import { isDevStubModel, formatModelUsageLine } from './modelUsageLabel';

describe('modelUsageLabel', () => {
  test('detects dev-stub', () => {
    expect(isDevStubModel('dev-stub')).toBe(true);
    expect(isDevStubModel('DEV-STUB')).toBe(true);
    expect(isDevStubModel('claude-3-5-haiku')).toBe(false);
  });

  test('format avoids premium wording for stub', () => {
    expect(formatModelUsageLine('dev-stub')).toMatch(/not billed as premium/i);
    expect(formatModelUsageLine('haiku')).toMatch(/^Model: haiku$/);
  });
});
