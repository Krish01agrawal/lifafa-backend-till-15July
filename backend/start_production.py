#!/usr/bin/env python3
"""
Production startup script for Gmail Intelligence WebSocket server
Ensures proper WebSocket configuration for EC2 deployment with optimized timeouts
"""

import uvicorn
import os
from .main import app

def main():
    """Start the production server with WebSocket support"""
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))  # Use 1 worker for WebSocket compatibility
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print("🚀 Starting Gmail Intelligence WebSocket Server (OPTIMIZED)")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Workers: {workers}")
    print(f"   Log Level: {log_level}")
    print("   WebSocket Endpoints:")
    print(f"     - ws://{host}:{port}/ws/chat")
    print(f"     - ws://{host}:{port}/ws/chat/{{chat_id}}")
    print(f"     - ws://{host}:{port}/ws/email-sync")
    print("   🔧 WebSocket Optimizations:")
    print("     - Ping Interval: 10s (was 20s)")
    print("     - Ping Timeout: 15s (was 20s)")
    print("     - Keep Alive: 60s (was 30s)")
    print("     - Heartbeat: Every 8s")
    
    # Start server with WebSocket-compatible configuration
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,  # Single worker for WebSocket state management
        log_level=log_level,
        reload=False,  # Disable reload in production
        access_log=True,
        ws_ping_interval=10,  # ✅ FIXED: Reduced from 20s - faster ping detection
        ws_ping_timeout=15,   # ✅ FIXED: Reduced from 20s - quicker timeout detection  
        timeout_keep_alive=60,  # ✅ INCREASED: Keep connections alive longer
        loop="uvloop"  # Use uvloop for better performance
    )

if __name__ == "__main__":
    main() 