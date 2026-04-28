"""
Comprehensive Documentation Generator for CrucibAI
Generates API docs, deployment guides, and developer documentation
"""

import json
from datetime import datetime
from typing import Any, Dict, List


class DocumentationGenerator:
    """Generate comprehensive documentation"""

    @staticmethod
    def generate_api_documentation(endpoints: List[Dict[str, Any]]) -> str:
        """Generate API documentation in Markdown"""
        doc = """# CrucibAI API Documentation

## Overview

CrucibAI provides a comprehensive REST API for building, deploying, and managing AI applications.

**Base URL:** `https://api.crucibai.com/api`

**Authentication:** All endpoints require a valid JWT token in the Authorization header.

```
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting

- **Standard Tier:** 100 requests/minute
- **Pro Tier:** 1,000 requests/minute
- **Enterprise:** Custom limits

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Error Handling

All errors follow a standard format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes

- `INVALID_REQUEST`: Request validation failed
- `AUTHENTICATION_ERROR`: Invalid or missing authentication
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource already exists
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error

## Endpoints

"""

        for endpoint in endpoints:
            doc += (
                f"\n### {endpoint.get('method', 'GET')} {endpoint.get('path', '/')}\n\n"
            )
            doc += f"{endpoint.get('description', 'No description')}\n\n"

            if endpoint.get("parameters"):
                doc += "**Parameters:**\n\n"
                for param in endpoint["parameters"]:
                    doc += f"- `{param['name']}` ({param.get('type', 'string')}): {param.get('description', '')}\n"
                doc += "\n"

            if endpoint.get("request_body"):
                doc += "**Request Body:**\n\n```json\n"
                doc += json.dumps(endpoint["request_body"], indent=2)
                doc += "\n```\n\n"

            if endpoint.get("response"):
                doc += "**Response:**\n\n```json\n"
                doc += json.dumps(endpoint["response"], indent=2)
                doc += "\n```\n\n"

        return doc

    @staticmethod
    def generate_deployment_guide() -> str:
        """Generate deployment guide"""
        return """# CrucibAI Deployment Guide

## Prerequisites

- Node.js 18+
- Python 3.11+
- MongoDB 5.0+
- Docker (optional)

## Environment Setup

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create `.env` file:

```
MONGO_URL=mongodb://localhost:27017
JWT_SECRET=your_secret_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
BRAINTREE_ENVIRONMENT=sandbox
BRAINTREE_MERCHANT_ID=your_braintree_merchant_id
BRAINTREE_PUBLIC_KEY=your_braintree_public_key
BRAINTREE_PRIVATE_KEY=your_braintree_private_key
BRAINTREE_MERCHANT_ACCOUNT_ID=your_default_merchant_account_id
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

Create `.env.local` file:

```
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=CrucibAI
```

## Running Locally

### Start Backend

```bash
cd backend
python3 server.py
```

Backend will be available at `http://localhost:8000`

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Docker Deployment

### Build Docker Images

```bash
# Backend
docker build -t crucibai-backend:latest ./backend

# Frontend
docker build -t crucibai-frontend:latest ./frontend
```

### Run with Docker Compose

```bash
docker-compose up -d
```

## Production Deployment

### 1. Build for Production

```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
pip install gunicorn
```

### 2. Deploy Backend

Using Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 server:app
```

### 3. Deploy Frontend

Using a static file server:

```bash
# Using Node.js
npm install -g serve
serve -s dist -l 3000

# Using Nginx
# Copy dist/ to /var/www/crucibai
# Configure Nginx to serve static files
```

### 4. Environment Variables

Set production environment variables:

```bash
export MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/crucibai
export JWT_SECRET=<strong_random_key>
export NODE_ENV=production
```

### 5. SSL/TLS

Use Let's Encrypt for free SSL certificates:

```bash
certbot certonly --standalone -d api.crucibai.com
```

### 6. Database Backups

Set up automated MongoDB backups:

```bash
mongodump --uri "mongodb+srv://user:pass@cluster.mongodb.net/crucibai" --out /backups/$(date +%Y%m%d)
```

## Monitoring

### Health Checks

```bash
curl http://localhost:8000/api/health
```

### Logs

Monitor application logs:

```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend logs
# Check browser console
```

### Performance Metrics

Monitor key metrics:
- API response times
- Database query performance
- Frontend bundle size
- Error rates

## Scaling

### Horizontal Scaling

1. Deploy multiple backend instances
2. Use load balancer (Nginx, HAProxy)
3. Use MongoDB replica set for high availability

### Vertical Scaling

1. Increase server resources (CPU, RAM)
2. Optimize database indexes
3. Enable caching (Redis)

## Troubleshooting

### Backend Won't Start

1. Check MongoDB connection: `mongosh mongodb://localhost:27017`
2. Check environment variables: `env | grep MONGO`
3. Check logs: `tail -f backend/logs/app.log`

### Frontend Build Fails

1. Clear node_modules: `rm -rf node_modules && npm install`
2. Clear cache: `npm cache clean --force`
3. Check Node version: `node --version` (should be 18+)

### Database Connection Issues

1. Check MongoDB is running: `ps aux | grep mongod`
2. Check connection string in .env
3. Check firewall rules

## Security Checklist

- [ ] Change default JWT_SECRET
- [ ] Enable HTTPS/SSL
- [ ] Set strong database passwords
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Monitor for suspicious activity
- [ ] Keep dependencies updated
- [ ] Use environment variables for secrets

## Support

For deployment issues, contact support@crucibai.com
"""

    @staticmethod
    def generate_developer_guide() -> str:
        """Generate developer guide"""
        return """# CrucibAI Developer Guide

## Project Structure

```
crucibai/
├── backend/
│   ├── server.py          # Main FastAPI app
│   ├── error_handlers.py  # Error handling utilities
│   ├── middleware.py      # Security middleware
│   ├── validators.py      # Input validation
│   ├── query_optimizer.py # Database optimization
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── components/    # Reusable components
│   │   ├── utils/         # Utility functions
│   │   ├── styles/        # CSS files
│   │   └── App.jsx        # Main app component
│   └── package.json       # Node dependencies
└── README.md
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following the style guide
- Add tests for new functionality
- Update documentation

### 3. Test Your Changes

```bash
# Backend tests
cd backend
pytest test_suite.py -v

# Frontend tests
cd frontend
npm test
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: description of your changes"
git push origin feature/your-feature-name
```

### 5. Create Pull Request

Create a PR on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots (if UI changes)

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Max line length: 100 characters
- Use meaningful variable names

```python
def get_user_by_email(email: str):
    # Get user by email address
    return db.users.find_one({'email': email})
```

### JavaScript/React

- Use ES6+ syntax
- Use functional components with hooks
- Use meaningful component names
- Add JSDoc comments

```javascript
/**
 * UserProfile component
 * @param {string} userId - User ID
 * @returns {JSX.Element}
 */
export const UserProfile = ({ userId }) => {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    fetchUser(userId);
  }, [userId]);
  
  return <div>{user?.name}</div>;
};
```

## Testing

### Backend Tests

```bash
pytest test_suite.py -v --cov=.
```

### Frontend Tests

```bash
npm test -- --coverage
```

### E2E Tests

```bash
npm run test:e2e
```

## Documentation

- Update README.md for major changes
- Add comments for complex logic
- Keep API documentation up-to-date
- Document new environment variables

## Performance Tips

1. **Frontend**
   - Use React.memo for expensive components
   - Implement code splitting
   - Optimize images
   - Use lazy loading

2. **Backend**
   - Add database indexes
   - Use query caching
   - Implement pagination
   - Use connection pooling

3. **Database**
   - Monitor slow queries
   - Optimize aggregation pipelines
   - Use appropriate data types
   - Archive old data

## Debugging

### Backend

```python
# Add logging
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Variable: {variable}")

# Use debugger
import pdb; pdb.set_trace()
```

### Frontend

```javascript
// Use console
console.log('Debug:', variable);
console.error('Error:', error);

// Use debugger
debugger;
```

## Common Issues

### Import Errors

Make sure all imports are correct and modules are installed.

### Type Errors

Use type hints (Python) and TypeScript for better error detection.

### Performance Issues

Profile code using:
- Python: `cProfile`
- JavaScript: Chrome DevTools

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Tailwind CSS](https://tailwindcss.com/)

## Getting Help

- Check existing issues on GitHub
- Ask in Discord community
- Email support@crucibai.com
"""

    @staticmethod
    def generate_user_guide() -> str:
        """Generate user guide"""
        return """# CrucibAI User Guide

## Getting Started

### 1. Sign Up

Visit [crucibai.com](https://crucibai.com) and click "Sign Up"

- Enter your email
- Create a strong password
- Verify your email address

### 2. Create Your First Project

1. Click "New Project"
2. Enter project name and description
3. Select project type (Web App, API, etc.)
4. Click "Create"

### 3. Describe Your Requirements

- Use natural language to describe what you want to build
- Include specific features and functionality
- Mention any design preferences

### 4. Review the Plan

CrucibAI will create a detailed plan showing:
- Architecture overview
- Technology stack
- Implementation steps
- Estimated tokens

### 5. Generate Code

Click "Generate" to start the building process. You can:
- Watch real-time progress
- See the thinking process
- Monitor token usage

### 6. Review and Deploy

- Review generated code
- Make adjustments if needed
- Deploy to your preferred platform

## Features

### AI Chat

Ask questions about your project:
- "How do I add authentication?"
- "Can you optimize this query?"
- "What's the best way to handle errors?"

### Code Generation

Generate code for:
- Components
- API endpoints
- Database schemas
- Tests

### Version Control

- View project history
- Rollback to previous versions
- Compare changes

### Collaboration

- Share projects with team members
- Leave comments on code
- Track changes

## Pricing

### Free Tier

- 10,000 tokens/month
- 1 project
- Community support

### Pro Tier

- 100,000 tokens/month
- Unlimited projects
- Priority support
- Advanced features

### Enterprise

- Custom token limits
- Dedicated support
- Custom integrations
- SLA guarantee

## Tips & Tricks

1. **Be Specific**: More detailed requirements = better results
2. **Use Examples**: Show examples of what you want
3. **Iterate**: Refine your project step by step
4. **Review Code**: Always review generated code before deploying
5. **Ask Questions**: Use AI Chat to understand the code

## Troubleshooting

### I've run out of tokens

Upgrade your plan or wait for your monthly reset.

### The generated code doesn't work

1. Check the error message
2. Ask AI Chat for help
3. Review the implementation plan
4. Contact support if needed

### How do I export my project?

1. Go to project settings
2. Click "Export"
3. Choose format (ZIP, Git, etc.)
4. Download your project

## Support

- Email: support@crucibai.com
- Discord: [Join Community](https://discord.gg/crucibai)
- Docs: [crucibai.com/docs](https://crucibai.com/docs)
"""


# ==================== USAGE ====================

if __name__ == "__main__":
    generator = DocumentationGenerator()

    # Generate all documentation
    api_docs = generator.generate_api_documentation([])
    deployment_guide = generator.generate_deployment_guide()
    dev_guide = generator.generate_developer_guide()
    user_guide = generator.generate_user_guide()

    # Save to files
    with open("API_DOCUMENTATION.md", "w") as f:
        f.write(api_docs)

    with open("DEPLOYMENT_GUIDE.md", "w") as f:
        f.write(deployment_guide)

    with open("DEVELOPER_GUIDE.md", "w") as f:
        f.write(dev_guide)

    with open("USER_GUIDE.md", "w") as f:
        f.write(user_guide)

    print("Documentation generated successfully!")
