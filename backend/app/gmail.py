from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import re
from typing import List, Dict, Optional, Any
import html
import os
import asyncio
import time
import gzip
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import logging
from .config import (
    EMAIL_TIME_RANGE_DAYS, MAX_PAGINATION_PAGES, 
    MAX_CONCURRENT_EMAIL_PROCESSING, ENABLE_BATCH_PROCESSING,
    DEFAULT_EMAIL_LIMIT, MAX_EMAIL_LIMIT, 
    PRESERVE_EMAIL_BODY, PRESERVE_EMAIL_HEADERS, PRESERVE_ATTACHMENTS_INFO,
    ENABLE_SMART_EMAIL_FILTERING, FINANCIAL_EMAIL_KEYWORDS,
    calculate_email_importance, PROMOTIONAL_EMAIL_PATTERNS,
    MAX_EMAIL_AGE_DAYS, ESSENTIAL_EMAIL_FIELDS
)
from .db import (
    insert_filtered_emails, get_complete_user_emails, get_financial_emails,
    email_filter, email_processor, db_manager
)

# Configure logging
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Thread pool for parallel Gmail API calls
gmail_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="gmail_fetch")

def build_gmail_service(access_token: str, refresh_token: str = None, client_id: str = None, client_secret: str = None):
    """Build Gmail service with proper credentials for token refresh"""
    
    # Get required OAuth credentials from environment if not provided
    if not client_id:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_secret:
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    logger.info(f"🔑 Building Gmail service with:")
    logger.info(f"   - Access token: {access_token[:20]}...")
    logger.info(f"   - Refresh token: {refresh_token[:20] if refresh_token else 'None'}...")
    logger.info(f"   - Client ID: {client_id[:20] if client_id else 'None'}...")
    logger.info(f"   - Client Secret: {client_secret[:20] if client_secret else 'None'}...")
    
    # Create credentials with all required fields for refresh
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    
    logger.info(f"🔄 Credentials created, building Gmail service...")
    # Disable discovery cache to prevent memory issues
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    logger.info(f"✅ Gmail service built successfully (cache disabled)")
    return service

# ============================================================================
# COMPLETE EMAIL DATA EXTRACTOR
# ============================================================================

