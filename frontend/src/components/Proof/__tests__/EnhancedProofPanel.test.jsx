/**
 * EnhancedProofPanel.test.jsx
 *
 * Tests for the product-layer upgrade proof panel component.
 * Covers: pass/fail states, what-if results, repair attempts, optional fields,
 * preview URL, repair/replay button visibility, and button interactions.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// --- Mocks -------------------------------------------------------------------

jest.mock('../../EnhancedProofPanel.css', () => ({}));
jest.mock('../../../authContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));
jest.mock('../../../apiBase', () => ({ API_BASE: 'https://api.test.com' }));

// --- Helpers -----------------------------------------------------------------

const createProof = (overrides = {}) => ({
  job_id: "test-job-123",
  project_id: "proj-1",
  user_intent: "Build a dashboard",
  selected_stack: {
    frontend: { framework: "react", library: "vite" },
    backend: { language: "python", framework: "fastapi" },
    database: null,
    product_type: "SaaS Dashboard",
    reasoning: "SaaS dashboard detected",
    explicit_language: null,
  },
  confidence: {
    stack_key: "python_fastapi",
    score: 0.95,
    tier: "production",
    warnings: [],
  },
  agents_used: [
    "BuilderAgent",
    "FrontendAgent",
    "BackendAgent",
    "RuntimeValidator",
    "RuntimeRepairGate",
    "WhatIfSimulator",
  ],
  generated_files: {
    count: 12,
    tree: [
      "backend/main.py",
      "backend/models.py",
      "frontend/src/App.jsx",
      "package.json",
      "requirements.txt",
    ],
    total_bytes: 45000,
  },
  validation: {
    overall_passed: true,
    failed_stage: null,
    stages: {
      syntax: { passed: true, duration_ms: 120, errors: [] },
      build: { passed: true, duration_ms: 5000, errors: [] },
      runtime: { passed: true, duration_ms: 3000, errors: [] },
      integration: { passed: true, duration_ms: 2000, errors: [] },
    },
    warnings: [],
    errors: [],
    total_duration_ms: 10320,
  },
  repair_attempts: [],
  what_if_results: [],
  deployment: {
    preview_url: null,
    deploy_url: null,
    readiness: {
      frontend_builds: true,
      backend_starts: true,
      health_responds: true,
      api_responds: true,
      not_stub_code: true,
    },
  },
  final_status: "pass",
  failure_reason: null,
  explanations: {},
  build_commands: ["pip install -r requirements.txt", "python main.py"],
  test_results: null,
  timestamp: "2026-05-01T00:00:00Z",
  duration_ms: 15000,
  readiness_checks: {},
  ...overrides,
});

/**
 * Helper: render the panel with default callbacks and switch to a specific tab.
 */
function renderPanel(proof, overrides = {}) {
  const onRepair = jest.fn();
  const onReplay = jest.fn();
  const openWorkspacePath = jest.fn();
  const defaultProps = {
    proof,
    jobId: proof?.job_id || 'test-job-123',
    jobStatus: overrides.jobStatus || 'completed',
    openWorkspacePath,
    onRepair,
    onReplay,
  };

  const result = render(
    // Wrap in a Fragment since the component uses useAuth which is mocked
    React.createElement(require('../EnhancedProofPanel').default, {
      ...defaultProps,
      ...overrides,
    }),
  );

  return { onRepair, onReplay, openWorkspacePath, ...result };
}

// --- Tests -------------------------------------------------------------------

