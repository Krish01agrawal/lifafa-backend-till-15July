import os
import time
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import re

# Determine the path to the .env file (two levels up from this file)
# main.py is in backend/app/main.py, .env is in the root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

# Now proceed with other imports
from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
# from app.auth import verify_google_token, create_jwt_token, decode_jwt_token
from .auth import verify_google_token, create_jwt_token, decode_jwt_token
# from app.oauth import generate_auth_url, exchange_code_for_tokens
from .oauth import generate_auth_url, exchange_code_for_tokens
# Import Google OAuth2 Credentials for Gmail API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .db import users_collection, emails_collection
from .gmail import build_gmail_service, fetch_emails, get_storage_statistics, process_and_store_emails, email_extractor, fetch_gmail_emails_historical, fetch_gmail_emails
from .mem0_agent_agno import upload_emails_to_mem0, query_mem0, process_gmail_data_for_user, search_emails_in_mem0
from .db import cleanup_manager, db_manager
from .models import GoogleToken, GmailFetchPayload
from .websocket import router as websocket_router
from .websocket import manager
import logging
import asyncio
from bson import ObjectId
from pydantic import BaseModel
import json
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .financial_agent import (
    process_financial_transactions_for_user,
    get_financial_summary,
    get_financial_transactions
)

# Import scalability components
from .config import (
    CONFIG, EMAIL_PROCESSING_TIMEOUT, CONCURRENT_USERS_LIMIT,
    DEFAULT_EMAIL_LIMIT, MAX_EMAIL_LIMIT, ENABLE_SMART_CACHING,
    ENABLE_BATCH_PROCESSING, MAX_CONCURRENT_EMAIL_PROCESSING,
    ENABLE_DATABASE_SHARDING, STORAGE_WARNING_THRESHOLD, 
    STORAGE_CRITICAL_THRESHOLD, ENABLE_AUTO_CLEANUP, ENABLE_SMART_EMAIL_FILTERING
)
from .core.middleware import (
    RateLimitMiddleware, email_processing_context, 
    get_health_status, resource_manager, performance_monitor
)

# Import new financial services
from .credit_report_service import credit_report_service
from .statement_processor import statement_processor
from .credit_card_service import credit_card_service
from .browser_automation_service import browser_automation_service

# Import new models for financial features
from .models import (
    CreditReportRequest, StatementUploadRequest, CreditCardCriteria,
    BrowserAutomationRequest
)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gmail Chatbot API",
    description="Scalable Gmail Chatbot with Financial Analytics",
    version="1.2.0"
)

# Define the security scheme
security = HTTPBearer()

# Add enhanced scalability middleware FIRST (before CORS)
app.add_middleware(RateLimitMiddleware)

# Allow CORS from frontend origin (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com", "http://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com/api", "http://localhost:8000", "http://localhost:8001", "http://127.0.0.1:8000", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "Referrer-Policy"],
    expose_headers=["*"]
)

app.include_router(websocket_router)

# Initialize APScheduler
scheduler = AsyncIOScheduler()

# Enhanced health check endpoint with comprehensive metrics
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with comprehensive scalability metrics."""
    health_data = get_health_status()
    
    # Determine overall health status
    overall_status = "healthy"
    if health_data.get("memory", {}).get("current_percent", 0) > 90:
        overall_status = "warning"
    if health_data.get("cpu", {}).get("current_percent", 0) > 90:
        overall_status = "warning"
    if health_data.get("capacity_utilization_percent", 0) > 95:
        overall_status = "critical"
    
    return {
        "status": overall_status,
        "_version": "1.2.0",
        "timestamp": time.time(),
        "scalability": health_data,
        "config": {
            "concurrent_users_limit": CONCURRENT_USERS_LIMIT,
            "email_processing_timeout": EMAIL_PROCESSING_TIMEOUT,
            "default_email_limit": DEFAULT_EMAIL_LIMIT,
            "max_email_limit": MAX_EMAIL_LIMIT,
            "smart_caching_enabled": ENABLE_SMART_CACHING,
            "batch_processing_enabled": ENABLE_BATCH_PROCESSING,
            "max_concurrent_processing": MAX_CONCURRENT_EMAIL_PROCESSING
        },
        "workers": {
            "email_sync_worker": {
                "interval": "10 seconds",
                "status": "active",
                "optimization": "enhanced"
            },
            "financial_analysis_worker": {
                "interval": "45 seconds", 
                "status": "active",
                "optimization": "enhanced"
            },
            "performance_monitor": {
                "interval": "1 second",
                "status": "active",
                "optimization": "new"
            }
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Get detailed system metrics for monitoring."""
    return get_health_status()

@app.get("/metrics/users")
async def get_user_metrics():
    """Get enhanced active user metrics."""
    stats = resource_manager.get_enhanced_stats()
    return {
        "active_users": stats.get("active_users", 0),
        "queued_users": stats.get("queued_users", 0),
        "concurrent_limit": CONCURRENT_USERS_LIMIT,
        "active_user_list": stats.get("active_user_list", []),
        "queued_user_list": stats.get("queued_user_list", []),
        "utilization_percent": stats.get("capacity_utilization_percent", 0),
        "queue_stats": stats.get("queue", {}),
        "user_priorities": stats.get("user_priorities", {})
    }

