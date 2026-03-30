// static/js/cv_module.js - CV Analysis Module

import { PlotlyPlotter } from './plot_utils.js';
import { bindIfPresent, clearChildren, getById, getAll, resetSelectOptions, setClassNameIfPresent, setTextIfPresent } from './dom_utils.js';

const CV_DEBUG = false;
const cvDebug = (...args) => {
    if (CV_DEBUG) console.log(...args);
};
const cvWarnDebug = (...args) => {
    if (CV_DEBUG) console.warn(...args);
};

export class CVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        cvDebug('Initializing CV Module');

        this.dom = {
            cvBtn: getById('cvBtn'),
            backToWelcomeBtn: getById('backToWelcomeFromCV'),
            backToCVSettingsBtn: getById('backToCVSettingsBtn'),
            nextToVisualizationBtn: getById('cvNextToVisualizationBtn'),
            startAnalysisBtn: getById('startCVAnalysisBtn'),
            status: getById('cvStatus'),
            folderStatus: getById('cvFolderStatus'),
            detectSegmentsBtn: getById('detectCVSegmentsBtn'),
            segmentStatus: getById('cvSegmentStatus'),
            cvPreviewPlot: getById('cvPreviewPlot'),
            folderPathInput: getById('cvFolderPathInput'),
            params: {
                fileHandleInput: getById('cvFileHandleInput'),
                numFilesInput: getById('cvNumFilesInput'),
                selectedElectrodesInput: getById('cvSelectedElectrodesInput'),
                scanRateInput: getById('cvScanRateInput'),
                lowVoltageInput: getById('cvLowVoltageInput'),
                highVoltageInput: getById('cvHighVoltageInput'),
                massTransportInput: getById('cvMassTransportInput'),
                analysisOptionsInput: getById('cvAnalysisOptionsInput'),
            },
            visualization: {
                forwardSegmentInput: getById('cvForwardSegmentInput'),
                reverseSegmentInput: getById('cvReverseSegmentInput'),
                peakMinVoltageInput: getById('cvPeakMinVoltageInput'),
                peakMaxVoltageInput: getById('cvPeakMaxVoltageInput'),
                probeVoltage1Input: getById('cvProbeVoltage1Input'),
                probeVoltage2Input: getById('cvProbeVoltage2Input'),
                updateProbeBtn: getById('updateProbeBtn'),
                resultsScreen: getById('cvResultsScreen'),
                resultsTitle: getById('cvResultsTitle'),
                resultsRoot: getById('cvResultsRoot'),
                electrodeControls: getById('cvElectrodeControls'),
                backToSettingsBtn: getById('backToCVResultsSettingsBtn'),
                exportCVDataBtn: getById('exportCVDataBtn'),
                exportStatus: getById('cvExportStatus'),
            },
            settings: {
                voltageColumnInput: getById('cvVoltageColumnInput'),
                currentColumnInput: getById('cvCurrentColumnInput'),
                spacingIndexInput: getById('cvSpacingIndexInput'),
                delimiterInput: getById('cvDelimiterInput'),
                fileExtensionInput: getById('cvFileExtensionInput'),
                sgModeInputs: getAll('input[name="cvSgMode"]'),
                sgWindowInput: getById('cvSgWindowInput'),
                sgDegreeInput: getById('cvSgDegreeInput'),
                sampleRateInput: getById('cvSampleRateInput'),
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
        cvDebug('CV Module DOM elements check:');
        cvDebug('cvPreviewPlot element:', this.dom.cvPreviewPlot);
        cvDebug('segmentStatus element:', this.dom.segmentStatus);

        if (!this.dom.cvPreviewPlot) {
            console.error('[ERROR] cvPreviewPlot element not found!');
        }
        if (!this.dom.segmentStatus) {
            console.error('[ERROR] segmentStatus element not found!');
        }

        this._setupEventListeners();
        this._setupSocketHandlers();
    }

    _setupEventListeners() {
        bindIfPresent(this.dom.cvBtn, 'click', () => {
            this.state.currentScreen = 'settings';
            this.uiManager.showScreen('cvAnalysisScreen');
        });

        bindIfPresent(this.dom.backToWelcomeBtn, 'click', () => {
            this.uiManager.showScreen('welcomeScreen');
            this._resetAnalysis();
        });

        bindIfPresent(this.dom.backToCVSettingsBtn, 'click', () => {
            this.state.currentScreen = 'settings';
            this.uiManager.showScreen('cvAnalysisScreen');
        });
        bindIfPresent(this.dom.visualization.backToSettingsBtn, 'click', () => {
            this._returnToSettings();
        });

        bindIfPresent(this.dom.nextToVisualizationBtn, 'click', this._handleNextToVisualization.bind(this));
        bindIfPresent(this.dom.startAnalysisBtn, 'click', this._handleStartAnalysis.bind(this));
        bindIfPresent(this.dom.detectSegmentsBtn, 'click', this._handleDetectSegments.bind(this));

        bindIfPresent(this.dom.visualization.exportCVDataBtn, 'click', this._handleCVExport.bind(this));

        bindIfPresent(this.dom.visualization.updateProbeBtn, 'click', this._updateProbeLines.bind(this));

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

    _returnToSettings() {
        cvDebug('Returning to CV settings - stopping analysis and clearing all data');

        if (this.state.isAnalysisRunning) {
            cvDebug('Stopping active CV analysis session...');
            this.socketManager.emit('stop_cv_analysis_session', { reason: 'user_returned_to_settings' });
        }

        this.state.cvResults = {};
        this.state.currentElectrode = null;
        this.state.selectedElectrodes = [];
        this.state.probeVoltages = [];
        this.state.numElectrodes = 0;
        this.state.isAnalysisRunning = false;
        this.state.currentScreen = 'settings';

        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;

        this._cleanupVisualizationArea();
        this.uiManager.showScreen('cvAnalysisScreen');
    }

    _getSelectedRadioValue(name) {
        const selected = document.querySelector(`input[name="${name}"]:checked`);
        return selected ? selected.value : null;
    }

    _setupSocketHandlers() {
        this.socketManager.on('connect', () => {
            console.log('✅ CV Module: Socket connected');

            // LOCAL MODE: No agent needed, hide agent status
            setTextIfPresent(this.dom.status, 'Local mode - ready');
            setClassNameIfPresent(this.dom.status, 'text-sm text-green-600 mt-1');
        });

        this.socketManager.on('disconnect', (reason) => {
            console.log('[ERROR] CV Module: Socket disconnected. Reason:', reason);
            // Clear any pending timeouts
            if (this._segmentDetectionTimeoutId) {
                clearTimeout(this._segmentDetectionTimeoutId);
                this._segmentDetectionTimeoutId = null;
            }

            // Update UI to show disconnection
            setTextIfPresent(this.dom.status, `Connection lost: ${reason}. Reconnecting...`);
            setClassNameIfPresent(this.dom.status, 'text-sm text-red-600 mt-1');
        });

        this.socketManager.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 CV Module: Reconnection attempt ${attemptNumber}`);
        });

        this.socketManager.on('reconnect_error', (error) => {
            console.error('[ERROR] CV Module: Reconnection error:', error);
        });

        // CV session started confirmation
        this.socketManager.on('cv_session_started', (data) => {
            console.log('✅ CV session started:', data);
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'CV session started. Monitoring for CV files...';

                // Mark analysis as running so live_cv_update events are processed
                this.state.isAnalysisRunning = true;
                this.state.currentScreen = 'visualization';

                // Switch to visualization area after session starts
                console.log('Switching to visualization area...');
                this.uiManager.showScreen('cvResultsScreen');
                this._setupCVVisualization('normal');
            } else {
                this.dom.folderStatus.textContent = data.message || 'Error starting CV session';
                this._resetAnalysisState();

                // Show alert for errors
                if (data.message) {
                    alert('Error starting CV session: ' + data.message);
                }
            }
        });

        // Legacy event name support
        this.socketManager.on('ack_start_cv_session', (data) => {
            console.log('✅ CV session ack (legacy):', data);
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'CV session started. Monitoring for CV files...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this._resetAnalysisState();

                if (data.message) {
                    alert('Error starting CV session: ' + data.message);
                }
            }
        });

        // Debug: Log all socket events to see what we're receiving
        console.log('Setting up CV preview response handler');

        this.socketManager.on('cv_preview_response', (data) => {
            console.log('✅ CV Preview Response received:', data);
            cvDebug('Response type:', typeof data, 'Keys:', Object.keys(data || {}));

            if (data && data.status === 'success') {
                console.log('CV preview success, checking cv_data:', data.cv_data);
                cvDebug('Content length:', data.content ? data.content.length : 'No content');

                if (data.cv_data && data.cv_data.voltage && data.cv_data.current) {
                    console.log('CV data looks valid, calling _displayCVPreview');
                    this.state.previewFileContent = data.content;
                    this.state.numElectrodes = data.num_electrodes || 0;
                    console.log(`Detected ${this.state.numElectrodes} electrodes in file`);
                    this._displayCVPreview(data.cv_data);
                    this.dom.segmentStatus.textContent = `CV preview loaded (${this.state.numElectrodes} electrodes detected). Click "Detect Segments" to analyze.`;
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

        // Handle CV segments processing acknowledgment
        this.socketManager.on('cv_segments_processing', (data) => {
            console.log('📝 [CV SEGMENTS] Processing acknowledgment received:', data);
            if (this.dom.segmentStatus) {
                this.dom.segmentStatus.textContent = data.message || 'Starting segment detection...';
                this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
            }
        });

        // New: Handle CV segments progress updates
        this.socketManager.on('cv_segments_progress', (data) => {
            console.log('[PLOT] [CV SEGMENTS] Progress update received:', data);
            if (this.dom.segmentStatus) {
                const progressText = data.progress ? ` (${data.progress}%)` : '';
                this.dom.segmentStatus.textContent = `${data.message}${progressText}`;
                this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';
            }
        });

        this.socketManager.on('cv_segments_response', (data) => {
            console.log('✅ [CV SEGMENTS] Final response received:', data);
            cvDebug('Response status:', data ? data.status : 'NO DATA');
            cvDebug('Response segments:', data ? data.segments : 'NO SEGMENTS');

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
                const match = data.filename.match(/CV_\d+Hz_(\d+)\./) || data.filename.match(/_(\d+)\./);
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
                        this.uiManager.showScreen('cvResultsScreen');
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
                this.uiManager.showScreen('cvResultsScreen');
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
                const filename = data.filename || this.dom.visualization.exportCVDataBtn.dataset.filename || 'cv_export.xlsx';
                this.dom.visualization.exportStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerWorkbookDownload(data.content_b64, filename);
            } else {
                this.dom.visualization.exportStatus.textContent = `Export failed: ${data.message}`;
            }
        });
    }

    /**
     * PUBLIC METHOD: Populate historical CV data for Monitor Mode
     * Called when a monitor device enters monitor mode and receives existing CV analysis data
     */
    populateHistoricalData(historicalData) {
        console.log('CV Module: Populating historical data for monitor mode', historicalData);

        const segmentsData = historicalData.segments_data;
        const cvResults = historicalData.cv_results;
        const analysisParams = historicalData.analysis_params;

        if (!cvResults || Object.keys(cvResults).length === 0) {
            console.warn('No CV results data to populate');
            return;
        }

        // Mark as analysis running (in monitor mode)
        this.state.isAnalysisRunning = true;
        this.state.currentScreen = 'visualization';

        // Determine which electrode to display
        const selectedElectrode = analysisParams?.selected_electrode;
        if (selectedElectrode !== undefined && selectedElectrode !== null) {
            this.state.currentElectrode = selectedElectrode;
        } else {
            // Use first available electrode
            const electrodes = Object.keys(cvResults);
            if (electrodes.length > 0) {
                const firstElectrode = electrodes[0];
                this.state.currentElectrode = firstElectrode !== 'averaged' ?
                                               parseInt(firstElectrode) : null;
            }
        }

        // Populate CV results structure
        // cvResults structure: { '0': {fileNum: {forward: ..., reverse: ...}}, '1': {...}, 'averaged': {...} }
        this.state.cvResults = cvResults;

        // Populate segment data if available
        if (segmentsData && Object.keys(segmentsData).length > 0) {
            this.state.availableSegments = segmentsData.segments || [];
            this.state.segmentInfo = segmentsData.segment_info || {};
            this.state.forwardSegments = segmentsData.forward_segments || [];
            this.state.reverseSegments = segmentsData.reverse_segments || [];
        }

        // Navigate directly to the dedicated CV results screen
        this.uiManager.showScreen('cvResultsScreen');

        // Set up electrode controls
        this._setupCVElectrodeControls();

        // Set up and render CV visualization
        this._setupCVVisualization();

        console.log('CV historical data populated successfully');
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

        // Get folder path
        const folderPath = this.dom.folderPathInput ? this.dom.folderPathInput.value.trim() : '';

        const filters = {
            folder_path: folderPath,
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: 1 // Just get the first file for preview
        };

        cvDebug('Requesting CV preview with filters:', filters);
        cvDebug('Analysis params (modified for preview):', analysisParams);

        this.dom.segmentStatus.textContent = 'Loading CV preview...';
        this.dom.segmentStatus.className = 'text-sm text-blue-600 mt-2';

        // Request the first file for preview
        cvDebug('Emitting get_cv_preview event');
        cvDebug('Socket connected:', this.socketManager.socket.connected);
        cvDebug('Socket ID:', this.socketManager.socket.id);

        this.socketManager.emit('get_cv_preview', { filters, analysisParams });

        // Set a timeout to check if we get a response
        setTimeout(() => {
            if (this.dom.segmentStatus.textContent === 'Loading CV preview...') {
                cvWarnDebug('[WARN] No CV preview response received after 5 seconds');
                this.dom.segmentStatus.textContent = 'Timeout: No response from server. Check the local backend and selected folder.';
                this.dom.segmentStatus.className = 'text-sm text-yellow-600 mt-2';
            }
        }, 5000);
    }

    _handleDetectSegments() {
        if (!this.state.previewFileContent) {
            cvDebug('No preview file content, requesting preview first...');
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

        cvDebug('=== Segment Detection Request ===');
        cvDebug('Preview file content length:', this.state.previewFileContent.length);
        cvDebug('Preview file content preview omitted');
        cvDebug('Analysis params:', analysisParams);

        const requestData = {
            // Don't send content - backend will use stored preview content from session
            // This avoids sending large payloads that cause socket disconnection
            content: '',  // Empty - backend will fetch from session
            filename: 'preview_cv_file.txt',
            params: analysisParams
        };

        cvDebug('=== Sending Segment Detection Request ===');
        cvDebug('Request data (content excluded for performance):', {
            filename: requestData.filename,
            params: requestData.params,
            contentLength: this.state.previewFileContent ? this.state.previewFileContent.length : 0
        });
        cvDebug('Socket connected:', this.socketManager.socket.connected);
        cvDebug('Socket id:', this.socketManager.socket.id);

        try {
            this.socketManager.emit('get_cv_segments', requestData);
            console.log('✅ Segment detection request emitted via socket');
            cvDebug('Waiting for server response (using session-stored preview content)...');
        } catch (error) {
            console.error('[ERROR] Failed to emit segment detection request:', error);
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

                console.warn('[WARN] Segment detection timeout after 30 seconds');
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
        resetSelectOptions(this.dom.visualization.forwardSegmentInput, 'Auto-detect', '');
        resetSelectOptions(this.dom.visualization.reverseSegmentInput, 'Auto-detect', '');

        // Add detected segments with type classification
        this.state.availableSegments.forEach(segment => {
            const segInfo = this.state.segmentInfo[segment] || {};
            const segmentType = segInfo.type || 'unknown';
            const points = segInfo.points || 0;
            const range = segInfo.potential_range || [0, 0];

            // Create descriptive labels
            const forwardLabel = `Segment ${segment} (${segmentType}, ${points} pts, ${range[0].toFixed(2)}V to ${range[1].toFixed(2)}V)`;
            const reverseLabel = `Segment ${segment} (${segmentType}, ${points} pts, ${range[0].toFixed(2)}V to ${range[1].toFixed(2)}V)`;

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
            voltage_units: 'V',
            current_units: 'A',
            sg_mode: this._getSelectedRadioValue('cvSgMode'),
            sg_window: this._getSelectedRadioValue('cvSgMode') === 'manual' ? parseInt(this.dom.settings.sgWindowInput.value) : undefined,
            sg_degree: this._getSelectedRadioValue('cvSgMode') === 'manual' ? parseInt(this.dom.settings.sgDegreeInput.value) : undefined,
            probe_voltages: this.state.probeVoltages || [],
            sample_rate: parseFloat(this.dom.settings.sampleRateInput.value),
        };
    }

    _handleStartAnalysis() {
        if (!window.cvFolderMonitor?.isMonitoring) {
            alert('Please start folder monitoring before starting analysis.');
            return;
        }

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
                alert("Please enter valid electrode numbers (starting from 1).");
                return;
            }

            // Validate electrodes are within range
            if (this.state.numElectrodes > 0) {
                const invalidElectrodes = selectedElectrodes.filter(e => e >= this.state.numElectrodes);
                if (invalidElectrodes.length > 0) {
                    const invalidDisplay = invalidElectrodes.map(e => e + 1).join(', ');
                    alert(`Error: Electrode(s) ${invalidDisplay} do not exist.\n\nDetected ${this.state.numElectrodes} electrode(s) in the file.\nValid electrode numbers: 1-${this.state.numElectrodes}`);
                    return;
                }
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
            numElectrodes: this.state.numElectrodes || 0,  // Preserve detected electrode count
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

        // Get folder path for monitoring
        const folderPath = this.dom.folderPathInput ? this.dom.folderPathInput.value.trim() : '';

        const filters = {
            folder_path: folderPath,
            handle: this.dom.params.fileHandleInput.value.trim(),
            range_start: 1,
            range_end: numFiles,
            frequencies: [60]  // CV files use 60Hz by default
        };

        this.dom.startAnalysisBtn.textContent = 'CV Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending CV instructions to server...";

        // Start CV analysis session (local mode - no agent needed)
        this.socketManager.emit('start_cv_analysis_session', {
            filters,
            analysisParams
        });

        // Set up timeout to automatically switch to visualization if no data is received
        this._setupCVAnalysisTimeout();
    }

    _setupCVVisualization(reason = 'normal') {
        // Set up CV-specific visualization in the shared visualization area
        const resultsRoot = this.dom.visualization.resultsRoot;
        if (!resultsRoot) return;

        // Hide SWV/FM containers — their data is preserved, SWV will restore visibility when switching back
        // Update the title for CV analysis
        const titleElement = this.dom.visualization.resultsTitle;
        if (titleElement) {
            if (reason === 'timeout_no_data') {
                titleElement.textContent = 'CV Analysis - No Data Received';
            } else if (reason === 'timeout_with_data') {
                titleElement.textContent = 'CV Analysis - Partial Results';
            } else {
                titleElement.textContent = 'CV Data Visualization';
            }
        }

        const exportCVDataBtn = this.dom.visualization.exportCVDataBtn;
        if (exportCVDataBtn) exportCVDataBtn.classList.remove('hidden');

        // Set up electrode controls if needed
        this._setupCVElectrodeControls();

        // Create comprehensive CV plots area
        this._createCVSummaryPlots();

        // Display CV results
        this._displayCVResults();
    }

    _setupCVElectrodeControls() {
        const electrodeControls = this.dom.visualization.electrodeControls;
        if (!electrodeControls) return;

        electrodeControls.classList.remove('hidden');

        // Clear existing buttons
        const existingButtons = electrodeControls.querySelectorAll('.electrode-btn');
        existingButtons.forEach(btn => btn.remove());

        // Get actual available electrodes from CV results
        const availableElectrodes = Object.keys(this.state.cvResults).filter(key => key !== 'averaged');
        console.log('CV: Available electrodes in results:', availableElectrodes);
        console.log('CV: Selected electrodes:', this.state.selectedElectrodes);

        // Add "Averaged" button if no specific electrodes selected
        if (this.state.selectedElectrodes.length === 0) {
            const avgBtn = document.createElement('button');
            avgBtn.className = 'electrode-btn px-4 py-2 text-sm font-medium rounded-lg border bg-blue-500 text-white';
            avgBtn.textContent = 'Averaged';
            avgBtn.disabled = true; // Current selection
            electrodeControls.appendChild(avgBtn);
        } else {
            // Add buttons for each selected electrode, but only if data exists
            this.state.selectedElectrodes.forEach(electrodeIdx => {
                const electrodeKey = electrodeIdx.toString();
                const hasData = availableElectrodes.includes(electrodeKey);

                const btn = document.createElement('button');
                btn.className = `electrode-btn px-4 py-2 text-sm font-medium rounded-lg border ${
                    electrodeIdx === this.state.currentElectrode
                        ? 'bg-blue-500 text-white'
                        : hasData
                            ? 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                            : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                }`;
                btn.textContent = `Electrode ${electrodeIdx + 1}`;  // Display as 1-based

                if (hasData) {
                    btn.onclick = () => this._switchCVElectrode(electrodeIdx);
                } else {
                    btn.disabled = true;
                    btn.title = 'No data for this electrode';
                }

                electrodeControls.appendChild(btn);
            });
        }
    }

    _switchCVElectrode(electrodeIdx) {
        if (this.state.currentElectrode === electrodeIdx) {
            console.log(`CV: Already on electrode ${electrodeIdx}, ignoring switch`);
            return;
        }

        console.log(`=== CV Electrode Switch ===`);
        console.log(`Switching from electrode ${this.state.currentElectrode} to ${electrodeIdx}`);
        console.log('Available CV results:', Object.keys(this.state.cvResults));

        const newElectrodeKey = electrodeIdx?.toString() || 'averaged';
        const newElectrodeData = this.state.cvResults[newElectrodeKey];

        if (!newElectrodeData) {
            console.warn(`CV: No data available for electrode ${newElectrodeKey}`);
            alert(`No data available for electrode ${electrodeIdx + 1}. The file may only contain fewer electrodes.`);
            return;
        }

        console.log(`Electrode ${newElectrodeKey} has ${Object.keys(newElectrodeData).length} files`);
        Object.keys(newElectrodeData).forEach(fileNum => {
            const fileData = newElectrodeData[fileNum];
            console.log(`  File ${fileNum}: Forward peak = ${fileData?.forward?.peak_current}, Reverse peak = ${fileData?.reverse?.peak_current}`);
        });

        this.state.currentElectrode = electrodeIdx;
        console.log('CV: Updating UI for new electrode...');
        this._setupCVElectrodeControls(); // Update button states
        this._displayCVResults(); // Refresh plots with new electrode data
        this._updateCVSummaryPlots(); // Update summary plots for new electrode
        console.log('CV: Electrode switch complete');
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
        const cvTextSummaries = this.dom.visualization.resultsRoot
            ? this.dom.visualization.resultsRoot.querySelectorAll('.analysis-summary, .cv-text-summary, .cv-analysis-summary')
            : [];
        cvTextSummaries.forEach(summary => summary.remove());
    }

    _setupCVAnalysisTimeout() {
        // Set up periodic checks and timeouts for CV analysis
        // Dynamic timeout based on number of files: 2 seconds per file + 60 seconds base
        const baseTimeout = 60000; // 60 seconds base
        const timePerFile = 2000; // 2 seconds per file
        const maxWaitTime = baseTimeout + (this.state.currentNumFiles * timePerFile);
        const checkInterval = 2000; // Check every 2 seconds

        console.log(`CV Analysis: Setting timeout to ${maxWaitTime}ms for ${this.state.currentNumFiles} files`);

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

            // Get total number of results across all electrodes
            const numResults = Object.keys(this.state.cvResults).reduce((total, electrode) => {
                return total + Object.keys(this.state.cvResults[electrode] || {}).length;
            }, 0);

            const hasSubstantialResults = numResults >= Math.min(10, this.state.currentNumFiles * 0.2);

            // Only timeout if we've exceeded the dynamic wait time
            // No early timeout based on 60 seconds anymore
            if (timeElapsed > maxWaitTime) {
                if (hasSubstantialResults) {
                    console.log(`CV analysis: Timeout after ${timeElapsed}ms with ${numResults}/${this.state.currentNumFiles} files`);
                    this._completeCVAnalysis('timeout_with_data');
                } else {
                    console.log(`CV analysis: Timeout after ${timeElapsed}ms with no data`);
                    this._completeCVAnalysis('timeout_no_data');
                }
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
        this.uiManager.showScreen('cvResultsScreen');
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
            console.error('[ERROR] No analysis result for real-time update');
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
            console.error('[ERROR] No CV forward/reverse data to visualize in real-time update');
            console.log('[PLOT] Analysis result structure:', JSON.stringify(analysisResult, null, 2));
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
        const resultsRoot = this.dom.visualization.resultsRoot;
        if (!resultsRoot) return;

        // Clear existing plots
        const existingPlots = resultsRoot.querySelectorAll('.cv-plot-container');
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
        const summaryElement = resultsRoot.querySelector('.analysis-summary') || resultsRoot.lastElementChild;
        if (summaryElement) {
            resultsRoot.insertBefore(plotContainer, summaryElement);
        } else {
            resultsRoot.appendChild(plotContainer);
        }
    }

    _createSingleCVPlot(sweepData, title, plotId) {
        const plotDiv = document.createElement('div');
        plotDiv.className = 'bg-white p-4 rounded-lg shadow';
        const heading = document.createElement('h3');
        heading.className = 'text-lg font-semibold mb-2';
        heading.textContent = title;
        const plotContainer = document.createElement('div');
        plotContainer.id = plotId;
        plotContainer.className = 'plotly-plot-container';
        plotDiv.appendChild(heading);
        plotDiv.appendChild(plotContainer);

        // Use setTimeout to ensure DOM is ready
        setTimeout(() => {
            const plotElement = document.getElementById(plotId);
            if (plotElement && window.Plotly) {
                // Convert all data to display units before plotting
                const convertedMain = this._convertCVDataUnits({
                    voltage: sweepData.potentials,
                    current: sweepData.currents
                });

                const traces = [
                    {
                        x: convertedMain.voltage,
                        y: convertedMain.current,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Raw Data',
                        line: { color: 'blue', width: 2 }
                    }
                ];

                // Add corrected data if available
                if (sweepData.corrected_currents) {
                    const convertedCorrected = this._convertCVDataUnits({
                        voltage: sweepData.potentials,
                        current: sweepData.corrected_currents
                    });
                    traces.push({
                        x: convertedCorrected.voltage,
                        y: convertedCorrected.current,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Baseline Corrected',
                        line: { color: 'red', width: 2 }
                    });
                }

                // Add baseline if available
                if (sweepData.baseline) {
                    const convertedBaseline = this._convertCVDataUnits({
                        voltage: sweepData.potentials,
                        current: sweepData.baseline
                    });
                    traces.push({
                        x: convertedBaseline.voltage,
                        y: convertedBaseline.current,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Baseline',
                        line: { color: 'gray', width: 1, dash: 'dash' }
                    });
                }

                // Use auto-selected display units for axis labels
                const voltageUnits = this._displayUnits?.voltage || 'V';
                const currentUnits = this._displayUnits?.current || 'A';

                // Calculate data range for better auto-zoom
                const allYValues = traces.flatMap(trace => trace.y || []);
                const yMin = Math.min(...allYValues);
                const yMax = Math.max(...allYValues);
                const yRange = yMax - yMin;
                const yPadding = yRange * 0.1;  // 10% padding on each side

                const layout = {
                    xaxis: {
                        title: `Potential (${voltageUnits})`,
                        autorange: true
                    },
                    yaxis: {
                        title: `Current (${currentUnits})`,
                        range: [yMin - yPadding, yMax + yPadding],  // Auto-zoom with padding
                        automargin: true
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

    _createCVSummaryPlotCard(title, plotId, heightPx, extraOptions = {}) {
        const card = document.createElement('div');
        card.className = extraOptions.cardClassName || 'bg-white p-4 rounded-lg shadow';
        if (extraOptions.cardId) {
            card.id = extraOptions.cardId;
        }
        if (extraOptions.hidden) {
            card.style.display = 'none';
        }

        const heading = document.createElement('h4');
        heading.className = 'text-sm font-semibold mb-1';
        heading.textContent = title;

        const plot = document.createElement('div');
        plot.id = plotId;
        plot.style.height = `${heightPx}px`;
        plot.style.width = '100%';

        card.appendChild(heading);
        card.appendChild(plot);
        return card;
    }

    _createCVResultsLayout() {
        const mainContainer = document.createElement('div');
        mainContainer.className = 'cv-main-container space-y-4 mt-4';

        const topRow = document.createElement('div');
        topRow.className = 'grid grid-cols-2 gap-4';
        topRow.appendChild(this._createCVSummaryPlotCard('Forward Sweep', 'cv-forward-plot', 320, {
            cardClassName: 'bg-white p-3 rounded-lg shadow'
        }));
        topRow.appendChild(this._createCVSummaryPlotCard('Reverse Sweep', 'cv-reverse-plot', 320, {
            cardClassName: 'bg-white p-3 rounded-lg shadow'
        }));

        const bottomSection = document.createElement('div');
        bottomSection.className = 'space-y-4';
        bottomSection.appendChild(this._createCVSummaryPlotCard('Peak Separation Trend', 'cv-peak-separation-plot', 260));
        bottomSection.appendChild(this._createCVSummaryPlotCard('Peak Height Trend', 'cv-peak-height-plot', 260));
        bottomSection.appendChild(this._createCVSummaryPlotCard('AUC Trend', 'cv-auc-plot', 260));
        bottomSection.appendChild(this._createCVSummaryPlotCard('Probe Voltage Currents', 'cv-probe-plot', 260, {
            cardId: 'cv-probe-plot-container',
            hidden: true
        }));

        mainContainer.appendChild(topRow);
        mainContainer.appendChild(bottomSection);
        return mainContainer;
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

        // Convert all data to display units before plotting
        const convertedMain = this._convertCVDataUnits({
            voltage: sweepData.potentials,
            current: sweepData.currents
        });

        const traces = [
            {
                x: convertedMain.voltage,
                y: convertedMain.current,
                type: 'scatter',
                mode: 'lines',
                name: 'Raw Data',
                line: { color: 'blue', width: 2 }
            }
        ];

        // Add corrected data if available
        if (sweepData.corrected_currents) {
            const convertedCorrected = this._convertCVDataUnits({
                voltage: sweepData.potentials,
                current: sweepData.corrected_currents
            });
            traces.push({
                x: convertedCorrected.voltage,
                y: convertedCorrected.current,
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline Corrected',
                line: { color: 'red', width: 2 }
            });
        }

        // Add baseline if available
        if (sweepData.baseline) {
            const convertedBaseline = this._convertCVDataUnits({
                voltage: sweepData.potentials,
                current: sweepData.baseline
            });
            traces.push({
                x: convertedBaseline.voltage,
                y: convertedBaseline.current,
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline',
                line: { color: 'gray', width: 1, dash: 'dash' }
            });
        }

        // Add peak marker if available
        if (sweepData.peak_potential !== undefined && sweepData.peak_current !== undefined) {
            const convertedPeak = this._convertCVDataUnits({
                voltage: [sweepData.peak_potential],
                current: [sweepData.peak_current]
            });

            // Use auto-selected display units for peak label
            const voltageUnits = this._displayUnits?.voltage || 'V';
            const currentUnits = this._displayUnits?.current || 'A';

            traces.push({
                x: convertedPeak.voltage,
                y: convertedPeak.current,
                type: 'scatter',
                mode: 'markers+text',
                name: 'Peak',
                marker: { color: 'red', size: 10, symbol: 'diamond' },
                text: [`Peak: ${convertedPeak.voltage[0].toFixed(3)} ${voltageUnits}, ${convertedPeak.current[0].toFixed(2)} ${currentUnits}`],
                textposition: 'top center',
                textfont: { size: 10 }
            });
        }

        // Add AUC shading if available
        if (sweepData.auc_vertices && sweepData.auc_vertices.length > 0) {
            const aucVoltages = sweepData.auc_vertices.map(v => v[0]);
            const aucCurrents = sweepData.auc_vertices.map(v => v[1]);
            const convertedAUC = this._convertCVDataUnits({
                voltage: aucVoltages,
                current: aucCurrents
            });
            traces.push({
                x: convertedAUC.voltage,
                y: convertedAUC.current,
                fill: 'tozeroy',
                type: 'scatter',
                mode: 'none',
                name: 'AUC Area',
                fillcolor: 'rgba(255, 0, 0, 0.2)',
                line: { color: 'transparent' }
            });
        }

        // Use auto-selected display units for axis labels
        const voltageUnits = this._displayUnits?.voltage || 'V';
        const currentUnits = this._displayUnits?.current || 'A';

        // Calculate data range for better auto-zoom
        const allYValues = traces.flatMap(trace => trace.y || []);
        const yMin = Math.min(...allYValues);
        const yMax = Math.max(...allYValues);
        const yRange = yMax - yMin;
        const yPadding = yRange * 0.1;  // 10% padding on each side

        const layout = {
            xaxis: {
                title: `Potential (${voltageUnits})`,
                autorange: true
            },
            yaxis: {
                title: `Current (${currentUnits})`,
                range: [yMin - yPadding, yMax + yPadding],
                automargin: true
            },
            showlegend: true,
            legend: {
                orientation: 'h',
                x: 0.5,
                xanchor: 'center',
                y: -0.2,
                yanchor: 'top'
            },
            margin: { l: 60, r: 20, t: 10, b: 90 },
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
        const titleElement = this.dom.visualization.resultsTitle;
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
        const resultsRoot = this.dom.visualization.resultsRoot;
        if (!resultsRoot) return;

        // Check if the new layout already exists
        const existingMainContainer = resultsRoot.querySelector('.cv-main-container');
        if (existingMainContainer) {
            // Layout already exists, no need to recreate
            return;
        }

        const oldPlots = resultsRoot.querySelectorAll('.cv-plot-container, .cv-summary-plots');
        oldPlots.forEach(plot => plot.remove());

        const textSummaries = resultsRoot.querySelectorAll('.analysis-summary');
        textSummaries.forEach(summary => summary.remove());

        // Layout: sweeps side-by-side on top, trend plots below
        const mainContainer = this._createCVResultsLayout();

        resultsRoot.appendChild(mainContainer);
    }

    _updateCVSummaryPlots() {
        // Update summary plots with all processed data
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
        const electrodeResults = this.state.cvResults[electrodeKey];

        if (!electrodeResults) return;

        const fileNumbers = Object.keys(electrodeResults).map(Number).sort((a, b) => a - b);
        const peakSeparations = [];
        const forwardPeakHeights = [];
        const reversePeakHeights = [];
        const forwardAUCs = [];
        const reverseAUCs = [];

        fileNumbers.forEach(fileNum => {
            const result = electrodeResults[fileNum];
            if (result && result.status === 'success') {
                if (result.peak_separation !== undefined && result.peak_separation !== null) {
                    peakSeparations.push({ x: fileNum, y: result.peak_separation });
                }
                if (result.forward && result.forward.peak_current !== undefined) {
                    forwardPeakHeights.push({ x: fileNum, y: result.forward.peak_current });
                }
                if (result.reverse && result.reverse.peak_current !== undefined) {
                    reversePeakHeights.push({ x: fileNum, y: result.reverse.peak_current });
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

        // Update peak height plot
        this._updatePeakHeightPlot(forwardPeakHeights, reversePeakHeights);

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
            yaxis: {
                title: 'Peak Separation (V)',
                rangemode: 'tozero'  // Force y-axis to start from 0
            },
            margin: { l: 70, r: 50, t: 50, b: 60 }
        };

        Plotly.react(plotElement, [trace], layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d'],
            displaylogo: false
        });
    }

    _updatePeakHeightPlot(forwardPeakHeights, reversePeakHeights) {
        const plotElement = document.getElementById('cv-peak-height-plot');
        if (!plotElement || !window.Plotly) return;

        const traces = [];

        // Get current display units for axis label
        const currentUnits = this._displayUnits?.current || 'μA';

        // Add forward peak heights trace
        if (forwardPeakHeights.length > 0) {
            traces.push({
                x: forwardPeakHeights.map(p => p.x),
                y: forwardPeakHeights.map(p => p.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Forward Sweep',
                line: { color: 'rgb(31, 119, 180)', width: 2 },
                marker: { size: 6 }
            });
        }

        // Add reverse peak heights trace
        if (reversePeakHeights.length > 0) {
            traces.push({
                x: reversePeakHeights.map(p => p.x),
                y: reversePeakHeights.map(p => p.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Reverse Sweep',
                line: { color: 'rgb(255, 127, 14)', width: 2 },
                marker: { size: 6 }
            });
        }

        const layout = {
            title: 'Peak Height vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: {
                title: `Peak Height (${currentUnits})`,
                rangemode: 'tozero'  // Force y-axis to start from 0
            },
            showlegend: true,
            legend: {
                orientation: 'h',  // Horizontal legend
                x: 0.5,            // Center horizontally
                xanchor: 'center',
                y: -0.15,          // Below plot
                yanchor: 'top'
            },
            margin: { l: 70, r: 50, t: 50, b: 80 }
        };

        Plotly.react(plotElement, traces, layout, {
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

        // Use auto-selected current unit for charge label (charge = current × time)
        const currentUnits = this._displayUnits?.current || 'A';

        const layout = {
            title: 'AUC vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: { title: `Charge (${currentUnits}·s)` },  // Coulomb = A·s
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
                // Convert probe currents to display units
                const forwardCurrents = forwardData.map(p => p.y);
                const convertedForward = this._convertCVDataUnits({
                    voltage: new Array(forwardCurrents.length).fill(voltage),
                    current: forwardCurrents
                });

                traces.push({
                    x: forwardData.map(p => p.x),
                    y: convertedForward.current,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${voltage}V Forward`,
                    line: { color: color, width: 2 },
                    marker: { size: 6 }
                });
            }

            if (reverseData.length > 0) {
                // Convert probe currents to display units
                const reverseCurrents = reverseData.map(p => p.y);
                const convertedReverse = this._convertCVDataUnits({
                    voltage: new Array(reverseCurrents.length).fill(voltage),
                    current: reverseCurrents
                });

                traces.push({
                    x: reverseData.map(p => p.x),
                    y: convertedReverse.current,
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

        // Use auto-selected current unit
        const currentUnits = this._displayUnits?.current || 'A';

        const layout = {
            title: 'Probe Voltage Currents vs File Number',
            xaxis: { title: 'File Number' },
            yaxis: { title: `Current (${currentUnits})` },
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

            // Use auto-selected display units for axis labels
            const voltageUnits = this._displayUnits?.voltage || 'V';
            const currentUnits = this._displayUnits?.current || 'A';

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
                clearChildren(this.dom.cvPreviewPlot);

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
        console.log('CV: Resetting analysis and cleaning up...');

        this.state.isAnalysisRunning = false;
        this.state.cvResults = {};
        this.state.previewFileContent = null;
        this.state.availableSegments = [];
        this.state.segmentInfo = {};
        this.state.forwardSegments = [];
        this.state.reverseSegments = [];
        this.state.originalCVData = null;
        this.state.currentScreen = 'settings';
        this.state.currentElectrode = null;  // Reset current electrode
        this.state.selectedElectrodes = [];  // Reset selected electrodes
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;

        // Clear any pending timeouts
        if (this._segmentDetectionTimeoutId) {
            clearTimeout(this._segmentDetectionTimeoutId);
            this._segmentDetectionTimeoutId = null;
        }

        // Clean up CV-specific content from shared visualization area
        this._cleanupVisualizationArea();

        console.log('CV: Cleanup complete');
    }

    _resetAnalysisState() {
        this.state.isAnalysisRunning = false;
        this.dom.startAnalysisBtn.disabled = false;
        this.dom.startAnalysisBtn.textContent = 'Start CV Analysis & Sync';
    }

    _cleanupVisualizationArea() {
        const resultsRoot = this.dom.visualization.resultsRoot;
        if (!resultsRoot) return;

        console.log('Cleaning up CV results screen...');

        clearChildren(resultsRoot);

        const titleElement = this.dom.visualization.resultsTitle;
        if (titleElement) {
            titleElement.textContent = 'CV Data Visualization';
        }

        const electrodeControls = this.dom.visualization.electrodeControls;
        if (electrodeControls) {
            electrodeControls.classList.add('hidden');
            const existingButtons = electrodeControls.querySelectorAll('.electrode-btn');
            existingButtons.forEach((btn) => btn.remove());
        }

        if (this.dom.visualization.exportCVDataBtn) {
            this.dom.visualization.exportCVDataBtn.classList.add('hidden');
        }

        if (this.dom.visualization.exportStatus) {
            this.dom.visualization.exportStatus.textContent = '';
        }

        console.log('CV results screen cleanup complete');
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
            const currentUnits = 'A';
            const voltageUnits = 'V';

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
        // SIMPLIFIED: Always display in V and μA
        // Backend sends data in file units (user specified)
        const fileVoltageUnit = 'V';
        const fileCurrentUnit = 'A';

        console.log(`File units: voltage=${fileVoltageUnit}, current=${fileCurrentUnit}`);

        // Convert file units to base units (V, A) first
        const toBaseFactors = {
            // Voltage
            'V': 1.0,
            'mV': 1e-3,
            'μV': 1e-6,
            'nV': 1e-9,
            // Current
            'A': 1.0,
            'mA': 1e-3,
            'μA': 1e-6,
            'nA': 1e-9
        };

        const voltageToBase = toBaseFactors[fileVoltageUnit] || 1.0;
        const currentToBase = toBaseFactors[fileCurrentUnit] || 1.0;

        // Convert to base units
        const voltageBase = cvData.voltage.map(v => v * voltageToBase);  // to V
        const currentBase = cvData.current.map(c => c * currentToBase);  // to A

        // FIXED DISPLAY UNITS: Always V and μA (simple and consistent)
        const displayVoltageUnit = 'V';
        const displayCurrentUnit = 'A';

        // Keep in base units (no conversion)
        const voltageDisplay = voltageBase;  // V
        const currentDisplay = currentBase;  // A

        console.log(`Display: ${displayVoltageUnit}, ${displayCurrentUnit}`);
        console.log(`Sample: V=${voltageDisplay[0]?.toFixed(3)}, I=${currentDisplay[0]?.toExponential(4)} A`);

        // Store display units for axis labels
        this._displayUnits = {
            voltage: displayVoltageUnit,
            current: displayCurrentUnit
        };

        return {
            voltage: voltageDisplay,
            current: currentDisplay
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
            alert(`Error: only ${detectedElectrodes} electrode(s) were detected in the file, but electrode ${maxRequested} was requested. Please check your electrode selection or file column settings.`);
            return false;
        }
        return true;
    }

    _handleCVExport() {
        const defaultFilename = `CV_AllElectrodes_${new Date().toISOString().slice(0, 10)}.xlsx`;
        const filename = prompt("Please enter a filename for the CV export:", defaultFilename);
        if (filename) {
            this.dom.visualization.exportCVDataBtn.dataset.filename = filename;
            this.dom.visualization.exportStatus.textContent = 'Generating CV export file...';

            // Export all electrodes (local mode - no agent needed)
            this.socketManager.emit('request_export_cv_data', {});
        }
    }

    _triggerWorkbookDownload(contentB64, filename) {
        const binary = atob(contentB64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }

        const blob = new Blob(
            [bytes],
            { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }
        );
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
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
            const voltageInBaseUnits = this._convertToBaseUnits(voltage, 'V');

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

