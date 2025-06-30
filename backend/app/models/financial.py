"""
Financial Models
================

This module contains models for financial transactions, summaries, and analysis.
"""

from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from .common import BaseModel, TimestampMixin, SearchQuery
from ..config.constants import TransactionType


class BankDetails(BaseModel):
    """Bank account details for transactions."""
    
    bank_name: Optional[str] = Field(default=None, description="Bank name")
    account_number: Optional[str] = Field(default=None, description="Account number (masked)")
    account_type: Optional[str] = Field(default=None, description="Account type (savings/current)")
    ifsc_code: Optional[str] = Field(default=None, description="IFSC code")
    branch: Optional[str] = Field(default=None, description="Branch name")


class UPIDetails(BaseModel):
    """UPI transaction details."""
    
    upi_id: Optional[str] = Field(default=None, description="UPI ID")
    transaction_id: Optional[str] = Field(default=None, description="UPI transaction ID")
    reference_id: Optional[str] = Field(default=None, description="UPI reference ID")
    app_name: Optional[str] = Field(default=None, description="UPI app used")


class CardDetails(BaseModel):
    """Credit/Debit card details."""
    
    card_number: Optional[str] = Field(default=None, description="Card number (masked)")
    card_type: Optional[str] = Field(default=None, description="Card type (credit/debit)")
    bank_name: Optional[str] = Field(default=None, description="Issuing bank")
    card_network: Optional[str] = Field(default=None, description="Card network (Visa/Mastercard)")


class SubscriptionDetails(BaseModel):
    """Subscription service details."""
    
    service_name: Optional[str] = Field(default=None, description="Subscription service name")
    plan_type: Optional[str] = Field(default=None, description="Subscription plan")
    billing_cycle: Optional[str] = Field(default=None, description="Billing cycle (monthly/yearly)")
    next_billing_date: Optional[datetime] = Field(default=None, description="Next billing date")
    cancellation_date: Optional[datetime] = Field(default=None, description="Cancellation date if applicable")


class FinancialTransaction(TimestampMixin):
    """Financial transaction model with comprehensive details."""
    
    id: str = Field(description="Unique transaction identifier")
    email_id: str = Field(description="Source email ID")
    user_id: str = Field(description="User ID")
    
    # Basic Transaction Info
    amount: Decimal = Field(description="Transaction amount")
    currency: str = Field(default="INR", description="Currency code")
    transaction_type: TransactionType = Field(description="Transaction type")
    description: str = Field(description="Transaction description")
    
    # Transaction Details
    merchant: Optional[str] = Field(default=None, description="Merchant name")
    category: Optional[str] = Field(default=None, description="Transaction category")
    subcategory: Optional[str] = Field(default=None, description="Transaction subcategory")
    
    # Date Information
    transaction_date: datetime = Field(description="Transaction date")
    processed_date: Optional[datetime] = Field(default=None, description="Processing date")
    
    # Payment Method Details
    payment_method: Optional[str] = Field(default=None, description="Payment method")
    bank_details: Optional[BankDetails] = Field(default=None, description="Bank account details")
    upi_details: Optional[UPIDetails] = Field(default=None, description="UPI transaction details")
    card_details: Optional[CardDetails] = Field(default=None, description="Card details")
    
    # Email Source Info
    sender: str = Field(description="Email sender")
    subject: str = Field(description="Email subject")
    snippet: str = Field(description="Email snippet")
    
    # Processing Metadata
    confidence_score: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field(description="Extraction method used")
    
    # Subscription Info
    is_subscription: bool = Field(default=False, description="Whether this is a subscription payment")
    subscription_details: Optional[SubscriptionDetails] = Field(default=None, description="Subscription details")
    
    # Location Info
    location: Optional[str] = Field(default=None, description="Transaction location")
    country: Optional[str] = Field(default=None, description="Transaction country")
    
    # Status
    status: str = Field(default="completed", description="Transaction status")
    is_recurring: bool = Field(default=False, description="Whether transaction is recurring")
    
    # Tags and Notes
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    notes: Optional[str] = Field(default=None, description="User notes")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "txn_123456",
                "email_id": "email_789",
                "user_id": "user_456",
                "amount": 1250.50,
                "currency": "INR",
                "transaction_type": "debit",
                "description": "Payment to Amazon",
                "merchant": "Amazon",
                "category": "Shopping",
                "transaction_date": "2024-01-15T10:30:00Z",
                "payment_method": "Credit Card",
                "confidence_score": 0.95,
                "extraction_method": "ai_extraction"
            }
        }


