"""
Enhanced Gmail Financial Transactions Extraction and Analysis System
====================================================================

This module extends the existing Agno Gmail Intelligence system with advanced
financial transaction processing capabilities as specified in the requirements.

Features:
- Advanced transaction filtering (5+ months historical data)
- Structured transaction data extraction with complete schemas
- Real-time transaction monitoring
- Comprehensive financial analytics and insights
- Visualization-ready JSON APIs
- MongoDB storage optimization for financial data

Integration with existing system:
- Extends mem0_agent_agno.py functionality
- Uses existing OAuth and Gmail API infrastructure
- Leverages Agno agents for intelligent processing
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass
import logging
import uuid
import hashlib

# Core imports from existing system
from app.mem0_agent_agno import EmailMessage, upload_emails_to_mem0, query_mem0
from app.gmail import build_gmail_service, fetch_emails
from app.db import users_collection, emails_collection

# Agno Framework
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.python import PythonTools

# ============================================================================
# ENHANCED DATA MODELS FOR FINANCIAL TRANSACTIONS
# ============================================================================

class TransactionData(BaseModel):
    """Complete comprehensive financial transaction data schema with maximum possible fields"""
    
    # ============================================================================
    # CORE IDENTIFIERS
    # ============================================================================
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fintransaction_id: str  # Unique financial transaction ID for deduplication
    transaction_hash: str = ""  # SHA-256 hash for duplicate detection
    reference_number: Optional[str] = None  # Bank/merchant reference
    transaction_reference_id: Optional[str] = None  # External reference ID
    order_id: Optional[str] = None  # E-commerce order ID
    invoice_number: Optional[str] = None  # Invoice/bill number
    
    # ============================================================================
    # CORE TRANSACTION DETAILS
    # ============================================================================
    date_time: Optional[datetime] = None  # Exact transaction timestamp
    receiver: Optional[str] = None  # Who received the payment
    amount: Optional[float] = None  # Transaction amount
    currency: Optional[str] = "INR"  # Currency code
    exchange_rate: Optional[float] = None  # For international transactions
    tax_amount: Optional[float] = None  # Tax component
    processing_fee: Optional[float] = None  # Processing fees
    cashback_amount: Optional[float] = None  # Cashback earned
    rewards_earned: Optional[float] = None  # Reward points earned
    balance_after_transaction: Optional[float] = None  # Account balance after transaction
    
    # ============================================================================
    # PAYMENT DETAILS
    # ============================================================================
    medium: Optional[str] = None  # upi, bank_transfer, credit_card, debit_card, wallet, cash, net_banking
    bank_account: Optional[str] = None  # Account used for transaction (masked)
    source: Optional[str] = None  # UPI ID, bank account, credit card details (masked)
    to: Optional[str] = None  # Destination account/UPI ID
    to_account: Optional[str] = None  # Destination account details
    transaction_type: Optional[str] = None  # debit, credit, refund, reversal, transfer
    transaction_status: Optional[str] = None  # completed, pending, failed, cancelled, processing
    transaction_channel: Optional[str] = None  # online, offline, mobile, atm, pos, web
    device_used: Optional[str] = None  # mobile, web, atm, pos_terminal, phone
    authentication_method: Optional[str] = None  # pin, biometric, otp, signature, contactless
    
    # ============================================================================
    # MERCHANT & BUSINESS DETAILS
    # ============================================================================
    merchant_name: Optional[str] = None  # Clean merchant name
    merchant_category_code: Optional[str] = None  # MCC code
    merchant_type: Optional[str] = None  # e-commerce, retail, service, restaurant, fuel, etc.
    merchant_details: Optional[Dict[str, Any]] = Field(default_factory=dict)  # address, phone, website
    business_category: Optional[str] = None  # Primary business category
    
    # ============================================================================
    # CATEGORIZATION & METADATA
    # ============================================================================
    metadata: Optional[str] = None  # Primary category: food, entertainment, utility, lifestyle, investment, shopping, etc.
    category_details: Dict[str, Any] = Field(default_factory=dict)  # Additional category info
    subcategory: Optional[str] = None  # Detailed subcategory
    spending_category: Optional[str] = None  # Personal finance category
    tags: List[str] = Field(default_factory=list)  # User-defined tags
    custom_category: Optional[str] = None  # User-defined category
    
    # ============================================================================
    # SUBSCRIPTION & RECURRING DETAILS
    # ============================================================================
    is_subscription: bool = False
    subscription_receiver: Optional[Dict[str, Any]] = None  # {brand_icon, brand_name, description, frequency}
    recurring_transaction_id: Optional[str] = None  # Link to recurring series
    subscription_type: Optional[str] = None  # monthly, yearly, weekly, daily
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    installment_info: Optional[Dict[str, Any]] = None  # EMI details
    parent_transaction_id: Optional[str] = None  # For refunds/reversals
    
    # ============================================================================
    # LOCATION & CONTEXT
    # ============================================================================
    location: Optional[str] = None  # Transaction location
    geolocation: Optional[Dict[str, float]] = None  # {lat, lng}
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    
    # ============================================================================
    # PROMOTIONAL & LOYALTY
    # ============================================================================
    promotion_code_used: Optional[str] = None  # Discount/promo code
    loyalty_program_info: Optional[Dict[str, Any]] = None  # Loyalty details
    discount_amount: Optional[float] = None  # Discount applied
    coupon_code: Optional[str] = None  # Coupon used
    offer_details: Optional[str] = None  # Special offer info
    
    # ============================================================================
    # RISK & SECURITY
    # ============================================================================
    risk_score: Optional[float] = None  # Fraud detection score (0-1)
    anomaly_score: Optional[float] = None  # Anomaly detection score
    verification_status: Optional[str] = None  # verified, unverified, pending
    security_flags: List[str] = Field(default_factory=list)  # Security alerts
    
    # ============================================================================
    # ANALYTICS & INSIGHTS
    # ============================================================================
    similar_transaction_count: Optional[int] = None  # Count of similar transactions
    frequency_pattern: Optional[str] = None  # daily, weekly, monthly, occasional
    seasonal_indicator: Optional[str] = None  # seasonal spending pattern
    spending_category_percentage: Optional[float] = None  # % of total spending
    budget_impact: Optional[Dict[str, Any]] = None  # Impact on budget categories
    trend_indicator: Optional[str] = None  # increasing, decreasing, stable
    
    # ============================================================================
    # EMAIL SOURCE INFORMATION
    # ============================================================================
    source_emails: List[str] = Field(default_factory=list)  # List of email IDs that reference this transaction
    email_types: List[str] = Field(default_factory=list)  # confirmation, receipt, notification, etc.
    user_id: str
    sender_email: str
    subject: str
    snippet: str
    transaction_description: Optional[str] = None  # Full description from email
    email_confidence_score: Optional[float] = None  # Confidence in email extraction
    
    # ============================================================================
    # USER ANNOTATIONS
    # ============================================================================
    notes: Optional[str] = None  # User notes
    user_rating: Optional[int] = None  # User rating (1-5)
    user_category: Optional[str] = None  # User-assigned category
    is_favorite: bool = False  # User marked as favorite
    is_hidden: bool = False  # User marked as hidden
    is_important: bool = False  # User marked as important
    user_tags: List[str] = Field(default_factory=list)  # User-defined tags
    
    # ============================================================================
    # PROCESSING METADATA
    # ============================================================================
    extracted_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    confidence_score: Optional[float] = None  # Overall extraction confidence
    processing_version: str = "4.0_comprehensive"
    extraction_method: Optional[str] = None  # email, api, manual, import
    data_source: str = "email"  # email, bank_api, manual, csv_import
    validation_status: Optional[str] = None  # validated, needs_review, auto_processed
    
    # ============================================================================
    # DUPLICATE DETECTION
    # ============================================================================
    duplicate_sources: List[str] = Field(default_factory=list)  # Sources that were merged
    duplicate_count: int = 1  # Number of duplicate sources found
    is_duplicate: bool = False  # Marked as duplicate
    original_transaction_id: Optional[str] = None  # Reference to original if duplicate
    merge_timestamp: Optional[datetime] = None  # When duplicates were merged
    
    def generate_transaction_id(self) -> str:
        """Generate unique transaction ID based on receiver, amount, and date"""
        if not self.receiver or not self.amount or not self.date_time:
            return str(uuid.uuid4())[:12]
        
        key_data = f"{self.receiver}_{self.amount}_{self.date_time.strftime('%Y%m%d%H%M')}"
        return hashlib.md5(key_data.encode()).hexdigest()[:12]
    
    def generate_transaction_hash(self) -> str:
        """Generate SHA-256 hash for duplicate detection"""
        hash_data = f"{self.receiver}_{self.amount}_{self.date_time.strftime('%Y%m%d%H%M') if self.date_time else 'unknown'}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]
    
    def is_duplicate_of(self, other_transaction: 'TransactionData') -> bool:
        """Check if this transaction is a duplicate of another"""
        return (
            self.receiver == other_transaction.receiver and
            self.amount == other_transaction.amount and
            self.date_time == other_transaction.date_time and
            abs((self.date_time - other_transaction.date_time).total_seconds()) < 3600  # Within 1 hour
        )
    
    def merge_with_duplicate(self, duplicate_transaction: 'TransactionData'):
        """Merge another transaction as a duplicate source"""
        if duplicate_transaction.source_emails:
            self.source_emails.extend(duplicate_transaction.source_emails)
        if duplicate_transaction.email_types:
            self.email_types.extend(duplicate_transaction.email_types)
        
        self.duplicate_sources.append(duplicate_transaction.fintransaction_id)
        self.duplicate_count += 1
        self.merge_timestamp = datetime.now()
        
        # Update confidence score based on multiple sources
        if self.confidence_score and duplicate_transaction.confidence_score:
            self.confidence_score = max(self.confidence_score, duplicate_transaction.confidence_score)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FinancialInsight(BaseModel):
    """Financial insights and analytics"""
    user_id: str
    period: str  # "monthly", "weekly", "5_months"
    
    # Summary statistics
    total_transactions: int
    total_amount: float
    average_transaction: float
    
    # Breakdowns
    category_breakdown: Dict[str, Any]
    merchant_breakdown: Dict[str, Any]
    payment_method_breakdown: Dict[str, Any]
    monthly_trends: Dict[str, Any]
    
    # Insights
    top_merchants: List[Dict[str, Any]]
    spending_patterns: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    
    generated_at: datetime = Field(default_factory=datetime.now)

# ============================================================================
# ADVANCED FINANCIAL TRANSACTION FILTERING
# ============================================================================

class FinancialTransactionFilter:
    """Advanced filtering for financial transaction emails"""
    
    # Enhanced financial keywords and patterns
    CURRENCY_PATTERNS = [
        r'₹\s*[\d,]+\.?\d*',          # Indian Rupee: ₹1,000.00
        r'Rs\.?\s*[\d,]+\.?\d*',      # Rupees: Rs. 1000
        r'INR\s*[\d,]+\.?\d*',        # INR 1000
        r'\$\s*[\d,]+\.?\d*',         # USD: $100.50
        r'USD\s*[\d,]+\.?\d*',        # USD 100
        r'€\s*[\d,]+\.?\d*',          # Euro: €50.00
        r'£\s*[\d,]+\.?\d*',          # Pound: £75.25
    ]
    
    TRANSACTION_KEYWORDS = [
        # Payment keywords
        'payment', 'paid', 'charged', 'debited', 'credited', 'transferred',
        'transaction', 'spent', 'purchase', 'order', 'receipt', 'invoice',
        'bill', 'amount', 'total', 'subtotal', 'refund', 'cashback',
        
        # UPI specific
        'upi', 'paytm', 'phonepe', 'googlepay', 'bharatpe', 'mobikwik',
        'payu', 'razorpay', 'cashfree', 'instamojo',
        
        # Banking terms
        'bank', 'account', 'card', 'atm', 'neft', 'rtgs', 'imps',
        'autopay', 'standing instruction', 'emi', 'loan',
        
        # E-commerce and services
        'order placed', 'order confirmed', 'delivery charge', 'service charge',
        'subscription', 'renewal', 'upgrade', 'premium',
    ]
    
    FINANCIAL_DOMAINS = [
        # Indian Banks
        '@hdfcbank.net', '@icicicbank.com', '@sbi.co.in', '@axisbank.com',
        '@kotak.com', '@indusind.com', '@yesbank.in', '@pnb.co.in',
        
        # Payment Gateways
        '@paytm.com', '@phonepe.com', '@googlepay.com', '@amazon.in',
        '@flipkart.com', '@swiggy.in', '@zomato.com', '@uber.com',
        '@ola.com', '@makemytrip.com', '@bookmyshow.com',
        
        # Credit Cards
        '@americanexpress.com', '@citibank.com', '@sc.com',
        
        # Wallets and Fintech
        '@mobikwik.com', '@payu.in', '@razorpay.com', '@cashfree.com',
        '@bharatpe.com', '@cred.club', '@slice.it',
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def is_financial_email(self, email: EmailMessage) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Advanced financial email detection with confidence scoring
        Returns: (is_financial, confidence_score, detection_details)
        """
        confidence_score = 0.0
        detection_details = {
            'currency_found': False,
            'keywords_found': [],
            'domain_match': False,
            'amount_extracted': None,
            'reasoning': []
        }
        
        content = f"{email.subject} {email.snippet} {email.body}".lower()
        
        # Check for currency patterns (high confidence)
        for pattern in self.CURRENCY_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                confidence_score += 0.4
                detection_details['currency_found'] = True
                match = re.search(pattern, content, re.IGNORECASE)
                detection_details['amount_extracted'] = match.group() if match else None
                detection_details['reasoning'].append(f"Currency pattern found: {pattern}")
                break
        
        # Check for financial keywords
        found_keywords = []
        for keyword in self.TRANSACTION_KEYWORDS:
            if keyword in content:
                found_keywords.append(keyword)
                confidence_score += 0.05  # Each keyword adds small confidence
        
        if found_keywords:
            detection_details['keywords_found'] = found_keywords[:5]  # Top 5
            detection_details['reasoning'].append(f"Financial keywords: {', '.join(found_keywords[:3])}")
        
        # Check sender domain (medium confidence)
        sender_lower = email.sender.lower()
        for domain in self.FINANCIAL_DOMAINS:
            if domain in sender_lower:
                confidence_score += 0.3
                detection_details['domain_match'] = True
                detection_details['reasoning'].append(f"Known financial domain: {domain}")
                break
        
        # Subject line analysis (additional confidence)
        subject_lower = email.subject.lower()
        transaction_subjects = [
            'payment', 'transaction', 'order', 'receipt', 'invoice',
            'charged', 'debited', 'credited', 'refund', 'cashback'
        ]
        
        for subj_keyword in transaction_subjects:
            if subj_keyword in subject_lower:
                confidence_score += 0.1
                detection_details['reasoning'].append(f"Transaction subject: {subj_keyword}")
                break
        
        # Final confidence normalization
        confidence_score = min(confidence_score, 1.0)
        is_financial = confidence_score >= 0.3  # Threshold for financial classification
        
        return is_financial, confidence_score, detection_details

