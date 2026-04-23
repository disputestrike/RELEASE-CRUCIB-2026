import React from 'react';
import styles from './orchestration.module.css';

export default function ProgressBar({ progress, compact = false, color = '#2563eb' }) {
  return (
    <div className={`${styles.progressBar} ${compact ? styles.compact : ''}`}>
      <div
        className={styles.progressFill}
        style={{ width: `${Math.min(progress || 0, 100)}%`, backgroundColor: color }}
      />
    </div>
  );
}
