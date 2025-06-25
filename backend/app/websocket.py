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
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

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
        manager.disconnect(client_id)
