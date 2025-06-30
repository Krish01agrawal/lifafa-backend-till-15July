# ============================================================================
# Gmail Intelligence Platform - Makefile
# ============================================================================
# Common operations for development and deployment

.PHONY: help build run dev stop clean setup test logs health

# Default target
help:
	@echo "🚀 Gmail Intelligence Platform - Available Commands:"
	@echo ""
	@echo "📦 Docker Operations:"
	@echo "  make build         - Build Docker image"
	@echo "  make run           - Run with Docker Compose"
	@echo "  make run-dev       - Run with development profile"
	@echo "  make run-prod      - Run with production profile"
	@echo "  make stop          - Stop all services"
	@echo "  make logs          - View logs"
	@echo "  make clean         - Clean Docker images and volumes"
	@echo ""
	@echo "💻 Development:"
	@echo "  make setup         - Setup development environment"
	@echo "  make dev           - Run development server (local)"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run code linting"
	@echo ""
	@echo "🔍 Monitoring:"
	@echo "  make health        - Check application health"
	@echo "  make mongo-cli     - Connect to MongoDB shell"
	@echo "  make redis-cli     - Connect to Redis shell"
	@echo ""
	@echo "🛠️ Utilities:"
	@echo "  make env           - Create .env from template"
	@echo "  make backup        - Backup database"
	@echo "  make restore       - Restore database"

# ============================================================================
# DOCKER OPERATIONS
# ============================================================================

build:
	@echo "🔨 Building Gmail Intelligence Docker image..."
	docker build -t gmail-intelligence:latest .

run: env-check
	@echo "🚀 Starting Gmail Intelligence with Docker Compose..."
	docker-compose up -d
	@echo "✅ Services started. Check http://localhost:8000/health"

run-dev: env-check
	@echo "🔧 Starting development environment..."
	docker-compose --profile development up -d
	@echo "✅ Development services started:"
	@echo "   - API: http://localhost:8000/docs"
	@echo "   - MongoDB UI: http://localhost:8081"

run-prod: env-check
	@echo "🌟 Starting production environment..."
	docker-compose --profile production up -d
	@echo "✅ Production services started with Nginx load balancer"

stop:
	@echo "🛑 Stopping all services..."
	docker-compose down

logs:
	@echo "📋 Viewing logs..."
	docker-compose logs -f gmail-intelligence

clean:
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# ============================================================================
# DEVELOPMENT SETUP
# ============================================================================

setup: env
	@echo "🔧 Setting up development environment..."
	@if [ ! -d "backend/venv" ]; then \
		echo "Creating Python virtual environment..."; \
		cd backend && python -m venv venv; \
	fi
	@echo "Installing Python dependencies..."
	cd backend && source venv/bin/activate && pip install -r requirements.txt
	@echo "Installing Playwright browsers..."
	cd backend && source venv/bin/activate && playwright install chromium
	@echo "✅ Development setup complete!"
	@echo "📝 Next steps:"
	@echo "   1. Edit .env with your API keys"
	@echo "   2. Run: make dev"

dev: env-check
	@echo "🔧 Starting development server..."
	cd backend && source venv/bin/activate && \
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "🧪 Running tests..."
	cd backend && source venv/bin/activate && python -m pytest -v

lint:
	@echo "🔍 Running code linting..."
	cd backend && source venv/bin/activate && \
	flake8 app/ --max-line-length=120 --ignore=E501,W503

# ============================================================================
# MONITORING & HEALTH
# ============================================================================

health:
	@echo "🔍 Checking application health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Service not responding"

mongo-cli:
	@echo "🗄️ Connecting to MongoDB shell..."
	docker-compose exec mongodb mongosh gmail_intelligence

redis-cli:
	@echo "🔴 Connecting to Redis shell..."
	docker-compose exec redis redis-cli

# ============================================================================
# UTILITIES
# ============================================================================

env:
	@if [ ! -f .env ]; then \
		echo "📋 Creating .env file from template..."; \
		cp backend/env.example .env; \
		echo "✅ .env created. Please edit it with your API keys."; \
		echo "📝 Required keys:"; \
		echo "   - OPENAI_API_KEY"; \
		echo "   - MEM0_API_KEY"; \
		echo "   - GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET"; \
		echo "   - JWT_SECRET"; \
		echo "   - MONGODB_URL (or use Docker MongoDB)"; \
	else \
		echo "✅ .env file already exists"; \
	fi

env-check:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make env' first."; \
		exit 1; \
	fi

backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	docker-compose exec mongodb mongodump --db gmail_intelligence --out /tmp/backup
	docker cp $$(docker-compose ps -q mongodb):/tmp/backup backups/mongodb-$$(date +%Y%m%d-%H%M%S)
	@echo "✅ Backup created in backups/ directory"

restore:
	@echo "🔄 Restoring database..."
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "❌ Please specify backup directory: make restore BACKUP_DIR=backups/mongodb-20240115-120000"; \
		exit 1; \
	fi
	docker cp $(BACKUP_DIR) $$(docker-compose ps -q mongodb):/tmp/restore
	docker-compose exec mongodb mongorestore --db gmail_intelligence /tmp/restore/gmail_intelligence --drop
	@echo "✅ Database restored"

# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

deploy:
	@echo "🚀 Deploying to production..."
	@./deploy_production.sh

ssl-setup:
	@echo "🔒 Setting up SSL certificates..."
	@mkdir -p ssl
	@echo "Please place your SSL certificates in the ssl/ directory:"
	@echo "  - ssl/cert.pem (certificate)"
	@echo "  - ssl/key.pem (private key)"

# ============================================================================
# DOCKER COMPOSE SHORTCUTS
# ============================================================================

up: run
down: stop
restart: stop run
rebuild: clean build run

# ============================================================================
# HELP TEXT
# ============================================================================

docker-help:
	@echo "🐳 Docker Commands Quick Reference:"
	@echo ""
	@echo "Basic Usage:"
	@echo "  make build && make run     # Build and start services"
	@echo "  make logs                  # View application logs"
	@echo "  make stop                  # Stop all services"
	@echo ""
	@echo "Development:"
	@echo "  make run-dev              # Start with MongoDB admin UI"
	@echo "  make mongo-cli            # Access MongoDB shell"
	@echo ""
	@echo "Production:"
	@echo "  make run-prod             # Start with Nginx load balancer"
	@echo "  make ssl-setup            # Setup SSL certificates"

# ============================================================================
# ENVIRONMENT INFO
# ============================================================================

info:
	@echo "📊 Gmail Intelligence Platform Info:"
	@echo "   Version: 1.3.0"
	@echo "   Python: $$(python --version 2>/dev/null || echo 'Not installed')"
	@echo "   Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "   Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"
	@echo ""
	@echo "📁 Project Structure:"
	@echo "   - backend/     FastAPI application"
	@echo "   - frontend/    Web interface"
	@echo "   - scripts/     Database initialization"
	@echo "   - .env         Environment configuration"
	@echo ""
	@if [ -f .env ]; then \
		echo "✅ Environment file exists"; \
	else \
		echo "❌ Environment file missing (run 'make env')"; \
	fi 