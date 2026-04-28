import {
  compactUrlLabel,
  realDeployUrlForCompletion,
  realPreviewUrlForJob,
} from './buildCompletionTargets';

describe('build completion targets', () => {
  test('does not fabricate a preview route from job id alone', () => {
    expect(realPreviewUrlForJob({ id: 'job_123' })).toBe(null);
  });

  test('uses real preview target fields in precedence order', () => {
    expect(
      realPreviewUrlForJob({
        dev_server_url: 'https://dev.example.com',
        preview_url: 'https://preview.example.com',
      }),
    ).toBe('https://dev.example.com');
    expect(realPreviewUrlForJob({ preview_url: 'https://preview.example.com' })).toBe(
      'https://preview.example.com',
    );
  });

  test('does not fabricate a deploy route from job id alone', () => {
    expect(realDeployUrlForCompletion({ job: { id: 'job_123' }, proof: {} })).toBe(null);
  });

  test('uses deploy response before proof and job deploy targets', () => {
    expect(
      realDeployUrlForCompletion({
        job: { deploy_url: 'https://job.example.com' },
        proof: {
          bundle: {
            deploy: [{ payload: { deploy_url: 'https://proof.example.com' } }],
          },
        },
        deployResult: { deploy_url: 'https://result.example.com' },
      }),
    ).toBe('https://result.example.com');
  });

  test('uses latest proof deploy payload when no deploy response exists', () => {
    expect(
      realDeployUrlForCompletion({
        proof: {
          bundle: {
            deploy: [
              { payload: { deploy_url: 'https://old.example.com' } },
              { payload: { url: 'https://new.example.com' } },
            ],
          },
        },
      }),
    ).toBe('https://new.example.com');
  });

  test('compacts http labels without changing the underlying url', () => {
    expect(compactUrlLabel('https://example.com/path')).toBe('example.com/path');
  });
});
