// frontend/src/hooks/useWebSocket.js
/**
 * Custom React hook for WebSocket connection management.
 * Handles reconnection, message parsing, and cleanup.
 */

import { useEffect, useState, useRef, useCallback } from 'react';

export function useWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const reconnectCount = useRef(0);
  const maxReconnects = 5;

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${url}`;
        
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
          setIsConnected(true);
          setError(null);
          reconnectCount.current = 0;
          console.log(`Connected to ${url}`);
        };

        ws.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            setLastMessage(message);
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('Connection error');
        };

        ws.current.onclose = () => {
          setIsConnected(false);
          console.log('WebSocket disconnected');
          
          // Attempt reconnection
          if (reconnectCount.current < maxReconnects) {
            reconnectCount.current += 1;
            const delay = Math.min(1000 * Math.pow(2, reconnectCount.current), 10000);
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(connectWebSocket, delay);
          } else {
            setError('Connection lost. Please refresh.');
          }
        };
      } catch (e) {
        console.error('WebSocket setup error:', e);
        setError(e.message);
      }
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  return {
    lastMessage,
    isConnected,
    error,
    sendMessage
  };
}

// frontend/src/hooks/useJobProgress.js
/**
 * Custom hook to manage job progress from WebSocket events.
 * Aggregates events into phases and logs.
 */

import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export function useJobProgress(jobId) {
  const [phases, setPhases] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(true);
  const [totalProgress, setTotalProgress] = useState(0);
  const [error, setError] = useState(null);

  const { lastMessage, isConnected } = useWebSocket(`/api/job/${jobId}/progress`);

  // Fetch initial state on mount
  useEffect(() => {
    const fetchInitialState = async () => {
      try {
        const response = await fetch(`/api/job/${jobId}/progress`);
        if (response.ok) {
          const data = await response.json();
          setPhases(data.phases || []);
          setTotalProgress(data.total_progress || 0);
          setIsRunning(data.is_running || false);
        }
      } catch (e) {
        console.error('Failed to fetch initial progress:', e);
        setError(e.message);
      }
    };

    fetchInitialState();
  }, [jobId]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    const event = lastMessage;

    switch (event.type) {
      case 'phase_update':
        setPhases(prev => 
          prev.map(p => 
            p.id === event.phase_id 
              ? {
                  ...p,
                  progress: event.progress || p.progress,
                  status: event.status || p.status,
                  completed: event.completed || p.completed,
                  total: event.total || p.total
                }
              : p
          )
        );
        setTotalProgress(event.progress || totalProgress);
        break;

      case 'agent_start':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'start',
          agent: event.agent_name,
          phase: event.phase_id,
          message: `Starting ${event.agent_name}...`,
          level: 'info'
        }]);
        
        // Update phase agent status
        setPhases(prev =>
          prev.map(p =>
            p.id === event.phase_id
              ? {
                  ...p,
                  agents: p.agents.map(a =>
                    a.name === event.agent_name
                      ? { ...a, status: 'running' }
                      : a
                  )
                }
              : p
          )
        );
        break;

      case 'agent_progress':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'progress',
          agent: event.agent_name,
          message: event.message || `${event.agent_name}: ${(event.progress || 0) * 100}%`,
          level: 'info'
        }]);
        break;

      case 'agent_complete':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'complete',
          agent: event.agent_name,
          message: `✓ ${event.agent_name} completed`,
          level: 'success'
        }]);

        // Update agent status in phases
        setPhases(prev =>
          prev.map(p =>
            p.id === event.phase_id
              ? {
                  ...p,
                  agents: p.agents.map(a =>
                    a.name === event.agent_name
                      ? { 
                          ...a, 
                          status: 'complete',
                          output: event.summary
                        }
                      : a
                  ),
                  completed: (p.completed || 0) + 1,
                  progress: Math.round(((p.completed || 0) + 1) / (p.total || 1) * 100)
                }
              : p
          )
        );
        
        setTotalProgress(event.progress || totalProgress);
        break;

      case 'agent_error':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'error',
          agent: event.agent_name,
          message: `✗ ${event.agent_name}: ${event.error}`,
          level: 'error'
        }]);

        // Update agent status
        setPhases(prev =>
          prev.map(p =>
            p.id === event.phase_id
              ? {
                  ...p,
                  agents: p.agents.map(a =>
                    a.name === event.agent_name
                      ? { 
                          ...a, 
                          status: 'error',
                          error: event.error
                        }
                      : a
                  )
                }
              : p
          )
        );
        break;

      case 'build_complete':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'complete',
          agent: 'build',
          message: `✅ Build completed in ${event.total_time}s`,
          level: 'success'
        }]);
        setIsRunning(false);
        setTotalProgress(100);
        break;

      case 'build_error':
        setLogs(prev => [...prev, {
          timestamp: new Date(event.timestamp),
          type: 'error',
          agent: 'build',
          message: `✗ Build failed: ${event.error}`,
          level: 'error'
        }]);
        setIsRunning(false);
        break;

      default:
        break;
    }
  }, [lastMessage]);

  return {
    phases,
    logs,
    isRunning,
    totalProgress,
    error: error || (phases === null && isConnected ? null : error),
    isConnected
  };
}
