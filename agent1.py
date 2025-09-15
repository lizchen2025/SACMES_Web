# agent1.py (Final Version - Forcing HTTP Long-Polling)
# This version forces the connection to use HTTP long-polling instead of WebSockets,
# making it much more robust against aggressive network proxies in cloud environments.

import os
import re
import time
import socketio
import threading
from collections import defaultdict

# --- GUI (using Python's built-in library) ---
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# --- Configuration ---
SERVER_URL = "https://sacmes-web-narroyo.apps.cloudapps.unc.edu"
AUTH_TOKEN = "your_super_secret_token_here"
POLLING_INTERVAL_SECONDS = 2
SEND_DELAY_SECONDS = 0.05  # Keep this delay to be gentle on the server

# --- Agent's Internal State ---
current_filters = {}
processed_files = set()
is_monitoring_active = False
agent_thread = None

# --- Socket.IO Client Setup ---
# The KEY CHANGE is forcing transports=['polling']
sio = socketio.Client(reconnection_attempts=5, reconnection_delay=5, logger=True, engineio_logger=True)


# --- Core Agent Logic (Unchanged)---

def file_matches_filters(filename):
    """Checks if a file matches the current filter rules received from the server."""
    required_keys = ['handle', 'frequencies', 'range_start', 'range_end', 'file_extension']
    if not all(k in current_filters for k in required_keys):
        return False
    if not filename.endswith(current_filters['file_extension']):
        return False
    if not filename.startswith(current_filters['handle']):
        return False
    try:
        match = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
        if not match: return False
        freq, num = int(match.group(1)), int(match.group(2))
    except (ValueError, IndexError):
        return False
    if freq not in current_filters['frequencies']:
        return False
    if not (current_filters['range_start'] <= num <= current_filters['range_end']):
        return False
    return True


def send_file_to_server(file_path):
    """Reads a file's content and sends it to the server via WebSocket."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        filename = os.path.basename(file_path)
        if sio.connected:
            app.log(f"--> Sending '{filename}'...")
            sio.emit('stream_instrument_data', {'filename': filename, 'content': content})
        else:
            app.log(f"[Warning] Cannot send '{filename}', not connected.")
            global is_monitoring_active
            is_monitoring_active = False
    except Exception as e:
        app.log(f"[Error] Could not read or send file {file_path}: {e}")


def monitor_directory_loop(directory):
    """
    Continuously polls the target directory, finds new matching files,
    and processes them in the correct order with a delay.
    """
    global processed_files
    app.log(f"--- Started monitoring folder: '{directory}' ---")
    app.log(f"--- Polling interval: {POLLING_INTERVAL_SECONDS} seconds ---")
    while is_monitoring_active:
        try:
            new_matching_files = [f for f in os.listdir(directory) if file_matches_filters(f) and f not in processed_files]
            if new_matching_files:
                files_by_number = defaultdict(list)
                for filename in new_matching_files:
                    match = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
                    if match:
                        files_by_number[int(match.group(2))].append(filename)
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


# --- Socket.IO Event Handlers (Unchanged) ---
@sio.event
def connect():
    app.update_status("Connected", "green")
    app.log(f"Successfully connected to server: {SERVER_URL}")

@sio.event
def connect_error(data):
    app.update_status("Connection Failed", "red")
    app.log(f"Connection failed! Please check if the server is running at {SERVER_URL}.")

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


# --- GUI Application Class ---
class AgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SACMES Lightweight Local Agent")
        self.root.geometry("600x450")
        self.root.minsize(500, 350)
        self.watch_directory = tk.StringVar(value="No folder selected")
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X)
        tk.Label(top_frame, text="Monitoring Folder:", anchor="w").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_display = tk.Label(top_frame, textvariable=self.watch_directory, fg="blue", anchor="w", wraplength=350)
        self.folder_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.select_button = tk.Button(top_frame, text="Select Folder", command=self.select_folder)
        self.select_button.pack(side=tk.RIGHT, padx=5)
        control_frame = tk.Frame(main_frame, pady=10)
        control_frame.pack(fill=tk.X)
        self.start_button = tk.Button(control_frame, text="Connect & Start", command=self.start_monitoring, state=tk.DISABLED, bg="#D4EDDA")
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = tk.Button(control_frame, text="Stop", command=self.stop_monitoring, state=tk.DISABLED, bg="#F8D7DA")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text="Server Status:", anchor="e").pack(side=tk.LEFT, padx=(20, 5))
        self.status_display = tk.Label(control_frame, text="Not Connected", fg="red", font=("Helvetica", 10, "bold"))
        self.status_display.pack(side=tk.LEFT)
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
            self.start_button.config(state=tk.NORMAL)
            self.log(f"Folder selected: {directory}")

    def start_monitoring(self):
        if self.watch_directory.get() == "No folder selected":
            messagebox.showerror("Error", "Please select a folder to monitor first.")
            return
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.select_button.config(state=tk.DISABLED)
        connection_thread = threading.Thread(target=self.run_connection_logic, daemon=True)
        connection_thread.start()

    def run_connection_logic(self):
        try:
            if sio.connected:
                self.log("Already connected. Waiting for filter instructions...")
                return
            self.log("--- SACMES Local Agent ---")
            self.update_status("Connecting...", "orange")
            self.log(f"Attempting to connect to server at {SERVER_URL}...")
            headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

            # --- THE ONLY CRITICAL CHANGE IS HERE ---
            # We explicitly tell the client to ONLY use 'polling' and not attempt 'websocket'.
            sio.connect(SERVER_URL, headers=headers, socketio_path='socket.io', transports=['polling'])

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