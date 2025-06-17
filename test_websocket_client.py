#!/usr/bin/env python3
"""
Simple WebSocket test client to verify Gmail Intelligence WebSocket connection
"""

import asyncio
import websockets
import json
import sys

# Test JWT token (replace with a valid one from your system)
TEST_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE2MTQxMDk4Mjg4MDE4NzQ5ODI0IiwiZW1haWwiOiJoZWxsb0BzdGF0aW9uOTEuaW4iLCJleHAiOjE3NTA2Nzc1MTl9.tZxCvfFOJYgRK7pyDqrd-E6q4LKbsCeKKvGm7C7Tbxw"

async def test_websocket_connection():
    """Test WebSocket connection stability"""
    uri = "ws://localhost:8000/ws/chat/test-chat-123"
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Send JWT token for authentication
            auth_message = {
                "jwt_token": TEST_JWT_TOKEN
            }
            
            print("🔐 Sending authentication...")
            await websocket.send(json.dumps(auth_message))
            
            # Wait for connection confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Received: {response_data}")
            
            if response_data.get("type") == "connection_success":
                print("✅ Authentication successful!")
                
                # Keep connection alive and test message sending
                print("💬 Connection established. You can now:")
                print("  - Type 'ping' to test ping/pong")
                print("  - Type any query to test Gmail Intelligence")
                print("  - Type 'quit' to exit")
                print("  - Or just wait to test connection stability")
                
                # Start listening for messages
                listen_task = asyncio.create_task(listen_for_messages(websocket))
                
                # Allow user input
                while True:
                    try:
                        user_input = await asyncio.wait_for(
                            asyncio.to_thread(input, "Enter message (or 'quit'): "), 
                            timeout=1.0
                        )
                        
                        if user_input.lower() == 'quit':
                            break
                        elif user_input.lower() == 'ping':
                            await websocket.send(json.dumps({
                                "type": "ping",
                                "message": "ping"
                            }))
                        else:
                            await websocket.send(json.dumps({
                                "type": "message",
                                "message": user_input
                            }))
                            
                    except asyncio.TimeoutError:
                        # No user input, continue listening
                        continue
                    except KeyboardInterrupt:
                        print("\n👋 Exiting...")
                        break
                
                listen_task.cancel()
                
            else:
                print(f"❌ Authentication failed: {response_data}")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔌 Connection closed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def listen_for_messages(websocket):
    """Listen for incoming messages"""
    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("type") == "ping":
                print("🏓 Received ping, sending pong...")
                await websocket.send(json.dumps({
                    "type": "pong",
                    "message": "pong"
                }))
            elif data.get("type") == "pong":
                print("🏓 Received pong - connection alive!")
            else:
                print(f"📨 Received: {data}")
                
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Connection closed while listening")
    except asyncio.CancelledError:
        print("👂 Stopped listening for messages")
    except Exception as e:
        print(f"❌ Error listening: {e}")

if __name__ == "__main__":
    print("🚀 Gmail Intelligence WebSocket Test Client")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        TEST_JWT_TOKEN = sys.argv[1]
        print(f"🔑 Using provided JWT token: {TEST_JWT_TOKEN[:50]}...")
    else:
        print(f"🔑 Using default JWT token: {TEST_JWT_TOKEN[:50]}...")
        print("💡 You can provide your own JWT token as argument: python test_websocket_client.py 'your_jwt_token'")
    
    print("\n🔌 Starting WebSocket connection test...")
    asyncio.run(test_websocket_connection()) 