class CompleteEmailExtractor:
    """Extract complete email data including headers, body, and attachment information"""
    
    def __init__(self):
        self.financial_keywords = FINANCIAL_EMAIL_KEYWORDS
        self.stats = {
            "total_processed": 0,
            "complete_data_extracted": 0,
            "headers_preserved": 0,
            "attachments_found": 0,
            "financial_emails": 0
        }
    
    def extract_complete_email_data(self, gmail_msg: Dict) -> Dict:
        """Extract complete email data from Gmail API response"""
        try:
            email_data = {}
            
            # Basic email information
            email_data["id"] = gmail_msg.get("id")
            email_data["threadId"] = gmail_msg.get("threadId")
            email_data["labelIds"] = gmail_msg.get("labelIds", [])
            
            # Extract headers (PRESERVE COMPLETE HEADERS)
            headers = self.extract_headers(gmail_msg)
            email_data.update(headers)
            
            if PRESERVE_EMAIL_HEADERS:
                email_data["headers"] = self.get_raw_headers(gmail_msg)
                self.stats["headers_preserved"] += 1
            
            # Extract email body (PRESERVE COMPLETE BODY)
            if PRESERVE_EMAIL_BODY:
                email_data["body"] = self.extract_email_body(gmail_msg)
            
            # Extract snippet (always preserve)
            email_data["snippet"] = gmail_msg.get("snippet", "")
            
            # Extract attachment information (PRESERVE ATTACHMENT METADATA)
            if PRESERVE_ATTACHMENTS_INFO:
                email_data["attachments_info"] = self.extract_attachment_details(gmail_msg)
                if email_data["attachments_info"]:
                    self.stats["attachments_found"] += 1
            
            # Financial email detection
            email_data["financial"] = self.is_financial_email(email_data)
            if email_data["financial"]:
                self.stats["financial_emails"] += 1
            
            # Calculate importance score
            email_data["importance_score"] = calculate_email_importance(email_data)
            
            # Add processing metadata
            email_data["extracted_at"] = datetime.now().isoformat()  # Convert to string immediately
            email_data["data_complete"] = True
            
            self.stats["total_processed"] += 1
            self.stats["complete_data_extracted"] += 1
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error extracting complete email data: {e}")
            return self.extract_minimal_email_data(gmail_msg)
    
    def extract_headers(self, gmail_msg: Dict) -> Dict:
        """Extract essential header information"""
        headers = {}
        payload = gmail_msg.get("payload", {})
        header_list = payload.get("headers", [])
        
        header_map = {
            "Subject": "subject",
            "From": "sender", 
            "To": "recipient",
            "Date": "date",
            "Message-ID": "message_id",
            "Return-Path": "return_path",
            "Reply-To": "reply_to"
        }
        
        for header in header_list:
            name = header.get("name")
            value = header.get("value")
            
            if name in header_map:
                headers[header_map[name]] = value
            
            # 🔧 CRITICAL FIX: Special handling for date - convert to string immediately
            if name == "Date":
                try:
                    parsed_date = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
                    headers["date"] = parsed_date.isoformat()  # Convert to string immediately
                except:
                    try:
                        # Try alternative date format
                        parsed_date = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z")
                        headers["date"] = parsed_date.isoformat()
                    except:
                        # Fallback to current time as string
                        headers["date"] = datetime.now().isoformat()
        
        return headers
    
    def get_raw_headers(self, gmail_msg: Dict) -> Dict:
        """Get complete raw headers for advanced filtering"""
        raw_headers = {}
        payload = gmail_msg.get("payload", {})
        header_list = payload.get("headers", [])
        
        for header in header_list:
            name = header.get("name")
            value = header.get("value")
            raw_headers[name] = value
        
        return raw_headers
    
    def extract_email_body(self, gmail_msg: Dict) -> str:
        """Extract complete email body content"""
        try:
            payload = gmail_msg.get("payload", {})
            
            # Try to get body from main payload
            body = self.get_body_from_payload(payload)
            if body:
                return body
            
            # If no body in main payload, check parts
            parts = payload.get("parts", [])
            for part in parts:
                body = self.get_body_from_payload(part)
                if body:
                    return body
            
            # If still no body, return snippet
            return gmail_msg.get("snippet", "")
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return gmail_msg.get("snippet", "")
    
    def get_body_from_payload(self, payload: Dict) -> str:
        """Extract body content from payload"""
        try:
            body_data = payload.get("body", {})
            
            if body_data.get("data"):
                # Decode base64 content
                decoded = base64.urlsafe_b64decode(body_data["data"]).decode('utf-8')
                return decoded
            
            # Check nested parts
            parts = payload.get("parts", [])
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    part_body = part.get("body", {})
                    if part_body.get("data"):
                        decoded = base64.urlsafe_b64decode(part_body["data"]).decode('utf-8')
                        return decoded
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting body from payload: {e}")
            return ""
    
    def extract_attachment_details(self, gmail_msg: Dict) -> List[Dict]:
        """Extract detailed attachment information for financial analysis"""
        attachments = []
        
        try:
            payload = gmail_msg.get("payload", {})
            parts = payload.get("parts", [])
            
            for part in parts:
                if part.get("filename"):
                    attachment_info = {
                        "filename": part.get("filename"),
                        "mimeType": part.get("mimeType"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": part.get("body", {}).get("attachmentId"),
                        "is_financial_document": self.is_financial_attachment(part.get("filename", "")),
                        "extracted_at": datetime.now().isoformat()  # Convert to string immediately
                    }
                    
                    # Add financial document metadata
                    if attachment_info["is_financial_document"]:
                        attachment_info["document_type"] = self.classify_financial_document(part.get("filename", ""))
                    
                    attachments.append(attachment_info)
            
            return attachments
            
        except Exception as e:
            logger.error(f"Error extracting attachment details: {e}")
            return []
    
    def is_financial_attachment(self, filename: str) -> bool:
        """Check if attachment is a financial document"""
        financial_patterns = [
            'invoice', 'receipt', 'statement', 'bill', 'transaction',
            'payment', 'order', 'ticket', 'booking', 'confirmation',
            'pdf', 'receipt.pdf', 'invoice.pdf', 'statement.pdf'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in financial_patterns)
    
    def classify_financial_document(self, filename: str) -> str:
        """Classify type of financial document"""
        filename_lower = filename.lower()
        
        if 'invoice' in filename_lower:
            return 'invoice'
        elif 'receipt' in filename_lower:
            return 'receipt'
        elif 'statement' in filename_lower:
            return 'statement'
        elif 'ticket' in filename_lower:
            return 'ticket'
        elif 'booking' in filename_lower:
            return 'booking'
        else:
            return 'financial_document'
    
    def is_financial_email(self, email_data: Dict) -> bool:
        """Check if email is financial/transaction related"""
        content = f"{email_data.get('subject', '')} {email_data.get('sender', '')} {email_data.get('snippet', '')}".lower()
        
        # Check for financial keywords
        if any(keyword.lower() in content for keyword in self.financial_keywords):
            return True
        
        # Check for financial attachments
        attachments = email_data.get('attachments_info', [])
        if any(att.get('is_financial_document') for att in attachments):
            return True
        
        return False
    
    def extract_minimal_email_data(self, gmail_msg: Dict) -> Dict:
        """Fallback minimal email extraction"""
        return {
            "id": gmail_msg.get("id"),
            "threadId": gmail_msg.get("threadId"),
            "subject": "Error extracting subject",
            "sender": "Error extracting sender",
            "snippet": gmail_msg.get("snippet", ""),
            "date": datetime.now().isoformat(),  # Convert to string immediately
            "financial": False,
            "importance_score": 5,
            "data_complete": False,
            "extraction_error": True
        }
    
    def get_extraction_stats(self) -> Dict:
        """Get email extraction statistics"""
        return {
            **self.stats,
            "complete_data_rate": round((self.stats["complete_data_extracted"] / max(self.stats["total_processed"], 1)) * 100, 1),
            "financial_detection_rate": round((self.stats["financial_emails"] / max(self.stats["total_processed"], 1)) * 100, 1),
            "attachment_detection_rate": round((self.stats["attachments_found"] / max(self.stats["total_processed"], 1)) * 100, 1)
        }

# Global email extractor
email_extractor = CompleteEmailExtractor()

# ============================================================================
# PARALLEL EMAIL FETCHING
# ============================================================================

async def smart_parallel_fetch(service, user_id='me', max_results=20000):
    """Intelligent parallel email fetching with priority-based processing"""
    
    logger.info(f"🚀 Starting smart parallel fetch for {max_results} emails")
    start_time = time.time()
    
    # Strategy 1: Recent emails first (high priority)
    recent_query = 'newer_than:30d'
    recent_limit = min(10000, max_results)
    
    # Strategy 2: Older emails in background (low priority)
    historical_query = f'older_than:30d newer_than:{EMAIL_TIME_RANGE_DAYS}d'
    historical_limit = max_results - recent_limit if max_results > recent_limit else 0
    
    # Execute parallel fetching
    tasks = []
    
    # High priority: Recent emails
    tasks.append(fetch_emails_parallel(service, user_id, recent_query, recent_limit, priority="high"))
    
    # Low priority: Historical emails (if needed)
    if historical_limit > 0:
        tasks.append(fetch_emails_parallel(service, user_id, historical_query, historical_limit, priority="low"))
    
    # Execute in parallel and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results
    all_emails = []
    for result in results:
        if isinstance(result, list):
            all_emails.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Error in parallel fetch: {result}")
    
    end_time = time.time()
    fetch_time = end_time - start_time
    
    logger.info(f"✅ Smart parallel fetch complete: {len(all_emails)} emails in {fetch_time:.2f}s")
    logger.info(f"📊 Fetch rate: {len(all_emails) / fetch_time:.1f} emails/second")
    
    return all_emails

async def fetch_emails_parallel(service, user_id, query, max_results, priority="normal"):
    """Optimized parallel page fetching with intelligent batching"""
    
    if max_results <= 0:
        return []
    
    logger.info(f"📧 Fetching {max_results} emails with query: {query} (priority: {priority})")
    
    all_messages = []
    concurrent_pages = 5 if priority == "high" else 3  # More workers for high priority
    semaphore = asyncio.Semaphore(concurrent_pages)
    
    async def fetch_page_async(page_token=None):
        """Fetch a single page asynchronously"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                gmail_executor, 
                fetch_single_page_sync, 
                service, user_id, query, page_token
            )
    
    try:
        # Get first page to establish pagination
        first_page = await fetch_page_async()
        if not first_page or 'messages' not in first_page:
            logger.warning(f"No messages found for query: {query}")
            return []
        
        all_messages.extend(first_page['messages'])
        logger.info(f"📄 First page fetched: {len(first_page['messages'])} messages")
        
        # Parallel fetch remaining pages
        next_token = first_page.get('nextPageToken')
        page_count = 1
        max_pages = min(MAX_PAGINATION_PAGES, (max_results // 500) + 1)
        
        while next_token and len(all_messages) < max_results and page_count < max_pages:
            # Prepare parallel page requests
            page_tasks = []
            current_tokens = []
            
            # Collect tokens for parallel processing
            for _ in range(min(concurrent_pages, max_pages - page_count)):
                if next_token and len(all_messages) < max_results:
                    current_tokens.append(next_token)
                    next_token = None  # Will be updated after processing
                    
            if not current_tokens:
                break
            
            # Fetch pages in parallel
            page_tasks = [fetch_page_async(token) for token in current_tokens]
            page_results = await asyncio.gather(*page_tasks, return_exceptions=True)
            
            # Process results
            for result in page_results:
                if isinstance(result, dict) and 'messages' in result:
                    new_messages = result['messages']
                    all_messages.extend(new_messages)
                    
                    # Update next token for continuation
                    if result.get('nextPageToken') and not next_token:
                        next_token = result['nextPageToken']
                        
                elif isinstance(result, Exception):
                    logger.error(f"Error fetching page: {result}")
                    
            page_count += len(current_tokens)
            
            if page_count % 5 == 0:  # Log progress every 5 pages
                logger.info(f"📄 Fetched {page_count} pages, {len(all_messages)} messages so far")
        
        logger.info(f"📊 Pagination complete: {len(all_messages)} messages from {page_count} pages")
        return all_messages[:max_results]
        
    except Exception as e:
        logger.error(f"❌ Error in parallel email fetching: {e}")
        return all_messages  # Return what we have so far

def fetch_single_page_sync(service, user_id, query, page_token=None):
    """Synchronous single page fetch for thread pool execution"""
    try:
        params = {
            'userId': user_id,
            'maxResults': 500,  # Gmail's maximum per request
            'q': query
        }
        if page_token:
            params['pageToken'] = page_token
            
        return service.users().messages().list(**params).execute()
        
    except Exception as e:
        logger.error(f"⚠️ Error fetching single page: {e}")
        return {}

# ============================================================================
# OPTIMIZED EMAIL PROCESSING
# ============================================================================

async def fetch_emails_optimized(service, user_id='me', max_results=20000):
    """
    Main optimized email fetching function with all improvements
    """
    
    logger.info(f"🚀 Starting optimized email fetch for {max_results} emails")
    logger.info(f"🔧 Using {EMAIL_TIME_RANGE_DAYS} days time range")
    logger.info(f"⚡ Batch processing enabled: {ENABLE_BATCH_PROCESSING}")
    logger.info(f"🔄 Max concurrent processing: {MAX_CONCURRENT_EMAIL_PROCESSING}")
    
    start_time = time.time()
    
    # Step 1: Smart parallel message fetching
    all_messages = await smart_parallel_fetch(service, user_id, max_results)
    
    if not all_messages:
        logger.warning("❌ No emails found matching criteria")
        return []
    
    # Step 2: Parallel detailed content fetching
    logger.info(f"📥 Fetching detailed content for {len(all_messages)} messages...")
    
    if ENABLE_BATCH_PROCESSING:
        emails = await fetch_detailed_content_batch(service, user_id, all_messages)
    else:
        emails = await fetch_detailed_content_sequential(service, user_id, all_messages)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info(f"✅ OPTIMIZED EMAIL FETCH COMPLETE")
    logger.info(f"📊 Total emails processed: {len(emails)}")
    logger.info(f"⏱️ Total time: {total_time:.2f} seconds")
    logger.info(f"🚀 Processing rate: {len(emails) / total_time:.1f} emails/second")
    logger.info(f"📄 Average time per email: {(total_time / len(emails)) * 1000:.1f}ms")
    
    return emails

async def fetch_detailed_content_batch(service, user_id, all_messages):
    """Fetch detailed email content using batch processing"""
    
    emails = []
    batch_size = 100  # Process 100 emails at a time
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMAIL_PROCESSING)
    
    async def fetch_email_details(msg_batch):
        """Fetch details for a batch of emails"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                gmail_executor,
                fetch_email_batch_sync,
                service, user_id, msg_batch
            )
    
    # Process emails in batches
    for i in range(0, len(all_messages), batch_size):
        batch = all_messages[i:i + batch_size]
        
        # Create batch processing tasks
        batch_tasks = []
        chunk_size = 20  # 20 emails per chunk within batch
        
        for j in range(0, len(batch), chunk_size):
            chunk = batch[j:j + chunk_size]
            batch_tasks.append(fetch_email_details(chunk))
        
        # Execute batch tasks in parallel
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Combine batch results
        for result in batch_results:
            if isinstance(result, list):
                emails.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in batch processing: {result}")
        
        # Progress update
        if (i + batch_size) % 500 == 0:
            logger.info(f"📧 Processed {len(emails)} emails so far...")
    
    return emails

