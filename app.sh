#!/bin/bash
# MIGRATED from eventlet to gevent for better performance
# Use geventwebsocket.gunicorn.workers.GeventWebSocketWorker for WebSocket support
# TEMPORARY: Use 1 worker to diagnose multi-worker communication issues
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --workers 1 \
         --worker-connections 1000 \
         --bind 0.0.0.0:${PORT:-8080} \
         --timeout 120 \
         --keep-alive 75 \
         --graceful-timeout 30 \
         --log-level debug \
         --access-logfile - \
         --error-logfile - \
         wsgi:app