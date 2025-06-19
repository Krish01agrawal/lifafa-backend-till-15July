#!/usr/bin/env python3
"""
Debug WebSocket connection for production server
Run this on your EC2 instance to test WebSocket functionality
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """Test WebSocket connection to localhost on EC2 instance"""
    
    print("🔍 Gmail Intelligence WebSocket Debug Tool")
    print("==========================================")
    
    # Test local connection first
    local_uri = "ws://localhost:8000/ws/chat/debug-test"
    print(f"🔌 Testing local connection: {local_uri}")
    
    try:
        async with websockets.connect(local_uri) as websocket:
            print("✅ Local WebSocket connected successfully!")
            
            # Send test authentication
            auth_message = {
                "jwt_token": "debug_token_test"
            }
            
            print("🔐 Sending test authentication...")
            await websocket.send(json.dumps(auth_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                print(f"📨 Server response: {response_data}")
                
                if "error" in response_data:
                    print("⚠️  Authentication failed (expected for debug)")
                else:
                    print("✅ WebSocket communication working!")
                    
            except asyncio.TimeoutError:
                print("⏰ Response timeout - server might be processing")
                
    except ConnectionRefused:
        print("❌ Connection refused - server not running on port 8000")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False
    
    # Test external connection
    external_uri = "ws://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8000/ws/chat/debug-test"
    print(f"\n🌐 Testing external connection: {external_uri}")
    
    try:
        async with websockets.connect(external_uri) as websocket:
            print("✅ External WebSocket connected successfully!")
            
            # Send test message
            test_message = {
                "jwt_token": "debug_token_external"
            }
            
            await websocket.send(json.dumps(test_message))
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"📨 External response: {response}")
                print("✅ External WebSocket working!")
                
            except asyncio.TimeoutError:
                print("⏰ External response timeout")
                
    except Exception as e:
        print(f"❌ External WebSocket error: {e}")
        print("🔍 This suggests AWS Security Group issues")
        return False
    
    return True

async def check_server_status():
    """Check if the HTTP server is running"""
    print("\n🌐 Checking HTTP server status...")
    
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ HTTP server running: {data}")
                    return True
                else:
                    print(f"❌ HTTP server error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ HTTP server not accessible: {e}")
        return False

async def main():
    """Run all debug tests"""
    print("Starting WebSocket debug tests...\n")
    
    # Check HTTP server first
    http_ok = await check_server_status()
    if not http_ok:
        print("\n❌ HTTP server is not running. Start your server first.")
        return
    
    # Test WebSocket connections
    websocket_ok = await test_websocket_connection()
    
    print("\n" + "="*50)
    print("DEBUG RESULTS SUMMARY")
    print("="*50)
    print(f"HTTP Server: {'✅ WORKING' if http_ok else '❌ FAILED'}")
    print(f"WebSocket:   {'✅ WORKING' if websocket_ok else '❌ FAILED'}")
    
    if websocket_ok:
        print("\n🎉 WebSocket server is working correctly!")
        print("   The issue might be with AWS Security Groups or frontend configuration.")
    else:
        print("\n⚠️  WebSocket server has issues.")
        print("   Check server logs and configuration.")
    
    print("\n📝 Check server logs with: tail -f websocket_server.log")

if __name__ == "__main__":
    # Install required dependencies
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp for HTTP testing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
    
    asyncio.run(main()) 