import os
from dotenv import load_dotenv
from typing import Optional
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
from app.auth import verify_google_token, create_jwt_token, decode_jwt_token
from app.oauth import generate_auth_url, exchange_code_for_tokens
from app.db import users_collection, emails_collection
from app.gmail import build_gmail_service, fetch_emails
from app.mem0_agent_agno import upload_emails_to_mem0, query_mem0, process_gmail_data_for_user, search_emails_in_mem0
from app.models import GoogleToken, GmailFetchPayload
from app.websocket import router as websocket_router
from app.websocket import manager
import logging
import asyncio
from bson import ObjectId
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.financial_agent import (
    process_financial_transactions_for_user,
    get_financial_summary,
    get_financial_transactions
)

# Import scalability components
from app.config import CONFIG, EMAIL_PROCESSING_TIMEOUT, CONCURRENT_USERS_LIMIT
from app.middleware import (
    rate_limit_middleware, email_processing_context, 
    get_health_status, resource_manager
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

# Add scalability middleware FIRST (before CORS)
app.middleware("http")(rate_limit_middleware)

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

# Health check endpoint with scalability metrics
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with scalability metrics."""
    health_data = get_health_status()
    return {
        "status": "Ok",
        "_version": "1.2.0",
        "scalability": health_data,
        "config": {
            "concurrent_users_limit": CONCURRENT_USERS_LIMIT,
            "email_processing_timeout": EMAIL_PROCESSING_TIMEOUT
        },
        "workers": {
            "email_sync_worker": {
                "interval": "30 seconds",
                "status": "active"
            },
            "financial_analysis_worker": {
                "interval": "45 seconds", 
                "status": "active"
            }
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Get detailed system metrics for monitoring."""
    return get_health_status()

@app.get("/metrics/users")
async def get_user_metrics():
    """Get active user metrics."""
    stats = resource_manager.get_stats()
    return {
        "active_users": stats.get("active_users", 0),
        "concurrent_limit": CONCURRENT_USERS_LIMIT,
        "active_user_list": stats.get("active_user_list", []),
        "utilization_percent": (stats.get("active_users", 0) / CONCURRENT_USERS_LIMIT) * 100
    }


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
async def _trigger_and_process_user_emails(user_id: str, access_token: str, max_results: int = 2500):
    logger.info(f"Starting email processing for user_id: {user_id}")
    try:
        # Mark that email fetch process has been initiated for this user
        logger.info(f"Marking fetched_email as true for user_id: {user_id}")
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"fetched_email": True}}
        )
        logger.info(f"fetched_email marked as true for user_id: {user_id}")

        # Get user's refresh token from database
        user_in_db = await users_collection.find_one({"user_id": user_id})
        if not user_in_db:
            raise Exception(f"User {user_id} not found in database")
        
        refresh_token = user_in_db.get("refresh_token")
        if not refresh_token:
            raise Exception(f"No refresh token found for user {user_id}. Please re-authenticate.")
        
        # Build Gmail service and fetch emails
        logger.info(f"Building Gmail service for user_id: {user_id}")
        service = build_gmail_service(access_token, refresh_token)
        
        logger.info(f"Fetching emails from Gmail for user_id: {user_id} (max: {max_results})...")
        emails = await fetch_emails(service, max_results=max_results)
        logger.info(f"Fetched {len(emails)} emails from Gmail for user_id: {user_id}")
        
        if emails:
            # Store emails in MongoDB
            logger.info(f"Storing {len(emails)} emails in MongoDB for user_id: {user_id}...")
            for email_item in emails:
                email_item['user_id'] = user_id
            
            # Remove existing emails for this user to avoid duplicates before new insertion
            await emails_collection.delete_many({"user_id": user_id})
            await emails_collection.insert_many(emails)
            logger.info(f"Emails stored in MongoDB for user_id: {user_id}")
            
            # Upload to Mem0 with enhanced user processing
            logger.info(f"Processing Gmail data with enhanced integration for user_id: {user_id}...")
            mem0_result = await process_gmail_data_for_user(user_id, emails)
            logger.info(f"Gmail data processed with Mem0 integration for user_id: {user_id}")

            # The enhanced function already updates user status, so we don't need to do it again
            return {"status": "success", "message": f"Successfully fetched and processed {len(emails)} emails for user {user_id}", "count": len(emails)}
        else:
            # If no emails were fetched, still mark initial_gmailData_sync as true because the fetch process completed.
            # This prevents re-fetching if the user genuinely has no emails or if max_results was 0.
            logger.info(f"No emails found for user_id: {user_id}. Marking initial_gmailData_sync as true.")
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"initial_gmailData_sync": True}} # Mark as synced even if no emails
            )
            logger.info(f"initial_gmailData_sync updated (no emails found) for user_id: {user_id}")
            return {"status": "success", "message": f"Email fetch process completed. No emails found for user {user_id}", "count": 0}

    except Exception as e:
        logger.error(f"Error during email processing for user_id {user_id}: {str(e)}", exc_info=True)
        # Optionally, you might want to reset fetched_email to false or add specific error handling/retry logic here
        return {"status": "error", "message": f"Failed to process emails for user {user_id}: {str(e)}"}

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
            except Exception as user_error:
                logger.error(f"Background worker: Failed to process emails for user {user_id}: {str(user_error)}", exc_info=True)
                # Reset fetched_email to false so it can be retried later
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"fetched_email": False}}
                )

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
    # Schedule the email fetching job to run every 30 seconds
    scheduler.add_job(check_and_fetch_new_user_emails, "interval", seconds=30, id="fetch_new_emails_job")
    
    # Schedule the financial analysis job to run every 45 seconds (offset to avoid conflicts)
    scheduler.add_job(check_and_process_financial_analysis, "interval", seconds=45, id="financial_analysis_job")
    
    scheduler.start()
    logger.info("APScheduler started.")
    logger.info("Job 'fetch_new_emails_job' scheduled every 30 seconds.")
    logger.info("Job 'financial_analysis_job' scheduled every 45 seconds.")

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
