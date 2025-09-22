// static/js/cv_module.js - CV Analysis Module

import { PlotlyPlotter } from './plot_utils.js';

export class CVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        this.dom = {
            cvBtn: document.getElementById('cvBtn'),
            backToWelcomeBtn: document.getElementById('backToWelcomeFromCV'),
            startAnalysisBtn: document.getElementById('startCVAnalysisBtn'),
            agentStatus: document.getElementById('cvAgentStatus'),
            folderStatus: document.getElementById('cvFolderStatus'),
            fileUpload: document.getElementById('cvFileUpload'),
            detectSegmentsBtn: document.getElementById('detectCVSegmentsBtn'),
            segmentStatus: document.getElementById('cvSegmentStatus'),
            params: {
                fileHandleInput: document.getElementById('cvFileHandleInput'),
                numFilesInput: document.getElementById('cvNumFilesInput'),
                numElectrodesInput: document.getElementById('cvNumElectrodesInput'),
                selectedElectrodesInput: document.getElementById('cvSelectedElectrodesInput'),
                scanRateInput: document.getElementById('cvScanRateInput'),
                forwardSegmentInput: document.getElementById('cvForwardSegmentInput'),
                reverseSegmentInput: document.getElementById('cvReverseSegmentInput'),
                lowVoltageInput: document.getElementById('cvLowVoltageInput'),
                highVoltageInput: document.getElementById('cvHighVoltageInput'),
                massTransportInput: document.getElementById('cvMassTransportInput'),
                analysisOptionsInput: document.getElementById('cvAnalysisOptionsInput'),
            },
            settings: {
                voltageColumnInput: document.getElementById('cvVoltageColumnInput'),
                currentColumnInput: document.getElementById('cvCurrentColumnInput'),
                spacingIndexInput: document.getElementById('cvSpacingIndexInput'),
                delimiterInput: document.getElementById('cvDelimiterInput'),
                fileExtensionInput: document.getElementById('cvFileExtensionInput'),
            }
        };

        this.state = {
            isAnalysisRunning: false,
            currentNumFiles: 0,
            selectedElectrodes: [],
            currentElectrode: null,
            cvResults: {},
            uploadedFileContent: null,
            availableSegments: []
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
    }

    _setupEventListeners() {
        this.dom.cvBtn.addEventListener('click', () => this.uiManager.showScreen('cvAnalysisScreen'));
        this.dom.backToWelcomeBtn.addEventListener('click', () => {
            this.uiManager.showScreen('welcomeScreen');
            this._resetAnalysis();
        });

        this.dom.startAnalysisBtn.addEventListener('click', this._handleStartAnalysis.bind(this));

        // File upload and segment detection
        this.dom.fileUpload.addEventListener('change', this._handleFileUpload.bind(this));
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

    _handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            this.state.uploadedFileContent = e.target.result;
            this.dom.detectSegmentsBtn.disabled = false;
            this.dom.segmentStatus.textContent = 'File loaded. Click "Detect Segments" to analyze.';
            this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
        };
        reader.readAsText(file);
    }

    _handleDetectSegments() {
        if (!this.state.uploadedFileContent) return;

        const analysisParams = this._collectAnalysisParams();

        this.socketManager.emit('get_cv_segments', {
            content: this.state.uploadedFileContent,
            filename: this.dom.fileUpload.files[0].name,
            params: analysisParams
        });

        this.dom.segmentStatus.textContent = 'Detecting segments...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
    }

    _updateSegmentDropdowns() {
        // Clear existing options
        this.dom.params.forwardSegmentInput.innerHTML = '<option value="">Auto-detect</option>';
        this.dom.params.reverseSegmentInput.innerHTML = '<option value="">Auto-detect</option>';

        // Add detected segments
        this.state.availableSegments.forEach(segment => {
            const option1 = new Option(`Segment ${segment}`, segment);
            const option2 = new Option(`Segment ${segment}`, segment);
            this.dom.params.forwardSegmentInput.add(option1);
            this.dom.params.reverseSegmentInput.add(option2);
        });

        // Auto-select typical forward and reverse segments if available
        if (this.state.availableSegments.length >= 2) {
            this.dom.params.forwardSegmentInput.value = this.state.availableSegments[0];
            this.dom.params.reverseSegmentInput.value = this.state.availableSegments[1];
        }
    }

    _collectAnalysisParams() {
        return {
            num_files: parseInt(this.dom.params.numFilesInput.value),
            num_electrodes: parseInt(this.dom.params.numElectrodesInput.value),
            scan_rate: parseFloat(this.dom.params.scanRateInput.value),
            forward_segment: parseInt(this.dom.params.forwardSegmentInput.value) || null,
            reverse_segment: parseInt(this.dom.params.reverseSegmentInput.value) || null,
            low_voltage: parseFloat(this.dom.params.lowVoltageInput.value),
            high_voltage: parseFloat(this.dom.params.highVoltageInput.value),
            mass_transport: this.dom.params.massTransportInput.value,
            SelectedOptions: this.dom.params.analysisOptionsInput.value,
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value),
            current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value),
            delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value,
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

    _resetAnalysis() {
        this.state.isAnalysisRunning = false;
        this.state.cvResults = {};
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;
    }

    _resetAnalysisState() {
        this.state.isAnalysisRunning = false;
        this.dom.startAnalysisBtn.disabled = false;
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
    }
}