"""
Optimized Email Processing Pipeline
===================================

This module implements the optimized flow where financial transaction extraction
happens IMMEDIATELY after MongoDB storage and BEFORE Mem0 upload.

Flow Order:
1. 📧 Gmail API Fetch
2. 🔍 Smart Email Filtering  
3. 💾 MongoDB Storage
4. 💰 FAST Financial Transaction Extraction (NEW PRIORITY)
5. 🧠 Mem0 Memory Upload (Time-consuming, moved to background)

Benefits:
- Financial data available in 5-10 seconds instead of 5-10 minutes
- Users can query financial transactions immediately
- Mem0 upload happens in background without blocking financial features
- Optimized user experience with instant financial insights
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from .fast_financial_processor import process_financial_transactions_from_mongodb
from .db import users_collection

# Configure comprehensive logging for optimized email processor
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create specialized loggers for different components
pipeline_logger = logging.getLogger(f"{__name__}.pipeline")
filter_logger = logging.getLogger(f"{__name__}.filter")
storage_logger = logging.getLogger(f"{__name__}.storage")
financial_logger = logging.getLogger(f"{__name__}.financial")
mem0_logger = logging.getLogger(f"{__name__}.mem0")
performance_logger = logging.getLogger(f"{__name__}.performance")
compression_logger = logging.getLogger(f"{__name__}.compression")

logger.info("🚀 OPTIMIZED EMAIL PROCESSOR - Enhanced logging initialized")
logger.info("📊 Component loggers: pipeline, filter, storage, financial, mem0, performance, compression")

async def process_and_store_emails_optimized(user_id: str, emails: List[Dict], is_historical: bool = False) -> Dict[str, Any]:
    """
    🚀 OPTIMIZED email processing pipeline with PRIORITIZED financial extraction
    
    NEW FLOW:
    1. Filter emails
    2. Store in MongoDB  
    3. 💰 IMMEDIATE financial extraction (5-10 seconds)
    4. 🧠 Background Mem0 upload (5-10 minutes)
    
    This allows users to query financial data immediately!
    """
    start_time = datetime.now()
    processing_type = "optimized-historical" if is_historical else "optimized-immediate"
    process_id = f"opt_{user_id}_{int(start_time.timestamp() * 1000)}"
    
    pipeline_logger.info(f"🚀 [START] OPTIMIZED PIPELINE - Process ID: {process_id}")
    pipeline_logger.info(f"📊 [INPUT] User: {user_id}, Emails: {len(emails)}, Type: {processing_type}")
    
    try:
        # ===== STEP 1: Smart Email Filtering + Intelligent Compression =====
        filter_start = datetime.now()
        filter_logger.info(f"🔍 [STEP 1] Starting smart email filtering - Process ID: {process_id}")
        
        from .db import email_filter
        from .intelligent_compressor import intelligent_compressor
        
        batch_size = 50
        filtered_emails = []
        compression_stats = {"successful": 0, "failed": 0, "total_saved_chars": 0}
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_start = datetime.now()
            
            # Apply smart filtering
            filter_logger.info(f"🔍 [FILTERING] Processing batch {i//batch_size + 1}/{(len(emails)-1)//batch_size + 1}")
            
            if hasattr(email_filter, 'smart_filter_emails'):
                batch_filtered = await email_filter.smart_filter_emails(batch, user_id, processing_type)
            else:
                batch_filtered = batch
            
            # Apply intelligent compression to filtered emails
            batch_compressed = []
            for email in batch_filtered:
                try:
                    original_size = len(str(email))
                    compressed_email = intelligent_compressor.compress_email_intelligently(email)
                    compressed_size = len(str(compressed_email))
                    
                    batch_compressed.append(compressed_email)
                    compression_stats["successful"] += 1
                    compression_stats["total_saved_chars"] += max(0, original_size - compressed_size)
                    
                except Exception as compression_error:
                    compression_stats["failed"] += 1
                    compression_logger.error(f"❌ [COMPRESSION] Error for email {email.get('id', 'unknown')}: {compression_error}")
                    batch_compressed.append(email)  # Use original if compression fails
            
            filtered_emails.extend(batch_compressed)
            batch_time = (datetime.now() - batch_start).total_seconds()
            
            if i % (batch_size * 2) == 0:  # Log every 2 batches
                progress = ((i + batch_size) / len(emails)) * 100
                filter_logger.info(f"📊 [PROGRESS] Filtering: {progress:.1f}%, Batch time: {batch_time:.2f}s")
            
            await asyncio.sleep(0.05)  # Yield control
        
        filter_time = (datetime.now() - filter_start).total_seconds()
        filter_logger.info(f"✅ [STEP 1] Filtering complete - Process ID: {process_id}, Time: {filter_time:.2f}s")
        filter_logger.info(f"📊 [RESULTS] Original: {len(emails)}, Filtered: {len(filtered_emails)}, Removed: {len(emails) - len(filtered_emails)}")
        
        compression_logger.info(f"📊 [COMPRESSION] Stats - Successful: {compression_stats['successful']}, Failed: {compression_stats['failed']}")
        compression_logger.info(f"💾 [COMPRESSION] Storage saved: {compression_stats['total_saved_chars']} characters")
        
        if not filtered_emails:
            pipeline_logger.info(f"📭 [COMPLETE] No emails to process after filtering - Process ID: {process_id}")
            return {
                "success": True,
                "status": "success", 
                "emails_stored": 0,
                "financial_transactions": 0,
                "message": "No emails to process after filtering"
            }
        
        # ===== STEP 2: Store in MongoDB =====
        storage_start = datetime.now()
        storage_logger.info(f"💾 [STEP 2] Starting MongoDB storage - Process ID: {process_id}, Count: {len(filtered_emails)}")
        
        storage_result = await insert_filtered_emails_optimized(user_id, filtered_emails, processing_type)
        storage_time = (datetime.now() - storage_start).total_seconds()
        
        if not storage_result.get("success", False):
            storage_logger.error(f"❌ [STEP 2] MongoDB storage failed - Process ID: {process_id}, Time: {storage_time:.2f}s")
            storage_logger.error(f"🔍 [DEBUG] Storage result: {storage_result}")
            return {
                "success": False,
                "status": "error",
                "message": f"Failed to store emails: {storage_result.get('error', 'Unknown error')}"
            }
        
        stored_count = storage_result.get("inserted", 0)
        storage_logger.info(f"✅ [STEP 2] MongoDB storage complete - Process ID: {process_id}, Time: {storage_time:.2f}s")
        storage_logger.info(f"📊 [RESULTS] Stored: {stored_count}/{len(filtered_emails)} emails")
        
        # ===== STEP 3: 💰 IMMEDIATE Financial Transaction Extraction =====
        financial_start = datetime.now()
        financial_transactions = 0
        
        try:
            financial_logger.info(f"💰 [STEP 3] Starting IMMEDIATE financial extraction - Process ID: {process_id}")
            financial_logger.info(f"📊 [CONTEXT] User: {user_id}, Stored emails: {stored_count}")
            
            # Extract financial transactions directly from stored MongoDB emails
            financial_result = await process_financial_transactions_from_mongodb(user_id)
            financial_time = (datetime.now() - financial_start).total_seconds()
            
            if financial_result.get("status") == "success":
                financial_transactions = financial_result.get("transactions_found", 0)
                total_amount = financial_result.get("total_amount", 0)
                
                financial_logger.info(f"✅ [STEP 3] Financial extraction complete - Process ID: {process_id}, Time: {financial_time:.2f}s")
                financial_logger.info(f"📊 [RESULTS] Transactions: {financial_transactions}, Amount: ₹{total_amount:,.2f}")
                
                # Update user flags for immediate financial availability
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "recent_financial_transactions": financial_transactions,
                        "financial_extraction_completed": True,
                        "financial_extraction_date": datetime.now().isoformat(),
                        "financial_processing_time": financial_time,
                        "optimized_pipeline_used": True
                    }}
                )
                
                # Console notification for immediate financial availability
                print(f"\n{'='*80}")
                print(f"💰 FINANCIAL DATA READY for User: {user_id}")
                print(f"📊 Financial transactions extracted: {financial_transactions}")
                print(f"💵 Total amount: ₹{total_amount:,.2f}")
                print(f"⏱️ Processing time: {financial_time:.2f} seconds")
                print(f"✅ User can query financial data immediately!")
                print(f"🔄 Background: Mem0 upload starting...")
                print(f"{'='*80}\n")
                
            else:
                financial_logger.warning(f"⚠️ [STEP 3] Financial extraction failed - Process ID: {process_id}")
                financial_logger.warning(f"🔍 [DEBUG] Error: {financial_result.get('error', 'Unknown error')}")
                
        except Exception as financial_error:
            financial_time = (datetime.now() - financial_start).total_seconds()
            financial_logger.error(f"❌ [STEP 3] Financial extraction exception - Process ID: {process_id}, Time: {financial_time:.2f}s")
            financial_logger.error(f"🔍 [DEBUG] Exception: {str(financial_error)}", exc_info=True)
            # Continue with Mem0 upload even if financial extraction fails
        
        # ===== STEP 4: 🧠 Background Mem0 Upload (Non-blocking) =====
        if stored_count > 0:
            mem0_logger.info(f"🧠 [STEP 4] Starting background Mem0 upload - Process ID: {process_id}, Count: {stored_count}")
            asyncio.create_task(upload_emails_to_mem0_background(
                user_id, 
                filtered_emails[:stored_count], 
                processing_type,
                process_id
            ))
            mem0_logger.info(f"✅ [STEP 4] Mem0 upload task created - Process ID: {process_id}")
        
        # ===== FINAL SUMMARY =====
        total_time = (datetime.now() - start_time).total_seconds()
        
        performance_logger.info(f"🎯 [PERFORMANCE] OPTIMIZED PIPELINE - Process ID: {process_id}")
        performance_logger.info(f"   ⏱️ Total time: {total_time:.2f}s")
        performance_logger.info(f"   🔍 Filtering time: {filter_time:.2f}s ({filter_time/total_time*100:.1f}%)")
        performance_logger.info(f"   💾 Storage time: {storage_time:.2f}s ({storage_time/total_time*100:.1f}%)")
        performance_logger.info(f"   💰 Financial time: {financial_time:.2f}s ({financial_time/total_time*100:.1f}%)")
        performance_logger.info(f"   📊 Throughput: {len(emails)/total_time:.1f} emails/second")
        
        pipeline_logger.info(f"🎉 [COMPLETE] OPTIMIZED PIPELINE SUCCESS - Process ID: {process_id}, Time: {total_time:.2f}s")
        
        return {
            "success": True,
            "status": "success",
            "emails_stored": stored_count,
            "financial_transactions": financial_transactions,
            "promotional_filtered": len(emails) - len(filtered_emails),
            "processing_type": processing_type,
            "financial_ready": financial_transactions > 0,
            "mem0_upload_status": "background_processing",
            "message": f"Emails stored and financial data extracted. Mem0 upload in progress.",
            "performance_metrics": {
                "total_time": total_time,
                "filter_time": filter_time,
                "storage_time": storage_time,
                "financial_time": financial_time,
                "throughput": len(emails)/total_time
            }
        }
        
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        pipeline_logger.error(f"❌ [CRITICAL] OPTIMIZED PIPELINE FAILED - Process ID: {process_id}, Time: {total_time:.2f}s")
        pipeline_logger.error(f"🔍 [DEBUG] Exception: {str(e)}", exc_info=True)
        return {
            "success": False,
            "status": "error",
            "message": str(e),
            "processing_type": processing_type,
            "process_id": process_id
        }

async def insert_filtered_emails_optimized(user_id: str, emails: List[Dict], processing_type: str) -> Dict[str, Any]:
    """
    Optimized email insertion with smaller batches for faster processing
    """
    start_time = datetime.now()
    storage_id = f"storage_{user_id}_{int(start_time.timestamp() * 1000)}"
    
    storage_logger.info(f"💾 [START] OPTIMIZED STORAGE - Storage ID: {storage_id}")
    storage_logger.info(f"📊 [INPUT] User: {user_id}, Emails: {len(emails)}, Type: {processing_type}")
    
    try:
        from .db import insert_filtered_emails
        
        # Use smaller batches for faster financial extraction
        batch_size = 20  # Reduced batch size for speed
        total_inserted = 0
        failed_batches = 0
        
        storage_logger.info(f"⚙️ [CONFIG] Batch size: {batch_size}, Total batches: {(len(emails)-1)//batch_size + 1}")
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_start = datetime.now()
            
            storage_logger.info(f"📦 [BATCH] Processing batch {i//batch_size + 1}/{(len(emails)-1)//batch_size + 1} - Storage ID: {storage_id}")
            
            batch_result = await insert_filtered_emails(user_id, batch, processing_type)
            batch_time = (datetime.now() - batch_start).total_seconds()
            
            if batch_result.get("success", False):
                batch_inserted = batch_result.get("inserted", 0)
                total_inserted += batch_inserted
                storage_logger.info(f"✅ [BATCH] Success - Inserted: {batch_inserted}/{len(batch)}, Time: {batch_time:.2f}s")
            else:
                failed_batches += 1
                error_msg = batch_result.get("error", "Unknown error")
                storage_logger.error(f"❌ [BATCH] Failed - Error: {error_msg}, Time: {batch_time:.2f}s")
            
            await asyncio.sleep(0.02)  # Minimal delay
            
            # Progress logging every 5 batches
            if i % (batch_size * 5) == 0:
                progress = ((i + batch_size) / len(emails)) * 100
                storage_logger.info(f"📊 [PROGRESS] Storage progress: {progress:.1f}% ({total_inserted} emails inserted)")
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        storage_logger.info(f"🎯 [PERFORMANCE] OPTIMIZED STORAGE - Storage ID: {storage_id}")
        storage_logger.info(f"   ⏱️ Total time: {total_time:.2f}s")
        storage_logger.info(f"   📊 Total inserted: {total_inserted}/{len(emails)}")
        storage_logger.info(f"   ❌ Failed batches: {failed_batches}")
        storage_logger.info(f"   📈 Success rate: {(total_inserted/len(emails)*100):.1f}%")
        storage_logger.info(f"   🚀 Throughput: {total_inserted/total_time:.1f} emails/second")
        
        storage_logger.info(f"✅ [COMPLETE] OPTIMIZED STORAGE SUCCESS - Storage ID: {storage_id}, Time: {total_time:.2f}s")
        
        return {
            "success": True,
            "inserted": total_inserted,
            "processing_type": processing_type,
            "failed_batches": failed_batches,
            "storage_time": total_time,
            "throughput": total_inserted/total_time
        }
        
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        storage_logger.error(f"❌ [CRITICAL] OPTIMIZED STORAGE FAILED - Storage ID: {storage_id}, Time: {total_time:.2f}s")
        storage_logger.error(f"🔍 [DEBUG] Exception: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processing_type": processing_type,
            "storage_id": storage_id
        }

async def upload_emails_to_mem0_background(user_id: str, emails: List[Dict], processing_type: str, process_id: str = None):
    """
    Background Mem0 upload (time-consuming operation moved to background)
    This runs independently and doesn't block financial data availability
    """
    start_time = datetime.now()
    mem0_id = process_id or f"mem0_{user_id}_{int(start_time.timestamp() * 1000)}"
    
    mem0_logger.info(f"🧠 [START] BACKGROUND MEM0 UPLOAD - Mem0 ID: {mem0_id}")
    mem0_logger.info(f"📊 [INPUT] User: {user_id}, Emails: {len(emails)}, Type: {processing_type}")
    
    try:
        from .mem0_agent_agno import upload_emails_to_mem0, EmailMessage
        
        # Process in very small batches to prevent timeouts
        batch_size = 8  # Small batches for reliable upload
        successful_uploads = 0
        failed_uploads = 0
        conversion_errors = 0
        
        mem0_logger.info(f"⚙️ [CONFIG] Batch size: {batch_size}, Total batches: {(len(emails)-1)//batch_size + 1}")
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_start = datetime.now()
            email_messages = []
            
            mem0_logger.info(f"📦 [BATCH] Processing batch {i//batch_size + 1}/{(len(emails)-1)//batch_size + 1} - Mem0 ID: {mem0_id}")
            
            # Convert emails to EmailMessage format
            for email in batch:
                try:
                    date_value = email.get("date", "")
                    if hasattr(date_value, 'isoformat'):
                        date_str = date_value.isoformat()
                    else:
                        date_str = str(date_value) if date_value else ""
                    
                    email_msg = EmailMessage(
                        id=email.get("id", ""),
                        subject=email.get("subject", ""),
                        sender=email.get("sender", ""),
                        snippet=email.get("snippet", ""),
                        body=email.get("body", ""),
                        date=date_str
                    )
                    email_messages.append(email_msg)
                except Exception as e:
                    conversion_errors += 1
                    mem0_logger.error(f"❌ [CONVERSION] Error converting email {email.get('id', 'unknown')}: {e}")
                    continue
            
            if email_messages:
                try:
                    # Upload batch to Mem0
                    mem0_logger.info(f"⬆️ [UPLOAD] Uploading {len(email_messages)} emails to Mem0 - Batch {i//batch_size + 1}")
                    mem0_result = await upload_emails_to_mem0(user_id, email_messages)
                    
                    batch_time = (datetime.now() - batch_start).total_seconds()
                    
                    if "successful uploads:" in mem0_result.lower():
                        successful_uploads += len(email_messages)
                        mem0_logger.info(f"✅ [UPLOAD] Batch success - Uploaded: {len(email_messages)}, Time: {batch_time:.2f}s")
                    else:
                        failed_uploads += len(email_messages)
                        mem0_logger.error(f"❌ [UPLOAD] Batch failed - Count: {len(email_messages)}, Time: {batch_time:.2f}s")
                        mem0_logger.error(f"🔍 [DEBUG] Mem0 result: {mem0_result}")
                    
                    # Progress logging every 5 batches
                    if i % (batch_size * 5) == 0:
                        progress = ((i + batch_size) / len(emails)) * 100
                        mem0_logger.info(f"📊 [PROGRESS] Mem0 upload: {progress:.1f}% ({successful_uploads} successful, {failed_uploads} failed)")
                
                except Exception as batch_error:
                    batch_time = (datetime.now() - batch_start).total_seconds()
                    failed_uploads += len(email_messages)
                    mem0_logger.error(f"❌ [UPLOAD] Batch exception - Count: {len(email_messages)}, Time: {batch_time:.2f}s, Error: {batch_error}")
            else:
                mem0_logger.warning(f"⚠️ [BATCH] No valid emails after conversion - Batch {i//batch_size + 1}")
            
            # Small delay between batches
            await asyncio.sleep(0.2)
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Update user with Mem0 completion status
        mem0_logger.info(f"💾 [DATABASE] Updating Mem0 status for user: {user_id}")
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "mem0_upload_completed": True,
                "mem0_upload_date": datetime.now().isoformat(),
                "mem0_processing_time": total_time,
                "mem0_successful_uploads": successful_uploads,
                "mem0_failed_uploads": failed_uploads,
                "mem0_conversion_errors": conversion_errors
            }}
        )
        
        mem0_logger.info(f"🎯 [PERFORMANCE] BACKGROUND MEM0 UPLOAD - Mem0 ID: {mem0_id}")
        mem0_logger.info(f"   ⏱️ Total time: {total_time:.2f}s")
        mem0_logger.info(f"   ✅ Successful uploads: {successful_uploads}")
        mem0_logger.info(f"   ❌ Failed uploads: {failed_uploads}")
        mem0_logger.info(f"   🔄 Conversion errors: {conversion_errors}")
        mem0_logger.info(f"   📈 Success rate: {(successful_uploads/(successful_uploads+failed_uploads)*100):.1f}%" if (successful_uploads+failed_uploads) > 0 else "   📈 Success rate: N/A")
        mem0_logger.info(f"   🚀 Throughput: {successful_uploads/total_time:.1f} emails/second")
        
        mem0_logger.info(f"✅ [COMPLETE] BACKGROUND MEM0 UPLOAD SUCCESS - Mem0 ID: {mem0_id}, Time: {total_time:.2f}s")
        
        # Console notification for Mem0 completion
        print(f"\n{'='*60}")
        print(f"🧠 MEM0 UPLOAD COMPLETED for User: {user_id}")
        print(f"📊 Successful uploads: {successful_uploads}")
        print(f"❌ Failed uploads: {failed_uploads}")
        print(f"🔄 Conversion errors: {conversion_errors}")
        print(f"⏱️ Processing time: {total_time:.2f} seconds")
        print(f"✅ Complete AI memory now available!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        mem0_logger.error(f"❌ [CRITICAL] BACKGROUND MEM0 UPLOAD FAILED - Mem0 ID: {mem0_id}, Time: {total_time:.2f}s")
        mem0_logger.error(f"🔍 [DEBUG] Exception: {str(e)}", exc_info=True)
        
        # Update user with failure status
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "mem0_upload_completed": False,
                "mem0_upload_error": str(e),
                "mem0_upload_date": datetime.now().isoformat(),
                "mem0_processing_time": total_time
            }}
        )

# Export optimized functions
__all__ = [
    'process_and_store_emails_optimized',
    'insert_filtered_emails_optimized', 
    'upload_emails_to_mem0_background'
] 