# app.py (Version with CSV Export Functionality)

import eventlet

eventlet.monkey_patch()

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
# Enhanced SocketIO configuration for OpenShift deployment
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,

    # OpenShift-optimized settings to prevent disconnections
    ping_timeout=60,        # Extended timeout for heavy operations (default: 20s)
    ping_interval=25,       # More frequent heartbeats (default: 25s)

    # Prevent disconnections during processing
    allow_upgrades=True,
    max_http_buffer_size=10000000,  # 10MB for large CV data files

    # Transport optimization for container environments
    transports=['websocket', 'polling'],

    # Additional stability settings
    always_connect=True,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    randomization_factor=0.5
)

# Redis connection - construct URL securely
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Allow override via environment variable
REDIS_URL = os.environ.get('REDIS_URL', REDIS_URL)
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Successfully connected to Redis")
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
fallback_data = {
    'agent_sid': None,
    'web_viewer_sids': set(),
    'live_analysis_params': {},
    'live_trend_data': {},
    'live_peak_detection_warnings': {},
    'validation_error_sent': False
}

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

    # Fallback to in-memory storage
    return fallback_data.get(key, default)

def set_session_data(session_id, key, value):
    """Set session-specific data in Redis or fallback"""
    if redis_client:
        try:
            redis_client.hset(f"session:{session_id}", key, json.dumps(value, default=str))
            redis_client.expire(f"session:{session_id}", 86400)  # 24 hour expiry
            return True
        except Exception as e:
            logger.error(f"Redis set error for session {session_id}, key {key}: {e}")

    # Fallback to in-memory storage
    fallback_data[key] = value
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

    # Clear fallback data (this affects all users when Redis is down)
    for key in fallback_data:
        if isinstance(fallback_data[key], dict):
            fallback_data[key] = {}
        elif isinstance(fallback_data[key], set):
            fallback_data[key] = set()
        else:
            fallback_data[key] = None

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
def calculate_trends(raw_peaks, params, selected_electrode_key='averaged'):
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
    kdm_trend = [None] * num_files

    # Get electrode-specific data
    electrode_data = raw_peaks.get(selected_electrode_key, {})

    for i in range(num_files):
        file_num = i + 1  # File numbers are 1-based
        for freq_str in peak_current_trends:
            peak = electrode_data.get(freq_str, {}).get(str(file_num))
            if peak is not None: peak_current_trends[freq_str][i] = peak
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
        low_peak = peak_current_trends.get(low_freq_str, [])[i]
        high_peak = peak_current_trends.get(high_freq_str, [])[i]
        if low_peak is not None and high_peak is not None and high_peak != 0:
            kdm_trend[i] = low_peak / high_peak
    return {"x_axis_values": x_axis_values, "peak_current_trends": peak_current_trends,
            "normalized_peak_trends": normalized_peak_trends, "kdm_trend": kdm_trend}


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
                            if session_key.decode() != 'session:global_agent_session':
                                session_data = redis_client.hget(session_key, 'web_viewer_sids')
                                if session_data:
                                    viewer_sids = json.loads(session_data)
                                    all_web_viewer_sids.extend(list(viewer_sids))
                    except Exception as e:
                        logger.error(f"Error getting all web viewers for CV validation error: {e}")

                if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
                    all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

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
                set_session_data(session_id, 'live_trend_data', live_trend_data)

        # Send CV update to ALL web viewers across all sessions
        all_web_viewer_sids = []
        if redis_client:
            try:
                session_keys = redis_client.keys("session:*")
                for session_key in session_keys:
                    if session_key.decode() != 'session:global_agent_session':  # Skip agent session
                        session_data = redis_client.hget(session_key, 'web_viewer_sids')
                        if session_data:
                            viewer_sids = json.loads(session_data)
                            all_web_viewer_sids.extend(list(viewer_sids))
            except Exception as e:
                logger.error(f"Error getting all web viewers for CV update: {e}")

        # Also check fallback storage
        if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
            all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

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


