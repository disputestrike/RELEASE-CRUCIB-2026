/**
 * useJobStream — subscribes to /api/jobs/{id}/stream (SSE) and maintains live state.
 * Uses fetch() + ReadableStream against the real backend origin in dev so webpack-dev-server
 * does not break EventSource (shows "Reconnecting" and zero step events otherwise).
 * Returns { job, steps, events, proof, isConnected, error }
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API_BASE, getJobStreamUrl } from '../apiBase';

const EMPTY_PROOF = {
  bundle: {
    files: [],
    routes: [],
    database: [],
    verification: [],
    deploy: [],
    generic: [],
  },
  total_proof_items: 0,
  verification_proof_items: 0,
  quality_score: 0,
  category_counts: {},
};

function normalizeProofPayload(data, jobId) {
  if (data && typeof data === 'object' && data.bundle) return data;
  return {
    ...EMPTY_PROOF,
    job_id: jobId,
    success: true,
  };
}

function handleStreamPayload(data, jobId, token, setters) {
  const { setEvents, setSteps, setProof, setJob, fetchJobState } = setters;
  if (!data || !data.type || data.type === 'heartbeat') return;

  setEvents((prev) => {
    const id = data.id ?? `${data.type}-${data.step_id ?? ''}-${data.ts ?? ''}-${JSON.stringify(data.payload || {}).slice(0, 80)}`;
    const exists = prev.some((e) => (e.id ?? '') === id);
    if (exists) return prev;
    return [...prev, { ...data, id }];
  });

  if (
    data.type === 'step_completed' ||
    data.type === 'step_failed' ||
    data.type === 'step_started' ||
    data.type === 'step_retrying'
  ) {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .get(`${API_BASE}/jobs/${jobId}/steps`, { headers })
      .then((r) => setSteps(r.data?.steps || []))
      .catch(() => {});
    if (data.type === 'step_completed' || data.type === 'step_failed') {
      axios
        .get(`${API_BASE}/jobs/${jobId}/proof`, { headers })
        .then((r) => setProof(normalizeProofPayload(r.data, jobId)))
        .catch(() =>
          setProof({
            ...EMPTY_PROOF,
            job_id: jobId,
            proofFetchFailed: true,
          }),
        );
    }
  }

  if (data.type === 'job_completed' || data.type === 'job_failed') {
    fetchJobState();
  }

  if (data.type === 'job_started' || data.type === 'job_completed') {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .get(`${API_BASE}/jobs/${jobId}`, { headers })
      .then((r) => {
        const d = r.data;
        setJob(d?.job ?? d);
      })
      .catch(() => {});
  }
}

export function useJobStream(jobId, token) {
  const [job, setJob] = useState(null);
  const [steps, setSteps] = useState([]);
  const [events, setEvents] = useState([]);
  const [proof, setProof] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const fetchJobState = useCallback(async () => {
    if (!jobId) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const [jobRes, stepsRes, eventsRes, proofRes] = await Promise.allSettled([
        axios.get(`${API_BASE}/jobs/${jobId}`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/steps`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/events`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/proof`, { headers }),
      ]);
      if (jobRes.status === 'fulfilled') {
        const d = jobRes.value.data;
        setJob(d?.job ?? d);
      }
      if (stepsRes.status === 'fulfilled') setSteps(stepsRes.value.data?.steps || []);
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.data?.events || []);
      if (proofRes.status === 'fulfilled') {
        setProof(normalizeProofPayload(proofRes.value.data, jobId));
      } else {
        setProof({
          ...EMPTY_PROOF,
          job_id: jobId,
          proofFetchFailed: true,
        });
      }
    } catch (e) {
      // non-fatal
    }
  }, [jobId, token]);

  useEffect(() => {
    if (!jobId) {
      setProof(null);
      setJob(null);
      setSteps([]);
      setEvents([]);
      return undefined;
    }
    setProof(null);
    fetchJobState();

    const startPoll = () => {
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchJobState, 3000);
      }
    };

    const ac = new AbortController();
    const url = getJobStreamUrl(jobId);
    const setters = { setEvents, setSteps, setProof, setJob, fetchJobState };

    (async () => {
      try {
        const headers = {
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
        const res = await fetch(url, { headers, signal: ac.signal });
        if (!res.ok) {
          throw new Error(`stream ${res.status}`);
        }
        setIsConnected(true);
        setError(null);
        const reader = res.body?.getReader();
        if (!reader) {
          throw new Error('no body');
        }
        const decoder = new TextDecoder();
        let buffer = '';
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let sep;
          while ((sep = buffer.indexOf('\n\n')) !== -1) {
            const block = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const line = block.split('\n').find((l) => l.startsWith('data:'));
            if (!line) continue;
            const jsonStr = line.replace(/^data:\s?/, '').trim();
            if (!jsonStr) continue;
            try {
              const data = JSON.parse(jsonStr);
              handleStreamPayload(data, jobId, token, setters);
            } catch {
              /* ignore bad chunk */
            }
          }
        }
        setIsConnected(false);
        startPoll();
      } catch (e) {
        if (e?.name === 'AbortError') return;
        setIsConnected(false);
        setError('Stream disconnected — falling back to polling');
        startPoll();
      }
    })();

    return () => {
      ac.abort();
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobId, token, fetchJobState]);

  return { job, steps, events, proof, isConnected, error, refresh: fetchJobState };
}
