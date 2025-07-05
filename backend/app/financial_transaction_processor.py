#!/usr/bin/env python3

"""
Centralized Financial Transaction Processor
===========================================

This module ensures financial transactions are extracted from MongoDB emails
and stored in the financial_transactions collection BEFORE Mem0 upload.

This is called by all email processing pipelines to maintain consistency.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from .fast_financial_processor import process_financial_transactions_from_mongodb
from .db import db_manager

# Configure logging
logger = logging.getLogger(__name__)

class CentralizedFinancialProcessor:
    """
    Centralized processor to extract financial transactions from stored emails
    """
    
    def __init__(self):
        self.stats = {
            "total_processed_users": 0,
            "total_transactions_extracted": 0,
            "total_processing_time": 0,
            "errors": 0
        }
    
    async def process_user_financial_transactions(
        self, 
        user_id: str, 
        processing_context: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Process financial transactions for a user from their stored MongoDB emails
        
        This function:
        1. Extracts financial emails from the emails collection
        2. Processes them into structured transactions
        3. Stores them in the financial_transactions collection
        4. Returns comprehensive results
        
        Args:
            user_id: The user's ID
            processing_context: Context of where this is called from
            
        Returns:
            Dictionary with processing results
        """
        
        start_time = datetime.now()
        context_id = f"fin_{user_id}_{int(start_time.timestamp() * 1000)}"
        
        logger.info(f"💰 [START] FINANCIAL PROCESSING - Context: {processing_context.upper()}")
        logger.info(f"📊 [INPUT] User: {user_id}, Context ID: {context_id}")
        
        try:
            # Step 1: Process financial transactions from MongoDB
            logger.info(f"🔍 [STEP 1] Extracting financial transactions from MongoDB emails")
            
            financial_result = await process_financial_transactions_from_mongodb(user_id)
            
            if financial_result["status"] != "success":
                logger.error(f"❌ [STEP 1] Financial extraction failed: {financial_result}")
                return {
                    "success": False,
                    "error": f"Financial extraction failed: {financial_result}",
                    "context": processing_context,
                    "context_id": context_id
                }
            
            transactions_found = financial_result.get("transactions_found", 0)
            total_amount = financial_result.get("total_amount", 0)
            
            # Step 2: Update user metadata
            logger.info(f"🔄 [STEP 2] Updating user financial metadata")
            
            try:
                users_coll = await db_manager.get_collection(user_id, "users")
                update_result = await users_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "financial_transactions_count": transactions_found,
                        "financial_total_amount": total_amount,
                        "financial_last_processed": datetime.now().isoformat(),
                        "financial_processing_context": processing_context,
                        "financial_ready_for_mem0": True  # Key flag for Mem0 upload
                    }}
                )
                
                if update_result.modified_count > 0:
                    logger.info(f"✅ [STEP 2] User metadata updated successfully")
                else:
                    logger.warning(f"⚠️ [STEP 2] User metadata update had no effect")
            
            except Exception as metadata_error:
                logger.error(f"❌ [STEP 2] Failed to update user metadata: {metadata_error}")
                # Don't fail the whole process for metadata update failure
            
            # Step 3: Calculate and log results
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.stats["total_processed_users"] += 1
            self.stats["total_transactions_extracted"] += transactions_found
            self.stats["total_processing_time"] += processing_time
            
            logger.info(f"✅ [COMPLETE] Financial processing successful - Context ID: {context_id}")
            logger.info(f"📊 [RESULTS] Transactions: {transactions_found}, Amount: ₹{total_amount:,.2f}, Time: {processing_time:.2f}s")
            
            # Console notification for visibility
            if transactions_found > 0:
                print(f"\n{'='*80}")
                print(f"💰 FINANCIAL TRANSACTIONS EXTRACTED")
                print(f"👤 User: {user_id}")
                print(f"📊 Transactions: {transactions_found}")
                print(f"💵 Total Amount: ₹{total_amount:,.2f}")
                print(f"⏱️ Processing Time: {processing_time:.2f}s")
                print(f"📝 Context: {processing_context}")
                print(f"✅ Ready for Mem0 upload")
                print(f"{'='*80}\n")
            
            return {
                "success": True,
                "transactions_found": transactions_found,
                "total_amount": total_amount,
                "processing_time": processing_time,
                "context": processing_context,
                "context_id": context_id,
                "ready_for_mem0": True,
                "message": f"Successfully extracted {transactions_found} financial transactions"
            }
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["errors"] += 1
            
            logger.error(f"❌ [ERROR] Financial processing failed - Context ID: {context_id}")
            logger.error(f"❌ [ERROR] Error: {str(e)}")
            logger.error(f"❌ [ERROR] Processing time: {processing_time:.2f}s")
            
            import traceback
            logger.error(f"❌ [TRACEBACK] {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "context": processing_context,
                "context_id": context_id,
                "ready_for_mem0": False,
                "transactions_found": 0,
                "total_amount": 0
            }
    
    async def ensure_financial_processing_before_mem0(
        self, 
        user_id: str, 
        processing_context: str = "before_mem0"
    ) -> bool:
        """
        Ensure financial processing is complete before Mem0 upload
        
        Returns:
            bool: True if financial processing is complete and ready for Mem0
        """
        
        logger.info(f"🔍 [PRE-MEM0] Checking financial processing status for user {user_id}")
        
        try:
            # Check if user already has financial processing completed
            users_coll = await db_manager.get_collection(user_id, "users")
            user_data = await users_coll.find_one({"user_id": user_id})
            
            if user_data and user_data.get("financial_ready_for_mem0"):
                transactions_count = user_data.get("financial_transactions_count", 0)
                logger.info(f"✅ [PRE-MEM0] Financial processing already complete: {transactions_count} transactions")
                return True
            
            # Financial processing not complete - run it now
            logger.info(f"🔄 [PRE-MEM0] Running financial processing before Mem0 upload")
            
            result = await self.process_user_financial_transactions(user_id, processing_context)
            
            if result["success"]:
                logger.info(f"✅ [PRE-MEM0] Financial processing completed: {result['transactions_found']} transactions")
                return True
            else:
                logger.error(f"❌ [PRE-MEM0] Financial processing failed: {result['error']}")
                return False
        
        except Exception as e:
            logger.error(f"❌ [PRE-MEM0] Error ensuring financial processing: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        if self.stats["total_processed_users"] > 0:
            avg_processing_time = self.stats["total_processing_time"] / self.stats["total_processed_users"]
            avg_transactions_per_user = self.stats["total_transactions_extracted"] / self.stats["total_processed_users"]
        else:
            avg_processing_time = 0
            avg_transactions_per_user = 0
        
        return {
            **self.stats,
            "avg_processing_time_per_user": round(avg_processing_time, 2),
            "avg_transactions_per_user": round(avg_transactions_per_user, 1),
            "success_rate": round((1 - self.stats["errors"] / max(self.stats["total_processed_users"], 1)) * 100, 1)
        }

# Global instance
financial_processor = CentralizedFinancialProcessor()

# Convenience functions for easy import
async def process_financial_before_mem0(user_id: str, context: str = "pipeline") -> Dict[str, Any]:
    """
    Process financial transactions before Mem0 upload
    
    This should be called by all email processing pipelines after MongoDB storage
    but before Mem0 upload.
    """
    return await financial_processor.process_user_financial_transactions(user_id, context)

async def ensure_financial_ready_for_mem0(user_id: str, context: str = "pre_mem0") -> bool:
    """
    Ensure financial processing is complete before Mem0 upload
    
    Returns True if ready for Mem0, False otherwise
    """
    return await financial_processor.ensure_financial_processing_before_mem0(user_id, context) 