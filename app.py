# app.py (Version with CSV Export Functionality)
# MIGRATED TO GEVENT for better performance and active maintenance

import gevent
from gevent.lock import Semaphore

# CRITICAL: Monkey patch must happen before importing other libraries
# Check if already patched by gunicorn gevent worker to avoid duplicate patching warning
if not gevent.monkey.is_module_patched('socket'):
    gevent.monkey.patch_all(
        thread=False,  # Don't patch threading to preserve better stack traces
        sys=False      # Don't patch sys to preserve better debugging
    )

# CRITICAL FIX: Patch socket to ignore "Bad file descriptor" errors
# This prevents server blocking when clients abruptly disconnect
# Note: gevent's socket handling is more robust than eventlet, but we keep this as defense-in-depth
import errno
_original_socket_shutdown = None

def patched_socket_shutdown(sock, how):
    """Wrapper for socket.shutdown() that ignores EBADF (Bad file descriptor) errors"""
    try:
        return _original_socket_shutdown(sock, how)
    except OSError as e:
        if e.errno == errno.EBADF:  # Bad file descriptor - client already closed
            pass  # Ignore this benign error (less common in gevent than eventlet)
        else:
            raise  # Re-raise other errors

# Apply the patch
try:
    from gevent import socket as gevent_socket
    if hasattr(gevent_socket.socket, 'shutdown'):
        _original_socket_shutdown = gevent_socket.socket.shutdown
        gevent_socket.socket.shutdown = lambda self, how: patched_socket_shutdown(self._sock if hasattr(self, '_sock') else self, how)
except Exception as patch_error:
    # If patching fails, continue without it (better than crashing)
    import sys
    print(f"Warning: Could not patch socket.shutdown: {patch_error}", file=sys.stderr)

import os
import re
import logging
import sys
import io
import csv
import uuid
import redis
import json
import threading
import socket
import time
import numpy as np
from datetime import datetime
from flask import Flask, send_from_directory, request, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

# --- Logging Setup (Unchanged) ---
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.propagate = False

try:
    from data_processing.swv_analyzer import analyze_swv_data
    from data_processing.cv_analyzer import analyze_cv_data, get_cv_segments

    logger.info("Successfully imported swv_analyzer and cv_analyzer.")
except ImportError as e:
    logger.critical(f"FATAL: Failed to import analyzers: {e}")
    analyze_swv_data = None
    analyze_cv_data = None
    get_cv_segments = None

# --- File Safety Validation Functions ---
def validate_file_safety(filename, content):
    """
    Perform efficient safety checks on uploaded files.
    Returns (is_safe: bool, error_message: str)
    """
    # 1. File extension validation (most efficient - check first)
    allowed_extensions = {'.txt', '.dta', '.csv'}
    file_ext = os.path.splitext(filename.lower())[1]
    if file_ext not in allowed_extensions:
        return False, f"File extension '{file_ext}' not allowed. Only .txt, .dta, .csv files are accepted."

    # 2. File size validation (check content length)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    content_size = len(content.encode('utf-8'))
    if content_size > MAX_FILE_SIZE:
        return False, f"File size ({content_size / 1024 / 1024:.1f}MB) exceeds 5MB limit."

    # 3. Efficient content validation (sample-based for performance)
    if not validate_content_safety(content):
        return False, "File contains binary or suspicious content. Only text-based data files are allowed."

    return True, ""

def validate_content_safety(content, sample_size=2048):
    """
    Efficiently validate content is text-based and safe.
    Uses sampling for large files to maintain performance.
    """
    # Sample beginning and end of file for efficiency
    if len(content) <= sample_size:
        sample = content
    else:
        # Sample first 1KB and last 1KB
        half_sample = sample_size // 2
        sample = content[:half_sample] + content[-half_sample:]

    # Check for binary content (null bytes and excessive non-printable chars)
    if '\x00' in sample:
        return False

    # Count non-printable characters (excluding common whitespace)
    printable_count = 0
    for char in sample:
        if char.isprintable() or char in '\n\r\t':
            printable_count += 1

    # If more than 20% non-printable, likely binary
    if len(sample) > 0 and (printable_count / len(sample)) < 0.8:
        return False

    # Check for suspicious patterns (basic security patterns)
    suspicious_patterns = [
        b'\x7fELF',  # ELF binary
        b'MZ',       # Windows executable
        b'\xff\xd8\xff',  # JPEG
        b'\x89PNG',  # PNG
        b'PK\x03\x04',    # ZIP
        b'\xd0\xcf\x11\xe0',  # MS Office
    ]

    content_bytes = sample.encode('utf-8', errors='ignore')
    for pattern in suspicious_patterns:
        if pattern in content_bytes:
            return False

    return True

