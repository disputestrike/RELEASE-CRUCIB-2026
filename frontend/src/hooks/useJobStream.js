/**
 * useJobStream — subscribes to /api/jobs/{id}/stream (SSE) and maintains live state.
 * Returns { job, steps, events, proof, isConnected, error }
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL || '';

export function useJobStream(jobId, token) {
  const [job, setJob] = useState(null);
  const [steps, setSteps] = useState([]);
  const [events, setEvents] = useState([]);
  const [proof, setProof] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const esRef = useRef(null);
  const pollRef = useRef(null);

  const fetchJobState = useCallback(async () => {
    if (!jobId) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const [jobRes, stepsRes, eventsRes, proofRes] = await Promise.allSettled([
        axios.get(`${API}/api/jobs/${jobId}`, { headers }),
        axios.get(`${API}/api/jobs/${jobId}/steps`, { headers }),
        axios.get(`${API}/api/jobs/${jobId}/events`, { headers }),
        axios.get(`${API}/api/jobs/${jobId}/proof`, { headers }),
      ]);
      if (jobRes.status === 'fulfilled') setJob(jobRes.value.data?.job);
      if (stepsRes.status === 'fulfilled') setSteps(stepsRes.value.data?.steps || []);
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.data?.events || []);
      if (proofRes.status === 'fulfilled') setProof(proofRes.value.data);
    } catch (e) {
      // non-fatal
    }
  }, [jobId, token]);

  useEffect(() => {
    if (!jobId) return;
    fetchJobState();

    // SSE stream
    const url = `${API}/api/jobs/${jobId}/stream${token ? `?token=${token}` : ''}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setIsConnected(true);
    es.onerror = () => {
      setIsConnected(false);
      setError('Stream disconnected — falling back to polling');
      // Fallback polling every 3s
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchJobState, 3000);
      }
    };
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (!data.type || data.type === 'heartbeat') return;

        setEvents(prev => {
          // deduplicate
          const exists = prev.some(e => e.id === data.id);
          return exists ? prev : [...prev, data];
        });

        if (data.type === 'step_completed' || data.type === 'step_failed' ||
            data.type === 'step_started' || data.type === 'step_retrying') {
          // Refresh steps list
          const headers = token ? { Authorization: `Bearer ${token}` } : {};
          axios.get(`${API}/api/jobs/${jobId}/steps`, { headers })
            .then(r => setSteps(r.data?.steps || []))
            .catch(() => {});
        }

        if (data.type === 'job_completed' || data.type === 'job_failed') {
          fetchJobState();
        }

        if (data.type === 'job_started' || data.type === 'job_completed') {
          const headers = token ? { Authorization: `Bearer ${token}` } : {};
          axios.get(`${API}/api/jobs/${jobId}`, { headers })
            .then(r => setJob(r.data?.job))
            .catch(() => {});
        }
      } catch {}
    };

    return () => {
      es.close();
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobId, token, fetchJobState]);

  return { job, steps, events, proof, isConnected, error, refresh: fetchJobState };
}
