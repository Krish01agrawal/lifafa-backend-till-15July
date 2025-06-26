#!/usr/bin/env python3
"""
Test Script: Mem0 Upload Fix Verification
==========================================

This script tests the complete email processing pipeline including:
1. MongoDB connection (with fallback)
2. Email storage in database
3. Mem0 upload functionality
4. Error handling and logging

Usage: python test_mem0_upload_fix.py
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_database_connection():
    """Test MongoDB connection with fallback"""
    
    print("🔧 TESTING DATABASE CONNECTION WITH FALLBACK")
    print("=" * 60)
    
    try:
        from app.db import db_manager
        
        # Test database manager initialization
        print("   ✅ Database manager initialized")
        print(f"   📊 Number of database shards: {len(db_manager.databases)}")
        
        # Check each database shard
        available_dbs = 0
        for i, db in db_manager.databases.items():
            if db is not None:
                available_dbs += 1
                print(f"   ✅ Database shard {i}: Available")
            else:
                print(f"   ❌ Database shard {i}: Not available")
        
        print(f"   📊 Available databases: {available_dbs}/{len(db_manager.databases)}")
        
        if available_dbs == 0:
            print("   ❌ CRITICAL: No databases available!")
            print("   💡 Solutions:")
            print("      1. Start local MongoDB: brew services start mongodb-community")
            print("      2. Check cloud MongoDB connection")
            print("      3. Verify MONGODB_URL environment variable")
            return False
        
        # Test getting a collection
        try:
            test_user_id = "test_user_123"
            emails_coll = await db_manager.get_collection(test_user_id, "emails")
            print(f"   ✅ Successfully got email collection for test user")
            
            # Test a simple operation
            await emails_coll.count_documents({})
            print(f"   ✅ Database operations working")
            
        except Exception as coll_error:
            print(f"   ❌ Collection test failed: {coll_error}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database connection test failed: {e}")
        return False

async def test_email_processing_pipeline():
    """Test the complete email processing pipeline"""
    
    print("\n🔧 TESTING EMAIL PROCESSING PIPELINE")
    print("=" * 60)
    
    try:
        # Import required functions
        from app.gmail import process_and_store_emails
        from app.mem0_agent_agno import EmailMessage, upload_emails_to_mem0
        from app.db import insert_filtered_emails
        
        print("   ✅ All functions imported successfully")
        
        # Create sample email data
        sample_emails = [
            {
                "id": "test_email_1",
                "subject": "Your payment of ₹500 was successful",
                "sender": "payments@paytm.com",
                "snippet": "Transaction ID: TXN123456789",
                "body": "Dear user, your payment of ₹500 to Swiggy was successful. Transaction ID: TXN123456789",
                "date": "2025-01-26T20:30:00Z",
                "headers": {"From": "payments@paytm.com", "To": "user@example.com"},
                "attachments": []
            },
            {
                "id": "test_email_2", 
                "subject": "Special offer just for you!",
                "sender": "marketing@example.com",
                "snippet": "Limited time offer - 50% off everything!",
                "body": "Don't miss out on this amazing deal! Click here to shop now!",
                "date": "2025-01-26T20:25:00Z",
                "headers": {"From": "marketing@example.com", "To": "user@example.com"},
                "attachments": []
            },
            {
                "id": "test_email_3",
                "subject": "Bank statement for January 2025",
                "sender": "statements@hdfc.com",
                "snippet": "Your monthly bank statement is ready",
                "body": "Dear customer, your bank statement for January 2025 is attached. Account balance: ₹25,000",
                "date": "2025-01-26T20:20:00Z",
                "headers": {"From": "statements@hdfc.com", "To": "user@example.com"},
                "attachments": [{"filename": "statement.pdf", "size": 1024}]
            }
        ]
        
        print(f"   📧 Created {len(sample_emails)} sample emails")
        
        # Test email processing
        test_user_id = "test_user_mem0_123"
        
        print(f"   🚀 Processing emails for user: {test_user_id}")
        result = await process_and_store_emails(test_user_id, sample_emails)
        
        print(f"   📊 Processing result: {result}")
        
        # Check if processing was successful
        if result.get("success", False):
            print("   ✅ Email processing completed successfully!")
            print(f"      📧 Emails processed: {result.get('emails_processed', 0)}")
            print(f"      💾 Emails stored: {result.get('emails_stored', 0)}")
            print(f"      🗑️ Promotional filtered: {result.get('promotional_filtered', 0)}")
            print(f"      💰 Financial preserved: {result.get('financial_preserved', 0)}")
            print(f"      📤 Mem0 uploaded: {result.get('mem0_uploaded', False)}")
            
            if result.get('mem0_uploaded', False):
                print("   🎉 MEM0 UPLOAD SUCCESSFUL!")
            else:
                print("   ⚠️ Mem0 upload failed or was skipped")
                
            return True
        else:
            print(f"   ❌ Email processing failed: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"   ❌ Email processing pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mem0_direct_upload():
    """Test direct Mem0 upload functionality"""
    
    print("\n🔧 TESTING DIRECT MEM0 UPLOAD")
    print("=" * 60)
    
    try:
        from app.mem0_agent_agno import EmailMessage, upload_emails_to_mem0
        
        # Create test EmailMessage objects
        test_emails = [
            EmailMessage(
                id="direct_test_1",
                subject="Test financial email",
                sender="bank@example.com",
                snippet="Your account was debited ₹1000",
                body="Transaction details: Amount: ₹1000, Merchant: Amazon",
                date="2025-01-26T20:30:00Z"
            ),
            EmailMessage(
                id="direct_test_2",
                subject="Test regular email",
                sender="friend@example.com",
                snippet="Hey, how are you?",
                body="Just wanted to check in and see how you're doing!",
                date="2025-01-26T20:25:00Z"
            )
        ]
        
        print(f"   📧 Created {len(test_emails)} test EmailMessage objects")
        
        # Test direct upload
        test_user_id = "direct_test_user_456"
        print(f"   📤 Uploading to Mem0 for user: {test_user_id}")
        
        result = await upload_emails_to_mem0(test_user_id, test_emails)
        print(f"   📊 Mem0 upload result: {result}")
        
        if "Successfully processed" in result:
            print("   ✅ Direct Mem0 upload successful!")
            return True
        else:
            print("   ⚠️ Direct Mem0 upload may have issues")
            return False
        
    except Exception as e:
        print(f"   ❌ Direct Mem0 upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_environment_configuration():
    """Test environment configuration"""
    
    print("\n🔧 TESTING ENVIRONMENT CONFIGURATION")
    print("=" * 60)
    
    try:
        # Check environment variables
        mongodb_url = os.getenv("MONGODB_URL")
        mem0_api_key = os.getenv("MEM0_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        use_local_fallback = os.getenv("USE_LOCAL_FALLBACK", "true")
        
        print(f"   📊 MONGODB_URL: {'Set' if mongodb_url else 'Not set (using default)'}")
        print(f"   📊 MEM0_API_KEY: {'Set' if mem0_api_key else 'Not set'}")
        print(f"   📊 OPENAI_API_KEY: {'Set' if openai_api_key else 'Not set'}")
        print(f"   📊 USE_LOCAL_FALLBACK: {use_local_fallback}")
        
        if mem0_api_key:
            print(f"   📊 Mem0 API key preview: {mem0_api_key[:8]}...{mem0_api_key[-3:]}")
        
        # Check configuration loading
        from app.config import SHARD_DATABASES, USE_LOCAL_FALLBACK, LOCAL_MONGODB_URL
        
        print(f"   📊 Configured databases: {len(SHARD_DATABASES)}")
        print(f"   📊 Local fallback enabled: {USE_LOCAL_FALLBACK}")
        print(f"   📊 Local MongoDB URL: {LOCAL_MONGODB_URL}")
        
        missing_config = []
        if not mem0_api_key:
            missing_config.append("MEM0_API_KEY")
        if not openai_api_key:
            missing_config.append("OPENAI_API_KEY")
        
        if missing_config:
            print(f"   ⚠️ Missing configuration: {', '.join(missing_config)}")
            print("   💡 Create a .env file with required API keys")
            return False
        else:
            print("   ✅ All required configuration present")
            return True
        
    except Exception as e:
        print(f"   ❌ Environment configuration test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print(f"🚀 MEM0 UPLOAD FIX VERIFICATION STARTED")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test environment configuration
        env_test = loop.run_until_complete(test_environment_configuration())
        
        # Test database connection
        db_test = loop.run_until_complete(test_database_connection())
        
        # Test email processing pipeline
        pipeline_test = loop.run_until_complete(test_email_processing_pipeline())
        
        # Test direct Mem0 upload
        mem0_test = loop.run_until_complete(test_mem0_direct_upload())
        
        # Overall result
        all_tests = [env_test, db_test, pipeline_test, mem0_test]
        passed_tests = sum(all_tests)
        
        print("\n" + "=" * 70)
        print(f"📊 TEST RESULTS: {passed_tests}/{len(all_tests)} PASSED")
        print("=" * 70)
        
        if passed_tests == len(all_tests):
            print("🎉 ALL TESTS PASSED - MEM0 UPLOAD SHOULD BE WORKING!")
            print("🚀 System ready for production deployment")
            return 0
        else:
            print(f"⚠️ {len(all_tests) - passed_tests} TESTS FAILED")
            print("💡 Check the failed tests above and fix the issues")
            
            if not env_test:
                print("   🔧 Fix: Set up .env file with API keys")
            if not db_test:
                print("   🔧 Fix: Start MongoDB or check connection")
            if not pipeline_test:
                print("   🔧 Fix: Check email processing logic")
            if not mem0_test:
                print("   🔧 Fix: Check Mem0 API configuration")
                
            return 1
            
    except Exception as e:
        print(f"\n❌ TEST EXECUTION FAILED: {e}")
        return 1
    finally:
        loop.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 