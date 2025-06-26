"""
Middleware for Scalability and Resource Management
=================================================

This module provides middleware for rate limiting, resource management,
and scalability controls for the Gmail Chatbot backend.

Recent Optimizations (2025-06-23):
- Enhanced resource management for 200 concurrent users
- Intelligent user queuing system
- Smart memory management and cleanup
- Advanced performance monitoring
- Optimized rate limiting algorithms
"""

import asyncio
import time
import psutil
import logging
from collections import defaultdict, deque
from typing import Dict, Set, Optional, Tuple, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json
import threading

from .config import (
    GMAIL_API_RATE_LIMIT, GMAIL_API_WINDOW_SECONDS, CONCURRENT_USERS_LIMIT,
    MAX_MEMORY_USAGE, EMAIL_PROCESSING_TIMEOUT, MAX_REQUESTS_PER_MINUTE,
    MAX_CONCURRENT_REQUESTS, MEMORY_WARNING_THRESHOLD, CPU_WARNING_THRESHOLD,
    ENABLE_SMART_CACHING, MAX_CACHE_SIZE_MB
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# ENHANCED RESOURCE MANAGEMENT
# ============================================================================

class EnhancedResourceManager:
    """Advanced resource manager with intelligent queuing and monitoring"""
    
    def __init__(self):
        # Enhanced rate limiting tracking
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.gmail_api_calls: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Advanced concurrent processing tracking
        self.active_users: Set[str] = set()
        self.queued_users: List[str] = []  # Queue for users waiting for resources
        self.user_concurrent_requests: Dict[str, int] = defaultdict(int)
        self.processing_start_times: Dict[str, float] = {}
        self.user_priorities: Dict[str, int] = defaultdict(lambda: 1)  # 1=normal, 2=premium
        
        # Enhanced memory tracking
        self.user_memory_usage: Dict[str, float] = defaultdict(float)
        self.total_memory_allocated = 0
        self.memory_cleanup_threshold = MAX_MEMORY_USAGE * 0.8  # Cleanup at 80%
        
        # System monitoring with history
        self.last_system_check = 0
        self.system_check_interval = 15  # Check every 15 seconds for better responsiveness
        self.performance_history = deque(maxlen=100)  # Keep last 100 performance snapshots
        
        # Smart caching integration
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Threading lock for thread-safe operations
        self.lock = threading.RLock()
        
        logger.info(f"🚀 Enhanced Resource Manager initialized")
        logger.info(f"📊 Capacity: {CONCURRENT_USERS_LIMIT} concurrent users")
        logger.info(f"🧠 Memory limit per user: {MAX_MEMORY_USAGE}MB")
        
    async def check_system_resources(self) -> Tuple[bool, str, Dict]:
        """Enhanced system resource checking with detailed metrics"""
        current_time = time.time()
        
        # Only check every 15 seconds to avoid overhead
        if current_time - self.last_system_check < self.system_check_interval:
            return True, "OK", {}
        
        try:
            # Get detailed system metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_memory_mb = memory.available / (1024 * 1024)
            
            # Get CPU usage with short interval for accuracy
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Calculate our application's memory usage
            app_memory_mb = sum(self.user_memory_usage.values())
            
            self.last_system_check = current_time
            
            # Create performance snapshot
            perf_snapshot = {
                'timestamp': current_time,
                'memory_percent': memory_percent,
                'cpu_percent': cpu_percent,
                'disk_percent': disk_percent,
                'active_users': len(self.active_users),
                'queued_users': len(self.queued_users),
                'app_memory_mb': app_memory_mb,
                'available_memory_mb': available_memory_mb
            }
            
            # Add to history
            self.performance_history.append(perf_snapshot)
            
            # Advanced warning thresholds
            if memory_percent > MEMORY_WARNING_THRESHOLD:
                logger.warning(f"🔥 High memory usage: {memory_percent:.1f}%")
                
            if cpu_percent > CPU_WARNING_THRESHOLD:
                logger.warning(f"⚡ High CPU usage: {cpu_percent:.1f}%")
            
            if disk_percent > 90:
                logger.warning(f"💾 High disk usage: {disk_percent:.1f}%")
            
            # Intelligent resource protection
            if memory_percent > 95 or available_memory_mb < 500:
                return False, "System memory critically low", perf_snapshot
                
            if cpu_percent > 98:
                return False, "System CPU critically high", perf_snapshot
                
            if app_memory_mb > MAX_CACHE_SIZE_MB * 10:  # If app uses 10x cache size
                logger.warning("🧹 Triggering memory cleanup due to high app usage")
                await self.cleanup_memory()
                
            return True, "OK", perf_snapshot
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return True, "OK", {}  # Allow requests if we can't check
    
    def check_rate_limit_enhanced(self, user_id: str, endpoint_type: str = "general") -> Tuple[bool, int]:
        """Enhanced rate limiting with priority and burst handling"""
        current_time = time.time()
        user_priority = self.user_priorities[user_id]
        
        with self.lock:
            if endpoint_type == "gmail_api":
                # Gmail API specific rate limiting with priority adjustment
                user_calls = self.gmail_api_calls[user_id]
                rate_limit = GMAIL_API_RATE_LIMIT * user_priority  # Premium users get 2x limit
                window = GMAIL_API_WINDOW_SECONDS
                
                # Remove old calls outside the window
                while user_calls and current_time - user_calls[0] > window:
                    user_calls.popleft()
                
                # Check if limit exceeded
                if len(user_calls) >= rate_limit:
                    remaining_time = int(window - (current_time - user_calls[0]))
                    return False, remaining_time
                    
                # Add current call
                user_calls.append(current_time)
                
            else:
                # General API rate limiting with burst allowance
                user_requests = self.user_requests[user_id]
                rate_limit = MAX_REQUESTS_PER_MINUTE * user_priority
                
                # Remove old requests outside 1-minute window
                while user_requests and current_time - user_requests[0] > 60:
                    user_requests.popleft()
                
                # Check if limit exceeded
                if len(user_requests) >= rate_limit:
                    remaining_time = int(60 - (current_time - user_requests[0]))
                    return False, remaining_time
                    
                # Add current request
                user_requests.append(current_time)
        
        return True, 0
    
    async def request_processing_slot(self, user_id: str) -> Tuple[bool, str]:
        """Intelligent processing slot allocation with queuing"""
        
        with self.lock:
            # Check if user is already active
            if user_id in self.active_users:
                return True, "Already active"
            
            # Check if we have immediate capacity
            if len(self.active_users) < CONCURRENT_USERS_LIMIT:
                self.active_users.add(user_id)
                self.processing_start_times[user_id] = time.time()
                logger.info(f"✅ User {user_id} allocated processing slot immediately")
                return True, "Slot allocated"
            
            # Add to priority queue if not already queued
            if user_id not in self.queued_users:
                # Priority users go to front of queue
                if self.user_priorities[user_id] > 1:
                    self.queued_users.insert(0, user_id)
                else:
                    self.queued_users.append(user_id)
                
                logger.info(f"⏳ User {user_id} added to queue (position: {self.queued_users.index(user_id) + 1})")
            
            return False, f"Queued (position: {self.queued_users.index(user_id) + 1})"
    
    def release_processing_slot(self, user_id: str):
        """Release processing slot and allocate to next user in queue"""
        
        with self.lock:
            if user_id in self.active_users:
                self.active_users.remove(user_id)
                self.processing_start_times.pop(user_id, None)
                self.user_memory_usage.pop(user_id, 0)
                
                logger.info(f"🔓 User {user_id} released processing slot")
                
                # Allocate slot to next user in queue
                if self.queued_users:
                    next_user = self.queued_users.pop(0)
                    self.active_users.add(next_user)
                    self.processing_start_times[next_user] = time.time()
                    logger.info(f"➡️ Processing slot allocated to queued user {next_user}")
    
    def check_user_concurrent_requests(self, user_id: str) -> bool:
        """Enhanced concurrent request checking"""
        max_concurrent = MAX_CONCURRENT_REQUESTS * self.user_priorities[user_id]
        return self.user_concurrent_requests[user_id] < max_concurrent
    
    def check_processing_timeout(self, user_id: str) -> bool:
        """Check if user processing has timed out"""
        if user_id not in self.processing_start_times:
            return False
            
        elapsed = time.time() - self.processing_start_times[user_id]
        timeout = EMAIL_PROCESSING_TIMEOUT * self.user_priorities[user_id]  # Premium users get longer timeout
        return elapsed > timeout
    
    def update_user_memory(self, user_id: str, memory_mb: float):
        """Enhanced user memory tracking with automatic cleanup"""
        with self.lock:
            old_memory = self.user_memory_usage.get(user_id, 0)
            self.user_memory_usage[user_id] = memory_mb
            self.total_memory_allocated += (memory_mb - old_memory)
            
            memory_limit = MAX_MEMORY_USAGE * self.user_priorities[user_id]
            
            if memory_mb > memory_limit:
                logger.warning(f"🔥 User {user_id} exceeding memory limit: {memory_mb}MB > {memory_limit}MB")
                
            # Trigger cleanup if total memory is high
            if self.total_memory_allocated > self.memory_cleanup_threshold * len(self.active_users):
                asyncio.create_task(self.cleanup_memory())
    
    async def cleanup_memory(self):
        """Intelligent memory cleanup"""
        try:
            logger.info("🧹 Starting intelligent memory cleanup...")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clean up expired cache entries if caching is enabled
            if ENABLE_SMART_CACHING:
                try:
                    from .mem0_agent_agno import smart_cache
                    smart_cache.cleanup_expired()
                    logger.info("✅ Cache cleanup completed")
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
            
            # Reset total memory counter
            with self.lock:
                self.total_memory_allocated = sum(self.user_memory_usage.values())
            
            logger.info("✅ Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def set_user_priority(self, user_id: str, priority: int = 1):
        """Set user priority (1=normal, 2=premium)"""
        with self.lock:
            self.user_priorities[user_id] = priority
            logger.info(f"👑 User {user_id} priority set to {priority}")
    
    def get_enhanced_stats(self) -> Dict:
        """Get comprehensive resource usage statistics"""
        try:
            current_time = time.time()
            
            with self.lock:
                # Calculate average performance over last 10 snapshots
                recent_snapshots = list(self.performance_history)[-10:]
                avg_memory = sum(s['memory_percent'] for s in recent_snapshots) / len(recent_snapshots) if recent_snapshots else 0
                avg_cpu = sum(s['cpu_percent'] for s in recent_snapshots) / len(recent_snapshots) if recent_snapshots else 0
                
                # Get queue statistics
                queue_wait_times = []
                for i, user_id in enumerate(self.queued_users):
                    # Estimate wait time based on queue position
                    estimated_wait = i * 30  # Assume 30 seconds per user ahead
                    queue_wait_times.append(estimated_wait)
                
                stats = {
                    "active_users": len(self.active_users),
                    "queued_users": len(self.queued_users),
                    "concurrent_limit": CONCURRENT_USERS_LIMIT,
                    "capacity_utilization_percent": (len(self.active_users) / CONCURRENT_USERS_LIMIT) * 100,
                    
                    "memory": {
                        "current_percent": avg_memory,
                        "app_usage_mb": self.total_memory_allocated,
                        "warning_threshold": MEMORY_WARNING_THRESHOLD,
                        "users_over_limit": len([u for u, m in self.user_memory_usage.items() if m > MAX_MEMORY_USAGE])
                    },
                    
                    "cpu": {
                        "current_percent": avg_cpu,
                        "warning_threshold": CPU_WARNING_THRESHOLD
                    },
                    
                    "queue": {
                        "length": len(self.queued_users),
                        "average_wait_time_seconds": sum(queue_wait_times) / len(queue_wait_times) if queue_wait_times else 0,
                        "max_wait_time_seconds": max(queue_wait_times) if queue_wait_times else 0
                    },
                    
                    "rate_limiting": {
                        "gmail_api_calls_per_user": {k: len(v) for k, v in self.gmail_api_calls.items()},
                        "general_requests_per_user": {k: len(v) for k, v in self.user_requests.items()}
                    },
                    
                    "user_priorities": dict(self.user_priorities),
                    "active_user_list": list(self.active_users),
                    "queued_user_list": self.queued_users.copy(),
                    
                    "performance_history_points": len(self.performance_history),
                    "last_system_check": self.last_system_check,
                    "timestamp": current_time
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting enhanced stats: {e}")
            return {"error": str(e)}

# Global enhanced resource manager instance
resource_manager = EnhancedResourceManager()

# ============================================================================
# ENHANCED MIDDLEWARE FUNCTIONS
# ============================================================================

@asynccontextmanager
async def request_context(user_id: str, request_type: str = "general"):
    """Enhanced context manager for tracking request lifecycle"""
    
    # Increment concurrent request counter
    resource_manager.user_concurrent_requests[user_id] += 1
    
    try:
        yield
    finally:
        # Decrement concurrent request counter
        resource_manager.user_concurrent_requests[user_id] -= 1

async def enhanced_rate_limit_middleware(request: Request, call_next):
    """Enhanced middleware with intelligent queuing and monitoring"""
    
    start_time = time.time()
    
    try:
        # Extract user ID from request
        user_id = await extract_user_id(request)
        
        if not user_id:
            # Allow non-authenticated requests (login, health checks, etc.)
            response = await call_next(request)
            return response
        
        # Check system resources first
        resource_ok, resource_msg, perf_data = await resource_manager.check_system_resources()
        if not resource_ok:
            logger.error(f"🚨 System resource limit exceeded: {resource_msg}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "System temporarily overloaded",
                    "message": resource_msg,
                    "retry_after": 30,
                    "performance_data": perf_data
                }
            )
        
        # Check rate limits
        endpoint_type = "gmail_api" if "/gmail/" in str(request.url) else "general"
        rate_ok, retry_after = resource_manager.check_rate_limit_enhanced(user_id, endpoint_type)
        
        if not rate_ok:
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id} on {endpoint_type}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "endpoint_type": endpoint_type
                }
            )
        
        # Check concurrent requests
        if not resource_manager.check_user_concurrent_requests(user_id):
            logger.warning(f"⚠️ Too many concurrent requests for user {user_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many concurrent requests",
                    "retry_after": 5
                }
            )
        
        # For processing-intensive endpoints, check for processing slot
        if any(path in str(request.url) for path in ["/gmail/fetch", "/financial/process"]):
            slot_ok, slot_msg = await resource_manager.request_processing_slot(user_id)
            
            if not slot_ok:
                return JSONResponse(
                    status_code=202,  # Accepted but queued
                    content={
                        "status": "queued",
                        "message": slot_msg,
                        "estimated_wait_seconds": len(resource_manager.queued_users) * 30
                    }
                )
        
        # Process request with context
        async with request_context(user_id, endpoint_type):
            response = await call_next(request)
        
        # Add performance headers
        processing_time = time.time() - start_time
        response.headers["X-Processing-Time"] = str(round(processing_time, 3))
        response.headers["X-User-Queue-Position"] = "0"  # Active user
        response.headers["X-System-Load"] = str(round(len(resource_manager.active_users) / CONCURRENT_USERS_LIMIT * 100, 1))
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Middleware error: {e}")
        # Return original response on middleware error
        return await call_next(request)
    finally:
        # Cleanup on processing-intensive endpoints
        if user_id and any(path in str(request.url) for path in ["/gmail/fetch", "/financial/process"]):
            resource_manager.release_processing_slot(user_id)

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Keep original function names for backward compatibility
rate_limit_middleware = enhanced_rate_limit_middleware

