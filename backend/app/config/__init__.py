from .settings import Settings, get_settings
from .database import DatabaseConfig, get_database_config
from .constants import *

# Initialize settings and database config
_settings = get_settings()
_db_config = get_database_config()

# Legacy CONFIG object for backward compatibility
CONFIG = _settings

# ============================================================================
# DATABASE CONSTANTS (mapped from DatabaseConfig)
# ============================================================================

# Database connection settings
DB_MAX_POOL_SIZE = _db_config.max_pool_size
DB_MIN_POOL_SIZE = _db_config.min_pool_size  
DB_CONNECTION_TIMEOUT = _db_config.connection_timeout
DATABASE_INSERT_BATCH_SIZE = _db_config.batch_insert_size

# Database sharding settings
ENABLE_DATABASE_SHARDING = _db_config.enable_sharding
MAX_USERS_PER_DATABASE = _db_config.max_users_per_database

# Database cleanup settings
ENABLE_AUTO_CLEANUP = _db_config.enable_auto_cleanup
MAX_EMAIL_AGE_DAYS = _db_config.max_email_age_days

# ============================================================================
# EMAIL PROCESSING CONSTANTS
# ============================================================================

# Email preservation settings
PRESERVE_EMAIL_BODY = True
PRESERVE_EMAIL_HEADERS = True
PRESERVE_ATTACHMENTS_INFO = True

# Email processing limits
EMAIL_TIME_RANGE_DAYS = 365
MAX_PAGINATION_PAGES = 50
MAX_CONCURRENT_EMAIL_PROCESSING = 25
DEFAULT_EMAIL_LIMIT = _settings.default_email_limit
MAX_EMAIL_LIMIT = _settings.max_email_limit

# Processing features
ENABLE_BATCH_PROCESSING = _settings.enable_batch_processing

# Performance and timeout settings
# ⏱️ Increase processing timeout to support large 6-month financial scans
EMAIL_PROCESSING_TIMEOUT = 1800  # 30 minutes
CONCURRENT_USERS_LIMIT = 50
STORAGE_WARNING_THRESHOLD = 80  # 80% storage usage warning
STORAGE_CRITICAL_THRESHOLD = 95  # 95% storage usage critical

# Credit bureau settings
SUPPORTED_CREDIT_BUREAUS = ["cibil", "experian", "crif", "equifax"]
CREDIT_REPORT_TIMEOUT = 60  # Credit report API timeout in seconds
CREDIT_REPORT_CACHE_HOURS = 24  # Cache credit reports for 24 hours
CREDIT_REPORT_RETRY_ATTEMPTS = 3  # Number of retry attempts for failed requests
MAX_CREDIT_REPORTS_PER_USER_PER_MONTH = 3  # Free tier limit
ENABLE_DATA_ENCRYPTION = True  # Enable encryption of sensitive data

# AI Analysis settings
CREDIT_REPORT_ANALYSIS_PROMPTS = {
    "score_analysis": "Analyze the credit score and provide insights on factors affecting it.",
    "account_analysis": "Analyze credit accounts and payment history patterns.",
    "improvement_suggestions": "Suggest actionable steps to improve credit score."
}
FINANCIAL_ANALYSIS_MODEL = "gpt-4"  # Model for financial analysis
FINANCIAL_ANALYSIS_MAX_TOKENS = 2000  # Max tokens for analysis responses

# Statement processing settings
STATEMENT_PROCESSING_TIMEOUT = 300  # 5 minutes for statement processing
MAX_STATEMENT_FILE_SIZE_MB = 10  # Maximum file size for statements
SUPPORTED_STATEMENT_FORMATS = ["pdf", "csv", "xlsx", "xls"]  # Supported file formats
PDF_PROCESSING_ENGINE = "pdfplumber"  # PDF processing engine
COMMON_PDF_PASSWORDS = ["statement", "123456", "password"]  # Common PDF passwords to try
STATEMENT_ANALYSIS_LOOKBACK_MONTHS = 6  # Months to analyze for patterns
MIN_TRANSACTIONS_FOR_ANALYSIS = 10  # Minimum transactions required for analysis
ENABLE_CATEGORY_AUTO_CLASSIFICATION = True  # Enable automatic transaction categorization
ENABLE_RECURRING_PAYMENT_DETECTION = True  # Enable recurring payment detection

