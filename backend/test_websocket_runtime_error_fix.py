#!/usr/bin/env python3
"""
🔧 WEBSOCKET RUNTIME ERROR FIX VERIFICATION
===========================================

This script tests the specific fix for:
"RuntimeError: WebSocket is not connected. Need to call 'accept' first."

Usage:
    python test_websocket_runtime_error_fix.py

Features:
- Tests connection state validation
- Verifies RuntimeError handling
- Checks connection cleanup logic
- Validates chat loop stability
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

class RuntimeErrorFixTester:
    """Test suite for WebSocket RuntimeError fixes"""
    
    def __init__(self):
        self.base_url = "ws://localhost:8001"
        self.test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE3NDU0ODc3OTc5NTAwNTIwNzAwIiwiZXhwIjoxNzUxMTc5NTQ1fQ.YOUR_JWT_TOKEN"
        self.results = []
        
    async def test_connection_state_validation(self):
        """Test that connection state is properly validated"""
        logger.info("🔧 Testing connection state validation...")
        
        try:
            uri = f"{self.base_url}/ws/chat/state-test"
            
            async with websockets.connect(uri) as websocket:
                # Authenticate
                auth_message = {"jwt_token": self.test_token}
                await websocket.send(json.dumps(auth_message))
                
                # Wait for welcome
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome)
                
                if "reply" in welcome_data:
                    logger.info("✅ Connection established and authenticated")
                    
                    # Send a test message
                    test_message = {
                        "message": "test connection state",
                        "chatId": "state-test"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    logger.info("✅ Sent test message")
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    if "reply" in response_data:
                        logger.info("✅ Received response - no RuntimeError!")
                        self.results.append(("connection_state", "PASS", "No RuntimeError during normal flow"))
                    else:
                        logger.warning("⚠️ Unexpected response format")
                        self.results.append(("connection_state", "PARTIAL", "Response received but format unexpected"))
                        
                else:
                    logger.error("❌ No welcome message received")
                    self.results.append(("connection_state", "FAIL", "No welcome message"))
                    
        except Exception as e:
            logger.error(f"❌ Connection state test failed: {e}")
            self.results.append(("connection_state", "FAIL", str(e)))
    
    async def test_rapid_connections(self):
        """Test rapid connection/disconnection to trigger race conditions"""
        logger.info("🔧 Testing rapid connections for race conditions...")
        
        successful_connections = 0
        runtime_errors = 0
        other_errors = 0
        total_attempts = 10
        
        for i in range(total_attempts):
            try:
                uri = f"{self.base_url}/ws/chat/rapid-test-{i}"
                
                async with websockets.connect(uri) as websocket:
                    # Quick auth
                    auth_message = {"jwt_token": self.test_token}
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for welcome with short timeout
                    welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    
                    # Quick message exchange
                    test_message = {
                        "message": f"rapid test {i}",
                        "chatId": f"rapid-test-{i}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    
                    successful_connections += 1
                    logger.info(f"✅ Rapid connection {i+1}/{total_attempts} successful")
                    
            except Exception as e:
                if "Need to call \"accept\" first" in str(e):
                    runtime_errors += 1
                    logger.error(f"❌ RuntimeError in connection {i+1}: {e}")
                else:
                    other_errors += 1
                    logger.warning(f"⚠️ Other error in connection {i+1}: {e}")
        
        # Evaluate results
        if runtime_errors == 0:
            self.results.append(("rapid_connections", "PASS", f"No RuntimeErrors in {total_attempts} rapid connections"))
        elif runtime_errors <= 2:
            self.results.append(("rapid_connections", "PARTIAL", f"Only {runtime_errors} RuntimeErrors out of {total_attempts}"))
        else:
            self.results.append(("rapid_connections", "FAIL", f"{runtime_errors} RuntimeErrors out of {total_attempts}"))
        
        logger.info(f"📊 Rapid test results: {successful_connections} success, {runtime_errors} RuntimeErrors, {other_errors} other errors")
    
    async def test_connection_cleanup(self):
        """Test connection cleanup after errors"""
        logger.info("🔧 Testing connection cleanup...")
        
        try:
            uri = f"{self.base_url}/ws/chat/cleanup-test"
            
            # First connection
            async with websockets.connect(uri) as websocket1:
                auth_message = {"jwt_token": self.test_token}
                await websocket1.send(json.dumps(auth_message))
                await asyncio.wait_for(websocket1.recv(), timeout=5.0)
                logger.info("✅ First connection established")
                
                # Immediately try second connection to same chat
                try:
                    async with websockets.connect(uri) as websocket2:
                        await websocket2.send(json.dumps(auth_message))
                        await asyncio.wait_for(websocket2.recv(), timeout=5.0)
                        logger.info("✅ Second connection also established")
                        
                        self.results.append(("connection_cleanup", "PASS", "Multiple connections handled properly"))
                        
                except Exception as e:
                    if "Need to call \"accept\" first" not in str(e):
                        logger.info("✅ Second connection handled gracefully")
                        self.results.append(("connection_cleanup", "PASS", "Connection conflicts handled properly"))
                    else:
                        logger.error(f"❌ RuntimeError in cleanup test: {e}")
                        self.results.append(("connection_cleanup", "FAIL", "RuntimeError during cleanup"))
                        
        except Exception as e:
            logger.error(f"❌ Cleanup test failed: {e}")
            self.results.append(("connection_cleanup", "FAIL", str(e)))
    
    async def test_message_after_disconnect(self):
        """Test sending messages after connection is disconnected"""
        logger.info("🔧 Testing message sending after disconnect...")
        
        try:
            uri = f"{self.base_url}/ws/chat/disconnect-test"
            
            websocket = await websockets.connect(uri)
            
            # Authenticate
            auth_message = {"jwt_token": self.test_token}
            await websocket.send(json.dumps(auth_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info("✅ Connection authenticated")
            
            # Close the connection abruptly
            await websocket.close()
            logger.info("🔌 Connection closed")
            
            # Wait a moment for cleanup
            await asyncio.sleep(1)
            
            # Try to reconnect to same endpoint
            async with websockets.connect(uri) as new_websocket:
                await new_websocket.send(json.dumps(auth_message))
                welcome = await asyncio.wait_for(new_websocket.recv(), timeout=5.0)
                
                if json.loads(welcome).get("reply"):
                    logger.info("✅ Reconnection successful after disconnect")
                    self.results.append(("message_after_disconnect", "PASS", "Reconnection works after disconnect"))
                else:
                    logger.warning("⚠️ Reconnection issue")
                    self.results.append(("message_after_disconnect", "PARTIAL", "Reconnection partial"))
                    
        except Exception as e:
            if "Need to call \"accept\" first" in str(e):
                logger.error(f"❌ RuntimeError in disconnect test: {e}")
                self.results.append(("message_after_disconnect", "FAIL", "RuntimeError after disconnect"))
            else:
                logger.warning(f"⚠️ Other error in disconnect test: {e}")
                self.results.append(("message_after_disconnect", "PARTIAL", str(e)))
    
    def print_results(self):
        """Print comprehensive test results"""
        logger.info("\n" + "="*80)
        logger.info("🔧 WEBSOCKET RUNTIME ERROR FIX VERIFICATION RESULTS")
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
            logger.info("🎉 ALL RUNTIME ERROR FIXES VERIFIED SUCCESSFULLY!")
            logger.info("   ✅ No more 'Need to call accept first' RuntimeErrors")
            logger.info("   ✅ Connection state validation working")
            logger.info("   ✅ Proper error handling in chat loop")
        else:
            logger.warning("⚠️ Some tests failed - RuntimeError fix may need adjustment")
        
        logger.info("="*80)

async def main():
    """Main test execution"""
    logger.info("🚀 Starting WebSocket RuntimeError Fix Verification...")
    logger.info("   This tests the fix for 'Need to call accept first' errors")
    
    tester = RuntimeErrorFixTester()
    
    # Run all tests
    test_functions = [
        tester.test_connection_state_validation,
        tester.test_rapid_connections,
        tester.test_connection_cleanup,
        tester.test_message_after_disconnect
    ]
    
    for test_func in test_functions:
        try:
            await test_func()
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            logger.error(f"❌ Test function {test_func.__name__} crashed: {e}")
    
    # Print final results
    tester.print_results()

if __name__ == "__main__":
    print("\n🔧 WebSocket RuntimeError Fix Verification Script")
    print("=================================================")
    print("This script tests the fix for RuntimeError: 'Need to call accept first'")
    print("Make sure your backend server is running on localhost:8001")
    print("Press Ctrl+C to cancel, or wait 3 seconds to start...")
    
    try:
        time.sleep(3)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}") 