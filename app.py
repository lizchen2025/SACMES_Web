# app.py (Final Version with Full Trend Calculation)

import eventlet

eventlet.monkey_patch()

import os
import re
import logging
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from data_processing.swv_analyzer import analyze_swv_data

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- Configuration & State Management ---
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

AGENT_AUTH_TOKEN = os.environ.get('AGENT_AUTH_TOKEN', "your_super_secret_token_here")

agent_sid = None
web_viewer_sids = set()
live_analysis_params = {}
live_trend_data = {}


# --- Helper Functions ---
def calculate_trends(raw_peaks, params):
    """
    [FIXED] Re-implements the full trend calculation logic for normalization and KDM.
    """
    num_files = params.get('num_files', 1)
    frequencies = params.get('frequencies', [])
    normalization_point = params.get('normalizationPoint', 1)

    # Ensure frequencies are sorted to identify low and high for KDM
    if not frequencies:
        return {}
    frequencies.sort()
    low_freq_str = str(frequencies[0])
    high_freq_str = str(frequencies[-1])

    x_axis_values = list(range(1, num_files + 1))

    peak_current_trends = {str(f): [None] * num_files for f in frequencies}
    normalized_peak_trends = {str(f): [None] * num_files for f in frequencies}
    kdm_trend = [None] * num_files

    # Populate raw peaks
    for i, file_num in enumerate(x_axis_values):
        for freq_str in peak_current_trends:
            peak = raw_peaks.get(freq_str, {}).get(str(file_num))
            if peak is not None:
                peak_current_trends[freq_str][i] = peak

    # Calculate normalization factors
    norm_factors = {}
    for freq_str in peak_current_trends:
        # Get the peak at the normalization point (index is point-1)
        norm_idx = normalization_point - 1
        if 0 <= norm_idx < len(peak_current_trends[freq_str]):
            norm_value = peak_current_trends[freq_str][norm_idx]
            norm_factors[freq_str] = norm_value if norm_value and norm_value != 0 else 1.0
        else:
            norm_factors[freq_str] = 1.0

    # Calculate normalized trends and KDM
    for i in range(num_files):
        # Normalization
        for freq_str in peak_current_trends:
            peak = peak_current_trends[freq_str][i]
            if peak is not None and norm_factors.get(freq_str):
                normalized_peak_trends[freq_str][i] = peak / norm_factors[freq_str]

        # KDM Calculation
        low_freq_peak = peak_current_trends.get(low_freq_str, [])[i]
        high_freq_peak = peak_current_trends.get(high_freq_str, [])[i]

        if low_freq_peak is not None and high_freq_peak is not None and high_freq_peak != 0:
            kdm_trend[i] = low_freq_peak / high_freq_peak

    return {
        "x_axis_values": x_axis_values,
        "peak_current_trends": peak_current_trends,
        "normalized_peak_trends": normalized_peak_trends,
        "kdm_trend": kdm_trend
    }


# --- Socket.IO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    global agent_sid
    auth_header = request.headers.get('Authorization')
    token_in_header = None
    if auth_header and auth_header.startswith('Bearer '):
        token_in_header = auth_header.split(' ')[1]

    if token_in_header and token_in_header == AGENT_AUTH_TOKEN:
        agent_sid = request.sid
        logger.info(f"Agent connected with SID: {agent_sid}")
        emit('agent_status', {'status': 'connected'}, to=list(web_viewer_sids), broadcast=True)
    else:
        web_viewer_sids.add(request.sid)
        logger.info(f"Web client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    global agent_sid
    if request.sid == agent_sid:
        agent_sid = None
        logger.warning("Agent has disconnected.")
        emit('agent_status', {'status': 'disconnected'}, to=list(web_viewer_sids), broadcast=True)
    elif request.sid in web_viewer_sids:
        web_viewer_sids.remove(request.sid)
        logger.info(f"Web client disconnected: {request.sid}")


@socketio.on('request_agent_status')
def handle_request_agent_status(data):
    if request.sid in web_viewer_sids:
        current_status = 'connected' if agent_sid else 'disconnected'
        emit('agent_status', {'status': current_status})


@socketio.on('start_analysis_session')
def handle_start_analysis_session(data):
    global live_analysis_params, live_trend_data
    if 'analysisParams' in data:
        live_analysis_params = data['analysisParams']
        live_trend_data = {
            "raw_peaks": {str(f): {} for f in live_analysis_params.get('frequencies', [])}
        }
        logger.info(f"Analysis session started. Params set and trend data reset.")

    if 'filters' in data and agent_sid:
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent to local agent.'})
    elif not agent_sid:
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    if request.sid != agent_sid: return

    # content = data.get('content')
    # original_filename = data.get('filename', 'unknown_file.txt')
    # filename = secure_filename(original_filename)
    #
    # if not content or not live_analysis_params: return
    #
    # params_for_this_file = live_analysis_params.copy()
    #
    # try:
    #     match = re.search(r'_(\d+)Hz_?_?(\d+)\.', original_filename, re.IGNORECASE)
    #     if not match: return
    #
    #     parsed_frequency = int(match.group(1))
    #     parsed_filenum = int(match.group(2))
    #     params_for_this_file['frequency'] = parsed_frequency
    #
    # except Exception as e:
    #     logger.error(f"Error parsing filename '{original_filename}': {e}")
    #     return
    #
    # required_keys = ['low_xstart', 'low_xend', 'high_xstart', 'high_xend']
    # for key in required_keys:
    #     if key not in params_for_this_file:
    #         params_for_this_file[key] = None
    #
    # temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # try:
    #     with open(temp_filepath, 'w', encoding='utf-8') as f:
    #         f.write(content)
    #
    #     analysis_result = analyze_swv_data(temp_filepath, params_for_this_file)
    #
    #     if analysis_result and analysis_result.get('status') in ['success', 'warning']:
    #         peak = analysis_result.get('peak_value')
    #         freq_str = str(parsed_frequency)
    #         filenum_str = str(parsed_filenum)
    #         if freq_str in live_trend_data['raw_peaks']:
    #             live_trend_data['raw_peaks'][freq_str][filenum_str] = peak
    #
    #     full_trends = calculate_trends(live_trend_data['raw_peaks'], live_analysis_params)
    #
    #     if web_viewer_sids:
    #         emit('live_analysis_update', {
    #             "filename": original_filename,
    #             "individual_analysis": analysis_result,
    #             "trend_data": full_trends
    #         }, to=list(web_viewer_sids), broadcast=True)
    #
    # except Exception as e:
    #     logger.error(f"Error processing streamed file {filename}: {e}", exc_info=True)
    # finally:
    #     if os.path.exists(temp_filepath):
    #         os.remove(temp_filepath)


# --- HTTP Routes ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# --- Main Execution ---
if __name__ == '__main__':
    logger.info("Starting SACMES server...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
