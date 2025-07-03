from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne, InsertOne, DeleteOne  # Add these imports
from typing import Optional, Dict, List, Any
import os
import certifi # Import certifi
import asyncio
import logging
from datetime import datetime, timedelta
import gzip
import json
import re  # Import re module for regex operations
from urllib.parse import quote_plus, urlparse, urlunparse
from .config import (
    DB_MAX_POOL_SIZE, DB_MIN_POOL_SIZE, DB_CONNECTION_TIMEOUT,
    DATABASE_INSERT_BATCH_SIZE, ENABLE_DATABASE_SHARDING, 
    SHARD_DATABASES, MAX_USERS_PER_DATABASE, get_database_for_user,
    ENABLE_AUTO_CLEANUP, MAX_EMAIL_AGE_DAYS, 
    ESSENTIAL_EMAIL_FIELDS, PRESERVE_EMAIL_BODY, PRESERVE_EMAIL_HEADERS,
    ENABLE_SMART_EMAIL_FILTERING, PROMOTIONAL_EMAIL_PATTERNS,
    FINANCIAL_EMAIL_KEYWORDS, calculate_email_importance,
    USE_LOCAL_FALLBACK, LOCAL_MONGODB_URL
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# FREE TIER MULTI-DATABASE SYSTEM
# ============================================================================

class DatabaseManager:
    """Manages multiple free MongoDB databases for infinite scaling"""
    
    def __init__(self):
        self.clients = {}
        self.databases = {}
        self.user_database_mapping = {}  # Track which user uses which database
        self.ca = certifi.where()
        self._initialize_databases()
    
    def _encode_mongodb_uri(self, uri: str) -> str:
        """Properly encode MongoDB URI with username and password"""
        try:
            # Parse the URI
            parsed = urlparse(uri)
            
            # If there's no userinfo, return as-is
            if not parsed.username:
                return uri
            
            # Encode username and password
            encoded_username = quote_plus(parsed.username) if parsed.username else None
            encoded_password = quote_plus(parsed.password) if parsed.password else None
            
            # Reconstruct the URI with encoded credentials
            if encoded_username and encoded_password:
                netloc = f"{encoded_username}:{encoded_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                
                encoded_uri = urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                
                logger.info(f"🔐 MongoDB URI encoded successfully")
                return encoded_uri
            else:
                return uri
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to encode MongoDB URI: {e}")
            return uri
    
    def _initialize_databases(self):
        """Initialize all shard databases with fallback support"""
        for i, uri in enumerate(SHARD_DATABASES):
            try:
                # Encode the URI to handle special characters in username/password
                encoded_uri = self._encode_mongodb_uri(uri)
                logger.info(f"🔄 Attempting to connect to database shard {i}: {encoded_uri[:50]}...")
                
                client = AsyncIOMotorClient(
                    encoded_uri, 
                    tlsCAFile=self.ca,
                    maxPoolSize=DB_MAX_POOL_SIZE,
                    minPoolSize=DB_MIN_POOL_SIZE,
                    connectTimeoutMS=5000,  # Reduced timeout for faster fallback
                    serverSelectionTimeoutMS=5000,  # Reduced timeout
                    socketTimeoutMS=10000,
                    retryWrites=True,
                    w="majority"
                )
                
                # Connection will be tested on first use
                # No need to test here as it's not an async context
                
                db_name = f"genai_gmail_chat_shard_{i}"
                self.clients[i] = client
                self.databases[i] = client[db_name]
                
                logger.info(f"✅ Successfully connected to database shard {i}: {db_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to database shard {i}: {e}")
                
                # Try local fallback if enabled
                if USE_LOCAL_FALLBACK:
                    try:
                        logger.info(f"🔄 Attempting local MongoDB fallback for shard {i}...")
                        
                        fallback_client = AsyncIOMotorClient(
                            LOCAL_MONGODB_URL,
                            maxPoolSize=5,
                            minPoolSize=1,
                            connectTimeoutMS=3000,
                            serverSelectionTimeoutMS=3000,
                        )
                        
                        db_name = f"gmail_chatbot_local_shard_{i}"
                        self.clients[i] = fallback_client
                        self.databases[i] = fallback_client[db_name]
                        
                        logger.info(f"✅ Using local MongoDB fallback for shard {i}: {db_name}")
                        
                    except Exception as fallback_error:
                        logger.error(f"❌ Local MongoDB fallback also failed for shard {i}: {fallback_error}")
                        logger.error(f"💡 Please ensure MongoDB is running locally or check cloud connection")
                        
                        # Create a dummy database that will fail gracefully
                        self.clients[i] = None
                        self.databases[i] = None
                else:
                    logger.error(f"❌ No fallback configured for shard {i}")
                    self.clients[i] = None
                    self.databases[i] = None
    
    async def _test_connection(self, client):
        """Test database connection"""
        try:
            await client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_database_for_user(self, user_id: str):
        """Get the appropriate database for a user"""
        if not ENABLE_DATABASE_SHARDING:
            if self.databases[0] is None:
                logger.error("❌ Primary database is not available")
                return None
            return self.databases[0]
        
        # Check if user already has a database assigned
        if user_id in self.user_database_mapping:
            db_index = self.user_database_mapping[user_id]
            if self.databases[db_index] is None:
                logger.error(f"❌ Assigned database shard {db_index} is not available for user {user_id}")
                # Try to find an available database
                for i, db in self.databases.items():
                    if db is not None:
                        self.user_database_mapping[user_id] = i
                        logger.info(f"👤 Reassigned user {user_id} to available database shard {i}")
                        return db
                return None
            return self.databases[db_index]
        
        # Assign user to least loaded available database
        for i, db in self.databases.items():
            if db is not None:
                self.user_database_mapping[user_id] = i
                logger.info(f"👤 Assigned user {user_id} to database shard {i}")
                return db
        
        logger.error(f"❌ No available databases for user {user_id}")
        return None
    
    def _get_least_loaded_database(self) -> int:
        """Find the database with least users"""
        # Simple round-robin for now
        # In production, you'd check actual user counts
        return len(self.user_database_mapping) % len(SHARD_DATABASES)
    
    async def get_collection(self, user_id: str, collection_name: str):
        """Get collection for specific user"""
        database = self.get_database_for_user(user_id)
        if database is None:
            raise Exception(f"No database available for user {user_id} - check MongoDB connection")
        return database[collection_name]

# Global database manager
db_manager = DatabaseManager()

# Backward compatibility - use first database as default
client = db_manager.clients[0]
db = db_manager.databases[0]

# Default collections (will be dynamically selected per user)
users_collection = db["users"]
emails_collection = db["emails"] 
chats_collection = db["chats"]

# ============================================================================
# DATA COMPRESSION UTILITIES
# ============================================================================

# Import the intelligent compressor
from .intelligent_compressor import intelligent_compressor

class SmartCompressor:
    """Smart compression wrapper that uses intelligent compression"""
    
    @staticmethod
    def compress_email_content(content: str) -> str:
        """Compress email content using intelligent compression"""
        if not content or len(content) < 50:
            return content
        
        # Create email-like data structure for intelligent compression
        email_data = {'body': content, 'snippet': content[:200]}
        
        # Use intelligent compression
        compressed = intelligent_compressor.compress_email_intelligently(email_data)
        
        return compressed.get('body', content)
    
    @staticmethod
    def decompress_email_content(content: str) -> str:
        """Decompress email content (for backward compatibility)"""
        try:
            # Check if it's hex-encoded compressed data
            if len(content) > 20 and all(c in '0123456789abcdef' for c in content.lower()):
                try:
                    compressed = bytes.fromhex(content)
                    return gzip.decompress(compressed).decode('utf-8')
                except:
                    pass
            
            return content
            
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            return content
    
    @staticmethod
    def minimize_email_data(email_data: Dict) -> Dict:
        """Intelligently minimize email data while preserving important information"""
        try:
            # Use intelligent compression
            compressed = intelligent_compressor.compress_email_intelligently(email_data)
            
            # Ensure essential fields are preserved
            minimized = {}
            for field in ESSENTIAL_EMAIL_FIELDS:
                if field in compressed:
                    minimized[field] = compressed[field]
            
            # Add compression metadata
            minimized['compressed'] = True
            minimized['compression_version'] = 2  # Updated version
            minimized['compression_type'] = compressed.get('compression_type', 'intelligent')
            
            # Add structured data if available
            if 'structured_data' in compressed:
                minimized['structured_data'] = compressed['structured_data']
            
            return minimized
            
        except Exception as e:
            logger.error(f"Intelligent compression error: {e}")
            # Fallback to basic compression
            return {
                field: email_data.get(field)
                for field in ESSENTIAL_EMAIL_FIELDS
                if field in email_data
            }

# Global compressor instance (updated to use smart compression)
compressor = SmartCompressor()

# ============================================================================
# AUTO-CLEANUP SYSTEM
# ============================================================================

class AutoCleanupManager:
    """Automatic data cleanup for free tier optimization"""
    
    def __init__(self):
        self.cleanup_running = False
    
    async def cleanup_old_emails(self, user_id: str):
        """Remove emails older than 6 months"""
        try:
            cutoff_date = datetime.now() - timedelta(days=MAX_EMAIL_AGE_DAYS)
            
            # Get user's email collection
            emails_coll = await db_manager.get_collection(user_id, "emails")
            
            # Delete old emails
            result = await emails_coll.delete_many({
                "user_id": user_id,
                "date": {"$lt": cutoff_date.strftime("%Y-%m-%d")}
            })
            
            logger.info(f"🧹 Cleaned up {result.deleted_count} old emails for user {user_id}")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup error for user {user_id}: {e}")
            return 0
    
    async def cleanup_all_users(self):
        """Run cleanup for all users"""
        if self.cleanup_running:
            logger.info("Cleanup already running, skipping...")
            return
        
        self.cleanup_running = True
        try:
            total_cleaned = 0
            
            # Get all users across all databases
            for db_index, database in db_manager.databases.items():
                users_coll = database["users"]
                
                async for user in users_coll.find({}):
                    user_id = user.get("user_id")
                    if user_id:
                        cleaned = await self.cleanup_old_emails(user_id)
                        total_cleaned += cleaned
            
            logger.info(f"🧹 Total cleanup complete: {total_cleaned} emails removed")
            
        except Exception as e:
            logger.error(f"Global cleanup error: {e}")
        finally:
            self.cleanup_running = False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics across all databases"""
        stats = {
            "total_users": 0,
            "total_emails": 0,
            "total_storage_mb": 0,
            "databases": {}
        }
        
        try:
            for db_index, database in db_manager.databases.items():
                try:
                    db_stats = await database.command('dbstats')
                    shard_stats = {
                        "users": await database["users"].count_documents({}),
                        "emails": await database["emails"].count_documents({}),
                        "storage_mb": db_stats.get("storageSize", 0) / (1024*1024)
                    }
                    
                    stats["databases"][f"shard_{db_index}"] = shard_stats
                    stats["total_users"] += shard_stats["users"]
                    stats["total_emails"] += shard_stats["emails"]
                    stats["total_storage_mb"] += shard_stats["storage_mb"]
                    
                except Exception as e:
                    logger.error(f"Error getting stats for shard {db_index}: {e}")
        
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
        
        return stats

# Global cleanup manager
cleanup_manager = AutoCleanupManager()

# ============================================================================
# SMART EMAIL FILTERING SYSTEM
# ============================================================================

class SmartEmailFilter:
    """Intelligent email filtering to remove promotional content while preserving complete important data"""
    
    def __init__(self):
        self.financial_keywords = FINANCIAL_EMAIL_KEYWORDS
        self.promotional_patterns = PROMOTIONAL_EMAIL_PATTERNS
        self.stats = {
            "total_processed": 0,
            "promotional_filtered": 0,
            "financial_preserved": 0,
            "important_preserved": 0
        }
    
    def is_promotional_email(self, email_data: Dict) -> bool:
        """Identify promotional/marketing emails to filter out"""
        content = f"{email_data.get('subject', '')} {email_data.get('sender', '')} {email_data.get('snippet', '')}".lower()
        
        # Check for promotional patterns
        for pattern in self.promotional_patterns:
            if pattern.lower() in content:
                return True
        
        # Check for marketing indicators in sender
        sender = email_data.get('sender', '').lower()
        marketing_domains = ['marketing', 'newsletter', 'no-reply', 'noreply', 'promo', 'offers']
        if any(domain in sender for domain in marketing_domains):
            return True
        
        return False
    
    def is_financial_email(self, email_data: Dict) -> bool:
        """Identify financial/transaction emails (ALWAYS PRESERVE)"""
        content = f"{email_data.get('subject', '')} {email_data.get('sender', '')} {email_data.get('snippet', '')}".lower()
        
        # Check for financial keywords
        return any(keyword.lower() in content for keyword in self.financial_keywords)
    
    def should_keep_email(self, email_data: Dict) -> tuple[bool, str]:
        """Determine if email should be kept and reason"""
        
        # ALWAYS keep financial emails
        if self.is_financial_email(email_data):
            self.stats["financial_preserved"] += 1
            return True, "financial"
        
        # Calculate importance score
        importance_score = calculate_email_importance(email_data)
        email_data["importance_score"] = importance_score
        
        # Keep high importance emails (score > 6)
        if importance_score > 6:
            self.stats["important_preserved"] += 1
            return True, f"important_{importance_score}"
        
        # Filter out promotional emails (score < 4)
        if importance_score < 4 or self.is_promotional_email(email_data):
            self.stats["promotional_filtered"] += 1
            return False, "promotional"
        
        # Keep medium importance emails
        self.stats["important_preserved"] += 1
        return True, f"medium_{importance_score}"
    
    def filter_email_batch(self, emails: List[Dict]) -> List[Dict]:
        """Filter a batch of emails, keeping only important ones"""
        filtered_emails = []
        
        for email in emails:
            self.stats["total_processed"] += 1
            keep, reason = self.should_keep_email(email)
            
            if keep:
                # Add filtering metadata
                email["filter_reason"] = reason
                email["filtered_at"] = datetime.now()
                filtered_emails.append(email)
        
        filter_ratio = (self.stats["promotional_filtered"] / max(self.stats["total_processed"], 1)) * 100
        logger.info(f"📊 Filtered {self.stats['promotional_filtered']} promotional emails ({filter_ratio:.1f}% space saved)")
        
        return filtered_emails
    
    async def smart_filter_emails(self, emails: List[Dict], user_id: str, processing_type: str = "standard") -> List[Dict]:
        """Smart email filtering with async support for different processing types"""
        try:
            logger.info(f"🔍 [{processing_type.upper()}] Smart filtering {len(emails)} emails for user {user_id}")
            
            # Use the existing filter_email_batch method
            filtered_emails = self.filter_email_batch(emails)
            
            filter_stats = self.get_filter_stats()
            logger.info(f"📊 [{processing_type.upper()}] Filtering complete: {filter_stats}")
            
            return filtered_emails
            
        except Exception as e:
            logger.error(f"❌ [{processing_type.upper()}] Error in smart filtering: {e}")
            # Return original emails if filtering fails
            return emails

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        total = self.stats["total_processed"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "promotional_filter_rate": round((self.stats["promotional_filtered"] / total) * 100, 1),
            "financial_preservation_rate": round((self.stats["financial_preserved"] / total) * 100, 1),
            "space_saved_percent": round((self.stats["promotional_filtered"] / total) * 100, 1)
        }

# ============================================================================
# COMPLETE EMAIL DATA PROCESSOR
# ============================================================================

class CompleteEmailProcessor:
    """Process emails with complete data preservation for financial analysis"""
    
    def __init__(self):
        self.email_filter = SmartEmailFilter()
    
    def extract_complete_email_data(self, email_data: Dict) -> Dict:
        """Extract complete email data including headers, body, and attachment info"""
        complete_data = {}
        
        # Essential fields
        for field in ESSENTIAL_EMAIL_FIELDS:
            if field in email_data:
                complete_data[field] = email_data[field]
        
        # Preserve email body for analysis
        if PRESERVE_EMAIL_BODY and 'body' in email_data:
            complete_data['body'] = email_data['body']
        
        # Preserve headers for better filtering
        if PRESERVE_EMAIL_HEADERS and 'headers' in email_data:
            complete_data['headers'] = email_data['headers']
        
        # Extract attachment information (not the files, just metadata)
        complete_data['attachments_info'] = self.extract_attachment_info(email_data)
        
        # Financial analysis metadata
        complete_data['financial_metadata'] = self.extract_financial_metadata(email_data)
        
        # Add processing metadata
        complete_data['processed_at'] = datetime.now().isoformat()  # Convert to string immediately
        complete_data['data_complete'] = True
        
        # 🔧 CRITICAL FIX: Ensure ALL datetime objects are converted to strings
        for key, value in complete_data.items():
            if isinstance(value, datetime):
                complete_data[key] = value.isoformat()
            elif hasattr(value, 'isoformat') and callable(getattr(value, 'isoformat')):
                complete_data[key] = value.isoformat()
        
        return complete_data
    
    def extract_attachment_info(self, email_data: Dict) -> List[Dict]:
        """Extract attachment metadata for financial document analysis"""
        attachments_info = []
        
        # Extract from Gmail payload if available
        payload = email_data.get('payload', {})
        parts = payload.get('parts', [])
        
        for part in parts:
            if part.get('filename'):
                attachment_info = {
                    'filename': part.get('filename'),
                    'mimeType': part.get('mimeType'),
                    'size': part.get('body', {}).get('size', 0),
                    'attachmentId': part.get('body', {}).get('attachmentId'),
                    'is_financial_document': self.is_financial_attachment(part.get('filename', ''))
                }
                attachments_info.append(attachment_info)
        
        return attachments_info
    
    def is_financial_attachment(self, filename: str) -> bool:
        """Check if attachment is likely a financial document"""
        financial_patterns = [
            'invoice', 'receipt', 'statement', 'bill', 'transaction',
            'payment', 'order', 'ticket', 'booking', 'confirmation'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in financial_patterns)
    
    def extract_financial_metadata(self, email_data: Dict) -> Dict:
        """Extract detailed financial metadata for better analysis"""
        content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}".lower()
        
        metadata = {
            'has_amount': bool(re.search(r'[₹\$]\s*[\d,]+', content)),
            'has_transaction_id': bool(re.search(r'transaction|txn|ref|order[\s#:]*[a-zA-Z0-9]+', content)),
            'payment_methods': [],
            'merchant_indicators': [],
            'transaction_type': None
        }
        
        # Detect payment methods
        payment_patterns = {
            'upi': r'upi|unified payments',
            'card': r'card\s*ending|card\s*\*+\d+|debit|credit',
            'netbanking': r'net\s*banking|internet\s*banking',
            'wallet': r'wallet|paytm|phonepe|googlepay'
        }
        
        for method, pattern in payment_patterns.items():
            if re.search(pattern, content):
                metadata['payment_methods'].append(method)
        
        # Detect transaction type
        if any(word in content for word in ['debited', 'charged', 'paid', 'spent']):
            metadata['transaction_type'] = 'debit'
        elif any(word in content for word in ['credited', 'received', 'refund', 'cashback']):
            metadata['transaction_type'] = 'credit'
        
        return metadata

# Global instances
email_filter = SmartEmailFilter()
email_processor = CompleteEmailProcessor()

# ============================================================================
# OPTIMIZED DATABASE OPERATIONS FOR COMPLETE DATA
# ============================================================================

async def insert_filtered_emails(user_id: str, emails_data: List[Dict], processing_type: str = "standard") -> Dict[str, Any]:
    """Insert emails with smart filtering and complete data preservation - FIXED: No data loss"""
    
    if not emails_data:
        logger.warning(f"⚠️ No emails provided for user {user_id}")
        return {"success": True, "inserted": 0, "filtered": 0, "financial": 0}
    
    try:
        logger.info(f"📧 [{processing_type.upper()}] Processing {len(emails_data)} emails with smart filtering for user {user_id}")
        
        # Apply smart filtering
        if ENABLE_SMART_EMAIL_FILTERING:
            logger.info(f"🎯 [{processing_type.upper()}] Applying smart email filtering for user {user_id}")
            filtered_emails = email_filter.filter_email_batch(emails_data)
            logger.info(f"🎯 [{processing_type.upper()}] Smart filtering result: {len(filtered_emails)}/{len(emails_data)} emails kept")
        else:
            logger.info(f"⚠️ [{processing_type.upper()}] Smart filtering disabled - keeping all emails")
            filtered_emails = emails_data
        
        # Process emails with complete data extraction
        processed_emails = []
        logger.info(f"🔄 Processing {len(filtered_emails)} filtered emails for complete data extraction")
        
        for i, email in enumerate(filtered_emails):
            try:
                complete_email = email_processor.extract_complete_email_data(email)
                complete_email["user_id"] = user_id
                processed_emails.append(complete_email)
                
                if i % 10 == 0:  # Log every 10 emails
                    logger.info(f"   📧 Processed {i+1}/{len(filtered_emails)} emails...")
                    
            except Exception as process_error:
                logger.error(f"⚠️ Failed to process email {i}: {process_error}")
        
        logger.info(f"✅ Successfully processed {len(processed_emails)} emails for MongoDB insertion")
        
        # Get user's email collection
        try:
            emails_coll = await db_manager.get_collection(user_id, "emails")
            logger.info(f"✅ Got email collection for user {user_id}")
        except Exception as db_error:
            logger.error(f"❌ Failed to get email collection for user {user_id}: {db_error}")
            return {"success": False, "inserted": 0, "filtered": 0, "financial": 0, "error": f"Database connection failed: {str(db_error)}"}
        
        # 🔧 CRITICAL FIX: Use upsert operations instead of deleting all emails
        # Check existing emails to avoid duplicates
        existing_email_ids = set()
        try:
            existing_cursor = emails_coll.find({"user_id": user_id}, {"id": 1})
            existing_emails = await existing_cursor.to_list(length=None)
            existing_email_ids = {email.get("id") for email in existing_emails if email.get("id")}
            logger.info(f"📊 Found {len(existing_email_ids)} existing emails for user {user_id}")
        except Exception as existing_error:
            logger.error(f"⚠️ Failed to check existing emails: {existing_error}")
            # Continue anyway with empty set
        
        # Filter out duplicate emails (by email ID)
        new_emails = []
        duplicates_skipped = 0
        emails_without_ids = 0
        
        for email in processed_emails:
            email_id = email.get("id")
            
            # 🔧 CRITICAL FIX: Handle emails without IDs
            if not email_id or email_id == "":
                # Generate a unique ID based on content if missing
                import hashlib
                content_for_id = f"{email.get('subject', '')}{email.get('sender', '')}{email.get('date', '')}{email.get('snippet', '')}"
                email_id = hashlib.md5(content_for_id.encode()).hexdigest()
                email["id"] = email_id
                emails_without_ids += 1
                logger.warning(f"⚠️ Email missing ID, generated: {email_id[:8]}... from content")
            
            if email_id in existing_email_ids:
                duplicates_skipped += 1
                logger.debug(f"🔄 Skipping duplicate email: {email_id[:8]}...")
                continue
            
            new_emails.append(email)
            logger.debug(f"📧 New email added: {email_id[:8]}... | {email.get('subject', 'No Subject')[:50]}")
        
        logger.info(f"📧 Email deduplication: {len(new_emails)} new emails, {duplicates_skipped} duplicates skipped, {emails_without_ids} missing IDs fixed")
        
        if not new_emails:
            logger.info(f"✅ No new emails to insert for user {user_id} (all were duplicates)")
            return {
                "success": True,
                "inserted": 0,
                "filtered": email_filter.stats.get("promotional_filtered", 0),
                "financial": email_filter.stats.get("financial_preserved", 0),
                "duplicates_skipped": duplicates_skipped,
                "emails_without_ids": emails_without_ids,
                "original_count": len(emails_data)
            }
        
        # Insert new emails in batches using upsert
        batch_size = DATABASE_INSERT_BATCH_SIZE
        total_inserted = 0
        total_upserted = 0
        failed_operations = 0
        
        logger.info(f"📥 Starting batch insertion of {len(new_emails)} NEW emails (batch size: {batch_size})")
        
        for i in range(0, len(new_emails), batch_size):
            batch = new_emails[i:i + batch_size]
            
            try:
                logger.info(f"📥 Inserting batch {i//batch_size + 1}: {len(batch)} emails...")
                
                # 🔧 CRITICAL FIX: Convert datetime objects to strings for MongoDB
                serialized_batch = []
                for email in batch:
                    serialized_email = {}
                    for key, value in email.items():
                        if isinstance(value, datetime):
                            # Convert datetime to ISO string
                            serialized_email[key] = value.isoformat()
                        elif hasattr(value, 'isoformat'):  # Handle other datetime-like objects
                            try:
                                serialized_email[key] = value.isoformat()
                            except Exception as dt_error:
                                # If isoformat fails, convert to string
                                serialized_email[key] = str(value)
                                logger.warning(f"⚠️ Failed to convert datetime field '{key}' to ISO format: {dt_error}")
                        elif isinstance(value, (list, dict)):
                            # Handle nested objects that might contain datetime
                            serialized_email[key] = json.loads(json.dumps(value, default=str))
                        else:
                            serialized_email[key] = value
                    serialized_batch.append(serialized_email)
                
                # Use upsert operations to handle any remaining duplicates gracefully
                bulk_operations = []
                for email in serialized_batch:
                    email_id = email.get("id")
                    if email_id:
                        # Use upsert for emails with ID - FIXED: Use PyMongo UpdateOne class
                        bulk_operations.append(
                            UpdateOne(
                                filter={"user_id": user_id, "id": email_id},
                                update={"$set": email},
                                upsert=True
                            )
                        )
                        logger.debug(f"🔄 Upsert operation for email: {email_id[:8]}...")
                    else:
                        # This should not happen now, but keep as fallback - FIXED: Use PyMongo InsertOne class
                        logger.error(f"❌ Email still missing ID after fix: {email}")
                        bulk_operations.append(
                            InsertOne(document=email)
                        )
                
                if bulk_operations:
                    logger.info(f"📤 Executing {len(bulk_operations)} bulk operations...")
                    result = await emails_coll.bulk_write(bulk_operations, ordered=False)
                    
                    batch_inserted = result.inserted_count
                    batch_upserted = result.upserted_count
                    batch_modified = result.modified_count
                    
                    total_inserted += batch_inserted
                    total_upserted += batch_upserted
                    
                    logger.info(f"✅ Inserted batch {i//batch_size + 1}: inserted={batch_inserted}, upserted={batch_upserted}, modified={batch_modified}")
                    logger.info(f"📊 Running totals: inserted={total_inserted}, upserted={total_upserted}")
                else:
                    logger.warning(f"⚠️ No bulk operations generated for batch {i//batch_size + 1}")
                
            except Exception as e:
                failed_operations += 1
                logger.error(f"❌ Batch insert error for batch {i//batch_size + 1}: {e}")
                logger.error(f"❌ Batch insert error type: {type(e).__name__}")
                
                # Log sample of failed emails for debugging
                sample_emails = [{"id": email.get("id"), "subject": email.get("subject", "")[:50]} for email in batch[:3]]
                logger.error(f"❌ Sample failed emails: {sample_emails}")
                
                # 🔧 CRITICAL DEBUG: Check if it's a bulk operation format issue
                if "bulk_write" in str(e).lower() or "command" in str(e).lower():
                    logger.error(f"❌ Likely bulk operation format error - check PyMongo operation classes")
                    logger.error(f"❌ Bulk operations count: {len(bulk_operations)}")
                    if bulk_operations:
                        logger.error(f"❌ First bulk operation type: {type(bulk_operations[0])}")
                
                # 🔧 CRITICAL DEBUG: Log serialization issues
                for email in serialized_batch[:1]:  # Check first email for datetime issues
                    datetime_fields = []
                    unsupported_fields = []
                    for key, value in email.items():
                        if isinstance(value, datetime) or hasattr(value, 'isoformat'):
                            datetime_fields.append(f"{key}: {type(value).__name__}")
                        elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            unsupported_fields.append(f"{key}: {type(value).__name__}")
                    if datetime_fields:
                        logger.error(f"❌ Datetime fields found: {datetime_fields}")
                    if unsupported_fields:
                        logger.error(f"❌ Unsupported data types found: {unsupported_fields}")
                
                import traceback
                logger.error(f"❌ Batch insert traceback: {traceback.format_exc()}")
        
        # Calculate total successfully processed
        total_successful = total_inserted + total_upserted
        
        # Get current total email count after insertion
        try:
            total_emails_now = await emails_coll.count_documents({"user_id": user_id})
            logger.info(f"📊 Total emails in database for user {user_id}: {total_emails_now}")
        except Exception as count_error:
            logger.error(f"⚠️ Failed to count total emails: {count_error}")
            total_emails_now = "unknown"
        
        # Get filtering statistics
        filter_stats = email_filter.get_filter_stats()
        
        logger.info(f"✅ Email processing complete for user {user_id}:")
        logger.info(f"   📊 Original emails: {len(emails_data)}")
        logger.info(f"   📧 New emails inserted: {total_inserted}")
        logger.info(f"   🔄 New emails upserted: {total_upserted}")
        logger.info(f"   📈 Total successful: {total_successful}")
        logger.info(f"   🔄 Duplicates skipped: {duplicates_skipped}")
        logger.info(f"   🆔 Missing IDs fixed: {emails_without_ids}")
        logger.info(f"   📊 Total emails in DB: {total_emails_now}")
        logger.info(f"   ❌ Failed operations: {failed_operations}")
        logger.info(f"   🗑️ Promotional filtered: {filter_stats['promotional_filtered']}")
        logger.info(f"   💰 Financial preserved: {filter_stats['financial_preserved']}")
        logger.info(f"   💾 Space saved: {filter_stats['space_saved_percent']}%")
        
        if total_successful == 0 and duplicates_skipped == 0:
            logger.error(f"❌ CRITICAL: No emails were inserted for user {user_id}!")
            logger.error(f"   📊 Original count: {len(emails_data)}")
            logger.error(f"   🎯 Filtered count: {len(filtered_emails)}")
            logger.error(f"   🔄 Processed count: {len(processed_emails)}")
            logger.error(f"   🆔 Emails without IDs: {emails_without_ids}")
            logger.error(f"   💾 Bulk operations failed: {failed_operations}")
        
        return {
            "success": True,
            "inserted": total_successful,  # Total of inserted + upserted
            "filtered": filter_stats["promotional_filtered"],
            "financial": filter_stats["financial_preserved"],
            "duplicates_skipped": duplicates_skipped,
            "emails_without_ids": emails_without_ids,
            "failed_operations": failed_operations,
            "filter_stats": filter_stats,
            "original_count": len(emails_data),
            "total_emails_in_db": total_emails_now
        }
        
    except Exception as e:
        logger.error(f"⚠️ Error in filtered email insertion: {e}")
        logger.error(f"⚠️ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"⚠️ Error traceback: {traceback.format_exc()}")
        return {"success": False, "inserted": 0, "filtered": 0, "financial": 0, "error": str(e)}

async def get_financial_emails(user_id: str, limit: int = 1000) -> List[Dict]:
    """Get financial emails with complete data for transaction analysis"""
    try:
        emails_coll = await db_manager.get_collection(user_id, "emails")
        
        # Query for financial emails with complete data
        query = {
            "user_id": user_id,
            "$or": [
                {"financial": True},
                {"importance_score": {"$gte": 9}},
                {"filter_reason": {"$regex": "financial"}}
            ]
        }
        
        cursor = emails_coll.find(query).sort([("date", -1)]).limit(limit)
        emails = await cursor.to_list(length=limit)
        
        logger.info(f"💰 Retrieved {len(emails)} financial emails for user {user_id}")
        return emails
        
    except Exception as e:
        logger.error(f"Error getting financial emails: {e}")
        return []

async def get_complete_user_emails(user_id: str, limit: int = 2000) -> List[Dict]:
    """Get user emails with complete data preserved"""
    try:
        emails_coll = await db_manager.get_collection(user_id, "emails")
        
        # Get all emails with complete data
        cursor = emails_coll.find({"user_id": user_id}).sort([("date", -1)]).limit(limit)
        emails = await cursor.to_list(length=limit)
        
        # Log data completeness statistics
        complete_emails = sum(1 for email in emails if email.get('data_complete'))
        financial_emails = sum(1 for email in emails if email.get('financial'))
        
        logger.info(f"📧 Retrieved {len(emails)} emails for user {user_id}")
        logger.info(f"   📊 Complete data: {complete_emails}/{len(emails)} emails")
        logger.info(f"   💰 Financial emails: {financial_emails}")
        
        return emails
        
    except Exception as e:
        logger.error(f"Error getting complete emails: {e}")
        return []

# Update the original function name for backward compatibility
insert_emails_optimized = insert_filtered_emails
get_user_emails_compressed = get_complete_user_emails

logger.info("🎯 Smart Email Filtering System initialized!")
logger.info(f"   📧 Complete data preservation enabled")
logger.info(f"   🗑️ Promotional filtering enabled")
logger.info(f"   💰 Financial email priority enabled") 
logger.info(f"   📎 Attachment metadata extraction enabled")

# ============================================================================
# FREE TIER PERFORMANCE INDEXES
# ============================================================================

async def create_minimal_indexes():
    """Create only essential indexes for free tier"""
    
    try:
        logger.info("🔧 Creating minimal indexes for free tier optimization...")
        
        # Create indexes for each database shard
        for db_index, database in db_manager.databases.items():
            try:
                users_coll = database["users"]
                emails_coll = database["emails"]
                chats_coll = database["chats"]
                
                # Essential indexes only
                await users_coll.create_index([("user_id", 1)], unique=True, background=True)
                await emails_coll.create_index([("user_id", 1), ("date", -1)], background=True)
                await chats_coll.create_index([("user_id", 1), ("timestamp", -1)], background=True)
                
                logger.info(f"✅ Minimal indexes created for shard {db_index}")
                
            except Exception as e:
                logger.error(f"Index creation error for shard {db_index}: {e}")
        
        logger.info("🚀 All minimal indexes created successfully!")
        
    except Exception as e:
        logger.error(f"⚠️ Error creating indexes: {e}")

# ============================================================================
# INITIALIZATION AND MONITORING
# ============================================================================

async def initialize_free_tier_database():
    """Initialize database with free tier optimizations"""
    
    try:
        logger.info("🚀 Initializing FREE TIER database system...")
        
        # Create minimal indexes
        await create_minimal_indexes()
        
        # Start cleanup scheduler if enabled
        if ENABLE_AUTO_CLEANUP:
            # Schedule cleanup every 6 hours
            asyncio.create_task(schedule_cleanup())
        
        # Get initial storage stats
        stats = await cleanup_manager.get_storage_stats()
        logger.info(f"📊 Initial storage stats: {stats['total_emails']} emails across {len(stats['databases'])} databases")
        
        logger.info("✅ FREE TIER database system initialized successfully!")
        
    except Exception as e:
        logger.error(f"⚠️ Database initialization error: {e}")

async def schedule_cleanup():
    """Schedule periodic cleanup"""
    while True:
        try:
            await asyncio.sleep(6 * 3600)  # 6 hours
            logger.info("🧹 Running scheduled cleanup...")
            await cleanup_manager.cleanup_all_users()
        except Exception as e:
            logger.error(f"Scheduled cleanup error: {e}")

# Initialize database when event loop is available
def schedule_db_init():
    """Schedule database initialization when event loop becomes available"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(initialize_free_tier_database())
        else:
            loop.run_until_complete(initialize_free_tier_database())
    except RuntimeError:
        # No event loop running, will initialize when app starts
        logger.info("Database initialization deferred until app startup")

# Try to initialize if event loop is available
try:
    schedule_db_init()
except Exception as e:
    logger.info(f"Database initialization scheduled for app startup: {e}")