@app.get("/metrics/optimization")
async def get_optimization_metrics():
    """Get optimization performance metrics."""
    try:
        # Get Gmail performance stats
        from .gmail import get_gmail_performance_stats
        gmail_stats = get_gmail_performance_stats()
        
        # Get cache statistics if available
        cache_stats = {}
        if ENABLE_SMART_CACHING:
            try:
                from .mem0_agent_agno import smart_cache
                cache_stats = smart_cache.get_stats()
            except Exception as e:
                cache_stats = {"error": str(e)}
        
        # Get email extraction statistics
        extraction_stats = email_extractor.get_extraction_stats()
        
        # Get database performance stats
        try:
            from .db import get_database_stats
            db_stats = await get_database_stats()
        except Exception as e:
            db_stats = {"error": str(e)}
        
        return {
            "timestamp": time.time(),
            "optimization_status": {
                "smart_caching_enabled": ENABLE_SMART_CACHING,
                "batch_processing_enabled": ENABLE_BATCH_PROCESSING,
                "parallel_processing_enabled": True,
                "intelligent_queuing_enabled": True,
                "complete_data_extraction": True,
                "smart_email_filtering": True
            },
            "performance_improvements": {
                "concurrent_users": f"{CONCURRENT_USERS_LIMIT} (↑ from 15)",
                "email_fetch_limit": f"{DEFAULT_EMAIL_LIMIT} (↑ from 3,500)",
                "memory_per_user": f"{resource_manager.memory_cleanup_threshold}MB (↑ from 1,024MB)",
                "background_worker_interval": "10s (↓ from 30s)",
                "gmail_api_rate_limit": f"{gmail_stats.get('thread_pool_size', 10)} workers"
            },
            "gmail_processing": gmail_stats,
            "caching": cache_stats,
            "database": db_stats,
            "email_extraction": extraction_stats,
            "data_preservation": {
                "complete_data_rate": extraction_stats.get("complete_data_rate", 0),
                "financial_detection_rate": extraction_stats.get("financial_detection_rate", 0),
                "attachment_detection_rate": extraction_stats.get("attachment_detection_rate", 0),
                "headers_preserved": extraction_stats.get("headers_preserved", 0),
                "space_optimization": "Smart filtering vs compression"
            },
            "expected_improvement": "Complete data + 60-70% space saved through smart filtering"
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization metrics: {e}")
        return {"error": str(e), "timestamp": time.time()}


@app.get("/websocket/health")
async def websocket_health():
    """WebSocket-specific health check endpoint"""
    return {
        "status": "healthy", 
        "websocket_endpoints": [
            "/ws/chat",
            "/ws/chat/{chat_id}"
        ],
        "websocket_url": "ws://your-domain.com/ws/chat/{chat_id}",
        "connection_manager": {
            "active_connections": len(manager.active_connections) if 'manager' in globals() else 0
        }
    }


# Define a Pydantic model for the test query request body
class TestMem0QueryPayload(BaseModel):
    user_id: str
    query: str


@app.post("/auth/google-login")
async def google_login(payload: GoogleToken):
    logger.info(f"Received request for /auth/google-login with token: {payload.token[:30]}...")
    try:
        logger.info("Verifying Google token...")
        raw_user_info_from_google = verify_google_token(payload.token)
        logger.info(f"Google token verified. Raw User info from Google: {raw_user_info_from_google}")

        user_id_from_google = raw_user_info_from_google["user_id"]
        logger.info(f"Checking user in database: {user_id_from_google}")
        
        # Fetch user from DB to get the version with _id (if it exists)
        user_in_db = await users_collection.find_one({"user_id": user_id_from_google})
        
        final_user_info_to_return = {}

        if not user_in_db:
            logger.info("User not found, creating new user with Google info...")
            # Use the info directly from Google for the first insert
            # MongoDB will add an _id field automatically
            user_to_insert = raw_user_info_from_google.copy() # Use a copy
            user_to_insert['initial_gmailData_sync'] = False # Initialize initial_gmailData_sync
            user_to_insert['fetched_email'] = False  # Initialize fetched_email
            # Initialize financial analysis fields
            user_to_insert['financial_analysis_completed'] = False
            user_to_insert['financial_analysis_date'] = None
            user_to_insert['financial_transactions_count'] = 0
            user_to_insert['financial_processing_method'] = None
            insert_result = await users_collection.insert_one(user_to_insert)
            logger.info(f"New user created. Inserted ID: {insert_result.inserted_id}")
            # Fetch the newly created user to get all fields including the auto-generated _id
            final_user_info_to_return = await users_collection.find_one({"_id": insert_result.inserted_id})
            if not final_user_info_to_return:
                 logger.error("CRITICAL: User just inserted but not found by _id!")
                 final_user_info_to_return = raw_user_info_from_google # Fallback, but _id will be missing
        else:
            logger.info("User found in database.")
            final_user_info_to_return = user_in_db

        # Ensure _id (and any other ObjectId) is converted to string before returning
        serializable_user_info = convert_objectid_to_str(final_user_info_to_return)
        logger.info(f"Serializable user info for response: {serializable_user_info}")

        logger.info("Creating JWT token...")
        # Create JWT based on consistent user_id and email
        jwt_payload_data = {"user_id": serializable_user_info["user_id"], "email": serializable_user_info["email"]}
        jwt_token = create_jwt_token(jwt_payload_data)
        logger.info("JWT token created successfully.")
        
        {
            "jwt_token": jwt_token,
            "user": {
                "email": serializable_user_info["email"],
                "name": serializable_user_info["name"],
                "picture": serializable_user_info["picture"],
                "user_id": serializable_user_info["user_id"],
            },
        }
        return {"jwt_token": jwt_token, "user": serializable_user_info}
    except HTTPException as e:
        logger.error(f"HTTPException in google_login: {e.detail}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"Unexpected error in google_login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.post("/gmail/fetch")
async def gmail_fetch(payload: GmailFetchPayload):
    """
    PROGRESSIVE EMAIL LOADING: 
    1. Immediately process 1-week recent emails for instant dashboard access
    2. Trigger background processing for 6-month historical data
    3. User can start querying immediately while historical data loads
    """
    logger.info("🚀 [PROGRESSIVE] Received request for /gmail/fetch")
    try:
        logger.info("Decoding JWT token...")
        user = decode_jwt_token(payload.jwt_token)
        user_id = user.get("user_id")
        logger.info(f"JWT decoded. User ID: {user_id}")

        # Use email processing context for resource management
        async with email_processing_context(user_id) as rm:
            # STEP 1: Process recent emails immediately (1 week) - FAST!
            logger.info(f"🔥 [IMMEDIATE] Processing recent emails for instant dashboard access...")
            
            result = await asyncio.wait_for(
                _process_immediate_emails(user_id=user_id, access_token=payload.access_token, days=7),
                timeout=60  # Shorter timeout for immediate processing
            )

            if result["status"] == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["message"]
                )

            # STEP 2: Log background processing status
            if result.get("dashboard_ready", False):
                logger.info(f"✅ [IMMEDIATE] Dashboard ready for user {user_id}")
                logger.info(f"🔄 [BACKGROUND] Historical data processing will start automatically")
                
                # Console message for immediate feedback
                print(f"\n{'='*80}")
                print(f"🎉 DASHBOARD READY for User: {user_id}")
                print(f"📊 Recent emails processed: {result.get('recent_emails_count', 0)}")
                print(f"💰 Recent financial transactions: {result.get('recent_financial_transactions', 0)}")
                print(f"✅ User can start querying immediately!")
                print(f"🔄 Background: 6-month historical data loading...")
                print(f"{'='*80}\n")

            return {
                "message": result["message"], 
                "count": result.get("recent_emails_count", 0),
                "dashboard_ready": result.get("dashboard_ready", False),
                "background_processing": result.get("background_processing", False),
                "processing_type": "progressive",
                "status": result["status"]
            }
            
    except asyncio.TimeoutError:
        logger.error(f"Gmail immediate fetch timeout for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Immediate email processing timed out after 60 seconds"
        )
    except HTTPException as e:
        logger.error(f"HTTPException in gmail_fetch: {e.detail}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in gmail_fetch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred during gmail fetch: {str(e)}"
        )

# Removed duplicate /test/mem0-query endpoint - functionality available via /gmail/query

# Add new OAuth routes after the existing CORS setup
@app.get("/auth/login")
async def login():
    """Redirect user to Google OAuth consent screen."""
    try:
        auth_url, state = generate_auth_url()
        logger.info(f"Redirecting user to Google OAuth with state: {state}")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Error in /auth/login: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {e}")

@app.get("/auth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from Google."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8000")
    # frontend_url = os.getenv("FRONTEND_URL", "http://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com")
    
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    
    if not code or not state:
        logger.error("Missing code or state in OAuth callback")
        return RedirectResponse(url=f"{frontend_url}?error=missing_parameters")
    
    try:
        # Exchange code for tokens and user info
        credentials, user_info = exchange_code_for_tokens(code, state)
        logger.info(f"OAuth successful for user: {user_info['email']}")
        
        # Store or update user in database
        user_id_from_google = user_info["user_id"]
        user_in_db = await users_collection.find_one({"user_id": user_id_from_google})
        
        if not user_in_db:
            logger.info("Creating new user from OAuth...")
            # Store user info with OAuth tokens
            user_data = user_info.copy()
            user_data.update({
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "initial_gmailData_sync": False,  # Initialize initial_gmailData_sync
                "fetched_email": False  # Initialize fetched_email
            })
            insert_result = await users_collection.insert_one(user_data)
            final_user_info = await users_collection.find_one({"_id": insert_result.inserted_id})
        else:
            logger.info("Updating existing user with new OAuth tokens...")
            # Update existing user with new tokens
            update_data = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "name": user_info.get("name"),
                "picture": user_info.get("picture")
            }
            
            # Check if user has any emails. If not, reset fetch status to re-trigger sync.
            has_email_data = await emails_collection.count_documents({"user_id": user_id_from_google}) > 0
            if not has_email_data:
                logger.info(f"User {user_id_from_google} has no email data. Resetting fetch status to trigger sync on re-login.")
                update_data["fetched_email"] = False
                update_data["initial_gmailData_sync"] = False
            
            await users_collection.update_one(
                {"user_id": user_id_from_google},
                {"$set": update_data}
            )
            final_user_info = await users_collection.find_one({"user_id": user_id_from_google})
        
        # Create JWT token
        jwt_payload = {"user_id": user_info["user_id"], "email": user_info["email"]}
        jwt_token = create_jwt_token(jwt_payload)
        
        logger.info(f"OAuth completed successfully for user: {user_info['email']}")
        
        # Redirect to frontend with JWT token (no auto-email fetching)
        return RedirectResponse(url=f"{frontend_url}?token={jwt_token}&user={user_info['email']}")
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return RedirectResponse(url=f"{frontend_url}?error=auth_failed")

@app.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Fetch details for the currently authenticated user.
    Uses HTTPBearer token for authentication.
    """
    logger.info("Received request for /me")
    try:
        token = credentials.credentials
        logger.info("Decoding JWT token for /me...")
        user_payload = decode_jwt_token(token)
        user_id = user_payload.get("user_id")
        
        if not user_id:
            logger.error("User ID not found in JWT payload for /me")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not found in token"
            )
        
        logger.info(f"Fetching user data for user_id: {user_id}")
        user_in_db = await users_collection.find_one({"user_id": user_id})
        
        if not user_in_db:
            logger.warning(f"User not found in database with user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check progressive loading status
        has_email_data = await emails_collection.count_documents({"user_id": user_id}) > 0
        current_sync_status = user_in_db.get("initial_gmailData_sync", False)
        current_fetched_status = user_in_db.get("fetched_email", False)
        dashboard_ready = user_in_db.get("dashboard_ready", False)
        background_sync_needed = user_in_db.get("background_sync_needed", False)
        historical_sync_completed = user_in_db.get("historical_sync_completed", False)
        recent_financial_transactions = user_in_db.get("recent_financial_transactions", 0)
        complete_financial_ready = user_in_db.get("complete_financial_ready", False)
        financial_analysis_completed = user_in_db.get("financial_analysis_completed", False)

        # Check if user has data in Mem0 as well
        has_mem0_data = False
        if has_email_data:
            try:
                mem0_results = await search_emails_in_mem0(user_id, "email", limit=1)
                has_mem0_data = len(mem0_results) > 0
                logger.info(f"User {user_id} Mem0 data check: {len(mem0_results) if mem0_results else 0} results found")
            except Exception as e:
                logger.warning(f"Failed to check Mem0 data for user {user_id}: {str(e)}")
                has_mem0_data = False

        # If user has MongoDB emails but no Mem0 data, reset sync to re-trigger Mem0 upload
        if has_email_data and not has_mem0_data:
            logger.info(f"User {user_id} has MongoDB emails but no Mem0 data - resetting sync flags to trigger Mem0 upload")
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "fetched_email": False, 
                    "initial_gmailData_sync": False,
                    "financial_analysis_completed": False
                }}
            )
            user_in_db["fetched_email"] = False
            user_in_db["initial_gmailData_sync"] = False
            user_in_db["financial_analysis_completed"] = False
        # If user has no emails AND hasn't been marked as fetched, trigger background processing
        elif not has_email_data and not current_fetched_status:
            logger.info(f"User {user_id} needs email sync - marking fetched_email=false for background processing")
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "fetched_email": False, 
                    "initial_gmailData_sync": False,
                    "financial_analysis_completed": False
                }}
            )
            user_in_db["fetched_email"] = False
            user_in_db["initial_gmailData_sync"] = False
            user_in_db["financial_analysis_completed"] = False
        elif has_email_data and has_mem0_data and not current_sync_status:
            # If both MongoDB and Mem0 have data but sync status is false, update it
            logger.info(f"User {user_id} has both email and Mem0 data - updating initial_gmailData_sync to true")
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"initial_gmailData_sync": True}}
            )
            user_in_db["initial_gmailData_sync"] = True
        
        # fetched_email field will be returned as is from the database.
        # It's updated when a fetch process is initiated.

        # Convert ObjectId to string before returning
        serializable_user_info = convert_objectid_to_str(user_in_db)
        
        # Add progressive loading status for frontend
        serializable_user_info["has_email_data"] = has_email_data
        serializable_user_info["dashboard_ready"] = dashboard_ready
        serializable_user_info["background_sync_needed"] = background_sync_needed
        serializable_user_info["historical_sync_completed"] = historical_sync_completed
        serializable_user_info["recent_financial_transactions"] = recent_financial_transactions
        serializable_user_info["complete_financial_ready"] = complete_financial_ready
        serializable_user_info["financial_analysis_completed"] = financial_analysis_completed
        serializable_user_info["needs_email_sync"] = not current_fetched_status
        serializable_user_info["email_sync_in_progress"] = current_fetched_status and not current_sync_status
        
        # Determine overall status for frontend
        if dashboard_ready and historical_sync_completed and financial_analysis_completed:
            serializable_user_info["sync_status"] = "complete"
            serializable_user_info["sync_message"] = "All email and financial data synchronized and ready for queries"
        elif dashboard_ready and historical_sync_completed and not financial_analysis_completed:
            serializable_user_info["sync_status"] = "financial_processing"
            serializable_user_info["sync_message"] = f"Email data ready! Processing complete financial analysis... ({recent_financial_transactions} recent transactions available)"
        elif dashboard_ready and background_sync_needed:
            serializable_user_info["sync_status"] = "partial"
            serializable_user_info["sync_message"] = f"Dashboard ready with {recent_financial_transactions} recent transactions! Historical data loading in background..."
        elif current_fetched_status and not dashboard_ready:
            serializable_user_info["sync_status"] = "processing"
            serializable_user_info["sync_message"] = "Processing recent emails and financial data for dashboard access..."
        else:
            serializable_user_info["sync_status"] = "pending"
            serializable_user_info["sync_message"] = "Click 'Sync Gmail' to start"
        
        logger.info(f"Successfully fetched user data for /me: {serializable_user_info.get('email')}")
        logger.info(f"   - Dashboard ready: {dashboard_ready}")
        logger.info(f"   - Background sync needed: {background_sync_needed}")
        logger.info(f"   - Historical sync completed: {historical_sync_completed}")
        logger.info(f"   - Recent financial transactions: {recent_financial_transactions}")
        logger.info(f"   - Complete financial ready: {complete_financial_ready}")
        logger.info(f"   - Overall status: {serializable_user_info['sync_status']}")
        
        return serializable_user_info
        
    except HTTPException as e:
        # Log specific HTTP exceptions and re-raise
        logger.error(f"HTTPException in /me endpoint: {e.detail}", exc_info=e.status_code not in [401, 404]) # Don't need full stack for 401/404
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /me endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

def convert_objectid_to_str(data):
    """Recursively converts ObjectId instances in a dictionary or list to strings."""
    if isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    return data

# Core email processing function
async def _trigger_and_process_user_emails(user_id: str, access_token: str, max_results: int = 5000):
    """
    Fetch and process user emails with FREE TIER optimization
    
    Key optimizations:
    - 6-month email retention only
    - Ultra-compressed storage (90% size reduction)
    - Automatic cleanup of old data
    - Multi-database sharding for infinite scaling
    """
    
    logger.info(f"🚀 [FREE TIER] Processing emails for user: {user_id} (limit: {max_results})")
    
    try:
        # Check storage status before processing
        storage_stats = await get_storage_statistics()
        
        if storage_stats.get("usage_percent", 0) > 85:
            logger.warning(f"⚠️ Storage usage critical: {storage_stats['usage_percent']}% - triggering cleanup")
            await cleanup_manager.cleanup_all_users()
        
        # Build Gmail service
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Fetch emails with 6-month limit and compression
        from .gmail import fetch_gmail_emails
        emails = await fetch_gmail_emails(service, user_id, max_results)
        
        if emails:
            # Process and store with ultra-compression
            result = await process_and_store_emails(user_id, emails)
            
            if result.get("success", False):
                logger.info(f"✅ [FREE TIER] Successfully processed {result['emails_stored']} emails for user {user_id}")
                logger.info(f"   📊 Smart filtering: {result.get('promotional_filtered', 0)} promotional emails removed")
                logger.info(f"   💰 Financial emails: {result.get('financial_preserved', 0)} preserved")
                logger.info(f"   ⏰ Retention: 6 months only")
                logger.info(f"   🗄️ Database: {'Sharded' if ENABLE_DATABASE_SHARDING else 'Single'}")
                
                # 🔧 CRITICAL FIX: Update user flags after successful processing
                users_coll = await db_manager.get_collection(user_id, "users")
                await users_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "fetched_email": True,  # ✅ Mark email fetch as complete
                        "initial_gmailData_sync": True,  # ✅ Mark initial sync as complete
                        "storage_optimized": True,
                        "email_sync_date": datetime.now().isoformat(),
                        "emails_processed": result['emails_stored'],
                        "promotional_filtered": result.get('promotional_filtered', 0),
                        "financial_preserved": result.get('financial_preserved', 0)
                    }},
                    upsert=True
                )
                
                logger.info(f"🎯 User {user_id} flags updated: fetched_email=True, initial_gmailData_sync=True")
                
                return {
                    "success": True,  # ✅ Consistent success key
                    "status": "success", 
                    "message": f"Successfully processed {result['emails_stored']} emails with smart filtering",
                    "count": result['emails_stored'],
                    "optimization": "smart_filtering",
                    "promotional_filtered": result.get('promotional_filtered', 0),
                    "financial_preserved": result.get('financial_preserved', 0),
                    "retention_days": 180,
                    "storage_stats": storage_stats
                }
            else:
                return result
        else:
            # No emails found - still mark as synced
            users_coll = await db_manager.get_collection(user_id, "users")
            await users_coll.update_one(
                {"user_id": user_id},
                {"$set": {
                    "fetched_email": True,  # ✅ Mark email fetch as complete
                    "initial_gmailData_sync": True,  # ✅ Mark initial sync as complete
                    "storage_optimized": True,
                    "email_sync_date": datetime.now().isoformat(),
                    "emails_processed": 0
                }},
                upsert=True
            )
            
            logger.info(f"No emails found for user {user_id} in last 6 months")
            logger.info(f"🎯 User {user_id} flags updated: fetched_email=True, initial_gmailData_sync=True")
            return {
                "success": True,  # ✅ Consistent success key
                "status": "success", 
                "message": f"No emails found for user {user_id} in last 6 months", 
                "count": 0,
                "optimization": "smart_filtering"
            }
            
    except Exception as e:
        logger.error(f"❌ [FREE TIER] Error processing emails for user {user_id}: {e}")
        return {"success": False, "status": "error", "message": str(e)}

async def check_and_fetch_new_user_emails():
    """
    PROGRESSIVE LOADING: Process only IMMEDIATE emails (1-week recent data)
    This allows users to start querying immediately while historical data loads in background
    """
    logger.info("🔄 [PROGRESSIVE] Background worker: Checking for users with fetched_email=false")
    try:
        users_to_fetch = users_collection.find({"fetched_email": False})
        users_found = 0
        async for user in users_to_fetch:
            users_found += 1
            user_id = user.get("user_id")
            access_token = user.get("access_token")
            
            if not user_id or not access_token:
                logger.warning(f"⚠️ [PROGRESSIVE] Background worker: Skipping user {user.get('_id')} due to missing user_id or access_token.")
                continue

            logger.info(f"🚀 [PROGRESSIVE] Background worker: Found user {user_id} with fetched_email=false. Starting IMMEDIATE processing.")
            
            # Reset all sync flags when starting new email fetch
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "financial_analysis_completed": False,
                    "dashboard_ready": False,
                    "background_sync_needed": False,
                    "historical_sync_completed": False,
                    "recent_financial_transactions": 0,
                    "complete_financial_ready": False
                }}
            )
            logger.info(f"🔄 [PROGRESSIVE] Reset all sync flags for user {user_id}")
            
            try:
                # 🎯 PHASE 1: Process IMMEDIATE emails (1-week recent data) - 60 seconds max
                logger.info(f"⚡ [PHASE 1] Starting IMMEDIATE email processing for user {user_id} (1-week recent data)")
                immediate_result = await _process_immediate_emails(user_id=user_id, access_token=access_token, days=7)
                logger.info(f"⚡ [PHASE 1] Immediate processing result for user {user_id}: {immediate_result}")
                
                if immediate_result.get("success", False):
                    logger.info(f"🎉 [PHASE 1] IMMEDIATE processing completed successfully for user {user_id}!")
                    logger.info(f"   📧 Recent emails processed: {immediate_result.get('emails_processed', 0)}")
                    logger.info(f"   💰 Recent financial transactions: {immediate_result.get('financial_transactions', 0)}")
                    logger.info(f"   ⏱️ Processing time: {immediate_result.get('processing_time', 'N/A')}")
                    
                    # Console message for user feedback
                    print(f"\n{'='*80}")
                    print(f"🎉 DASHBOARD READY for User: {user_id}")
                    print(f"📊 Recent emails processed: {immediate_result.get('emails_processed', 0)}")
                    print(f"💰 Recent financial transactions: {immediate_result.get('financial_transactions', 0)}")
                    print(f"✅ User can start querying immediately!")
                    print(f"🔄 Background: 6-month historical data loading...")
                    print(f"{'='*80}\n")
                    
                    # Flags are already updated in _process_immediate_emails function
                    # User can now start querying with recent data
                    
                else:
                    logger.error(f"❌ [PHASE 1] IMMEDIATE processing failed for user {user_id}: {immediate_result}")
                    # Keep fetched_email=false so it can be retried later
                    
            except Exception as user_error:
                logger.error(f"❌ [PROGRESSIVE] Failed to process IMMEDIATE emails for user {user_id}: {str(user_error)}", exc_info=True)
                # Keep fetched_email=false so it can be retried later
                logger.info(f"🔄 [PROGRESSIVE] User {user_id} will be retried in next cycle")

        if users_found == 0:
            logger.info("✅ [PROGRESSIVE] Background worker: No users found with fetched_email=false")
        else:
            logger.info(f"📊 [PROGRESSIVE] Background worker: Processed {users_found} users for IMMEDIATE sync")
            
        logger.info("🏁 [PROGRESSIVE] Background worker: Finished checking for users.")
    except Exception as e:
        logger.error(f"❌ [PROGRESSIVE] Background worker: Error during check_and_fetch_new_user_emails: {str(e)}", exc_info=True)

async def check_and_process_financial_analysis():
    """
    Background worker to process financial analysis for users who have completed email sync
    but haven't completed financial analysis yet.
    """
    logger.info("Financial worker: Checking for users needing financial analysis")
    try:
        # Find users who have completed historical sync but not complete financial analysis
        users_to_process = users_collection.find({
            "historical_sync_completed": True,
            "financial_analysis_completed": False
        })
        
        users_found = 0
        async for user in users_to_process:
            users_found += 1
            user_id = user.get("user_id")
            
            if not user_id:
                logger.warning(f"Financial worker: Skipping user {user.get('_id')} due to missing user_id.")
                continue

            logger.info(f"Financial worker: Found user {user_id} needing COMPLETE financial analysis. Starting processing.")
            
            try:
                # Import the fast processing logic
                from app.fast_financial_processor import process_financial_transactions_from_mongodb
                
                # Process COMPLETE financial transactions (recent + historical) with timeout
                result = await asyncio.wait_for(
                    process_financial_transactions_from_mongodb(user_id),
                    timeout=EMAIL_PROCESSING_TIMEOUT
                )
                
                if result["status"] == "success":
                    total_transactions = result.get('transactions_found', 0)
                    logger.info(f"Financial worker: Successfully processed COMPLETE financial data for user {user_id}")
                    logger.info(f"Financial worker: Found {total_transactions} total transactions (recent + historical)")
                    
                    # Update user status with complete financial information
                    await users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "financial_analysis_completed": True,
                            "financial_analysis_date": datetime.now().isoformat(),
                            "financial_transactions_count": total_transactions,
                            "financial_processing_method": "complete_mongodb",
                            "complete_financial_ready": True
                        }}
                    )
                    
                    # Console message for complete financial analysis
                    print(f"\n{'='*80}")
                    print(f"💰 COMPLETE FINANCIAL ANALYSIS DONE for User: {user_id}")
                    print(f"📊 Total financial transactions: {total_transactions}")
                    print(f"✅ Full financial insights now available for queries")
                    print(f"{'='*80}\n")
                    
                else:
                    logger.error(f"Financial worker: Failed to process complete financial data for user {user_id}: {result.get('error', 'Unknown error')}")
                    
            except asyncio.TimeoutError:
                logger.error(f"Financial worker: Timeout processing financial data for user {user_id}")
                # Don't reset the flag on timeout, let it retry later
            except Exception as user_error:
                logger.error(f"Financial worker: Failed to process financial data for user {user_id}: {str(user_error)}", exc_info=True)
                # Don't reset the flag on error, let it retry later

        if users_found == 0:
            logger.info("Financial worker: No users found needing financial analysis")
        else:
            logger.info(f"Financial worker: Processed financial analysis for {users_found} users")
            
        logger.info("Financial worker: Finished checking for financial analysis.")
    except Exception as e:
        logger.error(f"Financial worker: Error during check_and_process_financial_analysis: {str(e)}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    # Initialize database with performance optimizations
    try:
        from .db import initialize_free_tier_database
        await initialize_free_tier_database()
        logger.info("✅ FREE TIER database initialization complete")
    except Exception as e:
        logger.error(f"⚠️ Database initialization failed: {e}")
    
    # Schedule the email fetching job to run every 15 seconds (reduced frequency to prevent conflicts)
    scheduler.add_job(check_and_fetch_new_user_emails, "interval", seconds=15, id="fetch_new_emails_job", max_instances=1)
    
    # Schedule the NEW background historical sync job to run every 120 seconds (non-blocking, reduced frequency)
    scheduler.add_job(check_and_process_background_historical_sync, "interval", seconds=120, id="historical_sync_job", max_instances=1)
    
    # Schedule the financial analysis job to run every 90 seconds (offset to avoid conflicts)
    scheduler.add_job(check_and_process_financial_analysis, "interval", seconds=90, id="financial_analysis_job", max_instances=1)
    
    # Performance monitoring is handled by middleware
    # asyncio.create_task(performance_monitor())
    
    scheduler.start()
    logger.info("🚀 APScheduler started with PROGRESSIVE LOADING optimizations.")
    logger.info("📊 Progressive Loading Summary:")
    logger.info(f"   • Concurrent users: {CONCURRENT_USERS_LIMIT} (↑ from 15)")
    logger.info(f"   • Immediate processing: 1-week emails (⚡ instant dashboard)")
    logger.info(f"   • Background processing: 6-month emails (🔄 complete history)")
    logger.info(f"   • Smart caching: {'Enabled' if ENABLE_SMART_CACHING else 'Disabled'}")
    logger.info(f"   • Batch processing: {'Enabled' if ENABLE_BATCH_PROCESSING else 'Disabled'}")
    logger.info("   • Performance monitoring: Active")
    logger.info("📧 Job 'fetch_new_emails_job' scheduled every 10 seconds.")
    logger.info("🔄 Job 'historical_sync_job' scheduled every 30 seconds (NEW).")
    logger.info("💰 Job 'financial_analysis_job' scheduled every 45 seconds.")
    logger.info("🎯 PROGRESSIVE LOADING: Users can query immediately after 1-week sync!")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("APScheduler shut down.")

@app.post("/gmail/query")
async def gmail_query_endpoint(payload: TestMem0QueryPayload):
    """
    HTTP endpoint for Gmail Intelligence queries (alternative to WebSocket)
    """
    logger.info(f"Received Gmail query request for user_id: {payload.user_id} with query: {payload.query}")
    try:
        # Use the existing query_mem0 function
        response = await query_mem0(user_id=payload.user_id, query=payload.query)
        
        return {
            "status": "success",
            "message": response,
            "user_id": payload.user_id,
            "query": payload.query
        }
    except Exception as e:
        logger.error(f"Error in Gmail query endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.post("/admin/trigger-email-sync")
async def trigger_email_sync_for_user(payload: dict):
    """
    Manual trigger for email synchronization (for testing/debugging)
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    logger.info(f"Manual trigger: Forcing email sync for user_id: {user_id}")
    
    try:
        # Reset user status to trigger background processing
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "fetched_email": False, 
                "initial_gmailData_sync": False,
                "financial_analysis_completed": False
            }}
        )
        
        # Manually trigger the background worker
        await check_and_fetch_new_user_emails()
        
        return {
            "status": "success",
            "message": f"Email sync triggered for user {user_id}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error in manual email sync trigger: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger email sync: {str(e)}"
        )

