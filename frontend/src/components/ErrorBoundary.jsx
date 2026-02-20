import React from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

/**
 * ErrorBoundary Component
 * Catches React errors and displays user-friendly error UI
 * Prevents entire app from crashing
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error caught by boundary:', error, errorInfo);
    }

    // Update state with error details
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1
    }));

    // Log to error tracking service (e.g., Sentry, LogRocket)
    this.logErrorToService(error, errorInfo);
  }

  logErrorToService = (error, errorInfo) => {
    // This would integrate with your error tracking service
    const errorData = {
      message: error.toString(),
      stack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // Send to backend (wired to same API base as rest of app)
    const apiBase = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
    try {
      fetch(`${apiBase}/errors/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorData)
      }).catch(() => {
        // Silently fail - don't crash if logging fails
      });
    } catch (e) {
      // Ignore
    }
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const isDevelopment = process.env.NODE_ENV === 'development';

      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-#f5f5f5 flex items-center justify-center p-4">
          <div className="max-w-md w-full">
            {/* Error Icon */}
            <div className="flex justify-center mb-6">
              <div className="bg-gray-100 p-4 rounded-full">
                <AlertCircle className="w-12 h-12 text-gray-600" />
              </div>
            </div>

            {/* Error Message */}
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Oops! Something went wrong
              </h1>
              <p className="text-gray-600 text-sm mb-4">
                We encountered an unexpected error. Our team has been notified.
              </p>

              {/* Error Details (Development Only) */}
              {isDevelopment && this.state.error && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4 text-left">
                  <p className="text-xs font-mono text-gray-800 break-words">
                    <strong>Error:</strong> {this.state.error.toString()}
                  </p>
                  {this.state.errorInfo && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer font-semibold text-gray-700">
                        Stack Trace
                      </summary>
                      <pre className="mt-2 text-gray-700 overflow-auto max-h-40 text-xs">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {/* Error Count Warning */}
              {this.state.errorCount > 3 && (
                <div className="bg-#f5f5f5 border border-#e0e0e0 rounded-lg p-3 mb-4">
                  <p className="text-xs text-#333333">
                    Multiple errors detected. Please try reloading the page.
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <button
                onClick={this.handleReset}
                className="w-full bg-black hover:bg-black text-[#1A1A1A] font-semibold py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>

              <button
                onClick={this.handleReload}
                className="w-full bg-gray-200 hover:bg-gray-300 text-gray-900 font-semibold py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Reload Page
              </button>

              <button
                onClick={this.handleGoHome}
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-900 font-semibold py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
              >
                <Home className="w-4 h-4" />
                Go to Home
              </button>
            </div>

            {/* Support Info */}
            <div className="mt-6 pt-6 border-t border-gray-300 text-center">
              <p className="text-xs text-gray-600 mb-2">
                Need help? Contact our support team:
              </p>
              <a
                href="mailto:support@crucibai.com"
                className="text-#000000 hover:text-#000000 text-sm font-semibold"
              >
                support@crucibai.com
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
