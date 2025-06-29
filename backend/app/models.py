from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class GoogleToken(BaseModel):
    token: str

class ChatQuery(BaseModel):
    message: str
    jwt_token: str

class ChatResponse(BaseModel):
    reply: str

class GmailFetchPayload(BaseModel):
    jwt_token: str
    access_token: str

class FinancialTransactionResponse(BaseModel):
    """Enhanced transaction response model with subscription fields"""
    id: str
    email_id: str
    user_id: str
    date: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "INR"
    transaction_type: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    payment_method: Optional[str] = None
    account_info: Optional[str] = None
    transaction_id: Optional[str] = None
    sender: str
    subject: str
    snippet: str
    extracted_at: str
    confidence_score: float
    
    # Subscription fields
    is_subscription: bool = False
    subscription_product: Optional[str] = None
    
    # Enhanced details
    bank_details: Optional[Dict[str, Any]] = None
    upi_details: Optional[Dict[str, Any]] = None
    card_details: Optional[Dict[str, Any]] = None
    subscription_details: Optional[Dict[str, Any]] = None

class SubscriptionAnalysisResponse(BaseModel):
    """Response model for subscription analysis"""
    user_id: str
    total_subscriptions: int
    monthly_subscription_cost: float
    subscription_breakdown: Dict[str, Any]
    subscription_categories: Dict[str, int]
    active_subscriptions: List[Dict[str, Any]]
    recommendations: List[str]

# ============================================================================
# CREDIT REPORT MODELS
# ============================================================================

class CreditReportRequest(BaseModel):
    """Request model for fetching credit report"""
    jwt_token: str
    bureau: str  # "cibil", "experian", "crif", "equifax"
    pan_number: str
    date_of_birth: str  # YYYY-MM-DD format
    phone_number: str
    full_name: str
    address: Dict[str, str]  # Full address details
    consent_given: bool = True

class CreditScoreInfo(BaseModel):
    """Credit score information"""
    score: int
    range_max: int
    range_min: int
    factors_affecting_score: List[str]
    score_change: Optional[int] = None
    previous_score: Optional[int] = None

class CreditAccount(BaseModel):
    """Individual credit account information"""
    account_number: str
    account_type: str  # "Credit Card", "Personal Loan", etc.
    bank_name: str
    current_balance: float
    credit_limit: Optional[float] = None
    overdue_amount: float
    days_past_due: int
    payment_history: List[Dict[str, Any]]
    account_status: str  # "Active", "Closed", "Settled"
    date_opened: str
    date_last_payment: Optional[str] = None

class CreditEnquiry(BaseModel):
    """Credit enquiry information"""
    enquiry_date: str
    enquiring_member: str
    enquiry_purpose: str
    enquiry_amount: Optional[float] = None

class CreditReportData(BaseModel):
    """Complete credit report data"""
    report_id: str
    user_id: str
    bureau_name: str
    report_date: str
    credit_score_info: CreditScoreInfo
    personal_info: Dict[str, Any]
    accounts: List[CreditAccount]
    enquiries: List[CreditEnquiry]
    public_records: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]
    raw_report_data: Dict[str, Any]

class CreditReportInsights(BaseModel):
    """AI-generated insights from credit report"""
    user_id: str
    report_id: str
    overall_credit_health: str  # "Excellent", "Good", "Fair", "Poor"
    key_strengths: List[str]
    areas_for_improvement: List[str]
    action_recommendations: List[str]
    risk_factors: List[str]
    score_improvement_tips: List[str]
    debt_to_income_analysis: Dict[str, Any]
    credit_utilization_analysis: Dict[str, Any]
    payment_behavior_analysis: Dict[str, Any]
    generated_at: str

# ============================================================================
# ACCOUNT STATEMENT MODELS
# ============================================================================

class StatementUploadRequest(BaseModel):
    """Request model for uploading bank statement"""
    jwt_token: str
    statement_type: str  # "pdf", "csv", "excel"
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    statement_period: Dict[str, str]  # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}

class BankTransaction(BaseModel):
    """Individual bank transaction"""
    transaction_id: str
    date: str
    description: str
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    balance: float
    transaction_type: str  # "DEBIT", "CREDIT"
    reference_number: Optional[str] = None
    category: Optional[str] = None  # Auto-categorized

