import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import WorkspaceSystemsPanel from './WorkspaceSystemsPanel';

jest.mock('axios');
jest.mock('../../apiBase', () => ({ API_BASE: '/api' }));
jest.mock('../TerminalAgent', () => () => <div data-testid="terminal-agent-stub">terminal</div>);

const mockedAxios = axios;

describe('WorkspaceSystemsPanel callers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedAxios.get.mockImplementation((url) => {
      if (String(url).includes('/skills')) {
        return Promise.resolve({ data: { active_skill_ids: ['build', 'test'] } });
      }
      return Promise.resolve({ data: {} });
    });
    mockedAxios.post.mockResolvedValue({ data: {} });
  });

  test('calls spawn simulate endpoint from scenario action', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        recommendation: 'Proceed with reliability-first patch',
        consensus_reached: true,
        updates: [{ step: 1 }],
      },
    });

    render(
      <WorkspaceSystemsPanel
        jobId="job-1"
        projectId="project-1"
        token="token-123"
        events={[]}
        proof={{ quality_score: 80, trust_score: 75, total_proof_items: 12 }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /run simulation/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/spawn/simulate',
        expect.objectContaining({ jobId: 'job-1' }),
        expect.any(Object),
      );
      expect(screen.getByText(/proceed with reliability-first patch/i)).toBeInTheDocument();
    });
  });

  test('calls mobile build queue endpoint', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: { job_id: 'mobile-1', status: 'queued', platform: 'ios' },
    });

    render(
      <WorkspaceSystemsPanel
        jobId="job-1"
        projectId="project-1"
        token="token-123"
        events={[]}
        proof={{ quality_score: 80, trust_score: 75, total_proof_items: 12 }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /queue mobile build/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/mobile/build',
        expect.objectContaining({ project_id: 'project-1', platform: 'ios' }),
        expect.any(Object),
      );
      expect(screen.getByText('mobile-1')).toBeInTheDocument();
    });
  });

  test('calls worktree create endpoint', async () => {
    mockedAxios.post.mockResolvedValueOnce({ data: { id: 'wt-test', status: 'created' } });

    render(
      <WorkspaceSystemsPanel
        jobId="job-1"
        projectId="project-1"
        token="token-123"
        events={[]}
        proof={{ quality_score: 80, trust_score: 75, total_proof_items: 12 }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /^create$/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/worktrees/create',
        expect.objectContaining({ id: expect.any(String) }),
        expect.any(Object),
      );
      expect(screen.getByText(/last action/i)).toBeInTheDocument();
    });
  });

  test('calls worktree merge and delete endpoints', async () => {
    mockedAxios.post
      .mockResolvedValueOnce({ data: { id: 'wt-test', status: 'merged' } })
      .mockResolvedValueOnce({ data: { id: 'wt-test', status: 'deleted' } });

    render(
      <WorkspaceSystemsPanel
        jobId="job-1"
        projectId="project-1"
        token="token-123"
        events={[]}
        proof={{ quality_score: 80, trust_score: 75, total_proof_items: 12 }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /^merge$/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/worktrees/merge',
        expect.objectContaining({ id: expect.any(String), jobId: 'job-1' }),
        expect.any(Object),
      );
    });

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/worktrees/delete',
        expect.objectContaining({ id: expect.any(String) }),
        expect.any(Object),
      );
    });
  });

  test('calls mobile helper endpoints for qr and checklist', async () => {
    mockedAxios.get.mockImplementation((url) => {
      const path = String(url);
      if (path.includes('/skills')) {
        return Promise.resolve({ data: { active_skill_ids: ['build', 'test'] } });
      }
      if (path.includes('/projects/project-1/mobile/qr')) {
        return Promise.resolve({ data: { qr_code: 'data:image/png;base64,AAA', expo_url: 'exp://preview' } });
      }
      if (path.includes('/projects/project-1/mobile/store-checklist')) {
        return Promise.resolve({
          data: {
            sections: [
              { title: 'Submission', items: [{ id: '1' }] },
              { title: 'Review', items: [{ id: '2' }] },
            ],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <WorkspaceSystemsPanel
        jobId="job-1"
        projectId="project-1"
        token="token-123"
        events={[]}
        proof={{ quality_score: 80, trust_score: 75, total_proof_items: 12 }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /load mobile tools/i }));

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/projects/project-1/mobile/qr',
        expect.any(Object),
      );
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/projects/project-1/mobile/store-checklist',
        expect.any(Object),
      );
      expect(screen.getByText(/expo preview ready/i)).toBeInTheDocument();
      expect(screen.getByText(/submission/i)).toBeInTheDocument();
    });
  });
});
