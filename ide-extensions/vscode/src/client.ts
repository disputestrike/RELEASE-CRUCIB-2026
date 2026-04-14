"""
CrucibAI Client: API client for communicating with backend.
Handles REST calls and WebSocket connections.
"""

export class CrucibAIClient {
    private apiEndpoint: string;
    private apiKey: string;

    constructor(endpoint: string, apiKey: string = '') {
        this.apiEndpoint = endpoint;
        this.apiKey = apiKey;
    }

    async sendMessage(sessionId: string, message: string): Promise<any> {
        const response = await fetch(`${this.apiEndpoint}/api/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message,
            }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return await response.json();
    }

    async createSession(): Promise<string> {
        const response = await fetch(`${this.apiEndpoint}/api/chat/session/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
            },
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        return data.session_id;
    }

    async getSession(sessionId: string): Promise<any> {
        const response = await fetch(`${this.apiEndpoint}/api/chat/session/${sessionId}`, {
            headers: {
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
            },
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return await response.json();
    }

    async listAgents(): Promise<any[]> {
        const response = await fetch(`${this.apiEndpoint}/api/chat/agents/list`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
            },
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        return data.categories ? Object.values(data.categories).flat() : [];
    }

    async getAgentDefinition(agentName: string): Promise<any> {
        const response = await fetch(
            `${this.apiEndpoint}/api/agents/${agentName}`,
            {
                headers: {
                    ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
                },
            }
        );

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return await response.json();
    }

    async getSuggestions(sessionId: string, currentInput: string): Promise<string[]> {
        const response = await fetch(`${this.apiEndpoint}/api/chat/suggest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` }),
            },
            body: JSON.stringify({
                session_id: sessionId,
                current_input: currentInput,
            }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        return data.suggestions || [];
    }

    connectWebSocket(sessionId: string, onMessage: (msg: any) => void): WebSocket {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${this.apiEndpoint.split('://')[1]}/api/chat/ws/${sessionId}`;

        const ws = new WebSocket(wsUrl);

        ws.onmessage = event => {
            try {
                const message = JSON.parse(event.data);
                onMessage(message);
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };

        return ws;
    }
}
