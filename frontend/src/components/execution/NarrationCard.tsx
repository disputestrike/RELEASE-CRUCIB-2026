/**
 * NarrationCard - Plain-language narration for execution thread
 * 
 * Kimi-style narration that explains what's happening in human terms.
 */

import React from 'react';
import { NarrationEvent } from '../../hooks/useJobEvents';

interface NarrationCardProps {
  narration: NarrationEvent;
}

export const NarrationCard: React.FC<NarrationCardProps> = ({ narration }) => {
  const { narrationType, message, phase, timestamp } = narration;
  
  // Get styles based on narration type
  const getStyles = () => {
    switch (narrationType) {
      case 'started':
        return {
          borderLeft: '4px solid #3b82f6',
          icon: '🚀',
          bg: '#eff6ff',
        };
      case 'progress':
        return {
          borderLeft: '4px solid #6b7280',
          icon: '⚙',
          bg: '#f9fafb',
        };
      case 'completed':
        return {
          borderLeft: '4px solid #22c55e',
          icon: '✅',
          bg: '#f0fdf4',
        };
      case 'repair':
        return {
          borderLeft: '4px solid #f59e0b',
          icon: '🔧',
          bg: '#fffbeb',
        };
      case 'blocked':
        return {
          borderLeft: '4px solid #ef4444',
          icon: '⛔',
          bg: '#fef2f2',
        };
      case 'ready':
        return {
          borderLeft: '4px solid #22c55e',
          icon: '✨',
          bg: '#f0fdf4',
        };
      default:
        return {
          borderLeft: '4px solid #6b7280',
          icon: '•',
          bg: '#f9fafb',
        };
    }
  };
  
  const styles = getStyles();
  
  const formatTime = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div
      className="narration-card"
      style={{
        padding: '16px 20px',
        marginBottom: '12px',
        borderRadius: '8px',
        backgroundColor: styles.bg,
        borderLeft: styles.borderLeft,
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
        <span style={{ fontSize: '20px' }}>{styles.icon}</span>
        <div style={{ flex: 1 }}>
          <p
            style={{
              margin: 0,
              fontSize: '15px',
              lineHeight: '1.5',
              color: '#1f2937',
              fontWeight: 400,
            }}
          >
            {message}
          </p>
          <div
            style={{
              marginTop: '8px',
              display: 'flex',
              gap: '12px',
              fontSize: '12px',
              color: '#6b7280',
            }}
          >
            {phase && (
              <span
                style={{
                  backgroundColor: '#e5e7eb',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  textTransform: 'capitalize',
                }}
              >
                {phase}
              </span>
            )}
            <span>{formatTime(timestamp)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NarrationCard;
