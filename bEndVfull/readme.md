# 🚀 Gmail Intelligence Backend - Complete Architecture

A FastAPI-based backend service that integrates with Google OAuth2 and Gmail API to fetch, process, and analyze emails using AI-powered memory agents.

This backend implements a comprehensive Gmail Intelligence system that processes Gmail emails through Mem0 memory storage and provides AI-powered insights via WebSocket connections.

## 🏗️ ARCHITECTURE FLOW
- 🔐 **Google OAuth2 Authentication** - Secure user login with Google accounts
- 📧 **Gmail Integration** - Fetch and process emails from user's Gmail account
- 🧠 **AI-Powered Analysis** - Uses Mem0 and OpenAI for intelligent email processing
- 🔄 **Real-time Updates** - WebSocket support for live data streaming
- 📊 **Automated Email Syncing** - Background jobs to keep email data up-to-date
- 🛡️ **JWT Security** - Token-based authentication for API endpoints

### 1. **Gmail Data Ingestion Flow**
```
User Login → Gmail OAuth → Email Fetch → Mem0 Upload → User Status Update
```

**Components:**
- `oauth.py` - Google OAuth authentication
- `gmail.py` - Gmail API integration
- `mem0_agent.py` - Email processing and Mem0 storage
- `main.py` - API endpoints coordination
- **Framework**: FastAPI
- **Database**: MongoDB
- **Authentication**: Google OAuth2 + JWT
- **AI/ML**: OpenAI GPT, Mem0 AI
- **Background Jobs**: APScheduler
- **WebSockets**: FastAPI WebSocket support
- **Email API**: Gmail API

### 2. **Query Processing Flow**
```
Frontend → WebSocket → Query Analyzer → Mem0 Search → AI Response → WebSocket Response
```

**Components:**
- `websocket.py` - Real-time WebSocket communication
- `query_analyzer_agent.py` - Query refinement and optimization
- `mem0_agent.py` - Gmail Intelligence Team processing
- AI agents for comprehensive email analysis

## 🔧 KEY COMPONENTS

### **Main Application (`main.py`)**
- FastAPI application with CORS configuration
- Gmail fetch endpoints with JWT authentication
- Automatic user status tracking
- Background email processing scheduler

### **WebSocket Handler (`websocket.py`)**
- Real-time chat interface
- JWT-based authentication
- Enhanced query processing pipeline
- Multi-user chat room support

### **Gmail Intelligence System (`mem0_agent.py`)**
- **Gmail Intelligence Team** - Master coordination with Agno agents
- **Email Processor Agent** - Email categorization and Mem0 storage
- **Email Query Agent** - Intelligent search and analysis
- **Email Analytics Agent** - Comprehensive insights and reports
- **Direct Data Analysis** - Real transaction extraction and insights

### **Query Analyzer (`query_analyzer_agent.py`)**
- Query optimization for Gmail email search
- Intent detection and entity extraction
- Search term refinement for better results

## 🌊 COMPLETE DATA FLOW

### **Phase 1: Gmail Data Ingestion**

1. **User Authentication**
   ```
   POST /auth/google-login
   → Verify Google token
   → Create/update user in MongoDB
   → Return JWT token
   ```

2. **Gmail Data Fetch**
   ```
   POST /gmail/fetch
   → Authenticate with JWT
   → Build Gmail service with access token
   → Fetch emails (last 70 days, max 4500)
   → Store in MongoDB
   → Process with Mem0 Intelligence
   → Update user sync status
   ```

3. **Enhanced Mem0 Processing**
   ```python
   process_gmail_data_for_user(user_id, emails)
   → Email categorization (banking, food, shopping, etc.)
   → Metadata extraction (amounts, merchants, dates)
   → Mem0 memory storage with semantic indexing
   → User status update (initial_gmailData_sync = True)
   ```

### **Phase 2: Real-time Query Processing**

1. **WebSocket Connection**
   ```
   WS /ws/chat/{chat_id}
   → JWT authentication
   → Connection confirmation
   → Chat room initialization
   ```

2. **Query Processing Pipeline**
   ```
   User Query → Query Analyzer → Mem0 Search → AI Response
   
   handle_websocket_query()
   ├── Check user Gmail sync status
   ├── analyze_and_refine_query() - Query optimization
   ├── query_email_database() - Gmail Intelligence Team
   └── WebSocket response with insights
   ```

