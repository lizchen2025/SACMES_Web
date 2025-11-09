#!/bin/bash
# MIGRATED from eventlet to gevent for better performance
# Flask-SocketIO 5.x has built-in WebSocket support with gevent worker
# REMOVED geventwebsocket.gunicorn.workers.GeventWebSocketWorker (unmaintained, has fragmentation bugs)
# Using plain 'gevent' worker - Flask-SocketIO handles WebSocket upgrade natively
gunicorn --worker-class gevent \
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