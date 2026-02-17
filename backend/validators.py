"""
Comprehensive input validation module for CrucibAI
Provides Pydantic validators, custom validation rules, and async validators
"""

from pydantic import BaseModel, Field, EmailStr, validator, root_validator, constr
from typing import Optional, List, Dict, Any, Pattern
from datetime import datetime, timedelta
from enum import Enum
import re
from error_handlers import ValidationError

# ==================== VALIDATION PATTERNS ====================

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')
PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')

# ==================== ENUMS ====================

class BuildKind(str, Enum):
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    SAAS = "saas"
    BOT = "bot"
    AI_AGENT = "ai_agent"
    GAME = "game"
    TRADING = "trading"
    ANY = "any"

class DocumentType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    CODE = "code"
    MARKDOWN = "markdown"

class SearchType(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"

class TaskType(str, Enum):
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    ANALYZE = "analyze"

# ==================== BASE VALIDATORS ====================

class BaseValidator(BaseModel):
    """Base class with common validation settings"""
    class Config:
        validate_assignment = True
        str_strip_whitespace = True
        use_enum_values = True

# ==================== USER MODELS ====================

class UserRegisterValidator(BaseValidator):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=2, max_length=100)
    ref: Optional[str] = Field(None, max_length=50)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character (@$!%*?&)'
            )
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name doesn't contain suspicious characters"""
        if not re.match(r'^[a-zA-Z\s\'-]{2,100}$', v):
            raise ValueError('Name contains invalid characters')
        return v

class UserLoginValidator(BaseValidator):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class UserUpdateValidator(BaseValidator):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    
    @validator('avatar_url')
    def validate_avatar_url(cls, v):
        """Validate avatar URL is a valid URL"""
        if v and not URL_PATTERN.match(v):
            raise ValueError('Invalid avatar URL')
        return v

# ==================== CHAT & MESSAGE MODELS ====================

class ChatMessageValidator(BaseValidator):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field("auto", pattern="^(auto|gpt-4o|claude|gemini)$")
    mode: Optional[str] = Field(None, pattern="^(thinking|normal)?$")
    
    @validator('message')
    def validate_message_not_spam(cls, v):
        """Check message isn't just repeated characters"""
        if len(set(v.strip())) < 3:
            raise ValueError('Message appears to be spam')
        return v

# ==================== PROJECT MODELS ====================

class ProjectCreateValidator(BaseValidator):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=5000)
    project_type: str = Field(..., pattern="^(web|mobile|desktop|api|bot|other)$")
    requirements: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: Optional[int] = Field(None, ge=0, le=1000000)
    
    @validator('name')
    def validate_project_name(cls, v):
        """Validate project name format"""
        if not re.match(r'^[a-zA-Z0-9\s\-_]{3,100}$', v):
            raise ValueError('Project name contains invalid characters')
        return v
    
    @validator('requirements')
    def validate_requirements(cls, v):
        """Validate requirements structure"""
        if not isinstance(v, dict):
            raise ValueError('Requirements must be a dictionary')
        if len(v) > 100:
            raise ValueError('Too many requirements (max 100)')
        return v

class ProjectUpdateValidator(BaseValidator):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    status: Optional[str] = Field(None, pattern="^(draft|in_progress|completed|archived)$")

# ==================== BUILD MODELS ====================

class BuildPlanRequestValidator(BaseValidator):
    prompt: str = Field(..., min_length=10, max_length=50000)
    swarm: Optional[bool] = False
    build_kind: Optional[BuildKind] = None
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt quality"""
        if len(v.strip()) < 10:
            raise ValueError('Prompt must be at least 10 characters')
        if v.count('\n') > 100:
            raise ValueError('Prompt has too many line breaks')
        return v

# ==================== FILE UPLOAD MODELS ====================

class FileUploadValidator(BaseValidator):
    filename: str = Field(..., max_length=255)
    file_type: str = Field(..., pattern="^(image|document|code|video|audio)$")
    file_size: int = Field(..., ge=1, le=100*1024*1024)  # 100MB max
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename is safe"""
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Invalid filename')
        if not re.match(r'^[a-zA-Z0-9._\-]{1,255}$', v):
            raise ValueError('Filename contains invalid characters')
        return v

# ==================== DOCUMENT MODELS ====================

class DocumentProcessValidator(BaseValidator):
    content: str = Field(..., min_length=1, max_length=1000000)
    doc_type: DocumentType = DocumentType.TEXT
    task: TaskType = TaskType.SUMMARIZE
    
    @validator('content')
    def validate_content_not_empty(cls, v):
        """Ensure content isn't just whitespace"""
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v

