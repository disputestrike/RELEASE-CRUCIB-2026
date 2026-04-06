import { specGapCopy, normalizePlanBuildTarget } from './planApprovalCopy';

describe('planApprovalCopy', () => {
  test('normalizePlanBuildTarget defaults', () => {
    expect(normalizePlanBuildTarget(null)).toBe('vite_react');
    expect(normalizePlanBuildTarget('')).toBe('vite_react');
    expect(normalizePlanBuildTarget('api-backend')).toBe('api_backend');
  });

  test('vite_react mentions Vite and FastAPI', () => {
    const { bounded, targetDetail } = specGapCopy('vite_react', { label: 'Full-stack web (Vite + React)' });
    expect(bounded).toMatch(/bounded DAG/i);
    expect(targetDetail).toMatch(/Vite \+ React/);
    expect(targetDetail).toMatch(/FastAPI/);
  });

  test('api_backend stresses API sketch not Vite-first scaffold', () => {
    const { targetDetail } = specGapCopy('api_backend', { label: 'API & backend-first' });
    expect(targetDetail).toMatch(/Python API routes/);
    expect(targetDetail).not.toMatch(/^For .*Vite \+ React/);
  });

  test('next_app_router mentions next-app-stub', () => {
    const { targetDetail } = specGapCopy('next_app_router', null);
    expect(targetDetail).toMatch(/next-app-stub/);
  });
});
