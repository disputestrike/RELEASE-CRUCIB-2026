"""
FrontendAgent: Generates complete, validated frontend code.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class FrontendAgent(BaseAgent):
    """
    Generates complete frontend code with proper structure.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
        - design_output: dict (optional, from DesignAgent)
    
    Output:
        - files: dict with file paths and content
        - structure: dict with architecture overview
        - setup_instructions: list of setup commands
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["files", "structure", "setup_instructions"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate files is a dict
        if not isinstance(result["files"], dict):
            raise AgentValidationError(f"{self.name}: files must be a dictionary")
        
        # Must include package.json
        if "package.json" not in result["files"]:
            raise AgentValidationError(f"{self.name}: Must include package.json")
        
        # Validate package.json is valid JSON
        try:
            import json
            json.loads(result["files"]["package.json"])
        except json.JSONDecodeError as e:
            raise AgentValidationError(f"{self.name}: package.json must be valid JSON: {e}")
        
        # Validate structure has required fields
        structure_fields = ["description", "entry_point", "main_components"]
        for field in structure_fields:
            if field not in result["structure"]:
                raise AgentValidationError(f"{self.name}: structure missing field '{field}'")
        
        # Validate setup_instructions is a list
        if not isinstance(result["setup_instructions"], list):
            raise AgentValidationError(f"{self.name}: setup_instructions must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        design_output = context.get("design_output", {})
        
        # Build context from previous agents
        framework = "React"
        language = "TypeScript"
        styling = "TailwindCSS"
        state_mgmt = "Context"
        
        if stack_output:
            frontend = stack_output.get("frontend", {})
            framework = frontend.get("framework", "React")
            language = frontend.get("language", "TypeScript")
            styling = frontend.get("styling", "TailwindCSS")
            state_mgmt = frontend.get("state_management", "Context")
        
        # Include design system if available
        design_info = ""
        if design_output:
            design_system = design_output.get("design_system", {})
            colors = design_system.get("colors", {})
            if colors:
                design_info = "\n\nDesign System:\n"
                design_info += f"Primary Color: {colors.get('primary', '#1A1A1A')}\n"
                design_info += f"Secondary Color: {colors.get('secondary', '#808080')}\n"
                design_info += f"Styling: {styling}"
        
        context_info = f"\n\nTechnology Context:\nFramework: {framework}\nLanguage: {language}\nStyling: {styling}\nState Management: {state_mgmt}{design_info}"
        
        system_prompt = f"""You are an expert Frontend Development agent. Your job is to generate complete, production-ready frontend code.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Generate package.json with all dependencies
2. Create main application entry point
3. Implement reusable components
4. Configure build tools (Vite/Webpack)
5. Set up styling configuration (TailwindCSS config, etc.)
6. Add proper TypeScript types and interfaces
7. Include error boundaries and loading states
8. Provide setup instructions

Output ONLY valid JSON in this exact format:
{{
  "files": {{
    "package.json": "{{\\"name\\": \\"my-app\\", \\"version\\": \\"1.0.0\\", \\"type\\": \\"module\\", \\"scripts\\": {{\\"dev\\": \\"vite\\", \\"build\\": \\"vite build\\", \\"preview\\": \\"vite preview\\"}}, \\"dependencies\\": {{\\"react\\": \\"^18.2.0\\", \\"react-dom\\": \\"^18.2.0\\", \\"react-router-dom\\": \\"^6.20.0\\", \\"zustand\\": \\"^4.4.0\\"}}, \\"devDependencies\\": {{\\"@types/react\\": \\"^18.2.0\\", \\"@vitejs/plugin-react\\": \\"^4.0.0\\", \\"typescript\\": \\"^5.0.0\\", \\"vite\\": \\"^5.0.0\\"}}}}",
    "src/main.jsx": "import React from 'react'\\nimport ReactDOM from 'react-dom/client'\\nimport App from './App'\\nimport './index.css'\\n\\nReactDOM.createRoot(document.getElementById('root')).render(\\n  <React.StrictMode>\\n    <App />\\n  </React.StrictMode>\\n)",
    "src/App.jsx": "import {{ useState }} from 'react'\\nimport {{ MemoryRouter, Routes, Route }} from 'react-router-dom'\\nimport {{ useAuthStore }} from './stores/authStore'\\nimport Header from './components/Header'\\nimport Footer from './components/Footer'\\nimport Home from './pages/Home'\\nimport {{ AuthContext }} from './context/AuthContext'\\n\\nfunction App() {{\\n  const user = useAuthStore(state => state.user)\\n  const [authState] = useState({{ user, isAuthenticated: !!user }})\\n\\n  return (\\n    <AuthContext.Provider value={{authState}}>\\n      <MemoryRouter>\\n        <div className=\\"min-h-screen bg-gray-50 flex flex-col\\">\\n          <Header />\\n          <main className=\\"flex-1 container mx-auto px-4 py-8\\">\\n            <Routes>\\n              <Route path=\\"/*\\" element={{<Home />}} />\\n            </Routes>\\n          </main>\\n          <Footer />\\n        </div>\\n      </MemoryRouter>\\n    </AuthContext.Provider>\\n  )\\n}}\\n\\nexport default App",
    "src/context/AuthContext.jsx": "import { createContext } from 'react'\\n\\nexport const AuthContext = createContext(null)",
    "src/stores/authStore.js": "import { create } from 'zustand'\\nimport { persist } from 'zustand/middleware'\\n\\nexport const useAuthStore = create(\\n  persist(\\n    (set) => ({{\\n      user: null,\\n      setUser: (user) => set({{ user }}),\\n      logout: () => set({{ user: null }})\\n    }}),\\n    {{ name: 'auth-store', storage: localStorage }}\\n  )\\n)",
    "src/pages/Home.jsx": "import {{ useState }} from 'react'\\n\\nexport default function Home() {{\\n  const [count, setCount] = useState(0)\\n\\n  return (\\n    <div>\\n      <h1 className=\\"text-4xl font-bold text-gray-900 mb-4\\">Welcome to your app</h1>\\n      <button onClick={{() => setCount(count + 1)}} className=\\"px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600\\">\\n        Count: {{count}}\\n      </button>\\n    </div>\\n  )\\n}}",
    "src/components/Header.jsx": "export default function Header() {{\\n  return (\\n    <header className=\\"bg-white shadow\\">\\n      <div className=\\"container mx-auto px-4 py-4\\">\\n        <h1 className=\\"text-2xl font-bold text-gray-900\\">My App</h1>\\n      </div>\\n    </header>\\n  )\\n}}",
    "src/components/Footer.jsx": "export default function Footer() {{\\n  return (\\n    <footer className=\\"bg-gray-800 text-white py-4 mt-8\\">\\n      <div className=\\"container mx-auto px-4 text-center\\">\\n        <p>&copy; 2024 My App. All rights reserved.</p>\\n      </div>\\n    </footer>\\n  )\\n}}",
    "src/index.css": "@tailwind base;\\n@tailwind components;\\n@tailwind utilities;",
    "tailwind.config.js": "export default {{\\n  content: ['./index.html', './src/**/*.{{js,jsx,ts,tsx}}'],\\n  theme: {{\\n    extend: {{\\n      colors: {{\\n        primary: '#1A1A1A',\\n        secondary: '#808080'\\n      }}\\n    }}\\n  }},\\n  plugins: []\\n}}",
    "vite.config.js": "import { defineConfig } from 'vite'\\nimport react from '@vitejs/plugin-react'\\n\\nexport default defineConfig({{\\n  plugins: [react()],\\n  server: {{ port: 5173 }}\\n}})",
    "tsconfig.json": "{{\\"compilerOptions\\": {{\\"target\\": \\"ES2020\\", \\"useDefineForClassFields\\": true, \\"lib\\": [\\"ES2020\\", \\"DOM\\", \\"DOM.Iterable\\"], \\"module\\": \\"ESNext\\", \\"skipLibCheck\\": true, \\"moduleResolution\\": \\"bundler\\", \\"resolveJsonModule\\": true, \\"isolatedModules\\": true, \\"noEmit\\": true, \\"jsx\\": \\"react-jsx\\", \\"strict\\": true}}, \\"include\\": [\\"src\\"], \\"exclude\\": [\\"node_modules\\"]}}", 
    "index.html": "<!DOCTYPE html>\\n<html lang=\\"en\\">\\n<head>\\n  <meta charset=\\"UTF-8\\" />\\n  <meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1.0\\" />\\n  <title>My App</title>\\n</head>\\n<body>\\n  <div id=\\"root\\"></div>\\n  <script type=\\"module\\" src=\\"/src/main.jsx\\"></script>\\n</body>\\n</html>"
  }},
  "structure": {{
    "description": "Modern React application with TypeScript and TailwindCSS. Includes routing, authentication context, persistence layer, and component-based architecture.",
    "entry_point": "src/main.jsx",
    "main_components": ["App", "Home", "Header", "Footer"],
    "routing": "React Router (MemoryRouter with Routes)",
    "state_management": "Zustand with localStorage persistence + Context API for auth",
    "auth": "AuthContext + useAuthStore (Zustand)"
  }},
  "setup_instructions": [
    "npm install",
    "npm run dev",
    "Open http://localhost:5173"
  ]
}}

Quality expectations:
- ALL files must have proper imports and exports
- MUST include react-router-dom (MemoryRouter/Routes/Route) for routing
- MUST include zustand with persist middleware for state management + localStorage
- MUST include AuthContext and useAuth pattern for authentication
- MUST have src/components/ directory with reusable components
- MUST have App.jsx/App.js as root component
- MUST have src/main.jsx with ReactDOM.createRoot
- TypeScript interfaces for props and state
- Proper component structure and naming conventions
- Responsive design with mobile-first approach (Tailwind)
- Accessible components (ARIA labels, semantic HTML)
- Error boundaries for production
- Loading and error states
- Clean, maintainable code with comments where needed"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="claude-3-5-haiku-20241022",
            temperature=0.7,
            max_tokens=6000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "claude-3-5-haiku-20241022"
        data["_agent"] = self.name
        
        return data
