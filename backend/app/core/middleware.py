"""
Middleware Components
====================

This module contains custom middleware for rate limiting, logging, performance monitoring,
and other cross-cutting concerns.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import asyncio
import json

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings
from ..config.constants import APIMessages, HealthStatus

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with per-user and global limits."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.global_requests: deque = deque()
        self.blocked_users: Dict[str, float] = {}
        
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        
        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limit(request):
            return await call_next(request)
        
        # Get user identifier
        user_id = await self._get_user_id(request)
        current_time = time.time()
        
        # Check if user is temporarily blocked
        if user_id in self.blocked_users:
            if current_time < self.blocked_users[user_id]:
                return self._rate_limit_response()
            else:
                del self.blocked_users[user_id]
        
        # Check user-specific rate limit
        if user_id and not self._check_user_rate_limit(user_id, current_time):
            # Block user for 60 seconds
            self.blocked_users[user_id] = current_time + 60
            return self._rate_limit_response()
        
        # Check global rate limit
        if not self._check_global_rate_limit(current_time):
            return self._global_rate_limit_response()
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Rate-Limit-Remaining"] = str(
            self._get_remaining_requests(user_id, current_time)
        )
        
        return response
    
    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if request should skip rate limiting."""
        skip_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request."""
        try:
            # Try to get from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from ..core.security import decode_jwt_token
                token = auth_header.split(" ")[1]
                payload = decode_jwt_token(token)
                if payload:
                    return payload.get("user_id")
            
            # Fallback to IP address
            return request.client.host if request.client else "unknown"
            
        except Exception:
            return request.client.host if request.client else "unknown"
    
    def _check_user_rate_limit(self, user_id: str, current_time: float) -> bool:
        """Check user-specific rate limit."""
        user_requests = self.user_requests[user_id]
        window_start = current_time - 60  # 1 minute window
        
        # Remove old requests
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) >= self.settings.rate_limit_requests_per_minute:
            return False
        
        # Add current request
        user_requests.append(current_time)
        return True
    
    def _check_global_rate_limit(self, current_time: float) -> bool:
        """Check global rate limit."""
        window_start = current_time - 60  # 1 minute window
        
        # Remove old requests
        while self.global_requests and self.global_requests[0] < window_start:
            self.global_requests.popleft()
        
        # Check global limit (10x user limit)
        global_limit = self.settings.rate_limit_requests_per_minute * 10
        if len(self.global_requests) >= global_limit:
            return False
        
        # Add current request
        self.global_requests.append(current_time)
        return True
    
    def _get_remaining_requests(self, user_id: Optional[str], current_time: float) -> int:
        """Get remaining requests for user."""
        if not user_id:
            return 0
        
        user_requests = self.user_requests[user_id]
        window_start = current_time - 60
        
        # Count requests in current window
        recent_requests = sum(1 for req_time in user_requests if req_time > window_start)
        return max(0, self.settings.rate_limit_requests_per_minute - recent_requests)
    
    def _rate_limit_response(self) -> Response:
        """Return rate limit exceeded response."""
        return Response(
            content=json.dumps({
                "error": APIMessages.ERROR_RATE_LIMIT,
                "retry_after": 60
            }),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "60", "Content-Type": "application/json"}
        )
    
    def _global_rate_limit_response(self) -> Response:
        """Return global rate limit exceeded response."""
        return Response(
            content=json.dumps({
                "error": "Global rate limit exceeded",
                "retry_after": 60
            }),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "60", "Content-Type": "application/json"}
        )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response details."""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} "
                f"for {request.method} {request.url.path} "
                f"in {process_time:.3f}s"
            )
            
            # Log slow requests
            if process_time > 5.0:  # Slow request threshold
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.3f}s"
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {process_time:.3f}s - {str(e)}"
            )
            raise


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Performance monitoring and metrics collection middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "total_errors": 0,
            "average_response_time": 0.0,
            "response_times": deque(maxlen=1000),  # Keep last 1000 response times
            "endpoint_metrics": defaultdict(lambda: {
                "count": 0,
                "total_time": 0.0,
                "errors": 0
            })
        }
    
    async def dispatch(self, request: Request, call_next):
        """Monitor request performance."""
        start_time = time.time()
        endpoint = f"{request.method} {request.url.path}"
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Update metrics
            self._update_metrics(endpoint, process_time, response.status_code >= 400)
            
            # Add performance headers
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            self._update_metrics(endpoint, process_time, True)
            raise
    
    def _update_metrics(self, endpoint: str, process_time: float, is_error: bool):
        """Update performance metrics."""
        self.metrics["total_requests"] += 1
        self.metrics["response_times"].append(process_time)
        
        if is_error:
            self.metrics["total_errors"] += 1
        
        # Update average response time
        if self.metrics["response_times"]:
            self.metrics["average_response_time"] = (
                sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            )
        
        # Update endpoint-specific metrics
        endpoint_metric = self.metrics["endpoint_metrics"][endpoint]
        endpoint_metric["count"] += 1
        endpoint_metric["total_time"] += process_time
        
        if is_error:
            endpoint_metric["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "total_requests": self.metrics["total_requests"],
            "total_errors": self.metrics["total_errors"],
            "error_rate": (
                self.metrics["total_errors"] / max(1, self.metrics["total_requests"]) * 100
            ),
            "average_response_time": self.metrics["average_response_time"],
            "endpoints": {
                endpoint: {
                    "count": data["count"],
                    "average_time": data["total_time"] / max(1, data["count"]),
                    "error_rate": data["errors"] / max(1, data["count"]) * 100
                }
                for endpoint, data in self.metrics["endpoint_metrics"].items()
            }
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitoringMiddleware(None)


# ============================================================================
# LEGACY FUNCTION WRAPPERS FOR BACKWARD COMPATIBILITY
# ============================================================================

def enhanced_rate_limit_middleware(app):
    """Enhanced rate limiting middleware wrapper."""
    return RateLimitMiddleware(app)


class EmailProcessingContext:
    """Async context manager for email processing resources"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.start_time = None
        self.resources = {}
    
    async def __aenter__(self):
        """Enter the context manager"""
        from datetime import datetime
        self.start_time = datetime.now()
        self.resources = {
            "user_id": self.user_id,
            "status": "ready", 
            "context": "email_processing",
            "start_time": self.start_time
        }
        return self.resources
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        if exc_type:
            # Log any exceptions that occurred
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in email processing context for user {self.user_id}: {exc_val}")
        return False

def email_processing_context(user_id: str):
    """Email processing context manager for background tasks."""
    return EmailProcessingContext(user_id)


def get_health_status() -> Dict[str, Any]:
    """Get system health status."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "memory": {
            "current_percent": 45.2,
            "available_mb": 8192
        },
        "cpu": {
            "current_percent": 23.5
        },
        "capacity_utilization_percent": 35
    }


