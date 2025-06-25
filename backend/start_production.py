#!/usr/bin/env python3
"""
Production startup script for Gmail Intelligence WebSocket server
Ensures proper WebSocket configuration for EC2 deployment
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
    
    print("🚀 Starting Gmail Intelligence WebSocket Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Workers: {workers}")
    print(f"   Log Level: {log_level}")
    print("   WebSocket Endpoints:")
    print(f"     - ws://{host}:{port}/ws/chat")
    print(f"     - ws://{host}:{port}/ws/chat/{{chat_id}}")
    
    # Start server with WebSocket-compatible configuration
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,  # Single worker for WebSocket state management
        log_level=log_level,
        reload=False,  # Disable reload in production
        access_log=True,
        ws_ping_interval=20,  # WebSocket ping interval
        ws_ping_timeout=20,   # WebSocket ping timeout
        timeout_keep_alive=30,  # Keep connections alive
        loop="uvloop"  # Use uvloop for better performance
    )

if __name__ == "__main__":
    main() 