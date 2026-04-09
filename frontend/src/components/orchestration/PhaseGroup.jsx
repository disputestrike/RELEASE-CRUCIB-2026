import React from 'react';
import AgentCard from './AgentCard';
import ProgressBar from './ProgressBar';
import styles from './orchestration.module.css';

const STATUS_COLORS = {
  complete: '#16a34a',
  running: '#d97706',
  queued: '#6b7280',
  error: '#dc2626',
};

const STATUS_ICON = {
  complete: 'OK',
  running: 'RUN',
  queued: 'Q',
  error: 'ERR',
};

export default function PhaseGroup({ phase, isExpanded, onToggle }) {
  const tone = STATUS_COLORS[phase.status] || STATUS_COLORS.queued;

  return (
    <section className={`${styles.phaseGroup} ${isExpanded ? styles.expanded : ''}`} style={{ borderLeftColor: tone }}>
      <button type="button" className={styles.phaseHeader} onClick={onToggle}>
        <div className={styles.phaseTitle}>
          <span className={styles.statusIcon} style={{ color: tone }}>{STATUS_ICON[phase.status] || STATUS_ICON.queued}</span>
          <strong>{phase.name}</strong>
          <span className={styles.phaseStats}>({phase.completed}/{phase.total})</span>
        </div>
        <div className={styles.phaseProgress}>
          <ProgressBar progress={phase.progress} compact color={tone} />
          <span className={styles.progressPercent}>{phase.progress}%</span>
        </div>
      </button>
      {isExpanded && (
        <div className={styles.agentsContainer}>
          {(phase.agents || []).length === 0 ? (
            <div className={styles.emptyAgents}>No agents in this phase yet.</div>
          ) : (
            (phase.agents || []).map((agent, idx) => (
              <AgentCard key={agent.id || `${phase.id}-${idx}`} agent={agent} />
            ))
          )}
        </div>
      )}
    </section>
  );
}
