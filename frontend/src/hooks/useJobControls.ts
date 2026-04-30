import { useState, useCallback } from 'react';

export function useJobControls(jobId: string | null) {
  const [isLoading, setIsLoading] = useState(false);

  const makeRequest = useCallback(async (endpoint: string, body?: any) => {
    if (!jobId) throw new Error('No job ID');
    setIsLoading(true);
    try {
      const res = await fetch(/api/jobs/, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) throw new Error(HTTP );
      return await res.json();
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  return {
    pause: () => makeRequest('/pause'),
    resume: () => makeRequest('/resume'),
    cancel: () => makeRequest('/cancel'),
    retry: (nodeIds?: string[]) => makeRequest('/retry', { node_ids: nodeIds }),
    addInstruction: (instruction: string) => makeRequest('/instructions', { instruction }),
    approveContract: () => makeRequest('/approve-contract', { approved: true }),
    isLoading,
  };
}
