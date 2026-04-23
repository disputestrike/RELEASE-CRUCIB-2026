import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import WorkspaceLeftRail from './WorkspaceLeftRail';

jest.mock('./WorkspaceFileTree', () => function MockWorkspaceFileTree(props) {
  return (
    <div>
      <div data-testid="mock-tree">tree</div>
      <button type="button" onClick={() => props.onSelectPath('/src/App.jsx')}>pick-file</button>
    </div>
  );
});

function buildProps(overrides = {}) {
  return {
    leftCollapsed: false,
    leftWidth: 280,
    activePane: 'preview',
    wsPaths: ['/src/App.jsx'],
    activeWsPath: '/src/App.jsx',
    treeRevealTick: 0,
    wsListLoading: false,
    onToggleCollapsed: jest.fn(),
    onSelectPane: jest.fn(),
    onSelectWorkspacePath: jest.fn(),
    ...overrides,
  };
}

describe('WorkspaceLeftRail', () => {
  test('renders navigation buttons and forwards pane selections', () => {
    const props = buildProps();
    render(<WorkspaceLeftRail {...props} />);

    fireEvent.click(screen.getByRole('button', { name: /timeline/i }));
    fireEvent.click(screen.getByRole('button', { name: /proof/i }));

    expect(props.onSelectPane).toHaveBeenCalledWith('timeline');
    expect(props.onSelectPane).toHaveBeenCalledWith('proof');
  });

  test('toggles collapsed state and hides tree content when collapsed', () => {
    const expanded = buildProps();
    const { rerender } = render(<WorkspaceLeftRail {...expanded} />);

    expect(screen.getByTestId('mock-tree')).toBeInTheDocument();
    fireEvent.click(document.querySelector('.arp-rail-toggle'));
    expect(expanded.onToggleCollapsed).toHaveBeenCalled();

    const collapsed = buildProps({ leftCollapsed: true });
    rerender(<WorkspaceLeftRail {...collapsed} />);
    expect(screen.queryByTestId('mock-tree')).not.toBeInTheDocument();
  });

  test('forwards workspace file selections', () => {
    const props = buildProps();
    render(<WorkspaceLeftRail {...props} />);

    fireEvent.click(screen.getByRole('button', { name: /pick-file/i }));
    expect(props.onSelectWorkspacePath).toHaveBeenCalledWith('/src/App.jsx');
  });
});
