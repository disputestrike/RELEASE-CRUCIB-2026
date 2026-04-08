import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main style={{ padding: 24, color: '#e2e8f0', background: '#0f172a', minHeight: '100vh' }}>
          <h1>Something needs attention</h1>
          <p>The preview caught a recoverable UI error. Adjust the component and try again.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
