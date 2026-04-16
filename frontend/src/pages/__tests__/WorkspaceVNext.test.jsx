import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import WorkspaceVNext from '../WorkspaceVNext';
import { useAuth } from '../../authContext';

jest.mock('../../authContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../CrucibAIWorkspace', () => function MockCrucibAIWorkspace() {
  return <div data-testid="mock-vnext-workspace">CrucibAIWorkspace</div>;
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
  });

  it('falls back to simple mode when developer mode is requested without permission', async () => {
    useAuth.mockReturnValue({ user: { workspace_mode: 'simple', internal_team: false } });

    renderAt('/app/workspace?mode=developer');

    expect(screen.getByTestId('mock-vnext-workspace')).toBeInTheDocument();
    await waitFor(() => {
      expect(localStorage.getItem('crucibai_workspace_mode')).toBe('simple');
      expect(localStorage.getItem('crucibai_ux_mode')).toBe('simple');
    });

    expect(screen.getByRole('button', { name: /developer/i })).toBeDisabled();
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
});
