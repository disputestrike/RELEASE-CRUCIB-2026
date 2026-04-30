import React, { useState } from 'react';

interface BuildComposerProps {
  jobId: string | null;
  jobState: string | null;
}

export const BuildComposer: React.FC<BuildComposerProps> = ({ jobId, jobState }) => {
  const [input, setInput] = useState('');

  const getModeInfo = () => {
    if (!jobId || jobState === 'idle') {
      return { placeholder: 'Describe what you want to build...', buttonText: 'Start Build' };
    }
    if (jobState === 'running') {
      return { placeholder: 'Add instruction mid-build...', buttonText: 'Send Instruction' };
    }
    return { placeholder: 'Ask why it failed, request changes, or approve...', buttonText: 'Send' };
  };

  const modeInfo = getModeInfo();

  const handleSubmit = () => {
    if (!input.trim()) return;
    console.log('Submit:', input);
    setInput('');
  };

  return (
    <div style={{ padding: '16px', backgroundColor: '#fff', borderTop: '1px solid #e5e7eb' }}>
      <div style={{ position: 'relative' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={modeInfo.placeholder}
          style={{
            width: '100%',
            minHeight: '56px',
            padding: '12px 16px',
            paddingRight: '100px',
            border: '1px solid #d1d5db',
            borderRadius: '12px',
            fontSize: '14px',
            resize: 'none',
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim()}
          style={{
            position: 'absolute',
            right: '8px',
            bottom: '8px',
            padding: '8px 16px',
            backgroundColor: input.trim() ? '#3b82f6' : '#9ca3af',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            fontSize: '13px',
            cursor: input.trim() ? 'pointer' : 'not-allowed',
          }}
        >
          {modeInfo.buttonText}
        </button>
      </div>
    </div>
  );
};

export default BuildComposer;
