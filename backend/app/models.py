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
