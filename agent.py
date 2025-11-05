# agent1.py (Final Version with Configurable Server URL)
# This version allows the user to input the server URL directly in the GUI.

import os
import re
import time
import json
import socketio
import threading
import uuid
from collections import defaultdict
from datetime import datetime

# --- GUI (using Python's built-in library) ---
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# --- Configuration ---
# REMOVED: SERVER_URL is now a GUI variable
AUTH_TOKEN = "your_super_secret_token_here"
POLLING_INTERVAL_SECONDS = 0.5
SEND_DELAY_SECONDS = 0.05

# --- ID Management System ---
class IDManager:
    def __init__(self, config_file='agent.json'):
        self.config_file = config_file
        self.user_id = None
        self.session_id = None
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Load existing config or create new one with persistent user ID"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.user_id = config.get('user_id')
                    if self.user_id:
                        print(f"Loaded existing user ID: {self.user_id}")
                    else:
                        self._generate_new_user_id()
            else:
                self._generate_new_user_id()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}, generating new user ID")
            self._generate_new_user_id()

    def _generate_new_user_id(self):
        """Generate new persistent user ID and save to config"""
        self.user_id = str(uuid.uuid4())
        print(f"Generated new user ID: {self.user_id}")
        self._save_config()

    def _save_config(self):
        """Save current configuration to file"""
        try:
            config = {
                'user_id': self.user_id,
                'created_at': datetime.now().isoformat(),
                'last_session': self.session_id
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

    def get_user_id(self):
        """Get the persistent user ID"""
        return self.user_id

    def start_new_session(self):
        """Generate new session ID and save to config"""
        self.session_id = str(uuid.uuid4())
        print(f"Started new session: {self.session_id}")
        self._save_config()
        return self.session_id

    def get_session_id(self):
        """Get current session ID"""
        return self.session_id

    def get_consent_data(self):
        """Get consent data with user ID and session ID"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'agent_version': '1.0'
        }

# Global ID manager instance
id_manager = IDManager()

# --- Consent Dialog Class ---
class ConsentDialog:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.consent_given = False
        self.consent_text = self.load_consent_text()

    def load_consent_text(self):
        """Return hardcoded consent text"""
        return """SACMES Data Access Consent

By using this SACMES ( Software for the Analysis and Continuous Monitoring of Electrochemical Systems) agent, you acknowledge and agree to the following terms:

DATA ACCESS SCOPE:
• This agent will access ALL files within your selected folder and its subdirectories
• The agent monitors for new files continuously while active
• File contents are read and transmitted to the SACMES web server for analysis

DATA HANDLING:
• Your electrochemical data files are processed by our analysis algorithms
• Data is temporarily stored on our servers during analysis sessions
• We do not permanently retain your raw data files after session completion
• Analysis results and processed data may be temporarily cached for session continuity

FILE RESTRICTIONS:
• Only text-based files with extensions .txt, .dta, .csv are accepted by the server
• Files must be under 5MB in size
• Binary files and suspicious content will be automatically rejected
• The server performs content validation to ensure data integrity

SECURITY CONSIDERATIONS:
• Ensure your selected folder contains only data you consent to share
• Do not include sensitive, confidential, or proprietary files in the monitored folder
• This agent operates with the same file access privileges as your user account
• Network transmission occurs over HTTPS with standard encryption

USER RESPONSIBILITIES AND FILE SAFETY:
• YOU ARE SOLELY RESPONSIBLE for ensuring all files in the monitored folder are safe to share
• YOU MUST verify that no sensitive, confidential, or proprietary information is included
• YOU ARE RESPONSIBLE for ensuring you have proper authorization to share the data
• Verify that sharing this data complies with your institutional policies
• Remove any sensitive files from the monitored folder before starting the agent
• You may stop monitoring at any time by clicking the "Stop" button
• SACMES is not liable for any data you choose to share through this agent

TECHNICAL OPERATION:
• The agent scans for files matching specific naming patterns related to electrochemical data
• Only files matching the analysis filters will be processed and transmitted
• The agent requires an active internet connection to communicate with SACMES servers
• Session data is associated with a unique identifier for your analysis session

DATA RETENTION:
• Raw data files are not permanently stored on our servers
• Analysis results are retained only for the duration of your active session
• You are responsible for downloading/exporting your results before closing the application
• We do not backup or archive user data for long-term storage

CONSENT WITHDRAWAL:
• You may withdraw consent and stop data transmission at any time
• Stopping the agent immediately ceases all file monitoring and data transmission
• Previously transmitted data may remain in temporary server storage until session cleanup

By clicking "I Accept" below, you confirm that:
1. You have read and understood these terms
2. You authorize this agent to access files in your selected folder
3. You consent to the transmission and processing of your data as described
4. You have appropriate authorization to share this data
5. You understand the security implications and technical operation of this agent

If you do not agree to these terms, click "Cancel" to exit without starting the monitoring process."""

    def show_consent_dialog(self):
        """Show consent dialog and return True if accepted, False if declined"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("SACMES Data Access Consent")
        dialog.geometry("650x550")
        dialog.resizable(True, True)

        # Make dialog modal
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.focus_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (650 // 2)
        y = (dialog.winfo_screenheight() // 2) - (550 // 2)
        dialog.geometry(f"650x550+{x}+{y}")

        # Title
        title_label = tk.Label(dialog, text="Data Access Consent Required",
                              font=("Arial", 14, "bold"), fg="#DC2626")
        title_label.pack(pady=15)

        # Instruction text
        instruction = tk.Label(dialog,
                              text="Please read the following terms carefully before proceeding:",
                              font=("Arial", 10), fg="#374151")
        instruction.pack(pady=(0, 10))

        # Scrollable text area for consent
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        consent_text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 10),
            bg="#F9FAFB",
            relief=tk.SOLID,
            borderwidth=1
        )
        consent_text_widget.pack(fill=tk.BOTH, expand=True)
        consent_text_widget.insert(tk.END, self.consent_text)
        consent_text_widget.config(state=tk.DISABLED)

        # Warning text
        warning_label = tk.Label(dialog,
                                text="  This agent will access ALL files in your selected folder",
                                font=("Arial", 10, "bold"), fg="#DC2626")
        warning_label.pack(pady=(10, 5))

        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=15)

        # Button handlers
        def on_accept():
            self.consent_given = True
            dialog.destroy()

        def on_decline():
            self.consent_given = False
            dialog.destroy()

        def on_window_close():
            self.consent_given = False
            dialog.destroy()

        # Buttons
        decline_btn = tk.Button(button_frame, text="Cancel",
                               command=on_decline,
                               bg="#6B7280", fg="white",
                               font=("Arial", 11, "bold"),
                               width=12, height=2,
                               relief=tk.FLAT)
        decline_btn.pack(side=tk.LEFT, padx=15)

        accept_btn = tk.Button(button_frame, text="I Accept",
                              command=on_accept,
                              bg="#16A34A", fg="white",
                              font=("Arial", 11, "bold"),
                              width=12, height=2,
                              relief=tk.FLAT)
        accept_btn.pack(side=tk.LEFT, padx=15)

        # Handle window close
        dialog.protocol("WM_DELETE_WINDOW", on_window_close)

        # Show dialog and wait
        dialog.wait_window()

        return self.consent_given


