/**
 * RepairCard - Visualizes repair attempts and circuit breaker state
 * 
 * Shows: Issue detected → Repair agent → Attempt count → Result
 */

import React from 'react';

interface RepairAttempt {
  id: string;
  contract_item: string;
  error_type: string;
  agents_tried: string[];
  success: boolean;
  attempt_count: number;
  max_attempts: number;
  escalated: boolean;
}

interface RepairCardProps {
  repair: RepairAttempt;
  onRetry?: () => void;
  onBranch?: () => void;
  onCancel?: () => void;
}

export const RepairCard: React.FC<RepairCardProps> = ({
  repair,
  onRetry,
  onBranch,
  onCancel,
}) => {
  const isInProgress = !repair.success && !repair.escalated && repair.attempt_count < repair.max_attempts;
  const isEscalated = repair.escalated;

  return (
    <div
      className="repair-card"
      style={{
        padding: '16px 20px',
        marginBottom: '12px',
        borderRadius: '8px',
        backgroundColor: isEscalated ? '#fef2f2' : isInProgress ? '#fffbeb' : '#f0fdf4',
        border: `2px solid ${isEscalated ? '#ef4444' : isInProgress ? '#f59e0b' : '#22c55e'}`,
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <span style={{ fontSize: '24px' }}>
          {isEscalated ? '⚠️' : isInProgress ? '🔧' : '✅'}
        </span>
        <div>
          <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#1f2937' }}>
            {isEscalated ? 'Repair Escalated' : isInProgress ? 'Repair in Progress' : 'Repair Successful'}
          </h4>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#6b7280' }}>
            {repair.contract_item}
          </p>
        </div>
      </div>

      {/* Progress */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '12px', color: '#6b7280' }}>Repair Attempts</span>
          <span style={{ fontSize: '12px', fontWeight: 500, color: '#374151' }}>
            {repair.attempt_count} / {repair.max_attempts}
          </span>
        </div>
        <div
          style={{
            width: '100%',
            height: '6px',
            backgroundColor: '#e5e7eb',
            borderRadius: '3px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${(repair.attempt_count / repair.max_attempts) * 100}%`,
              height: '100%',
              backgroundColor: isEscalated ? '#ef4444' : isInProgress ? '#f59e0b' : '#22c55e',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      {/* Agents tried */}
      <div style={{ marginBottom: '12px' }}>
        <span style={{ fontSize: '12px', color: '#6b7280' }}>Agents: </span>
        {repair.agents_tried.map((agent, idx) => (
          <span
            key={idx}
            style={{
              display: 'inline-block',
              margin: '2px',
              padding: '2px 8px',
              backgroundColor: '#e5e7eb',
              borderRadius: '4px',
              fontSize: '11px',
              color: '#374151',
            }}
          >
            {agent}
          </span>
        ))}
      </div>

      {/* Escalation message */}
      {isEscalated && (
        <div
          style={{
            padding: '12px',
            backgroundColor: '#fee2e2',
            borderRadius: '6px',
            marginBottom: '12px',
          }}
        >
          <p style={{ margin: 0, fontSize: '13px', color: '#991b1b' }}>
            Repair failed {repair.max_attempts} times. Human steering required.
          </p>
        </div>
      )}

      {/* Success message */}
      {repair.success && (
        <div
          style={{
            padding: '12px',
            backgroundColor: '#dcfce7',
            borderRadius: '6px',
            marginBottom: '12px',
          }}
        >
          <p style={{ margin: 0, fontSize: '13px', color: '#166534' }}>
            ✓ Contract item repaired successfully. ExportGate unblocked.
          </p>
        </div>
      )}

      {/* Action buttons */}
      {isEscalated && (
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={onRetry}
            style={{
              padding: '8px 14px',
              backgroundColor: '#3b82f6',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Retry with Instruction
          </button>
          <button
            onClick={onBranch}
            style={{
              padding: '8px 14px',
              backgroundColor: '#fff',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Branch
          </button>
          <button
            onClick={onCancel}
            style={{
              padding: '8px 14px',
              backgroundColor: '#fff',
              color: '#ef4444',
              border: '1px solid #ef4444',
              borderRadius: '6px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};

export default RepairCard;
