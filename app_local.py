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
import base64
import zipfile
import numpy as np
from datetime import datetime
from xml.sax import saxutils
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

# --- Utility Functions ---
def natural_sort_key(s):
    """Generate sort key for natural sorting (1, 2, 10 instead of 1, 10, 2)"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def extract_file_number_and_frequency(filename):
    """
    Extract file number and frequency from filename for sorting.
    Example: SWV_15Hz__1.txt -> (1, 15)
             SWV_200Hz__92.txt -> (92, 200)
    Returns: (file_number, frequency) tuple
    """
    # Match pattern like: _15Hz__1 or _200Hz__92
    match = re.search(r'_(\d+)Hz_+(\d+)', filename)
    if match:
        frequency = int(match.group(1))
        file_number = int(match.group(2))
        return (file_number, frequency)
    # Fallback to natural sort
    return (float('inf'), 0)

def continuous_mode_sort_key(filename):
    """
    Sort key for continuous mode: group by file number, then by frequency.
    This ensures files are processed as: freq1_file1, freq2_file1, freq1_file2, freq2_file2
    """
    file_num, freq = extract_file_number_and_frequency(filename)
    return (file_num, freq)


def _excel_col_name(col_idx):
    name = ''
    while col_idx > 0:
        col_idx, rem = divmod(col_idx - 1, 26)
        name = chr(65 + rem) + name
    return name


def _sanitize_sheet_name(name, used_names):
    invalid = set('[]:*?/\\')
    cleaned = ''.join('_' if ch in invalid else ch for ch in str(name or 'Sheet')).strip()
    cleaned = cleaned[:31] or 'Sheet'
    base = cleaned
    suffix = 1
    while cleaned in used_names:
        tail = f"_{suffix}"
        cleaned = f"{base[:31 - len(tail)]}{tail}"
        suffix += 1
    used_names.add(cleaned)
    return cleaned


def _is_numeric_cell(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.upper() == 'N/A':
            return False
        try:
            float(stripped)
            return True
        except ValueError:
            return False
    return False


def _worksheet_xml(rows):
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>'
    ]

    for row_idx, row in enumerate(rows, start=1):
        parts.append(f'<row r="{row_idx}">')
        for col_idx, value in enumerate(row, start=1):
            if value is None or value == '':
                continue
            cell_ref = f'{_excel_col_name(col_idx)}{row_idx}'
            if _is_numeric_cell(value):
                parts.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
            else:
                escaped = saxutils.escape(str(value))
                parts.append(f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{escaped}</t></is></c>')
        parts.append('</row>')

    parts.extend(['</sheetData>', '</worksheet>'])
    return ''.join(parts)


def _build_xlsx_bytes(sheet_defs):
    used_names = set()
    normalized = []
    for idx, sheet in enumerate(sheet_defs, start=1):
        normalized.append({
            'name': _sanitize_sheet_name(sheet.get('name') or f'Sheet{idx}', used_names),
            'rows': sheet.get('rows') or [['No data available']]
        })

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    ]
    for idx in range(1, len(normalized) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append('</Types>')

    workbook = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '<sheets>'
    ]
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    ]
    for idx, sheet in enumerate(normalized, start=1):
        workbook.append(f'<sheet name="{saxutils.escape(sheet["name"])}" sheetId="{idx}" r:id="rId{idx}"/>')
        workbook_rels.append(
            f'<Relationship Id="rId{idx}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    workbook.extend(['</sheets>', '</workbook>'])
    workbook_rels.append('</Relationships>')

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', ''.join(content_types))
        archive.writestr('_rels/.rels', root_rels)
        archive.writestr('xl/workbook.xml', ''.join(workbook))
        archive.writestr('xl/_rels/workbook.xml.rels', ''.join(workbook_rels))
        archive.writestr('xl/styles.xml', styles)
        for idx, sheet in enumerate(normalized, start=1):
            archive.writestr(f'xl/worksheets/sheet{idx}.xml', _worksheet_xml(sheet['rows']))
    return buffer.getvalue()


def _sheet_defs_from_sectioned_csv(csv_text):
    metadata_rows = []
    sheets = []
    current_name = None
    current_rows = []

    for raw_line in csv_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith('### '):
            if current_name and current_rows:
                sheets.append({'name': current_name, 'rows': current_rows})
            current_name = stripped[4:].strip()
            current_rows = []
            continue
        if stripped.startswith('## '):
            if current_name and current_rows:
                sheets.append({'name': current_name, 'rows': current_rows})
            current_name = stripped[3:].strip()
            current_rows = []
            continue
        if stripped.startswith('# '):
            metadata_rows.append([stripped[2:].strip()])
            continue

        row = [cell.strip() for cell in raw_line.split(',')]
        if current_name is None:
            metadata_rows.append(row)
        else:
            current_rows.append(row)

    if current_name and current_rows:
        sheets.append({'name': current_name, 'rows': current_rows})

    if metadata_rows:
        sheets.insert(0, {'name': 'Metadata', 'rows': metadata_rows})

    return sheets or [{'name': 'Data', 'rows': [['No data available']]}]

# Add file handler for persistent logs
file_handler = logging.FileHandler('sacmes_local_debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# --- Import Data Processing Modules ---
# Ensure current directory is in Python path
import sys
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from data_processing.swv_analyzer import analyze_swv_data
    from data_processing.cv_analyzer import analyze_cv_data, get_cv_segments
    logger.info("Successfully imported analyzers.")
except ImportError as e:
    logger.critical(f"FATAL: Failed to import analyzers: {e}")
    logger.critical(f"Python path: {sys.path}")
    logger.critical(f"Current directory: {os.getcwd()}")
    logger.critical(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
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

# --- File Processing Queue with Flow Control ---
class FileProcessingQueue:
    """Queue with flow control to prevent overwhelming frontend"""
    def __init__(self, max_pending=10):
        self.lock = threading.Lock()
        self.max_pending = max_pending
        self.pending_files = {}  # {filename: timestamp}
        self.processing_enabled = True

    def can_process(self):
        """Check if we can process more files"""
        with self.lock:
            return self.processing_enabled and len(self.pending_files) < self.max_pending

    def add_pending(self, filename):
        """Mark file as pending confirmation"""
        with self.lock:
            self.pending_files[filename] = time.time()
            logger.debug(f"[QUEUE] Pending files: {len(self.pending_files)}")

    def acknowledge(self, filename):
        """Remove file from pending list"""
        with self.lock:
            if filename in self.pending_files:
                del self.pending_files[filename]
                logger.debug(f"[QUEUE] Acknowledged {filename}, pending: {len(self.pending_files)}")
                return True
            return False

    def clear(self):
        """Clear all pending files"""
        with self.lock:
            self.pending_files.clear()

    def pause(self):
        """Pause processing"""
        with self.lock:
            self.processing_enabled = False

    def resume(self):
        """Resume processing"""
        with self.lock:
            self.processing_enabled = True

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

    def get_trend_data_for_electrode(self, electrode_index):
        """
        Get trend data for specific electrode in format expected by frontend.
        Converts from nested dict {freq: {file_num: value}} to arrays {freq: [values]}
        """
        with self.lock:
            electrode_key = f"electrode_{electrode_index}"

            # Get raw data for this electrode
            raw_peaks = self.trend_data['raw_peaks'].get(electrode_key, {})
            peak_potentials = self.trend_data['peak_potentials'].get(electrode_key, {})

            # Convert to frontend format
            peak_current_trends = {}
            peak_potential_trends = {}
            x_axis_values = []
            max_file_num = 0

            # First pass: determine max file number
            for freq_str, file_data in raw_peaks.items():
                for file_num_str in file_data.keys():
                    file_num = int(file_num_str)
                    if file_num > max_file_num:
                        max_file_num = file_num

            # Create x_axis_values
            x_axis_values = list(range(1, max_file_num + 1))

            # Second pass: build arrays for each frequency
            for freq_str, file_data in raw_peaks.items():
                # Initialize arrays with None
                peak_current_trends[freq_str] = [None] * max_file_num
                peak_potential_trends[freq_str] = [None] * max_file_num

                # Fill in values
                for file_num_str, peak_value in file_data.items():
                    file_index = int(file_num_str) - 1  # Convert to 0-based index
                    if 0 <= file_index < max_file_num:
                        peak_current_trends[freq_str][file_index] = peak_value

                # Fill in peak potentials
                potential_data = peak_potentials.get(freq_str, {})
                for file_num_str, potential_value in potential_data.items():
                    file_index = int(file_num_str) - 1
                    if 0 <= file_index < max_file_num:
                        peak_potential_trends[freq_str][file_index] = potential_value

            return {
                'peak_current_trends': peak_current_trends,
                'peak_potential_trends': peak_potential_trends,
                'x_axis_values': x_axis_values
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

    def store_cv_result(self, electrode_index, filename, analysis_result):
        """Store CV analysis result"""
        with self.lock:
            electrode_key = f"electrode_{electrode_index}" if electrode_index is not None else "averaged"
            if electrode_key not in self.cv_results:
                self.cv_results[electrode_key] = {}
            self.cv_results[electrode_key][filename] = analysis_result

    def get_cv_results(self):
        """Retrieve all CV results"""
        with self.lock:
            return self.cv_results.copy()

# Global memory store instance
memory_store = MemoryStore()

# Global processing queue instance
processing_queue = FileProcessingQueue(max_pending=10)

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
    def __init__(self, socketio_instance, filters, folder_path=None):
        self.socketio = socketio_instance
        self.filters = filters
        self.folder_path = folder_path
        self.processed_files = set()
        self.is_stopping = False  # Flag to indicate monitor is stopping
        self.pause_new_files = False  # Pause real-time detection during batch replay
        self.processing_threads = []  # Track background processing threads
        self.last_processed_num = {}  # {frequency_int: last_file_num_int} for gap detection
        self._seq_lock = threading.Lock()
        logger.info(f"LocalFileMonitor initialized with filters: {filters}")

    def reset_sequence(self):
        """Reset file sequence tracking (call at start of a new analysis session)."""
        with self._seq_lock:
            self.last_processed_num.clear()
            self.processed_files.clear()
        logger.info("LocalFileMonitor sequence tracking reset")

    def _wait_for_file_stable(self, filepath, min_size=100, stable_secs=0.3, timeout_secs=10):
        """
        Poll file size until it stops changing (file fully written by instrument).
        Returns True if file is stable and large enough, False if timed out.
        min_size: minimum bytes required before we consider the file non-empty.
        stable_secs: how long the size must stay unchanged before we trust it.
        """
        deadline = time.time() + timeout_secs
        prev_size = -1
        stable_since = None
        while time.time() < deadline:
            if self.is_stopping:
                return False
            try:
                size = os.path.getsize(filepath)
            except OSError:
                time.sleep(0.1)
                continue
            if size < min_size:
                # Still too small — instrument is still writing or file is empty
                prev_size = size
                stable_since = None
                time.sleep(0.1)
                continue
            if size == prev_size:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= stable_secs:
                    logger.debug(f"File stable at {size} bytes: {os.path.basename(filepath)}")
                    return True
            else:
                stable_since = None
            prev_size = size
            time.sleep(0.05)
        logger.warning(f"File stability timeout ({timeout_secs}s) for: {os.path.basename(filepath)}")
        return False

    def _check_and_report_gaps(self, frequency, file_num, filename):
        """
        Compare incoming file_num against the last processed number for this frequency.
        If there is a gap (e.g. last=3, current=5 -> file 4 is missing), emit a warning.
        The missing file's data will naturally appear as null in trend plots and exports.
        """
        with self._seq_lock:
            last_num = self.last_processed_num.get(frequency, 0)
            missing = []
            if last_num > 0 and file_num > last_num + 1:
                missing = list(range(last_num + 1, file_num))
            # Always advance to the highest seen number
            self.last_processed_num[frequency] = max(
                self.last_processed_num.get(frequency, 0), file_num
            )
        if missing:
            logger.warning(
                f"[GAP] Freq {frequency}Hz: file(s) {missing} not detected "
                f"(discovered when file #{file_num} '{filename}' arrived)"
            )
            self.socketio.emit('missing_file_warning', {
                'frequency': frequency,
                'missing_file_numbers': missing,
                'detected_by_file_number': file_num,
                'message': (
                    f"{len(missing)} file(s) at {frequency} Hz appear to be missing "
                    f"(#{', #'.join(map(str, missing))}). "
                    f"Possible instrument software block. "
                    f"Data gaps will appear as null in plots and export."
                )
            })

    def stop(self):
        """Signal the monitor to stop processing new files"""
        logger.info("LocalFileMonitor stopping - setting stop flag")
        self.is_stopping = True
        # Wait for any ongoing processing threads to complete (with timeout)
        for thread in self.processing_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)  # Wait max 2 seconds per thread
        logger.info(f"LocalFileMonitor stopped - {len(self.processing_threads)} threads cleaned up")

    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return

        # Check stop flag immediately
        if self.is_stopping:
            logger.debug("Monitor is stopping, ignoring new file event")
            return

        # During batch replay, queue new files to be picked up after replay finishes
        if self.pause_new_files:
            logger.debug(f"Batch replay in progress, deferring real-time file: {os.path.basename(event.src_path)}")
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
            # Wait until the instrument has finished writing the file
            logger.debug(f"Waiting for file to be fully written: {filename}")
            stable = self._wait_for_file_stable(event.src_path)
            if not stable:
                logger.warning(f"File did not stabilise in time, attempting to read anyway: {filename}")

            # Check stop flag again after stability wait
            if self.is_stopping:
                logger.debug(f"Monitor stopping, skipping file {filename}")
                return

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

            # Process file in background thread to avoid blocking observer
            logger.info(f"[OK] File detected and validated: {filename} - queuing for processing...")

            # Emit status update to frontend
            self.socketio.emit('file_processing_status', {
                'filename': filename,
                'status': 'processing',
                'message': f'Processing file: {filename}'
            })

            # Process in background thread to avoid blocking the observer
            def process_in_background():
                try:
                    # Check stop flag before processing
                    if self.is_stopping:
                        logger.debug(f"Monitor stopping, aborting processing of {filename}")
                        return

                    # Gap detection: check if any file numbers were skipped for this frequency
                    file_num, freq = extract_file_number_and_frequency(filename)
                    if file_num != float('inf') and freq != 0:
                        self._check_and_report_gaps(freq, file_num, filename)

                    handle_instrument_data({
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
                    logger.error(f"Error in background processing for {filename}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

            # Start background thread
            bg_thread = threading.Thread(target=process_in_background, daemon=True)
            bg_thread.start()
            self.processing_threads.append(bg_thread)

            # Clean up finished threads from the list
            self.processing_threads = [t for t in self.processing_threads if t.is_alive()]

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
        handle = self.filters.get('handle', '').strip()
        frequency = self.filters.get('frequency', '').strip()
        file_extension = self.filters.get('fileExtension', '.txt').strip()
        range_start = self.filters.get('range_start')
        range_end = self.filters.get('range_end')

        # Check file extension
        if not filename.lower().endswith(file_extension.lower()):
            logger.debug(f" File extension mismatch (expected {file_extension}): {filename}")
            return False

        # Check file handle prefix
        if handle and not filename.startswith(handle):
            logger.debug(f" File handle mismatch (expected '{handle}'): {filename}")
            return False

        # Check frequency pattern (e.g., "_60Hz" or "_0060Hz")
        if frequency:
            # Handle comma-separated frequency list
            frequencies = [f.strip() for f in str(frequency).split(',')]
            matched = False
            for freq in frequencies:
                if freq:  # Skip empty strings
                    # Match with optional leading zeros: _0*5Hz matches _5Hz, _05Hz, _005Hz, etc.
                    freq_pattern = re.compile(rf'_0*{freq}Hz', re.IGNORECASE)
                    if freq_pattern.search(filename):
                        matched = True
                        logger.debug(f"[OK] Frequency matched ({freq}Hz): {filename}")
                        break
            if not matched:
                logger.debug(f" No frequency match in {frequencies}: {filename}")
                return False

        # Check file number range (e.g., SWV_15Hz__1.txt -> file number is 1)
        if range_start is not None or range_end is not None:
            file_num, _ = extract_file_number_and_frequency(filename)
            if file_num != float('inf'):  # Valid file number extracted
                if range_start is not None and file_num < range_start:
                    logger.debug(f" File number {file_num} is below range_start {range_start}: {filename}")
                    return False
                if range_end is not None and file_num > range_end:
                    logger.debug(f" File number {file_num} is above range_end {range_end}: {filename}")
                    return False

        logger.info(f"[OK] File ACCEPTED: {filename}")
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

@app.route('/browse_folder')
def browse_folder():
    """Open a native OS folder picker dialog and return the selected path.
    Uses osascript on macOS, PowerShell on Windows — no tkinter required."""
    import subprocess
    import sys

    try:
        if sys.platform == 'darwin':
            # macOS: AppleScript via osascript (built-in, zero dependencies)
            script = (
                'tell application "Finder"\n'
                '    activate\n'
                '    set chosen to choose folder with prompt "Select Data Folder:"\n'
                '    return POSIX path of chosen\n'
                'end tell'
            )
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=60
            )
            path = result.stdout.strip().rstrip('/')
            return {'path': path}

        elif sys.platform == 'win32':
            # Windows: PowerShell FolderBrowserDialog (built-in, zero dependencies)
            ps_script = (
                'Add-Type -AssemblyName System.Windows.Forms;'
                '$d = New-Object System.Windows.Forms.FolderBrowserDialog;'
                '$d.Description = "Select Data Folder";'
                '$d.ShowNewFolderButton = $true;'
                'if ($d.ShowDialog() -eq "OK") { $d.SelectedPath }'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=60
            )
            path = result.stdout.strip()
            return {'path': path}

        else:
            return {'path': '', 'error': 'Folder picker not supported on this platform'}, 200

    except subprocess.TimeoutExpired:
        return {'path': ''}, 200  # user cancelled or dialog timed out
    except Exception as e:
        return {'path': '', 'error': str(e)}, 200

@app.route('/clear_data', methods=['POST'])
def clear_data():
    """Clear all stored data"""
    memory_store.clear()
    return {'status': 'success', 'message': 'All data cleared'}, 200

@app.route('/api/get_voltammogram')
def get_voltammogram():
    """Re-read a specific SWV file and return its voltammogram for post-correction."""
    frequency = request.args.get('frequency', type=int)
    file_number = request.args.get('file_number', type=int)
    electrode = request.args.get('electrode', default='averaged')
    peaks_only = request.args.get('peaks_only', default='0') == '1'

    if frequency is None or file_number is None:
        return {'status': 'error', 'message': 'frequency and file_number are required'}, 400

    # peaks_only mode: just return the stored peak value without re-analyzing the file
    if peaks_only:
        electrode_key = f'electrode_{electrode}'
        freq_str = str(frequency)
        file_num_str = str(file_number)
        with memory_store.lock:
            current_peak = memory_store.trend_data['raw_peaks'].get(electrode_key, {}).get(freq_str, {}).get(file_num_str)
            current_potential = memory_store.trend_data['peak_potentials'].get(electrode_key, {}).get(freq_str, {}).get(file_num_str)
        return {'status': 'success', 'current_stored_peak': current_peak, 'current_stored_potential': current_potential}

    folder = file_monitor.folder_path if file_monitor else None
    if not folder or not os.path.isdir(folder):
        return {'status': 'error', 'message': 'No active monitoring folder'}, 400

    # Find the matching file by exact frequency + file_number, preferring text files
    TEXT_EXTENSIONS = {'.txt', '.csv', '.dta', '.dat'}
    matches = []
    try:
        for fname in os.listdir(folder):
            if os.path.splitext(fname)[1].lower() not in TEXT_EXTENSIONS:
                continue
            fn, fq = extract_file_number_and_frequency(fname)
            if fn == file_number and fq == frequency:
                matches.append(os.path.join(folder, fname))
    except Exception as e:
        return {'status': 'error', 'message': f'Error scanning folder: {e}'}, 500

    if not matches:
        return {'status': 'error', 'message': f'File not found for {frequency}Hz, file #{file_number}'}, 404

    filepath = matches[0]
    params = memory_store.current_params.get('analysisParams', {}).copy()
    params['frequency'] = frequency
    selected_electrode = None if electrode == 'averaged' else int(electrode)

    try:
        import tempfile

        # Read raw bytes with BOM detection, write clean UTF-8 temp file (same as process_file_in_background).
        with open(filepath, 'rb') as fh:
            raw_bytes = fh.read()
        if raw_bytes.startswith(b'\xff\xfe'):
            content = raw_bytes[2:].decode('utf-16-le', errors='ignore')
        elif raw_bytes.startswith(b'\xfe\xff'):
            content = raw_bytes[2:].decode('utf-16-be', errors='ignore')
        else:
            content = raw_bytes.decode('utf-8', errors='ignore')

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as tmp:
            tmp.write(content.encode('utf-8'))
            temp_filepath = tmp.name

        logger.info(f"[VOLTAMMOGRAM] running analyze_swv_data: file={os.path.basename(filepath)}, selected={selected_electrode}")

        try:
            result = analyze_swv_data(temp_filepath, params, selected_electrode)
        finally:
            try:
                os.unlink(temp_filepath)
            except Exception:
                pass

        logger.info(f"[VOLTAMMOGRAM] analyze_swv_data status={result.get('status')}, "
                    f"potentials={len(result.get('potentials', []))}")

    except Exception as e:
        logger.exception("[VOLTAMMOGRAM] analyze_swv_data failed")
        return {'status': 'error', 'message': f'Data read error: {e}'}, 500

    if result.get('status') == 'error' or not result.get('potentials'):
        return {'status': 'error', 'message': result.get('message', 'No data found.')}, 404

    potentials = result.get('potentials', [])
    currents = result.get('raw_currents', [])

    # Retrieve stored peak value from memory; fall back to freshly computed value
    electrode_key = f'electrode_{electrode}'
    freq_str = str(frequency)
    file_num_str = str(file_number)
    with memory_store.lock:
        current_peak = memory_store.trend_data['raw_peaks'].get(electrode_key, {}).get(freq_str, {}).get(file_num_str)
        current_potential = memory_store.trend_data['peak_potentials'].get(electrode_key, {}).get(freq_str, {}).get(file_num_str)

    if current_peak is None:
        current_peak = result.get('peak_value')
    if current_potential is None:
        current_potential = result.get('peak_info', {}).get('peak_potential')

    peak_info = result.get('peak_info', {})
    if current_potential is not None and 'peak_potential' not in peak_info:
        peak_info['peak_potential'] = current_potential

    return {
        'status': 'success',
        'potentials': potentials,
        'raw_currents': currents,
        'smoothed_currents': result.get('smoothed_currents', []),
        'regression_line': result.get('regression_line', []),
        'adjusted_potentials': result.get('adjusted_potentials', potentials),
        'peak_info': peak_info,
        'peak_value': current_peak,
        'current_stored_peak': current_peak,
        'current_stored_potential': current_potential,
    }

@app.route('/api/apply_correction', methods=['POST'])
def apply_correction():
    """Update the stored peak value and peak potential for a specific data point."""
    data = request.get_json()
    if not data:
        return {'status': 'error', 'message': 'JSON body required'}, 400

    frequency = data.get('frequency')
    file_number = data.get('file_number')
    electrode = data.get('electrode', 'averaged')
    new_peak_value = data.get('new_peak_value')
    new_peak_potential = data.get('new_peak_potential')

    if frequency is None or file_number is None or new_peak_value is None:
        return {'status': 'error', 'message': 'frequency, file_number, and new_peak_value are required'}, 400

    electrode_key = f'electrode_{electrode}'
    freq_str = str(frequency)
    file_num_str = str(file_number)

    new_averaged_peak = None
    new_averaged_potential = None

    with memory_store.lock:
        # Update raw_peaks for the individual electrode
        if electrode_key not in memory_store.trend_data['raw_peaks']:
            memory_store.trend_data['raw_peaks'][electrode_key] = {}
        if freq_str not in memory_store.trend_data['raw_peaks'][electrode_key]:
            memory_store.trend_data['raw_peaks'][electrode_key][freq_str] = {}
        memory_store.trend_data['raw_peaks'][electrode_key][freq_str][file_num_str] = new_peak_value

        # Update peak_potentials if provided
        if new_peak_potential is not None:
            if electrode_key not in memory_store.trend_data['peak_potentials']:
                memory_store.trend_data['peak_potentials'][electrode_key] = {}
            if freq_str not in memory_store.trend_data['peak_potentials'][electrode_key]:
                memory_store.trend_data['peak_potentials'][electrode_key][freq_str] = {}
            memory_store.trend_data['peak_potentials'][electrode_key][freq_str][file_num_str] = new_peak_potential

        # Recalculate averaged value from all individual (numeric-indexed) electrodes
        peak_vals, pot_vals = [], []
        for key, freq_data in memory_store.trend_data['raw_peaks'].items():
            if not key.startswith('electrode_'):
                continue
            suffix = key[len('electrode_'):]
            if not suffix.lstrip('-').isdigit():   # skip 'averaged'
                continue
            val = freq_data.get(freq_str, {}).get(file_num_str)
            if val is not None:
                peak_vals.append(val)
        for key, freq_data in memory_store.trend_data['peak_potentials'].items():
            if not key.startswith('electrode_'):
                continue
            suffix = key[len('electrode_'):]
            if not suffix.lstrip('-').isdigit():
                continue
            val = freq_data.get(freq_str, {}).get(file_num_str)
            if val is not None:
                pot_vals.append(val)

        if peak_vals:
            new_averaged_peak = sum(peak_vals) / len(peak_vals)
            avg_key = 'electrode_averaged'
            memory_store.trend_data['raw_peaks'].setdefault(avg_key, {}).setdefault(freq_str, {})[file_num_str] = new_averaged_peak
        if pot_vals:
            new_averaged_potential = sum(pot_vals) / len(pot_vals)
            avg_key = 'electrode_averaged'
            memory_store.trend_data['peak_potentials'].setdefault(avg_key, {}).setdefault(freq_str, {})[file_num_str] = new_averaged_potential

    logger.info(f"[POST-CORRECTION] Updated {electrode_key}/{freq_str}/#{file_num_str}: peak={new_peak_value:.4e}, avg_peak={new_averaged_peak}")
    return {
        'status': 'success',
        'new_averaged_peak': new_averaged_peak,
        'new_averaged_potential': new_averaged_potential,
    }

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
    mode = data.get('mode', 'default')

    if not folder_path:
        emit('folder_monitor_error', {'message': 'No folder path provided', 'mode': mode})
        return

    if not os.path.isdir(folder_path):
        emit('folder_monitor_error', {'message': f'Invalid folder path: {folder_path}', 'mode': mode})
        return

    try:
        # Stop existing monitor if any
        if file_observer:
            file_observer.stop()
            file_observer.join()

        # Create new monitor
        filters = filters.copy()
        filters['monitor_mode'] = mode
        file_monitor = LocalFileMonitor(socketio, filters, folder_path)
        file_observer = Observer()
        file_observer.schedule(file_monitor, folder_path, recursive=False)
        file_observer.start()

        logger.info(f"Started folder monitoring: {folder_path}")
        emit('folder_monitor_started', {
            'folder_path': folder_path,
            'filters': filters,
            'mode': mode
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

            # Sort files by name (natural sort: 1, 2, 10 not 1, 10, 2)
            existing_files.sort(key=natural_sort_key)

            logger.info(f"Found {len(existing_files)} existing files in folder")
            emit('folder_files_list', {
                'files': existing_files,
                'folder_path': folder_path,
                'mode': mode
            })

            # Note: Existing files will be processed when analysis session starts
            # (see start_frequency_map_session or start_analysis_session handlers)
            logger.info(f"Folder monitoring ready. Existing files will be processed when analysis starts.")

        except Exception as e:
            logger.error(f"Error scanning existing files: {e}")

    except Exception as e:
        logger.error(f"Error starting folder monitor: {e}")
        emit('folder_monitor_error', {'message': str(e), 'mode': mode})

@socketio.on('stop_folder_monitoring')
def stop_folder_monitoring(data=None):
    """Stop folder monitoring and clear SWV analysis data"""
    global file_observer, file_monitor
    requested_mode = (data or {}).get('mode')
    current_mode = file_monitor.filters.get('monitor_mode') if file_monitor else requested_mode or 'default'

    try:
        if file_observer:
            logger.info("Stopping folder monitoring...")

            # First, signal the monitor to stop processing new files
            if file_monitor:
                file_monitor.stop()

            # Then stop the observer
            file_observer.stop()

            # Wait for observer to stop with timeout (max 5 seconds)
            file_observer.join(timeout=5.0)

            if file_observer.is_alive():
                logger.warning("Observer thread did not stop within timeout, forcing cleanup")

            file_observer = None
            file_monitor = None
            logger.info("Stopped folder monitoring successfully")

        # Clear SWV analysis data from memory
        memory_store.swv_results = {}
        memory_store.frequency_map_results = {}
        memory_store.peak_warnings = []
        memory_store.trend_data = {
            'raw_peaks': {},
            'peak_potentials': {},
            'x_axis_values': [],
            'filter_params': {},
            'qc_metrics': {}
        }

        logger.info("Cleared SWV analysis data")
        emit('folder_monitor_stopped', {'mode': current_mode})

    except Exception as e:
        logger.error(f"Error stopping folder monitor: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        emit('folder_monitor_error', {'message': str(e), 'mode': current_mode})

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
    """Start SWV analysis session (continuous monitor mode)"""
    global file_monitor

    try:
        analysis_params = data.get('analysisParams', {})
        filters = data.get('filters', {})
        analysis_mode = data.get('analysis_mode', 'continuous')

        # Always clear the processing queue at session start so leftover pending entries
        # from a previous session (e.g. user navigated back without stopping) don't block
        # the new session's historical scan.
        processing_queue.clear()

        # Reset accumulated session data so old warnings / trend data don't bleed in
        memory_store.peak_warnings = []
        memory_store.trend_data = {
            'raw_peaks': {},
            'peak_potentials': {},
            'x_axis_values': [],
            'filter_params': {},
            'qc_metrics': {}
        }

        # Store parameters in memory
        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'analysis_mode': analysis_mode
        })

        logger.info(f"[CONTINUOUS] Started SWV analysis session: mode={analysis_mode}")
        logger.info(f"[CONTINUOUS] Analysis params: num_files={analysis_params.get('num_files')}, frequencies={analysis_params.get('frequencies')}")
        logger.info(f"[CONTINUOUS] Filters: {filters}")

        # Update file monitor filters if monitoring is active
        if file_monitor:
            # Reset sequence tracking so gap detection starts fresh for this session
            file_monitor.reset_sequence()

            frequencies = analysis_params.get('frequencies', [])
            if frequencies:
                freq_filter_str = ','.join(str(f) for f in frequencies)
                file_monitor.filters['frequency'] = freq_filter_str
                logger.info(f"[CONTINUOUS] Updated file monitor frequency filter: {freq_filter_str}")

            # Update file number range filters
            if 'range_start' in filters:
                file_monitor.filters['range_start'] = filters['range_start']
                logger.info(f"[CONTINUOUS] Updated file monitor range_start: {filters['range_start']}")
            if 'range_end' in filters:
                file_monitor.filters['range_end'] = filters['range_end']
                logger.info(f"[CONTINUOUS] Updated file monitor range_end: {filters['range_end']}")

        # If folder monitoring is active, reprocess existing files
        if file_monitor and file_monitor.folder_path:
            logger.info(f"[CONTINUOUS] Reprocessing existing files...")
            logger.info(f"[CONTINUOUS] File monitor filters: {file_monitor.filters}")
            folder_path = file_monitor.folder_path

            try:
                existing_files = sorted([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))], key=continuous_mode_sort_key)
                logger.info(f"[CONTINUOUS] Found {len(existing_files)} files in folder")
                logger.info(f"[CONTINUOUS] Files will be processed in order: file#1 all freqs, file#2 all freqs, ...")
                # Pause real-time monitor during batch replay to prevent race conditions
                file_monitor.pause_new_files = True
                processed_count = 0
                matched_count = 0

                for filename in existing_files:
                    if file_monitor.file_matches_filters(filename):
                        matched_count += 1
                        logger.info(f"[CONTINUOUS] File matched filters: {filename}")
                        file_path = os.path.join(folder_path, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()

                            is_safe, _ = validate_file_safety(filename, content)
                            if is_safe:
                                # Gap detection for historical scan (same as real-time watcher)
                                file_num, freq = extract_file_number_and_frequency(filename)
                                if file_num != float('inf') and freq != 0:
                                    file_monitor._check_and_report_gaps(freq, file_num, filename)

                                logger.info(f"[CONTINUOUS] Reprocessing existing file: {filename}")
                                processing_queue.clear()  # Batch replay: free queue so it never stalls
                                handle_instrument_data({
                                    'filename': filename,
                                    'content': content,
                                    'analysisParams': analysis_params
                                })
                                processing_queue.acknowledge(filename)  # Immediately release slot; no frontend ack needed for batch
                                processed_count += 1
                        except Exception as e:
                            logger.error(f"Error reprocessing file {filename}: {e}")

                logger.info(f"[CONTINUOUS] Reprocessing complete: {matched_count} files matched filters, {processed_count} files processed")
            except Exception as e:
                logger.error(f"Error during file reprocessing: {e}")
            finally:
                # Resume real-time monitor after batch replay
                file_monitor.pause_new_files = False

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
    processing_queue.clear()
    emit('analysis_session_stopped', {'status': 'success'})

@socketio.on('acknowledge_file_processed')
def handle_file_acknowledgment(data):
    """Handle frontend acknowledgment that file was processed and rendered"""
    global processing_queue
    filename = data.get('filename')
    if filename:
        processing_queue.acknowledge(filename)

@socketio.on('start_cv_analysis_session')
def handle_start_cv_analysis_session(data):
    """Start CV analysis session"""
    global file_observer, file_monitor

    try:
        filters = data.get('filters', {})
        analysis_params = data.get('analysisParams', {})
        folder_path = filters.get('folder_path', '')
        file_handle = filters.get('handle', '')

        # Store analysis parameters
        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'analysis_type': 'cv'
        })

        logger.info(f"[CV SESSION] Starting CV analysis session")
        logger.info(f"[CV SESSION] Folder: {folder_path}, Handle: {file_handle}")

        # Start folder monitoring if folder path provided
        if folder_path and os.path.isdir(folder_path):
            # Stop existing monitor if any
            if file_observer:
                try:
                    if file_monitor:
                        file_monitor.stop()
                    file_observer.stop()
                    file_observer.join(timeout=2.0)
                except:
                    pass
                file_observer = None
                file_monitor = None

            # Create new monitor with CV-specific filters
            cv_filters = {
                'handle': file_handle,
                'frequency': '',  # CV files may not have frequency in filename
                'fileExtension': analysis_params.get('file_extension', '.txt'),
                'analysisParams': analysis_params
            }

            file_monitor = LocalFileMonitor(socketio, cv_filters, folder_path)
            file_observer = Observer()
            file_observer.schedule(file_monitor, folder_path, recursive=False)
            file_observer.start()

            logger.info(f"[CV SESSION] Started folder monitoring: {folder_path}")

            # Scan and process existing files in the folder
            try:
                logger.info(f"[CV SESSION] Scanning existing files in: {folder_path}")
                files = os.listdir(folder_path)

                # Filter files matching the handle and extension
                matching_files = []
                for filename in files:
                    if os.path.isfile(os.path.join(folder_path, filename)):
                        # Check file extension
                        file_ext = cv_filters.get('fileExtension', '.txt')
                        if not filename.lower().endswith(file_ext.lower()):
                            continue

                        # Check file handle
                        if file_handle and not filename.startswith(file_handle):
                            continue

                        matching_files.append(filename)

                # Sort files naturally (1, 2, 10 not 1, 10, 2)
                matching_files.sort(key=natural_sort_key)

                logger.info(f"[CV SESSION] Found {len(matching_files)} existing CV files to process")

                # Process existing files
                for filename in matching_files:
                    try:
                        file_path = os.path.join(folder_path, filename)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Validate safety
                        is_safe, error_msg = validate_file_safety(filename, content)
                        if is_safe:
                            logger.info(f"[CV SESSION] Processing existing file: {filename}")
                            handle_cv_data({
                                'filename': filename,
                                'content': content
                            })
                        else:
                            logger.warning(f"[CV SESSION] Skipping unsafe file: {filename}")
                    except Exception as e:
                        logger.error(f"[CV SESSION] Error processing existing file {filename}: {e}")

            except Exception as e:
                logger.error(f"[CV SESSION] Error scanning existing files: {e}")

            emit('cv_session_started', {
                'status': 'success',
                'message': f'CV session started. Monitoring folder: {folder_path}'
            })
        else:
            logger.warning(f"[CV SESSION] No valid folder path provided: {folder_path}")
            emit('cv_session_started', {
                'status': 'success',
                'message': 'CV session started (no folder monitoring)'
            })

    except Exception as e:
        logger.error(f"Error starting CV session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('cv_session_started', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('stop_cv_analysis_session')
def handle_stop_cv_analysis_session(data):
    """Stop CV analysis session and folder monitoring"""
    global file_observer, file_monitor

    try:
        logger.info("Stopping CV analysis session...")

        # Stop file monitoring if active
        if file_observer:
            if file_monitor:
                file_monitor.stop()

            file_observer.stop()
            file_observer.join(timeout=5.0)

            if file_observer.is_alive():
                logger.warning("Observer thread did not stop within timeout")

            file_observer = None
            file_monitor = None
            logger.info("Stopped folder monitoring")

        # Clear CV results from memory
        memory_store.cv_results = {}

        logger.info("CV analysis session stopped successfully")
        emit('cv_session_stopped', {'status': 'success'})

    except Exception as e:
        logger.error(f"Error stopping CV session: {e}")
        emit('cv_session_stopped', {'status': 'error', 'message': str(e)})

@socketio.on('start_frequency_map_session')
def handle_start_frequency_map_session(data):
    """Start frequency map analysis session"""
    global file_monitor

    try:
        analysis_params = data.get('analysisParams', {})
        filters = data.get('filters', {})
        raw_frequencies = data.get('frequencies', [])

        # Normalize frequencies to integers to avoid type-mismatch when comparing
        frequencies = []
        for f in raw_frequencies:
            try:
                frequencies.append(int(f))
            except Exception:
                logger.warning(f"Invalid frequency value provided, ignoring: {f}")

        memory_store.set_analysis_params({
            'analysisParams': analysis_params,
            'frequencies': frequencies,
            'analysis_mode': 'frequency_map'
        })

        logger.info(f"Started frequency map session with {len(frequencies)} frequencies: {frequencies}")
        logger.info(f"[FREQ MAP] Filters: {filters}")

        # Update file monitor filters with new frequency list
        if file_monitor:
            # Convert frequencies list to comma-separated string for filter matching
            freq_filter_str = ','.join(str(f) for f in frequencies)
            file_monitor.filters['frequency'] = freq_filter_str
            logger.info(f"Updated file monitor frequency filter: {freq_filter_str}")

            # Update file number range filters
            if 'range_start' in filters:
                file_monitor.filters['range_start'] = filters['range_start']
                logger.info(f"[FREQ MAP] Updated file monitor range_start: {filters['range_start']}")
            if 'range_end' in filters:
                file_monitor.filters['range_end'] = filters['range_end']
                logger.info(f"[FREQ MAP] Updated file monitor range_end: {filters['range_end']}")

        # If folder monitoring is active, reprocess existing files with new analysis params
        if file_monitor and file_monitor.folder_path:
            logger.info(f"[FREQ MAP START] Reprocessing existing files with analysis parameters...")
            logger.info(f"[FREQ MAP START] File monitor filters: {file_monitor.filters}")
            folder_path = file_monitor.folder_path

            try:
                existing_files = sorted([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))], key=natural_sort_key)
                logger.info(f"[FREQ MAP START] Found {len(existing_files)} files in folder")
                logger.info(f"[FREQ MAP START] Stored frequencies for validation: {frequencies} (types: {[type(f) for f in frequencies]})")
                processed_count = 0
                matched_count = 0

                for filename in existing_files:
                    if file_monitor.file_matches_filters(filename):
                        matched_count += 1
                        logger.info(f"[FREQ MAP START] File matched filters: {filename}")
                        file_path = os.path.join(folder_path, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()

                            is_safe, error_msg = validate_file_safety(filename, content)
                            if is_safe:
                                logger.info(f"Reprocessing existing file: {filename}")
                                handle_instrument_data({
                                    'filename': filename,
                                    'content': content,
                                    'analysisParams': analysis_params
                                })
                                processed_count += 1
                        except Exception as e:
                            logger.error(f"Error reprocessing file {filename}: {e}")

                logger.info(f"[FREQ MAP START] Reprocessing complete: {matched_count} files matched filters, {processed_count} files processed")
            except Exception as e:
                logger.error(f"Error during file reprocessing: {e}")

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
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_swv_data:
            logger.error("analyze_swv_data not available")
            return

        # Call analyzer
        analysis_result = analyze_swv_data(temp_filepath, params_for_this_file, selected_electrode)

        # Handle errors
        if analysis_result and analysis_result.get('status') == 'error':
            logger.error(f"Analysis error: {analysis_result.get('message')}")
            if analysis_result.get('error_type') == 'electrode_not_present_in_file':
                socketio.emit('file_processing_warning', {
                    'filename': original_filename,
                    'warning_type': 'electrode_not_present_in_file',
                    'message': analysis_result.get('message'),
                    'detected_electrodes': analysis_result.get('detected_electrodes'),
                    'requested_electrode': analysis_result.get('requested_electrode')
                })
            elif 'detected_electrodes' in analysis_result:
                socketio.emit('electrode_validation_error', {
                    'message': analysis_result.get('message'),
                    'detected_electrodes': analysis_result.get('detected_electrodes'),
                    'requested_electrode': analysis_result.get('requested_electrode')
                })
            return

        if analysis_result and analysis_result.get('warning_type') in ['no_data', 'electrode_no_valid_data']:
            socketio.emit('file_processing_warning', {
                'filename': original_filename,
                'warning_type': analysis_result.get('warning_type'),
                'message': analysis_result.get('message', 'No valid data found for this file.')
            })
            logger.warning(f"Skipping storage for {original_filename}: {analysis_result.get('message')}")
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

                # Accumulate peak detection warnings
                if analysis_result.get('status') == 'warning':
                    memory_store.add_peak_warning({
                        'filename': original_filename,
                        'frequency': frequency,
                        'file_number': file_number,
                        'warning_type': analysis_result.get('warning_type', 'unknown'),
                        'message': analysis_result.get('message', '')
                    })

                # Build update payload - always send complete data for voltammogram display
                update_payload = {
                    'filename': original_filename,
                    'electrode_index': electrode_index,
                    'individual_analysis': {
                        'potentials': analysis_result.get('potentials', []),
                        'raw_currents': analysis_result.get('raw_currents', []),
                        'smoothed_currents': analysis_result.get('smoothed_currents', []),
                        'regression_line': analysis_result.get('regression_line', []),
                        'peak_info': analysis_result.get('peak_info', {}),
                        'peak_value': peak_value,
                        'filter_params': analysis_result.get('filter_params', {}),
                        'qc_metrics': analysis_result.get('qc_metrics', {})
                    },
                    'incremental_data': {
                        'frequency': frequency,
                        'file_number': file_number,
                        'peak_value': peak_value,
                        'peak_potential': peak_potential
                    }
                }

                # Only send full trend_data every 10 files to reduce bandwidth and improve performance
                if file_number % 10 == 0:
                    trend_data_formatted = memory_store.get_trend_data_for_electrode(electrode_index)
                    update_payload['trend_data'] = trend_data_formatted
                    logger.info(f"[SYNC] File #{file_number}: Full sync with {len(trend_data_formatted.get('x_axis_values', []))} files")

                # Always include current accumulated peak warnings so frontend stays in sync
                all_warnings = memory_store.get_peak_warnings()
                if all_warnings:
                    update_payload['peak_detection_warnings'] = all_warnings

                # Emit live update to frontend
                socketio.emit('live_analysis_update', update_payload)

                # Add to pending queue (wait for frontend acknowledgment)
                processing_queue.add_pending(original_filename)

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
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.unlink(temp_filepath)
            except OSError:
                logger.warning(f"Failed to remove temp file: {temp_filepath}")

def process_frequency_map_file(original_filename, content, frequency, params, electrode_index=0):
    """
    Process file for frequency map analysis.
    Simplified from original.
    """
    # Double-check frequency is in requested list
    stored_params = memory_store.get_analysis_params()
    requested_frequencies = stored_params.get('frequencies', [])
    if requested_frequencies and frequency not in requested_frequencies:
        logger.info(f"[SKIP] Frequency {frequency}Hz not in requested list {requested_frequencies}, skipping {original_filename}")
        return

    logger.info(f"[PROCESS] Processing frequency map file: {original_filename} at {frequency}Hz")

    import tempfile
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_swv_data:
            return

        # Add frequency to params for analyzer
        params_with_freq = params.copy()
        params_with_freq['frequency'] = frequency

        # Call analyzer
        analysis_result = analyze_swv_data(temp_filepath, params_with_freq, electrode_index if electrode_index != 'averaged' else None)

        if analysis_result and analysis_result.get('warning_type') in ['no_data', 'electrode_no_valid_data']:
            socketio.emit('file_processing_warning', {
                'filename': original_filename,
                'warning_type': analysis_result.get('warning_type'),
                'message': analysis_result.get('message', 'No valid data found for this file.')
            })
            logger.warning(f"Skipping frequency-map storage for {original_filename}: {analysis_result.get('message')}")
            return

        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            peak_value = analysis_result.get('peak_value')

            # Calculate charge (peak / frequency)
            charge = (peak_value / frequency) if frequency > 0 and peak_value else 0

            # Store frequency map data with all fields needed for visualization
            freq_data = {
                'frequency': frequency,  # Add frequency to data object
                'potentials': analysis_result.get('potentials', []),
                'smoothed_currents': analysis_result.get('smoothed_currents', []),  # Keep original name
                'regression_line': analysis_result.get('regression_line', []),  # Add baseline data
                'adjusted_potentials': analysis_result.get('adjusted_potentials', []),  # Add adjusted potentials
                'charge': charge,
                'peak_value': peak_value,
                'peak_potential': analysis_result.get('peak_info', {}).get('peak_potential', None),
                'baseline_left': analysis_result.get('peak_info', {}).get('baseline_left', None),
                'baseline_right': analysis_result.get('peak_info', {}).get('baseline_right', None),
            }

            memory_store.add_frequency_map_result(electrode_index, frequency, freq_data)

            # Emit update
            socketio.emit('frequency_map_update', {
                'frequency': frequency,
                'electrode_index': electrode_index,
                'data': freq_data
            })

            logger.info(f"Frequency map file processed: {frequency}Hz, electrode_index={electrode_index}, charge={charge:.6e}, peak={peak_value:.6e}")

    except Exception as e:
        logger.error(f"Error processing frequency map file: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.unlink(temp_filepath)
            except OSError:
                logger.warning(f"Failed to remove temp file: {temp_filepath}")

def process_cv_file_in_background(original_filename, content, params, selected_electrode=None):
    """
    Process CV data file in background.
    Simplified from original.
    """
    logger.info(f"Processing CV file: {original_filename}")

    import tempfile
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_filepath = f.name

        if not analyze_cv_data:
            logger.error("analyze_cv_data not available")
            return

        # Call analyzer
        analysis_result = analyze_cv_data(temp_filepath, params, selected_electrode)

        if analysis_result and analysis_result.get('status') == 'success':
            # Store CV result in memory
            memory_store.store_cv_result(selected_electrode, original_filename, analysis_result)

            # Emit CV update (match frontend expected format)
            socketio.emit('live_cv_update', {
                'electrode_index': selected_electrode if selected_electrode is not None else 'averaged',
                'filename': original_filename,
                'cv_analysis': analysis_result,  # Frontend expects 'cv_analysis' not 'result'
                'result': analysis_result  # Keep for backward compatibility
            })

            logger.info(f"CV file processed: {original_filename}")

    except Exception as e:
        logger.error(f"Error processing CV file: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.unlink(temp_filepath)
            except OSError:
                logger.warning(f"Failed to remove temp file: {temp_filepath}")

# --- File Data Stream Events ---

@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    """
    Handle incoming SWV data files.
    Simplified from original - no user_id or agent checks.
    """
    global processing_queue

    try:
        original_filename = data.get('filename', 'unknown_file.txt')
        file_content = data.get('content', '')

        # Flow control: wait for queue to have space (don't skip files!)
        retry_count = 0
        while not processing_queue.can_process() and retry_count < 100:
            time.sleep(0.05)  # Wait 50ms
            retry_count += 1

        if not processing_queue.can_process():
            logger.error(f"[QUEUE] Timeout waiting for queue space for {original_filename}")
            return

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
        analysis_type = stored_params.get('analysis_type', 'swv')  # 'swv' or 'cv'

        if not analysis_params:
            logger.warning("No analysis parameters set")
            return

        # If this is CV analysis, route to CV handler
        if analysis_type == 'cv':
            logger.info(f"[CV] Routing to CV handler: {original_filename}")
            handle_cv_data({
                'filename': original_filename,
                'content': file_content
            })
            return

        # For SWV analysis, extract frequency from filename (handle leading zeros like _0005Hz)
        match = re.search(r'_0*(\d+)Hz', original_filename, re.IGNORECASE)
        if not match:
            logger.warning(f"Filename does not match expected pattern: {original_filename}")
            return

        frequency = int(match.group(1))  # Convert to int to remove leading zeros
        selected_electrodes = analysis_params.get('selected_electrodes', [])

        # Process based on mode
        if analysis_mode == 'frequency_map':
            # Check if this frequency is in the requested frequency list
            requested_frequencies = stored_params.get('frequencies', [])
            logger.info(f"[FREQ VALIDATION] File: {original_filename}, Freq: {frequency} (type: {type(frequency)})")
            logger.info(f"[FREQ VALIDATION] Requested freqs: {requested_frequencies} (types: {[type(f) for f in requested_frequencies] if requested_frequencies else 'empty'})")

            if requested_frequencies and frequency not in requested_frequencies:
                logger.info(f"[SKIP] Frequency {frequency}Hz not in requested list {requested_frequencies}, skipping {original_filename}")
                return

            logger.info(f"[PROCESS] Processing in FREQUENCY MAP mode: {original_filename} (freq={frequency}Hz)")

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
            logger.info(f"[OK] Processing in CONTINUOUS mode: {original_filename} (freq={frequency}Hz)")

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

        # Emit status to frontend
        socketio.emit('file_processing_status', {
            'filename': original_filename,
            'status': 'analyzing',
            'message': f'Analyzing {original_filename} ({analysis_mode} mode, {frequency}Hz)'
        })

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
    from data_processing.cv_analyzer import _read_cv_data_simple
    import tempfile

    try:
        filters = data.get('filters', {})
        analysis_params = data.get('analysisParams', {})

        folder_path = filters.get('folder_path', '')
        file_handle = filters.get('handle', '')
        file_extension = analysis_params.get('file_extension', '.txt')
        selected_electrode = analysis_params.get('selected_electrode', None)

        logger.info(f"[CV PREVIEW] Looking for CV file in: {folder_path}")
        logger.info(f"[CV PREVIEW] Handle: '{file_handle}', Extension: '{file_extension}'")

        if not folder_path or not os.path.isdir(folder_path):
            emit('cv_preview_response', {
                'status': 'error',
                'message': f'Invalid folder path: "{folder_path}"'
            })
            return

        # Find first matching CV file
        try:
            files = os.listdir(folder_path)
            cv_files = []
            for filename in files:
                # Skip directories
                if os.path.isdir(os.path.join(folder_path, filename)):
                    continue

                # Always reject known binary formats
                _cv_text_extensions = {'.txt', '.csv', '.dat', '.tsv', '.asc', '.dta', '.mpt'}
                file_ext_lower = os.path.splitext(filename)[1].lower()
                if file_ext_lower and file_ext_lower not in _cv_text_extensions:
                    continue

                # Check file extension (if specified)
                if file_extension and file_extension.strip():
                    if not filename.lower().endswith(file_extension.lower()):
                        continue

                # Check file handle
                if file_handle and not filename.startswith(file_handle):
                    continue

                cv_files.append(filename)

            if not cv_files:
                # Build helpful error message
                if file_extension and file_extension.strip():
                    pattern = f'"{file_handle}*{file_extension}"'
                else:
                    pattern = f'"{file_handle}*"' if file_handle else 'any files'

                emit('cv_preview_response', {
                    'status': 'error',
                    'message': f'No CV files found matching {pattern} in folder. Found {len(files)} total files.'
                })
                return

            # Sort naturally and get first file (1, 2, 10 not 1, 10, 2)
            cv_files.sort(key=natural_sort_key)
            first_file = cv_files[0]
            file_path = os.path.join(folder_path, first_file)

            logger.info(f"[CV PREVIEW] Found {len(cv_files)} CV files, using: {first_file}")

            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Create temp file and read CV data
            with tempfile.NamedTemporaryFile(mode='w', suffix=file_extension, delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Read CV data using the analyzer
                potentials, currents = _read_cv_data_simple(temp_path, selected_electrode)

                if not potentials or not currents:
                    emit('cv_preview_response', {
                        'status': 'error',
                        'message': 'Failed to read CV data from file'
                    })
                    return

                logger.info(f"[CV PREVIEW] Successfully read {len(potentials)} data points")

                # Detect number of electrodes by reading file columns
                import numpy as np
                try:
                    data = np.loadtxt(temp_path, delimiter=' ')
                except:
                    try:
                        data = np.loadtxt(temp_path, delimiter='\t')
                    except:
                        try:
                            data = np.loadtxt(temp_path, delimiter=',')
                        except:
                            data = np.loadtxt(temp_path)

                num_electrodes = data.shape[1] - 1 if data.ndim == 2 else 0
                logger.info(f"[CV PREVIEW] Detected {num_electrodes} electrodes in file")

                # Store content for segment detection
                handle_get_cv_preview.last_content = content

                # Send response
                emit('cv_preview_response', {
                    'status': 'success',
                    'cv_data': {
                        'voltage': potentials,
                        'current': currents
                    },
                    'content': content,
                    'filename': first_file,
                    'num_electrodes': num_electrodes
                })

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"[CV PREVIEW] Error reading files: {e}")
            import traceback
            logger.error(traceback.format_exc())
            emit('cv_preview_response', {
                'status': 'error',
                'message': f'Error reading CV file: {str(e)}'
            })

    except Exception as e:
        logger.error(f"[CV PREVIEW] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('cv_preview_response', {
            'status': 'error',
            'message': f'Error loading preview: {str(e)}'
        })

@socketio.on('get_cv_segments')
def handle_get_cv_segments(data):
    """Get CV segment data"""
    from data_processing.cv_analyzer import _read_and_segment_data
    import tempfile

    try:
        params = data.get('params', {})
        content = data.get('content', '')

        logger.info(f"[CV SEGMENTS] Received request for segment detection")
        logger.info(f"[CV SEGMENTS] Params keys: {params.keys() if params else 'None'}")
        logger.info(f"[CV SEGMENTS] Content length: {len(content)}")

        # Validate params
        if not params:
            emit('cv_segments_response', {
                'status': 'error',
                'message': 'No analysis parameters provided'
            })
            return

        # Get file extension from params
        file_extension = params.get('file_extension', '.txt')
        if not file_extension or not file_extension.strip():
            file_extension = '.txt'

        selected_electrode = params.get('selected_electrode', None)

        # If no content provided, try to get from session or use stored preview content
        if not content and hasattr(handle_get_cv_preview, 'last_content'):
            content = handle_get_cv_preview.last_content
            logger.info(f"[CV SEGMENTS] Using stored preview content: {len(content)} bytes")

        if not content:
            emit('cv_segments_response', {
                'status': 'error',
                'message': 'No CV file content available. Please load preview first.'
            })
            return

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix=file_extension, delete=False, encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            logger.info(f"[CV SEGMENTS] Processing file with {len(content)} bytes")

            # Read and segment CV data
            _, _, segment_dict = _read_and_segment_data(temp_path, params, selected_electrode)

            if not segment_dict:
                emit('cv_segments_response', {
                    'status': 'error',
                    'message': 'Failed to detect segments. Check your CV data format.'
                })
                return

            # Build segment information
            segments = list(segment_dict.keys())
            segment_info = {}
            forward_segments = []
            reverse_segments = []

            for seg_num, seg_data in segment_dict.items():
                seg_potentials = seg_data.get('potentials', [])
                seg_type = seg_data.get('type', 'unknown')

                if seg_type == 'forward':
                    forward_segments.append(seg_num)
                elif seg_type == 'reverse':
                    reverse_segments.append(seg_num)

                segment_info[str(seg_num)] = {
                    'type': seg_type,
                    'points': len(seg_potentials),
                    'potential_range': [min(seg_potentials), max(seg_potentials)] if seg_potentials else [0, 0]
                }

            logger.info(f"[CV SEGMENTS] Found {len(segments)} segments: {len(forward_segments)} forward, {len(reverse_segments)} reverse")

            emit('cv_segments_response', {
                'status': 'success',
                'segments': segments,
                'segment_info': segment_info,
                'forward_segments': forward_segments,
                'reverse_segments': reverse_segments
            })

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        logger.error(f"[CV SEGMENTS] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('cv_segments_response', {
            'status': 'error',
            'message': f'Segment detection failed: {str(e)}'
        })

# --- Export Data Events ---

@socketio.on('request_pack_xlsx_from_csv')
def handle_pack_xlsx_from_csv(data):
    """Package sectioned CSV text into a multi-sheet XLSX workbook."""
    try:
        csv_text = (data or {}).get('csv_text', '')
        filename = (data or {}).get('filename', 'export.xlsx')
        target = (data or {}).get('target', 'generic')

        if not csv_text.strip():
            emit('pack_xlsx_response', {
                'status': 'error',
                'target': target,
                'message': 'No export data available'
            })
            return

        sheet_defs = _sheet_defs_from_sectioned_csv(csv_text)
        workbook_bytes = _build_xlsx_bytes(sheet_defs)

        emit('pack_xlsx_response', {
            'status': 'success',
            'target': target,
            'filename': filename,
            'content_b64': base64.b64encode(workbook_bytes).decode('ascii')
        })
    except Exception as e:
        logger.error(f"Error packaging XLSX workbook: {e}")
        logger.error(traceback.format_exc())
        emit('pack_xlsx_response', {
            'status': 'error',
            'target': (data or {}).get('target', 'generic'),
            'message': str(e)
        })

@socketio.on('request_export_data')
def handle_export_request(data):
    """Export SWV data to CSV in frequency map format for continuous mode"""
    try:
        import numpy as np
        from datetime import datetime

        trend_data = memory_store.get_trend_data()

        if not trend_data['raw_peaks']:
            emit('export_data_response', {
                'status': 'error',
                'message': 'No data available to export'
            })
            return

        # Determine normalization baseline file from request parameter (before metadata)
        normalization_point = int(data.get('normalization_point', 1)) if data else 1

        csv_lines = []

        # Metadata
        stored_params = memory_store.get_analysis_params()
        analysis_params_meta = stored_params.get('analysisParams', {})
        selected_options = analysis_params_meta.get('SelectedOptions', 'Peak Height Extraction')

        csv_lines.append(f"# SACMES SWV Continuous Mode Data")
        csv_lines.append(f"# Export Date: {datetime.now().isoformat()}")
        csv_lines.append(f"# Analysis Mode: {selected_options}")
        csv_lines.append(f"# Normalization Reference: File #{normalization_point}")
        csv_lines.append('')

        # Extract electrode indices
        individual_electrodes = []
        for key in trend_data['raw_peaks'].keys():
            if key.startswith('electrode_'):
                try:
                    idx = int(key.split('_')[1])
                    individual_electrodes.append(idx)
                except (ValueError, IndexError):
                    pass
        individual_electrodes.sort()

        if not individual_electrodes:
            emit('export_data_response', {
                'status': 'error',
                'message': 'No electrode data available'
            })
            return

        # Get all frequencies and file numbers
        all_freqs_set = set()
        all_file_nums_set = set()
        for electrode_key, freq_data in trend_data['raw_peaks'].items():
            for freq_str, file_data in freq_data.items():
                all_freqs_set.add(freq_str)
                for file_num_str in file_data.keys():
                    all_file_nums_set.add(file_num_str)

        # Sort frequencies and file numbers numerically
        frequencies = sorted(all_freqs_set, key=lambda x: float(x))
        file_numbers = sorted(all_file_nums_set, key=lambda x: int(x))

        # Identify low and high frequencies (min and max)
        low_freq_str = frequencies[0]
        high_freq_str = frequencies[-1]

        logger.info(f"[EXPORT] Frequencies: {frequencies}, Low: {low_freq_str}, High: {high_freq_str}")
        logger.info(f"[EXPORT] File numbers: {file_numbers}")
        logger.info(f"[EXPORT] Electrodes: {individual_electrodes}")

        # Helper function to calculate stats
        def calculate_stats(values):
            valid_values = [v for v in values if v is not None and not np.isnan(v)]
            if not valid_values:
                return None, None
            mean = np.mean(valid_values)
            std = np.std(valid_values, ddof=1) if len(valid_values) > 1 else 0.0
            return mean, std

        # Helper function to get peak value
        def get_peak_value(electrode_idx, freq_str, file_num_str):
            electrode_key = f'electrode_{electrode_idx}'
            if electrode_key in trend_data['raw_peaks']:
                if freq_str in trend_data['raw_peaks'][electrode_key]:
                    return trend_data['raw_peaks'][electrode_key][freq_str].get(file_num_str)
            return None

        norm_file_str = str(normalization_point)
        logger.info(f"[EXPORT] Using normalization point: file #{normalization_point}")

        # Calculate normalized peaks
        normalized_peaks = {}  # {electrode_idx: {freq_str: {file_num_str: normalized_value}}}

        for electrode_idx in individual_electrodes:
            normalized_peaks[electrode_idx] = {}
            for freq_str in frequencies:
                # Get baseline from user-specified normalization file
                baseline_value = get_peak_value(electrode_idx, freq_str, norm_file_str)
                # Fall back to first available file if specified file has no data
                if baseline_value is None:
                    for file_num_str in file_numbers:
                        baseline_value = get_peak_value(electrode_idx, freq_str, file_num_str)
                        if baseline_value is not None:
                            break

                if baseline_value is None or baseline_value == 0:
                    continue

                # Calculate normalized values
                normalized_peaks[electrode_idx][freq_str] = {}
                for file_num_str in file_numbers:
                    peak_value = get_peak_value(electrode_idx, freq_str, file_num_str)
                    if peak_value is not None:
                        normalized_peaks[electrode_idx][freq_str][file_num_str] = peak_value / baseline_value

        # --- Build horizontal layout with three sections side by side ---

        # Section titles
        csv_lines.append(f"## Low Frequency: {low_freq_str} Hz,,,,## High Frequency: {high_freq_str} Hz,,,,## KDM (Kinetic Difference Metric)")
        csv_lines.append(f"## Formula: ((High Freq Normalized - Low Freq Normalized) + 1) * 100")
        csv_lines.append('')

        # Build combined header
        header = ['File Number']

        # Low frequency columns
        header.extend([f'Low_{low_freq_str}Hz_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Low_Average', 'Low_Std'])
        header.extend(['', '', ''])  # Separator columns

        # High frequency columns
        header.extend([f'High_{high_freq_str}Hz_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['High_Average', 'High_Std'])
        header.extend(['', '', ''])  # Separator columns

        # KDM columns
        header.extend([f'KDM_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['KDM_Average', 'KDM_Std'])

        csv_lines.append(','.join(header))

        # Build data rows - all three sections in one row per file
        for file_num_str in file_numbers:
            row = [file_num_str]

            # --- Low Frequency Data ---
            low_values = []
            for idx in individual_electrodes:
                peak_value = get_peak_value(idx, low_freq_str, file_num_str)
                low_values.append(peak_value)
                if peak_value is not None:
                    row.append(f'{peak_value:.6e}')
                else:
                    row.append('N/A')

            # Low frequency average and std
            low_mean, low_std = calculate_stats(low_values)
            if low_mean is not None:
                row.append(f'{low_mean:.6e}')
            else:
                row.append('N/A')
            if low_std is not None:
                row.append(f'{low_std:.6e}')
            else:
                row.append('N/A')

            # Separator
            row.extend(['', '', ''])

            # --- High Frequency Data ---
            high_values = []
            for idx in individual_electrodes:
                peak_value = get_peak_value(idx, high_freq_str, file_num_str)
                high_values.append(peak_value)
                if peak_value is not None:
                    row.append(f'{peak_value:.6e}')
                else:
                    row.append('N/A')

            # High frequency average and std
            high_mean, high_std = calculate_stats(high_values)
            if high_mean is not None:
                row.append(f'{high_mean:.6e}')
            else:
                row.append('N/A')
            if high_std is not None:
                row.append(f'{high_std:.6e}')
            else:
                row.append('N/A')

            # Separator
            row.extend(['', '', ''])

            # --- KDM Data ---
            kdm_values = []
            for idx in individual_electrodes:
                # Get normalized values
                low_normalized = None
                high_normalized = None

                if idx in normalized_peaks:
                    if low_freq_str in normalized_peaks[idx]:
                        low_normalized = normalized_peaks[idx][low_freq_str].get(file_num_str)
                    if high_freq_str in normalized_peaks[idx]:
                        high_normalized = normalized_peaks[idx][high_freq_str].get(file_num_str)

                # Calculate KDM
                if low_normalized is not None and high_normalized is not None:
                    kdm_value = ((high_normalized - low_normalized) + 1) * 100
                    kdm_values.append(kdm_value)
                    row.append(f'{kdm_value:.4f}')
                else:
                    kdm_values.append(None)
                    row.append('N/A')

            # KDM average and std
            kdm_mean, kdm_std = calculate_stats(kdm_values)
            if kdm_mean is not None:
                row.append(f'{kdm_mean:.4f}')
            else:
                row.append('N/A')
            if kdm_std is not None:
                row.append(f'{kdm_std:.4f}')
            else:
                row.append('N/A')

            csv_lines.append(','.join(row))

        csv_data = '\n'.join(csv_lines)
        workbook_bytes = _build_xlsx_bytes(_sheet_defs_from_sectioned_csv(csv_data))

        emit('export_data_response', {
            'status': 'success',
            'filename': f"SACMES_SWV_AllElectrodes_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            'content_b64': base64.b64encode(workbook_bytes).decode('ascii')
        })

        logger.info("SWV continuous mode data exported successfully")

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('export_data_response', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('request_export_cv_data')
def handle_cv_export_request(data):
    """Export CV data to CSV in horizontal layout format"""
    try:
        import numpy as np
        from datetime import datetime

        cv_results = memory_store.get_cv_results()

        if not cv_results:
            emit('export_cv_data_response', {
                'status': 'error',
                'message': 'No CV data available to export'
            })
            return

        csv_lines = []

        # Metadata
        csv_lines.append(f"# SACMES CV Data")
        csv_lines.append(f"# Export Date: {datetime.now().isoformat()}")
        csv_lines.append('')

        # Extract electrode indices
        individual_electrodes = []
        for key in cv_results.keys():
            if key.startswith('electrode_'):
                try:
                    idx = int(key.split('_')[1])
                    individual_electrodes.append(idx)
                except (ValueError, IndexError):
                    pass
        individual_electrodes.sort()

        if not individual_electrodes:
            emit('export_cv_data_response', {
                'status': 'error',
                'message': 'No electrode data available'
            })
            return

        # Collect all unique filenames and extract file numbers
        file_data = {}  # {file_number: filename}
        for electrode_key, file_results in cv_results.items():
            for filename in file_results.keys():
                # Try to extract file number from filename (e.g., CV_1.txt -> 1)
                match = re.search(r'_(\d+)(?:\.|$)', filename)
                if match:
                    file_num = int(match.group(1))
                    if file_num not in file_data:
                        file_data[file_num] = filename

        # Sort by file number
        file_numbers = sorted(file_data.keys())

        logger.info(f"[CV EXPORT] Electrodes: {individual_electrodes}")
        logger.info(f"[CV EXPORT] File numbers: {file_numbers}")

        # Helper function to calculate stats
        def calculate_stats(values):
            valid_values = [v for v in values if v is not None and not np.isnan(v)]
            if not valid_values:
                return None, None
            mean = np.mean(valid_values)
            std = np.std(valid_values, ddof=1) if len(valid_values) > 1 else 0.0
            return mean, std

        # Helper function to get CV metric
        def get_cv_metric(electrode_idx, filename, scan_type, metric):
            electrode_key = f'electrode_{electrode_idx}'
            if electrode_key in cv_results:
                if filename in cv_results[electrode_key]:
                    scan_data = cv_results[electrode_key][filename].get(scan_type, {})
                    return scan_data.get(metric)
            return None

        # Helper function to get peak separation
        def get_peak_separation(electrode_idx, filename):
            electrode_key = f'electrode_{electrode_idx}'
            if electrode_key in cv_results:
                if filename in cv_results[electrode_key]:
                    return cv_results[electrode_key][filename].get('peak_separation')
            return None

        # --- Build horizontal layout with three sections side by side ---

        # Section titles
        csv_lines.append(f"## Forward Scan,,,,## Reverse Scan,,,,## Peak Separation")
        csv_lines.append('')

        # Build combined header for Peak Potential
        csv_lines.append("### Peak Potential")
        header = ['File Number']

        # Forward scan peak potential columns
        header.extend([f'Fwd_PeakV_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Fwd_PeakV_Avg', 'Fwd_PeakV_Std'])
        header.extend(['', '', ''])  # Separator

        # Reverse scan peak potential columns
        header.extend([f'Rev_PeakV_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Rev_PeakV_Avg', 'Rev_PeakV_Std'])
        header.extend(['', '', ''])  # Separator

        # Peak separation columns
        header.extend([f'PeakSep_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['PeakSep_Avg', 'PeakSep_Std'])

        csv_lines.append(','.join(header))

        # Build data rows for Peak Potential and Peak Separation
        for file_num in file_numbers:
            filename = file_data[file_num]
            row = [str(file_num)]

            # --- Forward Peak Potential ---
            fwd_peak_v_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'forward', 'peak_potential')
                fwd_peak_v_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(fwd_peak_v_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # --- Reverse Peak Potential ---
            rev_peak_v_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'reverse', 'peak_potential')
                rev_peak_v_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(rev_peak_v_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # --- Peak Separation ---
            peak_sep_values = []
            for idx in individual_electrodes:
                value = get_peak_separation(idx, filename)
                peak_sep_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(peak_sep_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')

            csv_lines.append(','.join(row))

        csv_lines.append('')
        csv_lines.append('')

        # --- Peak Current Section ---
        csv_lines.append("### Peak Current")
        header = ['File Number']

        # Forward scan peak current columns
        header.extend([f'Fwd_PeakI_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Fwd_PeakI_Avg', 'Fwd_PeakI_Std'])
        header.extend(['', '', ''])

        # Reverse scan peak current columns
        header.extend([f'Rev_PeakI_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Rev_PeakI_Avg', 'Rev_PeakI_Std'])
        header.extend(['', '', ''])

        # Placeholder for consistency
        header.extend([''] * (len(individual_electrodes) + 2))

        csv_lines.append(','.join(header))

        # Build data rows for Peak Current
        for file_num in file_numbers:
            filename = file_data[file_num]
            row = [str(file_num)]

            # --- Forward Peak Current ---
            fwd_peak_i_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'forward', 'peak_current')
                fwd_peak_i_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(fwd_peak_i_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # --- Reverse Peak Current ---
            rev_peak_i_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'reverse', 'peak_current')
                rev_peak_i_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(rev_peak_i_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # Placeholder columns
            row.extend([''] * (len(individual_electrodes) + 2))

            csv_lines.append(','.join(row))

        csv_lines.append('')
        csv_lines.append('')

        # --- Charge Section ---
        csv_lines.append("### Charge")
        header = ['File Number']

        # Forward scan charge columns
        header.extend([f'Fwd_Charge_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Fwd_Charge_Avg', 'Fwd_Charge_Std'])
        header.extend(['', '', ''])

        # Reverse scan charge columns
        header.extend([f'Rev_Charge_E{idx + 1}' for idx in individual_electrodes])
        header.extend(['Rev_Charge_Avg', 'Rev_Charge_Std'])
        header.extend(['', '', ''])

        # Placeholder for consistency
        header.extend([''] * (len(individual_electrodes) + 2))

        csv_lines.append(','.join(header))

        # Build data rows for Charge
        for file_num in file_numbers:
            filename = file_data[file_num]
            row = [str(file_num)]

            # --- Forward Charge ---
            fwd_charge_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'forward', 'charge')
                fwd_charge_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(fwd_charge_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # --- Reverse Charge ---
            rev_charge_values = []
            for idx in individual_electrodes:
                value = get_cv_metric(idx, filename, 'reverse', 'charge')
                rev_charge_values.append(value)
                if value is not None:
                    row.append(f'{value:.6e}')
                else:
                    row.append('N/A')

            mean, std = calculate_stats(rev_charge_values)
            row.append(f'{mean:.6e}' if mean is not None else 'N/A')
            row.append(f'{std:.6e}' if std is not None else 'N/A')
            row.extend(['', '', ''])

            # Placeholder columns
            row.extend([''] * (len(individual_electrodes) + 2))

            csv_lines.append(','.join(row))

        csv_data = '\n'.join(csv_lines)
        workbook_bytes = _build_xlsx_bytes(_sheet_defs_from_sectioned_csv(csv_data))

        emit('export_cv_data_response', {
            'status': 'success',
            'filename': f"CV_AllElectrodes_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            'content_b64': base64.b64encode(workbook_bytes).decode('ascii')
        })

        logger.info("CV data exported successfully in horizontal format")

    except Exception as e:
        logger.error(f"Error exporting CV data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('export_cv_data_response', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('request_export_frequency_map_data')
def handle_frequency_map_export_request(data):
    """Export frequency map data to CSV in Hold Mode format"""
    logger.info("="*60)
    logger.info("FREQUENCY MAP EXPORT REQUEST RECEIVED")
    logger.info("="*60)

    try:
        import numpy as np
        from datetime import datetime

        freq_map_data = memory_store.get_frequency_map_results()

        logger.info(f"Retrieved freq_map_data, type: {type(freq_map_data)}, keys: {list(freq_map_data.keys()) if freq_map_data else 'None'}")

        if not freq_map_data:
            emit('export_frequency_map_data_response', {
                'status': 'error',
                'message': 'No frequency map data available'
            })
            return

        csv_lines = []

        # Metadata
        csv_lines.append(f"# SACMES Frequency Map Data")
        csv_lines.append(f"# Export Date: {datetime.now().isoformat()}")
        csv_lines.append('')

        # Get individual electrode indices and check for averaged mode
        individual_electrodes = []
        has_averaged_only = False

        for key in freq_map_data.keys():
            # Check if we have averaged data
            if key == 'electrode_averaged':
                has_averaged_only = True
                continue
            # Extract numeric electrode indices
            if key.startswith('electrode_'):
                try:
                    idx = int(key.split('_')[1])
                    individual_electrodes.append(idx)
                    has_averaged_only = False  # We have individual electrodes
                except (ValueError, IndexError):
                    pass
        individual_electrodes.sort()

        logger.info(f"[EXPORT] Found electrodes: {individual_electrodes}, has_averaged_only: {has_averaged_only}")
        logger.info(f"[EXPORT] All keys in freq_map_data: {list(freq_map_data.keys())}")

        # Get all frequencies across all electrodes (keep as strings to match storage keys)
        all_freqs_set = set()
        for electrode_key, electrode_data in freq_map_data.items():
            logger.info(f"[EXPORT] Processing electrode key: {electrode_key}, frequencies: {list(electrode_data.keys())}")
            for freq_str in electrode_data.keys():
                all_freqs_set.add(freq_str)

        # Sort frequencies numerically
        frequencies = sorted(all_freqs_set, key=lambda x: float(x))

        logger.info(f"[EXPORT] All frequencies found: {frequencies}")

        if not frequencies:
            emit('export_frequency_map_data_response', {
                'status': 'error',
                'message': 'No frequency data available'
            })
            return

        # Helper function to calculate stats
        def calculate_stats(values):
            valid_values = [v for v in values if v is not None and not np.isnan(v)]
            if not valid_values:
                return None, None
            mean = np.mean(valid_values)
            std = np.std(valid_values, ddof=1) if len(valid_values) > 1 else 0.0
            return mean, std

        # --- Charge Section ---
        csv_lines.append("## Charge (C)")
        csv_lines.append('')

        # Build header - handle averaged-only mode
        if has_averaged_only and not individual_electrodes:
            # Only averaged data available
            charge_header = ['Frequency (Hz)', 'Averaged', 'Std']
            logger.info("[EXPORT] Using averaged-only mode for export")
        else:
            # Individual electrodes available
            charge_header = ['Frequency (Hz)', 'Averaged']
            charge_header.extend([f'Electrode {idx + 1}' for idx in individual_electrodes])
            charge_header.append('Std')
        csv_lines.append(','.join(charge_header))

        # Build charge rows
        for freq_idx, freq_str in enumerate(frequencies):
            row = [freq_str]

            if has_averaged_only and not individual_electrodes:
                # Only averaged data - get from electrode_averaged
                electrode_key = 'electrode_averaged'
                freq_data = freq_map_data.get(electrode_key, {}).get(freq_str)
                if freq_data:
                    charge = freq_data.get('charge')
                    if freq_idx == 0:
                        logger.info(f"[EXPORT] First freq {freq_str}: {electrode_key}, charge={charge}, peak={freq_data.get('peak_value')}")
                    row.append(f'{charge:.6e}' if charge is not None else 'N/A')
                else:
                    row.append('N/A')
                row.append('N/A')  # No std for single value
            else:
                # Collect charge values from individual electrodes
                charge_values = []
                for idx in individual_electrodes:
                    electrode_key = f'electrode_{idx}'
                    if electrode_key in freq_map_data:
                        freq_data = freq_map_data[electrode_key].get(freq_str)
                        if freq_data:
                            charge = freq_data.get('charge')
                            # Log first frequency for debugging
                            if freq_idx == 0:
                                logger.info(f"[EXPORT] First freq {freq_str}: {electrode_key}, charge={charge}, peak={freq_data.get('peak_value')}")
                            charge_values.append(charge)
                        else:
                            charge_values.append(None)
                    else:
                        charge_values.append(None)

                # Calculate averaged and std
                charge_mean, charge_std = calculate_stats(charge_values)

                # Add averaged
                if charge_mean is not None:
                    row.append(f'{charge_mean:.6e}')
                else:
                    row.append('N/A')

                # Add individual electrode values
                for val in charge_values:
                    if val is not None:
                        row.append(f'{val:.6e}')
                    else:
                        row.append('N/A')

                # Add std
                if charge_std is not None:
                    row.append(f'{charge_std:.6e}')
                else:
                    row.append('N/A')

            csv_lines.append(','.join(row))

        csv_lines.append('')

        # --- Peak Current Section ---
        csv_lines.append("## Peak Current (A)")
        csv_lines.append('')

        # Build header (same structure as charge section)
        if has_averaged_only and not individual_electrodes:
            # Only averaged data available
            peak_header = ['Frequency (Hz)', 'Averaged', 'Std']
        else:
            # Individual electrodes available
            peak_header = ['Frequency (Hz)', 'Averaged']
            peak_header.extend([f'Electrode {idx + 1}' for idx in individual_electrodes])
            peak_header.append('Std')
        csv_lines.append(','.join(peak_header))

        # Build peak current rows
        for freq_str in frequencies:
            row = [freq_str]

            if has_averaged_only and not individual_electrodes:
                # Only averaged data - get from electrode_averaged
                electrode_key = 'electrode_averaged'
                freq_data = freq_map_data.get(electrode_key, {}).get(freq_str)
                if freq_data:
                    peak = freq_data.get('peak_value')
                    row.append(f'{peak:.6e}' if peak is not None else 'N/A')
                else:
                    row.append('N/A')
                row.append('N/A')  # No std for single value
            else:
                # Collect peak values from individual electrodes
                peak_values = []
                for idx in individual_electrodes:
                    electrode_key = f'electrode_{idx}'
                    if electrode_key in freq_map_data:
                        freq_data = freq_map_data[electrode_key].get(freq_str)
                        if freq_data and 'peak_value' in freq_data:
                            peak_values.append(freq_data['peak_value'])
                        else:
                            peak_values.append(None)
                    else:
                        peak_values.append(None)

                # Calculate averaged and std
                peak_mean, peak_std = calculate_stats(peak_values)

                # Add averaged
                if peak_mean is not None:
                    row.append(f'{peak_mean:.6e}')
                else:
                    row.append('N/A')

                # Add individual electrode values
                for val in peak_values:
                    if val is not None:
                        row.append(f'{val:.6e}')
                    else:
                        row.append('N/A')

                # Add std
                if peak_std is not None:
                    row.append(f'{peak_std:.6e}')
                else:
                    row.append('N/A')

            csv_lines.append(','.join(row))

        csv_data = '\n'.join(csv_lines)
        workbook_bytes = _build_xlsx_bytes(_sheet_defs_from_sectioned_csv(csv_data))

        emit('export_frequency_map_data_response', {
            'status': 'success',
            'filename': f"SACMES_FrequencyMap_AllElectrodes_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            'content_b64': base64.b64encode(workbook_bytes).decode('ascii')
        })

        logger.info("Frequency map data exported successfully")

    except Exception as e:
        logger.error(f"Error exporting frequency map data: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

        # Process based on type (local mode - call handlers directly)
        if analysis_type == 'swv':
            logger.info(f"Processing SWV file: {filename}")
            handle_instrument_data({
                'filename': filename,
                'content': content,
                'analysisParams': stored_params.get('analysisParams', {})
            })
        elif analysis_type == 'cv':
            logger.info(f"Processing CV file: {filename}")
            handle_cv_data({
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
                sock.bind(('127.0.0.1', port))  # Explicit IPv4 -- avoids macOS localhost->IPv6 issue
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
    logger.info(f"  URL: http://127.0.0.1:{port}")
    logger.info("=" * 80)

    # Write port file so START.sh / SACMES.command can open the browser
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.sacmes_port')
    try:
        with open(port_file, 'w') as pf:
            pf.write(str(port))
    except Exception:
        pass  # Non-fatal -- browser open will just not work automatically

    # Note: Browser auto-open is handled by start.bat / START.sh
    # No need to open browser here to avoid double windows

    # Run SocketIO server
    try:
        socketio.run(app, host='127.0.0.1', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        if file_observer:
            file_observer.stop()
            file_observer.join()
        logger.info("Application stopped")