def process_file_in_background(original_filename, content, params_for_this_file, session_id):
    logger.info(f"BACKGROUND_TASK: Started processing for '{original_filename}' in session {session_id}")
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
                            if session_key.decode() != 'session:global_agent_session':
                                session_data = redis_client.hget(session_key, 'web_viewer_sids')
                                if session_data:
                                    viewer_sids = json.loads(session_data)
                                    all_web_viewer_sids.extend(list(viewer_sids))
                    except Exception as e:
                        logger.error(f"Error getting all web viewers for validation error: {e}")

                if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
                    all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

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
        full_trends = calculate_trends(live_trend_data.get('raw_peaks', {}), live_analysis_params, electrode_key)
        # Send update to ALL web viewers across all sessions
        all_web_viewer_sids = []
        if redis_client:
            try:
                session_keys = redis_client.keys("session:*")
                for session_key in session_keys:
                    if session_key.decode() != 'session:global_agent_session':  # Skip agent session
                        session_data = redis_client.hget(session_key, 'web_viewer_sids')
                        if session_data:
                            viewer_sids = json.loads(session_data)
                            all_web_viewer_sids.extend(list(viewer_sids))
            except Exception as e:
                logger.error(f"Error getting all web viewers for analysis update: {e}")

        # Also check fallback storage
        if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
            all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

        if all_web_viewer_sids:
            # Send update with electrode-specific information
            response_data = {
                "filename": base_filename,  # Use base filename for frontend processing
                "individual_analysis": analysis_result,
                "trend_data": full_trends,
                "electrode_index": selected_electrode,
                "peak_detection_warnings": live_peak_detection_warnings.get(electrode_key, [])
            }
            socketio.emit('live_analysis_update', response_data, to=all_web_viewer_sids)
            logger.info(f"Sent analysis update to {len(all_web_viewer_sids)} web viewers")

        # Send processing complete acknowledgment to agent
        agent_sid = agent_session_tracker.get('agent_sid')
        if agent_sid:
            socketio.emit('file_processing_complete', {'filename': base_filename}, to=agent_sid)
            logger.info(f"BACKGROUND_TASK: Sent processing complete ack for '{base_filename}' to agent")

    except Exception as e:
        logger.error(f"BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
        # Send error acknowledgment to agent even if processing failed
        agent_sid = agent_session_tracker.get('agent_sid')
        if agent_sid:
            socketio.emit('file_processing_complete', {'filename': original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename}, to=agent_sid)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"BACKGROUND_TASK: Finished job for '{original_filename}'.")


# --- *** NEW *** HELPER FUNCTION TO GENERATE CSV DATA ---
def generate_csv_data(current_electrode=None):
    """
    Generates a CSV formatted string from the current trend data with filter parameters and QC metrics.

    Args:
        current_electrode: The electrode index to export data for (None for averaged data).
    """
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
    header.append('KDM')
    writer.writerow(header)

    # Recalculate full trends to ensure data is consistent
    full_trends = calculate_trends(live_trend_data.get('raw_peaks', {}), live_analysis_params, electrode_key)

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


# --- Socket.IO Event Handlers (Connect, Disconnect, Start Session are Unchanged) ---
# Global session tracker for agent-web viewer communication
agent_session_tracker = {'current_session': None, 'agent_sid': None}

