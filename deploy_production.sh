#!/bin/bash
# Production deployment script for Gmail Intelligence WebSocket server on EC2
# Run this script on your EC2 instance

set -e  # Exit on any error

echo "🚀 Gmail Intelligence WebSocket Server - Production Deployment"
echo "============================================================="

# Get current directory
PROJECT_DIR=$(pwd)
BACKEND_DIR="$PROJECT_DIR/backend"

echo "📂 Project Directory: $PROJECT_DIR"
echo "📂 Backend Directory: $BACKEND_DIR"

# Check if we're in the right directory
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Backend directory not found. Are you in the project root?"
    exit 1
fi

echo ""
echo "🔍 Step 1: Checking System Requirements"
echo "---------------------------------------"

# Check Python version
python3 --version || { echo "❌ Python 3 not found. Install Python 3.8+"; exit 1; }

# Check pip
pip3 --version || { echo "❌ pip3 not found. Install pip3"; exit 1; }

echo "✅ System requirements met"

echo ""
echo "📦 Step 2: Installing Dependencies"
echo "----------------------------------"

cd "$BACKEND_DIR"

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "✅ Dependencies installed"

echo ""
echo "🔧 Step 3: Environment Configuration"
echo "------------------------------------"

# Check for .env file
if [ ! -f "../.env" ]; then
    echo "⚠️  Warning: .env file not found in root directory"
    echo "   Please ensure your environment variables are set:"
    echo "   - OPENAI_API_KEY"
    echo "   - MEM0_API_KEY"
    echo "   - MONGODB_URL"
    echo "   - JWT_SECRET_KEY"
fi

echo ""
echo "🔥 Step 4: Stop Existing Server"
echo "-------------------------------"

# Kill existing Python processes (be careful!)
echo "Stopping existing server processes..."
pkill -f "uvicorn" || echo "No existing uvicorn processes found"
pkill -f "python.*main" || echo "No existing Python main processes found"

sleep 2

echo ""
echo "🚀 Step 5: Start WebSocket Server"
echo "---------------------------------"

# Set production environment variables
export HOST="0.0.0.0"
export PORT="8000"
export WORKERS="1"
export LOG_LEVEL="info"

echo "Starting server with configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  Log Level: $LOG_LEVEL"

# Start the server in background
nohup python3 start_production.py > ../websocket_server.log 2>&1 &
SERVER_PID=$!

echo "✅ Server started with PID: $SERVER_PID"
echo "📝 Logs are being written to: ../websocket_server.log"

echo ""
echo "⏳ Step 6: Health Check"
echo "----------------------"

# Wait a moment for server to start
sleep 5

# Test HTTP endpoint
echo "Testing HTTP endpoint..."
curl -s "http://localhost:8000/health" || { echo "❌ HTTP health check failed"; exit 1; }

echo ""
echo "Testing WebSocket health endpoint..."
curl -s "http://localhost:8000/websocket/health" || { echo "❌ WebSocket health check failed"; exit 1; }

echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "========================"
echo ""
echo "Your WebSocket server is running!"
echo ""
echo "📡 WebSocket Endpoints:"
echo "  - ws://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8000/ws/chat"
echo "  - ws://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8000/ws/chat/{chat_id}"
echo ""
echo "🌐 HTTP Endpoints:"
echo "  - http://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8000/health"
echo "  - http://ec2-13-127-58-101.ap-south-1.compute.amazonaws.com:8000/websocket/health"
echo ""
echo "📝 Monitor logs with: tail -f websocket_server.log"
echo "🔴 Stop server with: kill $SERVER_PID"
echo ""
echo "Next Steps:"
echo "1. Update your AWS Security Group to allow port 8000"
echo "2. Test WebSocket connection from your frontend"
echo "3. Monitor logs for any connection issues" 