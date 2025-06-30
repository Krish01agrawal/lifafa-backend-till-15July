# ============================================================================
# Gmail Intelligence Backend - Production Dockerfile
# ============================================================================
# Multi-stage build for optimized production image
# Supports all advanced financial features including PDF processing, 
# browser automation, and AI services

FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHONUNBUFFERED=1
ARG PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ============================================================================
# Production Stage
# ============================================================================
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/backend"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    # Core system dependencies
    curl \
    wget \
    ca-certificates \
    gnupg \
    # PDF processing dependencies (for statement_processor.py)
    ghostscript \
    poppler-utils \
    # Browser automation dependencies (for browser_automation_service.py)
    chromium \
    chromium-driver \
    # Image processing dependencies
    libjpeg62-turbo \
    libpng16-16 \
    # XML/HTML processing
    libxml2 \
    libxslt1.1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Playwright browsers (for browser automation)
RUN python -m pip install playwright==1.42.0 \
    && playwright install chromium \
    && playwright install-deps chromium

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directories
RUN mkdir -p /app /app/logs /app/data /app/temp \
    && chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser frontend/ /app/frontend/
COPY --chown=appuser:appuser .env /app/.env
COPY --chown=appuser:appuser deploy_production.sh /app/
COPY --chown=appuser:appuser production_nginx.conf /app/

# Copy additional financial processing scripts
COPY --chown=appuser:appuser financial_*.py /app/
COPY --chown=appuser:appuser process_financial_*.py /app/
COPY --chown=appuser:appuser query_analyzer_agent.py /app/

# Create startup script
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Gmail Intelligence Backend..."
echo "📊 Version: 1.3.0"
echo "🐍 Python: $(python --version)"
echo "⚡ FastAPI: $(python -c 'import fastapi; print(fastapi.__version__)')"

# Validate environment variables
if [ -z "$MONGODB_URL" ]; then
    echo "❌ ERROR: MONGODB_URL is required"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is required"
    exit 1
fi

if [ -z "$MEM0_API_KEY" ]; then
    echo "❌ ERROR: MEM0_API_KEY is required"
    exit 1
fi

echo "✅ Environment validation passed"

# Health check
echo "🔍 Running health check..."
python -c "
import sys
sys.path.append('/app/backend')
try:
    from app.config.settings import get_settings
    settings = get_settings()
    print('✅ Configuration loaded successfully')
    print(f'📍 App: {settings.app_name} v{settings.app_version}')
    print(f'🌍 Environment: {settings.environment}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

# Start the application
echo "🌟 Starting FastAPI server..."
cd /app/backend
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-log \
    --log-level ${LOG_LEVEL:-info}
EOF

RUN chmod +x /app/start.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Expose port
EXPOSE 8000

# Set default command
CMD ["/app/start.sh"]

# ============================================================================
# METADATA
# ============================================================================
LABEL maintainer="Gmail Intelligence Team"
LABEL description="Gmail Intelligence Backend with Advanced Financial Features"
LABEL version="1.3.0"
LABEL org.opencontainers.image.title="Gmail Intelligence Backend"
LABEL org.opencontainers.image.description="Comprehensive financial intelligence platform with Gmail integration"
LABEL org.opencontainers.image.version="1.3.0"
LABEL org.opencontainers.image.vendor="Gmail Intelligence"

# ============================================================================
# VOLUME DEFINITIONS
# ============================================================================
# Persistent data volumes
VOLUME ["/app/data", "/app/logs"]

# ============================================================================
# BUILD INSTRUCTIONS
# ============================================================================
# To build: docker build -t gmail-intelligence:latest .
# To run: docker run -p 8000:8000 --env-file .env gmail-intelligence:latest
# With volumes: docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data gmail-intelligence:latest 