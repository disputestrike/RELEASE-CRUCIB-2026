"""
Structured logging module for CrucibAI
Provides JSON logging, request/response logging, and performance tracking
"""

import logging
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps
import traceback
from pythonjsonlogger import jsonlogger
from pathlib import Path

# ==================== SETUP ====================

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ==================== JSON LOGGER ====================

class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

# ==================== LOGGER SETUP ====================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup a structured logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = JSONFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler with JSON formatting
    file_handler = logging.FileHandler(LOG_DIR / f"{name}.log")
    file_handler.setLevel(level)
    file_formatter = JSONFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    file_handler.setFormatter(console_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# ==================== SPECIALIZED LOGGERS ====================

class RequestLogger:
    """Log HTTP requests and responses"""
    
    def __init__(self):
        self.logger = setup_logger("request_logger")
    
    def log_request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[Any] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log incoming request"""
        log_data = {
            "event": "request_received",
            "method": method,
            "path": path,
            "query_params": query_params,
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log headers (exclude sensitive ones)
        if headers:
            safe_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            log_data["headers"] = safe_headers
        
        # Log body (truncate if too large)
        if body:
            body_str = str(body)
            if len(body_str) > 1000:
                log_data["body"] = body_str[:1000] + "... [truncated]"
            else:
                log_data["body"] = body_str
        
        self.logger.info(json.dumps(log_data))
    
    def log_response(
        self,
        status_code: int,
        response_time: float,
        response_size: int,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log outgoing response"""
        log_data = {
            "event": "response_sent",
            "status_code": status_code,
            "response_time_ms": response_time * 1000,
            "response_size_bytes": response_size,
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            log_data["error"] = error
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

class ErrorLogger:
    """Log errors and exceptions"""
    
    def __init__(self):
        self.logger = setup_logger("error_logger", logging.ERROR)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        severity: str = "error"
    ):
        """Log error with full context"""
        log_data = {
            "event": "error_occurred",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
            "user_id": user_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc(),
            **(context or {})
        }
        
        if severity == "critical":
            self.logger.critical(json.dumps(log_data))
        elif severity == "warning":
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.error(json.dumps(log_data))

class PerformanceLogger:
    """Log performance metrics"""
    
    def __init__(self):
        self.logger = setup_logger("performance_logger")
    
    def log_operation(
        self,
        operation_name: str,
        duration_ms: float,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log operation performance"""
        log_data = {
            "event": "operation_completed",
            "operation": operation_name,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            **(details or {})
        }
        
        # Log warning if operation is slow
        if duration_ms > 5000:  # 5 seconds
            log_data["warning"] = "Slow operation detected"
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))
    
    def log_database_query(
        self,
        query: str,
        duration_ms: float,
        rows_affected: int,
        success: bool
    ):
        """Log database query performance"""
        log_data = {
            "event": "database_query",
            "query": query[:500],  # Truncate long queries
            "duration_ms": duration_ms,
            "rows_affected": rows_affected,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if duration_ms > 1000:  # 1 second
            log_data["warning"] = "Slow database query"
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

class AuditLogger:
    """Log user actions for audit trail"""
    
    def __init__(self):
        self.logger = setup_logger("audit_logger")
    
    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log user action"""
        log_data = {
            "event": "user_action",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
            **({"changes": changes} if changes else {})
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_authentication(
        self,
        user_id: Optional[str],
        success: bool,
        method: str,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Log authentication attempt"""
        log_data = {
            "event": "authentication_attempt",
            "user_id": user_id,
            "success": success,
            "method": method,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if reason:
            log_data["reason"] = reason
        
        if success:
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.warning(json.dumps(log_data))

    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Compatibility shim for async audit logger API used by server routes."""
        changes = None
        if old_value is not None or new_value is not None:
            changes = {"old_value": old_value, "new_value": new_value}
        if details:
            changes = {**(changes or {}), "details": details}
        self.log_action(
            user_id=user_id,
            action=action,
            resource=resource_type or "unknown",
            resource_id=resource_id or "unknown",
            changes=changes,
            ip_address=ip_address,
        )

# ==================== DECORATORS ====================

request_logger = RequestLogger()
error_logger = ErrorLogger()
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()

def log_performance(operation_name: str):
    """Decorator to log operation performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=False,
                    details={"error": str(e)}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=False,
                    details={"error": str(e)}
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def log_audit(action: str, resource: str):
    """Decorator to log user actions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user_id and resource_id from kwargs or request
            user_id = kwargs.get('user_id') or (args[0].user_id if hasattr(args[0], 'user_id') else None)
            resource_id = kwargs.get('resource_id') or (args[1] if len(args) > 1 else None)
            
            result = await func(*args, **kwargs)
            
            if user_id:
                audit_logger.log_action(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    resource_id=str(resource_id) if resource_id else "unknown"
                )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or (args[0].user_id if hasattr(args[0], 'user_id') else None)
            resource_id = kwargs.get('resource_id') or (args[1] if len(args) > 1 else None)
            
            result = func(*args, **kwargs)
            
            if user_id:
                audit_logger.log_action(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    resource_id=str(resource_id) if resource_id else "unknown"
                )
            
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# ==================== UTILITY FUNCTIONS ====================

def get_request_logger() -> RequestLogger:
    """Get request logger instance"""
    return request_logger

def get_error_logger() -> ErrorLogger:
    """Get error logger instance"""
    return error_logger

def get_performance_logger() -> PerformanceLogger:
    """Get performance logger instance"""
    return performance_logger

def get_audit_logger() -> AuditLogger:
    """Get audit logger instance"""
    return audit_logger
