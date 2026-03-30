// static/js/folder_monitor.js
// Folder Monitoring Component for Local Application

export class FolderMonitor {
    constructor(socketManager, prefix = '') {
        this.socketManager = socketManager;
        this.prefix = prefix;
        this.monitorMode = prefix || 'default';
        this.isMonitoring = false;
        this.currentPath = '';
        this.monitoredFiles = []; // Track files in monitored folder
        this.setupUI();
        this.setupSocketListeners();
    }

    setupUI() {
        const startBtnId = this.prefix ? `${this.prefix}StartMonitorBtn` : 'startMonitorBtn';
        const stopBtnId = this.prefix ? `${this.prefix}StopMonitorBtn` : 'stopMonitorBtn';
        const pathInputId = this.prefix ? `${this.prefix}FolderPathInput` : 'folderPathInput';

        const startBtn = document.getElementById(startBtnId);
        const stopBtn = document.getElementById(stopBtnId);
        const pathInput = document.getElementById(pathInputId);

        if (!startBtn || !stopBtn || !pathInput) {
            console.warn(`Folder monitor UI elements not found for prefix: ${this.prefix || 'default'}`);
            return;
        }

        // Allow manual path input
        pathInput.addEventListener('input', (e) => {
            this.currentPath = e.target.value.trim();
        });

        // Start monitoring button
        startBtn.addEventListener('click', () => {
            const folderPath = pathInput.value.trim();

            if (!folderPath) {
                alert('Please enter a folder path first');
                pathInput.focus();
                return;
            }

            this.currentPath = folderPath;

            // Get current analysis filters
            const filters = this.getCurrentFilters();

            this.socketManager.emit('start_folder_monitoring', {
                folder_path: this.currentPath,
                filters: filters,
                mode: this.monitorMode
            });

            this.updateStatus('Starting monitoring...', 'blue');
        });

        // Stop monitoring button
        stopBtn.addEventListener('click', () => {
            this.socketManager.emit('stop_folder_monitoring', { mode: this.monitorMode });
            this.updateStatus('Stopping monitoring...', 'gray');
        });
    }

    setupSocketListeners() {
        const startBtnId = this.prefix ? `${this.prefix}StartMonitorBtn` : 'startMonitorBtn';
        const stopBtnId = this.prefix ? `${this.prefix}StopMonitorBtn` : 'stopMonitorBtn';

        this.socketManager.on('folder_monitor_started', (data) => {
            if (!this._isRelevantEvent(data)) return;
            console.log('Folder monitoring started:', data);
            this.isMonitoring = true;
            this.monitoredFiles = [];

            const startBtn = document.getElementById(startBtnId);
            const stopBtn = document.getElementById(stopBtnId);

            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;

            this.updateStatus(`Monitoring: ${data.folder_path}`, 'green');
        });

        this.socketManager.on('folder_monitor_stopped', (data = {}) => {
            if (!this._isRelevantEvent(data)) return;
            console.log('Folder monitoring stopped');
            this.isMonitoring = false;
            this.monitoredFiles = [];

            const startBtn = document.getElementById(startBtnId);
            const stopBtn = document.getElementById(stopBtnId);

            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;

            this.updateStatus('Monitoring stopped', 'gray');
            this.updateFilesList();
        });

        this.socketManager.on('folder_monitor_error', (data) => {
            if (!this._isRelevantEvent(data)) return;
            console.error('Folder monitor error:', data.message);
            this.isMonitoring = false;

            const startBtn = document.getElementById(startBtnId);
            const stopBtn = document.getElementById(stopBtnId);

            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;

            this.updateStatus(`Error: ${data.message}`, 'red');
            alert(`Monitoring Error: ${data.message}`);
        });

        this.socketManager.on('file_monitor_error', (data) => {
            if (!this._isRelevantEvent(data)) return;
            console.error('File processing error:', data);
            this.updateStatus(`File error: ${data.filename}`, 'orange');
        });

        // Listen for file list updates
        this.socketManager.on('folder_files_list', (data) => {
            if (!this._isRelevantEvent(data)) return;
            console.log('Received folder files list:', data);
            if (data.files && Array.isArray(data.files)) {
                this.monitoredFiles = data.files;
                this.updateFilesList();
            }
        });

        // Listen for new file detected
        this.socketManager.on('new_file_detected', (data) => {
            if (!this._isRelevantEvent(data)) return;
            console.log('New file detected:', data.filename);
            if (data.filename && !this.monitoredFiles.includes(data.filename)) {
                this.monitoredFiles.push(data.filename);
                this.updateFilesList();
            }
        });
    }

