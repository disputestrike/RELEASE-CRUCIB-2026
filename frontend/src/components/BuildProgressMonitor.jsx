/**
 * BuildProgressMonitor — Real-time build progress display via WebSocket
 */

import React, { useEffect, useState, useRef } from 'react';
import './BuildProgressMonitor.css';

export default function BuildProgressMonitor({
  projectId,
  isVisible = true,
  token,
  apiBase = '/api',
}) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState('');
  const wsRef = useRef(null);

  useEffect(() => {
    if (!isVisible || !projectId || !token) return;

    // Connect to WebSocket
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/projects/${projectId}/build?token=${token}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ Connected to build progress stream');
      setIsConnected(true);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'build_event') {
          const event = {
            event_type: msg.event_type,
            message: msg.message,
            timestamp: msg.timestamp,
            data: msg.data || {},
          };

          setEvents((prev) => [...prev, event].slice(-100)); // Keep last 100 events

          // Update progress based on event type
          if (msg.event_type === 'build_phase_started') {
            const phaseNum = msg.data?.phase_number || 0;
            const totalPhases = msg.data?.total_phases || 1;
            setProgress((phaseNum - 1) / totalPhases);
            setCurrentPhase(msg.data?.phase_name || '');
          } else if (msg.event_type === 'build_completed' || msg.event_type === 'build_failed') {
            setProgress(1.0);
          }
        }
      } catch (e) {
        console.error('Failed to parse event:', e);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('Disconnected from build progress stream');
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isVisible, projectId, token]);

  if (!isVisible) return null;

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'build_started':
        return '🚀';
      case 'build_phase_started':
        return '⏳';
      case 'build_phase_completed':
        return '✅';
      case 'agent_started':
        return '🤖';
      case 'agent_completed':
        return '✔️';
      case 'agent_error':
        return '❌';
      case 'file_generated':
        return '📄';
      case 'validation_completed':
        return '🔍';
      case 'build_completed':
        return '🎉';
      case 'build_failed':
        return '💥';
      default:
        return '•';
    }
  };

  return (
    <div className="bpm-container">
      <div className="bpm-header">
        <h3>Build Progress</h3>
        <div className="bpm-connection-status">
          <span className={`bpm-status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      {currentPhase && (
        <div className="bpm-current-phase">
          <div className="bpm-phase-label">{currentPhase}</div>
          <div className="bpm-progress-bar">
            <div className="bpm-progress-fill" style={{ width: `${progress * 100}%` }} />
          </div>
          <div className="bpm-progress-text">{Math.round(progress * 100)}%</div>
        </div>
      )}

      <div className="bpm-events">
        {events.length === 0 ? (
          <div className="bpm-empty">Waiting for events...</div>
        ) : (
          events.map((event, idx) => (
            <div key={idx} className={`bpm-event bpm-event--${event.event_type}`}>
              <span className="bpm-event-icon">{getEventIcon(event.event_type)}</span>
              <div className="bpm-event-content">
                <div className="bpm-event-message">{event.message}</div>
                <div className="bpm-event-time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
