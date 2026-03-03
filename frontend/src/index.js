import "./resize-observer-patch";
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

// Global error handler: suppress cssRules errors that don't affect rendering
window.addEventListener('error', (event) => {
  if (event.message && event.message.includes('cssRules')) {
    console.warn('CSS manipulation warning (suppressed):', event.message);
    event.preventDefault();
  }
});

// Suppress unhandled promise rejections from CSS-related issues
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason && event.reason.toString && event.reason.toString().includes('cssRules')) {
    console.warn('CSS promise rejection (suppressed):', event.reason);
    event.preventDefault();
  }
});

class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    // Suppress cssRules errors - they don't prevent rendering
    if (error && error.message && error.message.includes('cssRules')) {
      console.warn('CSS error suppressed:', error.message);
      return { hasError: false }; // Don't show error boundary for CSS issues
    }
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, fontFamily: "sans-serif", background: "#1A1A1A", color: "#fff", minHeight: "100vh" }}>
          <h1 style={{ color: "#fff" }}>Something went wrong</h1>
          <pre style={{ overflow: "auto", fontSize: 12, color: "#ccc" }}>{this.state.error?.toString?.()}</pre>
          <p><a href="/" style={{ color: "#808080" }}>Reload</a></p>
        </div>
      );
    }
    return this.props.children;
  }
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
