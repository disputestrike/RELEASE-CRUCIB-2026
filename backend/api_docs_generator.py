"""
API Documentation Generator for CrucibAI
Generates comprehensive API documentation from FastAPI endpoints
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import inspect
from fastapi import FastAPI
from fastapi.routing import APIRoute

class APIDocumentationGenerator:
    """Generate comprehensive API documentation"""
    
    def __init__(self, app: FastAPI, title: str = "CrucibAI API", version: str = "1.0.0"):
        self.app = app
        self.title = title
        self.version = version
        self.docs = {
            "title": title,
            "version": version,
            "generated_at": datetime.utcnow().isoformat(),
            "endpoints": [],
            "models": {},
            "errors": {},
            "authentication": {},
            "rate_limits": {}
        }
    
    def generate(self) -> Dict[str, Any]:
        """Generate complete API documentation"""
        self._extract_endpoints()
        self._extract_models()
        self._extract_error_codes()
        self._extract_auth_info()
        self._extract_rate_limits()
        return self.docs
    
    def _extract_endpoints(self):
        """Extract endpoint information"""
        for route in self.app.routes:
            if isinstance(route, APIRoute):
                endpoint_doc = {
                    "path": route.path,
                    "method": route.methods,
                    "name": route.name,
                    "description": route.description or "No description",
                    "summary": route.summary or route.name,
                    "tags": route.tags or ["default"],
                    "parameters": self._extract_parameters(route),
                    "request_body": self._extract_request_body(route),
                    "responses": self._extract_responses(route),
                    "security": self._extract_security(route),
                    "examples": self._extract_examples(route),
                    "rate_limit": self._extract_rate_limit(route),
                    "deprecated": route.deprecated or False
                }
                self.docs["endpoints"].append(endpoint_doc)
    
    def _extract_parameters(self, route: APIRoute) -> List[Dict[str, Any]]:
        """Extract query and path parameters"""
        parameters = []
        
        if route.parameters:
            for param in route.parameters:
                param_doc = {
                    "name": param.name,
                    "in": param.param_type,
                    "required": param.required,
                    "description": param.description or "",
                    "type": self._get_type_name(param.annotation),
                    "default": param.default if param.default is not None else None
                }
                parameters.append(param_doc)
        
        return parameters
    
    def _extract_request_body(self, route: APIRoute) -> Optional[Dict[str, Any]]:
        """Extract request body schema"""
        if not route.body_field:
            return None
        
        return {
            "required": route.body_field.required,
            "content_type": "application/json",
            "schema": self._get_model_schema(route.body_field.type_),
            "example": self._get_model_example(route.body_field.type_)
        }
    
    def _extract_responses(self, route: APIRoute) -> Dict[str, Any]:
        """Extract response schemas"""
        responses = {}
        
        if route.responses:
            for status_code, response_info in route.responses.items():
                responses[str(status_code)] = {
                    "description": response_info.get("description", ""),
                    "content_type": "application/json",
                    "schema": response_info.get("model", {})
                }
        else:
            # Default responses
            responses["200"] = {
                "description": "Successful response",
                "content_type": "application/json"
            }
            responses["400"] = {
                "description": "Bad request"
            }
            responses["401"] = {
                "description": "Unauthorized"
            }
            responses["500"] = {
                "description": "Internal server error"
            }
        
        return responses
    
    def _extract_security(self, route: APIRoute) -> List[str]:
        """Extract security requirements"""
        security = []
        
        if route.dependencies:
            for dep in route.dependencies:
                if "Bearer" in str(dep):
                    security.append("Bearer Token")
                elif "API Key" in str(dep):
                    security.append("API Key")
        
        return security or ["None"]
    
    def _extract_examples(self, route: APIRoute) -> Dict[str, Any]:
        """Extract usage examples"""
        examples = {}
        
        # Generate basic example
        path = route.path
        methods = list(route.methods) if route.methods else ["GET"]
        method = methods[0].lower()
        
        examples["curl"] = f'curl -X {methods[0]} "http://api.crucibai.com{path}"'
        examples["python"] = f'import requests\nresponse = requests.{method}("http://api.crucibai.com{path}")'
        examples["javascript"] = f'fetch("http://api.crucibai.com{path}").then(r => r.json())'
        
        return examples
    
    def _extract_rate_limit(self, route: APIRoute) -> Dict[str, Any]:
        """Extract rate limit information"""
        return {
            "requests_per_minute": 100,
            "requests_per_hour": 6000,
            "burst_limit": 10
        }
    
    def _extract_models(self):
        """Extract model schemas"""
        # This would extract Pydantic models from the app
        models = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"}
                },
                "required": ["id", "email", "name"]
            },
            "Error": {
                "type": "object",
                "properties": {
                    "error_code": {"type": "string"},
                    "message": {"type": "string"},
                    "details": {"type": "object"}
                },
                "required": ["error_code", "message"]
            }
        }
        self.docs["models"] = models
    
    def _extract_error_codes(self):
        """Extract error codes and descriptions"""
        error_codes = {
            "VALIDATION_ERROR": {
                "status_code": 400,
                "description": "Input validation failed",
                "example": {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid email format",
                    "details": {"field": "email"}
                }
            },
            "AUTH_ERROR": {
                "status_code": 401,
                "description": "Authentication failed",
                "example": {
                    "error_code": "AUTH_ERROR",
                    "message": "Invalid credentials"
                }
            },
            "AUTHZ_ERROR": {
                "status_code": 403,
                "description": "Insufficient permissions",
                "example": {
                    "error_code": "AUTHZ_ERROR",
                    "message": "You don't have permission to access this resource"
                }
            },
            "NOT_FOUND": {
                "status_code": 404,
                "description": "Resource not found",
                "example": {
                    "error_code": "NOT_FOUND",
                    "message": "User not found: user_123"
                }
            },
            "CONFLICT": {
                "status_code": 409,
                "description": "Resource conflict",
                "example": {
                    "error_code": "CONFLICT",
                    "message": "Email already exists"
                }
            },
            "RATE_LIMIT": {
                "status_code": 429,
                "description": "Rate limit exceeded",
                "example": {
                    "error_code": "RATE_LIMIT",
                    "message": "Maximum 100 requests per minute allowed",
                    "retry_after": 60
                }
            },
            "EXTERNAL_SERVICE_ERROR": {
                "status_code": 503,
                "description": "External service failure",
                "example": {
                    "error_code": "EXTERNAL_SERVICE_ERROR",
                    "message": "OpenAI service error: rate limit exceeded"
                }
            },
            "DATABASE_ERROR": {
                "status_code": 500,
                "description": "Database operation failed",
                "example": {
                    "error_code": "DATABASE_ERROR",
                    "message": "Database insert failed"
                }
            },
            "INTERNAL_ERROR": {
                "status_code": 500,
                "description": "Internal server error",
                "example": {
                    "error_code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            }
        }
        self.docs["errors"] = error_codes
    
    def _extract_auth_info(self):
        """Extract authentication information"""
        auth_info = {
            "bearer_token": {
                "type": "http",
                "scheme": "bearer",
                "bearer_format": "JWT",
                "description": "JWT token obtained from /api/auth/login",
                "example": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            "api_key": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for programmatic access",
                "example": "sk_live_xxxxxxxxxxxxx"
            }
        }
        self.docs["authentication"] = auth_info
    
    def _extract_rate_limits(self):
        """Extract rate limit information"""
        rate_limits = {
            "default": {
                "requests_per_minute": 100,
                "requests_per_hour": 6000,
                "burst_limit": 10,
                "description": "Default rate limit for all endpoints"
            },
            "voice_transcription": {
                "requests_per_minute": 30,
                "requests_per_hour": 1000,
                "description": "Rate limit for voice transcription endpoint"
            },
            "image_generation": {
                "requests_per_minute": 10,
                "requests_per_hour": 100,
                "description": "Rate limit for image generation endpoint"
            },
            "build_plan": {
                "requests_per_minute": 5,
                "requests_per_hour": 50,
                "description": "Rate limit for build planning endpoint"
            }
        }
        self.docs["rate_limits"] = rate_limits
    
    def _get_type_name(self, annotation) -> str:
        """Get type name from annotation"""
        if annotation is None:
            return "null"
        if annotation == str:
            return "string"
        if annotation == int:
            return "integer"
        if annotation == float:
            return "number"
        if annotation == bool:
            return "boolean"
        return str(annotation)
    
    def _get_model_schema(self, model_class) -> Dict[str, Any]:
        """Get Pydantic model schema"""
        if hasattr(model_class, 'schema'):
            return model_class.schema()
        return {}
    
    def _get_model_example(self, model_class) -> Dict[str, Any]:
        """Get example data for model"""
        if hasattr(model_class, '__fields__'):
            example = {}
            for field_name, field in model_class.__fields__.items():
                if field.type_ == str:
                    example[field_name] = "example_value"
                elif field.type_ == int:
                    example[field_name] = 0
                elif field.type_ == bool:
                    example[field_name] = False
                elif field.type_ == list:
                    example[field_name] = []
                elif field.type_ == dict:
                    example[field_name] = {}
            return example
        return {}
    
    def save_markdown(self, filepath: Path):
        """Save documentation as Markdown"""
        md_content = self._generate_markdown()
        filepath.write_text(md_content)
    
    def save_json(self, filepath: Path):
        """Save documentation as JSON"""
        filepath.write_text(json.dumps(self.docs, indent=2))
    
    def save_html(self, filepath: Path):
        """Save documentation as HTML"""
        html_content = self._generate_html()
        filepath.write_text(html_content)
    
    def _generate_markdown(self) -> str:
        """Generate Markdown documentation"""
        md = f"# {self.title}\n\n"
        md += f"**Version:** {self.version}\n"
        md += f"**Generated:** {self.docs['generated_at']}\n\n"
        
        # Table of contents
        md += "## Table of Contents\n\n"
        md += "- [Authentication](#authentication)\n"
        md += "- [Rate Limits](#rate-limits)\n"
        md += "- [Endpoints](#endpoints)\n"
        md += "- [Error Codes](#error-codes)\n"
        md += "- [Models](#models)\n\n"
        
        # Authentication
        md += "## Authentication\n\n"
        for auth_type, auth_info in self.docs["authentication"].items():
            md += f"### {auth_type}\n\n"
            md += f"**Type:** {auth_info.get('type', 'N/A')}\n"
            md += f"**Description:** {auth_info.get('description', 'N/A')}\n"
            md += f"**Example:** `{auth_info.get('example', 'N/A')}`\n\n"
        
        # Rate Limits
        md += "## Rate Limits\n\n"
        for limit_name, limit_info in self.docs["rate_limits"].items():
            md += f"### {limit_name}\n\n"
            md += f"- **Requests per minute:** {limit_info.get('requests_per_minute', 'N/A')}\n"
            md += f"- **Requests per hour:** {limit_info.get('requests_per_hour', 'N/A')}\n"
            md += f"- **Description:** {limit_info.get('description', 'N/A')}\n\n"
        
        # Endpoints
        md += "## Endpoints\n\n"
        for endpoint in self.docs["endpoints"]:
            methods = ", ".join(endpoint["method"]) if endpoint["method"] else "GET"
            md += f"### {endpoint['summary']}\n\n"
            md += f"**Path:** `{endpoint['path']}`\n"
            md += f"**Method:** `{methods}`\n"
            md += f"**Description:** {endpoint['description']}\n\n"
            
            if endpoint["parameters"]:
                md += "**Parameters:**\n\n"
                for param in endpoint["parameters"]:
                    md += f"- `{param['name']}` ({param['type']}) - {param['description']}\n"
                md += "\n"
            
            if endpoint["security"]:
                md += f"**Security:** {', '.join(endpoint['security'])}\n\n"
            
            md += "**Examples:**\n\n"
            md += f"```bash\n{endpoint['examples'].get('curl', 'N/A')}\n```\n\n"
        
        # Error Codes
        md += "## Error Codes\n\n"
        for error_code, error_info in self.docs["errors"].items():
            md += f"### {error_code}\n\n"
            md += f"**Status Code:** {error_info.get('status_code', 'N/A')}\n"
            md += f"**Description:** {error_info.get('description', 'N/A')}\n\n"
        
        return md
    
    def _generate_html(self) -> str:
        """Generate HTML documentation"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #1A1A1A; }}
                h2 {{ color: #666; border-bottom: 2px solid #1A1A1A; padding-bottom: 10px; }}
                .endpoint {{ background: #F5F5F4; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .method {{ font-weight: bold; color: #1A1A1A; }}
                .path {{ font-family: monospace; background: #fff; padding: 5px; }}
                .error {{ background: #fee; padding: 10px; margin: 5px 0; border-left: 4px solid #f00; }}
            </style>
        </head>
        <body>
            <h1>{self.title}</h1>
            <p><strong>Version:</strong> {self.version}</p>
            <p><strong>Generated:</strong> {self.docs['generated_at']}</p>
            
            <h2>Endpoints</h2>
            {"".join([f'''
            <div class="endpoint">
                <p><span class="method">{", ".join(ep["method"])}</span> <span class="path">{ep["path"]}</span></p>
                <p>{ep["description"]}</p>
            </div>
            ''' for ep in self.docs["endpoints"][:10]])}
            
            <h2>Error Codes</h2>
            {"".join([f'''
            <div class="error">
                <strong>{code}</strong> ({info.get("status_code", "N/A")}): {info.get("description", "N/A")}
            </div>
            ''' for code, info in self.docs["errors"].items()])}
        </body>
        </html>
        """
        return html

# ==================== USAGE ====================

def generate_api_docs(app: FastAPI, output_dir: Path = Path("./docs")):
    """Generate and save API documentation"""
    output_dir.mkdir(exist_ok=True)
    
    generator = APIDocumentationGenerator(app)
    docs = generator.generate()
    
    # Save in multiple formats
    generator.save_json(output_dir / "api_docs.json")
    generator.save_markdown(output_dir / "API.md")
    generator.save_html(output_dir / "api_docs.html")
    
    return docs
