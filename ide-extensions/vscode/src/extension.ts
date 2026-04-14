/**
 * Extension entry point for CrucibAI VS Code extension.
 * Manages lifecycle, panel communication, command handling, and agent/session management.
 */

import * as vscode from 'vscode';
import { ChatPanel } from './panels/ChatPanel';
import { AgentsProvider, AgentDetailsPanel } from './providers/AgentsProvider';
import { SessionsProvider, SessionManager } from './providers/SessionsProvider';
import { CrucibAIClient } from './client';

let chatPanel: ChatPanel | undefined;
let client: CrucibAIClient;
let sessionManager: SessionManager;
let agentsProvider: AgentsProvider;
let sessionsProvider: SessionsProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('🧠 CrucibAI Copilot activated');

    // Initialize client
    const config = vscode.workspace.getConfiguration('crucibai');
    client = new CrucibAIClient(
        config.get('apiEndpoint') || 'http://localhost:8000',
        config.get('apiKey') || ''
    );

    // Initialize managers and providers
    sessionManager = SessionManager.getInstance(client);
    agentsProvider = new AgentsProvider(client);
    sessionsProvider = new SessionsProvider(client);

    // Register tree data providers
    vscode.window.registerTreeDataProvider('crucibai-agents', agentsProvider);
    vscode.window.registerTreeDataProvider('crucibai-sessions', sessionsProvider);

    // Chat panel command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.openChat', async () => {
            if (!chatPanel) {
                chatPanel = new ChatPanel(context.extensionUri, client, sessionManager);
            } else {
                chatPanel.reveal();
            }
        })
    );

    // New session command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.newSession', async () => {
            try {
                const sessionId = await sessionManager.createSession('New Session');
                sessionsProvider.refresh();
                vscode.commands.executeCommand('crucibai.openChat');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to create session: ${error}`);
            }
        })
    );

    // Open session command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.openSession', async (sessionId: string) => {
            await sessionManager.setCurrentSession(sessionId);
            sessionsProvider.setActiveSession(sessionId);
            vscode.commands.executeCommand('crucibai.openChat');
        })
    );

    // View agent details
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.viewAgentDetails', (agent: any) => {
            AgentDetailsPanel.show(context.extensionUri, agent);
        })
    );

    // Code analysis command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.analyzeCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const selection = editor.selection;
                const code = editor.document.getText(selection);
                
                const sessionId = await sessionManager.createSession('Code Analysis');
                await sessionManager.setCurrentSession(sessionId);

                if (chatPanel) {
                    chatPanel.sendMessage(`Analyze this code:\n\`\`\`\n${code}\n\`\`\``);
                } else {
                    vscode.commands.executeCommand('crucibai.openChat');
                }
            }
        })
    );

    // Generate tests command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const selection = editor.selection;
                const code = editor.document.getText(selection);
                
                const sessionId = await sessionManager.createSession('Test Generation');
                await sessionManager.setCurrentSession(sessionId);

                if (chatPanel) {
                    chatPanel.sendMessage(`Generate comprehensive tests for this code:\n\`\`\`\n${code}\n\`\`\``);
                } else {
                    vscode.commands.executeCommand('crucibai.openChat');
                }
            }
        })
    );

    // Explain code command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const selection = editor.selection;
                const code = editor.document.getText(selection);
                
                const sessionId = await sessionManager.createSession('Code Explanation');
                await sessionManager.setCurrentSession(sessionId);

                if (chatPanel) {
                    chatPanel.sendMessage(`Explain this code in detail:\n\`\`\`\n${code}\n\`\`\``);
                } else {
                    vscode.commands.executeCommand('crucibai.openChat');
                }
            }
        })
    );

    // Refactor code command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.refactorCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const selection = editor.selection;
                const code = editor.document.getText(selection);
                
                const sessionId = await sessionManager.createSession('Code Refactoring');
                await sessionManager.setCurrentSession(sessionId);

                if (chatPanel) {
                    chatPanel.sendMessage(`Refactor this code for better readability and performance:\n\`\`\`\n${code}\n\`\`\``);
                } else {
                    vscode.commands.executeCommand('crucibai.openChat');
                }
            }
        })
    );

    // Fix errors command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.fixErrors', async () => {
            const sessionId = await sessionManager.createSession('Error Fixing');
            await sessionManager.setCurrentSession(sessionId);

            if (chatPanel) {
                chatPanel.sendMessage('Fix any errors in my code');
            } else {
                vscode.commands.executeCommand('crucibai.openChat');
            }
        })
    );

    // Run tests command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.runTests', async () => {
            const sessionId = await sessionManager.createSession('Test Execution');
            await sessionManager.setCurrentSession(sessionId);

            if (chatPanel) {
                chatPanel.sendMessage('Run all tests and provide a summary');
            } else {
                vscode.commands.executeCommand('crucibai.openChat');
            }
        })
    );

    // Deploy project command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.deployProject', async () => {
            const sessionId = await sessionManager.createSession('Deployment');
            await sessionManager.setCurrentSession(sessionId);

            if (chatPanel) {
                chatPanel.sendMessage('Deploy this project');
            } else {
                vscode.commands.executeCommand('crucibai.openChat');
            }
        })
    );

    // List agents command
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.listAgents', async () => {
            try {
                const agents = await client.listAgents();
                const agentNames = agents.map((a: any) => a.name || a.id);
                const selected = await vscode.window.showQuickPick(agentNames);
                if (selected) {
                    const agent = agents.find((a: any) => (a.name || a.id) === selected);
                    if (agent) {
                        AgentDetailsPanel.show(context.extensionUri, agent);
                    }
                }
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to list agents: ${error}`);
            }
        })
    );

    // Refresh agents
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.refreshAgents', () => {
            agentsProvider.refresh();
        })
    );

    // Clear sessions
    context.subscriptions.push(
        vscode.commands.registerCommand('crucibai.clearSessions', async () => {
            const confirmed = await vscode.window.showWarningMessage(
                'Clear all sessions?',
                { modal: true },
                'Clear'
            );

            if (confirmed === 'Clear') {
                const sessions = sessionManager.getAllSessions();
                sessions.forEach(session => sessionManager.deleteSession(session.id));
                sessionsProvider.refresh();
                vscode.window.showInformationMessage('Sessions cleared');
            }
        })
    );

    // Watch configuration changes
    vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration('crucibai')) {
            const newConfig = vscode.workspace.getConfiguration('crucibai');
            client = new CrucibAIClient(
                newConfig.get('apiEndpoint') || 'http://localhost:8000',
                newConfig.get('apiKey') || ''
            );
            vscode.window.showInformationMessage('CrucibAI configuration updated');
        }
    });

    console.log('✅ CrucibAI extension fully initialized with', agentsProvider.getAgentCount?.() || '?', 'agents');
}

export function deactivate() {
    if (chatPanel) {
        chatPanel.dispose();
    }
}
