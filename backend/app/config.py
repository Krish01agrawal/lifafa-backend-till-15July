"""
Backend Configuration for Scalability
=====================================

This module contains all configuration settings, limits, and constraints
for the Gmail Chatbot backend to ensure scalability and production readiness.
"""

import os
from typing import Dict, Any

# ============================================================================
# SCALABILITY LIMITS
# ============================================================================

# Gmail API Rate Limiting
GMAIL_API_RATE_LIMIT = 250  # requests per user per 100 seconds
GMAIL_API_WINDOW_SECONDS = 100  # rate limit window
GMAIL_API_COOLDOWN = 60  # seconds to wait when rate limit hit

# Processing Timeouts
EMAIL_PROCESSING_TIMEOUT = 300  # 5 minutes for email processing
FINANCIAL_PROCESSING_TIMEOUT = 600  # 10 minutes for financial processing
DATABASE_QUERY_TIMEOUT = 30  # 30 seconds for database operations
EXTERNAL_API_TIMEOUT = 60  # 60 seconds for external API calls

# Memory Management
MAX_MEMORY_USAGE = 1024  # MB per user processing
MAX_EMAIL_BATCH_SIZE = 1000  # emails per batch to prevent memory issues
MAX_EMAIL_BODY_SIZE = 500 * 1024  # 500KB per email body
MAX_TOTAL_EMAILS_MEMORY = 50 * 1024 * 1024  # 50MB total email content

# Concurrent User Limits
CONCURRENT_USERS_LIMIT = 15  # maximum concurrent users processing
MAX_BACKGROUND_WORKERS = 5  # maximum background worker threads
QUEUE_MAX_SIZE = 100  # maximum queue size for pending operations

# ============================================================================
# EMAIL PROCESSING LIMITS
# ============================================================================

# Email Fetching Constraints
DEFAULT_EMAIL_LIMIT = 3500  # default emails per fetch (increased from 2500)
MAX_EMAIL_LIMIT = 10000  # absolute maximum emails per user
EMAIL_TIME_RANGE_DAYS = 150  # 5 months of email history
MAX_PAGINATION_PAGES = 20  # safety limit for Gmail API pagination

# Financial Processing Limits
FINANCIAL_TIME_MONTHS = 5  # months of financial data to process
FINANCIAL_MAX_PAGES = 30  # maximum pages for financial email fetching
FINANCIAL_BATCH_SIZE = 500  # financial emails per batch
MAX_FINANCIAL_TRANSACTIONS = 10000  # maximum transactions to retrieve

# ============================================================================
# DATABASE LIMITS
# ============================================================================

# MongoDB Configuration
DB_CONNECTION_TIMEOUT = 30  # seconds
DB_MAX_POOL_SIZE = 50  # maximum connection pool size
DB_MIN_POOL_SIZE = 5  # minimum connection pool size
DB_MAX_IDLE_TIME = 300  # seconds before closing idle connections

# Collection Limits
MAX_DOCUMENTS_PER_QUERY = 10000  # maximum documents per query
DEFAULT_QUERY_LIMIT = 100  # default limit for queries
MAX_BULK_INSERT_SIZE = 1000  # maximum documents per bulk insert

# ============================================================================
# MEMORY STORAGE (MEM0) LIMITS
# ============================================================================

# Mem0 Search Limits
MEM0_DEFAULT_SEARCH_LIMIT = 500  # default search results
MEM0_MAX_SEARCH_LIMIT = 2000  # maximum search results
MEM0_RETRY_ATTEMPTS = 3  # retry attempts for failed operations
MEM0_RETRY_DELAY = 2  # seconds between retries

# Memory Management
MEM0_MEMORY_CLEANUP_DAYS = 30  # cleanup memories older than 30 days
MEM0_MAX_MEMORIES_PER_USER = 50000  # maximum memories per user

# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================

# Scheduler Configuration
BACKGROUND_WORKER_INTERVAL = 30  # 30 seconds between checks (increased frequency)
MAX_BACKGROUND_PROCESSING_TIME = 1800  # 30 minutes maximum processing time
BACKGROUND_WORKER_TIMEOUT = 300  # 5 minutes timeout per worker task

# Queue Management
PROCESSING_QUEUE_TIMEOUT = 600  # 10 minutes in queue before timeout
MAX_RETRY_ATTEMPTS = 3  # maximum retry attempts for failed operations
RETRY_BACKOFF_FACTOR = 2  # exponential backoff multiplier

# ============================================================================
# API RATE LIMITING
# ============================================================================

