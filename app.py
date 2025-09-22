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
    from data_processing.cv_analyzer import analyze_cv_data, get_cv_segments

    logger.info("Successfully imported swv_analyzer and cv_analyzer.")
except ImportError as e:
    logger.critical(f"FATAL: Failed to import analyzers: {e}")
    analyze_swv_data = None
    analyze_cv_data = None
    get_cv_segments = None

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
        # Convert file numbers to hours: (file_number - 1) * sample_rate / 3600
        x_axis_values = [(i * sample_rate) / 3600 for i in range(num_files)]
    else:
        # Default file number mode
        x_axis_values = list(range(1, num_files + 1))
    peak_current_trends = {str(f): [None] * num_files for f in frequencies}
    normalized_peak_trends = {str(f): [None] * num_files for f in frequencies}
    kdm_trend = [None] * num_files

    # Get electrode-specific data
    electrode_data = raw_peaks.get(selected_electrode_key, {})

    for i, file_num in enumerate(x_axis_values):
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


# --- Background Task ---
def process_cv_file_in_background(original_filename, content, params_for_this_file):
    logger.info(f"CV_BACKGROUND_TASK: Started processing for '{original_filename}'.")
    filename = secure_filename(original_filename)
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        if not analyze_cv_data: return

        # Get selected electrode from params (if any)
        selected_electrode = params_for_this_file.get('selected_electrode')
        analysis_result = analyze_cv_data(temp_filepath, params_for_this_file, selected_electrode)

        if analysis_result and analysis_result.get('status') == 'success':
            # Store CV results differently - not in trend data but as individual results
            match = re.search(r'_(\d+)Hz_?_?(\d+)\.', original_filename, re.IGNORECASE) or re.search(r'_(\d+)\.', original_filename, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                else:
                    parsed_frequency, parsed_filenum = 0, int(match.group(1))  # No frequency in filename

                electrode_key = str(selected_electrode) if selected_electrode is not None else 'averaged'

                # Initialize CV results structure if needed
                if 'cv_results' not in live_trend_data:
                    live_trend_data['cv_results'] = {}
                if electrode_key not in live_trend_data['cv_results']:
                    live_trend_data['cv_results'][electrode_key] = {}

                live_trend_data['cv_results'][electrode_key][str(parsed_filenum)] = analysis_result

        if web_viewer_sids:
            # Send CV update
            response_data = {
                "filename": original_filename,
                "cv_analysis": analysis_result,
                "electrode_index": selected_electrode
            }
            socketio.emit('live_cv_update', response_data, to=list(web_viewer_sids))

    except Exception as e:
        logger.error(f"CV_BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"CV_BACKGROUND_TASK: Finished job for '{original_filename}'.")


def process_file_in_background(original_filename, content, params_for_this_file):
    logger.info(f"BACKGROUND_TASK: Started processing for '{original_filename}'.")
    filename = secure_filename(original_filename)
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
            logger.error(f"Electrode validation error: {analysis_result.get('message')}")
            socketio.emit('electrode_validation_error', {
                'message': analysis_result.get('message'),
                'detected_electrodes': analysis_result.get('detected_electrodes'),
                'requested_electrode': analysis_result.get('requested_electrode')
            }, room=list(web_viewer_sids))
            return

        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            # Extract from original filename (without electrode suffix)
            base_filename = original_filename.replace(f'_electrode_{selected_electrode}', '') if selected_electrode is not None else original_filename
            match = re.search(r'_(\d+)Hz_?_?(\d+)\.', base_filename, re.IGNORECASE)
            if match:
                parsed_frequency, parsed_filenum = int(match.group(1)), int(match.group(2))
                peak = analysis_result.get('peak_value')
                # Store data per electrode
                electrode_key = str(selected_electrode) if selected_electrode is not None else 'averaged'
                freq_key = str(parsed_frequency)
                file_key = str(parsed_filenum)

                # Initialize nested structure if needed
                if 'raw_peaks' not in live_trend_data:
                    live_trend_data['raw_peaks'] = {}
                if electrode_key not in live_trend_data['raw_peaks']:
                    live_trend_data['raw_peaks'][electrode_key] = {}
                if freq_key not in live_trend_data['raw_peaks'][electrode_key]:
                    live_trend_data['raw_peaks'][electrode_key][freq_key] = {}

                live_trend_data['raw_peaks'][electrode_key][freq_key][file_key] = peak
        # Get current electrode selection from params
        current_electrode = live_analysis_params.get('selected_electrode')
        electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'
        full_trends = calculate_trends(live_trend_data.get('raw_peaks', {}), live_analysis_params, electrode_key)
        if web_viewer_sids:
            # Send update with electrode-specific information
            response_data = {
                "filename": base_filename,  # Use base filename for frontend processing
                "individual_analysis": analysis_result,
                "trend_data": full_trends,
                "electrode_index": selected_electrode
            }
            socketio.emit('live_analysis_update', response_data, to=list(web_viewer_sids))
    except Exception as e:
        logger.error(f"BACKGROUND_TASK: CRITICAL ERROR while processing '{original_filename}': {e}", exc_info=True)
    finally:
        if os.path.exists(temp_filepath): os.remove(temp_filepath)
        logger.info(f"BACKGROUND_TASK: Finished job for '{original_filename}'.")


# --- *** NEW *** HELPER FUNCTION TO GENERATE CSV DATA ---
def generate_csv_data(current_electrode=None):
    """
    Generates a CSV formatted string from the current trend data.

    Args:
        current_electrode: The electrode index to export data for (None for averaged data).
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
    # Use the electrode specified in the export request
    electrode_key = str(current_electrode) if current_electrode is not None else 'averaged'
    full_trends = calculate_trends(live_trend_data.get('raw_peaks', {}), live_analysis_params, electrode_key)

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
        live_trend_data = {"raw_peaks": {}}
        logger.info("Analysis session started. Params set and trend data reset.")
    if 'filters' in data and agent_sid:
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_session', {'status': 'success', 'message': 'Instructions sent.'})
    elif not agent_sid:
        emit('ack_start_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('start_cv_analysis_session')
def handle_start_cv_analysis_session(data):
    global live_analysis_params, live_trend_data
    logger.info(f"Received 'start_cv_analysis_session' from {request.sid}")
    if 'analysisParams' in data:
        live_analysis_params = data['analysisParams']
        live_trend_data = {"cv_results": {}}
        logger.info("CV Analysis session started. Params set and CV data reset.")
    if 'filters' in data and agent_sid:
        filters = data['filters']
        filters['file_extension'] = live_analysis_params.get('file_extension', '.txt')
        emit('set_filters', filters, to=agent_sid)
        emit('ack_start_cv_session', {'status': 'success', 'message': 'CV Instructions sent.'})
    elif not agent_sid:
        emit('ack_start_cv_session', {'status': 'error', 'message': 'Error: Local agent not detected.'})


@socketio.on('stream_instrument_data')
def handle_instrument_data(data):
    if request.sid != agent_sid: return
    original_filename = data.get('filename', 'unknown_file.txt')
    if not live_analysis_params: return

    match = re.search(r'_(\d+)Hz', original_filename, re.IGNORECASE)
    if not match: return

    # Get selected electrodes from analysis params
    selected_electrodes = live_analysis_params.get('selected_electrodes', [])

    if selected_electrodes:
        # Process each selected electrode
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
                                         content=data.get('content', ''),
                                         params_for_this_file=params_for_this_file)
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
                                     content=data.get('content', ''),
                                     params_for_this_file=params_for_this_file)


@socketio.on('stream_cv_data')
def handle_cv_instrument_data(data):
    if request.sid != agent_sid: return
    original_filename = data.get('filename', 'unknown_file.txt')
    if not live_analysis_params: return

    # Get selected electrodes from analysis params
    selected_electrodes = live_analysis_params.get('selected_electrodes', [])

    if selected_electrodes:
        # Process each selected electrode for CV
        for electrode_idx in selected_electrodes:
            params_for_this_file = live_analysis_params.copy()
            params_for_this_file['selected_electrode'] = electrode_idx

            socketio.start_background_task(target=process_cv_file_in_background,
                                         original_filename=f"{original_filename}_electrode_{electrode_idx}",
                                         content=data.get('content', ''),
                                         params_for_this_file=params_for_this_file)
    else:
        # Original averaging behavior for CV
        params_for_this_file = live_analysis_params.copy()
        socketio.start_background_task(target=process_cv_file_in_background,
                                     original_filename=original_filename,
                                     content=data.get('content', ''),
                                     params_for_this_file=params_for_this_file)


@socketio.on('get_cv_preview')
def handle_get_cv_preview(data):
    """Get CV preview file from agent for segment selection"""
    try:
        if not agent_sid:
            emit('cv_preview_response', {'status': 'error', 'message': 'Agent not connected'})
            return

        filters = data.get('filters', {})
        analysis_params = data.get('analysisParams', {})

        # Request first file from agent for preview
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
    """Get available CV segments from uploaded file"""
    try:
        if not get_cv_segments:
            emit('cv_segments_response', {'status': 'error', 'message': 'CV analyzer not available'})
            return

        file_content = data.get('content', '')
        analysis_params = data.get('params', {})
        selected_electrode = analysis_params.get('selected_electrode')

        # Create temporary file
        filename = secure_filename(data.get('filename', 'temp_cv.txt'))
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(file_content)

        # Get segments
        segments_result = get_cv_segments(temp_filepath, analysis_params, selected_electrode)

        # Clean up
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        emit('cv_segments_response', segments_result)

    except Exception as e:
        logger.error(f"Error getting CV segments: {e}", exc_info=True)
        emit('cv_segments_response', {'status': 'error', 'message': str(e)})


@socketio.on('cv_data_from_agent')
def handle_cv_data_from_agent(data):
    """Handle CV data from agent - both preview and analysis modes"""
    if request.sid != agent_sid:
        return

    try:
        preview_mode = data.get('preview_mode', False)
        file_content = data.get('content', '')
        analysis_params = data.get('analysisParams', {})

        if preview_mode:
            # This is for segment selection preview
            if file_content:
                # Parse the CV data for preview visualization
                import tempfile
                from data_processing.data_reader import ReadData

                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name

                try:
                    # Read the data for preview
                    voltage_column = analysis_params.get('voltage_column', 1) - 1
                    current_column = analysis_params.get('current_column', 2) - 1
                    spacing_index = analysis_params.get('spacing_index', 1)
                    delimiter = analysis_params.get('delimiter', 1)
                    file_extension = analysis_params.get('file_extension', '.txt')

                    # Read data for first electrode or averaged
                    data_result = ReadData(
                        temp_path,
                        voltage_column_index=voltage_column,
                        current_column_start_index=current_column,
                        spacing_index=spacing_index,
                        num_electrodes=1,
                        delimiter_char=delimiter,
                        file_extension=file_extension,
                        selected_electrodes=None  # Use averaging for preview
                    )

                    if data_result and 'voltage' in data_result and 'current' in data_result:
                        # Send the CV data for preview visualization
                        emit('cv_preview_response', {
                            'status': 'success',
                            'content': file_content,
                            'cv_data': {
                                'voltage': data_result['voltage'],
                                'current': data_result['current']
                            }
                        })
                    else:
                        emit('cv_preview_response', {
                            'status': 'error',
                            'message': 'Could not parse CV data for preview'
                        })

                finally:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                emit('cv_preview_response', {
                    'status': 'error',
                    'message': 'No file content received'
                })
        else:
            # Regular analysis mode - use existing logic
            original_filename = data.get('filename', 'unknown_file.txt')
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
                                                 params_for_this_file=params_for_this_file)
            else:
                # Original averaging behavior for CV
                params_for_this_file = live_analysis_params.copy()
                socketio.start_background_task(target=process_cv_file_in_background,
                                             original_filename=original_filename,
                                             content=file_content,
                                             params_for_this_file=params_for_this_file)

    except Exception as e:
        logger.error(f"Error handling CV data from agent: {e}", exc_info=True)
        if data.get('preview_mode', False):
            emit('cv_preview_response', {'status': 'error', 'message': str(e)})


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



# --- HTTP Routes (Unchanged) ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    logger.info("Starting SACMES server in development mode...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)