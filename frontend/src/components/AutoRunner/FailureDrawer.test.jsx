import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import FailureDrawer from './FailureDrawer';

describe('FailureDrawer', () => {
  test('renders live diagnosis and repair actions instead of demo recovery text', () => {
    const onRetry = jest.fn();
    render(
      <FailureDrawer
        step={{
          step_key: 'verification.preview',
          failure_type: 'syntax_error',
          error_message: 'Prose preamble detected in src/App.jsx',
          retry_count: 2,
          diagnosis: {
            failure_class: 'prose_in_code',
            specific_file: 'src/App.jsx',
            specific_line: 1,
            explanation: 'LLM wrote conversational text into src/App.jsx.',
            repair_actions: [
              'Strip prose from src/App.jsx',
              'Re-run frontend generation with code-only output',
            ],
          },
          fix_strategy: 'strip_prose_and_regenerate_frontend',
        }}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText(/Fix strategy: strip_prose_and_regenerate_frontend/i)).toBeInTheDocument();
    expect(screen.getByText(/Strip prose from src\/App.jsx/i)).toBeInTheDocument();
    expect(screen.queryByText(/Recovered \(demo\)/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Retry Automatically/i }));
    expect(onRetry).toHaveBeenCalled();
    expect(screen.getByText(/Retry requested/i)).toBeInTheDocument();
  });
});