def fetch_email_batch_sync(service, user_id, msg_batch):
    """Synchronously fetch a batch of email details with complete data extraction"""
    emails = []
    
    for msg in msg_batch:
        try:
            message = service.users().messages().get(
                userId=user_id, 
                id=msg['id'], 
                format='full'
            ).execute()
            
            # Use complete email data extraction
            email_data = email_extractor.extract_complete_email_data(message)
            if email_data:
                emails.append(email_data)
                
        except Exception as e:
            logger.error(f"⚠️ Error processing message {msg.get('id', 'unknown')}: {e}")
            continue
    
    return emails

async def fetch_detailed_content_sequential(service, user_id, all_messages):
    """Fallback sequential processing for detailed content with complete data extraction"""
    
    emails = []
    
    for i, msg in enumerate(all_messages):
        try:
            if i % 100 == 0:
                logger.info(f"📧 Processing message {i+1}/{len(all_messages)}...")
                
            message = service.users().messages().get(
                userId=user_id, 
                id=msg['id'], 
                format='full'
            ).execute()
            
            # Use complete email data extraction
            email_data = email_extractor.extract_complete_email_data(message)
            if email_data:
                emails.append(email_data)
                
        except Exception as e:
            logger.error(f"⚠️ Error processing message {i+1}: {e}")
            continue
    
    return emails