@app.post("/admin/trigger-financial-analysis")
async def trigger_financial_analysis_for_user(payload: dict):
    """
    Manual trigger for financial analysis (for testing/debugging)
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    logger.info(f"Manual trigger: Forcing financial analysis for user_id: {user_id}")
    
    try:
        # Reset financial analysis status to trigger background processing
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"financial_analysis_completed": False}}
        )
        
        # Manually trigger the financial analysis worker
        await check_and_process_financial_analysis()
        
        return {
            "status": "success",
            "message": f"Financial analysis triggered for user {user_id}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error in manual financial analysis trigger: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger financial analysis: {str(e)}"
        )

# Pydantic models for financial endpoints
class FinancialProcessingRequest(BaseModel):
    jwt_token: str

class FastFinancialProcessingRequest(BaseModel):
    jwt_token: str

class GmailDownloadRequest(BaseModel):
    jwt_token: str

@app.post("/gmail/download-data")
async def download_gmail_data(payload: GmailDownloadRequest):
    """
    🚀 NEW: Download Gmail data for the last 6 months in JSON format
    
    This endpoint:
    1. Validates JWT token
    2. Fetches user's Gmail data for the last 6 months
    3. Returns complete email data in JSON format
    4. Includes email content, headers, attachments info, and metadata
    """
    try:
        logger.info(f"📥 Gmail data download request received")
        
        # 1. Validate JWT token
        try:
            payload_data = decode_jwt_token(payload.jwt_token)
            user_id = payload_data.get("user_id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: no user_id")
                
            logger.info(f"✅ JWT token validated for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ JWT token validation failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        # 2. Get user data from database
        try:
            users_collection = await db_manager.get_collection(user_id, "users")
            user_data = await users_collection.find_one({"user_id": user_id})
            
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            
            access_token = user_data.get("access_token")
            refresh_token = user_data.get("refresh_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No Gmail access token found")
                
            logger.info(f"✅ User data retrieved for: {user_data.get('email', 'unknown')}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error retrieving user data: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving user data")
        
        # 3. Build Gmail service
        try:
            service = build_gmail_service(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
            )
            logger.info(f"✅ Gmail service built successfully")
            
        except Exception as e:
            logger.error(f"❌ Error building Gmail service: {e}")
            raise HTTPException(status_code=500, detail="Error connecting to Gmail")
        
        # 4. Fetch Gmail data for last 6 months
        try:
            logger.info(f"📧 Fetching Gmail data for last 6 months...")
            
            # Calculate date range (6 months ago) - make timezone-aware
            from datetime import timezone
            six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
            logger.info(f"📅 Date range: from {six_months_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
            
            # Use the simpler Gmail fetch function for download API
            # Start with a smaller limit for faster response, can be increased later
            logger.info(f"🔄 Starting Gmail API fetch (max 1000 emails)...")
            emails = await fetch_gmail_emails(
                service=service,
                user_id='me',
                max_results=1000  # Reduced limit for faster response
            )
            logger.info(f"📧 Gmail API returned {len(emails)} emails")
            
            # Filter emails to last 6 months if needed
            if emails:
                logger.info(f"🔄 Filtering emails to last 6 months...")
                filtered_emails = []
                for i, email in enumerate(emails):
                    if i % 100 == 0:  # Log progress every 100 emails
                        logger.info(f"📊 Filtering progress: {i}/{len(emails)} emails processed")
                    
                    email_date = email.get('date')
                    if email_date:
                        # Handle different date formats and make timezone-aware
                        if isinstance(email_date, str):
                            try:
                                email_date = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                            except:
                                continue
                        elif hasattr(email_date, 'replace'):  # datetime object
                            # Make timezone-aware if it's naive
                            if email_date.tzinfo is None:
                                email_date = email_date.replace(tzinfo=timezone.utc)
                        else:
                            continue
                        
                        # Check if email is within last 6 months (both are now timezone-aware)
                        if email_date >= six_months_ago:
                            filtered_emails.append(email)
                
                emails = filtered_emails
                logger.info(f"📊 After 6-month filter: {len(emails)} emails remain")
            
            logger.info(f"✅ Fetched {len(emails)} emails from last 6 months")
            
        except Exception as e:
            logger.error(f"❌ Error fetching Gmail data: {e}")
            raise HTTPException(status_code=500, detail="Error fetching Gmail data")
        
        # 5. Process and enrich email data
        try:
            logger.info(f"🔄 Processing and enriching email data...")
            
            # Use the complete email extractor to get full data (already imported at top)
            
            processed_emails = []
            for email in emails:
                try:
                    # Extract complete email data
                    complete_email = email_extractor.extract_complete_email_data(email)
                    
                    # Convert datetime objects to strings for JSON serialization
                    if isinstance(complete_email.get('date'), datetime):
                        complete_email['date'] = complete_email['date'].isoformat()
                    if isinstance(complete_email.get('extracted_at'), datetime):
                        complete_email['extracted_at'] = complete_email['extracted_at'].isoformat()
                    
                    processed_emails.append(complete_email)
                    
                except Exception as email_error:
                    logger.warning(f"⚠️ Error processing email {email.get('id', 'unknown')}: {email_error}")
                    # Include basic email data even if processing fails
                    basic_email = {
                        "id": email.get("id"),
                        "subject": email.get("subject", "No Subject"),
                        "sender": email.get("sender", "Unknown"),
                        "date": email.get("date", datetime.now()).isoformat() if isinstance(email.get("date"), datetime) else str(email.get("date", "")),
                        "snippet": email.get("snippet", ""),
                        "error": "Processing failed"
                    }
                    processed_emails.append(basic_email)
            
            logger.info(f"✅ Processed {len(processed_emails)} emails successfully")
            
        except Exception as e:
            logger.error(f"❌ Error processing email data: {e}")
            raise HTTPException(status_code=500, detail="Error processing email data")
        
        # 6. Prepare response data
        try:
            response_data = {
                "status": "success",
                "user_info": {
                    "user_id": user_id,
                    "email": user_data.get("email", "unknown"),
                    "name": user_data.get("name", "unknown")
                },
                "data_info": {
                    "total_emails": len(processed_emails),
                    "date_range": f"Last 6 months (from {six_months_ago.strftime('%Y-%m-%d')})",
                    "download_timestamp": datetime.now().isoformat(),
                    "data_completeness": "full"  # Complete headers, body, attachments info
                },
                "emails": processed_emails,
                "extraction_stats": email_extractor.get_extraction_stats(),
                "metadata": {
                    "api_version": "1.2.0",
                    "format": "json",
                    "compression": "none",
                    "includes": [
                        "email_headers",
                        "email_body", 
                        "attachment_info",
                        "financial_classification",
                        "importance_scores"
                    ]
                }
            }
            
            logger.info(f"✅ Gmail data download completed successfully")
            logger.info(f"📊 Response summary: {len(processed_emails)} emails, {len(json.dumps(response_data))} bytes")
            
            return JSONResponse(
                content=response_data,
                headers={
                    "Content-Type": "application/json",
                    "Content-Disposition": f"attachment; filename=gmail_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error preparing response: {e}")
            raise HTTPException(status_code=500, detail="Error preparing download")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in Gmail data download: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/financial/process-from-emails")
async def process_financial_from_stored_emails(payload: FastFinancialProcessingRequest):
    """
    FAST Financial Processing - Process emails already stored in MongoDB
    This is much faster than /financial/process as it doesn't fetch from Gmail API
    
    Usage: POST /financial/process-from-emails
    Body: {"jwt_token": "your_jwt_token"}
    
    Returns: Processed financial transactions from existing emails
    """
    logger.info("Received request for FAST /financial/process-from-emails")
    try:
        # Authenticate user with JWT
        user = decode_jwt_token(payload.jwt_token)
        user_id = user.get("user_id")
        user_email = user.get("email")
        logger.info(f"JWT decoded. User ID: {user_id}, Email: {user_email}")
        
        # Use email processing context for resource management
        async with email_processing_context(user_id) as rm:
            # Import the fast processing logic
            from app.fast_financial_processor import process_financial_transactions_from_mongodb
            
            # Process transactions from MongoDB emails with timeout
            logger.info(f"Starting fast financial processing for user {user_id}")
            result = await asyncio.wait_for(
                process_financial_transactions_from_mongodb(user_id),
                timeout=EMAIL_PROCESSING_TIMEOUT
            )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
            return {
                "message": "Fast financial transaction processing completed successfully",
                "processing_method": "mongodb_emails",
                "speed": "fast",
                "data": result
            }
        
    except asyncio.TimeoutError:
        logger.error(f"Fast financial processing timeout for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Financial processing timed out after {EMAIL_PROCESSING_TIMEOUT} seconds"
        )
    except HTTPException as e:
        logger.error(f"HTTPException in fast financial processing: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in fast financial processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during fast financial processing: {str(e)}"
        )

@app.post("/financial/process")
async def process_financial_transactions(payload: FinancialProcessingRequest):
    """
    Process financial transactions for authenticated user
    Fetches 5 months of financial transaction data from Gmail
    """
    logger.info("Received request for /financial/process")
    try:
        # Authenticate user with JWT
        user = decode_jwt_token(payload.jwt_token)
        user_id = user.get("user_id")
        logger.info(f"JWT decoded. User ID: {user_id}")
        
        # Get user data from database to get tokens
        user_in_db = await users_collection.find_one({"user_id": user_id})
        if not user_in_db:
            raise HTTPException(status_code=404, detail="User not found")
        
        access_token = user_in_db.get("access_token")
        refresh_token = user_in_db.get("refresh_token")
        
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="Missing authentication tokens. Please re-authenticate.")
        
        # Process financial transactions
        result = await process_financial_transactions_for_user(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return {
            "message": "Financial transaction processing completed successfully",
            "data": result
        }
        
    except HTTPException as e:
        logger.error(f"HTTPException in financial processing: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in financial processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/financial/summary")
async def get_user_financial_summary(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get financial summary for authenticated user
    Returns comprehensive financial analytics and insights
    """
    logger.info("Received request for /financial/summary")
    try:
        # Extract JWT token from Authorization header
        token = credentials.credentials
        user = decode_jwt_token(token)
        user_id = user.get("user_id")
        
        # Get financial summary
        summary = await get_financial_summary(user_id)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail="Financial summary not found. Please process financial transactions first."
            )
        
        return {
            "status": "success",
            "data": summary
        }
        
    except HTTPException as e:
        logger.error(f"HTTPException in financial summary: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in financial summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Removed duplicate /financial/transactions endpoint - functionality available via /financial/transactions/all

# Removed duplicate /financial/analyze endpoint - functionality available via /gmail/query with financial context

@app.get("/financial/transactions/all")
async def get_all_user_financial_transactions(jwt_token: str):
    """
    GET endpoint to retrieve all financial transactions for a user
    Takes JWT token as query parameter for Postman testing
    
    Usage: GET /financial/transactions/all?jwt_token=your_jwt_token_here
    
    Returns:
    - All financial transactions (credit card, debit card, UPI, bank transfers, etc.)
    - Comprehensive transaction data including merchant info, amounts, dates, categories
    - Structured JSON format ready for analysis and visualization
    """
    logger.info("Received GET request for /financial/transactions/all")
    try:
        # Authenticate user with JWT token from query parameter
        logger.info("Decoding JWT token from query parameter...")
        user = decode_jwt_token(jwt_token)
        user_id = user.get("user_id")
        user_email = user.get("email")
        logger.info(f"JWT decoded. User ID: {user_id}, Email: {user_email}")

        # Get all financial transactions for this user (no limit)
        logger.info(f"Fetching all financial transactions for user: {user_id}")
        transactions = await get_financial_transactions(user_id, limit=10000)  # High limit to get all
        
        # Also get financial summary for additional insights
        summary = await get_financial_summary(user_id)
        
        # Count transactions by type for quick overview
        transaction_types = {}
        payment_methods = {}
        merchants = {}
        total_amount = 0.0
        
        for txn in transactions:
            # Count by transaction type
            txn_type = txn.get('transaction_type', 'unknown')
            transaction_types[txn_type] = transaction_types.get(txn_type, 0) + 1
            
            # Count by payment method
            payment_method = txn.get('payment_method', 'unknown')
            payment_methods[payment_method] = payment_methods.get(payment_method, 0) + 1
            
            # Count by merchant
            merchant = txn.get('merchant', 'unknown')
            merchants[merchant] = merchants.get(merchant, 0) + 1
            
            # Sum total amount
            amount = txn.get('amount', 0)
            if amount:
                total_amount += float(amount)

        # Prepare response with comprehensive data
        response_data = {
            "status": "success",
            "user_info": {
                "user_id": user_id,
                "email": user_email
            },
            "transactions": {
                "count": len(transactions),
                "total_amount": round(total_amount, 2),
                "data": transactions
            },
            "analytics": {
                "transaction_types": transaction_types,
                "payment_methods": payment_methods,
                "top_merchants": dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:10]),
                "summary": summary
            },
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "data_includes": [
                    "credit_card_transactions",
                    "debit_card_transactions", 
                    "upi_transactions",
                    "bank_transfers",
                    "online_payments",
                    "subscription_payments",
                    "refunds_and_cashbacks",
                    "bill_payments",
                    "investment_transactions"
                ]
            }
        }
        
        logger.info(f"Successfully retrieved {len(transactions)} financial transactions for user {user_id}")
        return response_data
        
    except HTTPException as e:
        logger.error(f"HTTPException in get_all_user_financial_transactions: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_all_user_financial_transactions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching financial transactions: {str(e)}"
        )

