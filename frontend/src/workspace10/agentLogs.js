/**
 * IndexedDB persistence for agent/workspace events (debug panel).
 */

const DB_NAME = 'CrucibAI_Logs';
const STORE_NAME = 'agentEvents';
const MAX_SESSIONS = 20;

let dbPromise = null;

function openDB() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const store = database.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('sessionId', 'sessionId', { unique: false });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  return dbPromise;
}

function sessionId() {
  let sid = localStorage.getItem('agentSessionId');
  if (!sid) {
    sid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `sess_${Date.now()}`;
    localStorage.setItem('agentSessionId', sid);
  }
  return sid;
}

export async function logWorkspaceEvent(event) {
  try {
    const database = await openDB();
    const sid = sessionId();
    const id = `${sid}-${event.timestamp}-${event.type}`;
    const stored = { ...event, sessionId: sid, id };
    await new Promise((resolve, reject) => {
      const tx = database.transaction(STORE_NAME, 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE_NAME).put(stored);
    });
  } catch (e) {
    console.warn('[agentLogs]', e);
  }
}

export async function getSessions() {
  const database = await openDB();
  return new Promise((resolve, reject) => {
    const tx = database.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const map = new Map();
    const req = store.openCursor();
    req.onerror = () => reject(req.error);
    req.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        const row = cursor.value;
        const prev = map.get(row.sessionId) || 0;
        if (row.timestamp > prev) map.set(row.sessionId, row.timestamp);
        cursor.continue();
      } else {
        const sessions = Array.from(map.entries())
          .map(([id, lastEvent]) => ({ id, lastEvent }))
          .sort((a, b) => b.lastEvent - a.lastEvent)
          .slice(0, MAX_SESSIONS);
        resolve(sessions);
      }
    };
  });
}

export async function getSessionEvents(sessionIdValue) {
  const database = await openDB();
  return new Promise((resolve, reject) => {
    const tx = database.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const idx = store.index('sessionId');
    const out = [];
    const req = idx.openCursor(IDBKeyRange.only(sessionIdValue));
    req.onerror = () => reject(req.error);
    req.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        out.push(cursor.value);
        cursor.continue();
      } else {
        out.sort((a, b) => a.timestamp - b.timestamp);
        resolve(out);
      }
    };
  });
}
