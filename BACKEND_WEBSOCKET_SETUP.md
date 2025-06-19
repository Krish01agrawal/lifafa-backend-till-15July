# Backend WebSocket Setup Guide

This guide helps you set up the WebSocket server on your backend to fix the connection issues you're experiencing.

## Problem Diagnosis

Based on our tests, your backend server is:
- ✅ Running and accessible via HTTP
- ❌ Not configured to handle WebSocket connections
- ❌ Returning HTTP 200 instead of WebSocket upgrade
- ❌ No HTTPS/SSL configuration

## Required WebSocket Endpoint

Your frontend expects a WebSocket endpoint at:
```
ws://your-domain.com/ws/chat/{chatId}
```

## Setup Instructions by Framework

### FastAPI (Python)

1. **Install dependencies:**
```bash
pip install fastapi uvicorn websockets
```

2. **Add WebSocket endpoint to your FastAPI app:**
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketDisconnect
import json
import asyncio

app = FastAPI()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, chat_id: str):
        await websocket.accept()
        self.active_connections[chat_id] = websocket
        print(f"✅ WebSocket connected for chat: {chat_id}")

    def disconnect(self, chat_id: str):
        if chat_id in self.active_connections:
            del self.active_connections[chat_id]
            print(f"❌ WebSocket disconnected for chat: {chat_id}")

    async def send_message(self, message: str, chat_id: str):
        if chat_id in self.active_connections:
            websocket = self.active_connections[chat_id]
            await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "ping":
                # Respond to heartbeat
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
            
            # Handle authentication
            if "jwt_token" in message_data:
                # Validate JWT token here
                print(f"🔐 Authentication received for chat: {chat_id}")
                await websocket.send_text(json.dumps({
                    "type": "auth_success",
                    "message": "Authenticated successfully"
                }))
                continue
            
            # Handle chat messages
            if "message" in message_data:
                user_message = message_data["message"]
                print(f"📩 Received message in chat {chat_id}: {user_message}")
                
                # TODO: Process with your AI model
                # For now, send a mock response
                ai_response = f"I received your message: '{user_message}'. This is a test response from the WebSocket server."
                
                response_data = {
                    "message": {
                        "reply": [ai_response]
                    }
                }
                
                await websocket.send_text(json.dumps(response_data))
                
    except WebSocketDisconnect:
        manager.disconnect(chat_id)
        print(f"🔌 Client disconnected from chat: {chat_id}")
    except Exception as e:
        print(f"❌ WebSocket error in chat {chat_id}: {e}")
        manager.disconnect(chat_id)

# Add this to your existing FastAPI routes
@app.get("/")
async def root():
    return {"message": "WebSocket server is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "websocket_endpoint": "/ws/chat/{chat_id}"}
```

3. **Run your FastAPI server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Express.js (Node.js)

1. **Install dependencies:**
```bash
npm install express ws jsonwebtoken
```

2. **Create WebSocket server:**
```javascript
const express = require('express');
const { WebSocketServer } = require('ws');
const http = require('http');
const url = require('url');
const jwt = require('jsonwebtoken');

const app = express();
const server = http.createServer(app);

// Create WebSocket server
const wss = new WebSocketServer({ 
    server,
    path: '/ws/chat'
});

// Store active connections
const connections = new Map();

wss.on('connection', (ws, req) => {
    const pathname = url.parse(req.url).pathname;
    const chatId = pathname.split('/').pop(); // Extract chat ID from path
    
    console.log(`✅ WebSocket connected for chat: ${chatId}`);
    connections.set(chatId, ws);
    
    ws.on('message', async (data) => {
        try {
            const message = JSON.parse(data.toString());
            
            // Handle heartbeat
            if (message.type === 'ping') {
                ws.send(JSON.stringify({ type: 'pong' }));
                return;
            }
            
            // Handle authentication
            if (message.jwt_token) {
                // Validate JWT token here
                console.log(`🔐 Authentication received for chat: ${chatId}`);
                ws.send(JSON.stringify({
                    type: 'auth_success',
                    message: 'Authenticated successfully'
                }));
                return;
            }
            
            // Handle chat messages
            if (message.message) {
                console.log(`📩 Received message in chat ${chatId}: ${message.message}`);
                
                // TODO: Process with your AI model
                // For now, send a mock response
                const aiResponse = `I received your message: '${message.message}'. This is a test response from the WebSocket server.`;
                
                const responseData = {
                    message: {
                        reply: [aiResponse]
                    }
                };
                
                ws.send(JSON.stringify(responseData));
            }
            
        } catch (error) {
            console.error('❌ Error processing WebSocket message:', error);
        }
    });
    
    ws.on('close', () => {
        console.log(`🔌 Client disconnected from chat: ${chatId}`);
        connections.delete(chatId);
    });
    
    ws.on('error', (error) => {
        console.error(`❌ WebSocket error in chat ${chatId}:`, error);
        connections.delete(chatId);
    });
});

// Regular HTTP routes
app.get('/', (req, res) => {
    res.json({ message: 'WebSocket server is running' });
});

app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        websocket_endpoint: '/ws/chat/{chat_id}',
        active_connections: connections.size
    });
});

const PORT = process.env.PORT || 8000;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}/ws/chat/{chat_id}`);
});
```

3. **Run your Node.js server:**
```bash
node server.js
```

## Testing Your WebSocket Server

1. **Test the WebSocket endpoint:**
```bash
cd /path/to/your/frontend
node scripts/test-websocket.js
```

2. **Expected output:**
```
✅ ws://your-domain.com/ws/chat/test-123 - WORKING
```

## Deployment on EC2

1. **Install dependencies on your EC2 instance**
2. **Configure your web server (nginx/apache) to proxy WebSocket connections**
3. **For nginx, add this to your config:**
```nginx
location /ws/ {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

4. **Restart your web server:**
```bash
sudo systemctl restart nginx
```

## SSL/HTTPS Setup (Optional but Recommended)

1. **Install Let's Encrypt certificate:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

2. **Update your frontend config to use HTTPS:**
```javascript
// In app.config.js
apiUrl: "https://your-domain.com/api"
```

## Troubleshooting

### Common Issues:

1. **"Unexpected server response: 200"**
   - Your server is not configured to handle WebSocket upgrades
   - Make sure you're using a proper WebSocket library
   - Check that the WebSocket endpoint path matches exactly

2. **"ECONNREFUSED"**
   - WebSocket server is not running
   - Wrong port or URL
   - Firewall blocking connections

3. **Connection drops immediately**
   - Missing authentication handling
   - Incorrect message format
   - Server-side error in WebSocket handler

### Debug Steps:

1. **Check if WebSocket endpoint exists:**
```bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://your-domain.com/ws/chat/test-123
```

2. **Check server logs for WebSocket connections**

3. **Use browser dev tools to inspect WebSocket traffic**

## Next Steps

1. **Choose your backend framework** (FastAPI recommended for Python, Express.js for Node.js)
2. **Implement the WebSocket endpoint** using the code above
3. **Deploy to your EC2 instance**
4. **Test with our WebSocket test script**
5. **Configure SSL for production** (optional)

Once you have the WebSocket server running, your chat application will connect successfully and stop the infinite reconnection loop! 