import { Component } from 'react';

/**
 * ErrorBoundaryRoute — CF26
 * Wraps routes to catch render errors and show a graceful fallback
 * instead of crashing the whole SPA.
 */
export default class ErrorBoundaryRoute extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    if (typeof window !== 'undefined' && window.console) {
      console.error('[ErrorBoundaryRoute]', error, info);
    }
    try {
      const payload = { message: String(error?.message || error), stack: info?.componentStack };
      fetch('/api/client-errors', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).catch(() => {});
    } catch {}
  }
  reload = () => {
    this.setState({ hasError: false, error: null });
    if (typeof window !== 'undefined') window.location.reload();
  };
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 48, textAlign: 'center', fontFamily: '-apple-system, system-ui, sans-serif' }}>
          <div style={{ fontSize: 22, fontWeight: 600, marginBottom: 8, color: '#1a1a1a' }}>Something went wrong.</div>
          <div style={{ fontSize: 14, color: '#71717a', marginBottom: 20 }}>
            {this.state.error?.message || 'Unexpected error rendering this page.'}
          </div>
          <button
            type="button"
            onClick={this.reload}
            style={{ padding: '10px 20px', borderRadius: 10, background: '#1a1a1a', color: '#fafafa', border: 0, fontWeight: 600, cursor: 'pointer' }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
