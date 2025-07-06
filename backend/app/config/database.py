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
    enable_auto_cleanup: bool = Field(default=False, description="Enable automatic cleanup - DISABLED to prevent data loss")
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

# ============================================================================
# AUTO-CLEANUP SETTINGS - MODIFIED FOR DATA LOSS PREVENTION
# ============================================================================

# 🚨 CRITICAL SAFETY: Auto-cleanup disabled by default after data loss incident
ENABLE_AUTO_CLEANUP = False  # Changed from True to False to prevent data loss

# More conservative cleanup settings
MAX_EMAIL_AGE_DAYS = 730  # Increased from 365 to 730 days (2 years)
MAX_DELETION_PERCENTAGE = 5  # Reduced from 10% to 5% maximum deletion per cleanup
MIN_EMAILS_FOR_CLEANUP = 1000  # Increased from 100 to 1000 minimum emails before cleanup

# Enhanced monitoring settings
ENABLE_DATA_LOSS_MONITORING = True
ALERT_ON_EMAIL_COUNT_REDUCTION = True
EMAIL_COUNT_REDUCTION_THRESHOLD = 10  # Alert if more than 10% emails lost

# Database integrity checks
ENABLE_INTEGRITY_CHECKS = True
INTEGRITY_CHECK_INTERVAL = 3600  # Check every hour
BACKUP_BEFORE_MAJOR_OPERATIONS = True

# ============================================================================
# DATA RECOVERY SETTINGS
# ============================================================================

# Recovery operation settings
RECOVERY_BATCH_SIZE = 100
RECOVERY_OPERATION_TIMEOUT = 300  # 5 minutes
ENABLE_RECOVERY_LOGGING = True

# Cross-database consolidation settings
ENABLE_CROSS_DATABASE_CHECKS = True
CONSOLIDATE_DUPLICATE_EMAILS = True
PRESERVE_EMAIL_HISTORY = True

# ============================================================================
# ENHANCED LOGGING FOR DATA OPERATIONS
# ============================================================================

# Log all operations that affect email data
LOG_EMAIL_OPERATIONS = True
LOG_BULK_OPERATIONS = True
LOG_CLEANUP_OPERATIONS = True
LOG_RECOVERY_OPERATIONS = True

# Alert settings for data operations
ALERT_ON_LARGE_DELETIONS = True
ALERT_ON_BULK_OPERATIONS = True
ALERT_ON_PROCESSING_ERRORS = True

# Database operation safety settings
REQUIRE_CONFIRMATION_FOR_BULK_DELETE = True
ENABLE_OPERATION_ROLLBACK = True
ENABLE_SAFETY_CHECKS = True

# ============================================================================
# PROCESSING SAFETY SETTINGS
# ============================================================================

# Prevent operations during processing
BLOCK_CLEANUP_DURING_PROCESSING = True
BLOCK_BULK_OPERATIONS_DURING_PROCESSING = True
ENABLE_PROCESSING_LOCKS = True

# Data preservation settings
PRESERVE_EMAILS_DURING_MEM0_PROCESSING = True
VERIFY_DATA_INTEGRITY_BEFORE_PROCESSING = True
VERIFY_DATA_INTEGRITY_AFTER_PROCESSING = True

# ============================================================================
# MONITORING AND ALERTS
# ============================================================================

# Email count monitoring
MONITOR_EMAIL_COUNTS = True
EMAIL_COUNT_CHECK_INTERVAL = 300  # Check every 5 minutes
LOG_EMAIL_COUNT_CHANGES = True

# Performance monitoring
MONITOR_PROCESSING_PERFORMANCE = True
MONITOR_DATABASE_PERFORMANCE = True
ALERT_ON_SLOW_OPERATIONS = True

# Data loss prevention
ENABLE_DATA_LOSS_PREVENTION = True
BACKUP_CRITICAL_DATA = True
ENABLE_EMERGENCY_RECOVERY = True 