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

# Use gunicorn for production
# --worker-class eventlet: Required for Socket.IO with eventlet
# --workers 1: Single worker with eventlet (handles concurrency internally)
# --threads 4: Number of threads per worker
# --timeout 120: Request timeout (matches ping_timeout)
# --keep-alive 75: Keep-alive timeout
# --log-level info: Logging level
CMD ["gunicorn", \
     "--worker-class", "eventlet", \
     "--workers", "2", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--keep-alive", "75", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
