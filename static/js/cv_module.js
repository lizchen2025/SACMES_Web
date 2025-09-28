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
            },
            settings: {
                voltageColumnInput: document.getElementById('cvVoltageColumnInput'),
                currentColumnInput: document.getElementById('cvCurrentColumnInput'),
                spacingIndexInput: document.getElementById('cvSpacingIndexInput'),
                delimiterInput: document.getElementById('cvDelimiterInput'),
                fileExtensionInput: document.getElementById('cvFileExtensionInput'),
                voltageUnitsInput: document.getElementById('cvVoltageUnitsInput'),
                currentUnitsInput: document.getElementById('cvCurrentUnitsInput'),
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
    }

    _setupSocketHandlers() {
        this.socketManager.on('connect', () => {
            console.log('CV Module: Socket connected');
            this.socketManager.emit('request_agent_status', {});
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

                // Extract file number from filename (support CV_60Hz_1.txt format and others)
                const match = data.filename.match(/CV_\d+Hz_(\d+)\./) || data.filename.match(/_(\d+)\./);
                if (match) {
                    const fileNum = match[1];
                    this.state.cvResults[electrodeKey][fileNum] = data.cv_analysis;

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
            peak_min_voltage: this.dom.visualization.peakMinVoltageInput.value === '' ? null : parseFloat(this.dom.visualization.peakMinVoltageInput.value),
            peak_max_voltage: this.dom.visualization.peakMaxVoltageInput.value === '' ? null : parseFloat(this.dom.visualization.peakMaxVoltageInput.value),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value),
            current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value),
            delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value,
            voltage_units: this.dom.settings.voltageUnitsInput.value,
            current_units: this.dom.settings.currentUnitsInput.value,
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
            analysisStartTime: Date.now()
        };

        const analysisParams = this._collectAnalysisParams();
        analysisParams.selected_electrode = this.state.currentElectrode;
        analysisParams.selected_electrodes = this.state.selectedElectrodes;

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

        // Change back button to go to CV settings
        if (backToSWVBtn) {
            backToSWVBtn.textContent = 'Back to CV Settings';
            backToSWVBtn.onclick = () => {
                this.state.currentScreen = 'settings';
                this.uiManager.showScreen('cvAnalysisScreen');
                this.state.isAnalysisRunning = false;
            };
        }

        // Set up electrode controls if needed
        this._setupCVElectrodeControls();

        // Display CV results
        this._displayCVResults();
    }

    _setupCVElectrodeControls() {
        const electrodeControls = document.getElementById('electrodeControls');
        if (!electrodeControls) return;

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

        this.state.currentElectrode = electrodeIdx;
        this._setupCVElectrodeControls(); // Update button states
        this._displayCVResults(); // Refresh plots with new electrode data
    }

    _displayCVResults() {
        // Display CV analysis results in the visualization area
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';
        const electrodeResults = this.state.cvResults[electrodeKey];
        const hasResults = electrodeResults && Object.keys(electrodeResults).length > 0;

        // Clear individual plots container and show CV visualization
        const individualPlotsContainer = document.getElementById('individualPlotsContainer');
        if (individualPlotsContainer) {
            if (hasResults) {
                // Get the most recent analysis result for visualization
                const fileNumbers = Object.keys(electrodeResults).map(Number).sort((a, b) => b - a);
                const latestFileNum = fileNumbers[0];
                const latestResult = electrodeResults[latestFileNum];

                if (latestResult && latestResult.status === 'success') {
                    // Display CV plots
                    this._updateCVVisualization(latestResult);
                }

                // Also show summary
                individualPlotsContainer.innerHTML = `
                    <div class="border rounded-lg p-4 bg-gray-50 mt-4">
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">CV Analysis Summary</h4>
                        <div class="text-sm text-gray-600">
                            <p>Files analyzed: ${Object.keys(electrodeResults).length}</p>
                            <p>Electrode: ${currentElectrode !== null ? currentElectrode + 1 : 'Averaged'}</p>
                            ${latestResult && latestResult.peak_separation ? `<p>Peak Separation: ${latestResult.peak_separation.toFixed(3)} V</p>` : ''}
                            <p>Analysis complete!</p>
                        </div>
                    </div>
                `;
            } else {
                individualPlotsContainer.innerHTML = `
                    <div class="border rounded-lg p-4 bg-yellow-50 border-yellow-200">
                        <h4 class="text-lg font-semibold text-yellow-700 mb-2">No CV Data Received</h4>
                        <div class="text-sm text-yellow-600">
                            <p>No CV analysis results were received.</p>
                            <p><strong>Possible causes:</strong></p>
                            <ul class="list-disc list-inside mt-2 space-y-1">
                                <li>Incorrect file handle (check that files start with "${this.dom.params.fileHandleInput.value || 'your_handle'}")</li>
                                <li>No matching files in the monitored directory</li>
                                <li>Agent connection issues</li>
                                <li>File format incompatibility</li>
                            </ul>
                            <p class="mt-2"><strong>Please check:</strong></p>
                            <ul class="list-disc list-inside mt-1 space-y-1">
                                <li>Agent is running and connected</li>
                                <li>File handle matches your file names</li>
                                <li>Files are in the monitored directory</li>
                            </ul>
                        </div>
                    </div>
                `;
            }
        }

        // Hide trend plots as they are SWV-specific
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            if (hasResults) {
                trendPlotsContainer.innerHTML = `
                    <div class="border rounded-lg p-4 bg-gray-50">
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">CV Results</h4>
                        <div class="text-sm text-gray-600">
                            <p>CV analysis results are available.</p>
                            <p>Individual file analysis details have been processed.</p>
                            <p><strong>Note:</strong> CV-specific trend visualization will be implemented in future updates.</p>
                        </div>
                    </div>
                `;
            } else {
                trendPlotsContainer.innerHTML = `
                    <div class="border rounded-lg p-4 bg-blue-50 border-blue-200">
                        <h4 class="text-lg font-semibold text-blue-700 mb-2">Troubleshooting CV Analysis</h4>
                        <div class="text-sm text-blue-600">
                            <p><strong>File Naming Example:</strong></p>
                            <p>For handle "CV_60Hz", files should be named:</p>
                            <ul class="list-disc list-inside mt-1 space-y-1">
                                <li>CV_60Hz_1.txt</li>
                                <li>CV_60Hz_2.txt</li>
                                <li>CV_60Hz_3.txt, etc.</li>
                            </ul>
                            <p class="mt-2"><strong>Current Settings:</strong></p>
                            <ul class="list-disc list-inside mt-1">
                                <li>Handle: ${this.dom.params.fileHandleInput.value || 'Not set'}</li>
                                <li>Number of files: ${this.state.currentNumFiles || 'Not set'}</li>
                            </ul>
                        </div>
                    </div>
                `;
            }
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
            // 1. We have some results and 10 seconds have passed
            // 2. 30 seconds have passed regardless of results
            // 3. We've received data but no new data for 10 seconds
            if (hasAnyResults && timeElapsed > 10000) {
                console.log(`CV analysis: Force switching to visualization after ${timeElapsed}ms with results`);
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

        const processedFiles = Object.keys(electrodeResults).length;
        const totalFiles = this.state.currentNumFiles;

        // For CV analysis, only complete when ALL files are processed (like SWV)
        // This allows real-time visualization during analysis
        console.log(`CV analysis progress: ${processedFiles}/${totalFiles} files processed.`);

        if (processedFiles >= totalFiles) {
            console.log(`CV analysis complete: ${processedFiles}/${totalFiles} files processed.`);
            this._completeCVAnalysis('complete');
        }
        // Note: No early completion - let analysis run to completion like SWV
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
    }

    _updateCVVisualization(analysisResult) {
        console.log('CV Analysis Result:', analysisResult);

        if (!analysisResult || !analysisResult.forward && !analysisResult.reverse) {
            console.log('No CV data to visualize');
            return;
        }

        // Create CV visualization plots
        this._createCVPlots(analysisResult);
        this._displayCVSummary(analysisResult);
    }

    _updateCVVisualizationRealTime(analysisResult, fileNum) {
        console.log(`CV Real-time Update: File ${fileNum}`, analysisResult);

        if (!analysisResult || (!analysisResult.forward && !analysisResult.reverse)) {
            console.log('No CV data to visualize in real-time update');
            return;
        }

        // Update or create plots in real-time
        this._createCVPlotsRealTime(analysisResult, fileNum);
        this._updateCVProgressDisplay(fileNum);
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
            <div id="${plotId}" style="height: 400px;"></div>
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
                    xaxis: { title: 'Potential (V)' },
                    yaxis: { title: 'Current (A)' },
                    showlegend: true,
                    margin: { l: 50, r: 30, t: 30, b: 50 }
                };

                Plotly.newPlot(plotElement, traces, layout, { responsive: true });
            }
        }, 100);

        return plotDiv;
    }

    _createCVPlotsRealTime(analysisResult, fileNum) {
        // Update existing plots or create them if they don't exist
        const forwardPlotElement = document.getElementById('cv-forward-plot');
        const reversePlotElement = document.getElementById('cv-reverse-plot');

        // If plots don't exist yet, create them
        if (!forwardPlotElement || !reversePlotElement) {
            this._createCVPlots(analysisResult);
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

        const layout = {
            title: title,
            xaxis: { title: 'Potential (V)' },
            yaxis: { title: 'Current (A)' },
            showlegend: true,
            margin: { l: 50, r: 30, t: 50, b: 50 }
        };

        // Use Plotly.redraw for real-time updates
        Plotly.redraw(plotElement, traces, layout);
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
            console.log('Voltage range:', Math.min(...cvData.voltage), 'to', Math.max(...cvData.voltage));
            console.log('Current range:', Math.min(...cvData.current), 'to', Math.max(...cvData.current));

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
                xaxis: {
                    title: 'Voltage (V)',
                    showgrid: true,
                    zeroline: true
                },
                yaxis: {
                    title: 'Current (A)',
                    showgrid: true,
                    zeroline: true
                },
                margin: { t: 50, r: 20, b: 50, l: 60 },
                showlegend: false,
                autosize: true,
                width: undefined,  // Let it auto-size
                height: undefined  // Let it auto-size
            };

            console.log('About to call Plotly.newPlot with:', plotData, layout);
            try {
                // Clear the container first
                this.dom.cvPreviewPlot.innerHTML = '';

                // Create the plot with proper configuration
                Plotly.newPlot(this.dom.cvPreviewPlot, plotData, layout, {
                    responsive: true,
                    displayModeBar: false  // Hide the toolbar for cleaner look
                });

                // Ensure the plot resizes when container changes
                setTimeout(() => {
                    Plotly.Plots.resize(this.dom.cvPreviewPlot);
                }, 100);

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