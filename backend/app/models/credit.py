"""
Credit Models
=============

This module contains models for credit reports, scores, accounts, and credit analysis.
"""

from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from .common import BaseModel, TimestampMixin
from ..config.constants import CreditBureau


class CreditScore(BaseModel):
    """Credit score information."""
    
    score: int = Field(ge=300, le=900, description="Credit score")
    score_range: str = Field(description="Score range (e.g., 300-900)")
    rating: str = Field(description="Credit rating (Excellent/Good/Fair/Poor)")
    bureau: CreditBureau = Field(description="Credit bureau")
    score_date: datetime = Field(description="Score calculation date")
    
    # Score Change
    previous_score: Optional[int] = Field(default=None, description="Previous credit score")
    score_change: Optional[int] = Field(default=None, description="Score change from previous")
    
    # Factors
    positive_factors: List[str] = Field(default_factory=list, description="Factors improving score")
    negative_factors: List[str] = Field(default_factory=list, description="Factors reducing score")
    
    class Config:
        schema_extra = {
            "example": {
                "score": 750,
                "score_range": "300-900",
                "rating": "Good",
                "bureau": "cibil",
                "score_date": "2024-01-15T00:00:00Z",
                "previous_score": 725,
                "score_change": 25,
                "positive_factors": ["Regular payments", "Low credit utilization"],
                "negative_factors": ["High number of recent inquiries"]
            }
        }


class CreditAccount(BaseModel):
    """Individual credit account information."""
    
    account_id: str = Field(description="Account identifier")
    account_number: str = Field(description="Account number (masked)")
    account_type: str = Field(description="Account type (Credit Card, Personal Loan, etc.)")
    bank_name: str = Field(description="Financial institution name")
    
    # Account Status
    account_status: str = Field(description="Account status (Active/Closed/Settled)")
    date_opened: datetime = Field(description="Account opening date")
    date_closed: Optional[datetime] = Field(default=None, description="Account closure date")
    
    # Financial Details
    credit_limit: Optional[Decimal] = Field(default=None, description="Credit limit")
    current_balance: Decimal = Field(description="Current outstanding balance")
    available_credit: Optional[Decimal] = Field(default=None, description="Available credit")
    
    # Payment Information
    minimum_due: Optional[Decimal] = Field(default=None, description="Minimum amount due")
    payment_due_date: Optional[datetime] = Field(default=None, description="Next payment due date")
    last_payment_date: Optional[datetime] = Field(default=None, description="Last payment date")
    last_payment_amount: Optional[Decimal] = Field(default=None, description="Last payment amount")
    
    # Overdue Information
    overdue_amount: Decimal = Field(default=0, description="Overdue amount")
    days_past_due: int = Field(default=0, description="Days past due")
    
    # Payment History (last 12 months)
    payment_history: List[str] = Field(default_factory=list, description="Payment history (XXX format)")
    
    # Account Behavior
    highest_balance: Optional[Decimal] = Field(default=None, description="Highest balance ever")
    average_balance: Optional[Decimal] = Field(default=None, description="Average balance")
    utilization_rate: Optional[float] = Field(default=None, description="Credit utilization rate")
    
    class Config:
        schema_extra = {
            "example": {
                "account_id": "acc_123",
                "account_number": "****1234",
                "account_type": "Credit Card",
                "bank_name": "HDFC Bank",
                "account_status": "Active",
                "date_opened": "2020-03-15T00:00:00Z",
                "credit_limit": 100000.00,
                "current_balance": 25000.00,
                "available_credit": 75000.00,
                "overdue_amount": 0.00,
                "days_past_due": 0,
                "utilization_rate": 0.25
            }
        }


class CreditInquiry(BaseModel):
    """Credit inquiry information."""
    
    inquiry_id: str = Field(description="Inquiry identifier")
    inquiry_date: datetime = Field(description="Inquiry date")
    inquiring_member: str = Field(description="Organization that made inquiry")
    inquiry_purpose: str = Field(description="Purpose of inquiry")
    inquiry_type: str = Field(description="Type of inquiry (hard/soft)")
    inquiry_amount: Optional[Decimal] = Field(default=None, description="Loan amount inquired for")
    
    class Config:
        schema_extra = {
            "example": {
                "inquiry_id": "inq_123",
                "inquiry_date": "2024-01-10T00:00:00Z",
                "inquiring_member": "HDFC Bank",
                "inquiry_purpose": "Credit Card",
                "inquiry_type": "hard",
                "inquiry_amount": 50000.00
            }
        }