# --- Agent's Internal State ---
current_filters = {}
processed_files = set()
is_monitoring_active = False
agent_thread = None
file_processing_complete = False
pending_file_ack = None

# --- Flow Control Configuration ---
# Time delay between sending files to prevent overwhelming the server
# Default: 0.1 seconds = 10 files/second (configurable from server)
file_send_interval = 0.1  # seconds between files
max_send_rate = 10  # maximum files per second (safety limit)

# --- Socket.IO Client Setup ---
# Note: transports parameter is specified in connect() method, not in Client() init
sio = socketio.Client(
    reconnection_attempts=5,
    reconnection_delay=5,
    logger=True,
    engineio_logger=True
)


# --- Core Agent Logic (Unchanged) ---
def file_matches_filters(filename):
    required_keys = ['handle', 'frequencies', 'range_start', 'range_end', 'file_extension']
    if not all(k in current_filters for k in required_keys): return False

    # Allow files without extension if file_extension is empty, or check extension normally
    file_ext = current_filters['file_extension']
    if file_ext and not filename.endswith(file_ext): return False
    if not filename.startswith(current_filters['handle']): return False

    # Check if this is frequency map mode
    analysis_mode = current_filters.get('analysis_mode', 'continuous')

    try:
        if analysis_mode == 'frequency_map':
            # Frequency Map mode: handle_freqHz.txt or handle_freqHz_.txt (NO file number)
            # Pattern: handle_100Hz.txt or handle_100Hz_.txt
            match_freq_map = re.search(r'_(\d+)Hz_?\.', filename, re.IGNORECASE)
            if match_freq_map:
                freq = int(match_freq_map.group(1))
                # Check if frequency is in the list
                if freq not in current_filters['frequencies']:
                    return False
                return True  # No file number check for frequency map
            else:
                return False
        else:
            # Continuous/CV modes (original logic)
            # Three file naming patterns:
            # 1. SWV: handle_freqHz_{1,2}num  (e.g., SWV_15Hz_1 or SWV_15Hz__1)
            #    - frequency MUST be extracted from filename for KDM calculation
            # 2. CV: handle_{1,2}num  (e.g., CV_60Hz_1, 2025_10_03_CV_Test__1)
            #    - CV doesn't use frequency, just handle + file number

            # First try SWV pattern (handle + frequency in filename)
            # Support SWV_75Hz_1.txt, SWV_75Hz__1.txt, and SWV_75Hz1.txt formats
            match_swv = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
            if match_swv:
                # SWV format: extract frequency from filename
                freq, num = int(match_swv.group(1)), int(match_swv.group(2))
            else:
                # CV format: handle_{1,2}num (no Hz in filename)
                remaining = filename[len(current_filters['handle']):]
                match_cv = re.search(r'^_{1,2}(\d+)\.', remaining, re.IGNORECASE)
                if not match_cv:
                    return False
                # CV doesn't use frequency
                num = int(match_cv.group(1))
                freq = None  # No frequency for CV

            # Only check frequency for SWV files (freq is not None)
            if freq is not None:
                if freq not in current_filters['frequencies']:
                    return False

            # Check file number range (applies to both SWV and CV)
            if not (current_filters['range_start'] <= num <= current_filters['range_end']):
                return False

            return True
    except (ValueError, IndexError):
        return False


