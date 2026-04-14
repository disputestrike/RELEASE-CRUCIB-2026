/**
 * Chat Panel: Webview panel for conversational chat in VS Code.
 * Displays the CrucibAI chat interface and handles message exchange.
 */

import * as vscode from 'vscode';
import { CrucibAIClient } from '../client';
import { SessionManager } from '../providers/SessionsProvider';

export class ChatPanel {
    public static readonly viewType = 'crucibaiChat';
    private static currentPanel: ChatPanel | undefined;
    
    private _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _client: CrucibAIClient;
    private _sessionManager: SessionManager;
    private _sessionId: string | undefined;
    private _extensionUri: vscode.Uri;

    public static render(extensionUri: vscode.Uri, client?: CrucibAIClient, sessionManager?: SessionManager) {
        if (ChatPanel.currentPanel) {
            ChatPanel.currentPanel._panel.reveal(vscode.ViewColumn.Two);
            return;
        }

        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        const panel = vscode.window.createWebviewPanel(
            ChatPanel.viewType,
            '🧠 CrucibAI Chat',
            column || vscode.ViewColumn.Two,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        ChatPanel.currentPanel = new ChatPanel(panel, extensionUri, client, sessionManager);
    }

    constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        client?: CrucibAIClient,
        sessionManager?: SessionManager
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._client = client || new CrucibAIClient('http://localhost:8000');
        this._sessionManager = sessionManager || SessionManager.getInstance(this._client);

        this._panel.webview.html = this._getHtmlContent();
        this._setupMessageHandling();

        this._panel.onDidDispose(
            () => {
                ChatPanel.currentPanel = undefined;
                this._panel.dispose();
                while (this._disposables.length) {
                    const x = this._disposables.pop();
                    if (x) {
                        x.dispose();
                    }
                }
            },
            null,
            this._disposables
        );
    }

    private _getHtmlContent(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>CrucibAI Chat</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                        height: 100vh;
                        display: flex;
                        flex-direction: column;
                    }
                    .header {
                        padding: 12px 16px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                        background: var(--vscode-sideBar-background);
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }
                    .header h3 { margin: 0; }
                    .session-info {
                        font-size: 0.85em;
                        opacity: 0.7;
                    }
                    .messages {
                        flex: 1;
                        overflow-y: auto;
                        padding: 16px;
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                    }
                    .message {
                        padding: 12px;
                        border-radius: 6px;
                        max-width: 90%;
                        line-height: 1.5;
                        word-wrap: break-word;
                    }
                    .message.user {
                        background: var(--vscode-inputOption-activeBorder);
                        color: var(--vscode-editor-foreground);
                        margin-left: auto;
                        text-align: right;
                    }
                    .message.assistant {
                        background: var(--vscode-editor-findMatchHighlightBackground);
                        color: var(--vscode-editor-foreground);
                        margin-right: auto;
                    }
                    .message.error {
                        background: var(--vscode-notificationCenter-border);
                        color: var(--vscode-errorForeground);
                    }
                    .input-area {
                        padding: 12px;
                        border-top: 1px solid var(--vscode-panel-border);
                        display: flex;
                        gap: 8px;
                    }
                    input {
                        flex: 1;
                        padding: 8px 12px;
                        background: var(--vscode-input-background);
                        color: var(--vscode-input-foreground);
                        border: 1px solid var(--vscode-input-border);
                        border-radius: 4px;
                        font-family: inherit;
                    }
                    input:focus {
                        outline: none;
                        border-color: var(--vscode-focusBorder);
                    }
                    button {
                        padding: 8px 16px;
                        background: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 500;
                    }
                    button:hover {
                        background: var(--vscode-button-hoverBackground);
                    }
                    .typing {
                        display: flex;
                        gap: 4px;
                    }
                    .typing span {
                        width: 6px;
                        height: 6px;
                        background: var(--vscode-editor-foreground);
                        border-radius: 50%;
                        animation: typing 1.2s infinite;
                    }
                    .typing span:nth-child(2) { animation-delay: 0.2s; }
                    .typing span:nth-child(3) { animation-delay: 0.4s; }
                    @keyframes typing {
                        0%, 60%, 100% { opacity: 0.3; }
                        30% { opacity: 1; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h3>🧠 CrucibAI Copilot</h3>
                    <span class="session-info" id="sessionInfo">Session: Loading...</span>
                </div>
                <div class="messages" id="messages"></div>
                <div class="input-area">
                    <input type="text" id="input" placeholder="Ask me anything..." autofocus/>
                    <button id="send">Send</button>
                </div>

                <script>
                    const vscode = acquireVsCodeApi();
                    const input = document.getElementById('input');
                    const send = document.getElementById('send');
                    const messages = document.getElementById('messages');
                    const sessionInfo = document.getElementById('sessionInfo');

                    send.onclick = sendMessage;
                    input.addEventListener('keypress', e => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            sendMessage();
                        }
                    });

