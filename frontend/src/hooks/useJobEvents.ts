/**
 * useJobEvents - Real-time job event streaming hook
 * 
 * Polls /api/jobs/{job_id}/events and transforms raw events
 * into UI-ready event cards with narration.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface JobEvent {
  id: string;
  type: string;
  payload: any;
  agent_id?: string;
  timestamp: string;
}

export interface NarrationEvent extends JobEvent {
  narrationType: 'started' | 'progress' | 'completed' | 'repair' | 'blocked' | 'ready';
  message: string;
  phase?: string;
}

export function useJobEvents(jobId: string | null) {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [narrations, setNarrations] = useState<NarrationEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastTimestamp = useRef<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Transform raw event into narration
  const transformToNarration = (event: JobEvent): NarrationEvent | null => {
    const { type, payload, agent_id } = event;
    
    switch (type) {
      case 'narration.started':
        return {
          ...event,
          narrationType: 'started',
          message: payload.message || 'Build started',
          phase: payload.phase
        };
      
      case 'narration.progress':
        return {
          ...event,
          narrationType: 'progress',
          message: payload.message || 'Building...',
          phase: payload.phase
        };
      
      case 'phase_started':
        return {
          ...event,
          narrationType: 'started',
          message: `Starting phase: ${payload.phase}`,
          phase: payload.phase
        };
      
      case 'phase_completed':
        return {
          ...event,
          narrationType: 'completed',
          message: `Completed: ${payload.phase}`,
          phase: payload.phase
        };
      
      case 'phase_blocked':
        return {
          ...event,
          narrationType: 'blocked',
          message: `Blocked: ${payload.reason || payload.phase}`,
          phase: payload.phase
        };
      
      case 'error':
      case 'node_fail':
        return {
          ...event,
          narrationType: 'blocked',
          message: `Issue detected: ${payload.error || payload.message}`,
          phase: payload.phase
        };
      
      case 'repair_started':
        return {
          ...event,
          narrationType: 'repair',
          message: `Repairing: ${payload.contract_item || 'issue'}`,
          phase: 'repair'
        };
      
      case 'repair_completed':
        return {
          ...event,
          narrationType: 'repair',
          message: `Repair successful: ${payload.contract_item || 'issue fixed'}`,
          phase: 'repair'
        };
      
      case 'export_gate_blocked':
        return {
          ...event,
          narrationType: 'blocked',
          message: `Export blocked: ${payload.reason || 'contract incomplete'}`,
          phase: 'export'
        };
      
      case 'export_gate_ready':
        return {
          ...event,
          narrationType: 'ready',
          message: 'Export ready: all requirements satisfied',
          phase: 'export'
        };
      
      case 'done':
        return {
          ...event,
          narrationType: 'completed',
          message: 'Build complete and verified',
          phase: 'complete'
        };
      
      case 'user_instruction':
        return {
          ...event,
          narrationType: 'progress',
          message: `Instruction added: ${payload.instruction}`,
          phase: 'steering'
        };
      
      case 'circuit_breaker_escalated':
        return {
          ...event,
          narrationType: 'blocked',
          message: 'Repair failed 3 times. Human steering required.',
          phase: 'escalation'
        };
      
      default:
        // Generic fallback for unknown events
        return {
          ...event,
          narrationType: 'progress',
          message: payload.message || `${type}: ${JSON.stringify(payload).slice(0, 100)}`,
          phase: payload.phase || 'unknown'
        };
    }
  };

  // Poll for new events
  const pollEvents = useCallback(async () => {
    if (!jobId) return;

    try {
      const params = lastTimestamp.current 
        ? `?since=${encodeURIComponent(lastTimestamp.current)}`
        : '';
      
      const response = await fetch(`/api/jobs/${jobId}/events${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const newEvents: JobEvent[] = await response.json();
      
      if (newEvents.length > 0) {
        setEvents(prev => [...prev, ...newEvents]);
        
        // Transform to narrations
        const newNarrations = newEvents
          .map(transformToNarration)
          .filter((n): n is NarrationEvent => n !== null);
        
        if (newNarrations.length > 0) {
          setNarrations(prev => [...prev, ...newNarrations]);
        }
        
        // Update last timestamp
        const lastEvent = newEvents[newEvents.length - 1];
        if (lastEvent?.timestamp) {
          lastTimestamp.current = lastEvent.timestamp;
        }
      }
      
      setIsConnected(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
      setIsConnected(false);
    }
  }, [jobId]);

  // Start polling
  useEffect(() => {
    if (!jobId) {
      setEvents([]);
      setNarrations([]);
      lastTimestamp.current = null;
      return;
    }

    // Initial poll
    pollEvents();

    // Set up polling interval (1 second)
    pollingRef.current = setInterval(pollEvents, 1000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [jobId, pollEvents]);

  // Refresh function
  const refresh = useCallback(() => {
    lastTimestamp.current = null;
    setEvents([]);
    setNarrations([]);
    pollEvents();
  }, [pollEvents]);

  return {
    events,
    narrations,
    isConnected,
    error,
    refresh
  };
}