def send_file_to_server(file_path):
    """
    Send a file to the server and wait for confirmation.
    Returns: True if file was successfully sent and confirmed, False otherwise
    """
    global file_processing_complete, pending_file_ack, is_monitoring_active
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        filename = os.path.basename(file_path)
        if sio.connected:
            app.log(f"--> Sending '{filename}'...")

            # Reset processing state and set pending file
            file_processing_complete = False
            pending_file_ack = filename

            # Determine if this is CV analysis based on filename pattern
            # CV files don't have Hz in the filename (e.g., CV_60Hz_1.txt, 2025_10_03_CV_Test__1.txt)
            # SWV files MUST have Hz in the filename (e.g., SWV_15Hz_1.txt)
            is_cv_file = 'Hz' not in filename

            if is_cv_file:
                # Send CV file to CV handler
                sio.emit('cv_data_from_agent', {
                    'filename': filename,
                    'content': content,
                    'preview_mode': False,
                    'status': 'success'
                })
            else:
                # Send SWV file to SWV handler
                sio.emit('stream_instrument_data', {'filename': filename, 'content': content})

            # Wait for server processing complete acknowledgment (interruptible)
            timeout_counter = 0
            max_wait_time = 60  # Increased to 60 seconds for heavy data processing
            last_log_time = 0

            while not file_processing_complete and timeout_counter < max_wait_time and is_monitoring_active:
                time.sleep(0.05)  # Faster check interval for responsive stop
                timeout_counter += 0.05

                # Progress feedback every 5 seconds to show Agent is not frozen
                if int(timeout_counter) > last_log_time and int(timeout_counter) % 5 == 0:
                    app.log(f"[Processing] Waiting for server... {int(timeout_counter)}s (file: '{filename}')")
                    last_log_time = int(timeout_counter)

            # Reset state
            pending_file_ack = None

            # Check if stopped by user/server
            if not is_monitoring_active:
                app.log(f"[Info] File sending interrupted by stop command for '{filename}'")
                return False  # Failed: interrupted
            elif file_processing_complete:
                elapsed = f"{timeout_counter:.1f}s" if timeout_counter < 1 else f"{int(timeout_counter)}s"
                app.log(f"<-- Server confirmed processing complete for '{filename}' (took {elapsed})")

                # Flow Control: Add delay between file sends to prevent overwhelming server
                # This ensures steady data flow and prevents WebSocket buffer overflow
                if file_send_interval > 0 and is_monitoring_active:
                    time.sleep(file_send_interval)

                return True  # Success: confirmed by server
            else:
                app.log(f"[Warning] Timeout ({max_wait_time}s) waiting for server confirmation for '{filename}' - continuing anyway")
                # Even on timeout, we consider it "sent" to avoid re-sending
                # The server may still be processing it
                return True

        else:
            app.log(f"[Warning] Cannot send '{filename}', not connected.")
            is_monitoring_active = False
            return False  # Failed: not connected
    except Exception as e:
        app.log(f"[Error] Could not read or send file {file_path}: {e}")
        pending_file_ack = None
        return False  # Failed: exception occurred


