# app.py (Final Corrected Version)

import eventlet

eventlet.monkey_patch()

import os
import re
import logging
import sys
from flask import Flask, send_from_directory, request
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

    logger.info("Successfully imported swv_analyzer.")
except ImportError as e:
    logger.critical(f"FATAL: Failed to import swv_analyzer: {e}")
    analyze_swv_data = None

# --- App Setup (Unchanged) ---
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
AGENT_AUTH_TOKEN = os.environ.get('AGENT_AUTH_TOKEN', "your_super_secret_token_here")
agent_sid, web_viewer_sids, live_analysis_params, live_trend_data = None, set(), {}, {}


# --- Helper function calculate_trends (Unchanged) ---
def calculate_trends(raw_peaks, params):
    num_files = params.get('num_files', 1)
    frequencies = params.get('frequencies', [])
    normalization_point = params.get('normalizationPoint', 1)
    if not frequencies: return {}
    frequencies.sort()
    low_freq_str, high_freq_str = str(frequencies[0]), str(frequencies[-1])
    x_axis_values = list(range(1, num_files + 1))
    peak_current_trends = {str(f): [None] * num_files for f in frequencies}
    normalized_peak_trends = {str(f): [None] * num_files for f in frequencies}
    kdm_trend = [None] * num_files
    for i, file_num in enumerate(x_axis_values):
        for freq_str in peak_current_trends:
            peak = raw_peaks.get(freq_str, {}).get(str(file_num))
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


# --- Background Task (Unchanged) ---
def process_file_in_background(original_filename, content, params_for_this_file):
    logger.info(f"BACKGROUND_TASK: Started processing for '{original_filename}'.")
    filename = secure_filename(original_filename)
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"BACKGROUND_TASK: Wrote temp file to '{temp_filepath}'.")
        if not analyze_swv_data:
            logger.error("BACKGROUND_TASK: swv_analyzer is not available. Aborting analysis.")
            return
        analysis_result = analyze_swv_data(temp_filepath, params_for_this_file)
        logger.info(
            f"BACKGROUND_TASK: Analysis for '{original_filename}' completed with status: {analysis_result.get('status')}.")
        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            match = re.search(r'_(\d+)Hz_?_?(\d+)\.', original_filename, re.IGNORECASE)
            if match:
                parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                peak = analysis_result.get('peak_value')
                live_trend_data['raw_peaks'][str(parsed_frequency)][str(parsed_filenum)] = peak
        full_trends = calculate_trends(live_trend_data['raw_peaks'], live_analysis_params)
        logger.info(f"BACKGROUND_TASK: Trend calculation complete. Emitting update.")
        if web_viewer_sids:
            socketio.emit('live_analysis_update',
                          {"filename": original_filename, "individual_analysis": analysis_result,
                           "trend_data": full_trends}, to=list(web_viewer_sids), broadcast=True)
    except Exception as e:
        logger.error(f"BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"BACKGROUND_TASK: Finished job for '{original_filename}'.")


# --- Socket.IO Event Handlers (Connect, Disconnect, Start Session are Unchanged) ---
@socketio.on('connect')
def handle_connect():
    global agent_sid
    logger.info(f"Client connected with SID: {request.sid}")
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None
    if token and token == AGENT_AUTH_TOKEN:
        agent_sid = request.sid
        logger.info(f"Authenticated client is an AGENT. SID: {agent_sid}")
        emit('agent_status', {'status': 'connected'}, to=list(web_viewer_sids), broadcast=True)
    else:
        web_viewer_sids.add(request.sid)
        logger.info(f"Client is a WEB VIEWER. Total viewers: {len(web_viewer_sids)}")


@socketio.on('disconnect')
def handle_disconnect():
    global agent_sid
    logger.info(f"Client disconnected: {request.sid}. Reason: {request.args.get('reason', 'N/A')}")
    if request.sid == agent_sid:
        agent_sid = None
        logger.warning("Agent has disconnected.")
        emit('agent_status', {'status': 'disconnected'}, to=list(web_viewer_sids), broadcast=True)
    elif request.sid in web_viewer_sids:
        web_viewer_sids.remove(request.sid)
        logger.info(f"Web viewer disconnected. Total viewers: {len(web_viewer_sids)}")


@socketio.on('start_analysis_session')
def handle_start_analysis_session(data):
    global live_analysis_params, live_trend_data
    logger.info(f"Received 'start_analysis_session' from {request.sid}")
    if 'analysisParams' in data:
        live_analysis_params = data['analysisParams']
        live_trend_data = {"raw_peaks": {str(f): {} for f in live_analysis_params.get('frequencies', [])}}
        logger.info("Analysis session started. Params set and trend data reset.")
    if 'filters' in data and agent_sid:
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')
        emit('set_filters', filters, to=agent_sid)
        logger.info(f"Sent 'set_filters' instruction to agent {agent_sid}.")
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent.'})
    elif not agent_sid:
        logger.warning("'start_analysis_session' received, but no agent is connected.")
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    """
    Receives file data and starts a background task.
    *** THIS IS THE ONLY FUNCTION THAT HAS BEEN MODIFIED ***
    """
    if request.sid != agent_sid: return
    original_filename = data.get('filename', 'unknown_file.txt')
    logger.info(f"Received 'stream_instrument_data' for file '{original_filename}' from agent.")
    if not live_analysis_params:
        logger.warning("Received instrument data, but analysis params are not set. Ignoring.")
        return

    params_for_this_file = live_analysis_params.copy()
    match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
    if match:
        params_for_this_file['frequency'] = int(match.group(1))
    else:
        logger.warning(f"Could not parse frequency from filename: '{original_filename}'.")
        return

    # --- KEY FIX IS HERE ---
    # We ensure the optional keys exist before passing them to the analyzer.
    # The .setdefault(key, None) command adds the key with a value of None ONLY if it's not already present.
    params_for_this_file.setdefault('low_xstart', None)
    params_for_this_file.setdefault('low_xend', None)
    params_for_this_file.setdefault('high_xstart', None)
    params_for_this_file.setdefault('high_xend', None)

    socketio.start_background_task(
        target=process_file_in_background,
        original_filename=original_filename,
        content=data.get('content', ''),
        params_for_this_file=params_for_this_file
    )
    logger.info(f"Queued background processing for '{original_filename}'. Handler is now free.")


# --- HTTP Routes (Unchanged) ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    logger.info("Starting SACMES server in development mode...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)