def extract_email_data(message):
    """Extract complete email data (updated for compatibility)"""
    # Use the new complete email extractor
    return email_extractor.extract_complete_email_data(message)

def extract_email_body(payload):
    """Extract complete email body content"""
    body = ""
    
    try:
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and part.get('body', {}).get('data'):
                    raw_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    body = clean_html(raw_html)
                    break
        else:
            if payload.get('body') and payload['body'].get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

    except Exception as e:
        logger.error(f"Error extracting email body: {e}")
        body = ""
    
    return body

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

async def fetch_emails(service, user_id='me', max_results=2500):
    """
    Backward compatible fetch_emails function with complete data extraction
    This maintains the original function signature while using new complete data processing
    """
    
    # Determine optimal max_results based on configuration
    optimal_limit = min(max_results, DEFAULT_EMAIL_LIMIT)
    
    logger.info(f"📧 Backward compatible fetch with complete data extraction")
    logger.info(f"🔧 Requested: {max_results}, Optimal: {optimal_limit}")
    
    # Use optimized fetching with complete data
    return await fetch_emails_optimized(service, user_id, optimal_limit)

def clean_html(raw_html):
    """Basic clean-up to remove HTML tags, decode entities"""
    try:
        text = re.sub('<[^<]+?>', '', raw_html)
        text = html.unescape(text)
        return text.strip()
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}")
        return raw_html

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def get_gmail_performance_stats():
    """Get Gmail fetching performance statistics with complete data processing"""
    
    extraction_stats = email_extractor.get_extraction_stats()
    
    return {
        "thread_pool_size": gmail_executor._max_workers,
        "active_threads": len([t for t in gmail_executor._threads if t.is_alive()]) if hasattr(gmail_executor, '_threads') else 0,
        "batch_processing_enabled": ENABLE_BATCH_PROCESSING,
        "max_concurrent_processing": MAX_CONCURRENT_EMAIL_PROCESSING,
        "max_pagination_pages": MAX_PAGINATION_PAGES,
        "email_time_range_days": EMAIL_TIME_RANGE_DAYS,
        "complete_data_extraction": True,
        "extraction_stats": extraction_stats,
        "data_preservation": {
            "email_body_preserved": PRESERVE_EMAIL_BODY,
            "headers_preserved": PRESERVE_EMAIL_HEADERS,
            "attachments_info_preserved": PRESERVE_ATTACHMENTS_INFO
        }
    }

logger.info("🚀 Gmail module loaded with complete data extraction!")
logger.info(f"   📧 Complete email data preservation enabled")
logger.info(f"   🎯 Smart promotional filtering enabled")
logger.info(f"   💰 Financial email priority processing")
logger.info(f"   📎 Attachment metadata extraction")

# ============================================================================
# ENHANCED GMAIL PROCESSING WITH COMPLETE DATA
# ============================================================================

async def fetch_gmail_emails(service, user_id: str, max_results: int = None) -> List[Dict]:
    """Fetch Gmail emails with complete data preservation and smart filtering"""
    
    if max_results is None:
        max_results = DEFAULT_EMAIL_LIMIT
    
    # Limit to maximum allowed
    max_results = min(max_results, MAX_EMAIL_LIMIT)
    
    try:
        logger.info(f"🔄 Fetching complete Gmail data for user {user_id} (limit: {max_results})")
        
        # Calculate date range for 6 months only
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=EMAIL_TIME_RANGE_DAYS)
        date_query = f"after:{six_months_ago.strftime('%Y/%m/%d')}"
        
        # Get email IDs
        email_ids = []
        page_token = None
        
        while len(email_ids) < max_results:
            try:
                result = service.users().messages().list(
                    userId='me',
                    q=date_query,
                    maxResults=min(500, max_results - len(email_ids)),
                    pageToken=page_token
                ).execute()
                
                messages = result.get('messages', [])
                email_ids.extend([msg['id'] for msg in messages])
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                    
                logger.info(f"📥 Collected {len(email_ids)} email IDs...")
                
            except Exception as e:
                logger.error(f"Error fetching email IDs: {e}")
                break
        
        logger.info(f"📧 Total email IDs collected: {len(email_ids)}")
        
        # Fetch complete email data
        complete_emails = []
        batch_size = 20  # Smaller batches for complete data
        
        for i in range(0, len(email_ids), batch_size):
            batch_ids = email_ids[i:i + batch_size]
            
            try:
                # Process batch
                batch_emails = []
                for email_id in batch_ids:
                    try:
                        gmail_msg = service.users().messages().get(
                            userId='me',
                            id=email_id,
                            format='full'
                        ).execute()
                        
                        # Extract complete email data
                        email_data = email_extractor.extract_complete_email_data(gmail_msg)
                        if email_data:
                            batch_emails.append(email_data)
                            
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {e}")
                
                complete_emails.extend(batch_emails)
                logger.info(f"📊 Processed batch {i//batch_size + 1}: {len(complete_emails)} complete emails")
                
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
        
        # Get extraction statistics
        stats = email_extractor.get_extraction_stats()
        
        logger.info(f"✅ Complete Gmail data extraction finished:")
        logger.info(f"   📧 Total emails processed: {stats['total_processed']}")
        logger.info(f"   📊 Complete data extracted: {stats['complete_data_extracted']}")
        logger.info(f"   💰 Financial emails detected: {stats['financial_emails']}")
        logger.info(f"   📎 Emails with attachments: {stats['attachments_found']}")
        logger.info(f"   🎯 Complete data rate: {stats['complete_data_rate']}%")
        
        return complete_emails
        
    except Exception as e:
        logger.error(f"⚠️ Error in complete Gmail data fetch: {e}")
        return []

