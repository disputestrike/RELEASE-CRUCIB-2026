import React from 'react';
import { ExecutionThread } from './ExecutionThread';
import { BuildComposer } from './BuildComposer';
import { JobControlBar } from './JobControlBar';
import { useJobEvents } from '../../hooks/useJobEvents';

interface MiddlePaneProps {
  jobId: string | null;
  jobState?: string | null;
}

export const MiddlePane: React.FC<MiddlePaneProps> = ({ jobId, jobState = 'idle' }) => {
  const { events, narrations, isConnected } = useJobEvents(jobId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#f8fafc' }}>
      <div style={{ padding: '12px 16px', backgroundColor: '#fff', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ 
            width: '8px', 
            height: '8px', 
            borderRadius: '50%', 
            backgroundColor: isConnected ? '#22c55e' : '#ef4444' 
          }} />
          <span style={{ fontSize: '14px', fontWeight: 500 }}>
            {jobId ? Job: ... () : 'New Build'}
          </span>
        </div>
      </div>
      
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ExecutionThread narrations={narrations} events={events} jobId={jobId} />
      </div>
      
      <JobControlBar jobId={jobId} jobState={jobState} />
      <BuildComposer jobId={jobId} jobState={jobState} />
    </div>
  );
};

export default MiddlePane;
