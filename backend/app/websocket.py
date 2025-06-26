import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
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

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepts and stores a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """Removes a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

    async def send_json(self, client_id: str, message: dict):
        """Sends a JSON message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

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

manager = ConnectionManager()

@router.websocket("/ws/email-sync")
async def websocket_email_sync(websocket: WebSocket):
    """
    WebSocket endpoint for real-time email synchronization with progress updates
    This prevents connection timeouts during long email processing operations
    """
    client_id = f"sync_{uuid.uuid4()}"
    await manager.connect(websocket, client_id)
    
    try:
        # 1. Authentication Phase
        auth_data = await websocket.receive_json()
        token = auth_data.get("jwt_token")
        
        payload = decode_jwt_token_websocket(token)
        if not payload or "user_id" not in payload:
            logger.warning(f"{client_id} - Email sync auth failed: Invalid token")
            await manager.send_json(client_id, {"type": "error", "message": "Authentication failed"})
            await websocket.close(code=1008)
            return

        user_id = payload["user_id"]
        logger.info(f"🔄 Email sync authenticated for user: {user_id}")

        # 2. Send initial connection confirmation
        await manager.send_progress_update(
            client_id, 
            "connected", 
            "Connected to email sync service", 
            0
        )

        # 3. Start email synchronization with progress updates
        await sync_emails_with_progress(client_id, user_id, auth_data.get("access_token"))

    except WebSocketDisconnect:
        logger.info(f"Email sync WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Email sync error for {client_id}: {e}", exc_info=True)
        await manager.send_json(client_id, {
            "type": "error", 
            "message": f"Email sync failed: {str(e)}"
        })
    finally:
        manager.disconnect(client_id)

async def sync_emails_with_progress(client_id: str, user_id: str, access_token: str):
    """
    Perform email synchronization with real-time progress updates
    """
    try:
        # Import here to avoid circular imports
        from .main import _process_immediate_emails
        from .db import users_collection
        
        # Step 1: Check user status
        await manager.send_progress_update(
            client_id, 
            "checking_status", 
            "Checking user email sync status...", 
            10
        )
        
        user = await users_collection.find_one({"user_id": user_id})
        if not user:
            raise Exception("User not found")

        # Step 2: Start immediate email processing
        await manager.send_progress_update(
            client_id, 
            "starting_sync", 
            "Starting immediate email synchronization (1-week recent emails)...", 
            20
        )

        # Step 3: Process emails with progress updates
        await manager.send_progress_update(
            client_id, 
            "fetching_emails", 
            "Fetching recent emails from Gmail...", 
            30
        )

        # Run email processing with WebSocket progress updates
        result = await _process_immediate_emails(user_id, access_token, days=7, websocket_client_id=client_id)
        
        if result.get("success"):
            emails_processed = result.get("emails_processed", 0)
            financial_transactions = result.get("financial_transactions", 0)
            processing_time = result.get("processing_time", "0s")
            
            # Step 4: Success notification
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
            
            # Step 5: Background sync notification
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

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections for the chat.

    This endpoint manages a persistent, stateful connection with the client,
    aligning with the frontend's expected protocol:
    1.  Accepts connection.
    2.  Waits for an authentication message with a JWT token.
    3.  If auth is successful, it generates a unique `chat_id`.
    4.  Sends a "welcome" message back to the client, including the `chat_id`.
    5.  Enters a loop, listening for incoming user queries on the same connection.
    6.  Processes each query using the `query_mem0` agent function.
    7.  Sends the agent's response back to the client.
    8.  Handles disconnection gracefully.
    """
    await handle_websocket_connection(websocket)

@router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint_with_chat_id(websocket: WebSocket, chat_id: str):
    """
    Alternative WebSocket endpoint that accepts a chat ID in the URL path.
    This is for compatibility with frontends that include the chat ID in the URL.
    """
    await handle_websocket_connection(websocket, provided_chat_id=chat_id)

async def handle_websocket_connection(websocket: WebSocket, provided_chat_id: str = None):
    """
    Common WebSocket connection handler that can work with or without a provided chat ID.
    """
    client_id = f"client_{uuid.uuid4()}"
    await manager.connect(websocket, client_id)
    
    user_id = None
    chat_id = provided_chat_id or f"chat_{uuid.uuid4()}"
    
    # Start heartbeat task to keep connection alive during background processing
    heartbeat_task = asyncio.create_task(send_heartbeat_periodically(client_id))

    try:
        # 1. Authentication Phase
        auth_data = await websocket.receive_json()
        token = auth_data.get("jwt_token")
        
        payload = decode_jwt_token_websocket(token)
        if not payload or "user_id" not in payload:
            logger.warning(f"{client_id} - WebSocket auth failed: Invalid token or payload.")
            await manager.send_json(client_id, {"error": "Authentication failed. Invalid token."})
            await websocket.close(code=1008)
            manager.disconnect(client_id)
            return

        user_id = payload["user_id"]
        logger.info(f"WebSocket authenticated for user_id: {user_id} ({client_id})")

        # 2. Welcome Phase: Send welcome message with chat ID
        welcome_message = {
            "reply": [f"Connected to chat {chat_id}. How can I help you with your emails today?"],
            "chatId": chat_id,
            "error": False
        }
        await manager.send_json(client_id, welcome_message)
        logger.info(f"Sent welcome message to user {user_id} with chat_id: {chat_id} ({client_id})")

        # 3. Chat Loop Phase
        while True:
            try:
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
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from {client_id}")
                await manager.send_json(client_id, {"error": "Invalid JSON format.", "chatId": chat_id})
            except Exception as e:
                logger.error(f"An error occurred in the chat loop for {client_id}: {e}", exc_info=True)
                await manager.send_json(client_id, {"error": "An unexpected error occurred.", "chatId": chat_id})
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected before completing auth: {client_id}")
    except Exception as e:
        logger.error(f"An error occurred during WebSocket setup for {client_id}: {e}", exc_info=True)
        # Ensure connection is closed if an error occurs during setup
        await websocket.close(code=1011)
    finally:
        # Cancel heartbeat task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        manager.disconnect(client_id)

async def send_heartbeat_periodically(client_id: str):
    """
    Send periodic heartbeat messages to keep WebSocket connection alive
    """
    try:
        while True:
            await asyncio.sleep(25)  # Send heartbeat every 25 seconds
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
