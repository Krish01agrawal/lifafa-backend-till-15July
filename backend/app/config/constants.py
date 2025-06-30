"""
Application Constants
====================

This module contains all application-wide constants, enums, and static values.
"""

from enum import Enum
from typing import Dict, List, Pattern
import re


class ProcessingStatus(str, Enum):
    """Email processing status constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class EmailType(str, Enum):
    """Email type classification constants."""
    FINANCIAL = "financial"
    PROMOTIONAL = "promotional"
    PERSONAL = "personal"
    WORK = "work"
    SPAM = "spam"
    NEWSLETTER = "newsletter"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    STATEMENT = "statement"


class TransactionType(str, Enum):
    """Financial transaction type constants."""
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"
    SUBSCRIPTION = "subscription"
    INVESTMENT = "investment"
    LOAN = "loan"


class CreditBureau(str, Enum):
    """Credit bureau constants."""
    CIBIL = "cibil"
    EXPERIAN = "experian"
    EQUIFAX = "equifax"
    CRIF = "crif"


class HealthStatus(str, Enum):
    """System health status constants."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


# ============================================================================
# EMAIL PROCESSING CONSTANTS
# ============================================================================

# Financial Email Keywords
FINANCIAL_KEYWORDS = [
    "transaction", "payment", "debit", "credit", "refund", "invoice", "receipt",
    "statement", "balance", "transfer", "withdrawal", "deposit", "subscription",
    "billing", "charged", "amount", "rupees", "inr", "upi", "netbanking",
    "credit card", "debit card", "loan", "emi", "interest", "bank", "account"
]

# Promotional Email Patterns
PROMOTIONAL_PATTERNS = [
    r"unsubscribe",
    r"click here",
    r"limited time offer",
    r"sale.*off",
    r"discount.*%",
    r"buy now",
    r"exclusive offer",
    r"don't miss out",
    r"hurry.*expires",
    r"newsletter"
]

# Compiled regex patterns for performance
PROMOTIONAL_REGEX: List[Pattern] = [re.compile(pattern, re.IGNORECASE) for pattern in PROMOTIONAL_PATTERNS]

# Essential email fields to preserve
ESSENTIAL_EMAIL_FIELDS = [
    "id", "threadId", "snippet", "sender", "recipient", "subject", 
    "date", "body", "attachments", "labels", "importance", "read"
]

# Financial transaction keywords for better extraction
FINANCIAL_TRANSACTION_KEYWORDS = [
    "debited", "credited", "transferred", "paid", "received", "refunded",
    "charged", "billed", "withdrawn", "deposited", "spent", "earned"
]

# Banking institution patterns
BANK_PATTERNS = [
    r"state bank of india|sbi",
    r"hdfc bank|hdfc",
    r"icici bank|icici",
    r"axis bank|axis",
    r"kotak mahindra|kotak",
    r"punjab national bank|pnb",
    r"bank of baroda|bob",
    r"union bank",
    r"canara bank",
    r"indian bank"
]

BANK_REGEX: List[Pattern] = [re.compile(pattern, re.IGNORECASE) for pattern in BANK_PATTERNS]

# ============================================================================
# API RESPONSE MESSAGES
# ============================================================================

class APIMessages:
    """Standard API response messages."""
    
    # Success Messages
    SUCCESS_LOGIN = "Successfully authenticated"
    SUCCESS_LOGOUT = "Successfully logged out"
    SUCCESS_EMAIL_FETCH = "Emails fetched successfully"
    SUCCESS_EMAIL_PROCESS = "Emails processed successfully"
    SUCCESS_FINANCIAL_ANALYSIS = "Financial analysis completed"
    SUCCESS_QUERY = "Query processed successfully"
    
    # Error Messages
    ERROR_INVALID_TOKEN = "Invalid or expired token"
    ERROR_USER_NOT_FOUND = "User not found"
    ERROR_EMAIL_FETCH_FAILED = "Failed to fetch emails"
    ERROR_PROCESSING_FAILED = "Processing failed"
    ERROR_RATE_LIMIT = "Rate limit exceeded"
    ERROR_INTERNAL_SERVER = "Internal server error"
    ERROR_INVALID_INPUT = "Invalid input parameters"
    ERROR_UNAUTHORIZED = "Unauthorized access"
    ERROR_FORBIDDEN = "Forbidden access"
    ERROR_NOT_FOUND = "Resource not found"
    
    # Warning Messages
    WARNING_PARTIAL_PROCESSING = "Partial processing completed with warnings"
    WARNING_RATE_LIMIT_APPROACHING = "Rate limit approaching"
    WARNING_STORAGE_FULL = "Storage limit approaching"


# ============================================================================
# CACHE KEYS
# ============================================================================

class CacheKeys:
    """Cache key constants."""
    
    USER_SESSION = "user_session:{user_id}"
    EMAIL_METADATA = "email_metadata:{user_id}:{email_id}"
    SEARCH_RESULTS = "search_results:{user_id}:{query_hash}"
    AI_RESPONSE = "ai_response:{query_hash}"
    FINANCIAL_DATA = "financial_data:{user_id}"
    CREDIT_REPORT = "credit_report:{user_id}:{report_id}"
    USER_PREFERENCES = "user_preferences:{user_id}"
    SYSTEM_STATS = "system_stats"


# ============================================================================
# DEFAULT LIMITS
# ============================================================================

class DefaultLimits:
    """Default processing limits."""
    
    # Email Limits
    EMAIL_FETCH_LIMIT = 20000
    EMAIL_BODY_SIZE_MB = 2
    EMAIL_PROCESSING_TIMEOUT = 1800
    
    # Financial Limits
    FINANCIAL_PROCESSING_TIMEOUT = 2400
    MAX_FINANCIAL_TRANSACTIONS = 50000
    FINANCIAL_ANALYSIS_MONTHS = 12
    
    # Memory Limits
    MAX_MEMORY_USAGE_GB = 6
    MAX_CONCURRENT_USERS = 200
    
    # Rate Limits
    REQUESTS_PER_MINUTE = 240
    CONCURRENT_REQUESTS = 40


# ============================================================================
# WEBHOOK EVENTS
# ============================================================================

class WebSocketEvents:
    """WebSocket event constants."""
    
    # Client Events
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"
    CLIENT_QUERY = "client_query"
    CLIENT_KEEPALIVE = "client_keepalive"
    
    # Server Events
    SERVER_PROCESSING_START = "processing_start"
    SERVER_PROCESSING_UPDATE = "processing_update"
    SERVER_PROCESSING_COMPLETE = "processing_complete"
    SERVER_PROCESSING_ERROR = "processing_error"
    SERVER_RESPONSE = "response"
    SERVER_KEEPALIVE = "keepalive"
    
    # Email Events
    EMAIL_SYNC_START = "email_sync_start"
    EMAIL_SYNC_PROGRESS = "email_sync_progress"
    EMAIL_SYNC_COMPLETE = "email_sync_complete"
    EMAIL_SYNC_ERROR = "email_sync_error"
    
    # Financial Events
    FINANCIAL_ANALYSIS_START = "financial_analysis_start"
    FINANCIAL_ANALYSIS_PROGRESS = "financial_analysis_progress"
    FINANCIAL_ANALYSIS_COMPLETE = "financial_analysis_complete"
    FINANCIAL_ANALYSIS_ERROR = "financial_analysis_error" 