class FinancialSummary(BaseModel):
    """Financial summary for a user."""
    
    user_id: str = Field(description="User ID")
    period_start: datetime = Field(description="Summary period start")
    period_end: datetime = Field(description="Summary period end")
    
    # Transaction Counts
    total_transactions: int = Field(description="Total number of transactions")
    debit_transactions: int = Field(description="Number of debit transactions")
    credit_transactions: int = Field(description="Number of credit transactions")
    
    # Amount Summaries
    total_spent: Decimal = Field(description="Total amount spent")
    total_received: Decimal = Field(description="Total amount received")
    net_flow: Decimal = Field(description="Net cash flow")
    
    # Category Breakdown
    spending_by_category: Dict[str, Decimal] = Field(description="Spending by category")
    income_by_source: Dict[str, Decimal] = Field(description="Income by source")
    
    # Top Merchants
    top_merchants: List[Dict[str, Any]] = Field(description="Top merchants by spending")
    
    # Monthly Trends
    monthly_spending: List[Dict[str, Any]] = Field(description="Monthly spending trends")
    monthly_income: List[Dict[str, Any]] = Field(description="Monthly income trends")
    
    # Subscription Analysis
    subscription_count: int = Field(default=0, description="Number of active subscriptions")
    monthly_subscription_cost: Decimal = Field(default=0, description="Monthly subscription cost")
    subscription_breakdown: List[Dict[str, Any]] = Field(default_factory=list, description="Subscription details")
    
    # Insights
    insights: List[str] = Field(default_factory=list, description="AI-generated insights")
    recommendations: List[str] = Field(default_factory=list, description="Financial recommendations")
    
    # Risk Analysis
    risk_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Financial risk score")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors identified")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_456",
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-01-31T23:59:59Z",
                "total_transactions": 45,
                "debit_transactions": 32,
                "credit_transactions": 13,
                "total_spent": 12500.75,
                "total_received": 8750.00,
                "net_flow": -3750.75,
                "subscription_count": 5,
                "monthly_subscription_cost": 1250.00,
                "risk_score": 3.2
            }
        }


class FinancialQuery(SearchQuery):
    """Financial transaction search query."""
    
    # Amount filters
    amount_min: Optional[Decimal] = Field(default=None, description="Minimum transaction amount")
    amount_max: Optional[Decimal] = Field(default=None, description="Maximum transaction amount")
    
    # Date filters
    date_from: Optional[datetime] = Field(default=None, description="Transaction date from")
    date_to: Optional[datetime] = Field(default=None, description="Transaction date to")
    
    # Transaction filters
    transaction_type: Optional[TransactionType] = Field(default=None, description="Transaction type")
    category: Optional[str] = Field(default=None, description="Transaction category")
    merchant: Optional[str] = Field(default=None, description="Merchant name")
    payment_method: Optional[str] = Field(default=None, description="Payment method")
    
    # Subscription filters
    is_subscription: Optional[bool] = Field(default=None, description="Filter subscription transactions")
    is_recurring: Optional[bool] = Field(default=None, description="Filter recurring transactions")
    
    # Status filters
    status: Optional[str] = Field(default=None, description="Transaction status")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Amazon purchase",
                "amount_min": 100.00,
                "amount_max": 5000.00,
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "transaction_type": "debit",
                "category": "Shopping",
                "is_subscription": False,
                "page": 1,
                "per_page": 20
            }
        }


