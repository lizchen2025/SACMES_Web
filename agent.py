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
POLLING_INTERVAL_SECONDS = 2
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

# --- Socket.IO Client Setup ---
sio = socketio.Client(reconnection_attempts=5, reconnection_delay=5, logger=True, engineio_logger=True)


# --- Core Agent Logic (Unchanged) ---
def file_matches_filters(filename):
    required_keys = ['handle', 'frequencies', 'range_start', 'range_end', 'file_extension']
    if not all(k in current_filters for k in required_keys): return False
    if not filename.endswith(current_filters['file_extension']): return False
    if not filename.startswith(current_filters['handle']): return False
    try:
        match = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
        if not match: return False
        freq, num = int(match.group(1)), int(match.group(2))
    except (ValueError, IndexError):
        return False
    if freq not in current_filters['frequencies']: return False
    if not (current_filters['range_start'] <= num <= current_filters['range_end']): return False
    return True


def send_file_to_server(file_path):
    global file_processing_complete, pending_file_ack
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        filename = os.path.basename(file_path)
        if sio.connected:
            app.log(f"--> Sending '{filename}'...")

            # Reset processing state and set pending file
            file_processing_complete = False
            pending_file_ack = filename

            # Send file to server
            sio.emit('stream_instrument_data', {'filename': filename, 'content': content})

            # Wait for server processing complete acknowledgment
            timeout_counter = 0
            max_wait_time = 30  # 30 seconds timeout
            while not file_processing_complete and timeout_counter < max_wait_time:
                time.sleep(0.1)
                timeout_counter += 0.1

            if file_processing_complete:
                app.log(f"<-- Server confirmed processing complete for '{filename}'")
            else:
                app.log(f"[Warning] Timeout waiting for server confirmation for '{filename}'")

            # Reset state
            pending_file_ack = None

        else:
            app.log(f"[Warning] Cannot send '{filename}', not connected.")
            global is_monitoring_active
            is_monitoring_active = False
    except Exception as e:
        app.log(f"[Error] Could not read or send file {file_path}: {e}")
        pending_file_ack = None


def monitor_directory_loop(directory):
    global processed_files
    app.log(f"--- Started monitoring folder: '{directory}' ---")
    while is_monitoring_active:
        try:
            new_matching_files = [f for f in os.listdir(directory) if
                                  file_matches_filters(f) and f not in processed_files]
            if new_matching_files:
                files_by_number = defaultdict(list)
                for filename in new_matching_files:
                    match = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
                    if match: files_by_number[int(match.group(2))].append(filename)
                app.log(f"Found {len(new_matching_files)} new file(s) to process...")
                for num in sorted(files_by_number.keys()):
                    for filename in sorted(files_by_number[num]):
                        if not is_monitoring_active:
                            app.log("Monitoring stopped, aborting file sending.")
                            return
                        send_file_to_server(os.path.join(directory, filename))
                        processed_files.add(filename)
                        time.sleep(SEND_DELAY_SECONDS)
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
    app.log(f"Connection failed! Please check if the server is running at {app.server_url.get()}.")


@sio.event
def disconnect():
    app.update_status("Disconnected", "red")
    app.log("Disconnected from server.")


@sio.on('set_filters')
def on_set_filters(data):
    global current_filters, processed_files, agent_thread, is_monitoring_active
    app.log(f"<-- Received new filter instructions from server: {data}")
    current_filters.clear()
    current_filters.update(data)
    processed_files = set()
    if agent_thread and agent_thread.is_alive():
        is_monitoring_active = False
        agent_thread.join()
    is_monitoring_active = True
    directory = app.watch_directory.get()
    agent_thread = threading.Thread(target=monitor_directory_loop, args=(directory,), daemon=True)
    agent_thread.start()


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

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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

            # Always try to connect, even if already connected (to ensure fresh connection)
            if sio.connected:
                self.log("Disconnecting from previous connection...")
                sio.disconnect()
                time.sleep(0.5)  # Reduced wait time

            headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
            sio.connect(server_url_to_connect, headers=headers, socketio_path='socket.io', transports=['polling'])

            # Log consent to server after successful connection (non-blocking)
            if hasattr(self, 'consent_data'):
                try:
                    sio.emit('agent_consent', self.consent_data)
                    self.log("Consent logged to server successfully.")
                except Exception as e:
                    self.log(f"Could not log consent to server: {e}")

            self.log("Agent is now running and waiting for analysis instructions from the server...")
        except socketio.exceptions.ConnectionError as e:
            self.log(f"[FATAL] Could not connect to the server. Is it running? Details: {e}")
            self.update_status("Connection Failed", "red")
            self.stop_monitoring_logic()
        except Exception as e:
            self.log(f"[FATAL] An unexpected error occurred: {e}")
            self.update_status("Error", "red")
            self.stop_monitoring_logic()

    def stop_monitoring(self):
        self.log("Stopping process...")
        self.stop_monitoring_logic()
        if sio.connected:
            sio.disconnect()

    def stop_monitoring_logic(self):
        global is_monitoring_active, agent_thread
        is_monitoring_active = False
        if agent_thread and agent_thread.is_alive():
            agent_thread.join(timeout=POLLING_INTERVAL_SECONDS + 1)
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
            self.stop_monitoring()
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AgentApp(root)
    root.mainloop()
