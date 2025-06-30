"""
Authentication Models
====================

This module contains authentication-related models including User, login requests,
and authentication responses.
"""

from pydantic import Field, EmailStr, validator, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

from .common import BaseModel, TimestampMixin, UserPreferences


class User(TimestampMixin):
    """User model with authentication and profile information."""
    
    id: str = Field(description="Unique user identifier")
    email: EmailStr = Field(description="User email address")
    name: Optional[str] = Field(default=None, description="User full name")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")
    
    # Authentication
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_verified: bool = Field(default=False, description="Whether email is verified")
    is_admin: bool = Field(default=False, description="Whether user has admin privileges")
    
    # Google OAuth Info
    google_id: Optional[str] = Field(default=None, description="Google OAuth user ID")
    google_access_token: Optional[str] = Field(default=None, description="Google access token")
    google_refresh_token: Optional[str] = Field(default=None, description="Google refresh token")
    
    # User Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    
    # Usage Statistics
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Total number of logins")
    email_count: int = Field(default=0, description="Total emails processed")
    
    # Subscription Info
    subscription_tier: str = Field(default="free", description="User subscription tier")
    subscription_expires: Optional[datetime] = Field(default=None, description="Subscription expiry date")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "google_123456789",
                "email": "user@example.com",
                "name": "John Doe",
                "picture": "https://example.com/avatar.jpg",
                "is_active": True,
                "is_verified": True,
                "is_admin": False,
                "subscription_tier": "free",
                "login_count": 5,
                "email_count": 1250
            }
        }


class UserCreate(BaseModel):
    """Model for creating a new user."""
    
    email: EmailStr = Field(description="User email address")
    name: Optional[str] = Field(default=None, description="User full name")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")
    google_id: Optional[str] = Field(default=None, description="Google OAuth user ID")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "picture": "https://example.com/avatar.jpg",
                "google_id": "123456789"
            }
        }


class UserUpdate(BaseModel):
    """Model for updating user information."""
    
    name: Optional[str] = Field(default=None, description="User full name")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")
    preferences: Optional[UserPreferences] = Field(default=None, description="User preferences")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Smith",
                "preferences": {
                    "timezone": "America/New_York",
                    "theme": "dark",
                    "email_notifications": False
                }
            }
        }


class LoginRequest(BaseModel):
    """Login request model for Google OAuth."""
    
    google_token: str = Field(description="Google OAuth ID token")
    
    class Config:
        schema_extra = {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
            }
        }


class LoginResponse(BaseModel):
    """Login response model with JWT token and user info."""
    
    access_token: str = Field(description="JWT access token")
    refresh_token: Optional[str] = Field(default=None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    user: User = Field(description="User information")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "token_type": "bearer",
                "expires_in": 172800,
                "user": {
                    "id": "google_123456789",
                    "email": "user@example.com",
                    "name": "John Doe"
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str = Field(description="JWT refresh token")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
            }
        }


class LogoutRequest(BaseModel):
    """Logout request model."""
    
    refresh_token: Optional[str] = Field(default=None, description="JWT refresh token to invalidate")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
            }
        }


class TokenVerifyRequest(BaseModel):
    """Token verification request model."""
    
    token: str = Field(description="JWT token to verify")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
            }
        }


class TokenVerifyResponse(BaseModel):
    """Token verification response model."""
    
    valid: bool = Field(description="Whether token is valid")
    expires_at: Optional[datetime] = Field(default=None, description="Token expiration time")
    user_id: Optional[str] = Field(default=None, description="User ID from token")
    
    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "expires_at": "2024-01-15T10:30:00Z",
                "user_id": "google_123456789"
            }
        }


class UserSession(BaseModel):
    """User session information."""
    
    session_id: str = Field(description="Session identifier")
    user_id: str = Field(description="User identifier")
    created_at: datetime = Field(description="Session creation time")
    last_activity: datetime = Field(description="Last activity timestamp")
    ip_address: Optional[str] = Field(default=None, description="User IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    is_active: bool = Field(default=True, description="Whether session is active")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": "google_123456789",
                "created_at": "2024-01-15T10:00:00Z",
                "last_activity": "2024-01-15T10:30:00Z",
                "ip_address": "192.168.1.1",
                "is_active": True
            }
        } 