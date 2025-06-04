# Lifafa Backend

A FastAPI-based backend service that integrates with Google OAuth2 and Gmail API to fetch, process, and analyze emails using AI-powered memory agents.

## Features

- 🔐 **Google OAuth2 Authentication** - Secure user login with Google accounts
- 📧 **Gmail Integration** - Fetch and process emails from user's Gmail account
- 🧠 **AI-Powered Analysis** - Uses Mem0 and OpenAI for intelligent email processing
- 🔄 **Real-time Updates** - WebSocket support for live data streaming
- 📊 **Automated Email Syncing** - Background jobs to keep email data up-to-date
- 🛡️ **JWT Security** - Token-based authentication for API endpoints

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB
- **Authentication**: Google OAuth2 + JWT
- **AI/ML**: OpenAI GPT, Mem0 AI
- **Background Jobs**: APScheduler
- **WebSockets**: FastAPI WebSocket support
- **Email API**: Gmail API

## Prerequisites

- Python 3.8+
- MongoDB instance
- Google Cloud Console project with Gmail API enabled
- OpenAI API key
- Mem0 API key

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd lifafa-backend/backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Fill in your configuration values in `.env`:

```env
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# OAuth2 Redirect URI
REDIRECT_URI=http://localhost:8001/auth/callback

# Frontend URL
FRONTEND_URL=http://localhost:8000

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production

# MongoDB Configuration
MONGO_URI=your-mongodb-connection-string

# Memory Platform Configuration
MEM0_API_KEY=your-mem0-api-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
```

### 5. Google Cloud Console Setup

1. Create a new project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth2 credentials (Web application)
4. Add your redirect URI to authorized redirect URIs
5. Copy the client ID and secret to your `.env` file

### 6. Run the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`

## API Documentation

### Authentication Endpoints

#### `POST /auth/google-login`
Authenticate user with Google ID token.

**Request Body:**
```json
{
  "token": "google-id-token"
}
```

**Response:**
```json
{
  "jwt_token": "jwt-token",
  "user": {
    "email": "user@example.com",
    "name": "User Name",
    "picture": "profile-picture-url",
    "user_id": "google-user-id"
  }
}
```

#### `GET /auth/login`
Redirect to Google OAuth consent screen.

#### `GET /auth/callback`
Handle OAuth callback from Google.

### Email Endpoints

#### `POST /gmail/fetch`
Fetch emails from user's Gmail account.

**Request Body:**
```json
{
  "jwt_token": "user-jwt-token",
  "access_token": "google-access-token"
}
```

#### `POST /emails/fetch-with-token`
Fetch emails with JWT authentication.

**Request Body:**
```json
{
  "jwt_token": "user-jwt-token",
  "max_results": 10
}
```

### User Endpoints

#### `GET /me`
Get current user information.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

### AI Query Endpoints

#### `POST /test/mem0-query`
Query the AI memory agent.

**Request Body:**
```json
{
  "user_id": "user-id",
  "query": "your-question"
}
```

## WebSocket Support

The application includes WebSocket support for real-time communication. WebSocket routes are defined in `app/websocket.py`.

## Background Jobs

The application runs background jobs using APScheduler to:
- Automatically fetch new emails for users
- Process and analyze email content
- Update AI memory with new information

Jobs run every 2 minutes to check for new emails.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and routes
│   ├── auth.py          # JWT and authentication utilities
│   ├── oauth.py         # Google OAuth2 implementation
│   ├── gmail.py         # Gmail API integration
│   ├── db.py            # MongoDB connection and operations
│   ├── models.py        # Pydantic models
│   ├── mem0_agent.py    # AI memory agent integration
│   └── websocket.py     # WebSocket routes
├── requirements.txt     # Python dependencies
├── env.example         # Environment variables template
├── Dockerfile          # Docker configuration
└── README.md           # This file
```

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Environment Variables

All environment variables are documented in `env.example`. Make sure to:
- Use strong JWT secrets in production
- Secure your MongoDB connection
- Keep API keys confidential
- Configure proper CORS origins

### Logging

The application uses Python's built-in logging. Logs include:
- Authentication events
- Email fetch operations
- AI query processing
- Error handling

## Deployment

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t lifafa-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8001:8001 --env-file .env lifafa-backend
   ```

### Production Considerations

- Use a production WSGI server like Gunicorn
- Set up proper environment variable management
- Configure database connection pooling
- Implement rate limiting
- Set up monitoring and logging
- Use HTTPS in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please [create an issue](link-to-issues) in the repository.