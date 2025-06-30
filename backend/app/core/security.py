"""
Security Utilities
==================

This module contains security-related functions for JWT tokens, password hashing,
and other authentication utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import hashlib
import secrets
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests

from ..config import get_settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_jwt_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT token with expiration.
    
    Args:
        data: Data to encode in the token
        
    Returns:
        str: JWT token
    """
    settings = get_settings()
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Optional[Dict[str, Any]]: Decoded payload or None if invalid
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token and return payload.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Optional[Dict[str, Any]]: Token payload or None if invalid
    """
    return decode_jwt_token(token)


def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Google OAuth2 token.
    
    Args:
        token: Google OAuth2 ID token
        
    Returns:
        Optional[Dict[str, Any]]: User info from Google or None if invalid
    """
    settings = get_settings()
    
    try:
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.google_client_id
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning(f"Invalid Google token issuer: {idinfo['iss']}")
            return None
            
        return {
            "user_id": idinfo['sub'],
            "email": idinfo['email'],
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "email_verified": idinfo.get('email_verified', False)
        }
        
    except ValueError as e:
        logger.warning(f"Google token verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying Google token: {e}")
        return None


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        str: Secure API key
    """
    return secrets.token_urlsafe(32)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token
        
    Returns:
        str: Secure token
    """
    return secrets.token_urlsafe(length)


def hash_string(text: str) -> str:
    """
    Create SHA256 hash of a string.
    
    Args:
        text: Text to hash
        
    Returns:
        str: SHA256 hash
    """
    return hashlib.sha256(text.encode()).hexdigest()


def create_refresh_token(user_id: str) -> str:
    """
    Create a refresh token for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        str: Refresh token
    """
    settings = get_settings()
    
    data = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=30)  # 30 days expiry
    }
    
    return jwt.encode(
        data,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify refresh token and return user ID.
    
    Args:
        token: Refresh token
        
    Returns:
        Optional[str]: User ID if token valid, None otherwise
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        if payload.get("type") != "refresh":
            return None
            
        return payload.get("user_id")
        
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if JWT token is expired.
    
    Args:
        token: JWT token
        
    Returns:
        bool: True if expired
    """
    try:
        payload = decode_jwt_token(token)
        if not payload:
            return True
            
        exp = payload.get("exp")
        if not exp:
            return True
            
        return datetime.now(timezone.utc).timestamp() > exp
        
    except Exception:
        return True 