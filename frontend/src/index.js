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
        <div style={{ padding: 24, fontFamily: "sans-serif", background: "#0a0a0a", color: "#fff", minHeight: "100vh" }}>
          <h1 style={{ color: "#f87171" }}>Something went wrong</h1>
          <pre style={{ overflow: "auto", fontSize: 12 }}>{this.state.error?.toString?.()}</pre>
          <p><a href="/" style={{ color: "#60a5fa" }}>Reload</a></p>
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