async def process_and_store_emails(user_id: str, emails: List[Dict]) -> Dict[str, Any]:
    """Process and store emails with smart filtering and complete data preservation + Mem0 upload"""
    
    try:
        logger.info(f"🚀 Processing and storing {len(emails)} emails with complete data for user {user_id}")
        
        # Store emails with smart filtering
        result = await insert_filtered_emails(user_id, emails)
        
        # 🔧 CRITICAL FIX: Upload to Mem0 after successful MongoDB storage
        mem0_upload_success = False
        if result.get("inserted", 0) > 0:
            try:
                logger.info(f"📤 Starting Mem0 upload for {result['inserted']} emails for user {user_id}")
                
                # Convert stored emails to EmailMessage format for Mem0
                from .mem0_agent_agno import EmailMessage
                
                # Get the stored emails from MongoDB
                from .db import get_complete_user_emails
                logger.info(f"🔍 Retrieving stored emails from MongoDB for user {user_id}")
                stored_emails = await get_complete_user_emails(user_id, limit=result["inserted"])
                
                logger.info(f"📧 Retrieved {len(stored_emails)} emails from MongoDB for Mem0 upload")
                
                if not stored_emails:
                    logger.error(f"❌ No stored emails found in MongoDB for user {user_id} - cannot upload to Mem0")
                else:
                    # Convert to EmailMessage format
                    email_messages = []
                    for i, email_data in enumerate(stored_emails):
                        try:
                            # 🔧 CRITICAL FIX: Convert datetime to string for EmailMessage
                            date_value = email_data.get("date", "")
                            if hasattr(date_value, 'isoformat'):  # It's a datetime object
                                date_str = date_value.isoformat()
                            elif isinstance(date_value, str):
                                date_str = date_value
                            else:
                                date_str = str(date_value) if date_value else ""
                            
                            email_msg = EmailMessage(
                                id=email_data.get("id", f"email_{i}"),
                                subject=email_data.get("subject", ""),
                                sender=email_data.get("sender", ""),
                                snippet=email_data.get("snippet", ""),
                                body=email_data.get("body", ""),
                                date=date_str
                            )
                            email_messages.append(email_msg)
                        except Exception as conversion_error:
                            logger.error(f"⚠️ Failed to convert email {i} to EmailMessage: {conversion_error}")
                            logger.error(f"⚠️ Email data sample: {dict(list(email_data.items())[:3])}")
                    
                    logger.info(f"✅ Converted {len(email_messages)} emails to EmailMessage format")
                    
                    if email_messages:
                        # ===== STEP 1: PROCESS FINANCIAL TRANSACTIONS FIRST =====
                        logger.info(f"💰 Processing financial transactions for {len(email_messages)} emails for user {user_id}")
                        try:
                            # Call financial processing function directly (no API call needed)
                            from .financial_transaction_processor import process_financial_before_mem0
                            
                            financial_result = await process_financial_before_mem0(user_id, "pre_mem0_upload")
                            
                            if financial_result.get("success", False):
                                transactions_found = financial_result.get('transactions_found', 0)
                                logger.info(f"✅ Financial processing completed: {transactions_found} transactions")
                            else:
                                logger.warning(f"⚠️ Financial processing failed: {financial_result.get('error', 'Unknown error')}")
                        except Exception as financial_error:
                            logger.error(f"❌ Financial processing error: {financial_error}")
                            # Continue with Mem0 upload even if financial processing fails
                        
                        # ===== STEP 2: UPLOAD TO MEM0 WITH FINANCIAL CONTEXT =====
                        from .parallel_mem0_uploader import upload_emails_parallel_optimized
                        logger.info(f"🚀 Uploading {len(email_messages)} emails to Mem0 for user {user_id} (WITH financial context)")
                        mem0_result = await upload_emails_parallel_optimized(user_id, email_messages)
                        logger.info(f"✅ Mem0 upload completed: {mem0_result}")
                        mem0_upload_success = True
                    else:
                        logger.error(f"❌ No valid email messages to upload to Mem0 for user {user_id}")
                
            except Exception as mem0_error:
                logger.error(f"⚠️ Mem0 upload failed for user {user_id}: {mem0_error}")
                logger.error(f"⚠️ Mem0 error details: {type(mem0_error).__name__}: {str(mem0_error)}")
                import traceback
                logger.error(f"⚠️ Mem0 error traceback: {traceback.format_exc()}")
                # Don't fail the entire process if Mem0 upload fails
        else:
            logger.warning(f"⚠️ No emails inserted for user {user_id} - skipping Mem0 upload")
            logger.warning(f"⚠️ Insert result: {result}")
        
        # Get processing statistics
        extraction_stats = email_extractor.get_extraction_stats()
        
        # 🔧 CRITICAL FIX: Ensure consistent return format with "success" key
        processing_summary = {
            "success": True,  # ✅ Consistent success key
            "user_id": user_id,
            "emails_processed": len(emails),
            "emails_stored": result.get("inserted", 0),
            "promotional_filtered": result.get("filtered", 0),
            "financial_preserved": result.get("financial", 0),
            "mem0_uploaded": mem0_upload_success,  # ✅ Mem0 status
            "extraction_stats": extraction_stats,
            "filter_stats": result.get("filter_stats", {}),
            "data_preservation": {
                "complete_data_rate": extraction_stats.get("complete_data_rate", 0),
                "headers_preserved": extraction_stats.get("headers_preserved", 0),
                "attachments_detected": extraction_stats.get("attachments_found", 0),
                "financial_detection_rate": extraction_stats.get("financial_detection_rate", 0)
            }
        }
        
        logger.info(f"🎉 Email processing completed for user {user_id}:")
        logger.info(f"   📧 Emails processed: {processing_summary['emails_processed']}")
        logger.info(f"   💾 Emails stored: {processing_summary['emails_stored']}")
        logger.info(f"   🗑️ Promotional filtered: {processing_summary['promotional_filtered']}")
        logger.info(f"   💰 Financial preserved: {processing_summary['financial_preserved']}")
        logger.info(f"   📤 Mem0 uploaded: {processing_summary['mem0_uploaded']}")
        logger.info(f"   📊 Complete data rate: {extraction_stats.get('complete_data_rate', 0)}%")
        
        return processing_summary
        
    except Exception as e:
        logger.error(f"⚠️ Error in email processing: {e}")
        return {"success": False, "error": str(e)}

