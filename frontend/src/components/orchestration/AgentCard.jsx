import React, { useState } from 'react';
import styles from './orchestration.module.css';

const STATUS_STYLES = {
  running: { border: '#d97706', badge: 'Running' },
  complete: { border: '#16a34a', badge: 'Complete' },
  error: { border: '#dc2626', badge: 'Error' },
  queued: { border: '#6b7280', badge: 'Queued' },
};

export default function AgentCard({ agent }) {
  const [expanded, setExpanded] = useState(false);
  const tone = STATUS_STYLES[agent.status] || STATUS_STYLES.queued;

  return (
    <article className={styles.agentCard} style={{ borderLeftColor: tone.border }}>
      <button type="button" className={styles.agentCardHeader} onClick={() => setExpanded((value) => !value)}>
        <div className={styles.agentInfo}>
          <strong>{agent.name}</strong>
          <span className={styles.agentBadge} style={{ color: tone.border }}>{tone.badge}</span>
        </div>
        {agent.error ? <span className={styles.agentError}>{agent.error}</span> : null}
      </button>
      {expanded && agent.output ? (
        <pre className={styles.agentOutput}>{agent.output}</pre>
      ) : null}
    </article>
  );
}
