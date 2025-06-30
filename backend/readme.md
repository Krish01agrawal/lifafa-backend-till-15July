# 🚀 Gmail Intelligence Backend - Complete Financial & AI Platform

A comprehensive FastAPI-based financial intelligence platform that integrates Gmail, AI agents, and advanced financial services to provide users with intelligent email analysis, financial insights, and personalized recommendations.

## 🏗️ ARCHITECTURE OVERVIEW

### **Clean Architecture Implementation**
```
backend/
├── app/
│   ├── config/          # Configuration layer
│   │   ├── settings.py  # Pydantic settings with env vars
│   │   ├── database.py  # MongoDB configuration
│   │   └── constants.py # Application constants
│   ├── core/           # Core infrastructure
│   │   ├── dependencies.py  # FastAPI dependency injection
│   │   ├── security.py     # JWT & OAuth security
│   │   └── middleware.py   # Rate limiting & monitoring
│   ├── models/         # Data models
│   │   ├── auth.py     # User & authentication models
│   │   ├── gmail.py    # Email & thread models
│   │   ├── financial.py # Transaction & analysis models
│   │   ├── credit.py   # Credit report & card models
│   │   └── common.py   # Base models & responses
│   └── services/       # Service layer (business logic)
│       ├── auth_service.py
│       ├── gmail_service.py
│       └── database_service.py
```

### **Technology Stack (160+ Dependencies)**
- **Core Framework**: FastAPI 0.115.12, Uvicorn, Starlette
- **Database**: MongoDB with Motor (async) + PyMongo (sync)
- **AI/ML**: OpenAI GPT-4, Agno 1.5.6 (AI agent framework), Mem0 AI 0.1.102
- **Authentication**: Google OAuth2, JWT with python-jose
- **Advanced Features**: PDF processing, browser automation (Playwright), data analysis (Pandas, NumPy, SciPy)
- **Real-time**: WebSocket support with connection management
- **Performance**: Smart caching, batch processing, rate limiting

## 🎯 CORE FEATURES

### **1. Gmail Intelligence System**
- **Progressive Email Loading**: Immediate 1-week processing + background 6-month historical sync
- **AI-Powered Categorization**: Agno agent teams for email classification
- **Smart Memory**: Mem0 integration for contextual email search and insights
- **Real-time Processing**: WebSocket progress updates during email sync

### **2. Advanced Financial Features**
- **Credit Report Integration**: CIBIL, Experian, CRIF, Equifax APIs
- **Bank Statement Processing**: PDF/CSV/Excel parsing with AI insights
- **Credit Card Recommendations**: Personalized suggestions based on financial profile
- **Browser Automation**: Automated form filling and data scraping
- **Transaction Analysis**: AI-powered spending pattern recognition

### **3. Real-time Communication**
- **Multiple WebSocket Endpoints**: Chat, email sync, historical processing
- **Connection Management**: User-based connection tracking with cleanup
- **Progress Updates**: Real-time sync status and processing updates
- **Heartbeat System**: Connection keepalive and timeout prevention

### **4. Performance & Scalability**
- **Smart Caching**: In-memory caching with LRU eviction
- **Rate Limiting**: Per-user and global request limits
- **Batch Processing**: Concurrent email processing with semaphores
- **Resource Management**: Memory monitoring and cleanup

## 🔄 COMPLETE DATA FLOW

### **Phase 1: Authentication & Setup**
```
POST /auth/google-login
├── Verify Google OAuth token
├── Create/update user in MongoDB
├── Generate JWT token
└── Return authentication response
```

### **Phase 2: Progressive Email Processing**
```
POST /gmail/fetch (with JWT)
├── Immediate Processing (1 week)
│   ├── Fetch recent emails via Gmail API
│   ├── Process with Mem0 Intelligence
│   ├── Update user status (dashboard_ready = true)
│   └── Return immediate response
└── Background Processing (6 months)
    ├── WebSocket connection for progress updates
    ├── Historical email fetch with batching
    ├── AI categorization using Agno agents
    ├── Mem0 memory storage with semantic indexing
    └── Financial transaction extraction
```

### **Phase 3: Real-time Query Processing**
```
WebSocket /ws/chat/{chat_id}
├── JWT authentication
├── Query analysis and refinement
├── Mem0 semantic search
├── AI-powered response generation
├── Financial insights compilation
└── Real-time response delivery
```

## 📡 API ENDPOINTS

### **Authentication**
- `POST /auth/google-login` - Google OAuth login with JWT generation
- `GET /auth/login` - OAuth redirect initiation
- `GET /auth/callback` - OAuth callback handling
- `GET /me` - Current user profile with sync status

