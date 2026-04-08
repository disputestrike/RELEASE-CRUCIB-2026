/**
 * React Hook: useExecutionTargetDetection
 * Detects optimal execution targets from user requests
 * Handles caching and confidence thresholds
 */

import { useState, useCallback, useEffect } from 'react';

const useExecutionTargetDetection = () => {
  const [targetSuggestion, setTargetSuggestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cache, setCache] = useState({});

  const detectTarget = useCallback(async (userRequest) => {
    // Check cache first
    if (cache[userRequest]) {
      setTargetSuggestion(cache[userRequest]);
      return cache[userRequest];
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/execution-target/detect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_request: userRequest,
          allow_secondary: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Detection failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Cache result
      setCache(prev => ({ ...prev, [userRequest]: data }));
      setTargetSuggestion(data);
      setLoading(false);

      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  }, [cache]);

  const clearCache = useCallback(() => {
    setCache({});
  }, []);

  // Decision helper: Should show selector or auto-confirm?
  const shouldShowSelector = useCallback((suggestion) => {
    return suggestion && suggestion.confidence < 80;
  }, []);

  // Decision helper: Should auto-confirm?
  const shouldAutoConfirm = useCallback((suggestion) => {
    return suggestion && suggestion.confidence > 90;
  }, []);

  return {
    targetSuggestion,
    loading,
    error,
    detectTarget,
    clearCache,
    shouldShowSelector,
    shouldAutoConfirm,
  };
};

export default useExecutionTargetDetection;
