// frontend/src/components/orchestration/KanbanBoard.jsx
/**
 * Real-time orchestration dashboard showing all agents by phase.
 * Updates via WebSocket as agents complete.
 */

import React, { useState } from 'react';
import { useJobProgress } from '../../hooks/useJobProgress';
import PhaseGroup from './PhaseGroup';
import LiveLog from './LiveLog';
import ProgressBar from './ProgressBar';
import styles from './orchestration.module.css';

export default function KanbanBoard({ jobId }) {
  const {
    phases,
    logs,
    isRunning,
    totalProgress,
    controller,
    currentPhase,
    isConnected,
    error,
  } = useJobProgress(jobId);
  const [expandedPhase, setExpandedPhase] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);

  if (error) {
    return (
      <div className={styles.error}>
        <h2>Error Loading Build</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!phases) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Loading orchestration...</p>
      </div>
    );
  }

  return (
    <div className={styles.kanbanContainer}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1>CrucibAI Build</h1>
          <span className={styles.jobId}>{jobId}</span>
        </div>
        
        <div className={styles.headerRight}>
          <div className={styles.status}>
            <span className={isRunning ? styles.statusRunning : styles.statusComplete}>
              {isRunning ? 'Running' : 'Complete'}
            </span>
            <ProgressBar progress={totalProgress} />
            <span className={styles.progressText}>{totalProgress}%</span>
          </div>
        </div>
      </div>

      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.jobId}>Phase: {currentPhase || 'pending'}</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.jobId}>Socket: {isConnected ? 'connected' : 'reconnecting'}</span>
          {controller?.status ? (
            <span className={styles.jobId}>Controller: {controller.status}</span>
          ) : null}
        </div>
      </div>

      {/* Phases Grid */}
      <div className={styles.phasesContainer}>
        {phases.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No phases found. Build may not have started.</p>
          </div>
        ) : (
          phases.map((phase, idx) => (
            <PhaseGroup
              key={phase.id}
              phase={phase}
              phaseIndex={idx}
              totalPhases={phases.length}
              isExpanded={expandedPhase === phase.id}
              onToggle={() => 
                setExpandedPhase(expandedPhase === phase.id ? null : phase.id)
              }
            />
          ))
        )}
      </div>

      {/* Live Log */}
      <LiveLog 
        logs={logs} 
        isRunning={isRunning}
        autoScroll={autoScroll}
        onAutoScrollToggle={() => setAutoScroll(!autoScroll)}
      />
    </div>
  );
}
