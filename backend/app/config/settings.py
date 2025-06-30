"""
Centralized Settings Configuration
=================================

This module contains all application settings using Pydantic for type safety
and validation. Settings are loaded from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator, ConfigDict
from typing import List, Dict, Any, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with type validation and environment variable support."""
    
    # Application Info
    app_name: str = Field(default="Gmail Chatbot API", description="Application name")
    app_version: str = Field(default="1.3.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/production)")
    
    # Security
    jwt_secret: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=48, description="JWT expiration in hours")
    access_token_expire_minutes: Optional[int] = Field(default=10080, description="Access token expiration in minutes")
    
    # Google OAuth (matching actual env variable names)
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    redirect_uri: str = Field(..., description="Google OAuth redirect URI")  # Changed from google_redirect_uri
    frontend_url: str = Field(default="http://localhost:8000", description="Frontend URL")
    
    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    
    # Mem0 Configuration (made optional with defaults)
    mem0_api_key: str = Field(..., description="Mem0 API key")
    mem0_user_id: Optional[str] = Field(default="default_user", description="Mem0 user ID")
    mem0_org_name: Optional[str] = Field(default="default_org", description="Mem0 organization name")
    mem0_project_name: Optional[str] = Field(default="gmail_chatbot", description="Mem0 project name")
    
    # MongoDB Configuration (matching actual env variable names)
    mongo_uri: str = Field(..., description="MongoDB connection URL")  # Changed from mongodb_url
    mongodb_database: str = Field(default="gmail_chatbot", description="MongoDB database name")
    mongodb_connection_string: Optional[str] = Field(default=None, description="Alternative MongoDB connection string")
    
    # Credit Bureau APIs (making them optional)
    cibil_api_endpoint: Optional[str] = Field(default="https://api.cibil.com/v1", description="CIBIL API endpoint")
    cibil_api_key: Optional[str] = Field(default=None, description="CIBIL API key")
    cibil_merchant_id: Optional[str] = Field(default=None, description="CIBIL merchant ID")
    cibil_username: Optional[str] = Field(default=None, description="CIBIL username")
    cibil_password: Optional[str] = Field(default=None, description="CIBIL password")
    cibil_enabled: Optional[bool] = Field(default=False, description="Enable CIBIL integration")
    cibil_sandbox: Optional[bool] = Field(default=True, description="Use CIBIL sandbox")
    cibil_daily_limit: Optional[int] = Field(default=100, description="CIBIL daily API limit")
    cibil_cost_per_call: Optional[float] = Field(default=15.0, description="CIBIL cost per API call")
    
    experian_api_endpoint: Optional[str] = Field(default="https://api.experian.in/v1", description="Experian API endpoint")
    experian_api_key: Optional[str] = Field(default=None, description="Experian API key")
    experian_client_id: Optional[str] = Field(default=None, description="Experian client ID")
    experian_client_secret: Optional[str] = Field(default=None, description="Experian client secret")
    experian_enabled: Optional[bool] = Field(default=False, description="Enable Experian integration")
    experian_sandbox: Optional[bool] = Field(default=True, description="Use Experian sandbox")
    experian_daily_limit: Optional[int] = Field(default=100, description="Experian daily API limit")
    experian_cost_per_call: Optional[float] = Field(default=12.0, description="Experian cost per API call")
    
    crif_api_endpoint: Optional[str] = Field(default="https://api.crifhighmark.com/v1", description="CRIF API endpoint")
    crif_api_key: Optional[str] = Field(default=None, description="CRIF API key")
    crif_partner_id: Optional[str] = Field(default=None, description="CRIF partner ID")
    crif_access_token: Optional[str] = Field(default=None, description="CRIF access token")
    crif_enabled: Optional[bool] = Field(default=False, description="Enable CRIF integration")
    crif_sandbox: Optional[bool] = Field(default=True, description="Use CRIF sandbox")
    crif_daily_limit: Optional[int] = Field(default=100, description="CRIF daily API limit")
    crif_cost_per_call: Optional[float] = Field(default=10.0, description="CRIF cost per API call")
    
    equifax_api_endpoint: Optional[str] = Field(default="https://api.equifax.co.in/v1", description="Equifax API endpoint")
    equifax_api_key: Optional[str] = Field(default=None, description="Equifax API key")
    equifax_subscriber_id: Optional[str] = Field(default=None, description="Equifax subscriber ID")
    equifax_security_code: Optional[str] = Field(default=None, description="Equifax security code")
    equifax_enabled: Optional[bool] = Field(default=False, description="Enable Equifax integration")
    equifax_sandbox: Optional[bool] = Field(default=True, description="Use Equifax sandbox")
    equifax_daily_limit: Optional[int] = Field(default=100, description="Equifax daily API limit")
    equifax_cost_per_call: Optional[float] = Field(default=10.0, description="Equifax cost per API call")
    
    # Credit Bureau Security
    credit_data_encryption_key: Optional[str] = Field(default=None, description="Credit data encryption key")
    credit_api_timeout: Optional[int] = Field(default=180, description="Credit API timeout in seconds")
    credit_api_retry_attempts: Optional[int] = Field(default=3, description="Credit API retry attempts")
    credit_api_retry_delay: Optional[int] = Field(default=5, description="Credit API retry delay in seconds")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:8000",
            "http://localhost:8001", 
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
        ],
        description="CORS allowed origins"
    )
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=240, description="Rate limit requests per minute")
    rate_limit_concurrent_requests: int = Field(default=40, description="Concurrent requests limit")
    
    # Processing Limits
    max_email_batch_size: int = Field(default=10000, description="Maximum emails per batch")
    max_email_body_size: int = Field(default=2097152, description="Maximum email body size in bytes")  # 2MB
    email_processing_timeout: int = Field(default=1800, description="Email processing timeout in seconds")
    financial_processing_timeout: int = Field(default=2400, description="Financial processing timeout in seconds")
    
    # Background Workers
    concurrent_users_limit: int = Field(default=200, description="Maximum concurrent users")
    max_background_workers: int = Field(default=25, description="Maximum background workers")
    background_worker_interval: int = Field(default=10, description="Background worker interval in seconds")
    
    # Email Processing
    default_email_limit: int = Field(default=20000, description="Default email limit per fetch")
    max_email_limit: int = Field(default=100000, description="Maximum email limit per fetch")
    
    # Feature Flags
    enable_smart_caching: bool = Field(default=True, description="Enable smart caching")
    enable_batch_processing: bool = Field(default=True, description="Enable batch processing")
    enable_smart_email_filtering: bool = Field(default=True, description="Enable smart email filtering")
    enable_mem0_processing: bool = Field(default=True, description="Enable Mem0 processing")
    enable_financial_features: bool = Field(default=True, description="Enable financial features")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file_max_size: int = Field(default=209715200, description="Max log file size in bytes")  # 200MB
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'production', 'testing']:
            raise ValueError('Environment must be development, production, or testing')
        return v
    
    @property
    def mongodb_url(self) -> str:
        """Get MongoDB URL (backward compatibility)"""
        return self.mongodb_connection_string or self.mongo_uri
    
    @property
    def google_redirect_uri(self) -> str:
        """Get Google redirect URI (backward compatibility)"""
        return self.redirect_uri
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from environment
    )


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings() 