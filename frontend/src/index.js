import "./resize-observer-patch";
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, fontFamily: "sans-serif", background: "#FAFAF8", color: "#1A1A1A", minHeight: "100vh" }}>
          <h1 style={{ color: "#cc0000" }}>Something went wrong</h1>
          <pre style={{ overflow: "auto", fontSize: 12 }}>{this.state.error?.toString?.()}</pre>
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
