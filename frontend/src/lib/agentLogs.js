/**
 * Agent Logs — IndexedDB-backed persistent debug logs
 * Every event from every build is stored and searchable
 * Makes runtime telemetry visible and exportable.
 */

const DB_NAME = 'CrucibAI_AgentLogs';
const STORE = 'events';
const MAX_SESSIONS = 20;

let _db = null;

async function openDB() {
  if (_db) return _db;
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const store = req.result.createObjectStore(STORE, { keyPath: 'logId' });
      store.createIndex('sessionId', 'sessionId');
      store.createIndex('timestamp', 'timestamp');
      store.createIndex('type', 'type');
    };
    req.onsuccess = () => { _db = req.result; resolve(_db); };
    req.onerror = () => reject(req.error);
  });
}

export async function logEvent(event, sessionId) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put({
      ...event,
      logId: `${sessionId}_${event.timestamp}_${Math.random().toString(36).slice(2)}`,
      sessionId,
    });
  } catch {}
}

export async function getSessions() {
  try {
    const db = await openDB();
    return new Promise(resolve => {
      const tx = db.transaction(STORE, 'readonly');
      const idx = tx.objectStore(STORE).index('sessionId');
      const sessions = new Map();
      idx.openCursor().onsuccess = e => {
        const cursor = e.target.result;
        if (cursor) {
          const { sessionId, timestamp } = cursor.value;
          const existing = sessions.get(sessionId);
          if (!existing || timestamp > existing) sessions.set(sessionId, timestamp);
          cursor.continue();
        } else {
          resolve(
            Array.from(sessions.entries())
              .map(([id, lastEvent]) => ({ id, lastEvent }))
              .sort((a, b) => b.lastEvent - a.lastEvent)
              .slice(0, MAX_SESSIONS)
          );
        }
      };
    });
  } catch { return []; }
}

export async function getSessionEvents(sessionId) {
  try {
    const db = await openDB();
    return new Promise(resolve => {
      const events = [];
      const tx = db.transaction(STORE, 'readonly');
      tx.objectStore(STORE).index('sessionId')
        .openCursor(IDBKeyRange.only(sessionId)).onsuccess = e => {
          const cursor = e.target.result;
          if (cursor) { events.push(cursor.value); cursor.continue(); }
          else resolve(events.sort((a, b) => a.timestamp - b.timestamp));
        };
    });
  } catch { return []; }
}

export function exportSessionAsJSON(events, sessionId) {
  const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `crucibai-logs-${sessionId.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Current session ID persisted in localStorage
export function getCurrentSessionId() {
  let id = sessionStorage.getItem('crucibai_session_id');
  if (!id) {
    id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem('crucibai_session_id', id);
  }
  return id;
}