### **Gmail Intelligence**
- `POST /gmail/fetch` - Progressive email fetch (immediate + background)
- `POST /gmail/download-data` - Export Gmail data (6 months JSON)
- `GET /gmail/query` - Direct email search in Mem0

### **Financial Services**
- `POST /financial/process-from-emails` - Fast financial analysis from stored emails
- `GET /financial/summary` - Comprehensive financial dashboard
- `GET /financial/transactions` - Transaction history with categorization

### **Credit Services**
- `POST /credit-reports/fetch` - Fetch credit report from Indian bureaus
- `GET /credit-reports/history` - User's credit report history
- `POST /credit-cards/recommendations` - Personalized card recommendations
- `POST /credit-cards/apply` - Initiate card application process

### **Statement Processing**
- `POST /statement/upload` - Upload and process bank statements
- `GET /statement/insights` - AI-generated financial insights
- `GET /statement/transactions` - Extracted transaction data

### **Browser Automation**
- `POST /automation/scrape-cards` - Scrape credit cards from comparison sites
- `POST /automation/fill-application` - Auto-fill application forms
- `GET /automation/status` - Track automation task status

### **System Monitoring**
- `GET /health` - Comprehensive health check with scalability metrics
- `GET /metrics` - Detailed system performance metrics
- `GET /financial/health` - Financial services health check

### **WebSocket Endpoints**
- `WS /ws/chat/{chat_id}` - Real-time chat with AI agents
- `WS /ws/email-sync` - Email synchronization progress
- `WS /ws/historical-sync` - 6-month historical processing

## 🧠 AI AGENT SYSTEM (Agno Framework)

### **Gmail Intelligence Team**
```python
# Master coordination with specialized agents
Gmail Intelligence Team:
├── Email Processor Agent    # Categorization & Mem0 storage
├── Email Query Agent       # Intelligent search & analysis  
├── Email Analytics Agent   # Insights & reporting
└── Financial Analysis Agent # Transaction extraction
```

### **Query Processing Pipeline**
```
User Query → Query Analyzer → Intent Detection → Mem0 Search → AI Response
```

### **Email Categorization**
- **Smart Batch Processing**: Concurrent categorization with rate limiting
- **Financial Detection**: Banking, payments, subscriptions, investments
- **Merchant Recognition**: Automated vendor and amount extraction
- **Pattern Learning**: Improved accuracy through user feedback

## 🗄️ DATABASE SCHEMA

### **Users Collection**
```javascript
{
  user_id: "google_user_id",
  email: "user@gmail.com",
  name: "User Name",
  picture: "profile_url",
  
  // Progressive sync status
  dashboard_ready: true,
  initial_gmailData_sync: true,
  historical_sync_completed: true,
  background_sync_needed: false,
  
  // Financial features
  complete_financial_ready: true,
  financial_analysis_completed: true,
  recent_financial_transactions: 1250,
  
  // Timestamps
  last_sync_timestamp: "2025-01-15T10:30:00Z",
  access_token: "encrypted_oauth_token",
  refresh_token: "encrypted_refresh_token"
}
```

### **Emails Collection**
```javascript
{
  user_id: "google_user_id",
  id: "gmail_message_id",
  subject: "Email Subject",
  sender: "sender@domain.com",
  snippet: "Email preview text",
  body: "Full email content",
  date: "2025-01-15T10:30:00Z",
  
  // AI categorization
  category: "financial",
  subcategory: "banking",
  merchant: "HDFC Bank",
  amount: 5000.0,
  payment_method: "UPI",
  
  // Processing metadata
  processed_at: "2025-01-15T10:35:00Z",
  mem0_stored: true
}
```

### **Financial Collections**
- **credit_reports**: Credit bureau data with AI insights
- **bank_statements**: Processed statement data and transactions
- **credit_cards**: Recommendations and application tracking
- **automation_tasks**: Browser automation task status

## 🔧 CONFIGURATION

### **Environment Variables**
```bash
# Core Application
OPENAI_API_KEY=your_openai_key
MEM0_API_KEY=your_mem0_key
JWT_SECRET=your_jwt_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
REDIRECT_URI=your_redirect_uri

# Database
MONGODB_URL=your_mongodb_connection

# Credit Bureau APIs
CIBIL_API_KEY=your_cibil_key
EXPERIAN_API_KEY=your_experian_key
CRIF_API_KEY=your_crif_key
EQUIFAX_API_KEY=your_equifax_key

# Performance Settings
ENABLE_SMART_CACHING=true
ENABLE_BATCH_PROCESSING=true
MAX_CONCURRENT_EMAIL_PROCESSING=10
EMAIL_PROCESSING_TIMEOUT=600
```

