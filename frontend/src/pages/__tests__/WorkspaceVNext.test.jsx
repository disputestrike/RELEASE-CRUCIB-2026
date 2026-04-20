import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import WorkspaceVNext from '../WorkspaceVNext';
import { useAuth } from '../../authContext';

jest.mock('../../authContext', () => ({
  useAuth: jest.fn(),
}));

const mockUnifiedWorkspace = jest.fn();
jest.mock('../UnifiedWorkspace', () => (props) => {
  mockUnifiedWorkspace(props);
  return <div data-testid="mock-vnext-workspace">UnifiedWorkspace</div>;
});

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/workspace" element={<WorkspaceVNext />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('WorkspaceVNext', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  afterEach(() => {
    if (global.fetch?.mockRestore) {
      global.fetch.mockRestore();
    }
  });

  it('falls back to simple mode when developer mode is requested without permission', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'simple', internal_team: false } });

    renderAt('/app/workspace?mode=developer');

    await waitFor(() => {
      expect(localStorage.getItem('crucibai_workspace_mode')).toBe('simple');
      expect(localStorage.getItem('crucibai_ux_mode')).toBe('simple');
    });

    expect(screen.getByRole('button', { name: /developer/i })).toBeDisabled();
    await waitFor(() => {
      expect(mockUnifiedWorkspace).toHaveBeenLastCalledWith(
        expect.objectContaining({ workspaceSurface: 'build' }),
      );
    });
  });

  it('keeps developer mode when user is allowed', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'developer', internal_team: false } });

    renderAt('/app/workspace?mode=developer');

    await waitFor(() => {
      expect(localStorage.getItem('crucibai_workspace_mode')).toBe('developer');
      expect(localStorage.getItem('crucibai_ux_mode')).toBe('pro');
    });

    expect(screen.queryByText(/unavailable/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /developer/i })).not.toBeDisabled();
  });

  it('uses policy mode when no query mode is provided', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'developer', internal_team: false } });

    renderAt('/app/workspace');

    await waitFor(() => {
      expect(localStorage.getItem('crucibai_workspace_mode')).toBe('developer');
      expect(localStorage.getItem('crucibai_ux_mode')).toBe('pro');
    });

    expect(screen.getByRole('button', { name: /developer/i })).not.toBeDisabled();
  });

  it('renders all canonical workspace surface tabs', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'developer', internal_team: false } });

    renderAt('/app/workspace?mode=developer');

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /build/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /inspect/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /what-if/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /deploy/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /repair/i })).toBeInTheDocument();
    });
  });

  it('defaults to build surface when an unknown surface is requested', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'simple', internal_team: false } });

    renderAt('/app/workspace?surface=unknown-surface');

    await waitFor(() => {
      expect(mockUnifiedWorkspace).toHaveBeenLastCalledWith(
        expect.objectContaining({ workspaceSurface: 'build' }),
      );
    });
  });

  it('shows runtime telemetry card when endpoint returns data in developer mode', async () => {
    useAuth.mockReturnValue({ user: { id: 'user-telemetry-1', workspace_mode: 'developer', internal_team: true } });
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        task_count: 2,
        memory_graph: { node_count: 5, edge_count: 3 },
        cost_ledger: { a: { credits: 1 }, b: { credits: 2 } },
        recent_events: [{ id: 'e1' }],
      }),
    });

    renderAt('/app/workspace');

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
      expect(screen.getByLabelText(/runtime telemetry/i)).toBeInTheDocument();
      expect(screen.getByText('Tasks')).toBeInTheDocument();
      expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1);
    });
  });
});
