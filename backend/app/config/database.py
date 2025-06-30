"""
Database Configuration
=====================

This module contains database-specific configuration and connection settings.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from functools import lru_cache
import certifi
from .settings import get_settings


class DatabaseConfig(BaseModel):
    """Database configuration with connection pooling settings."""
    
    # Connection Settings
    max_pool_size: int = Field(default=15, description="Maximum connection pool size")
    min_pool_size: int = Field(default=3, description="Minimum connection pool size")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    socket_timeout: int = Field(default=60, description="Socket timeout in seconds")
    max_idle_time: int = Field(default=600, description="Max idle time in seconds")
    
    # Query Limits
    max_documents_per_query: int = Field(default=25000, description="Maximum documents per query")
    default_query_limit: int = Field(default=500, description="Default query limit")
    max_bulk_insert_size: int = Field(default=5000, description="Maximum bulk insert size")
    
    # Retry Configuration
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    
    # Sharding Configuration
    enable_sharding: bool = Field(default=False, description="Enable database sharding")
    max_users_per_database: int = Field(default=10000, description="Maximum users per database shard")
    
    # Cleanup Configuration
    enable_auto_cleanup: bool = Field(default=True, description="Enable automatic cleanup")
    max_email_age_days: int = Field(default=365, description="Maximum email age in days")
    cleanup_interval_hours: int = Field(default=24, description="Cleanup interval in hours")
    
    # Performance Settings
    enable_indexing: bool = Field(default=True, description="Enable database indexing")
    batch_insert_size: int = Field(default=1000, description="Batch insert size")
    
    @property
    def ca_cert_path(self) -> str:
        """Get CA certificate path for MongoDB connection."""
        return certifi.where()
    
    @property
    def connection_params(self) -> Dict:
        """Get MongoDB connection parameters."""
        return {
            "tlsCAFile": self.ca_cert_path,
            "maxPoolSize": self.max_pool_size,
            "minPoolSize": self.min_pool_size,
            "connectTimeoutMS": self.connection_timeout * 1000,
            "socketTimeoutMS": self.socket_timeout * 1000,
            "maxIdleTimeMS": self.max_idle_time * 1000,
            "retryWrites": True,
            "w": "majority"
        }


@lru_cache()
def get_database_config() -> DatabaseConfig:
    """Get database configuration (cached)."""
    return DatabaseConfig() 