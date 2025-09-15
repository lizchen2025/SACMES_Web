# app.py (Version with CSV Export Functionality)

import eventlet

eventlet.monkey_patch()

import os
import re
import logging
import sys
import io
import csv
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
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
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
        if not analyze_swv_data: return
        analysis_result = analyze_swv_data(temp_filepath, params_for_this_file)
        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            match = re.search(r'_(\d+)Hz_?_?(\d+)\.', original_filename, re.IGNORECASE)
            if match:
                parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                peak = analysis_result.get('peak_value')
                live_trend_data['raw_peaks'][str(parsed_frequency)][str(parsed_filenum)] = peak
        full_trends = calculate_trends(live_trend_data['raw_peaks'], live_analysis_params)
        if web_viewer_sids:
            socketio.emit('live_analysis_update',
                          {"filename": original_filename, "individual_analysis": analysis_result,
                           "trend_data": full_trends}, to=list(web_viewer_sids))
    except Exception as e:
        logger.error(f"BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"BACKGROUND_TASK: Finished job for '{original_filename}'.")


# --- *** NEW *** HELPER FUNCTION TO GENERATE CSV DATA ---
def generate_csv_data():
    """
    Generates a CSV formatted string from the current trend data.
    """
    if not live_trend_data or not live_analysis_params:
        return ""

    string_io = io.StringIO()
    writer = csv.writer(string_io)

    frequencies = [str(f) for f in live_analysis_params.get('frequencies', [])]
    num_files = live_analysis_params.get('num_files', 0)

    # Write header
    header = ['File_Number']
    for freq in frequencies:
        header.append(f'Peak_Current_{freq}Hz')
    for freq in frequencies:
        header.append(f'Normalized_Peak_{freq}Hz')
    header.append('KDM')
    writer.writerow(header)

    # Recalculate full trends to ensure data is consistent
    full_trends = calculate_trends(live_trend_data.get('raw_peaks', {}), live_analysis_params)

    # Write data rows
    for i in range(num_files):
        file_num = i + 1
        row = [file_num]
        for freq in frequencies:
            row.append(full_trends.get('peak_current_trends', {}).get(freq, [None] * num_files)[i])
        for freq in frequencies:
            row.append(full_trends.get('normalized_peak_trends', {}).get(freq, [None] * num_files)[i])
        row.append(full_trends.get('kdm_trend', [None] * num_files)[i])
        writer.writerow(row)

    return string_io.getvalue()


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
        emit('agent_status', {'status': 'connected'}, to=list(web_viewer_sids))
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
        emit('agent_status', {'status': 'disconnected'}, to=list(web_viewer_sids))
    elif request.sid in web_viewer_sids:
        web_viewer_sids.remove(request.sid)


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
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent.'})
    elif not agent_sid:
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    if request.sid != agent_sid: return
    original_filename = data.get('filename', 'unknown_file.txt')
    if not live_analysis_params: return
    params_for_this_file = live_analysis_params.copy()
    match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
    if match:
        params_for_this_file['frequency'] = int(match.group(1))
    else:
        return
    params_for_this_file.setdefault('low_xstart', None)
    params_for_this_file.setdefault('low_xend', None)
    params_for_this_file.setdefault('high_xstart', None)
    params_for_this_file.setdefault('high_xend', None)
    socketio.start_background_task(target=process_file_in_background, original_filename=original_filename,
                                   content=data.get('content', ''), params_for_this_file=params_for_this_file)


# --- *** NEW *** SOCKET.IO EVENT HANDLER FOR EXPORTING DATA ---
@socketio.on('request_export_data')
def handle_export_request():
    """
    Handles a request from the client to export data to CSV.
    """
    logger.info(f"Received 'request_export_data' from {request.sid}")
    try:
        csv_data = generate_csv_data()
        if csv_data:
            emit('export_data_response', {'status': 'success', 'data': csv_data})
            logger.info(f"Sent CSV data back to client {request.sid}")
        else:
            emit('export_data_response', {'status': 'error', 'message': 'No data available to export.'})
            logger.warning("Export requested, but no data was available.")
    except Exception as e:
        logger.error(f"Failed to generate CSV for export: {e}", exc_info=True)
        emit('export_data_response', {'status': 'error', 'message': f'Server error during CSV generation: {e}'})


# --- HTTP Routes (Unchanged) ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    logger.info("Starting SACMES server in development mode...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)