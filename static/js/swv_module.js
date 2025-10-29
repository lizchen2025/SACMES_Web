// static/js/swv_module.js (Final version with persistent client-side state)

import { PlotlyPlotter } from './plot_utils.js';

export class SWVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        this.dom = {
            swvBtn: document.getElementById('swvBtn'),
            backToWelcomeBtn: document.getElementById('backToWelcomeFromSWV'),
            startAnalysisBtn: document.getElementById('startAnalysisBtn'),
            agentStatus: document.getElementById('agentStatus'),
            folderStatus: document.getElementById('folderStatus'),
            params: {
                analysisModeInputs: document.querySelectorAll('input[name="analysisMode"]'),
                frequencyInputLabel: document.getElementById('frequencyInputLabel'),
                frequencyInputHint: document.getElementById('frequencyInputHint'),
                numFilesContainer: document.getElementById('numFilesContainer'),
                numFilesFrequencyMapHint: document.getElementById('numFilesFrequencyMapHint'),
                fileHandleInput: document.getElementById('fileHandleInput'),
                frequencyInput: document.getElementById('frequencyInput'),
                numFilesInput: document.getElementById('numFilesInput'),
                selectedElectrodesInput: document.getElementById('selectedElectrodesInput'),
                peakMinVoltageInput: document.getElementById('peakMinVoltageInput'),
                peakMaxVoltageInput: document.getElementById('peakMaxVoltageInput'),
                hampelModeInputs: document.querySelectorAll('input[name="hampelMode"]'),
                sgModeInputs: document.querySelectorAll('input[name="sgMode"]'),
                hampelWindowInput: document.getElementById('hampelWindowInput'),
                hampelThresholdInput: document.getElementById('hampelThresholdInput'),
                sgWindowInput: document.getElementById('sgWindowInput'),
                sgDegreeInput: document.getElementById('sgDegreeInput'),
                polyfitDegreeInput: document.getElementById('polyfitDegreeInput'),
                cutoffFrequencyInput: document.getElementById('cutoffFrequencyInput'),
                normalizationPointInput: document.getElementById('normalizationPointInput'),
                lowFrequencyOffsetInput: document.getElementById('lowFrequencyOffsetInput'),
                lowFrequencySlopeInput: document.getElementById('lowFrequencySlopeInput'),
                injectionPointInput: document.getElementById('injectionPointInput'),
            },
            settings: {
                voltageColumnInput: document.getElementById('voltageColumnInput'),
                currentColumnInput: document.getElementById('currentColumnInput'),
                spacingIndexInput: document.getElementById('spacingIndexInput'),
                delimiterInput: document.getElementById('delimiterInput'),
                fileExtensionInput: document.getElementById('fileExtensionInput'),
                voltageUnitsInput: document.getElementById('voltageUnitsInput'),
                currentUnitsInput: document.getElementById('currentUnitsInput'),
                byteLimitInput: document.getElementById('byteLimitInput'),
                sampleRateInput: document.getElementById('sampleRateInput'),
                analysisIntervalInput: document.getElementById('analysisIntervalInput'),
                resizeIntervalInput: document.getElementById('resizeIntervalInput'),
                selectedOptionsInput: document.getElementById('selectedOptionsInput'),
                xAxisOptionsInput: document.getElementById('xAxisOptionsInput'),
            },
            visualization: {
                visualizationArea: document.getElementById('visualizationArea'),
                electrodeControls: document.getElementById('electrodeControls'),
                continuousMonitorContainer: document.getElementById('continuousMonitorContainer'),
                frequencyMapContainer: document.getElementById('frequencyMapContainer'),
                frequencyMapVoltammogramPlot: document.getElementById('frequencyMapVoltammogramPlot'),
                frequencyMapChargePlot: document.getElementById('frequencyMapChargePlot'),
                currentFrequencyLabel: document.getElementById('currentFrequencyLabel'),
                analyzedFrequenciesCount: document.getElementById('analyzedFrequenciesCount'),
                latestFrequency: document.getElementById('latestFrequency'),
                latestCharge: document.getElementById('latestCharge'),
                exportFrequencyMapDataBtn: document.getElementById('exportFrequencyMapDataBtn'),
                exportFrequencyMapStatus: document.getElementById('exportFrequencyMapStatus'),
                individualPlotsContainer: document.getElementById('individualPlotsContainer'),
                trendPlotsContainer: document.getElementById('trendPlotsContainer'),
                adjustmentControls: document.getElementById('adjustmentControls'),
                backToSWVBtn: document.getElementById('backToSWVBtn'),
                exportDataBtn: document.getElementById('exportDataBtn'),
                exportStatus: document.getElementById('exportStatus'),
                peakDetectionWarnings: document.getElementById('peakDetectionWarnings'),
                warningsList: document.getElementById('warningsList'),
                postProcessNormalizationPointInput: document.getElementById('postProcessNormalizationPointInput'),
                postProcessLowFrequencyOffsetInput: document.getElementById('postProcessLowFrequencyOffsetInput'),
                postProcessLowFrequencySlopeInput: document.getElementById('postProcessLowFrequencySlopeInput'),
                postProcessInjectionPointInput: document.getElementById('postProcessInjectionPointInput'),
                updateInjectionPointBtn: document.getElementById('updateInjectionPointBtn'),
                applyPostProcessNormalizationBtn: document.getElementById('applyPostProcessNormalizationBtn'),
            },
        };

        this.state = {
            isAnalysisRunning: false,
            analysisMode: 'continuous', // 'continuous' or 'frequency_map'
            currentFrequencies: [],
            currentNumFiles: 0,
            currentXAxisOptions: "File Number",
            currentKdmHighFreq: null,
            currentKdmLowFreq: null,
            rawTrendData: null, // Holds the raw peak currents from the server
            lastCalculatedData: null, // Holds the last fully calculated trend object
            selectedElectrodes: [], // List of selected electrodes
            currentElectrode: null, // Currently displayed electrode (null for averaged)
            electrodeData: {}, // Raw data for each electrode
            frequencyMapData: {}, // {frequency: {potentials, currents, charge, etc.}}
            analyzedFrequencies: [] // List of frequencies already analyzed in frequency map mode
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
        this._setupFrequencyMapSocketHandlers();
        this._setupFilterModeToggle();
    }

    _setupEventListeners() {
        // Analysis mode toggle
        this.dom.params.analysisModeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.state.analysisMode = e.target.value;
                this._updateUIForMode(e.target.value);
            });
        });

        this.dom.swvBtn.addEventListener('click', () => this.uiManager.showScreen('swvAnalysisScreen'));
        this.dom.startAnalysisBtn.addEventListener('click', this._handleStartAnalysis.bind(this));
        this.dom.backToWelcomeBtn.addEventListener('click', () => this.uiManager.showScreen('welcomeScreen'));
        
        this.dom.visualization.backToSWVBtn.addEventListener('click', () => {
            this.dom.visualization.adjustmentControls.classList.add('hidden');
            this.dom.visualization.exportDataBtn.classList.add('hidden');
            this.uiManager.showScreen('swvAnalysisScreen');
            this.state.isAnalysisRunning = false;
            this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
            this.dom.startAnalysisBtn.disabled = false;
        });
        
        this.dom.visualization.exportDataBtn.addEventListener('click', () => {
            const defaultFilename = `SACMES_SWV_AllElectrodes_${new Date().toISOString().slice(0, 10)}.csv`;
            const filename = prompt("Please enter a filename for the CSV export:", defaultFilename);
            if (filename) {
                this.dom.visualization.exportDataBtn.dataset.filename = filename;
                this.dom.visualization.exportStatus.textContent = 'Generating export file...';

                // Check if connected to agent
                if (typeof isConnectedToAgent === 'function' && !isConnectedToAgent()) {
                    alert('Please connect to an agent first by entering your User ID.');
                    this.dom.visualization.exportStatus.textContent = '';
                    return;
                }

                // Export all electrodes
                this.socketManager.emit('request_export_data', {
                    user_id: getCurrentUserId()
                });
            }
        });

        // Frequency Map export all electrodes button
        if (this.dom.visualization.exportFrequencyMapDataBtn) {
            this.dom.visualization.exportFrequencyMapDataBtn.addEventListener('click', () => {
                const defaultFilename = `SACMES_FrequencyMap_AllElectrodes_${new Date().toISOString().slice(0, 10)}.csv`;
                const filename = prompt("Please enter a filename for the CSV export:", defaultFilename);
                if (filename) {
                    this.dom.visualization.exportFrequencyMapDataBtn.dataset.filename = filename;
                    this.dom.visualization.exportFrequencyMapStatus.textContent = 'Generating export file...';

                    // Check if connected to agent
                    if (typeof isConnectedToAgent === 'function' && !isConnectedToAgent()) {
                        alert('Please connect to an agent first by entering your User ID.');
                        this.dom.visualization.exportFrequencyMapStatus.textContent = '';
                        return;
                    }

                    this.socketManager.emit('request_export_frequency_map_data', {
                        user_id: getCurrentUserId(),
                        export_all: true
                    });
                }
            });
        }

        // Use a single handler for all adjustment updates
        this.dom.visualization.updateInjectionPointBtn.addEventListener('click', () => this._handlePostProcessUpdate());
        this.dom.visualization.applyPostProcessNormalizationBtn.addEventListener('click', () => this._handlePostProcessUpdate());

        // Add listener for x-axis options change during analysis
        this.dom.settings.xAxisOptionsInput.addEventListener('change', () => {
            if (this.state.isAnalysisRunning && this.state.lastCalculatedData) {
                this.state.currentXAxisOptions = this.dom.settings.xAxisOptionsInput.value;
                // Recalculate trends with new x-axis option
                this._handlePostProcessUpdate();
            }
        });
    }

    _setupFilterModeToggle() {
        const autoModeDescription = document.getElementById('autoModeDescription');
        const hampelManualParams = document.getElementById('hampelManualParams');
        const sgManualParams = document.getElementById('sgManualParams');

        const toggleFilterParams = () => {
            const hampelMode = this._getSelectedRadioValue('hampelMode');
            const sgMode = this._getSelectedRadioValue('sgMode');

            // Show/hide auto mode description based on whether any filter is in auto mode
            if (hampelMode === 'auto' || sgMode === 'auto') {
                autoModeDescription.classList.remove('hidden');
            } else {
                autoModeDescription.classList.add('hidden');
            }

            // Show/hide Hampel manual params based on Hampel mode
            if (hampelMode === 'manual') {
                hampelManualParams.classList.remove('hidden');
            } else {
                hampelManualParams.classList.add('hidden');
            }

            // Show/hide SG manual params based on SG mode
            if (sgMode === 'manual') {
                sgManualParams.classList.remove('hidden');
            } else {
                sgManualParams.classList.add('hidden');
            }
        };

        // Add event listeners to all radio buttons
        this.dom.params.hampelModeInputs.forEach(input => {
            input.addEventListener('change', toggleFilterParams);
        });
        this.dom.params.sgModeInputs.forEach(input => {
            input.addEventListener('change', toggleFilterParams);
        });

        toggleFilterParams(); // Initialize on load
    }

    _getSelectedRadioValue(name) {
        const selected = document.querySelector(`input[name="${name}"]:checked`);
        return selected ? selected.value : null;
    }
    
    _setupSocketHandlers() {
        this.socketManager.on('connect', () => this.socketManager.emit('request_agent_status', {}));

        this.socketManager.on('agent_status', (data) => {
            this.dom.agentStatus.className = data.status === 'connected' ? 'text-sm text-green-700 mt-1' : 'text-sm text-red-700 mt-1';
            this.dom.agentStatus.textContent = data.status === 'connected' ? 'Local agent connected. Ready to sync.' : 'Error: Local agent is disconnected.';
        });

        this.socketManager.on('ack_start_session', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'Instructions sent. Agent is now scanning...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';

                // Show alert for user_id related errors
                if (data.message && data.message.includes('User ID')) {
                    alert('Error: ' + data.message + '\n\nPlease go back to the welcome screen and connect to your agent first.');
                }
            }
        });

        this.socketManager.on('live_analysis_update', (data) => {
            if (!this.state.isAnalysisRunning) return;

            // 1. Store electrode-specific data
            if (data.individual_analysis && data.filename && data.electrode_index !== undefined) {
                const match = data.filename.match(/_(\d+)Hz_?_?(\d+)\./);
                if (match) {
                    const [_, freq, fileNum] = match;
                    const electrodeKey = data.electrode_index !== null ? data.electrode_index.toString() : 'averaged';

                    // Store analysis result for this electrode
                    if (!this.state.electrodeData[electrodeKey]) {
                        this.state.electrodeData[electrodeKey] = {};
                    }
                    if (!this.state.electrodeData[electrodeKey][freq]) {
                        this.state.electrodeData[electrodeKey][freq] = {};
                    }
                    this.state.electrodeData[electrodeKey][freq][fileNum] = data.individual_analysis;

                    // 3. Update individual plots only if this is the currently displayed electrode
                    if (data.electrode_index === this.state.currentElectrode) {
                        this._updateIndividualPlotsUI(data.filename, data.individual_analysis);
                    }
                }
            }

            // 2. Update the source of truth for raw trend data (only for current electrode)
            if (data.trend_data && data.electrode_index === this.state.currentElectrode) {
                this.state.rawTrendData = {
                    peak_current_trends: data.trend_data.peak_current_trends,
                    x_axis_values: data.trend_data.x_axis_values
                };

                // 4. Always recalculate and render the trend plots based on the UI controls
                this._handlePostProcessUpdate();
            }

            // 5. Update peak detection warnings
            if (data.peak_detection_warnings && data.electrode_index === this.state.currentElectrode) {
                this._updatePeakDetectionWarnings(data.peak_detection_warnings);
            }
        });

        this.socketManager.on('electrode_validation_error', (data) => {
            // Only show alert if analysis is still running (prevent duplicate alerts)
            if (this.state.isAnalysisRunning) {
                alert(data.message);
                // Reset analysis state
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.folderStatus.textContent = 'Please correct electrode selection and try again.';

                // Notify server to stop the analysis session
                this.socketManager.emit('stop_analysis_session', { reason: 'electrode_validation_failed' });
            }
        });

        this.socketManager.on('export_data_response', (data) => {
            if (data.status === 'success') {
                const filename = this.dom.visualization.exportDataBtn.dataset.filename || 'export.csv';
                this.dom.visualization.exportStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerCsvDownload(data.data, filename);
            } else {
                this.dom.visualization.exportStatus.textContent = `Export failed: ${data.message}`;
            }
        });

        this.socketManager.on('electrode_warnings_response', (data) => {
            if (data.status === 'success' && data.electrode_index === this.state.currentElectrode) {
                this._updatePeakDetectionWarnings(data.warnings);
            }
        });
    }

    /**
     * PUBLIC METHOD: Populate historical data for Monitor Mode
     * Called when a monitor device enters monitor mode and receives existing analysis data
     */
    populateHistoricalData(historicalData) {
        console.log('SWV Module: Populating historical data for monitor mode', historicalData);

        const trendData = historicalData.trend_data;
        const analysisParams = historicalData.analysis_params;

        if (!trendData || !trendData.raw_peaks) {
            console.warn('No SWV trend data to populate');
            return;
        }

        // Mark as analysis running (in monitor mode)
        this.state.isAnalysisRunning = true;

        // Determine which electrode to display (prefer the one from params, or use first available)
        const selectedElectrode = analysisParams?.selected_electrode;
        if (selectedElectrode !== undefined && selectedElectrode !== null) {
            this.state.currentElectrode = selectedElectrode;
        }

        // Populate electrode data from raw_peaks structure
        // raw_peaks structure: { '0': {freq: {fileNum: data}}, '1': {...}, 'averaged': {...} }
        const rawPeaks = trendData.raw_peaks;

        for (const electrodeKey in rawPeaks) {
            if (!this.state.electrodeData[electrodeKey]) {
                this.state.electrodeData[electrodeKey] = {};
            }

            const electrodeFreqs = rawPeaks[electrodeKey];
            for (const freq in electrodeFreqs) {
                if (!this.state.electrodeData[electrodeKey][freq]) {
                    this.state.electrodeData[electrodeKey][freq] = {};
                }

                const fileNumData = electrodeFreqs[freq];
                for (const fileNum in fileNumData) {
                    this.state.electrodeData[electrodeKey][freq][fileNum] = fileNumData[fileNum];
                }
            }
        }

        // Set raw trend data for current electrode
        const currentElectrodeKey = this.state.currentElectrode !== null ?
                                     this.state.currentElectrode.toString() : 'averaged';

        if (trendData.peak_current_trends && trendData.x_axis_values) {
            this.state.rawTrendData = {
                peak_current_trends: trendData.peak_current_trends,
                x_axis_values: trendData.x_axis_values
            };
        }

        // Navigate to visualization and set up UI
        this.uiManager.showScreen('visualizationArea');

        // Set up electrode controls (buttons for switching electrodes)
        this._setupElectrodeControls();

        // Render initial trend plots
        this._handlePostProcessUpdate();

        console.log('SWV historical data populated successfully');
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

    _recalculateTrends() {
        // Use current electrode to get the right data
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';

        // Always try to reconstruct from stored electrode data first (for electrode switching)
        // Fall back to rawTrendData only if no stored data is available
        let rawPeaks = this._reconstructTrendDataFromElectrodeData(electrodeKey);

        // If reconstruction failed and we have rawTrendData from server, use it
        if (!rawPeaks && this.state.rawTrendData && this.state.rawTrendData.peak_current_trends) {
            rawPeaks = this.state.rawTrendData.peak_current_trends;
        }

        if (!rawPeaks) return null;

        const newParams = {
            num_files: this.state.currentNumFiles,
            frequencies: this.state.currentFrequencies,
            normalizationPoint: parseInt(this.dom.visualization.postProcessNormalizationPointInput.value)
        };

        const { num_files, frequencies } = newParams;
        const freqStrings = frequencies.map(String).sort((a, b) => parseInt(a) - parseInt(b));
        const lowFreqStr = freqStrings[0];
        const highFreqStr = freqStrings[freqStrings.length - 1];

        // Calculate x-axis values based on user preference
        let x_axis_values;

        // Check if we have server-calculated x_axis_values that match our current settings
        if (this.state.rawTrendData && this.state.rawTrendData.x_axis_values &&
            this.state.rawTrendData.x_axis_values.length === num_files) {
            // Use server-calculated values if available and correct length
            x_axis_values = this.state.rawTrendData.x_axis_values;
        } else {
            // Calculate on client side if server data not available
            if (this.state.currentXAxisOptions === 'Experiment Time') {
                // Convert file numbers to minutes: (file_number - 1) * sample_rate / 60
                const sampleRate = parseFloat(this.dom.settings.sampleRateInput.value) || 20; // seconds per file
                x_axis_values = Array.from({ length: num_files }, (_, i) => (i * sampleRate) / 60);
            } else {
                // Default file number mode
                x_axis_values = Array.from({ length: num_files }, (_, i) => i + 1);
            }
        }

        const recalculated = {
            x_axis_values: x_axis_values,
            peak_current_trends: rawPeaks,
            normalized_peak_trends: {},
            kdm_trend: Array(num_files).fill(null)
        };

        const normFactors = {};
        for (const freq of freqStrings) {
            const normIdx = newParams.normalizationPoint - 1;
            const normValue = (rawPeaks[freq] && normIdx >= 0 && normIdx < rawPeaks[freq].length) ? rawPeaks[freq][normIdx] : 1.0;
            normFactors[freq] = (normValue && normValue !== 0) ? normValue : 1.0;
            recalculated.normalized_peak_trends[freq] = Array(num_files).fill(null);
        }

        for (let i = 0; i < num_files; i++) {
            for (const freq of freqStrings) {
                if (rawPeaks[freq] && rawPeaks[freq][i] !== null) {
                    recalculated.normalized_peak_trends[freq][i] = rawPeaks[freq][i] / normFactors[freq];
                }
            }
            const lowPeak = rawPeaks[lowFreqStr] ? rawPeaks[lowFreqStr][i] : null;
            const highPeak = rawPeaks[highFreqStr] ? rawPeaks[highFreqStr][i] : null;
            if (lowPeak !== null && highPeak !== null && highPeak !== 0) {
                recalculated.kdm_trend[i] = lowPeak / highPeak;
            }
        }
        return recalculated;
    }

    _reconstructTrendDataFromElectrodeData(electrodeKey) {
        const electrodeData = this.state.electrodeData[electrodeKey];
        if (!electrodeData) {
            console.log(`No data found for electrode: ${electrodeKey}`);
            return null;
        }

        const rawPeaks = {};
        let hasData = false;

        // Reconstruct peak data for each frequency
        for (const freq of this.state.currentFrequencies) {
            const freqStr = freq.toString();
            const freqData = electrodeData[freqStr];

            if (!freqData) {
                console.log(`No data for frequency ${freqStr} in electrode ${electrodeKey}`);
                continue;
            }

            rawPeaks[freqStr] = Array(this.state.currentNumFiles).fill(null);

            // Fill in available data
            for (const fileNum in freqData) {
                const fileIndex = parseInt(fileNum) - 1;
                if (fileIndex >= 0 && fileIndex < this.state.currentNumFiles) {
                    const analysisResult = freqData[fileNum];
                    if (analysisResult && analysisResult.peak_value !== null) {
                        rawPeaks[freqStr][fileIndex] = analysisResult.peak_value;
                        hasData = true;
                    }
                }
            }
        }

        if (!hasData) {
            console.log(`No valid peak data found for electrode ${electrodeKey}`);
            return null;
        }

        console.log(`Successfully reconstructed data for electrode ${electrodeKey}:`, rawPeaks);
        return rawPeaks;
    }

    _handlePostProcessUpdate() {
        const recalculatedData = this._recalculateTrends();
        if (recalculatedData) {
            this.state.lastCalculatedData = recalculatedData;
            this._renderTrendPlots(recalculatedData);
        }
    }

    _handleStartAnalysis() {
        const frequencies = this.dom.params.frequencyInput.value.split(',').map(f => parseInt(f.trim())).filter(f => !isNaN(f));

        // Validation based on analysis mode
        if (this.state.analysisMode === 'frequency_map') {
            // Frequency map: at least 2 frequencies required, no file number check
            if (frequencies.length < 2) {
                alert("Please enter at least two valid frequencies for frequency map analysis.");
                return;
            }
        } else {
            // Continuous monitor: need both numFiles and frequencies
            const numFiles = parseInt(this.dom.params.numFilesInput.value);
            if (isNaN(numFiles) || numFiles < 1) {
                alert("Please enter a valid number of files.");
                return;
            }
            if (frequencies.length < 2) {
                alert("Please enter at least two valid frequencies.");
                return;
            }
        }

        // Set numFiles appropriately
        const numFiles = this.state.analysisMode === 'frequency_map' ? 1 : parseInt(this.dom.params.numFilesInput.value);

        // Parse selected electrodes (convert from 1-based to 0-based)
        const selectedElectrodesStr = this.dom.params.selectedElectrodesInput.value.trim();
        let selectedElectrodes = [];
        if (selectedElectrodesStr) {
            selectedElectrodes = selectedElectrodesStr.split(',')
                .map(e => parseInt(e.trim()) - 1)  // Convert from 1-based to 0-based
                .filter(e => !isNaN(e) && e >= 0);
            if (selectedElectrodes.length === 0) {
                alert("Please enter valid electrode numbers (starting from 1)");
                return;
            }
        }
        
        // Preserve analysisMode when updating state
        const currentAnalysisMode = this.state.analysisMode;

        this.state = {
            isAnalysisRunning: true,
            analysisMode: currentAnalysisMode,  // Preserve mode
            currentFrequencies: frequencies,
            currentNumFiles: numFiles,
            currentXAxisOptions: this.dom.settings.xAxisOptionsInput.value,
            currentKdmHighFreq: Math.max(...frequencies),
            currentKdmLowFreq: Math.min(...frequencies),
            rawTrendData: null,
            lastCalculatedData: null,
            selectedElectrodes: selectedElectrodes,
            currentElectrode: selectedElectrodes.length > 0 ? selectedElectrodes[0] : null,
            electrodeData: {},
            frequencyMapData: {},  // Reset frequency map data {electrode: {frequency: data}}
            analyzedFrequencies: {}  // Reset analyzed frequencies {electrode: [frequencies]}
        };
        
        this.dom.visualization.postProcessNormalizationPointInput.value = this.dom.params.normalizationPointInput.value;
        this.dom.visualization.postProcessLowFrequencyOffsetInput.value = this.dom.params.lowFrequencyOffsetInput.value;
        this.dom.visualization.postProcessLowFrequencySlopeInput.value = this.dom.params.lowFrequencySlopeInput.value;
        this.dom.visualization.postProcessInjectionPointInput.value = this.dom.params.injectionPointInput.value;
        
        const hampelMode = this._getSelectedRadioValue('hampelMode');
        const sgMode = this._getSelectedRadioValue('sgMode');

        const analysisParams = {
            num_files: numFiles, frequencies: this.state.currentFrequencies, num_electrodes: this._autoDetectNumElectrodes(),
            hampel_mode: hampelMode,
            sg_mode: sgMode,
            hampel_window: hampelMode === 'manual' ? parseInt(this.dom.params.hampelWindowInput.value) : undefined,
            hampel_threshold: hampelMode === 'manual' ? parseFloat(this.dom.params.hampelThresholdInput.value) : undefined,
            sg_window: sgMode === 'manual' ? parseInt(this.dom.params.sgWindowInput.value) : undefined,
            sg_degree: sgMode === 'manual' ? parseInt(this.dom.params.sgDegreeInput.value) : undefined,
            polyfit_deg: parseInt(this.dom.params.polyfitDegreeInput.value), cutoff_frequency: parseInt(this.dom.params.cutoffFrequencyInput.value),
            normalizationPoint: parseInt(this.dom.params.normalizationPointInput.value), lowFrequencyOffset: parseFloat(this.dom.params.lowFrequencyOffsetInput.value),
            lowFrequencySlope: parseFloat(this.dom.params.lowFrequencySlopeInput.value), injectionPoint: this.dom.params.injectionPointInput.value === '' ? null : parseInt(this.dom.params.injectionPointInput.value),
            peak_min_voltage: this.dom.params.peakMinVoltageInput.value === '' ? null : parseFloat(this.dom.params.peakMinVoltageInput.value),
            peak_max_voltage: this.dom.params.peakMaxVoltageInput.value === '' ? null : parseFloat(this.dom.params.peakMaxVoltageInput.value),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value), current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value), delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value, SelectedOptions: this.dom.settings.selectedOptionsInput.value,
            voltage_units: this.dom.settings.voltageUnitsInput.value,
            current_units: this.dom.settings.currentUnitsInput.value,
            xAxisOptions: this.state.currentXAxisOptions,
            sampleRate: parseFloat(this.dom.settings.sampleRateInput.value),
            selected_electrode: this.state.currentElectrode, // Add current electrode to params
            selected_electrodes: this.state.selectedElectrodes // Add all selected electrodes
        };
        const filters = { handle: this.dom.params.fileHandleInput.value.trim(), frequencies: this.state.currentFrequencies, range_start: 1, range_end: numFiles };

        this.dom.startAnalysisBtn.textContent = 'Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending instructions to server...";

        // Ensure CV buttons are hidden and SWV buttons are visible
        const exportCVBtn = document.getElementById('exportCVDataBtn');
        const backToSWVBtn = document.getElementById('backToSWVBtn');
        if (exportCVBtn) {
            exportCVBtn.classList.add('hidden');
        }
        if (backToSWVBtn) {
            backToSWVBtn.textContent = 'Back to SWV Settings';
            backToSWVBtn.onclick = () => this.uiManager.showScreen('swvAnalysisScreen');
        }

        // Check analysis mode and setup appropriate visualization
        if (this.state.analysisMode === 'frequency_map') {
            // Frequency Map mode
            console.log('=== Starting Frequency Map Mode ===');
            console.log('Analysis mode:', this.state.analysisMode);

            this._setupFrequencyMapVisualization();
            this._setupElectrodeControls();  // Show electrode controls

            console.log('Switching to visualizationArea...');
            this.uiManager.showScreen('visualizationArea');

            // Debug: Verify visualization area and containers are visible
            setTimeout(() => {
                const visualizationArea = document.getElementById('visualizationArea');
                const frequencyMapContainer = document.getElementById('frequencyMapContainer');
                const continuousMonitorContainer = document.getElementById('continuousMonitorContainer');

                console.log('=== DOM State Check (after showScreen) ===');
                console.log('visualizationArea:');
                console.log('  - classList:', visualizationArea?.classList.toString());
                console.log('  - computed display:', window.getComputedStyle(visualizationArea).display);
                console.log('  - offsetParent:', visualizationArea?.offsetParent);  // null means hidden

                console.log('frequencyMapContainer:');
                console.log('  - classList:', frequencyMapContainer?.classList.toString());
                console.log('  - computed display:', window.getComputedStyle(frequencyMapContainer).display);
                console.log('  - offsetParent:', frequencyMapContainer?.offsetParent);

                console.log('continuousMonitorContainer:');
                console.log('  - classList:', continuousMonitorContainer?.classList.toString());
                console.log('  - computed display:', window.getComputedStyle(continuousMonitorContainer).display);
                console.log('=========================================');
            }, 100);  // Small delay to ensure DOM updates

            // Hide continuous monitor specific controls
            this.dom.visualization.adjustmentControls.classList.add('hidden');
            this.dom.visualization.exportDataBtn.classList.add('hidden');

            console.log('Frequency map visualization setup complete');

            // Clear frequency map data for current electrode
            const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
            if (!this.state.frequencyMapData[electrodeKey]) {
                this.state.frequencyMapData[electrodeKey] = {};
            }
            if (!this.state.analyzedFrequencies[electrodeKey]) {
                this.state.analyzedFrequencies[electrodeKey] = [];
            }

            this._updateFrequencyMapStats();

            // Check if connected to agent
            if (typeof isConnectedToAgent === 'function' && !isConnectedToAgent()) {
                alert('Please connect to an agent first by entering your User ID on the welcome screen.');
                return;
            }

            this.socketManager.emit('start_frequency_map_session', {
                user_id: getCurrentUserId(),
                filters,
                analysisParams,
                frequencies: this.state.currentFrequencies
            });
        } else {
            // Continuous Monitor mode (original behavior)
            this._setupVisualizationLayout();
            this._setupElectrodeControls();
            this.uiManager.showScreen('visualizationArea');
            this.dom.visualization.adjustmentControls.classList.remove('hidden');
            this.dom.visualization.exportDataBtn.classList.remove('hidden');
            this.dom.visualization.exportStatus.textContent = '';
            // Clear warnings at the start of analysis
            this.dom.visualization.peakDetectionWarnings.classList.add('hidden');
            this.dom.visualization.warningsList.innerHTML = '';

            // Check if connected to agent
            if (typeof isConnectedToAgent === 'function' && !isConnectedToAgent()) {
                alert('Please connect to an agent first by entering your User ID on the welcome screen.');
                return;
            }

            this.socketManager.emit('start_analysis_session', {
                user_id: getCurrentUserId(),
                filters,
                analysisParams
            });
        }
    }

    _setupFrequencyMapVisualization() {
        console.log('Setting up Frequency Map visualization...');

        // Clean up any CV remnants before setting up frequency map visualization
        this._cleanupCVRemnants();

        // DEBUG: Check if plot divs exist after cleanup
        const voltammogramPlot = document.getElementById('frequencyMapVoltammogramPlot');
        const chargePlot = document.getElementById('frequencyMapChargePlot');
        console.log('=== Frequency Map Plot Divs Check (after cleanup) ===');
        console.log('frequencyMapVoltammogramPlot exists:', !!voltammogramPlot);
        console.log('frequencyMapVoltammogramPlot innerHTML:', voltammogramPlot?.innerHTML.substring(0, 100));
        console.log('frequencyMapChargePlot exists:', !!chargePlot);
        console.log('frequencyMapChargePlot innerHTML:', chargePlot?.innerHTML.substring(0, 100));

        // If plot divs don't exist or are damaged, recreate them
        if (!voltammogramPlot || !chargePlot) {
            console.warn('Plot divs missing after cleanup - attempting to restore...');
            this._restoreFrequencyMapPlotDivs();
        }

        // Hide continuous monitor containers
        if (this.dom.visualization.continuousMonitorContainer) {
            console.log('Hiding continuousMonitorContainer');
            this.dom.visualization.continuousMonitorContainer.classList.add('hidden');
        } else {
            console.warn('continuousMonitorContainer not found!');
        }

        // Show frequency map container
        if (this.dom.visualization.frequencyMapContainer) {
            console.log('Showing frequencyMapContainer');
            this.dom.visualization.frequencyMapContainer.classList.remove('hidden');
        } else {
            console.warn('frequencyMapContainer not found!');
        }

        // Show electrode controls for frequency map (multi-electrode support)
        if (this.dom.visualization.electrodeControls) {
            console.log('Showing electrodeControls for frequency map');
            this.dom.visualization.electrodeControls.style.display = 'flex';
        }

        console.log('Frequency Map visualization setup complete');
    }

    _restoreFrequencyMapPlotDivs() {
        console.log('Restoring frequency map plot divs...');
        const container = document.getElementById('frequencyMapContainer');
        if (!container) {
            console.error('Cannot restore - frequencyMapContainer not found!');
            return;
        }

        // Recreate the entire frequency map structure
        container.innerHTML = `
            <div class="grid grid-cols-1 gap-6">
                <!-- Voltammogram Plot (Top) -->
                <div class="border rounded-lg p-4 bg-gradient-to-r from-blue-50 to-purple-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">Current Voltammogram</h4>
                    <div id="frequencyMapVoltammogramPlot" class="w-full plotly-plot-container bg-white rounded-lg border border-gray-200" style="height: 400px;">
                        <div class="flex items-center justify-center h-full text-gray-400">Waiting for data...</div>
                    </div>
                    <p id="currentFrequencyLabel" class="text-sm text-gray-600 mt-2 text-center">No frequency selected</p>
                </div>

                <!-- Frequency vs Charge Plot (Bottom) -->
                <div class="border rounded-lg p-4 bg-gradient-to-r from-purple-50 to-pink-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">Frequency Map: Charge vs Frequency</h4>
                    <div id="frequencyMapChargePlot" class="w-full plotly-plot-container bg-white rounded-lg border border-gray-200" style="height: 400px;">
                        <div class="flex items-center justify-center h-full text-gray-400">Waiting for data...</div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2 text-center">Logarithmic frequency scale</p>
                </div>

                <!-- Frequency Map Statistics -->
                <div class="border rounded-lg p-4 bg-blue-50">
                    <h4 class="text-md font-semibold text-gray-700 mb-2">Analysis Progress</h4>
                    <div id="frequencyMapStats" class="text-sm text-gray-600">
                        <p>Frequencies analyzed: <span id="analyzedFrequenciesCount" class="font-bold">0</span></p>
                        <p>Latest frequency: <span id="latestFrequency" class="font-bold">-</span> Hz</p>
                    </div>
                </div>
            </div>
        `;
        console.log('Frequency map plot divs restored');
    }
    
    _updateIndividualPlotsUI(filename, individual_analysis) {
        if (!filename || !individual_analysis || individual_analysis.status === 'error') return;
        const match = filename.match(/_(\d+)Hz_?_?(\d+)\./);
        if (match) {
            const [_, freq, fileNum] = match;

            // Only update plots if this data is for the currently selected electrode
            const currentElectrode = this.state.currentElectrode;
            const plotDivId = `plotArea-${freq}`;
            const fileNumEl = document.getElementById(`fileNumDisplay-${freq}`);
            const peakHeightEl = document.getElementById(`peakHeightDisplay-${freq}`);

            if (document.getElementById(plotDivId) && fileNumEl && peakHeightEl) {
                PlotlyPlotter.plotIndividualData(
                    plotDivId,
                    individual_analysis.potentials,
                    individual_analysis.raw_currents,
                    individual_analysis.smoothed_currents,
                    individual_analysis.regression_line,
                    individual_analysis.adjusted_potentials,
                    individual_analysis.auc_vertices,
                    this.dom.settings.selectedOptionsInput.value,
                    individual_analysis.peak_info,  // NEW: Peak detection info
                    individual_analysis.peak_baseline_line,  // NEW: Peak-to-baseline line
                    this.dom.settings.voltageUnitsInput.value,  // Voltage units
                    this.dom.settings.currentUnitsInput.value   // Current units
                );
                fileNumEl.textContent = fileNum;
                peakHeightEl.textContent = individual_analysis.peak_value !== null ? individual_analysis.peak_value.toFixed(4) : "N/A";
            }
        }
    }

    _updateIndividualPlotsForElectrode(electrode) {
        // Update individual plots when switching electrodes
        const electrodeKey = electrode !== null ? electrode.toString() : 'averaged';
        const electrodeData = this.state.electrodeData[electrodeKey];

        if (!electrodeData) return;

        // Update both frequency plots
        [this.state.currentKdmHighFreq, this.state.currentKdmLowFreq].forEach(freq => {
            const freqData = electrodeData[freq];
            if (!freqData) return;

            // Get the latest file data for this frequency
            const fileNumbers = Object.keys(freqData).map(Number).sort((a, b) => b - a);
            if (fileNumbers.length === 0) return;

            const latestFileNum = fileNumbers[0];
            const latestData = freqData[latestFileNum];

            const plotDivId = `plotArea-${freq}`;
            const fileNumEl = document.getElementById(`fileNumDisplay-${freq}`);
            const peakHeightEl = document.getElementById(`peakHeightDisplay-${freq}`);

            if (document.getElementById(plotDivId) && fileNumEl && peakHeightEl && latestData) {
                PlotlyPlotter.plotIndividualData(
                    plotDivId,
                    latestData.potentials,
                    latestData.raw_currents,
                    latestData.smoothed_currents,
                    latestData.regression_line,
                    latestData.adjusted_potentials,
                    latestData.auc_vertices,
                    this.dom.settings.selectedOptionsInput.value,
                    latestData.peak_info,  // NEW: Peak detection info
                    latestData.peak_baseline_line,  // NEW: Peak-to-baseline line
                    this.dom.settings.voltageUnitsInput.value,  // Voltage units
                    this.dom.settings.currentUnitsInput.value   // Current units
                );
                fileNumEl.textContent = latestFileNum;
                peakHeightEl.textContent = latestData.peak_value !== null ? latestData.peak_value.toFixed(4) : "N/A";
            }
        });
    }
    
    _renderTrendPlots(trendData) {
        const injectionPoint = parseInt(this.dom.visualization.postProcessInjectionPointInput.value) || null;
        const resizeInterval = parseInt(this.dom.settings.resizeIntervalInput.value);
        const freqStrs = this.state.currentFrequencies.map(String);
        const xAxisTitle = (this.state.currentXAxisOptions === "Experiment Time") ? 'Experiment Time (min)' : 'File Number';

        // Determine Y-axis title based on analysis mode (Peak or AUC)
        const selectedOptions = this.dom.settings.selectedOptionsInput.value;
        const isAUCMode = selectedOptions === "Area Under the Curve";
        const firstPlotYTitle = isAUCMode ? 'AUC (a.u.)' : `Peak Current (${this.dom.settings.currentUnitsInput.value})`;

        PlotlyPlotter.renderFullTrendPlot('peakCurrentTrendPlot', trendData, freqStrs, xAxisTitle, firstPlotYTitle, this.state.currentNumFiles, '', 'peak', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('normalizedPeakTrendPlot', trendData, freqStrs, xAxisTitle, 'Normalized Current', this.state.currentNumFiles, '', 'normalized', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('kdmTrendPlot', trendData, freqStrs, xAxisTitle, 'KDM Value', this.state.currentNumFiles, '', 'kdm', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
    }
    
    _setupElectrodeControls() {
        const { electrodeControls } = this.dom.visualization;
        if (!electrodeControls) return;

        // Ensure electrode controls are visible
        electrodeControls.style.display = 'flex';

        // Clear existing buttons
        const existingButtons = electrodeControls.querySelectorAll('.electrode-btn');
        existingButtons.forEach(btn => btn.remove());

        // Determine which switch function to use based on analysis mode
        const switchFunction = this.state.analysisMode === 'frequency_map'
            ? (idx) => this._switchFrequencyMapElectrode(idx)
            : (idx) => this._switchElectrode(idx);

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
                btn.onclick = () => switchFunction(electrodeIdx);
                electrodeControls.appendChild(btn);
            });
        }
    }

    _switchElectrode(electrodeIdx) {
        if (this.state.currentElectrode === electrodeIdx) return;

        console.log(`Switching to electrode ${electrodeIdx}`);
        console.log('Available electrode data:', Object.keys(this.state.electrodeData));

        this.state.currentElectrode = electrodeIdx;

        // Clear rawTrendData to force using stored electrode data
        this.state.rawTrendData = null;

        this._setupElectrodeControls(); // Update button states
        this._updateIndividualPlotsForElectrode(electrodeIdx); // Update individual plots
        this._handlePostProcessUpdate(); // Refresh trend plots with new electrode data

        // Update warnings for this electrode
        // Note: We'll need to request updated warnings from the server for this electrode
        this.socketManager.emit('request_electrode_warnings', {
            electrode_index: electrodeIdx
        });
    }

    _cleanupCVRemnants() {
        console.log('SWV: Cleaning up any CV remnants...');

        const visualizationArea = document.getElementById('visualizationArea');
        if (!visualizationArea) return;

        // Remove all CV-specific elements that might interfere with SWV
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
                console.log(`SWV: Removing CV element: ${selector}`);
                element.remove();
            });
        });

        // Restore electrode controls visibility (CV may have hidden it)
        const electrodeControls = document.getElementById('electrodeControls');
        if (electrodeControls) {
            // Don't set to 'block' yet - let _setupElectrodeControls handle visibility
            // But ensure CV hasn't forced it to 'none'
            if (electrodeControls.style.display === 'none') {
                electrodeControls.style.display = '';
                console.log('SWV: Restored electrodeControls visibility');
            }
        }

        // Ensure trend plots container is visible and restore its structure if needed
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            trendPlotsContainer.style.display = '';

            // Check if the trend plots structure is intact, if not, restore it
            const peakPlot = document.getElementById('peakCurrentTrendPlot');
            const normalizedPlot = document.getElementById('normalizedPeakTrendPlot');
            const kdmPlot = document.getElementById('kdmTrendPlot');

            if (!peakPlot || !normalizedPlot || !kdmPlot) {
                console.log('SWV: Restoring trend plots structure...');
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
                console.log('SWV: Trend plots structure restored');
            } else {
                console.log('SWV: Trend plots structure is intact');
            }

            console.log('SWV: Ensured trendPlotsContainer is visible and intact');
        }

        console.log('SWV: CV remnants cleanup complete');
    }

    _setupVisualizationLayout() {
        // Clean up any CV remnants before setting up SWV visualization
        this._cleanupCVRemnants();

        // Show continuous monitor containers
        if (this.dom.visualization.continuousMonitorContainer) {
            this.dom.visualization.continuousMonitorContainer.classList.remove('hidden');
        }

        // Hide frequency map container
        if (this.dom.visualization.frequencyMapContainer) {
            this.dom.visualization.frequencyMapContainer.classList.add('hidden');
        }

        const { individualPlotsContainer } = this.dom.visualization;
        const { currentKdmHighFreq, currentKdmLowFreq } = this.state;
        if (individualPlotsContainer) {
            individualPlotsContainer.innerHTML = `
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">${currentKdmHighFreq} Hz Analysis</h4>
                    <div id="plotArea-${currentKdmHighFreq}" class="w-full plotly-plot-container bg-gray-100 flex justify-center items-center text-gray-400">Waiting for data...</div>
                    <p class="text-sm mt-2">File: <span id="fileNumDisplay-${currentKdmHighFreq}">N/A</span>, Peak: <span id="peakHeightDisplay-${currentKdmHighFreq}">N/A</span></p>
                </div>
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">${currentKdmLowFreq} Hz Analysis</h4>
                    <div id="plotArea-${currentKdmLowFreq}" class="w-full plotly-plot-container bg-gray-100 flex justify-center items-center text-gray-400">Waiting for data...</div>
                    <p class="text-sm mt-2">File: <span id="fileNumDisplay-${currentKdmLowFreq}">N/A</span>, Peak: <span id="peakHeightDisplay-${currentKdmLowFreq}">N/A</span></p>
                </div>
            `;
        }
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

    _updatePeakDetectionWarnings(warnings) {
        const warningsContainer = this.dom.visualization.peakDetectionWarnings;
        const warningsList = this.dom.visualization.warningsList;

        if (!warnings || warnings.length === 0) {
            warningsContainer.classList.add('hidden');
            return;
        }

        // Group warnings by type for better display
        const groupedWarnings = {};
        warnings.forEach(warning => {
            const key = warning.warning_type || 'unknown';
            if (!groupedWarnings[key]) {
                groupedWarnings[key] = [];
            }
            groupedWarnings[key].push(warning);
        });

        // Clear existing warnings
        warningsList.innerHTML = '';

        // Display grouped warnings
        Object.keys(groupedWarnings).forEach(warningType => {
            const warningGroup = groupedWarnings[warningType];
            const count = warningGroup.length;

            let description = '';
            switch (warningType) {
                case 'no_derivative_peak':
                    description = `No derivative peaks found in ${count} file(s)`;
                    break;
                case 'insufficient_points_for_derivative':
                    description = `Insufficient data points for peak detection in ${count} file(s)`;
                    break;
                case 'internal_baseline_error':
                    description = `Baseline calculation error in ${count} file(s)`;
                    break;
                default:
                    description = `Peak detection issues in ${count} file(s)`;
            }

            const warningDiv = document.createElement('div');
            warningDiv.className = 'mb-2 p-2 bg-yellow-100 border border-yellow-200 rounded';

            // Create collapsible details
            const summary = document.createElement('div');
            summary.className = 'font-medium cursor-pointer flex items-center justify-between';
            summary.innerHTML = `
                <span>${description}</span>
                <span class="text-xs bg-yellow-200 px-2 py-1 rounded">Show Files</span>
            `;

            const details = document.createElement('div');
            details.className = 'mt-2 text-xs hidden';
            details.innerHTML = warningGroup.map(w =>
                `• ${w.filename} (${w.frequency}Hz, File #${w.file_number})`
            ).join('<br>');

            summary.addEventListener('click', () => {
                details.classList.toggle('hidden');
                const showText = details.classList.contains('hidden') ? 'Show Files' : 'Hide Files';
                summary.querySelector('span:last-child').textContent = showText;
            });

            warningDiv.appendChild(summary);
            warningDiv.appendChild(details);
            warningsList.appendChild(warningDiv);
        });

        warningsContainer.classList.remove('hidden');
    }

    _updateUIForMode(mode) {
        // Update UI elements based on analysis mode
        if (mode === 'frequency_map') {
            // Update frequency input hint
            this.dom.params.frequencyInputHint.classList.remove('hidden');
            this.dom.params.frequencyInput.placeholder = 'e.g., 10,20,50,100,200,500,1000';

            // Hide num files input, show frequency map hint
            this.dom.params.numFilesContainer.classList.add('hidden');
            this.dom.params.numFilesFrequencyMapHint.classList.remove('hidden');

            // Switch button text
            this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';
        } else {
            // Continuous monitor mode
            this.dom.params.frequencyInputHint.classList.add('hidden');
            this.dom.params.frequencyInput.placeholder = '';

            // Show num files input, hide frequency map hint
            this.dom.params.numFilesContainer.classList.remove('hidden');
            this.dom.params.numFilesFrequencyMapHint.classList.add('hidden');

            this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
        }
    }

    _setupFrequencyMapSocketHandlers() {
        // Handle frequency map update from server
        this.socketManager.on('frequency_map_update', (data) => {
            if (!this.state.isAnalysisRunning || this.state.analysisMode !== 'frequency_map') {
                console.log('Ignoring frequency_map_update: not in frequency map mode or analysis stopped');
                return;
            }

            console.log('Received frequency map update:', data);

            const { frequency, electrode_index, data: freqData } = data;

            // Determine electrode key
            const electrodeKey = electrode_index !== null ? electrode_index.toString() : 'averaged';

            // Initialize electrode data structures if needed
            if (!this.state.frequencyMapData[electrodeKey]) {
                this.state.frequencyMapData[electrodeKey] = {};
            }
            if (!this.state.analyzedFrequencies[electrodeKey]) {
                this.state.analyzedFrequencies[electrodeKey] = [];
            }

            // Check if this frequency was already processed for this electrode (prevent duplicates)
            if (this.state.frequencyMapData[electrodeKey][frequency]) {
                console.warn(`Duplicate update for electrode ${electrodeKey}, frequency ${frequency}Hz - ignoring`);
                return;
            }

            // Store frequency data for this electrode
            this.state.frequencyMapData[electrodeKey][frequency] = freqData;

            // Add to analyzed frequencies list for this electrode
            this.state.analyzedFrequencies[electrodeKey].push(frequency);
            this.state.analyzedFrequencies[electrodeKey].sort((a, b) => a - b); // Keep sorted

            console.log(`Electrode ${electrodeKey}: Processed ${this.state.analyzedFrequencies[electrodeKey].length} / ${this.state.currentFrequencies.length} frequencies`);
            console.log(`Expected frequencies: [${this.state.currentFrequencies.sort((a, b) => a - b).join(', ')}]`);
            console.log(`Analyzed frequencies: [${this.state.analyzedFrequencies[electrodeKey].join(', ')}]`);

            // Check if all frequencies complete for THIS electrode
            const electrodeComplete = this.state.analyzedFrequencies[electrodeKey].length === this.state.currentFrequencies.length;
            console.log(` Electrode ${electrodeKey}: Complete? ${electrodeComplete} (${this.state.analyzedFrequencies[electrodeKey].length}/${this.state.currentFrequencies.length})`);
            console.log(` Current electrode: ${this.state.currentElectrode}, Update electrode: ${electrode_index}`);

            // Only update visualization if this is the currently displayed electrode
            if (electrode_index === this.state.currentElectrode) {
                console.log(`Updating visualization for current electrode ${electrodeKey}`);
                this._updateFrequencyMapStats();

                if (electrodeComplete) {
                    // Show overlay if all frequencies are complete for current electrode
                    console.log(`🎉 All frequencies complete for electrode ${electrodeKey} - SHOWING OVERLAY`);
                    this._updateFrequencyMapOverlay();
                } else {
                    // Update voltammogram plot (top) - only for NEW frequency
                    console.log(` Showing individual frequency ${frequency}Hz for electrode ${electrodeKey}`);
                    this._updateFrequencyMapVoltammogram(freqData);
                }

                // Update frequency-charge plot (bottom) - cumulative
                this._updateFrequencyChargeChart();
            } else {
                console.log(`⏭Not current electrode - skipping visualization update (current: ${this.state.currentElectrode}, received: ${electrode_index})`);
            }

            // Check if all frequencies have been analyzed for ALL electrodes
            const allElectrodesComplete = this._checkAllElectrodesComplete();
            if (allElectrodesComplete) {
                console.log('All frequencies analyzed for all electrodes!');
                this.dom.folderStatus.textContent = `Analysis complete! All electrodes analyzed.`;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';
            }
        });

        // Handle acknowledgment for frequency map session start
        this.socketManager.on('ack_start_frequency_map_session', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'Frequency map analysis started. Agent is scanning files...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';

                // Show alert for user_id related errors
                if (data.message && data.message.includes('User ID')) {
                    alert('Error: ' + data.message + '\n\nPlease go back to the welcome screen and connect to your agent first.');
                }
            }
        });

        // Handle frequency map export response
        this.socketManager.on('export_frequency_map_data_response', (data) => {
            if (data.status === 'success') {
                const filename = this.dom.visualization.exportFrequencyMapDataBtn.dataset.filename || 'frequency_map_export.csv';
                this.dom.visualization.exportFrequencyMapStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerCsvDownload(data.data, filename);
            } else {
                this.dom.visualization.exportFrequencyMapStatus.textContent = `Export failed: ${data.message}`;
            }
        });
    }

    _updateFrequencyMapVoltammogram(freqData) {
        const plotDiv = this.dom.visualization.frequencyMapVoltammogramPlot;

        // Show individual frequency plot
        const traces = [];

        // Smoothed data trace
        if (freqData.smoothed_currents && freqData.smoothed_currents.length > 0) {
            traces.push({
                x: freqData.potentials,
                y: freqData.smoothed_currents, // Keep in Amperes (A)
                type: 'scatter',
                mode: 'markers',
                name: 'Smoothed Data',
                marker: { size: 3, color: 'black' }
            });
        }

        // Regression line trace
        if (freqData.regression_line && freqData.regression_line.length > 0) {
            traces.push({
                x: freqData.adjusted_potentials || freqData.potentials,
                y: freqData.regression_line, // Keep in Amperes (A)
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline',
                line: { color: 'red', width: 2 }
            });
        }

        const layout = {
            title: `Voltammogram at ${freqData.frequency} Hz`,
            xaxis: {
                title: 'Potential (V)',
                autorange: 'reversed' // Texas convention
            },
            yaxis: { title: 'Current (A)' },
            showlegend: true,
            legend: { x: 0.7, y: 1 },
            margin: { l: 60, r: 30, t: 50, b: 50 },
            hovermode: 'closest'
        };

        Plotly.react(plotDiv, traces, layout, { responsive: true });

        // Update label
        this.dom.visualization.currentFrequencyLabel.textContent =
            `Current: ${freqData.frequency} Hz | Peak: ${freqData.peak_value.toExponential(4)} A | Charge: ${freqData.charge.toExponential(4)} C`;
    }

    _updateFrequencyMapOverlay() {
        console.log('🎨 _updateFrequencyMapOverlay called');
        // Show all frequencies overlaid on one plot (no baselines)
        const plotDiv = this.dom.visualization.frequencyMapVoltammogramPlot;
        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

        console.log(`   Electrode: ${electrodeKey}`);
        console.log(`   Analyzed frequencies: ${analyzedFreqs.length} [${analyzedFreqs.join(', ')}]`);
        console.log(`   Frequency data keys: [${Object.keys(electrodeFreqData).join(', ')}]`);

        // Generate color palette for different frequencies
        const colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'];

        const traces = [];
        const sortedFreqs = analyzedFreqs.slice().sort((a, b) => a - b);

        sortedFreqs.forEach((freq, index) => {
            const freqData = electrodeFreqData[freq];
            if (freqData && freqData.smoothed_currents && freqData.smoothed_currents.length > 0) {
                console.log(`   ✓ Adding trace for ${freq}Hz (${freqData.smoothed_currents.length} points, color: ${colors[index % colors.length]})`);
                traces.push({
                    x: freqData.potentials,
                    y: freqData.smoothed_currents,
                    type: 'scatter',
                    mode: 'markers',
                    name: `${freq} Hz`,
                    marker: { size: 3, color: colors[index % colors.length] }
                });
            } else {
                console.warn(`   ✗ Missing data for ${freq}Hz`);
            }
        });

        console.log(`   Total traces: ${traces.length}`);

        const layout = {
            title: 'Frequency Map: All Frequencies Overlay',
            xaxis: {
                title: 'Potential (V)',
                autorange: 'reversed' // Texas convention
            },
            yaxis: { title: 'Current (A)' },
            showlegend: true,
            legend: { x: 1.05, y: 1, xanchor: 'left' },
            margin: { l: 60, r: 120, t: 50, b: 50 },
            hovermode: 'closest'
        };

        console.log(`   Calling Plotly.react with ${traces.length} traces`);
        Plotly.react(plotDiv, traces, layout, { responsive: true });

        // Update label
        this.dom.visualization.currentFrequencyLabel.textContent =
            `Analysis Complete - Showing all ${sortedFreqs.length} frequencies`;
        console.log(`   ✓ Overlay plot complete!`);
    }

    _updateFrequencyChargeChart() {
        const plotDiv = this.dom.visualization.frequencyMapChargePlot;

        // Get data for current electrode
        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

        if (analyzedFreqs.length === 0) {
            return; // No data to plot yet
        }

        // Sort data by frequency
        const sortedFrequencies = analyzedFreqs.slice().sort((a, b) => a - b);
        const charges = sortedFrequencies.map(freq => electrodeFreqData[freq].charge);

        const trace = {
            x: sortedFrequencies,
            y: charges,
            type: 'scatter',
            mode: 'markers+lines',
            name: 'Charge vs Frequency',
            marker: { size: 8, color: 'blue' },
            line: { color: 'blue', width: 2 }
        };

        const layout = {
            title: 'Frequency Map: Charge vs Frequency',
            xaxis: {
                title: 'Frequency (Hz)',
                type: 'log', // Logarithmic scale
                autorange: true
            },
            yaxis: { title: 'Charge (C)' },
            showlegend: false,
            margin: { l: 60, r: 30, t: 50, b: 50 },
            hovermode: 'closest'
        };

        Plotly.react(plotDiv, [trace], layout, { responsive: true });
    }

    _updateFrequencyMapStats() {
        // Update stats for current electrode
        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};

        this.dom.visualization.analyzedFrequenciesCount.textContent = analyzedFreqs.length;

        if (analyzedFreqs.length > 0) {
            const latestFreq = analyzedFreqs[analyzedFreqs.length - 1];
            const latestData = electrodeFreqData[latestFreq];
            if (latestData) {
                this.dom.visualization.latestFrequency.textContent = latestFreq;
                this.dom.visualization.latestCharge.textContent = latestData.charge.toExponential(4);
            }
        } else {
            this.dom.visualization.latestFrequency.textContent = '-';
            this.dom.visualization.latestCharge.textContent = '-';
        }
    }

    _checkAllElectrodesComplete() {
        // Check if all expected electrodes have analyzed all frequencies
        const expectedElectrodes = this.state.selectedElectrodes.length > 0
            ? this.state.selectedElectrodes
            : [null]; // null represents averaged

        for (const electrode of expectedElectrodes) {
            const electrodeKey = electrode !== null ? electrode.toString() : 'averaged';
            const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

            if (analyzedFreqs.length < this.state.currentFrequencies.length) {
                return false; // This electrode hasn't finished yet
            }
        }

        return true; // All electrodes complete
    }

    _switchFrequencyMapElectrode(electrodeIdx) {
        // Switch electrode in frequency map mode
        if (this.state.currentElectrode === electrodeIdx) return;

        console.log(`Switching frequency map to electrode ${electrodeIdx}`);
        this.state.currentElectrode = electrodeIdx;

        // Update electrode button states
        this._setupElectrodeControls();

        // Get data for this electrode
        const electrodeKey = electrodeIdx !== null ? electrodeIdx.toString() : 'averaged';
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

        // Update statistics
        this._updateFrequencyMapStats();

        // Check if all frequencies are complete for this electrode
        const allFrequenciesComplete = analyzedFreqs.length === this.state.currentFrequencies.length;

        if (analyzedFreqs.length > 0) {
            if (allFrequenciesComplete) {
                // Show overlay of all frequencies
                this._updateFrequencyMapOverlay();
            } else {
                // Show latest individual voltammogram
                const latestFreq = analyzedFreqs[analyzedFreqs.length - 1];
                const latestData = electrodeFreqData[latestFreq];
                if (latestData) {
                    this._updateFrequencyMapVoltammogram(latestData);
                }
            }
        } else {
            // No data yet for this electrode, show waiting message
            this.dom.visualization.currentFrequencyLabel.textContent = 'No data for this electrode yet';
        }

        // Update charge chart
        this._updateFrequencyChargeChart();
    }
}