class StatementData(BaseModel):
    """Complete bank statement data"""
    statement_id: str
    user_id: str
    bank_name: str
    account_number: str
    account_type: str  # "Savings", "Current", "Credit Card"
    statement_period: Dict[str, str]
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    transactions: List[BankTransaction]
    uploaded_at: str

class StatementInsights(BaseModel):
    """AI-generated insights from bank statement"""
    user_id: str
    statement_id: str
    spending_analysis: Dict[str, Any]  # Category-wise spending
    income_analysis: Dict[str, Any]    # Regular income patterns
    savings_analysis: Dict[str, Any]   # Savings behavior
    cash_flow_pattern: Dict[str, Any]  # Monthly cash flow
    recurring_payments: List[Dict[str, Any]]  # EMIs, subscriptions
    unusual_transactions: List[Dict[str, Any]]  # Outliers
    financial_habits: Dict[str, Any]   # Spending habits
    recommendations: List[str]
    risk_indicators: List[str]
    generated_at: str

# ============================================================================
# CREDIT CARD RECOMMENDATION & APPLICATION MODELS
# ============================================================================

class CreditCardCriteria(BaseModel):
    """Criteria for credit card recommendations"""
    jwt_token: str
    income_range: str  # "0-25000", "25000-50000", "50000-100000", "100000+"
    credit_score_range: str  # "300-550", "550-650", "650-750", "750-900"
    preferred_category: Optional[str] = None  # "Cashback", "Rewards", "Travel", "Fuel"
    existing_cards: List[str] = []
    spending_categories: Dict[str, float] = {}  # Category-wise monthly spending
    age: int
    employment_type: str  # "Salaried", "Self-Employed", "Business"
    city: str

class CreditCardInfo(BaseModel):
    """Credit card information"""
    card_id: str
    card_name: str
    bank_name: str
    card_type: str  # "Cashback", "Rewards", "Travel", "Premium"
    annual_fee: float
    joining_fee: float
    reward_rate: Dict[str, float]  # Category-wise reward rates
    benefits: List[str]
    eligibility_criteria: Dict[str, Any]
    application_url: str
    card_image_url: Optional[str] = None
    rating: float
    user_reviews: List[Dict[str, Any]] = []

class CreditCardRecommendation(BaseModel):
    """Credit card recommendation"""
    user_id: str
    recommended_cards: List[CreditCardInfo]
    personalized_reasons: Dict[str, List[str]]  # Card ID -> reasons
    estimated_benefits: Dict[str, Dict[str, Any]]  # Card ID -> benefit calculation
    comparison_matrix: Dict[str, Dict[str, Any]]
    generated_at: str

class CreditCardApplication(BaseModel):
    """Credit card application data"""
    application_id: str
    user_id: str
    card_id: str
    bank_name: str
    card_name: str
    application_status: str  # "initiated", "in_progress", "submitted", "approved", "rejected"
    application_data: Dict[str, Any]  # Pre-filled application form data
    documents_required: List[str]
    application_url: str
    tracking_number: Optional[str] = None
    submitted_at: Optional[str] = None
    status_updates: List[Dict[str, Any]] = []

# ============================================================================
# BROWSER AUTOMATION MODELS
# ============================================================================

class BrowserAutomationRequest(BaseModel):
    """Request for browser automation tasks"""
    jwt_token: str
    task_type: str  # "scrape_cards", "fill_application", "track_status"
    parameters: Dict[str, Any]

class ScrapingResult(BaseModel):
    """Result from web scraping"""
    task_id: str
    status: str  # "success", "failed", "partial"
    data: Dict[str, Any]
    errors: List[str] = []
    scraped_at: str
    source_urls: List[str]

# ============================================================================
# ENHANCED RESPONSE MODELS
# ============================================================================

class CreditHealthResponse(BaseModel):
    """Complete credit health response"""
    user_id: str
    credit_score: int
    credit_report_summary: Dict[str, Any]
    statement_insights: Dict[str, Any]
    recommended_cards: List[CreditCardInfo]
    financial_goals: List[str]
    action_plan: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    generated_at: str
