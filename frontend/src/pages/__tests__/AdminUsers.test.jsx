/**
 * Fortune 100: AdminUsers component tests.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminUsers from '../AdminUsers';

const mockUseAuth = jest.fn();
jest.mock('../../App', () => ({
  useAuth: () => mockUseAuth(),
  API: 'http://test/api',
}));

const mockGet = jest.fn();
jest.mock('axios', () => ({
  get: (...args) => mockGet(...args),
}));

describe('AdminUsers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: 'mock-token' });
  });

  it('renders User management heading', async () => {
    mockGet.mockResolvedValue({ data: { users: [] } });
    render(
      <MemoryRouter>
        <AdminUsers />
      </MemoryRouter>
    );
    expect(screen.getByText('User management')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/No users match the filters/)).toBeInTheDocument();
    });
  });

  it('displays users when data loads', async () => {
    mockGet.mockResolvedValue({
      data: {
        users: [
          { id: 'u1', email: 'u1@test.com', plan: 'free', credit_balance: 50, created_at: '2026-01-01' },
          { id: 'u2', email: 'u2@test.com', plan: 'pro', credit_balance: 100, created_at: '2026-01-02' },
        ],
      },
    });
    render(
      <MemoryRouter>
        <AdminUsers />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('u1@test.com')).toBeInTheDocument();
      expect(screen.getByText('u2@test.com')).toBeInTheDocument();
    });
  });

  it('displays empty state when no users match', async () => {
    mockGet.mockResolvedValue({ data: { users: [] } });
    render(
      <MemoryRouter>
        <AdminUsers />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/No users match the filters/)).toBeInTheDocument();
    });
  });

  it('displays error when API fails', async () => {
    mockGet.mockRejectedValue({ response: { data: { detail: 'Admin access required' } } });
    render(
      <MemoryRouter>
        <AdminUsers />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/Admin access required/)).toBeInTheDocument();
    });
  });
});