                    window.addEventListener('message', event => {
                        const msg = event.data;
                        if (
                            msg.type === 'message' ||
                            msg.type === 'response' ||
                            msg.type === 'status' ||
                            msg.type === 'reasoning' ||
                            msg.type === 'clarification'
                        ) {
                            addMessage(msg.content, 'assistant');
                        } else if (msg.type === 'error') {
                            addMessage(msg.content, 'error');
                        } else if (msg.type === 'sessionInfo') {
                            sessionInfo.textContent = 'Session: ' + msg.sessionId.substr(0, 12) + '...';
                        } else if (msg.type === 'typing') {
                            showTypingIndicator();
                        }
                    });

                    function sendMessage() {
                        const text = input.value.trim();
                        if (!text) return;

                        addMessage(text, 'user');
                        vscode.postMessage({ type: 'message', content: text });
                        input.value = '';
                    }

                    function addMessage(text, role) {
                        const div = document.createElement('div');
                        div.className = 'message ' + role;
                        
                        if (role === 'assistant') {
                            div.innerHTML = text;
                        } else {
                            div.textContent = text;
                        }
                        
                        messages.appendChild(div);
                        messages.scrollTop = messages.scrollHeight;
                    }

                    function showTypingIndicator() {
                        const div = document.createElement('div');
                        div.className = 'message assistant';
                        div.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
                        div.id = 'typing';
                        messages.appendChild(div);
                        messages.scrollTop = messages.scrollHeight;
                    }
                </script>
            </body>
            </html>
        `;
    }

    private _setupMessageHandling() {
        this._panel.webview.onDidReceiveMessage(
            async message => {
                if (message.type === 'message') {
                    try {
                        // Create session if needed
                        if (!this._sessionId) {
                            this._sessionId = await this._sessionManager.createSession('Chat Session');
                            this._panel.webview.postMessage({
                                type: 'sessionInfo',
                                sessionId: this._sessionId,
                            });
                        }

                        // Show typing indicator
                        this._panel.webview.postMessage({ type: 'typing' });

                        // Send message
                        const response = await this._client.sendMessage(
                            this._sessionId,
                            message.content
                        );

                        // Store message in session
                        this._sessionManager.addMessageToSession(this._sessionId, {
                            id: `msg_${Date.now()}`,
                            role: 'user',
                            content: message.content,
                            timestamp: new Date().toISOString(),
                        });

                        this._sessionManager.addMessageToSession(this._sessionId, {
                            id: `msg_${Date.now()}_resp`,
                            role: 'assistant',
                            content: response.assistant_response || response.response || 'No response',
                            timestamp: new Date().toISOString(),
                        });

                        // Display response
                        this._panel.webview.postMessage({
                            type: 'response',
                            content: response.assistant_response || response.response || 'No response',
                        });
                    } catch (error) {
                        this._panel.webview.postMessage({
                            type: 'error',
                            content: `Error: ${error}`,
                        });
                    }
                }
            },
            undefined,
            this._disposables
        );
    }

    public sendMessage(message: string) {
        this._panel.webview.postMessage({
            type: 'message',
            content: message,
        });
        this._panel.reveal();
    }

    public reveal() {
        this._panel.reveal(vscode.ViewColumn.Two);
    }

    public dispose() {
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}