@socketio.on('connect')
def handle_connect():
    # Check if this is an agent with a specific session_id in auth data
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None

    if token and token == AGENT_AUTH_TOKEN:
        # For agents: use a global session approach
        agent_session_id = 'global_agent_session'
        session['session_id'] = agent_session_id
        session_id = agent_session_id

        # Update global agent tracker
        agent_session_tracker['current_session'] = session_id
        agent_session_tracker['agent_sid'] = request.sid

        set_session_agent_sid(session_id, request.sid)
        logger.info(f"AGENT connected. SID: {request.sid}, Global Session: {session_id}")

        # Notify ALL web viewers in ALL sessions about agent connection
        all_web_viewer_sids = []
        if redis_client:
            try:
                # Get all session keys
                session_keys = redis_client.keys("session:*")
                for session_key in session_keys:
                    session_data = redis_client.hget(session_key, 'web_viewer_sids')
                    if session_data:
                        viewer_sids = json.loads(session_data)
                        all_web_viewer_sids.extend(list(viewer_sids))
            except Exception as e:
                logger.error(f"Error getting all web viewers: {e}")

        # Also check fallback storage
        if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
            all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

        if all_web_viewer_sids:
            emit('agent_status', {'status': 'connected'}, to=all_web_viewer_sids)
            logger.info(f"Notified {len(all_web_viewer_sids)} web viewers of agent connection")
        else:
            logger.info("No web viewers to notify of agent connection")

        # Send session info back to agent
        emit('session_info', {'session_id': session_id})

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
    logger.info(f"Client disconnected: {request.sid}, Session: {session_id}. Reason: {request.args.get('reason', 'N/A')}")

    # Check if this was the global agent disconnection
    if request.sid == agent_session_tracker.get('agent_sid'):
        # Clear agent tracker
        agent_session_tracker['current_session'] = None
        agent_session_tracker['agent_sid'] = None

        # Also clear from session storage
        set_session_agent_sid('global_agent_session', None)
        logger.warning(f"Global Agent has disconnected: {request.sid}")

        # Notify ALL web viewers across all sessions
        all_web_viewer_sids = []
        if redis_client:
            try:
                session_keys = redis_client.keys("session:*")
                for session_key in session_keys:
                    session_data = redis_client.hget(session_key, 'web_viewer_sids')
                    if session_data:
                        viewer_sids = json.loads(session_data)
                        all_web_viewer_sids.extend(list(viewer_sids))
            except Exception as e:
                logger.error(f"Error getting all web viewers for disconnect: {e}")

        # Also check fallback storage
        if not all_web_viewer_sids and fallback_data.get('web_viewer_sids'):
            all_web_viewer_sids.extend(list(fallback_data['web_viewer_sids']))

        if all_web_viewer_sids:
            emit('agent_status', {'status': 'disconnected'}, to=all_web_viewer_sids)
            logger.info(f"Notified {len(all_web_viewer_sids)} web viewers of agent disconnection")
    else:
        # Check if this was a web viewer disconnection
        web_viewer_sids = get_session_web_viewer_sids(session_id)
        if request.sid in web_viewer_sids:
            remove_session_web_viewer_sid(session_id, request.sid)
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


