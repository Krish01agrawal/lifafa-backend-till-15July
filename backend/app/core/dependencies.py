"""
Dependency Injection
==================

This module contains FastAPI dependency injection functions for authentication,
database access, and service layer components.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from ..config import get_settings
from ..services.database_service import DatabaseService, get_database_service
from ..services.gmail_service import GmailService, get_gmail_service
from ..services.auth_service import AuthService, get_auth_service
from ..models.auth import User
from ..config.constants import APIMessages

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db_service: DatabaseService = Depends(get_database_service)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token from request header
        auth_service: Authentication service instance
        db_service: Database service instance
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Verify and decode JWT token
        payload = auth_service.decode_jwt_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=APIMessages.ERROR_INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=APIMessages.ERROR_INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user_data = await db_service.get_user_by_id(user_id)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=APIMessages.ERROR_USER_NOT_FOUND,
            )
        
        return User(**user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=APIMessages.ERROR_INTERNAL_SERVER,
        )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db_service: DatabaseService = Depends(get_database_service)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Used for optional authentication endpoints.
    
    Args:
        credentials: Optional HTTP Bearer token
        auth_service: Authentication service instance
        db_service: Database service instance
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, auth_service, db_service)
    except HTTPException:
        return None


async def verify_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that current user has admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=APIMessages.ERROR_FORBIDDEN,
        )
    
    return current_user


def get_pagination_params(
    skip: int = 0, 
    limit: int = 100
) -> Dict[str, int]:
    """
    Get pagination parameters with validation.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Dict[str, int]: Pagination parameters
        
    Raises:
        HTTPException: If parameters are invalid
    """
    settings = get_settings()
    
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit <= 0 or limit > settings.max_email_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit must be between 1 and {settings.max_email_limit}"
        )
    
    return {"skip": skip, "limit": limit}


def get_search_params(
    query: str,
    max_results: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get search parameters with validation.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        
    Returns:
        Dict[str, Any]: Validated search parameters
        
    Raises:
        HTTPException: If parameters are invalid
    """
    settings = get_settings()
    
    if not query or len(query.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter is required"
        )
    
    if len(query) > 2000:  # Max query length from settings
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query is too long (max 2000 characters)"
        )
    
    if max_results is not None:
        if max_results <= 0 or max_results > settings.max_email_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Max results must be between 1 and {settings.max_email_limit}"
            )
    
    return {
        "query": query.strip(),
        "max_results": max_results or settings.default_email_limit
    } 