@app.get("/financial/transactions/enhanced")
async def get_enhanced_financial_transactions(jwt_token: str):
    """
    ENHANCED endpoint to retrieve all financial transactions with comprehensive details
    
    Returns:
    - Proper transaction IDs (not generic keywords)
    - Bank account details (masked account numbers, bank names, account holder names)
    - UPI transaction details (UPI IDs, app names, receiver names)
    - Card transaction details (masked card numbers, card types, bank names)
    - Complete transaction metadata
    
    Usage: GET /financial/transactions/enhanced?jwt_token=your_jwt_token_here
    """
    logger.info("Received GET request for /financial/transactions/enhanced")
    try:
        # Authenticate user with JWT token
        user = decode_jwt_token(jwt_token)
        user_id = user.get("user_id")
        user_email = user.get("email")
        logger.info(f"JWT decoded. User ID: {user_id}, Email: {user_email}")

        # Process transactions with enhanced extractor
        from app.fast_financial_processor import EnhancedTransactionExtractor
        
        # Get all emails for the user
        cursor = emails_collection.find({"user_id": user_id})
        all_emails = await cursor.to_list(length=None)
        
        logger.info(f"Found {len(all_emails)} total emails in MongoDB")
        
        # Extract enhanced financial transactions
        extractor = EnhancedTransactionExtractor()
        enhanced_transactions = []
        transactions_without_ids = []
        
        for email in all_emails:
            if extractor.is_financial_email(email):
                transaction = extractor.extract_transaction(email, user_id)
                if transaction:
                    if transaction.get('transaction_id'):
                        enhanced_transactions.append(transaction)
                    else:
                        # Include transactions without IDs but mark them separately
                        transaction['transaction_id'] = f"NO_ID_{transaction['id'][-8:]}"
                        transaction['id_type'] = 'generated'
                        transactions_without_ids.append(transaction)
        
        # Combine all transactions (prioritize those with proper IDs)
        all_enhanced_transactions = enhanced_transactions + transactions_without_ids
        
        logger.info(f"Extracted {len(enhanced_transactions)} transactions with proper IDs and {len(transactions_without_ids)} without IDs")

        # Calculate analytics
        total_amount = sum(t['amount'] for t in all_enhanced_transactions if t['amount'])
        
        # Enhanced analytics with detailed breakdowns
        transaction_types = {}
        payment_methods = {}
        merchants = {}
        banks = {}
        upi_apps = {}
        
        for txn in all_enhanced_transactions:
            # Transaction types
            txn_type = txn.get('transaction_type', 'unknown')
            transaction_types[txn_type] = transaction_types.get(txn_type, 0) + 1
            
            # Payment methods  
            payment_method = txn.get('payment_method', 'unknown')
            payment_methods[payment_method] = payment_methods.get(payment_method, 0) + 1
            
            # Merchants
            merchant = txn.get('merchant', 'unknown')
            merchants[merchant] = merchants.get(merchant, 0) + 1
            
            # Banks
            bank_name = txn.get('bank_details', {}).get('bank_name')
            if bank_name:
                banks[bank_name] = banks.get(bank_name, 0) + 1
            
            # UPI Apps
            upi_app = txn.get('upi_details', {}).get('app_name')
            if upi_app:
                upi_apps[upi_app] = upi_apps.get(upi_app, 0) + 1

        # Create comprehensive response
        response_data = {
            "status": "success",
            "user_info": {
                "user_id": user_id,
                "email": user_email
            },
            "transactions": {
                "count": len(all_enhanced_transactions),
                "total_amount": round(total_amount, 2),
                "data": all_enhanced_transactions
            },
            "enhanced_analytics": {
                "transaction_types": transaction_types,
                "payment_methods": payment_methods,
                "top_merchants": dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:10]),
                "banks_used": banks,
                "upi_apps_used": upi_apps,
                "summary": {
                    "user_id": user_id,
                    "period": "all_stored_emails",
                    "total_transactions": len(all_enhanced_transactions),
                    "total_amount": total_amount,
                    "average_transaction": total_amount / len(all_enhanced_transactions) if all_enhanced_transactions else 0,
                    "merchant_breakdown": dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True)),
                    "payment_method_breakdown": payment_methods,
                    "transaction_type_breakdown": transaction_types,
                    "generated_at": datetime.now().isoformat()
                }
            },
            "data_quality": {
                "transactions_with_proper_ids": len(enhanced_transactions),
                "transactions_with_generated_ids": len(transactions_without_ids),
                "total_transactions": len(all_enhanced_transactions),
                "transactions_with_bank_details": len([t for t in all_enhanced_transactions if t.get('bank_details', {}).get('bank_name')]),
                "transactions_with_upi_details": len([t for t in all_enhanced_transactions if t.get('upi_details')]),
                "transactions_with_card_details": len([t for t in all_enhanced_transactions if t.get('card_details')]),
                "extraction_method": "enhanced_regex_patterns",
                "validation_applied": "includes_subscription_transactions"
            },
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "extraction_improvements": [
                    "proper_transaction_id_extraction",
                    "bank_account_details_extraction", 
                    "upi_id_and_app_detection",
                    "card_details_extraction",
                    "merchant_name_enhancement",
                    "payment_method_classification"
                ],
                "data_includes": [
                    "bank_account_numbers_masked",
                    "bank_names",
                    "account_holder_names_where_available",
                    "transaction_ids_validated", 
                    "upi_transaction_ids",
                    "upi_virtual_payment_addresses",
                    "upi_app_names",
                    "card_numbers_masked",
                    "card_types_detected",
                    "enhanced_merchant_detection"
                ]
            }
        }
        
        logger.info(f"Successfully retrieved {len(all_enhanced_transactions)} enhanced financial transactions")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in get_enhanced_financial_transactions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Add new storage monitoring endpoints
