import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './useWebSocket';

function normalizeBootstrap(payload) {
  return {
    phases: payload?.phases || [],
    logs: payload?.logs || [],
    isRunning: Boolean(payload?.is_running),
    totalProgress: payload?.total_progress || 0,
    controller: payload?.controller || null,
    currentPhase: payload?.current_phase || null,
  };
}

function updateAgentStatus(phases, agentName, status, patch = {}) {
  return (phases || []).map((phase) => ({
    ...phase,
    agents: (phase.agents || []).map((agent) =>
      agent.name === agentName
        ? { ...agent, status, ...patch }
        : agent
    ),
  }));
}

function appendLog(prevLogs, entry) {
  return [...prevLogs, entry].slice(-200);
}

export function useJobProgress(jobId) {
  const [phases, setPhases] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [totalProgress, setTotalProgress] = useState(0);
  const [controller, setController] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [error, setError] = useState(null);

  const { lastMessage, isConnected, error: wsError } = useWebSocket(jobId ? `/api/job/${jobId}/progress` : null);

  useEffect(() => {
    if (!jobId) {
      setPhases(null);
      setLogs([]);
      setIsRunning(false);
      setTotalProgress(0);
      setController(null);
      setCurrentPhase(null);
      setError(null);
      return;
    }

    let cancelled = false;

    async function fetchInitialState() {
      try {
        const response = await fetch(`/api/job/${jobId}/progress`);
        if (!response.ok) {
          throw new Error(`Progress bootstrap failed (${response.status})`);
        }
        const data = await response.json();
        if (cancelled) {
          return;
        }
        const normalized = normalizeBootstrap(data);
        setPhases(normalized.phases);
        setLogs(normalized.logs);
        setIsRunning(normalized.isRunning);
        setTotalProgress(normalized.totalProgress);
        setController(normalized.controller);
        setCurrentPhase(normalized.currentPhase);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load job progress');
        }
      }
    }

    fetchInitialState();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  useEffect(() => {
    if (!lastMessage) {
      return;
    }

    if (lastMessage.type === 'bootstrap' && lastMessage.payload) {
      const normalized = normalizeBootstrap(lastMessage.payload);
      setPhases(normalized.phases);
      setLogs(normalized.logs);
      setIsRunning(normalized.isRunning);
      setTotalProgress(normalized.totalProgress);
      setController(normalized.controller);
      setCurrentPhase(normalized.currentPhase);
      return;
    }

    if (lastMessage.snapshot) {
      const normalized = normalizeBootstrap(lastMessage.snapshot);
      setPhases(normalized.phases);
      setLogs(normalized.logs);
      setIsRunning(normalized.isRunning);
      setTotalProgress(normalized.totalProgress);
      setController(normalized.controller);
      setCurrentPhase(normalized.currentPhase);
      setError(null);
      return;
    }

    const payload = lastMessage.payload || {};
    const timestamp = new Date().toISOString();
    const agentName = payload.agent_name || payload.agent || payload.step_key || 'system';

    if (lastMessage.type === 'step_started') {
      setPhases((prev) => updateAgentStatus(prev, agentName, 'running'));
      setLogs((prev) => appendLog(prev, { timestamp, type: 'step_started', agent: agentName, message: `${agentName} started`, level: 'info' }));
      setIsRunning(true);
      return;
    }

    if (lastMessage.type === 'step_completed') {
      setPhases((prev) => updateAgentStatus(prev, agentName, 'complete', { output: payload.summary || payload.message || '' }));
      setLogs((prev) => appendLog(prev, { timestamp, type: 'step_completed', agent: agentName, message: payload.message || `${agentName} completed`, level: 'success' }));
      setTotalProgress((prev) => Math.min(100, prev + 2));
      return;
    }

    if (lastMessage.type === 'step_failed' || lastMessage.type === 'verification_attempt_failed') {
      setPhases((prev) => updateAgentStatus(prev, agentName, 'error', { error: payload.error || payload.failure_reason || 'failed' }));
      setLogs((prev) => appendLog(prev, { timestamp, type: lastMessage.type, agent: agentName, message: payload.error || payload.failure_reason || `${agentName} failed`, level: 'error' }));
      return;
    }

    if (lastMessage.type === 'job_completed' || lastMessage.type === 'job_failed') {
      setIsRunning(false);
      setTotalProgress(100);
      setLogs((prev) => appendLog(prev, { timestamp, type: lastMessage.type, agent: 'build', message: payload.message || lastMessage.type.replace('_', ' '), level: lastMessage.type === 'job_completed' ? 'success' : 'error' }));
    }
  }, [lastMessage]);

  useEffect(() => {
    if (wsError) {
      setError(wsError);
    }
  }, [wsError]);

  const summary = useMemo(() => ({
    phases,
    logs,
    isRunning,
    totalProgress,
    controller,
    currentPhase,
    isConnected,
    error,
  }), [phases, logs, isRunning, totalProgress, controller, currentPhase, isConnected, error]);

  return summary;
}