    getCurrentFilters() {
        const filters = {
            handle: '',
            frequency: '',
            fileExtension: '.txt'
        };

        const fieldIds = this._getFieldIds();
        const fileHandleInput = document.getElementById(fieldIds.fileHandle);
        if (fileHandleInput) {
            filters.handle = (fileHandleInput.value || '').trim();
            console.log('[FOLDER MONITOR] File handle from input:', filters.handle);
        }

        const frequencyInput = fieldIds.frequency ? document.getElementById(fieldIds.frequency) : null;
        if (frequencyInput) {
            filters.frequency = frequencyInput.value || '';
            console.log('[FOLDER MONITOR] Frequency from input:', filters.frequency);
        }

        const fileExtensionSelect = document.getElementById(fieldIds.fileExtension);
        if (fileExtensionSelect) {
            filters.fileExtension = fileExtensionSelect.value || '.txt';
        }

        // Get current analysis parameters
        // This is a simplified version - actual implementation would need to get
        // the full analysis params from the active module
        const analysisParams = this.getAnalysisParamsFromUI();
        if (analysisParams) {
            filters.analysisParams = analysisParams;
        }

        console.log('[FOLDER MONITOR] Final filters being sent:', filters);
        return filters;
    }

    _getFieldIds() {
        if (this.prefix === 'cv') {
            return {
                fileHandle: 'cvFileHandleInput',
                frequency: null,
                fileExtension: 'cvFileExtensionInput'
            };
        }

        return {
            fileHandle: 'fileHandleInput',
            frequency: 'frequencyInput',
            fileExtension: 'fileExtensionInput'
        };
    }

    _isRelevantEvent(data = {}) {
        const eventMode = data.mode || data.monitor_mode;
        return !eventMode || eventMode === this.monitorMode;
    }

    getAnalysisParamsFromUI() {
        // This is a placeholder - actual implementation would collect
        // all analysis parameters from the current screen
        // For now, return null and let the stream_instrument_data handler
        // use the stored params from start_analysis_session
        return null;
    }

    updateStatus(message, color) {
        const statusId = this.prefix ? `${this.prefix}MonitorStatus` : 'monitorStatus';
        const statusElement = document.getElementById(statusId);
        if (!statusElement) return;

        statusElement.textContent = message;

        // Set color based on status
        const colorClasses = {
            'green': 'text-green-600',
            'red': 'text-red-600',
            'blue': 'text-blue-600',
            'orange': 'text-orange-600',
            'gray': 'text-gray-500'
        };

        statusElement.className = `text-sm ${colorClasses[color] || 'text-gray-500'}`;
    }

    updateFilesList() {
        const listId = this.prefix ? `${this.prefix}MonitorFilesList` : 'monitorFilesList';
        const containerId = this.prefix ? `${this.prefix}MonitorFilesContainer` : 'monitorFilesContainer';

        const listElement = document.getElementById(listId);
        const containerElement = document.getElementById(containerId);

        if (!listElement || !containerElement) return;

        if (this.monitoredFiles.length === 0) {
            listElement.classList.add('hidden');
            return;
        }

        listElement.classList.remove('hidden');

        // Build file list HTML
        const filesHTML = this.monitoredFiles.map((filename, index) => `
            <div class="py-1 px-2 hover:bg-gray-50 text-xs text-gray-700">
                ${index + 1}. ${filename}
            </div>
        `).join('');

        containerElement.innerHTML = filesHTML || '<p class="text-xs text-gray-500 p-2">No files found</p>';
    }
}
