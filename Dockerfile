# ============================================================================
# SACMES Web Application Dockerfile
# Based on UBI9 (Universal Base Image 9) for OpenShift compatibility
# ============================================================================

FROM registry.access.redhat.com/ubi9/python-39:latest

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp uploads directory
RUN mkdir -p temp_uploads && \
    chmod 755 temp_uploads

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=3)"

# Use gunicorn for production with gevent
# MIGRATED from eventlet to gevent for better performance and active maintenance
# Flask-SocketIO 5.x has built-in WebSocket support - no need for gevent-websocket
# --worker-class gevent: Plain gevent worker (Flask-SocketIO handles WebSocket upgrade)
# --workers 1: Single worker for diagnostic (will increase after testing)
# --worker-connections 1000: Max concurrent connections per worker
# --timeout 120: Request timeout (matches ping_timeout)
# --keep-alive 75: Keep-alive timeout
# --graceful-timeout 30: Graceful shutdown time
# --log-level info: Logging level
CMD ["gunicorn", \
     "--worker-class", "gevent", \
     "--workers", "1", \
     "--worker-connections", "1000", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--keep-alive", "75", \
     "--graceful-timeout", "30", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
