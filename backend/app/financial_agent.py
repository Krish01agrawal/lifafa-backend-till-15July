"""
Gmail Financial Transactions Agent
==================================

This module provides enhanced financial transaction processing capabilities
that integrate with the existing Gmail Intelligence system.

Key Features:
- Advanced transaction filtering and detection
- Structured transaction data extraction
- 5-month historical data processing
- Comprehensive financial analytics
- Real-time transaction monitoring
- Visualization-ready APIs
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
import logging

# Core imports from existing system
from .mem0_agent_agno import EmailMessage
from .gmail import build_gmail_service
from .db import users_collection, emails_collection
from .models import GoogleToken

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ENHANCED DATA MODELS
# ============================================================================

class TransactionData(BaseModel):
    """Enhanced transaction data model"""
    id: str
    email_id: str
    user_id: str
    
    # Core transaction details
    date: Optional[datetime] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    
    # Transaction metadata
    transaction_type: str = "unknown"
    merchant: Optional[str] = None
    description: Optional[str] = None
    
    # Payment details
    payment_method: Optional[str] = None
    account_info: Optional[str] = None
    transaction_id: Optional[str] = None
    
    # Email source
    sender: str
    subject: str
    snippet: str
    
    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    confidence_score: Optional[float] = None

class FinancialSummary(BaseModel):
    """Financial summary for visualization"""
    user_id: str
    period: str
    total_transactions: int
    total_amount: float
    average_transaction: float
    category_breakdown: Dict[str, Any]
    merchant_breakdown: Dict[str, Any]
    monthly_trends: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.now)

# ============================================================================
# FINANCIAL TRANSACTION FILTER
# ============================================================================

class FinancialTransactionFilter:
    """Advanced financial email filtering"""
    
    CURRENCY_PATTERNS = [
        r'₹\s*[\d,]+\.?\d*',
        r'Rs\.?\s*[\d,]+\.?\d*',
        r'INR\s*[\d,]+\.?\d*',
        r'\$\s*[\d,]+\.?\d*',
        r'USD\s*[\d,]+\.?\d*',
    ]
    
    FINANCIAL_KEYWORDS = [
        'payment', 'paid', 'charged', 'debited', 'credited', 'transaction',
        'order', 'receipt', 'invoice', 'bill', 'upi', 'card', 'bank',
        'refund', 'cashback', 'purchase', 'spent', 'total', 'amount'
    ]
    
    FINANCIAL_SENDERS = [
        'hdfcbank', 'icici', 'sbi', 'axis', 'kotak', 'paytm', 'phonepe',
        'googlepay', 'amazon', 'flipkart', 'swiggy', 'zomato', 'uber'
    ]
    
    def is_financial_transaction(self, email: EmailMessage) -> Tuple[bool, float]:
        """
        Determine if email is a financial transaction
        Returns: (is_financial, confidence_score)
        """
        confidence = 0.0
        content = f"{email.subject} {email.snippet} {email.body}".lower()
        
        # Check for currency patterns (high confidence)
        for pattern in self.CURRENCY_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                confidence += 0.4
                break
        
        # Check for financial keywords
        keyword_matches = sum(1 for keyword in self.FINANCIAL_KEYWORDS if keyword in content)
        confidence += min(keyword_matches * 0.05, 0.3)
        
        # Check sender domain
        sender_lower = email.sender.lower()
        for sender in self.FINANCIAL_SENDERS:
            if sender in sender_lower:
                confidence += 0.3
                break
        
        return confidence >= 0.3, confidence

# ============================================================================
# TRANSACTION DATA EXTRACTOR
# ============================================================================

class TransactionExtractor:
    """Extract structured data from financial emails"""
    
    def __init__(self):
        self.amount_patterns = [
            r'(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)',
            r'(?:\$|USD)\s*([\d,]+\.?\d*)',
            r'(?:amount|total|paid|charged):\s*(?:₹|Rs\.?)\s*([\d,]+\.?\d*)',
        ]
        
        self.date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4})',
        ]
    
    def extract_transaction_data(self, email: EmailMessage, user_id: str) -> Optional[TransactionData]:
        """Extract transaction data from email"""
        try:
            content = f"{email.subject} {email.snippet} {email.body}"
            
            # Extract amount and currency
            amount, currency = self._extract_amount(content)
            
            # Extract date
            trans_date = self._extract_date(content, email.date)
            
            # Extract merchant
            merchant = self._extract_merchant(email)
            
            # Determine transaction type
            trans_type = self._determine_type(content)
            
            # Extract payment method
            payment_method = self._extract_payment_method(content)
            
            return TransactionData(
                id=f"{user_id}_{email.id}_{datetime.now().timestamp()}",
                email_id=email.id,
                user_id=user_id,
                date=trans_date,
                amount=amount,
                currency=currency,
                transaction_type=trans_type,
                merchant=merchant,
                description=email.subject,
                payment_method=payment_method,
                sender=email.sender,
                subject=email.subject,
                snippet=email.snippet,
                confidence_score=0.8
            )
            
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            return None
    
    def _extract_amount(self, content: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract amount and currency"""
        for pattern in self.amount_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    if '₹' in match.group(0) or 'Rs.' in match.group(0) or 'INR' in match.group(0):
                        return amount, 'INR'
                    elif '$' in match.group(0) or 'USD' in match.group(0):
                        return amount, 'USD'
                except ValueError:
                    continue
        return None, None
    
    def _extract_date(self, content: str, email_date: Optional[str]) -> Optional[datetime]:
        """Extract transaction date"""
        # Try to extract from content
        for pattern in self.date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    date_str = match.group(1)
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d %b %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except:
                    continue
        
        # Fallback to email date
        if email_date:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(email_date)
            except:
                pass
        
        return None
    
    def _extract_merchant(self, email: EmailMessage) -> Optional[str]:
        """Extract merchant name"""
        sender = email.sender.lower()
        subject = email.subject.lower()
        
        merchants = [
            'amazon', 'flipkart', 'swiggy', 'zomato', 'uber', 'ola',
            'paytm', 'phonepe', 'netflix', 'spotify', 'hdfc', 'icici'
        ]
        
        for merchant in merchants:
            if merchant in sender or merchant in subject:
                return merchant.title()
        
        # Extract from email domain
        if '@' in email.sender:
            domain = email.sender.split('@')[1].split('.')[0]
            return domain.title()
        
        return None
    
    def _determine_type(self, content: str) -> str:
        """Determine transaction type"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['debited', 'charged', 'paid', 'purchase']):
            return 'debit'
        elif any(word in content_lower for word in ['credited', 'refund', 'cashback']):
            return 'credit'
        else:
            return 'payment'
    
    def _extract_payment_method(self, content: str) -> Optional[str]:
        """Extract payment method"""
        content_lower = content.lower()
        
        if 'upi' in content_lower:
            return 'upi'
        elif any(card in content_lower for card in ['card', 'credit card', 'debit card']):
            return 'card'
        elif any(bank in content_lower for bank in ['bank', 'neft', 'rtgs']):
            return 'bank_transfer'
        else:
            return 'unknown'

# ============================================================================
# ENHANCED GMAIL FETCHER FOR 5 MONTHS
# ============================================================================

async def fetch_extended_financial_emails(access_token: str, refresh_token: str, user_id: str, months: int = 5) -> List[EmailMessage]:
    """Fetch extended Gmail history for financial analysis"""
    try:
        logger.info(f"Fetching {months} months of financial emails for user {user_id}")
        
        # Build Gmail service
        service = build_gmail_service(access_token, refresh_token)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        start_date_str = start_date.strftime('%Y/%m/%d')
        
        # Enhanced query for financial emails
        financial_query = f'after:{start_date_str} (from:@hdfcbank.net OR from:@icici OR from:@sbi OR from:@paytm OR from:@phonepe OR from:@amazon OR from:@flipkart OR from:@swiggy OR subject:payment OR subject:transaction OR subject:order OR subject:receipt OR ₹ OR Rs OR amount OR charged OR debited OR credited)'
        
        logger.info(f"Using financial query: {financial_query}")
        
        # Fetch messages with pagination
        all_messages = []
        page_token = None
        max_pages = 30
        
        for page in range(max_pages):
            logger.info(f"Fetching page {page + 1}/{max_pages}")
            
            request_params = {
                'userId': 'me',
                'maxResults': 500,
                'q': financial_query
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            results = service.users().messages().list(**request_params).execute()
            messages = results.get('messages', [])
            
            if not messages:
                break
            
            all_messages.extend(messages)
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        
        logger.info(f"Found {len(all_messages)} potential financial messages")
        
        # Process messages to extract email content
        emails = []
        filter_engine = FinancialTransactionFilter()
        
        for i, msg in enumerate(all_messages):
            try:
                if i % 100 == 0:
                    logger.info(f"Processing message {i+1}/{len(all_messages)}")
                
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                payload = message['payload']
                headers = payload.get('headers', [])
                
                # Extract email details
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                snippet = message.get('snippet', '')
                
                # Extract body
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain' and part.get('body', {}).get('data'):
                            import base64
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                else:
                    if payload.get('body') and payload['body'].get('data'):
                        import base64
                        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                
                email = EmailMessage(
                    id=msg['id'],
                    subject=subject,
                    sender=sender,
                    snippet=snippet,
                    body=body,
                    date=date
                )
                
                # Filter for financial transactions
                is_financial, confidence = filter_engine.is_financial_transaction(email)
                if is_financial:
                    emails.append(email)
                
            except Exception as e:
                logger.warning(f"Error processing message {i+1}: {e}")
                continue
        
        logger.info(f"Extracted {len(emails)} financial transaction emails")
        return emails
        
    except Exception as e:
        logger.error(f"Error fetching extended financial emails: {e}")
        return []

# ============================================================================
# FINANCIAL ANALYTICS ENGINE
# ============================================================================

class FinancialAnalytics:
    """Generate comprehensive financial analytics"""
    
    def generate_financial_summary(self, user_id: str, transactions: List[TransactionData]) -> FinancialSummary:
        """Generate financial summary for user"""
        try:
            total_transactions = len(transactions)
            total_amount = sum(t.amount for t in transactions if t.amount)
            avg_transaction = total_amount / total_transactions if total_transactions > 0 else 0
            
            # Category breakdown
            categories = {}
            for t in transactions:
                if t.payment_method:
                    categories[t.payment_method] = categories.get(t.payment_method, 0) + (t.amount or 0)
            
            # Merchant breakdown
            merchants = {}
            for t in transactions:
                if t.merchant:
                    merchants[t.merchant] = merchants.get(t.merchant, 0) + (t.amount or 0)
            
            # Monthly trends
            monthly = {}
            for t in transactions:
                if t.date and t.amount:
                    month = t.date.strftime('%Y-%m')
                    monthly[month] = monthly.get(month, 0) + t.amount
            
            return FinancialSummary(
                user_id=user_id,
                period="5_months",
                total_transactions=total_transactions,
                total_amount=total_amount,
                average_transaction=avg_transaction,
                category_breakdown=categories,
                merchant_breakdown=merchants,
                monthly_trends=monthly
            )
            
        except Exception as e:
            logger.error(f"Error generating financial summary: {e}")
            raise

# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

async def process_financial_transactions_for_user(user_id: str, access_token: str, refresh_token: str) -> Dict[str, Any]:
    """Main function to process financial transactions for a user"""
    try:
        logger.info(f"Starting financial transaction processing for user {user_id}")
        
        # Fetch extended financial email history
        emails = await fetch_extended_financial_emails(access_token, refresh_token, user_id, months=5)
        
        # Extract transaction data
        extractor = TransactionExtractor()
        transactions = []
        
        for email in emails:
            transaction = extractor.extract_transaction_data(email, user_id)
            if transaction:
                transactions.append(transaction)
        
        logger.info(f"Extracted {len(transactions)} financial transactions")
        
        # Generate analytics
        analytics = FinancialAnalytics()
        summary = analytics.generate_financial_summary(user_id, transactions)
        
        # Store in MongoDB
        await store_financial_data(user_id, transactions, summary)
        
        # Update user status
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "financial_analysis_completed": True,
                "financial_transactions_count": len(transactions),
                "financial_analysis_date": datetime.now().isoformat()
            }}
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "transactions_found": len(transactions),
            "total_amount": summary.total_amount,
            "period": "5_months",
            "summary": summary.dict()
        }
        
    except Exception as e:
        logger.error(f"Error processing financial transactions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

async def store_financial_data(user_id: str, transactions: List[TransactionData], summary: FinancialSummary):
    """Store financial data in MongoDB"""
    try:
        # Create financial_transactions collection
        financial_collection = emails_collection.database["financial_transactions"]
        
        # Store transactions
        if transactions:
            # Convert to dict for MongoDB
            transaction_dicts = [t.dict() for t in transactions]
            
            # Remove existing data for user
            await financial_collection.delete_many({"user_id": user_id})
            
            # Insert new data
            await financial_collection.insert_many(transaction_dicts)
        
        # Store summary
        summary_collection = emails_collection.database["financial_summaries"]
        await summary_collection.delete_many({"user_id": user_id})
        await summary_collection.insert_one(summary.dict())
        
        logger.info(f"Stored {len(transactions)} transactions and summary for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error storing financial data: {e}")
        raise

# ============================================================================
# API ENDPOINTS FOR FINANCIAL DATA
# ============================================================================

async def get_financial_summary(user_id: str) -> Optional[Dict[str, Any]]:
    """Get financial summary for user"""
    try:
        summary_collection = emails_collection.database["financial_summaries"]
        summary = await summary_collection.find_one({"user_id": user_id})
        
        if summary:
            # Remove MongoDB _id field
            summary.pop('_id', None)
            return summary
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving financial summary: {e}")
        return None

async def get_financial_transactions(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get financial transactions for user"""
    try:
        financial_collection = emails_collection.database["financial_transactions"]
        cursor = financial_collection.find({"user_id": user_id}).limit(limit)
        
        transactions = []
        async for transaction in cursor:
            transaction.pop('_id', None)  # Remove MongoDB _id
            transactions.append(transaction)
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error retrieving financial transactions: {e}")
        return []

logger.info("🔥 Financial Transaction Agent loaded successfully!")
logger.info("📊 Features: Enhanced filtering, 5-month history, structured extraction, comprehensive analytics") 