# ============================================================================
# TRANSACTION DATA EXTRACTION ENGINE
# ============================================================================

class TransactionExtractor:
    """Extract structured transaction data from financial emails"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Enhanced extraction patterns
        self.amount_patterns = [
            r'(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)',
            r'(?:\$|USD)\s*([\d,]+\.?\d*)',
            r'(?:€|EUR)\s*([\d,]+\.?\d*)',
            r'(?:£|GBP)\s*([\d,]+\.?\d*)',
            r'(?:amount|total|paid|charged):\s*(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)',
        ]
        
        self.date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4})',
            r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        
        self.transaction_id_patterns = [
            r'(?:transaction id|txn id|ref no|reference|order id)[:\s]*([A-Z0-9]+)',
            r'(?:utr|rrn)[:\s]*([A-Z0-9]+)',
        ]
    
    async def extract_transaction_data(self, email: EmailMessage, user_id: str) -> Optional[TransactionData]:
        """Extract complete transaction data from email"""
        try:
            content = f"{email.subject} {email.snippet} {email.body}"
            
            # Extract amount and currency
            amount, currency = self._extract_amount_and_currency(content)
            
            # Extract transaction date
            transaction_date = self._extract_transaction_date(content, email.date)
            
            # Extract merchant/payee
            merchant = self._extract_merchant(email)
            
            # Determine transaction type
            transaction_type = self._determine_transaction_type(content)
            
            # Extract payment method
            payment_method = self._extract_payment_method(content)
            
            # Extract transaction ID
            transaction_id = self._extract_transaction_id(content)
            
            # Extract account information
            account_info = self._extract_account_info(content)
            
            # Create transaction record
            transaction = TransactionData(
                id=f"{user_id}_{email.id}_{datetime.now().timestamp()}",
                email_id=email.id,
                user_id=user_id,
                date_time=transaction_date,
                amount=amount,
                currency=currency,
                medium=transaction_type,
                bank_account=account_info,
                source=transaction_id,
                to_account=transaction_id,
                metadata=merchant,
                category_details={'merchant': merchant},
                sender_email=email.sender,
                subject=email.subject,
                snippet=email.snippet,
                confidence_score=0.8,  # TODO: Calculate based on extraction quality
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error extracting transaction data: {e}")
            return None
    
    def _extract_amount_and_currency(self, content: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract amount and currency from content"""
        for pattern in self.amount_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Determine currency from pattern
                    if '₹' in match.group(0) or 'Rs.' in match.group(0) or 'INR' in match.group(0):
                        return amount, 'INR'
                    elif '$' in match.group(0) or 'USD' in match.group(0):
                        return amount, 'USD'
                    elif '€' in match.group(0) or 'EUR' in match.group(0):
                        return amount, 'EUR'
                    elif '£' in match.group(0) or 'GBP' in match.group(0):
                        return amount, 'GBP'
                except ValueError:
                    continue
        return None, None
    
    def _extract_transaction_date(self, content: str, email_date: Optional[str]) -> Optional[datetime]:
        """Extract transaction date from content or use email date"""
        # Try to extract from content first
        for pattern in self.date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    date_str = match.group(1)
                    # Try different date formats
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %b %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except:
                    continue
        
        # Fallback to email date
        if email_date:
            try:
                # Parse Gmail date format
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(email_date)
            except:
                pass
        
        return None
    
    def _extract_merchant(self, email: EmailMessage) -> Optional[str]:
        """Extract merchant/payee information"""
        # Simple merchant extraction from sender or subject
        sender = email.sender.lower()
        subject = email.subject.lower()
        
        # Common merchant patterns
        merchant_indicators = [
            'amazon', 'flipkart', 'swiggy', 'zomato', 'uber', 'ola',
            'paytm', 'phonepe', 'googlepay', 'netflix', 'spotify',
            'hdfc', 'icici', 'sbi', 'axis', 'kotak'
        ]
        
        for indicator in merchant_indicators:
            if indicator in sender or indicator in subject:
                return indicator.title()
        
        # Extract from email domain
        if '@' in email.sender:
            domain = email.sender.split('@')[1].split('.')[0]
            return domain.title()
        
        return None
    
    def _determine_transaction_type(self, content: str) -> str:
        """Determine if transaction is debit, credit, payment, etc."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['debited', 'charged', 'paid', 'spent', 'purchase']):
            return 'debit'
        elif any(word in content_lower for word in ['credited', 'received', 'refund', 'cashback']):
            return 'credit'
        elif any(word in content_lower for word in ['transfer', 'sent']):
            return 'transfer'
        else:
            return 'payment'  # Default
    
    def _extract_payment_method(self, content: str) -> Optional[str]:
        """Extract payment method from content"""
        content_lower = content.lower()
        
        if any(upi in content_lower for upi in ['upi', 'unified payments']):
            return 'upi'
        elif any(card in content_lower for card in ['card', 'credit card', 'debit card']):
            return 'card'
        elif any(bank in content_lower for bank in ['bank transfer', 'neft', 'rtgs', 'imps']):
            return 'bank_transfer'
        elif any(wallet in content_lower for wallet in ['wallet', 'paytm wallet', 'phonepe wallet']):
            return 'wallet'
        else:
            return 'unknown'
    
    def _extract_transaction_id(self, content: str) -> Optional[str]:
        """Extract transaction ID from content"""
        for pattern in self.transaction_id_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_account_info(self, content: str) -> Optional[str]:
        """Extract account or card information (last 4 digits, etc.)"""
        # Pattern for last 4 digits of card/account
        pattern = r'(?:ending|last|card)\s*(?:with|in)?\s*\*+(\d{4})'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return f"****{match.group(1)}"
        return None

# ============================================================================
# EXTENDED HISTORICAL DATA FETCHING (5 MONTHS)
# ============================================================================

async def fetch_extended_gmail_history(access_token: str, refresh_token: str, user_id: str, months: int = 5) -> List[EmailMessage]:
    """
    Fetch extended Gmail history for the specified number of months
    Enhanced version of existing fetch_emails function
    """
    try:
        print(f"📧 Fetching {months} months of Gmail history for user {user_id}")
        
        # Build Gmail service
        service = build_gmail_service(access_token, refresh_token)
        
        # Calculate date range for extended history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)  # Approximate months to days
        
        # Format dates for Gmail query
        start_date_str = start_date.strftime('%Y/%m/%d')
        query_filter = f'after:{start_date_str}'
        
        print(f"🔍 Query filter: {query_filter} (from {start_date_str} to now)")
        
        # Enhanced pagination for larger datasets
        all_messages = []
        page_token = None
        page_count = 0
        max_pages = 50  # Increased for 5 months of data
        
        while page_count < max_pages:
            page_count += 1
            print(f"📄 Fetching page {page_count}... (current total: {len(all_messages)})")
            
            request_params = {
                'userId': 'me',
                'maxResults': 500,  # Gmail's maximum
                'q': query_filter
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            results = service.users().messages().list(**request_params).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("📄 No more messages found.")
                break
            
            all_messages.extend(messages)
            print(f"✅ Page {page_count} fetched: {len(messages)} messages (total: {len(all_messages)})")
            
            page_token = results.get('nextPageToken')
            if not page_token:
                print("📄 No more pages available.")
                break
        
        print(f"📊 Total messages found: {len(all_messages)}")
        
        # Fetch detailed content for each message
        emails = []
        for i, msg in enumerate(all_messages):
            try:
                if i % 200 == 0:
                    print(f"📧 Processing message {i+1}/{len(all_messages)}...")
                
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                payload = message['payload']
                headers = payload.get('headers', [])
                
                # Extract email details
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                snippet = message.get('snippet', '')
                
                # Extract body content
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain' and part.get('body', {}).get('data'):
                            import base64
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                        elif part['mimeType'] == 'text/html' and part.get('body', {}).get('data'):
                            import base64
                            raw_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            # Use existing clean_html function
                            from app.gmail import clean_html
                            body = clean_html(raw_html)
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
                emails.append(email)
                
            except Exception as e:
                print(f"⚠️ Error processing message {i+1}: {str(e)}")
                continue
        
        print(f"✅ Extended Gmail history fetch completed: {len(emails)} emails from {months} months")
        return emails
        
    except Exception as e:
        print(f"❌ Error fetching extended Gmail history: {e}")
        return []

# ============================================================================
# FINANCIAL ANALYTICS ENGINE
# ============================================================================

class FinancialAnalytics:
    """Advanced financial analytics and insights generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_comprehensive_insights(self, user_id: str, transactions: List[TransactionData]) -> FinancialInsight:
        """Generate comprehensive financial insights from transactions"""
        try:
            print(f"📊 Generating financial insights for {len(transactions)} transactions")
            
            # Basic statistics
            total_transactions = len(transactions)
            total_amount = sum(t.amount for t in transactions if t.amount)
            average_transaction = total_amount / total_transactions if total_transactions > 0 else 0
            
            # Category breakdown
            category_breakdown = self._analyze_categories(transactions)
            
            # Merchant breakdown
            merchant_breakdown = self._analyze_merchants(transactions)
            
            # Payment method breakdown
            payment_method_breakdown = self._analyze_payment_methods(transactions)
            
            # Monthly trends
            monthly_trends = self._analyze_monthly_trends(transactions)
            
            # Top merchants
            top_merchants = self._get_top_merchants(transactions, limit=10)
            
            # Spending patterns
            spending_patterns = self._analyze_spending_patterns(transactions)
            
            # Anomaly detection
            anomalies = self._detect_anomalies(transactions)
            
            insight = FinancialInsight(
                user_id=user_id,
                period="5_months",
                total_transactions=total_transactions,
                total_amount=total_amount,
                average_transaction=average_transaction,
                category_breakdown=category_breakdown,
                merchant_breakdown=merchant_breakdown,
                payment_method_breakdown=payment_method_breakdown,
                monthly_trends=monthly_trends,
                top_merchants=top_merchants,
                spending_patterns=spending_patterns,
                anomalies=anomalies
            )
            
            return insight
            
        except Exception as e:
            self.logger.error(f"Error generating financial insights: {e}")
            raise
    
    def _analyze_categories(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """Analyze spending by category"""
        categories = {}
        for transaction in transactions:
            if transaction.amount and transaction.category_details.get('merchant'):
                category = transaction.category_details['merchant']
                if category not in categories:
                    categories[category] = {'count': 0, 'amount': 0.0}
                categories[category]['count'] += 1
                categories[category]['amount'] += transaction.amount
        
        # Calculate percentages
        total_amount = sum(cat['amount'] for cat in categories.values())
        for category in categories:
            categories[category]['percentage'] = (categories[category]['amount'] / total_amount * 100) if total_amount > 0 else 0
        
        return categories
    
    def _analyze_merchants(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """Analyze spending by merchant"""
        merchants = {}
        for transaction in transactions:
            if transaction.amount and transaction.category_details.get('merchant'):
                merchant = transaction.category_details['merchant']
                if merchant not in merchants:
                    merchants[merchant] = {'count': 0, 'amount': 0.0}
                merchants[merchant]['count'] += 1
                merchants[merchant]['amount'] += transaction.amount
        
        return merchants
    
    def _analyze_payment_methods(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """Analyze usage by payment method"""
        methods = {}
        for transaction in transactions:
            if transaction.medium:
                method = transaction.medium
                if method not in methods:
                    methods[method] = {'count': 0, 'amount': 0.0}
                methods[method]['count'] += 1
                if transaction.amount:
                    methods[method]['amount'] += transaction.amount
        
        return methods
    
    def _analyze_monthly_trends(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """Analyze spending trends by month"""
        monthly_data = {}
        for transaction in transactions:
            if transaction.date_time and transaction.amount:
                month_key = transaction.date_time.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'count': 0, 'amount': 0.0}
                monthly_data[month_key]['count'] += 1
                monthly_data[month_key]['amount'] += transaction.amount
        
        return monthly_data
    
    def _get_top_merchants(self, transactions: List[TransactionData], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top merchants by spending"""
        merchant_totals = {}
        for transaction in transactions:
            if transaction.amount and transaction.category_details.get('merchant'):
                merchant = transaction.category_details['merchant']
                if merchant not in merchant_totals:
                    merchant_totals[merchant] = 0.0
                merchant_totals[merchant] += transaction.amount
        
        # Sort by amount and return top merchants
        sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)
        return [{'merchant': merchant, 'amount': amount} for merchant, amount in sorted_merchants[:limit]]
    
    def _analyze_spending_patterns(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """Analyze spending patterns and behaviors"""
        patterns = {
            'avg_transaction_size': 0.0,
            'most_frequent_category': None,
            'most_expensive_category': None,
            'spending_consistency': 'variable',
            'digital_payment_preference': 0.0
        }
        
        if not transactions:
            return patterns
        
        # Average transaction size
        amounts = [t.amount for t in transactions if t.amount]
        if amounts:
            patterns['avg_transaction_size'] = sum(amounts) / len(amounts)
        
        # Most frequent category
        category_counts = {}
        category_amounts = {}
        digital_payments = 0
        
        for transaction in transactions:
            if transaction.category_details.get('merchant'):
                category = transaction.category_details['merchant']
                category_counts[category] = category_counts.get(category, 0) + 1
                if transaction.amount:
                    category_amounts[category] = category_amounts.get(category, 0) + transaction.amount
            
            # Count digital payments
            if transaction.medium in ['upi', 'card', 'wallet']:
                digital_payments += 1
        
        if category_counts:
            patterns['most_frequent_category'] = max(category_counts, key=category_counts.get)
        
        if category_amounts:
            patterns['most_expensive_category'] = max(category_amounts, key=category_amounts.get)
        
        # Digital payment preference
        patterns['digital_payment_preference'] = (digital_payments / len(transactions) * 100) if transactions else 0
        
        return patterns
    
    def _detect_anomalies(self, transactions: List[TransactionData]) -> List[Dict[str, Any]]:
        """Simple anomaly detection for unusual transactions"""
        anomalies = []
        
        if not transactions:
            return anomalies
        
        # Calculate average transaction amount
        amounts = [t.amount for t in transactions if t.amount]
        if not amounts:
            return anomalies
        
        avg_amount = sum(amounts) / len(amounts)
        std_amount = (sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)) ** 0.5
        
        # Detect unusually high transactions (3 standard deviations above mean)
        threshold = avg_amount + (3 * std_amount)
        
        for transaction in transactions:
            if transaction.amount and transaction.amount > threshold:
                anomalies.append({
                    'type': 'high_amount',
                    'transaction_id': transaction.fintransaction_id,
                    'amount': transaction.amount,
                    'merchant': transaction.category_details.get('merchant'),
                    'date': transaction.date_time.isoformat() if transaction.date_time else None,
                    'reason': f'Amount {transaction.amount} is {((transaction.amount / avg_amount) - 1) * 100:.1f}% above average'
                })
        
        return anomalies[:10]  # Return top 10 anomalies

class FinancialTransactionProcessor:
    """Enhanced processor with deduplication and comprehensive data extraction"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.transactions_cache = {}  # For deduplication
        
        # Enhanced merchant patterns
        self.merchant_patterns = {
            'sbi': 'SBI Bank',
            'icici': 'ICICI Bank', 
            'hdfc': 'HDFC Bank',
            'axis': 'Axis Bank',
            'paytm': 'Paytm',
            'phonepe': 'PhonePe',
            'googlepay': 'Google Pay',
            'swiggy': 'Swiggy',
            'zomato': 'Zomato',
            'uber': 'Uber',
            'ola': 'Ola',
            'amazon': 'Amazon',
            'flipkart': 'Flipkart',
            'netflix': 'Netflix',
            'spotify': 'Spotify',
            'bookmyshow': 'BookMyShow',
            'mutual fund': 'Investment - Mutual Fund',
            'irctc': 'IRCTC',
            'electricity': 'Utility - Electricity',
            'gas': 'Utility - Gas',
            'water': 'Utility - Water',
            'mobile': 'Utility - Mobile',
            'broadband': 'Utility - Internet'
        }
        
        # Subscription detection patterns
        self.subscription_patterns = {
            'netflix': {'icon': '🎬', 'name': 'Netflix', 'description': 'Video Streaming', 'frequency': 'monthly'},
            'spotify': {'icon': '🎵', 'name': 'Spotify', 'description': 'Music Streaming', 'frequency': 'monthly'},
            'amazon prime': {'icon': '📦', 'name': 'Amazon Prime', 'description': 'Shopping & Video', 'frequency': 'yearly'},
            'youtube premium': {'icon': '📺', 'name': 'YouTube Premium', 'description': 'Video Streaming', 'frequency': 'monthly'},
            'microsoft 365': {'icon': '💼', 'name': 'Microsoft 365', 'description': 'Office Suite', 'frequency': 'monthly'},
            'adobe': {'icon': '🎨', 'name': 'Adobe Creative', 'description': 'Design Software', 'frequency': 'monthly'}
        }
        
        # Category mapping
        self.category_mapping = {
            'food': ['swiggy', 'zomato', 'dominos', 'pizza', 'restaurant', 'food'],
            'entertainment': ['netflix', 'spotify', 'bookmyshow', 'movie', 'music'],
            'transportation': ['uber', 'ola', 'metro', 'bus', 'train', 'irctc'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'shopping', 'purchase'],
            'utility': ['electricity', 'gas', 'water', 'mobile', 'broadband', 'recharge'],
            'investment': ['mutual fund', 'sip', 'investment', 'equity', 'share'],
            'lifestyle': ['salon', 'spa', 'gym', 'fitness', 'health'],
            'education': ['course', 'book', 'education', 'learning', 'training'],
            'medical': ['hospital', 'doctor', 'medicine', 'health', 'medical']
        }
        
        # Payment medium patterns
        self.medium_patterns = {
            'upi': ['upi', 'unified payments', 'vpa', '@'],
            'bank_transfer': ['neft', 'rtgs', 'imps', 'bank transfer'],
            'credit_card': ['credit card', 'cc', 'visa', 'mastercard', 'amex'],
            'debit_card': ['debit card', 'dc', 'atm card'],
            'wallet': ['wallet', 'paytm', 'phonepe', 'google pay', 'amazon pay'],
            'cash': ['cash', 'cod', 'cash on delivery']
        }

    def extract_transaction_data(self, email, user_id: str) -> Optional[TransactionData]:
        """Extract comprehensive transaction data with advanced deduplication"""
        try:
            content = f"{email.subject} {email.snippet}"
            
            # Extract core transaction details
            amount = self._extract_amount(content)
            if not amount:
                return None
                
            transaction_date = self._extract_date(content, email)
            receiver = self._extract_receiver(content)
            medium = self._detect_payment_medium(content)
            category = self._detect_category(content)
            bank_account = self._extract_bank_account(content)
            source_info = self._extract_source_info(content)
            to_account = self._extract_to_account(content)
            
            # Extract additional comprehensive details
            transaction_type = self._extract_transaction_type(content)
            transaction_status = self._extract_transaction_status(content)
            reference_number = self._extract_reference_number(content)
            merchant_details = self._extract_merchant_details(content, receiver)
            location_info = self._extract_location_info(content)
            promotional_info = self._extract_promotional_info(content)
            
            # Create comprehensive transaction data
            transaction_data = TransactionData(
                fintransaction_id="",  # Will be generated
                user_id=user_id,
                
                # Core transaction details
                date_time=transaction_date,
                receiver=receiver,
                amount=amount,
                currency="INR",
                
                # Payment details
                medium=medium,
                bank_account=bank_account,
                source=source_info,
                to=to_account,
                to_account=to_account,
                transaction_type=transaction_type,
                transaction_status=transaction_status,
                transaction_channel=self._detect_transaction_channel(content),
                device_used=self._detect_device_used(content),
                authentication_method=self._detect_auth_method(content),
                
                # Merchant details
                merchant_name=receiver,
                merchant_type=self._classify_merchant_type(receiver),
                merchant_details=merchant_details,
                business_category=category,
                
                # Categorization
                metadata=category,
                category_details={
                    'merchant': receiver,
                    'category': category,
                    'subcategory': self._get_subcategory(content, category),
                    'confidence': self._calculate_confidence_score(content, amount, receiver)
                },
                subcategory=self._get_subcategory(content, category),
                spending_category=self._map_to_spending_category(category),
                tags=self._generate_auto_tags(content, receiver, category),
                
                # Additional transaction info
                reference_number=reference_number,
                transaction_reference_id=self._extract_transaction_id(content),
                order_id=self._extract_order_id(content),
                invoice_number=self._extract_invoice_number(content),
                
                # Amounts and fees
                tax_amount=self._extract_tax_amount(content),
                processing_fee=self._extract_processing_fee(content),
                cashback_amount=self._extract_cashback_amount(content),
                discount_amount=self._extract_discount_amount(content),
                
                # Location and context
                location=location_info.get('location'),
                city=location_info.get('city'),
                state=location_info.get('state'),
                country=location_info.get('country', 'India'),
                
                # Promotional info
                promotion_code_used=promotional_info.get('promo_code'),
                coupon_code=promotional_info.get('coupon_code'),
                offer_details=promotional_info.get('offer_details'),
                
                # Email source information
                source_emails=[email.id],
                email_types=[self._classify_email_type(content)],
                sender_email=email.sender,
                subject=email.subject,
                snippet=email.snippet,
                transaction_description=content[:500],
                email_confidence_score=self._calculate_confidence_score(content, amount, receiver),
                
                # Processing metadata
                confidence_score=self._calculate_confidence_score(content, amount, receiver),
                extraction_method="email",
                data_source="email",
                validation_status="auto_processed"
            )
            
            # Generate unique transaction ID and hash
            transaction_data.fintransaction_id = transaction_data.generate_transaction_id()
            transaction_data.transaction_hash = transaction_data.generate_transaction_hash()
            
            # Check for subscription
            subscription_info = self._detect_subscription(content, receiver)
            if subscription_info:
                transaction_data.is_subscription = True
                transaction_data.subscription_receiver = subscription_info
                transaction_data.subscription_type = subscription_info.get('frequency', 'monthly')
                transaction_data.recurring_transaction_id = f"sub_{transaction_data.fintransaction_id}"
            
            # Advanced deduplication check
            deduplicated_transaction = self._advanced_deduplicate_transaction(transaction_data)
            
            return deduplicated_transaction
            
        except Exception as e:
            self.logger.error(f"Error extracting comprehensive transaction data: {e}")
            return None

    def _advanced_deduplicate_transaction(self, transaction: TransactionData) -> TransactionData:
        """Advanced deduplication with multiple criteria"""
        
        # Primary deduplication key
        primary_key = f"{transaction.receiver}_{transaction.amount}_{transaction.date_time.strftime('%Y%m%d%H%M') if transaction.date_time else 'unknown'}"
        
        # Secondary deduplication key (for slight time variations)
        if transaction.date_time:
            date_rounded = transaction.date_time.replace(minute=0, second=0, microsecond=0)
            secondary_key = f"{transaction.receiver}_{transaction.amount}_{date_rounded.strftime('%Y%m%d%H')}"
        else:
            secondary_key = primary_key
        
        # Check primary key first
        if primary_key in self.transactions_cache:
            existing = self.transactions_cache[primary_key]
            existing.merge_with_duplicate(transaction)
            self.logger.info(f"🔄 EXACT DUPLICATE: Merged transaction {primary_key}")
            return existing
        
        # Check secondary key for near-duplicates (within same hour)
        elif secondary_key in self.transactions_cache and secondary_key != primary_key:
            existing = self.transactions_cache[secondary_key]
            if abs((existing.date_time - transaction.date_time).total_seconds()) < 3600:  # Within 1 hour
                existing.merge_with_duplicate(transaction)
                self.logger.info(f"🔄 NEAR DUPLICATE: Merged transaction {secondary_key} (time variance)")
                return existing
        
        # Check for hash collision (different keys but same transaction)
        for existing_key, existing_transaction in self.transactions_cache.items():
            if (existing_transaction.transaction_hash == transaction.transaction_hash and 
                existing_key != primary_key):
                existing_transaction.merge_with_duplicate(transaction)
                self.logger.info(f"🔄 HASH DUPLICATE: Merged via hash collision")
                return existing_transaction
        
        # New unique transaction
        self.transactions_cache[primary_key] = transaction
        self.logger.info(f"✅ NEW UNIQUE TRANSACTION: {primary_key}")
        return transaction

    # ============================================================================
    # ENHANCED EXTRACTION METHODS
    # ============================================================================

    def _extract_transaction_type(self, content: str) -> str:
        """Extract transaction type"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['refund', 'reversal', 'returned']):
            return 'refund'
        elif any(word in content_lower for word in ['credit', 'received', 'deposit']):
            return 'credit'
        elif any(word in content_lower for word in ['debit', 'paid', 'charged', 'sent']):
            return 'debit'
        elif any(word in content_lower for word in ['transfer', 'sent to']):
            return 'transfer'
        else:
            return 'debit'  # Default assumption
    
    def _extract_transaction_status(self, content: str) -> str:
        """Extract transaction status"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['failed', 'declined', 'rejected']):
            return 'failed'
        elif any(word in content_lower for word in ['pending', 'processing']):
            return 'pending'
        elif any(word in content_lower for word in ['cancelled', 'canceled']):
            return 'cancelled'
        elif any(word in content_lower for word in ['completed', 'successful', 'confirmed']):
            return 'completed'
        else:
            return 'completed'  # Default assumption
    
    def _extract_reference_number(self, content: str) -> Optional[str]:
        """Extract transaction reference number"""
        patterns = [
            r'ref(?:erence)?[:\s#]+([A-Z0-9]{6,20})',
            r'transaction[:\s]+id[:\s]+([A-Z0-9]{6,20})',
            r'txn[:\s]+(?:id|ref)[:\s]+([A-Z0-9]{6,20})',
            r'reference[:\s]+no[:\s]+([A-Z0-9]{6,20})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_merchant_details(self, content: str, merchant_name: str) -> Dict[str, Any]:
        """Extract detailed merchant information"""
        details = {}
        
        # Extract phone number
        phone_match = re.search(r'(\+91[-\s]?\d{10}|\d{10})', content)
        if phone_match:
            details['phone'] = phone_match.group(1)
        
        # Extract email
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
        if email_match:
            details['email'] = email_match.group(1)
        
        # Extract website
        website_match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', content)
        if website_match:
            details['website'] = website_match.group(1)
        
        return details
    
    def _extract_location_info(self, content: str) -> Dict[str, str]:
        """Extract location information"""
        location_info = {}
        
        # Indian cities
        cities = ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad']
        for city in cities:
            if city in content.lower():
                location_info['city'] = city.title()
                break
        
        # States
        states = ['maharashtra', 'karnataka', 'tamil nadu', 'west bengal', 'telangana', 'gujarat']
        for state in states:
            if state in content.lower():
                location_info['state'] = state.title()
                break
        
        return location_info
    
    def _extract_promotional_info(self, content: str) -> Dict[str, str]:
        """Extract promotional information"""
        promo_info = {}
        
        # Promo code patterns
        promo_patterns = [
            r'promo[:\s]+code[:\s]+([A-Z0-9]{3,15})',
            r'coupon[:\s]+code[:\s]+([A-Z0-9]{3,15})',
            r'discount[:\s]+code[:\s]+([A-Z0-9]{3,15})'
        ]
        
        for pattern in promo_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                promo_info['promo_code'] = match.group(1)
                break
        
        # Offer details
        if any(word in content.lower() for word in ['offer', 'discount', 'cashback', 'sale']):
            promo_info['offer_details'] = "Promotional offer applied"
        
        return promo_info
    
    def _classify_merchant_type(self, merchant: str) -> str:
        """Classify merchant type"""
        if not merchant:
            return 'unknown'
        
        merchant_lower = merchant.lower()
        
        type_mapping = {
            'e-commerce': ['amazon', 'flipkart', 'myntra', 'ajio'],
            'food_delivery': ['swiggy', 'zomato', 'foodpanda'],
            'transportation': ['uber', 'ola', 'rapido'],
            'streaming': ['netflix', 'amazon prime', 'hotstar', 'spotify'],
            'banking': ['sbi', 'hdfc', 'icici', 'axis'],
            'fuel': ['iocl', 'bpcl', 'hpcl', 'petrol', 'diesel'],
            'utility': ['electricity', 'gas', 'water', 'broadband'],
            'investment': ['mutual fund', 'sip', 'share', 'stock']
        }
        
        for merchant_type, keywords in type_mapping.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return merchant_type
        
        return 'retail'
    
    def _map_to_spending_category(self, category: str) -> str:
        """Map to standard spending categories"""
        mapping = {
            'food': 'Food & Dining',
            'entertainment': 'Entertainment',
            'transportation': 'Transportation',
            'shopping': 'Shopping',
            'utility': 'Bills & Utilities',
            'investment': 'Investment',
            'lifestyle': 'Personal Care',
            'education': 'Education',
            'medical': 'Healthcare'
        }
        
        return mapping.get(category, 'Other')
    
    def _generate_auto_tags(self, content: str, merchant: str, category: str) -> List[str]:
        """Generate automatic tags"""
        tags = []
        
        # Add category tag
        if category:
            tags.append(category)
        
        # Add merchant tag
        if merchant and merchant != 'Unknown Merchant':
            tags.append(merchant.lower().replace(' ', '_'))
        
        # Add amount-based tags
        content_lower = content.lower()
        if any(word in content_lower for word in ['cashback', 'reward']):
            tags.append('cashback')
        if any(word in content_lower for word in ['emi', 'installment']):
            tags.append('emi')
        if any(word in content_lower for word in ['recurring', 'subscription']):
            tags.append('recurring')
        
        return tags[:5]  # Limit to 5 tags
    
    def _classify_email_type(self, content: str) -> str:
        """Classify email type"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['receipt', 'invoice']):
            return 'receipt'
        elif any(word in content_lower for word in ['confirmation', 'confirmed']):
            return 'confirmation'
        elif any(word in content_lower for word in ['alert', 'notification']):
            return 'notification'
        elif any(word in content_lower for word in ['statement', 'summary']):
            return 'statement'
        else:
            return 'notification'
    
    def _detect_transaction_channel(self, content: str) -> str:
        """Detect transaction channel"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['mobile', 'app']):
            return 'mobile'
        elif any(word in content_lower for word in ['web', 'website', 'online']):
            return 'web'
        elif any(word in content_lower for word in ['atm']):
            return 'atm'
        elif any(word in content_lower for word in ['pos', 'swipe']):
            return 'pos'
        else:
            return 'online'
    
    def _detect_device_used(self, content: str) -> str:
        """Detect device used"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['mobile', 'phone']):
            return 'mobile'
        elif any(word in content_lower for word in ['web', 'computer']):
            return 'web'
        elif any(word in content_lower for word in ['atm']):
            return 'atm'
        else:
            return 'mobile'  # Default assumption
    
    def _detect_auth_method(self, content: str) -> str:
        """Detect authentication method"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['otp', 'one time password']):
            return 'otp'
        elif any(word in content_lower for word in ['biometric', 'fingerprint']):
            return 'biometric'
        elif any(word in content_lower for word in ['pin']):
            return 'pin'
        elif any(word in content_lower for word in ['contactless', 'tap']):
            return 'contactless'
        else:
            return 'unknown'

    # Additional extraction methods for amounts and fees
    def _extract_tax_amount(self, content: str) -> Optional[float]:
        """Extract tax amount"""
        tax_patterns = [
            r'tax[:\s]+₹?([\d,]+\.?\d*)',
            r'gst[:\s]+₹?([\d,]+\.?\d*)',
            r'vat[:\s]+₹?([\d,]+\.?\d*)'
        ]
        
        for pattern in tax_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return None
    
    def _extract_processing_fee(self, content: str) -> Optional[float]:
        """Extract processing fee"""
        fee_patterns = [
            r'(?:processing|service|convenience)\s+fee[:\s]+₹?([\d,]+\.?\d*)',
            r'charges[:\s]+₹?([\d,]+\.?\d*)'
        ]
        
        for pattern in fee_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return None
    
    def _extract_cashback_amount(self, content: str) -> Optional[float]:
        """Extract cashback amount"""
        cashback_patterns = [
            r'cashback[:\s]+₹?([\d,]+\.?\d*)',
            r'reward[:\s]+₹?([\d,]+\.?\d*)'
        ]
        
        for pattern in cashback_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return None
    
    def _extract_discount_amount(self, content: str) -> Optional[float]:
        """Extract discount amount"""
        discount_patterns = [
            r'discount[:\s]+₹?([\d,]+\.?\d*)',
            r'saved[:\s]+₹?([\d,]+\.?\d*)'
        ]
        
        for pattern in discount_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return None
    
    def _extract_order_id(self, content: str) -> Optional[str]:
        """Extract order ID"""
        order_patterns = [
            r'order[:\s]+id[:\s]+([A-Z0-9-]{6,20})',
            r'order[:\s]+number[:\s]+([A-Z0-9-]{6,20})',
            r'order[:\s]+([A-Z0-9-]{6,20})'
        ]
        
        for pattern in order_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_invoice_number(self, content: str) -> Optional[str]:
        """Extract invoice number"""
        invoice_patterns = [
            r'invoice[:\s]+(?:no|number)[:\s]+([A-Z0-9-]{4,15})',
            r'bill[:\s]+(?:no|number)[:\s]+([A-Z0-9-]{4,15})'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

# ============================================================================
# MAIN EXTRACTION FUNCTION
# ============================================================================

def extract_enhanced_transaction_data(email, user_id: str) -> Optional[TransactionData]:
    """Main function to extract deduplicated transaction data"""
    try:
        processor = FinancialTransactionProcessor()
        return processor.extract_transaction_data(email, user_id)
    except Exception as e:
        print(f"❌ Error extracting enhanced transaction: {e}")
        return None

print("🔥 Enhanced Financial Transactions System Loaded Successfully!")
print("📊 New capabilities: Advanced filtering, 5-month history, structured extraction, comprehensive analytics") 