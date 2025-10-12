// static/js/cv_module.js - CV Analysis Module

import { PlotlyPlotter } from './plot_utils.js';

export class CVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        console.log('Initializing CV Module');

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
                peakMinVoltageInput: document.getElementById('cvPeakMinVoltageInput'),
                peakMaxVoltageInput: document.getElementById('cvPeakMaxVoltageInput'),
                probeVoltage1Input: document.getElementById('cvProbeVoltage1Input'),
                probeVoltage2Input: document.getElementById('cvProbeVoltage2Input'),
                updateProbeBtn: document.getElementById('updateProbeBtn'),
                exportCVDataBtn: document.getElementById('exportCVDataBtn'),
                exportStatus: document.getElementById('exportStatus'),
            },
            settings: {
                voltageColumnInput: document.getElementById('cvVoltageColumnInput'),
                currentColumnInput: document.getElementById('cvCurrentColumnInput'),
                spacingIndexInput: document.getElementById('cvSpacingIndexInput'),
                delimiterInput: document.getElementById('cvDelimiterInput'),
                fileExtensionInput: document.getElementById('cvFileExtensionInput'),
                voltageUnitsInput: document.getElementById('cvVoltageUnitsInput'),
                currentUnitsInput: document.getElementById('cvCurrentUnitsInput'),
                sgModeInputs: document.querySelectorAll('input[name="cvSgMode"]'),
                sgWindowInput: document.getElementById('cvSgWindowInput'),
                sgDegreeInput: document.getElementById('cvSgDegreeInput'),
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

        // Check if critical DOM elements exist
        console.log('CV Module DOM elements check:');
        console.log('cvPreviewPlot element:', this.dom.cvPreviewPlot);
        console.log('segmentStatus element:', this.dom.segmentStatus);

        if (!this.dom.cvPreviewPlot) {
            console.error('❌ cvPreviewPlot element not found!');
        }
        if (!this.dom.segmentStatus) {
            console.error('❌ segmentStatus element not found!');
        }

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

        // Set up CV export functionality
        this.dom.visualization.exportCVDataBtn.addEventListener('click', this._handleCVExport.bind(this));

        // Set up voltage probe functionality
        this.dom.visualization.updateProbeBtn.addEventListener('click', this._updateProbeLines.bind(this));

        // Set up SG filtering parameter visibility toggle
        this._setupCVFilterParams();
    }

    _setupCVFilterParams() {
        const cvSgManualParams = document.getElementById('cvSgManualParams');

        const toggleFilterParams = () => {
            const sgMode = this._getSelectedRadioValue('cvSgMode');

            // Show/hide CV SG manual params based on SG mode
            if (sgMode === 'manual') {
                cvSgManualParams.classList.remove('hidden');
            } else {
                cvSgManualParams.classList.add('hidden');
            }
        };

        // Add event listeners to all CV SG mode radio buttons
        this.dom.settings.sgModeInputs.forEach(input => {
            input.addEventListener('change', toggleFilterParams);
        });

        toggleFilterParams(); // Initialize on load
    }

    _getSelectedRadioValue(name) {
        const selected = document.querySelector(`input[name="${name}"]:checked`);
        return selected ? selected.value : null;
    }

    _setupSocketHandlers() {
        this.socketManager.on('connect', () => {
            console.log('✅ CV Module: Socket connected');
            this.socketManager.emit('request_agent_status', {});

            // Update connection status if we have UI elements
            if (this.dom.agentStatus) {
                this.dom.agentStatus.textContent = 'Checking agent connection...';
                this.dom.agentStatus.className = 'text-sm text-blue-600 mt-1';
            }
        });

        this.socketManager.on('disconnect', (reason) => {
            console.log('❌ CV Module: Socket disconnected. Reason:', reason);
            // Clear any pending timeouts
            if (this._segmentDetectionTimeoutId) {
                clearTimeout(this._segmentDetectionTimeoutId);
                this._segmentDetectionTimeoutId = null;
            }

            // Update UI to show disconnection
            if (this.dom.agentStatus) {
                this.dom.agentStatus.textContent = `Connection lost: ${reason}. Reconnecting...`;
                this.dom.agentStatus.className = 'text-sm text-red-600 mt-1';
            }
        });

        this.socketManager.on('reconnect', (attemptNumber) => {
            console.log(`🔄 CV Module: Socket reconnected after ${attemptNumber} attempts`);
            this.socketManager.emit('request_agent_status', {});
        });

        this.socketManager.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 CV Module: Reconnection attempt ${attemptNumber}`);
        });

        this.socketManager.on('reconnect_error', (error) => {
            console.error('❌ CV Module: Reconnection error:', error);
        });

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

        // Debug: Log all socket events to see what we're receiving
        console.log('Setting up CV preview response handler');

        this.socketManager.on('cv_preview_response', (data) => {
            console.log('✅ CV Preview Response received:', data);
            console.log('Response type:', typeof data, 'Keys:', Object.keys(data || {}));

            if (data && data.status === 'success') {
                console.log('CV preview success, checking cv_data:', data.cv_data);
                console.log('Content length:', data.content ? data.content.length : 'No content');

                if (data.cv_data && data.cv_data.voltage && data.cv_data.current) {
                    console.log('CV data looks valid, calling _displayCVPreview');
                    this.state.previewFileContent = data.content;
                    this._displayCVPreview(data.cv_data);
                    this.dom.segmentStatus.textContent = 'CV preview loaded. Click "Detect Segments" to analyze.';
                    this.dom.segmentStatus.className = 'text-sm text-green-600 mt-2';
                } else {
                    console.error('CV data missing or invalid:', data.cv_data);
                    this.dom.segmentStatus.textContent = 'Error: Invalid CV data received';
                    this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
                }
            } else {
                console.error('CV preview error:', data ? data.message : 'No data received');
                this.dom.segmentStatus.textContent = `Error loading preview: ${data ? data.message : 'No response'}`;
                this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
            }
        });

        // Debug: Test if we can receive any events at all
        this.socketManager.on('agent_status', (data) => {
            console.log('🔍 Test: Received agent_status event:', data);
        });

        // Debug: Note - onAny is not available in this SocketManager implementation
        console.log('Note: Using simplified event listening for debugging');

        // New: Handle CV segments processing acknowledgment
        this.socketManager.on('cv_segments_processing', (data) => {
            console.log('📝 [CV SEGMENTS] Processing acknowledgment received:', data);
            if (this.dom.segmentStatus) {
                this.dom.segmentStatus.textContent = data.message || 'Starting segment detection...';
                this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
            }
        });

        // New: Handle CV segments progress updates
        this.socketManager.on('cv_segments_progress', (data) => {
            console.log('📊 [CV SEGMENTS] Progress update received:', data);
            if (this.dom.segmentStatus) {
                const progressText = data.progress ? ` (${data.progress}%)` : '';
                this.dom.segmentStatus.textContent = `${data.message}${progressText}`;
                this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
            }
        });

        this.socketManager.on('cv_segments_response', (data) => {
            console.log('✅ [CV SEGMENTS] Final response received:', data);
            console.log('Response status:', data ? data.status : 'NO DATA');
            console.log('Response segments:', data ? data.segments : 'NO SEGMENTS');

            // Clear any pending timeout
            if (this._segmentDetectionTimeoutId) {
                clearTimeout(this._segmentDetectionTimeoutId);
                this._segmentDetectionTimeoutId = null;
            }

            if (data && data.status === 'success') {
                // Store enhanced segment information
                this.state.availableSegments = data.segments || [];
                this.state.segmentInfo = data.segment_info || {};
                this.state.forwardSegments = data.forward_segments || [];
                this.state.reverseSegments = data.reverse_segments || [];

                this._updateSegmentDropdowns();

                if (this.state.availableSegments.length > 0) {
                    const forwardCount = this.state.forwardSegments.length;
                    const reverseCount = this.state.reverseSegments.length;
                    this.dom.segmentStatus.textContent =
                        `Found ${data.segments.length} segments: ${forwardCount} forward, ${reverseCount} reverse`;
                    this.dom.segmentStatus.className = 'text-sm text-green-600 mt-2';

                    // Highlight segments on preview plot
                    this._highlightSegmentsOnPreview();
                } else {
                    this.dom.segmentStatus.textContent = 'No segments found. Using auto-detection for analysis.';
                    this.dom.segmentStatus.className = 'text-sm text-yellow-600 mt-2';
                }
            } else {
                console.error('CV segments error:', data);
                this.dom.segmentStatus.textContent = `Segment detection failed: ${data ? data.message : 'Unknown error'}`;
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
            console.log('=== CV Live Update Received ===');
            console.log('Full data object:', data);
            console.log('Analysis running:', this.state.isAnalysisRunning);

            if (!this.state.isAnalysisRunning) return;

            // Store CV results per electrode
            if (data.cv_analysis && data.electrode_index !== undefined) {
                console.log('CV Analysis data structure:', data.cv_analysis);
                console.log('CV Analysis keys:', Object.keys(data.cv_analysis));
                console.log('Forward data:', data.cv_analysis.forward);
                console.log('Reverse data:', data.cv_analysis.reverse);
                console.log('ELECTRODE INDEX received:', data.electrode_index, 'Type:', typeof data.electrode_index);

                const electrodeKey = data.electrode_index !== null ? data.electrode_index.toString() : 'averaged';
                console.log('Storing data under electrode key:', electrodeKey);

                if (!this.state.cvResults[electrodeKey]) {
                    this.state.cvResults[electrodeKey] = {};
                }

                // Extract file number from filename (support CV_60Hz_1.txt format and others)
                const match = data.filename.match(/CV_\d+Hz_+(\d+)\./) || data.filename.match(/_(\d+)\./);
                if (match) {
                    const fileNum = match[1];
                    this.state.cvResults[electrodeKey][fileNum] = data.cv_analysis;
                    console.log(`Stored CV data: Electrode ${electrodeKey}, File ${fileNum}`);
                    console.log(`Current CV Results structure:`, Object.keys(this.state.cvResults));
                    Object.keys(this.state.cvResults).forEach(elecKey => {
                        console.log(`  Electrode ${elecKey}: ${Object.keys(this.state.cvResults[elecKey]).length} files`);
                    });

                    // Switch to visualization on first result (like SWV)
                    if (this.state.currentScreen !== 'visualization' && Object.keys(this.state.cvResults[electrodeKey]).length === 1) {
                        console.log('First CV result received - switching to visualization');
                        this.state.currentScreen = 'visualization';
                        this.uiManager.showScreen('visualizationArea');
                        this._setupCVVisualization();
                    }

                    // Update visualization in real-time if this is the current electrode
                    if (data.electrode_index === this.state.currentElectrode && this.state.currentScreen === 'visualization') {
                        this._updateCVVisualizationRealTime(data.cv_analysis, fileNum);
                    }

                    // Check if we have enough files to complete analysis
                    this._checkCVAnalysisProgress();

                    // Update electrode controls as we receive data for different electrodes
                    this._setupCVElectrodeControls();
                }
            }
        });

        // Add handler for CV analysis completion
        this.socketManager.on('cv_analysis_complete', (data) => {
            if (data.status === 'success') {
                // Analysis completed successfully, switch to visualization
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.textContent = 'CV Analysis Complete';
                this.dom.startAnalysisBtn.disabled = false;

                // Switch to visualization area (reuse SWV's visualization area)
                this.uiManager.showScreen('visualizationArea');
                this._setupCVVisualization();
            } else {
                // Analysis failed
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.segmentStatus.textContent = `Analysis failed: ${data.message}`;
                this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
            }
        });

        // Add handler for CV export data response
        this.socketManager.on('export_cv_data_response', (data) => {
            if (data.status === 'success') {
                const filename = this.dom.visualization.exportCVDataBtn.dataset.filename || 'cv_export.csv';
                this.dom.visualization.exportStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerCsvDownload(data.data, filename);
            } else {
                this.dom.visualization.exportStatus.textContent = `Export failed: ${data.message}`;
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

        // For CV preview, we don't require a specific file extension
        // Override file_extension to be empty to match files without extensions
        analysisParams.file_extension = '';

        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: 1 // Just get the first file for preview
        };

        console.log('Requesting CV preview with filters:', filters);
        console.log('Analysis params (modified for preview):', analysisParams);

        this.dom.segmentStatus.textContent = 'Loading CV preview...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';

        // Request the first file for preview
        console.log('Emitting get_cv_preview event');
        console.log('Socket connected:', this.socketManager.socket.connected);
        console.log('Socket ID:', this.socketManager.socket.id);

        this.socketManager.emit('get_cv_preview', { filters, analysisParams });

        // Set a timeout to check if we get a response
        setTimeout(() => {
            if (this.dom.segmentStatus.textContent === 'Loading CV preview...') {
                console.warn('⚠️ No CV preview response received after 5 seconds');
                this.dom.segmentStatus.textContent = 'Timeout: No response from server. Check agent connection.';
                this.dom.segmentStatus.className = 'text-sm text-yellow-600 mt-2';
            }
        }, 5000);
    }

    _handleDetectSegments() {
        if (!this.state.previewFileContent) {
            console.log('No preview file content, requesting preview first...');
            this.dom.segmentStatus.textContent = 'Loading preview file first...';
            this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
            this._requestPreviewFile();

            // Set a timeout to auto-detect segments after preview loads
            setTimeout(() => {
                if (this.state.previewFileContent) {
                    this._handleDetectSegments();
                }
            }, 3000);
            return;
        }

        const analysisParams = this._collectAnalysisParams();

        console.log('=== Segment Detection Request ===');
        console.log('Preview file content length:', this.state.previewFileContent.length);
        console.log('Preview file content preview:', this.state.previewFileContent.substring(0, 200));
        console.log('Analysis params:', analysisParams);

        const requestData = {
            // Don't send content - backend will use stored preview content from session
            // This avoids sending large payloads that cause socket disconnection
            content: '',  // Empty - backend will fetch from session
            filename: 'preview_cv_file.txt',
            params: analysisParams
        };

        console.log('=== Sending Segment Detection Request ===');
        console.log('Request data (content excluded for performance):', {
            filename: requestData.filename,
            params: requestData.params,
            contentLength: this.state.previewFileContent ? this.state.previewFileContent.length : 0
        });
        console.log('Socket connected:', this.socketManager.socket.connected);
        console.log('Socket id:', this.socketManager.socket.id);

        try {
            this.socketManager.emit('get_cv_segments', requestData);
            console.log('✅ Segment detection request emitted via socket');
            console.log('Waiting for server response (using session-stored preview content)...');
        } catch (error) {
            console.error('❌ Failed to emit segment detection request:', error);
            this.dom.segmentStatus.textContent = 'Failed to send request. Check connection.';
            this.dom.segmentStatus.className = 'text-sm text-red-600 mt-2';
            return;
        }

        this.dom.segmentStatus.textContent = 'Initializing segment detection...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';

        // Extended timeout handling for background processing
        this._segmentDetectionTimeoutId = setTimeout(() => {
            // Check if we're still waiting for a response (status hasn't been updated by progress events)
            if (this.dom.segmentStatus.textContent.includes('Initializing') ||
                this.dom.segmentStatus.textContent.includes('Processing') ||
                this.dom.segmentStatus.textContent.includes('Creating') ||
                this.dom.segmentStatus.textContent.includes('Reading') ||
                this.dom.segmentStatus.textContent.includes('Analyzing')) {

                console.warn('⚠️ Segment detection timeout after 30 seconds');
                this.dom.segmentStatus.textContent = 'Segment detection timeout. Using auto-detection for analysis.';
                this.dom.segmentStatus.className = 'text-sm text-yellow-600 mt-2';

                // Set default segments for fallback with basic info
                this.state.availableSegments = [1, 2];
                this.state.segmentInfo = {
                    '1': { type: 'forward', points: 0, potential_range: [0, 0] },
                    '2': { type: 'reverse', points: 0, potential_range: [0, 0] }
                };
                this._updateSegmentDropdowns();
            }
        }, 30000); // Extended timeout from 15s to 30s for background processing
    }

    _updateSegmentDropdowns() {
        // Clear existing options
        this.dom.visualization.forwardSegmentInput.innerHTML = '<option value="">Auto-detect</option>';
        this.dom.visualization.reverseSegmentInput.innerHTML = '<option value="">Auto-detect</option>';

        // Add detected segments with type classification
        this.state.availableSegments.forEach(segment => {
            const segInfo = this.state.segmentInfo[segment] || {};
            const segmentType = segInfo.type || 'unknown';
            const points = segInfo.points || 0;
            const range = segInfo.potential_range || [0, 0];

            // Create descriptive labels
            const forwardLabel = `Segment ${segment} (${segmentType}, ${points} pts, ${range[0].toFixed(2)}${this.dom.settings.voltageUnitsInput.value} to ${range[1].toFixed(2)}${this.dom.settings.voltageUnitsInput.value})`;
            const reverseLabel = `Segment ${segment} (${segmentType}, ${points} pts, ${range[0].toFixed(2)}${this.dom.settings.voltageUnitsInput.value} to ${range[1].toFixed(2)}${this.dom.settings.voltageUnitsInput.value})`;

            const option1 = new Option(forwardLabel, segment);
            const option2 = new Option(reverseLabel, segment);

            // Style options based on segment type
            if (segmentType === 'forward') {
                option1.style.backgroundColor = '#e6f3ff';  // Light blue for forward
                option2.style.backgroundColor = '#e6f3ff';
            } else if (segmentType === 'reverse') {
                option1.style.backgroundColor = '#ffe6e6';  // Light red for reverse
                option2.style.backgroundColor = '#ffe6e6';
            }

            this.dom.visualization.forwardSegmentInput.add(option1);
            this.dom.visualization.reverseSegmentInput.add(option2);
        });

        // Smart auto-selection based on segment classification
        if (this.state.forwardSegments.length > 0) {
            this.dom.visualization.forwardSegmentInput.value = this.state.forwardSegments[0];
        } else if (this.state.availableSegments.length > 0) {
            this.dom.visualization.forwardSegmentInput.value = this.state.availableSegments[0];
        }

        if (this.state.reverseSegments.length > 0) {
            this.dom.visualization.reverseSegmentInput.value = this.state.reverseSegments[0];
        } else if (this.state.availableSegments.length > 1) {
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
            peak_min_voltage: this.dom.visualization.peakMinVoltageInput.value === '' ? null : parseFloat(this.dom.visualization.peakMinVoltageInput.value),
            peak_max_voltage: this.dom.visualization.peakMaxVoltageInput.value === '' ? null : parseFloat(this.dom.visualization.peakMaxVoltageInput.value),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value),
            current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value),
            delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value,
            voltage_units: this.dom.settings.voltageUnitsInput.value,
            current_units: this.dom.settings.currentUnitsInput.value,
            sg_mode: this._getSelectedRadioValue('cvSgMode'),
            sg_window: this._getSelectedRadioValue('cvSgMode') === 'manual' ? parseInt(this.dom.settings.sgWindowInput.value) : undefined,
            sg_degree: this._getSelectedRadioValue('cvSgMode') === 'manual' ? parseInt(this.dom.settings.sgDegreeInput.value) : undefined,
            probe_voltages: this.state.probeVoltages || [],
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
            availableSegments: this.state.availableSegments,
            probeVoltages: this.state.probeVoltages || [],  // Preserve probe voltages
            analysisStartTime: Date.now()
        };

        const analysisParams = this._collectAnalysisParams();
        analysisParams.selected_electrode = this.state.currentElectrode;
        analysisParams.selected_electrodes = this.state.selectedElectrodes;

        console.log('=== CV Analysis Starting ===');
        console.log('Selected electrodes:', selectedElectrodes);
        console.log('Current electrode:', this.state.currentElectrode);
        console.log('Probe voltages:', this.state.probeVoltages);
        console.log('Analysis params probe_voltages:', analysisParams.probe_voltages);

        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: numFiles,
            frequencies: [60]  // CV files use 60Hz by default
        };

        this.dom.startAnalysisBtn.textContent = 'CV Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending CV instructions to server...";

        this.socketManager.emit('start_cv_analysis_session', { filters, analysisParams });

        // Set up timeout to automatically switch to visualization if no data is received
        this._setupCVAnalysisTimeout();
    }

    _setupCVVisualization(reason = 'normal') {
        // Set up CV-specific visualization in the shared visualization area
        const visualizationArea = document.getElementById('visualizationArea');
        if (!visualizationArea) return;

        // Update the title for CV analysis
        const titleElement = visualizationArea.querySelector('h2');
        if (titleElement) {
            if (reason === 'timeout_no_data') {
                titleElement.textContent = 'CV Analysis - No Data Received';
            } else if (reason === 'timeout_with_data') {
                titleElement.textContent = 'CV Analysis - Partial Results';
            } else {
                titleElement.textContent = 'CV Data Visualization';
            }
        }

        // Hide SWV-specific controls and show basic visualization
        const adjustmentControls = document.getElementById('adjustmentControls');
        const exportDataBtn = document.getElementById('exportDataBtn');
        const backToSWVBtn = document.getElementById('backToSWVBtn');

        if (adjustmentControls) adjustmentControls.classList.add('hidden');
        if (exportDataBtn) exportDataBtn.classList.add('hidden');

        // Show CV export button
        const exportCVDataBtn = document.getElementById('exportCVDataBtn');
        if (exportCVDataBtn) exportCVDataBtn.classList.remove('hidden');

        // Change back button to go to CV settings
        if (backToSWVBtn) {
            backToSWVBtn.textContent = 'Back to CV Settings';
            backToSWVBtn.onclick = () => {
                // Stop any running CV analysis
                if (this.state.isAnalysisRunning) {
                    this.socketManager.emit('stop_cv_analysis_session', { reason: 'user_returned_to_settings' });
                }
                this.state.currentScreen = 'settings';
                this.uiManager.showScreen('cvAnalysisScreen');
                this.state.isAnalysisRunning = false;

                // Reset button state when returning to settings
                this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
                this.dom.startAnalysisBtn.disabled = false;
            };
        }

        // Set up electrode controls if needed
        this._setupCVElectrodeControls();

        // Create comprehensive CV plots area
        this._createCVSummaryPlots();

        // Display CV results
        this._displayCVResults();
    }

    _setupCVElectrodeControls() {
        const electrodeControls = document.getElementById('electrodeControls');
        if (!electrodeControls) return;

        // Always show electrode controls (like SWV module)
        electrodeControls.style.display = 'block';

        // Clear existing buttons
        const existingButtons = electrodeControls.querySelectorAll('.electrode-btn');
        existingButtons.forEach(btn => btn.remove());

        // Add "Averaged" button if no specific electrodes selected
        if (this.state.selectedElectrodes.length === 0) {
            const avgBtn = document.createElement('button');
            avgBtn.className = 'electrode-btn px-4 py-2 text-sm font-medium rounded-lg border bg-blue-500 text-white';
            avgBtn.textContent = 'Averaged';
            avgBtn.disabled = true; // Current selection
            electrodeControls.appendChild(avgBtn);
        } else {
            // Add buttons for each selected electrode
            this.state.selectedElectrodes.forEach(electrodeIdx => {
                const btn = document.createElement('button');
                btn.className = `electrode-btn px-4 py-2 text-sm font-medium rounded-lg border ${
                    electrodeIdx === this.state.currentElectrode
                        ? 'bg-blue-500 text-white'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`;
                btn.textContent = `Electrode ${electrodeIdx + 1}`;  // Display as 1-based
                btn.onclick = () => this._switchCVElectrode(electrodeIdx);
                electrodeControls.appendChild(btn);
            });
        }
    }

    _switchCVElectrode(electrodeIdx) {
        if (this.state.currentElectrode === electrodeIdx) return;

        console.log(`=== CV Electrode Switch ===`);
        console.log(`Switching from electrode ${this.state.currentElectrode} to ${electrodeIdx}`);
        console.log('Available CV results:', Object.keys(this.state.cvResults));

        const newElectrodeKey = electrodeIdx?.toString() || 'averaged';
        const newElectrodeData = this.state.cvResults[newElectrodeKey];
        console.log(`New electrode ${newElectrodeKey} data:`, newElectrodeData);

        if (newElectrodeData) {
            console.log(`Electrode ${newElectrodeKey} has ${Object.keys(newElectrodeData).length} files`);
            Object.keys(newElectrodeData).forEach(fileNum => {
                const fileData = newElectrodeData[fileNum];
                console.log(`  File ${fileNum}: Forward peak = ${fileData?.forward?.peak_current}, Reverse peak = ${fileData?.reverse?.peak_current}`);
            });
        } else {
            console.log(`No data found for electrode ${newElectrodeKey}`);
        }

        this.state.currentElectrode = electrodeIdx;
        this._setupCVElectrodeControls(); // Update button states
        this._displayCVResults(); // Refresh plots with new electrode data
        this._updateCVSummaryPlots(); // Update summary plots for new electrode
    }

    _displayCVResults() {
        // Display CV analysis results in the visualization area
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
        const electrodeResults = this.state.cvResults[electrodeKey];
        const hasResults = electrodeResults && Object.keys(electrodeResults).length > 0;

        if (hasResults) {
            // Get the most recent analysis result for visualization
            const fileNumbers = Object.keys(electrodeResults).map(Number).sort((a, b) => b - a);
            const latestFileNum = fileNumbers[0];
            const latestResult = electrodeResults[latestFileNum];

            if (latestResult && latestResult.status === 'success') {
                // Display the latest CV plots with all peaks/AUC intact
                this._updateCVVisualization(latestResult);
                // Update comprehensive analysis
                this._updateCVSummaryPlots();
            }
        }

        // Remove only CV-specific text summaries (not SWV content)
        const cvTextSummaries = document.querySelectorAll('.analysis-summary, .cv-text-summary, .cv-analysis-summary');
        cvTextSummaries.forEach(summary => summary.remove());

        // Hide SWV trend plots container since we use our own CV layout
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            trendPlotsContainer.style.display = 'none';
        }
    }

    _setupCVAnalysisTimeout() {
        // Set up periodic checks and timeouts for CV analysis
        const maxWaitTime = 30000; // 30 seconds maximum wait
        const checkInterval = 2000; // Check every 2 seconds

        let checkCount = 0;
        const maxChecks = maxWaitTime / checkInterval;

        const checkProgress = () => {
            checkCount++;

            if (!this.state.isAnalysisRunning) {
                return; // Analysis already completed
            }

            // Check if we have any results
            const hasAnyResults = Object.keys(this.state.cvResults).length > 0;
            const timeElapsed = Date.now() - this.state.analysisStartTime;

            // Force visualization switch if:
            // 1. We have substantial results and 60 seconds have passed
            // 2. Maximum wait time has been reached
            const numResults = Object.keys(this.state.cvResults).reduce((total, electrode) => {
                return total + Object.keys(this.state.cvResults[electrode] || {}).length;
            }, 0);

            const hasSubstantialResults = numResults >= Math.min(10, this.state.currentNumFiles * 0.2);

            if (hasSubstantialResults && timeElapsed > 60000) {
                console.log(`CV analysis: Force switching to visualization after ${timeElapsed}ms with ${numResults} results`);
                this._completeCVAnalysis('timeout_with_data');
                return;
            } else if (timeElapsed > maxWaitTime) {
                console.log(`CV analysis: Force switching to visualization after ${timeElapsed}ms timeout`);
                this._completeCVAnalysis('timeout_no_data');
                return;
            }

            // Check normal progress
            this._checkCVAnalysisProgress();

            // Continue checking if we haven't reached max checks
            if (checkCount < maxChecks && this.state.isAnalysisRunning) {
                setTimeout(checkProgress, checkInterval);
            }
        };

        // Start checking after a brief delay
        setTimeout(checkProgress, checkInterval);
    }

    _checkCVAnalysisProgress() {
        // Check if we have processed enough files to show results
        if (!this.state.isAnalysisRunning) return;

        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
        const electrodeResults = this.state.cvResults[electrodeKey];

        if (!electrodeResults) return;

        // Only count files with successful analysis results
        const validResults = Object.keys(electrodeResults).filter(key => {
            const result = electrodeResults[key];
            return result && typeof result === 'object' &&
                   result.status === 'success' &&
                   (result.forward_sweep || result.reverse_sweep || result.peak_info);
        });

        const processedFiles = validResults.length;
        const totalFiles = this.state.currentNumFiles;

        // For CV analysis, only complete when ALL files are processed (like SWV)
        // This allows real-time visualization during analysis
        console.log(`CV analysis progress: ${processedFiles}/${totalFiles} files processed (with valid data).`);

        // Only complete if we have at least 80% of expected files OR we've been running for a long time
        const completionThreshold = Math.max(Math.floor(totalFiles * 0.95), totalFiles - 2);

        if (processedFiles >= completionThreshold) {
            console.log(`CV analysis complete: ${processedFiles}/${totalFiles} files processed.`);
            this._completeCVAnalysis('complete');
        }
        // Note: No early completion - let analysis run to near completion like SWV
    }

    _completeCVAnalysis(reason = 'normal') {
        if (!this.state.isAnalysisRunning) return;

        // Analysis completed, switch to visualization
        this.state.isAnalysisRunning = false;

        // Update button text based on completion reason
        switch (reason) {
            case 'timeout_no_data':
                this.dom.startAnalysisBtn.textContent = 'CV Analysis Timeout (No Data)';
                this.dom.folderStatus.textContent = 'No CV data received. Check file handle and agent connection.';
                break;
            case 'timeout_with_data':
                this.dom.startAnalysisBtn.textContent = 'CV Analysis Complete (Timeout)';
                this.dom.folderStatus.textContent = 'CV analysis timeout reached. Showing available results.';
                break;
            case 'sufficient_data':
                this.dom.startAnalysisBtn.textContent = 'CV Analysis Complete';
                this.dom.folderStatus.textContent = 'CV analysis completed successfully.';
                break;
            default:
                this.dom.startAnalysisBtn.textContent = 'CV Analysis Complete';
                this.dom.folderStatus.textContent = 'CV analysis finished.';
        }

        this.dom.startAnalysisBtn.disabled = false;

        // Switch to visualization area (reuse SWV's visualization area)
        this.uiManager.showScreen('visualizationArea');
        this._setupCVVisualization(reason);

        // Show electrode controls now that analysis is complete
        this._setupCVElectrodeControls();
    }

    _updateCVVisualization(analysisResult) {
        console.log('CV Analysis Result:', analysisResult);

        if (!analysisResult || !analysisResult.forward && !analysisResult.reverse) {
            console.log('No CV data to visualize');
            return;
        }

        // Check if the new layout already exists
        const mainContainer = document.querySelector('.cv-main-container');
        if (!mainContainer) {
            // Create the layout structure first
            this._createCVSummaryPlots();
        }

        // Update individual plot elements with preserved peak markers and AUC areas
        const forwardPlotElement = document.getElementById('cv-forward-plot');
        const reversePlotElement = document.getElementById('cv-reverse-plot');

        if (analysisResult.forward && forwardPlotElement) {
            this._updateSingleCVPlot(forwardPlotElement, analysisResult.forward, 'Forward Sweep');
        }

        if (analysisResult.reverse && reversePlotElement) {
            this._updateSingleCVPlot(reversePlotElement, analysisResult.reverse, 'Reverse Sweep');
        }
    }

    _updateCVVisualizationRealTime(analysisResult, fileNum) {
        console.log(`=== CV Real-time Visualization Update: File ${fileNum} ===`);
        console.log('Analysis result full object:', analysisResult);

        // Always update progress display, even if there's no data to plot
        this._updateCVProgressDisplay(fileNum);

        if (!analysisResult) {
            console.error('❌ No analysis result for real-time update');
            return;
        }

        console.log('Analysis result status:', analysisResult.status);
        console.log('Analysis result keys:', Object.keys(analysisResult));

        // Check if we have any CV data to visualize
        console.log('🔍 Checking forward data...');
        console.log('Forward object:', analysisResult.forward);
        console.log('Forward is object:', typeof analysisResult.forward === 'object');
        console.log('Forward keys:', analysisResult.forward ? Object.keys(analysisResult.forward) : 'null/undefined');

        console.log('🔍 Checking reverse data...');
        console.log('Reverse object:', analysisResult.reverse);
        console.log('Reverse is object:', typeof analysisResult.reverse === 'object');
        console.log('Reverse keys:', analysisResult.reverse ? Object.keys(analysisResult.reverse) : 'null/undefined');

        const hasForward = analysisResult.forward && Object.keys(analysisResult.forward).length > 0;
        const hasReverse = analysisResult.reverse && Object.keys(analysisResult.reverse).length > 0;

        console.log('Has forward data:', hasForward);
        console.log('Has reverse data:', hasReverse);

        if (!hasForward && !hasReverse) {
            console.error('❌ No CV forward/reverse data to visualize in real-time update');
            console.log('📊 Analysis result structure:', JSON.stringify(analysisResult, null, 2));
            return;
        }

        console.log('✅ CV data available, creating plots...');
        // Update or create plots in real-time
        this._createCVPlotsRealTime(analysisResult, fileNum);

        // Update summary plots with all data
        this._updateCVSummaryPlots();
    }

    _createCVPlots(analysisResult) {
        // Find or create plot containers
        const visualizationArea = document.getElementById('visualizationArea');
        if (!visualizationArea) return;

        // Clear existing plots
        const existingPlots = visualizationArea.querySelectorAll('.cv-plot-container');
        existingPlots.forEach(plot => plot.remove());

        // Create plot containers
        const plotContainer = document.createElement('div');
        plotContainer.className = 'cv-plot-container grid grid-cols-1 md:grid-cols-2 gap-4 mt-4';

        // Forward sweep plot
        if (analysisResult.forward && analysisResult.forward.potentials) {
            const forwardPlot = this._createSingleCVPlot(
                analysisResult.forward,
                'Forward Sweep',
                'cv-forward-plot'
            );
            plotContainer.appendChild(forwardPlot);
        }

        // Reverse sweep plot
        if (analysisResult.reverse && analysisResult.reverse.potentials) {
            const reversePlot = this._createSingleCVPlot(
                analysisResult.reverse,
                'Reverse Sweep',
                'cv-reverse-plot'
            );
            plotContainer.appendChild(reversePlot);
        }

        // Insert plots before summary
        const summaryElement = visualizationArea.querySelector('.analysis-summary') || visualizationArea.lastElementChild;
        visualizationArea.insertBefore(plotContainer, summaryElement);
    }

    _createSingleCVPlot(sweepData, title, plotId) {
        const plotDiv = document.createElement('div');
        plotDiv.className = 'bg-white p-4 rounded-lg shadow';
        plotDiv.innerHTML = `
            <h3 class="text-lg font-semibold mb-2">${title}</h3>
            <div id="${plotId}" class="plotly-plot-container"></div>
        `;

        // Use setTimeout to ensure DOM is ready
        setTimeout(() => {
            const plotElement = document.getElementById(plotId);
            if (plotElement && window.Plotly) {
                const traces = [
                    {
                        x: sweepData.potentials,
                        y: sweepData.currents,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Raw Data',
                        line: { color: 'blue', width: 2 }
                    }
                ];

                // Add corrected data if available
                if (sweepData.corrected_currents) {
                    traces.push({
                        x: sweepData.potentials,
                        y: sweepData.corrected_currents,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Baseline Corrected',
                        line: { color: 'red', width: 2 }
                    });
                }

                // Add baseline if available
                if (sweepData.baseline) {
                    traces.push({
                        x: sweepData.potentials,
                        y: sweepData.baseline,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Baseline',
                        line: { color: 'gray', width: 1, dash: 'dash' }
                    });
                }

                const layout = {
                    xaxis: {
                        title: 'Potential (V)',
                        autorange: true
                    },
                    yaxis: {
                        title: 'Current (A)',
                        autorange: true
                    },
                    showlegend: true,
                    margin: { l: 60, r: 40, t: 40, b: 60 },
                    autosize: true
                };

                Plotly.newPlot(plotElement, traces, layout, {
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
                    displaylogo: false
                });
            }
        }, 100);

        return plotDiv;
    }

    _createCVPlotsRealTime(analysisResult, fileNum) {
        // Update existing plots or create them if they don't exist
        const forwardPlotElement = document.getElementById('cv-forward-plot');
        const reversePlotElement = document.getElementById('cv-reverse-plot');

        // If plots don't exist yet, create the new layout
        if (!forwardPlotElement || !reversePlotElement) {
            this._createCVSummaryPlots();
            // Get the plot elements again after creating the layout
            const newForwardPlotElement = document.getElementById('cv-forward-plot');
            const newReversePlotElement = document.getElementById('cv-reverse-plot');

            // Update the plots with the current data
            if (analysisResult.forward && newForwardPlotElement) {
                this._updateSingleCVPlot(newForwardPlotElement, analysisResult.forward, `Forward Sweep (File ${fileNum})`);
            }
            if (analysisResult.reverse && newReversePlotElement) {
                this._updateSingleCVPlot(newReversePlotElement, analysisResult.reverse, `Reverse Sweep (File ${fileNum})`);
            }
            return;
        }

        // Update forward plot
        if (analysisResult.forward && analysisResult.forward.potentials && forwardPlotElement) {
            this._updateSingleCVPlot(forwardPlotElement, analysisResult.forward, `Forward Sweep (File ${fileNum})`);
        }

        // Update reverse plot
        if (analysisResult.reverse && analysisResult.reverse.potentials && reversePlotElement) {
            this._updateSingleCVPlot(reversePlotElement, analysisResult.reverse, `Reverse Sweep (File ${fileNum})`);
        }
    }

    _updateSingleCVPlot(plotElement, sweepData, title) {
        if (!plotElement || !window.Plotly) return;

        const traces = [
            {
                x: sweepData.potentials,
                y: sweepData.currents,
                type: 'scatter',
                mode: 'lines',
                name: 'Raw Data',
                line: { color: 'blue', width: 2 }
            }
        ];

        // Add corrected data if available
        if (sweepData.corrected_currents) {
            traces.push({
                x: sweepData.potentials,
                y: sweepData.corrected_currents,
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline Corrected',
                line: { color: 'red', width: 2 }
            });
        }

        // Add baseline if available
        if (sweepData.baseline) {
            traces.push({
                x: sweepData.potentials,
                y: sweepData.baseline,
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline',
                line: { color: 'gray', width: 1, dash: 'dash' }
            });
        }

        // Add peak marker if available
        if (sweepData.peak_potential !== undefined && sweepData.peak_current !== undefined) {
            traces.push({
                x: [sweepData.peak_potential],
                y: [sweepData.peak_current],
                type: 'scatter',
                mode: 'markers+text',
                name: 'Peak',
                marker: { color: 'red', size: 10, symbol: 'diamond' },
                text: [`Peak: ${sweepData.peak_potential.toFixed(3)}${this.dom.settings.voltageUnitsInput.value}, ${sweepData.peak_current.toFixed(2)}${this.dom.settings.currentUnitsInput.value}`],
                textposition: 'top center',
                textfont: { size: 10 }
            });
        }

        // Add AUC shading if available
        if (sweepData.auc_vertices && sweepData.auc_vertices.length > 0) {
            const aucX = sweepData.auc_vertices.map(v => v[0]);
            const aucY = sweepData.auc_vertices.map(v => v[1]);
            traces.push({
                x: aucX,
                y: aucY,
                fill: 'tozeroy',
                type: 'scatter',
                mode: 'none',
                name: 'AUC Area',
                fillcolor: 'rgba(255, 0, 0, 0.2)',
                line: { color: 'transparent' }
            });
        }

        const layout = {
            title: title,
            xaxis: {
                title: 'Potential (V)',
                autorange: true
            },
            yaxis: {
                title: `Current (${this.dom.settings.currentUnitsInput.value})`,
                autorange: true
            },
            showlegend: true,
            margin: { l: 60, r: 40, t: 60, b: 60 },
            autosize: true
        };

        // Use Plotly.react for real-time updates (better than redraw)
        Plotly.react(plotElement, traces, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
            displaylogo: false
        });
    }

    _updateCVProgressDisplay(fileNum) {
        // Update progress display to show current file being processed
        const titleElement = document.querySelector('#visualizationArea h2');
        if (titleElement) {
            const currentElectrode = this.state.currentElectrode;
            const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
            const totalProcessed = Object.keys(this.state.cvResults[electrodeKey] || {}).length;
            const totalFiles = this.state.currentNumFiles;

            titleElement.textContent = `CV Data Visualization - Processing: ${totalProcessed}/${totalFiles} files`;
        }
    }

    _createCVSummaryPlots() {
        // Create comprehensive CV analysis plots with new layout
        const visualizationArea = document.getElementById('visualizationArea');
        if (!visualizationArea) return;

        // Check if the new layout already exists
        const existingMainContainer = visualizationArea.querySelector('.cv-main-container');
        if (existingMainContainer) {
            // Layout already exists, no need to recreate
            return;
        }

        // Remove old layout elements and text summaries only
        const oldPlots = visualizationArea.querySelectorAll('.cv-plot-container, .cv-summary-plots');
        oldPlots.forEach(plot => plot.remove());

        // Remove text summaries
        const textSummaries = visualizationArea.querySelectorAll('.analysis-summary, .border');
        textSummaries.forEach(summary => summary.remove());

        // Create new layout: left side segments, right side comprehensive analysis
        const mainContainer = document.createElement('div');
        mainContainer.className = 'cv-main-container grid grid-cols-1 lg:grid-cols-4 gap-4 mt-4';
        mainContainer.innerHTML = `
            <!-- Left side: CV Segments (responsive width) -->
            <div class="cv-segments-side lg:col-span-1">
                <div class="space-y-4">
                    <div class="bg-white p-3 rounded-lg shadow">
                        <h4 class="text-sm font-semibold mb-2">Forward Sweep</h4>
                        <div id="cv-forward-plot" class="plotly-plot-container w-full"></div>
                    </div>
                    <div class="bg-white p-3 rounded-lg shadow">
                        <h4 class="text-sm font-semibold mb-2">Reverse Sweep</h4>
                        <div id="cv-reverse-plot" class="plotly-plot-container w-full"></div>
                    </div>
                </div>
            </div>

            <!-- Right side: Comprehensive Analysis (responsive width) -->
            <div class="cv-analysis-side lg:col-span-3">
                <div class="space-y-4">
                    <div class="bg-white p-4 rounded-lg shadow">
                        <h4 class="text-md font-semibold mb-2">Peak Separation Trend</h4>
                        <div id="cv-peak-separation-plot" class="plotly-plot-container w-full"></div>
                    </div>
                    <div class="bg-white p-4 rounded-lg shadow">
                        <h4 class="text-md font-semibold mb-2">AUC Trend</h4>
                        <div id="cv-auc-plot" class="plotly-plot-container w-full"></div>
                    </div>
                    <div class="bg-white p-4 rounded-lg shadow" id="cv-probe-plot-container" style="display: none;">
                        <h4 class="text-md font-semibold mb-2">Probe Voltage Currents</h4>
                        <div id="cv-probe-plot" class="plotly-plot-container w-full"></div>
                    </div>
                </div>
            </div>
        `;

        visualizationArea.appendChild(mainContainer);
    }

    _updateCVSummaryPlots() {
        // Update summary plots with all processed data
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
        const electrodeResults = this.state.cvResults[electrodeKey];

        if (!electrodeResults) return;

        const fileNumbers = Object.keys(electrodeResults).map(Number).sort((a, b) => a - b);
        const peakSeparations = [];
        const forwardAUCs = [];
        const reverseAUCs = [];

        fileNumbers.forEach(fileNum => {
            const result = electrodeResults[fileNum];
            if (result && result.status === 'success') {
                if (result.peak_separation !== undefined && result.peak_separation !== null) {
                    peakSeparations.push({ x: fileNum, y: result.peak_separation });
                }
                if (result.forward && result.forward.charge !== undefined) {
                    forwardAUCs.push({ x: fileNum, y: result.forward.charge });
                }
                if (result.reverse && result.reverse.charge !== undefined) {
                    reverseAUCs.push({ x: fileNum, y: result.reverse.charge });
                }
            }
        });

        // Update peak separation plot
        this._updatePeakSeparationPlot(peakSeparations);

        // Update AUC plot
        this._updateAUCPlot(forwardAUCs, reverseAUCs);

        // Update probe data plot if probe voltages exist
        this._updateProbeDataPlot(electrodeResults, fileNumbers);
    }

    _updatePeakSeparationPlot(peakSeparations) {
        const plotElement = document.getElementById('cv-peak-separation-plot');
        if (!plotElement || !window.Plotly || peakSeparations.length === 0) return;

        const trace = {
            x: peakSeparations.map(p => p.x),
            y: peakSeparations.map(p => p.y),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Peak Separation',
            line: { color: 'blue', width: 2 },
            marker: { size: 6 }
        };

        const layout = {
            title: 'Peak Separation vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: { title: 'Peak Separation (V)' },
            margin: { l: 70, r: 50, t: 50, b: 60 }
        };

        Plotly.react(plotElement, [trace], layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
            displaylogo: false
        });
    }

    _updateAUCPlot(forwardAUCs, reverseAUCs) {
        const plotElement = document.getElementById('cv-auc-plot');
        if (!plotElement || !window.Plotly) return;

        const traces = [];

        if (forwardAUCs.length > 0) {
            traces.push({
                x: forwardAUCs.map(p => p.x),
                y: forwardAUCs.map(p => p.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Forward AUC',
                line: { color: 'red', width: 2 },
                marker: { size: 6 }
            });
        }

        if (reverseAUCs.length > 0) {
            traces.push({
                x: reverseAUCs.map(p => p.x),
                y: reverseAUCs.map(p => p.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Reverse AUC',
                line: { color: 'green', width: 2 },
                marker: { size: 6 }
            });
        }

        const layout = {
            title: 'AUC vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: { title: `Charge (${this.dom.settings.currentUnitsInput.value}C)` },
            margin: { l: 70, r: 50, t: 50, b: 60 }
        };

        Plotly.react(plotElement, traces, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
            displaylogo: false
        });
    }

    _updateProbeDataPlot(electrodeResults, fileNumbers) {
        // Check if probe data exists and we have analysis parameters
        const probeVoltages = this.state.probeVoltages || [];

        // Also check if probe voltages are stored in analysis params
        if (probeVoltages.length === 0) {
            const analysisParams = this.state.analysisParams || {};
            const storedProbeVoltages = analysisParams.probe_voltages;
            if (storedProbeVoltages && storedProbeVoltages.length > 0) {
                probeVoltages.push(...storedProbeVoltages);
            }
        }

        if (!probeVoltages || probeVoltages.length === 0) {
            // Hide probe plot if no probe voltages are configured
            const plotContainer = document.getElementById('cv-probe-plot-container');
            if (plotContainer) {
                plotContainer.style.display = 'none';
            }
            return;
        }

        // Extract probe data from results
        const probeDataSeries = {};
        probeVoltages.forEach((voltage, voltageIndex) => {
            probeDataSeries[`probe_${voltageIndex + 1}_forward`] = [];
            probeDataSeries[`probe_${voltageIndex + 1}_reverse`] = [];
        });

        fileNumbers.forEach(fileNum => {
            const result = electrodeResults[fileNum];

            if (result && result.status === 'success' && result.probe_data) {
                const forwardProbes = result.probe_data.forward || [];
                const reverseProbes = result.probe_data.reverse || [];

                probeVoltages.forEach((voltage, voltageIndex) => {
                    if (forwardProbes[voltageIndex]) {
                        probeDataSeries[`probe_${voltageIndex + 1}_forward`].push({
                            x: fileNum,
                            y: forwardProbes[voltageIndex].current
                        });
                    }
                    if (reverseProbes[voltageIndex]) {
                        probeDataSeries[`probe_${voltageIndex + 1}_reverse`].push({
                            x: fileNum,
                            y: reverseProbes[voltageIndex].current
                        });
                    }
                });
            }
        });

        // Create plot if we have data
        const plotElement = document.getElementById('cv-probe-plot');
        if (!plotElement || !window.Plotly) return;

        // Show the plot container
        const plotContainer = document.getElementById('cv-probe-plot-container');
        if (plotContainer) {
            plotContainer.style.display = 'block';
        }

        const traces = [];
        const colors = ['red', 'blue', 'green', 'orange']; // Colors for different probe voltages

        probeVoltages.forEach((voltage, voltageIndex) => {
            const forwardData = probeDataSeries[`probe_${voltageIndex + 1}_forward`];
            const reverseData = probeDataSeries[`probe_${voltageIndex + 1}_reverse`];
            const color = colors[voltageIndex % colors.length];

            if (forwardData.length > 0) {
                traces.push({
                    x: forwardData.map(p => p.x),
                    y: forwardData.map(p => p.y),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${voltage}V Forward`,
                    line: { color: color, width: 2 },
                    marker: { size: 6 }
                });
            }

            if (reverseData.length > 0) {
                traces.push({
                    x: reverseData.map(p => p.x),
                    y: reverseData.map(p => p.y),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${voltage}V Reverse`,
                    line: { color: color, width: 2, dash: 'dash' },
                    marker: { size: 6 }
                });
            }
        });

        if (traces.length === 0) {
            const plotContainer = document.getElementById('cv-probe-plot-container');
            if (plotContainer) {
                plotContainer.style.display = 'none';
            }
            return;
        }

        const layout = {
            title: 'Probe Voltage Currents vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: { title: `Current (${this.dom.settings.currentUnitsInput.value})` },
            margin: { l: 70, r: 50, t: 50, b: 60 }
        };

        Plotly.react(plotElement, traces, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
            displaylogo: false
        });
    }

    _displayCVSummary(analysisResult) {
        // This function would display CV analysis summary
        // For now, keep the existing summary display logic
        console.log('CV Summary:', {
            forward_peak: analysisResult.forward?.peak_potential,
            reverse_peak: analysisResult.reverse?.peak_potential,
            peak_separation: analysisResult.peak_separation
        });
    }

    _displayCVPreview(cvData) {
        // Use PlotlyPlotter to display CV preview
        console.log('_displayCVPreview called with:', cvData);
        console.log('cvPreviewPlot element:', this.dom.cvPreviewPlot);

        if (cvData && cvData.voltage && cvData.current) {
            console.log('CV data valid - voltage points:', cvData.voltage.length, 'current points:', cvData.current.length);
            console.log('Raw voltage range:', Math.min(...cvData.voltage), 'to', Math.max(...cvData.voltage));
            console.log('Raw current range:', Math.min(...cvData.current), 'to', Math.max(...cvData.current));

            // Apply unit conversion to match user settings
            const convertedData = this._convertCVDataUnits(cvData);

            console.log('Converted voltage range:', Math.min(...convertedData.voltage), 'to', Math.max(...convertedData.voltage));
            console.log('Converted current range:', Math.min(...convertedData.current), 'to', Math.max(...convertedData.current));

            // Store converted CV data for segment highlighting
            this.state.originalCVData = {
                voltage: convertedData.voltage,
                current: convertedData.current
            };

            const plotData = [{
                x: convertedData.voltage,
                y: convertedData.current,
                type: 'scatter',
                mode: 'lines',
                name: 'CV Preview',
                line: { color: '#1f77b4', width: 2 }
            }];

            // Get unit settings for axis labels
            const voltageUnits = this.dom.settings.voltageUnitsInput.value;
            const currentUnits = this.dom.settings.currentUnitsInput.value;

            const layout = {
                title: 'CV Preview - Select Segments',
                xaxis: {
                    title: `Voltage (${voltageUnits})`,
                    showgrid: true,
                    zeroline: true,
                    autorange: true
                },
                yaxis: {
                    title: `Current (${currentUnits})`,
                    showgrid: true,
                    zeroline: true,
                    autorange: true
                },
                margin: { t: 50, r: 50, b: 50, l: 80 },
                showlegend: false,
                autosize: true
            };

            console.log('About to call Plotly.newPlot with:', plotData, layout);
            try {
                // Clear the container first
                this.dom.cvPreviewPlot.innerHTML = '';

                // Create the plot with proper configuration
                Plotly.newPlot(this.dom.cvPreviewPlot, plotData, layout, {
                    responsive: true,
                    displayModeBar: true,  // Show toolbar for zoom controls
                    modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'],
                    displaylogo: false
                });

                // Ensure the plot resizes when container changes
                setTimeout(() => {
                    if (window.Plotly && this.dom.cvPreviewPlot) {
                        Plotly.Plots.resize(this.dom.cvPreviewPlot);
                        // Force relayout to fix axis scaling
                        Plotly.relayout(this.dom.cvPreviewPlot, {
                            'xaxis.autorange': true,
                            'yaxis.autorange': true
                        });
                    }
                }, 200);

                console.log('Plotly.newPlot completed successfully');
            } catch (error) {
                console.error('Error calling Plotly.newPlot:', error);
            }
        } else {
            console.error('CV data invalid or missing:', {
                cvData: !!cvData,
                voltage: cvData ? !!cvData.voltage : false,
                current: cvData ? !!cvData.current : false,
                voltageLength: cvData && cvData.voltage ? cvData.voltage.length : 'N/A',
                currentLength: cvData && cvData.current ? cvData.current.length : 'N/A'
            });
        }
    }

    _resetAnalysis() {
        this.state.isAnalysisRunning = false;
        this.state.cvResults = {};
        this.state.previewFileContent = null;
        this.state.availableSegments = [];
        this.state.segmentInfo = {};
        this.state.forwardSegments = [];
        this.state.reverseSegments = [];
        this.state.originalCVData = null;
        this.state.currentScreen = 'settings';
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;

        // Clear any pending timeouts
        if (this._segmentDetectionTimeoutId) {
            clearTimeout(this._segmentDetectionTimeoutId);
            this._segmentDetectionTimeoutId = null;
        }

        // Clean up CV-specific content from shared visualization area
        this._cleanupVisualizationArea();
    }

    _resetAnalysisState() {
        this.state.isAnalysisRunning = false;
        this.dom.startAnalysisBtn.disabled = false;
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
    }

    _cleanupVisualizationArea() {
        const visualizationArea = document.getElementById('visualizationArea');
        if (!visualizationArea) return;

        console.log('Cleaning up CV visualization area...');

        // Remove all CV-specific elements
        const elementsToRemove = [
            '.cv-main-container',           // Main CV layout
            '.cv-plot-container',           // Individual CV plots
            '.cv-summary-plots',            // Summary plots container
            '#cv-forward-plot',             // Forward plot
            '#cv-reverse-plot',             // Reverse plot
            '#cv-peak-separation-plot',     // Peak separation plot
            '#cv-auc-plot',                 // AUC plot
            '#cv-probe-plot-container',     // Probe plot container
            '.analysis-summary'             // Text summaries
        ];

        elementsToRemove.forEach(selector => {
            const elements = visualizationArea.querySelectorAll(selector);
            elements.forEach(element => {
                console.log(`Removing CV element: ${selector}`);
                element.remove();
            });
        });

        // Reset visualization area title
        const titleElement = visualizationArea.querySelector('h2');
        if (titleElement) {
            titleElement.textContent = 'Data Visualization';
        }

        // Hide electrode controls since we're leaving CV
        const electrodeControls = document.getElementById('electrodeControls');
        if (electrodeControls) {
            electrodeControls.style.display = 'none';
            // Clear electrode buttons
            const existingButtons = electrodeControls.querySelectorAll('.electrode-btn');
            existingButtons.forEach(btn => btn.remove());
        }

        // Restore SWV trend plots container visibility and structure
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            trendPlotsContainer.style.display = '';

            // Restore trend plots structure if it was damaged
            const peakPlot = document.getElementById('peakCurrentTrendPlot');
            const normalizedPlot = document.getElementById('normalizedPeakTrendPlot');
            const kdmPlot = document.getElementById('kdmTrendPlot');

            if (!peakPlot || !normalizedPlot || !kdmPlot) {
                console.log('CV Cleanup: Restoring SWV trend plots structure...');
                trendPlotsContainer.innerHTML = `
                    <!-- Peak Current Trend Plot -->
                    <div class="border rounded-lg p-4 bg-gray-50">
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Peak Current Trend</h4>
                        <div id="peakCurrentTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                            Loading...
                        </div>
                    </div>

                    <!-- Normalized Peak Current Trend Plot -->
                    <div class="border rounded-lg p-4 bg-gray-50">
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Normalized Peak Current Trend</h4>
                        <div id="normalizedPeakTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                            Loading...
                        </div>
                    </div>

                    <!-- KDM Trend Plot -->
                    <div class="border rounded-lg p-4 bg-gray-50">
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">KDM Trend</h4>
                        <div id="kdmTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                            Loading...
                        </div>
                    </div>
                `;
                console.log('CV Cleanup: SWV trend plots structure restored');
            }

            console.log('Restored trendPlotsContainer visibility for SWV');
        }

        console.log('CV visualization area cleanup complete');
    }

    _highlightSegmentsOnPreview() {
        // Add colored segment overlays to preserve original CV curve shape
        if (!this.dom.cvPreviewPlot || !window.Plotly) {
            console.warn('Cannot highlight segments: Plot or Plotly not available');
            return;
        }

        if (!this.state.segmentInfo || Object.keys(this.state.segmentInfo).length === 0) {
            console.warn('No segment information available for highlighting');
            return;
        }

        if (!this.state.originalCVData) {
            console.warn('No original CV data available for highlighting');
            return;
        }

        try {
            console.log('Adding colored segment highlighting while preserving CV curve shape');

            const plotElement = this.dom.cvPreviewPlot;

            // Store the current axis ranges to prevent rescaling
            const currentLayout = plotElement.layout || {};
            const xRange = currentLayout.xaxis ? currentLayout.xaxis.range : null;
            const yRange = currentLayout.yaxis ? currentLayout.yaxis.range : null;

            // Start with the original CV data as the base trace (grayed out)
            const allTraces = [{
                x: this.state.originalCVData.voltage,
                y: this.state.originalCVData.current,
                mode: 'lines',
                type: 'scatter',
                name: 'Full CV',
                line: {
                    color: 'rgba(150, 150, 150, 0.3)',  // Light gray background
                    width: 1
                },
                showlegend: true,
                hoverinfo: 'skip'  // Don't show hover for background trace
            }];

            // Add colored segment overlays on top
            Object.entries(this.state.segmentInfo).forEach(([segmentNum, segInfo]) => {
                const segmentType = segInfo.type || 'unknown';
                const potentials = segInfo.potentials || [];
                const currents = segInfo.currents || [];

                if (potentials.length === 0 || currents.length === 0) {
                    console.warn(`Segment ${segmentNum} has no data points`);
                    return;
                }

                // Apply unit conversion to segment data to match preview
                const convertedSegmentData = this._convertCVDataUnits({
                    voltage: potentials,
                    current: currents
                });

                // Choose colors based on segment type
                const color = segmentType === 'forward' ?
                    'rgba(0, 120, 255, 0.9)' :   // Blue for forward
                    'rgba(255, 100, 0, 0.9)';    // Orange for reverse

                const name = `Segment ${segmentNum} (${segmentType})`;

                // Create colored overlay trace for this segment
                allTraces.push({
                    x: convertedSegmentData.voltage,
                    y: convertedSegmentData.current,
                    mode: 'lines',
                    type: 'scatter',
                    name: name,
                    line: {
                        color: color,
                        width: 4  // Thicker for visibility on top
                    },
                    showlegend: true,
                    hovertemplate: `${name}<br>Voltage: %{x:.3f}${voltageUnits}<br>Current: %{y:.3e}${currentUnits}<extra></extra>`
                });
            });

            if (allTraces.length <= 1) {
                console.warn('No segment traces created');
                return;
            }

            // Create updated layout, preserving zoom and improving axes labels
            const currentUnits = this.dom.settings.currentUnitsInput.value;
            const voltageUnits = this.dom.settings.voltageUnitsInput.value;

            const updatedLayout = {
                title: 'CV Preview - Highlighted Segments',
                xaxis: {
                    title: `Voltage (${voltageUnits})`,
                    showgrid: true,
                    zeroline: true,
                    range: xRange || undefined,  // Preserve zoom if available
                    autorange: xRange ? false : true
                },
                yaxis: {
                    title: `Current (${currentUnits})`,
                    showgrid: true,
                    zeroline: true,
                    range: yRange || undefined,  // Preserve zoom if available
                    autorange: yRange ? false : true
                },
                margin: { t: 50, r: 50, b: 50, l: 80 },
                showlegend: true,
                legend: {
                    x: 1.02,
                    y: 1,
                    xanchor: 'left',
                    yanchor: 'top',
                    bgcolor: 'rgba(255,255,255,0.9)',
                    bordercolor: 'rgba(0,0,0,0.2)',
                    borderwidth: 1
                },
                autosize: true
            };

            // Update the plot with all traces (preserving shape and scale)
            Plotly.react(plotElement, allTraces, updatedLayout, {
                responsive: true,
                displayModeBar: true,
                displaylogo: false
            });

            console.log(`✅ Successfully highlighted ${allTraces.length - 1} segments on original CV curve`);

        } catch (error) {
            console.error('Error highlighting segments on preview:', error);
        }
    }

    _convertCVDataUnits(cvData) {
        // Convert CV data from base units (V, A) to user-selected units
        const voltageUnits = this.dom.settings.voltageUnitsInput.value || 'V';
        const currentUnits = this.dom.settings.currentUnitsInput.value || 'A';

        // Unit conversion factors from base units
        const voltageFactors = {
            'V': 1.0,
            'mV': 1e3,    // V to mV
            'μV': 1e6,    // V to μV
            'nV': 1e9     // V to nV
        };

        const currentFactors = {
            'A': 1.0,
            'mA': 1e3,    // A to mA
            'μA': 1e6,    // A to μA
            'nA': 1e9     // A to nA
        };

        const voltageFactor = voltageFactors[voltageUnits] || 1.0;
        const currentFactor = currentFactors[currentUnits] || 1.0;

        console.log(`Converting units: voltage × ${voltageFactor} (${voltageUnits}), current × ${currentFactor} (${currentUnits})`);

        return {
            voltage: cvData.voltage.map(v => v * voltageFactor),
            current: cvData.current.map(c => c * currentFactor)
        };
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

    _handleCVExport() {
        const electrodeInfo = this.state.currentElectrode !== null ? `_Electrode_${this.state.currentElectrode + 1}` : '_Averaged';
        const defaultFilename = `CV_Analysis${electrodeInfo}_${new Date().toISOString().slice(0, 10)}.csv`;
        const filename = prompt("Please enter a filename for the CV export:", defaultFilename);
        if (filename) {
            this.dom.visualization.exportCVDataBtn.dataset.filename = filename;
            this.dom.visualization.exportStatus.textContent = 'Generating CV export file...';
            // Send current electrode info to server for correct data export
            this.socketManager.emit('request_export_cv_data', {
                current_electrode: this.state.currentElectrode
            });
        }
    }

    _triggerCsvDownload(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    _updateProbeLines() {
        const voltage1 = parseFloat(this.dom.visualization.probeVoltage1Input.value);
        const voltage2 = parseFloat(this.dom.visualization.probeVoltage2Input.value);

        // Store probe voltages for later use in analysis
        this.state.probeVoltages = [];
        if (!isNaN(voltage1)) this.state.probeVoltages.push(voltage1);
        if (!isNaN(voltage2)) this.state.probeVoltages.push(voltage2);

        // Update the preview plot with probe lines
        this._addProbeLinesToPreview();
    }

    _addProbeLinesToPreview() {
        const plotElement = this.dom.cvPreviewPlot;
        if (!plotElement || !window.Plotly || !this.state.probeVoltages) return;

        // Get existing plot data
        const plotData = plotElement.data;
        const plotLayout = plotElement.layout;

        if (!plotData || !plotLayout) return;

        // Remove existing probe line shapes if any
        let shapes = plotLayout.shapes || [];
        shapes = shapes.filter(shape => !shape.name || !shape.name.startsWith('probe_line_'));

        // Add new probe lines
        this.state.probeVoltages.forEach((voltage, index) => {
            const voltageUnits = this.dom.settings.voltageUnitsInput.value;
            const voltageInBaseUnits = this._convertToBaseUnits(voltage, voltageUnits);

            shapes.push({
                type: 'line',
                name: `probe_line_${index + 1}`,
                x0: voltageInBaseUnits,
                x1: voltageInBaseUnits,
                y0: 0,
                y1: 1,
                yref: 'paper',
                line: {
                    color: index === 0 ? 'red' : 'orange',
                    width: 2,
                    dash: 'dash'
                }
            });
        });

        // Update the layout with new shapes
        const updatedLayout = {
            ...plotLayout,
            shapes: shapes
        };

        Plotly.relayout(plotElement, updatedLayout);
        console.log(`✅ Updated probe lines for voltages: ${this.state.probeVoltages.join(', ')}V`);
    }

    _convertToBaseUnits(value, unit) {
        const voltageFactors = {
            'V': 1.0,
            'mV': 1e-3,
            'μV': 1e-6,
            'nV': 1e-9
        };
        return value * (voltageFactors[unit] || 1.0);
    }
}