@app.get("/storage/stats")
async def get_storage_stats():
    """
    Get comprehensive storage statistics for FREE TIER monitoring
    
    Returns:
    - Storage usage across all database shards
    - Compression ratios and space savings
    - User distribution across databases
    - Cleanup recommendations
    """
    try:
        storage_stats = await get_storage_statistics()
        
        return {
            "message": "FREE TIER storage statistics",
            "timestamp": datetime.now().isoformat(),
            "storage": storage_stats,
            "recommendations": _get_storage_recommendations(storage_stats)
        }
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return {"error": str(e)}

@app.post("/storage/cleanup")
async def trigger_storage_cleanup():
    """
    Manually trigger storage cleanup
    
    - Removes emails older than 6 months
    - Cleans up temporary processing data
    - Optimizes database indexes
    """
    try:
        logger.info("🧹 Manual storage cleanup triggered")
        
        # Get stats before cleanup
        before_stats = await cleanup_manager.get_storage_stats()
        
        # Run cleanup
        await cleanup_manager.cleanup_all_users()
        
        # Get stats after cleanup
        after_stats = await cleanup_manager.get_storage_stats()
        
        # Calculate cleanup impact
        emails_removed = before_stats["total_emails"] - after_stats["total_emails"]
        space_freed = before_stats["total_storage_mb"] - after_stats["total_storage_mb"]
        
        logger.info(f"✅ Cleanup complete: {emails_removed} emails removed, {space_freed:.1f}MB freed")
        
        return {
            "message": "Storage cleanup completed successfully",
            "emails_removed": emails_removed,
            "space_freed_mb": round(space_freed, 1),
            "before_stats": before_stats,
            "after_stats": after_stats
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return {"error": str(e)}

@app.get("/storage/recommendations")
async def get_storage_recommendations():
    """Get intelligent storage optimization recommendations"""
    try:
        storage_stats = await get_storage_statistics()
        recommendations = _get_storage_recommendations(storage_stats)
        
        return {
            "message": "Storage optimization recommendations",
            "current_usage": storage_stats,
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {"error": str(e)}

def _get_storage_recommendations(storage_stats: dict) -> List[str]:
    """Generate intelligent storage recommendations"""
    recommendations = []
    usage_percent = storage_stats.get("usage_percent", 0)
    
    if usage_percent > 85:
        recommendations.append("🚨 CRITICAL: Storage usage > 85%. Immediate cleanup required!")
        recommendations.append("🧹 Run manual cleanup: POST /storage/cleanup")
        recommendations.append("📧 Consider reducing email retention period")
    elif usage_percent > 70:
        recommendations.append("⚠️ WARNING: Storage usage > 70%. Cleanup recommended soon.")
        recommendations.append("🗄️ Consider setting up additional database shards")
    else:
        recommendations.append("✅ Storage usage healthy")
    
    if not storage_stats.get("compression_enabled", False):
        recommendations.append("🗜️ Enable compression for 90% space savings")
    
    if ENABLE_AUTO_CLEANUP:
        recommendations.append("🔄 Auto-cleanup is enabled (runs every 6 hours)")
    else:
        recommendations.append("⏰ Consider enabling auto-cleanup for maintenance-free operation")
    
    return recommendations

# Update health check to include storage monitoring
@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check with FREE TIER storage monitoring"""
    try:
        # Get storage statistics
        storage_stats = await get_storage_statistics()
        
        # Determine overall health
        storage_status = storage_stats.get("status", "unknown")
        usage_percent = storage_stats.get("usage_percent", 0)
        
        health_status = "healthy"
        if usage_percent > 85:
            health_status = "critical"
        elif usage_percent > 70:
            health_status = "warning"
        
        # Get system information
        from .mem0_agent_agno import get_system_info
        system_info = get_system_info()
        
        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "version": "FREE TIER OPTIMIZED",
            "database": {
                "sharding_enabled": ENABLE_DATABASE_SHARDING,
                "auto_cleanup_enabled": ENABLE_AUTO_CLEANUP,
                "storage_status": storage_status,
                "usage_percent": usage_percent,
                "total_users": storage_stats.get("storage_stats", {}).get("total_users", 0),
                "total_emails": storage_stats.get("storage_stats", {}).get("total_emails", 0)
            },
            "optimization": {
                "compression_enabled": storage_stats.get("compression_enabled", False),
                "retention_days": storage_stats.get("retention_days", 180),
                "emails_per_user_avg": storage_stats.get("emails_per_user_avg", 0)
            },
            "system": system_info,
            "recommendations": _get_storage_recommendations(storage_stats) if health_status != "healthy" else []
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Add startup event for database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks"""
    try:
        from .db import initialize_free_tier_database
        await initialize_free_tier_database()
        logger.info("✅ FREE TIER database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Update startup message
logger.info("🚀 FREE TIER Gmail Chatbot Backend Started!")
logger.info(f"   💰 Cost: $0 (100% free)")
logger.info(f"   🗄️ Database sharding: {'Enabled' if ENABLE_DATABASE_SHARDING else 'Disabled'}")
logger.info(f"   🧹 Auto cleanup: {'Enabled' if ENABLE_AUTO_CLEANUP else 'Disabled'}")
logger.info(f"   📧 Email retention: 6 months maximum")
logger.info(f"   🗜️ Storage compression: 90% space saving")
logger.info(f"   ♾️ Scalability: Infinite (with multiple free accounts)")
logger.info("   🔗 Monitoring: /storage/stats, /storage/cleanup, /health")

# Add new progressive loading functions after the existing imports and before the main endpoints

# ============================================================================
# PROGRESSIVE EMAIL LOADING SYSTEM
# ============================================================================

async def _process_immediate_emails(user_id: str, access_token: str, days: int = 7, websocket_client_id: str = None) -> Dict[str, Any]:
    """
    IMMEDIATE Processing: Fetch and process recent emails (1 week) for instant dashboard access
    This runs synchronously when user hits /gmail/fetch for immediate user experience
    """
    start_time = datetime.now()
    logger.info(f"🚀 [IMMEDIATE] Starting {days}-day email processing for user: {user_id}")
    logger.info(f"   📅 Date range: Last {days} days")
    logger.info(f"   📧 Max emails: 500")
    logger.info(f"   ⏰ Started at: {start_time.strftime('%H:%M:%S')}")
    
    try:
        # Step 1: Build Gmail service (memory-safe)
        logger.info(f"🔑 [IMMEDIATE] Step 1: Building Gmail service for user {user_id}")
        credentials = Credentials(token=access_token)
        # Disable discovery cache to prevent memory issues
        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        logger.info(f"✅ [IMMEDIATE] Gmail service built successfully (cache disabled)")
        
        # Step 2: Fetch recent emails only (much faster)
        logger.info(f"📧 [IMMEDIATE] Step 2: Fetching {days}-day recent emails...")
        
        # Send progress update if WebSocket is available
        if websocket_client_id:
            try:
                from .websocket import manager
                await manager.send_progress_update(
                    websocket_client_id, 
                    "fetching_emails", 
                    f"Fetching {days}-day recent emails from Gmail...", 
                    40
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket progress update failed: {ws_error}")
        
        from .gmail import fetch_gmail_emails_by_days
        emails = await fetch_gmail_emails_by_days(service, user_id, days=days, max_results=500)
        logger.info(f"📊 [IMMEDIATE] Fetched {len(emails) if emails else 0} recent emails")
        
        # Send fetch completion update
        if websocket_client_id:
            try:
                from .websocket import manager
                await manager.send_progress_update(
                    websocket_client_id, 
                    "emails_fetched", 
                    f"Fetched {len(emails) if emails else 0} recent emails", 
                    50,
                    {"emails_count": len(emails) if emails else 0}
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket progress update failed: {ws_error}")
        
        if emails:
            logger.info(f"🔄 [IMMEDIATE] Step 3: Processing {len(emails)} emails for storage...")
            
            # Force garbage collection before processing to free memory
            import gc
            gc.collect()
            logger.info(f"🧹 [IMMEDIATE] Memory cleanup completed before processing")
            
            # Send processing update
            if websocket_client_id:
                try:
                    from .websocket import manager
                    await manager.send_progress_update(
                        websocket_client_id, 
                        "processing_emails", 
                        f"Processing and storing {len(emails)} emails...", 
                        60
                    )
                except Exception as ws_error:
                    logger.warning(f"WebSocket progress update failed: {ws_error}")
            
            # Process and store recent emails
            result = await process_and_store_emails(user_id, emails, is_immediate=True)
            
            if result.get("success", False):
                emails_stored = result.get('emails_stored', 0)
                logger.info(f"✅ [IMMEDIATE] Step 3 Complete: Successfully processed {emails_stored} recent emails")
                logger.info(f"   📊 Storage result: {result}")
                
                # Step 4: PARALLEL PROCESSING - Financial Analysis + Mem0 Upload
                logger.info(f"🚀 [IMMEDIATE] Step 4: Starting PARALLEL processing (Financial + Mem0)...")
                
                # Send parallel processing update
                if websocket_client_id:
                    try:
                        from .websocket import manager
                        await manager.send_progress_update(
                            websocket_client_id, 
                            "parallel_processing", 
                            "Starting parallel financial analysis and Mem0 upload...", 
                            70
                        )
                    except Exception as ws_error:
                        logger.warning(f"WebSocket progress update failed: {ws_error}")
                
                # Import parallel processing components
                from .mem0_agent_agno import call_financial_processing_api, parallel_processor, EmailMessage
                
                # Convert emails to EmailMessage format for parallel processing
                email_messages = []
                for email in emails[:emails_stored]:  # Only process stored emails
                    try:
                        # Handle date conversion properly
                        date_value = email.get("date", "")
                        if hasattr(date_value, 'isoformat'):  # It's a datetime object
                            date_str = date_value.isoformat()
                        elif isinstance(date_value, str):
                            date_str = date_value
                        else:
                            date_str = str(date_value) if date_value else ""
                        
                        email_msg = EmailMessage(
                            id=email.get("id", ""),
                            subject=email.get("subject", ""),
                            sender=email.get("sender", ""),
                            snippet=email.get("snippet", ""),
                            body=email.get("body", ""),
                            date=date_str
                        )
                        email_messages.append(email_msg)
                    except Exception as e:
                        logger.error(f"Error converting email to EmailMessage: {e}")
                        continue
                
                # PARALLEL EXECUTION: Financial Processing + Mem0 Upload
                try:
                    logger.info(f"⚡ [IMMEDIATE] Starting parallel tasks: Financial API + Mem0 Upload")
                    
                    # Create parallel tasks
                    financial_task = asyncio.create_task(
                        call_financial_processing_api(user_id, "immediate_7day")
                    )
                    
                    mem0_task = asyncio.create_task(
                        parallel_processor.upload_emails_parallel_with_priority(
                            user_id, email_messages, websocket_client_id
                        )
                    )
                    
                    # Wait for both tasks to complete
                    financial_result, mem0_result = await asyncio.gather(
                        financial_task, mem0_task, return_exceptions=True
                    )
                    
                    # Process financial result with enhanced error handling
                    if isinstance(financial_result, Exception):
                        logger.error(f"❌ [IMMEDIATE] Financial processing failed: {financial_result}")
                        recent_transactions = 0
                    elif financial_result.get("success", False):
                        recent_transactions = financial_result.get('transactions_found', 0)
                        logger.info(f"✅ [IMMEDIATE] Financial processing complete: {recent_transactions} transactions found")
                    else:
                        recent_transactions = 0
                        error_msg = financial_result.get('error', 'Unknown error')
                        
                        # Check if it's a timeout - don't treat as critical error
                        if "timed out" in error_msg.lower():
                            logger.warning(f"⚠️ [IMMEDIATE] Financial processing timed out - dashboard will still be ready")
                            logger.info(f"📋 [IMMEDIATE] Financial analysis will continue in background")
                        else:
                            logger.warning(f"⚠️ [IMMEDIATE] Financial processing failed: {error_msg}")
                    
                    # Process Mem0 result
                    if isinstance(mem0_result, Exception):
                        logger.error(f"❌ [IMMEDIATE] Mem0 parallel processing failed: {mem0_result}")
                        mem0_success = False
                    elif mem0_result.get("success", False):
                        logger.info(f"✅ [IMMEDIATE] Mem0 parallel processing complete: {mem0_result.get('priority_emails_processed', 0)} priority emails processed")
                        mem0_success = True
                    else:
                        logger.warning(f"⚠️ [IMMEDIATE] Mem0 parallel processing failed: {mem0_result.get('message', 'Unknown error')}")
                        mem0_success = False
                    
                    logger.info(f"🎉 [IMMEDIATE] PARALLEL PROCESSING COMPLETE:")
                    logger.info(f"   💰 Financial transactions found: {recent_transactions}")
                    logger.info(f"   🧠 Mem0 processing success: {mem0_success}")
                    logger.info(f"   ⚡ Both processes ran in parallel for maximum speed!")
                    
                except Exception as parallel_error:
                    logger.error(f"❌ [IMMEDIATE] Parallel processing error: {parallel_error}", exc_info=True)
                    recent_transactions = 0
                
                # Step 5: Update user flags for immediate access with financial data
                logger.info(f"🔄 [IMMEDIATE] Step 5: Updating user flags for immediate access...")
                users_coll = await db_manager.get_collection(user_id, "users")
                await users_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "fetched_email": True,  # ✅ Enable dashboard access
                        "recent_sync_completed": True,  # ✅ Recent data ready
                        "recent_sync_date": datetime.now().isoformat(),
                        "recent_emails_processed": emails_stored,
                        "recent_financial_transactions": recent_transactions,  # ✅ Recent financial data
                        "dashboard_ready": True,  # ✅ User can start querying
                        "background_sync_needed": True  # 🔄 Trigger background processing
                    }},
                    upsert=True
                )
                
                # Calculate processing time
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                logger.info(f"🎉 [IMMEDIATE] COMPLETE SUCCESS for user {user_id}:")
                logger.info(f"   📧 Recent emails processed: {emails_stored}")
                logger.info(f"   💰 Financial transactions: {recent_transactions}")
                logger.info(f"   ⏱️ Processing time: {processing_time:.2f} seconds")
                logger.info(f"   ✅ Dashboard ready: User can start querying!")
                logger.info(f"   🔄 Background sync: Historical data will load in background")
                
                return {
                    "success": True,
                    "status": "immediate_ready",
                    "message": f"Dashboard ready! {emails_stored} recent emails processed, {recent_transactions} financial transactions found. Historical data loading in background.",
                    "emails_processed": emails_stored,
                    "financial_transactions": recent_transactions,
                    "processing_time": f"{processing_time:.2f}s",
                    "dashboard_ready": True,
                    "background_processing": True,
                    "financial_ready": recent_transactions > 0,
                    "processing_type": "immediate"
                }
            else:
                logger.error(f"❌ [IMMEDIATE] Step 3 Failed: Email storage failed for user {user_id}")
                logger.error(f"   📊 Storage result: {result}")
                return result
        else:
            # No recent emails - still enable dashboard and check for existing financial data
            logger.info(f"📭 [IMMEDIATE] No recent emails found for user {user_id}")
            logger.info(f"💰 [IMMEDIATE] Step 3: Checking existing financial data...")
            recent_transactions = 0
            try:
                from app.fast_financial_processor import process_financial_transactions_from_mongodb
                
                # Check for any existing financial transactions
                financial_result = await asyncio.wait_for(
                    process_financial_transactions_from_mongodb(user_id),
                    timeout=15  # Quick check
                )
                
                if financial_result["status"] == "success":
                    recent_transactions = financial_result.get('transactions_found', 0)
                    logger.info(f"✅ [IMMEDIATE] Found {recent_transactions} existing financial transactions")
                else:
                    logger.info(f"📊 [IMMEDIATE] No existing financial transactions found")
                    
            except Exception as financial_error:
                logger.warning(f"⚠️ [IMMEDIATE] Financial check failed: {financial_error}")
            
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.info(f"🔄 [IMMEDIATE] Step 4: Updating user flags (no recent emails case)...")
            users_coll = await db_manager.get_collection(user_id, "users")
            await users_coll.update_one(
                {"user_id": user_id},
                {"$set": {
                    "fetched_email": True,
                    "recent_sync_completed": True,
                    "dashboard_ready": True,
                    "background_sync_needed": True,
                    "recent_emails_processed": 0,
                    "recent_financial_transactions": recent_transactions
                }},
                upsert=True
            )
            
            logger.info(f"🎉 [IMMEDIATE] COMPLETE SUCCESS for user {user_id} (no recent emails):")
            logger.info(f"   📧 Recent emails processed: 0")
            logger.info(f"   💰 Financial transactions: {recent_transactions}")
            logger.info(f"   ⏱️ Processing time: {processing_time:.2f} seconds")
            logger.info(f"   ✅ Dashboard ready: User can start querying!")
            logger.info(f"   🔄 Background sync: Historical data will load in background")
            
            return {
                "success": True,
                "status": "immediate_ready",
                "message": f"Dashboard ready! No recent emails found, {recent_transactions} financial transactions available. Historical data loading in background.",
                "emails_processed": 0,
                "financial_transactions": recent_transactions,
                "processing_time": f"{processing_time:.2f}s",
                "dashboard_ready": True,
                "background_processing": True,
                "financial_ready": recent_transactions > 0,
                "processing_type": "immediate"
            }
            
    except Exception as e:
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.error(f"❌ [IMMEDIATE] CRITICAL ERROR for user {user_id}:")
        logger.error(f"   🚨 Error: {str(e)}")
        logger.error(f"   ⏱️ Failed after: {processing_time:.2f} seconds")
        logger.error(f"   🔄 User will be retried in next cycle")
        return {"success": False, "status": "error", "message": str(e), "processing_time": f"{processing_time:.2f}s"}

async def _process_historical_emails(user_id: str, access_token: str, months: int = 6) -> Dict[str, Any]:
    """
    BACKGROUND Processing: Fetch and process historical emails (6 months) for complete data
    This runs in background worker after immediate processing is complete
    """
    logger.info(f"🔄 [BACKGROUND] Processing {months}-month historical emails for user: {user_id}")
    
    try:
        # Build Gmail service
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Fetch historical emails (excluding recent 7 days already processed)
        from .gmail import fetch_gmail_emails_historical
        emails = await fetch_gmail_emails_historical(service, user_id, months=months, exclude_recent_days=7, max_results=5000)
        
        if emails:
            # Process and store historical emails
            result = await process_and_store_emails(user_id, emails, is_historical=True)
            
            if result.get("success", False):
                logger.info(f"✅ [BACKGROUND] Successfully processed {result['emails_stored']} historical emails")
                
                # Update user flags for complete sync
                users_coll = await db_manager.get_collection(user_id, "users")
                await users_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "initial_gmailData_sync": True,  # ✅ Complete data sync done
                        "historical_sync_completed": True,
                        "historical_sync_date": datetime.now().isoformat(),
                        "historical_emails_processed": result['emails_stored'],
                        "background_sync_needed": False,  # ✅ Background processing complete
                        "total_emails_processed": result.get('total_count', 0)
                    }},
                    upsert=True
                )
                
                logger.info(f"🎉 [BACKGROUND] User {user_id} complete sync finished - {result['emails_stored']} historical emails")
                
                return {
                    "success": True,
                    "status": "historical_complete",
                    "message": f"Complete email sync finished! {result['emails_stored']} historical emails processed.",
                    "historical_emails_count": result['emails_stored'],
                    "complete_sync": True,
                    "processing_type": "historical"
                }
            else:
                return result
        else:
            # No historical emails found - mark as complete
            users_coll = await db_manager.get_collection(user_id, "users")
            await users_coll.update_one(
                {"user_id": user_id},
                {"$set": {
                    "initial_gmailData_sync": True,
                    "historical_sync_completed": True,
                    "background_sync_needed": False,
                    "historical_emails_processed": 0
                }},
                upsert=True
            )
            
            return {
                "success": True,
                "status": "historical_complete", 
                "message": "Complete email sync finished! No additional historical emails found.",
                "historical_emails_count": 0,
                "complete_sync": True,
                "processing_type": "historical"
            }
            
    except Exception as e:
        logger.error(f"❌ [BACKGROUND] Error processing historical emails for user {user_id}: {e}")
        return {"success": False, "status": "error", "message": str(e)}

