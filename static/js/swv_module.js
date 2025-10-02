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
            currentFrequencies: [],
            currentNumFiles: 0,
            currentXAxisOptions: "File Number",
            currentKdmHighFreq: null,
            currentKdmLowFreq: null,
            rawTrendData: null, // Holds the raw peak currents from the server
            lastCalculatedData: null, // Holds the last fully calculated trend object
            selectedElectrodes: [], // List of selected electrodes
            currentElectrode: null, // Currently displayed electrode (null for averaged)
            electrodeData: {} // Raw data for each electrode
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
        this._setupFilterModeToggle();
    }

    _setupEventListeners() {
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
            const electrodeInfo = this.state.currentElectrode !== null ? `_Electrode_${this.state.currentElectrode + 1}` : '_Averaged';  // Display as 1-based
            const defaultFilename = `SACMES_Analysis${electrodeInfo}_${new Date().toISOString().slice(0, 10)}.csv`;
            const filename = prompt("Please enter a filename for the CSV export:", defaultFilename);
            if (filename) {
                this.dom.visualization.exportDataBtn.dataset.filename = filename;
                this.dom.visualization.exportStatus.textContent = 'Generating export file...';
                // Send current electrode info to server for correct data export
                this.socketManager.emit('request_export_data', {
                    current_electrode: this.state.currentElectrode
                });
            }
        });

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
        const numFiles = parseInt(this.dom.params.numFilesInput.value);
        if (isNaN(numFiles) || numFiles < 1) { alert("Please enter a valid number of files."); return; }
        const frequencies = this.dom.params.frequencyInput.value.split(',').map(f => parseInt(f.trim())).filter(f => !isNaN(f));
        if (frequencies.length < 2) { alert("Please enter at least two valid frequencies."); return; }

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
            isAnalysisRunning: true, currentFrequencies: frequencies, currentNumFiles: numFiles,
            currentXAxisOptions: this.dom.settings.xAxisOptionsInput.value,
            currentKdmHighFreq: Math.max(...frequencies), currentKdmLowFreq: Math.min(...frequencies),
            rawTrendData: null, lastCalculatedData: null,
            selectedElectrodes: selectedElectrodes,
            currentElectrode: selectedElectrodes.length > 0 ? selectedElectrodes[0] : null,
            electrodeData: {}
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
        this._setupVisualizationLayout();
        this._setupElectrodeControls();
        this.uiManager.showScreen('visualizationArea');
        this.dom.visualization.adjustmentControls.classList.remove('hidden');
        this.dom.visualization.exportDataBtn.classList.remove('hidden');
        this.dom.visualization.exportStatus.textContent = '';
        // Clear warnings at the start of analysis
        this.dom.visualization.peakDetectionWarnings.classList.add('hidden');
        this.dom.visualization.warningsList.innerHTML = '';
        this.socketManager.emit('start_analysis_session', { filters, analysisParams });
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
        PlotlyPlotter.renderFullTrendPlot('peakCurrentTrendPlot', trendData, freqStrs, xAxisTitle, `Peak Current (${this.dom.settings.currentUnitsInput.value})`, this.state.currentNumFiles, '', 'peak', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('normalizedPeakTrendPlot', trendData, freqStrs, xAxisTitle, 'Normalized Current', this.state.currentNumFiles, '', 'normalized', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('kdmTrendPlot', trendData, freqStrs, xAxisTitle, 'KDM Value', this.state.currentNumFiles, '', 'kdm', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
    }
    
    _setupElectrodeControls() {
        const { electrodeControls } = this.dom.visualization;
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
                btn.onclick = () => this._switchElectrode(electrodeIdx);
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

        // Ensure trend plots container is visible for SWV
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            trendPlotsContainer.style.display = '';
            console.log('SWV: Ensured trendPlotsContainer is visible');
        }

        console.log('SWV: CV remnants cleanup complete');
    }

    _setupVisualizationLayout() {
        // Clean up any CV remnants before setting up SWV visualization
        this._cleanupCVRemnants();

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
}