def monitor_directory_loop(directory):
    global processed_files, is_monitoring_active
    app.log(f"--- Started monitoring folder: '{directory}' ---")
    app.log(f"Current filters: {current_filters}")

    while is_monitoring_active:
        try:
            # List all files in directory
            all_files = os.listdir(directory)
            app.log(f"Found {len(all_files)} total files in directory")

            # Filter matching files
            new_matching_files = [f for f in all_files if
                                  file_matches_filters(f) and f not in processed_files]

            if new_matching_files:
                app.log(f"Found {len(new_matching_files)} new matching file(s) to process...")

                # Check if this is frequency map mode
                analysis_mode = current_filters.get('analysis_mode', 'continuous')

                if analysis_mode == 'frequency_map':
                    # Frequency map mode: no file numbering, send files directly sorted by name
                    app.log("Frequency Map mode: sending files without number grouping")
                    for filename in sorted(new_matching_files):
                        if not is_monitoring_active:
                            app.log("Monitoring stopped, aborting file sending.")
                            return
                        app.log(f"Sending file: {filename}")
                        # Only mark as processed if successfully sent
                        if send_file_to_server(os.path.join(directory, filename)):
                            processed_files.add(filename)
                        else:
                            app.log(f"[Warning] File '{filename}' not sent, will retry later")
                            # If sending failed, stop monitoring to avoid accumulating failures
                            return
                else:
                    # Continuous/CV mode: group by file number
                    files_by_number = defaultdict(list)
                    for filename in new_matching_files:
                        # Extract file number for grouping
                        if filename.startswith(current_filters['handle']):
                            # For files starting with handle (like CV_60Hz_1.txt or CV_60Hz__1.txt)
                            remaining = filename[len(current_filters['handle']):]
                            match = re.search(r'_{1,2}(\d+)\.', remaining, re.IGNORECASE)
                            if match:
                                num = int(match.group(1))
                                files_by_number[num].append(filename)
                        else:
                            # For older format files like _60Hz_1. or _60Hz__1.
                            match = re.search(r'(?:^|_)(\d+)Hz.*?_{1,2}(\d+)(?:\.|$)', filename, re.IGNORECASE)
                            if match:
                                files_by_number[int(match.group(2))].append(filename)

                    for num in sorted(files_by_number.keys()):
                        for filename in sorted(files_by_number[num]):
                            if not is_monitoring_active:
                                app.log("Monitoring stopped, aborting file sending.")
                                return
                            app.log(f"Sending file: {filename}")
                            # Only mark as processed if successfully sent
                            if send_file_to_server(os.path.join(directory, filename)):
                                processed_files.add(filename)
                            else:
                                app.log(f"[Warning] File '{filename}' not sent, will retry later")
                                # If sending failed, stop monitoring to avoid accumulating failures
                                return
            else:
                # Show a few example files to help with debugging
                if len(all_files) > 0:
                    sample_files = all_files[:3]
                    app.log(f"No matching files found. Sample files: {sample_files}")
                    # Check one sample file against filters
                    if sample_files:
                        sample_file = sample_files[0]
                        matches = file_matches_filters(sample_file)
                        app.log(f"Sample file '{sample_file}' matches filters: {matches}")
                else:
                    app.log("Directory is empty")

            time.sleep(POLLING_INTERVAL_SECONDS)
        except FileNotFoundError:
            app.log(f"[FATAL] Monitored directory '{directory}' no longer exists. Stopping.")
            app.stop_monitoring_logic()
            break
        except Exception as e:
            app.log(f"[Error] An unexpected error occurred in the monitoring loop: {e}")
            time.sleep(POLLING_INTERVAL_SECONDS * 2)


# --- Socket.IO Event Handlers ---
@sio.event
def connect():
    app.update_status("Connected", "green")
    app.log(f"Successfully connected to server: {app.server_url.get()}")


@sio.event
def connect_error(data):
    app.update_status("Connection Failed", "red")
    app.log(f"✗ Connection failed! Server issue at {app.server_url.get()}")
    app.log(f"Error details: {data}")


@sio.event
def disconnect():
    app.update_status("Disconnected", "red")
    app.log("Disconnected from server.")


@sio.on('set_filters')
def on_set_filters(data):
    global current_filters, processed_files, agent_thread, is_monitoring_active
    app.log(f"Received filter instructions from server: {data}")
    current_filters.clear()
    current_filters.update(data)
    processed_files = set()
    app.log(f"Updated current filters: {current_filters}")
    app.log(f"Monitor directory: {app.watch_directory.get()}")

    if agent_thread and agent_thread.is_alive():
        app.log("Stopping previous monitoring thread...")
        is_monitoring_active = False
        agent_thread.join()

    is_monitoring_active = True
    directory = app.watch_directory.get()

    if directory == "No folder selected":
        app.log("ERROR: No folder selected for monitoring!")
        return

    app.log(f"Starting file monitoring in directory: {directory}")
    agent_thread = threading.Thread(target=monitor_directory_loop, args=(directory,), daemon=True)
    agent_thread.start()
    app.log("File monitoring thread started successfully")


@sio.on('request_frequency_scan')
def on_request_frequency_scan(data):
    """
    Scan the monitored directory for all available frequencies.
    Used for frequency map mode to populate frequency dropdown.
    """
    app.log(f"[FREQUENCY SCAN] Received request_frequency_scan event with data: {data}")

    file_handle = data.get('file_handle', '')
    requester_sid = data.get('requester_sid')

    directory = app.watch_directory.get()
    app.log(f"[FREQUENCY SCAN] Scanning directory: {directory}")

    if directory == "No folder selected":
        app.log("[FREQUENCY SCAN] ERROR: No folder selected")
        sio.emit('frequency_scan_result', {
            'status': 'error',
            'message': 'No folder selected',
            'requester_sid': requester_sid
        })
        return

    try:
        frequencies = set()
        file_extension = '.txt'
        file_count = 0
        matched_files = []

        app.log(f"[FREQUENCY SCAN] Looking for files with handle: '{file_handle}'")

        for filename in os.listdir(directory):
            file_count += 1

            if not filename.endswith(file_extension):
                continue

            if file_handle and not filename.startswith(file_handle):
                continue

            match = re.search(r'_(\d+)Hz_?\.', filename, re.IGNORECASE)
            if match:
                freq = int(match.group(1))
                frequencies.add(freq)
                matched_files.append(filename)

        frequencies_list = sorted(list(frequencies))
        app.log(f"[FREQUENCY SCAN] Scanned {file_count} files, found {len(matched_files)} matching files")
        app.log(f"[FREQUENCY SCAN] Detected frequencies: {frequencies_list}")
        app.log(f"[FREQUENCY SCAN] Sample matched files: {matched_files[:5]}")

        sio.emit('frequency_scan_result', {
            'frequencies': frequencies_list,
            'file_handle': file_handle,
            'requester_sid': requester_sid
        })

        app.log(f"[FREQUENCY SCAN] Emitted frequency_scan_result to server")

    except Exception as e:
        app.log(f"[FREQUENCY SCAN] ERROR: {str(e)}")
        import traceback
        app.log(f"[FREQUENCY SCAN] Traceback: {traceback.format_exc()}")
        sio.emit('frequency_scan_result', {
            'status': 'error',
            'message': str(e),
            'requester_sid': requester_sid
        })