# External API Limits
OPENAI_RATE_LIMIT = 100  # requests per minute
GOOGLE_API_RATE_LIMIT = 1000  # requests per day per user
MEM0_API_RATE_LIMIT = 200  # requests per minute

# Internal API Limits
MAX_REQUESTS_PER_MINUTE = 60  # requests per user per minute
MAX_CONCURRENT_REQUESTS = 10  # concurrent requests per user
REQUEST_TIMEOUT = 30  # seconds for API request timeout

# ============================================================================
# SECURITY & VALIDATION
# ============================================================================

# JWT Configuration
JWT_EXPIRATION_HOURS = 24  # JWT token expiration
JWT_REFRESH_THRESHOLD_HOURS = 2  # refresh token if expires within 2 hours

# Input Validation
MAX_QUERY_LENGTH = 1000  # maximum characters in user queries
MAX_EMAIL_SUBJECT_LENGTH = 500  # maximum email subject length
MAX_USER_ID_LENGTH = 100  # maximum user ID length

# ============================================================================
# MONITORING & LOGGING
# ============================================================================

# Performance Monitoring
SLOW_QUERY_THRESHOLD = 5  # seconds - log slow database queries
MEMORY_WARNING_THRESHOLD = 800  # MB - warn when approaching memory limit
CPU_WARNING_THRESHOLD = 80  # percentage - warn when CPU usage high

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_MAX_SIZE = 100 * 1024 * 1024  # 100MB per log file
LOG_FILE_BACKUP_COUNT = 5  # keep 5 backup log files

# ============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ============================================================================

def get_config() -> Dict[str, Any]:
    """Get configuration with environment-specific overrides"""
    config = {
        # Rate Limits
        "gmail_api_rate_limit": int(os.getenv("GMAIL_API_RATE_LIMIT", GMAIL_API_RATE_LIMIT)),
        "concurrent_users_limit": int(os.getenv("CONCURRENT_USERS_LIMIT", CONCURRENT_USERS_LIMIT)),
        
        # Timeouts
        "email_processing_timeout": int(os.getenv("EMAIL_PROCESSING_TIMEOUT", EMAIL_PROCESSING_TIMEOUT)),
        "database_query_timeout": int(os.getenv("DATABASE_QUERY_TIMEOUT", DATABASE_QUERY_TIMEOUT)),
        
        # Memory Limits
        "max_memory_usage": int(os.getenv("MAX_MEMORY_USAGE", MAX_MEMORY_USAGE)),
        "max_email_batch_size": int(os.getenv("MAX_EMAIL_BATCH_SIZE", MAX_EMAIL_BATCH_SIZE)),
        
        # Processing Limits
        "default_email_limit": int(os.getenv("DEFAULT_EMAIL_LIMIT", DEFAULT_EMAIL_LIMIT)),
        "max_email_limit": int(os.getenv("MAX_EMAIL_LIMIT", MAX_EMAIL_LIMIT)),
        
        # Background Processing
        "background_worker_interval": int(os.getenv("BACKGROUND_WORKER_INTERVAL", BACKGROUND_WORKER_INTERVAL)),
        "max_background_workers": int(os.getenv("MAX_BACKGROUND_WORKERS", MAX_BACKGROUND_WORKERS)),
    }
    
    return config

# Export commonly used configuration
CONFIG = get_config()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

def get_rate_limit_for_user(user_id: str) -> int:
    """Get rate limit for specific user (can be customized per user)"""
    # Premium users could have higher limits
    premium_users = os.getenv("PREMIUM_USERS", "").split(",")
    if user_id in premium_users:
        return GMAIL_API_RATE_LIMIT * 2
    return GMAIL_API_RATE_LIMIT

def get_memory_limit_for_user(user_id: str) -> int:
    """Get memory limit for specific user"""
    premium_users = os.getenv("PREMIUM_USERS", "").split(",")
    if user_id in premium_users:
        return MAX_MEMORY_USAGE * 2
    return MAX_MEMORY_USAGE

print("⚙️ Backend configuration loaded successfully!")
print(f"📧 Email fetching limit: {DEFAULT_EMAIL_LIMIT} emails per fetch")
print(f"🔧 Concurrent users limit: {CONCURRENT_USERS_LIMIT}")
print(f"⏱️ Email processing timeout: {EMAIL_PROCESSING_TIMEOUT}s")
print(f"🧠 Max memory per user: {MAX_MEMORY_USAGE}MB")
print(f"🚀 Gmail API rate limit: {GMAIL_API_RATE_LIMIT} requests per {GMAIL_API_WINDOW_SECONDS}s")
print(f"⚡ Background worker interval: {BACKGROUND_WORKER_INTERVAL}s") 