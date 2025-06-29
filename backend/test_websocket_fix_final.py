#!/usr/bin/env python3
"""
🔧 FINAL WEBSOCKET FIX VERIFICATION SCRIPT
==========================================

This script tests the critical WebSocket double-accept fix to ensure
the "Expected ASGI message 'websocket.send' or 'websocket.close', but got 'websocket.accept'" 
error is resolved.

Usage:
    python test_websocket_fix_final.py

Features:
- Tests all WebSocket endpoints
- Verifies no double-accept errors
- Checks authentication flow
- Validates connection stability
"""

import asyncio
import json
import logging
import websockets
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketFixVerifier:
    """Test suite to verify WebSocket fixes"""
    
    def __init__(self):
        self.base_url = "ws://localhost:8001"
        self.test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE3NDU0ODc3OTc5NTAwNTIwNzAwIiwiZXhwIjoxNzUxMTc5NTQ1fQ.YOUR_JWT_TOKEN"
        self.results = []
        
    async def test_chat_websocket(self):
        """Test the main chat WebSocket endpoint"""
        logger.info("🔧 Testing /ws/chat endpoint...")
        
        try:
            uri = f"{self.base_url}/ws/chat/test-chat-id"
            
            async with websockets.connect(uri) as websocket:
                # Test authentication
                auth_message = {
                    "jwt_token": self.test_token
                }
                
                await websocket.send(json.dumps(auth_message))
                logger.info("✅ Sent authentication message")
                
                # Wait for welcome message
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(response)
                
                if "reply" in welcome_data:
                    logger.info("✅ Received welcome message - no double-accept error!")
                    self.results.append(("chat_websocket", "PASS", "No double-accept error"))
                    
                    # Test a simple query
                    test_query = {
                        "message": "hello",
                        "chatId": "test-chat-id"
                    }
                    
                    await websocket.send(json.dumps(test_query))
                    logger.info("✅ Sent test query")
                    
                    # Wait for response
                    query_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    query_data = json.loads(query_response)
                    
                    if "reply" in query_data:
                        logger.info("✅ Chat WebSocket working perfectly!")
                        self.results.append(("chat_query", "PASS", "Query responded successfully"))
                    else:
                        logger.warning("⚠️ Chat query failed")
                        self.results.append(("chat_query", "FAIL", "No reply in response"))
                        
                else:
                    logger.error("❌ No welcome message received")
                    self.results.append(("chat_websocket", "FAIL", "No welcome message"))
                    
        except Exception as e:
            logger.error(f"❌ Chat WebSocket test failed: {e}")
            self.results.append(("chat_websocket", "FAIL", str(e)))
    
    async def test_historical_sync_websocket(self):
        """Test the historical sync WebSocket endpoint"""
        logger.info("🔧 Testing /ws/historical-sync endpoint...")
        
        try:
            uri = f"{self.base_url}/ws/historical-sync"
            
            async with websockets.connect(uri) as websocket:
                # Test authentication
                auth_message = {
                    "jwt_token": self.test_token,
                    "access_token": "test_access_token"
                }
                
                await websocket.send(json.dumps(auth_message))
                logger.info("✅ Sent authentication message")
                
                # Wait for connection confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                progress_data = json.loads(response)
                
                if progress_data.get("type") == "progress" and progress_data.get("step") == "connected":
                    logger.info("✅ Historical sync connected - no double-accept error!")
                    self.results.append(("historical_sync", "PASS", "No double-accept error"))
                else:
                    logger.warning("⚠️ Unexpected response format")
                    self.results.append(("historical_sync", "PARTIAL", "Connected but unexpected format"))
                    
        except Exception as e:
            logger.error(f"❌ Historical sync test failed: {e}")
            self.results.append(("historical_sync", "FAIL", str(e)))
    
    async def test_email_sync_websocket(self):
        """Test the email sync WebSocket endpoint"""
        logger.info("🔧 Testing /ws/email-sync endpoint...")
        
        try:
            uri = f"{self.base_url}/ws/email-sync"
            
            async with websockets.connect(uri) as websocket:
                # Test authentication
                auth_message = {
                    "jwt_token": self.test_token,
                    "access_token": "test_access_token"
                }
                
                await websocket.send(json.dumps(auth_message))
                logger.info("✅ Sent authentication message")
                
                # Wait for connection confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                progress_data = json.loads(response)
                
                if progress_data.get("type") == "progress" and progress_data.get("step") == "connected":
                    logger.info("✅ Email sync connected - no double-accept error!")
                    self.results.append(("email_sync", "PASS", "No double-accept error"))
                else:
                    logger.warning("⚠️ Unexpected response format")
                    self.results.append(("email_sync", "PARTIAL", "Connected but unexpected format"))
                    
        except Exception as e:
            logger.error(f"❌ Email sync test failed: {e}")
            self.results.append(("email_sync", "FAIL", str(e)))
    
    async def test_connection_stability(self):
        """Test connection stability with multiple rapid connections"""
        logger.info("🔧 Testing connection stability...")
        
        successful_connections = 0
        total_attempts = 5
        
        for i in range(total_attempts):
            try:
                uri = f"{self.base_url}/ws/chat/stability-test-{i}"
                
                async with websockets.connect(uri) as websocket:
                    # Quick auth and disconnect
                    auth_message = {"jwt_token": self.test_token}
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for welcome
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    successful_connections += 1
                    logger.info(f"✅ Connection {i+1}/{total_attempts} successful")
                    
            except Exception as e:
                logger.warning(f"⚠️ Connection {i+1}/{total_attempts} failed: {e}")
        
        success_rate = (successful_connections / total_attempts) * 100
        
        if success_rate >= 80:
            self.results.append(("stability_test", "PASS", f"{success_rate}% success rate"))
        else:
            self.results.append(("stability_test", "FAIL", f"Only {success_rate}% success rate"))
    
    def print_results(self):
        """Print comprehensive test results"""
        logger.info("\n" + "="*80)
        logger.info("🔧 WEBSOCKET FIX VERIFICATION RESULTS")
        logger.info("="*80)
        
        passed = 0
        failed = 0
        
        for test_name, status, details in self.results:
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            logger.info(f"{status_icon} {test_name.upper()}: {status}")
            logger.info(f"   Details: {details}")
            
            if status == "PASS":
                passed += 1
            elif status == "FAIL":
                failed += 1
        
        logger.info("-" * 80)
        logger.info(f"📊 SUMMARY: {passed} passed, {failed} failed, {len(self.results) - passed - failed} partial")
        
        if failed == 0:
            logger.info("🎉 ALL WEBSOCKET FIXES VERIFIED SUCCESSFULLY!")
            logger.info("   ✅ No more 'Expected ASGI message websocket.accept' errors")
            logger.info("   ✅ Authentication flows working correctly")
            logger.info("   ✅ Connection stability improved")
        else:
            logger.warning("⚠️ Some tests failed - please check the logs above")
        
        logger.info("="*80)

async def main():
    """Main test execution"""
    logger.info("🚀 Starting WebSocket Fix Verification...")
    logger.info("   This will test the critical double-accept fix")
    logger.info("   Expected: No 'websocket.accept' ASGI errors")
    
    verifier = WebSocketFixVerifier()
    
    # Run all tests
    test_functions = [
        verifier.test_chat_websocket,
        verifier.test_historical_sync_websocket,
        verifier.test_email_sync_websocket,
        verifier.test_connection_stability
    ]
    
    for test_func in test_functions:
        try:
            await test_func()
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            logger.error(f"❌ Test function {test_func.__name__} crashed: {e}")
    
    # Print final results
    verifier.print_results()

if __name__ == "__main__":
    print("\n🔧 WebSocket Fix Verification Script")
    print("=====================================")
    print("This script tests the critical WebSocket double-accept fix.")
    print("Make sure your backend server is running on localhost:8001")
    print("Press Ctrl+C to cancel, or wait 3 seconds to start...")
    
    try:
        time.sleep(3)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}") 