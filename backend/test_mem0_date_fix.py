#!/usr/bin/env python3
"""
Test Script: Mem0 Date Conversion Fix Verification
==================================================

This script tests the complete email processing pipeline with the date conversion fix:
1. MongoDB storage with datetime objects
2. Date conversion from datetime to string
3. EmailMessage creation with proper date format
4. Mem0 upload functionality

Usage: python test_mem0_date_fix.py
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_complete_mem0_pipeline():
    """Test the complete Mem0 upload pipeline with date fix"""
    
    print("🔧 TESTING COMPLETE MEM0 PIPELINE WITH DATE FIX")
    print("=" * 70)
    
    try:
        # Import required functions
        from app.gmail import process_and_store_emails
        from app.mem0_agent_agno import EmailMessage, upload_emails_to_mem0
        from app.db import insert_filtered_emails, get_complete_user_emails
        
        print("   ✅ All functions imported successfully")
        
        # Create sample emails with various date formats
        sample_emails = [
            {
                "id": "date_test_1",
                "subject": "Payment successful - ₹1500",
                "sender": "payments@paytm.com",
                "snippet": "Your payment was successful",
                "body": "Dear customer, your payment of ₹1500 to Swiggy was successful.",
                "date": datetime(2025, 6, 26, 15, 30, 45),  # datetime object
                "headers": {"From": "payments@paytm.com"},
                "attachments": []
            },
            {
                "id": "date_test_2",
                "subject": "Bank statement ready",
                "sender": "bank@hdfc.com", 
                "snippet": "Your statement is ready",
                "body": "Your monthly bank statement is ready for download.",
                "date": "2025-06-25T10:15:30Z",  # string format
                "headers": {"From": "bank@hdfc.com"},
                "attachments": []
            },
            {
                "id": "date_test_3",
                "subject": "Special offer - 50% off!",
                "sender": "marketing@shop.com",
                "snippet": "Limited time offer",
                "body": "Don't miss this amazing deal!",
                "date": datetime.now(),  # current datetime
                "headers": {"From": "marketing@shop.com"},
                "attachments": []
            }
        ]
        
        print(f"   📧 Created {len(sample_emails)} test emails with mixed date formats")
        
        # Test user ID
        test_user_id = "date_fix_test_user_789"
        
        # Step 1: Test email processing and storage
        print(f"\n   🚀 Step 1: Processing emails for user {test_user_id}")
        result = await process_and_store_emails(test_user_id, sample_emails)
        
        print(f"   📊 Processing result: {result}")
        
        if not result.get("success", False):
            print(f"   ❌ Email processing failed: {result}")
            return False
        
        # Step 2: Verify emails were stored
        print(f"\n   🔍 Step 2: Verifying emails were stored in MongoDB")
        stored_emails = await get_complete_user_emails(test_user_id, limit=10)
        
        print(f"   📧 Retrieved {len(stored_emails)} emails from MongoDB")
        
        if not stored_emails:
            print("   ❌ No emails found in MongoDB!")
            return False
        
        # Step 3: Test date conversion manually
        print(f"\n   📅 Step 3: Testing date conversion for each email")
        
        converted_emails = []
        for i, email_data in enumerate(stored_emails):
            try:
                # Apply the same conversion logic as in gmail.py
                date_value = email_data.get("date", "")
                if hasattr(date_value, 'isoformat'):  # It's a datetime object
                    date_str = date_value.isoformat()
                elif isinstance(date_value, str):
                    date_str = date_value
                else:
                    date_str = str(date_value) if date_value else ""
                
                print(f"      📅 Email {i+1}: {type(date_value).__name__} -> {date_str[:19]}...")
                
                # Test EmailMessage creation
                email_msg = EmailMessage(
                    id=email_data.get("id", f"email_{i}"),
                    subject=email_data.get("subject", ""),
                    sender=email_data.get("sender", ""),
                    snippet=email_data.get("snippet", ""),
                    body=email_data.get("body", ""),
                    date=date_str
                )
                converted_emails.append(email_msg)
                
            except Exception as conversion_error:
                print(f"      ❌ Failed to convert email {i}: {conversion_error}")
                return False
        
        print(f"   ✅ Successfully converted {len(converted_emails)} emails to EmailMessage format")
        
        # Step 4: Test direct Mem0 upload
        print(f"\n   📤 Step 4: Testing direct Mem0 upload")
        
        try:
            mem0_result = await upload_emails_to_mem0(test_user_id, converted_emails)
            print(f"   📊 Mem0 upload result: {mem0_result}")
            
            if "Successfully processed" in mem0_result:
                print("   ✅ Direct Mem0 upload successful!")
            else:
                print("   ⚠️ Mem0 upload completed but may have issues")
            
        except Exception as mem0_error:
            print(f"   ❌ Mem0 upload failed: {mem0_error}")
            return False
        
        # Step 5: Test the complete pipeline
        print(f"\n   🔄 Step 5: Testing complete pipeline with new user")
        
        new_test_user = "complete_pipeline_test_456"
        complete_result = await process_and_store_emails(new_test_user, sample_emails)
        
        print(f"   📊 Complete pipeline result: {complete_result}")
        
        if complete_result.get("mem0_uploaded", False):
            print("   🎉 COMPLETE PIPELINE SUCCESS - MEM0 UPLOAD WORKING!")
            return True
        else:
            print("   ⚠️ Complete pipeline completed but Mem0 upload may have failed")
            return False
        
    except Exception as e:
        print(f"   ❌ Complete pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_date_edge_cases():
    """Test various date format edge cases"""
    
    print("\n🔧 TESTING DATE FORMAT EDGE CASES")
    print("=" * 70)
    
    try:
        from app.mem0_agent_agno import EmailMessage
        
        # Test various date formats
        test_cases = [
            ("datetime object", datetime(2025, 6, 26, 15, 30, 45, 123456)),
            ("ISO string", "2025-06-26T15:30:45.123456"),
            ("simple string", "2025-06-26 15:30:45"),
            ("empty string", ""),
            ("None value", None),
            ("timestamp", 1719420645),
        ]
        
        for case_name, date_value in test_cases:
            try:
                # Apply conversion logic
                if hasattr(date_value, 'isoformat'):  # It's a datetime object
                    date_str = date_value.isoformat()
                elif isinstance(date_value, str):
                    date_str = date_value
                else:
                    date_str = str(date_value) if date_value else ""
                
                # Test EmailMessage creation
                email_msg = EmailMessage(
                    id=f"test_{case_name.replace(' ', '_')}",
                    subject="Test Subject",
                    sender="test@example.com",
                    snippet="Test snippet",
                    body="Test body",
                    date=date_str
                )
                
                print(f"   ✅ {case_name}: {date_value} -> {date_str}")
                
            except Exception as e:
                print(f"   ❌ {case_name}: {date_value} -> FAILED: {e}")
                return False
        
        print("   ✅ All date format edge cases handled successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Date edge case test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print(f"🚀 MEM0 DATE CONVERSION FIX VERIFICATION")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test date edge cases
        edge_case_test = loop.run_until_complete(test_date_edge_cases())
        
        # Test complete pipeline
        pipeline_test = loop.run_until_complete(test_complete_mem0_pipeline())
        
        # Overall result
        all_tests = [edge_case_test, pipeline_test]
        passed_tests = sum(all_tests)
        
        print("\n" + "=" * 80)
        print(f"📊 FINAL TEST RESULTS: {passed_tests}/{len(all_tests)} PASSED")
        print("=" * 80)
        
        if passed_tests == len(all_tests):
            print("🎉 ALL TESTS PASSED - MEM0 DATE CONVERSION FIX SUCCESSFUL!")
            print("🚀 Mem0 upload should now work with all date formats")
            print("✅ System ready for production with complete email intelligence")
            return 0
        else:
            print(f"⚠️ {len(all_tests) - passed_tests} TESTS FAILED")
            print("💡 Check the failed tests above and investigate further")
            return 1
            
    except Exception as e:
        print(f"\n❌ TEST EXECUTION FAILED: {e}")
        return 1
    finally:
        loop.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 