# ============================================================================
# PROGRESSIVE BACKGROUND WORKERS
# ============================================================================

async def check_and_process_background_historical_sync():
    """
    NON-BLOCKING Background worker to process historical emails
    Starts background tasks without blocking WebSocket connections
    """
    logger.info("🔄 [BACKGROUND WORKER] Checking for users needing historical email sync")
    try:
        # Debug: First check all users
        all_users = await users_collection.find({}).to_list(length=10)
        logger.info(f"🔍 [BACKGROUND DEBUG] Found {len(all_users)} total users in database")
        
        for user in all_users:
            user_id = user.get("user_id", "unknown")
            dashboard_ready = user.get("dashboard_ready", False)
            background_sync_needed = user.get("background_sync_needed", False)
            historical_sync_completed = user.get("historical_sync_completed", False)
            
            logger.info(f"🔍 [BACKGROUND DEBUG] User {user_id}:")
            logger.info(f"    dashboard_ready: {dashboard_ready}")
            logger.info(f"    background_sync_needed: {background_sync_needed}")
            logger.info(f"    historical_sync_completed: {historical_sync_completed}")
        
        # Find users who completed recent sync but need historical processing
        query = {
            "dashboard_ready": True,
            "background_sync_needed": True,
            "historical_sync_completed": {"$ne": True}
        }
        logger.info(f"🔍 [BACKGROUND DEBUG] Query: {query}")
        
        users_to_process = users_collection.find(query)
        
        users_found = 0
        async for user in users_to_process:
            users_found += 1
            user_id = user.get("user_id")
            access_token = user.get("access_token")
            
            logger.info(f"🎯 [BACKGROUND] Found user needing historical sync: {user_id}")
            logger.info(f"    access_token present: {bool(access_token)}")
            
            if not user_id or not access_token:
                logger.warning(f"[BACKGROUND] Skipping user {user.get('_id')} due to missing credentials")
                continue

            logger.info(f"🚀 [BACKGROUND] Starting NON-BLOCKING historical sync for user {user_id}")
            
            # Start background processing in a separate task to avoid blocking WebSocket
            asyncio.create_task(process_historical_emails_non_blocking(user_id, access_token))
            
            # Process only 1 user per cycle to avoid system overload
            break

        if users_found == 0:
            logger.info("[BACKGROUND WORKER] No users found needing historical sync")
        else:
            logger.info(f"[BACKGROUND WORKER] Started background sync for {users_found} users")
            
    except Exception as e:
        logger.error(f"[BACKGROUND WORKER] Error during historical sync check: {str(e)}", exc_info=True)