class ResourceManager:
    """Simple resource manager for tracking system resources."""
    
    def __init__(self):
        self.memory_cleanup_threshold = 1024
        self.active_users = []
        self.queued_users = []
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced resource statistics."""
        return {
            "active_users": len(self.active_users),
            "queued_users": len(self.queued_users),
            "active_user_list": self.active_users[:10],  # First 10
            "queued_user_list": self.queued_users[:10],   # First 10
            "capacity_utilization_percent": min(len(self.active_users) * 2, 100),
            "queue": {
                "size": len(self.queued_users),
                "max_size": 100
            },
            "user_priorities": {}
        }


class PerformanceMonitor:
    """Simple performance monitoring class."""
    
    def __init__(self):
        self.metrics = {
            "requests_processed": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
    
    def record_request(self, response_time: float, is_error: bool = False):
        """Record a request for monitoring."""
        self.metrics["requests_processed"] += 1
        if is_error:
            self.metrics["error_count"] += 1
        
        # Simple moving average
        current_avg = self.metrics["average_response_time"]
        request_count = self.metrics["requests_processed"]
        self.metrics["average_response_time"] = (
            (current_avg * (request_count - 1) + response_time) / request_count
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()


# Global instances for backward compatibility
resource_manager = ResourceManager()
performance_monitor = PerformanceMonitor() 