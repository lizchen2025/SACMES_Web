// static/js/diagnostics_panel.js
// Diagnostic and Troubleshooting Panel Component

export class DiagnosticsPanel {
    constructor(socketManager) {
        this.socketManager = socketManager;
        this.isVisible = false;
        this.setupUI();
        this.setupSocketListeners();
    }

    setupUI() {
        // Create diagnostics panel button in the UI
        const navButtons = document.querySelector('.flex.gap-4.mb-4');
        const diagButton = document.createElement('button');
        diagButton.id = 'showDiagnosticsBtn';
        diagButton.textContent = 'Diagnostics';
        diagButton.className = navButtons
            ? 'bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded transition duration-200'
            : 'fixed bottom-4 right-4 bg-gray-700 hover:bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-40 transition duration-200';

        if (navButtons) {
            navButtons.appendChild(diagButton);
        } else {
            document.body.appendChild(diagButton);
        }

        diagButton.addEventListener('click', () => {
            this.togglePanel();
        });

        // Create the diagnostics panel (initially hidden)
        this.createPanel();
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'diagnosticsPanel';
        panel.className = 'hidden fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
        panel.innerHTML = `
            <div class="bg-white rounded-lg shadow-2xl w-11/12 max-w-4xl max-h-screen overflow-auto">
                <div class="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
                    <h2 class="text-xl font-bold">System Diagnostics & Troubleshooting</h2>
                    <button id="closeDiagnosticsBtn" class="text-white hover:text-gray-200 text-2xl">&times;</button>
                </div>

                <div class="p-6">
                    <!-- Connection Status -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Connection Status</h3>
                        <div id="connectionStatusInfo" class="bg-gray-100 p-3 rounded text-sm">
                            <p><strong>Socket Connection:</strong> <span id="socketStatus" class="text-gray-600">Checking...</span></p>
                        </div>
                    </div>

                    <!-- Quick Diagnostics -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Run Diagnostics</h3>
                        <div class="flex gap-2 mb-3">
                            <input type="text" id="diagFolderPath" placeholder="Folder path to test (optional)"
                                   class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"/>
                            <button id="runDiagnosticsBtn" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded text-sm font-semibold">
                                Run Diagnostics
                            </button>
                        </div>
                        <div id="diagnosticsResults" class="bg-gray-100 p-3 rounded text-sm max-h-64 overflow-auto hidden"></div>
                    </div>

                    <!-- Test File Read -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Test File Reading</h3>
                        <div class="flex gap-2 mb-3">
                            <input type="text" id="testFilePath" placeholder="Folder path"
                                   class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"/>
                            <input type="text" id="testFileName" placeholder="Filename (e.g., SWV_15Hz.txt)"
                                   class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"/>
                            <button id="testFileReadBtn" class="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded text-sm font-semibold">
                                Test Read
                            </button>
                        </div>
                        <div id="fileReadResults" class="bg-gray-100 p-3 rounded text-sm max-h-64 overflow-auto hidden"></div>
                    </div>

                    <!-- Manual File Processing -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Manual File Processing</h3>
                        <p class="text-sm text-gray-600 mb-2">Note: Start an analysis session first before processing files</p>
                        <div class="flex gap-2 mb-3">
                            <input type="text" id="processFilePath" placeholder="Folder path"
                                   class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"/>
                            <input type="text" id="processFileName" placeholder="Filename"
                                   class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"/>
                            <select id="processAnalysisType" class="px-3 py-2 border border-gray-300 rounded text-sm">
                                <option value="swv">SWV</option>
                                <option value="cv">CV</option>
                            </select>
                            <button id="manualProcessBtn" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded text-sm font-semibold">
                                Process
                            </button>
                        </div>
                        <div id="processResults" class="bg-gray-100 p-3 rounded text-sm max-h-64 overflow-auto hidden"></div>
                    </div>

                    <!-- Log View -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Recent Activity Log</h3>
                        <div id="activityLog" class="bg-gray-900 text-green-400 p-3 rounded text-xs font-mono max-h-64 overflow-auto">
                            <p>Waiting for events...</p>
                        </div>
                    </div>

                    <!-- Common Issues -->
                    <div class="mb-6">
                        <h3 class="text-lg font-bold mb-2">Common Issues & Solutions</h3>
                        <div class="text-sm space-y-2">
                            <details class="bg-gray-100 p-3 rounded">
                                <summary class="font-semibold cursor-pointer">Files not being detected</summary>
                                <ul class="mt-2 ml-4 list-disc space-y-1 text-gray-700">
                                    <li>Check that the folder path is correct and accessible</li>
                                    <li>Ensure files have the correct extensions (.txt, .dta, .csv)</li>
                                    <li>Verify filename contains frequency (e.g., _15Hz, _200Hz)</li>
                                    <li>Check that monitoring is started (Status should show "Monitoring: path")</li>
                                    <li>Look at the Activity Log above for error messages</li>
                                </ul>
                            </details>
                            <details class="bg-gray-100 p-3 rounded">
                                <summary class="font-semibold cursor-pointer">Analysis not running</summary>
                                <ul class="mt-2 ml-4 list-disc space-y-1 text-gray-700">
                                    <li>Make sure you started an analysis session (clicked "Start Analysis")</li>
                                    <li>Verify analysis parameters are set correctly</li>
                                    <li>Check that file contains valid data in expected format</li>
                                    <li>Use "Manual File Processing" above to test specific file</li>
                                </ul>
                            </details>
                            <details class="bg-gray-100 p-3 rounded">
                                <summary class="font-semibold cursor-pointer">Frequency scan not working</summary>
                                <ul class="mt-2 ml-4 list-disc space-y-1 text-gray-700">
                                    <li>Ensure folder path is entered before clicking "Scan Folder"</li>
                                    <li>Filename must contain frequency with "Hz" (case insensitive)</li>
                                    <li>Examples: SWV_15Hz.txt, data_200hz.dta, test-1000Hz.csv</li>
                                    <li>File handle (prefix) is optional but helps filter files</li>
                                </ul>
                            </details>
                            <details class="bg-gray-100 p-3 rounded">
                                <summary class="font-semibold cursor-pointer">Permission errors</summary>
                                <ul class="mt-2 ml-4 list-disc space-y-1 text-gray-700">
                                    <li>Ensure the application has read access to the folder</li>
                                    <li>Try running the application with appropriate permissions</li>
                                    <li>Check that files are not locked by another program</li>
                                </ul>
                            </details>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Setup event listeners
        document.getElementById('closeDiagnosticsBtn').addEventListener('click', () => {
            this.hidePanel();
        });

        document.getElementById('runDiagnosticsBtn').addEventListener('click', () => {
            this.runDiagnostics();
        });

        document.getElementById('testFileReadBtn').addEventListener('click', () => {
            this.testFileRead();
        });

        document.getElementById('manualProcessBtn').addEventListener('click', () => {
            this.manualProcessFile();
        });

        // Close panel when clicking outside
        panel.addEventListener('click', (e) => {
            if (e.target.id === 'diagnosticsPanel') {
                this.hidePanel();
            }
        });
    }

    setupSocketListeners() {
        // Update connection status
        this.socketManager.on('connect', () => {
            this.updateConnectionStatus('Connected', 'green');
            this.log('Socket connection established');
        });

        this.socketManager.on('disconnect', () => {
            this.updateConnectionStatus('Disconnected', 'red');
            this.log('Socket disconnected');
        });

        this.socketManager.on('connection_status', (data) => {
            this.log(`Connection status: ${JSON.stringify(data)}`);
        });

        // Listen to diagnostic responses
        this.socketManager.on('diagnostics_response', (data) => {
            this.displayDiagnostics(data);
        });

        this.socketManager.on('file_read_test_response', (data) => {
            this.displayFileReadResults(data);
        });

        this.socketManager.on('manual_process_response', (data) => {
            this.displayProcessResults(data);
        });

        // Log all folder monitoring events
        this.socketManager.on('folder_monitor_started', (data) => {
            this.log(`Monitoring started: ${data.folder_path}`);
        });

        this.socketManager.on('folder_monitor_stopped', () => {
            this.log('Monitoring stopped');
        });

        this.socketManager.on('folder_monitor_error', (data) => {
            this.log(`ERROR: ${data.message}`, 'error');
        });

        this.socketManager.on('file_monitor_error', (data) => {
            this.log(`File error: ${data.filename} - ${data.error}`, 'error');
        });

        this.socketManager.on('new_file_detected', (data) => {
            this.log(`New file detected: ${data.filename}`);
        });

        this.socketManager.on('folder_files_list', (data) => {
            this.log(`Files list received: ${data.files.length} files`);
        });
    }

    togglePanel() {
        if (this.isVisible) {
            this.hidePanel();
        } else {
            this.showPanel();
        }
    }

    showPanel() {
        document.getElementById('diagnosticsPanel').classList.remove('hidden');
        this.isVisible = true;
        this.updateConnectionStatus(
            this.socketManager.socket.connected ? 'Connected' : 'Disconnected',
            this.socketManager.socket.connected ? 'green' : 'red'
        );
    }

    hidePanel() {
        document.getElementById('diagnosticsPanel').classList.add('hidden');
        this.isVisible = false;
    }

    updateConnectionStatus(status, color) {
        const statusEl = document.getElementById('socketStatus');
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = color === 'green' ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold';
        }
    }

    runDiagnostics() {
        const folderPath = document.getElementById('diagFolderPath').value.trim();
        const btn = document.getElementById('runDiagnosticsBtn');

        btn.textContent = 'Running...';
        btn.disabled = true;

        this.log('Running diagnostics...');
        this.socketManager.emit('run_diagnostics', {
            folder_path: folderPath || undefined
        });
    }

    testFileRead() {
        const folderPath = document.getElementById('testFilePath').value.trim();
        const filename = document.getElementById('testFileName').value.trim();

        if (!folderPath || !filename) {
            alert('Please enter both folder path and filename');
            return;
        }

        const btn = document.getElementById('testFileReadBtn');
        btn.textContent = 'Testing...';
        btn.disabled = true;

        this.log(`Testing file read: ${folderPath}/${filename}`);
        this.socketManager.emit('test_file_read', {
            folder_path: folderPath,
            filename: filename
        });
    }

    manualProcessFile() {
        const folderPath = document.getElementById('processFilePath').value.trim();
        const filename = document.getElementById('processFileName').value.trim();
        const analysisType = document.getElementById('processAnalysisType').value;

        if (!folderPath || !filename) {
            alert('Please enter both folder path and filename');
            return;
        }

        const btn = document.getElementById('manualProcessBtn');
        btn.textContent = 'Processing...';
        btn.disabled = true;

        this.log(`Manual processing: ${folderPath}/${filename} (${analysisType})`);
        this.socketManager.emit('manual_process_file', {
            folder_path: folderPath,
            filename: filename,
            analysis_type: analysisType
        });
    }

    displayDiagnostics(data) {
        const resultsDiv = document.getElementById('diagnosticsResults');
        const btn = document.getElementById('runDiagnosticsBtn');

        btn.textContent = 'Run Diagnostics';
        btn.disabled = false;

        if (data.status === 'success') {
            const diag = data.diagnostics;
            let html = '<div class="space-y-2">';

            // System info
            html += '<div><strong>System:</strong></div>';
            html += `<div class="ml-4 text-xs">Platform: ${diag.system.platform}</div>`;
            html += `<div class="ml-4 text-xs">Working Dir: ${diag.system.cwd}</div>`;

            // Analyzers
            html += '<div class="mt-2"><strong>Analyzers:</strong></div>';
            html += `<div class="ml-4 text-xs">SWV Analyzer: ${diag.analyzers.swv_analyzer_loaded ? '[OK] Loaded' : '[X] Not Loaded'}</div>`;
            html += `<div class="ml-4 text-xs">CV Analyzer: ${diag.analyzers.cv_analyzer_loaded ? '[OK] Loaded' : '[X] Not Loaded'}</div>`;

            // Folder monitoring
            html += '<div class="mt-2"><strong>Folder Monitoring:</strong></div>';
            html += `<div class="ml-4 text-xs">Observer Active: ${diag.folder_monitoring.observer_active ? 'Yes' : 'No'}</div>`;
            html += `<div class="ml-4 text-xs">Monitor Active: ${diag.folder_monitoring.monitor_active ? 'Yes' : 'No'}</div>`;
            if (diag.folder_monitoring.processed_files_count !== undefined) {
                html += `<div class="ml-4 text-xs">Processed Files: ${diag.folder_monitoring.processed_files_count}</div>`;
            }

            // File access
            if (diag.file_access.test_path) {
                html += '<div class="mt-2"><strong>File Access Test:</strong></div>';
                html += `<div class="ml-4 text-xs">Path: ${diag.file_access.test_path}</div>`;
                html += `<div class="ml-4 text-xs">Exists: ${diag.file_access.path_exists ? 'Yes' : 'No'}</div>`;
                html += `<div class="ml-4 text-xs">Is Directory: ${diag.file_access.is_directory ? 'Yes' : 'No'}</div>`;

                if (diag.file_access.can_read_directory !== undefined) {
                    html += `<div class="ml-4 text-xs">Can Read Directory: ${diag.file_access.can_read_directory ? 'Yes' : 'No'}</div>`;
                }

                if (diag.file_access.file_count !== undefined) {
                    html += `<div class="ml-4 text-xs">Total Files: ${diag.file_access.file_count}</div>`;
                }

                if (diag.file_access.can_read_files !== undefined) {
                    html += `<div class="ml-4 text-xs">Can Read Files: ${diag.file_access.can_read_files ? 'Yes' : 'No'}</div>`;
                }

                if (diag.file_access.test_file) {
                    html += `<div class="ml-4 text-xs">Test File: ${diag.file_access.test_file} (${diag.file_access.test_file_size} bytes)</div>`;
                }
            }

            html += '</div>';
            resultsDiv.innerHTML = html;
            resultsDiv.classList.remove('hidden');

            this.log('Diagnostics completed successfully');
        } else {
            resultsDiv.innerHTML = `<div class="text-red-600">Error: ${data.message}</div>`;
            resultsDiv.classList.remove('hidden');
            this.log('Diagnostics failed', 'error');
        }
    }

    displayFileReadResults(data) {
        const resultsDiv = document.getElementById('fileReadResults');
        const btn = document.getElementById('testFileReadBtn');

        btn.textContent = 'Test Read';
        btn.disabled = false;

        if (data.status === 'success') {
            const result = data.result;
            let html = '<div class="space-y-1">';
            html += `<div><strong>File:</strong> ${result.filename}</div>`;
            html += `<div>Exists: ${result.exists ? 'Yes' : 'No'}</div>`;
            html += `<div>Is File: ${result.is_file ? 'Yes' : 'No'}</div>`;
            html += `<div>Readable: ${result.readable ? 'Yes' : 'No'}</div>`;
            html += `<div>Size: ${result.file_size} bytes</div>`;
            html += `<div>Lines: ${result.line_count}</div>`;
            html += `<div>Safety Check: ${result.safety_check ? '[OK] Passed' : '[X] Failed'}</div>`;
            if (result.safety_error) {
                html += `<div class="text-red-600">Safety Error: ${result.safety_error}</div>`;
            }
            html += `<div>Frequency Detected: ${result.frequency_detected || 'None'}</div>`;
            html += `<div class="mt-2"><strong>First 100 chars:</strong></div>`;
            html += `<div class="bg-white p-2 rounded text-xs font-mono">${result.first_100_chars}</div>`;
            html += '</div>';
            resultsDiv.innerHTML = html;
            this.log(`File read test successful: ${result.filename}`);
        } else {
            const result = data.result || {};
            let html = '<div class="text-red-600">';
            html += `<div><strong>Error:</strong> ${data.message || 'Unknown error'}</div>`;
            if (result.error) {
                html += `<div class="mt-2 text-xs">${result.error}</div>`;
            }
            html += '</div>';
            resultsDiv.innerHTML = html;
            this.log('File read test failed', 'error');
        }

        resultsDiv.classList.remove('hidden');
    }

    displayProcessResults(data) {
        const resultsDiv = document.getElementById('processResults');
        const btn = document.getElementById('manualProcessBtn');

        btn.textContent = 'Process';
        btn.disabled = false;

        if (data.status === 'success') {
            resultsDiv.innerHTML = `<div class="text-green-600">${data.message}</div>`;
            this.log(`Manual processing successful: ${data.message}`);
        } else {
            resultsDiv.innerHTML = `<div class="text-red-600">Error: ${data.message}</div>`;
            this.log(`Manual processing failed: ${data.message}`, 'error');
        }

        resultsDiv.classList.remove('hidden');
    }

    log(message, type = 'info') {
        const logDiv = document.getElementById('activityLog');
        if (!logDiv) return;

        const timestamp = new Date().toLocaleTimeString();
        const colorClass = type === 'error' ? 'text-red-400' : 'text-green-400';
        const prefix = type === 'error' ? '[ERROR]' : '[INFO]';

        const logEntry = document.createElement('div');
        logEntry.className = colorClass;
        logEntry.textContent = `[${timestamp}] ${prefix} ${message}`;

        // Remove "Waiting for events..." message if present
        const waitingMsg = logDiv.querySelector('p');
        if (waitingMsg && waitingMsg.textContent === 'Waiting for events...') {
            logDiv.innerHTML = '';
        }

        logDiv.appendChild(logEntry);

        // Auto-scroll to bottom
        logDiv.scrollTop = logDiv.scrollHeight;

        // Keep only last 50 entries
        while (logDiv.children.length > 50) {
            logDiv.removeChild(logDiv.firstChild);
        }
    }
}
