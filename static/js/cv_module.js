// static/js/cv_module.js - CV Analysis Module

import { PlotlyPlotter } from './plot_utils.js';

export class CVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        this.dom = {
            cvBtn: document.getElementById('cvBtn'),
            backToWelcomeBtn: document.getElementById('backToWelcomeFromCV'),
            backToCVSettingsBtn: document.getElementById('backToCVSettingsBtn'),
            nextToVisualizationBtn: document.getElementById('cvNextToVisualizationBtn'),
            startAnalysisBtn: document.getElementById('startCVAnalysisBtn'),
            agentStatus: document.getElementById('cvAgentStatus'),
            folderStatus: document.getElementById('cvFolderStatus'),
            detectSegmentsBtn: document.getElementById('detectCVSegmentsBtn'),
            segmentStatus: document.getElementById('cvSegmentStatus'),
            cvPreviewPlot: document.getElementById('cvPreviewPlot'),
            params: {
                fileHandleInput: document.getElementById('cvFileHandleInput'),
                numFilesInput: document.getElementById('cvNumFilesInput'),
                selectedElectrodesInput: document.getElementById('cvSelectedElectrodesInput'),
                scanRateInput: document.getElementById('cvScanRateInput'),
                lowVoltageInput: document.getElementById('cvLowVoltageInput'),
                highVoltageInput: document.getElementById('cvHighVoltageInput'),
                massTransportInput: document.getElementById('cvMassTransportInput'),
                analysisOptionsInput: document.getElementById('cvAnalysisOptionsInput'),
            },
            visualization: {
                forwardSegmentInput: document.getElementById('cvForwardSegmentInput'),
                reverseSegmentInput: document.getElementById('cvReverseSegmentInput'),
            },
            settings: {
                voltageColumnInput: document.getElementById('cvVoltageColumnInput'),
                currentColumnInput: document.getElementById('cvCurrentColumnInput'),
                spacingIndexInput: document.getElementById('cvSpacingIndexInput'),
                delimiterInput: document.getElementById('cvDelimiterInput'),
                fileExtensionInput: document.getElementById('cvFileExtensionInput'),
                byteLimitInput: document.getElementById('cvByteLimitInput'),
                sampleRateInput: document.getElementById('cvSampleRateInput'),
                analysisIntervalInput: document.getElementById('cvAnalysisIntervalInput'),
                resizeIntervalInput: document.getElementById('cvResizeIntervalInput'),
            }
        };

        this.state = {
            isAnalysisRunning: false,
            currentNumFiles: 0,
            selectedElectrodes: [],
            currentElectrode: null,
            cvResults: {},
            previewFileContent: null,
            availableSegments: [],
            currentScreen: 'settings' // 'settings', 'visualization', 'analysis'
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
    }

    _setupEventListeners() {
        this.dom.cvBtn.addEventListener('click', () => {
            this.state.currentScreen = 'settings';
            this.uiManager.showScreen('cvAnalysisScreen');
        });

        this.dom.backToWelcomeBtn.addEventListener('click', () => {
            this.uiManager.showScreen('welcomeScreen');
            this._resetAnalysis();
        });

        this.dom.backToCVSettingsBtn.addEventListener('click', () => {
            this.state.currentScreen = 'settings';
            this.uiManager.showScreen('cvAnalysisScreen');
        });

        this.dom.nextToVisualizationBtn.addEventListener('click', this._handleNextToVisualization.bind(this));
        this.dom.startAnalysisBtn.addEventListener('click', this._handleStartAnalysis.bind(this));
        this.dom.detectSegmentsBtn.addEventListener('click', this._handleDetectSegments.bind(this));
    }

    _setupSocketHandlers() {
        this.socketManager.on('connect', () => this.socketManager.emit('request_agent_status', {}));

        this.socketManager.on('agent_status', (data) => {
            this.dom.agentStatus.className = data.status === 'connected' ? 'text-sm text-green-700 mt-1' : 'text-sm text-red-700 mt-1';
            this.dom.agentStatus.textContent = data.status === 'connected' ? 'Local agent connected. Ready to sync.' : 'Error: Local agent is disconnected.';
        });

        this.socketManager.on('ack_start_cv_session', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'CV Instructions sent. Agent is now scanning...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this._resetAnalysisState();
            }
        });

        this.socketManager.on('cv_preview_response', (data) => {
            if (data.status === 'success') {
                this.state.previewFileContent = data.content;
                this._displayCVPreview(data.cv_data);
                this.dom.segmentStatus.textContent = 'CV preview loaded. Click "Detect Segments" to analyze.';
                this.dom.segmentStatus.className = 'text-sm text-green-600 mt-2';
            } else {
                this.dom.segmentStatus.textContent = `Error loading preview: ${data.message}`;
                this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
            }
        });

        this.socketManager.on('cv_segments_response', (data) => {
            if (data.status === 'success') {
                this.state.availableSegments = data.segments;
                this._updateSegmentDropdowns();
                this.dom.segmentStatus.textContent = `Found ${data.segments.length} scan segments: ${data.segments.join(', ')}`;
                this.dom.segmentStatus.className = 'text-sm text-green-600 mt-2';
            } else {
                this.dom.segmentStatus.textContent = `Error: ${data.message}`;
                this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
            }
        });

        this.socketManager.on('electrode_validation_error', (data) => {
            // Only show alert if analysis is still running (prevent duplicate alerts)
            if (this.state.isAnalysisRunning) {
                alert(data.message);
                // Reset analysis state
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.segmentStatus.textContent = 'Please correct electrode selection and try again.';

                // Notify server to stop the analysis session
                this.socketManager.emit('stop_cv_analysis_session', { reason: 'electrode_validation_failed' });
            }
        });

        this.socketManager.on('live_cv_update', (data) => {
            if (!this.state.isAnalysisRunning) return;

            // Store CV results per electrode
            if (data.cv_analysis && data.electrode_index !== undefined) {
                const electrodeKey = data.electrode_index !== null ? data.electrode_index.toString() : 'averaged';

                if (!this.state.cvResults[electrodeKey]) {
                    this.state.cvResults[electrodeKey] = {};
                }

                // Extract file number from filename
                const match = data.filename.match(/_(\d+)\./);
                if (match) {
                    const fileNum = match[1];
                    this.state.cvResults[electrodeKey][fileNum] = data.cv_analysis;
                }

                // Update visualization if this is the current electrode
                if (data.electrode_index === this.state.currentElectrode) {
                    this._updateCVVisualization(data.cv_analysis);
                }
            }
        });
    }

    _handleNextToVisualization() {
        // Validate basic parameters first
        const numFiles = parseInt(this.dom.params.numFilesInput.value);
        if (isNaN(numFiles) || numFiles < 1) {
            alert("Please enter a valid number of files.");
            return;
        }

        this.state.currentScreen = 'visualization';
        this.uiManager.showScreen('cvVisualizationScreen');

        // Request a preview file from the agent
        this._requestPreviewFile();
    }

    _requestPreviewFile() {
        const analysisParams = this._collectAnalysisParams();
        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: 1 // Just get the first file for preview
        };

        this.dom.segmentStatus.textContent = 'Loading CV preview...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';

        // Request the first file for preview
        this.socketManager.emit('get_cv_preview', { filters, analysisParams });
    }

    _handleDetectSegments() {
        if (!this.state.previewFileContent) {
            this._requestPreviewFile();
            return;
        }

        const analysisParams = this._collectAnalysisParams();

        this.socketManager.emit('get_cv_segments', {
            content: this.state.previewFileContent,
            filename: 'preview_file',
            params: analysisParams
        });

        this.dom.segmentStatus.textContent = 'Detecting segments...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
    }

    _updateSegmentDropdowns() {
        // Clear existing options
        this.dom.visualization.forwardSegmentInput.innerHTML = '<option value="">Auto-detect</option>';
        this.dom.visualization.reverseSegmentInput.innerHTML = '<option value="">Auto-detect</option>';

        // Add detected segments
        this.state.availableSegments.forEach(segment => {
            const option1 = new Option(`Segment ${segment}`, segment);
            const option2 = new Option(`Segment ${segment}`, segment);
            this.dom.visualization.forwardSegmentInput.add(option1);
            this.dom.visualization.reverseSegmentInput.add(option2);
        });

        // Auto-select typical forward and reverse segments if available
        if (this.state.availableSegments.length >= 2) {
            this.dom.visualization.forwardSegmentInput.value = this.state.availableSegments[0];
            this.dom.visualization.reverseSegmentInput.value = this.state.availableSegments[1];
        }
    }

    _collectAnalysisParams() {
        return {
            num_files: parseInt(this.dom.params.numFilesInput.value),
            num_electrodes: this._autoDetectNumElectrodes(),
            scan_rate: parseFloat(this.dom.params.scanRateInput.value),
            forward_segment: parseInt(this.dom.visualization.forwardSegmentInput.value) || null,
            reverse_segment: parseInt(this.dom.visualization.reverseSegmentInput.value) || null,
            low_voltage: parseFloat(this.dom.params.lowVoltageInput.value),
            high_voltage: parseFloat(this.dom.params.highVoltageInput.value),
            mass_transport: this.dom.params.massTransportInput.value,
            SelectedOptions: this.dom.params.analysisOptionsInput.value,
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value),
            current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value),
            delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value,
            byte_limit: parseInt(this.dom.settings.byteLimitInput.value),
            sample_rate: parseFloat(this.dom.settings.sampleRateInput.value),
            analysis_interval: parseInt(this.dom.settings.analysisIntervalInput.value),
            resize_interval: parseInt(this.dom.settings.resizeIntervalInput.value),
        };
    }

    _handleStartAnalysis() {
        const numFiles = parseInt(this.dom.params.numFilesInput.value);
        if (isNaN(numFiles) || numFiles < 1) {
            alert("Please enter a valid number of files.");
            return;
        }

        // Parse selected electrodes (convert from 1-based to 0-based)
        const selectedElectrodesStr = this.dom.params.selectedElectrodesInput.value.trim();
        let selectedElectrodes = [];
        if (selectedElectrodesStr) {
            selectedElectrodes = selectedElectrodesStr.split(',')
                .map(e => parseInt(e.trim()) - 1)  // Convert from 1-based to 0-based
                .filter(e => !isNaN(e) && e >= 0);
            if (selectedElectrodes.length === 0) {
                alert("Please enter valid electrode numbers (starting from 1) or leave empty for averaging.");
                return;
            }
        }

        this.state = {
            isAnalysisRunning: true,
            currentNumFiles: numFiles,
            selectedElectrodes: selectedElectrodes,
            currentElectrode: selectedElectrodes.length > 0 ? selectedElectrodes[0] : null,
            cvResults: {},
            uploadedFileContent: this.state.uploadedFileContent,
            availableSegments: this.state.availableSegments
        };

        const analysisParams = this._collectAnalysisParams();
        analysisParams.selected_electrode = this.state.currentElectrode;
        analysisParams.selected_electrodes = this.state.selectedElectrodes;

        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: numFiles
        };

        this.dom.startAnalysisBtn.textContent = 'CV Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending CV instructions to server...";

        this.socketManager.emit('start_cv_analysis_session', { filters, analysisParams });
    }

    _updateCVVisualization(analysisResult) {
        // This would update CV-specific plots
        // For now, just log the results
        console.log('CV Analysis Result:', analysisResult);

        // TODO: Implement CV-specific visualization
        // - Forward sweep plot
        // - Reverse sweep plot
        // - Peak separation display
        // - Charge/AUC display
    }

    _displayCVPreview(cvData) {
        // Use PlotlyPlotter to display CV preview
        if (cvData && cvData.voltage && cvData.current) {
            const plotData = [{
                x: cvData.voltage,
                y: cvData.current,
                type: 'scatter',
                mode: 'lines',
                name: 'CV Preview',
                line: { color: '#1f77b4', width: 2 }
            }];

            const layout = {
                title: 'CV Preview - Select Segments',
                xaxis: { title: 'Voltage (V)' },
                yaxis: { title: 'Current (A)' },
                margin: { t: 50, r: 50, b: 50, l: 80 },
                showlegend: false
            };

            Plotly.newPlot(this.dom.cvPreviewPlot, plotData, layout, { responsive: true });
        }
    }

    _resetAnalysis() {
        this.state.isAnalysisRunning = false;
        this.state.cvResults = {};
        this.state.previewFileContent = null;
        this.state.availableSegments = [];
        this.state.currentScreen = 'settings';
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;
    }

    _resetAnalysisState() {
        this.state.isAnalysisRunning = false;
        this.dom.startAnalysisBtn.disabled = false;
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
    }

    _autoDetectNumElectrodes() {
        // Parse selected electrodes to determine max electrode number needed
        const selectedElectrodesStr = this.dom.params.selectedElectrodesInput.value.trim();
        if (selectedElectrodesStr) {
            const selectedElectrodes = selectedElectrodesStr.split(',')
                .map(e => parseInt(e.trim()))
                .filter(e => !isNaN(e) && e >= 1);

            if (selectedElectrodes.length > 0) {
                // Return the maximum electrode number (they're 1-based in input)
                return Math.max(...selectedElectrodes);
            }
        }

        // Default to 1 electrode if no selection or invalid input
        return 1;
    }

    _validateElectrodeCount(detectedElectrodes, requestedElectrodes) {
        // This function will be called from backend response to validate
        if (requestedElectrodes.some(e => e > detectedElectrodes)) {
            const maxRequested = Math.max(...requestedElectrodes);
            alert(`错误：文件中只检测到 ${detectedElectrodes} 个电极，但您请求了第 ${maxRequested} 号电极。请检查您的电极选择或文件格式设置。`);
            return false;
        }
        return true;
    }
}