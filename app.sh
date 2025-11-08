#!/bin/bash
# MIGRATED from eventlet to gevent for better performance
gunicorn --worker-class gevent \
         --workers 2 \
         --worker-connections 1000 \
         --bind 0.0.0.0:${PORT:-8080} \
         --timeout 120 \
         --keep-alive 75 \
         --graceful-timeout 30 \
         --log-level info \
         --access-logfile - \
         --error-logfile - \
         wsgi:app