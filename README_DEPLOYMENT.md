# SACMES Multi-User Deployment Guide

## Overview
This guide covers deploying SACMES Web Application with multi-user support, Redis session management, and parallel processing capabilities.

## Features Added
- ✅ Multi-user session isolation using Redis
- ✅ Parallel analysis processing for different electrodes
- ✅ Browser close confirmation with data export warning
- ✅ Automatic session cleanup when users disconnect
- ✅ OpenShift and Docker deployment support

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User 1        │    │                  │    │                 │
│   Session A     │◄──►│   SACMES Web     │◄──►│     Redis       │
│                 │    │   Application    │    │   Session Store │
├─────────────────┤    │                  │    │                 │
│   User 2        │    │  - Flask-SocketIO│    │ - Session Data  │
│   Session B     │◄──►│  - Background    │    │ - Analysis Data │
│                 │    │    Processing    │    │ - User State    │
├─────────────────┤    │  - Session Mgmt  │    │                 │
│   User N        │    │                  │    │                 │
│   Session N     │◄──►│                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start with Docker

### 1. Copy Environment Variables
```bash
cp docker/.env.example docker/.env
# Edit docker/.env with your secure passwords and tokens
```

### 2. Start Services
```bash
cd docker
docker-compose up -d
```

### 3. Access Application
- Web Interface: http://localhost:5000
- Redis: localhost:6379

## OpenShift Deployment

### Prerequisites
- OpenShift cluster access
- `oc` CLI tool installed

### Deploy using Template
```bash
# Create new project
oc new-project sacmes-web

# Process and apply template
oc process -f openshift-deployment.yaml \
  -p GIT_SOURCE_URL=https://github.com/your-repo/SACMES_Web-cv.git \
  -p GIT_SOURCE_REF=main \
  | oc apply -f -

# Check deployment status
oc get pods
oc get routes
```

### Configuration Parameters
- `APP_NAME`: Application name (default: sacmes-web)
- `GIT_SOURCE_URL`: Your Git repository URL
- `GIT_SOURCE_REF`: Git branch/tag (default: main)
- `REDIS_PASSWORD`: Auto-generated secure password
- `SECRET_KEY`: Auto-generated Flask secret key
- `AGENT_AUTH_TOKEN`: Auto-generated agent authentication token

## Environment Variables

### Required
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Flask session encryption key
- `AGENT_AUTH_TOKEN`: Token for local agent authentication

### Optional
- `FLASK_ENV`: Set to 'development' for debug mode
- `LOG_LEVEL`: Logging level (INFO, DEBUG, ERROR)

## Session Management

### How It Works
1. Each user gets a unique session ID when they connect
2. All analysis data is stored per-session in Redis
3. Multiple users can run analyses simultaneously without interference
4. Sessions auto-cleanup after 5 minutes of inactivity

### Session Data Structure
```python
session:{session_id} = {
    'agent_sid': 'socket_id',
    'web_viewer_sids': ['sid1', 'sid2'],
    'live_analysis_params': {...},
    'live_trend_data': {...},
    'live_peak_detection_warnings': {...},
    'validation_error_sent': False
}
```

## Multi-User Features

### Parallel Analysis
- Each electrode can be processed in parallel background tasks
- Users don't block each other's analyses
- Redis ensures data isolation between sessions

### Data Export Warning
- Browser shows confirmation dialog when closing with unsaved data
- Automatic session cleanup via beacon API
- Data is not persisted after user disconnects

### Session Cleanup
- Automatic cleanup after 5 minutes of no activity
- Manual cleanup when user closes browser
- Cleanup endpoint: `POST /cleanup-session`

## Monitoring and Logging

### Application Logs
```bash
# Docker
docker-compose logs -f sacmes-web

# OpenShift
oc logs deployment/sacmes-web -f
```

### Redis Monitoring
```bash
# Connect to Redis
redis-cli -h localhost -p 6379 -a your_password

# Monitor commands
MONITOR
INFO memory
KEYS session:*
```

## Scaling

### Horizontal Pod Autoscaler (OpenShift)
```yaml
minReplicas: 2
maxReplicas: 10
metrics:
  - CPU: 70%
  - Memory: 80%
```

### Load Balancing
- Multiple app instances can run simultaneously
- Redis handles session sharing between instances
- WebSocket connections use sticky sessions

## Security Considerations

### Production Checklist
- [ ] Change all default passwords and tokens
- [ ] Enable HTTPS/TLS encryption
- [ ] Use Redis AUTH password
- [ ] Set up proper firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates

### Redis Security
```bash
# Set strong password
CONFIG SET requirepass "your_very_strong_password"

# Disable dangerous commands
CONFIG SET rename-command FLUSHDB ""
CONFIG SET rename-command FLUSHALL ""
```

## Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Check Redis is running
docker-compose ps redis
oc get pods -l component=redis

# Check Redis logs
docker-compose logs redis
oc logs deployment/sacmes-web-redis
```

#### Session Data Lost
- Check Redis memory usage: `INFO memory`
- Verify Redis persistence settings
- Check if maxmemory-policy is appropriate

#### WebSocket Connection Issues
- Verify CORS settings in app.py
- Check if proxy preserves WebSocket headers
- Ensure sticky sessions for load balancers

### Debug Mode
```bash
# Enable debug logging
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
```

## Performance Tuning

### Redis Optimization
```bash
# Memory optimization
maxmemory 256mb
maxmemory-policy allkeys-lru

# Network optimization
tcp-keepalive 60
timeout 300
```

### Application Optimization
- Increase worker processes for CPU-bound tasks
- Use connection pooling for Redis
- Implement caching for static analysis results

## Backup and Recovery

### Redis Backup
```bash
# Create backup
redis-cli -h localhost -p 6379 -a password --rdb backup.rdb

# Restore backup
cp backup.rdb /data/dump.rdb
docker-compose restart redis
```

### Application Data
- Analysis results are ephemeral (session-based)
- Export functionality provides user data backup
- No persistent storage needed for application state

## Support and Maintenance

### Health Checks
- Application: `GET /` (200 OK)
- Redis: `redis-cli ping` (PONG)

### Maintenance Tasks
- Regular Redis memory cleanup
- Log rotation and archival
- Security patches and updates
- Performance monitoring and optimization

For additional support, consult the main SACMES documentation or contact the development team.