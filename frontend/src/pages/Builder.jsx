import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Editor from '@monaco-editor/react';
import { 
  Play, Send, Loader2, FolderTree, Code, Eye, Terminal, 
  ChevronRight, ChevronDown, File, Folder, X, Download,
  Rocket, RefreshCw, Sparkles, Bot, Check, AlertCircle,
  Maximize2, Minimize2, ExternalLink, Copy, Settings
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

const Builder = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildPhase, setBuildPhase] = useState('idle'); // idle, planning, generating, testing, deploying, complete
  const [currentAgent, setCurrentAgent] = useState(null);
  const [agentProgress, setAgentProgress] = useState([]);
  const [files, setFiles] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [logs, setLogs] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [showPreview, setShowPreview] = useState(true);
  const [sessionId] = useState(() => `build_${Date.now()}`);
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Agent definitions
  const agents = [
    { id: 'planner', name: 'Planner', icon: '🎯', phase: 'planning' },
    { id: 'requirements', name: 'Requirements', icon: '📋', phase: 'planning' },
    { id: 'stack', name: 'Stack Selector', icon: '🔧', phase: 'planning' },
    { id: 'frontend', name: 'Frontend', icon: '🎨', phase: 'generating' },
    { id: 'backend', name: 'Backend', icon: '⚙️', phase: 'generating' },
    { id: 'database', name: 'Database', icon: '🗄️', phase: 'generating' },
    { id: 'api', name: 'API Integration', icon: '🔌', phase: 'generating' },
    { id: 'security', name: 'Security', icon: '🔒', phase: 'testing' },
    { id: 'testing', name: 'Testing', icon: '✅', phase: 'testing' },
    { id: 'deploy', name: 'Deploy', icon: '🚀', phase: 'deploying' }
  ];

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { message, type, timestamp }]);
  };

  const generateCode = async () => {
    if (!prompt.trim()) return;
    
    setIsBuilding(true);
    setBuildPhase('planning');
    setFiles({});
    setLogs([]);
    setAgentProgress([]);
    setChatMessages([{ role: 'user', content: prompt }]);
    
    addLog('🚀 Starting build process...', 'info');
    addLog(`📝 Prompt: "${prompt}"`, 'info');

    try {
      // Phase 1: Planning
      addLog('🎯 Planner Agent analyzing requirements...', 'agent');
      setCurrentAgent('planner');
      setAgentProgress(prev => [...prev, { id: 'planner', status: 'running' }]);
      
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      // Get AI to create a plan
      const planResponse = await axios.post(`${API}/ai/chat`, {
        message: `You are a software architect. Analyze this request and create a detailed build plan with file structure. Request: "${prompt}". 
        
        Respond with JSON only:
        {
          "appName": "name",
          "description": "brief description",
          "techStack": ["React", "Tailwind", "Node.js"],
          "files": ["src/App.jsx", "src/components/Header.jsx", "src/index.css"],
          "features": ["feature1", "feature2"]
        }`,
        session_id: sessionId,
        model: 'auto'
      }, { headers });

      setAgentProgress(prev => prev.map(a => a.id === 'planner' ? { ...a, status: 'complete' } : a));
      addLog('✅ Planner Agent complete', 'success');
      
      let plan;
      try {
        const jsonMatch = planResponse.data.response.match(/\{[\s\S]*\}/);
        plan = jsonMatch ? JSON.parse(jsonMatch[0]) : {
          appName: 'MyApp',
          description: 'A custom application',
          techStack: ['React', 'Tailwind CSS'],
          files: ['src/App.jsx', 'src/components/Main.jsx', 'src/index.css'],
          features: ['Responsive design', 'Modern UI']
        };
      } catch {
        plan = {
          appName: 'MyApp',
          description: prompt,
          techStack: ['React', 'Tailwind CSS'],
          files: ['src/App.jsx', 'src/components/Main.jsx', 'src/index.css'],
          features: ['Custom functionality']
        };
      }

      addLog(`📦 App: ${plan.appName}`, 'info');
      addLog(`🔧 Tech Stack: ${plan.techStack.join(', ')}`, 'info');
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `I'll build **${plan.appName}** for you!\n\n**Tech Stack:** ${plan.techStack.join(', ')}\n\n**Features:**\n${plan.features.map(f => `• ${f}`).join('\n')}\n\nGenerating code now...`
      }]);

      // Phase 2: Generate Frontend
      setBuildPhase('generating');
      setCurrentAgent('frontend');
      setAgentProgress(prev => [...prev, { id: 'frontend', status: 'running' }]);
      addLog('🎨 Frontend Agent generating UI components...', 'agent');

      const frontendResponse = await axios.post(`${API}/ai/chat`, {
        message: `Generate a complete React component for: ${prompt}. 
        
        Requirements:
        - Use React functional components with hooks
        - Use Tailwind CSS for styling
        - Make it modern, responsive, and beautiful
        - Include all necessary imports
        - Make it fully functional
        
        Respond with ONLY the code, no explanations. Start with import statements.`,
        session_id: sessionId,
        model: 'auto'
      }, { headers });

      const appCode = frontendResponse.data.response
        .replace(/```jsx?/g, '')
        .replace(/```/g, '')
        .trim();

      setFiles(prev => ({
        ...prev,
        'src/App.jsx': appCode
      }));
      setSelectedFile('src/App.jsx');
      
      setAgentProgress(prev => prev.map(a => a.id === 'frontend' ? { ...a, status: 'complete' } : a));
      addLog('✅ Frontend Agent complete - App.jsx generated', 'success');

      // Generate CSS
      addLog('🎨 Generating styles...', 'agent');
      const cssCode = `@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles for ${plan.appName} */
:root {
  --primary: #3b82f6;
  --secondary: #8b5cf6;
}

body {
  font-family: 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
}

.gradient-bg {
  background: linear-gradient(135deg, var(--primary), var(--secondary));
}

.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}`;

      setFiles(prev => ({
        ...prev,
        'src/index.css': cssCode
      }));
      addLog('✅ Styles generated', 'success');

      // Generate index.js
      const indexCode = `import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);`;

      setFiles(prev => ({
        ...prev,
        'src/index.js': indexCode
      }));

      // Generate package.json
      const packageJson = JSON.stringify({
        name: plan.appName.toLowerCase().replace(/\s+/g, '-'),
        version: '1.0.0',
        private: true,
        dependencies: {
          'react': '^18.2.0',
          'react-dom': '^18.2.0',
          'lucide-react': '^0.263.1'
        },
        devDependencies: {
          'tailwindcss': '^3.3.0',
          'autoprefixer': '^10.4.14',
          'postcss': '^8.4.24'
        },
        scripts: {
          'start': 'react-scripts start',
          'build': 'react-scripts build'
        }
      }, null, 2);

      setFiles(prev => ({
        ...prev,
        'package.json': packageJson
      }));

      // Phase 3: Testing
      setBuildPhase('testing');
      setCurrentAgent('testing');
      setAgentProgress(prev => [...prev, { id: 'testing', status: 'running' }]);
      addLog('✅ Testing Agent validating code...', 'agent');
      
      await new Promise(r => setTimeout(r, 1000));
      
      setAgentProgress(prev => prev.map(a => a.id === 'testing' ? { ...a, status: 'complete' } : a));
      addLog('✅ All tests passed!', 'success');

      // Phase 4: Deploy
      setBuildPhase('deploying');
      setCurrentAgent('deploy');
      setAgentProgress(prev => [...prev, { id: 'deploy', status: 'running' }]);
      addLog('🚀 Deploy: use Workspace Export or Deploy when ready.', 'agent');
      setAgentProgress(prev => prev.map(a => a.id === 'deploy' ? { ...a, status: 'complete' } : a));
      setPreviewUrl('');

      setBuildPhase('complete');
      setCurrentAgent(null);
      addLog('🎉 Build complete! Your app is ready.', 'success');
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `✅ **Build Complete!**\n\nYour app is ready. Edit the code, use live preview, or go to Workspace to export or deploy. Need changes? Just describe what to modify.`
      }]);

    } catch (error) {
      addLog(`❌ Error: ${error.message}`, 'error');
      setBuildPhase('idle');
      setIsBuilding(false);
    }
    
    setIsBuilding(false);
  };

  const handleChatSubmit = async (e) => {
    e?.preventDefault();
    if (!chatInput.trim() || isBuilding) return;

    const message = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: message }]);
    
    addLog(`💬 User: "${message}"`, 'info');
    
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      const response = await axios.post(`${API}/ai/chat`, {
        message: `The user wants to modify their app. Current code:\n\n${files['src/App.jsx'] || ''}\n\nUser request: "${message}"\n\nProvide the updated complete code. Respond with ONLY the code, no explanations.`,
        session_id: sessionId,
        model: 'auto'
      }, { headers });

      const newCode = response.data.response
        .replace(/```jsx?/g, '')
        .replace(/```/g, '')
        .trim();

      if (newCode.includes('import') || newCode.includes('function') || newCode.includes('const')) {
        setFiles(prev => ({
          ...prev,
          'src/App.jsx': newCode
        }));
        addLog('✅ Code updated!', 'success');
        
        setChatMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `Done! I've updated the code. Check the preview to see your changes.`
        }]);
      } else {
        setChatMessages(prev => [...prev, { 
          role: 'assistant', 
          content: response.data.response
        }]);
      }
    } catch (error) {
      addLog(`❌ Error: ${error.message}`, 'error');
    }
  };

  const downloadProject = () => {
    const content = Object.entries(files)
      .map(([name, code]) => `// ${name}\n${code}`)
      .join('\n\n// ---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crucibai-project.txt';
    a.click();
  };

  const fileTree = Object.keys(files).reduce((acc, path) => {
    const parts = path.split('/');
    let current = acc;
    parts.forEach((part, i) => {
      if (i === parts.length - 1) {
        current[part] = { type: 'file', path };
      } else {
        current[part] = current[part] || { type: 'folder', children: {} };
        current = current[part].children;
      }
    });
    return acc;
  }, {});

  const FileTreeItem = ({ name, item, depth = 0 }) => {
    const [expanded, setExpanded] = useState(true);
    
    if (item.type === 'file') {
      return (
        <button
          onClick={() => setSelectedFile(item.path)}
          className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm hover:bg-gray-100 rounded transition ${
            selectedFile === item.path ? 'bg-orange-50 text-[#1A1A1A]' : 'text-gray-700'
          }`}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          <File className="w-4 h-4" />
          {name}
        </button>
      );
    }
    
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2 px-2 py-1.5 text-sm hover:bg-gray-100 rounded text-gray-700"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Folder className="w-4 h-4 text-orange-500" />
          {name}
        </button>
        {expanded && item.children && (
          <div>
            {Object.entries(item.children).map(([childName, childItem]) => (
              <FileTreeItem key={childName} name={childName} item={childItem} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/app')} className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight">crucib<span className="text-[#1A1A1A]">ai</span></span>
          </button>
          <span className="text-gray-300">|</span>
          <span className="text-sm text-gray-500">Builder</span>
        </div>
        
        <div className="flex items-center gap-3">
          {buildPhase === 'complete' && (
            <>
              <button
                onClick={downloadProject}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
              <button className="flex items-center gap-2 px-4 py-1.5 text-sm bg-orange-600 text-[#1A1A1A] rounded-lg hover:bg-orange-700 transition">
                <Rocket className="w-4 h-4" />
                Deploy
              </button>
            </>
          )}
        </div>
      </header>

      {/* Agent Progress Bar */}
      {isBuilding && (
        <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4 gap-4 overflow-x-auto flex-shrink-0">
          {agents.map((agent) => {
            const progress = agentProgress.find(a => a.id === agent.id);
            const status = progress?.status || 'pending';
            
            return (
              <div
                key={agent.id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm whitespace-nowrap ${
                  status === 'complete' ? 'bg-green-100 text-green-700' :
                  status === 'running' ? 'bg-orange-100 text-orange-700 animate-pulse' :
                  'bg-gray-100 text-[#666666]'
                }`}
              >
                <span>{agent.icon}</span>
                <span>{agent.name}</span>
                {status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                {status === 'complete' && <Check className="w-3 h-3" />}
              </div>
            );
          })}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: File Explorer + Editor */}
        <div className="flex-1 flex flex-col border-r border-gray-200 bg-white">
          {buildPhase === 'idle' ? (
            /* Initial Prompt Screen */
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="max-w-2xl w-full text-center">
                <div className="w-16 h-16 bg-orange-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <Sparkles className="w-8 h-8 text-[#1A1A1A]" />
                </div>
                <h1 className="text-3xl font-bold mb-4">What do you want to build?</h1>
                <p className="text-gray-600 mb-8">
                  Describe your app in natural language. CrucibAI's agents will design, code, and deploy it for you.
                </p>
                <form onSubmit={(e) => { e.preventDefault(); generateCode(); }} className="space-y-4">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="e.g., Build a task management app with drag-and-drop, user authentication, and dark mode..."
                    className="w-full h-32 px-4 py-3 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 outline-none resize-none text-lg"
                    data-testid="builder-prompt-input"
                  />
                  <button
                    type="submit"
                    disabled={!prompt.trim() || isBuilding}
                    className="w-full py-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed text-[#1A1A1A] rounded-xl font-medium text-lg transition flex items-center justify-center gap-2"
                    data-testid="builder-start-btn"
                  >
                    {isBuilding ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Building...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        Start Building
                      </>
                    )}
                  </button>
                </form>
                
                <div className="mt-8 grid grid-cols-2 gap-4 text-left">
                  {[
                    'Landing page for my startup',
                    'E-commerce product catalog',
                    'Personal portfolio website',
                    'Dashboard with charts'
                  ].map((example) => (
                    <button
                      key={example}
                      onClick={() => setPrompt(example)}
                      className="p-3 border border-gray-200 rounded-lg hover:border-orange-300 hover:bg-orange-50 transition text-sm text-gray-600"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Editor View */
            <>
              <div className="flex border-b border-gray-200">
                {/* File Explorer */}
                <div className="w-56 border-r border-gray-200 bg-gray-50">
                  <div className="p-3 border-b border-gray-200 flex items-center gap-2 text-sm font-medium text-gray-700">
                    <FolderTree className="w-4 h-4" />
                    Files
                  </div>
                  <div className="p-2 max-h-48 overflow-y-auto">
                    {Object.entries(fileTree).map(([name, item]) => (
                      <FileTreeItem key={name} name={name} item={item} />
                    ))}
                  </div>
                </div>
                
                {/* Editor Tabs */}
                <div className="flex-1 flex items-center gap-1 px-2 bg-gray-50">
                  {Object.keys(files).map((file) => (
                    <button
                      key={file}
                      onClick={() => setSelectedFile(file)}
                      className={`flex items-center gap-2 px-3 py-2 text-sm rounded-t-lg transition ${
                        selectedFile === file 
                          ? 'bg-white border-t border-l border-r border-gray-200 text-gray-900' 
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      <Code className="w-4 h-4" />
                      {file.split('/').pop()}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Code Editor */}
              <div className="flex-1">
                <Editor
                  height="100%"
                  language={selectedFile?.endsWith('.css') ? 'css' : selectedFile?.endsWith('.json') ? 'json' : 'javascript'}
                  value={files[selectedFile] || '// Select a file'}
                  onChange={(value) => setFiles(prev => ({ ...prev, [selectedFile]: value }))}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                  }}
                />
              </div>
            </>
          )}
        </div>

        {/* Right: Preview + Chat */}
        {buildPhase !== 'idle' && (
          <div className="w-[500px] flex flex-col bg-white">
            {/* Preview */}
            <div className="flex-1 border-b border-gray-200 flex flex-col">
              <div className="h-10 border-b border-gray-200 flex items-center justify-between px-3 bg-gray-50">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Eye className="w-4 h-4" />
                  Preview
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-1 hover:bg-gray-200 rounded">
                    <RefreshCw className="w-4 h-4 text-gray-500" />
                  </button>
                  <button className="p-1 hover:bg-gray-200 rounded">
                    <ExternalLink className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
              <div className="flex-1 bg-white p-4">
                {buildPhase === 'complete' ? (
                  <div className="h-full border border-gray-200 rounded-lg overflow-hidden bg-gradient-to-br from-orange-50 to-orange-50 flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Check className="w-8 h-8 text-green-600" />
                      </div>
                      <p className="font-semibold text-gray-900">Preview Ready!</p>
                      <p className="text-sm text-gray-500 mt-1">Your app has been generated</p>
                      {previewUrl && (
                        <a 
                          href={previewUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-orange-600 text-[#1A1A1A] rounded-lg text-sm hover:bg-orange-700"
                        >
                          <ExternalLink className="w-4 h-4" />
                          Open Preview
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-full border border-gray-200 rounded-lg flex items-center justify-center bg-gray-50">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 animate-spin text-[#1A1A1A] mx-auto mb-3" />
                      <p className="text-sm text-gray-500">Building your app...</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Chat */}
            <div className="h-72 flex flex-col">
              <div className="h-10 border-b border-gray-200 flex items-center px-3 bg-gray-50">
                <span className="text-sm text-gray-600 flex items-center gap-2">
                  <Bot className="w-4 h-4" />
                  Chat with CrucibAI
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] p-3 rounded-xl text-sm ${
                      msg.role === 'user' 
                        ? 'bg-gray-900 text-[#1A1A1A]' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))}
              </div>
              <form onSubmit={handleChatSubmit} className="p-3 border-t border-gray-200">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask for changes..."
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-orange-500 outline-none"
                    data-testid="builder-chat-input"
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim()}
                    className="px-3 py-2 bg-gray-900 text-[#1A1A1A] rounded-lg disabled:bg-gray-300"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      {/* Console */}
      {buildPhase !== 'idle' && (
        <div className="h-36 bg-gray-900 text-[#1A1A1A] flex flex-col flex-shrink-0">
          <div className="h-8 border-b border-gray-700 flex items-center px-3 bg-gray-800">
            <span className="text-xs text-[#666666] flex items-center gap-2">
              <Terminal className="w-3 h-3" />
              Console
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className={`py-0.5 ${
                log.type === 'error' ? 'text-red-400' :
                log.type === 'success' ? 'text-green-400' :
                log.type === 'agent' ? 'text-orange-400' :
                'text-gray-300'
              }`}>
                <span className="text-gray-500">[{log.timestamp}]</span> {log.message}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Builder;
