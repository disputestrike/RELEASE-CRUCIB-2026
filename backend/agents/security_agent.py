"""
SecurityAgent: Security audit, vulnerability scanning, and fixes.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class SecurityAgent(BaseAgent):
    """
    Performs security audit and provides fixes.
    
    Input:
        - user_prompt: str
        - frontend_output: dict (optional, from FrontendAgent)
        - backend_output: dict (optional, from BackendAgent)
    
    Output:
        - vulnerabilities: list of vulnerability findings
        - security_config: dict with security configurations
        - security_score: str
        - recommendations: list of security recommendations
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["vulnerabilities", "security_config", "security_score", "recommendations"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate vulnerabilities is a list
        if not isinstance(result["vulnerabilities"], list):
            raise AgentValidationError(f"{self.name}: vulnerabilities must be a list")
        
        # Validate security_config is a dict
        if not isinstance(result["security_config"], dict):
            raise AgentValidationError(f"{self.name}: security_config must be a dictionary")
        
        # Validate recommendations is a list
        if not isinstance(result["recommendations"], list):
            raise AgentValidationError(f"{self.name}: recommendations must be a list")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        frontend_output = context.get("frontend_output", {})
        backend_output = context.get("backend_output", {})
        
        # Build context from code outputs
        context_info = ""
        if frontend_output:
            files = frontend_output.get("files", {})
            context_info += "\n\nFrontend Code Review:\n"
            for filename in list(files.keys())[:3]:  # Sample a few files
                context_info += f"- {filename}\n"
        
        if backend_output:
            files = backend_output.get("files", {})
            context_info += "\n\nBackend Code Review:\n"
            api_spec = backend_output.get("api_spec", {})
            endpoints = api_spec.get("endpoints", [])
            context_info += f"- {len(endpoints)} API endpoints to secure\n"
            for filename in list(files.keys())[:3]:
                context_info += f"- {filename}\n"
        
        system_prompt = f"""You are an expert Security Audit agent. Your job is to identify vulnerabilities and provide security recommendations.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Identify common security vulnerabilities (OWASP Top 10)
2. Check for SQL injection, XSS, CSRF, etc.
3. Review authentication and authorization
4. Audit API security (rate limiting, input validation)
5. Check for exposed secrets and sensitive data
6. Provide security configuration recommendations
7. Generate fixed code for identified issues

Common vulnerabilities to check:
- SQL Injection
- Cross-Site Scripting (XSS)
- Cross-Site Request Forgery (CSRF)
- Insecure Direct Object References
- Security Misconfiguration
- Sensitive Data Exposure
- Missing Function Level Access Control
- Using Components with Known Vulnerabilities
- Insufficient Logging & Monitoring

Output ONLY valid JSON in this exact format:
{{
  "vulnerabilities": [
    {{
      "severity": "high|medium|low",
      "type": "SQL Injection",
      "location": "routes/users.py:line 42",
      "description": "User input directly concatenated into SQL query without sanitization",
      "fix": "Use parameterized queries or ORM methods",
      "fixed_code": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
    }},
    {{
      "severity": "medium",
      "type": "Missing CORS Configuration",
      "location": "main.py:line 10",
      "description": "CORS allows all origins (*) which may expose API to unauthorized domains",
      "fix": "Restrict CORS to specific trusted origins",
      "fixed_code": "app.add_middleware(CORSMiddleware, allow_origins=['https://yourdomain.com'])"
    }}
  ],
  "security_config": {{
    "cors_settings": "app.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=['https://yourdomain.com'],\\n    allow_credentials=True,\\n    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\\n    allow_headers=['*'],\\n    max_age=3600\\n)",
    "helmet_config": "// For Express.js\\nconst helmet = require('helmet')\\napp.use(helmet())\\napp.use(helmet.contentSecurityPolicy({{\\n  directives: {{\\n    defaultSrc: [\\"'self'\\"],\\n    styleSrc: [\\"'self'\\", \\"'unsafe-inline'\\"],\\n    scriptSrc: [\\"'self'\\"]\\n  }}\\n}}))",
    "rate_limiting": "from fastapi_limiter import FastAPILimiter\\nfrom fastapi_limiter.depends import RateLimiter\\n\\n@app.post('/api/login', dependencies=[Depends(RateLimiter(times=5, seconds=60))])\\nasync def login(): ...",
    "jwt_config": "JWT_SECRET should be stored in environment variable, minimum 32 characters, rotated regularly",
    "password_hashing": "Use bcrypt or argon2 with proper salt and cost factor. Never store plain text passwords.",
    "input_validation": "Use Pydantic models for FastAPI or Joi for Express to validate all inputs"
  }},
  "security_score": "72/100",
  "recommendations": [
    "Enable HTTPS/TLS for all traffic",
    "Implement rate limiting on authentication endpoints",
    "Add Content Security Policy (CSP) headers",
    "Use environment variables for all secrets and API keys",
    "Implement proper session management with secure cookies",
    "Add request validation and sanitization",
    "Enable audit logging for sensitive operations",
    "Implement CSRF protection for state-changing operations",
    "Keep dependencies up to date and scan for vulnerabilities",
    "Add security headers (X-Frame-Options, X-Content-Type-Options, etc.)"
  ]
}}

Quality expectations:
- Prioritize by severity (high/medium/low)
- Provide actionable fixes with code examples
- Focus on OWASP Top 10 and common web vulnerabilities
- Include both immediate fixes and long-term recommendations
- Consider both frontend and backend security"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data