class SpendingInsight(BaseModel):
    """Individual spending insight."""
    
    insight_type: str = Field(description="Type of insight")
    title: str = Field(description="Insight title")
    description: str = Field(description="Detailed description")
    impact: str = Field(description="Impact level (low/medium/high)")
    recommendation: str = Field(description="Recommendation")
    amount_involved: Optional[Decimal] = Field(default=None, description="Amount involved")
    frequency: Optional[str] = Field(default=None, description="Frequency of occurrence")
    trend: Optional[str] = Field(default=None, description="Trend direction")
    
    class Config:
        schema_extra = {
            "example": {
                "insight_type": "spending_spike",
                "title": "Unusual Spending on Dining",
                "description": "Your dining expenses increased by 40% this month",
                "impact": "medium",
                "recommendation": "Consider setting a monthly budget for dining",
                "amount_involved": 2500.00,
                "frequency": "monthly",
                "trend": "increasing"
            }
        }


class BudgetRecommendation(BaseModel):
    """Budget recommendation based on spending patterns."""
    
    category: str = Field(description="Spending category")
    current_spending: Decimal = Field(description="Current monthly spending")
    recommended_budget: Decimal = Field(description="Recommended monthly budget")
    savings_potential: Decimal = Field(description="Potential monthly savings")
    confidence: float = Field(ge=0.0, le=1.0, description="Recommendation confidence")
    reasoning: str = Field(description="Reasoning for recommendation")
    
    class Config:
        schema_extra = {
            "example": {
                "category": "Entertainment",
                "current_spending": 3500.00,
                "recommended_budget": 2500.00,
                "savings_potential": 1000.00,
                "confidence": 0.85,
                "reasoning": "Based on your spending pattern, reducing entertainment expenses by 30% is achievable"
            }
        }


class FinancialGoal(TimestampMixin):
    """User financial goal."""
    
    id: str = Field(description="Goal ID")
    user_id: str = Field(description="User ID")
    title: str = Field(description="Goal title")
    description: Optional[str] = Field(default=None, description="Goal description")
    target_amount: Decimal = Field(description="Target amount")
    current_amount: Decimal = Field(default=0, description="Current saved amount")
    target_date: datetime = Field(description="Target completion date")
    category: str = Field(description="Goal category")
    priority: str = Field(description="Priority level")
    status: str = Field(default="active", description="Goal status")
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.target_amount <= 0:
            return 0.0
        return min(100.0, (float(self.current_amount) / float(self.target_amount)) * 100)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "goal_789",
                "user_id": "user_123",
                "title": "Emergency Fund",
                "description": "Save for 6 months of expenses",
                "target_amount": 150000.00,
                "current_amount": 45000.00,
                "target_date": "2024-12-31T00:00:00Z",
                "category": "savings",
                "priority": "high",
                "status": "active"
            }
        }


class StatementUploadRequest(BaseModel):
    """Request model for bank statement upload."""
    
    jwt_token: str = Field(description="JWT authentication token")
    bank_name: Optional[str] = Field(default=None, description="Bank name")
    account_number: Optional[str] = Field(default=None, description="Account number (masked)")
    statement_period_from: Optional[str] = Field(default=None, description="Statement period start date")
    statement_period_to: Optional[str] = Field(default=None, description="Statement period end date")
    file_format: Optional[str] = Field(default="pdf", description="Statement file format")
    
    class Config:
        schema_extra = {
            "example": {
                "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "bank_name": "HDFC Bank",
                "account_number": "****1234",
                "statement_period_from": "2024-01-01",
                "statement_period_to": "2024-01-31",
                "file_format": "pdf"
            }
        }


