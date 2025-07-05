import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from starlette.websockets import WebSocketState
from .mem0_agent_agno import query_mem0
from .auth import decode_jwt_token_websocket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections."""
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.user_connections: dict[str, list[str]] = {}  # user_id -> [client_ids]

    async def connect(self, websocket: WebSocket, client_id: str, user_id: str = None):
        """Accepts and stores a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Track user connections for targeted updates
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(client_id)
        
        logger.info(f"WebSocket connected: {client_id} (user: {user_id})")
    
    def update_user_connection(self, client_id: str, user_id: str):
        """Update existing connection with user_id without re-accepting."""
        # Track user connections for targeted updates
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            if client_id not in self.user_connections[user_id]:
                self.user_connections[user_id].append(client_id)
        
        logger.debug(f"Updated connection tracking: {client_id} -> user {user_id}")

    def disconnect(self, client_id: str, user_id: str = None):
        """Removes a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Remove from user connections tracking
        if user_id and user_id in self.user_connections:
            if client_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(client_id)
            if not self.user_connections[user_id]:  # Remove empty user entry
                del self.user_connections[user_id]
                
        logger.info(f"WebSocket disconnected: {client_id}")

    async def send_json(self, client_id: str, message: dict):
        """Sends a JSON message to a specific client with enhanced error handling."""
        if client_id not in self.active_connections:
            logger.debug(f"⚠️ Client {client_id} not in active connections")
            return False
            
        try:
            websocket = self.active_connections[client_id]
            
            # Check WebSocket state before sending
            if hasattr(websocket, 'client_state') and websocket.client_state != WebSocketState.CONNECTED:
                logger.debug(f"⚠️ WebSocket {client_id} not connected (state: {websocket.client_state})")
                self._cleanup_failed_connection(client_id)
                return False
            
            await websocket.send_json(message)
            return True
        except ConnectionClosed:
            logger.debug(f"🔌 Connection {client_id} closed during send")
            self._cleanup_failed_connection(client_id)
            return False
        except Exception as e:
            # Only log error if it's not an empty string (which indicates normal disconnection)
            if str(e).strip():
                logger.error(f"❌ Error sending message to {client_id}: {e}")
            else:
                logger.debug(f"🔌 Connection {client_id} disconnected during send")
            
            # Clean up the failed connection
            self._cleanup_failed_connection(client_id)
            return False
    
    def _cleanup_failed_connection(self, client_id: str):
        """Clean up a failed connection from all tracking structures"""
        try:
            # Remove from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            # Remove from user connections tracking
            for user_id, client_ids in list(self.user_connections.items()):
                if client_id in client_ids:
                    client_ids.remove(client_id)
                    if not client_ids:  # Remove empty user entry
                        del self.user_connections[user_id]
                    break
                    
            logger.debug(f"🧹 Cleaned up failed connection: {client_id}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up connection {client_id}: {e}")

    async def send_progress_update(self, client_id: str, step: str, message: str, progress: int = 0, data: dict = None):
        """Send real-time progress updates to prevent connection timeout"""
        progress_message = {
            "type": "progress",
            "step": step,
            "message": message,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data or {}
        }
        await self.send_json(client_id, progress_message)

    async def send_keepalive(self, client_id: str):
        """Send keepalive message to prevent WebSocket timeout"""
        keepalive_message = {
            "type": "keepalive",
            "timestamp": asyncio.get_event_loop().time(),
            "message": "Connection active"
        }
        await self.send_json(client_id, keepalive_message)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a specific user with improved error handling"""
        if user_id not in self.user_connections:
            logger.debug(f"⚠️ No connections found for user {user_id}")
            return 0
            
        # Create a copy to avoid modification during iteration
        client_ids = self.user_connections[user_id].copy()
        successful_sends = 0
        failed_sends = 0
        
        for client_id in client_ids:
            success = await self.send_json(client_id, message)
            if success:
                successful_sends += 1
            else:
                failed_sends += 1
        
        if failed_sends > 0:
            logger.warning(f"⚠️ Broadcast to user {user_id}: {successful_sends} successful, {failed_sends} failed")
        else:
            logger.debug(f"✅ Broadcast to user {user_id}: {successful_sends} messages sent")
            
        return successful_sends

manager = ConnectionManager()

# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@router.websocket("/ws/historical-sync")
async def websocket_historical_sync(websocket: WebSocket):
    """
    🚀 FIXED: WebSocket endpoint for 6-month historical email fetch with real-time progress
    This fixes the disconnection issue by maintaining active WebSocket communication during long operations
    """
    client_id = f"historical_{uuid.uuid4()}"
    user_id = None
    
    try:
        # 1. Initial Connection
        await websocket.accept()
        manager.active_connections[client_id] = websocket
        
        # 2. Authentication Phase
        auth_data = await websocket.receive_json()
        token = auth_data.get("jwt_token")
        
        payload = decode_jwt_token_websocket(token)
        if not payload or "user_id" not in payload:
            logger.warning(f"{client_id} - Historical sync auth failed: Invalid token")
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close(code=1008)
            return

        user_id = payload["user_id"]
        # Update connection tracking with user_id (don't re-accept!)
        manager.update_user_connection(client_id, user_id)
        logger.info(f"🔄 Historical sync authenticated for user: {user_id}")

        # 3. Send initial connection confirmation
        await manager.send_progress_update(
            client_id, 
            "connected", 
            "Connected to 6-month historical email sync", 
            0
        )

        # 4. Start 6-month historical sync with REAL-TIME progress updates
        await historical_sync_with_realtime_progress(client_id, user_id, auth_data.get("access_token"))

    except WebSocketDisconnect:
        logger.info(f"Historical sync WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Historical sync error for {client_id}: {e}", exc_info=True)
        if client_id in manager.active_connections:
            await manager.send_json(client_id, {
                "type": "error", 
                "message": f"Historical sync failed: {str(e)}"
            })
    finally:
        manager.disconnect(client_id, user_id)