# Transaction categories
TRANSACTION_CATEGORIES = {
    "food": ["restaurant", "food", "swiggy", "zomato", "cafe", "hotel"],
    "transport": ["uber", "ola", "taxi", "bus", "metro", "petrol", "fuel"],
    "shopping": ["amazon", "flipkart", "mall", "store", "shop"],
    "utilities": ["electricity", "water", "gas", "phone", "internet", "mobile"],
    "healthcare": ["hospital", "medical", "pharmacy", "doctor", "clinic"],
    "entertainment": ["movie", "cinema", "netflix", "spotify", "gaming"],
    "education": ["school", "college", "course", "book", "training"],
    "investment": ["mutual fund", "sip", "fd", "deposit", "shares"],
    "insurance": ["insurance", "premium", "policy"],
    "transfer": ["transfer", "neft", "imps", "upi", "withdraw"],
    "salary": ["salary", "wage", "income", "bonus"],
    "other": []
}

# Statement analysis AI prompts
STATEMENT_ANALYSIS_PROMPTS = {
    "spending_analysis": "Analyze spending patterns from the bank statement transactions.",
    "income_analysis": "Analyze income patterns and sources from the transactions.",
    "financial_health": "Assess overall financial health based on transaction patterns.",
    "recommendations": "Provide actionable recommendations based on transaction analysis."
}

# Credit card recommendation settings
CARD_RECOMMENDATION_PROMPTS = {
    "personalized_analysis": "Analyze user's financial profile and recommend suitable credit cards.",
    "benefit_calculation": "Calculate estimated benefits based on spending patterns.",
    "risk_assessment": "Assess financial risk for credit card recommendations.",
    "comparison": "Compare multiple credit cards for the user's specific needs."
}
BANK_APPLICATION_URLS = {
    "hdfc": "https://www.hdfcbank.com/personal/pay/cards/credit-cards/apply",
    "icici": "https://www.icicibank.com/personal-banking/cards/credit-card",
    "sbi": "https://www.sbi.co.in/web/personal-banking/cards/credit-cards",
    "axis": "https://www.axisbank.com/personal/cards/credit-cards",
    "kotak": "https://www.kotak.com/en/personal-banking/cards/credit-cards.html",
    "yes": "https://www.yesbank.in/personal-banking/cards/credit-cards"
}
MAX_APPLICATION_ATTEMPTS_PER_DAY = 3  # Maximum card applications per day per user

# Browser automation settings
BROWSER_AUTOMATION_TIMEOUT = 300  # 5 minutes for browser operations
BROWSER_TYPE = "chromium"  # Browser type for automation (chromium/firefox/webkit)
BROWSER_HEADLESS_MODE = True  # Run browser in headless mode
PLAYWRIGHT_BROWSER_ARGS = ["--no-sandbox", "--disable-setuid-sandbox"]  # Browser launch arguments
ENABLE_AUTO_FORM_FILLING = True  # Enable automatic form filling
FORM_FILLING_DELAY_SECONDS = 2  # Delay between form field fills

# Credit card scraping sources
CREDIT_CARD_SOURCES = {
    "bankbazaar": {
        "url": "https://www.bankbazaar.com/credit-card.html",
        "enabled": True,
        "rate_limit": 60,  # seconds between requests
        "selectors": {
            "card_container": ".card-item",
            "card_name": ".card-name",
            "bank_name": ".bank-name",
            "annual_fee": ".annual-fee"
        }
    },
    "paisabazaar": {
        "url": "https://www.paisabazaar.com/credit-card/",
        "enabled": True,
        "rate_limit": 60,
        "selectors": {
            "card_container": ".product-item",
            "card_name": ".product-name",
            "bank_name": ".bank-name",
            "annual_fee": ".fee-amount"
        }
    },
    "cardexpert": {
        "url": "https://www.cardexpert.in/credit-cards/",
        "enabled": False,  # Disabled by default for free tier
        "rate_limit": 90,
        "selectors": {
            "card_container": "[data-testid*='card']",
            "card_name": ".card-title",
            "bank_name": ".issuer-name",
            "annual_fee": ".fee-info"
        }
    }
}