# --- Helper function to read secrets ---
def read_secret(secret_name, fallback_env_var=None, default_value=None):
    """Read secret from file or environment variable"""
    # Try to read from Docker secret file first
    secret_file = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_file):
        try:
            with open(secret_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not read secret file {secret_file}: {e}")

    # Try environment variable with _FILE suffix
    env_file_var = f"{secret_name.upper()}_FILE"
    if env_file_var in os.environ:
        try:
            with open(os.environ[env_file_var], 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not read secret file from {env_file_var}: {e}")

    # Fallback to regular environment variable
    if fallback_env_var and fallback_env_var in os.environ:
        return os.environ[fallback_env_var]

    # Return default value
    return default_value

# --- App Setup with Redis Session Management ---
app = Flask(__name__, static_folder='static', static_url_path='')

# Read secrets securely
SECRET_KEY = read_secret('secret_key', 'SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
REDIS_PASSWORD = read_secret('redis_password', 'REDIS_PASSWORD')
AGENT_AUTH_TOKEN = read_secret('agent_auth_token', 'AGENT_AUTH_TOKEN', 'your_super_secret_token_here')

app.config['SECRET_KEY'] = SECRET_KEY

# Redis connection - construct URL securely BEFORE SocketIO initialization
# This is required for message_queue configuration in multi-pod deployments

# Strategy: Build Redis URL from components (REDIS_HOST, REDIS_PORT, REDIS_DB)
# Only use REDIS_URL environment variable if it's explicitly a valid redis:// URL
# This prevents issues with auto-injected Kubernetes service URLs

def build_redis_url():
    """Build Redis URL from environment variables with robust error handling"""
    # Check if REDIS_URL is explicitly set and valid
    env_redis_url = os.environ.get('REDIS_URL', '').strip()

    # Only use REDIS_URL if it looks like a valid redis:// URL
    if env_redis_url and env_redis_url.startswith('redis://') and ':tcp:' not in env_redis_url:
        logger.info(f"Using REDIS_URL from environment: {env_redis_url.split('@')[-1] if '@' in env_redis_url else env_redis_url}")
        return env_redis_url

    # Build URL from components (preferred method)
    # Smart default: use 'redis' in Kubernetes/OpenShift, 'localhost' otherwise
    default_host = 'redis' if os.environ.get('KUBERNETES_SERVICE_HOST') else 'localhost'

    redis_host = os.environ.get('REDIS_HOST', '').strip()
    if not redis_host:
        redis_host = default_host
        logger.warning(f"REDIS_HOST not set, using default: {default_host}")

    redis_port = os.environ.get('REDIS_PORT', '6379')
    redis_db = os.environ.get('REDIS_DB', '0')

    # Validate port is numeric
    try:
        int(redis_port)
    except ValueError:
        logger.error(f"Invalid REDIS_PORT: {redis_port}, using default 6379")
        redis_port = '6379'

    # Build URL based on whether password is set
    if REDIS_PASSWORD:
        redis_url = f"redis://:{REDIS_PASSWORD}@{redis_host}:{redis_port}/{redis_db}"
        logger.info(f"Redis URL configured with password: redis://***@{redis_host}:{redis_port}/{redis_db}")
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        logger.info(f"Redis URL configured: redis://{redis_host}:{redis_port}/{redis_db}")

    return redis_url

REDIS_URL = build_redis_url()

# Extract components for connection pool (needed below)
# Use the same smart default as build_redis_url()
default_host = 'redis' if os.environ.get('KUBERNETES_SERVICE_HOST') else 'localhost'
REDIS_HOST = os.environ.get('REDIS_HOST', '').strip() or default_host
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')
logger.info(f"Redis connection pool will use: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Enhanced SocketIO configuration for OpenShift deployment
# DIAGNOSTIC: Temporarily disable message_queue for single-worker testing
# Redis message queue can cause serialization issues with large payloads
socketio = SocketIO(
    app,

    # DIAGNOSTIC: Disable Redis message queue in single-worker mode
    # When workers=1, message queue is unnecessary and may cause issues
    # Enables communication between multiple Flask app pods in OpenShift
    # message_queue=REDIS_URL,  # TEMPORARILY DISABLED FOR TESTING

    cors_allowed_origins="*",
    async_mode='gevent',  # MIGRATED from eventlet: gevent provides faster libev-based event loop
    logger=True,
    engineio_logger=False,  # Disable verbose engine.io logging to hide benign "Bad file descriptor" errors during socket cleanup

    # CRITICAL FIX: Enable async handlers to prevent blocking on large messages
    async_handlers=True,  # Allow gevent to handle large messages asynchronously

    # CRITICAL FIX: Disable http compression to prevent issues with large messages
    http_compression=False,  # Compression can cause issues with websocket frames

    # OpenShift-optimized settings to prevent disconnections during heavy file transfers
    ping_timeout=120,       # Increased to 120s for bulk file uploads (was 60s)
    ping_interval=25,       # More frequent heartbeats (default: 25s)

    # Prevent disconnections during processing
    allow_upgrades=True,
    max_http_buffer_size=10000000,  # 10MB for large CV data files

    # Transport optimization for container environments
    transports=['websocket', 'polling']
)
logger.info("SocketIO initialized WITHOUT message queue for single-worker diagnostic")

# Create connection pool with optimized settings for multi-user deployment
try:
    # Build keepalive options with cross-platform compatibility
    keepalive_options = {}
    if hasattr(socket, 'TCP_KEEPIDLE'):
        keepalive_options[socket.TCP_KEEPIDLE] = 60
    if hasattr(socket, 'TCP_KEEPINTVL'):
        keepalive_options[socket.TCP_KEEPINTVL] = 10
    if hasattr(socket, 'TCP_KEEPCNT'):
        keepalive_options[socket.TCP_KEEPCNT] = 3

    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        db=int(REDIS_DB),
        password=REDIS_PASSWORD,
        max_connections=50,           # Limit connections for 10-user concurrent scenario
        socket_timeout=5,             # 5 second timeout for operations
        socket_connect_timeout=2,     # 2 second timeout for initial connection
        socket_keepalive=True,        # Enable TCP keepalive
        socket_keepalive_options=keepalive_options if keepalive_options else None,
        retry_on_timeout=True,        # Auto retry on timeout
        decode_responses=True
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    redis_client.ping()  # Test connection
    logger.info(f"Successfully connected to Redis with connection pool (max_connections=50)")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Session management - now using Redis instead of global variables
session_lock = threading.Lock()
active_sessions = {}  # {session_id: {'agent_sid': sid, 'web_viewer_sids': set(), ...}}

# Global fallback for when Redis is not available
# Changed to per-session storage to prevent data pollution between users
fallback_data = {}  # {session_id: {'agent_sid': None, 'web_viewer_sids': set(), ...}}

# Concurrency control - limit simultaneous file processing tasks
# This prevents memory/CPU overload when multiple users upload files simultaneously
# TUNING: Optimized for gevent with CPU-intensive numpy/scipy analysis
# gevent handles CPU tasks better than eventlet, but we still limit concurrency
# - 20: Conservative (2 workers × 10 tasks) - prevents worker blocking during heavy analysis
# - 40: Balanced (2 workers × 20 tasks) - good for most deployments with gevent
# - 60: High throughput (2 workers × 30 tasks) - if resources abundant and analysis is fast
MAX_CONCURRENT_FILE_TASKS = 20  # OPTIMIZED: Conservative limit to ensure stable ping/pong
file_processing_semaphore = Semaphore(MAX_CONCURRENT_FILE_TASKS)
logger.info(f"File processing concurrency limit set to {MAX_CONCURRENT_FILE_TASKS}")

# Flow control - track agent sending rates
# {user_id: {'current_interval': 0.1, 'last_adjusted': timestamp}}
agent_rate_tracking = {}

# Flow control thresholds
LOAD_THRESHOLD_HIGH = 0.80  # 80% capacity - slow down agents
LOAD_THRESHOLD_LOW = 0.30   # 30% capacity - allow agents to speed up
RATE_SLOW = 0.1    # 10 files/sec when under load
RATE_NORMAL = 0.05  # 20 files/sec normal operation
RATE_CHECK_INTERVAL = 2.0  # Don't adjust same agent more than once per 2 seconds

def check_and_adjust_agent_rate(user_id, agent_sid):
    """
    Monitor server load and adjust agent sending rate if needed.
    Called each time agent sends a file.
    """
    try:
        # Calculate current load
        available_slots = file_processing_semaphore.balance
        used_slots = MAX_CONCURRENT_FILE_TASKS - available_slots
        load_ratio = used_slots / MAX_CONCURRENT_FILE_TASKS

        # Get agent's current rate settings
        if user_id not in agent_rate_tracking:
            agent_rate_tracking[user_id] = {
                'current_interval': RATE_NORMAL,
                'last_adjusted': 0
            }

        current_time = time.time()
        agent_info = agent_rate_tracking[user_id]
        time_since_adjust = current_time - agent_info['last_adjusted']

        # Periodic load monitoring (every 5 seconds per agent)
        if time_since_adjust > 5.0:
            logger.info(f"[LOAD] Server load: {load_ratio*100:.0f}% ({used_slots}/{MAX_CONCURRENT_FILE_TASKS} slots), agent {user_id} rate: {1/agent_info['current_interval']:.1f} files/sec")

        # Avoid adjusting too frequently
        if time_since_adjust < RATE_CHECK_INTERVAL:
            return

        # Determine if adjustment is needed
        should_slow_down = (load_ratio > LOAD_THRESHOLD_HIGH and
                           agent_info['current_interval'] < RATE_SLOW)
        should_speed_up = (load_ratio < LOAD_THRESHOLD_LOW and
                          agent_info['current_interval'] > RATE_NORMAL)

        if should_slow_down:
            # Server is under load, slow down this agent
            new_interval = RATE_SLOW
            reason = f"server load high ({load_ratio*100:.0f}% capacity)"
            logger.info(f"[FLOW CONTROL] Slowing down agent {user_id}: {load_ratio*100:.0f}% load")

            try:
                socketio.emit('adjust_send_rate', {
                    'interval': new_interval,
                    'reason': reason
                }, to=agent_sid)
                logger.debug(f"[FLOW CONTROL] Successfully sent rate adjustment to agent {agent_sid}")
            except Exception as emit_error:
                logger.error(f"[FLOW CONTROL] Failed to send rate adjustment to agent {agent_sid}: {emit_error}")
                # Don't update tracking if emit failed
                return

            agent_info['current_interval'] = new_interval
            agent_info['last_adjusted'] = current_time

        elif should_speed_up:
            # Server load is low, allow agent to speed up
            new_interval = RATE_NORMAL
            reason = f"server load normal ({load_ratio*100:.0f}% capacity)"
            logger.info(f"[FLOW CONTROL] Speeding up agent {user_id}: {load_ratio*100:.0f}% load")

            try:
                socketio.emit('adjust_send_rate', {
                    'interval': new_interval,
                    'reason': reason
                }, to=agent_sid)
                logger.debug(f"[FLOW CONTROL] Successfully sent rate adjustment to agent {agent_sid}")
            except Exception as emit_error:
                logger.error(f"[FLOW CONTROL] Failed to send rate adjustment to agent {agent_sid}: {emit_error}")
                # Don't update tracking if emit failed
                return

            agent_info['current_interval'] = new_interval
            agent_info['last_adjusted'] = current_time

    except Exception as e:
        logger.error(f"Error in flow control adjustment: {e}")

# --- Session Management Helper Functions ---
def get_session_id():
    """Get or create a session ID for the current user"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def get_session_data(session_id, key, default=None):
    """Get session-specific data from Redis or fallback"""
    if redis_client:
        try:
            data = redis_client.hget(f"session:{session_id}", key)
            if data:
                return json.loads(data)
            return default
        except Exception as e:
            logger.error(f"Redis get error for session {session_id}, key {key}: {e}")

    # Fallback to in-memory storage (per-session)
    with session_lock:
        if session_id not in fallback_data:
            fallback_data[session_id] = {}
        return fallback_data[session_id].get(key, default)

def set_session_data(session_id, key, value):
    """Set session-specific data in Redis or fallback"""
    if redis_client:
        try:
            redis_client.hset(f"session:{session_id}", key, json.dumps(value, default=str))
            # Extended expiry for large analyses: 48 hours
            # This prevents session loss during long-running analyses (500+ files)
            redis_client.expire(f"session:{session_id}", 172800)  # 48 hour expiry (was 24h)
            return True
        except Exception as e:
            logger.error(f"Redis set error for session {session_id}, key {key}: {e}")

    # Fallback to in-memory storage (per-session)
    with session_lock:
        if session_id not in fallback_data:
            fallback_data[session_id] = {}
        fallback_data[session_id][key] = value
    return False

def clear_session_data(session_id):
    """Clear all session data"""
    if redis_client:
        try:
            redis_client.delete(f"session:{session_id}")
            logger.info(f"Cleared Redis data for session {session_id}")
        except Exception as e:
            logger.error(f"Redis clear error for session {session_id}: {e}")

    # Clear from active sessions
    with session_lock:
        if session_id in active_sessions:
            del active_sessions[session_id]

        # Clear fallback data for this specific session only
        if session_id in fallback_data:
            del fallback_data[session_id]

def get_real_client_ip():
    """Get real client IP address, considering proxies and load balancers"""
    # Check X-Forwarded-For header (most common for proxies/load balancers)
    if 'X-Forwarded-For' in request.headers:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # The first IP is usually the original client
        forwarded_ips = request.headers['X-Forwarded-For'].split(',')
        return forwarded_ips[0].strip()

    # Check X-Real-IP header (used by some proxies like nginx)
    if 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP'].strip()

    # Check X-Original-Forwarded-For (used by some cloud services)
    if 'X-Original-Forwarded-For' in request.headers:
        return request.headers['X-Original-Forwarded-For'].strip()

    # Fallback to direct connection IP
    return request.remote_addr

def log_consent(user_id, user_ip=None, session_id=None):
    """Log user consent with user ID, session ID and timestamp"""
    try:
        timestamp = datetime.now().isoformat()
        consent_record = {
            'user_id': user_id,
            'session_id': session_id or 'unknown',
            'timestamp': timestamp,
            'user_ip': user_ip or 'unknown'
        }

        logger.info(f"LOGGING CONSENT RECORD: {consent_record}")

        # Store in Redis if available
        if redis_client:
            try:
                logger.info("Attempting to write to Redis...")
                redis_client.lpush('consent_log', json.dumps(consent_record))
                redis_client.ltrim('consent_log', 0, 9999)  # Keep last 10,000 records
                logger.info(f"✓ Successfully logged consent to Redis for user {user_id}")

                # Verify the data was stored
                list_length = redis_client.llen('consent_log')
                logger.info(f"✓ Redis consent_log now has {list_length} entries")

                # Debug: Show the latest entry to verify it was stored correctly
                if list_length > 0:
                    latest_entry = redis_client.lindex('consent_log', 0)
                    logger.info(f"Latest consent entry: {latest_entry}")

                return True
            except Exception as e:
                logger.error(f"✗ Failed to log consent to Redis: {e}")

        # Fallback to file logging
        logger.info("Redis not available, using file logging...")
        try:
            with open('consent_log.txt', 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(consent_record)}\n")
            logger.info(f"✓ Consent logged to file for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to log consent to file: {e}")
            return False

    except Exception as e:
        logger.error(f"Error logging consent: {e}")
        return False

def get_session_agent_sid(session_id):
    """Get agent SID for a session"""
    return get_session_data(session_id, 'agent_sid')

def set_session_agent_sid(session_id, agent_sid):
    """Set agent SID for a session"""
    set_session_data(session_id, 'agent_sid', agent_sid)

def get_current_agent_sid(user_id=None, session_id=None):
    """
    CRITICAL FIX: Get current agent SID, resilient to reconnections.

    Background tasks use this to send ACKs. If agent reconnects to a new session
    during processing, we need to find the NEW SID, not the old session's (now-None) SID.

    Priority:
    1. If user_id provided: lookup current SID via user_id mapping (survives reconnect)
    2. Fallback to session_id: lookup SID via session (fails if agent reconnected)

    Args:
        user_id: User ID from agent registration
        session_id: Session ID (may be stale if agent reconnected)

    Returns:
        Agent SID string or None if agent not found
    """
    # Priority 1: Use user_id to find CURRENT agent SID (survives reconnection)
    if user_id:
        agent_mapping = get_agent_session_by_user_id(user_id)
        if agent_mapping:
            agent_sid = agent_mapping.get('agent_sid')
            if agent_sid:
                logger.debug(f"get_current_agent_sid: Found via user_id={user_id} → SID={agent_sid}")
                return agent_sid
        logger.debug(f"get_current_agent_sid: No agent found for user_id={user_id}")

    # Priority 2: Fallback to session_id (may return None if agent reconnected to new session)
    if session_id:
        agent_sid = get_session_agent_sid(session_id)
        if agent_sid:
            logger.debug(f"get_current_agent_sid: Found via session_id={session_id} → SID={agent_sid}")
            return agent_sid
        logger.debug(f"get_current_agent_sid: No agent_sid in session {session_id} (agent may have reconnected)")

    logger.warning(f"get_current_agent_sid: Could not find agent (user_id={user_id}, session_id={session_id})")
    return None

def get_session_web_viewer_sids(session_id):
    """Get web viewer SIDs for a session"""
    sids = get_session_data(session_id, 'web_viewer_sids', [])
    return set(sids) if sids else set()

def add_session_web_viewer_sid(session_id, sid):
    """Add web viewer SID to a session"""
    sids = get_session_web_viewer_sids(session_id)
    sids.add(sid)
    set_session_data(session_id, 'web_viewer_sids', list(sids))

def remove_session_web_viewer_sid(session_id, sid):
    """Remove web viewer SID from a session"""
    sids = get_session_web_viewer_sids(session_id)
    sids.discard(sid)
    set_session_data(session_id, 'web_viewer_sids', list(sids))

# --- Helper function calculate_trends (Updated for session support) ---
def calculate_trends(raw_peaks, params, selected_electrode_key='averaged', peak_potentials=None):
    """
    Calculate trends for SWV continuous monitoring mode.

    Args:
        raw_peaks: Dict of peak current values {electrode_key: {freq: {file_num: peak}}}
        params: Analysis parameters
        selected_electrode_key: Which electrode to analyze
        peak_potentials: Optional dict of peak potential values {electrode_key: {freq: {file_num: potential}}}

    Returns:
        Dict with x_axis_values, peak_current_trends, normalized_peak_trends, kdm_trend, and peak_potential_trends
    """
    num_files = params.get('num_files', 1)
    frequencies = params.get('frequencies', [])
    normalization_point = params.get('normalizationPoint', 1)
    x_axis_options = params.get('xAxisOptions', 'File Number')
    sample_rate = params.get('sampleRate', 20)  # seconds per file

    if not frequencies: return {}
    frequencies.sort()
    low_freq_str, high_freq_str = str(frequencies[0]), str(frequencies[-1])

    # Calculate x-axis values based on user preference
    if x_axis_options == 'Experiment Time':
        # Convert file numbers to minutes: (file_number - 1) * sample_rate / 60
        x_axis_values = [(i * sample_rate) / 60 for i in range(num_files)]
    else:
        # Default file number mode
        x_axis_values = list(range(1, num_files + 1))
    peak_current_trends = {str(f): [None] * num_files for f in frequencies}
    normalized_peak_trends = {str(f): [None] * num_files for f in frequencies}
    peak_potential_trends = {str(f): [None] * num_files for f in frequencies}  # NEW: Peak potential trends
    kdm_trend = [None] * num_files

    # Get electrode-specific data
    electrode_data = raw_peaks.get(selected_electrode_key, {})

    # NEW: Get electrode-specific peak potential data
    potential_electrode_data = {}
    if peak_potentials:
        potential_electrode_data = peak_potentials.get(selected_electrode_key, {})

    for i in range(num_files):
        file_num = i + 1  # File numbers are 1-based
        for freq_str in peak_current_trends:
            peak = electrode_data.get(freq_str, {}).get(str(file_num))
            if peak is not None: peak_current_trends[freq_str][i] = peak

            # NEW: Extract peak potential for this file/frequency
            potential = potential_electrode_data.get(freq_str, {}).get(str(file_num))
            if potential is not None: peak_potential_trends[freq_str][i] = potential

    norm_factors = {}
    for freq_str in peak_current_trends:
        norm_idx = normalization_point - 1
        if 0 <= norm_idx < len(peak_current_trends[freq_str]):
            norm_value = peak_current_trends[freq_str][norm_idx]
            norm_factors[freq_str] = norm_value if norm_value and norm_value != 0 else 1.0
        else:
            norm_factors[freq_str] = 1.0
    for i in range(num_files):
        for freq_str in peak_current_trends:
            peak = peak_current_trends[freq_str][i]
            if peak is not None and norm_factors.get(freq_str):
                normalized_peak_trends[freq_str][i] = peak / norm_factors[freq_str]

        # KDM calculation using normalized peaks
        # Formula: ((high_freq_normalized - low_freq_normalized) + 1) * 100
        low_normalized = normalized_peak_trends.get(low_freq_str, [])[i]
        high_normalized = normalized_peak_trends.get(high_freq_str, [])[i]
        if low_normalized is not None and high_normalized is not None:
            kdm_trend[i] = ((high_normalized - low_normalized) + 1) * 100

    result = {
        "x_axis_values": x_axis_values,
        "peak_current_trends": peak_current_trends,
        "normalized_peak_trends": normalized_peak_trends,
        "kdm_trend": kdm_trend,
        "peak_potential_trends": peak_potential_trends  # NEW: Include peak potential trends
    }

    # DEBUG: Log peak potential data availability
    has_potential_data = any(
        any(v is not None for v in values) if values else False
        for values in peak_potential_trends.values()
    )
    logger.debug(f"calculate_trends: electrode={selected_electrode_key}, has_potential_data={has_potential_data}")
    if has_potential_data:
        sample_data = {freq: [v for v in values if v is not None][:3] for freq, values in peak_potential_trends.items()}
        logger.debug(f"calculate_trends: peak_potential sample data: {sample_data}")
    else:
        logger.warning(f"calculate_trends: No peak potential data found! peak_potentials input: {bool(peak_potentials)}")

    return result


# --- Background Task (Updated for session support) ---
def process_cv_file_in_background(original_filename, content, params_for_this_file, session_id):
    logger.info(f"CV_BACKGROUND_TASK: Started processing for '{original_filename}' in session {session_id}")
    filename = secure_filename(f"{session_id}_{original_filename}")
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        if not analyze_cv_data: return

        # Get selected electrode from params (if any)
        selected_electrode = params_for_this_file.get('selected_electrode')

        # Validate electrode count before analysis
        if selected_electrode is not None:
            try:
                import numpy as np
                # Try to load data to detect electrode count
                try:
                    data = np.loadtxt(temp_filepath, delimiter=',')
                except:
                    try:
                        data = np.loadtxt(temp_filepath, delimiter='\t')
                    except:
                        try:
                            data = np.loadtxt(temp_filepath, delimiter=' ')
                        except:
                            data = np.loadtxt(temp_filepath)

                if data.ndim == 2:
                    detected_electrodes = data.shape[1] - 1  # First column is potential
                    logger.info(f"CV: Detected {detected_electrodes} electrode(s) in file '{original_filename}'")

                    # Check if requested electrode exists
                    if selected_electrode >= detected_electrodes:
                        logger.error(f"CV: Requested electrode {selected_electrode} (1-based: {selected_electrode + 1}) but file only has {detected_electrodes} electrode(s)")
                        analysis_result = {
                            'status': 'error',
                            'message': f'File only contains {detected_electrodes} electrode(s), but you requested electrode {selected_electrode + 1}.',
                            'detected_electrodes': detected_electrodes,
                            'requested_electrode': selected_electrode + 1
                        }
                    else:
                        # Electrode exists, proceed with analysis
                        analysis_result = analyze_cv_data(temp_filepath, params_for_this_file, selected_electrode)
                else:
                    # 1D data, assume single electrode
                    if selected_electrode > 0:
                        analysis_result = {
                            'status': 'error',
                            'message': f'File only contains 1 electrode, but you requested electrode {selected_electrode + 1}.',
                            'detected_electrodes': 1,
                            'requested_electrode': selected_electrode + 1
                        }
                    else:
                        analysis_result = analyze_cv_data(temp_filepath, params_for_this_file, selected_electrode)
            except Exception as e:
                logger.error(f"CV electrode validation failed: {e}")
                analysis_result = analyze_cv_data(temp_filepath, params_for_this_file, selected_electrode)
        else:
            # No specific electrode selected, use original averaging behavior
            analysis_result = analyze_cv_data(temp_filepath, params_for_this_file, selected_electrode)

        # Handle electrode validation errors for CV
        if analysis_result and analysis_result.get('status') == 'error' and 'detected_electrodes' in analysis_result:
            validation_error_sent = get_session_data(session_id, 'validation_error_sent', False)
            if not validation_error_sent:
                set_session_data(session_id, 'validation_error_sent', True)
                logger.error(f"CV Electrode validation error: {analysis_result.get('message')}")

                # Send to ALL web viewers across all sessions
                all_web_viewer_sids = []
                if redis_client:
                    try:
                        session_keys = redis_client.keys("session:*")
                        for session_key in session_keys:
                            # session_key is already a string due to decode_responses=True
                            session_data = redis_client.hget(session_key, 'web_viewer_sids')
                            if session_data:
                                viewer_sids = json.loads(session_data)
                                all_web_viewer_sids.extend(list(viewer_sids))
                    except Exception as e:
                        logger.error(f"Error getting all web viewers for CV validation error: {e}")

                # Check fallback data for all sessions
                if not all_web_viewer_sids:
                    with session_lock:
                        for sess_id, sess_data in fallback_data.items():
                            if isinstance(sess_data, dict) and 'web_viewer_sids' in sess_data:
                                all_web_viewer_sids.extend(list(sess_data['web_viewer_sids']))

                if all_web_viewer_sids:
                    socketio.emit('electrode_validation_error', {
                        'message': analysis_result.get('message'),
                        'detected_electrodes': analysis_result.get('detected_electrodes'),
                        'requested_electrode': analysis_result.get('requested_electrode')
                    }, room=all_web_viewer_sids)
            return

        if analysis_result and analysis_result.get('status') == 'success':
            # Store CV results differently - not in trend data but as individual results
            # Support CV_60Hz_1.txt format and other formats
            match = re.search(r'CV_(\d+)Hz_(\d+)(?:\.|$)', original_filename, re.IGNORECASE) or re.search(r'_(\d+)Hz_?_?(\d+)(?:\.|$)', original_filename, re.IGNORECASE) or re.search(r'_(\d+)(?:\.|$)', original_filename, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                else:
                    parsed_frequency, parsed_filenum = 0, int(match.group(1))  # No frequency in filename

                electrode_key = str(selected_electrode) if selected_electrode is not None else 'averaged'

                # Initialize CV results structure if needed
                live_trend_data = get_session_data(session_id, 'live_trend_data', {})
                if 'cv_results' not in live_trend_data:
                    live_trend_data['cv_results'] = {}
                if electrode_key not in live_trend_data['cv_results']:
                    live_trend_data['cv_results'][electrode_key] = {}

                live_trend_data['cv_results'][electrode_key][str(parsed_filenum)] = analysis_result

                # NOTE: No sliding window for CV - analysis results needed for export. Keep all data.
                set_session_data(session_id, 'live_trend_data', live_trend_data)

        # Send CV update to ALL web viewers across all sessions
        all_web_viewer_sids = []
        if redis_client:
            try:
                session_keys = redis_client.keys("session:*")
                for session_key in session_keys:
                    # session_key is already a string due to decode_responses=True
                    session_data = redis_client.hget(session_key, 'web_viewer_sids')
                    if session_data:
                        viewer_sids = json.loads(session_data)
                        all_web_viewer_sids.extend(list(viewer_sids))
            except Exception as e:
                logger.error(f"Error getting all web viewers for CV update: {e}")

        # Check fallback data for all sessions
        if not all_web_viewer_sids:
            with session_lock:
                for sess_id, sess_data in fallback_data.items():
                    if isinstance(sess_data, dict) and 'web_viewer_sids' in sess_data:
                        all_web_viewer_sids.extend(list(sess_data['web_viewer_sids']))

        if all_web_viewer_sids:
            # Send CV update
            response_data = {
                "filename": original_filename,
                "cv_analysis": analysis_result,
                "electrode_index": selected_electrode
            }
            socketio.emit('live_cv_update', response_data, to=all_web_viewer_sids)
            logger.info(f"Sent CV update to {len(all_web_viewer_sids)} web viewers")

        # Send processing complete acknowledgment to agent for CV
        base_filename = original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename
        agent_sid = agent_session_tracker.get('agent_sid')
        if agent_sid:
            socketio.emit('file_processing_complete', {'filename': base_filename}, to=agent_sid)
            logger.info(f"CV_BACKGROUND_TASK: Sent processing complete ack for '{base_filename}' to agent")

    except Exception as e:
        logger.error(f"CV_BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
        # Send error acknowledgment to agent even if processing failed
        base_filename = original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename
        agent_sid = agent_session_tracker.get('agent_sid')
        if agent_sid:
            socketio.emit('file_processing_complete', {'filename': base_filename}, to=agent_sid)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"CV_BACKGROUND_TASK: Finished job for '{original_filename}'.")


def get_all_web_viewer_sids():
    """Helper function to get all web viewer SIDs across all sessions"""
    all_sids = []
    if redis_client:
        try:
            session_keys = redis_client.keys("session:*")
            for session_key in session_keys:
                # session_key is already a string due to decode_responses=True
                session_data = redis_client.hget(session_key, 'web_viewer_sids')
                if session_data:
                    viewer_sids = json.loads(session_data)
                    all_sids.extend(list(viewer_sids))
        except Exception as e:
            logger.error(f"Error getting all web viewers: {e}")

    # Fallback to in-memory storage for all sessions
    if not all_sids:
        with session_lock:
            for sess_id, sess_data in fallback_data.items():
                if isinstance(sess_data, dict) and 'web_viewer_sids' in sess_data:
                    all_sids.extend(list(sess_data['web_viewer_sids']))

    return all_sids


def process_frequency_map_file(original_filename, content, frequency, params, session_id, total_electrodes=1, electrode_index=0, user_id=None):
    """Process a single file for frequency map analysis

    Args:
        original_filename: Name of the file being processed
        content: File content
        user_id: User ID for ACK routing (survives reconnections)
        frequency: Frequency in Hz
        params: Analysis parameters
        session_id: Session ID
        total_electrodes: Total number of electrodes being processed for this file
        electrode_index: Index of current electrode (0-based)
    """
    temp_filepath = None

    try:
        logger.info(f"FREQUENCY_MAP: Processing '{original_filename}' at {frequency}Hz (electrode {electrode_index+1}/{total_electrodes})")

        # Create temporary file
        secure_name = secure_filename(f"freqmap_{frequency}Hz_{session_id}_{original_filename}")
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)

        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # Call existing SWV analysis function
        params_copy = params.copy()
        params_copy['frequency'] = frequency

        selected_electrode = params.get('selected_electrode')
        analysis_result = analyze_swv_data(temp_filepath, params_copy, selected_electrode)

        # Handle electrode validation errors
        if analysis_result and analysis_result.get('status') == 'error' and 'detected_electrodes' in analysis_result:
            validation_error_sent = get_session_data(session_id, 'validation_error_sent', False)
            if not validation_error_sent:
                set_session_data(session_id, 'validation_error_sent', True)
                logger.error(f"Frequency map electrode validation error: {analysis_result.get('message')}")

                all_web_viewer_sids = get_all_web_viewer_sids()
                if all_web_viewer_sids:
                    socketio.emit('electrode_validation_error', {
                        'message': analysis_result.get('message'),
                        'detected_electrodes': analysis_result.get('detected_electrodes'),
                        'requested_electrode': analysis_result.get('requested_electrode')
                    }, to=all_web_viewer_sids)
            return

        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            logger.debug(f"FREQUENCY_MAP: Analysis successful for {original_filename} @ {frequency}Hz")
            # Calculate charge in Coulombs: Charge (C) = Peak (A) / Frequency (Hz)
            peak_value = analysis_result.get('peak_value', 0)
            peak_potential = analysis_result.get('peak_info', {}).get('peak_potential')  # NEW: Get peak voltage
            charge = (peak_value / frequency) if frequency > 0 else 0

            # Store results
            frequency_map_data = get_session_data(session_id, 'frequency_map_data', {})
            if 'results' not in frequency_map_data:
                frequency_map_data['results'] = {}

            electrode_key = str(selected_electrode) if selected_electrode is not None else 'averaged'
            if electrode_key not in frequency_map_data['results']:
                frequency_map_data['results'][electrode_key] = {}

            # Check if this frequency was already processed (prevent duplicate emissions)
            freq_str = str(frequency)
            already_processed = freq_str in frequency_map_data['results'][electrode_key]

            if already_processed:
                logger.info(f"FREQUENCY_MAP: Frequency {frequency}Hz already processed, skipping duplicate")
                # Still send ack to agent but don't emit update
                # CRITICAL FIX: Use user_id for ACK routing (survives reconnections)
                agent_sid = get_current_agent_sid(user_id=user_id, session_id=session_id)
                if agent_sid:
                    socketio.emit('file_processing_complete', {'filename': original_filename}, to=agent_sid)
                    logger.debug(f"FREQUENCY_MAP: Sent ack for duplicate to agent {agent_sid}")
                else:
                    logger.warning(f"FREQUENCY_MAP: No agent found for user_id={user_id}, session={session_id}")
                return

            # Store complete data including arrays (needed for hold mode and overlay)
            frequency_map_data['results'][electrode_key][freq_str] = {
                'potentials': analysis_result.get('potentials', []),
                'raw_currents': analysis_result.get('raw_currents', []),
                'smoothed_currents': analysis_result.get('smoothed_currents', []),
                'regression_line': analysis_result.get('regression_line', []),
                'adjusted_potentials': analysis_result.get('adjusted_potentials', []),
                'peak_value': peak_value,
                'peak_potential': peak_potential,  # NEW: Store peak voltage
                'charge': charge,
                'frequency': frequency,
                'filename': original_filename
            }

            set_session_data(session_id, 'frequency_map_data', frequency_map_data)

            logger.info(f"FREQUENCY_MAP: Stored result for {frequency}Hz, charge={charge:.2f}µC, peak={peak_value:.4e}A")

            # Send update to all web viewers
            all_web_viewer_sids = get_all_web_viewer_sids()
            if all_web_viewer_sids:
                update_data = {
                    'filename': original_filename,
                    'frequency': frequency,
                    'electrode_index': selected_electrode,
                    'data': frequency_map_data['results'][electrode_key][str(frequency)]
                }
                socketio.emit('frequency_map_update', update_data, to=all_web_viewer_sids)
                logger.info(f"FREQUENCY_MAP: ✓ Sent update to {len(all_web_viewer_sids)} web viewers for {original_filename} @ {frequency}Hz (peak={peak_value:.4e}A)")
            else:
                logger.warning(f"FREQUENCY_MAP: No web viewers to send update for {original_filename} @ {frequency}Hz")
        else:
            # Analysis failed or returned unexpected status
            status = analysis_result.get('status') if analysis_result else 'None'
            logger.error(f"FREQUENCY_MAP: ✗ Analysis FAILED for {original_filename} @ {frequency}Hz - status: {status}")
            if analysis_result:
                logger.error(f"FREQUENCY_MAP: Error details: {analysis_result.get('message', 'No message')}")

        # Track electrode completion for this file
        file_processing_key = f"file_processing_{original_filename}"
        file_progress = get_session_data(session_id, file_processing_key, {'completed': 0, 'total': total_electrodes})

        # Check if file_progress is None (race condition where it was already cleaned up)
        if file_progress is None:
            file_progress = {'completed': 0, 'total': total_electrodes}
            logger.warning(f"FREQUENCY_MAP: File progress was None for '{original_filename}', reinitializing")

        file_progress['completed'] += 1

        # Only send acknowledgment when all electrodes are processed
        if file_progress['completed'] >= file_progress['total']:
            # CRITICAL FIX: Use user_id for ACK routing (survives reconnections)
            agent_sid = get_current_agent_sid(user_id=user_id, session_id=session_id)
            if agent_sid:
                socketio.emit('file_processing_complete', {'filename': original_filename}, to=agent_sid)
                logger.info(f"FREQUENCY_MAP: All electrodes complete ({file_progress['completed']}/{file_progress['total']}) - sent ack for '{original_filename}' to agent {agent_sid}")
            else:
                logger.warning(f"FREQUENCY_MAP: No agent found for user_id={user_id}, session={session_id}, cannot send ack for '{original_filename}'")
            # Clean up tracking data
            set_session_data(session_id, file_processing_key, None)
        else:
            # Still processing, update the count
            set_session_data(session_id, file_processing_key, file_progress)
            logger.info(f"FREQUENCY_MAP: Electrode progress for '{original_filename}': {file_progress['completed']}/{file_progress['total']}")

    except Exception as e:
        logger.error(f"FREQUENCY_MAP: Error processing '{original_filename}': {e}", exc_info=True)

        # Track electrode completion even on error
        file_processing_key = f"file_processing_{original_filename}"
        file_progress = get_session_data(session_id, file_processing_key, {'completed': 0, 'total': total_electrodes})

        # Check if file_progress is None (race condition)
        if file_progress is None:
            file_progress = {'completed': 0, 'total': total_electrodes}
            logger.warning(f"FREQUENCY_MAP: File progress was None for '{original_filename}' (in error handler), reinitializing")

        file_progress['completed'] += 1

        # Only send acknowledgment when all electrodes are processed (or failed)
        if file_progress['completed'] >= file_progress['total']:
            # CRITICAL FIX: Use user_id for ACK routing (survives reconnections)
            agent_sid = get_current_agent_sid(user_id=user_id, session_id=session_id)
            if agent_sid:
                socketio.emit('file_processing_complete', {'filename': original_filename}, to=agent_sid)
                logger.info(f"FREQUENCY_MAP: All electrodes complete ({file_progress['completed']}/{file_progress['total']}, with errors) - sent ack for '{original_filename}' to agent {agent_sid}")
            else:
                logger.warning(f"FREQUENCY_MAP: No agent found for user_id={user_id}, session={session_id}, cannot send ack for '{original_filename}' (error case)")
            # Clean up tracking data
            set_session_data(session_id, file_processing_key, None)
        else:
            # Still processing, update the count
            set_session_data(session_id, file_processing_key, file_progress)
            logger.info(f"FREQUENCY_MAP: Electrode progress for '{original_filename}' (error): {file_progress['completed']}/{file_progress['total']}")
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        logger.info(f"FREQUENCY_MAP: Finished processing '{original_filename}'")


# --- Concurrency-controlled task wrapper ---
def start_limited_file_task(target_function, **kwargs):
    """
    Start a background file processing task with concurrency control.
    Uses semaphore to limit the number of simultaneous file processing tasks.
    """
    def wrapped_task():
        with file_processing_semaphore:
            logger.debug(f"Acquired semaphore for {target_function.__name__} (available: {file_processing_semaphore.balance})")
            try:
                target_function(**kwargs)
            finally:
                logger.debug(f"Released semaphore for {target_function.__name__} (available: {file_processing_semaphore.balance})")

    socketio.start_background_task(wrapped_task)


def process_file_in_background(original_filename, content, params_for_this_file, session_id, user_id=None):
    logger.info(f"BACKGROUND_TASK: Started processing for '{original_filename}' in session {session_id}, user_id={user_id}")
    filename = secure_filename(f"{session_id}_{original_filename}")
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        if not analyze_swv_data: return
        # Get selected electrode from params (if any)
        selected_electrode = params_for_this_file.get('selected_electrode')
        analysis_result = analyze_swv_data(temp_filepath, params_for_this_file, selected_electrode)

        # Handle electrode validation errors
        if analysis_result and analysis_result.get('status') == 'error' and 'detected_electrodes' in analysis_result:
            validation_error_sent = get_session_data(session_id, 'validation_error_sent', False)
            if not validation_error_sent:
                set_session_data(session_id, 'validation_error_sent', True)
                logger.error(f"Electrode validation error: {analysis_result.get('message')}")

                # Send to ALL web viewers across all sessions
                all_web_viewer_sids = []
                if redis_client:
                    try:
                        session_keys = redis_client.keys("session:*")
                        for session_key in session_keys:
                            # session_key is already a string due to decode_responses=True
                            session_data = redis_client.hget(session_key, 'web_viewer_sids')
                            if session_data:
                                viewer_sids = json.loads(session_data)
                                all_web_viewer_sids.extend(list(viewer_sids))
                    except Exception as e:
                        logger.error(f"Error getting all web viewers for validation error: {e}")

                # Check fallback data for all sessions
                if not all_web_viewer_sids:
                    with session_lock:
                        for sess_id, sess_data in fallback_data.items():
                            if isinstance(sess_data, dict) and 'web_viewer_sids' in sess_data:
                                all_web_viewer_sids.extend(list(sess_data['web_viewer_sids']))

                if all_web_viewer_sids:
                    socketio.emit('electrode_validation_error', {
                        'message': analysis_result.get('message'),
                        'detected_electrodes': analysis_result.get('detected_electrodes'),
                        'requested_electrode': analysis_result.get('requested_electrode')
                    }, room=all_web_viewer_sids)
            return

        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            # Extract from original filename (without electrode suffix)
            base_filename = original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename
            # Support both old format (_60Hz_1.) and new format (_60Hz_1 or CV_60Hz_1)
            match = re.search(r'_(\d+)Hz_?_?(\d+)(?:\.|$)', base_filename, re.IGNORECASE)
            if match:
                parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                peak = analysis_result.get('peak_value')
                peak_potential = analysis_result.get('peak_info', {}).get('peak_potential')  # NEW: Get peak voltage

                # DEBUG: Log peak potential extraction
                logger.debug(f"CONTINUOUS: File {parsed_filenum} @ {parsed_frequency}Hz - Peak: {peak}, Peak Potential: {peak_potential}")
                if peak_potential is None:
                    logger.warning(f"CONTINUOUS: peak_potential is None for {base_filename}. peak_info: {analysis_result.get('peak_info')}")

                # Store data per electrode
                electrode_key = str(selected_electrode) if selected_electrode is not None else 'averaged'
                freq_key = str(parsed_frequency)
                file_key = str(parsed_filenum)

                # Initialize nested structure if needed
                live_trend_data = get_session_data(session_id, 'live_trend_data', {})
                if 'raw_peaks' not in live_trend_data:
                    live_trend_data['raw_peaks'] = {}
                if electrode_key not in live_trend_data['raw_peaks']:
                    live_trend_data['raw_peaks'][electrode_key] = {}
                if freq_key not in live_trend_data['raw_peaks'][electrode_key]:
                    live_trend_data['raw_peaks'][electrode_key][freq_key] = {}

                live_trend_data['raw_peaks'][electrode_key][freq_key][file_key] = peak

                # NEW: Store peak potentials (voltages where peak occurs)
                if 'peak_potentials' not in live_trend_data:
                    live_trend_data['peak_potentials'] = {}
                if electrode_key not in live_trend_data['peak_potentials']:
                    live_trend_data['peak_potentials'][electrode_key] = {}
                if freq_key not in live_trend_data['peak_potentials'][electrode_key]:
                    live_trend_data['peak_potentials'][electrode_key][freq_key] = {}

                if peak_potential is not None:
                    live_trend_data['peak_potentials'][electrode_key][freq_key][file_key] = peak_potential

                # Store filter parameters and QC metrics for each individual file
                if 'filter_params' not in live_trend_data:
                    live_trend_data['filter_params'] = {}
                if electrode_key not in live_trend_data['filter_params']:
                    live_trend_data['filter_params'][electrode_key] = {}
                if freq_key not in live_trend_data['filter_params'][electrode_key]:
                    live_trend_data['filter_params'][electrode_key][freq_key] = {}

                if 'qc_metrics' not in live_trend_data:
                    live_trend_data['qc_metrics'] = {}
                if electrode_key not in live_trend_data['qc_metrics']:
                    live_trend_data['qc_metrics'][electrode_key] = {}
                if freq_key not in live_trend_data['qc_metrics'][electrode_key]:
                    live_trend_data['qc_metrics'][electrode_key][freq_key] = {}

                # Store filter parameters and QC metrics for this specific file
                if 'filter_params' in analysis_result and analysis_result['filter_params']:
                    live_trend_data['filter_params'][electrode_key][freq_key][file_key] = analysis_result['filter_params']

                if 'qc_metrics' in analysis_result and analysis_result['qc_metrics']:
                    live_trend_data['qc_metrics'][electrode_key][freq_key][file_key] = analysis_result['qc_metrics']

                # Save the updated trend data back to session
                # NOTE: No sliding window here - peak values and analysis results are small
                # and needed for export. Keep all data.
                set_session_data(session_id, 'live_trend_data', live_trend_data)

                # Track peak detection warnings
                if analysis_result.get('warning_type') in ['no_derivative_peak', 'insufficient_points_for_derivative', 'internal_baseline_error']:
                    live_peak_detection_warnings = get_session_data(session_id, 'live_peak_detection_warnings', {})
                    if electrode_key not in live_peak_detection_warnings:
                        live_peak_detection_warnings[electrode_key] = []
                    warning_info = {
                        'filename': base_filename,
                        'frequency': parsed_frequency,
                        'file_number': parsed_filenum,
                        'warning_type': analysis_result.get('warning_type'),
                        'message': analysis_result.get('message', '')
                    }
                    live_peak_detection_warnings[electrode_key].append(warning_info)
                    set_session_data(session_id, 'live_peak_detection_warnings', live_peak_detection_warnings)
        # Get current electrode selection from params
        live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
        live_trend_data = get_session_data(session_id, 'live_trend_data', {})
        live_peak_detection_warnings = get_session_data(session_id, 'live_peak_detection_warnings', {})
        current_electrode = live_analysis_params.get('selected_electrode')
        electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'

        # PERFORMANCE OPTIMIZATION: Incremental updates instead of full data
        # Only send current file's data point, not entire history
        # Frontend maintains the trend chart locally

        # Extract current file's peak data for incremental update
        freq_key = str(parsed_frequency)
        file_key = str(parsed_filenum)
        electrode_data = live_trend_data.get('raw_peaks', {}).get(electrode_key, {})
        current_peak = electrode_data.get(freq_key, {}).get(file_key)

        # NEW: Extract current file's peak potential for incremental update
        potential_data = live_trend_data.get('peak_potentials', {}).get(electrode_key, {})
        current_peak_potential = potential_data.get(freq_key, {}).get(file_key)

        # Build incremental data (only current file)
        incremental_data = {
            "file_number": parsed_filenum,
            "frequency": parsed_frequency,
            "peak_value": current_peak,
            "peak_potential": current_peak_potential,  # NEW: Include peak potential for drift detection
            "electrode": electrode_key
        }

        # Every 10 files, send full trend data for synchronization
        # This ensures frontend stays in sync even if some updates are lost
        send_full_data = (parsed_filenum % 10 == 0)

        full_trends = None
        if send_full_data:
            # NEW: Pass peak_potentials to calculate_trends for drift detection
            full_trends = calculate_trends(
                live_trend_data.get('raw_peaks', {}),
                live_analysis_params,
                electrode_key,
                peak_potentials=live_trend_data.get('peak_potentials', {})
            )
            trend_data_size = len(json.dumps(full_trends))
            logger.info(f"[PERF] Sending FULL trend data for file #{parsed_filenum}, size: {trend_data_size} bytes")

        # PRIVACY FIX: Send update ONLY to web viewers with matching user_id
        # First, find the user_id for this session
        user_id = get_user_id_by_session_id(session_id)

        if user_id:
            # Get web viewers registered to this user_id
            user_web_viewers = get_web_viewers_by_user_id(user_id)

            if user_web_viewers:
                # Send update with electrode-specific information
                response_data = {
                    "filename": base_filename,  # Use base filename for frontend processing
                    "individual_analysis": analysis_result,
                    "incremental_data": incremental_data,  # NEW: Only current file's data
                    "trend_data": full_trends if send_full_data else None,  # Full data every 10 files
                    "electrode_index": selected_electrode,
                    "peak_detection_warnings": live_peak_detection_warnings.get(electrode_key, [])
                }

                # Monitor data size
                response_size = len(json.dumps(response_data))
                logger.info(f"[PERF] Sent {'FULL' if send_full_data else 'INCREMENTAL'} update to {len(user_web_viewers)} viewers, size: {response_size} bytes")

                socketio.emit('live_analysis_update', response_data, to=user_web_viewers)
            else:
                logger.info(f"No web viewers registered for user_id: {user_id}")
        else:
            logger.warning(f"Could not find user_id for session: {session_id} - skipping broadcast for privacy")

        # Send processing complete acknowledgment to agent
        # CRITICAL FIX: Use user_id for ACK routing (survives reconnections)
        agent_sid = get_current_agent_sid(user_id=user_id, session_id=session_id)
        if agent_sid:
            socketio.emit('file_processing_complete', {'filename': base_filename}, to=agent_sid)
            logger.info(f"CONTINUOUS: ✓ Sent ack for '{base_filename}' to agent {agent_sid}")
        else:
            logger.warning(f"CONTINUOUS: No agent found for user_id={user_id}, session={session_id}, cannot send ack for '{base_filename}'")

    except Exception as e:
        logger.error(f"CONTINUOUS: ✗ ERROR processing '{original_filename}': {e}", exc_info=True)
        # Send error acknowledgment to agent even if processing failed
        # CRITICAL FIX: Use user_id for ACK routing (survives reconnections)
        agent_sid = get_current_agent_sid(user_id=user_id, session_id=session_id)
        if agent_sid:
            error_filename = original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename
            socketio.emit('file_processing_complete', {'filename': error_filename}, to=agent_sid)
            logger.info(f"CONTINUOUS: Sent error ack for '{error_filename}' to agent {agent_sid}")
        else:
            logger.warning(f"CONTINUOUS: No agent_sid found for session {session_id}, cannot send error ack")
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"BACKGROUND_TASK: Finished job for '{original_filename}'.")


# --- *** NEW *** HELPER FUNCTION TO GENERATE CSV DATA ---
def generate_csv_data(session_id, current_electrode=None):
    """
    Generates a CSV formatted string from the current trend data with filter parameters and QC metrics.

    Args:
        current_electrode: The electrode index to export data for (None for averaged data).
        session_id: The session ID to get data from.
    """
    # Get session data
    live_trend_data = get_session_data(session_id, 'live_trend_data', {})
    live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})

    if not live_trend_data or not live_analysis_params:
        return ""

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    frequencies = [str(f) for f in live_analysis_params.get('frequencies', [])]
    num_files = live_analysis_params.get('num_files', 0)

    # Write metadata section first
    writer.writerow(['# SACMES Analysis Report'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_info = f"Electrode {current_electrode + 1}" if current_electrode is not None else "Averaged"
    writer.writerow(['# Electrode:', electrode_info])
    writer.writerow([])

    # Write filter parameters section
    writer.writerow(['# Filter Parameters'])
    filter_mode = live_analysis_params.get('filter_mode', 'auto')
    writer.writerow(['Filter Mode:', filter_mode])

    if filter_mode == 'manual':
        writer.writerow(['Hampel Window:', live_analysis_params.get('hampel_window', 'N/A')])
        writer.writerow(['Hampel Threshold:', live_analysis_params.get('hampel_threshold', 'N/A')])
        writer.writerow(['SG Window:', live_analysis_params.get('sg_window', 'N/A')])
        writer.writerow(['SG Degree:', live_analysis_params.get('sg_degree', 'N/A')])
    else:
        writer.writerow(['Hampel Window:', 'Auto (1/10 FWHM)'])
        writer.writerow(['Hampel Threshold:', 'Auto (3×MAD)'])
        writer.writerow(['SG Window:', 'Auto (1/3 FWHM)'])
        writer.writerow(['SG Degree:', 'Auto (2)'])

    writer.writerow([])

    writer.writerow(['# Analysis Data'])

    # Get electrode key
    electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'

    # Write detailed header with QC and filter parameters for each frequency
    header = ['File_Number']
    for freq in frequencies:
        header.extend([
            f'Peak_Current_{freq}Hz',
            f'Filter_Mode_{freq}Hz',
            f'Hampel_Window_{freq}Hz',
            f'Hampel_Threshold_{freq}Hz',
            f'SG_Window_{freq}Hz',
            f'SG_Degree_{freq}Hz',
            f'FWHM_{freq}Hz',
            f'SNR_Improvement_{freq}Hz',
            f'Peak_Retention_{freq}Hz',
            f'Residual_Metric_{freq}Hz',
            f'QC_Status_{freq}Hz'
        ])
    for freq in frequencies:
        header.append(f'Normalized_Peak_{freq}Hz')
    header.append('KDM_%')
    writer.writerow(header)

    # Recalculate full trends to ensure data is consistent
    # NEW: Pass peak_potentials to calculate_trends for drift detection
    full_trends = calculate_trends(
        live_trend_data.get('raw_peaks', {}),
        live_analysis_params,
        electrode_key,
        peak_potentials=live_trend_data.get('peak_potentials', {})
    )

    # Get stored data
    filter_data = live_trend_data.get('filter_params', {}).get(electrode_key, {})
    qc_data = live_trend_data.get('qc_metrics', {}).get(electrode_key, {})

    # Write data rows with individual file parameters
    for i in range(num_files):
        file_num = i + 1
        file_key = str(file_num)
        row = [file_num]

        # Add peak current and corresponding filter/QC data for each frequency
        for freq in frequencies:
            freq_str = str(freq)
            peak_value = full_trends.get('peak_current_trends', {}).get(freq_str, [None] * num_files)[i]
            row.append(peak_value)

            # Get filter and QC data for this specific file and frequency
            file_filter_data = filter_data.get(freq_str, {}).get(file_key, {})
            file_qc_data = qc_data.get(freq_str, {}).get(file_key, {})

            # Add filter parameters
            row.extend([
                file_filter_data.get('filter_mode', 'N/A'),
                file_filter_data.get('hampel_window', 'N/A'),
                file_filter_data.get('hampel_threshold', 'N/A'),
                file_filter_data.get('sg_window', 'N/A'),
                file_filter_data.get('sg_degree', 'N/A'),
                file_filter_data.get('fwhm', 'N/A')
            ])

            # Add QC metrics
            row.extend([
                f"{file_qc_data.get('snr_improvement', 'N/A'):.3f}" if isinstance(file_qc_data.get('snr_improvement'), (int, float)) else 'N/A',
                f"{file_qc_data.get('peak_retention', 'N/A'):.3f}" if isinstance(file_qc_data.get('peak_retention'), (int, float)) else 'N/A',
                f"{file_qc_data.get('residual_metric', 'N/A'):.3f}" if isinstance(file_qc_data.get('residual_metric'), (int, float)) else 'N/A',
                file_qc_data.get('qc_status', 'N/A')
            ])

        # Add normalized peaks
        for freq in frequencies:
            freq_str = str(freq)
            normalized_value = full_trends.get('normalized_peak_trends', {}).get(freq_str, [None] * num_files)[i]
            row.append(normalized_value)

        # Add KDM
        row.append(full_trends.get('kdm_trend', [None] * num_files)[i])
        writer.writerow(row)

    return string_io.getvalue()


def generate_csv_data_all_electrodes(session_id):
    """
    Generates a CSV formatted string with all electrodes data combined, including mean and std.
    Filter parameters are hidden, QC warnings are listed at the end.

    Args:
        session_id: The session ID to get data from.
    """
    # Get session data
    live_trend_data = get_session_data(session_id, 'live_trend_data', {})
    live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})

    if not live_trend_data or not live_analysis_params:
        return ""

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    frequencies = [str(f) for f in live_analysis_params.get('frequencies', [])]
    num_files = live_analysis_params.get('num_files', 0)
    num_electrodes = live_analysis_params.get('num_electrodes', 1)

    # Get all electrode keys (excluding 'averaged' if present)
    all_electrode_keys = [str(i) for i in range(num_electrodes)]

    # Write metadata section
    writer.writerow(['# SACMES Continuous Monitor Analysis Report - All Electrodes'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_list = ', '.join([f'E{int(k)+1}' for k in all_electrode_keys])
    writer.writerow(['# Electrodes:', electrode_list])
    writer.writerow(['# Number of Files:', num_files])
    writer.writerow([])

    # Prepare trend data for all electrodes
    all_trends = {}
    for electrode_key in all_electrode_keys:
        all_trends[electrode_key] = calculate_trends(
            live_trend_data.get('raw_peaks', {}),
            live_analysis_params,
            electrode_key
        )

    # Section 1: Peak Current and Peak Potential for each frequency
    for freq in frequencies:
        writer.writerow([f'# Peak Current {freq}Hz (A) and Peak Potential (V)'])
        header = ['File_Number']
        for k in all_electrode_keys:
            header.extend([f'E{int(k)+1}_Peak_A', f'E{int(k)+1}_Peak_V'])
        header.extend(['Mean_Peak_A', 'Std_Peak_A'])
        writer.writerow(header)

        for i in range(num_files):
            file_num = i + 1
            row = [file_num]

            # Collect peak values from all electrodes
            peak_values = []
            for electrode_key in all_electrode_keys:
                # Peak current
                peak_value = all_trends[electrode_key].get('peak_current_trends', {}).get(freq, [None] * num_files)[i]
                peak_values.append(peak_value if peak_value is not None else 0)
                row.append(f'{peak_value:.6e}' if peak_value is not None else 'N/A')

                # Peak potential (voltage where peak occurs)
                peak_potential = live_trend_data.get('peak_potentials', {}).get(electrode_key, {}).get(freq, {}).get(str(file_num))
                row.append(f'{peak_potential:.4f}' if peak_potential is not None else 'N/A')

            # Calculate mean and std for peak currents
            valid_peaks = [p for p in peak_values if p is not None and p != 0]
            if valid_peaks:
                mean_peak = np.mean(valid_peaks)
                std_peak = np.std(valid_peaks, ddof=1) if len(valid_peaks) > 1 else 0
                row.append(f'{mean_peak:.6e}')
                row.append(f'{std_peak:.6e}')
            else:
                row.extend(['N/A', 'N/A'])

            writer.writerow(row)
        writer.writerow([])

    # Section 2: Normalized Peak for each frequency
    for freq in frequencies:
        writer.writerow([f'# Normalized Peak {freq}Hz'])
        header = ['File_Number'] + [f'E{int(k)+1}_Normalized' for k in all_electrode_keys] + ['Mean_Normalized', 'Std_Normalized']
        writer.writerow(header)

        for i in range(num_files):
            file_num = i + 1
            row = [file_num]

            # Collect normalized values from all electrodes
            norm_values = []
            for electrode_key in all_electrode_keys:
                norm_value = all_trends[electrode_key].get('normalized_peak_trends', {}).get(freq, [None] * num_files)[i]
                norm_values.append(norm_value if norm_value is not None else 0)
                row.append(f'{norm_value:.6f}' if norm_value is not None else 'N/A')

            # Calculate mean and std
            valid_norms = [n for n in norm_values if n is not None and n != 0]
            if valid_norms:
                mean_norm = np.mean(valid_norms)
                std_norm = np.std(valid_norms, ddof=1) if len(valid_norms) > 1 else 0
                row.append(f'{mean_norm:.6f}')
                row.append(f'{std_norm:.6f}')
            else:
                row.extend(['N/A', 'N/A'])

            writer.writerow(row)
        writer.writerow([])

    # Section 3: KDM
    writer.writerow(['# KDM (%) - Formula: ((High_Freq_Normalized - Low_Freq_Normalized) + 1) * 100'])
    header = ['File_Number'] + [f'E{int(k)+1}_KDM_%' for k in all_electrode_keys] + ['Mean_KDM_%', 'Std_KDM_%']
    writer.writerow(header)

    for i in range(num_files):
        file_num = i + 1
        row = [file_num]

        # Collect KDM values from all electrodes
        kdm_values = []
        for electrode_key in all_electrode_keys:
            kdm_value = all_trends[electrode_key].get('kdm_trend', [None] * num_files)[i]
            kdm_values.append(kdm_value if kdm_value is not None else 0)
            row.append(f'{kdm_value:.6f}' if kdm_value is not None else 'N/A')

        # Calculate mean and std
        valid_kdms = [k for k in kdm_values if k is not None and k != 0]
        if valid_kdms:
            mean_kdm = np.mean(valid_kdms)
            std_kdm = np.std(valid_kdms, ddof=1) if len(valid_kdms) > 1 else 0
            row.append(f'{mean_kdm:.6f}')
            row.append(f'{std_kdm:.6f}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 4: Summary Statistics per Electrode
    writer.writerow(['# Summary Statistics per Electrode'])
    summary_header = ['Electrode']
    for freq in frequencies:
        summary_header.extend([f'Avg_Peak_{freq}Hz_A', f'Std_Peak_{freq}Hz_A'])
    summary_header.extend(['Avg_KDM_%', 'Std_KDM_%'])
    writer.writerow(summary_header)

    for electrode_key in all_electrode_keys:
        electrode_label = f'E{int(electrode_key)+1}'
        row = [electrode_label]

        trends = all_trends[electrode_key]

        # Add peak current stats for each frequency
        for freq in frequencies:
            peak_trend = trends.get('peak_current_trends', {}).get(freq, [])
            valid_peaks = [p for p in peak_trend if p is not None]
            if valid_peaks:
                row.append(f'{np.mean(valid_peaks):.6e}')
                row.append(f'{np.std(valid_peaks, ddof=1):.6e}' if len(valid_peaks) > 1 else '0.000000e+00')
            else:
                row.extend(['N/A', 'N/A'])

        # Add KDM stats
        kdm_trend = trends.get('kdm_trend', [])
        valid_kdms = [k for k in kdm_trend if k is not None]
        if valid_kdms:
            row.append(f'{np.mean(valid_kdms):.6f}')
            row.append(f'{np.std(valid_kdms, ddof=1):.6f}' if len(valid_kdms) > 1 else '0.000000')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)

    # Section 5: QC Warnings
    # Collect all QC warnings where status is not 'Pass'
    writer.writerow([])
    writer.writerow(['# Quality Control Warnings'])
    writer.writerow(['# Only files/electrodes/frequencies with QC flags are listed below'])
    writer.writerow([])

    qc_data = live_trend_data.get('qc_metrics', {})
    warnings_found = False

    # Check each electrode
    for electrode_key in all_electrode_keys:
        electrode_qc = qc_data.get(electrode_key, {})
        if not electrode_qc:
            continue

        electrode_label = f'E{int(electrode_key)+1}'

        # Check each frequency
        for freq in frequencies:
            freq_qc = electrode_qc.get(freq, {})
            if not freq_qc:
                continue

            # Check each file
            for i in range(num_files):
                file_num = i + 1
                file_key = str(file_num)
                file_qc = freq_qc.get(file_key, {})

                qc_status = file_qc.get('qc_status', 'Pass')

                # Only report if NOT Pass
                if qc_status and qc_status != 'Pass':
                    if not warnings_found:
                        # Write header
                        writer.writerow(['Electrode', 'Frequency_Hz', 'File_Number', 'QC_Status', 'SNR_Improvement', 'Peak_Retention', 'Residual_Metric'])
                        warnings_found = True

                    # Write warning row
                    snr = file_qc.get('snr_improvement', 'N/A')
                    peak_ret = file_qc.get('peak_retention', 'N/A')
                    residual = file_qc.get('residual_metric', 'N/A')

                    writer.writerow([
                        electrode_label,
                        freq,
                        file_num,
                        qc_status,
                        f'{snr:.3f}' if isinstance(snr, (int, float)) else snr,
                        f'{peak_ret:.3f}' if isinstance(peak_ret, (int, float)) else peak_ret,
                        f'{residual:.3f}' if isinstance(residual, (int, float)) else residual
                    ])

    if not warnings_found:
        writer.writerow(['No QC warnings detected. All data passed quality control.'])

    return string_io.getvalue()


# --- Socket.IO Event Handlers (Connect, Disconnect, Start Session are Unchanged) ---
# DEPRECATED: Old global session tracker (kept for backward compatibility, will be removed)
agent_session_tracker = {'current_session': None, 'agent_sid': None}

# NEW: User ID based mapping for multi-user support
agent_user_mapping = {}  # {user_id: {'session_id': xxx, 'agent_sid': xxx, 'connected_at': xxx}}
agent_user_mapping_lock = threading.Lock()

# NEW: Web viewer to user_id mapping for multi-viewer support (monitor mode)
# This allows multiple web browsers to monitor the same agent's analysis
web_user_mapping = {}  # {user_id: set([web_viewer_sid1, web_viewer_sid2, ...])}
web_user_mapping_lock = threading.Lock()

def register_agent_user(user_id, session_id, agent_sid):
    """
    Register agent user_id to session mapping.
    This allows multiple agents to connect simultaneously.

    Args:
        user_id: Unique user identifier from agent
        session_id: Server-generated session ID
        agent_sid: Socket.IO connection ID
    """
    with agent_user_mapping_lock:
        agent_user_mapping[user_id] = {
            'session_id': session_id,
            'agent_sid': agent_sid,
            'connected_at': datetime.now().isoformat()
        }

    # Store in Redis for persistence
    if redis_client:
        try:
            redis_client.hset(
                'agent_user_mapping',
                user_id,
                json.dumps({
                    'session_id': session_id,
                    'agent_sid': agent_sid,
                    'connected_at': datetime.now().isoformat()
                })
            )
            logger.info(f"Registered agent mapping in Redis: {user_id} -> {session_id}")
        except Exception as e:
            logger.error(f"Failed to store agent mapping in Redis: {e}")

    logger.info(f"Registered agent user: {user_id}, session: {session_id}, sid: {agent_sid}")

def get_agent_session_by_user_id(user_id):
    """
    Get agent session info by user_id.

    Args:
        user_id: User identifier

    Returns:
        dict with 'session_id', 'agent_sid', 'connected_at' or None if not found
    """
    # Try Redis first
    if redis_client:
        try:
            data = redis_client.hget('agent_user_mapping', user_id)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get agent mapping error: {e}")

    # Fallback to in-memory
    with agent_user_mapping_lock:
        return agent_user_mapping.get(user_id)

def unregister_agent_user(user_id):
    """
    Unregister agent when disconnected.

    Args:
        user_id: User identifier to remove
    """
    with agent_user_mapping_lock:
        if user_id in agent_user_mapping:
            del agent_user_mapping[user_id]
            logger.info(f"Unregistered agent user from memory: {user_id}")

    if redis_client:
        try:
            redis_client.hdel('agent_user_mapping', user_id)
            logger.info(f"Unregistered agent user from Redis: {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete agent mapping from Redis: {e}")

def get_user_id_by_agent_sid(agent_sid):
    """
    Reverse lookup: find user_id by agent socket ID.
    Used during disconnect to identify which user disconnected.

    Args:
        agent_sid: Socket.IO connection ID

    Returns:
        user_id or None if not found
    """
    # Check memory first
    with agent_user_mapping_lock:
        for user_id, mapping in agent_user_mapping.items():
            if mapping['agent_sid'] == agent_sid:
                return user_id

    # Check Redis if not in memory
    if redis_client:
        try:
            all_mappings = redis_client.hgetall('agent_user_mapping')
            for user_id_bytes, mapping_json in all_mappings.items():
                user_id = user_id_bytes.decode('utf-8') if isinstance(user_id_bytes, bytes) else user_id_bytes
                mapping = json.loads(mapping_json)
                if mapping.get('agent_sid') == agent_sid:
                    return user_id
        except Exception as e:
            logger.error(f"Redis reverse lookup error: {e}")

    return None

def register_web_viewer_user(user_id, web_viewer_sid):
    """
    Register a web viewer to a user_id for monitor mode.
    Multiple web viewers can connect to the same user_id to monitor analysis.

    Args:
        user_id: User identifier from agent
        web_viewer_sid: Socket.IO connection ID of the web viewer
    """
    with web_user_mapping_lock:
        if user_id not in web_user_mapping:
            web_user_mapping[user_id] = set()
        web_user_mapping[user_id].add(web_viewer_sid)

    # Store in Redis for persistence
    if redis_client:
        try:
            redis_client.hset(
                'web_user_mapping',
                user_id,
                json.dumps(list(web_user_mapping[user_id]))
            )
            logger.info(f"Registered web viewer in Redis: user_id={user_id}, sid={web_viewer_sid}, total_viewers={len(web_user_mapping[user_id])}")
        except Exception as e:
            logger.error(f"Failed to store web viewer mapping in Redis: {e}")

    logger.info(f"Registered web viewer: user_id={user_id}, sid={web_viewer_sid}, total_viewers={len(web_user_mapping[user_id])}")

def unregister_web_viewer_user(user_id, web_viewer_sid):
    """
    Unregister a web viewer from a user_id when disconnected.

    Args:
        user_id: User identifier
        web_viewer_sid: Socket.IO connection ID of the web viewer
    """
    with web_user_mapping_lock:
        if user_id in web_user_mapping:
            web_user_mapping[user_id].discard(web_viewer_sid)

            # Remove the user_id entry if no more viewers
            if not web_user_mapping[user_id]:
                del web_user_mapping[user_id]
                logger.info(f"Removed user_id mapping (no more viewers): {user_id}")
            else:
                logger.info(f"Unregistered web viewer: user_id={user_id}, sid={web_viewer_sid}, remaining_viewers={len(web_user_mapping[user_id])}")

    # Update Redis
    if redis_client:
        try:
            if user_id in web_user_mapping:
                redis_client.hset(
                    'web_user_mapping',
                    user_id,
                    json.dumps(list(web_user_mapping[user_id]))
                )
            else:
                redis_client.hdel('web_user_mapping', user_id)
                logger.info(f"Removed web viewer mapping from Redis: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update web viewer mapping in Redis: {e}")

def get_web_viewers_by_user_id(user_id):
    """
    Get all web viewer SIDs for a given user_id.

    Args:
        user_id: User identifier

    Returns:
        list of web viewer socket IDs
    """
    # Try Redis first
    if redis_client:
        try:
            data = redis_client.hget('web_user_mapping', user_id)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get web viewer mapping error: {e}")

    # Fallback to in-memory
    with web_user_mapping_lock:
        if user_id in web_user_mapping:
            return list(web_user_mapping[user_id])
        return []

def get_user_id_by_web_viewer_sid(web_viewer_sid):
    """
    Reverse lookup: find user_id by web viewer socket ID.
    Used during disconnect to identify which user_id the viewer was monitoring.

    Args:
        web_viewer_sid: Web viewer socket ID

    Returns:
        user_id string or None if not found
    """
    # Check in-memory first
    with web_user_mapping_lock:
        for user_id, viewer_sids in web_user_mapping.items():
            if web_viewer_sid in viewer_sids:
                return user_id

    # Check Redis if not in memory
    if redis_client:
        try:
            all_mappings = redis_client.hgetall('web_user_mapping')
            for user_id_bytes, viewers_json in all_mappings.items():
                user_id = user_id_bytes.decode('utf-8') if isinstance(user_id_bytes, bytes) else user_id_bytes
                viewer_sids = json.loads(viewers_json)
                if web_viewer_sid in viewer_sids:
                    return user_id
        except Exception as e:
            logger.error(f"Redis reverse lookup for web viewer error: {e}")

    return None

def get_user_id_by_session_id(session_id):
    """
    Reverse lookup: find user_id by session_id.
    Used to determine which user's data is being processed.

    Args:
        session_id: Session ID

    Returns:
        user_id string or None if not found
    """
    # Check in-memory first
    with agent_user_mapping_lock:
        for user_id, mapping in agent_user_mapping.items():
            if mapping.get('session_id') == session_id:
                return user_id

    # Check Redis if not in memory
    if redis_client:
        try:
            all_mappings = redis_client.hgetall('agent_user_mapping')
            for user_id_bytes, mapping_json in all_mappings.items():
                user_id = user_id_bytes.decode('utf-8') if isinstance(user_id_bytes, bytes) else user_id_bytes
                mapping = json.loads(mapping_json)
                if mapping.get('session_id') == session_id:
                    return user_id
        except Exception as e:
            logger.error(f"Redis reverse lookup for session error: {e}")

    return None

def detect_ongoing_analysis(session_id):
    """
    Detect if there are ongoing SWV or CV analyses for a given session.
    Used for smart monitor mode - shows appropriate monitor buttons.

    Args:
        session_id: Session ID to check

    Returns:
        dict: {'swv': bool, 'cv': bool} indicating ongoing analyses
    """
    result = {'swv': False, 'cv': False}

    try:
        # Check for SWV data
        swv_trend_data = get_session_data(session_id, 'live_trend_data', {})
        if swv_trend_data and swv_trend_data.get('raw_peaks'):
            result['swv'] = True

        # Check for CV data
        cv_data = get_session_data(session_id, 'cv_segments_data', {})
        if cv_data and len(cv_data) > 0:
            result['cv'] = True

        logger.info(f"Detected ongoing analysis for session {session_id}: {result}")
    except Exception as e:
        logger.error(f"Error detecting ongoing analysis: {e}")

    return result

@socketio.on('connect')
def handle_connect():
    # WebSocket health monitoring with connection timing
    client_info = f"sid={request.sid}, remote={request.remote_addr}"
    connection_timestamp = time.time()
    logger.info(f"[WEBSOCKET] New connection at {connection_timestamp}: {client_info}")

    # Check if this is an agent with a specific session_id in auth data
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None

    if token and token == AGENT_AUTH_TOKEN:
        # NEW: Get user_id from query parameters
        user_id = request.args.get('user_id')

        if not user_id:
            logger.error("Agent connected without user_id - connection rejected")
            return False  # Reject connection

        # SECURITY: Check if user_id is already in use
        existing_agent = get_agent_session_by_user_id(user_id)
        if existing_agent:
            existing_sid = existing_agent.get('agent_sid')

            # Check if the existing connection is still active
            try:
                # Try to check if the old socket is still connected
                # Flask-SocketIO uses socketio.server.manager to track active connections
                is_still_connected = False
                if hasattr(socketio, 'server') and hasattr(socketio.server, 'manager'):
                    # Check if the old sid is in the active connections
                    namespace = '/'
                    if namespace in socketio.server.manager.rooms:
                        rooms = socketio.server.manager.rooms[namespace]
                        # Check if existing_sid has any active rooms (means it's connected)
                        is_still_connected = existing_sid in rooms

                if is_still_connected:
                    # Old connection is truly still active - reject new connection
                    logger.error(f"SECURITY: User ID collision detected! user_id={user_id} is already ACTIVELY connected by agent_sid={existing_sid}")
                    logger.error(f"Rejecting new connection attempt from sid={request.sid}")

                    # Notify the connecting agent that user_id is taken
                    emit('connection_rejected', {
                        'reason': 'user_id_collision',
                        'message': f'User ID {user_id} is already in use by an active agent. Please restart your agent to generate a new User ID.',
                        'user_id': user_id
                    })
                    return False  # Reject connection
                else:
                    # Old connection is stale (disconnected but not cleaned up yet)
                    logger.warning(f"Replacing stale agent mapping for user_id={user_id} (old sid={existing_sid} is no longer connected)")

                    # Clean up the stale mapping immediately
                    old_session_id = existing_agent.get('session_id')
                    if old_session_id:
                        # Clear agent_sid from old session
                        set_session_agent_sid(old_session_id, None)
                        logger.info(f"Cleared stale agent_sid from old session {old_session_id}")

                    # Clean up global tracker if it matches
                    if agent_session_tracker.get('agent_sid') == existing_sid:
                        agent_session_tracker['current_session'] = None
                        agent_session_tracker['agent_sid'] = None
                        logger.info(f"Cleared stale agent from global tracker")

                    # Continue to allow connection and will overwrite the stale mapping below

            except Exception as e:
                logger.error(f"Error checking connection status for existing agent: {e}")
                # On error, be conservative and allow the reconnection
                # (assuming it's a genuine reconnection attempt)
                logger.warning(f"Could not verify old connection status, allowing reconnection for user_id={user_id}")

        # For agents: create a unique session for this agent connection
        # This prevents data pollution between multiple concurrent agent sessions

        # CRITICAL FIX: Check if this is a reconnection and preserve analysis parameters
        old_agent_session = get_agent_session_by_user_id(user_id)
        old_session_id = old_agent_session.get('session_id') if old_agent_session else None

        agent_session_id = str(uuid.uuid4())
        session['session_id'] = agent_session_id
        session_id = agent_session_id

        # CRITICAL FIX: If reconnecting, migrate analysis parameters from old session to new session
        if old_session_id and old_session_id != agent_session_id:
            logger.info(f"Agent reconnection detected for user {user_id}: old_session={old_session_id}, new_session={agent_session_id}")

            # Migrate critical session data from old to new session
            data_to_migrate = [
                'live_analysis_params',
                'live_trend_data',
                'live_peak_detection_warnings',
                'frequency_map_data',
                'frequency_map_params'
            ]

            for key in data_to_migrate:
                old_data = get_session_data(old_session_id, key, None)
                if old_data is not None:
                    set_session_data(agent_session_id, key, old_data)
                    logger.info(f"Migrated '{key}' from old session to new session ({len(str(old_data))} bytes)")

            logger.info(f"✓ Session migration complete for user {user_id}")

        # NEW: Register user_id mapping (multi-user support)
        register_agent_user(user_id, session_id, request.sid)
        logger.info(f"[SOCKET] Successfully registered agent: user_id={user_id}, sid={request.sid}, session={session_id}, timestamp={connection_timestamp}")

        # DEPRECATED: Update global agent tracker (kept for backward compatibility)
        agent_session_tracker['current_session'] = session_id
        agent_session_tracker['agent_sid'] = request.sid

        set_session_agent_sid(session_id, request.sid)
        logger.info(f"AGENT connected. User ID: {user_id}, SID: {request.sid}, Session: {session_id}")

        # PRIVACY FIX: Notify ONLY web viewers with matching user_id
        user_web_viewers = get_web_viewers_by_user_id(user_id)

        if user_web_viewers:
            emit('agent_status', {'status': 'connected', 'user_id': user_id}, to=user_web_viewers)
            logger.info(f"Notified {len(user_web_viewers)} web viewers of agent connection (user_id: {user_id})")
        else:
            logger.info(f"No web viewers registered yet for user_id: {user_id}")

        # Send session info back to agent
        emit('session_info', {'session_id': session_id, 'user_id': user_id})

    else:
        # For web viewers: use normal session management
        session_id = get_session_id()
        add_session_web_viewer_sid(session_id, request.sid)
        web_viewer_sids = get_session_web_viewer_sids(session_id)
        logger.info(f"WEB VIEWER connected. SID: {request.sid}, Session: {session_id}, Total viewers: {len(web_viewer_sids)}")

        # Send session ID to client for tracking
        emit('session_info', {'session_id': session_id})

        # Check if global agent is connected
        if agent_session_tracker['agent_sid']:
            emit('agent_status', {'status': 'connected'})
            logger.info("Notified new web viewer that agent is connected")
        else:
            emit('agent_status', {'status': 'disconnected'})


@socketio.on('disconnect')
def handle_disconnect():
    session_id = get_session_id()
    disconnected_sid = request.sid

    # WebSocket health monitoring - log disconnect details
    disconnect_reason = request.args.get('reason', 'unknown')
    client_info = f"sid={disconnected_sid}, remote={request.remote_addr}"
    logger.warning(f"[WEBSOCKET] Client disconnected: {client_info}, session={session_id}, reason={disconnect_reason}")

    # NEW: Check if this is an agent disconnection by looking up user_id
    disconnected_user_id = get_user_id_by_agent_sid(disconnected_sid)

    if disconnected_user_id:
        # This is an agent disconnection
        logger.warning(f"AGENT disconnecting: User ID: {disconnected_user_id}, SID: {disconnected_sid}")

        # Get current session before cleanup
        disconnected_session = None
        if agent_session_tracker.get('agent_sid') == disconnected_sid:
            disconnected_session = agent_session_tracker.get('current_session')

        # Grace period for agent reconnection
        # CRITICAL FIX: Increased to 30 seconds for Windows agents over OpenShift router
        # Analysis shows Windows agents typically need 5-8 seconds to reconnect
        def delayed_agent_cleanup():
            import time
            time.sleep(30.0)  # 30 second grace period (was 3s, too short for OpenShift)

            # CRITICAL: Check if there are still pending file processing tasks before cleanup
            # Background tasks may still be processing files from the old session
            agent_mapping = get_agent_session_by_user_id(disconnected_user_id)
            if agent_mapping:
                old_session_id = agent_mapping.get('session_id')
                if old_session_id:
                    # Check for pending file processing tasks
                    pending_tasks = get_session_data(old_session_id, 'pending_file_count', 0)
                    if pending_tasks > 0:
                        logger.warning(f"[CLEANUP] Session {old_session_id} still has {pending_tasks} pending tasks, delaying cleanup...")
                        time.sleep(10.0)  # Additional 10 seconds for tasks to complete

            # Check if agent reconnected (user_id would have new mapping with different sid)
            current_mapping = get_agent_session_by_user_id(disconnected_user_id)

            if current_mapping and current_mapping.get('agent_sid') == disconnected_sid:
                # Agent did not reconnect, clean up
                logger.warning(f"Agent (User ID: {disconnected_user_id}) did not reconnect within 30s grace period. Cleaning up...")

                # Unregister from user_id mapping
                unregister_agent_user(disconnected_user_id)

                # DEPRECATED: Clear global tracker if it matches
                if agent_session_tracker.get('agent_sid') == disconnected_sid:
                    agent_session_tracker['current_session'] = None
                    agent_session_tracker['agent_sid'] = None
                    if disconnected_session:
                        set_session_agent_sid(disconnected_session, None)

                # PRIVACY FIX: Notify ONLY web viewers with matching user_id
                user_web_viewers = get_web_viewers_by_user_id(disconnected_user_id)

                if user_web_viewers:
                    socketio.emit('agent_status', {'status': 'disconnected', 'user_id': disconnected_user_id}, to=user_web_viewers)
                    logger.info(f"Notified {len(user_web_viewers)} web viewers of agent disconnection (user_id: {disconnected_user_id})")
                else:
                    logger.info(f"No web viewers to notify for user_id: {disconnected_user_id}")
            else:
                logger.info(f"Agent (User ID: {disconnected_user_id}) reconnected or replaced. Skipping cleanup.")

        # Start the delayed cleanup in background
        socketio.start_background_task(delayed_agent_cleanup)

    else:
        # Check if this was a web viewer disconnection
        web_viewer_sids = get_session_web_viewer_sids(session_id)
        if request.sid in web_viewer_sids:
            remove_session_web_viewer_sid(session_id, request.sid)

            # NEW: Clean up web_user_mapping when web viewer disconnects
            viewer_user_id = get_user_id_by_web_viewer_sid(request.sid)
            if viewer_user_id:
                unregister_web_viewer_user(viewer_user_id, request.sid)
                logger.info(f"Cleaned up web_user_mapping for disconnected viewer: user_id={viewer_user_id}, sid={request.sid}")

            # Reset validation error flag when a web viewer disconnects
            set_session_data(session_id, 'validation_error_sent', False)
            remaining_viewers = get_session_web_viewer_sids(session_id)
            logger.info(f"Web viewer disconnected from session {session_id}, remaining viewers: {len(remaining_viewers)}")

            # Clean up session if no more viewers and no agent
            if not remaining_viewers and not get_session_agent_sid(session_id):
                logger.info(f"Session {session_id} has no active connections, scheduling cleanup")
                # Schedule cleanup after a delay to allow for reconnections
                socketio.start_background_task(cleanup_session_after_delay, session_id, 300)  # 5 minutes

@socketio.on('request_agent_status')
def handle_request_agent_status(data):
    """Handle frontend request for current agent connection status"""
    # Check global agent tracker first
    agent_connected = bool(agent_session_tracker.get('agent_sid'))

    # Double-check with session storage if needed
    if not agent_connected:
        if redis_client:
            try:
                agent_sid_data = redis_client.hget('session:global_agent_session', 'agent_sid')
                agent_connected = bool(agent_sid_data and agent_sid_data != 'null')
            except Exception as e:
                logger.error(f"Error checking global agent status: {e}")
        else:
            # Check fallback storage
            agent_connected = bool(fallback_data.get('agent_sid'))

    if agent_connected:
        emit('agent_status', {'status': 'connected'})
        logger.info("Reported global agent as connected")
    else:
        emit('agent_status', {'status': 'disconnected'})
        logger.info("Reported global agent as disconnected")

def cleanup_session_after_delay(session_id, delay_seconds):
    """Clean up session data after a delay if no active connections"""
    import time
    time.sleep(delay_seconds)

    # Check if session still has no active connections
    web_viewer_sids = get_session_web_viewer_sids(session_id)
    agent_sid = get_session_agent_sid(session_id)

    if not web_viewer_sids and not agent_sid:
        logger.info(f"Cleaning up abandoned session {session_id}")
        clear_session_data(session_id)
    else:
        logger.info(f"Session {session_id} has active connections, skipping cleanup")


@socketio.on('scan_available_frequencies')
def handle_scan_frequencies(data):
    """
    Request agent to scan folder and detect all available frequencies.
    Used for frequency map mode to populate frequency dropdown.
    """
    logger.info(f"[FREQUENCY SCAN] Received scan_available_frequencies from {request.sid}")
    logger.info(f"[FREQUENCY SCAN] Data: {data}")

    user_id = data.get('user_id') if data else None
    file_handle = data.get('file_handle', '')

    if not user_id:
        logger.error("[FREQUENCY SCAN] ERROR: Scan frequencies request missing user_id")
        emit('available_frequencies_response', {'status': 'error', 'message': 'User ID is required'})
        return

    agent_mapping = get_agent_session_by_user_id(user_id)
    if not agent_mapping:
        logger.warning(f"[FREQUENCY SCAN] ERROR: No agent found for user_id: {user_id}")
        emit('available_frequencies_response', {'status': 'error', 'message': 'Agent not connected'})
        return

    agent_sid = agent_mapping['agent_sid']
    logger.info(f"[FREQUENCY SCAN] Requesting frequency scan from agent")
    logger.info(f"[FREQUENCY SCAN] - user_id: {user_id}")
    logger.info(f"[FREQUENCY SCAN] - agent_sid: {agent_sid}")
    logger.info(f"[FREQUENCY SCAN] - file_handle: {file_handle}")
    logger.info(f"[FREQUENCY SCAN] - requester_sid: {request.sid}")

    emit('request_frequency_scan', {
        'file_handle': file_handle,
        'requester_sid': request.sid
    }, to=agent_sid)

    logger.info(f"[FREQUENCY SCAN] Emitted request_frequency_scan to agent_sid: {agent_sid}")


@socketio.on('start_analysis_session')
def handle_start_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'start_analysis_session' from {request.sid}, Session: {session_id}")

    # NEW: Get user_id from web viewer request
    user_id = data.get('user_id') if data else None

    if not user_id:
        logger.error("Start analysis request missing user_id")
        emit('ack_start_session', {'status': 'error', 'message': 'User ID is required to start analysis.'})
        return

    if 'analysisParams' in data:
        set_session_data(session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(session_id, 'live_trend_data', {"raw_peaks": {}})
        set_session_data(session_id, 'live_peak_detection_warnings', {})
        set_session_data(session_id, 'validation_error_sent', False)
        logger.info(f"Analysis session started for session {session_id}. Params set and trend data reset.")

    # NEW: Look up agent by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)

    if 'filters' in data and agent_mapping:
        agent_sid = agent_mapping['agent_sid']
        agent_session_id = agent_mapping['session_id']

        live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')

        # Store analysis params in agent's session for data processing
        set_session_data(agent_session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(agent_session_id, 'live_trend_data', {"raw_peaks": {}})
        set_session_data(agent_session_id, 'live_peak_detection_warnings', {})
        set_session_data(agent_session_id, 'validation_error_sent', False)

        logger.info(f"Sending filters to agent (user_id: {user_id}, sid: {agent_sid}): {filters}")
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent.'})
    elif not agent_mapping:
        logger.warning(f"No agent found for user_id: {user_id}")
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected for this User ID.'})


@socketio.on('start_cv_analysis_session')
def handle_start_cv_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'start_cv_analysis_session' from {request.sid}, Session: {session_id}")

    # NEW: Get user_id from web viewer request
    user_id = data.get('user_id') if data else None

    if not user_id:
        logger.error("Start CV analysis request missing user_id")
        emit('ack_start_cv_session', {'status': 'error', 'message': 'User ID is required to start CV analysis.'})
        return

    if 'analysisParams' in data:
        set_session_data(session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(session_id, 'live_trend_data', {"cv_results": {}})
        set_session_data(session_id, 'validation_error_sent', False)
        logger.info(f"CV Analysis session started for session {session_id}. Params set and CV data reset.")

    # NEW: Look up agent by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)

    if 'filters' in data and agent_mapping:
        agent_sid = agent_mapping['agent_sid']
        agent_session_id = agent_mapping['session_id']

        live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')

        # Store CV analysis params in agent's session for data processing
        set_session_data(agent_session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(agent_session_id, 'live_trend_data', {"cv_results": {}})
        set_session_data(agent_session_id, 'validation_error_sent', False)

        logger.info(f"Sending CV filters to agent (user_id: {user_id}, sid: {agent_sid}): {filters}")
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_cv_session', {'status': 'success', 'message': 'CV Instructions sent.'})
    elif not agent_mapping:
        logger.warning(f"No agent found for user_id: {user_id}")
        emit('ack_start_cv_session', {'status': 'error', 'message': 'Error: Local agent not detected for this User ID.'})


@socketio.on('stop_analysis_session')
def handle_stop_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'stop_analysis_session' from {request.sid}, Session: {session_id}")

    # Reset all analysis states
    set_session_data(session_id, 'live_analysis_params', {})
    set_session_data(session_id, 'live_trend_data', {})
    set_session_data(session_id, 'live_peak_detection_warnings', {})
    set_session_data(session_id, 'validation_error_sent', False)

    # Notify agent to stop if connected
    agent_sid = get_session_agent_sid(session_id)
    if agent_sid:
        emit('stop_data_stream', {}, to=agent_sid)

    logger.info(f"Analysis session stopped for session {session_id} and states reset.")


@socketio.on('stop_cv_analysis_session')
def handle_stop_cv_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'stop_cv_analysis_session' from {request.sid}, Session: {session_id}")

    # Reset all analysis states
    set_session_data(session_id, 'live_analysis_params', {})
    set_session_data(session_id, 'live_trend_data', {})
    set_session_data(session_id, 'validation_error_sent', False)

    # Notify agent to stop if connected
    agent_sid = get_session_agent_sid(session_id)
    if agent_sid:
        emit('stop_cv_data_stream', {}, to=agent_sid)

    logger.info(f"CV Analysis session stopped for session {session_id} and states reset.")


@socketio.on('start_frequency_map_session')
def handle_start_frequency_map_session(data):
    """
    Start frequency map analysis session
    Expected data structure:
    {
        'user_id': 'xxx-xxx-xxx',
        'analysisParams': {...},
        'frequencies': [10, 20, 50, 100, ...],
        'filters': {...}
    }
    """
    session_id = get_session_id()
    logger.info(f"Received 'start_frequency_map_session' from {request.sid}, Session: {session_id}")

    # NEW: Get user_id from web viewer request
    user_id = data.get('user_id') if data else None

    if not user_id:
        logger.error("Start frequency map request missing user_id")
        emit('ack_start_frequency_map_session', {'status': 'error', 'message': 'User ID is required to start frequency map.'})
        return

    if 'analysisParams' in data:
        # Store frequency map specific params
        data['analysisParams']['analysis_mode'] = 'frequency_map'
        set_session_data(session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(session_id, 'frequency_map_data', {
            'frequencies': data.get('frequencies', []),
            'results': {}  # {electrode_key: {frequency: {data}}}
        })
        set_session_data(session_id, 'validation_error_sent', False)
        logger.info(f"Frequency Map session started for session {session_id} with frequencies: {data.get('frequencies', [])}")

    # NEW: Look up agent by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)

    if 'filters' in data and agent_mapping:
        agent_sid = agent_mapping['agent_sid']
        agent_session_id = agent_mapping['session_id']

        filters = data['filters']
        filters['analysis_mode'] = 'frequency_map'
        filters['frequencies'] = data.get('frequencies', [])
        filters['file_extension'] = data['analysisParams'].get('file_extension', '.txt')

        # Store in agent's session for data processing
        set_session_data(agent_session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(agent_session_id, 'frequency_map_data', {
            'frequencies': data.get('frequencies', []),
            'results': {}
        })
        set_session_data(agent_session_id, 'validation_error_sent', False)

        logger.info(f"Sending frequency map filters to agent (user_id: {user_id}, sid: {agent_sid}): {filters}")

        # CRITICAL FIX: Add error handling for emit operations to prevent socket errors
        try:
            emit('set_filters', filters, to=agent_sid)
            logger.debug(f"Successfully sent set_filters to agent {agent_sid}")
        except Exception as e:
            logger.error(f"Failed to send set_filters to agent {agent_sid}: {e}")
            emit('ack_start_frequency_map_session', {'status': 'error', 'message': f'Failed to communicate with agent: {str(e)}'})
            return

        try:
            emit('ack_start_frequency_map_session', {'status': 'success', 'message': 'Frequency map instructions sent.'})
            logger.debug(f"Successfully sent ack_start_frequency_map_session to web viewer")
        except Exception as e:
            logger.error(f"Failed to send ack to web viewer: {e}")
    elif not agent_mapping:
        logger.warning(f"No agent found for user_id: {user_id}")
        emit('ack_start_frequency_map_session', {'status': 'error', 'message': 'Error: Local agent not detected for this User ID.'})


@socketio.on('stop_frequency_map_session')
def handle_stop_frequency_map_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'stop_frequency_map_session' from {request.sid}, Session: {session_id}")

    # Reset frequency map states
    set_session_data(session_id, 'live_analysis_params', {})
    set_session_data(session_id, 'frequency_map_data', {})
    set_session_data(session_id, 'validation_error_sent', False)

    # Notify agent to stop if connected
    agent_sid = get_session_agent_sid(session_id)
    if agent_sid:
        emit('stop_data_stream', {}, to=agent_sid)

    logger.info(f"Frequency Map session stopped for session {session_id} and states reset.")


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    try:
        # CONNECTION STABILITY: Log data arrival with detailed socket info
        logger.info(f"[SOCKET] ===== stream_instrument_data START =====")
        logger.info(f"[SOCKET] From sid={request.sid}, remote={request.remote_addr}")

        filename = data.get('filename', 'unknown') if data else 'unknown'
        content_size = len(data.get('content', '')) if data else 0
        logger.info(f"[SOCKET] File: {filename}, Size: {content_size} bytes")

        # NEW: Verify this is from a registered agent using user_id lookup
        user_id = get_user_id_by_agent_sid(request.sid)

        if not user_id:
            logger.error(f"[SOCKET ERROR] UNREGISTERED agent SID: {request.sid}")
            logger.error(f"[SOCKET ERROR] Agent connected but didn't register with user_id")
            emit('file_validation_error', {
                'filename': filename,
                'error': 'Agent not registered',
                'message': 'Agent session not found. Please reconnect agent.'
            }, to=request.sid)
            return

        logger.info(f"[SOCKET] Agent verified: user_id={user_id}")

        # Get agent session by user_id
        agent_mapping = get_agent_session_by_user_id(user_id)
        if not agent_mapping:
            logger.error(f"[SOCKET ERROR] No session for user_id: {user_id}")
            emit('file_validation_error', {
                'filename': filename,
                'error': 'Session not found',
                'message': 'Agent session expired. Please reconnect.'
            }, to=request.sid)
            return

        agent_session_id = agent_mapping['session_id']
        logger.info(f"[SOCKET] Session: {agent_session_id}")

        # FLOW CONTROL: Check server load and adjust agent rate if needed
        try:
            check_and_adjust_agent_rate(user_id, request.sid)
        except Exception as rate_error:
            logger.error(f"[SOCKET ERROR] Flow control failed: {rate_error}")

        original_filename = data.get('filename', 'unknown_file.txt')
        file_content = data.get('content', '')
        logger.info(f"[SOCKET] Processing: {original_filename} (session {agent_session_id})")

    except Exception as pre_process_error:
        logger.error(f"[SOCKET CRITICAL] Pre-processing error: {pre_process_error}")
        import traceback
        logger.error(f"[SOCKET CRITICAL] Traceback:\n{traceback.format_exc()}")
        return

    # SAFETY VALIDATION: Check file safety before processing
    is_safe, error_message = validate_file_safety(original_filename, file_content)
    if not is_safe:
        logger.warning(f"File safety check failed for {original_filename}: {error_message}")
        emit('file_validation_error', {
            'filename': original_filename,
            'error': error_message,
            'message': f"File '{original_filename}' was rejected: {error_message}"
        }, to=request.sid)
        return

    # Use the agent's session for analysis parameters
    live_analysis_params = get_session_data(agent_session_id, 'live_analysis_params', {})
    if not live_analysis_params:
        logger.warning("No analysis parameters found in global agent session")
        return

    # Check analysis mode
    analysis_mode = live_analysis_params.get('analysis_mode', 'continuous')

    # Support both old format (_60Hz_1.) and new format (_60Hz_1 or CV_60Hz_1)
    match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
    if not match:
        logger.warning(f"Filename does not match expected pattern: {original_filename}")
        return

    frequency = int(match.group(1))

    # Get selected electrodes from analysis params
    selected_electrodes = live_analysis_params.get('selected_electrodes', [])

    if analysis_mode == 'frequency_map':
        # Frequency Map mode: Process file for frequency map visualization
        logger.info(f"Processing in FREQUENCY MAP mode: {original_filename} at {frequency}Hz")

        if selected_electrodes:
            # Process each selected electrode
            total_electrodes = len(selected_electrodes)
            for idx, electrode_idx in enumerate(selected_electrodes):
                params_for_this_file = live_analysis_params.copy()
                params_for_this_file['selected_electrode'] = electrode_idx
                params_for_this_file.setdefault('low_xstart', None)
                params_for_this_file.setdefault('low_xend', None)
                params_for_this_file.setdefault('high_xstart', None)
                params_for_this_file.setdefault('high_xend', None)

                start_limited_file_task(
                    target_function=process_frequency_map_file,
                    original_filename=original_filename,
                    content=file_content,
                    frequency=frequency,
                    params=params_for_this_file,
                    session_id=agent_session_id,
                    total_electrodes=total_electrodes,
                    electrode_index=idx,
                    user_id=user_id  # CRITICAL: For ACK routing after reconnection
                )
        else:
            # Averaged electrode data (single task)
            params_for_this_file = live_analysis_params.copy()
            params_for_this_file.setdefault('low_xstart', None)
            params_for_this_file.setdefault('low_xend', None)
            params_for_this_file.setdefault('high_xstart', None)
            params_for_this_file.setdefault('high_xend', None)

            # FIXED: Use start_limited_file_task to respect concurrency limits
            start_limited_file_task(
                target_function=process_frequency_map_file,
                original_filename=original_filename,
                content=file_content,
                frequency=frequency,
                params=params_for_this_file,
                session_id=agent_session_id,
                total_electrodes=1,
                electrode_index=0,
                user_id=user_id  # CRITICAL: For ACK routing after reconnection
            )

    else:
        # Continuous Monitor mode: Original behavior
        logger.info(f"Processing in CONTINUOUS MONITOR mode: {original_filename}")

        if selected_electrodes:
            # Process each selected electrode in parallel
            for electrode_idx in selected_electrodes:
                params_for_this_file = live_analysis_params.copy()
                params_for_this_file['frequency'] = frequency
                params_for_this_file['selected_electrode'] = electrode_idx
                params_for_this_file.setdefault('low_xstart', None)
                params_for_this_file.setdefault('low_xend', None)
                params_for_this_file.setdefault('high_xstart', None)
                params_for_this_file.setdefault('high_xend', None)

                start_limited_file_task(target_function=process_file_in_background,
                                             original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                             content=file_content,
                                             params_for_this_file=params_for_this_file,
                                             session_id=agent_session_id,
                                             user_id=user_id)  # CRITICAL: For ACK routing after reconnection
        else:
            # Original averaging behavior
            params_for_this_file = live_analysis_params.copy()
            params_for_this_file['frequency'] = frequency
            params_for_this_file.setdefault('low_xstart', None)
            params_for_this_file.setdefault('low_xend', None)
            params_for_this_file.setdefault('high_xstart', None)
            params_for_this_file.setdefault('high_xend', None)

            start_limited_file_task(target_function=process_file_in_background,
                                         original_filename=original_filename,
                                         content=file_content,
                                         params_for_this_file=params_for_this_file,
                                         session_id=agent_session_id,
                                         user_id=user_id)  # CRITICAL: For ACK routing after reconnection


@socketio.on('stream_cv_data')
def handle_cv_instrument_data(data):
    # NEW: Verify this is from a registered agent using user_id lookup
    user_id = get_user_id_by_agent_sid(request.sid)

    if not user_id:
        logger.warning(f"Received CV data from unregistered agent SID: {request.sid}")
        return

    # Get agent session by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)
    if not agent_mapping:
        logger.error(f"No active CV session found for user_id: {user_id}")
        return

    agent_session_id = agent_mapping['session_id']
    session_id = agent_session_id
    logger.debug(f"Processing CV data for user_id: {user_id}, session: {session_id}")

    # FLOW CONTROL: Check server load and adjust agent rate if needed
    check_and_adjust_agent_rate(user_id, request.sid)

    original_filename = data.get('filename', 'unknown_file.txt')
    file_content = data.get('content', '')

    # SAFETY VALIDATION: Check file safety before processing
    is_safe, error_message = validate_file_safety(original_filename, file_content)
    if not is_safe:
        logger.warning(f"CV file safety check failed for {original_filename}: {error_message}")
        emit('file_validation_error', {
            'filename': original_filename,
            'error': error_message,
            'message': f"File '{original_filename}' was rejected: {error_message}"
        }, to=request.sid)
        return

    live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
    if not live_analysis_params:
        return

    # Get selected electrodes from analysis params
    selected_electrodes = live_analysis_params.get('selected_electrodes', [])

    if selected_electrodes:
        # Process each selected electrode for CV
        for electrode_idx in selected_electrodes:
            params_for_this_file = live_analysis_params.copy()
            params_for_this_file['selected_electrode'] = electrode_idx

            start_limited_file_task(target_function=process_cv_file_in_background,
                                         original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                         content=file_content,
                                         params_for_this_file=params_for_this_file,
                                         session_id=session_id)
    else:
        # Original averaging behavior for CV
        params_for_this_file = live_analysis_params.copy()
        start_limited_file_task(target_function=process_cv_file_in_background,
                                     original_filename=original_filename,
                                     content=file_content,
                                     params_for_this_file=params_for_this_file,
                                     session_id=session_id)


@socketio.on('get_cv_preview')
def handle_get_cv_preview(data):
    """Get CV preview file from agent for segment selection"""
    try:
        logger.info(f"CV Preview requested from client: {request.sid}")

        # Get agent_sid from the global agent tracker
        agent_sid = agent_session_tracker.get('agent_sid')

        if not agent_sid:
            logger.warning("No agent connected for CV preview request")
            emit('cv_preview_response', {'status': 'error', 'message': 'Agent not connected'})
            return

        filters = data.get('filters', {})
        analysis_params = data.get('analysisParams', {})
        logger.info(f"CV Preview filters: {filters}")
        logger.info(f"CV Preview params: {analysis_params}")

        # Store the requesting client's socket ID for response routing
        analysis_params['requesting_client_sid'] = request.sid

        # Request first file from agent for preview
        logger.info(f"Sending get_cv_file_for_preview to agent {agent_sid}")
        logger.info(f"Original request from client: {request.sid}")
        socketio.emit('get_cv_file_for_preview', {
            'filters': filters,
            'analysisParams': analysis_params,
            'preview_mode': True
        }, room=agent_sid)

    except Exception as e:
        logger.error(f"Error requesting CV preview: {e}", exc_info=True)
        emit('cv_preview_response', {'status': 'error', 'message': str(e)})


@socketio.on('get_cv_segments')
def handle_get_cv_segments(data):
    """Get available CV segments from uploaded file - Non-blocking version"""
    try:
        logger.info(f"=== CV Segments Request RECEIVED (Non-blocking) ===")
        logger.info(f"From session/client: {request.sid}")
        logger.info(f"Request namespace: {request.namespace}")
        logger.info(f"Data keys: {list(data.keys()) if data else 'NO DATA'}")
        logger.info(f"Socket connected: {request.sid is not None}")

        if not get_cv_segments:
            logger.error("CV analyzer not available")
            emit('cv_segments_response', {'status': 'error', 'message': 'CV analyzer not available'})
            return

        file_content = data.get('content', '')
        analysis_params = data.get('params', {})

        # Try to use preview content from agent's session first to avoid large payload transfers
        agent_session_id = agent_session_tracker.get('current_session')
        if not agent_session_id:
            logger.error("No active agent session for CV segments")
            emit('cv_segments_response', {'status': 'error', 'message': 'No active agent session found.'})
            return
        session_id = agent_session_id
        if not file_content:
            file_content = get_session_data(session_id, 'cv_preview_content', '')
            if file_content:
                logger.info(f"Using CV preview content from session ({len(file_content)} bytes)")

        logger.info(f"File content length: {len(file_content)}")
        logger.info(f"Analysis params keys: {list(analysis_params.keys())}")

        if not file_content:
            logger.error("No file content provided and no preview content in session")
            emit('cv_segments_response', {'status': 'error', 'message': 'No file content provided'})
            return

        # Send immediate acknowledgment to prevent timeout
        logger.info(f"Sending cv_segments_processing acknowledgment to {request.sid}")
        emit('cv_segments_processing', {
            'status': 'started',
            'message': 'Processing CV segments in background...'
        })
        logger.info(f"cv_segments_processing acknowledgment sent")

        # Start background task to avoid blocking the main thread
        logger.info(f"Starting background task for CV segment processing")
        socketio.start_background_task(
            target=process_cv_segments_background,
            data=data,
            client_sid=request.sid
        )

        logger.info(f"✅ Background CV segment processing task started for client {request.sid}")

    except Exception as e:
        logger.error(f"Error starting CV segments processing: {e}", exc_info=True)
        emit('cv_segments_response', {'status': 'error', 'message': str(e)})


def process_cv_segments_background(data, client_sid):
    """Background processing for CV segments to avoid blocking main thread"""
    temp_filepath = None
    try:
        logger.info(f"=== Background CV Segments Processing Started ===")
        logger.info(f"Client SID: {client_sid}")

        # Extract data
        file_content = data.get('content', '')
        analysis_params = data.get('params', {})
        selected_electrode = analysis_params.get('selected_electrode')

        # If no content provided, try to get from agent's session (preview content)
        if not file_content:
            agent_session_id = agent_session_tracker.get('current_session')
            if not agent_session_id:
                logger.error("No active agent session for CV segments preview content")
                socketio.emit('cv_segments_response', {
                    'status': 'error',
                    'message': 'No active agent session found.'
                }, room=client_sid)
                return
            file_content = get_session_data(agent_session_id, 'cv_preview_content', '')
            if file_content:
                logger.info(f"Retrieved CV preview content from session ({len(file_content)} bytes)")
            else:
                logger.error("No file content in request and no preview content in session")
                socketio.emit('cv_segments_response', {
                    'status': 'error',
                    'message': 'No file content available. Please load preview first.'
                }, room=client_sid)
                return

        logger.info(f"File content available: {len(file_content)} bytes")

        # Send progress update
        socketio.emit('cv_segments_progress', {
            'progress': 10,
            'message': 'Creating temporary file...'
        }, room=client_sid)

        # Create temporary file
        filename = secure_filename(data.get('filename', f'temp_cv_{client_sid}.txt'))
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.info(f"Creating temp file: {temp_filepath}")

        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(file_content)

        # Yield control to event loop
        gevent.sleep(0)

        # Verify file was written correctly
        if not os.path.exists(temp_filepath):
            logger.error("Failed to create temporary file")
            socketio.emit('cv_segments_response', {
                'status': 'error',
                'message': 'Failed to create temporary file'
            }, room=client_sid)
            return

        logger.info(f"Temp file size: {os.path.getsize(temp_filepath)} bytes")

        # Send progress update
        socketio.emit('cv_segments_progress', {
            'progress': 30,
            'message': 'Reading and parsing CV data...'
        }, room=client_sid)

        # Yield control before heavy operation
        gevent.sleep(0)

        # Get segments with periodic yielding
        logger.info("Calling get_cv_segments function...")
        segments_result = get_cv_segments_with_yield(temp_filepath, analysis_params, selected_electrode, client_sid)
        logger.info(f"Segments result: {segments_result}")

        # Send final progress update
        socketio.emit('cv_segments_progress', {
            'progress': 100,
            'message': 'Segment detection completed!'
        }, room=client_sid)

        # Send final result
        socketio.emit('cv_segments_response', segments_result, room=client_sid)

        logger.info(f"CV segments processing completed successfully for client {client_sid}")

    except Exception as e:
        logger.error(f"Error in background CV segments processing: {e}", exc_info=True)
        socketio.emit('cv_segments_response', {
            'status': 'error',
            'message': f'Background processing error: {str(e)}'
        }, room=client_sid)

    finally:
        # Clean up temporary file
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.info(f"Temporary file cleaned up: {temp_filepath}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_filepath}: {cleanup_error}")


def get_cv_segments_with_yield(file_path, params, selected_electrode, client_sid=None):
    """CV segments detection with yielding to prevent blocking"""
    try:
        # Send progress update
        if client_sid:
            socketio.emit('cv_segments_progress', {
                'progress': 50,
                'message': 'Analyzing CV segments...'
            }, room=client_sid)

        # Yield control before calling the heavy function
        gevent.sleep(0)

        # Call the original function but with yielding
        result = get_cv_segments(file_path, params, selected_electrode)

        # Yield control after processing
        gevent.sleep(0)

        # Send progress update
        if client_sid:
            socketio.emit('cv_segments_progress', {
                'progress': 90,
                'message': 'Finalizing segment detection...'
            }, room=client_sid)

        return result

    except Exception as e:
        logger.error(f"Error in get_cv_segments_with_yield: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@socketio.on('frequency_scan_result')
def handle_frequency_scan_result(data):
    """
    Receive frequency scan results from agent and forward to requesting web viewer.
    """
    logger.info(f"[FREQUENCY SCAN] Received frequency_scan_result from agent {request.sid}")
    logger.info(f"[FREQUENCY SCAN] Result data: {data}")

    frequencies = data.get('frequencies', [])
    requester_sid = data.get('requester_sid')
    status = data.get('status', 'success')

    logger.info(f"[FREQUENCY SCAN] Status: {status}, Frequencies count: {len(frequencies)}, Requester: {requester_sid}")

    if status == 'error':
        message = data.get('message', 'Unknown error')
        logger.error(f"[FREQUENCY SCAN] ERROR from agent: {message}")
        socketio.emit('available_frequencies_response', {
            'status': 'error',
            'message': message
        }, to=requester_sid)
        logger.info(f"[FREQUENCY SCAN] Sent error response to {requester_sid}")
        return

    logger.info(f"[FREQUENCY SCAN] Detected frequencies: {frequencies}")

    socketio.emit('available_frequencies_response', {
        'status': 'success',
        'frequencies': frequencies,
        'file_handle': data.get('file_handle', '')
    }, to=requester_sid)

    logger.info(f"[FREQUENCY SCAN] Sent success response to {requester_sid} with {len(frequencies)} frequencies")


@socketio.on('cv_data_from_agent')
def handle_cv_data_from_agent(data):
    """Handle CV data from agent - both preview and analysis modes"""
    logger.info(f"Received cv_data_from_agent from {request.sid}")

    # Get agent_sid from the global agent tracker
    agent_sid = agent_session_tracker.get('agent_sid')
    if request.sid != agent_sid:
        logger.warning(f"CV data received from non-agent SID: {request.sid}, expected: {agent_sid}")
        return

    try:
        preview_mode = data.get('preview_mode', False)
        file_content = data.get('content', '')
        analysis_params = data.get('analysisParams', {})
        filename = data.get('filename', 'unknown')
        status = data.get('status', 'unknown')

        logger.info(f"CV data - Preview mode: {preview_mode}, Filename: {filename}, Status: {status}")
        logger.info(f"Content length: {len(file_content)}")

        if status == 'error':
            error_message = data.get('message', 'Unknown error')
            logger.error(f"Agent reported CV error: {error_message}")
            requesting_client_sid = analysis_params.get('requesting_client_sid')
            socketio.emit('cv_preview_response', {'status': 'error', 'message': error_message}, room=requesting_client_sid)
            return

        if preview_mode:
            # This is for segment selection preview
            logger.info("Processing CV preview data")
            if file_content:
                # Parse the CV data for preview visualization
                import tempfile
                from data_processing.data_reader import ReadData

                logger.info("Creating temporary file for CV preview parsing")
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name

                try:
                    # Read the data for preview
                    voltage_column = analysis_params.get('voltage_column', 1) - 1
                    current_column = analysis_params.get('current_column', 2) - 1
                    spacing_index = analysis_params.get('spacing_index', 1)
                    delimiter_num = analysis_params.get('delimiter', 1)
                    file_extension = analysis_params.get('file_extension', '.txt')

                    # Convert delimiter number to character string
                    delimiter_map = {1: " ", 2: "\t", 3: ","}
                    delimiter_char = delimiter_map.get(delimiter_num, " ")

                    logger.info(f"CV Preview parsing params: voltage_col={voltage_column}, current_col={current_column}, spacing={spacing_index}, delimiter_num={delimiter_num}, delimiter_char='{delimiter_char}'")

                    # Read data for first electrode or averaged
                    data_result = ReadData(
                        temp_path,
                        voltage_column_index=voltage_column,
                        current_column_start_index=current_column,
                        spacing_index=spacing_index,
                        num_electrodes=1,
                        delimiter_char=delimiter_char,
                        file_extension=file_extension,
                        selected_electrodes=None  # Use averaging for preview
                    )

                    logger.info(f"CV data parsing result: {type(data_result)}")
                    if data_result:
                        logger.info(f"Data result keys: {list(data_result.keys()) if isinstance(data_result, dict) else 'Not a dict'}")
                        if 'voltage' in data_result and 'current' in data_result:
                            voltage_data = data_result['voltage']
                            current_data = data_result['current']
                            logger.info(f"CV data parsed successfully: voltage points={len(voltage_data)}, current points={len(current_data)}")
                            logger.info(f"Voltage range: {min(voltage_data)} to {max(voltage_data)}")
                            logger.info(f"Current range: {min(current_data)} to {max(current_data)}")

                            # Get the original requesting client's socket ID
                            requesting_client_sid = analysis_params.get('requesting_client_sid')
                            logger.info(f"Sending CV preview response to original client: {requesting_client_sid}")

                            # Store preview content in agent's session for segment detection (avoid re-sending large data)
                            agent_session_id = agent_session_tracker.get('current_session')
                            if agent_session_id:
                                set_session_data(agent_session_id, 'cv_preview_content', file_content)
                                set_session_data(agent_session_id, 'cv_preview_client_sid', requesting_client_sid)
                            logger.info(f"Stored CV preview content in session ({len(file_content)} bytes)")

                            # Send the CV data for preview visualization (without content to reduce payload)
                            socketio.emit('cv_preview_response', {
                                'status': 'success',
                                'content': file_content,  # Keep for backward compatibility
                                'cv_data': {
                                    'voltage': voltage_data,
                                    'current': current_data
                                }
                            }, room=requesting_client_sid)
                            logger.info(f"Sent CV preview response to client {requesting_client_sid}")
                        else:
                            logger.error(f"CV data missing required keys. Available keys: {list(data_result.keys()) if isinstance(data_result, dict) else 'Not a dict'}")
                            requesting_client_sid = analysis_params.get('requesting_client_sid')
                            socketio.emit('cv_preview_response', {
                                'status': 'error',
                                'message': 'CV data missing voltage or current information'
                            }, room=requesting_client_sid)
                    else:
                        logger.error("CV data parsing returned None or empty result")
                        requesting_client_sid = analysis_params.get('requesting_client_sid')
                        socketio.emit('cv_preview_response', {
                            'status': 'error',
                            'message': 'Could not parse CV data for preview'
                        }, room=requesting_client_sid)

                finally:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                requesting_client_sid = analysis_params.get('requesting_client_sid')
                socketio.emit('cv_preview_response', {
                    'status': 'error',
                    'message': 'No file content received'
                }, room=requesting_client_sid)
        else:
            # Regular analysis mode - use existing logic
            original_filename = data.get('filename', 'unknown_file.txt')

            # Use agent's session for CV analysis parameters
            agent_session_id = agent_session_tracker.get('current_session')
            if not agent_session_id:
                logger.error("No active agent session for CV file processing")
                return
            session_id = agent_session_id
            live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
            if not live_analysis_params:
                logger.warning(f"No CV analysis parameters found in global agent session for file: {original_filename}")
                logger.warning("This may indicate session timeout or data loss. Sending acknowledgment to agent to prevent timeout.")
                # Send processing complete acknowledgment even if we can't process
                # This prevents agent from waiting 30 seconds for timeout
                agent_sid = agent_session_tracker.get('agent_sid')
                if agent_sid:
                    socketio.emit('file_processing_complete', {'filename': original_filename}, to=agent_sid)
                    logger.info(f"Sent processing complete ack (error) for '{original_filename}' to agent")
                return

            # Get selected electrodes from analysis params
            selected_electrodes = live_analysis_params.get('selected_electrodes', [])

            if selected_electrodes:
                # Process each selected electrode for CV
                for electrode_idx in selected_electrodes:
                    params_for_this_file = live_analysis_params.copy()
                    params_for_this_file['selected_electrode'] = electrode_idx

                    start_limited_file_task(target_function=process_cv_file_in_background,
                                                 original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                                 content=file_content,
                                                 params_for_this_file=params_for_this_file,
                                                 session_id=session_id)
            else:
                # Original averaging behavior for CV
                params_for_this_file = live_analysis_params.copy()
                start_limited_file_task(target_function=process_cv_file_in_background,
                                             original_filename=original_filename,
                                             content=file_content,
                                             params_for_this_file=params_for_this_file,
                                             session_id=session_id)

    except Exception as e:
        logger.error(f"Error handling CV data from agent: {e}", exc_info=True)
        if data.get('preview_mode', False):
            analysis_params = data.get('analysisParams', {})
            requesting_client_sid = analysis_params.get('requesting_client_sid')
            socketio.emit('cv_preview_response', {'status': 'error', 'message': str(e)}, room=requesting_client_sid)


# --- *** USER ID CONNECTION CHECK HANDLER ***
@socketio.on('check_agent_connection')
def handle_check_agent_connection(data):
    """
    Check if agent with given user_id is currently connected.
    Web viewers use this to verify their agent is online before starting analysis.
    """
    logger.info(f"Received 'check_agent_connection' from {request.sid}")

    user_id = data.get('user_id')

    if not user_id:
        logger.error("check_agent_connection missing user_id")
        emit('agent_connection_status', {
            'status': 'error',
            'message': 'User ID is required'
        })
        return

    # Look up agent by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)

    if agent_mapping:
        logger.info(f"Agent found for user_id: {user_id}")

        # Register this web viewer to the user_id (enable monitor mode)
        register_web_viewer_user(user_id, request.sid)

        # Get count of web viewers for this user_id
        web_viewers = get_web_viewers_by_user_id(user_id)
        viewer_count = len(web_viewers)

        # Check for ongoing analysis (for smart monitor mode)
        session_id = agent_mapping['session_id']
        ongoing_analysis = detect_ongoing_analysis(session_id)

        emit('agent_connection_status', {
            'status': 'success',
            'connected': True,
            'user_id': user_id,
            'connected_at': agent_mapping.get('connected_at'),
            'viewer_count': viewer_count,  # Let user know how many devices are monitoring
            'ongoing_analysis': ongoing_analysis  # {'swv': True/False, 'cv': True/False}
        })

        logger.info(f"Web viewer {request.sid} registered to user_id: {user_id}, total viewers: {viewer_count}, ongoing: {ongoing_analysis}")
    else:
        logger.warning(f"No agent found for user_id: {user_id}")
        emit('agent_connection_status', {
            'status': 'success',
            'connected': False,
            'user_id': user_id,
            'message': 'No agent found with this User ID. Please ensure your agent is running.'
        })


# --- *** MONITOR MODE: REQUEST HISTORICAL DATA HANDLER ***
@socketio.on('request_historical_data')
def handle_request_historical_data(data):
    """
    Send all existing analysis data to a monitor device.
    This allows monitor mode to see historical data, not just new updates.

    Used when a monitor device enters monitor mode and needs to sync
    with ongoing analysis that already has data.
    """
    logger.info(f"Received 'request_historical_data' from {request.sid}")

    user_id = data.get('user_id')
    analysis_type = data.get('analysis_type')  # 'swv' or 'cv'

    if not user_id or not analysis_type:
        logger.error(f"request_historical_data missing required fields: user_id={user_id}, analysis_type={analysis_type}")
        emit('historical_data_response', {
            'status': 'error',
            'message': 'user_id and analysis_type are required'
        })
        return

    # Get agent session by user_id
    agent_mapping = get_agent_session_by_user_id(user_id)
    if not agent_mapping:
        logger.warning(f"No agent found for user_id: {user_id}")
        emit('historical_data_response', {
            'status': 'error',
            'message': 'No active agent session found'
        })
        return

    session_id = agent_mapping['session_id']

    try:
        if analysis_type == 'swv':
            # Get all SWV data
            live_trend_data = get_session_data(session_id, 'live_trend_data', {})
            live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
            live_peak_detection_warnings = get_session_data(session_id, 'live_peak_detection_warnings', {})

            # Send comprehensive SWV data
            emit('historical_data_response', {
                'status': 'success',
                'analysis_type': 'swv',
                'data': {
                    'trend_data': live_trend_data,
                    'analysis_params': live_analysis_params,
                    'peak_detection_warnings': live_peak_detection_warnings
                }
            })
            logger.info(f"Sent SWV historical data to monitor device {request.sid} for user_id: {user_id}")

        elif analysis_type == 'cv':
            # Get all CV data
            cv_segments_data = get_session_data(session_id, 'cv_segments_data', {})
            live_trend_data = get_session_data(session_id, 'live_trend_data', {})
            cv_results = live_trend_data.get('cv_results', {})
            cv_analysis_params = get_session_data(session_id, 'cv_analysis_params', {})

            # Send comprehensive CV data
            emit('historical_data_response', {
                'status': 'success',
                'analysis_type': 'cv',
                'data': {
                    'segments_data': cv_segments_data,
                    'cv_results': cv_results,
                    'analysis_params': cv_analysis_params
                }
            })
            logger.info(f"Sent CV historical data to monitor device {request.sid} for user_id: {user_id}")

        else:
            emit('historical_data_response', {
                'status': 'error',
                'message': f'Unknown analysis_type: {analysis_type}'
            })

    except Exception as e:
        logger.error(f"Error getting historical data: {e}", exc_info=True)
        emit('historical_data_response', {
            'status': 'error',
            'message': str(e)
        })


# --- *** NEW *** SOCKET.IO EVENT HANDLER FOR EXPORTING DATA ---
@socketio.on('request_export_data')
def handle_export_request(data):
    """
    Handles a request from the client to export SWV data to CSV.
    Now exports all electrodes by default.
    """
    logger.info(f"Received 'request_export_data' from {request.sid} with data: {data}")
    try:
        # NEW: Get user_id from request
        user_id = data.get('user_id') if data else None

        if not user_id:
            logger.error("SWV export request missing user_id")
            emit('export_data_response', {'status': 'error', 'message': 'User ID is required for export.'})
            return

        # Get agent session by user_id
        agent_mapping = get_agent_session_by_user_id(user_id)
        if not agent_mapping:
            logger.error(f"No active agent session for user_id: {user_id}")
            emit('export_data_response', {'status': 'error', 'message': 'No active agent session found for this User ID.'})
            return

        agent_session_id = agent_mapping['session_id']
        logger.info(f"Exporting SWV data for user_id: {user_id}, session: {agent_session_id}")

        # Export all electrodes
        csv_data = generate_csv_data_all_electrodes(agent_session_id)
        if csv_data:
            emit('export_data_response', {'status': 'success', 'data': csv_data})
        else:
            emit('export_data_response', {'status': 'error', 'message': 'No data available to export.'})
    except Exception as e:
        logger.error(f"Failed to generate CSV for export: {e}", exc_info=True)
        emit('export_data_response', {'status': 'error', 'message': f'Export failed: {str(e)}'})


@socketio.on('request_export_cv_data')
def handle_cv_export_request(data):
    """
    Handles a request from the client to export CV data to CSV.
    Now exports all electrodes by default.
    """
    logger.info(f"Received 'request_export_cv_data' from {request.sid} with data: {data}")
    try:
        # NEW: Get user_id from request
        user_id = data.get('user_id') if data else None

        if not user_id:
            logger.error("CV export request missing user_id")
            emit('export_cv_data_response', {'status': 'error', 'message': 'User ID is required for export.'})
            return

        # Get agent session by user_id
        agent_mapping = get_agent_session_by_user_id(user_id)
        if not agent_mapping:
            logger.error(f"No active agent session for user_id: {user_id}")
            emit('export_cv_data_response', {'status': 'error', 'message': 'No active agent session found for this User ID.'})
            return

        agent_session_id = agent_mapping['session_id']
        logger.info(f"Exporting CV data for user_id: {user_id}, session: {agent_session_id}")

        # Export all electrodes
        csv_data = generate_cv_csv_data_all_electrodes(agent_session_id)
        if csv_data:
            emit('export_cv_data_response', {'status': 'success', 'data': csv_data})
        else:
            emit('export_cv_data_response', {'status': 'error', 'message': 'No CV data available to export.'})
    except Exception as e:
        logger.error(f"Failed to generate CV CSV for export: {e}", exc_info=True)
        emit('export_cv_data_response', {'status': 'error', 'message': f'CV export failed: {str(e)}'})


@socketio.on('request_export_frequency_map_data')
def handle_frequency_map_export_request(data):
    """
    Handles a request from the client to export Frequency Map data to CSV.
    """
    logger.info(f"Received 'request_export_frequency_map_data' from {request.sid} with data: {data}")
    try:
        current_electrode = data.get('current_electrode') if data else None
        export_all = data.get('export_all', False) if data else False

        # Get the agent's session ID (same as CV export)
        agent_session_id = agent_session_tracker.get('current_session')
        if not agent_session_id:
            logger.error("No active agent session for Frequency Map export")
            emit('export_frequency_map_data_response', {'status': 'error', 'message': 'No active agent session found.'})
            return

        if export_all:
            csv_data = generate_frequency_map_all_electrodes_csv(agent_session_id)
        else:
            csv_data = generate_frequency_map_csv_data(agent_session_id, current_electrode)

        if csv_data:
            emit('export_frequency_map_data_response', {'status': 'success', 'data': csv_data})
        else:
            emit('export_frequency_map_data_response', {'status': 'error', 'message': 'No Frequency Map data available to export.'})
    except Exception as e:
        logger.error(f"Failed to generate Frequency Map CSV for export: {e}", exc_info=True)
        emit('export_frequency_map_data_response', {'status': 'error', 'message': f'Frequency Map export failed: {str(e)}'})


@socketio.on('request_electrode_warnings')
def handle_electrode_warnings_request(data):
    """
    Handles a request from the client to get warnings for a specific electrode.
    """
    logger.info(f"Received 'request_electrode_warnings' from {request.sid} with data: {data}")
    try:
        # Get the agent's session ID
        agent_session_id = agent_session_tracker.get('current_session')
        if not agent_session_id:
            logger.error("No active agent session for warnings request")
            emit('electrode_warnings_response', {'status': 'error', 'message': 'No active agent session found.'})
            return

        # Get warnings from session data
        live_peak_detection_warnings = get_session_data(agent_session_id, 'live_peak_detection_warnings', {})
        electrode_index = data.get('electrode_index')
        electrode_key = str(electrode_index) if electrode_index is not None else 'averaged'
        warnings = live_peak_detection_warnings.get(electrode_key, [])

        emit('electrode_warnings_response', {
            'status': 'success',
            'warnings': warnings,
            'electrode_index': electrode_index
        })
    except Exception as e:
        logger.error(f"Failed to get electrode warnings: {e}", exc_info=True)
        emit('electrode_warnings_response', {
            'status': 'error',
            'message': f'Failed to get warnings: {str(e)}',
            'electrode_index': electrode_index
        })

@socketio.on('agent_consent')
def handle_agent_consent(data):
    """Handle consent logging from local agent"""
    logger.info(f"CONSENT HANDLER CALLED with data: {data}")

    # This will be called by the local agent when user gives consent
    user_id = data.get('user_id', 'unknown')
    session_id = data.get('session_id', 'unknown')
    user_ip = get_real_client_ip()

    logger.info(f"Processing consent - User: {user_id}, Session: {session_id}, IP: {user_ip}")
    logger.info(f"Redis client available: {redis_client is not None}")

    success = log_consent(user_id, user_ip, session_id)

    logger.info(f"Consent logging result: {success}")

    emit('consent_logged', {
        'status': 'success' if success else 'error',
        'user_id': user_id
    })



# --- HTTP Routes ---
# Health check endpoints for OpenShift
@app.route('/health')
def health_check():
    """Health check for OpenShift liveness probe"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'SACMES Web Frontend'
    }, 200


@app.route('/ready')
def readiness_check():
    """Readiness check for OpenShift readiness probe"""
    try:
        # Check if critical services are available
        redis_ok = True
        redis_message = "connected"
        try:
            if redis_client:
                redis_client.ping()
            else:
                redis_ok = False
                redis_message = "not configured"
        except Exception as e:
            redis_ok = False
            redis_message = f"error: {str(e)}"

        # Check if analyzers are loaded
        analyzers_ok = bool(analyze_cv_data and get_cv_segments)

        # Overall readiness
        is_ready = redis_ok and analyzers_ok

        return {
            'status': 'ready' if is_ready else 'not_ready',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'redis': {
                    'status': redis_message,
                    'healthy': redis_ok
                },
                'analyzers': {
                    'cv_analyzer': bool(analyze_cv_data),
                    'cv_segments': bool(get_cv_segments),
                    'healthy': analyzers_ok
                }
            }
        }, 200 if is_ready else 503

    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/consent.txt')
def get_consent():
    """Serve the consent text"""
    try:
        with open('consent.txt', 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except FileNotFoundError:
        return 'Consent text not found', 404
    except Exception as e:
        logger.error(f"Error reading consent file: {e}")
        return 'Error loading consent text', 500

@app.route('/cleanup-session', methods=['POST'])
def cleanup_session():
    """Handle session cleanup from client-side beacon"""
    try:
        data = request.get_json()
        if data and 'session_id' in data:
            session_id = data['session_id']
            logger.info(f"Cleaning up session {session_id} via beacon")
            clear_session_data(session_id)
            return {'status': 'success'}, 200
        return {'status': 'error', 'message': 'No session_id provided'}, 400
    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")
        return {'status': 'error', 'message': str(e)}, 500


@app.route('/debug/consent-logs', methods=['GET'])
def debug_consent_logs():
    """Debug endpoint to check consent logs in Redis"""
    try:
        if not redis_client:
            return {'status': 'error', 'message': 'Redis not available', 'fallback_file_exists': os.path.exists('consent_log.txt')}, 500

        # Get Redis info
        list_length = redis_client.llen('consent_log')
        logs = []

        if list_length > 0:
            # Get the last 10 entries
            raw_logs = redis_client.lrange('consent_log', 0, 9)
            for log_entry in raw_logs:
                try:
                    logs.append(json.loads(log_entry))
                except json.JSONDecodeError:
                    logs.append({'error': 'Invalid JSON', 'raw': log_entry})

        return {
            'status': 'success',
            'redis_available': True,
            'total_logs': list_length,
            'recent_logs': logs
        }, 200

    except Exception as e:
        logger.error(f"Error checking consent logs: {e}")
        return {'status': 'error', 'message': str(e)}, 500


def generate_cv_csv_data(session_id, current_electrode=None):
    """
    Generates a CSV formatted string from the current CV analysis data with AUC and peak separation data.

    Args:
        session_id: The session ID to get data from.
        current_electrode: The electrode index to export data for (None for averaged data).
    """
    # Get CV results from session data
    live_trend_data = get_session_data(session_id, 'live_trend_data', {})
    live_cv_results = live_trend_data.get('cv_results', {})

    if not live_cv_results:
        return ""

    # Also get analysis parameters from session
    live_cv_analysis_params = get_session_data(session_id, 'live_analysis_params', {})

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    # Write metadata section first
    writer.writerow(['# SACMES CV Analysis Report'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_info = f"Electrode {current_electrode + 1}" if current_electrode is not None else "Averaged"
    writer.writerow(['# Electrode:', electrode_info])
    writer.writerow([])

    # Write analysis parameters section
    writer.writerow(['# Analysis Parameters'])
    if live_cv_analysis_params:
        writer.writerow(['Scan Rate (V/s):', live_cv_analysis_params.get('scan_rate', 'N/A')])
        writer.writerow(['Mass Transport:', live_cv_analysis_params.get('mass_transport', 'N/A')])
        writer.writerow(['Analysis Type:', live_cv_analysis_params.get('SelectedOptions', 'N/A')])
        sg_mode = live_cv_analysis_params.get('sg_mode', 'auto')
        writer.writerow(['SG Filter Mode:', sg_mode])
        if sg_mode == 'manual':
            writer.writerow(['SG Window:', live_cv_analysis_params.get('sg_window', 'N/A')])
            writer.writerow(['SG Degree:', live_cv_analysis_params.get('sg_degree', 'N/A')])
        else:
            writer.writerow(['SG Window:', 'Auto (20% of data length)'])
            writer.writerow(['SG Degree:', 'Auto (2)'])

        # Add probe voltage information
        probe_voltages = live_cv_analysis_params.get('probe_voltages', [])
        if probe_voltages:
            probe_voltages_str = ', '.join([f"{v} V" for v in probe_voltages])
            writer.writerow(['Probe Voltages:', probe_voltages_str])
        else:
            writer.writerow(['Probe Voltages:', 'None'])
    writer.writerow([])

    # Write CV data header
    writer.writerow(['# CV Analysis Data'])
    header = [
        'File_Number',
        'Forward_Peak_Potential_V',
        'Forward_Peak_Current',
        'Forward_AUC_Charge',
        'Reverse_Peak_Potential_V',
        'Reverse_Peak_Current',
        'Reverse_AUC_Charge',
        'Peak_Separation_V'
    ]

    # Add probe voltage columns if probe data exists
    probe_voltages = live_cv_analysis_params.get('probe_voltages', []) if live_cv_analysis_params else []
    for i, voltage in enumerate(probe_voltages):
        probe_num = i + 1
        header.extend([
            f'Probe_{probe_num}_Voltage_V',
            f'Probe_{probe_num}_Forward_Current',
            f'Probe_{probe_num}_Reverse_Current'
        ])

    writer.writerow(header)

    # Get electrode key
    electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'

    # Get CV results for the specified electrode
    cv_electrode_results = live_cv_results.get(electrode_key, {})

    if cv_electrode_results:
        # Sort file numbers and write data rows
        file_numbers = sorted([int(f) for f in cv_electrode_results.keys()])

        for file_num in file_numbers:
            file_key = str(file_num)
            result = cv_electrode_results.get(file_key, {})

            if result and result.get('status') == 'success':
                forward_data = result.get('forward', {})
                reverse_data = result.get('reverse', {})
                peak_separation = result.get('peak_separation', '')
                probe_data = result.get('probe_data', {})

                row = [
                    file_num,
                    forward_data.get('peak_potential', ''),
                    forward_data.get('peak_current', ''),
                    forward_data.get('charge', ''),
                    reverse_data.get('peak_potential', ''),
                    reverse_data.get('peak_current', ''),
                    reverse_data.get('charge', ''),
                    peak_separation
                ]

                # Add probe data if available
                for i, voltage in enumerate(probe_voltages):
                    forward_probe_currents = probe_data.get('forward', [])
                    reverse_probe_currents = probe_data.get('reverse', [])

                    # Get current values for this probe voltage (index i)
                    forward_current = forward_probe_currents[i]['current'] if i < len(forward_probe_currents) else ''
                    reverse_current = reverse_probe_currents[i]['current'] if i < len(reverse_probe_currents) else ''

                    row.extend([
                        voltage,  # Probe voltage
                        forward_current,  # Forward current at this voltage
                        reverse_current   # Reverse current at this voltage
                    ])

                writer.writerow(row)

    return string_io.getvalue()


def generate_cv_csv_data_all_electrodes(session_id):
    """
    Generates a CSV formatted string with all electrodes CV data combined, including mean and std.

    Args:
        session_id: The session ID to get data from.
    """
    # Get CV results from session data
    live_trend_data = get_session_data(session_id, 'live_trend_data', {})
    live_cv_results = live_trend_data.get('cv_results', {})

    if not live_cv_results:
        return ""

    # Also get analysis parameters from session
    live_cv_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
    num_electrodes = live_cv_analysis_params.get('num_electrodes', 1)

    # Get all electrode keys (excluding 'averaged' if present)
    all_electrode_keys = [str(i) for i in range(num_electrodes)]

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    # Write metadata section
    writer.writerow(['# SACMES CV Analysis Report - All Electrodes'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_list = ', '.join([f'E{int(k)+1}' for k in all_electrode_keys])
    writer.writerow(['# Electrodes:', electrode_list])
    writer.writerow([])

    # Write analysis parameters section
    writer.writerow(['# Analysis Parameters'])
    if live_cv_analysis_params:
        writer.writerow(['Scan Rate (V/s):', live_cv_analysis_params.get('scan_rate', 'N/A')])
        writer.writerow(['Mass Transport:', live_cv_analysis_params.get('mass_transport', 'N/A')])
        writer.writerow(['Analysis Type:', live_cv_analysis_params.get('SelectedOptions', 'N/A')])
        sg_mode = live_cv_analysis_params.get('sg_mode', 'auto')
        writer.writerow(['SG Filter Mode:', sg_mode])
        if sg_mode == 'manual':
            writer.writerow(['SG Window:', live_cv_analysis_params.get('sg_window', 'N/A')])
            writer.writerow(['SG Degree:', live_cv_analysis_params.get('sg_degree', 'N/A')])
        else:
            writer.writerow(['SG Window:', 'Auto (20% of data length)'])
            writer.writerow(['SG Degree:', 'Auto (2)'])

        # Add probe voltage information
        probe_voltages = live_cv_analysis_params.get('probe_voltages', [])
        if probe_voltages:
            probe_voltages_str = ', '.join([f"{v} V" for v in probe_voltages])
            writer.writerow(['Probe Voltages:', probe_voltages_str])
        else:
            writer.writerow(['Probe Voltages:', 'None'])
    writer.writerow([])

    # Get all file numbers across all electrodes
    all_file_numbers = set()
    for electrode_key in all_electrode_keys:
        cv_electrode_results = live_cv_results.get(electrode_key, {})
        all_file_numbers.update([int(f) for f in cv_electrode_results.keys()])
    file_numbers = sorted(all_file_numbers)

    probe_voltages = live_cv_analysis_params.get('probe_voltages', []) if live_cv_analysis_params else []

    # Section 1: Forward Peak Current (A)
    writer.writerow(['# Forward Peak Current (A)'])
    header = ['File_Number'] + [f'E{int(k)+1}_Forward_Peak_A' for k in all_electrode_keys] + ['Mean_Forward_Peak_A', 'Std_Forward_Peak_A']
    writer.writerow(header)

    for file_num in file_numbers:
        file_key = str(file_num)
        row = [file_num]
        forward_peaks = []

        for electrode_key in all_electrode_keys:
            cv_electrode_results = live_cv_results.get(electrode_key, {})
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                forward_current = result.get('forward', {}).get('peak_current', None)
                forward_peaks.append(forward_current if forward_current is not None else 0)
                row.append(f'{forward_current:.6e}' if forward_current is not None else 'N/A')
            else:
                forward_peaks.append(0)
                row.append('N/A')

        # Calculate mean and std
        valid_peaks = [p for p in forward_peaks if p is not None and p != 0]
        if valid_peaks:
            mean_peak = np.mean(valid_peaks)
            std_peak = np.std(valid_peaks, ddof=1) if len(valid_peaks) > 1 else 0
            row.append(f'{mean_peak:.6e}')
            row.append(f'{std_peak:.6e}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 2: Forward AUC Charge (C)
    writer.writerow(['# Forward AUC Charge (C)'])
    header = ['File_Number'] + [f'E{int(k)+1}_Forward_Charge_C' for k in all_electrode_keys] + ['Mean_Forward_Charge_C', 'Std_Forward_Charge_C']
    writer.writerow(header)

    for file_num in file_numbers:
        file_key = str(file_num)
        row = [file_num]
        forward_charges = []

        for electrode_key in all_electrode_keys:
            cv_electrode_results = live_cv_results.get(electrode_key, {})
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                forward_charge = result.get('forward', {}).get('charge', None)
                forward_charges.append(forward_charge if forward_charge is not None else 0)
                row.append(f'{forward_charge:.6e}' if forward_charge is not None else 'N/A')
            else:
                forward_charges.append(0)
                row.append('N/A')

        # Calculate mean and std
        valid_charges = [c for c in forward_charges if c is not None and c != 0]
        if valid_charges:
            mean_charge = np.mean(valid_charges)
            std_charge = np.std(valid_charges, ddof=1) if len(valid_charges) > 1 else 0
            row.append(f'{mean_charge:.6e}')
            row.append(f'{std_charge:.6e}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 3: Reverse Peak Current (A)
    writer.writerow(['# Reverse Peak Current (A)'])
    header = ['File_Number'] + [f'E{int(k)+1}_Reverse_Peak_A' for k in all_electrode_keys] + ['Mean_Reverse_Peak_A', 'Std_Reverse_Peak_A']
    writer.writerow(header)

    for file_num in file_numbers:
        file_key = str(file_num)
        row = [file_num]
        reverse_peaks = []

        for electrode_key in all_electrode_keys:
            cv_electrode_results = live_cv_results.get(electrode_key, {})
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                reverse_current = result.get('reverse', {}).get('peak_current', None)
                reverse_peaks.append(reverse_current if reverse_current is not None else 0)
                row.append(f'{reverse_current:.6e}' if reverse_current is not None else 'N/A')
            else:
                reverse_peaks.append(0)
                row.append('N/A')

        # Calculate mean and std
        valid_peaks = [p for p in reverse_peaks if p is not None and p != 0]
        if valid_peaks:
            mean_peak = np.mean(valid_peaks)
            std_peak = np.std(valid_peaks, ddof=1) if len(valid_peaks) > 1 else 0
            row.append(f'{mean_peak:.6e}')
            row.append(f'{std_peak:.6e}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 4: Reverse AUC Charge (C)
    writer.writerow(['# Reverse AUC Charge (C)'])
    header = ['File_Number'] + [f'E{int(k)+1}_Reverse_Charge_C' for k in all_electrode_keys] + ['Mean_Reverse_Charge_C', 'Std_Reverse_Charge_C']
    writer.writerow(header)

    for file_num in file_numbers:
        file_key = str(file_num)
        row = [file_num]
        reverse_charges = []

        for electrode_key in all_electrode_keys:
            cv_electrode_results = live_cv_results.get(electrode_key, {})
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                reverse_charge = result.get('reverse', {}).get('charge', None)
                reverse_charges.append(reverse_charge if reverse_charge is not None else 0)
                row.append(f'{reverse_charge:.6e}' if reverse_charge is not None else 'N/A')
            else:
                reverse_charges.append(0)
                row.append('N/A')

        # Calculate mean and std
        valid_charges = [c for c in reverse_charges if c is not None and c != 0]
        if valid_charges:
            mean_charge = np.mean(valid_charges)
            std_charge = np.std(valid_charges, ddof=1) if len(valid_charges) > 1 else 0
            row.append(f'{mean_charge:.6e}')
            row.append(f'{std_charge:.6e}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 5: Peak Separation (V)
    writer.writerow(['# Peak Separation (V)'])
    header = ['File_Number'] + [f'E{int(k)+1}_Peak_Sep_V' for k in all_electrode_keys] + ['Mean_Peak_Sep_V', 'Std_Peak_Sep_V']
    writer.writerow(header)

    for file_num in file_numbers:
        file_key = str(file_num)
        row = [file_num]
        peak_seps = []

        for electrode_key in all_electrode_keys:
            cv_electrode_results = live_cv_results.get(electrode_key, {})
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                peak_sep = result.get('peak_separation', None)
                peak_seps.append(peak_sep if peak_sep is not None else 0)
                row.append(f'{peak_sep:.6f}' if peak_sep is not None else 'N/A')
            else:
                peak_seps.append(0)
                row.append('N/A')

        # Calculate mean and std
        valid_seps = [s for s in peak_seps if s is not None and s != 0]
        if valid_seps:
            mean_sep = np.mean(valid_seps)
            std_sep = np.std(valid_seps, ddof=1) if len(valid_seps) > 1 else 0
            row.append(f'{mean_sep:.6f}')
            row.append(f'{std_sep:.6f}')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)
    writer.writerow([])

    # Section 6: Probe Data (if available)
    if probe_voltages:
        # Forward Probe Currents
        for i, voltage in enumerate(probe_voltages):
            probe_num = i + 1
            writer.writerow([f'# Probe {probe_num} Forward Current at {voltage}V (A)'])
            header = ['File_Number'] + [f'E{int(k)+1}_Probe{probe_num}_Fwd_A' for k in all_electrode_keys] + ['Mean_Probe_Fwd_A', 'Std_Probe_Fwd_A']
            writer.writerow(header)

            for file_num in file_numbers:
                file_key = str(file_num)
                row = [file_num]
                probe_currents = []

                for electrode_key in all_electrode_keys:
                    cv_electrode_results = live_cv_results.get(electrode_key, {})
                    result = cv_electrode_results.get(file_key, {})
                    if result and result.get('status') == 'success':
                        probe_data = result.get('probe_data', {})
                        forward_probe_currents = probe_data.get('forward', [])
                        if i < len(forward_probe_currents):
                            current = forward_probe_currents[i].get('current')
                            probe_currents.append(current if current is not None else 0)
                            row.append(f'{current:.6e}' if current is not None else 'N/A')
                        else:
                            probe_currents.append(0)
                            row.append('N/A')
                    else:
                        probe_currents.append(0)
                        row.append('N/A')

                # Calculate mean and std
                valid_currents = [c for c in probe_currents if c is not None and c != 0]
                if valid_currents:
                    mean_current = np.mean(valid_currents)
                    std_current = np.std(valid_currents, ddof=1) if len(valid_currents) > 1 else 0
                    row.append(f'{mean_current:.6e}')
                    row.append(f'{std_current:.6e}')
                else:
                    row.extend(['N/A', 'N/A'])

                writer.writerow(row)
            writer.writerow([])

        # Reverse Probe Currents
        for i, voltage in enumerate(probe_voltages):
            probe_num = i + 1
            writer.writerow([f'# Probe {probe_num} Reverse Current at {voltage}V (A)'])
            header = ['File_Number'] + [f'E{int(k)+1}_Probe{probe_num}_Rev_A' for k in all_electrode_keys] + ['Mean_Probe_Rev_A', 'Std_Probe_Rev_A']
            writer.writerow(header)

            for file_num in file_numbers:
                file_key = str(file_num)
                row = [file_num]
                probe_currents = []

                for electrode_key in all_electrode_keys:
                    cv_electrode_results = live_cv_results.get(electrode_key, {})
                    result = cv_electrode_results.get(file_key, {})
                    if result and result.get('status') == 'success':
                        probe_data = result.get('probe_data', {})
                        reverse_probe_currents = probe_data.get('reverse', [])
                        if i < len(reverse_probe_currents):
                            current = reverse_probe_currents[i].get('current')
                            probe_currents.append(current if current is not None else 0)
                            row.append(f'{current:.6e}' if current is not None else 'N/A')
                        else:
                            probe_currents.append(0)
                            row.append('N/A')
                    else:
                        probe_currents.append(0)
                        row.append('N/A')

                # Calculate mean and std
                valid_currents = [c for c in probe_currents if c is not None and c != 0]
                if valid_currents:
                    mean_current = np.mean(valid_currents)
                    std_current = np.std(valid_currents, ddof=1) if len(valid_currents) > 1 else 0
                    row.append(f'{mean_current:.6e}')
                    row.append(f'{std_current:.6e}')
                else:
                    row.extend(['N/A', 'N/A'])

                writer.writerow(row)
            writer.writerow([])

    # Section 7: Summary Statistics per Electrode
    writer.writerow(['# Summary Statistics per Electrode'])
    summary_header = ['Electrode', 'Avg_Forward_Peak_A', 'Std_Forward_Peak_A', 'Avg_Forward_Charge_C', 'Std_Forward_Charge_C',
                      'Avg_Reverse_Peak_A', 'Std_Reverse_Peak_A', 'Avg_Reverse_Charge_C', 'Std_Reverse_Charge_C',
                      'Avg_Peak_Sep_V', 'Std_Peak_Sep_V']
    writer.writerow(summary_header)

    for electrode_key in all_electrode_keys:
        electrode_label = f'E{int(electrode_key)+1}'
        row = [electrode_label]

        cv_electrode_results = live_cv_results.get(electrode_key, {})

        # Collect all data for this electrode
        forward_peaks = []
        forward_charges = []
        reverse_peaks = []
        reverse_charges = []
        peak_seps = []

        for file_num in file_numbers:
            file_key = str(file_num)
            result = cv_electrode_results.get(file_key, {})
            if result and result.get('status') == 'success':
                forward_data = result.get('forward', {})
                reverse_data = result.get('reverse', {})

                fp = forward_data.get('peak_current')
                if fp is not None:
                    forward_peaks.append(fp)
                fc = forward_data.get('charge')
                if fc is not None:
                    forward_charges.append(fc)
                rp = reverse_data.get('peak_current')
                if rp is not None:
                    reverse_peaks.append(rp)
                rc = reverse_data.get('charge')
                if rc is not None:
                    reverse_charges.append(rc)
                ps = result.get('peak_separation')
                if ps is not None:
                    peak_seps.append(ps)

        # Calculate stats
        if forward_peaks:
            row.append(f'{np.mean(forward_peaks):.6e}')
            row.append(f'{np.std(forward_peaks, ddof=1):.6e}' if len(forward_peaks) > 1 else '0.000000e+00')
        else:
            row.extend(['N/A', 'N/A'])

        if forward_charges:
            row.append(f'{np.mean(forward_charges):.6e}')
            row.append(f'{np.std(forward_charges, ddof=1):.6e}' if len(forward_charges) > 1 else '0.000000e+00')
        else:
            row.extend(['N/A', 'N/A'])

        if reverse_peaks:
            row.append(f'{np.mean(reverse_peaks):.6e}')
            row.append(f'{np.std(reverse_peaks, ddof=1):.6e}' if len(reverse_peaks) > 1 else '0.000000e+00')
        else:
            row.extend(['N/A', 'N/A'])

        if reverse_charges:
            row.append(f'{np.mean(reverse_charges):.6e}')
            row.append(f'{np.std(reverse_charges, ddof=1):.6e}' if len(reverse_charges) > 1 else '0.000000e+00')
        else:
            row.extend(['N/A', 'N/A'])

        if peak_seps:
            row.append(f'{np.mean(peak_seps):.6f}')
            row.append(f'{np.std(peak_seps, ddof=1):.6f}' if len(peak_seps) > 1 else '0.000000')
        else:
            row.extend(['N/A', 'N/A'])

        writer.writerow(row)

    return string_io.getvalue()


def generate_frequency_map_csv_data(session_id, current_electrode=None):
    """
    Generates a CSV formatted string from Frequency Map analysis data.

    Args:
        session_id: Session ID to retrieve data from
        current_electrode: The electrode index to export data for (None for averaged data).

    Returns:
        CSV formatted string with frequency, peak, and charge data
    """
    # Get frequency map data from session
    frequency_map_data = get_session_data(session_id, 'frequency_map_data', {})

    if not frequency_map_data or 'results' not in frequency_map_data:
        return ""

    # Get analysis parameters
    live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})

    # Get electrode key
    electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'

    # Get results for this electrode
    electrode_results = frequency_map_data['results'].get(electrode_key, {})

    if not electrode_results:
        return ""

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    # Write metadata section
    writer.writerow(['# SACMES Frequency Map Analysis Report'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_info = f"Electrode {current_electrode + 1}" if current_electrode is not None else "Averaged"
    writer.writerow(['# Electrode:', electrode_info])
    writer.writerow([])

    # Write analysis parameters section
    writer.writerow(['# Analysis Parameters'])
    if live_analysis_params:
        # Filter settings
        sg_mode = live_analysis_params.get('sg_mode', 'auto')
        hampel_mode = live_analysis_params.get('hampel_mode', 'disabled')

        writer.writerow(['Hampel Filter Mode:', hampel_mode])
        if hampel_mode == 'manual':
            writer.writerow(['Hampel Window:', live_analysis_params.get('hampel_window', 'N/A')])
            writer.writerow(['Hampel Threshold:', live_analysis_params.get('hampel_threshold', 'N/A')])
        elif hampel_mode == 'auto':
            writer.writerow(['Hampel Window:', 'Auto (1/10 FWHM)'])
            writer.writerow(['Hampel Threshold:', 'Auto (3×MAD)'])

        writer.writerow(['SG Filter Mode:', sg_mode])
        if sg_mode == 'manual':
            writer.writerow(['SG Window:', live_analysis_params.get('sg_window', 'N/A')])
            writer.writerow(['SG Degree:', live_analysis_params.get('sg_degree', 'N/A')])
        else:
            writer.writerow(['SG Window:', 'Auto (1/3 FWHM)'])
            writer.writerow(['SG Degree:', 'Auto (2)'])

        writer.writerow(['Polyfit Degree:', live_analysis_params.get('polyfit_degree', 'N/A')])
        writer.writerow(['Cutoff Frequency (Hz):', live_analysis_params.get('cutoff_frequency', 'N/A')])

    writer.writerow([])

    # Write frequency map data header
    writer.writerow(['# Frequency Map Data'])
    header = [
        'Frequency_Hz',
        'Peak_Current_A',
        'Peak_Potential_V',
        'Charge_C',
        'Filename'
    ]
    writer.writerow(header)

    # Sort frequencies in ascending order
    frequencies = sorted([int(freq) for freq in electrode_results.keys()])

    # Write data rows
    for freq in frequencies:
        freq_key = str(freq)
        result = electrode_results.get(freq_key, {})

        if result:
            peak_value_A = result.get('peak_value', 0)
            peak_potential_V = result.get('peak_potential')  # NEW: Peak voltage
            charge_C = result.get('charge', 0)
            filename = result.get('filename', '')

            row = [
                freq,
                f"{peak_value_A:.6e}",  # Scientific notation in Amperes
                f"{peak_potential_V:.4f}" if peak_potential_V is not None else 'N/A',  # Peak voltage in Volts
                f"{charge_C:.6e}",  # Scientific notation in Coulombs
                filename
            ]
            writer.writerow(row)

    writer.writerow([])

    # Write summary statistics
    writer.writerow(['# Summary Statistics'])

    if frequencies:
        charges = [electrode_results[str(freq)].get('charge', 0) for freq in frequencies]
        peaks_A = [electrode_results[str(freq)].get('peak_value', 0) for freq in frequencies]

        writer.writerow(['Total Frequencies Analyzed:', len(frequencies)])
        writer.writerow(['Frequency Range (Hz):', f"{min(frequencies)} - {max(frequencies)}"])
        writer.writerow(['Average Charge (C):', f"{sum(charges) / len(charges):.6e}"])
        writer.writerow(['Average Peak Current (A):', f"{sum(peaks_A) / len(peaks_A):.6e}"])
        writer.writerow(['Max Charge (C):', f"{max(charges):.6e}"])
        writer.writerow(['Min Charge (C):', f"{min(charges):.6e}"])

    return string_io.getvalue()


def generate_frequency_map_all_electrodes_csv(session_id):
    """
    Generates CSV with charge and peak current data for all electrodes.
    Format: Metadata + Charge section (Freq, Averaged, Electrodes, Std) + Peak section (Freq, Averaged, Electrodes, Std)

    Args:
        session_id: Session ID to retrieve data from

    Returns:
        CSV formatted string with all electrodes data
    """
    frequency_map_data = get_session_data(session_id, 'frequency_map_data', {})

    if not frequency_map_data or 'results' not in frequency_map_data:
        return ""

    live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
    all_results = frequency_map_data['results']

    if not all_results:
        return ""

    # Get individual electrodes (exclude 'averaged' if it exists)
    individual_electrodes = sorted([int(k) for k in all_results.keys() if k != 'averaged'])

    # Get all frequencies from all electrodes (union of all frequency keys)
    all_freq_set = set()
    for electrode_data in all_results.values():
        if isinstance(electrode_data, dict):
            all_freq_set.update(electrode_data.keys())

    frequencies = sorted([int(freq) for freq in all_freq_set])

    if not frequencies:
        return ""

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    # Write metadata
    writer.writerow(['# SACMES Frequency Map Analysis Report'])
    writer.writerow(['# Export Date:', str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
    electrode_list = [f"Electrode {idx + 1}" for idx in individual_electrodes]
    writer.writerow(['# Electrodes:', ', '.join(electrode_list)])
    writer.writerow(['# Number of Frequencies:', len(frequencies)])
    writer.writerow([])

    # Write Charge data section
    writer.writerow(['# Charge (C)'])
    charge_header = ['Frequency (Hz)', 'Averaged'] + [f"Electrode {idx + 1}" for idx in individual_electrodes] + ['Std']
    writer.writerow(charge_header)

    for freq in frequencies:
        freq_key = str(freq)
        row = [freq]
        charge_values = []

        # Collect individual electrode charges
        for electrode_idx in individual_electrodes:
            electrode_key = str(electrode_idx)
            electrode_data = all_results.get(electrode_key, {})
            result = electrode_data.get(freq_key)
            if result and 'charge' in result:
                charge_values.append(result['charge'])
            else:
                charge_values.append(None)

        # Calculate averaged and std
        valid_charges = [c for c in charge_values if c is not None]
        if valid_charges:
            mean_charge = np.mean(valid_charges)
            std_charge = np.std(valid_charges, ddof=1) if len(valid_charges) > 1 else 0
            row.append(f"{mean_charge:.6e}")
        else:
            row.append('N/A')

        # Add individual values
        for charge in charge_values:
            row.append(f"{charge:.6e}" if charge is not None else 'N/A')

        # Add std
        if valid_charges and len(valid_charges) > 1:
            row.append(f"{std_charge:.6e}")
        elif valid_charges:
            row.append('0.000000e+00')
        else:
            row.append('N/A')

        writer.writerow(row)

    writer.writerow([])

    # Write Peak Current data section
    writer.writerow(['# Peak Current (A)'])
    peak_header = ['Frequency (Hz)', 'Averaged'] + [f"Electrode {idx + 1}" for idx in individual_electrodes] + ['Std']
    writer.writerow(peak_header)

    for freq in frequencies:
        freq_key = str(freq)
        row = [freq]
        peak_values = []

        # Collect individual electrode peaks
        for electrode_idx in individual_electrodes:
            electrode_key = str(electrode_idx)
            electrode_data = all_results.get(electrode_key, {})
            result = electrode_data.get(freq_key)
            if result and 'peak_value' in result:
                peak_values.append(result['peak_value'])
            else:
                peak_values.append(None)

        # Calculate averaged and std
        valid_peaks = [p for p in peak_values if p is not None]
        if valid_peaks:
            mean_peak = np.mean(valid_peaks)
            std_peak = np.std(valid_peaks, ddof=1) if len(valid_peaks) > 1 else 0
            row.append(f"{mean_peak:.6e}")
        else:
            row.append('N/A')

        # Add individual values
        for peak in peak_values:
            row.append(f"{peak:.6e}" if peak is not None else 'N/A')

        # Add std
        if valid_peaks and len(valid_peaks) > 1:
            row.append(f"{std_peak:.6e}")
        elif valid_peaks:
            row.append('0.000000e+00')
        else:
            row.append('N/A')

        writer.writerow(row)

    writer.writerow([])

    # Write Peak Potential data section
    writer.writerow(['# Peak Potential (V)'])
    potential_header = ['Frequency (Hz)', 'Averaged'] + [f"Electrode {idx + 1}" for idx in individual_electrodes] + ['Std']
    writer.writerow(potential_header)

    for freq in frequencies:
        freq_key = str(freq)
        row = [freq]
        potential_values = []

        # Collect individual electrode peak potentials
        for electrode_idx in individual_electrodes:
            electrode_key = str(electrode_idx)
            electrode_data = all_results.get(electrode_key, {})
            result = electrode_data.get(freq_key)
            if result and 'peak_potential' in result and result['peak_potential'] is not None:
                potential_values.append(result['peak_potential'])
            else:
                potential_values.append(None)

        # Calculate averaged and std
        valid_potentials = [v for v in potential_values if v is not None]
        if valid_potentials:
            mean_potential = np.mean(valid_potentials)
            std_potential = np.std(valid_potentials, ddof=1) if len(valid_potentials) > 1 else 0
            row.append(f"{mean_potential:.4f}")
        else:
            row.append('N/A')

        # Add individual values
        for potential in potential_values:
            row.append(f"{potential:.4f}" if potential is not None else 'N/A')

        # Add std
        if valid_potentials and len(valid_potentials) > 1:
            row.append(f"{std_potential:.4f}")
        elif valid_potentials:
            row.append('0.0000')
        else:
            row.append('N/A')

        writer.writerow(row)

    return string_io.getvalue()


# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    logger.info("Starting SACMES server in development mode...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)