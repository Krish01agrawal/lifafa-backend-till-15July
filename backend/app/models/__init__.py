from .auth import User, UserCreate, UserUpdate, LoginRequest, LoginResponse
from .gmail import Email, EmailThread, EmailQuery, EmailResponse, GmailCredentials, GoogleToken, GmailFetchPayload
# Temporarily skip importing from financial.py due to syntax error
# from .financial import FinancialTransaction, FinancialSummary, FinancialQuery, StatementUploadRequest

# Create stub models for all financial and statement processing models
from .common import BaseModel, TimestampMixin
from pydantic import Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

class StatementUploadRequest(BaseModel):
    """Request model for bank statement upload."""
    jwt_token: str = Field(description="JWT authentication token")
    bank_name: Optional[str] = Field(default=None, description="Bank name")
    account_number: Optional[str] = Field(default=None, description="Account number")
    statement_period_from: Optional[str] = Field(default=None, description="Statement period start")
    statement_period_to: Optional[str] = Field(default=None, description="Statement period end")
    file_format: Optional[str] = Field(default="pdf", description="Statement file format")

class FinancialTransaction(TimestampMixin):
    """Stub for financial transaction model."""
    id: str = Field(description="Transaction identifier")
    email_id: str = Field(description="Source email ID")
    user_id: str = Field(description="User ID")
    amount: Decimal = Field(description="Transaction amount")
    description: str = Field(description="Transaction description")
    transaction_date: datetime = Field(description="Transaction date")
    sender: str = Field(description="Email sender")
    subject: str = Field(description="Email subject")

class FinancialSummary(BaseModel):
    """Stub for financial summary model."""
    user_id: str = Field(description="User ID")
    total_transactions: int = Field(description="Total transactions")
    total_spent: Decimal = Field(description="Total spent")
    total_received: Decimal = Field(description="Total received")

class FinancialQuery(BaseModel):
    """Stub for financial query model."""
    query: str = Field(description="Search query")
    user_id: str = Field(description="User ID")

class BankTransaction(BaseModel):
    """Stub for bank transaction model."""
    transaction_id: str = Field(description="Transaction identifier")
    date: str = Field(description="Transaction date")
    description: str = Field(description="Transaction description")
    amount: float = Field(description="Transaction amount")
    balance: Optional[float] = Field(default=None, description="Account balance")
    transaction_type: str = Field(description="Transaction type")
    category: Optional[str] = Field(default=None, description="Transaction category")

class StatementData(TimestampMixin):
    """Stub for statement data model."""
    statement_id: str = Field(description="Statement identifier")
    user_id: str = Field(description="User identifier")
    bank_name: str = Field(description="Bank name")
    account_number: str = Field(description="Account number")
    transactions: List[BankTransaction] = Field(description="Transactions")
    total_credits: float = Field(description="Total credits")
    total_debits: float = Field(description="Total debits")
    transaction_count: int = Field(description="Transaction count")

class StatementInsights(TimestampMixin):
    """Stub for statement insights model."""
    insights_id: str = Field(description="Insights identifier")
    statement_id: str = Field(description="Statement ID")
    user_id: str = Field(description="User identifier")
    spending_by_category: Dict[str, float] = Field(description="Spending by category")
    recommendations: List[str] = Field(description="Recommendations")
    financial_health_score: int = Field(description="Health score")

# Credit card service models
class CreditCardInfo(BaseModel):
    """Stub for credit card info model."""
    card_id: str = Field(description="Card identifier")
    card_name: str = Field(description="Card name")
    bank_name: str = Field(description="Bank name")
    annual_fee: float = Field(description="Annual fee")
    benefits: List[str] = Field(description="Card benefits")

class CreditCardApplication(TimestampMixin):
    """Stub for credit card application model."""
    application_id: str = Field(description="Application identifier")
    user_id: str = Field(description="User identifier")
    card_id: str = Field(description="Card identifier")
    status: str = Field(description="Application status")
    application_data: Dict[str, Any] = Field(description="Application data")

class CreditHealthResponse(BaseModel):
    """Stub for credit health response model."""
    user_id: str = Field(description="User identifier")
    overall_score: int = Field(description="Overall credit health score")
    recommendations: List[str] = Field(description="Health recommendations")
    risk_factors: List[str] = Field(description="Risk factors")

# Browser automation models
class ScrapingResult(TimestampMixin):
    """Stub for scraping result model."""
    task_id: str = Field(description="Task identifier")
    status: str = Field(description="Scraping status")
    data: Dict[str, Any] = Field(description="Scraped data")
    errors: List[str] = Field(description="Scraping errors")
    scraped_at: str = Field(description="Scraping timestamp")
    source_urls: List[str] = Field(description="Source URLs")
from .credit import CreditReport, CreditScore, CreditAccount, CreditInsights, CreditReportRequest, CreditCardCriteria, CreditInquiry, CreditCardRecommendation
from .common import BaseModel, ResponseModel, ErrorResponse, PaginatedResponse, BrowserAutomationRequest

# Aliases for backward compatibility with credit_report_service.py
CreditReportData = CreditReport
CreditReportInsights = CreditInsights
CreditScoreInfo = CreditScore
CreditEnquiry = CreditInquiry

__all__ = [
    # Auth Models
    "User", "UserCreate", "UserUpdate", "LoginRequest", "LoginResponse",
    
    # Gmail Models
    "Email", "EmailThread", "EmailQuery", "EmailResponse", "GmailCredentials", "GoogleToken", "GmailFetchPayload",
    
    # Financial Models
    "FinancialTransaction", "FinancialSummary", "FinancialQuery", "StatementUploadRequest", "BankTransaction", "StatementData", "StatementInsights",
    # Credit card models
    "CreditCardInfo", "CreditCardApplication", "CreditHealthResponse",
    # Browser automation models
    "ScrapingResult",
    
    # Credit Models
    "CreditReport", "CreditScore", "CreditAccount", "CreditInsights", "CreditReportRequest", "CreditCardCriteria", "CreditInquiry", "CreditCardRecommendation",
    # Credit Model Aliases
    "CreditReportData", "CreditReportInsights", "CreditScoreInfo", "CreditEnquiry",
    
    # Common Models
    "BaseModel", "ResponseModel", "ErrorResponse", "PaginatedResponse", "BrowserAutomationRequest",
] 