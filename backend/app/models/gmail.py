"""
Gmail Models
============

This module contains models for Gmail emails, threads, queries, and related operations.
"""

from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from .common import BaseModel, TimestampMixin, SearchQuery, PaginatedResponse
from ..config.constants import EmailType, ProcessingStatus


class EmailAttachment(BaseModel):
    """Email attachment model."""
    
    filename: str = Field(description="Attachment filename")
    content_type: str = Field(description="MIME content type")
    size: int = Field(description="Attachment size in bytes")
    attachment_id: Optional[str] = Field(default=None, description="Gmail attachment ID")
    is_financial: bool = Field(default=False, description="Whether attachment contains financial data")


class EmailLabel(BaseModel):
    """Gmail label model."""
    
    id: str = Field(description="Label ID")
    name: str = Field(description="Label name")
    type: str = Field(description="Label type (system/user)")


class Email(TimestampMixin):
    """Email model with comprehensive metadata."""
    
    id: str = Field(description="Unique email identifier (Gmail message ID)")
    thread_id: str = Field(description="Gmail thread ID")
    user_id: str = Field(description="Owner user ID")
    
    # Basic Email Info
    subject: str = Field(description="Email subject")
    sender: str = Field(description="Sender email address") 
    sender_name: Optional[str] = Field(default=None, description="Sender display name")
    recipient: str = Field(description="Primary recipient email")
    recipients: List[str] = Field(default_factory=list, description="All recipients")
    cc: List[str] = Field(default_factory=list, description="CC recipients")
    bcc: List[str] = Field(default_factory=list, description="BCC recipients")
    
    # Content
    body: str = Field(description="Email body content")
    snippet: str = Field(description="Email snippet/preview")
    html_body: Optional[str] = Field(default=None, description="HTML email body")
    
    # Metadata
    date: datetime = Field(description="Email date/time")
    labels: List[EmailLabel] = Field(default_factory=list, description="Gmail labels")
    attachments: List[EmailAttachment] = Field(default_factory=list, description="Email attachments")
    
    # Classification
    email_type: EmailType = Field(default=EmailType.PERSONAL, description="Email classification")
    importance: int = Field(default=5, ge=1, le=10, description="Email importance score (1-10)")
    is_read: bool = Field(default=False, description="Whether email has been read")
    is_starred: bool = Field(default=False, description="Whether email is starred")
    is_spam: bool = Field(default=False, description="Whether email is spam")
    
    # Financial Data
    is_financial: bool = Field(default=False, description="Whether email contains financial data")
    financial_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Extracted financial data")
    
    # Processing Status
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, description="Processing status")
    mem0_uploaded: bool = Field(default=False, description="Whether uploaded to Mem0")
    extraction_confidence: Optional[float] = Field(default=None, description="Data extraction confidence")
    
    # Storage Optimization
    is_compressed: bool = Field(default=False, description="Whether content is compressed")
    original_size: Optional[int] = Field(default=None, description="Original email size in bytes")
    compressed_size: Optional[int] = Field(default=None, description="Compressed size in bytes")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "gmail_msg_123",
                "thread_id": "gmail_thread_456",
                "user_id": "google_789",
                "subject": "Your Transaction Receipt",
                "sender": "noreply@bank.com",
                "sender_name": "MyBank",
                "recipient": "user@example.com",
                "body": "Your transaction of $100 has been processed...",
                "snippet": "Your transaction of $100 has been processed",
                "email_type": "financial",
                "importance": 8,
                "is_financial": True,
                "date": "2024-01-15T10:30:00Z"
            }
        }


class EmailThread(BaseModel):
    """Email thread model containing multiple related emails."""
    
    id: str = Field(description="Thread ID")
    user_id: str = Field(description="Owner user ID")
    subject: str = Field(description="Thread subject")
    participants: List[str] = Field(description="Thread participants")
    email_count: int = Field(description="Number of emails in thread")
    emails: List[Email] = Field(default_factory=list, description="Emails in thread")
    last_email_date: datetime = Field(description="Date of most recent email")
    labels: List[EmailLabel] = Field(default_factory=list, description="Thread labels")
    is_important: bool = Field(default=False, description="Whether thread is important")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "gmail_thread_456",
                "user_id": "google_789", 
                "subject": "Re: Transaction Inquiry",
                "participants": ["user@example.com", "support@bank.com"],
                "email_count": 3,
                "last_email_date": "2024-01-15T10:30:00Z",
                "is_important": True
            }
        }


class EmailQuery(SearchQuery):
    """Email-specific search query model."""
    
    # Email-specific filters
    sender: Optional[str] = Field(default=None, description="Filter by sender")
    subject_contains: Optional[str] = Field(default=None, description="Filter by subject content")
    date_from: Optional[datetime] = Field(default=None, description="Filter emails from this date")
    date_to: Optional[datetime] = Field(default=None, description="Filter emails to this date")
    email_type: Optional[EmailType] = Field(default=None, description="Filter by email type")
    has_attachments: Optional[bool] = Field(default=None, description="Filter emails with attachments")
    is_financial: Optional[bool] = Field(default=None, description="Filter financial emails")
    importance_min: Optional[int] = Field(default=None, ge=1, le=10, description="Minimum importance score")
    labels: Optional[List[str]] = Field(default=None, description="Filter by Gmail labels")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "bank transaction",
                "sender": "noreply@bank.com",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "email_type": "financial",
                "is_financial": True,
                "importance_min": 5,
                "page": 1,
                "per_page": 20
            }
        }


