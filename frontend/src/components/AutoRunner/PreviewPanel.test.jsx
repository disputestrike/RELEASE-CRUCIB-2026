/**
 * PreviewPanel: remote iframe vs Sandpack. Sandpack is mocked so Jest does not load the full bundler.
 * @jest-environment jsdom
 */
import React from 'react';
import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';

jest.mock('../SandpackErrorBoundary.css', () => ({}));
jest.mock('./PreviewPanel.css', () => ({}));

import PreviewPanel from './PreviewPanel';

jest.mock('@codesandbox/sandpack-react', () => ({
  SandpackProvider: ({ children }) => <div data-testid="sandpack-provider">{children}</div>,
  SandpackPreview: () => <div data-testid="sandpack-preview" />,
}));

jest.mock('../SandpackErrorBoundary', () => function MockBoundary({ children }) {
  return <div data-testid="sandpack-error-boundary">{children}</div>;
});

describe('PreviewPanel', () => {
  test('renders Sandpack when status ready, no previewUrl, and sandpackFiles non-empty', () => {
    const sandpackFiles = { '/src/App.jsx': { code: 'export default function App(){return null}' } };
    const sandpackDeps = { react: '^18.2.0', 'react-dom': '^18.2.0' };
    render(
      <PreviewPanel
        previewUrl={null}
        status="ready"
        sandpackFiles={sandpackFiles}
        sandpackDeps={sandpackDeps}
        filesReadyKey="t1"
      />,
    );
    expect(screen.getByTestId('sandpack-provider')).toBeInTheDocument();
    expect(screen.getByTestId('sandpack-preview')).toBeInTheDocument();
  });

  test('prefers remote iframe when previewUrl and status ready', () => {
    render(
      <PreviewPanel
        previewUrl="https://example.com/preview"
        status="ready"
        sandpackFiles={{ '/src/App.jsx': { code: 'x' } }}
        sandpackDeps={{ react: '^18.2.0' }}
        filesReadyKey="t2"
      />,
    );
    const iframe = document.querySelector('iframe.pp-preview-iframe');
    expect(iframe).toBeTruthy();
    expect(iframe.getAttribute('src')).toBe('https://example.com/preview');
    expect(screen.queryByTestId('sandpack-provider')).not.toBeInTheDocument();
  });

  test('shows ready fallback when status ready but sandpackFiles empty and no previewUrl', () => {
    render(
      <PreviewPanel previewUrl={null} status="ready" sandpackFiles={{}} sandpackDeps={{}} filesReadyKey="t3" />,
    );
    expect(screen.getByText(/Build complete! Add your UI files below|use Sync to pull generated code/i)).toBeInTheDocument();
  });

  test('shows building shimmer when status building and no sandpack yet', () => {
    const { container } = render(
      <PreviewPanel previewUrl={null} status="building" sandpackFiles={null} sandpackDeps={null} filesReadyKey="t4" />,
    );
    expect(container.querySelector('.pp-preview-building')).toBeTruthy();
    expect(screen.getByText(/Assembling your preview/i)).toBeInTheDocument();
  });

  test('shows paused banner when status blocked and sandpack present', () => {
    const sandpackFiles = { '/src/App.jsx': { code: 'export default function App(){return null}' } };
    const sandpackDeps = { react: '^18.2.0', 'react-dom': '^18.2.0' };
    render(
      <PreviewPanel
        previewUrl={null}
        status="blocked"
        sandpackFiles={sandpackFiles}
        sandpackDeps={sandpackDeps}
        filesReadyKey="t-blocked"
        blockedDetail="Type error in App.jsx"
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent(/Preview paused/i);
    expect(screen.getByText(/Type error in App.jsx/i)).toBeInTheDocument();
    expect(document.querySelector('.pp-preview-status')?.textContent).toMatch(/Paused/i);
  });

  test('shows fallback trust banner when sandpackIsFallback', () => {
    const sandpackFiles = { '/src/Foo.jsx': { code: 'export default function Foo(){return null}' } };
    const sandpackDeps = { react: '^18.2.0', 'react-dom': '^18.2.0' };
    render(
      <PreviewPanel
        previewUrl={null}
        status="ready"
        sandpackFiles={sandpackFiles}
        sandpackDeps={sandpackDeps}
        filesReadyKey="t5"
        sandpackIsFallback
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent(/Starter shell/i);
  });
});
