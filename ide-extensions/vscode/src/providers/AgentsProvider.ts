import * as vscode from 'vscode';
import { CrucibAIClient } from './client';

export class AgentTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly agentData?: any,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);
        
        if (agentData) {
            this.tooltip = agentData.description || agentData.purpose;
            this.description = agentData.category;
        }
    }
}

export class AgentsProvider implements vscode.TreeDataProvider<AgentTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AgentTreeItem | undefined | null | void> =
        new vscode.EventEmitter<AgentTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AgentTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private agents: any[] = [];
    private categories: Map<string, any[]> = new Map();
    private client: CrucibAIClient;

    constructor(client: CrucibAIClient) {
        this.client = client;
        this.refresh();
    }

    refresh(): void {
        this.loadAgents();
        this._onDidChangeTreeData.fire(null);
    }

    private async loadAgents(): Promise<void> {
        try {
            this.agents = await this.client.listAgents();
            this.categories.clear();

            for (const agent of this.agents) {
                const category = agent.category || 'Uncategorized';
                if (!this.categories.has(category)) {
                    this.categories.set(category, []);
                }
                this.categories.get(category)!.push(agent);
            }

            // Sort categories and agents within each category
            this.categories = new Map(
                Array.from(this.categories.entries()).sort((a, b) => a[0].localeCompare(b[0]))
            );

            for (const agents of this.categories.values()) {
                agents.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to load agents: ${error}`);
        }
    }

    getTreeItem(element: AgentTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: AgentTreeItem): Promise<AgentTreeItem[]> {
        if (!element) {
            // Return root categories
            return Array.from(this.categories.keys()).map(category => {
                const agentCount = this.categories.get(category)?.length || 0;
                return new AgentTreeItem(
                    `${category} (${agentCount})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    { category }
                );
            });
        }

        // Return agents in this category
        const category = element.label.split(' (')[0]; // Extract category name
        const agents = this.categories.get(category) || [];

        return agents.map(agent => {
            return new AgentTreeItem(
                agent.name || agent.id,
                vscode.TreeItemCollapsibleState.None,
                agent,
                {
                    title: 'View Agent Details',
                    command: 'crucibai.viewAgentDetails',
                    arguments: [agent],
                }
            );
        });
    }
}

export class AgentDetailsPanel {
    public static currentPanel: AgentDetailsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static show(
        extensionUri: vscode.Uri,
        agent: any
    ): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (AgentDetailsPanel.currentPanel) {
            AgentDetailsPanel.currentPanel._panel.reveal(column);
            AgentDetailsPanel.currentPanel.update(agent);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'agentDetails',
            `Agent: ${agent.name || agent.id}`,
            column || vscode.ViewColumn.One,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        AgentDetailsPanel.currentPanel = new AgentDetailsPanel(panel, extensionUri, agent);
    }

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        agent: any
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this.update(agent);

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public dispose(): void {
        AgentDetailsPanel.currentPanel = undefined;
        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private update(agent: any): void {
        this._panel.webview.html = this.getWebviewContent(agent);
    }

    private getWebviewContent(agent: any): string {
        const capabilities = (agent.capabilities || [])
            .map((cap: string) => `<li>${cap}</li>`)
            .join('');

        const parameters = (agent.parameters || [])
            .map((param: any) => `<li><code>${param.name}</code> (${param.type}): ${param.description}</li>`)
            .join('');

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        padding: 20px;
                        color: var(--vscode-foreground);
                        background-color: var(--vscode-editor-background);
                    }
                    h1 { margin-top: 0; color: var(--vscode-symbolIcon-classForeground); }
                    h2 { color: var(--vscode-symbolIcon-methodForeground); margin-top: 20px; }
                    .metadata {
                        display: grid;
                        grid-template-columns: auto 1fr;
                        gap: 10px;
                        margin-bottom: 20px;
                        padding: 10px;
                        background-color: var(--vscode-editor-lineHighlightBackground);
                        border-radius: 4px;
                    }
                    .metadata-key {
                        font-weight: bold;
                        color: var(--vscode-symbolIcon-keywordForeground);
                    }
                    ul { margin: 10px 0; padding-left: 20px; }
                    li { margin: 5px 0; }
                    code {
                        background-color: var(--vscode-textCodeBlock-background);
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    }
                    .button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 10px;
                    }
                    .button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }
                </style>
            </head>
            <body>
                <h1>${agent.name || agent.id}</h1>
                
                <div class="metadata">
                    <div class="metadata-key">Category:</div>
                    <div>${agent.category || 'Unknown'}</div>
                    
                    <div class="metadata-key">Status:</div>
                    <div>${agent.status || 'Active'}</div>
                    
                    <div class="metadata-key">Phase:</div>
                    <div>${agent.phase || 'N/A'}</div>
                </div>

                <h2>Description</h2>
                <p>${agent.description || agent.purpose || 'No description available'}</p>

                ${capabilities ? `
                <h2>Capabilities</h2>
                <ul>${capabilities}</ul>
                ` : ''}

                ${parameters ? `
                <h2>Parameters</h2>
                <ul>${parameters}</ul>
                ` : ''}

                ${agent.dependencies ? `
                <h2>Dependencies</h2>
                <pre>${JSON.stringify(agent.dependencies, null, 2)}</pre>
                ` : ''}

                <button class="button" onclick="alert('Launch ${agent.name} functionality')">
                    Launch Agent
                </button>
            </body>
            </html>
        `;
    }
}
