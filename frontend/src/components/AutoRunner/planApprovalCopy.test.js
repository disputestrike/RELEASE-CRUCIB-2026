import {
  specGapCopy,
  normalizePlanBuildTarget,
  PIPELINE_INFRA_SCOPE_RISK,
  BEFORE_PRODUCTION_SMTP_NOTE,
} from './planApprovalCopy';

describe('planApprovalCopy', () => {
  test('normalizePlanBuildTarget defaults', () => {
    expect(normalizePlanBuildTarget(null)).toBe('vite_react');
    expect(normalizePlanBuildTarget('')).toBe('vite_react');
    expect(normalizePlanBuildTarget('api-backend')).toBe('api_backend');
  });

  test('vite_react mentions full pipeline and Vite + FastAPI', () => {
    const { runIntro, targetDetail } = specGapCopy('vite_react', { label: 'Full-stack web (Vite + React)' });
    expect(runIntro).toMatch(/runs to completion/i);
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

  test('static scope strings mention infra and SMTP without implying blocked runs', () => {
    expect(PIPELINE_INFRA_SCOPE_RISK).toMatch(/Terraform|OTel/i);
    expect(PIPELINE_INFRA_SCOPE_RISK).toMatch(/not block/i);
    expect(BEFORE_PRODUCTION_SMTP_NOTE).toMatch(/SMTP/i);
  });
});
