"""
Common Models
=============

This module contains base models and common response schemas used across the application.
"""

from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum

DataT = TypeVar('DataT')


class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        # Use enum values for serialization
        use_enum_values=True,
        # Allow population by field name or alias
        populate_by_name=True,  # Updated from allow_population_by_field_name
        # Validate assignment on model creation
        validate_assignment=True,
        # Generate schema with examples
        json_schema_extra={
            "example": {}
        }  # Updated from schema_extra
    )


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp fields."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class ResponseModel(BaseModel, Generic[DataT]):
    """Generic response model for API responses."""
    
    success: bool = Field(description="Whether the request was successful")
    message: str = Field(description="Response message")
    data: Optional[DataT] = Field(default=None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated response model."""
    
    items: List[DataT] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        items: List[DataT],
        total: int,
        page: int,
        per_page: int
    ) -> "PaginatedResponse[DataT]":
        """Create paginated response."""
        pages = (total + per_page - 1) // per_page  # Ceiling division
        
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class StatusResponse(BaseModel):
    """Simple status response."""
    
    status: str = Field(description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(description="Health status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: Optional[Dict[str, str]] = Field(default=None, description="Service statuses")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="System metrics")


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResponse(BaseModel):
    """Background task response model."""
    
    task_id: str = Field(description="Task identifier")
    status: ProcessingStatus = Field(description="Task status")
    message: str = Field(description="Status message")
    progress: Optional[float] = Field(default=None, description="Progress percentage (0-100)")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Last update time")


class SearchQuery(BaseModel):
    """Generic search query model."""
    
    query: str = Field(min_length=1, max_length=2000, description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=1000, description="Items per page")


class FileUpload(BaseModel):
    """File upload information model."""
    
    filename: str = Field(description="Original filename")
    content_type: str = Field(description="File content type")
    size: int = Field(description="File size in bytes")
    file_id: Optional[str] = Field(default=None, description="Stored file identifier")
    upload_url: Optional[str] = Field(default=None, description="File access URL")


class UserPreferences(BaseModel):
    """User preferences model."""
    
    timezone: str = Field(default="UTC", description="User timezone")
    language: str = Field(default="en", description="Preferred language")
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    push_notifications: bool = Field(default=True, description="Enable push notifications")
    theme: str = Field(default="light", description="UI theme preference")
    currency: str = Field(default="USD", description="Preferred currency")


class SystemMetrics(BaseModel):
    """System metrics model."""
    
    cpu_usage: float = Field(description="CPU usage percentage")
    memory_usage: float = Field(description="Memory usage percentage")
    disk_usage: float = Field(description="Disk usage percentage")
    active_users: int = Field(description="Number of active users")
    requests_per_minute: float = Field(description="Current requests per minute")
    error_rate: float = Field(description="Error rate percentage")
    average_response_time: float = Field(description="Average response time in seconds")


class BrowserAutomationRequest(BaseModel):
    """Request model for browser automation tasks."""
    
    jwt_token: str = Field(description="JWT authentication token")
    task_type: str = Field(description="Type of automation task")
    target_url: Optional[str] = Field(default=None, description="Target URL for automation")
    form_data: Optional[Dict[str, Any]] = Field(default=None, description="Form data to fill")
    selectors: Optional[Dict[str, str]] = Field(default=None, description="CSS selectors for elements")
    wait_time: Optional[int] = Field(default=5, description="Wait time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "task_type": "form_fill",
                "target_url": "https://example.com/application",
                "form_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "9876543210"
                },
                "selectors": {
                    "name_field": "#applicant-name",
                    "email_field": "#applicant-email",
                    "submit_button": ".submit-btn"
                },
                "wait_time": 10
            }
        } 