3. **AI-Powered Analysis**
   ```python
   Gmail Intelligence Team:
   ├── Email Processor Agent - Categorization
   ├── Email Query Agent - Search optimization  
   └── Email Analytics Agent - Insights generation
   
   Response Types:
   ├── Transaction tables with real data
   ├── Financial insights and recommendations
   ├── Spending pattern analysis
   └── Risk profiling and investment advice
   ```

## 🔑 KEY FEATURES

### **Automatic User ID Detection**
- JWT token contains user_id from Google OAuth
- All operations automatically use signed-in user's ID
- No manual user_id input required

### **Query Refinement**
- Original: "Show me food expenses"
- Refined: "food delivery swiggy zomato restaurant order meal payment"
- Better search results through optimization

### **Comprehensive Email Analysis**
- Real transaction extraction from email content
- Category-wise spending breakdown
- Merchant analysis and payment method tracking
- Financial insights with exact numbers

### **Real-time WebSocket Communication**
- Instant query processing and responses
- Multi-user chat room support
- Connection status management
- Error handling and reconnection

## 📡 API ENDPOINTS

### **Authentication**
- `POST /auth/google-login` - Google OAuth login
- `GET /auth/login` - OAuth redirect
- `GET /auth/callback` - OAuth callback
- `GET /me` - Current user info

### **Gmail Integration**
- `POST /gmail/fetch` - Fetch and process Gmail emails
- `POST /emails/fetch` - Alternative email fetch
- `POST /emails/fetch-with-token` - Token-based fetch

### **Testing**
- `POST /test/mem0-query` - Direct Mem0 query testing

### **WebSocket**
- `WS /ws/chat/{chat_id}` - Real-time chat interface

## 🗄️ DATABASE SCHEMA

### **Users Collection**
```javascript
{
  user_id: "google_user_id",
  email: "user@gmail.com", 
  name: "User Name",
  picture: "profile_url",
  initial_gmailData_sync: true,
  fetched_email: true,
  last_sync_timestamp: "2025-01-15T10:30:00Z",
  access_token: "oauth_token"
}
```

### **Emails Collection**
```javascript
{
  user_id: "google_user_id",
  id: "gmail_message_id",
  subject: "Email Subject",
  snippet: "Email preview",
  body: "Full email content"
}
```

## 🚀 DEPLOYMENT

### **Environment Variables**
```bash
OPENAI_API_KEY=your_openai_key
MEM0_API_KEY=your_mem0_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MONGODB_URL=your_mongodb_connection
JWT_SECRET_KEY=your_jwt_secret
FRONTEND_URL=your_frontend_url
```

### **Installation**
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔄 BACKGROUND PROCESSING

- **Scheduler**: Checks for new users every 2 minutes
- **Auto-fetch**: Processes emails for users with `fetched_email=false`
- **Status tracking**: Updates sync status automatically

## 🎯 FRONTEND INTEGRATION

### **WebSocket Connection**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/room1');

// Send authentication
ws.send(JSON.stringify({
  jwt_token: "your_jwt_token"
}));

// Send queries
ws.send(JSON.stringify({
  message: "Show me my April food expenses"
}));
```

### **Response Format**
```javascript
{
  message: "AI-generated response with insights",
  type: "success|warning|error",
  sender_id: "user_id",
  chat_id: "room1",
  timestamp: "2025-01-15T10:30:00Z",
  requires_sync: false
}
```

## 🛡️ SECURITY

- JWT-based authentication for all operations
- Google OAuth integration
- WebSocket authentication required
- User data isolation by user_id
- Secure token handling

## 📊 MONITORING

- Comprehensive logging throughout the pipeline
- Error tracking and handling
- Performance monitoring
- User activity tracking

---

## 🎉 RESULT

**Complete Gmail Intelligence System** with:
✅ Automatic Gmail data ingestion and processing  
✅ Real-time WebSocket communication  
✅ AI-powered query refinement  
✅ Comprehensive financial insights  
✅ User-specific data isolation  
✅ Scalable architecture with background processing  

The system now provides the exact flow you requested: **Gmail Fetch → Mem0 Upload → Auto User ID → Query Refinement → AI Response → WebSocket Delivery**