async def process_historical_emails_non_blocking(user_id: str, access_token: str):
    """
    Process historical emails in background without blocking WebSocket connections
    Uses smaller batches and yields control to prevent blocking
    """
    logger.info(f"🔄 [NON-BLOCKING] Starting background historical processing for user: {user_id}")
    
    # Start keepalive task for active WebSocket connections
    keepalive_task = asyncio.create_task(send_keepalive_to_user_connections(user_id))
    
    try:
        # Build Gmail service
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        
        # Fetch historical emails in smaller batches (excluding recent 7 days already processed)
        from .gmail import fetch_gmail_emails_historical
        
        logger.info(f"📧 [NON-BLOCKING] Fetching historical emails for user {user_id}...")
        emails = await fetch_gmail_emails_historical(service, user_id, months=6, exclude_recent_days=7, max_results=2000)  # Reduced from 5000
        
        if emails:
            logger.info(f"📧 [NON-BLOCKING] Processing {len(emails)} historical emails in background...")
            
            # Process emails in smaller batches with async yields to prevent blocking
            result = await process_and_store_emails_non_blocking(user_id, emails, is_historical=True)
            
            if result.get("success", False):
                logger.info(f"✅ [NON-BLOCKING] Successfully processed {result['emails_stored']} historical emails")
                
                # PARALLEL PROCESSING: Historical Financial Analysis + Mem0 Upload
                logger.info(f"🚀 [NON-BLOCKING] Starting parallel historical financial processing...")
                
                try:
                    # Import parallel processing components
                    from .mem0_agent_agno import call_financial_processing_api
                    
                    # Process historical financial transactions
                    historical_financial_result = await call_financial_processing_api(user_id, "historical_6month")
                    
                    if historical_financial_result.get("success", False):
                        historical_transactions = historical_financial_result.get('transactions_found', 0)
                        total_amount = historical_financial_result.get('total_amount', 0)
                        logger.info(f"✅ [NON-BLOCKING] Historical financial processing complete:")
                        logger.info(f"   💳 Total transactions: {historical_transactions}")
                        logger.info(f"   💰 Total amount: {total_amount}")
                    else:
                        historical_transactions = 0
                        total_amount = 0
                        logger.warning(f"⚠️ [NON-BLOCKING] Historical financial processing failed: {historical_financial_result.get('error', 'Unknown error')}")
                        
                except Exception as financial_error:
                    logger.error(f"❌ [NON-BLOCKING] Historical financial processing error: {financial_error}", exc_info=True)
                    historical_transactions = 0
                    total_amount = 0
                
                # Update user flags for complete sync with financial data
                users_coll = await db_manager.get_collection(user_id, "users")
                await users_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "initial_gmailData_sync": True,  # ✅ Complete data sync done
                        "historical_sync_completed": True,
                        "historical_sync_date": datetime.now().isoformat(),
                        "historical_emails_processed": result['emails_stored'],
                        "historical_financial_transactions": historical_transactions,  # ✅ Historical financial data
                        "historical_total_amount": total_amount,  # ✅ Total financial amount
                        "complete_financial_ready": True,  # ✅ Complete financial analysis done
                        "background_sync_needed": False,  # ✅ Background processing complete
                        "total_emails_processed": result.get('total_count', 0)
                    }},
                    upsert=True
                )
                
                # Console message for user feedback
                print(f"\n{'='*80}")
                print(f"🎉 BACKGROUND SYNC COMPLETED for User: {user_id}")
                print(f"📊 Historical emails processed: {result['emails_stored']}")
                print(f"💰 Historical financial transactions: {historical_transactions}")
                print(f"💳 Total financial amount: {total_amount}")
                print(f"✅ Complete 6-month email + financial history now available for queries")
                print(f"{'='*80}\n")
                
            else:
                logger.error(f"❌ [NON-BLOCKING] Historical sync failed for user {user_id}: {result.get('message', 'Unknown error')}")
        else:
            # No historical emails found - mark as complete
            users_coll = await db_manager.get_collection(user_id, "users")
            await users_coll.update_one(
                {"user_id": user_id},
                {"$set": {
                    "initial_gmailData_sync": True,
                    "historical_sync_completed": True,
                    "background_sync_needed": False,
                    "historical_emails_processed": 0
                }},
                upsert=True
            )
            
            logger.info(f"✅ [NON-BLOCKING] No historical emails found for user {user_id}, marked as complete")
            
    except Exception as e:
        logger.error(f"❌ [NON-BLOCKING] Error processing historical emails for user {user_id}: {e}", exc_info=True)
    finally:
        # Cancel keepalive task
        if 'keepalive_task' in locals():
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass

async def process_and_store_emails_non_blocking(user_id: str, emails: List[Dict], is_historical: bool = False) -> Dict[str, Any]:
    """
    NON-BLOCKING email processing that yields control periodically to prevent WebSocket timeouts
    Processes emails in small batches with async yields between batches
    """
    processing_type = "historical-non-blocking" if is_historical else "non-blocking"
    logger.info(f"🔄 [{processing_type.upper()}] Processing {len(emails)} emails for user {user_id}")
    
    try:
        # Import here to avoid circular imports
        from .gmail import process_and_store_emails
        from .db import email_filter, insert_filtered_emails
        
        # Apply smart email filtering in smaller batches
        batch_size = 50  # Small batches to prevent blocking
        filtered_emails = []
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            # Filter batch
            if ENABLE_SMART_EMAIL_FILTERING:
                batch_filtered = await email_filter.smart_filter_emails(batch, user_id, processing_type)
            else:
                batch_filtered = batch
            
            filtered_emails.extend(batch_filtered)
            
            # Yield control every batch to prevent blocking WebSocket
            await asyncio.sleep(0.1)  # Small delay to yield control
            
            # Progress logging
            progress = ((i + batch_size) / len(emails)) * 100
            if i % (batch_size * 2) == 0:  # Log every 2 batches
                logger.info(f"🔄 [{processing_type.upper()}] Filtering progress: {progress:.1f}% ({i + len(batch)}/{len(emails)} emails)")
        
        logger.info(f"📊 [{processing_type.upper()}] Smart filtering: {len(emails)} → {len(filtered_emails)} emails")
        
        if not filtered_emails:
            logger.info(f"📭 [{processing_type.upper()}] No emails to process after filtering")
            return {
                "success": True,
                "status": "success",
                "emails_stored": 0,
                "promotional_filtered": len(emails),
                "processing_type": processing_type
            }
        
        # Store emails in database in batches
        storage_result = await insert_filtered_emails_non_blocking(user_id, filtered_emails, processing_type)
        
        if storage_result.get("success", False):
            stored_count = storage_result.get("inserted", 0)
            logger.info(f"✅ [{processing_type.upper()}] Successfully stored {stored_count} emails")
            
            # Upload to Mem0 in batches to prevent blocking
            if stored_count > 0:
                await upload_emails_to_mem0_non_blocking(user_id, filtered_emails[:stored_count], processing_type)
            
            return {
                "success": True,
                "status": "success",
                "emails_stored": stored_count,
                "promotional_filtered": len(emails) - len(filtered_emails),
                "financial_preserved": sum(1 for email in filtered_emails if email.get("financial", False)),
                "processing_type": processing_type,
                "total_count": len(emails)
            }
        else:
            logger.error(f"❌ [{processing_type.upper()}] Failed to store emails: {storage_result}")
            return {
                "success": False,
                "status": "error",
                "message": f"Failed to store emails: {storage_result.get('error', 'Unknown error')}",
                "processing_type": processing_type
            }
    
    except Exception as e:
        logger.error(f"❌ [{processing_type.upper()}] Error processing emails: {e}")
        return {
            "success": False,
            "status": "error", 
            "message": str(e),
            "processing_type": processing_type
        }

async def insert_filtered_emails_non_blocking(user_id: str, emails: List[Dict], processing_type: str) -> Dict[str, Any]:
    """
    Insert emails into database in small batches to prevent blocking
    """
    try:
        from .db import insert_filtered_emails
        
        # Process in smaller batches
        batch_size = 25  # Very small batches for non-blocking
        total_inserted = 0
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            # Insert batch
            batch_result = await insert_filtered_emails(user_id, batch, processing_type)
            
            if batch_result.get("success", False):
                total_inserted += batch_result.get("inserted", 0)
            
            # Yield control between batches
            await asyncio.sleep(0.05)
            
            # Progress logging
            if i % (batch_size * 4) == 0:  # Log every 4 batches
                progress = ((i + batch_size) / len(emails)) * 100
                logger.info(f"🔄 [NON-BLOCKING] Database insert progress: {progress:.1f}% ({total_inserted} emails inserted)")
        
        return {
            "success": True,
            "inserted": total_inserted,
            "processing_type": processing_type
        }
        
    except Exception as e:
        logger.error(f"❌ [NON-BLOCKING] Error inserting emails: {e}")
        return {
            "success": False,
            "error": str(e),
            "processing_type": processing_type
        }

async def upload_emails_to_mem0_non_blocking(user_id: str, emails: List[Dict], processing_type: str):
    """
    Upload emails to Mem0 in small batches to prevent blocking WebSocket connections
    Enhanced with 503 Service Unavailable handling
    """
    try:
        from .mem0_agent_agno import upload_emails_to_mem0, EmailMessage
        
        # Convert to EmailMessage objects in batches
        batch_size = 10  # Very small batches for Mem0 upload
        successful_batches = 0
        failed_batches = 0
        service_unavailable_count = 0
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            email_messages = []
            
            for email in batch:
                try:
                    # Handle date conversion properly
                    date_value = email.get("date", "")
                    if hasattr(date_value, 'isoformat'):  # It's a datetime object
                        date_str = date_value.isoformat()
                    elif isinstance(date_value, str):
                        date_str = date_value
                    else:
                        date_str = str(date_value) if date_value else ""
                    
                    email_msg = EmailMessage(
                        id=email.get("id", ""),
                        subject=email.get("subject", ""),
                        sender=email.get("sender", ""),
                        snippet=email.get("snippet", ""),
                        body=email.get("body", ""),
                        date=date_str
                    )
                    email_messages.append(email_msg)
                except Exception as e:
                    logger.error(f"Error converting email to EmailMessage: {e}")
                    continue
            
            if email_messages:
                try:
                    # Upload batch to Mem0 with error handling
                    mem0_result = await upload_emails_to_mem0(user_id, email_messages)
                    
                    # Check if upload was successful
                    if "successful uploads:" in mem0_result.lower():
                        successful_batches += 1
                    else:
                        failed_batches += 1
                        
                        # Check for service unavailability
                        if "service unavailable" in mem0_result.lower() or "503" in mem0_result:
                            service_unavailable_count += 1
                    
                    # Progress logging
                    progress = ((i + batch_size) / len(emails)) * 100
                    if i % (batch_size * 2) == 0:  # Log every 2 batches
                        logger.info(f"🧠 [NON-BLOCKING] Mem0 upload progress: {progress:.1f}% ({i + len(email_messages)}/{len(emails)} emails)")
                
                except Exception as batch_error:
                    failed_batches += 1
                    error_str = str(batch_error).lower()
                    
                    if "503" in error_str or "service temporarily unavailable" in error_str:
                        service_unavailable_count += 1
                        logger.warning(f"🔄 [NON-BLOCKING] Mem0 service unavailable for batch {i//batch_size + 1}")
                    else:
                        logger.error(f"❌ [NON-BLOCKING] Error uploading batch {i//batch_size + 1}: {batch_error}")
            
            # Yield control between batches to prevent blocking
            await asyncio.sleep(0.2)  # Slightly longer delay for Mem0 API calls
        
        # Final summary
        total_batches = (len(emails) + batch_size - 1) // batch_size
        success_rate = (successful_batches / total_batches) * 100 if total_batches > 0 else 0
        
        if service_unavailable_count > 0:
            logger.warning(f"⚠️ [NON-BLOCKING] Mem0 upload completed with {service_unavailable_count} service unavailable incidents")
            logger.info(f"📊 [NON-BLOCKING] Mem0 upload summary: {successful_batches}/{total_batches} batches successful ({success_rate:.1f}%)")
        else:
            logger.info(f"✅ [NON-BLOCKING] Completed Mem0 upload for {len(emails)} emails - {successful_batches}/{total_batches} batches successful")
        
        # Update user's Mem0 sync status based on results
        if success_rate >= 80:
            await update_user_flags(user_id, {"mem0_sync_status": "completed"})
        elif success_rate >= 50:
            await update_user_flags(user_id, {"mem0_sync_status": "partial"})
        else:
            await update_user_flags(user_id, {"mem0_sync_status": "pending"})
        
    except Exception as e:
        logger.error(f"❌ [NON-BLOCKING] Error uploading emails to Mem0: {e}")
        
        # Check if it's a service unavailability issue
        if "503" in str(e) or "service temporarily unavailable" in str(e).lower():
            logger.warning(f"🔄 [NON-BLOCKING] Mem0 service is temporarily unavailable - emails stored in MongoDB for later retry")
            await update_user_flags(user_id, {"mem0_sync_status": "pending"})
        else:
            logger.error(f"❌ [NON-BLOCKING] Unexpected Mem0 error: {e}")
            await update_user_flags(user_id, {"mem0_sync_status": "error"})

