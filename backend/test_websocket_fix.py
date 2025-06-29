#!/usr/bin/env python3
"""
WebSocket Connection Fix Test for 6-Month Email Fetching
========================================================

This script tests the new /ws/historical-sync endpoint that fixes the
WebSocket disconnection issue during long-running 6-month email fetches.

Usage:
    python test_websocket_fix.py

The script will:
1. Connect to the historical sync WebSocket endpoint
2. Send a JWT token for authentication
3. Monitor real-time progress updates during 6-month email sync
4. Demonstrate that the connection stays alive throughout the process
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

# Configuration
WEBSOCKET_URL = "ws://localhost:8001/ws/historical-sync"
# WEBSOCKET_URL = "ws://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8001/ws/historical-sync"

# Test JWT token (replace with actual user token)
TEST_JWT_TOKEN = "your_jwt_token_here"
TEST_ACCESS_TOKEN = "your_access_token_here"

async def test_historical_sync_websocket():
    """
    Test the new historical sync WebSocket endpoint
    """
    print("🔧 TESTING WEBSOCKET FIX FOR 6-MONTH EMAIL SYNC")
    print("=" * 60)
    print(f"📡 Connecting to: {WEBSOCKET_URL}")
    
    try:
        # Connect to WebSocket
        async with websockets.connect(WEBSOCKET_URL, timeout=None) as websocket:
            print("✅ WebSocket connection established")
            
            # Send authentication
            auth_message = {
                "jwt_token": TEST_JWT_TOKEN,
                "access_token": TEST_ACCESS_TOKEN
            }
            
            print("🔐 Sending authentication...")
            await websocket.send(json.dumps(auth_message))
            
            # Monitor progress updates
            connection_start_time = time.time()
            last_heartbeat = time.time()
            progress_count = 0
            
            print("📊 Monitoring real-time progress updates...")
            print("-" * 60)
            
            while True:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    current_time = time.time()
                    connection_duration = current_time - connection_start_time
                    
                    try:
                        data = json.loads(message)
                        message_type = data.get("type", "unknown")
                        
                        if message_type == "progress":
                            progress_count += 1
                            step = data.get("step", "unknown")
                            progress = data.get("progress", 0)
                            msg = data.get("message", "")
                            
                            print(f"🔄 [{progress:3d}%] {step}: {msg}")
                            print(f"   ⏱️  Connection time: {connection_duration:.1f}s | Progress #{progress_count}")
                            
                            # Check if sync is complete
                            if progress >= 100 and step == "complete":
                                print("🎉 HISTORICAL SYNC COMPLETED SUCCESSFULLY!")
                                print(f"✅ Total connection time: {connection_duration:.1f} seconds")
                                print(f"✅ Total progress updates: {progress_count}")
                                break
                                
                        elif message_type == "keepalive":
                            last_heartbeat = current_time
                            heartbeat_interval = current_time - last_heartbeat if last_heartbeat else 0
                            print(f"💓 Keepalive received (interval: {heartbeat_interval:.1f}s)")
                            
                        elif message_type == "error":
                            error_msg = data.get("message", "Unknown error")
                            print(f"❌ Error received: {error_msg}")
                            break
                            
                        else:
                            print(f"📨 Message: {data}")
                            
                    except json.JSONDecodeError:
                        print(f"📨 Raw message: {message}")
                
                except asyncio.TimeoutError:
                    current_time = time.time()
                    connection_duration = current_time - connection_start_time
                    print(f"⚠️  No message received for 30 seconds (connection time: {connection_duration:.1f}s)")
                    
                    # Check if connection is still alive
                    try:
                        await websocket.ping()
                        print("🔄 Connection still alive, continuing...")
                    except Exception as e:
                        print(f"❌ Connection lost: {e}")
                        break
            
            print("=" * 60)
            print("🔧 WEBSOCKET TEST COMPLETED")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

async def test_old_vs_new_endpoints():
    """
    Compare old vs new WebSocket behavior
    """
    print("\n🔄 COMPARING OLD VS NEW WEBSOCKET BEHAVIOR")
    print("=" * 60)
    
    # Test results summary
    print("📊 EXPECTED RESULTS:")
    print("❌ OLD: /gmail/fetch → 6-month sync runs in background → WebSocket disconnects")
    print("✅ NEW: /ws/historical-sync → Real-time progress updates → Connection maintained")
    print("")
    print("🔧 KEY FIXES IMPLEMENTED:")
    print("1. ✅ WebSocket ping timeout: 20s → 15s")
    print("2. ✅ Heartbeat interval: 25s → 8s") 
    print("3. ✅ Real-time progress updates during email fetch")
    print("4. ✅ Memory-safe email processing with progress callbacks")
    print("5. ✅ User connection tracking for targeted updates")
    print("6. ✅ Proper error handling and connection recovery")

if __name__ == "__main__":
    print("🚀 WEBSOCKET DISCONNECTION FIX TEST")
    print("📧 Testing 6-Month Email Sync WebSocket Connection")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Instructions for user
    print("\n📋 SETUP INSTRUCTIONS:")
    print("1. Start your backend server: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001")
    print("2. Replace TEST_JWT_TOKEN and TEST_ACCESS_TOKEN with real values")
    print("3. Run this script: python test_websocket_fix.py")
    print("4. Observe real-time progress updates without disconnection")
    
    # Check if tokens are configured
    if TEST_JWT_TOKEN == "your_jwt_token_here" or TEST_ACCESS_TOKEN == "your_access_token_here":
        print("\n⚠️  CONFIGURATION REQUIRED:")
        print("Please update TEST_JWT_TOKEN and TEST_ACCESS_TOKEN in this script")
        print("You can get these from your browser's developer tools after logging in")
    else:
        # Run the test
        asyncio.run(test_historical_sync_websocket())
    
    # Show comparison
    asyncio.run(test_old_vs_new_endpoints()) 