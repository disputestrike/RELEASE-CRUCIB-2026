/**
 * Fortune 100: AdminDashboard component tests.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminDashboard from '../AdminDashboard';

const mockUseAuth = jest.fn();
jest.mock('../../authContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockGet = jest.fn();
jest.mock('axios', () => ({
  get: (...args) => mockGet(...args),
}));

describe('AdminDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: 'mock-token' });
  });

  it('renders loading spinner initially', () => {
    mockGet.mockImplementation(() => new Promise(() => {}));
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    );
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders Admin Dashboard when data loads', async () => {
    mockGet.mockResolvedValue({
      data: {
        total_users: 150,
        signups_today: 3,
        signups_week: 12,
        referral_count: 5,
        projects_today: 2,
        revenue_today: 99,
        revenue_week: 299,
        revenue_month: 899,
        fraud_flags_count: 0,
        system_health: 'ok',
      },
    });
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });
  });

  it('displays statistics when data loads', async () => {
    mockGet.mockResolvedValue({
      data: {
        total_users: 42,
        signups_today: 1,
        signups_week: 5,
        referral_count: 0,
        projects_today: 0,
        revenue_today: 0,
        revenue_week: 0,
        revenue_month: 0,
        fraud_flags_count: 0,
        system_health: 'ok',
      },
    });
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });

  it('displays error when API fails', async () => {
    mockGet.mockRejectedValue(new Error('Forbidden'));
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/Forbidden/)).toBeInTheDocument();
    });
  });
});