@socketio.on('start_analysis_session')
def handle_start_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'start_analysis_session' from {request.sid}, Session: {session_id}")

    if 'analysisParams' in data:
        set_session_data(session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(session_id, 'live_trend_data', {"raw_peaks": {}})
        set_session_data(session_id, 'live_peak_detection_warnings', {})
        set_session_data(session_id, 'validation_error_sent', False)
        logger.info(f"Analysis session started for session {session_id}. Params set and trend data reset.")

    # Use global agent tracker
    agent_sid = agent_session_tracker.get('agent_sid')

    # Fallback: check global agent session
    if not agent_sid:
        agent_sid = get_session_agent_sid('global_agent_session')
        if agent_sid:
            agent_session_tracker['agent_sid'] = agent_sid
            logger.info(f"Retrieved agent SID from storage: {agent_sid}")

    if 'filters' in data and agent_sid:
        live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')

        # Store analysis params in global agent session for data processing
        set_session_data('global_agent_session', 'live_analysis_params', data['analysisParams'])
        set_session_data('global_agent_session', 'live_trend_data', {"raw_peaks": {}})
        set_session_data('global_agent_session', 'live_peak_detection_warnings', {})
        set_session_data('global_agent_session', 'validation_error_sent', False)

        logger.info(f"Sending filters to global agent {agent_sid}: {filters}")
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent.'})
    elif not agent_sid:
        logger.warning("No global agent found")
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('start_cv_analysis_session')
def handle_start_cv_analysis_session(data):
    session_id = get_session_id()
    logger.info(f"Received 'start_cv_analysis_session' from {request.sid}, Session: {session_id}")

    if 'analysisParams' in data:
        set_session_data(session_id, 'live_analysis_params', data['analysisParams'])
        set_session_data(session_id, 'live_trend_data', {"cv_results": {}})
        set_session_data(session_id, 'validation_error_sent', False)
        logger.info(f"CV Analysis session started for session {session_id}. Params set and CV data reset.")

    # Use global agent tracker
    agent_sid = agent_session_tracker.get('agent_sid')

    # Fallback: check global agent session
    if not agent_sid:
        agent_sid = get_session_agent_sid('global_agent_session')
        if agent_sid:
            agent_session_tracker['agent_sid'] = agent_sid
            logger.info(f"Retrieved agent SID from storage for CV: {agent_sid}")

    if 'filters' in data and agent_sid:
        live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')

        # Store CV analysis params in global agent session for data processing
        set_session_data('global_agent_session', 'live_analysis_params', data['analysisParams'])
        set_session_data('global_agent_session', 'live_trend_data', {"cv_results": {}})
        set_session_data('global_agent_session', 'validation_error_sent', False)

        logger.info(f"Sending CV filters to global agent {agent_sid}: {filters}")
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_cv_session', {'status': 'success', 'message': 'CV Instructions sent.'})
    elif not agent_sid:
        logger.warning("No global agent found for CV analysis")
        emit('ack_start_cv_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


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


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    # Verify this is from the global agent
    if request.sid != agent_session_tracker.get('agent_sid'):
        logger.warning(f"Received data from non-agent SID: {request.sid}")
        return

    original_filename = data.get('filename', 'unknown_file.txt')
    file_content = data.get('content', '')
    logger.info(f"Received data from agent: {original_filename}")

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

    # Use global agent session for analysis parameters
    live_analysis_params = get_session_data('global_agent_session', 'live_analysis_params', {})
    if not live_analysis_params:
        logger.warning("No analysis parameters found in global agent session")
        return

    # Support both old format (_60Hz_1.) and new format (_60Hz_1 or CV_60Hz_1)
    match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
    if not match:
        logger.warning(f"Filename does not match expected pattern: {original_filename}")
        return

    # Get selected electrodes from analysis params
    selected_electrodes = live_analysis_params.get('selected_electrodes', [])

    if selected_electrodes:
        # Process each selected electrode in parallel
        for electrode_idx in selected_electrodes:
            params_for_this_file = live_analysis_params.copy()
            params_for_this_file['frequency'] = int(match.group(1))
            params_for_this_file['selected_electrode'] = electrode_idx
            params_for_this_file.setdefault('low_xstart', None)
            params_for_this_file.setdefault('low_xend', None)
            params_for_this_file.setdefault('high_xstart', None)
            params_for_this_file.setdefault('high_xend', None)

            socketio.start_background_task(target=process_file_in_background,
                                         original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                         content=file_content,
                                         params_for_this_file=params_for_this_file,
                                         session_id='global_agent_session')
    else:
        # Original averaging behavior
        params_for_this_file = live_analysis_params.copy()
        params_for_this_file['frequency'] = int(match.group(1))
        params_for_this_file.setdefault('low_xstart', None)
        params_for_this_file.setdefault('low_xend', None)
        params_for_this_file.setdefault('high_xstart', None)
        params_for_this_file.setdefault('high_xend', None)

        socketio.start_background_task(target=process_file_in_background,
                                     original_filename=original_filename,
                                     content=file_content,
                                     params_for_this_file=params_for_this_file,
                                     session_id='global_agent_session')


@socketio.on('stream_cv_data')
def handle_cv_instrument_data(data):
    session_id = get_session_id()
    agent_sid = get_session_agent_sid(session_id)
    if request.sid != agent_sid:
        return

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
        }, to=agent_sid)
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

            socketio.start_background_task(target=process_cv_file_in_background,
                                         original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                         content=file_content,
                                         params_for_this_file=params_for_this_file,
                                         session_id=session_id)
    else:
        # Original averaging behavior for CV
        params_for_this_file = live_analysis_params.copy()
        socketio.start_background_task(target=process_cv_file_in_background,
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

        # Fallback: check global agent session
        if not agent_sid:
            agent_sid = get_session_agent_sid('global_agent_session')
            if agent_sid:
                agent_session_tracker['agent_sid'] = agent_sid
                logger.info(f"Retrieved agent SID from storage for CV preview: {agent_sid}")

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

        # Try to use preview content from session first to avoid large payload transfers
        session_id = 'global_agent_session'
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

        # If no content provided, try to get from session (preview content)
        if not file_content:
            session_id = 'global_agent_session'
            file_content = get_session_data(session_id, 'cv_preview_content', '')
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
        eventlet.sleep(0)

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
        eventlet.sleep(0)

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
        eventlet.sleep(0)

        # Call the original function but with yielding
        result = get_cv_segments(file_path, params, selected_electrode)

        # Yield control after processing
        eventlet.sleep(0)

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

                            # Store preview content in session for segment detection (avoid re-sending large data)
                            session_id = 'global_agent_session'
                            set_session_data(session_id, 'cv_preview_content', file_content)
                            set_session_data(session_id, 'cv_preview_client_sid', requesting_client_sid)
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

            # Use global agent session for CV analysis parameters
            session_id = 'global_agent_session'
            live_analysis_params = get_session_data(session_id, 'live_analysis_params', {})
            if not live_analysis_params:
                logger.warning("No CV analysis parameters found in global agent session")
                return

            # Get selected electrodes from analysis params
            selected_electrodes = live_analysis_params.get('selected_electrodes', [])

            if selected_electrodes:
                # Process each selected electrode for CV
                for electrode_idx in selected_electrodes:
                    params_for_this_file = live_analysis_params.copy()
                    params_for_this_file['selected_electrode'] = electrode_idx

                    socketio.start_background_task(target=process_cv_file_in_background,
                                                 original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                                 content=file_content,
                                                 params_for_this_file=params_for_this_file,
                                                 session_id=session_id)
            else:
                # Original averaging behavior for CV
                params_for_this_file = live_analysis_params.copy()
                socketio.start_background_task(target=process_cv_file_in_background,
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


# --- *** NEW *** SOCKET.IO EVENT HANDLER FOR EXPORTING DATA ---
@socketio.on('request_export_data')
def handle_export_request(data):
    """
    Handles a request from the client to export data to CSV.
    """
    logger.info(f"Received 'request_export_data' from {request.sid} with data: {data}")
    try:
        # Get current electrode from request data
        current_electrode = data.get('current_electrode') if data else None
        csv_data = generate_csv_data(current_electrode)
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
    """
    logger.info(f"Received 'request_export_cv_data' from {request.sid} with data: {data}")
    try:
        # Get current electrode from request data
        current_electrode = data.get('current_electrode') if data else None
        csv_data = generate_cv_csv_data(current_electrode)
        if csv_data:
            emit('export_cv_data_response', {'status': 'success', 'data': csv_data})
        else:
            emit('export_cv_data_response', {'status': 'error', 'message': 'No CV data available to export.'})
    except Exception as e:
        logger.error(f"Failed to generate CV CSV for export: {e}", exc_info=True)
        emit('export_cv_data_response', {'status': 'error', 'message': f'CV export failed: {str(e)}'})


@socketio.on('request_electrode_warnings')
def handle_electrode_warnings_request(data):
    """
    Handles a request from the client to get warnings for a specific electrode.
    """
    logger.info(f"Received 'request_electrode_warnings' from {request.sid} with data: {data}")
    try:
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


def generate_cv_csv_data(current_electrode=None):
    """
    Generates a CSV formatted string from the current CV analysis data with AUC and peak separation data.

    Args:
        current_electrode: The electrode index to export data for (None for averaged data).
    """
    # Get CV results from session data
    session_id = 'global_agent_session'
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


# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    logger.info("Starting SACMES server in development mode...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)