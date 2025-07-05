#!/usr/bin/env python3
"""
IMMEDIATE FIX FOR USER DATA LOSS
===============================

This script specifically addresses the user's data loss from 500 to 72 emails.
It will scan all databases and recover any missing emails.

Usage:
    python fix_user_data_loss.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def fix_user_data_loss():
    """Fix the specific user's data loss issue"""
    
    # The user ID from your system
    USER_ID = "118347882719275014790"  # Update this if different
    
    print(f"🚨 EMERGENCY DATA RECOVERY")
    print(f"============================")
    print(f"⏰ Started at: {datetime.now()}")
    print(f"🎯 User ID: {USER_ID}")
    print(f"🔍 Issue: Emails reduced from 500 to 72 during mem0 processing")
    print("")
    
    try:
        # Initialize database
        from app.db import db_manager
        # Database manager auto-initializes on import
        print("✅ Database connections initialized")
        
        # Import recovery functions
        from app.db import (
            get_user_emails_across_all_databases,
            get_user_email_count_all_databases,
            recover_user_emails,
            verify_data_integrity_before_processing
        )
        
        print("📊 STEP 1: Scanning all databases for user emails...")
        
        # Check all databases for this user
        all_emails = await get_user_emails_across_all_databases(USER_ID)
        total_unique = len(all_emails)
        
        print(f"📧 Total unique emails found across ALL databases: {total_unique}")
        
        # Check each database individually
        for db_index, database in db_manager.databases.items():
            try:
                emails_coll = database["emails"]
                count = await emails_coll.count_documents({"user_id": USER_ID})
                print(f"   📊 Database {db_index}: {count} emails")
            except Exception as e:
                print(f"   ❌ Database {db_index}: Error - {e}")
        
        # Get primary database count
        primary_emails_coll = await db_manager.get_collection(USER_ID, "emails")
        primary_count = await primary_emails_coll.count_documents({"user_id": USER_ID})
        
        print(f"💾 Primary database emails: {primary_count}")
        print(f"📦 Total emails available: {total_unique}")
        print(f"🔄 Emails that can be recovered: {total_unique - primary_count}")
        print("")
        
        if total_unique <= primary_count:
            print("✅ No recovery needed - all emails are in primary database")
            return
        
        print("🚨 DATA LOSS CONFIRMED - Recovery needed!")
        print(f"📉 Lost emails: {total_unique - primary_count}")
        print("")
        
        # Verify data integrity
        print("🔍 STEP 2: Verifying data integrity...")
        integrity_check = await verify_data_integrity_before_processing(USER_ID)
        
        if integrity_check.get("integrity_ok", False):
            print("✅ Data integrity check passed")
        else:
            print(f"⚠️ Data integrity issues detected: {integrity_check.get('issues', [])}")
        print("")
        
        # Ask for confirmation
        print("🚀 STEP 3: Ready to recover emails")
        print("This will:")
        print("   📦 Consolidate emails from all databases")
        print("   🔄 Remove duplicates")
        print("   💾 Restore missing emails to primary database")
        print("")
        
        confirm = input("Continue with recovery? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Recovery cancelled by user")
            return
        
        print("🚀 Starting email recovery...")
        recovery_result = await recover_user_emails(USER_ID)
        
        if recovery_result.get("success", False):
            emails_recovered = recovery_result.get("emails_recovered", 0)
            final_count = recovery_result.get("final_count", 0)
            
            print("🎉 RECOVERY SUCCESSFUL!")
            print(f"   ➕ Emails recovered: {emails_recovered}")
            print(f"   📊 Final email count: {final_count}")
            print(f"   📈 Recovery rate: {(emails_recovered / (total_unique - primary_count)) * 100:.1f}%")
            
            # Update user record
            from app.db import users_collection
            await users_collection.update_one(
                {"user_id": USER_ID},
                {"$set": {
                    "data_recovery_completed": True,
                    "data_recovery_date": datetime.now().isoformat(),
                    "emails_recovered": emails_recovered,
                    "recovery_method": "emergency_cross_database_recovery",
                    "pre_recovery_count": primary_count,
                    "post_recovery_count": final_count
                }}
            )
            print("✅ User record updated with recovery status")
            
        else:
            print("❌ RECOVERY FAILED!")
            print(f"   Error: {recovery_result.get('message', 'Unknown error')}")
            print(f"   Details: {recovery_result}")
        
        print("")
        print("📊 FINAL VERIFICATION:")
        
        # Final count check
        final_primary_count = await primary_emails_coll.count_documents({"user_id": USER_ID})
        final_total = await get_user_email_count_all_databases(USER_ID)
        
        print(f"   📧 Final primary database count: {final_primary_count}")
        print(f"   📦 Final total across all databases: {final_total}")
        
        if final_primary_count >= total_unique * 0.9:  # 90% recovery threshold
            print("✅ RECOVERY SUCCESS - Most emails recovered")
        elif final_primary_count > primary_count:
            print("✅ PARTIAL RECOVERY - Some emails recovered")
        else:
            print("❌ RECOVERY INCOMPLETE - Manual intervention may be needed")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        print(f"⏰ Completed at: {datetime.now()}")
        print("🏁 Recovery script finished")
    
    return True

async def quick_scan_only():
    """Just scan without recovery - for diagnostics"""
    
    USER_ID = "118347882719275014790"
    
    print(f"🔍 QUICK SCAN - User {USER_ID}")
    print("=" * 50)
    
    try:
        from app.db import db_manager, get_user_emails_across_all_databases
        # Database manager auto-initializes on import
        
        print("📊 Scanning all databases...")
        
        total_emails = 0
        for db_index, database in db_manager.databases.items():
            try:
                emails_coll = database["emails"]
                count = await emails_coll.count_documents({"user_id": USER_ID})
                total_emails += count
                
                # Get sample emails
                sample = await emails_coll.find({"user_id": USER_ID}, {"subject": 1, "date": 1}).limit(2).to_list(length=2)
                
                print(f"   Database {db_index}: {count} emails")
                for email in sample:
                    subject = email.get("subject", "No subject")[:40]
                    date = email.get("date", "No date")
                    print(f"      - {subject}... ({date})")
                
            except Exception as e:
                print(f"   Database {db_index}: Error - {e}")
        
        # Get unique count
        all_emails = await get_user_emails_across_all_databases(USER_ID)
        unique_count = len(all_emails)
        
        print("")
        print(f"📊 SUMMARY:")
        print(f"   Raw total: {total_emails} emails")
        print(f"   Unique emails: {unique_count} emails")
        print(f"   Duplicates: {total_emails - unique_count}")
        
        # Check primary database
        primary_emails_coll = await db_manager.get_collection(USER_ID, "emails")
        primary_count = await primary_emails_coll.count_documents({"user_id": USER_ID})
        print(f"   Primary DB: {primary_count} emails")
        print(f"   Recoverable: {unique_count - primary_count} emails")
        
        if unique_count > primary_count:
            print("⚠️ DATA LOSS DETECTED - Recovery recommended")
        else:
            print("✅ No data loss detected")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scan-only":
        asyncio.run(quick_scan_only())
    else:
        asyncio.run(fix_user_data_loss()) 