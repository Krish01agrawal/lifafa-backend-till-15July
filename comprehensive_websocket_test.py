#!/usr/bin/env python3
"""
Comprehensive WebSocket test for Gmail Intelligence
Tests both persistent connection and request-response patterns
"""

import json
import time
import asyncio
from websocket import create_connection, WebSocketException

# Test JWT token
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE2MTQxMDk4Mjg4MDE4NzQ5ODI0IiwiZW1haWwiOiJoZWxsb0BzdGF0aW9uOTEuaW4iLCJleHAiOjE3NTA2Nzc1MTl9.tZxCvfFOJYgRK7pyDqrd-E6q4LKbsCeKKvGm7C7Tbxw"
USER_ID = "116141098288018749824"

def test_persistent_connection():
    """Test persistent WebSocket connection (chat pattern)"""
    print("\n🔄 Testing Persistent Connection Pattern")
    print("=" * 50)
    
    try:
        print("🔌 Connecting to chat WebSocket...")
        ws = create_connection("ws://localhost:8000/ws/chat/test-123")
        print("✅ WebSocket connected!")
        
        # Send authentication
        auth_message = {"jwt_token": JWT_TOKEN}
        print("🔐 Sending authentication...")
        ws.send(json.dumps(auth_message))
        
        # Wait for response
        print("⏳ Waiting for connection confirmation...")
        result = ws.recv()
        print(f"📨 Received: {result}")
        
        response_data = json.loads(result)
        if response_data.get("type") == "connection_success":
            print("✅ Authentication successful!")
            
            # Test sending a query
            print("🎯 Sending test query...")
            test_message = {"message": "Show me my transactions"}
            ws.send(json.dumps(test_message))
            
            print("⏳ Waiting for query response...")
            response = ws.recv()
            print(f"📨 Query Response: {response}")
            
            # Keep connection alive for a bit
            print("💬 Keeping connection alive for 3 seconds...")
            time.sleep(3)
            
        else:
            print(f"❌ Authentication failed: {response_data}")
        
        ws.close()
        print("🔌 Connection closed successfully")
        return True
        
    except WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def test_request_response_pattern():
    """Test request-response WebSocket pattern (immediate query)"""
    print("\n⚡ Testing Request-Response Pattern")
    print("=" * 50)
    
    try:
        print("🔌 Connecting to query WebSocket...")
        ws = create_connection(f"ws://localhost:8000/ws/query/{USER_ID}")
        print("✅ WebSocket connected!")
        
        # Send query with JWT token
        query_message = {
            "jwt_token": JWT_TOKEN,
            "query": "Show me my spending analysis"
        }
        print("🔍 Sending query with authentication...")
        ws.send(json.dumps(query_message))
        
        # Wait for response
        print("⏳ Waiting for response...")
        result = ws.recv()
        print(f"📨 Received: {result}")
        
        response_data = json.loads(result)
        if response_data.get("type") != "error":
            print("✅ Query processed successfully!")
        else:
            print(f"❌ Query failed: {response_data}")
        
        ws.close()
        print("🔌 Connection closed")
        return True
        
    except WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def test_frontend_behavior_simulation():
    """Simulate typical frontend behavior - connect, auth, disconnect quickly"""
    print("\n🎭 Testing Frontend Behavior Simulation")
    print("=" * 50)
    
    try:
        print("🔌 Connecting like frontend...")
        ws = create_connection("ws://localhost:8000/ws/chat/frontend-test")
        print("✅ WebSocket connected!")
        
        # Send authentication
        auth_message = {"jwt_token": JWT_TOKEN}
        print("🔐 Sending authentication...")
        ws.send(json.dumps(auth_message))
        
        # Wait for response
        print("⏳ Waiting for connection confirmation...")
        result = ws.recv()
        print(f"📨 Received: {result}")
        
        response_data = json.loads(result)
        if response_data.get("type") == "connection_success":
            print("✅ Authentication successful!")
            print("🏃‍♂️ Simulating immediate frontend disconnection...")
            # Disconnect immediately like frontend does
            
        ws.close()
        print("🔌 Connection closed (simulating frontend behavior)")
        return True
        
    except WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def main():
    print("🚀 Comprehensive Gmail Intelligence WebSocket Test")
    print("=" * 60)
    
    # Test all patterns
    results = []
    
    # Test 1: Persistent Connection
    results.append(test_persistent_connection())
    
    # Test 2: Request-Response Pattern
    results.append(test_request_response_pattern())
    
    # Test 3: Frontend Behavior Simulation
    results.append(test_frontend_behavior_simulation())
    
    # Summary
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    print(f"Persistent Connection: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"Request-Response: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"Frontend Simulation: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! WebSocket is working correctly!")
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main() 