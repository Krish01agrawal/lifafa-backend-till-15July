"""
Middleware for Scalability and Resource Management
=================================================

This module provides middleware for rate limiting, resource management,
and scalability controls for the Gmail Chatbot backend.
"""

import asyncio
import time
import psutil
import logging
from collections import defaultdict, deque
from typing import Dict, Set, Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .config import (
    GMAIL_API_RATE_LIMIT, GMAIL_API_WINDOW_SECONDS, CONCURRENT_USERS_LIMIT,
    MAX_MEMORY_USAGE, EMAIL_PROCESSING_TIMEOUT, MAX_REQUESTS_PER_MINUTE,
    MAX_CONCURRENT_REQUESTS, MEMORY_WARNING_THRESHOLD, CPU_WARNING_THRESHOLD
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE MANAGEMENT
# ============================================================================

class ResourceManager:
    """Manages system resources and user limits"""
    
    def __init__(self):
        # Rate limiting tracking
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.gmail_api_calls: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Concurrent processing tracking
        self.active_users: Set[str] = set()
        self.user_concurrent_requests: Dict[str, int] = defaultdict(int)
        self.processing_start_times: Dict[str, float] = {}
        
        # Memory tracking
        self.user_memory_usage: Dict[str, float] = defaultdict(float)
        
        # System monitoring
        self.last_system_check = 0
        self.system_check_interval = 30  # seconds
        
    async def check_system_resources(self) -> Tuple[bool, str]:
        """Check if system has enough resources"""
        current_time = time.time()
        
        # Only check every 30 seconds to avoid overhead
        if current_time - self.last_system_check < self.system_check_interval:
            return True, "OK"
            
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            self.last_system_check = current_time
            
            # Log warnings if resources are high
            if memory_percent > MEMORY_WARNING_THRESHOLD:
                logger.warning(f"High memory usage: {memory_percent:.1f}%")
                
            if cpu_percent > CPU_WARNING_THRESHOLD:
                logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
            
            # Block new requests if resources are critically low
            if memory_percent > 95:
                return False, "System memory critically low"
                
            if cpu_percent > 95:
                return False, "System CPU critically high"
                
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return True, "OK"  # Allow requests if we can't check
    
    def check_rate_limit(self, user_id: str, endpoint_type: str = "general") -> bool:
        """Check if user has exceeded rate limits"""
        current_time = time.time()
        
        if endpoint_type == "gmail_api":
            # Gmail API specific rate limiting
            user_calls = self.gmail_api_calls[user_id]
            
            # Remove old calls outside the window
            while user_calls and current_time - user_calls[0] > GMAIL_API_WINDOW_SECONDS:
                user_calls.popleft()
            
            # Check if limit exceeded
            if len(user_calls) >= GMAIL_API_RATE_LIMIT:
                return False
                
            # Add current call
            user_calls.append(current_time)
            
        else:
            # General API rate limiting
            user_requests = self.user_requests[user_id]
            
            # Remove old requests outside 1-minute window
            while user_requests and current_time - user_requests[0] > 60:
                user_requests.popleft()
            
            # Check if limit exceeded
            if len(user_requests) >= MAX_REQUESTS_PER_MINUTE:
                return False
                
            # Add current request
            user_requests.append(current_time)
        
        return True
    
    def check_concurrent_users(self, user_id: str) -> bool:
        """Check if we can accept another concurrent user"""
        if user_id in self.active_users:
            return True  # User already active
            
        if len(self.active_users) >= CONCURRENT_USERS_LIMIT:
            return False
            
        return True
    
    def check_user_concurrent_requests(self, user_id: str) -> bool:
        """Check if user has too many concurrent requests"""
        return self.user_concurrent_requests[user_id] < MAX_CONCURRENT_REQUESTS
    
    def start_user_processing(self, user_id: str) -> bool:
        """Start tracking user processing"""
        if not self.check_concurrent_users(user_id):
            return False
            
        self.active_users.add(user_id)
        self.processing_start_times[user_id] = time.time()
        return True
    
    def end_user_processing(self, user_id: str):
        """End tracking user processing"""
        self.active_users.discard(user_id)
        self.processing_start_times.pop(user_id, None)
        self.user_memory_usage.pop(user_id, 0)
    
    def check_processing_timeout(self, user_id: str) -> bool:
        """Check if user processing has timed out"""
        if user_id not in self.processing_start_times:
            return False
            
        elapsed = time.time() - self.processing_start_times[user_id]
        return elapsed > EMAIL_PROCESSING_TIMEOUT
    
    def update_user_memory(self, user_id: str, memory_mb: float):
        """Update user memory usage"""
        self.user_memory_usage[user_id] = memory_mb
        
        if memory_mb > MAX_MEMORY_USAGE:
            logger.warning(f"User {user_id} exceeding memory limit: {memory_mb}MB")
    
    def get_stats(self) -> Dict:
        """Get current resource usage stats"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            return {
                "active_users": len(self.active_users),
                "concurrent_limit": CONCURRENT_USERS_LIMIT,
                "system_memory_percent": memory.percent,
                "system_cpu_percent": cpu_percent,
                "total_user_memory_mb": sum(self.user_memory_usage.values()),
                "active_user_list": list(self.active_users)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

# Global resource manager instance
resource_manager = ResourceManager()

# ============================================================================
# MIDDLEWARE FUNCTIONS
# ============================================================================

@asynccontextmanager
async def request_context(user_id: str, request_type: str = "general"):
    """Context manager for tracking request lifecycle"""
    
    # Increment concurrent request counter
    resource_manager.user_concurrent_requests[user_id] += 1
    
    try:
        yield
    finally:
        # Decrement concurrent request counter
        resource_manager.user_concurrent_requests[user_id] -= 1
        if resource_manager.user_concurrent_requests[user_id] <= 0:
            resource_manager.user_concurrent_requests.pop(user_id, None)

async def rate_limit_middleware(request: Request, call_next):
    """Middleware for rate limiting and resource management"""
    
    # Skip middleware for health checks and static files
    if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    try:
        # Check system resources first
        system_ok, system_message = await resource_manager.check_system_resources()
        if not system_ok:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Service temporarily unavailable",
                    "message": system_message,
                    "retry_after": 60
                }
            )
        
        # Extract user_id from request (JWT token, query params, etc.)
        user_id = await extract_user_id(request)
        
        if user_id:
            # Determine endpoint type for rate limiting
            endpoint_type = "gmail_api" if "/gmail/" in request.url.path else "general"
            
            # Check rate limits
            if not resource_manager.check_rate_limit(user_id, endpoint_type):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {GMAIL_API_RATE_LIMIT if endpoint_type == 'gmail_api' else MAX_REQUESTS_PER_MINUTE} per {'100 seconds' if endpoint_type == 'gmail_api' else 'minute'}",
                        "retry_after": GMAIL_API_WINDOW_SECONDS if endpoint_type == "gmail_api" else 60
                    }
                )
            
            # Check concurrent requests per user
            if not resource_manager.check_user_concurrent_requests(user_id):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Too many concurrent requests",
                        "message": f"Maximum {MAX_CONCURRENT_REQUESTS} concurrent requests per user",
                        "retry_after": 30
                    }
                )
            
            # Check processing timeout for long-running operations
            if resource_manager.check_processing_timeout(user_id):
                resource_manager.end_user_processing(user_id)
                return JSONResponse(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    content={
                        "error": "Processing timeout",
                        "message": f"Processing exceeded {EMAIL_PROCESSING_TIMEOUT} seconds timeout",
                        "suggestion": "Try processing smaller batches"
                    }
                )
            
            # Use request context for tracking
            async with request_context(user_id):
                response = await call_next(request)
                return response
        else:
            # No user_id found, proceed without user-specific limits
            response = await call_next(request)
            return response
            
    except Exception as e:
        logger.error(f"Error in rate limit middleware: {e}")
        # Don't block requests due to middleware errors
        return await call_next(request)

async def extract_user_id(request: Request) -> Optional[str]:
    """Extract user_id from request for rate limiting"""
    try:
        # Try to get from JWT token in Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from .auth import decode_jwt_token
            token = auth_header.split(" ")[1]
            user_data = decode_jwt_token(token)
            return user_data.get("user_id")
        
        # Try to get from query parameters
        jwt_token = request.query_params.get("jwt_token")
        if jwt_token:
            from .auth import decode_jwt_token
            user_data = decode_jwt_token(jwt_token)
            return user_data.get("user_id")
        
        # Try to get from request body (for POST requests)
        if request.method == "POST":
            # This is a bit tricky as we need to read the body
            # For now, we'll skip body parsing to avoid consuming the request
            pass
            
        return None
        
    except Exception as e:
        logger.error(f"Error extracting user_id: {e}")
        return None

# ============================================================================
# PROCESSING CONTEXT MANAGERS
# ============================================================================

@asynccontextmanager
async def email_processing_context(user_id: str):
    """Context manager for email processing operations"""
    
    # Check if we can start processing
    if not resource_manager.start_user_processing(user_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Too many concurrent users processing. Limit: {CONCURRENT_USERS_LIMIT}"
        )
    
    try:
        logger.info(f"Started email processing for user {user_id}")
        yield resource_manager
        
    except asyncio.TimeoutError:
        logger.error(f"Email processing timeout for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Processing timeout after {EMAIL_PROCESSING_TIMEOUT} seconds"
        )
        
    except Exception as e:
        logger.error(f"Error in email processing for user {user_id}: {e}")
        raise
        
    finally:
        resource_manager.end_user_processing(user_id)
        logger.info(f"Ended email processing for user {user_id}")

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

def get_health_status() -> Dict:
    """Get system health status"""
    stats = resource_manager.get_stats()
    
    # Determine health status
    health_status = "healthy"
    issues = []
    
    if stats.get("system_memory_percent", 0) > MEMORY_WARNING_THRESHOLD:
        health_status = "warning"
        issues.append(f"High memory usage: {stats['system_memory_percent']:.1f}%")
    
    if stats.get("system_cpu_percent", 0) > CPU_WARNING_THRESHOLD:
        health_status = "warning"
        issues.append(f"High CPU usage: {stats['system_cpu_percent']:.1f}%")
    
    if stats.get("active_users", 0) >= CONCURRENT_USERS_LIMIT * 0.9:
        health_status = "warning"
        issues.append(f"Near concurrent user limit: {stats['active_users']}/{CONCURRENT_USERS_LIMIT}")
    
    return {
        "status": health_status,
        "timestamp": time.time(),
        "issues": issues,
        "stats": stats,
        "limits": {
            "concurrent_users": CONCURRENT_USERS_LIMIT,
            "gmail_api_rate_limit": GMAIL_API_RATE_LIMIT,
            "max_memory_per_user_mb": MAX_MEMORY_USAGE,
            "email_processing_timeout_seconds": EMAIL_PROCESSING_TIMEOUT
        }
    }

logger.info("🛡️ Scalability middleware loaded successfully!")
logger.info(f"⚡ Rate limits: {MAX_REQUESTS_PER_MINUTE}/min general, {GMAIL_API_RATE_LIMIT}/100s Gmail API")
logger.info(f"👥 Concurrent users limit: {CONCURRENT_USERS_LIMIT}")
logger.info(f"🧠 Memory limit per user: {MAX_MEMORY_USAGE}MB") 