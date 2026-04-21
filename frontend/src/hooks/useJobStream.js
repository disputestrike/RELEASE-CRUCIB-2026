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
  const { setEvents, setSteps, setProof, setJob, setLatestFailure, fetchJobState, fetchCheckpoints } = setters;
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
          setProof((prev) => {
            const had = prev && typeof prev.total_proof_items === 'number' && prev.total_proof_items > 0;
            if (had) return { ...prev, proofFetchFailed: true };
            return {
              ...EMPTY_PROOF,
              job_id: jobId,
              proofFetchFailed: true,
            };
          }),
        );
      if (typeof fetchCheckpoints === 'function') fetchCheckpoints();
    }
  }

  if (
    data.type === 'job_completed' ||
    data.type === 'job_failed' ||
    data.type === 'brain_guidance' ||
    data.type === 'job_reactivated' ||
    data.type === 'user_steering'
  ) {
    fetchJobState();
  }

  if (data.type === 'job_started' || data.type === 'job_completed') {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .get(`${API_BASE}/jobs/${jobId}`, { headers })
      .then((r) => {
        const d = r.data;
        setJob(d?.job ?? d);
        setLatestFailure(d?.latest_failure ?? null);
      })
      .catch(() => {});
  }
}

export function useJobStream(jobId, token) {
  const [job, setJob] = useState(null);
  const [latestFailure, setLatestFailure] = useState(null);
  const [milestoneBatch, setMilestoneBatch] = useState(null);
  const [repairQueueLen, setRepairQueueLen] = useState(0);
  const [steps, setSteps] = useState([]);
  const [events, setEvents] = useState([]);
  const [proof, setProof] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionMode, setConnectionMode] = useState('offline');
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const fetchCheckpoints = useCallback(async () => {
    if (!jobId || !token) return;
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [mb, rq] = await Promise.allSettled([
        axios.get(`${API_BASE}/jobs/${jobId}/checkpoint/last_milestone_batch`, { headers, timeout: 12_000 }),
        axios.get(`${API_BASE}/jobs/${jobId}/checkpoint/repair_queue`, { headers, timeout: 12_000 }),
      ]);
      if (mb.status === 'fulfilled') {
        setMilestoneBatch(mb.value.data?.data ?? null);
      } else {
        setMilestoneBatch(null);
      }
      if (rq.status === 'fulfilled') {
        const d = rq.value.data?.data;
        const items = d?.items;
        const n = typeof d?.count === 'number' ? d.count : Array.isArray(items) ? items.length : 0;
        setRepairQueueLen(n);
      } else {
        setRepairQueueLen(0);
      }
    } catch {
      setMilestoneBatch(null);
      setRepairQueueLen(0);
    }
  }, [jobId, token]);

  const fetchJobState = useCallback(async () => {
    if (!jobId || !token) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [jobRes, stepsRes, eventsRes, proofRes] = await Promise.allSettled([
        axios.get(`${API_BASE}/jobs/${jobId}`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/steps`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/events`, { headers }),
        axios.get(`${API_BASE}/jobs/${jobId}/proof`, { headers }),
      ]);
      if (jobRes.status === 'fulfilled') {
        const d = jobRes.value.data;
        setJob(d?.job ?? d);
        setLatestFailure(d?.latest_failure ?? null);
      }
      if (stepsRes.status === 'fulfilled') setSteps(stepsRes.value.data?.steps || []);
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.data?.events || []);
      if (proofRes.status === 'fulfilled') {
        setProof(normalizeProofPayload(proofRes.value.data, jobId));
      } else {
        setProof((prev) => {
          const had = prev && typeof prev.total_proof_items === 'number' && prev.total_proof_items > 0;
          if (had) return { ...prev, proofFetchFailed: true };
          return {
            ...EMPTY_PROOF,
            job_id: jobId,
            proofFetchFailed: true,
          };
        });
      }
      if (token) await fetchCheckpoints();
      const anySuccess = [jobRes, stepsRes, eventsRes, proofRes].some((result) => result.status === 'fulfilled');
      if (anySuccess && pollRef.current) {
        setConnectionMode('polling');
      }
    } catch (e) {
      if (pollRef.current) setConnectionMode('offline');
    }
  }, [jobId, token, fetchCheckpoints]);

  useEffect(() => {
    if (!jobId || !token) {
      setProof(null);
      setJob(null);
      setSteps([]);
      setEvents([]);
      setMilestoneBatch(null);
      setRepairQueueLen(0);
      setConnectionMode('offline');
      setIsConnected(false);
      setError(null);
      return undefined;
    }
    setProof(null);
    setMilestoneBatch(null);
    setRepairQueueLen(0);
    fetchJobState();

    const startPoll = () => {
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchJobState, 3000);
      }
      setConnectionMode('polling');
    };

    const ac = new AbortController();
    const url = getJobStreamUrl(jobId);
    const setters = {
      setEvents,
      setSteps,
      setProof,
      setJob,
      setLatestFailure,
      fetchJobState,
      fetchCheckpoints,
    };

    (async () => {
      try {
        const headers = {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        };
        const res = await fetch(url, { headers, signal: ac.signal });
        if (!res.ok) {
          throw new Error(`stream ${res.status}`);
        }
        setIsConnected(true);
        setConnectionMode('stream');
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
      setConnectionMode('offline');
    };
  }, [jobId, token, fetchJobState, fetchCheckpoints]);

  return {
    job,
    latestFailure,
    milestoneBatch,
    repairQueueLen,
    steps,
    events,
    proof,
    isConnected,
    connectionMode,
    error,
    refresh: fetchJobState,
  };
}
