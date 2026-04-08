import React from 'react';
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CRMPage from './pages/CRMPage';
import QuotesPage from './pages/QuotesPage';
import ProjectsPage from './pages/ProjectsPage';
import PolicyPage from './pages/PolicyPage';
import AuditPage from './pages/AuditPage';
import AnalyticsPage from './pages/AnalyticsPage';
import TeamPage from './pages/TeamPage';

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<ShellLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/crm" element={<CRMPage />} />
              <Route path="/quotes" element={<QuotesPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/policy" element={<PolicyPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/team" element={<TeamPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