# Smart email filtering
ENABLE_SMART_EMAIL_FILTERING = _settings.enable_smart_email_filtering
PROMOTIONAL_EMAIL_PATTERNS = PROMOTIONAL_REGEX
FINANCIAL_EMAIL_KEYWORDS = FINANCIAL_KEYWORDS

# Caching settings
ENABLE_SMART_CACHING = _settings.enable_smart_caching
CACHE_AI_RESPONSES = True
CACHE_SEARCH_RESULTS = True
CACHE_EMAIL_METADATA = True
MAX_CACHE_SIZE_MB = 256

# Batch processing settings
EMAIL_CATEGORIZATION_BATCH_SIZE = 100
MAX_CONCURRENT_AI_REQUESTS = 25

# Mem0 settings
MEM0_DEFAULT_SEARCH_LIMIT = 500
MEM0_MAX_SEARCH_LIMIT = 2000
MEM0_RETRY_ATTEMPTS = 3
MEM0_RETRY_DELAY = 5

# ============================================================================
# FALLBACK AND SHARD DATABASES
# ============================================================================

# Use local fallback for development
USE_LOCAL_FALLBACK = not _settings.is_production
LOCAL_MONGODB_URL = "mongodb://localhost:27017"

# Shard databases - for now using single database but structured as list for scaling
SHARD_DATABASES = [_settings.mongodb_url]

# Enable aggressive compression for free tier
ENABLE_AGGRESSIVE_COMPRESSION = True

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_database_for_user(user_id: str) -> str:
    """Get database for user (simple hash-based routing)"""
    if not ENABLE_DATABASE_SHARDING:
        return _settings.mongodb_database
    
    # Simple hash-based routing for multiple databases
    shard_index = hash(user_id) % len(SHARD_DATABASES)
    return f"{_settings.mongodb_database}_shard_{shard_index}"