async def get_storage_statistics() -> Dict[str, Any]:
    """Get comprehensive storage statistics"""
    
    try:
        extraction_stats = email_extractor.get_extraction_stats()
        
        return {
            "email_extraction": extraction_stats,
            "data_preservation": {
                "email_body_preserved": PRESERVE_EMAIL_BODY,
                "headers_preserved": PRESERVE_EMAIL_HEADERS,
                "attachments_info_preserved": PRESERVE_ATTACHMENTS_INFO,
                "smart_filtering_enabled": ENABLE_SMART_EMAIL_FILTERING
            },
            "storage_optimization": {
                "promotional_filtering": "60-70% space saved",
                "complete_data_preserved": "Financial & important emails",
                "retention_period": f"{EMAIL_TIME_RANGE_DAYS} days"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting storage statistics: {e}")
        return {"error": str(e)}

logger.info("📧 Gmail module updated for FREE TIER optimization!")
logger.info(f"   📊 Email limit per user: {DEFAULT_EMAIL_LIMIT}")
logger.info(f"   ⏰ Retention period: {EMAIL_TIME_RANGE_DAYS} days (6 months)")
logger.info(f"   🗜️ Smart filtering enabled: {ENABLE_SMART_EMAIL_FILTERING}")
logger.info(f"   💾 Body storage: {'Enabled' if PRESERVE_EMAIL_BODY else 'Disabled'}")

# ============================================================================
# PROGRESSIVE EMAIL LOADING FUNCTIONS
# ============================================================================

async def fetch_gmail_emails_by_days(service, user_id: str, days: int = 7, max_results: int = 500) -> List[Dict]:
    """
    Fetch recent emails for immediate dashboard access (progressive loading)
    
    Args:
        service: Gmail service instance
        user_id: User ID
        days: Number of recent days to fetch (default: 7)
        max_results: Maximum emails to fetch (default: 500)
    
    Returns:
        List of email dictionaries
    """
    logger.info(f"🚀 [IMMEDIATE] Fetching {days}-day recent emails for user {user_id} (limit: {max_results})")
    
    try:
        # Calculate date range for recent emails
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 🔧 CRITICAL FIX: Remove 'before' clause to include TODAY's emails
        # Gmail's 'before' is exclusive, so using only 'after' includes all emails from start_date onwards
        query = f"after:{start_date.strftime('%Y/%m/%d')}"
        
        logger.info(f"🔍 [IMMEDIATE] Gmail query: {query}")
        logger.info(f"📅 [IMMEDIATE] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (including TODAY)")
        
        # Fetch emails using existing optimized function
        all_messages = []
        page_token = None
        fetched_count = 0
        
        while fetched_count < max_results:
            try:
                # Fetch page of message IDs
                result = service.users().messages().list(
                    userId=user_id,
                    q=query,
                    maxResults=min(100, max_results - fetched_count),
                    pageToken=page_token
                ).execute()
                
                messages = result.get('messages', [])
                if not messages:
                    break
                
                all_messages.extend(messages)
                fetched_count += len(messages)
                
                logger.info(f"📧 [IMMEDIATE] Fetched {len(messages)} message IDs, total: {fetched_count}")
                
                # Check for next page
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"❌ [IMMEDIATE] Error fetching message IDs: {e}")
                break
        
        if not all_messages:
            logger.info(f"📭 [IMMEDIATE] No emails found for {days} days")
            return []
        
        # Fetch detailed email content
        logger.info(f"📧 [IMMEDIATE] Fetching detailed content for {len(all_messages)} emails")
        
        detailed_emails = []
        batch_size = 20  # Smaller batches for faster response
        
        for i in range(0, len(all_messages), batch_size):
            batch = all_messages[i:i + batch_size]
            batch_emails = await fetch_email_batch_details(service, user_id, batch)
            detailed_emails.extend(batch_emails)
            
            logger.info(f"✅ [IMMEDIATE] Processed batch {i//batch_size + 1}/{(len(all_messages) + batch_size - 1)//batch_size}")
        
        logger.info(f"🎉 [IMMEDIATE] Successfully fetched {len(detailed_emails)} recent emails INCLUDING TODAY")
        return detailed_emails
        
    except Exception as e:
        logger.error(f"❌ [IMMEDIATE] Error fetching recent emails: {e}")
        return []

async def fetch_gmail_emails_historical(service, user_id: str, months: int = 6, exclude_recent_days: int = 7, max_results: int = 5000) -> List[Dict]:
    """
    Fetch historical emails for background processing (progressive loading)
    
    Args:
        service: Gmail service instance
        user_id: User ID
        months: Number of months to go back (default: 6)
        exclude_recent_days: Days to exclude from the beginning (default: 7)
        max_results: Maximum emails to fetch (default: 5000)
    
    Returns:
        List of email dictionaries
    """
    logger.info(f"🔄 [BACKGROUND] Fetching {months}-month historical emails for user {user_id} (limit: {max_results})")
    
    try:
        # Calculate date range for historical emails (exclude recent days already processed)
        end_date = datetime.now() - timedelta(days=exclude_recent_days)
        start_date = end_date - timedelta(days=months * 30)  # Approximate months to days
        
        # 🔧 FIXED: Use proper date range with 'before' for historical emails (end_date is exclusive)
        # This ensures we don't overlap with the immediate emails already processed
        query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        
        logger.info(f"🔍 [BACKGROUND] Gmail query: {query}")
        logger.info(f"📅 [BACKGROUND] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (excluding recent {exclude_recent_days} days)")
        
        # Fetch emails using existing optimized function
        all_messages = []
        page_token = None
        fetched_count = 0
        
        while fetched_count < max_results:
            try:
                # Fetch page of message IDs
                result = service.users().messages().list(
                    userId=user_id,
                    q=query,
                    maxResults=min(100, max_results - fetched_count),
                    pageToken=page_token
                ).execute()
                
                messages = result.get('messages', [])
                if not messages:
                    break
                
                all_messages.extend(messages)
                fetched_count += len(messages)
                
                logger.info(f"📧 [BACKGROUND] Fetched {len(messages)} message IDs, total: {fetched_count}")
                
                # Check for next page
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"❌ [BACKGROUND] Error fetching message IDs: {e}")
                break
        
        if not all_messages:
            logger.info(f"📭 [BACKGROUND] No historical emails found for {months} months")
            return []
        
        # Fetch detailed email content in larger batches (background processing can be slower)
        logger.info(f"📧 [BACKGROUND] Fetching detailed content for {len(all_messages)} historical emails")
        
        detailed_emails = []
        batch_size = 50  # Larger batches for background processing
        
        for i in range(0, len(all_messages), batch_size):
            batch = all_messages[i:i + batch_size]
            batch_emails = await fetch_email_batch_details(service, user_id, batch)
            detailed_emails.extend(batch_emails)
            
            # Progress logging for background processing
            progress = ((i + batch_size) / len(all_messages)) * 100
            logger.info(f"🔄 [BACKGROUND] Progress: {progress:.1f}% ({i + len(batch)}/{len(all_messages)} emails)")
            
            # Console progress for user feedback
            if i % (batch_size * 4) == 0:  # Every 4 batches
                print(f"🔄 Background sync progress: {progress:.1f}% ({i + len(batch)}/{len(all_messages)} historical emails)")
        
        logger.info(f"🎉 [BACKGROUND] Successfully fetched {len(detailed_emails)} historical emails")
        return detailed_emails
        
    except Exception as e:
        logger.error(f"❌ [BACKGROUND] Error fetching historical emails: {e}")
        return []

