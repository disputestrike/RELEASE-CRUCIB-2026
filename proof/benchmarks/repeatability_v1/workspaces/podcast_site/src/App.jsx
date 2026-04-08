import React from 'react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
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
              <Route path="/team" element={<TeamPage />} />
              {/* CRUCIB_APP_ROUTE_ANCHOR */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