### **Performance Configuration**
```python
# Smart caching settings
MAX_CACHE_SIZE_MB = 256
CACHE_TTL_SECONDS = 3600

# Batch processing
EMAIL_CATEGORIZATION_BATCH_SIZE = 50
MAX_CONCURRENT_AI_REQUESTS = 5

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 100
CONCURRENT_USERS_LIMIT = 1000
```

## 🚀 DEPLOYMENT

### **Installation**
```bash
cd backend
pip install -r requirements.txt
```

### **Run Development Server**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Production Deployment**
```bash
# Using the provided deployment script
./deploy_production.sh

# Or manually with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📊 MONITORING & PERFORMANCE

### **Health Check Response**
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "timestamp": 1736934000,
  "scalability": {
    "cpu": {"current_percent": 45.2},
    "memory": {"current_percent": 67.8},
    "capacity_utilization_percent": 72.5
  },
  "services": {
    "credit_reports": {"status": "healthy", "total_reports": 1250},
    "statement_processor": {"status": "healthy", "total_statements": 890},
    "credit_card_service": {"status": "healthy", "total_cards": 450}
  }
}
```

### **Performance Metrics**
- **Email Processing**: 1000+ emails/minute with batch processing
- **WebSocket Connections**: 1000+ simultaneous connections
- **Cache Hit Rate**: 85%+ for frequent queries
- **Response Time**: <500ms for cached queries, <2s for AI processing

## 🛡️ SECURITY FEATURES

### **Authentication & Authorization**
- **Google OAuth2**: Secure user authentication
- **JWT Tokens**: Stateless authentication with 48-hour expiry
- **Rate Limiting**: Per-user and global request limits
- **Data Encryption**: Sensitive financial data encryption

### **Data Privacy**
- **Email Content**: Never logged in plain text
- **Financial Data**: Encrypted storage and transmission
- **PII Protection**: Masking of sensitive personal information
- **Compliance**: Following email privacy regulations

## 🔄 BACKGROUND PROCESSING

### **Scheduled Tasks**
- **Email Sync Worker**: Checks for new users every 10 seconds
- **Financial Analysis Worker**: Processes financial data every 45 seconds
- **Performance Monitor**: System health checks every second
- **Cache Cleanup**: Removes expired cache entries every hour

### **WebSocket Management**
- **Connection Cleanup**: Automatic cleanup of failed connections
- **User Tracking**: Multiple connections per user supported
- **Heartbeat System**: Prevents connection timeouts
- **Progress Updates**: Real-time sync status communication

## 🎯 FRONTEND INTEGRATION

### **WebSocket Connection Example**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/room1');

// Authentication
ws.send(JSON.stringify({
  jwt_token: "your_jwt_token"
}));

// Query processing
ws.send(JSON.stringify({
  message: "Show me my December food expenses with UPI payments"
}));

// Handle responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('AI Response:', data.message);
};
```

### **API Integration Example**
```javascript
// Fetch user emails with progressive loading
const response = await fetch('/gmail/fetch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    jwt_token: userToken,
    access_token: googleAccessToken
  })
});

// Get comprehensive financial dashboard
const dashboard = await fetch('/financial/dashboard/complete', {
  headers: {
    'Authorization': `Bearer ${userToken}`
  }
});
```

---

## 🎉 SYSTEM CAPABILITIES

**✅ Complete Gmail Intelligence System**
- Progressive email loading with immediate dashboard access
- AI-powered email categorization and insights
- Real-time query processing with contextual responses
- 6-month historical data processing with progress tracking

**✅ Advanced Financial Services**
- Credit report integration with 4 Indian bureaus
- Bank statement processing with AI insights
- Personalized credit card recommendations
- Browser automation for applications

**✅ Enterprise-Grade Performance**
- Smart caching with 85%+ hit rate
- Batch processing for high throughput
- Rate limiting and resource management
- Comprehensive monitoring and health checks

**✅ Real-time Communication**
- Multiple WebSocket endpoints for different use cases
- Connection management with cleanup and heartbeat
- Progress updates for long-running operations
- Multi-user support with user-specific tracking

The backend now provides a **comprehensive financial intelligence platform** that processes Gmail data, provides AI-powered insights, and offers advanced financial services through a clean, scalable architecture.