async def fetch_email_batch_details(service, user_id: str, message_batch: List[Dict]) -> List[Dict]:
    """
    Fetch detailed email content for a batch of message IDs (MEMORY-SAFE VERSION)
    
    Args:
        service: Gmail service instance
        user_id: User ID
        message_batch: List of message dictionaries with IDs
    
    Returns:
        List of detailed email dictionaries
    """
    detailed_emails = []
    
    try:
        logger.info(f"🔄 [BATCH] Processing {len(message_batch)} emails sequentially (memory-safe)")
        
        # Process emails SEQUENTIALLY to avoid memory conflicts
        for i, msg in enumerate(message_batch):
            try:
                # 🔧 CRITICAL: Validate message ID before processing
                msg_id = msg.get('id')
                if not msg_id:
                    logger.error(f"❌ [BATCH] Message {i+1} missing ID: {msg}")
                    continue
                
                logger.debug(f"📧 [BATCH] Processing email {i+1}/{len(message_batch)}: {msg_id[:8]}...")
                
                # Add small delay to prevent API rate limiting and memory pressure
                if i > 0 and i % 5 == 0:
                    await asyncio.sleep(0.1)
                
                # Fetch detailed email content synchronously (safer)
                email_detail = service.users().messages().get(userId=user_id, id=msg_id).execute()
                
                # 🔧 CRITICAL: Validate Gmail API response has ID
                gmail_response_id = email_detail.get("id")
                if not gmail_response_id:
                    logger.error(f"❌ [BATCH] Gmail API response missing ID for message {msg_id}")
                    continue
                
                logger.debug(f"✅ [BATCH] Gmail API returned email: {gmail_response_id[:8]}...")
                
                # Extract complete email data
                email_data = email_extractor.extract_complete_email_data(email_detail)
                
                # 🔧 CRITICAL: Validate extracted email has ID
                extracted_id = email_data.get("id")
                if not extracted_id:
                    logger.error(f"❌ [BATCH] Email extractor lost ID for message {msg_id}")
                    # Force set the ID from original message
                    email_data["id"] = msg_id
                    logger.warning(f"🔧 [BATCH] Forced ID back to email: {msg_id[:8]}...")
                
                logger.debug(f"📧 [BATCH] Extracted email: {extracted_id[:8]}... | {email_data.get('subject', 'No Subject')[:30]}")
                
                detailed_emails.append(email_data)
                
                # Log progress every 5 emails
                if (i + 1) % 5 == 0:
                    logger.info(f"📧 [BATCH] Processed {i + 1}/{len(message_batch)} emails")
                
                # Force garbage collection every 10 emails to prevent memory buildup
                if (i + 1) % 10 == 0:
                    import gc
                    gc.collect()
                
            except Exception as e:
                logger.error(f"❌ [BATCH] Error fetching email {msg.get('id', 'unknown')}: {e}")
                logger.error(f"❌ [BATCH] Error type: {type(e).__name__}")
                continue
        
        logger.info(f"✅ [BATCH] Successfully processed {len(detailed_emails)}/{len(message_batch)} emails")
        
        # 🔧 FINAL VALIDATION: Check all emails have IDs
        emails_without_ids = 0
        for email in detailed_emails:
            if not email.get("id"):
                emails_without_ids += 1
        
        if emails_without_ids > 0:
            logger.error(f"❌ [BATCH] CRITICAL: {emails_without_ids} emails missing IDs after extraction!")
        else:
            logger.info(f"✅ [BATCH] All {len(detailed_emails)} emails have valid IDs")
        
        return detailed_emails
        
    except Exception as e:
        logger.error(f"❌ [BATCH] Critical error in batch processing: {e}")
        import traceback
        logger.error(f"❌ [BATCH] Traceback: {traceback.format_exc()}")
        return []