class EmailResponse(BaseModel):
    """Email response model for API responses."""
    
    emails: List[Email] = Field(description="List of emails")
    total_count: int = Field(description="Total number of matching emails")
    financial_count: int = Field(default=0, description="Number of financial emails")
    processing_stats: Dict[str, int] = Field(default_factory=dict, description="Processing statistics")
    
    class Config:
        schema_extra = {
            "example": {
                "emails": [],
                "total_count": 1250,
                "financial_count": 87,
                "processing_stats": {
                    "processed": 1200,
                    "pending": 50,
                    "failed": 0
                }
            }
        }


class EmailFetchRequest(BaseModel):
    """Request model for fetching emails from Gmail."""
    
    max_results: int = Field(default=1000, ge=1, le=50000, description="Maximum emails to fetch")
    days_back: Optional[int] = Field(default=30, ge=1, le=365, description="Days back to fetch emails")
    query: Optional[str] = Field(default=None, description="Gmail search query")
    labels: Optional[List[str]] = Field(default=None, description="Specific labels to fetch")
    include_spam: bool = Field(default=False, description="Whether to include spam emails")
    include_trash: bool = Field(default=False, description="Whether to include trashed emails")
    process_financial: bool = Field(default=True, description="Whether to process financial data")
    upload_to_mem0: bool = Field(default=True, description="Whether to upload to Mem0")
    
    class Config:
        schema_extra = {
            "example": {
                "max_results": 5000,
                "days_back": 90,
                "query": "from:bank OR subject:transaction",
                "include_spam": False,
                "process_financial": True,
                "upload_to_mem0": True
            }
        }


class EmailProcessingResponse(BaseModel):
    """Response model for email processing operations."""
    
    task_id: str = Field(description="Processing task ID")
    status: ProcessingStatus = Field(description="Processing status")
    emails_fetched: int = Field(default=0, description="Number of emails fetched")
    emails_processed: int = Field(default=0, description="Number of emails processed")
    financial_emails: int = Field(default=0, description="Number of financial emails found")
    mem0_uploads: int = Field(default=0, description="Number of emails uploaded to Mem0")
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "completed",
                "emails_fetched": 1000,
                "emails_processed": 980,
                "financial_emails": 45,
                "mem0_uploads": 980,
                "errors": [],
                "processing_time": 45.2
            }
        }


class GmailCredentials(BaseModel):
    """Gmail API credentials model."""
    
    access_token: str = Field(description="Gmail API access token")
    refresh_token: Optional[str] = Field(default=None, description="Gmail API refresh token")
    token_expires: Optional[datetime] = Field(default=None, description="Token expiration time")
    scopes: List[str] = Field(default_factory=list, description="Granted OAuth scopes")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "ya29.a0AWY7Ckm...",
                "refresh_token": "1//04tLzQ...",
                "token_expires": "2024-01-15T11:30:00Z",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
            }
        }


class EmailStats(BaseModel):
    """Email statistics model."""
    
    total_emails: int = Field(description="Total number of emails")
    financial_emails: int = Field(description="Number of financial emails")
    processed_emails: int = Field(description="Number of processed emails")
    pending_emails: int = Field(description="Number of pending emails")
    failed_emails: int = Field(description="Number of failed emails")
    total_size_mb: float = Field(description="Total email size in MB")
    avg_processing_time: float = Field(description="Average processing time per email")
    last_sync: Optional[datetime] = Field(default=None, description="Last synchronization time")
    
    class Config:
        schema_extra = {
            "example": {
                "total_emails": 5000,
                "financial_emails": 250,
                "processed_emails": 4900,
                "pending_emails": 100,
                "failed_emails": 0,
                "total_size_mb": 150.5,
                "avg_processing_time": 0.05,
                "last_sync": "2024-01-15T10:30:00Z"
            }
        }


class GoogleToken(BaseModel):
    """Google OAuth token model."""
    
    access_token: str = Field(description="Google OAuth access token")
    refresh_token: Optional[str] = Field(default=None, description="Google OAuth refresh token")
    id_token: Optional[str] = Field(default=None, description="Google OAuth ID token")
    expires_in: Optional[int] = Field(default=None, description="Token expiration time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "ya29.a0AfH6SMC...",
                "refresh_token": "1//04...",
                "id_token": "eyJhbGciOiJSUzI1NiIs...",
                "expires_in": 3599
            }
        }


class GmailFetchPayload(BaseModel):
    """Gmail fetch request payload."""
    
    jwt_token: str = Field(description="JWT authentication token")
    max_results: Optional[int] = Field(default=5000, ge=1, le=50000, description="Maximum emails to fetch")
    days_back: Optional[int] = Field(default=30, ge=1, le=365, description="Days back to fetch emails")
    include_body: Optional[bool] = Field(default=True, description="Whether to include email body")
    process_financial: Optional[bool] = Field(default=True, description="Whether to process financial data")
    upload_to_mem0: Optional[bool] = Field(default=True, description="Whether to upload to Mem0")
    
    class Config:
        schema_extra = {
            "example": {
                "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "max_results": 10000,
                "days_back": 90,
                "include_body": True,
                "process_financial": True,
                "upload_to_mem0": True
            }
        } 