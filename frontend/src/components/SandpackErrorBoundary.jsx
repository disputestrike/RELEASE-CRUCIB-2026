import { useEffect, useRef, useState, useCallback } from 'react';
import { useSandpack } from '@codesandbox/sandpack-react';
import { AlertTriangle, RefreshCw, Check } from 'lucide-react';

/**
 * SandpackErrorBoundary — Auto-detects Sandpack runtime errors and triggers auto-fix.
 * 
 * Sits inside SandpackProvider and watches for errors.
 * When an error is detected:
 * 1. Logs the error
 * 2. Waits 2 seconds (debounce)
 * 3. Calls onAutoFix with the error message
 * 4. Retries up to 3 times
 * 
 * This is the "error correction loop" that closes the gap with Manus/Cursor.
 */
const SandpackErrorBoundary = ({
  onAutoFix,
  onError,
  maxRetries = 3,
  autoFixEnabled = true,
}) => {
  const { sandpack } = useSandpack();
  const [errorState, setErrorState] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isFixing, setIsFixing] = useState(false);
  const [lastFixedError, setLastFixedError] = useState(null);
  const debounceRef = useRef(null);
  const lastErrorRef = useRef(null);

  const handleError = useCallback((error) => {
    // Avoid duplicate errors
    const errorKey = typeof error === 'string' ? error : error?.message || '';
    if (errorKey === lastErrorRef.current) return;
    lastErrorRef.current = errorKey;

    setErrorState({
      message: errorKey,
      timestamp: Date.now(),
    });

    // Notify parent
    if (onError) onError(errorKey);

    // Auto-fix with debounce
    if (autoFixEnabled && retryCount < maxRetries && onAutoFix) {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        setIsFixing(true);
        try {
          await onAutoFix(errorKey);
          setRetryCount(prev => prev + 1);
          setLastFixedError(errorKey);
        } catch (e) {
          // Fix failed
        } finally {
          setIsFixing(false);
        }
      }, 2000); // 2 second debounce
    }
  }, [autoFixEnabled, maxRetries, onAutoFix, onError, retryCount]);

  // Watch Sandpack status for errors
  useEffect(() => {
    if (sandpack.status === 'idle') {
      // Check for bundler errors
      const errors = sandpack.error;
      if (errors) {
        handleError(errors.message || String(errors));
      }
    }
  }, [sandpack.status, sandpack.error, handleError]);

  // Reset retry count when files change (user made a new edit)
  useEffect(() => {
    setRetryCount(0);
    lastErrorRef.current = null;
    setErrorState(null);
  }, [sandpack.files]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Don't render anything if no error
  if (!errorState && !isFixing) return null;

  return (
    <div className="sandpack-error-boundary">
      {isFixing ? (
        <div className="error-boundary-fixing">
          <RefreshCw size={14} className="animate-spin" />
          <span>Auto-fixing error (attempt {retryCount + 1}/{maxRetries})...</span>
        </div>
      ) : errorState ? (
        <div className="error-boundary-error">
          <AlertTriangle size={14} />
          <span className="error-boundary-message">{errorState.message?.substring(0, 100)}</span>
          {retryCount >= maxRetries ? (
            <span className="error-boundary-exhausted">Max retries reached</span>
          ) : (
            <button
              className="error-boundary-retry"
              onClick={() => {
                setRetryCount(0);
                handleError(errorState.message);
              }}
            >
              Retry
            </button>
          )}
        </div>
      ) : lastFixedError ? (
        <div className="error-boundary-fixed">
          <Check size={14} />
          <span>Error auto-fixed</span>
        </div>
      ) : null}
    </div>
  );
};

export default SandpackErrorBoundary;