describe('EnhancedProofPanel — product-layer upgrade', () => {
  // -------------------------------------------------------------------------
  // 1. Renders pass state correctly
  // -------------------------------------------------------------------------
  test('renders pass state correctly', () => {
    const proof = createProof({ final_status: 'pass' });
    renderPanel(proof);

    // Status badge should show "Pass"
    expect(screen.getByText('Pass')).toBeInTheDocument();

    // Confidence score displayed (95%)
    expect(screen.getByText(/95%/)).toBeInTheDocument();
    expect(screen.getByText(/Production/)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 2. Renders fail state correctly
  // -------------------------------------------------------------------------
  test('renders fail state correctly', () => {
    const proof = createProof({
      final_status: 'fail',
      failure_reason: 'Runtime validation failed',
    });
    renderPanel(proof);

    // Status badge should show "Fail"
    expect(screen.getByText('Fail')).toBeInTheDocument();

    // Failure reason should be rendered in the overview
    expect(screen.getByText(/Runtime validation failed/)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 3. What-If results render correctly
  // -------------------------------------------------------------------------
  test('what-if results render correctly', () => {
    const proof = createProof({
      what_if_results: [
        {
          scenario: 'Database connection timeout',
          risk: 'high',
          result: 'App becomes unresponsive after 30s',
          recommended_fix: 'Add connection pooling with retries',
          auto_fix_available: true,
        },
        {
          scenario: 'Memory leak under load',
          risk: 'low',
          result: 'App handles 1000 concurrent users without issue',
          recommended_fix: null,
          auto_fix_available: false,
        },
      ],
    });
    renderPanel(proof);

    // Click on the What-If tab to show its content
    const whatIfTab = screen.getByRole('tab', { name: /What-If/i });
    userEvent.click(whatIfTab);

    // Both scenarios should be rendered
    expect(screen.getByText('Database connection timeout')).toBeInTheDocument();
    expect(screen.getByText('Memory leak under load')).toBeInTheDocument();

    // Risk badges
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toBeInTheDocument();

    // Fix text for high-risk scenario
    expect(screen.getByText('Add connection pooling with retries')).toBeInTheDocument();

    // Auto-fix label
    expect(screen.getByText('Auto-fix available')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 4. Repair attempts render correctly
  // -------------------------------------------------------------------------
  test('repair attempts render correctly', () => {
    const proof = createProof({
      repair_attempts: [
        {
          attempt: 1,
          error_type: 'syntax',
          error_log: 'ModuleNotFoundError: No module named flask',
          agent_used: 'SyntaxRepairAgent',
          files_changed: ['backend/requirements.txt'],
          result: 'pass',
        },
        {
          attempt: 2,
          error_type: 'runtime',
          error_log: 'TypeError: Cannot read properties of undefined',
          agent_used: 'RuntimeRepairAgent',
          files_changed: ['backend/main.py', 'frontend/src/App.jsx'],
          result: 'pass',
        },
      ],
    });
    renderPanel(proof);

    // Click the Repairs tab
    const repairsTab = screen.getByRole('tab', { name: /Repairs/i });
    userEvent.click(repairsTab);

    // Should show 2 repair attempts
    expect(screen.getByText(/2 repair attempts/)).toBeInTheDocument();

    // Agent names should be visible
    expect(screen.getByText('SyntaxRepairAgent')).toBeInTheDocument();
    expect(screen.getByText('RuntimeRepairAgent')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 5. Missing optional fields do not crash UI
  // -------------------------------------------------------------------------
  test('missing optional fields do not crash UI', () => {
    // Minimal proof — just job_id and final_status
    const proof = {
      job_id: 'minimal-job-456',
      final_status: 'pass',
    };
    expect(() => renderPanel(proof)).not.toThrow();

    // "Not available yet." should appear for missing data
    const notAvailable = screen.getAllByText(/Not available yet/);
    expect(notAvailable.length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // 6. Preview URL renders if present
  // -------------------------------------------------------------------------
  test('preview URL renders if present', () => {
    const proof = createProof({
      deployment: {
        ...createProof().deployment,
        preview_url: 'https://example.com',
      },
    });
    renderPanel(proof);

    // Click the Runtime tab
    const runtimeTab = screen.getByRole('tab', { name: /Runtime/i });
    userEvent.click(runtimeTab);

    // Preview link should be rendered
    const link = screen.getByRole('link', { name: /https:\/\/example\.com/ });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', 'https://example.com');
  });

  // -------------------------------------------------------------------------
  // 7. Repair From Proof button appears only on failed/risky builds
  // -------------------------------------------------------------------------
  describe('Repair From Proof button visibility', () => {
    test('shows Repair From Proof button on failed build', () => {
      const proof = createProof({
        final_status: 'fail',
        failure_reason: 'Build stage failed',
      });
      const { onRepair } = renderPanel(proof);

      expect(screen.getByText(/Repair From Proof/i)).toBeInTheDocument();
    });

    test('hides Repair From Proof button on clean pass build', () => {
      const proof = createProof({
        final_status: 'pass',
        what_if_results: [],
      });
      renderPanel(proof);

      expect(screen.queryByText(/Repair From Proof/i)).not.toBeInTheDocument();
    });

    test('shows Repair From Proof button when what-if has high-risk scenario', () => {
      const proof = createProof({
        final_status: 'pass',
        what_if_results: [
          {
            scenario: 'Critical failure scenario',
            risk: 'high',
            result: 'Data loss potential',
            recommended_fix: 'Add validation layer',
            auto_fix_available: false,
          },
        ],
      });
      renderPanel(proof);

      expect(screen.getByText(/Repair From Proof/i)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 8. Replay Build button does not crash when clicked
  // -------------------------------------------------------------------------
  test('Replay Build button does not crash when clicked', () => {
    const proof = createProof();
    const { onReplay } = renderPanel(proof, { jobStatus: 'completed' });

    // The replay button should exist and be enabled (not disabled) since job is completed
    const replayBtn = screen.getByText(/Replay Build/i);
    expect(replayBtn).toBeInTheDocument();
    expect(replayBtn).not.toBeDisabled();

    // Click should not throw
    expect(() => userEvent.click(replayBtn)).not.toThrow();
  });
});
