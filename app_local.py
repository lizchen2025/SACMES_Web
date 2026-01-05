# app_local.py - SACMES Local Version (Standalone Desktop Application)
# Simplified version without Redis, Gevent, multi-user support, and agent connection
# Designed to run as a local Flask server accessed via browser

import os
import re
import logging
import sys
import io
import csv
import json
import threading
import time
import numpy as np
from datetime import datetime
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Logging Setup ---
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)  # Enable DEBUG level for troubleshooting
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable DEBUG level for troubleshooting
logger.addHandler(log_handler)
logger.propagate = False

# Add file handler for persistent logs
file_handler = logging.FileHandler('sacmes_local_debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# --- Import Data Processing Modules ---
try:
    from data_processing.swv_analyzer import analyze_swv_data
    from data_processing.cv_analyzer import analyze_cv_data, get_cv_segments
    logger.info("Successfully imported analyzers.")
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
    # 1. File extension validation
    allowed_extensions = {'.txt', '.dta', '.csv'}
    file_ext = os.path.splitext(filename.lower())[1]
    if file_ext not in allowed_extensions:
        return False, f"File extension '{file_ext}' not allowed. Only .txt, .dta, .csv files are accepted."

    # 2. File size validation (5MB limit)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    content_size = len(content.encode('utf-8'))
    if content_size > MAX_FILE_SIZE:
        return False, f"File size ({content_size / 1024 / 1024:.1f}MB) exceeds 5MB limit."

    # 3. Content validation
    if not validate_content_safety(content):
        return False, "File contains binary or suspicious content. Only text-based data files are allowed."

    return True, ""

def validate_content_safety(content, sample_size=2048):
    """
    Efficiently validate content is text-based and safe.
    """
    # Sample beginning and end of file
    if len(content) <= sample_size:
        sample = content
    else:
        half_sample = sample_size // 2
        sample = content[:half_sample] + content[-half_sample:]

    # Check for binary content
    if '\x00' in sample:
        return False

    # Count printable characters
    printable_count = sum(1 for char in sample if char.isprintable() or char in '\n\r\t')

    # If more than 20% non-printable, likely binary
    if len(sample) > 0 and (printable_count / len(sample)) < 0.8:
        return False

    # Check for suspicious binary patterns
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

# --- Memory Store (Replaces Redis) ---
class MemoryStore:
    """
    In-memory storage for single-user local application.
    Replaces Redis session management.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.clear()

    def clear(self):
        """Clear all stored data"""
        with self.lock:
            self.swv_results = {}          # Electrode -> results
            self.cv_results = {}           # CV analysis results
            self.frequency_map_results = {}  # Frequency map data
            self.trend_data = {            # SWV trend data
                'raw_peaks': {},
                'peak_potentials': {},
                'x_axis_values': [],
                'filter_params': {},
                'qc_metrics': {}
            }
            self.current_params = {}       # Current analysis parameters
            self.peak_warnings = []        # Peak detection warnings
            logger.info("Memory store cleared")

    def set_analysis_params(self, params):
        """Store analysis parameters"""
        with self.lock:
            self.current_params = params

    def get_analysis_params(self):
        """Retrieve analysis parameters"""
        with self.lock:
            return self.current_params.copy()

    def update_trend_data(self, electrode_index, frequency, file_number, peak_value, peak_potential):
        """Update trend data for SWV analysis"""
        with self.lock:
            freq_str = str(frequency)
            electrode_key = f"electrode_{electrode_index}"

            if electrode_key not in self.trend_data['raw_peaks']:
                self.trend_data['raw_peaks'][electrode_key] = {}
            if electrode_key not in self.trend_data['peak_potentials']:
                self.trend_data['peak_potentials'][electrode_key] = {}

            if freq_str not in self.trend_data['raw_peaks'][electrode_key]:
                self.trend_data['raw_peaks'][electrode_key][freq_str] = {}
            if freq_str not in self.trend_data['peak_potentials'][electrode_key]:
                self.trend_data['peak_potentials'][electrode_key][freq_str] = {}

            self.trend_data['raw_peaks'][electrode_key][freq_str][str(file_number)] = peak_value
            self.trend_data['peak_potentials'][electrode_key][freq_str][str(file_number)] = peak_potential

    def get_trend_data(self):
        """Retrieve all trend data"""
        with self.lock:
            return {
                'raw_peaks': self.trend_data['raw_peaks'].copy(),
                'peak_potentials': self.trend_data['peak_potentials'].copy(),
                'x_axis_values': self.trend_data['x_axis_values'].copy(),
                'filter_params': self.trend_data['filter_params'].copy(),
                'qc_metrics': self.trend_data['qc_metrics'].copy()
            }

    def add_frequency_map_result(self, electrode_index, frequency, data):
        """Store frequency map result"""
        with self.lock:
            electrode_key = f"electrode_{electrode_index}"
            if electrode_key not in self.frequency_map_results:
                self.frequency_map_results[electrode_key] = {}
            self.frequency_map_results[electrode_key][str(frequency)] = data

    def get_frequency_map_results(self):
        """Retrieve frequency map results"""
        with self.lock:
            return self.frequency_map_results.copy()

    def add_peak_warning(self, warning):
        """Add peak detection warning"""
        with self.lock:
            self.peak_warnings.append(warning)

    def get_peak_warnings(self):
        """Retrieve peak warnings"""
        with self.lock:
            return self.peak_warnings.copy()

# Global memory store instance
memory_store = MemoryStore()

# --- Flask App Setup ---
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'local_secret_key_for_single_user'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload

# --- SocketIO Setup (Simplified for Local Use) ---
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',  # Use threading instead of gevent
    logger=True,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10000000,  # 10MB
    allow_upgrades=True,
    transports=['polling', 'websocket']
)

logger.info("=" * 80)
logger.info("SACMES LOCAL APPLICATION INITIALIZED")
logger.info("  Mode: Local single-user")
logger.info("  SocketIO async mode: threading")
logger.info("  Max buffer size: 10MB")
logger.info("=" * 80)

# --- File Monitor Class (Extracted from agent.py) ---
class LocalFileMonitor(FileSystemEventHandler):
    """
    Local file folder monitor for automatic file processing.
    Extracted and adapted from agent.py watchdog logic.
    """
    def __init__(self, socketio_instance, filters):
        self.socketio = socketio_instance
        self.filters = filters
        self.processed_files = set()
        logger.info(f"LocalFileMonitor initialized with filters: {filters}")

    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)
        logger.debug(f"File created event: {filename}")

        # Check if file matches filters
        if not self.file_matches_filters(filename):
            logger.debug(f"File {filename} does not match filters, skipping")
            return

        if filename in self.processed_files:
            logger.debug(f"File {filename} already processed, skipping")
            return

        try:
            # Small delay to ensure file is fully written
            logger.debug(f"Waiting for file to be fully written: {filename}")
            time.sleep(0.1)

            # Check if file exists and is accessible
            if not os.path.exists(event.src_path):
                logger.warning(f"File disappeared: {filename}")
                return

            if not os.access(event.src_path, os.R_OK):
                logger.error(f"File not readable: {filename}")
                self.socketio.emit('file_monitor_error', {
                    'filename': filename,
                    'error': 'File is not readable (permission denied)'
                })
                return

            # Read file content
            logger.debug(f"Reading file: {filename}")
            try:
                with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                logger.debug(f"File read successfully: {filename} ({len(content)} bytes)")
            except Exception as read_error:
                logger.error(f"Failed to read file {filename}: {read_error}")
                self.socketio.emit('file_monitor_error', {
                    'filename': filename,
                    'error': f'Read error: {str(read_error)}'
                })
                return

            # Validate file safety
            logger.debug(f"Validating file safety: {filename}")
            is_safe, error_msg = validate_file_safety(filename, content)
            if not is_safe:
                logger.warning(f"File {filename} failed safety check: {error_msg}")
                self.socketio.emit('file_monitor_error', {
                    'filename': filename,
                    'error': f'Safety check failed: {error_msg}'
                })
                return

            # Emit file to processing
            logger.info(f"File detected and validated: {filename} - sending for processing")
            self.socketio.emit('stream_instrument_data', {
                'filename': filename,
                'content': content,
                'analysisParams': self.filters.get('analysisParams', {})
            })

            # Emit new file notification
            self.socketio.emit('new_file_detected', {
                'filename': filename
            })

            self.processed_files.add(filename)
            logger.debug(f"File added to processed list: {filename}")

        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.socketio.emit('file_monitor_error', {
                'filename': filename,
                'error': str(e)
            })

    def file_matches_filters(self, filename):
        """
        Check if filename matches configured filters.
        Adapted from agent.py file matching logic.
        """
        handle = self.filters.get('handle', '')
        frequency = self.filters.get('frequency', '')
        file_extension = self.filters.get('fileExtension', '.txt')

        # Check file extension
        if not filename.lower().endswith(file_extension.lower()):
            return False

        # Check file handle prefix
        if handle and not filename.startswith(handle):
            return False

        # Check frequency pattern (e.g., "_60Hz")
        if frequency:
            freq_pattern = re.compile(rf'_{frequency}Hz', re.IGNORECASE)
            if not freq_pattern.search(filename):
                return False

        return True

# Global file observer
file_observer = None
file_monitor = None

# --- HTTP Routes ---

# Add cache control headers to prevent browser caching during development
@app.after_request
def add_cache_control(response):
    """Add cache control headers to prevent browser caching"""
    if request.path.endswith(('.js', '.css', '.html')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    """Serve main application page"""
    return send_from_directory('static', 'index_local.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'mode': 'local'}, 200

@app.route('/clear_data', methods=['POST'])
def clear_data():
    """Clear all stored data"""
    memory_store.clear()
    return {'status': 'success', 'message': 'All data cleared'}, 200

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: sid={request.sid}")
    emit('connection_status', {'status': 'connected', 'mode': 'local'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: sid={request.sid}")

# --- Folder Monitoring Events ---

@socketio.on('start_folder_monitoring')
def start_folder_monitoring(data):
    """Start monitoring a folder for new files"""
    global file_observer, file_monitor

    folder_path = data.get('folder_path')
    filters = data.get('filters', {})

    if not folder_path:
        emit('folder_monitor_error', {'message': 'No folder path provided'})
        return

    if not os.path.isdir(folder_path):
        emit('folder_monitor_error', {'message': f'Invalid folder path: {folder_path}'})
        return

    try:
        # Stop existing monitor if any
        if file_observer:
            file_observer.stop()
            file_observer.join()

        # Create new monitor
        file_monitor = LocalFileMonitor(socketio, filters)
        file_observer = Observer()
        file_observer.schedule(file_monitor, folder_path, recursive=False)
        file_observer.start()

        logger.info(f"Started folder monitoring: {folder_path}")
        emit('folder_monitor_started', {
            'folder_path': folder_path,
            'filters': filters
        })

        # Scan and send existing files in the folder
        try:
            existing_files = []
            allowed_extensions = {'.txt', '.dta', '.csv'}

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename.lower())[1]
                    if file_ext in allowed_extensions:
                        existing_files.append(filename)

            # Sort files by name
            existing_files.sort()

            logger.info(f"Found {len(existing_files)} existing files in folder")
            emit('folder_files_list', {
                'files': existing_files,
                'folder_path': folder_path
            })
        except Exception as e:
            logger.error(f"Error scanning existing files: {e}")

    except Exception as e:
        logger.error(f"Error starting folder monitor: {e}")
        emit('folder_monitor_error', {'message': str(e)})

@socketio.on('stop_folder_monitoring')
def stop_folder_monitoring():
    """Stop folder monitoring"""
    global file_observer, file_monitor

    try:
        if file_observer:
            file_observer.stop()
            file_observer.join()
            file_observer = None
            file_monitor = None
            logger.info("Stopped folder monitoring")
            emit('folder_monitor_stopped', {})
        else:
            emit('folder_monitor_error', {'message': 'No active monitoring to stop'})
    except Exception as e:
        logger.error(f"Error stopping folder monitor: {e}")
        emit('folder_monitor_error', {'message': str(e)})

@socketio.on('scan_available_frequencies')
def scan_available_frequencies(data):
    """Scan folder for available frequencies from filenames"""
    try:
        folder_path = data.get('folder_path')
        file_handle = data.get('file_handle', '')

        if not folder_path:
            emit('available_frequencies_response', {
                'status': 'error',
                'message': 'No folder path provided'
            })
            return

        if not os.path.isdir(folder_path):
            emit('available_frequencies_response', {
                'status': 'error',
                'message': f'Invalid folder path: {folder_path}'
            })
            return

        logger.info(f"Scanning frequencies in: {folder_path}, handle: {file_handle}")

        # Scan files and extract frequencies
        frequencies = set()
        allowed_extensions = {'.txt', '.dta', '.csv'}

        # Pattern to match frequency in filename (e.g., _15Hz, _200Hz, 15hz, etc.)
        freq_pattern = re.compile(r'[_\-]?(\d+(?:\.\d+)?)\s*hz', re.IGNORECASE)

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue

            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext not in allowed_extensions:
                continue

            # Filter by file handle if specified
            if file_handle and not filename.startswith(file_handle):
                continue

            # Extract frequency from filename
            match = freq_pattern.search(filename)
            if match:
                try:
                    freq_value = float(match.group(1))
                    frequencies.add(freq_value)
                except ValueError:
                    continue

        # Convert to sorted list
        freq_list = sorted(list(frequencies))

        logger.info(f"Found {len(freq_list)} frequencies: {freq_list}")
        emit('available_frequencies_response', {
            'status': 'success',
            'frequencies': freq_list,
            'folder_path': folder_path
        })

    except Exception as e:
        logger.error(f"Error scanning frequencies: {e}")
        emit('available_frequencies_response', {
            'status': 'error',
            'message': str(e)
        })

# --- Analysis Session Events (Simplified) ---

@socketio.on('start_analysis_session')
def handle_start_analysis_session(data):
    """Start SWV analysis session (simplified from original)"""
    try:
        analysis_params = data.get('analysisParams', {})
        analysis_mode = data.get('analysis_mode', 'continuous')

        # Store parameters in memory
        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'analysis_mode': analysis_mode
        })

        logger.info(f"Started SWV analysis session: mode={analysis_mode}")
        emit('analysis_session_started', {
            'status': 'success',
            'mode': analysis_mode
        })

    except Exception as e:
        logger.error(f"Error starting analysis session: {e}")
        emit('analysis_session_started', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('stop_analysis_session')
def handle_stop_analysis_session(data):
    """Stop analysis session"""
    logger.info("Stopped analysis session")
    emit('analysis_session_stopped', {'status': 'success'})

@socketio.on('start_cv_analysis_session')
def handle_start_cv_analysis_session(data):
    """Start CV analysis session"""
    try:
        analysis_params = data.get('analysisParams', {})

        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'analysis_type': 'cv'
        })

        logger.info("Started CV analysis session")
        emit('cv_session_started', {'status': 'success'})

    except Exception as e:
        logger.error(f"Error starting CV session: {e}")
        emit('cv_session_started', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('stop_cv_analysis_session')
def handle_stop_cv_analysis_session(data):
    """Stop CV analysis session"""
    logger.info("Stopped CV analysis session")
    emit('cv_session_stopped', {'status': 'success'})

@socketio.on('start_frequency_map_session')
def handle_start_frequency_map_session(data):
    """Start frequency map analysis session"""
    try:
        analysis_params = data.get('analysisParams', {})
        frequencies = data.get('frequencies', [])

        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'frequencies': frequencies,
            'analysis_mode': 'frequency_map'
        })

        logger.info(f"Started frequency map session with {len(frequencies)} frequencies")
        emit('frequency_map_session_started', {'status': 'success'})

    except Exception as e:
        logger.error(f"Error starting frequency map session: {e}")
        emit('frequency_map_session_started', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('stop_frequency_map_session')
def handle_stop_frequency_map_session(data):
    """Stop frequency map session"""
    logger.info("Stopped frequency map session")
    emit('frequency_map_session_stopped', {'status': 'success'})

# --- Data Processing Functions ---

def process_file_in_background(original_filename, content, params_for_this_file, selected_electrode=None):
    """
    Process SWV data file in background.
    Simplified from original - no session management, direct memory storage.
    """
    logger.info(f"Processing file: {original_filename}")

    # Create temporary file
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_swv_data:
            logger.error("analyze_swv_data not available")
            return

        # Call analyzer
        analysis_result = analyze_swv_data(temp_filepath, params_for_this_file, selected_electrode)

        # Clean up temp file
        os.unlink(temp_filepath)

        # Handle errors
        if analysis_result and analysis_result.get('status') == 'error':
            logger.error(f"Analysis error: {analysis_result.get('message')}")
            if 'detected_electrodes' in analysis_result:
                socketio.emit('electrode_validation_error', {
                    'message': analysis_result.get('message'),
                    'detected_electrodes': analysis_result.get('detected_electrodes'),
                    'requested_electrode': analysis_result.get('requested_electrode')
                })
            return

        # Process successful results
        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            # Extract frequency and file number from filename
            match = re.search(r'_(\d+)Hz_?_?(\d+)(?:\.|$)', original_filename, re.IGNORECASE)
            if match:
                frequency = int(match.group(1))
                file_number = int(match.group(2))
                peak_value = analysis_result.get('peak_value')
                peak_potential = analysis_result.get('peak_info', {}).get('peak_potential')

                # Update memory store
                electrode_index = selected_electrode if selected_electrode is not None else 'averaged'
                memory_store.update_trend_data(electrode_index, frequency, file_number, peak_value, peak_potential)

                # Emit live update to frontend
                socketio.emit('live_analysis_update', {
                    'filename': original_filename,
                    'electrode_index': electrode_index,
                    'individual_analysis': {
                        'potentials': analysis_result.get('potentials', []),
                        'raw_currents': analysis_result.get('raw_currents', []),
                        'smoothed_currents': analysis_result.get('smoothed_currents', []),
                        'regression_line': analysis_result.get('regression_line', []),
                        'peak_info': analysis_result.get('peak_info', {}),
                        'filter_params': analysis_result.get('filter_params', {}),
                        'qc_metrics': analysis_result.get('qc_metrics', {})
                    },
                    'incremental_data': {
                        'frequency': frequency,
                        'file_number': file_number,
                        'peak_value': peak_value,
                        'peak_potential': peak_potential
                    },
                    'trend_data': memory_store.get_trend_data()
                })

                # Acknowledge file processing
                socketio.emit('file_processing_complete', {
                    'filename': original_filename,
                    'status': 'success'
                })

                logger.info(f"File processed successfully: {original_filename}")

    except Exception as e:
        logger.error(f"Error processing file {original_filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        socketio.emit('file_processing_error', {
            'filename': original_filename,
            'error': str(e)
        })

def process_frequency_map_file(original_filename, content, frequency, params, electrode_index=0):
    """
    Process file for frequency map analysis.
    Simplified from original.
    """
    logger.info(f"Processing frequency map file: {original_filename} at {frequency}Hz")

    import tempfile
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_swv_data:
            return

        # Call analyzer
        analysis_result = analyze_swv_data(temp_filepath, params, electrode_index if electrode_index != 'averaged' else None)

        # Clean up
        os.unlink(temp_filepath)

        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            peak_value = analysis_result.get('peak_value')

            # Calculate charge (peak / frequency)
            charge = (peak_value / frequency) if frequency > 0 and peak_value else 0

            # Store frequency map data
            freq_data = {
                'potentials': analysis_result.get('potentials', []),
                'currents': analysis_result.get('smoothed_currents', []),
                'charge': charge,
                'peak_value': peak_value,
                'peak_potential': analysis_result.get('peak_info', {}).get('peak_potential')
            }

            memory_store.add_frequency_map_result(electrode_index, frequency, freq_data)

            # Emit update
            socketio.emit('frequency_map_update', {
                'frequency': frequency,
                'electrode_index': electrode_index,
                'data': freq_data
            })

            logger.info(f"Frequency map file processed: {frequency}Hz")

    except Exception as e:
        logger.error(f"Error processing frequency map file: {e}")
        import traceback
        logger.error(traceback.format_exc())

def process_cv_file_in_background(original_filename, content, params, selected_electrode=None):
    """
    Process CV data file in background.
    Simplified from original.
    """
    logger.info(f"Processing CV file: {original_filename}")

    import tempfile
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_cv_data:
            logger.error("analyze_cv_data not available")
            return

        # Call analyzer
        analysis_result = analyze_cv_data(temp_filepath, params, selected_electrode)

        # Clean up
        os.unlink(temp_filepath)

        if analysis_result and analysis_result.get('status') == 'success':
            # Emit CV update
            socketio.emit('live_cv_update', {
                'electrode_index': selected_electrode if selected_electrode is not None else 'averaged',
                'filename': original_filename,
                'result': analysis_result
            })

            logger.info(f"CV file processed: {original_filename}")

    except Exception as e:
        logger.error(f"Error processing CV file: {e}")
        import traceback
        logger.error(traceback.format_exc())

# --- File Data Stream Events ---

@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    """
    Handle incoming SWV data files.
    Simplified from original - no user_id or agent checks.
    """
    try:
        original_filename = data.get('filename', 'unknown_file.txt')
        file_content = data.get('content', '')

        logger.info(f"Received file: {original_filename} ({len(file_content)} bytes)")

        # Validate file safety
        is_safe, error_message = validate_file_safety(original_filename, file_content)
        if not is_safe:
            logger.warning(f"File safety check failed: {error_message}")
            emit('file_validation_error', {
                'filename': original_filename,
                'error': error_message
            })
            return

        # Get analysis parameters from memory
        stored_params = memory_store.get_analysis_params()
        analysis_params = stored_params.get('analysisParams', {})
        analysis_mode = stored_params.get('analysis_mode', 'continuous')

        if not analysis_params:
            logger.warning("No analysis parameters set")
            return

        # Extract frequency from filename
        match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
        if not match:
            logger.warning(f"Filename does not match expected pattern: {original_filename}")
            return

        frequency = int(match.group(1))
        selected_electrodes = analysis_params.get('selected_electrodes', [])

        # Process based on mode
        if analysis_mode == 'frequency_map':
            logger.info(f"Processing in FREQUENCY MAP mode: {original_filename}")

            if selected_electrodes:
                for electrode_idx in selected_electrodes:
                    params_copy = analysis_params.copy()
                    params_copy['selected_electrode'] = electrode_idx
                    threading.Thread(target=process_frequency_map_file,
                                   args=(original_filename, file_content, frequency, params_copy, electrode_idx),
                                   daemon=True).start()
            else:
                params_copy = analysis_params.copy()
                threading.Thread(target=process_frequency_map_file,
                               args=(original_filename, file_content, frequency, params_copy, 'averaged'),
                               daemon=True).start()

        else:  # continuous mode
            logger.info(f"Processing in CONTINUOUS mode: {original_filename}")

            if selected_electrodes:
                for electrode_idx in selected_electrodes:
                    params_copy = analysis_params.copy()
                    params_copy['frequency'] = frequency
                    params_copy['selected_electrode'] = electrode_idx
                    threading.Thread(target=process_file_in_background,
                                   args=(original_filename, file_content, params_copy, electrode_idx),
                                   daemon=True).start()
            else:
                params_copy = analysis_params.copy()
                params_copy['frequency'] = frequency
                threading.Thread(target=process_file_in_background,
                               args=(original_filename, file_content, params_copy, None),
                               daemon=True).start()

    except Exception as e:
        logger.error(f"Error handling instrument data: {e}")
        import traceback
        logger.error(traceback.format_exc())

@socketio.on('stream_cv_data')
def handle_cv_data(data):
    """Handle incoming CV data files"""
    try:
        original_filename = data.get('filename', 'unknown_file.txt')
        file_content = data.get('content', '')

        logger.info(f"Received CV file: {original_filename}")

        # Validate file safety
        is_safe, error_message = validate_file_safety(original_filename, file_content)
        if not is_safe:
            emit('file_validation_error', {
                'filename': original_filename,
                'error': error_message
            })
            return

        # Get analysis parameters
        stored_params = memory_store.get_analysis_params()
        cv_params = stored_params.get('analysisParams', {})

        if not cv_params:
            logger.warning("No CV analysis parameters set")
            return

        selected_electrodes = cv_params.get('selected_electrodes', [])

        if selected_electrodes:
            for electrode_idx in selected_electrodes:
                params_copy = cv_params.copy()
                threading.Thread(target=process_cv_file_in_background,
                               args=(original_filename, file_content, params_copy, electrode_idx),
                               daemon=True).start()
        else:
            threading.Thread(target=process_cv_file_in_background,
                           args=(original_filename, file_content, cv_params, None),
                           daemon=True).start()

    except Exception as e:
        logger.error(f"Error handling CV data: {e}")
        import traceback
        logger.error(traceback.format_exc())

# --- CV Preview and Segments ---

@socketio.on('get_cv_preview')
def handle_get_cv_preview(data):
    """Get CV preview data"""
    # This would need to be implemented based on the original logic
    # For now, just acknowledge
    emit('cv_preview_response', {'status': 'not_implemented'})

@socketio.on('get_cv_segments')
def handle_get_cv_segments(data):
    """Get CV segment data"""
    # This would need to be implemented based on the original logic
    emit('cv_segments_response', {'status': 'not_implemented'})

# --- Export Data Events ---

@socketio.on('request_export_data')
def handle_export_request(data):
    """Export SWV data to CSV"""
    try:
        trend_data = memory_store.get_trend_data()

        # Generate CSV (simplified version)
        csv_data = "Electrode,Frequency,File_Number,Peak_Value,Peak_Potential\n"

        for electrode_key, freq_data in trend_data['raw_peaks'].items():
            for freq_str, file_data in freq_data.items():
                for file_num, peak_value in file_data.items():
                    peak_potential = trend_data['peak_potentials'].get(electrode_key, {}).get(freq_str, {}).get(file_num, '')
                    csv_data += f"{electrode_key},{freq_str},{file_num},{peak_value},{peak_potential}\n"

        emit('export_data_response', {
            'status': 'success',
            'data': csv_data
        })

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        emit('export_data_response', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('request_export_cv_data')
def handle_cv_export_request(data):
    """Export CV data to CSV"""
    emit('export_cv_data_response', {'status': 'not_fully_implemented'})

@socketio.on('request_export_frequency_map_data')
def handle_frequency_map_export_request(data):
    """Export frequency map data to CSV"""
    try:
        freq_map_data = memory_store.get_frequency_map_results()

        # Generate CSV
        csv_data = "Electrode,Frequency,Peak_Value,Peak_Potential,Charge\n"

        for electrode_key, freq_data in freq_map_data.items():
            for freq_str, data_dict in freq_data.items():
                csv_data += f"{electrode_key},{freq_str},{data_dict.get('peak_value', '')},{data_dict.get('peak_potential', '')},{data_dict.get('charge', '')}\n"

        emit('export_frequency_map_data_response', {
            'status': 'success',
            'data': csv_data
        })

    except Exception as e:
        logger.error(f"Error exporting frequency map data: {e}")
        emit('export_frequency_map_data_response', {
            'status': 'error',
            'message': str(e)
        })

# --- Diagnostic and Troubleshooting Events ---

@socketio.on('run_diagnostics')
def run_diagnostics(data):
    """Run comprehensive system diagnostics"""
    logger.info("Running system diagnostics...")

    diagnostics = {
        'timestamp': datetime.now().isoformat(),
        'system': {},
        'analyzers': {},
        'folder_monitoring': {},
        'file_access': {}
    }

    # System checks
    diagnostics['system']['python_version'] = sys.version
    diagnostics['system']['cwd'] = os.getcwd()
    diagnostics['system']['platform'] = sys.platform

    # Analyzer checks
    diagnostics['analyzers']['swv_analyzer_loaded'] = analyze_swv_data is not None
    diagnostics['analyzers']['cv_analyzer_loaded'] = analyze_cv_data is not None

    # Folder monitoring status
    diagnostics['folder_monitoring']['observer_active'] = file_observer is not None
    diagnostics['folder_monitoring']['monitor_active'] = file_monitor is not None
    if file_monitor:
        diagnostics['folder_monitoring']['processed_files_count'] = len(file_monitor.processed_files)

    # Test folder path if provided
    test_path = data.get('folder_path')
    if test_path:
        diagnostics['file_access']['test_path'] = test_path
        diagnostics['file_access']['path_exists'] = os.path.exists(test_path)
        diagnostics['file_access']['is_directory'] = os.path.isdir(test_path)

        if os.path.isdir(test_path):
            try:
                files = os.listdir(test_path)
                diagnostics['file_access']['can_read_directory'] = True
                diagnostics['file_access']['file_count'] = len(files)

                # Test reading a file if any exist
                txt_files = [f for f in files if f.endswith(('.txt', '.dta', '.csv'))]
                if txt_files:
                    test_file = os.path.join(test_path, txt_files[0])
                    try:
                        with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(100)  # Read first 100 chars
                        diagnostics['file_access']['can_read_files'] = True
                        diagnostics['file_access']['test_file'] = txt_files[0]
                        diagnostics['file_access']['test_file_size'] = os.path.getsize(test_file)
                    except Exception as e:
                        diagnostics['file_access']['can_read_files'] = False
                        diagnostics['file_access']['read_error'] = str(e)
                else:
                    diagnostics['file_access']['data_files_found'] = False
            except Exception as e:
                diagnostics['file_access']['can_read_directory'] = False
                diagnostics['file_access']['directory_error'] = str(e)

    logger.info(f"Diagnostics complete: {json.dumps(diagnostics, indent=2)}")
    emit('diagnostics_response', {
        'status': 'success',
        'diagnostics': diagnostics
    })

@socketio.on('test_file_read')
def test_file_read(data):
    """Test reading a specific file for troubleshooting"""
    folder_path = data.get('folder_path')
    filename = data.get('filename')

    if not folder_path or not filename:
        emit('file_read_test_response', {
            'status': 'error',
            'message': 'folder_path and filename required'
        })
        return

    file_path = os.path.join(folder_path, filename)

    logger.info(f"Testing file read: {file_path}")

    result = {
        'filename': filename,
        'file_path': file_path,
        'exists': os.path.exists(file_path),
        'is_file': os.path.isfile(file_path),
    }

    if os.path.isfile(file_path):
        try:
            result['file_size'] = os.path.getsize(file_path)
            result['readable'] = os.access(file_path, os.R_OK)

            # Try to read the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            result['content_length'] = len(content)
            result['first_100_chars'] = content[:100]
            result['line_count'] = len(content.splitlines())

            # Validate file safety
            is_safe, error_msg = validate_file_safety(filename, content)
            result['safety_check'] = is_safe
            if not is_safe:
                result['safety_error'] = error_msg

            # Check if filename matches expected pattern
            freq_match = re.search(r'_(\d+)Hz', filename, re.IGNORECASE)
            result['frequency_detected'] = freq_match.group(1) if freq_match else None

            logger.info(f"File read successful: {filename} ({result['content_length']} bytes)")
            emit('file_read_test_response', {
                'status': 'success',
                'result': result
            })

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            import traceback
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            emit('file_read_test_response', {
                'status': 'error',
                'result': result
            })
    else:
        logger.warning(f"File not found or not accessible: {file_path}")
        emit('file_read_test_response', {
            'status': 'error',
            'result': result,
            'message': 'File not found or not accessible'
        })

@socketio.on('manual_process_file')
def manual_process_file(data):
    """Manually trigger file processing for troubleshooting"""
    folder_path = data.get('folder_path')
    filename = data.get('filename')
    analysis_type = data.get('analysis_type', 'swv')  # swv, cv, or ht

    if not folder_path or not filename:
        emit('manual_process_response', {
            'status': 'error',
            'message': 'folder_path and filename required'
        })
        return

    file_path = os.path.join(folder_path, filename)

    logger.info(f"Manual file processing requested: {file_path} (type: {analysis_type})")

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        logger.debug(f"File content length: {len(content)} bytes")

        # Validate safety
        is_safe, error_msg = validate_file_safety(filename, content)
        if not is_safe:
            logger.warning(f"Safety check failed: {error_msg}")
            emit('manual_process_response', {
                'status': 'error',
                'message': f'Safety check failed: {error_msg}'
            })
            return

        # Get analysis parameters
        stored_params = memory_store.get_analysis_params()
        if not stored_params or 'analysisParams' not in stored_params:
            logger.warning("No analysis parameters found. Please start an analysis session first.")
            emit('manual_process_response', {
                'status': 'error',
                'message': 'No analysis parameters set. Start an analysis session first.'
            })
            return

        # Process based on type
        if analysis_type == 'swv':
            logger.info(f"Emitting to stream_instrument_data: {filename}")
            socketio.emit('stream_instrument_data', {
                'filename': filename,
                'content': content,
                'analysisParams': stored_params.get('analysisParams', {})
            })
        elif analysis_type == 'cv':
            logger.info(f"Emitting to stream_cv_data: {filename}")
            socketio.emit('stream_cv_data', {
                'filename': filename,
                'content': content
            })
        else:
            emit('manual_process_response', {
                'status': 'error',
                'message': f'Unsupported analysis type: {analysis_type}'
            })
            return

        emit('manual_process_response', {
            'status': 'success',
            'message': f'File {filename} sent for processing'
        })

    except Exception as e:
        logger.error(f"Error in manual file processing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('manual_process_response', {
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        })

# --- Main Application Entry Point ---
if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Find available port
    def find_available_port(start_port=5000, max_attempts=10):
        """Find an available port starting from start_port"""
        import socket
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        return None

    port = find_available_port()
    if port is None:
        logger.error("Could not find available port in range 5000-5009")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info(f"STARTING SACMES LOCAL APPLICATION")
    logger.info(f"  Port: {port}")
    logger.info(f"  URL: http://localhost:{port}")
    logger.info("=" * 80)

    # Note: Browser auto-open is handled by start.bat
    # No need to open browser here to avoid double windows

    # Run SocketIO server
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        if file_observer:
            file_observer.stop()
            file_observer.join()
        logger.info("Application stopped")