# ============================================================================
# PROGRESSIVE EMAIL PROCESSING
# ============================================================================

async def process_and_store_emails(user_id: str, emails: List[Dict], is_immediate: bool = False, is_historical: bool = False) -> Dict[str, Any]:
    """
    Enhanced email processing with progressive loading support
    
    Args:
        user_id: User ID
        emails: List of email dictionaries
        is_immediate: True if processing recent emails for immediate access
        is_historical: True if processing historical emails in background
    
    Returns:
        Processing result dictionary
    """
    processing_type = "immediate" if is_immediate else ("historical" if is_historical else "standard")
    logger.info(f"🔄 [{processing_type.upper()}] Processing {len(emails)} emails for user {user_id}")
    
    try:
        # Apply smart email filtering
        if ENABLE_SMART_EMAIL_FILTERING:
            filtered_emails = await email_filter.smart_filter_emails(emails, user_id, processing_type)
            logger.info(f"📊 [{processing_type.upper()}] Smart filtering: {len(emails)} → {len(filtered_emails)} emails")
        else:
            filtered_emails = emails
        
        if not filtered_emails:
            logger.info(f"📭 [{processing_type.upper()}] No emails to process after filtering")
            return {
                "success": True,
                "status": "success",
                "emails_stored": 0,
                "promotional_filtered": len(emails),
                "processing_type": processing_type
            }
        
        # Store emails in database
        storage_result = await insert_filtered_emails(user_id, filtered_emails, processing_type)
        
        if storage_result.get("success", False):
            stored_count = storage_result.get("inserted", 0)
            logger.info(f"✅ [{processing_type.upper()}] Successfully stored {stored_count} emails")
            
            # Upload to Mem0 for AI processing
            if stored_count > 0:
                from .mem0_agent_agno import EmailMessage
                
                # Convert to EmailMessage objects
                email_messages = []
                for email in filtered_emails[:stored_count]:  # Only process stored emails
                    try:
                        # Handle date conversion properly
                        date_value = email.get("date", "")
                        if hasattr(date_value, 'isoformat'):  # It's a datetime object
                            date_str = date_value.isoformat()
                        elif isinstance(date_value, str):
                            date_str = date_value
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
                        logger.error(f"Error converting email to EmailMessage: {e}")
                        continue
                
                if email_messages:
                    logger.info(f"🚀 [{processing_type.upper()}] Starting HIGH-PERFORMANCE PARALLEL Mem0 upload for {len(email_messages)} emails...")
                    
                    # Convert EmailMessage objects back to dict format for parallel uploader
                    emails_for_parallel = []
                    for email_msg in email_messages:
                        emails_for_parallel.append({
                            "id": email_msg.id,
                            "subject": email_msg.subject,
                            "sender": email_msg.sender,
                            "snippet": email_msg.snippet,
                            "body": email_msg.body,
                            "date": email_msg.date
                        })
                    
                    # ===== STEP 1: PROCESS FINANCIAL TRANSACTIONS FIRST =====
                    logger.info(f"💰 [{processing_type.upper()}] Processing financial transactions for {len(emails_for_parallel)} emails")
                    try:
                        # Call financial processing function directly (no API call needed)
                        from .financial_transaction_processor import process_financial_before_mem0
                        
                        financial_result = await process_financial_before_mem0(user_id, f"pre_mem0_{processing_type}")
                        
                        if financial_result.get("success", False):
                            transactions_found = financial_result.get('transactions_found', 0)
                            logger.info(f"✅ [{processing_type.upper()}] Financial processing completed: {transactions_found} transactions")
                        else:
                            logger.warning(f"⚠️ [{processing_type.upper()}] Financial processing failed: {financial_result.get('error', 'Unknown error')}")
                    except Exception as financial_error:
                        logger.error(f"❌ [{processing_type.upper()}] Financial processing error: {financial_error}")
                        # Continue with Mem0 upload even if financial processing fails
                    
                    # ===== STEP 2: UPLOAD TO MEM0 WITH FINANCIAL CONTEXT =====
                    logger.info(f"🧠 [{processing_type.upper()}] Starting Mem0 upload with financial context")
                    from .parallel_mem0_uploader import upload_emails_parallel_optimized
                    mem0_result = await upload_emails_parallel_optimized(user_id, emails_for_parallel)
                    
                    logger.info(f"⚡ [{processing_type.upper()}] Parallel Mem0 upload completed - Performance: ~10x faster!")
                    logger.info(f"✅ [{processing_type.upper()}] Results: {mem0_result.get('successful_uploads', 0)} successful, {mem0_result.get('failed_uploads', 0)} failed")
            
            return {
                "success": True,
                "status": "success",
                "emails_stored": stored_count,
                "promotional_filtered": len(emails) - len(filtered_emails),
                "financial_preserved": sum(1 for email in filtered_emails if email.get("financial", False)),
                "processing_type": processing_type,
                "total_count": len(emails)
            }
        else:
            logger.error(f"❌ [{processing_type.upper()}] Failed to store emails: {storage_result}")
            return {
                "success": False,
                "status": "error",
                "message": f"Failed to store emails: {storage_result.get('error', 'Unknown error')}",
                "processing_type": processing_type
            }
    
    except Exception as e:
        logger.error(f"❌ [{processing_type.upper()}] Error processing emails: {e}")
        return {
            "success": False,
            "status": "error", 
            "message": str(e),
            "processing_type": processing_type
        }
