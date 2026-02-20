/**
 * CollaborativeEditingService.js
 * Real-time collaborative editing using Yjs
 * Handles conflict resolution, CRDT synchronization, and multi-user editing
 */

import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

class CollaborativeEditingService {
  constructor() {
    this.ydoc = null;
    this.ytext = null;
    this.provider = null;
    this.awareness = null;
    this.files = new Map(); // fileName -> YText
    this.listeners = {};
    this.isConnected = false;
    this.userId = null;
    this.userName = null;
  }

  /**
   * Initialize collaborative editing
   */
  init(projectId, userId, userName) {
    this.userId = userId;
    this.userName = userName;

    // Create Yjs document
    this.ydoc = new Y.Doc();

    // Create WebSocket provider for real-time sync
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}`;

    this.provider = new WebsocketProvider(
      wsUrl,
      `crucibai-${projectId}`,
      this.ydoc
    );

    // Setup awareness (for cursors, selections, etc.)
    this.awareness = this.provider.awareness;
    this.setupAwareness();

    // Listen for provider events
    this.provider.on('status', (event) => {
      this.isConnected = event.status === 'connected';
      this.emit('connection_status', { connected: this.isConnected });
    });

    this.provider.on('sync', (isSynced) => {
      this.emit('synced', { synced: isSynced });
    });
  }

  /**
   * Setup awareness for presence and cursors
   */
  setupAwareness() {
    const color = this.getRandomColor();
    const userInfo = {
      user: {
        name: this.userName,
        color,
        id: this.userId,
      },
    };

    this.awareness.setLocalState(userInfo);

    // Listen for awareness changes
    this.awareness.on('change', (changes) => {
      changes.added.forEach(clientID => {
        const state = this.awareness.getStates().get(clientID);
        if (state) {
          this.emit('user_joined', {
            clientID,
            user: state.user,
          });
        }
      });

      changes.updated.forEach(clientID => {
        const state = this.awareness.getStates().get(clientID);
        if (state) {
          this.emit('user_updated', {
            clientID,
            user: state.user,
          });
        }
      });

      changes.removed.forEach(clientID => {
        this.emit('user_left', { clientID });
      });
    });
  }

  /**
   * Get or create shared text for a file
   */
  getSharedText(fileName) {
    if (this.files.has(fileName)) {
      return this.files.get(fileName);
    }

    const ytext = this.ydoc.getText(fileName);
    this.files.set(fileName, ytext);

    // Listen for changes
    ytext.observe((event) => {
      this.emit('file_changed', {
        fileName,
        changes: event.changes,
        content: ytext.toString(),
      });
    });

    return ytext;
  }

  /**
   * Set file content
   */
  setFileContent(fileName, content) {
    const ytext = this.getSharedText(fileName);
    ytext.delete(0, ytext.length);
    ytext.insert(0, content);
  }

  /**
   * Get file content
   */
  getFileContent(fileName) {
    const ytext = this.getSharedText(fileName);
    return ytext.toString();
  }

  /**
   * Insert text at position
   */
  insertText(fileName, index, text) {
    const ytext = this.getSharedText(fileName);
    ytext.insert(index, text);
  }

  /**
   * Delete text range
   */
  deleteText(fileName, index, length) {
    const ytext = this.getSharedText(fileName);
    ytext.delete(index, length);
  }

  /**
   * Update user cursor position
   */
  updateCursor(fileName, line, column, selection = null) {
    const state = this.awareness.getLocalState() || {};
    state.cursor = {
      fileName,
      line,
      column,
      selection,
    };
    this.awareness.setLocalState(state);
  }

  /**
   * Get all connected users
   */
  getConnectedUsers() {
    const users = [];
    this.awareness.getStates().forEach((state, clientID) => {
      if (state.user && clientID !== this.awareness.clientID) {
        users.push({
          clientID,
          ...state.user,
          cursor: state.cursor,
        });
      }
    });
    return users;
  }

  /**
   * Get user by client ID
   */
  getUser(clientID) {
    const state = this.awareness.getStates().get(clientID);
    return state ? state.user : null;
  }

  /**
   * Get all file names
   */
  getFileNames() {
    return Array.from(this.files.keys());
  }

  /**
   * Delete file
   */
  deleteFile(fileName) {
    this.files.delete(fileName);
    this.ydoc.getMap().delete(fileName);
  }

  /**
   * Get undo manager for undo/redo
   */
  getUndoManager(fileName) {
    const ytext = this.getSharedText(fileName);
    return new Y.UndoManager([ytext]);
  }

  /**
   * Export document as JSON
   */
  exportAsJSON() {
    const data = {};
    this.files.forEach((ytext, fileName) => {
      data[fileName] = ytext.toString();
    });
    return data;
  }

  /**
   * Import document from JSON
   */
  importFromJSON(data) {
    Object.entries(data).forEach(([fileName, content]) => {
      this.setFileContent(fileName, content);
    });
  }

  /**
   * Get random color for user
   */
  getRandomColor() {
    const colors = [
      '#808080', '#999999', '#AAAAAA', '#BBBBBB', '#CCCCCC',
      '#DDDDDD', '#808080', '#999999', '#AAAAAA', '#BBBBBB',
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  /**
   * Register event listener
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  /**
   * Unregister event listener
   */
  off(event, callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
  }

  /**
   * Emit event
   */
  emit(event, data) {
    if (!this.listeners[event]) return;
    this.listeners[event].forEach(callback => callback(data));
  }

  /**
   * Disconnect
   */
  disconnect() {
    if (this.provider) {
      this.provider.disconnect();
      this.provider = null;
    }
    if (this.ydoc) {
      this.ydoc.destroy();
      this.ydoc = null;
    }
    this.files.clear();
    this.isConnected = false;
  }
}

export default new CollaborativeEditingService();