def calculate_email_importance(email_data: dict) -> float:
    """🔧 MASSIVELY ENHANCED: Calculate email importance score - PRESERVE MORE EMAILS"""
    score = 5.0  # High base score - start with assumption that email is important
    
    # Check if it's a financial email
    subject = email_data.get('subject', '').lower()
    body = email_data.get('body', '').lower()
    sender = email_data.get('sender', '').lower()
    snippet = email_data.get('snippet', '').lower()
    
    # 🔧 MASSIVELY EXPANDED: All transaction-related content gets very high scores
    transaction_keywords = [
        # Financial transactions
        'transaction', 'payment', 'debit', 'credit', 'refund', 'invoice', 'receipt',
        'statement', 'balance', 'transfer', 'withdrawal', 'deposit', 'charged',
        'amount', 'rupees', 'inr', '₹', 'rs.', 'money', 'fund', 'bill', 'due',
        
        # Shopping & orders
        'order', 'purchase', 'bought', 'cart', 'checkout', 'item', 'product',
        'delivery', 'shipped', 'dispatched', 'tracking', 'confirmed', 'booking',
        'reserved', 'ticket', 'seat', 'confirmation', 'booking reference',
        
        # Services & subscriptions
        'subscription', 'premium', 'plan', 'renewal', 'expired', 'activate',
        'membership', 'pro version', 'upgrade', 'service', 'appointment',
        
        # Investment & trading
        'investment', 'invest', 'mutual fund', 'sip', 'stock', 'share', 'equity',
        'trading', 'portfolio', 'dividend', 'redemption', 'units', 'nav',
        'profit', 'loss', 'capital gains', 'market'
    ]
    
    content = f"{subject} {body} {snippet}"
    transaction_score = sum(1 for keyword in transaction_keywords if keyword in content)
    if transaction_score > 0:
        score += min(transaction_score * 2.0, 8.0)  # Cap at 8 extra points
    
    # 🔧 MASSIVELY EXPANDED: Important sender patterns
    import re
    important_sender_patterns = [
        # Banks and financial institutions
        r'bank|hdfc|icici|sbi|axis|kotak|pnb|bob|canara|union|indian|central',
        # Payment platforms  
        r'paytm|phonepe|googlepay|amazonpay|mobikwik|freecharge|bharatpe',
        # E-commerce platforms
        r'amazon|flipkart|myntra|ajio|nykaa|bigbasket|grofers|snapdeal',
        # Food delivery
        r'swiggy|zomato|ubereats|foodpanda|dominos|pizzahut|kfc|mcdonalds',
        # Travel & transportation
        r'makemytrip|goibibo|cleartrip|irctc|redbus|uber|ola|rapido',
        r'indigo|spicejet|airindia|vistara|goair|airlines?',
        # Investment platforms
        r'zerodha|groww|angel.*broking|icicidirect|hdfcsec|kotaksecurities',
        r'mutual.*fund|aditya.*birla|nippon|axis.*mutual|sbi.*mutual',
        # Streaming & subscriptions
        r'netflix|prime|hotstar|spotify|youtube|adobe|microsoft|apple',
        r'google|dropbox|zoom|slack|notion|canva|figma',
        # Utilities & services
        r'airtel|jio|vodafone|bsnl|tata|adani|bescom|electricity|gas|water',
        r'insurance|policy|lic|bajaj|hdfc.*ergo|icici.*lombard',
        # Government & official
        r'irctc|uidai|epfo|income.*tax|gst|passport|driving.*license',
        r'aadhaar|pan|voter|election|government|official|ministry'
    ]
    
    for pattern in important_sender_patterns:
        if re.search(pattern, sender):
            score += 3.0  # High score for important senders
            break
    
    # 🔧 ENHANCED: Transaction patterns get very high scores
    transaction_patterns = [
        r'[₹\$]\s*[\d,]+',  # Amount patterns
        r'(?:rs\.?|rupees?|inr)\s*[\d,]+',
        r'order\s*(?:id|no|number)?\s*:?\s*[a-zA-Z0-9]+',
        r'transaction\s*(?:id|ref|no)?\s*:?\s*[a-zA-Z0-9]+',
        r'booking\s*(?:id|ref|no)?\s*:?\s*[a-zA-Z0-9]+',
        r'ticket\s*(?:no|number)?\s*:?\s*[a-zA-Z0-9]+',
        r'reference\s*(?:no|number)?\s*:?\s*[a-zA-Z0-9]+',
        r'order\s+(?:confirmed|placed|delivered|shipped|dispatched)',
        r'payment\s+(?:successful|completed|received|failed)',
        r'booking\s+(?:confirmed|cancelled|modified)',
        r'subscription\s+(?:activated|renewed|expired|cancelled)',
    ]
    
    for pattern in transaction_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            score += 2.0  # High score for transaction patterns
            break
    
    # 🔧 MINIMAL: Only penalize very clear promotional content
    clear_promotional_patterns = [
        r'unsubscribe.*from.*newsletter',
        r'marketing.*email|promotional.*email',
        r'daily.*newsletter|weekly.*newsletter',
        r'click.*here.*unsubscribe',
        r'remove.*me.*from.*list'
    ]
    
    for pattern in clear_promotional_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            score -= 2.0  # Reduced penalty
            break
    
    # 🔧 ENHANCED: Scale to 0-10 range with high preservation tendency
    return max(0.5, min(10.0, score))  # Minimum 0.5 to avoid filtering most emails

