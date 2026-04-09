import React, { useEffect, useRef } from 'react';
import styles from './orchestration.module.css';

const LEVEL_SYMBOL = {
  info: 'i',
  success: 'ok',
  error: 'err',
  warning: 'warn',
};

export default function LiveLog({ logs, isRunning, autoScroll, onAutoScrollToggle }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  return (
    <section className={styles.liveLogContainer}>
      <div className={styles.logHeader}>
        <strong>Live Log</strong>
        <label className={styles.logToggle}>
          <input type="checkbox" checked={autoScroll} onChange={onAutoScrollToggle} />
          Auto-scroll
        </label>
      </div>
      <div className={styles.liveLog} ref={logRef}>
        {(logs || []).length === 0 ? (
          <p className={styles.noLogs}>Waiting for build events…</p>
        ) : (
          (logs || []).map((log, idx) => (
            <div key={`${log.timestamp || 't'}-${idx}`} className={styles.logLine}>
              <span className={styles.logTime}>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '--:--:--'}</span>
              <span className={styles.logLevel}>{LEVEL_SYMBOL[log.level] || 'i'}</span>
              <span className={styles.logAgent}>{log.agent}</span>
              <span className={styles.logMessage}>{log.message}</span>
            </div>
          ))
        )}
        {isRunning ? <div className={styles.runningLine}>Running…</div> : null}
      </div>
    </section>
  );
}
