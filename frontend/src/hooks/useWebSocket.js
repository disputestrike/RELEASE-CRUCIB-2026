import { useCallback, useEffect, useRef, useState } from 'react';

export function useWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);
  const reconnectRef = useRef(0);
  const timerRef = useRef(null);
  const maxReconnects = 5;

  const connect = useCallback(() => {
    if (!url) {
      return;
    }
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${url}`;
      socketRef.current = new WebSocket(wsUrl);

      socketRef.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectRef.current = 0;
      };

      socketRef.current.onmessage = (event) => {
        if (event.data === 'pong') {
          return;
        }
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          setLastMessage({ type: 'raw', payload: event.data });
        }
      };

      socketRef.current.onerror = () => {
        setError('Connection error');
      };

      socketRef.current.onclose = () => {
        setIsConnected(false);
        if (reconnectRef.current >= maxReconnects) {
          setError('Connection lost. Please refresh.');
          return;
        }
        reconnectRef.current += 1;
        const delay = Math.min(1000 * (2 ** reconnectRef.current), 10000);
        timerRef.current = window.setTimeout(connect, delay);
      };
    } catch (err) {
      setError(err?.message || 'WebSocket setup failed');
    }
  }, [url]);

  useEffect(() => {
    if (!url) {
      return () => {};
    }
    connect();
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }, []);

  return {
    lastMessage,
    isConnected,
    error,
    sendMessage,
  };
}