__all__ = [
    "Settings",
    "get_settings", 
    "DatabaseConfig",
    "get_database_config",
    "CONFIG",
    # Database constants
    "DB_MAX_POOL_SIZE",
    "DB_MIN_POOL_SIZE", 
    "DB_CONNECTION_TIMEOUT",
    "DATABASE_INSERT_BATCH_SIZE",
    "ENABLE_DATABASE_SHARDING",
    "SHARD_DATABASES",
    "MAX_USERS_PER_DATABASE",
    "get_database_for_user",
    "ENABLE_AUTO_CLEANUP",
    "MAX_EMAIL_AGE_DAYS",
    # Email processing constants
    "ESSENTIAL_EMAIL_FIELDS",
    "PRESERVE_EMAIL_BODY", 
    "PRESERVE_EMAIL_HEADERS",
    "PRESERVE_ATTACHMENTS_INFO",
    "EMAIL_TIME_RANGE_DAYS",
    "MAX_PAGINATION_PAGES",
    "MAX_CONCURRENT_EMAIL_PROCESSING",
    "DEFAULT_EMAIL_LIMIT",
    "MAX_EMAIL_LIMIT",
    "ENABLE_BATCH_PROCESSING",
    "ENABLE_SMART_EMAIL_FILTERING",
    "PROMOTIONAL_EMAIL_PATTERNS",
    "FINANCIAL_EMAIL_KEYWORDS",
    "calculate_email_importance",
    "USE_LOCAL_FALLBACK",
    "LOCAL_MONGODB_URL",
    "ENABLE_AGGRESSIVE_COMPRESSION",
    # Caching constants
    "ENABLE_SMART_CACHING",
    "CACHE_AI_RESPONSES",
    "CACHE_SEARCH_RESULTS", 
    "CACHE_EMAIL_METADATA",
    "MAX_CACHE_SIZE_MB",
    "EMAIL_CATEGORIZATION_BATCH_SIZE",
    "MAX_CONCURRENT_AI_REQUESTS",
    # Mem0 constants
    "MEM0_DEFAULT_SEARCH_LIMIT",
    "MEM0_MAX_SEARCH_LIMIT",
    "MEM0_RETRY_ATTEMPTS",
    "MEM0_RETRY_DELAY",
    # Performance constants
    "EMAIL_PROCESSING_TIMEOUT",
    "CONCURRENT_USERS_LIMIT",
    "STORAGE_WARNING_THRESHOLD",
    "STORAGE_CRITICAL_THRESHOLD",
    "SUPPORTED_CREDIT_BUREAUS",
    "CREDIT_REPORT_TIMEOUT",
    "CREDIT_REPORT_CACHE_HOURS",
    "CREDIT_REPORT_RETRY_ATTEMPTS",
    "MAX_CREDIT_REPORTS_PER_USER_PER_MONTH",
    "ENABLE_DATA_ENCRYPTION",
    "CREDIT_REPORT_ANALYSIS_PROMPTS",
    "FINANCIAL_ANALYSIS_MODEL",
    "FINANCIAL_ANALYSIS_MAX_TOKENS",
    # Statement processing constants
    "STATEMENT_PROCESSING_TIMEOUT",
    "MAX_STATEMENT_FILE_SIZE_MB",
    "SUPPORTED_STATEMENT_FORMATS",
    "PDF_PROCESSING_ENGINE",
    "COMMON_PDF_PASSWORDS",
    "STATEMENT_ANALYSIS_LOOKBACK_MONTHS",
    "MIN_TRANSACTIONS_FOR_ANALYSIS",
    "TRANSACTION_CATEGORIES",
    "STATEMENT_ANALYSIS_PROMPTS",
    "ENABLE_CATEGORY_AUTO_CLASSIFICATION",
    "ENABLE_RECURRING_PAYMENT_DETECTION",
    # Credit card constants
    "CARD_RECOMMENDATION_PROMPTS",
    "BANK_APPLICATION_URLS",
    "MAX_APPLICATION_ATTEMPTS_PER_DAY",
    # Browser automation constants
    "BROWSER_AUTOMATION_TIMEOUT",
    "BROWSER_TYPE",
    "BROWSER_HEADLESS_MODE",
    "PLAYWRIGHT_BROWSER_ARGS",
    "CREDIT_CARD_SOURCES",
    "ENABLE_AUTO_FORM_FILLING",
    "FORM_FILLING_DELAY_SECONDS",
    # All constants from constants.py will be available via import
] 