@sio.on('file_processing_complete')
def on_file_processing_complete(data):
    global file_processing_complete, pending_file_ack
    received_filename = data.get('filename', '')
    if pending_file_ack and received_filename == pending_file_ack:
        file_processing_complete = True
        app.log(f"<-- Processing acknowledgment received for: {received_filename}")
    else:
        app.log(f"[Warning] Unexpected processing acknowledgment for: {received_filename}")


@sio.on('file_validation_error')
def on_file_validation_error(data):
    filename = data.get('filename', 'unknown_file')
    error_message = data.get('message', 'File validation failed')
    app.log(f"[SECURITY] File rejected by server: {filename}")
    app.log(f"[SECURITY] Reason: {error_message}")


@sio.on('get_cv_file_for_preview')
def on_get_cv_file_for_preview(data):
    """Handle request for CV preview file from server"""
    global current_filters
    app.log(f"Received CV preview request from server: {data}")

    filters = data.get('filters', {})
    analysis_params = data.get('analysisParams', {})
    preview_mode = data.get('preview_mode', True)

    app.log(f"CV Preview filters: {filters}")

    # Get directory and find the first matching file for preview
    directory = app.watch_directory.get()
    if directory == "No folder selected":
        app.log("ERROR: No folder selected for monitoring!")
        sio.emit('cv_data_from_agent', {
            'status': 'error',
            'message': 'No folder selected',
            'preview_mode': True
        })
        return

    try:
        # Look for files matching the pattern in the directory
        handle = filters.get('handle', '')
        app.log(f"Looking for CV files with handle: '{handle}'")

        # Optimized: directly search for files starting with handle to avoid processing all files
        try:
            all_files = [f for f in os.listdir(directory)
                        if os.path.isfile(os.path.join(directory, f)) and f.startswith(handle)]
            app.log(f"Found {len(all_files)} files starting with handle '{handle}'")
        except Exception as e:
            app.log(f"Error reading directory: {e}")
            sio.emit('cv_data_from_agent', {
                'status': 'error',
                'message': f'Error reading directory: {e}',
                'preview_mode': True
            })
            return

        # Filter for CV files that match the pattern - optimized regex
        matching_files = []
        import re

        # Debug: show some example files
        if all_files:
            app.log(f"Sample files found: {all_files[:3]}")

        # Pattern to match CV files with single or double underscore before file number
        # Examples: CV_60Hz_1.txt, CV_60Hz__1.txt, 2025_10_03_CV_Test__1.txt
        # The pattern is: handle + (_ or __) + number + .txt
        cv_pattern = re.compile(r'^' + re.escape(handle) + r'_{1,2}(\d+)\.txt$', re.IGNORECASE)
        app.log(f"Using regex pattern: ^{re.escape(handle)}_{{1,2}}(\d+)\.txt$")

        for filename in all_files:
            app.log(f"Testing file: '{filename}' against pattern")
            match = cv_pattern.match(filename)
            if match:
                matching_files.append(filename)
                app.log(f"Found matching CV file: {filename}")
                # For preview, we only need the first file, so break early
                break
            else:
                app.log(f"File '{filename}' does not match pattern")

        if not matching_files:
            app.log(f"No CV files found matching handle '{handle}' in directory")
            sample_files = all_files[:3] if all_files else []
            app.log(f"Sample files in directory: {sample_files}")
            sio.emit('cv_data_from_agent', {
                'status': 'error',
                'message': f'No CV files found matching handle "{handle}"',
                'preview_mode': True
            })
            return

        # Use the first matching file for preview
        preview_file = matching_files[0]
        file_path = os.path.join(directory, preview_file)
        app.log(f"Reading CV preview file: {preview_file}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        app.log(f"Successfully read CV preview file, content length: {len(content)} characters")

        # Send the content back to server for preview processing
        sio.emit('cv_data_from_agent', {
            'filename': preview_file,
            'content': content,
            'analysisParams': analysis_params,
            'preview_mode': True,
            'status': 'success'
        })

        app.log(f"Sent CV preview data to server: {preview_file}")

    except Exception as e:
        app.log(f"Error getting CV preview file: {e}")
        sio.emit('cv_data_from_agent', {
            'status': 'error',
            'message': str(e),
            'preview_mode': True
        })


@sio.on('stop_data_stream')
def on_stop_data_stream(data):
    """Handle stop command from server for SWV analysis"""
    global is_monitoring_active
    app.log("Received STOP command from server for SWV analysis")
    is_monitoring_active = False
    app.log("File monitoring stopped by server")


@sio.on('stop_cv_data_stream')
def on_stop_cv_data_stream(data):
    """Handle stop command from server for CV analysis"""
    global is_monitoring_active
    app.log("Received STOP command from server for CV analysis")
    is_monitoring_active = False
    app.log("File monitoring stopped by server")


@sio.on('consent_logged')
def on_consent_logged(data):
    status = data.get('status', 'unknown')
    user_id = data.get('user_id', 'unknown')
    if status == 'success':
        app.log(f"Server confirmed consent logged for user: {user_id}")
    else:
        app.log(f"Server failed to log consent for user: {user_id}")


@sio.on('connection_rejected')
def on_connection_rejected(data):
    """Handle connection rejection from server (e.g., user_id collision)"""
    reason = data.get('reason', 'unknown')
    message = data.get('message', 'Connection rejected by server')
    user_id = data.get('user_id', 'unknown')

    app.log("\n" + "=" * 60)
    app.log("ERROR: Connection Rejected by Server")
    app.log("=" * 60)


@sio.on('adjust_send_rate')
def on_adjust_send_rate(data):
    """
    Handle server request to adjust file sending rate.
    Server can dynamically control Agent's send rate based on its load.
    """
    global file_send_interval

    requested_interval = data.get('interval', 0.1)  # seconds between files
    reason = data.get('reason', 'load balancing')

    # Apply safety limits: minimum 0.05s (20 files/s), maximum 1.0s (1 file/s)
    if requested_interval < 0.05:
        requested_interval = 0.05
    elif requested_interval > 1.0:
        requested_interval = 1.0

    old_interval = file_send_interval
    file_send_interval = requested_interval

    files_per_sec = int(1 / file_send_interval) if file_send_interval > 0 else 0
    app.log(f"[FLOW CONTROL] Send rate adjusted: {old_interval:.2f}s → {requested_interval:.2f}s/file (~{files_per_sec} files/sec)")
    app.log(f"[FLOW CONTROL] Reason: {reason}")


# --- Advanced Settings Dialog (Hidden Menu) ---
class AdvancedSettingsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.result = None

    def show(self):
        """Show the advanced settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Advanced Settings")
        self.dialog.geometry("400x250")
        self.dialog.resizable(False, False)

        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Main frame
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="Flow Control Settings",
                              font=("Helvetica", 12, "bold"))
        title_label.pack(pady=(0, 15))

        # Current rate display
        global file_send_interval
        current_rate = int(1 / file_send_interval) if file_send_interval > 0 else 0
        info_text = f"Current: {current_rate} files/sec ({file_send_interval:.2f}s interval)"
        current_label = tk.Label(main_frame, text=info_text, fg="blue")
        current_label.pack(pady=(0, 10))

        # Rate slider frame
        slider_frame = tk.Frame(main_frame)
        slider_frame.pack(fill=tk.X, pady=10)

        tk.Label(slider_frame, text="Send Rate (files/sec):").pack(anchor="w")

        # Value display
        self.rate_var = tk.IntVar(value=current_rate)
        self.rate_display = tk.Label(slider_frame, text=f"{current_rate} files/sec",
                                     font=("Helvetica", 10, "bold"), fg="green")
        self.rate_display.pack(pady=5)

        # Slider (1-20 files/sec)
        def update_display(val):
            rate = int(float(val))
            self.rate_var.set(rate)
            self.rate_display.config(text=f"{rate} files/sec")

        self.rate_slider = tk.Scale(slider_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                                   command=update_display, length=300)
        self.rate_slider.set(current_rate)
        self.rate_slider.pack(fill=tk.X)

        # Info text
        info_label = tk.Label(main_frame, text="1-5: Slow (server under load)\n"
                                              "6-10: Normal\n"
                                              "11-20: Fast (use with caution)",
                             justify=tk.LEFT, fg="gray")
        info_label.pack(pady=10)

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))

        tk.Button(button_frame, text="Apply", command=self.apply_settings,
                 bg="#4CAF50", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self.dialog.destroy,
                 width=10).pack(side=tk.LEFT, padx=5)

        # Wait for dialog to close
        self.parent.wait_window(self.dialog)

    def apply_settings(self):
        """Apply the new rate settings"""
        global file_send_interval

        new_rate = self.rate_var.get()
        new_interval = 1.0 / new_rate if new_rate > 0 else 0.1

        old_rate = int(1 / file_send_interval) if file_send_interval > 0 else 0
        file_send_interval = new_interval

        app.log(f"[MANUAL SETTING] Send rate changed: {old_rate} → {new_rate} files/sec")
        app.log(f"[MANUAL SETTING] New interval: {new_interval:.3f}s between files")

        messagebox.showinfo("Settings Applied",
                           f"Send rate updated to {new_rate} files/sec\n"
                           f"({new_interval:.3f}s interval between files)",
                           parent=self.dialog)
        self.dialog.destroy()


# --- GUI Application Class ---
class AgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SACMES Lightweight Local Agent")
        self.root.geometry("600x500")  # Increased height for the new input field
        self.root.minsize(500, 400)

        # --- NEW: GUI variables ---
        self.watch_directory = tk.StringVar(value="No folder selected")
        self.server_url = tk.StringVar(value="https://sacmes-web-narroyo.apps.cloudapps.unc.edu")

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- NEW: Server URL Frame ---
        server_frame = tk.Frame(main_frame, pady=5)
        server_frame.pack(fill=tk.X)
        tk.Label(server_frame, text="Server URL:", anchor="w").pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = tk.Entry(server_frame, textvariable=self.server_url, font=("Helvetica", 9))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- User ID Display Frame ---
        user_id_frame = tk.Frame(main_frame, pady=5, bg="#e8f5e9", relief=tk.RIDGE, bd=1)
        user_id_frame.pack(fill=tk.X, pady=(5, 0))

        tk.Label(user_id_frame, text="User ID (for web connection):", anchor="w", bg="#e8f5e9",
                font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(5, 5))

        # User ID display with copy button
        user_id_display_frame = tk.Frame(user_id_frame, bg="white", relief=tk.SUNKEN, bd=1)
        user_id_display_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.user_id_label = tk.Label(
            user_id_display_frame,
            text=id_manager.get_user_id(),
            bg="white",
            fg="#0066cc",
            font=("Courier New", 9),
            anchor="w",
            padx=5
        )
        self.user_id_label.pack(fill=tk.X)

        def copy_user_id():
            user_id = id_manager.get_user_id()
            root.clipboard_clear()
            root.clipboard_append(user_id)
            self.log(f"User ID copied to clipboard: {user_id}")
            # Visual feedback
            copy_btn.config(text="Copied!", bg="#66bb6a")
            root.after(2000, lambda: copy_btn.config(text="Copy", bg="#4CAF50"))

        copy_btn = tk.Button(
            user_id_frame,
            text="Copy",
            command=copy_user_id,
            width=8,
            bg="#4CAF50",
            fg="white",
            font=("Helvetica", 9, "bold"),
            relief=tk.RAISED,
            cursor="hand2",
            padx=5
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Folder Selection Frame
        folder_frame = tk.Frame(main_frame)
        folder_frame.pack(fill=tk.X)
        tk.Label(folder_frame, text="Monitoring Folder:", anchor="w").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_display = tk.Label(folder_frame, textvariable=self.watch_directory, fg="blue", anchor="w",
                                       wraplength=350)
        self.folder_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.select_button = tk.Button(folder_frame, text="Select Folder", command=self.select_folder)
        self.select_button.pack(side=tk.RIGHT, padx=5)

        # Control Frame
        control_frame = tk.Frame(main_frame, pady=10)
        control_frame.pack(fill=tk.X)
        self.start_button = tk.Button(control_frame, text="Connect & Start", command=self.start_monitoring,
                                      state=tk.DISABLED, bg="#D4EDDA")
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = tk.Button(control_frame, text="Stop", command=self.stop_monitoring, state=tk.DISABLED,
                                     bg="#F8D7DA")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text="Server Status:", anchor="e").pack(side=tk.LEFT, padx=(20, 5))
        self.status_display = tk.Label(control_frame, text="Not Connected", fg="red", font=("Helvetica", 10, "bold"))
        self.status_display.pack(side=tk.LEFT)

        # Log Frame
        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Agent Log:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, font=("Courier New", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Hidden menu: Triple-click on User ID label to open advanced settings
        self.user_id_label.bind('<Triple-Button-1>', lambda _: self.open_advanced_settings())

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_advanced_settings(self):
        """Open the advanced settings dialog (hidden menu)"""
        self.log("[HIDDEN MENU] Opening advanced settings...")
        dialog = AdvancedSettingsDialog(self.root)
        dialog.show()

    def select_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            self.watch_directory.set(directory)
            if self.server_url.get():  # Enable start button only if URL is also present
                self.start_button.config(state=tk.NORMAL)
            self.log(f"Folder selected: {directory}")

    def start_monitoring(self):
        if not self.server_url.get().strip():
            messagebox.showerror("Error", "Please enter a valid server URL.")
            return
        if self.watch_directory.get() == "No folder selected":
            messagebox.showerror("Error", "Please select a folder to monitor first.")
            return

        # Show consent dialog before proceeding
        self.log("Requesting user consent for data access...")
        consent_dialog = ConsentDialog(self.root)

        if not consent_dialog.show_consent_dialog():
            messagebox.showinfo("Analysis Cancelled",
                              "You must accept the data access terms to proceed with monitoring.\n\n"
                              "The agent requires explicit consent to access files in your selected folder.")
            self.log("User declined consent - monitoring cancelled.")
            return

        # Start new session and log consent acceptance
        session_id = id_manager.start_new_session()
        user_id = id_manager.get_user_id()
        self.log(f"User consent obtained (User ID: {user_id}, Session ID: {session_id})")

        # Proceed with monitoring immediately (skip blocking consent logging to server)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.select_button.config(state=tk.DISABLED)
        self.url_entry.config(state=tk.DISABLED)  # Disable URL entry while running

        # Store consent data for later logging through main connection
        self.consent_data = id_manager.get_consent_data()

        connection_thread = threading.Thread(target=self.run_connection_logic, daemon=True)
        connection_thread.start()

    def run_connection_logic(self):
        try:
            server_url_to_connect = self.server_url.get()
            self.log("--- SACMES Local Agent ---")
            self.update_status("Connecting...", "orange")
            self.log(f"Attempting to connect to server at {server_url_to_connect}...")

            # Check if already connected and if URL has changed
            if sio.connected:
                # Check if the URL has changed
                if hasattr(self, 'last_connected_url') and self.last_connected_url == server_url_to_connect:
                    self.log("Already connected to the same server - reusing existing connection")
                    self.update_status("Connected", "green")

                    # Send consent data if available
                    if hasattr(self, 'consent_data'):
                        try:
                            self.log(f"Sending consent data: {self.consent_data}")
                            sio.emit('agent_consent', self.consent_data)
                            self.log("Consent data sent to server successfully.")
                        except Exception as e:
                            self.log(f"Could not log consent to server: {e}")

                    self.log("Agent is ready and waiting for analysis instructions from the server...")
                    return
                else:
                    # URL has changed, disconnect first
                    self.log(f"Server URL changed from {getattr(self, 'last_connected_url', 'N/A')} to {server_url_to_connect}")
                    self.log("Disconnecting from old server...")
                    sio.disconnect()
                    self.log("Disconnected from old server")

            self.log("Preparing connection with authentication...")
            headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

            # Get user_id to send with connection
            user_id = id_manager.get_user_id()
            connection_url = f"{server_url_to_connect}?user_id={user_id}"

            self.log(f"Initiating Socket.IO connection with User ID: {user_id}...")
            # WebSocket-first configuration for reduced server load and lower latency
            sio.connect(connection_url, headers=headers, socketio_path='socket.io', transports=['websocket', 'polling'])
            self.log("Socket.IO connection established!")

            # Save the connected URL for future comparison
            self.last_connected_url = server_url_to_connect

            # Diagnostic: List all registered event handlers
            registered_events = list(sio.handlers.get('/', {}).keys())
            self.log(f"[DIAGNOSTIC] Registered Socket.IO events: {registered_events}")
            if 'request_frequency_scan' in registered_events:
                self.log("[DIAGNOSTIC] request_frequency_scan handler is registered")
            else:
                self.log("[DIAGNOSTIC] WARNING: request_frequency_scan handler NOT registered!")

            # Wait a moment for connection to stabilize
            time.sleep(0.5)

            # Log consent to server after successful connection (non-blocking)
            if hasattr(self, 'consent_data'):
                try:
                    self.log(f"Sending consent data: {self.consent_data}")
                    sio.emit('agent_consent', self.consent_data)
                    self.log("Consent data sent to server successfully.")
                except Exception as e:
                    self.log(f"Could not log consent to server: {e}")
            else:
                self.log("No consent data found to send.")

            self.log("Agent is now running and waiting for analysis instructions from the server...")
        except socketio.exceptions.ConnectionError as e:
            self.log(f"[FATAL] Could not connect to the server. Is it running? Details: {e}")
            self.log(f"Attempted URL: {server_url_to_connect}")
            self.log("Please check: 1) Internet connection, 2) Server URL, 3) Server status")
            self.update_status("Connection Failed", "red")
            self.stop_monitoring_logic()
        except Exception as e:
            self.log(f"[FATAL] An unexpected error occurred: {e}")
            self.log(f"Error type: {type(e).__name__}")
            self.log(f"Attempted URL: {server_url_to_connect}")
            self.update_status("Error", "red")
            self.stop_monitoring_logic()

    def stop_monitoring(self):
        self.log("Stopping process...")
        self.stop_monitoring_logic()
        # Keep connection alive - don't disconnect to avoid reconnection issues

    def stop_monitoring_logic(self):
        global is_monitoring_active, agent_thread
        is_monitoring_active = False
        if agent_thread and agent_thread.is_alive():
            agent_thread.join(timeout=0.5)  # Quick timeout for immediate UI response
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.select_button.config(state=tk.NORMAL)
        self.url_entry.config(state=tk.NORMAL)  # Re-enable URL entry
        self.log("Monitoring has been stopped.")

    def log(self, message):
        self.root.after(0, self._log_message, message)

    def _log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def update_status(self, text, color):
        self.root.after(0, self._update_status, text, color)

    def _update_status(self, text, color):
        self.status_display.config(text=text, fg=color)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Are you sure you want to close the agent?"):
            self.log("Closing agent - disconnecting from server...")
            self.stop_monitoring()

            # Explicitly disconnect socket to ensure clean shutdown
            if sio.connected:
                try:
                    self.log("Disconnecting socket connection...")
                    sio.disconnect()
                    self.log("Socket disconnected successfully")
                except Exception as e:
                    self.log(f"Error disconnecting socket: {e}")

            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AgentApp(root)
    root.mainloop()