class BankTransaction(BaseModel):
    """Individual bank transaction from statement."""
    
    transaction_id: str = Field(description="Transaction identifier")
    date: str = Field(description="Transaction date")
    description: str = Field(description="Transaction description")
    amount: float = Field(description="Transaction amount")
    balance: Optional[float] = Field(default=None, description="Account balance after transaction")
    transaction_type: str = Field(description="Transaction type (CREDIT/DEBIT)")
    category: Optional[str] = Field(default=None, description="Transaction category")
    reference_number: Optional[str] = Field(default=None, description="Bank reference number")
    
    class Config:
        schema_extra = {
            "example": {
                "transaction_id": "txn_001",
                "date": "2024-01-15",
                "description": "UPI-Amazon Payment",
                "amount": -1250.50,
                "balance": 15750.00,
                "transaction_type": "DEBIT",
                "category": "shopping"
            }
        }


class StatementData(TimestampMixin):
    """Bank statement data container."""
    
    statement_id: str = Field(description="Statement identifier")
    user_id: str = Field(description="User identifier")
    bank_name: str = Field(description="Bank name")
    account_number: str = Field(description="Account number (masked)")
    statement_period_from: str = Field(description="Statement period start")
    statement_period_to: str = Field(description="Statement period end")
    
    # Transactions
    transactions: List[BankTransaction] = Field(description="Statement transactions")
    
    # Summary
    opening_balance: Optional[float] = Field(default=None, description="Opening balance")
    closing_balance: Optional[float] = Field(default=None, description="Closing balance")
    total_credits: float = Field(description="Total credit amount")
    total_debits: float = Field(description="Total debit amount")
    transaction_count: int = Field(description="Total number of transactions")
    
    class Config:
        schema_extra = {
            "example": {
                "statement_id": "stmt_123",
                "user_id": "user_456",
                "bank_name": "HDFC Bank",
                "account_number": "****1234",
                "statement_period_from": "2024-01-01",
                "statement_period_to": "2024-01-31",
                "opening_balance": 25000.00,
                "closing_balance": 22750.00,
                "total_credits": 8500.00,
                "total_debits": 10750.00,
                "transaction_count": 45
            }
        }


class StatementInsights(TimestampMixin):
    """AI-generated insights from bank statement analysis."""
    
    insights_id: str = Field(description="Insights identifier")
    statement_id: str = Field(description="Associated statement ID")
    user_id: str = Field(description="User identifier")
    
    # Spending Analysis
    spending_by_category: Dict[str, float] = Field(description="Spending breakdown by category")
    top_merchants: List[Dict[str, Any]] = Field(description="Top merchants by spending")
    average_transaction_amount: float = Field(description="Average transaction amount")
    
    # Income Analysis
    income_sources: List[Dict[str, Any]] = Field(description="Identified income sources")
    total_income: float = Field(description="Total income in period")
    
    # Financial Health
    cash_flow: float = Field(description="Net cash flow")
    savings_rate: float = Field(description="Savings rate percentage")
    financial_health_score: int = Field(ge=0, le=100, description="Financial health score")
    
    # Patterns and Insights
    recurring_payments: List[Dict[str, Any]] = Field(description="Detected recurring payments")
    unusual_transactions: List[Dict[str, Any]] = Field(description="Unusual transaction patterns")
    spending_trends: Dict[str, Any] = Field(description="Spending trend analysis")
    
    # Recommendations
    recommendations: List[str] = Field(description="AI-generated recommendations")
    cost_saving_opportunities: List[Dict[str, Any]] = Field(description="Cost saving opportunities")
    
    # Risk Analysis
    risk_indicators: List[str] = Field(description="Financial risk indicators")
    
    class Config:
        schema_extra = {
            "example": {
                "insights_id": "ins_123",
                "statement_id": "stmt_123",
                "user_id": "user_456",
                "cash_flow": -2250.00,
                "savings_rate": 15.5,
                "financial_health_score": 72,
                "total_income": 45000.00,
                "recommendations": [
                    "Consider reducing dining out expenses",
                    "Set up automatic savings for emergency fund"
                                ]
            }
        }  