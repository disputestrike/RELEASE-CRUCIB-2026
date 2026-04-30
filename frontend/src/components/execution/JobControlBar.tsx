import React from 'react';
import { useJobControls } from '../../hooks/useJobControls';

interface JobControlBarProps {
  jobId: string | null;
  jobState: string | null;
}

export const JobControlBar: React.FC<JobControlBarProps> = ({ jobId, jobState }) => {
  const { pause, resume, cancel, retry, isLoading } = useJobControls(jobId);

  const getVisibleControls = () => {
    const controls: { key: string; label: string; onClick: () => void; style: string }[] = [];
    
    if (jobState === 'running') {
      controls.push({ key: 'pause', label: 'Pause', onClick: pause, style: 'secondary' });
      controls.push({ key: 'cancel', label: 'Cancel', onClick: cancel, style: 'danger' });
    } else if (jobState === 'paused') {
      controls.push({ key: 'resume', label: 'Resume', onClick: resume, style: 'primary' });
      controls.push({ key: 'cancel', label: 'Cancel', onClick: cancel, style: 'danger' });
    } else if (jobState === 'failed_recoverable' || jobState === 'repair_required') {
      controls.push({ key: 'retry', label: 'Retry', onClick: retry, style: 'primary' });
      controls.push({ key: 'cancel', label: 'Cancel', onClick: cancel, style: 'danger' });
    }
    
    return controls;
  };

  const controls = getVisibleControls();
  if (controls.length === 0) return null;

  const getStyle = (style: string) => {
    switch (style) {
      case 'primary': return { backgroundColor: '#3b82f6', color: '#fff', border: '1px solid #3b82f6' };
      case 'secondary': return { backgroundColor: '#fff', color: '#374151', border: '1px solid #d1d5db' };
      case 'danger': return { backgroundColor: '#fff', color: '#ef4444', border: '1px solid #ef4444' };
      default: return { backgroundColor: '#fff', color: '#374151', border: '1px solid #d1d5db' };
    }
  };

  return (
    <div style={{ padding: '12px 16px', backgroundColor: '#f9fafb', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '8px' }}>
      {controls.map((control) => (
        <button
          key={control.key}
          onClick={control.onClick}
          disabled={isLoading}
          style={{
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '13px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1,
            ...getStyle(control.style),
          }}
        >
          {control.label}
        </button>
      ))}
    </div>
  );
};

export default JobControlBar;