class PublicRecord(BaseModel):
    """Public record information."""
    
    record_id: str = Field(description="Record identifier")
    record_type: str = Field(description="Type of public record")
    record_date: datetime = Field(description="Record date")
    court_name: Optional[str] = Field(default=None, description="Court name")
    case_number: Optional[str] = Field(default=None, description="Case number")
    status: str = Field(description="Record status")
    amount: Optional[Decimal] = Field(default=None, description="Amount involved")
    
    class Config:
        schema_extra = {
            "example": {
                "record_id": "rec_123",
                "record_type": "Civil Suit",
                "record_date": "2023-05-15T00:00:00Z",
                "court_name": "Delhi High Court",
                "case_number": "CS123/2023",
                "status": "Disposed",
                "amount": 15000.00
            }
        }


class CreditReport(TimestampMixin):
    """Complete credit report."""
    
    report_id: str = Field(description="Unique report identifier")
    user_id: str = Field(description="User identifier")
    bureau: CreditBureau = Field(description="Credit bureau")
    report_date: datetime = Field(description="Report generation date")
    
    # Personal Information
    personal_info: Dict[str, Any] = Field(description="Personal information")
    
    # Credit Score
    credit_score: CreditScore = Field(description="Credit score information")
    
    # Accounts
    accounts: List[CreditAccount] = Field(description="Credit accounts")
    
    # Inquiries
    inquiries: List[CreditInquiry] = Field(description="Credit inquiries")
    
    # Public Records
    public_records: List[PublicRecord] = Field(default_factory=list, description="Public records")
    
    # Summary Statistics
    total_accounts: int = Field(description="Total number of accounts")
    active_accounts: int = Field(description="Number of active accounts")
    total_credit_limit: Decimal = Field(description="Total credit limit")
    total_outstanding: Decimal = Field(description="Total outstanding balance")
    overall_utilization: float = Field(description="Overall credit utilization")
    
    # Payment Summary
    accounts_never_late: int = Field(description="Accounts with no late payments")
    accounts_with_late_payments: int = Field(description="Accounts with late payments")
    
    # Inquiry Summary
    inquiries_last_6_months: int = Field(description="Inquiries in last 6 months")
    inquiries_last_12_months: int = Field(description="Inquiries in last 12 months")
    
    # Age of Credit
    oldest_account_age_months: int = Field(description="Age of oldest account in months")
    average_account_age_months: int = Field(description="Average age of accounts in months")
    
    class Config:
        schema_extra = {
            "example": {
                "report_id": "rpt_123456",
                "user_id": "user_789",
                "bureau": "cibil",
                "report_date": "2024-01-15T10:30:00Z",
                "total_accounts": 5,
                "active_accounts": 3,
                "total_credit_limit": 500000.00,
                "total_outstanding": 125000.00,
                "overall_utilization": 0.25,
                "accounts_never_late": 4,
                "accounts_with_late_payments": 1,
                "inquiries_last_6_months": 2,
                "oldest_account_age_months": 48
            }
        }


class CreditInsights(TimestampMixin):
    """AI-generated credit insights and recommendations."""
    
    insights_id: str = Field(description="Insights identifier")
    user_id: str = Field(description="User identifier")
    report_id: str = Field(description="Associated credit report ID")
    
    # Overall Assessment
    credit_health_score: float = Field(ge=0.0, le=10.0, description="Credit health score (0-10)")
    credit_health_rating: str = Field(description="Credit health rating")
    
    # Key Strengths
    strengths: List[str] = Field(description="Credit profile strengths")
    
    # Areas for Improvement
    improvement_areas: List[str] = Field(description="Areas needing improvement")
    
    # Action Recommendations
    immediate_actions: List[str] = Field(description="Immediate actions to take")
    short_term_goals: List[str] = Field(description="Short-term goals (3-6 months)")
    long_term_goals: List[str] = Field(description="Long-term goals (1-2 years)")
    
    # Risk Analysis
    risk_factors: List[str] = Field(description="Risk factors identified")
    risk_level: str = Field(description="Overall risk level")
    
    # Score Improvement Potential
    score_improvement_potential: int = Field(description="Potential score improvement")
    estimated_timeframe: str = Field(description="Estimated timeframe for improvement")
    
    # Specific Recommendations
    utilization_recommendations: List[str] = Field(description="Credit utilization recommendations")
    payment_recommendations: List[str] = Field(description="Payment behavior recommendations")
    account_recommendations: List[str] = Field(description="Account management recommendations")
    
    # Monitoring Suggestions
    monitoring_frequency: str = Field(description="Recommended monitoring frequency")
    key_metrics_to_watch: List[str] = Field(description="Key metrics to monitor")
    
    class Config:
        schema_extra = {
            "example": {
                "insights_id": "ins_123",
                "user_id": "user_789",
                "report_id": "rpt_123456",
                "credit_health_score": 7.5,
                "credit_health_rating": "Good",
                "strengths": ["Consistent payment history", "Low credit utilization"],
                "improvement_areas": ["Reduce number of recent inquiries", "Increase credit history length"],
                "immediate_actions": ["Pay down credit card balances", "Avoid new credit applications"],
                "risk_level": "Low",
                "score_improvement_potential": 50,
                "estimated_timeframe": "6-12 months"
            }
        }


