# agent.py
# This is the local agent script that runs on the user's machine.
# REQUIRED DEPENDENCIES:
# pip install "python-socketio[client]" watchdog websocket-client

import time
import os
import re
import socketio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from collections import defaultdict

# --- GUI Imports ---
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# --- Configuration ---
SERVER_URL = "http://127.0.0.1:5000"
AUTH_TOKEN = "your_super_secret_token_here"

# --- Agent's Internal State ---
current_filters = {
    'handle': '',
    'frequencies': [],
    'range_start': -1,
    'range_end': -1,
    'file_extension': '.txt'
}

# --- Socket.IO Client Setup ---
sio = socketio.Client(reconnection_attempts=5, reconnection_delay=5)
agent_logic_thread = None
observer = None


# --- Core Agent Logic ---

def file_matches_filters(filename):
    """Checks if a file should be sent based on the current filters."""
    if not filename.endswith(current_filters.get('file_extension', '.txt')):
        return False
    if not current_filters.get('handle') or not current_filters.get('frequencies'):
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
    # No log here to prevent clutter, logging is done when sending
    return True


def send_file_to_server(file_path):
    """Reads a file and sends its content to the server via WebSocket."""
    try:
        time.sleep(0.1)  # Reduced sleep time for faster batch processing
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        filename = os.path.basename(file_path)
        if sio.connected:
            app.log(f"--> Sending '{filename}'...")
            sio.emit('stream_instrument_data', {'filename': filename, 'content': content})
        else:
            app.log(f"[Warning] Cannot send '{filename}', not connected.")
    except Exception as e:
        app.log(f"[Error] Could not read or send file {file_path}: {e}")


def process_existing_files_with_filters(directory):
    """
    [FIXED] Scans, groups, and sends files in the correct, interleaved order.
    """
    app.log("\n--- Scanning for existing files with current filters... ---")
    try:
        all_files = os.listdir(directory)

        # Group files by their number
        files_by_number = defaultdict(list)
        for filename in all_files:
            if os.path.isfile(os.path.join(directory, filename)) and file_matches_filters(filename):
                match = re.search(r'_(\d+)Hz_?_?(\d+)\.', filename, re.IGNORECASE)
                if match:
                    file_num = int(match.group(2))
                    files_by_number[file_num].append(filename)

        # Process in numerical order
        sorted_file_numbers = sorted(files_by_number.keys())
        app.log(f"Found {len(sorted_file_numbers)} file number groups to process.")

        for num in sorted_file_numbers:
            # Sort files within the group by frequency to be consistent
            files_by_number[num].sort()
            for filename in files_by_number[num]:
                full_path = os.path.join(directory, filename)
                send_file_to_server(full_path)

    except Exception as e:
        app.log(f"[Error] Failed during initial scan: {e}")
    finally:
        app.log("--- Finished scanning existing files. Now monitoring for new files. ---\n")


# --- Socket.IO Event Handlers ---
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
    """Called when the SERVER sends new filter instructions."""
    global current_filters
    app.log(f"<-- Received new filter instructions from server: {data}")
    current_filters.update(data)
    # Use a thread to avoid blocking the UI while scanning
    scan_thread = threading.Thread(target=process_existing_files_with_filters, args=(app.watch_directory.get(),),
                                   daemon=True)
    scan_thread.start()


# --- Real-time File System Event Handler ---
class InstrumentDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            app.log(f"New file detected: '{filename}'")
            if file_matches_filters(filename):
                send_file_to_server(event.src_path)


# --- GUI Application Class ---
class AgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SACMES Local Agent")
        self.root.geometry("600x450")
        self.root.minsize(500, 350)

        self.watch_directory = tk.StringVar()
        self.watch_directory.set("No folder selected")

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X)

        folder_label = tk.Label(top_frame, text="Monitoring Folder:", anchor="w")
        folder_label.pack(side=tk.LEFT, padx=(0, 5))

        self.folder_display = tk.Label(top_frame, textvariable=self.watch_directory, fg="blue", anchor="w",
                                       wraplength=350)
        self.folder_display.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.select_button = tk.Button(top_frame, text="Select Folder", command=self.select_folder)
        self.select_button.pack(side=tk.RIGHT, padx=5)

        control_frame = tk.Frame(main_frame, pady=10)
        control_frame.pack(fill=tk.X)

        self.start_button = tk.Button(control_frame, text="Start Monitoring", command=self.start_monitoring,
                                      state=tk.DISABLED, bg="#D4EDDA")
        self.start_button.pack(side=tk.LEFT)

        status_label = tk.Label(control_frame, text="Server Status:", anchor="e")
        status_label.pack(side=tk.LEFT, padx=(20, 5))

        self.status_display = tk.Label(control_frame, text="Not Connected", fg="red", font=("Helvetica", 10, "bold"))
        self.status_display.pack(side=tk.LEFT)

        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label = tk.Label(log_frame, text="Agent Log:")
        log_label.pack(anchor="w")

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

        self.start_button.config(state=tk.DISABLED, text="Running...")
        self.select_button.config(state=tk.DISABLED)

        global agent_logic_thread
        agent_logic_thread = threading.Thread(target=self.run_agent_logic, daemon=True)
        agent_logic_thread.start()

    def run_agent_logic(self):
        global observer
        try:
            self.log("--- SACMES Local Agent ---")
            self.update_status("Connecting...", "orange")
            self.log(f"Attempting to connect to server at {SERVER_URL}...")

            headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
            sio.connect(SERVER_URL, headers=headers, socketio_path='socket.io')

            event_handler = InstrumentDataHandler()
            observer = Observer()
            observer.schedule(event_handler, self.watch_directory.get(), recursive=False)
            observer.start()

            self.log(f"Successfully started monitoring directory: '{os.path.abspath(self.watch_directory.get())}'")
            self.log("Agent is now running and waiting for filter instructions from the server...")

        except socketio.exceptions.ConnectionError as e:
            self.log(f"[Fatal Error] Could not connect to the server. Is it running? Details: {e}")
            self.update_status("Connection Failed", "red")
        except Exception as e:
            self.log(f"[Fatal Error] An unexpected error occurred: {e}")
            self.update_status("Error", "red")

    def log(self, message):
        self.root.after(0, self._log_message, message)

    def _log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def update_status(self, text, color):
        self.root.after(0, self._update_status, text, color)

    def _update_status(self, text, color):
        self.status_display.config(text=text, fg=color)

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Are you sure you want to close the agent?"):
            global observer
            if observer and observer.is_alive():
                observer.stop()
                observer.join()
            if sio.connected:
                sio.disconnect()
            self.root.destroy()


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = AgentApp(root)
    root.mainloop()
