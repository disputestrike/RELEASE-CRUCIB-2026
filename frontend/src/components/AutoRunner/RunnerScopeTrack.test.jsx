import React from 'react';
import { render, screen } from '@testing-library/react';
import RunnerScopeTrack from './RunnerScopeTrack';

describe('RunnerScopeTrack', () => {
  test('shows run-to-completion copy and target detail for vite_react', () => {
    render(
      <RunnerScopeTrack
        buildTargetId="vite_react"
        buildTargetMeta={{ label: 'Full-stack web (Vite + React)' }}
      />,
    );
    expect(screen.getByText(/runs to completion/i)).toBeInTheDocument();
    expect(screen.getByText(/Vite \+ React/)).toBeInTheDocument();
    expect(screen.getByText(/Approve & Run is never blocked/i)).toBeInTheDocument();
  });

  test('shows infra follow-up and SMTP notes', () => {
    render(<RunnerScopeTrack buildTargetId="vite_react" buildTargetMeta={null} />);
    expect(screen.getByText(/Terraform/i)).toBeInTheDocument();
    expect(screen.getByText(/SMTP_\*/i)).toBeInTheDocument();
  });
});
