"""
CrucibAI Monitoring & Error Tracking
Integrates Sentry for production error tracking and performance monitoring
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """Centralized monitoring and error tracking"""
    
    def __init__(self):
        self.sentry_initialized = False
        self.health_status = {
            "database": "unknown",
            "redis": "unknown",
            "api": "unknown",
            "timestamp": None
        }
    
    def initialize_sentry(self, dsn: Optional[str] = None, environment: str = "production"):
        """Initialize Sentry error tracking"""
        
        sentry_dsn = dsn or os.getenv("SENTRY_DSN")
        
        if not sentry_dsn:
            logger.warning("⚠️ SENTRY_DSN not configured, error tracking disabled")
            return False
        
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                    AsyncioIntegration(),
                ],
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
                attach_stacktrace=True,
                send_default_pii=False,
                max_breadcrumbs=50,
            )
            
            self.sentry_initialized = True
            logger.info("✅ Sentry monitoring initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Sentry: {e}")
            return False
    
    async def check_health(self, db_pool=None, redis_client=None) -> Dict[str, Any]:
        """Check system health"""
        
        health = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check database
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health["components"]["database"] = {
                    "status": "healthy",
                    "pool_size": db_pool.get_size()
                }
                self.health_status["database"] = "healthy"
            except Exception as e:
                health["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                self.health_status["database"] = "unhealthy"
                health["status"] = "degraded"
        
        # Check Redis
        if redis_client:
            try:
                await redis_client.ping()
                health["components"]["redis"] = {"status": "healthy"}
                self.health_status["redis"] = "healthy"
            except Exception as e:
                health["components"]["redis"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                self.health_status["redis"] = "unhealthy"
                health["status"] = "degraded"
        
        # API is always healthy if this endpoint is reached
        health["components"]["api"] = {"status": "healthy"}
        self.health_status["api"] = "healthy"
        
        return health
    
    def capture_exception(self, exception: Exception, context: Optional[Dict] = None):
        """Capture exception in Sentry"""
        if self.sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_exception(exception)
    
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict] = None):
        """Capture message in Sentry"""
        if self.sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_message(message, level=level)
    
    def set_user_context(self, user_id: str, email: str = None, username: str = None):
        """Set user context for error tracking"""
        if self.sentry_initialized:
            sentry_sdk.set_user({
                "id": user_id,
                "email": email,
                "username": username
            })
    
    def clear_user_context(self):
        """Clear user context"""
        if self.sentry_initialized:
            sentry_sdk.set_user(None)
    
    def add_breadcrumb(self, message: str, category: str = "info", level: str = "info", data: Optional[Dict] = None):
        """Add breadcrumb for debugging"""
        if self.sentry_initialized:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )


class PerformanceMonitor:
    """Monitor API performance"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "total_response_time": 0.0,
            "endpoints": {}
        }
    
    def record_request(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Record API request metrics"""
        
        self.metrics["total_requests"] += 1
        self.metrics["total_response_time"] += response_time
        
        if status_code >= 400:
            self.metrics["total_errors"] += 1
        
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.metrics["endpoints"]:
            self.metrics["endpoints"][endpoint_key] = {
                "count": 0,
                "errors": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf')
            }
        
        ep_metrics = self.metrics["endpoints"][endpoint_key]
        ep_metrics["count"] += 1
        ep_metrics["total_time"] += response_time
        ep_metrics["avg_time"] = ep_metrics["total_time"] / ep_metrics["count"]
        ep_metrics["max_time"] = max(ep_metrics["max_time"], response_time)
        ep_metrics["min_time"] = min(ep_metrics["min_time"], response_time)
        
        if status_code >= 400:
            ep_metrics["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = self.metrics.copy()
        
        if metrics["total_requests"] > 0:
            metrics["avg_response_time"] = metrics["total_response_time"] / metrics["total_requests"]
            metrics["error_rate"] = metrics["total_errors"] / metrics["total_requests"]
        
        return metrics
    
    def get_endpoint_metrics(self, endpoint: str = None) -> Dict[str, Any]:
        """Get metrics for specific endpoint"""
        if endpoint:
            return self.metrics["endpoints"].get(endpoint, {})
        return self.metrics["endpoints"]


class AlertingSystem:
    """Alert on critical issues"""
    
    def __init__(self, monitoring: MonitoringSystem):
        self.monitoring = monitoring
        self.alerts = []
    
    async def check_thresholds(self, performance_monitor: PerformanceMonitor):
        """Check if metrics exceed thresholds"""
        
        metrics = performance_monitor.get_metrics()
        
        # Check error rate
        if metrics.get("error_rate", 0) > 0.05:  # > 5% error rate
            alert = {
                "severity": "critical",
                "message": f"High error rate: {metrics['error_rate']*100:.2f}%",
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            self.monitoring.capture_message(alert["message"], level="error")
        
        # Check response time
        if metrics.get("avg_response_time", 0) > 2.0:  # > 2 seconds
            alert = {
                "severity": "warning",
                "message": f"Slow response time: {metrics['avg_response_time']:.2f}s",
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            self.monitoring.capture_message(alert["message"], level="warning")
    
    def get_alerts(self) -> list:
        """Get all alerts"""
        return self.alerts
    
    def clear_alerts(self):
        """Clear alerts"""
        self.alerts = []


# Global instances
monitoring_system = MonitoringSystem()
performance_monitor = PerformanceMonitor()
alerting_system = AlertingSystem(monitoring_system)


async def initialize_monitoring():
    """Initialize all monitoring systems"""
    
    environment = os.getenv("ENVIRONMENT", "production")
    
    # Initialize Sentry
    monitoring_system.initialize_sentry(environment=environment)
    
    logger.info("✅ Monitoring systems initialized")


def get_monitoring_system() -> MonitoringSystem:
    """Get monitoring system instance"""
    return monitoring_system


def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor instance"""
    return performance_monitor


def get_alerting_system() -> AlertingSystem:
    """Get alerting system instance"""
    return alerting_system