class CreditCardRecommendation(BaseModel):
    """Credit card recommendation based on credit profile."""
    
    recommendation_id: str = Field(description="Recommendation identifier")
    user_id: str = Field(description="User identifier")
    
    # Card Information
    card_name: str = Field(description="Credit card name")
    bank_name: str = Field(description="Issuing bank")
    card_type: str = Field(description="Card type (Cashback/Rewards/Travel)")
    
    # Eligibility
    approval_probability: float = Field(ge=0.0, le=1.0, description="Approval probability")
    eligibility_status: str = Field(description="Eligibility status")
    
    # Features
    annual_fee: Decimal = Field(description="Annual fee")
    joining_fee: Decimal = Field(description="Joining fee")
    reward_rate: float = Field(description="Reward rate percentage")
    key_benefits: List[str] = Field(description="Key card benefits")
    
    # Recommendation Reasons
    recommendation_reasons: List[str] = Field(description="Why this card is recommended")
    suitability_score: float = Field(ge=0.0, le=10.0, description="Suitability score")
    
    # Comparison
    better_than_current: Optional[bool] = Field(default=None, description="Better than current cards")
    potential_savings: Optional[Decimal] = Field(default=None, description="Potential annual savings")
    
    class Config:
        schema_extra = {
            "example": {
                "recommendation_id": "rec_123",
                "user_id": "user_789",
                "card_name": "HDFC Regalia Gold",
                "bank_name": "HDFC Bank",
                "card_type": "Rewards",
                "approval_probability": 0.85,
                "eligibility_status": "High",
                "annual_fee": 2500.00,
                "reward_rate": 2.5,
                "suitability_score": 8.5,
                "potential_savings": 5000.00
            }
        }


class CreditMonitoring(TimestampMixin):
    """Credit monitoring alert."""
    
    alert_id: str = Field(description="Alert identifier")
    user_id: str = Field(description="User identifier")
    alert_type: str = Field(description="Type of alert")
    severity: str = Field(description="Alert severity level")
    title: str = Field(description="Alert title")
    description: str = Field(description="Alert description")
    recommendation: str = Field(description="Recommended action")
    is_read: bool = Field(default=False, description="Whether alert has been read")
    
    class Config:
        schema_extra = {
            "example": {
                "alert_id": "alert_123",
                "user_id": "user_789",
                "alert_type": "score_change",
                "severity": "medium",
                "title": "Credit Score Increased",
                "description": "Your credit score increased by 25 points to 750",
                "recommendation": "Keep maintaining good payment habits",
                "is_read": False
            }
        }


class CreditReportRequest(BaseModel):
    """Request model for fetching credit reports."""
    
    jwt_token: str = Field(description="JWT authentication token")
    bureau: str = Field(description="Credit bureau name (cibil/experian/crif/equifax)")
    report_type: Optional[str] = Field(default="standard", description="Type of credit report")
    include_score: bool = Field(default=True, description="Whether to include credit score")
    include_accounts: bool = Field(default=True, description="Whether to include account details")
    include_inquiries: bool = Field(default=True, description="Whether to include credit inquiries")
    
    class Config:
        schema_extra = {
            "example": {
                "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "bureau": "cibil",
                "report_type": "standard",
                "include_score": True,
                "include_accounts": True,
                "include_inquiries": True
            }
        }


class CreditCardCriteria(BaseModel):
    """Credit card recommendation criteria."""
    
    jwt_token: str = Field(description="JWT authentication token")
    income_range: Optional[str] = Field(default=None, description="Monthly income range")
    credit_score_range: Optional[str] = Field(default=None, description="Credit score range")
    preferred_features: List[str] = Field(default_factory=list, description="Preferred card features")
    spending_categories: List[str] = Field(default_factory=list, description="Primary spending categories")
    annual_fee_preference: Optional[str] = Field(default="no_preference", description="Annual fee preference")
    
    class Config:
        schema_extra = {
            "example": {
                "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "income_range": "50000-100000",
                "credit_score_range": "700-800",
                "preferred_features": ["cashback", "travel_rewards", "no_annual_fee"],
                "spending_categories": ["dining", "shopping", "fuel"],
                "annual_fee_preference": "low"
            }
        } 