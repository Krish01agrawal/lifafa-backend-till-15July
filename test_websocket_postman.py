#!/usr/bin/env python3
"""
Simple WebSocket test to verify server is working
This will help diagnose why Postman isn't connecting
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """Test WebSocket connection to identify issues"""
    
    # Test backend port (8001) as specified by user
    test_urls = [
        "ws://localhost:8001/ws/chat/postman-test"
    ]
    
    for url in test_urls:
        print(f"\n🔌 Testing connection to: {url}")
        try:
            # Try to connect
            async with websockets.connect(url) as websocket:
                print(f"✅ Connected successfully to {url}")
                
                # Send a test auth message
                test_auth = {
                    "jwt_token": "test-token"
                }
                
                print("🔐 Sending test authentication...")
                await websocket.send(json.dumps(test_auth))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    print(f"📨 Received response: {response}")
                    
                    # Parse response
                    response_data = json.loads(response)
                    if "error" in response_data:
                        print("⚠️  Authentication failed (expected for test token)")
                    else:
                        print("✅ WebSocket communication working!")
                        
                except asyncio.TimeoutError:
                    print("⏰ Response timeout - server might be processing")
                    
                print(f"✅ {url} is working!")
                return True
                
        except ConnectionRefusedError:
            print(f"❌ Connection refused to {url} - server not running on this port")
        except Exception as e:
            print(f"❌ Error connecting to {url}: {e}")
    
    print("\n❌ No working WebSocket server found")
    return False

async def test_http_server():
    """Test if HTTP server is running"""
    import aiohttp
    
    test_urls = [
        "http://localhost:8001/health"  # Backend is on 8001
    ]
    
    print("\n🌐 Testing HTTP server...")
    
    for url in test_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ HTTP server running on {url}: {data}")
                        return True
        except Exception as e:
            print(f"❌ HTTP server not accessible at {url}: {e}")
    
    print("❌ No HTTP server found")
    return False

async def main():
    """Main test function"""
    print("🔍 WebSocket Connection Diagnostic Tool")
    print("=" * 50)
    
    # Test HTTP server first
    http_working = await test_http_server()
    
    # Test WebSocket connections
    websocket_working = await test_websocket_connection()
    
    print("\n📋 Summary:")
    print(f"   HTTP Server: {'✅ Working' if http_working else '❌ Not accessible'}")
    print(f"   WebSocket: {'✅ Working' if websocket_working else '❌ Not accessible'}")
    
    if http_working and not websocket_working:
        print("\n💡 Recommendations:")
        print("   1. Check if your server is running with WebSocket support")
        print("   2. Verify the port number in Postman matches your server")
        print("   3. Make sure your FastAPI app includes the WebSocket router")
    
    elif not http_working:
        print("\n💡 Recommendations:")
        print("   1. Start your server first")
        print("   2. Check if it's running on port 8000 or 8001")
        print("   3. Verify no firewall is blocking the connection")

if __name__ == "__main__":
    # Install required packages if not available
    try:
        import websockets
        import aiohttp
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "aiohttp"])
        import websockets
        import aiohttp
    
    asyncio.run(main()) 