async def extract_user_id(request: Request) -> Optional[str]:
    """Extract user ID from request with enhanced JWT handling"""
    try:
        # Check authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Extract user ID from JWT token
            from .auth import decode_jwt_token
            token = auth_header.split(" ")[1]
            payload = decode_jwt_token(token)
            if payload:
                return payload.get("user_id")
        
        # Check request body for JWT token (for POST requests)
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    body_data = json.loads(body)
                    if "jwt_token" in body_data:
                        from .auth import decode_jwt_token
                        payload = decode_jwt_token(body_data["jwt_token"])
                        if payload:
                            return payload.get("user_id")
            except:
                pass  # Not JSON or no JWT token in body
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting user ID: {e}")
        return None

@asynccontextmanager
async def email_processing_context(user_id: str):
    """Enhanced email processing context with memory tracking"""
    
    # Request processing slot
    slot_ok, slot_msg = await resource_manager.request_processing_slot(user_id)
    
    if not slot_ok:
        raise HTTPException(
            status_code=503,
            detail=f"Processing queue full: {slot_msg}"
        )
    
    # Set initial memory usage
    resource_manager.update_user_memory(user_id, 0)
    
    try:
        yield
    except Exception as e:
        logger.error(f"Error in email processing context for {user_id}: {e}")
        raise
    finally:
        # Release processing slot
        resource_manager.release_processing_slot(user_id)

def get_health_status() -> Dict:
    """Get enhanced system health status"""
    return resource_manager.get_enhanced_stats()

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

async def performance_monitor():
    """Background task for continuous performance monitoring"""
    
    while True:
        try:
            # Check system resources
            await resource_manager.check_system_resources()
            
            # Cleanup expired entries periodically
            if time.time() % 300 < 1:  # Every 5 minutes
                await resource_manager.cleanup_memory()
            
            # Log system status every minute
            if time.time() % 60 < 1:
                stats = resource_manager.get_enhanced_stats()
                logger.info(f"📊 System Status: {stats['active_users']}/{stats['concurrent_limit']} users, "
                           f"Queue: {stats['queued_users']}, "
                           f"CPU: {stats['cpu']['current_percent']:.1f}%, "
                           f"Memory: {stats['memory']['current_percent']:.1f}%")
            
            await asyncio.sleep(1)  # Check every second
            
        except Exception as e:
            logger.error(f"Performance monitor error: {e}")
            await asyncio.sleep(5)  # Wait longer on error

logger.info("🚀 Enhanced middleware loaded with intelligent resource management!") 