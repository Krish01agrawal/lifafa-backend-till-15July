#!/usr/bin/env python3
"""
Simple WebSocket test using websocket-client library
"""

import json
import time
from websocket import create_connection, WebSocketException

def test_websocket():
    """Test WebSocket connection with simple websocket-client library"""
    
    # Test JWT token
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE2MTQxMDk4Mjg4MDE4NzQ5ODI0IiwiZW1haWwiOiJoZWxsb0BzdGF0aW9uOTEuaW4iLCJleHAiOjE3NTA2Nzc1MTl9.tZxCvfFOJYgRK7pyDqrd-E6q4LKbsCeKKvGm7C7Tbxw"
    
    try:
        print("🔌 Connecting to WebSocket...")
        ws = create_connection("ws://localhost:8000/ws/chat/test-123")
        print("✅ WebSocket connected!")
        
        # Send authentication
        auth_message = {"jwt_token": jwt_token}
        print("🔐 Sending authentication...")
        ws.send(json.dumps(auth_message))
        
        # Wait for response
        print("⏳ Waiting for response...")
        result = ws.recv()
        print(f"📨 Received: {result}")
        
        response_data = json.loads(result)
        if response_data.get("type") == "connection_success":
            print("✅ Authentication successful!")
            print("💬 Connection is stable. Waiting 10 seconds...")
            
            # Keep connection alive for 10 seconds
            for i in range(10):
                print(f"⏰ {i+1}/10 seconds - Connection still alive")
                time.sleep(1)
            
            print("🎯 Sending test message...")
            test_message = {"message": "Hello Gmail Intelligence!"}
            ws.send(json.dumps(test_message))
            
            print("⏳ Waiting for response...")
            response = ws.recv()
            print(f"📨 Response: {response}")
            
        else:
            print(f"❌ Authentication failed: {response_data}")
        
        ws.close()
        print("🔌 Connection closed successfully")
        
    except WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except Exception as e:
        print(f"❌ General error: {e}")

if __name__ == "__main__":
    print("🚀 Simple WebSocket Test")
    print("=" * 30)
    test_websocket() 