/**
 * EventBus — unified WebSocket + event emitter
 * Connects to /ws/events?jobId=X and dispatches typed events to subscribers
 */
class EventBus {
  constructor() {
    this.listeners = new Map(); // eventType -> Set<fn>
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnects = 5;
    this.subscribedJobs = new Set();
    this._sessionId = null;
  }

  connect(baseUrl) {
    const wsUrl = (baseUrl || '').replace('https://', 'wss://').replace('http://', 'ws://');
    try {
      this.ws = new WebSocket(`${wsUrl}/ws/events`);
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.subscribedJobs.forEach(id => this._send({ action: 'subscribe', jobId: id }));
      };
      this.ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          this._dispatch(event.type, event);
          this._dispatch('*', event);
        } catch {}
      };
      this.ws.onclose = () => {
        if (this.reconnectAttempts < this.maxReconnects) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(baseUrl),
            Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000));
        }
      };
    } catch {}
  }

  subscribe(jobId) {
    this.subscribedJobs.add(jobId);
    this._send({ action: 'subscribe', jobId });
  }

  unsubscribe(jobId) {
    this.subscribedJobs.delete(jobId);
    this._send({ action: 'unsubscribe', jobId });
  }

  on(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type).add(fn);
    return () => this.off(type, fn);
  }

  off(type, fn) {
    this.listeners.get(type)?.delete(fn);
  }

  emitLocal(event) {
    this._dispatch(event.type, event);
    this._dispatch('*', event);
  }

  emitEvent(event) {
    this._send(event);
    this.emitLocal(event);
  }

  _dispatch(type, event) {
    this.listeners.get(type)?.forEach(fn => { try { fn(event); } catch {} });
  }

  _send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify(data)); } catch {}
    }
  }

  disconnect() { this.ws?.close(); }
}

export const eventBus = new EventBus();
export default eventBus;
