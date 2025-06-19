#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_postman_connection():
    """Test the exact connection Postman is trying to make"""
    try:
        uri = 'ws://localhost:8001/ws/chat/test123'
        print(f'🔌 Connecting to: {uri}')
        
        # Connect like Postman might
        async with websockets.connect(uri) as websocket:
            print('✅ Connected successfully!')
            
            # Send auth message
            auth_msg = {'jwt_token': 'test-token'}
            print('📤 Sending auth message...')
            await websocket.send(json.dumps(auth_msg))
            
            # Wait for response
            print('⏳ Waiting for response...')
            response = await asyncio.wait_for(websocket.recv(), timeout=15)
            print(f'📥 Received: {response}')
            
            print('🎉 Connection test successful!')
            
    except asyncio.TimeoutError:
        print('❌ Connection timeout - this might be the Postman issue')
    except ConnectionRefusedError:
        print('❌ Connection refused - server not running')
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        print(f'   Error type: {type(e).__name__}')

async def test_simple_endpoint():
    """Test the simpler endpoint without chat ID"""
    try:
        uri = 'ws://localhost:8001/ws/chat'
        print(f'\n🔌 Testing simpler endpoint: {uri}')
        
        async with websockets.connect(uri) as websocket:
            print('✅ Connected to simple endpoint!')
            
            auth_msg = {'jwt_token': 'test-token'}
            await websocket.send(json.dumps(auth_msg))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f'📥 Received: {response}')
            
    except Exception as e:
        print(f'❌ Simple endpoint failed: {e}')

if __name__ == "__main__":
    print("🔍 Testing Postman WebSocket Connection Issues")
    print("=" * 50)
    
    asyncio.run(test_postman_connection())
    asyncio.run(test_simple_endpoint()) 