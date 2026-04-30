import React from 'react';
import { NarrationCard } from './NarrationCard';
import { EventCard } from './EventCard';
import { NarrationEvent, JobEvent } from '../../hooks/useJobEvents';

interface ExecutionThreadProps {
  narrations: NarrationEvent[];
  events: JobEvent[];
  jobId: string | null;
  showRawEvents?: boolean;
}

export const ExecutionThread: React.FC<ExecutionThreadProps> = ({ 
  narrations, 
  events, 
  jobId,
  showRawEvents = false 
}) => {
  if (!jobId) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9ca3af' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: '18px', marginBottom: '8px' }}>Welcome to CrucibAI</p>
          <p style={{ fontSize: '14px' }}>Enter a build prompt below to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '16px' }}>
      {narrations.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#9ca3af', paddingTop: '40px' }}>
          Waiting for events...
        </div>
      ) : (
        <>
          {narrations.map((narration, index) => (
            <NarrationCard key={index} narration={narration} />
          ))}
          
          {showRawEvents && (
            <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '2px dashed #e5e7eb' }}>
              <h4 style={{ fontSize: '12px', color: '#6b7280', marginBottom: '12px' }}>Raw Events</h4>
              {events.map((event, index) => (
                <EventCard key={index} event={event} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ExecutionThread;
