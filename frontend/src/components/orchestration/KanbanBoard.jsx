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

      {controller ? (
        <section className={styles.controllerPanel}>
          <div className={styles.controllerHeader}>
            <strong>Controller Brain</strong>
            <span className={styles.controllerStatus}>{controller.status || 'idle'}</span>
          </div>
          <div className={styles.controllerGrid}>
            <div className={styles.controllerCard}>
              <span className={styles.controllerLabel}>Recommended focus</span>
              <strong>{controller.recommended_focus || 'Await new work'}</strong>
            </div>
            <div className={styles.controllerCard}>
              <span className={styles.controllerLabel}>Active agents</span>
              <strong>{controller.active_agent_count || 0}</strong>
              {(controller.active_agents || []).length > 0 ? (
                <span className={styles.controllerMeta}>{controller.active_agents.join(', ')}</span>
              ) : null}
            </div>
            <div className={styles.controllerCard}>
              <span className={styles.controllerLabel}>Queued agents</span>
              <strong>{controller.queued_agent_count || 0}</strong>
              {(controller.queued_agents || []).length > 0 ? (
                <span className={styles.controllerMeta}>{controller.queued_agents.join(', ')}</span>
              ) : null}
            </div>
            <div className={styles.controllerCard}>
              <span className={styles.controllerLabel}>Parallel phases</span>
              <strong>{controller.parallel_phase_count || 0}</strong>
            </div>
          </div>
          {(controller.next_actions || []).length > 0 ? (
            <div className={styles.controllerListBlock}>
              <span className={styles.controllerLabel}>Next actions</span>
              <div className={styles.tagList}>
                {(controller.next_actions || []).map((action) => (
                  <span key={action} className={styles.tag}>{action}</span>
                ))}
              </div>
            </div>
          ) : null}
          {(controller.blockers || []).length > 0 ? (
            <div className={styles.controllerListBlock}>
              <span className={styles.controllerLabel}>Blockers</span>
              <div className={styles.blockerList}>
                {(controller.blockers || []).map((blocker) => (
                  <div key={blocker.step_key || blocker.agent_name} className={styles.blockerCard}>
                    <strong>{blocker.agent_name || blocker.step_key}</strong>
                    <span>{blocker.error}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {(controller.repair_plan || []).length > 0 ? (
            <div className={styles.controllerListBlock}>
              <span className={styles.controllerLabel}>Repair plan</span>
              <div className={styles.tagList}>
                {(controller.repair_plan || []).map((step) => (
                  <span key={`${step.step_key}-${step.action}`} className={styles.tag}>
                    {step.agent_name}: {step.action}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

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
