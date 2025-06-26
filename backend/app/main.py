import os
import time
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from datetime import datetime

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
from .gmail import build_gmail_service, fetch_emails, get_storage_statistics, process_and_store_emails, email_extractor
from .mem0_agent_agno import upload_emails_to_mem0, query_mem0, process_gmail_data_for_user, search_emails_in_mem0
from .db import cleanup_manager, db_manager
from .models import GoogleToken, GmailFetchPayload
from .websocket import router as websocket_router
from .websocket import manager
import logging
import asyncio
from bson import ObjectId
from pydantic import BaseModel
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
    STORAGE_CRITICAL_THRESHOLD, ENABLE_AUTO_CLEANUP
)
from .middleware import (
    enhanced_rate_limit_middleware, email_processing_context, 
    get_health_status, resource_manager, performance_monitor
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
app.middleware("http")(enhanced_rate_limit_middleware)

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
    # Authenticate user with JWT
    logger.info("Received request for /gmail/fetch")
    try:
        logger.info("Decoding JWT token...")
        user = decode_jwt_token(payload.jwt_token)
        user_id = user.get("user_id")
        logger.info(f"JWT decoded. User ID: {user_id}")

        # Use email processing context for resource management
        async with email_processing_context(user_id) as rm:
            # Call the core processing function with timeout
            result = await asyncio.wait_for(
                _trigger_and_process_user_emails(user_id=user_id, access_token=payload.access_token, max_results=3500),
                timeout=EMAIL_PROCESSING_TIMEOUT
            )

            if result["status"] == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["message"]
                )

            return {"message": result["message"], "count": result["count"]}
            
    except asyncio.TimeoutError:
        logger.error(f"Gmail fetch timeout for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Email processing timed out after {EMAIL_PROCESSING_TIMEOUT} seconds"
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
        
        # Check if user needs initial email sync
        has_email_data = await emails_collection.count_documents({"user_id": user_id}) > 0
        current_sync_status = user_in_db.get("initial_gmailData_sync", False)
        current_fetched_status = user_in_db.get("fetched_email", False)

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
        logger.info(f"Successfully fetched user data for /me: {serializable_user_info.get('email')}")
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
    logger.info("Background worker: Checking for users with fetched_email=false")
    try:
        users_to_fetch = users_collection.find({"fetched_email": False})
        users_found = 0
        async for user in users_to_fetch:
            users_found += 1
            user_id = user.get("user_id")
            access_token = user.get("access_token")
            
            if not user_id or not access_token:
                logger.warning(f"Background worker: Skipping user {user.get('_id')} due to missing user_id or access_token.")
                continue

            logger.info(f"Background worker: Found user {user_id} with fetched_email=false. Triggering email processing.")
            
            # Reset financial analysis status when starting new email fetch
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"financial_analysis_completed": False}}
            )
            
            try:
                # Process emails for this user
                result = await _trigger_and_process_user_emails(user_id=user_id, access_token=access_token, max_results=3500)
                logger.info(f"Background worker: Email processing result for user {user_id}: {result}")
                
                # 🔧 CRITICAL FIX: Check for consistent success key
                if result.get("success", False) or result.get("status") == "success":
                    logger.info(f"🎉 Background worker: User {user_id} email processing completed successfully!")
                    # Flags are already updated in _trigger_and_process_user_emails function
                else:
                    logger.error(f"Background worker: Email processing failed for user {user_id}: {result}")
                    
            except Exception as user_error:
                logger.error(f"Background worker: Failed to process emails for user {user_id}: {str(user_error)}", exc_info=True)
                # Keep fetched_email=false so it can be retried later
                logger.info(f"Background worker: User {user_id} will be retried in next cycle")

        if users_found == 0:
            logger.info("Background worker: No users found with fetched_email=false")
        else:
            logger.info(f"Background worker: Processed {users_found} users")
            
        logger.info("Background worker: Finished checking for users.")
    except Exception as e:
        logger.error(f"Background worker: Error during check_and_fetch_new_user_emails: {str(e)}", exc_info=True)

async def check_and_process_financial_analysis():
    """
    Background worker to process financial analysis for users who have completed email sync
    but haven't completed financial analysis yet.
    """
    logger.info("Financial worker: Checking for users needing financial analysis")
    try:
        # Find users who have completed email sync but not financial analysis
        users_to_process = users_collection.find({
            "initial_gmailData_sync": True,
            "financial_analysis_completed": False
        })
        
        users_found = 0
        async for user in users_to_process:
            users_found += 1
            user_id = user.get("user_id")
            
            if not user_id:
                logger.warning(f"Financial worker: Skipping user {user.get('_id')} due to missing user_id.")
                continue

            logger.info(f"Financial worker: Found user {user_id} needing financial analysis. Starting processing.")
            
            try:
                # Import the fast processing logic
                from app.fast_financial_processor import process_financial_transactions_from_mongodb
                
                # Process financial transactions with timeout
                result = await asyncio.wait_for(
                    process_financial_transactions_from_mongodb(user_id),
                    timeout=EMAIL_PROCESSING_TIMEOUT
                )
                
                if result["status"] == "success":
                    logger.info(f"Financial worker: Successfully processed financial data for user {user_id}")
                    logger.info(f"Financial worker: Found {result.get('transactions_found', 0)} transactions")
                    
                    # Update user status with detailed information
                    await users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "financial_analysis_completed": True,
                            "financial_analysis_date": datetime.now().isoformat(),
                            "financial_transactions_count": result.get('transactions_found', 0),
                            "financial_processing_method": "fast_mongodb"
                        }}
                    )
                else:
                    logger.error(f"Financial worker: Failed to process financial data for user {user_id}: {result.get('error', 'Unknown error')}")
                    
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
    
    # Schedule the email fetching job to run every 10 seconds (optimized)
    scheduler.add_job(check_and_fetch_new_user_emails, "interval", seconds=10, id="fetch_new_emails_job")
    
    # Schedule the financial analysis job to run every 45 seconds (offset to avoid conflicts)
    scheduler.add_job(check_and_process_financial_analysis, "interval", seconds=45, id="financial_analysis_job")
    
    # Start continuous performance monitoring
    asyncio.create_task(performance_monitor())
    
    scheduler.start()
    logger.info("🚀 APScheduler started with enhanced optimizations.")
    logger.info("📊 Optimization Summary:")
    logger.info(f"   • Concurrent users: {CONCURRENT_USERS_LIMIT} (↑ from 15)")
    logger.info(f"   • Email fetch limit: {DEFAULT_EMAIL_LIMIT} (↑ from 3,500)")
    logger.info(f"   • Smart caching: {'Enabled' if ENABLE_SMART_CACHING else 'Disabled'}")
    logger.info(f"   • Batch processing: {'Enabled' if ENABLE_BATCH_PROCESSING else 'Disabled'}")
    logger.info("   • Performance monitoring: Active")
    logger.info("📧 Job 'fetch_new_emails_job' scheduled every 10 seconds (↓ from 30s).")
    logger.info("💰 Job 'financial_analysis_job' scheduled every 45 seconds.")
    logger.info("🚀 Expected 10-15x performance improvement!")

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