@router.websocket("/ws/email-sync")
async def websocket_email_sync(websocket: WebSocket):
    """
    🚀 FIXED: WebSocket endpoint for immediate 7-day email sync with real-time progress
    """
    client_id = f"sync_{uuid.uuid4()}"
    user_id = None
    
    try:
        # 1. Initial Connection
        await websocket.accept()
        manager.active_connections[client_id] = websocket
        
        # 2. Authentication Phase
        auth_data = await websocket.receive_json()
        token = auth_data.get("jwt_token")
        
        payload = decode_jwt_token_websocket(token)
        if not payload or "user_id" not in payload:
            logger.warning(f"{client_id} - Email sync auth failed: Invalid token")
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close(code=1008)
            return

        user_id = payload["user_id"]
        # Update connection tracking with user_id (don't re-accept!)
        manager.update_user_connection(client_id, user_id)
        logger.info(f"📧 Email sync authenticated for user: {user_id}")

        # 3. Send initial connection confirmation
        await manager.send_progress_update(
            client_id, 
            "connected", 
            "Connected to 7-day email sync", 
            0
        )

        # 4. Start immediate email sync with REAL-TIME progress updates
        await sync_emails_with_progress(client_id, user_id, auth_data.get("access_token"))

    except WebSocketDisconnect:
        logger.info(f"Email sync WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Email sync error for {client_id}: {e}", exc_info=True)
        if client_id in manager.active_connections:
            await manager.send_json(client_id, {
                "type": "error", 
                "message": f"Email sync failed: {str(e)}"
            })
    finally:
        manager.disconnect(client_id, user_id)

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    🚀 FIXED: Handles WebSocket connections for the chat.
    """
    await handle_websocket_connection(websocket)

@router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint_with_chat_id(websocket: WebSocket, chat_id: str):
    """
    🚀 FIXED: Alternative WebSocket endpoint that accepts a chat ID in the URL path.
    """
    await handle_websocket_connection(websocket, provided_chat_id=chat_id)

async def handle_websocket_connection(websocket: WebSocket, provided_chat_id: str = None):
    """
    🚀 FIXED: Common WebSocket connection handler that can work with or without a provided chat ID.
    """
    client_id = f"client_{uuid.uuid4()}"
    user_id = None
    chat_id = provided_chat_id or f"chat_{uuid.uuid4()}"
    
    # Start heartbeat task to keep connection alive during background processing
    heartbeat_task = asyncio.create_task(send_heartbeat_periodically(client_id))

    try:
        # 1. Initial WebSocket Connection
        await manager.connect(websocket, client_id)
        logger.debug(f"🔌 WebSocket connected: {client_id}")
        
        # 2. Authentication Phase with timeout
        try:
            # Wait for authentication message with timeout
            logger.info(f"🔐 {client_id} - Waiting for authentication message...")
            auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            logger.info(f"🔐 {client_id} - Received auth data: {list(auth_data.keys()) if auth_data else 'None'}")
            
            token = auth_data.get("jwt_token")
            
            if not token:
                logger.warning(f"❌ {client_id} - No JWT token provided in auth data: {auth_data}")
                await manager.send_json(client_id, {"error": "Authentication failed. No token provided."})
                await websocket.close(code=1008)
                return

            logger.info(f"🔐 {client_id} - JWT token received, length: {len(token)} chars")
            payload = decode_jwt_token_websocket(token)
            logger.info(f"🔐 {client_id} - JWT payload decoded: {payload is not None}")
            
            if not payload or "user_id" not in payload:
                logger.warning(f"❌ {client_id} - Invalid token or payload: {payload}")
                await manager.send_json(client_id, {"error": "Authentication failed. Invalid token."})
                await websocket.close(code=1008)
                return

            user_id = payload["user_id"]
            logger.info(f"✅ Authentication successful for user: {user_id} ({client_id})")
            
            # Update connection tracking with user_id (don't re-accept!)
            manager.update_user_connection(client_id, user_id)
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ {client_id} - Authentication timeout")
            await manager.send_json(client_id, {"error": "Authentication timeout."})
            await websocket.close(code=1008)
            return
        except json.JSONDecodeError:
            logger.warning(f"📝 {client_id} - Invalid JSON in authentication")
            await manager.send_json(client_id, {"error": "Invalid JSON format for authentication."})
            await websocket.close(code=1008)
            return
        
        logger.info(f"WebSocket authenticated for user_id: {user_id} ({client_id})")

        # 3. Welcome Phase: Send welcome message with chat ID
        welcome_message = {
            "reply": [f"Connected to chat {chat_id}. How can I help you with your emails today?"],
            "chatId": chat_id,
            "error": False
        }
        await manager.send_json(client_id, welcome_message)
        logger.info(f"Sent welcome message to user {user_id} with chat_id: {chat_id} ({client_id})")

        # 4. Chat Loop Phase
        while True:
            try:
                # Check if connection is still valid before trying to receive
                if client_id not in manager.active_connections:
                    logger.warning(f"⚠️ Connection {client_id} no longer in active connections, breaking loop")
                    break
                
                # Validate WebSocket state before receiving
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.warning(f"⚠️ WebSocket {client_id} not in connected state ({websocket.client_state}), breaking loop")
                    break
                
                data = await websocket.receive_json()
                message = data.get("message")
                received_chat_id = data.get("chatId")

                if not message:
                    await manager.send_json(client_id, {"error": "No message provided.", "chatId": received_chat_id})
                    continue
                
                if received_chat_id and received_chat_id != chat_id:
                    logger.warning(f"Chat ID mismatch for user {user_id}. Expected {chat_id}, got {received_chat_id}.")
                    await manager.send_json(client_id, {"error": "Chat ID mismatch.", "chatId": received_chat_id})
                    continue

                logger.info(f"Received query from user {user_id} in chat {chat_id}: '{message}'")
                
                # Call the agent to get a response
                try:
                    logger.info(f"🔄 Calling query_mem0 for user {user_id}...")
                    response = await query_mem0(user_id=user_id, query=message)
                    logger.info(f"✅ query_mem0 completed. Response type: {type(response)}, Length: {len(str(response)) if response else 0}")
                    
                    # Prepare response message
                    response_message = {
                        "reply": [str(response)] if response else ["I apologize, but I couldn't generate a response. Please try again."],
                        "chatId": chat_id,
                        "error": False
                    }
                    logger.info(f"📤 Sending response message: {response_message}")
                    
                    # Send the response back to the client
                    await manager.send_json(client_id, response_message)
                    logger.info(f"✅ Successfully sent response to user {user_id} in chat {chat_id}")
                    
                except Exception as agent_error:
                    logger.error(f"❌ Error in query_mem0 for user {user_id}: {agent_error}", exc_info=True)
                    await manager.send_json(client_id, {
                        "reply": ["I encountered an error while processing your request. Please try again."],
                        "chatId": chat_id,
                        "error": True
                    })

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected by client: {client_id} (User: {user_id}, Chat: {chat_id})")
                break
            except ConnectionClosed:
                logger.info(f"WebSocket connection closed: {client_id} (User: {user_id}, Chat: {chat_id})")
                break
            except RuntimeError as e:
                if "Need to call \"accept\" first" in str(e):
                    logger.warning(f"⚠️ WebSocket {client_id} not properly connected: {e}")
                    break
                else:
                    logger.error(f"Runtime error in chat loop for {client_id}: {e}", exc_info=True)
                    break
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from {client_id}")
                # Don't try to send if connection is invalid
                if client_id in manager.active_connections:
                    await manager.send_json(client_id, {"error": "Invalid JSON format.", "chatId": chat_id})
            except Exception as e:
                logger.error(f"An error occurred in the chat loop for {client_id}: {e}", exc_info=True)
                # Don't try to send if connection is invalid
                if client_id in manager.active_connections:
                    await manager.send_json(client_id, {"error": "An unexpected error occurred.", "chatId": chat_id})
                break

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected before completing auth: {client_id}")
    except ConnectionClosed:
        logger.info(f"🔌 WebSocket connection closed during setup: {client_id}")
    except Exception as e:
        logger.error(f"❌ An error occurred during WebSocket setup for {client_id}: {e}", exc_info=True)
        # Send error message if possible, then close connection
        try:
            if client_id in manager.active_connections:
                await manager.send_json(client_id, {
                    "error": "WebSocket setup failed",
                    "message": "An unexpected error occurred during connection setup"
                })
            await websocket.close(code=1011)
        except Exception as close_error:
            logger.debug(f"⚠️ Error closing WebSocket {client_id}: {close_error}")
    finally:
        # Cancel heartbeat task
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Clean up connection tracking
        manager.disconnect(client_id, user_id)
        logger.debug(f"🧹 Cleaned up WebSocket connection: {client_id}")

async def send_heartbeat_periodically(client_id: str):
    """
    🔧 FIXED: Send periodic heartbeat messages to keep WebSocket connection alive
    Reduced from 25s to 8s to stay well within the 15s timeout
    """
    try:
        while True:
            await asyncio.sleep(8)  # ✅ FIXED: Reduced from 25s - faster than 10s ping interval
            try:
                await manager.send_keepalive(client_id)
                logger.debug(f"💓 [HEARTBEAT] Sent to {client_id}")
            except Exception as e:
                logger.debug(f"⚠️ [HEARTBEAT] Failed to send to {client_id}: {e}")
                break
    except asyncio.CancelledError:
        logger.debug(f"💓 [HEARTBEAT] Task cancelled for {client_id}")
        raise
    except Exception as e:
        logger.error(f"❌ [HEARTBEAT] Error in heartbeat task for {client_id}: {e}")

# ============================================================================
# HELPER FUNCTIONS (Placeholder - implement based on your existing code)
# ============================================================================

async def historical_sync_with_realtime_progress(client_id: str, user_id: str, access_token: str):
    """
    🔧 FIXED: 6-month email sync with continuous WebSocket progress updates to prevent timeouts
    """
    try:
        # Import here to avoid circular imports
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from .gmail import fetch_gmail_emails_historical, email_extractor
        from .db import users_collection, db_manager
        
        # Step 1: Setup (5%)
        await manager.send_progress_update(
            client_id, 
            "initializing", 
            "Setting up 6-month historical email sync...", 
            5
        )
        
        # Build Gmail service with proper credentials for refresh
        # Get user's refresh token from database
        from .db import db_manager
        users_coll = await db_manager.get_collection(user_id, "users")
        user_data = await users_coll.find_one({"user_id": user_id})
        refresh_token = user_data.get("refresh_token") if user_data else None
        
        from .gmail import build_gmail_service
        service = build_gmail_service(
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )
        
        # Step 2: Email Fetching (10-50%)
        await manager.send_progress_update(
            client_id, 
            "fetching", 
            "Fetching 6-month email history (this may take several minutes)...", 
            10
        )
        
        # Fetch emails with progress callbacks
        emails = await fetch_historical_emails_with_progress(service, user_id, client_id)
        
        if not emails:
            await manager.send_progress_update(
                client_id, 
                "complete", 
                "No additional historical emails found", 
                100,
                {"emails_processed": 0, "complete": True}
            )
            return
        
        # Step 3: Email Processing (50-90%)
        await manager.send_progress_update(
            client_id, 
            "processing", 
            f"Processing {len(emails)} historical emails...", 
            50
        )
        
        # Process emails with progress updates and parallel processing
        result = await process_emails_with_websocket_progress(user_id, emails, client_id)
        
        # Step 4: Parallel Financial Processing (75-90%)
        await manager.send_progress_update(
            client_id, 
            "financial_processing", 
            "Processing financial transactions from historical emails...", 
            75
        )
        
        # Process historical financial transactions in parallel
        financial_transactions = 0
        total_amount = 0
        try:
            from .mem0_agent_agno import call_financial_processing_api
            
            financial_result = await call_financial_processing_api(user_id, "websocket_historical_6month")
            
            if financial_result.get("success", False):
                financial_transactions = financial_result.get('transactions_found', 0)
                total_amount = financial_result.get('total_amount', 0)
                logger.info(f"✅ [WEBSOCKET] Historical financial processing complete: {financial_transactions} transactions, total: {total_amount}")
                
                await manager.send_progress_update(
                    client_id, 
                    "financial_complete", 
                    f"Financial analysis complete: {financial_transactions} transactions found", 
                    85
                )
            else:
                logger.warning(f"⚠️ [WEBSOCKET] Financial processing failed: {financial_result.get('error', 'Unknown error')}")
                
        except Exception as financial_error:
            logger.error(f"❌ [WEBSOCKET] Financial processing error: {financial_error}", exc_info=True)
        
        # Step 5: Database Updates (90-95%)
        await manager.send_progress_update(
            client_id, 
            "finalizing", 
            "Updating user status and finalizing sync...", 
            90
        )
        
        # Update user flags with financial data
        users_coll = await db_manager.get_collection(user_id, "users")
        await users_coll.update_one(
            {"user_id": user_id},
            {"$set": {
                "initial_gmailData_sync": True,
                "historical_sync_completed": True,
                "historical_sync_date": asyncio.get_event_loop().time(),
                "historical_emails_processed": result.get("emails_processed", 0),
                "historical_financial_transactions": financial_transactions,
                "historical_total_amount": total_amount,
                "complete_financial_ready": True,
                "background_sync_needed": False
            }},
            upsert=True
        )
        
        # Step 6: Complete (100%)
        await manager.send_progress_update(
            client_id, 
            "complete", 
            f"✅ Complete! {result.get('emails_processed', 0)} emails + {financial_transactions} transactions processed", 
            100,
            {
                "emails_processed": result.get("emails_processed", 0),
                "financial_transactions": financial_transactions,
                "total_amount": total_amount,
                "sync_complete": True,
                "dashboard_enhanced": True,
                "complete_financial_ready": True
            }
        )
        
        logger.info(f"🎉 Historical sync completed successfully for user {user_id}")

    except Exception as e:
        logger.error(f"Error in historical_sync_with_realtime_progress: {e}", exc_info=True)
        await manager.send_json(client_id, {
            "type": "error",
            "message": f"Historical sync failed: {str(e)}"
        })

async def fetch_historical_emails_with_progress(service, user_id: str, client_id: str):
    """Fetch historical emails with real-time progress updates"""
    try:
        from .gmail import fetch_gmail_emails_historical
        from datetime import datetime, timedelta
        
        # Calculate date range for HISTORICAL emails (excludes recent days)
        # This is INTENTIONAL - historical sync should NOT overlap with immediate sync
        end_date = datetime.now() - timedelta(days=7)  # Exclude recent 7 days
        start_date = end_date - timedelta(days=6 * 30)  # Go back 6 months
        
        # NOTE: Using 'before' here is CORRECT for historical emails
        # This ensures no overlap with immediate emails that include today
        query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        
        # Progress updates during fetch
        await manager.send_progress_update(
            client_id, 
            "fetching_phase1", 
            f"Scanning historical emails from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (excluding recent 7 days)...", 
            15
        )
        
        all_messages = []
        page_token = None
        fetched_count = 0
        max_results = 3000  # Reduced for better performance
        
        while fetched_count < max_results:
            try:
                result = service.users().messages().list(
                    userId=user_id,
                    q=query,
                    maxResults=min(100, max_results - fetched_count),
                    pageToken=page_token
                ).execute()
                
                messages = result.get('messages', [])
                if not messages:
                    break
                
                all_messages.extend(messages)
                fetched_count += len(messages)
                
                # Progress update every 500 emails
                if fetched_count % 500 == 0:
                    progress = 15 + (fetched_count / max_results) * 20  # 15-35%
                    await manager.send_progress_update(
                        client_id, 
                        "fetching_ids", 
                        f"Found {fetched_count} historical emails...", 
                        int(progress)
                    )
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching message IDs: {e}")
                break
        
        if not all_messages:
            return []
        
        # Fetch detailed content with progress
        await manager.send_progress_update(
            client_id, 
            "fetching_details", 
            f"Fetching detailed content for {len(all_messages)} emails...", 
            35
        )
        
        emails = []
        batch_size = 50
        
        for i in range(0, len(all_messages), batch_size):
            batch = all_messages[i:i + batch_size]
            
            for message in batch:
                try:
                    email_data = service.users().messages().get(
                        userId=user_id,
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email information
                    headers = email_data.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    
                    # Extract body
                    body = email_extractor.extract_email_body(email_data)
                    
                    emails.append({
                        'id': message['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body,
                        'snippet': email_data.get('snippet', '')
                    })
                    
                except Exception as e:
                    logger.error(f"Error fetching email {message['id']}: {e}")
                    continue
            
            # Progress update
            progress = 35 + ((i + batch_size) / len(all_messages)) * 15  # 35-50%
            await manager.send_progress_update(
                client_id, 
                "fetching_details", 
                f"Fetched {min(i + batch_size, len(all_messages))}/{len(all_messages)} email details...", 
                int(progress)
            )
        
        return emails
        
    except Exception as e:
        logger.error(f"Error fetching historical emails: {e}", exc_info=True)
        return []

async def process_emails_with_websocket_progress(user_id: str, emails: list, client_id: str):
    """Process emails with WebSocket progress updates"""
    try:
        from .main import process_and_store_emails_non_blocking
        
        # Process emails in background with progress updates
        result = await process_and_store_emails_non_blocking(user_id, emails, is_historical=True)
        
        return {
            "emails_processed": len(emails),
            "success": result.get("success", False),
            "financial_transactions": result.get("financial_transactions", 0)
        }
        
    except Exception as e:
        logger.error(f"Error processing emails with WebSocket progress: {e}", exc_info=True)
        return {"emails_processed": 0, "success": False, "financial_transactions": 0}

async def sync_emails_with_progress(client_id: str, user_id: str, access_token: str):
    """
    🔧 FIXED: 7-day email sync with continuous WebSocket progress updates
    """
    try:
        from .main import _process_immediate_emails
        
        # Step 1: Setup (5%)
        await manager.send_progress_update(
            client_id, 
            "initializing", 
            "Setting up 7-day email sync...", 
            5
        )
        
        # Step 2: Process immediate emails (5-95%)
        result = await _process_immediate_emails(user_id, access_token, days=7, websocket_client_id=client_id)
        
        if result.get("success", False):
            emails_processed = result.get("emails_processed", 0)
            financial_transactions = result.get("financial_transactions", 0)
            processing_time = result.get("processing_time", 0)
            
            # Step 3: Success notification
            await manager.send_progress_update(
                client_id, 
                "sync_complete", 
                f"Email sync completed! {emails_processed} emails processed, {financial_transactions} financial transactions found", 
                100,
                {
                    "emails_processed": emails_processed,
                    "financial_transactions": financial_transactions,
                    "processing_time": processing_time,
                    "dashboard_ready": True
                }
            )
            
            # Step 4: Background sync notification
            await manager.send_progress_update(
                client_id, 
                "background_starting", 
                "Dashboard ready! Historical data will load in background...", 
                100,
                {
                    "background_sync": True,
                    "can_start_querying": True
                }
            )
            
        else:
            await manager.send_json(client_id, {
                "type": "error",
                "message": f"Email sync failed: {result.get('message', 'Unknown error')}"
            })

    except Exception as e:
        logger.error(f"Error in sync_emails_with_progress: {e}", exc_info=True)
        await manager.send_json(client_id, {
            "type": "error",
            "message": f"Email sync failed: {str(e)}"
        }) 