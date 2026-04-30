/**
 * EventCard - Generic event renderer for execution thread
 * 
 * Renders any backend event with appropriate styling based on type.
 */

import React, { useState } from 'react';
import { JobEvent } from '../../hooks/useJobEvents';

interface EventCardProps {
  event: JobEvent;
  isExpanded?: boolean;
}

export const EventCard: React.FC<EventCardProps> = ({ event, isExpanded: defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  const { type, payload, agent_id, timestamp } = event;
  
  // Get icon and color based on event type
  const getEventStyles = () => {
    switch (type) {
      case 'phase_started':
      case 'narration.started':
        return { icon: '▶', color: '#3b82f6', bg: '#eff6ff' }; // blue
      
      case 'phase_completed':
      case 'narration.completed':
      case 'done':
        return { icon: '✓', color: '#22c55e', bg: '#f0fdf4' }; // green
      
      case 'error':
      case 'node_fail':
      case 'phase_blocked':
        return { icon: '✗', color: '#ef4444', bg: '#fef2f2' }; // red
      
      case 'repair_started':
        return { icon: '🔧', color: '#f59e0b', bg: '#fffbeb' }; // amber
      
      case 'repair_completed':
        return { icon: '✓', color: '#22c55e', bg: '#f0fdf4' }; // green
      
      case 'export_gate_blocked':
        return { icon: '🚫', color: '#ef4444', bg: '#fef2f2' }; // red
      
      case 'export_gate_ready':
        return { icon: '✓', color: '#22c55e', bg: '#f0fdf4' }; // green
      
      case 'user_instruction':
        return { icon: '💬', color: '#8b5cf6', bg: '#f5f3ff' }; // purple
      
      case 'circuit_breaker_escalated':
        return { icon: '⚠', color: '#f59e0b', bg: '#fffbeb' }; // amber
      
      case 'tool_call':
        return { icon: '⚙', color: '#6b7280', bg: '#f9fafb' }; // gray
      
      default:
        return { icon: '•', color: '#6b7280', bg: '#f9fafb' }; // gray
    }
  };
  
  const styles = getEventStyles();
  
  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div 
      className="event-card"
      style={{
        padding: '12px 16px',
        marginBottom: '8px',
        borderRadius: '8px',
        backgroundColor: styles.bg,
        border: `1px solid ${styles.color}20`,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: '14px',
      }}
    >
      {/* Header */}
      <div 
        className="event-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span style={{ fontSize: '16px' }}>{styles.icon}</span>
        <span style={{ 
          fontWeight: 500, 
          color: styles.color,
          textTransform: 'capitalize',
        }}>
          {type.replace(/_/g, ' ')}
        </span>
        {agent_id && (
          <span style={{ 
            fontSize: '12px', 
            color: '#6b7280',
            backgroundColor: '#e5e7eb',
            padding: '2px 6px',
            borderRadius: '4px',
          }}>
            {agent_id}
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#9ca3af' }}>
          {formatTimestamp(timestamp)}
        </span>
        <span style={{ fontSize: '12px', color: '#9ca3af' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>
      
      {/* Summary (always visible) */}
      {payload?.message && (
        <div style={{ marginTop: '8px', color: '#374151' }}>
          {payload.message}
        </div>
      )}
      
      {/* Expanded details */}
      {isExpanded && (
        <div 
          className="event-details"
          style={{
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: '1px solid #e5e7eb',
            fontSize: '12px',
            color: '#6b7280',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          <pre style={{ margin: 0 }}>
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default EventCard;
