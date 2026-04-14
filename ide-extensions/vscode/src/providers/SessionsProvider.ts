import * as vscode from 'vscode';
import { CrucibAIClient } from './client';

export class SessionTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState = vscode.TreeItemCollapsibleState.None,
        public readonly sessionData?: any,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);
        
        if (sessionData) {
            this.iconPath = new vscode.ThemeIcon('chat');
            this.contextValue = 'session';
        }
    }
}

export class SessionsProvider implements vscode.TreeDataProvider<SessionTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<SessionTreeItem | undefined | null | void> =
        new vscode.EventEmitter<SessionTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<SessionTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private sessions: any[] = [];
    private client: CrucibAIClient;
    private activeSessionId: string | undefined;

    constructor(client: CrucibAIClient) {
        this.client = client;
        this.loadSessions();
        
        // Refresh sessions periodically
        setInterval(() => this.refresh(), 30000);
    }

    refresh(): void {
        this.loadSessions();
        this._onDidChangeTreeData.fire(null);
    }

    private async loadSessions(): Promise<void> {
        try {
            // Sessions are stored in localStorage or backend
            const sessionList = this.getStoredSessions();
            this.sessions = sessionList;
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    }

    private getStoredSessions(): any[] {
        // Retrieve from VS Code workspace state or local storage
        const stored = globalThis['crucibaiSessions'] || [];
        return stored
            .sort((a: any, b: any) => 
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            )
            .slice(0, 20); // Keep last 20 sessions
    }

    addSession(session: any): void {
        if (!globalThis['crucibaiSessions']) {
            globalThis['crucibaiSessions'] = [];
        }
        globalThis['crucibaiSessions'].push(session);
        this.refresh();
    }

    setActiveSession(sessionId: string): void {
        this.activeSessionId = sessionId;
        this.refresh();
    }

    getActiveSession(): string | undefined {
        return this.activeSessionId;
    }

    getTreeItem(element: SessionTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: SessionTreeItem): SessionTreeItem[] {
        if (!element) {
            // Return list of sessions
            return this.sessions.map(session => {
                const title = session.title || `Session ${session.id.substr(0, 8)}`;
                const isActive = session.id === this.activeSessionId;
                
                return new SessionTreeItem(
                    isActive ? `● ${title}` : title,
                    vscode.TreeItemCollapsibleState.None,
                    session,
                    {
                        title: 'Open Session',
                        command: 'crucibai.openSession',
                        arguments: [session.id],
                    }
                );
            });
        }
        return [];
    }
}

export class SessionManager {
    private static instance: SessionManager;
    private currentSessionId: string | undefined;
    private sessionStorage: Map<string, SessionData> = new Map();
    private client: CrucibAIClient;

    private constructor(client: CrucibAIClient) {
        this.client = client;
    }

    static getInstance(client: CrucibAIClient): SessionManager {
        if (!SessionManager.instance) {
            SessionManager.instance = new SessionManager(client);
        }
        return SessionManager.instance;
    }

    async createSession(title?: string): Promise<string> {
        try {
            const sessionId = await this.client.createSession();
            
            const session: SessionData = {
                id: sessionId,
                title: title || `Session ${new Date().toLocaleTimeString()}`,
                created_at: new Date().toISOString(),
                messages: [],
                metadata: {},
            };

            this.sessionStorage.set(sessionId, session);
            this.currentSessionId = sessionId;

            // Persist to global storage
            if (!globalThis['crucibaiSessions']) {
                globalThis['crucibaiSessions'] = [];
            }
            globalThis['crucibaiSessions'].push(session);

            return sessionId;
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to create session: ${error}`);
            throw error;
        }
    }

    async getCurrentSession(): Promise<SessionData | undefined> {
        if (!this.currentSessionId) {
            return undefined;
        }
        return this.sessionStorage.get(this.currentSessionId);
    }

    async setCurrentSession(sessionId: string): Promise<void> {
        this.currentSessionId = sessionId;
    }

    addMessageToSession(sessionId: string, message: MessageData): void {
        const session = this.sessionStorage.get(sessionId);
        if (session) {
            session.messages.push(message);
            // Limit messages in memory
            if (session.messages.length > 100) {
                session.messages = session.messages.slice(-50);
            }
        }
    }

    getSessionMessages(sessionId: string): MessageData[] {
        const session = this.sessionStorage.get(sessionId);
        return session ? session.messages : [];
    }

    getAllSessions(): SessionData[] {
        return Array.from(this.sessionStorage.values());
    }

    deleteSession(sessionId: string): void {
        this.sessionStorage.delete(sessionId);
        if (this.currentSessionId === sessionId) {
            this.currentSessionId = undefined;
        }
        
        // Remove from global storage
        if (globalThis['crucibaiSessions']) {
            globalThis['crucibaiSessions'] = globalThis['crucibaiSessions'].filter(
                (s: any) => s.id !== sessionId
            );
        }
    }
}

export interface SessionData {
    id: string;
    title: string;
    created_at: string;
    messages: MessageData[];
    metadata: Record<string, any>;
}

export interface MessageData {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    agentUsed?: string;
    metadata?: Record<string, any>;
}