async def update_user_flags(user_id: str, update_data: Dict[str, Any]):
    """
    Update user flags in the database
    """
    try:
        users_coll = await db_manager.get_collection(user_id, "users")
        result = await users_coll.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count > 0:
            logger.debug(f"✅ Updated user flags for {user_id}: {update_data}")
        else:
            logger.warning(f"⚠️ No user found to update flags for {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Error updating user flags for {user_id}: {e}")

async def send_keepalive_to_user_connections(user_id: str):
    """
    Send periodic keepalive messages to active WebSocket connections for a user
    to prevent timeouts during background processing
    
    FIXED: Prevents "dictionary changed size during iteration" error
    """
    try:
        from .websocket import manager
        
        # Send keepalive every 8 seconds (before 10-second timeout)
        while True:
            await asyncio.sleep(8)
            
            # FIXED: Create a copy of the connections to avoid iteration issues
            try:
                # Get user-specific connections if available
                user_client_ids = []
                if user_id in manager.user_connections:
                    user_client_ids = manager.user_connections[user_id].copy()
                
                # If no user-specific connections, use a copy of all active connections
                if not user_client_ids:
                    user_client_ids = list(manager.active_connections.keys())
                
                # Send keepalive to each connection
                keepalive_sent = 0
                keepalive_failed = 0
                
                for client_id in user_client_ids:
                    # Double-check connection still exists before sending
                    if client_id in manager.active_connections:
                        try:
                            await manager.send_keepalive(client_id)
                            keepalive_sent += 1
                            logger.debug(f"📡 [KEEPALIVE] Sent keepalive to connection {client_id}")
                        except Exception as e:
                            keepalive_failed += 1
                            logger.debug(f"⚠️ [KEEPALIVE] Failed to send keepalive to {client_id}: {e}")
                            # Remove failed connection from manager
                            manager.disconnect(client_id, user_id)
                
                # Summary logging (only if there were connections)
                if keepalive_sent > 0 or keepalive_failed > 0:
                    logger.debug(f"📊 [KEEPALIVE] User {user_id}: {keepalive_sent} sent, {keepalive_failed} failed")
                    
            except Exception as iteration_error:
                logger.warning(f"⚠️ [KEEPALIVE] Iteration error for user {user_id}: {iteration_error}")
                # Continue the loop even if one iteration fails
                continue
                    
    except asyncio.CancelledError:
        logger.info(f"🔄 [KEEPALIVE] Keepalive task cancelled for user {user_id}")
        raise
    except Exception as e:
        logger.error(f"❌ [KEEPALIVE] Error in keepalive task for user {user_id}: {e}")

# ============================================================================
# CREDIT REPORT API ENDPOINTS - NEW FEATURE
# ============================================================================

@app.post("/credit-report/fetch")
async def fetch_credit_report(request: CreditReportRequest):
    """Fetch credit report from specified bureau"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(request.jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        request.jwt_token = user_id  # Use user_id consistently
        
        result = await credit_report_service.fetch_credit_report(request)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Credit report fetched successfully",
                "data": result["data"],
                "source": result.get("source", "api")
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        logger.error(f"Error in fetch_credit_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/credit-report/insights/{report_id}")
async def generate_credit_insights(report_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Generate AI-powered insights from credit report"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        insights = await credit_report_service.generate_credit_insights(user_id, report_id)
        
        return {
            "success": True,
            "insights": insights.dict()
        }
        
    except Exception as e:
        logger.error(f"Error generating credit insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credit-report/history")
async def get_credit_report_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's credit report history"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        reports = await credit_report_service.get_user_credit_reports(user_id)
        
        return {
            "success": True,
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"Error getting credit report history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credit-report/insights/{report_id}")
async def get_credit_insights(report_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get credit insights for a specific report"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        insights = await credit_report_service.get_credit_insights(user_id, report_id)
        
        if insights:
            return {
                "success": True,
                "insights": insights
            }
        else:
            return {
                "success": False,
                "error": "Insights not found"
            }
        
    except Exception as e:
        logger.error(f"Error getting credit insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BANK STATEMENT PROCESSING API ENDPOINTS - NEW FEATURE
# ============================================================================

from fastapi import UploadFile, File, Form

@app.post("/statement/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    jwt_token: str = Form(...),
    bank_name: str = Form(""),
    account_number: str = Form(""),
    statement_period_from: str = Form(""),
    statement_period_to: str = Form("")
):
    """Upload and process bank statement"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        # Read file content
        file_content = await file.read()
        file_type = file.filename.split('.')[-1].lower() if file.filename else "pdf"
        
        # Create statement upload request
        request = StatementUploadRequest(
            jwt_token=user_id,
            statement_type=file_type,
            bank_name=bank_name,
            account_number=account_number,
            statement_period={
                "from": statement_period_from,
                "to": statement_period_to
            }
        )
        
        result = await statement_processor.process_statement(file_content, file_type, request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading bank statement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statement/history")
async def get_statement_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's bank statement history"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        statements = await statement_processor.get_user_statements(user_id)
        
        return {
            "success": True,
            "statements": statements
        }
        
    except Exception as e:
        logger.error(f"Error getting statement history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statement/insights/{statement_id}")
async def get_statement_insights(statement_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get insights for a specific bank statement"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        insights = await statement_processor.get_statement_insights(user_id, statement_id)
        
        if insights:
            return {
                "success": True,
                "insights": insights
            }
        else:
            return {
                "success": False,
                "error": "Insights not found"
            }
        
    except Exception as e:
        logger.error(f"Error getting statement insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CREDIT CARD RECOMMENDATION API ENDPOINTS - NEW FEATURE
# ============================================================================

@app.post("/credit-cards/recommendations")
async def get_credit_card_recommendations(criteria: CreditCardCriteria):
    """Get personalized credit card recommendations"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(criteria.jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        criteria.jwt_token = user_id  # Use user_id consistently
        
        recommendations = await credit_card_service.get_personalized_recommendations(criteria)
        
        return {
            "success": True,
            "recommendations": recommendations.dict()
        }
        
    except Exception as e:
        logger.error(f"Error getting credit card recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credit-cards/recommendations/history")
async def get_recommendation_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's credit card recommendation history"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        recommendations = await credit_card_service.get_user_recommendations(user_id)
        
        return {
            "success": True,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/credit-cards/apply")
async def initiate_card_application(
    card_id: str = Form(...),
    jwt_token: str = Form(...),
    pre_filled_data: str = Form("{}")
):
    """Initiate credit card application process"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        # Parse pre-filled data
        try:
            pre_filled_dict = json.loads(pre_filled_data)
        except json.JSONDecodeError:
            pre_filled_dict = {}
        
        application = await credit_card_service.initiate_card_application(user_id, card_id, pre_filled_dict)
        
        return {
            "success": True,
            "application": application.dict()
        }
        
    except Exception as e:
        logger.error(f"Error initiating card application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credit-cards/applications")
async def get_application_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's credit card application history"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        applications = await credit_card_service.get_user_applications(user_id)
        
        return {
            "success": True,
            "applications": applications
        }
        
    except Exception as e:
        logger.error(f"Error getting application history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credit-health/complete-report")
async def get_complete_credit_health_report(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Generate comprehensive credit health report"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        health_report = await credit_card_service.generate_complete_credit_health_report(user_id)
        
        return {
            "success": True,
            "credit_health_report": health_report.dict()
        }
        
    except Exception as e:
        logger.error(f"Error generating credit health report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BROWSER AUTOMATION API ENDPOINTS - NEW FEATURE
# ============================================================================

@app.post("/automation/scrape-cards")
async def scrape_credit_cards(request: BrowserAutomationRequest):
    """Scrape credit cards from comparison websites"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(request.jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        request.jwt_token = user_id  # Use user_id consistently
        
        async with browser_automation_service as automation:
            result = await automation.execute_automation_request(request)
        
        return {
            "success": True,
            "result": result.dict()
        }
        
    except Exception as e:
        logger.error(f"Error scraping credit cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/automation/fill-application")
async def fill_application_form(request: BrowserAutomationRequest):
    """Automatically fill credit card application form"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(request.jwt_token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        request.jwt_token = user_id  # Use user_id consistently
        
        async with browser_automation_service as automation:
            result = await automation.execute_automation_request(request)
        
        return {
            "success": True,
            "result": result.dict()
        }
        
    except Exception as e:
        logger.error(f"Error filling application form: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automation/scraped-cards/latest")
async def get_latest_scraped_cards(limit: int = 50):
    """Get latest scraped credit cards from all sources"""
    try:
        async with browser_automation_service as automation:
            cards = await automation.get_latest_scraped_cards(limit)
        
        return {
            "success": True,
            "cards": cards,
            "total": len(cards)
        }
        
    except Exception as e:
        logger.error(f"Error getting latest scraped cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automation/history")
async def get_automation_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's browser automation history"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        async with browser_automation_service as automation:
            history = await automation.get_scraping_history(user_id)
        
        return {
            "success": True,
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting automation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# COMPREHENSIVE FINANCIAL DASHBOARD API - NEW FEATURE
# ============================================================================

@app.get("/financial/dashboard/complete")
async def get_complete_financial_dashboard(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get comprehensive financial dashboard with all features"""
    try:
        # Decode JWT to get user_id
        user_data = decode_jwt_token(credentials.credentials)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        
        user_id = user_data.get("user_id", user_data.get("sub", ""))
        
        # Gather data from all services in parallel
        credit_reports_task = credit_report_service.get_user_credit_reports(user_id)
        statements_task = statement_processor.get_user_statements(user_id)
        recommendations_task = credit_card_service.get_user_recommendations(user_id)
        applications_task = credit_card_service.get_user_applications(user_id)
        
        # Wait for all tasks to complete
        credit_reports, statements, recommendations, applications = await asyncio.gather(
            credit_reports_task, statements_task, recommendations_task, applications_task,
            return_exceptions=True
        )
        
        # Handle exceptions gracefully
        dashboard_data = {
            "user_id": user_id,
            "credit_reports": credit_reports if not isinstance(credit_reports, Exception) else [],
            "bank_statements": statements if not isinstance(statements, Exception) else [],
            "card_recommendations": recommendations if not isinstance(recommendations, Exception) else [],
            "card_applications": applications if not isinstance(applications, Exception) else [],
            "generated_at": datetime.now().isoformat()
        }
        
        # Add summary statistics
        dashboard_data["summary"] = {
            "total_credit_reports": len(dashboard_data["credit_reports"]),
            "total_statements": len(dashboard_data["bank_statements"]),
            "total_recommendations": len(dashboard_data["card_recommendations"]),
            "total_applications": len(dashboard_data["card_applications"]),
            "latest_credit_score": dashboard_data["credit_reports"][0].get("credit_score_info", {}).get("score", 0) if dashboard_data["credit_reports"] else 0
        }
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Error getting complete financial dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FINANCIAL FEATURES HEALTH CHECK - NEW FEATURE
# ============================================================================

@app.get("/financial/health")
async def financial_features_health_check():
    """Health check for all financial features"""
    try:
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # Check credit report service
        try:
            # Simple check - count documents
            credit_reports_count = await credit_report_service.credit_reports_collection.count_documents({})
            health_data["services"]["credit_reports"] = {
                "status": "healthy",
                "total_reports": credit_reports_count
            }
        except Exception as e:
            health_data["services"]["credit_reports"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check statement processor
        try:
            statements_count = await statement_processor.statements_collection.count_documents({})
            health_data["services"]["statement_processor"] = {
                "status": "healthy",
                "total_statements": statements_count
            }
        except Exception as e:
            health_data["services"]["statement_processor"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check credit card service
        try:
            cards_count = await credit_card_service.cards_collection.count_documents({})
            health_data["services"]["credit_card_service"] = {
                "status": "healthy",
                "total_cards": cards_count
            }
        except Exception as e:
            health_data["services"]["credit_card_service"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall health status
        error_count = sum(1 for service in health_data["services"].values() if service["status"] == "error")
        if error_count == 0:
            health_data["overall_status"] = "healthy"
        elif error_count < len(health_data["services"]) / 2:
            health_data["overall_status"] = "degraded"
        else:
            health_data["overall_status"] = "unhealthy"
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error in financial features health check: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(e)
        }