# ==================== SEARCH MODELS ====================

class SearchQueryValidator(BaseValidator):
    query: str = Field(..., min_length=1, max_length=1000)
    search_type: SearchType = SearchType.HYBRID
    top_k: int = Field(5, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query"""
        if len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        return v

class RAGQueryValidator(BaseValidator):
    query: str = Field(..., min_length=1, max_length=5000)
    context: Optional[str] = Field(None, max_length=50000)
    top_k: int = Field(5, ge=1, le=100)
    
    @validator('query')
    def validate_rag_query(cls, v):
        """Validate RAG query"""
        if len(v.strip()) < 1:
            raise ValueError('Query cannot be empty')
        return v

# ==================== PAYMENT MODELS ====================

class TokenPurchaseValidator(BaseValidator):
    bundle: str = Field(..., pattern="^(starter|pro|enterprise|custom)$")
    quantity: Optional[int] = Field(1, ge=1, le=1000)
    promo_code: Optional[str] = Field(None, max_length=50)

class DeployTokensUpdateValidator(BaseValidator):
    vercel: Optional[str] = Field(None, max_length=500)
    netlify: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)
    aws: Optional[str] = Field(None, max_length=500)

# ==================== ENTERPRISE MODELS ====================

class EnterpriseContactValidator(BaseValidator):
    company: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    team_size: Optional[str] = Field(None, pattern="^(1-10|11-50|51-100|100\\+)$")
    use_case: Optional[str] = Field(None, pattern="^(agency|startup|enterprise|other)$")
    budget: Optional[str] = Field(None, pattern="^(10K|50K|100K|custom)$")
    message: Optional[str] = Field(None, max_length=5000)

# ==================== VALIDATION HELPER FUNCTIONS ====================

def validate_email(email: str) -> bool:
    """Validate email format"""
    try:
        EmailStr.validate(email)
        return True
    except:
        return False

def validate_url(url: str) -> bool:
    """Validate URL format"""
    return bool(URL_PATTERN.match(url))

def validate_slug(slug: str) -> bool:
    """Validate slug format"""
    return bool(SLUG_PATTERN.match(slug))

def validate_username(username: str) -> bool:
    """Validate username format"""
    return bool(USERNAME_PATTERN.match(username))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    if not any(c in '@$!%*?&' for c in password):
        return False, "Password must contain at least one special character (@$!%*?&)"
    return True, "Password is strong"

def sanitize_string(s: str, max_length: int = 1000) -> str:
    """Sanitize string input"""
    if not isinstance(s, str):
        raise ValidationError("Input must be a string")
    
    # Remove null bytes
    s = s.replace('\x00', '')
    
    # Truncate if too long
    if len(s) > max_length:
        s = s[:max_length]
    
    return s.strip()

def validate_json_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate JSON structure against schema
    Simple validation - checks required keys and types
    """
    for key, expected_type in schema.items():
        if key not in data:
            raise ValidationError(f"Missing required field: {key}")
        
        if not isinstance(data[key], expected_type):
            raise ValidationError(
                f"Field '{key}' has wrong type. Expected {expected_type.__name__}, "
                f"got {type(data[key]).__name__}"
            )
    
    return True

def validate_pagination(page: int, limit: int, max_limit: int = 100) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters
    Returns: (normalized_page, normalized_limit)
    """
    if page < 1:
        raise ValidationError("Page must be >= 1")
    if limit < 1:
        raise ValidationError("Limit must be >= 1")
    if limit > max_limit:
        limit = max_limit
    
    return page, limit

def validate_date_range(start_date: datetime, end_date: datetime, max_days: int = 365) -> bool:
    """Validate date range is reasonable"""
    if start_date > end_date:
        raise ValidationError("Start date must be before end date")
    
    delta = end_date - start_date
    if delta.days > max_days:
        raise ValidationError(f"Date range cannot exceed {max_days} days")
    
    return True

# ==================== BATCH VALIDATION ====================

def validate_batch_request(items: List[Dict[str, Any]], validator_class, max_items: int = 100) -> List[Dict[str, Any]]:
    """
    Validate a batch of items
    Returns list of validated items
    """
    if len(items) > max_items:
        raise ValidationError(f"Batch size cannot exceed {max_items} items")
    
    validated_items = []
    for i, item in enumerate(items):
        try:
            validated = validator_class(**item)
            validated_items.append(validated.dict())
        except Exception as e:
            raise ValidationError(f"Item {i} validation failed: {str(e)}")
    
    return validated_items
