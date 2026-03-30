// static/js/swv_module.js (Final version with persistent client-side state)

import { PlotlyPlotter } from './plot_utils.js';
import { bindIfPresent, clearChildren, setSelectOptions, setSingleMessage } from './dom_utils.js';

const SWV_DEBUG = false;
const swvDebug = (...args) => {
    if (SWV_DEBUG) console.log(...args);
};
const swvWarnDebug = (...args) => {
    if (SWV_DEBUG) console.warn(...args);
};

export class SWVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        this.dom = {
            swvBtn: document.getElementById('swvBtn'),
            backToWelcomeBtn: document.getElementById('backToWelcomeFromSWV'),
            startAnalysisBtn: document.getElementById('startAnalysisBtn'),
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
                hampelModeInputs: document.querySelectorAll('input[name="hampelMode"]'),
                sgModeInputs: document.querySelectorAll('input[name="sgMode"]'),
                hampelWindowInput: document.getElementById('hampelWindowInput'),
                hampelThresholdInput: document.getElementById('hampelThresholdInput'),
                sgWindowInput: document.getElementById('sgWindowInput'),
                sgDegreeInput: document.getElementById('sgDegreeInput'),
                polyfitDegreeInput: document.getElementById('polyfitDegreeInput'),
                cutoffFrequencyInput: document.getElementById('cutoffFrequencyInput'),
                lowXstartInput: document.getElementById('lowXstartInput'),
                lowXendInput: document.getElementById('lowXendInput'),
                highXstartInput: document.getElementById('highXstartInput'),
                highXendInput: document.getElementById('highXendInput'),
            },
            settings: {
                voltageColumnInput: document.getElementById('voltageColumnInput'),
                currentColumnInput: document.getElementById('currentColumnInput'),
                spacingIndexInput: document.getElementById('spacingIndexInput'),
                delimiterInput: document.getElementById('delimiterInput'),
                fileExtensionInput: document.getElementById('fileExtensionInput'),
                sampleRateInput: document.getElementById('sampleRateInput'),
                selectedOptionsInput: document.getElementById('selectedOptionsInput'),
                xAxisOptionsInput: document.getElementById('xAxisOptionsInput'),
            },
            visualization: {
                visualizationArea: document.getElementById('visualizationArea'),
                electrodeControls: document.getElementById('electrodeControls'),
                continuousMonitorContainer: document.getElementById('continuousMonitorContainer'),
                frequencyMapContainer: document.getElementById('frequencyMapContainer'),
                holdModeVoltammogramContainer: document.getElementById('holdModeVoltammogramContainer'),
                nonHoldModeContainer: document.getElementById('nonHoldModeContainer'),
                heldSessionVoltammogramTitle: document.getElementById('heldSessionVoltammogramTitle'),
                currentSessionVoltammogramTitle: document.getElementById('currentSessionVoltammogramTitle'),
                heldSessionVoltammogramPlot: document.getElementById('heldSessionVoltammogramPlot'),
                frequencyMapVoltammogramPlot: document.getElementById('frequencyMapVoltammogramPlot'),
                frequencyMapChargePlot: document.getElementById('frequencyMapChargePlot'),
                nonHoldVoltammogramPlot: document.getElementById('nonHoldVoltammogramPlot'),
                nonHoldChargePlot: document.getElementById('nonHoldChargePlot'),
                currentFrequencyLabel: document.getElementById('currentFrequencyLabel'),
                nonHoldFrequencyLabel: document.getElementById('nonHoldFrequencyLabel'),
                analyzedFrequenciesCount: document.getElementById('analyzedFrequenciesCount'),
                latestFrequency: document.getElementById('latestFrequency'),
                latestCharge: document.getElementById('latestCharge'),
                exportFrequencyMapDataBtn: document.getElementById('exportFrequencyMapDataBtn'),
                exportFrequencyMapStatus: document.getElementById('exportFrequencyMapStatus'),
                holdFrequencyMapDataBtn: document.getElementById('holdFrequencyMapDataBtn'),
                sessionNamingModal: document.getElementById('sessionNamingModal'),
                currentSessionNameInput: document.getElementById('currentSessionNameInput'),
                nextSessionNameInput: document.getElementById('nextSessionNameInput'),
                confirmSessionNamingBtn: document.getElementById('confirmSessionNamingBtn'),
                cancelSessionNamingBtn: document.getElementById('cancelSessionNamingBtn'),
                holdModeStatus: document.getElementById('holdFrequencyMapStatus'),
                individualPlotsContainer: document.getElementById('individualPlotsContainer'),
                trendPlotsContainer: document.getElementById('trendPlotsContainer'),
                kdmHighFreqSelect: document.getElementById('kdmHighFreqSelect'),
                kdmLowFreqSelect: document.getElementById('kdmLowFreqSelect'),
                correction: {
                    freqSelect: document.getElementById('corrFreqSelect'),
                    fileNumInput: document.getElementById('corrFileNumInput'),
                    electrodeSelect: document.getElementById('corrElectrodeSelect'),
                    loadBtn: document.getElementById('corrLoadBtn'),
                    voltammogramPlaceholder: document.getElementById('corrVoltammogramPlaceholder'),
                    voltammogramDiv: document.getElementById('corrVoltammogramDiv'),
                    baselineV1: document.getElementById('corrBaselineV1'),
                    baselineV2: document.getElementById('corrBaselineV2'),
                    peakV: document.getElementById('corrPeakV'),
                    currentValueSpan: document.getElementById('corrCurrentValueSpan'),
                    newValueSpan: document.getElementById('corrNewValueSpan'),
                    statusSpan: document.getElementById('corrStatusSpan'),
                    applyBtn: document.getElementById('corrApplyBtn'),
                    resetBtn: document.getElementById('corrResetBtn'),
                    header: document.getElementById('postCorrectionHeader'),
                    body: document.getElementById('postCorrectionBody'),
                    toggle: document.getElementById('postCorrectionToggle'),
                },
                fmCorrection: {
                    sessionSelectContainer: document.getElementById('fmCorrSessionSelectContainer'),
                    sessionSelect: document.getElementById('fmCorrSessionSelect'),
                    electrodeSelect: document.getElementById('fmCorrElectrodeSelect'),
                    freqSelect: document.getElementById('fmCorrFreqSelect'),
                    loadBtn: document.getElementById('fmCorrLoadBtn'),
                    voltammogramPlaceholder: document.getElementById('fmCorrVoltammogramPlaceholder'),
                    voltammogramDiv: document.getElementById('fmCorrVoltammogramDiv'),
                    baselineV1: document.getElementById('fmCorrBaselineV1'),
                    baselineV2: document.getElementById('fmCorrBaselineV2'),
                    peakV: document.getElementById('fmCorrPeakV'),
                    currentValueSpan: document.getElementById('fmCorrCurrentValue'),
                    newValueSpan: document.getElementById('fmCorrNewValue'),
                    newChargeSpan: document.getElementById('fmCorrNewCharge'),
                    statusSpan: document.getElementById('fmCorrStatus'),
                    applyBtn: document.getElementById('fmCorrApplyBtn'),
                    resetBtn: document.getElementById('fmCorrResetBtn'),
                },
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
                applyPostProcessNormalizationBtn: document.getElementById('applyPostProcessNormalizationBtn'),
                replicationInput: document.getElementById('replicationInput'),
                applyReplicationBtn: document.getElementById('applyReplicationBtn'),
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
            analyzedFrequencies: {}, // {electrode: [frequencies]} - analyzed frequencies per electrode
            heldData: null, // Holds previous session data for comparison
            heldFrequencies: null, // Holds frequency list for held session
            groupedData: null, // Holds grouped data when replication is applied
            heldSessionName: null, // Name of the held session
            currentSessionName: null, // Name of the current session
            correctionOverrides: {}, // {electrodeKey: {freqStr: {fileNumStr: {peak_value, peak_potential}}}}
            correctionLoadedData: null, // Raw voltammogram data loaded for correction preview
            frequencyMapCorrectionOverrides: {}, // {sessionKey: {electrodeKey: {freqStr: {peak_value, charge, peak_potential}}}}
            frequencyMapCorrectionLoadedData: null // Voltammogram data loaded for FM correction preview
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
        this._setupFrequencyMapSocketHandlers();
        this._setupFilterModeToggle();
    }

    _setupEventListeners() {
        // Analysis mode toggle
        bindIfPresent(this.dom.params.analysisModeInputs, 'change', (e) => {
                this.state.analysisMode = e.target.value;
                this._updateUIForMode(e.target.value);
        });

        bindIfPresent(this.dom.swvBtn, 'click', () => this.uiManager.showScreen('swvAnalysisScreen'));
        bindIfPresent(this.dom.startAnalysisBtn, 'click', this._handleStartAnalysis.bind(this));
        bindIfPresent(this.dom.backToWelcomeBtn, 'click', () => this.uiManager.showScreen('welcomeScreen'));
        
        bindIfPresent(this.dom.visualization.backToSWVBtn, 'click', () => {
            this._handleBackToSettings();
        });
        
        bindIfPresent(this.dom.visualization.exportDataBtn, 'click', () => {
            const defaultFilename = `SACMES_SWV_AllElectrodes_${new Date().toISOString().slice(0, 10)}.xlsx`;
            const filename = prompt("Please enter a filename for the Excel export:", defaultFilename);
            if (filename) {
                this.dom.visualization.exportStatus.textContent = 'Generating export file...';
                const csvData = this.state.groupedData && this.state.currentReplication > 1
                    ? this._generateGroupedCSV()
                    : this._generateFullCSV();
                if (csvData) {
                    this.socketManager.emit('request_pack_xlsx_from_csv', {
                        target: 'swv',
                        filename,
                        csv_text: csvData
                    });
                } else {
                    this.dom.visualization.exportStatus.textContent = 'Export failed: No data available.';
                }
            }
        });

        // Frequency Map export all electrodes button
        if (this.dom.visualization.exportFrequencyMapDataBtn) {
            this.dom.visualization.exportFrequencyMapDataBtn.addEventListener('click', () => {
                const defaultFilename = `SACMES_FrequencyMap_AllElectrodes_${new Date().toISOString().slice(0, 10)}.xlsx`;
                const filename = prompt("Please enter a filename for the Excel export:", defaultFilename);
                if (filename) {
                    this.dom.visualization.exportFrequencyMapDataBtn.dataset.filename = filename;
                    this.dom.visualization.exportFrequencyMapStatus.textContent = 'Generating export file...';

                    // Generate sectioned CSV client-side so correction overrides are reflected,
                    // then let the backend package it as a multi-sheet workbook.
                    if (this.state.heldData !== null) {
                        const csvData = this._generateHoldModeCSV();
                        this.socketManager.emit('request_pack_xlsx_from_csv', {
                            target: 'frequency_map',
                            filename,
                            csv_text: csvData
                        });
                    } else {
                        const csvData = this._generateNonHoldModeCSV();
                        this.socketManager.emit('request_pack_xlsx_from_csv', {
                            target: 'frequency_map',
                            filename,
                            csv_text: csvData
                        });
                    }
                }
            });
        }

        // Hold Frequency Map Data button
        if (this.dom.visualization.holdFrequencyMapDataBtn) {
            this.dom.visualization.holdFrequencyMapDataBtn.addEventListener('click', () => {
                // Check if already in hold mode
                if (this.state.heldData !== null) {
                    alert('Already in hold mode. To start a new comparison, please reload the page.');
                    return;
                }

                // Check if we have frequency map data to hold
                if (!this.state.frequencyMapData || Object.keys(this.state.frequencyMapData).length === 0) {
                    alert('No frequency map data available to hold. Please run an analysis first.');
                    return;
                }

                // Show the session naming modal
                this.dom.visualization.sessionNamingModal.classList.remove('hidden');

                // Pre-fill with default names if empty
                if (!this.dom.visualization.currentSessionNameInput.value) {
                    this.dom.visualization.currentSessionNameInput.value = 'Session 1';
                }
                if (!this.dom.visualization.nextSessionNameInput.value) {
                    this.dom.visualization.nextSessionNameInput.value = 'Session 2';
                }
            });
        }

        // Session naming modal - Confirm button
        if (this.dom.visualization.confirmSessionNamingBtn) {
            this.dom.visualization.confirmSessionNamingBtn.addEventListener('click', () => {
                const currentName = this.dom.visualization.currentSessionNameInput.value.trim();
                const nextName = this.dom.visualization.nextSessionNameInput.value.trim();

                if (!currentName || !nextName) {
                    alert('Please provide names for both sessions.');
                    return;
                }

                // Store the current data as held data
                this.state.heldData = JSON.parse(JSON.stringify(this.state.frequencyMapData));
                this.state.heldFrequencies = [...this.state.currentFrequencies]; // Store frequency list for held session
                this.state.heldSessionName = currentName;
                this.state.currentSessionName = nextName;

                // Migrate 'current' FM correction overrides to 'session1' (persists across hold)
                if (this.state.frequencyMapCorrectionOverrides['current']) {
                    this.state.frequencyMapCorrectionOverrides['session1'] =
                        JSON.parse(JSON.stringify(this.state.frequencyMapCorrectionOverrides['current']));
                    delete this.state.frequencyMapCorrectionOverrides['current'];
                }

                // Show session selector in FM correction panel
                const fmc = this.dom.visualization.fmCorrection;
                if (fmc?.sessionSelectContainer) {
                    fmc.sessionSelectContainer.classList.remove('hidden');
                }

                swvDebug('[HOLD MODE] Stored session data:', {
                    sessionName: currentName,
                    frequencies: this.state.heldFrequencies,
                    electrodes: Object.keys(this.state.heldData)
                });

                // Clear frequency checkboxes to prevent confusion with old frequency list
                const checkboxContainer = document.getElementById('frequencyCheckboxContainer');
                if (checkboxContainer) {
                    setSingleMessage(
                        checkboxContainer,
                        'Please scan folder again or manually enter frequencies for the new session.',
                        'text-sm text-gray-500 col-span-4'
                    );
                    swvDebug('[HOLD MODE] Cleared frequency checkboxes for new session');
                }

                // Update status message
                if (this.dom.visualization.holdModeStatus) {
                    this.dom.visualization.holdModeStatus.textContent = `Held: ${currentName} | Ready for: ${nextName}`;
                    this.dom.visualization.holdModeStatus.classList.remove('hidden');
                }

                // Hide modal
                this.dom.visualization.sessionNamingModal.classList.add('hidden');

                // Navigate back to settings page
                this.uiManager.showScreen('swvAnalysisScreen');

                // Clear current frequency map data to prepare for next session
                this.state.frequencyMapData = {};
                this.state.analyzedFrequencies = {};
            });
        }

        // Session naming modal - Cancel button
        if (this.dom.visualization.cancelSessionNamingBtn) {
            this.dom.visualization.cancelSessionNamingBtn.addEventListener('click', () => {
                // Hide modal without saving
                this.dom.visualization.sessionNamingModal.classList.add('hidden');
            });
        }

        // Apply adjustments button (re-normalize, injection point, low freq offset/slope)
        this.dom.visualization.applyPostProcessNormalizationBtn.addEventListener('click', () => this._handlePostProcessUpdate());

        // Apply replication button (separate, for grouping data after analysis)
        this.dom.visualization.applyReplicationBtn.addEventListener('click', () => this._handleReplicationGrouping());

        // Add listener for x-axis options change during analysis
        this.dom.settings.xAxisOptionsInput.addEventListener('change', () => {
            if (this.state.isAnalysisRunning && this.state.lastCalculatedData) {
                this.state.currentXAxisOptions = this.dom.settings.xAxisOptionsInput.value;
                // Recalculate trends with new x-axis option
                this._handlePostProcessUpdate();
            }
        });

        // Frequency selector event listeners
        const scanFreqBtn = document.getElementById('scanFrequenciesBtn');
        const selectAllBtn = document.getElementById('selectAllFreqBtn');
        const deselectAllBtn = document.getElementById('deselectAllFreqBtn');
        const applyFreqBtn = document.getElementById('applyFreqSelectionBtn');

        if (scanFreqBtn) {
            scanFreqBtn.addEventListener('click', () => {
                swvDebug('[FREQUENCY SCAN] Scan button clicked');
                const fileHandle = this.dom.params.fileHandleInput.value.trim();
                swvDebug('[FREQUENCY SCAN] File handle:', fileHandle);

                // Get folder path from monitoring input
                const folderPathInput = document.getElementById('swvFolderPathInput');
                const folderPath = folderPathInput ? folderPathInput.value.trim() : '';

                if (!folderPath) {
                    alert('Please enter a folder path first to scan for frequencies.');
                    return;
                }

                swvDebug('[FREQUENCY SCAN] Emitting scan_available_frequencies');
                swvDebug('[FREQUENCY SCAN] Folder path:', folderPath);
                swvDebug('[FREQUENCY SCAN] File handle:', fileHandle);

                this.socketManager.emit('scan_available_frequencies', {
                    folder_path: folderPath,
                    file_handle: fileHandle
                });
                swvDebug('[FREQUENCY SCAN] Event emitted successfully');

                scanFreqBtn.textContent = 'Scanning...';
                scanFreqBtn.disabled = true;
            });
        }

        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                document.querySelectorAll('#frequencyCheckboxContainer input[type="checkbox"]').forEach(cb => {
                    cb.checked = true;
                });
            });
        }

        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', () => {
                document.querySelectorAll('#frequencyCheckboxContainer input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
            });
        }

        if (applyFreqBtn) {
            applyFreqBtn.addEventListener('click', () => {
                const selectedFreqs = [];
                document.querySelectorAll('#frequencyCheckboxContainer input[type="checkbox"]:checked').forEach(cb => {
                    selectedFreqs.push(cb.value);
                });
                this.dom.params.frequencyInput.value = selectedFreqs.join(',');
            });
        }
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
        // Listen for file processing status updates
        this.socketManager.on('file_processing_status', (data) => {
            swvDebug(`[FILE STATUS] ${data.status}: ${data.message}`);
            if (this.dom.folderStatus) {
                const statusIcon = data.status === 'processing' ? '[PROCESSING]' :
                                  data.status === 'analyzing' ? '[ANALYZING]' :
                                  data.status === 'complete' ? '[OK]' : '[FILE]';
                this.dom.folderStatus.textContent = `${statusIcon} ${data.message}`;
            }
        });

        this.socketManager.on('live_analysis_update', (data) => {
            if (!this.state.isAnalysisRunning) return;

            // Check if electrode matches (handle 'averaged' vs null comparison)
            const isCurrentElectrode = (data.electrode_index === this.state.currentElectrode) ||
                                      (data.electrode_index === 'averaged' && this.state.currentElectrode === null) ||
                                      (data.electrode_index === null && this.state.currentElectrode === null);

            // 1. Store electrode-specific data (memory optimized)
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

                    // Store complete data for the LATEST file to enable voltammogram display
                    // For older files, only store essential data for trend reconstruction
                    const isLatestFile = !this.state.electrodeData[electrodeKey][freq] ||
                                        Object.keys(this.state.electrodeData[electrodeKey][freq]).length === 0 ||
                                        fileNum >= Math.max(...Object.keys(this.state.electrodeData[electrodeKey][freq]).map(Number));

                    if (isLatestFile) {
                        // Keep complete voltammogram data for the latest file
                        this.state.electrodeData[electrodeKey][freq][fileNum] = {
                            peak_value: data.individual_analysis.peak_value,
                            peak_info: data.individual_analysis.peak_info,
                            peak_potential: data.individual_analysis.peak_info?.peak_potential,
                            // Full voltammogram data for visualization
                            potentials: data.individual_analysis.potentials,
                            raw_currents: data.individual_analysis.raw_currents,
                            smoothed_currents: data.individual_analysis.smoothed_currents,
                            regression_line: data.individual_analysis.regression_line,
                            adjusted_potentials: data.individual_analysis.adjusted_potentials,
                            auc_vertices: data.individual_analysis.auc_vertices,
                            peak_baseline_line: data.individual_analysis.peak_baseline_line
                        };

                        // Clean up previous files' full data (keep only essential data)
                        for (const prevFileNum in this.state.electrodeData[electrodeKey][freq]) {
                            const prevFileNumInt = parseInt(prevFileNum);
                            if (prevFileNumInt < fileNum) {
                                const prevData = this.state.electrodeData[electrodeKey][freq][prevFileNum];
                                // Only keep essential data for trend reconstruction
                                this.state.electrodeData[electrodeKey][freq][prevFileNum] = {
                                    peak_value: prevData.peak_value,
                                    peak_info: prevData.peak_info,
                                    peak_potential: prevData.peak_potential || prevData.peak_info?.peak_potential
                                };
                            }
                        }
                    } else {
                        // For non-latest files, only store essential data
                        this.state.electrodeData[electrodeKey][freq][fileNum] = {
                            peak_value: data.individual_analysis.peak_value,
                            peak_info: data.individual_analysis.peak_info,
                            peak_potential: data.individual_analysis.peak_info?.peak_potential
                        };
                    }

                    // 3. Update individual plots only if this is the currently displayed electrode
                    if (isCurrentElectrode) {
                        this._updateIndividualPlotsUI(data.filename, data.individual_analysis);
                    }
                }
            }

            // 2. PERFORMANCE OPTIMIZATION: Handle incremental vs full data updates
            let shouldRedraw = false;

            // 2a. Incremental update: Only update single data point (reduces data transfer by 99%)
            if (data.incremental_data && isCurrentElectrode) {
                const inc = data.incremental_data;
                const freqKey = inc.frequency.toString();
                const fileIndex = inc.file_number - 1; // Convert to 0-based index

                // Initialize rawTrendData if not exists
                if (!this.state.rawTrendData) {
                    this.state.rawTrendData = {
                        peak_current_trends: {},
                        peak_potential_trends: {},
                        x_axis_values: []
                    };
                }

                // Ensure peak_current_trends exists
                if (!this.state.rawTrendData.peak_current_trends) {
                    this.state.rawTrendData.peak_current_trends = {};
                }

                // Ensure peak_potential_trends exists
                if (!this.state.rawTrendData.peak_potential_trends) {
                    this.state.rawTrendData.peak_potential_trends = {};
                }

                // Initialize this frequency's array if needed
                if (!this.state.rawTrendData.peak_current_trends[freqKey]) {
                    this.state.rawTrendData.peak_current_trends[freqKey] = [];
                }

                // Initialize peak potential array if needed
                if (!this.state.rawTrendData.peak_potential_trends[freqKey]) {
                    this.state.rawTrendData.peak_potential_trends[freqKey] = [];
                }

                // Update single data point
                this.state.rawTrendData.peak_current_trends[freqKey][fileIndex] = inc.peak_value;

                // NEW: Update peak potential data point
                if (inc.peak_potential !== undefined && inc.peak_potential !== null) {
                    this.state.rawTrendData.peak_potential_trends[freqKey][fileIndex] = inc.peak_potential;
                }

                // Ensure x_axis_values array is long enough
                while (this.state.rawTrendData.x_axis_values.length <= fileIndex) {
                    this.state.rawTrendData.x_axis_values.push(this.state.rawTrendData.x_axis_values.length + 1);
                }

                shouldRedraw = true;
                swvDebug(`[PERF] Incremental update: file #${inc.file_number}, freq ${inc.frequency}Hz, peak_potential: ${inc.peak_potential}`);
            }

            // 2b. Full update: Complete synchronization (every 10 files for reliability)
            if (data.trend_data && isCurrentElectrode) {
                this.state.rawTrendData = {
                    peak_current_trends: data.trend_data.peak_current_trends,
                    peak_potential_trends: data.trend_data.peak_potential_trends || {},
                    x_axis_values: data.trend_data.x_axis_values
                };
                shouldRedraw = true;

                // Enhanced logging
                const currentCount = Object.keys(data.trend_data.peak_current_trends || {}).length;
                const potentialCount = Object.keys(data.trend_data.peak_potential_trends || {}).length;
                const fileCount = (data.trend_data.x_axis_values || []).length;

                swvDebug(`[PERF] Full sync update: ${fileCount} files, ${currentCount} current freqs, ${potentialCount} potential freqs`);

                // Log detailed potential data
                if (potentialCount > 0) {
                    Object.keys(data.trend_data.peak_potential_trends).forEach(freq => {
                        const validCount = data.trend_data.peak_potential_trends[freq].filter(v => v != null).length;
                        swvDebug(`  Freq ${freq}Hz: ${validCount} valid potential values`);
                    });
                }
            }

            // 4. Redraw plots if data was updated
            if (shouldRedraw) {
                this._handlePostProcessUpdate();
            }

            // 5. Update peak detection warnings
            if (data.peak_detection_warnings && isCurrentElectrode) {
                this._updatePeakDetectionWarnings(data.peak_detection_warnings);
            }

            // 6. Send acknowledgment to backend (flow control)
            if (data.filename) {
                this.socketManager.emit('acknowledge_file_processed', {
                    filename: data.filename
                });
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
                const filename = data.filename || this.dom.visualization.exportDataBtn.dataset.filename || 'export.xlsx';
                this.dom.visualization.exportStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerWorkbookDownload(data.content_b64, filename);
            } else {
                this.dom.visualization.exportStatus.textContent = `Export failed: ${data.message}`;
            }
        });

        this.socketManager.on('pack_xlsx_response', (data) => {
            if (data.status !== 'success') {
                const message = `Export failed: ${data.message}`;
                if (data.target === 'frequency_map') {
                    this.dom.visualization.exportFrequencyMapStatus.textContent = message;
                } else {
                    this.dom.visualization.exportStatus.textContent = message;
                }
                return;
            }

            const filename = data.filename || 'export.xlsx';
            if (data.target === 'frequency_map') {
                this.dom.visualization.exportFrequencyMapStatus.textContent = `Export successful! Downloading ${filename}...`;
            } else {
                this.dom.visualization.exportStatus.textContent = `Export successful! Downloading ${filename}...`;
            }
            this._triggerWorkbookDownload(data.content_b64, filename);
        });

        this.socketManager.on('electrode_warnings_response', (data) => {
            if (data.status === 'success' && data.electrode_index === this.state.currentElectrode) {
                this._updatePeakDetectionWarnings(data.warnings);
            }
        });

        this.socketManager.on('missing_file_warning', (data) => {
            this._addMissingFileWarning(data);
        });

        this.socketManager.on('file_processing_warning', (data) => {
            this._addFileProcessingWarning(data);
        });

        this.socketManager.on('available_frequencies_response', (data) => {
            swvDebug('[FREQUENCY SCAN] Received available_frequencies_response');
            swvDebug('[FREQUENCY SCAN] Response data:', data);

            const scanFreqBtn = document.getElementById('scanFrequenciesBtn');
            if (scanFreqBtn) {
                scanFreqBtn.textContent = 'Scan Folder';
                scanFreqBtn.disabled = false;
            }

            if (data.status === 'error') {
                console.error('[FREQUENCY SCAN] Error response:', data.message);
                alert('Error scanning frequencies: ' + data.message);
                return;
            }

            const frequencies = data.frequencies || [];
            swvDebug('[FREQUENCY SCAN] Detected frequencies:', frequencies);

            const container = document.getElementById('frequencyCheckboxContainer');
            if (!container) {
                console.error('[FREQUENCY SCAN] Checkbox container not found');
                return;
            }

            clearChildren(container);

            if (frequencies.length === 0) {
                swvWarnDebug('[FREQUENCY SCAN] No frequencies found');
                setSingleMessage(container, 'No frequencies found. Please check your file handle and folder.', 'text-sm text-gray-500 col-span-4');
                return;
            }

            swvDebug('[FREQUENCY SCAN] Creating checkboxes for', frequencies.length, 'frequencies');

            frequencies.forEach(freq => {
                const label = document.createElement('label');
                label.className = 'flex items-center text-sm cursor-pointer hover:bg-gray-100 p-1 rounded';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = freq;
                checkbox.checked = true;
                checkbox.className = 'mr-2';

                const span = document.createElement('span');
                span.textContent = `${freq} Hz`;

                label.appendChild(checkbox);
                label.appendChild(span);
                container.appendChild(label);
            });

            const selectedFreqs = frequencies.join(',');
            this.dom.params.frequencyInput.value = selectedFreqs;
            swvDebug('[FREQUENCY SCAN] Updated frequency input with:', selectedFreqs);
        });
    }

    /**
     * PUBLIC METHOD: Populate historical data for Monitor Mode
     * Called when a monitor device enters monitor mode and receives existing analysis data
     */
    populateHistoricalData(historicalData) {
        swvDebug('SWV Module: Populating historical data for monitor mode', historicalData);

        const trendData = historicalData.trend_data;
        const analysisParams = historicalData.analysis_params;

        if (!trendData || !trendData.raw_peaks) {
            swvWarnDebug('No SWV trend data to populate');
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

        swvDebug('SWV historical data populated successfully');
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

    _generateFullCSV() {
        if (!this.state.electrodeData || !this.state.currentFrequencies?.length) return null;

        const csvLines = [];
        const frequencies = [...this.state.currentFrequencies].sort((a, b) => a - b);
        const freqStrs = frequencies.map(String);
        const numFiles = this.state.currentNumFiles || 0;
        const highFreq = this.state.currentKdmHighFreq;
        const lowFreq = this.state.currentKdmLowFreq;
        const highStr = String(highFreq);
        const lowStr = String(lowFreq);
        const normPoint = parseInt(this.dom.visualization.postProcessNormalizationPointInput?.value) || 1;
        const lowFreqOffset = parseFloat(this.dom.visualization.postProcessLowFrequencyOffsetInput?.value) || 0;
        const lowFreqSlope = parseFloat(this.dom.visualization.postProcessLowFrequencySlopeInput?.value) || 0;
        const isAUC = this.dom.settings?.selectedOptionsInput?.value === 'Area Under the Curve';
        const peakLabel = isAUC ? 'AUC (a.u.)' : 'Peak Current (A)';

        // Determine per-electrode keys (integer keys, excluding 'averaged')
        const electrodeKeys = Object.keys(this.state.electrodeData)
            .filter(k => k !== 'averaged' && !isNaN(parseInt(k)))
            .sort((a, b) => parseInt(a) - parseInt(b));
        const hasPerElectrode = electrodeKeys.length > 0;
        const eLabels = electrodeKeys.map(k => `E${parseInt(k) + 1}`);

        // Helpers — check correctionOverrides first, fall back to raw electrodeData
        const getRaw = (ek, freqStr, fileIdx) => {
            const ov = this.state.correctionOverrides?.[ek]?.[freqStr]?.[String(fileIdx + 1)];
            if (ov) return ov.peak_value;
            return this.state.electrodeData?.[ek]?.[freqStr]?.[fileIdx + 1]?.peak_value ?? null;
        };
        const getPot = (ek, freqStr, fileIdx) => {
            const ov = this.state.correctionOverrides?.[ek]?.[freqStr]?.[String(fileIdx + 1)];
            if (ov?.peak_potential != null) return ov.peak_potential;
            const d = this.state.electrodeData?.[ek]?.[freqStr]?.[fileIdx + 1];
            return d?.peak_potential ?? d?.peak_info?.peak_potential ?? null;
        };
        const avgStd = (arr) => {
            const v = arr.filter(x => x !== null && !isNaN(x));
            if (!v.length) return [null, null];
            const avg = v.reduce((a, b) => a + b, 0) / v.length;
            const std = Math.sqrt(v.reduce((a, b) => a + (b - avg) ** 2, 0) / v.length);
            return [avg, std];
        };
        const fmt = (v, digits = 6) => v !== null && !isNaN(v) ? Number(v).toExponential(digits) : 'N/A';
        const fmtF = (v, digits = 6) => v !== null && !isNaN(v) ? Number(v).toFixed(digits) : 'N/A';

        // Normalization factors: per electrode per frequency, at normPoint file
        const normFactors = {};
        for (const freqStr of freqStrs) {
            normFactors[freqStr] = {};
            const keys = hasPerElectrode ? electrodeKeys : ['averaged'];
            for (const ek of keys) {
                normFactors[freqStr][ek] = getRaw(ek, freqStr, normPoint - 1) || 1;
            }
        }
        const getNormFactor = (ek, freqStr) =>
            normFactors[freqStr]?.[ek] ?? normFactors[freqStr]?.['averaged'] ?? 1;

        const getNorm = (ek, freqStr, fileIdx) => {
            const raw = getRaw(ek, freqStr, fileIdx);
            if (raw === null) return null;
            let n = raw / getNormFactor(ek, freqStr);
            if (freqStr === lowStr) n += (lowFreqSlope * (fileIdx + 1)) + lowFreqOffset;
            return n;
        };

        // Build per-freq header columns for a section
        const freqCols = (suffix) => {
            const cols = [];
            for (const freq of freqStrs) {
                if (hasPerElectrode) eLabels.forEach(el => cols.push(`${freq}Hz_${el}${suffix}`));
                cols.push(`${freq}Hz_Avg${suffix}`);
                if (hasPerElectrode) cols.push(`${freq}Hz_STD${suffix}`);
            }
            return cols;
        };

        // Build a data row for one file across all frequencies using a getValue fn
        const buildRow = (fileIdx, getValue) => {
            const row = [fileIdx + 1];
            for (const freqStr of freqStrs) {
                if (hasPerElectrode) {
                    const perE = electrodeKeys.map(ek => getValue(ek, freqStr, fileIdx));
                    perE.forEach(v => row.push(fmt(v)));
                    const [avg, std] = avgStd(perE);
                    row.push(fmt(avg)); row.push(fmt(std));
                } else {
                    row.push(fmt(getValue('averaged', freqStr, fileIdx)));
                }
            }
            return row;
        };

        // Metadata
        csvLines.push('# SACMES SWV Export');
        csvLines.push(`# Date: ${new Date().toISOString()}`);
        csvLines.push(`# All Frequencies (Hz): ${freqStrs.join(', ')}`);
        csvLines.push(`# KDM Frequencies: High=${highFreq}Hz, Low=${lowFreq}Hz`);
        csvLines.push(`# Normalization Point: File #${normPoint}`);
        csvLines.push(`# Electrodes: ${hasPerElectrode ? eLabels.join(', ') : 'Averaged only'}`);
        csvLines.push('');

        // Section 1: KDM per electrode (first)
        const computeKDM = (ek, i) => {
            const h = getNorm(ek, highStr, i);
            const l = getNorm(ek, lowStr, i);
            return (h !== null && l !== null) ? ((h - l) + 1) * 100 : null;
        };
        csvLines.push(`## KDM (%) - High: ${highFreq}Hz vs Low: ${lowFreq}Hz`);
        const kdmCols = hasPerElectrode ? [...eLabels.map(e => `${e}_KDM`), 'Avg_KDM', 'STD_KDM'] : ['Avg_KDM'];
        csvLines.push(['File#', ...kdmCols].join(','));
        for (let i = 0; i < numFiles; i++) {
            const row = [i + 1];
            if (hasPerElectrode) {
                const perE = electrodeKeys.map(ek => computeKDM(ek, i));
                perE.forEach(v => row.push(fmtF(v, 4)));
                const [avg, std] = avgStd(perE);
                row.push(fmtF(avg, 4)); row.push(fmtF(std, 4));
            } else {
                row.push(fmtF(computeKDM('averaged', i), 4));
            }
            csvLines.push(row.join(','));
        }
        csvLines.push('');

        // Section 2: Raw Peak Current / AUC
        csvLines.push(`## ${peakLabel} - All Frequencies`);
        csvLines.push(['File#', ...freqCols('')].join(','));
        for (let i = 0; i < numFiles; i++) csvLines.push(buildRow(i, getRaw).join(','));
        csvLines.push('');

        // Section 3: Normalized Peak Current
        csvLines.push(`## Normalized Peak Current - All Frequencies (norm. to File #${normPoint})`);
        csvLines.push(['File#', ...freqCols('_Norm')].join(','));
        for (let i = 0; i < numFiles; i++) {
            const row = [i + 1];
            for (const freqStr of freqStrs) {
                if (hasPerElectrode) {
                    const perE = electrodeKeys.map(ek => getNorm(ek, freqStr, i));
                    perE.forEach(v => row.push(fmtF(v)));
                    const [avg, std] = avgStd(perE);
                    row.push(fmtF(avg)); row.push(fmtF(std));
                } else {
                    row.push(fmtF(getNorm('averaged', freqStr, i)));
                }
            }
            csvLines.push(row.join(','));
        }
        csvLines.push('');

        // Section 4: Peak Voltage
        csvLines.push('## Peak Voltage (V) - All Frequencies');
        csvLines.push(['File#', ...freqCols('_V')].join(','));
        for (let i = 0; i < numFiles; i++) csvLines.push(buildRow(i, getPot).join(','));

        return csvLines.join('\n');
    }

    _generateGroupedCSV() {
        if (!this.state.groupedData) {
            console.error('No grouped data available for export');
            return null;
        }

        const csvLines = [];
        const data = this.state.groupedData;
        const replication = this.state.currentReplication;

        // Metadata
        csvLines.push(`# SACMES SWV Data - Grouped by Replication`);
        csvLines.push(`# Export Date: ${new Date().toISOString()}`);
        csvLines.push(`# Replication: n=${replication}`);
        csvLines.push(`# Original Data Points: ${this.state.currentNumFiles}`);
        csvLines.push(`# Grouped Data Points: ${data.num_groups}`);
        csvLines.push(`# Frequencies (Hz): ${this.state.currentFrequencies.join(', ')}`);
        csvLines.push(`# X-axis: ${this.state.currentXAxisOptions}`);
        csvLines.push('');

        const xAxisLabel = this.state.currentXAxisOptions === 'Experiment Time' ? 'Time (min)' : 'Group Number';
        const freqStrings = this.state.currentFrequencies.map(String).sort((a, b) => parseInt(a) - parseInt(b));
        const isAUCMode = this.dom.settings.selectedOptionsInput.value === 'Area Under the Curve';
        const peakSectionLabel = isAUCMode ? 'AUC Trends' : 'Peak Current Trends';
        const peakColLabel = isAUCMode ? 'AUC (a.u.)' : 'Peak Current';

        // Peak Current / AUC Trends section
        csvLines.push(`## ${peakSectionLabel}`);
        csvLines.push('');

        // Build header for peak current / AUC
        const peakHeader = [xAxisLabel, 'X_SE'];
        freqStrings.forEach(freq => {
            peakHeader.push(`${freq}Hz_${peakColLabel}_Mean`);
            peakHeader.push(`${freq}Hz_${peakColLabel}_SE`);
        });
        csvLines.push(peakHeader.join(','));

        // Build data rows for peak current
        for (let i = 0; i < data.num_groups; i++) {
            const row = [];
            row.push(data.x_axis_values[i] != null ? data.x_axis_values[i].toFixed(4) : 'N/A');
            row.push(data.x_axis_errors[i] != null ? data.x_axis_errors[i].toFixed(6) : 'N/A');

            freqStrings.forEach(freq => {
                const mean = data.peak_current_trends[freq][i];
                const se = data.peak_current_errors[freq][i];
                row.push(mean != null ? mean.toExponential(6) : 'N/A');
                row.push(se != null ? se.toExponential(6) : 'N/A');
            });

            csvLines.push(row.join(','));
        }

        csvLines.push('');

        // Normalized Peak Current Trends section
        csvLines.push(`## Normalized Peak Current Trends`);
        csvLines.push('');

        // Build header for normalized peak
        const normHeader = [xAxisLabel, 'X_SE'];
        freqStrings.forEach(freq => {
            normHeader.push(`${freq}Hz_Mean`);
            normHeader.push(`${freq}Hz_SE`);
        });
        csvLines.push(normHeader.join(','));

        // Build data rows for normalized peak
        for (let i = 0; i < data.num_groups; i++) {
            const row = [];
            row.push(data.x_axis_values[i] != null ? data.x_axis_values[i].toFixed(4) : 'N/A');
            row.push(data.x_axis_errors[i] != null ? data.x_axis_errors[i].toFixed(6) : 'N/A');

            freqStrings.forEach(freq => {
                const mean = data.normalized_peak_trends[freq][i];
                const se = data.normalized_peak_errors[freq][i];
                row.push(mean != null ? mean.toFixed(6) : 'N/A');
                row.push(se != null ? se.toFixed(6) : 'N/A');
            });

            csvLines.push(row.join(','));
        }

        csvLines.push('');

        // KDM Trend section
        csvLines.push(`## KDM Trend`);
        csvLines.push('');

        const kdmHeader = [xAxisLabel, 'X_SE', 'KDM_Mean (%)', 'KDM_SE (%)'];
        csvLines.push(kdmHeader.join(','));

        for (let i = 0; i < data.num_groups; i++) {
            const row = [];
            row.push(data.x_axis_values[i] != null ? data.x_axis_values[i].toFixed(4) : 'N/A');
            row.push(data.x_axis_errors[i] != null ? data.x_axis_errors[i].toFixed(6) : 'N/A');
            row.push(data.kdm_trend[i] != null ? data.kdm_trend[i].toFixed(4) : 'N/A');
            row.push(data.kdm_errors[i] != null ? data.kdm_errors[i].toFixed(4) : 'N/A');

            csvLines.push(row.join(','));
        }

        return csvLines.join('\n');
    }

    _generateHoldModeCSV() {
        // Generate CSV for both held and current sessions
        const csvLines = [];

        // Metadata
        csvLines.push(`# SACMES Frequency Map Data - Hold Mode Comparison`);
        csvLines.push(`# Export Date: ${new Date().toISOString()}`);
        csvLines.push(`# Session 1: ${this.state.heldSessionName}`);
        csvLines.push(`# Session 2: ${this.state.currentSessionName}`);
        csvLines.push('');

        // Helper function to calculate mean and std
        const calculateStats = (values) => {
            const validValues = values.filter(v => v !== null && v !== undefined && !isNaN(v));
            if (validValues.length === 0) return { mean: null, std: null };

            const mean = validValues.reduce((sum, v) => sum + v, 0) / validValues.length;
            if (validValues.length === 1) return { mean, std: 0 };

            const variance = validValues.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (validValues.length - 1);
            const std = Math.sqrt(variance);
            return { mean, std };
        };

        // Helper function to generate CSV for one session
        const generateSessionData = (sessionName, sessionData, sessionKey) => {
            const individualElectrodes = Object.keys(sessionData)
                .filter(key => key !== 'averaged')
                .map(key => parseInt(key))
                .sort((a, b) => a - b);

            const allFreqsSet = new Set();
            Object.values(sessionData).forEach(electrodeData => {
                Object.keys(electrodeData).forEach(freq => allFreqsSet.add(parseFloat(freq)));
            });
            const frequencies = Array.from(allFreqsSet).sort((a, b) => a - b);

            // Charge section
            csvLines.push(`## ${sessionName} - Charge (C)`);
            csvLines.push('');
            csvLines.push(['Frequency (Hz)', 'Averaged', ...individualElectrodes.map(idx => `Electrode ${idx + 1}`), 'Std'].join(','));

            frequencies.forEach(freq => {
                const row = [freq];
                const chargeValues = individualElectrodes.map(idx => {
                    const eff = this._getFmEffectiveValues(sessionKey, idx.toString(), freq);
                    return eff?.charge ?? null;
                });
                const chargeStats = calculateStats(chargeValues);
                const avgEff = this._getFmEffectiveValues(sessionKey, 'averaged', freq);
                const avgCharge = avgEff?.charge ?? chargeStats.mean;
                row.push(avgCharge !== null ? avgCharge.toExponential(6) : 'N/A');
                chargeValues.forEach(val => row.push(val !== null ? val.toExponential(6) : 'N/A'));
                row.push(chargeStats.std !== null ? chargeStats.std.toExponential(6) : 'N/A');
                csvLines.push(row.join(','));
            });

            csvLines.push('');

            // Peak Current section
            csvLines.push(`## ${sessionName} - Peak Current (A)`);
            csvLines.push('');
            csvLines.push(['Frequency (Hz)', 'Averaged', ...individualElectrodes.map(idx => `Electrode ${idx + 1}`), 'Std'].join(','));

            frequencies.forEach(freq => {
                const row = [freq];
                const peakValues = individualElectrodes.map(idx => {
                    const eff = this._getFmEffectiveValues(sessionKey, idx.toString(), freq);
                    return eff?.peak_value ?? null;
                });
                const peakStats = calculateStats(peakValues);
                const avgEff = this._getFmEffectiveValues(sessionKey, 'averaged', freq);
                const avgPeak = avgEff?.peak_value ?? peakStats.mean;
                row.push(avgPeak !== null ? avgPeak.toExponential(6) : 'N/A');
                peakValues.forEach(val => row.push(val !== null ? val.toExponential(6) : 'N/A'));
                row.push(peakStats.std !== null ? peakStats.std.toExponential(6) : 'N/A');
                csvLines.push(row.join(','));
            });

            csvLines.push('');
        };

        // Generate held session data (session1) then current session data (session2)
        generateSessionData(this.state.heldSessionName, this.state.heldData, 'session1');
        csvLines.push(''); // Extra blank line between sessions
        generateSessionData(this.state.currentSessionName, this.state.frequencyMapData, 'session2');

        return csvLines.join('\n');
    }

    _generateNonHoldModeCSV() {
        const csvLines = [];
        const sessionData = this.state.frequencyMapData;
        const sessionKey = 'current';

        csvLines.push('# SACMES Frequency Map Data');
        csvLines.push(`# Export Date: ${new Date().toISOString()}`);
        csvLines.push('');

        const calculateStats = (values) => {
            const valid = values.filter(v => v !== null && v !== undefined && !isNaN(v));
            if (valid.length === 0) return { mean: null, std: null };
            const mean = valid.reduce((s, v) => s + v, 0) / valid.length;
            if (valid.length === 1) return { mean, std: 0 };
            const variance = valid.reduce((s, v) => s + Math.pow(v - mean, 2), 0) / (valid.length - 1);
            return { mean, std: Math.sqrt(variance) };
        };

        const individualElectrodes = Object.keys(sessionData)
            .filter(k => k !== 'averaged')
            .map(k => parseInt(k))
            .sort((a, b) => a - b);

        const allFreqsSet = new Set();
        Object.values(sessionData).forEach(ed => Object.keys(ed).forEach(f => allFreqsSet.add(parseFloat(f))));
        const frequencies = Array.from(allFreqsSet).sort((a, b) => a - b);

        // Charge section
        csvLines.push('## Charge (C)');
        csvLines.push('');
        csvLines.push(['Frequency (Hz)', 'Averaged', ...individualElectrodes.map(idx => `Electrode ${idx + 1}`), 'Std'].join(','));

        frequencies.forEach(freq => {
            const row = [freq];
            const chargeValues = individualElectrodes.map(idx => {
                const eff = this._getFmEffectiveValues(sessionKey, idx.toString(), freq);
                return eff?.charge ?? null;
            });
            const stats = calculateStats(chargeValues);
            const avgEff = this._getFmEffectiveValues(sessionKey, 'averaged', freq);
            const avgCharge = avgEff?.charge ?? stats.mean;
            row.push(avgCharge !== null ? avgCharge.toExponential(6) : 'N/A');
            chargeValues.forEach(v => row.push(v !== null ? v.toExponential(6) : 'N/A'));
            row.push(stats.std !== null ? stats.std.toExponential(6) : 'N/A');
            csvLines.push(row.join(','));
        });

        csvLines.push('');

        // Peak Current section
        csvLines.push('## Peak Current (A)');
        csvLines.push('');
        csvLines.push(['Frequency (Hz)', 'Averaged', ...individualElectrodes.map(idx => `Electrode ${idx + 1}`), 'Std'].join(','));

        frequencies.forEach(freq => {
            const row = [freq];
            const peakValues = individualElectrodes.map(idx => {
                const eff = this._getFmEffectiveValues(sessionKey, idx.toString(), freq);
                return eff?.peak_value ?? null;
            });
            const stats = calculateStats(peakValues);
            const avgEff = this._getFmEffectiveValues(sessionKey, 'averaged', freq);
            const avgPeak = avgEff?.peak_value ?? stats.mean;
            row.push(avgPeak !== null ? avgPeak.toExponential(6) : 'N/A');
            peakValues.forEach(v => row.push(v !== null ? v.toExponential(6) : 'N/A'));
            row.push(stats.std !== null ? stats.std.toExponential(6) : 'N/A');
            csvLines.push(row.join(','));
        });

        return csvLines.join('\n');
    }

    _recalculateTrends() {
        // Use current electrode to get the right data
        const currentElectrode = this.state.currentElectrode;
        const electrodeKey = currentElectrode !== null ? currentElectrode.toString() : 'averaged';

        // Always try to reconstruct from stored electrode data first (for electrode switching)
        // Fall back to rawTrendData only if no stored data is available
        let reconstructedData = this._reconstructTrendDataFromElectrodeData(electrodeKey);

        let rawPeaks, rawPotentials;

        // If reconstruction succeeded, use reconstructed data
        if (reconstructedData) {
            rawPeaks = reconstructedData.peak_current_trends;
            rawPotentials = reconstructedData.peak_potential_trends;
            swvDebug('[DEBUG] Using reconstructed data from electrodeData');
        }
        // Otherwise, fall back to rawTrendData from server
        else if (this.state.rawTrendData) {
            rawPeaks = this.state.rawTrendData.peak_current_trends;
            rawPotentials = this.state.rawTrendData.peak_potential_trends || {};
            swvDebug('[DEBUG] Using rawTrendData from server');
        }

        if (!rawPeaks) {
            swvWarnDebug('[DEBUG] _recalculateTrends: No rawPeaks data available!');
            return null;
        }

        // Apply correction overrides (shallow-copy arrays so we don't mutate state)
        const overridesForElectrode = this.state.correctionOverrides && this.state.correctionOverrides[electrodeKey];
        if (overridesForElectrode) {
            rawPeaks = Object.fromEntries(Object.entries(rawPeaks).map(([f, arr]) => [f, [...arr]]));
            rawPotentials = Object.fromEntries(Object.entries(rawPotentials || {}).map(([f, arr]) => [f, [...arr]]));
            for (const freqStr in overridesForElectrode) {
                for (const fileNumStr in overridesForElectrode[freqStr]) {
                    const ov = overridesForElectrode[freqStr][fileNumStr];
                    const idx = parseInt(fileNumStr) - 1;
                    if (rawPeaks[freqStr] && idx >= 0 && idx < rawPeaks[freqStr].length) {
                        rawPeaks[freqStr][idx] = ov.peak_value;
                    }
                    if (ov.peak_potential != null && rawPotentials[freqStr] && idx >= 0 && idx < rawPotentials[freqStr].length) {
                        rawPotentials[freqStr][idx] = ov.peak_potential;
                    }
                }
            }
        }

        swvDebug('[DEBUG] _recalculateTrends: rawPeaks frequencies:', Object.keys(rawPeaks));
        for (const freq in rawPeaks) {
            const validCount = rawPeaks[freq].filter(v => v != null).length;
            swvDebug(`  Freq ${freq}Hz: array length ${rawPeaks[freq].length}, valid values: ${validCount}`);
        }

        // Log peak potential data
        if (rawPotentials && Object.keys(rawPotentials).length > 0) {
            swvDebug('[DEBUG] Peak potential data available:', Object.keys(rawPotentials).length, 'frequencies');
            for (const freq in rawPotentials) {
                const validValues = rawPotentials[freq].filter(v => v !== null && v !== undefined);
                swvDebug(`[DEBUG] Freq ${freq}Hz: ${validValues.length} valid potential values`);
            }
        } else {
            swvWarnDebug('[DEBUG] No peak_potential_trends available after reconstruction!');
            rawPotentials = {};  // Ensure it's at least an empty object
        }

        const newParams = {
            num_files: this.state.currentNumFiles,
            frequencies: this.state.currentFrequencies,
            normalizationPoint: parseInt(this.dom.visualization.postProcessNormalizationPointInput.value)
        };

        const { num_files, frequencies } = newParams;
        const freqStrings = frequencies.map(String).sort((a, b) => parseInt(a) - parseInt(b));
        // Use user-selected KDM frequencies if set, otherwise fall back to min/max
        const lowFreqStr = this.state.currentKdmLowFreq != null
            ? this.state.currentKdmLowFreq.toString()
            : freqStrings[0];
        const highFreqStr = this.state.currentKdmHighFreq != null
            ? this.state.currentKdmHighFreq.toString()
            : freqStrings[freqStrings.length - 1];

        swvDebug('[DEBUG] _recalculateTrends: num_files =', num_files, 'frequencies =', frequencies);

        // Calculate x-axis values based on user preference.
        // "Experiment Time" is always computed client-side from sample rate because the
        // server only ever sends file-number indices [1, 2, 3, ...].
        let x_axis_values;
        if (this.state.currentXAxisOptions === 'Experiment Time') {
            const sampleRate = parseFloat(this.dom.settings.sampleRateInput.value) || 20; // seconds per file
            x_axis_values = Array.from({ length: num_files }, (_, i) => (i * sampleRate) / 60);
        } else if (this.state.rawTrendData && this.state.rawTrendData.x_axis_values &&
                   this.state.rawTrendData.x_axis_values.length === num_files) {
            // File Number mode: use server-provided indices directly
            x_axis_values = this.state.rawTrendData.x_axis_values;
        } else {
            x_axis_values = Array.from({ length: num_files }, (_, i) => i + 1);
        }

        const recalculated = {
            x_axis_values: x_axis_values,
            peak_current_trends: rawPeaks,
            normalized_peak_trends: {},
            peak_potential_trends: rawPotentials,  // NEW: Include peak potential data
            kdm_trend: Array(num_files).fill(null)
        };

        const normFactors = {};
        for (const freq of freqStrings) {
            const normIdx = newParams.normalizationPoint - 1;
            const normValue = (rawPeaks[freq] && normIdx >= 0 && normIdx < rawPeaks[freq].length) ? rawPeaks[freq][normIdx] : 1.0;
            normFactors[freq] = (normValue && normValue !== 0) ? normValue : 1.0;
            recalculated.normalized_peak_trends[freq] = Array(num_files).fill(null);
        }

        // Get low frequency adjustment parameters
        const lowFreqOffset = parseFloat(this.dom.visualization.postProcessLowFrequencyOffsetInput.value) || 0;
        const lowFreqSlope = parseFloat(this.dom.visualization.postProcessLowFrequencySlopeInput.value) || 0;

        for (let i = 0; i < num_files; i++) {
            // First normalize all frequencies
            for (const freq of freqStrings) {
                if (rawPeaks[freq] && rawPeaks[freq][i] !== null) {
                    recalculated.normalized_peak_trends[freq][i] = rawPeaks[freq][i] / normFactors[freq];
                }
            }

            // Apply low frequency adjustments (offset + slope)
            // Total adjustment = (Slope × file_number) + Offset
            if (recalculated.normalized_peak_trends[lowFreqStr] && recalculated.normalized_peak_trends[lowFreqStr][i] !== null) {
                const fileNumber = i + 1; // 1-based file number
                const totalAdjustment = (lowFreqSlope * fileNumber) + lowFreqOffset;
                recalculated.normalized_peak_trends[lowFreqStr][i] += totalAdjustment;
            }

            // KDM calculation using normalized (and adjusted) peaks
            // Formula: ((high_freq_normalized - low_freq_normalized) + 1) * 100
            const lowNormalized = recalculated.normalized_peak_trends[lowFreqStr] ? recalculated.normalized_peak_trends[lowFreqStr][i] : null;
            const highNormalized = recalculated.normalized_peak_trends[highFreqStr] ? recalculated.normalized_peak_trends[highFreqStr][i] : null;
            if (lowNormalized !== null && highNormalized !== null) {
                recalculated.kdm_trend[i] = ((highNormalized - lowNormalized) + 1) * 100;
            }
        }
        return recalculated;
    }

    _reconstructTrendDataFromElectrodeData(electrodeKey) {
        const electrodeData = this.state.electrodeData[electrodeKey];
        if (!electrodeData) {
            swvDebug(`No data found for electrode: ${electrodeKey}`);
            return null;
        }

        const rawPeaks = {};
        const rawPotentials = {};  // NEW: Reconstruct peak potentials
        let hasData = false;
        let maxFileNum = 0;

        // First pass: determine actual max file number from stored data
        for (const freq of this.state.currentFrequencies) {
            const freqStr = freq.toString();
            const freqData = electrodeData[freqStr];
            if (freqData) {
                for (const fileNum in freqData) {
                    const fileNumInt = parseInt(fileNum);
                    if (fileNumInt > maxFileNum) {
                        maxFileNum = fileNumInt;
                    }
                }
            }
        }

        if (maxFileNum === 0) {
            swvDebug(`No file data found for electrode ${electrodeKey}`);
            return null;
        }

        swvDebug(`[RECONSTRUCT] Actual max file: ${maxFileNum} (state.currentNumFiles: ${this.state.currentNumFiles})`);

        // Second pass: reconstruct peak data AND peak potential data for each frequency
        for (const freq of this.state.currentFrequencies) {
            const freqStr = freq.toString();
            const freqData = electrodeData[freqStr];

            if (!freqData) {
                swvDebug(`No data for frequency ${freqStr} in electrode ${electrodeKey}`);
                continue;
            }

            rawPeaks[freqStr] = Array(maxFileNum).fill(null);
            rawPotentials[freqStr] = Array(maxFileNum).fill(null);  // NEW: Initialize peak potential array

            // Fill in available data
            for (const fileNum in freqData) {
                const fileIndex = parseInt(fileNum) - 1;
                if (fileIndex >= 0 && fileIndex < maxFileNum) {
                    const analysisResult = freqData[fileNum];
                    if (analysisResult && analysisResult.peak_value !== null) {
                        rawPeaks[freqStr][fileIndex] = analysisResult.peak_value;
                        hasData = true;
                    }
                    // NEW: Reconstruct peak potential
                    if (analysisResult && analysisResult.peak_potential !== null && analysisResult.peak_potential !== undefined) {
                        rawPotentials[freqStr][fileIndex] = analysisResult.peak_potential;
                    }
                }
            }
        }

        if (!hasData) {
            swvDebug(`No valid peak data found for electrode ${electrodeKey}`);
            return null;
        }

        // Log summary instead of full object
        const summary = {};
        for (const freq in rawPeaks) {
            const validPeakCount = rawPeaks[freq].filter(v => v != null).length;
            const validPotentialCount = rawPotentials[freq].filter(v => v != null).length;
            summary[freq] = `peaks: ${validPeakCount}/${rawPeaks[freq].length}, potentials: ${validPotentialCount}/${rawPotentials[freq].length}`;
        }
        swvDebug(`Successfully reconstructed data for electrode ${electrodeKey}:`, summary);

        // NEW: Return both peak current and peak potential data
        return {
            peak_current_trends: rawPeaks,
            peak_potential_trends: rawPotentials
        };
    }

    _handleBackToSettings() {
        swvDebug('Returning to settings - stopping analysis and clearing all data');

        // Stop file monitoring and analysis session
        // Always emit stop_analysis_session so the server clears its processing queue,
        // regardless of whether analysis is considered "running" on the frontend.
        this.socketManager.emit('stop_analysis_session', { reason: 'user_back_to_settings' });
        if (this.state.isAnalysisRunning) {
            swvDebug('Stopping active analysis session...');
            this.socketManager.emit('stop_folder_monitoring', {});
        }

        // Hide visualization controls
        this.dom.visualization.adjustmentControls.classList.add('hidden');
        this.dom.visualization.exportDataBtn.classList.add('hidden');

        // Reset button state
        this.state.isAnalysisRunning = false;
        this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
        this.dom.startAnalysisBtn.disabled = false;

        // Clear all analysis data
        this.state.rawTrendData = null;
        this.state.lastCalculatedData = null;
        this.state.electrodeData = {};
        this.state.frequencyMapData = {};
        this.state.analyzedFrequencies = {};

        // Clear hold mode data
        this.state.heldData = null;
        this.state.heldSessionName = null;
        this.state.currentSessionName = null;

        // Clear replication grouping data
        this.state.groupedData = null;
        this.state.currentReplication = 1;
        if (this.dom.visualization.replicationInput) {
            this.dom.visualization.replicationInput.value = '1';
        }

        // Hide hold mode UI elements
        if (this.dom.visualization.holdModeStatus) {
            this.dom.visualization.holdModeStatus.textContent = '';
            this.dom.visualization.holdModeStatus.classList.add('hidden');
        }

        // Reset analysis mode to default (continuous)
        this.state.analysisMode = 'continuous';

        // Update radio buttons to reflect continuous mode
        const continuousRadio = document.querySelector('input[name="analysisMode"][value="continuous"]');
        if (continuousRadio) {
            continuousRadio.checked = true;
        }

        // Update UI for continuous mode
        this._updateUIForMode('continuous');

        // Navigate back to settings screen
        this.uiManager.showScreen('swvAnalysisScreen');

        // Reset post-correction panel
        const c = this.dom.visualization.correction;
        if (c) {
            c.fileNumInput.value = '1';
            c.baselineV1.value = '';
            c.baselineV2.value = '';
            c.peakV.value = '';
            c.statusSpan.textContent = '';
            c.currentValueSpan.textContent = 'N/A';
            c.newValueSpan.textContent = 'N/A';
            c.voltammogramDiv.classList.add('hidden');
            c.voltammogramPlaceholder.classList.remove('hidden');
            if (window.Plotly) Plotly.purge(c.voltammogramDiv);
        }

        // Clear FM correction state and reset FM correction panel
        this.state.frequencyMapCorrectionOverrides = {};
        this.state.frequencyMapCorrectionLoadedData = null;
        const fmc = this.dom.visualization.fmCorrection;
        if (fmc) {
            fmc.voltammogramDiv.classList.add('hidden');
            fmc.voltammogramPlaceholder.classList.remove('hidden');
            fmc.baselineV1.value = '';
            fmc.baselineV2.value = '';
            fmc.peakV.value = '';
            fmc.statusSpan.textContent = '';
            fmc.currentValueSpan.textContent = '—';
            fmc.newValueSpan.textContent = '—';
            fmc.newChargeSpan.textContent = '—';
            fmc.sessionSelectContainer.classList.add('hidden');
            if (window.Plotly) Plotly.purge(fmc.voltammogramDiv);
        }

        swvDebug('Analysis stopped, state cleared, returned to default continuous mode');
    }

    _handlePostProcessUpdate() {
        const recalculatedData = this._recalculateTrends();
        if (recalculatedData) {
            this.state.lastCalculatedData = recalculatedData;
            this._renderTrendPlots(recalculatedData);
        }
    }

    _handleStartAnalysis() {
        // Require folder monitor to be active before entering visualization
        if (!window.swvFolderMonitor?.isMonitoring) {
            alert('Please start folder monitoring before starting analysis.');
            return;
        }

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
            if (frequencies.length < 1) {
                alert("Please enter at least one valid frequency.");
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
        
        // Preserve analysisMode and hold mode data when updating state
        const currentAnalysisMode = this.state.analysisMode;
        const heldData = this.state.heldData;
        const heldFrequencies = this.state.heldFrequencies;
        const heldSessionName = this.state.heldSessionName;
        const currentSessionName = this.state.currentSessionName;
        // Preserve session1 FM correction overrides when entering hold mode session 2
        const savedFmOverrides = heldData
            ? { session1: this.state.frequencyMapCorrectionOverrides?.session1 || {} }
            : {};

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
            analyzedFrequencies: {},  // Reset analyzed frequencies {electrode: [frequencies]}
            heldData: heldData,  // Preserve held session data
            heldFrequencies: heldFrequencies,  // Preserve held session frequency list
            heldSessionName: heldSessionName,  // Preserve held session name
            currentSessionName: currentSessionName,  // Preserve current session name
            correctionOverrides: {},
            correctionLoadedData: null,
            frequencyMapCorrectionOverrides: savedFmOverrides,
            frequencyMapCorrectionLoadedData: null
        };
        

        // Log frequency information for hold mode and analysis mode debugging
        swvDebug(`[${this.state.analysisMode.toUpperCase()}] Starting analysis with frequencies:`, this.state.currentFrequencies);
        if (this.state.heldData) {
            swvDebug('[HOLD MODE] Comparing with held session:');
            swvDebug('  Held session:', this.state.heldSessionName, 'Frequencies:', this.state.heldFrequencies);
            swvDebug('  Current session:', this.state.currentSessionName, 'Frequencies:', this.state.currentFrequencies);
        }

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
            low_xstart: this.dom.params.lowXstartInput.value === '' ? null : parseFloat(this.dom.params.lowXstartInput.value),
            low_xend: this.dom.params.lowXendInput.value === '' ? null : parseFloat(this.dom.params.lowXendInput.value),
            high_xstart: this.dom.params.highXstartInput.value === '' ? null : parseFloat(this.dom.params.highXstartInput.value),
            high_xend: this.dom.params.highXendInput.value === '' ? null : parseFloat(this.dom.params.highXendInput.value),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value), current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value), delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value, SelectedOptions: this.dom.settings.selectedOptionsInput.value,
            voltage_units: 'V',
            current_units: 'A',
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
            backToSWVBtn.onclick = () => this._handleBackToSettings();
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

            // Start frequency map session (local mode - no agent needed)
            this.socketManager.emit('start_frequency_map_session', {
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
            clearChildren(this.dom.visualization.warningsList);
            // Initialise post-correction panel
            this._initCorrectionPanel();

            // Start analysis session (local mode - no agent needed)
            this.socketManager.emit('start_analysis_session', {
                filters,
                analysisParams
            });
        }
    }

    _setupFrequencyMapVisualization() {
        console.log('Setting up Frequency Map visualization...');

        // Wire up FM correction panel (header click + button handlers)
        this._setupFrequencyMapCorrectionUI();

        // Clean up any CV remnants before setting up frequency map visualization
        this._cleanupCVRemnants();

        const isHoldMode = !!this.state.heldData;
        this._refreshFrequencyMapPlotRefs();

        const activeVoltammogramPlot = isHoldMode
            ? this.dom.visualization.frequencyMapVoltammogramPlot
            : this.dom.visualization.nonHoldVoltammogramPlot;
        const activeChargePlot = isHoldMode
            ? this.dom.visualization.frequencyMapChargePlot
            : this.dom.visualization.nonHoldChargePlot;

        if (!activeVoltammogramPlot || !activeChargePlot) {
            console.error('Frequency map plot containers are missing for the current mode.', {
                isHoldMode,
                hasActiveVoltammogramPlot: !!activeVoltammogramPlot,
                hasActiveChargePlot: !!activeChargePlot
            });
            return;
        }

        // Hide continuous monitor containers
        if (this.dom.visualization.continuousMonitorContainer) {
            console.log('Hiding continuousMonitorContainer');
            this.dom.visualization.continuousMonitorContainer.classList.add('hidden');
        } else {
            console.warn('continuousMonitorContainer not found!');
        }

        // Hide continuous-mode post correction panel
        const contCorrPanel = document.getElementById('postCorrectionPanel');
        if (contCorrPanel) contCorrPanel.classList.add('hidden');

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

        if (isHoldMode) {
            // Show hold mode layout, hide non-hold mode layout
            if (this.dom.visualization.holdModeVoltammogramContainer) {
                this.dom.visualization.holdModeVoltammogramContainer.classList.remove('hidden');
            }
            if (this.dom.visualization.nonHoldModeContainer) {
                this.dom.visualization.nonHoldModeContainer.classList.add('hidden');
            }

            // Update session titles in voltammogram headers
            if (this.dom.visualization.heldSessionVoltammogramTitle) {
                this.dom.visualization.heldSessionVoltammogramTitle.textContent = this.state.heldSessionName;
            }
            if (this.dom.visualization.currentSessionVoltammogramTitle) {
                this.dom.visualization.currentSessionVoltammogramTitle.textContent = this.state.currentSessionName;
            }

            // Update hold mode status
            if (this.dom.visualization.holdModeStatus) {
                this.dom.visualization.holdModeStatus.textContent = `Held: ${this.state.heldSessionName} | Ready for: ${this.state.currentSessionName}`;
                this.dom.visualization.holdModeStatus.classList.remove('hidden');
            }

            // Immediately render held session voltammogram (left side, doesn't change)
            this._renderHeldSessionVoltammogram();
        } else {
            // Show non-hold mode layout, hide hold mode layout
            if (this.dom.visualization.holdModeVoltammogramContainer) {
                this.dom.visualization.holdModeVoltammogramContainer.classList.add('hidden');
            }
            if (this.dom.visualization.nonHoldModeContainer) {
                this.dom.visualization.nonHoldModeContainer.classList.remove('hidden');
            }

            // Clear hold mode status
            if (this.dom.visualization.holdModeStatus) {
                this.dom.visualization.holdModeStatus.textContent = '';
                this.dom.visualization.holdModeStatus.classList.add('hidden');
            }
        }

        console.log('Frequency Map visualization setup complete');
    }

    _refreshFrequencyMapPlotRefs() {
        this.dom.visualization.frequencyMapVoltammogramPlot = document.getElementById('frequencyMapVoltammogramPlot');
        this.dom.visualization.frequencyMapChargePlot = document.getElementById('frequencyMapChargePlot');
        this.dom.visualization.nonHoldVoltammogramPlot = document.getElementById('nonHoldVoltammogramPlot');
        this.dom.visualization.nonHoldChargePlot = document.getElementById('nonHoldChargePlot');
        this.dom.visualization.currentFrequencyLabel = document.getElementById('currentFrequencyLabel');
        this.dom.visualization.nonHoldFrequencyLabel = document.getElementById('nonHoldFrequencyLabel');
        this.dom.visualization.analyzedFrequenciesCount = document.getElementById('analyzedFrequenciesCount');
        this.dom.visualization.latestFrequency = document.getElementById('latestFrequency');
        this.dom.visualization.latestCharge = document.getElementById('latestCharge');
    }

    _renderHeldSessionVoltammogram() {
        // Render held session voltammogram overlay (left side in hold mode)
        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const heldElectrodeData = this.state.heldData[electrodeKey] || {};

        console.log('Rendering held session voltammogram...');

        // Generate color palette
        const colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'];

        // Render held session voltammogram overlay (without baseline)
        this._renderVoltammogramOverlay(
            this.dom.visualization.heldSessionVoltammogramPlot,
            heldElectrodeData,
            colors,
            '', // No title needed, it's in the header
            false // Don't show baseline for held session
        );

        // Trigger resize to fix any layout issues
        setTimeout(() => {
            if (this.dom.visualization.heldSessionVoltammogramPlot) {
                Plotly.Plots.resize(this.dom.visualization.heldSessionVoltammogramPlot);
            }
        }, 100);

        console.log('Held session voltammogram rendered');
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
                    'V',   // Voltage units
                    'A'   // Current units
                );
                fileNumEl.textContent = fileNum;
                peakHeightEl.textContent = individual_analysis.peak_value != null ? individual_analysis.peak_value.toFixed(4) : "N/A";
            }
        }
    }

    _updateIndividualPlotsForElectrode(electrode) {
        // Update individual plots when switching electrodes
        const electrodeKey = electrode !== null ? electrode.toString() : 'averaged';
        const electrodeData = this.state.electrodeData[electrodeKey];

        if (!electrodeData) return;

        // Update all frequency plots
        this.state.currentFrequencies.forEach(freq => {
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
                    'V',   // Voltage units
                    'A'   // Current units
                );
                fileNumEl.textContent = latestFileNum;
                peakHeightEl.textContent = latestData.peak_value != null ? latestData.peak_value.toFixed(4) : "N/A";
            }
        });
    }
    
    _renderTrendPlots(trendData) {
        console.log('[DEBUG] _renderTrendPlots called with trendData keys:', Object.keys(trendData));
        console.log('[DEBUG] peak_potential_trends present?', 'peak_potential_trends' in trendData);
        if (trendData.peak_potential_trends) {
            const potentialKeys = Object.keys(trendData.peak_potential_trends);
            console.log('[DEBUG] peak_potential_trends frequencies:', potentialKeys);
            potentialKeys.forEach(freq => {
                const validCount = trendData.peak_potential_trends[freq].filter(v => v !== null && v !== undefined).length;
                console.log(`[DEBUG] Freq ${freq}: ${validCount} valid potential values`);
            });
        }

        const injectionPoint = parseInt(this.dom.visualization.postProcessInjectionPointInput.value) || null;
        const freqStrs = this.state.currentFrequencies.map(String);
        const xAxisTitle = (this.state.currentXAxisOptions === "Experiment Time") ? 'Experiment Time (min)' : 'File Number';

        // Determine Y-axis title based on analysis mode (Peak or AUC)
        const selectedOptions = this.dom.settings.selectedOptionsInput.value;
        const isAUCMode = selectedOptions === "Area Under the Curve";
        const firstPlotYTitle = isAUCMode ? 'AUC (a.u.)' : 'Peak Current (A)';

        // Get voltage units for peak potential plot
        const voltageUnits = 'V';

        PlotlyPlotter.renderFullTrendPlot('peakCurrentTrendPlot', trendData, freqStrs, xAxisTitle, firstPlotYTitle, this.state.currentNumFiles, '', 'peak', this.state.currentXAxisOptions, null, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('normalizedPeakTrendPlot', trendData, freqStrs, xAxisTitle, 'Normalized Current', this.state.currentNumFiles, '', 'normalized', this.state.currentXAxisOptions, null, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('kdmTrendPlot', trendData, freqStrs, xAxisTitle, 'KDM (%)', this.state.currentNumFiles, '', 'kdm', this.state.currentXAxisOptions, null, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);

        // NEW: Render peak potential trend plot (for drift detection)
        console.log('[DEBUG] Calling renderFullTrendPlot for peakPotentialTrendPlot');
        PlotlyPlotter.renderFullTrendPlot('peakPotentialTrendPlot', trendData, freqStrs, xAxisTitle, `Peak Potential (${voltageUnits})`, this.state.currentNumFiles, '', 'peak_potential', this.state.currentXAxisOptions, null, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
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

        this.socketManager.on('analysis_session_started', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = data.message || 'Analysis session started. Monitoring for files...';
                this.state.isAnalysisRunning = true;
                this.dom.startAnalysisBtn.disabled = true;
                return;
            }

            this.dom.folderStatus.textContent = data.message || 'Error starting analysis session';
            this.state.isAnalysisRunning = false;
            this.dom.startAnalysisBtn.disabled = false;
            this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';

            if (data.message) {
                alert('Error starting analysis session: ' + data.message);
            }
        });

        this.socketManager.on('frequency_map_session_started', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = data.message || 'Frequency map analysis started. Monitoring for files...';
                this.state.isAnalysisRunning = true;
                this.dom.startAnalysisBtn.disabled = true;
                this.dom.startAnalysisBtn.textContent = 'Analyzing...';
                return;
            }

            this.dom.folderStatus.textContent = data.message || 'Error starting frequency map analysis';
            this.state.isAnalysisRunning = false;
            this.dom.startAnalysisBtn.disabled = false;
            this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';

            if (data.message) {
                alert('Error starting frequency map analysis: ' + data.message);
            }
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

        // Ensure trend plots container is visible and confirm the expected structure exists
        const trendPlotsContainer = document.getElementById('trendPlotsContainer');
        if (trendPlotsContainer) {
            trendPlotsContainer.style.display = '';

            this.dom.visualization.trendPlotsContainer = trendPlotsContainer;
            this.dom.visualization.kdmHighFreqSelect = document.getElementById('kdmHighFreqSelect');
            this.dom.visualization.kdmLowFreqSelect = document.getElementById('kdmLowFreqSelect');

            const peakPlot = document.getElementById('peakCurrentTrendPlot');
            const normalizedPlot = document.getElementById('normalizedPeakTrendPlot');
            const kdmPlot = document.getElementById('kdmTrendPlot');
            const peakPotentialPlot = document.getElementById('peakPotentialTrendPlot');

            if (!peakPlot || !normalizedPlot || !kdmPlot || !peakPotentialPlot) {
                console.error('SWV trend plot containers are missing from the template.', {
                    hasPeakPlot: !!peakPlot,
                    hasNormalizedPlot: !!normalizedPlot,
                    hasKdmPlot: !!kdmPlot,
                    hasPeakPotentialPlot: !!peakPotentialPlot
                });
                return;
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

        // Restore continuous-mode post correction panel
        const contCorrPanel = document.getElementById('postCorrectionPanel');
        if (contCorrPanel) contCorrPanel.classList.remove('hidden');

        // Hide frequency map container
        if (this.dom.visualization.frequencyMapContainer) {
            this.dom.visualization.frequencyMapContainer.classList.add('hidden');
        }

        const { individualPlotsContainer } = this.dom.visualization;
        const frequencies = this.state.currentFrequencies;

        if (individualPlotsContainer) {
            const count = frequencies.length;

            // 2-column grid layout regardless of count (2 per row)
            let containerClass, plotHeightClass, titleClass, infoClass;
            containerClass = 'grid grid-cols-2 gap-4';
            if (count <= 2) {
                plotHeightClass = 'plotly-plot-container';
                titleClass = 'text-lg font-semibold text-gray-700 mb-2';
                infoClass = 'text-sm mt-2';
            } else if (count <= 6) {
                plotHeightClass = 'plotly-plot-container';
                titleClass = 'text-sm font-semibold text-gray-700 mb-1';
                infoClass = 'text-xs mt-1';
            } else {
                plotHeightClass = 'plotly-plot-container-sm';
                titleClass = 'text-xs font-semibold text-gray-700 mb-1';
                infoClass = 'text-xs mt-1';
            }
            individualPlotsContainer.className = containerClass;

            const sortedFreqs = [...frequencies].sort((a, b) => b - a); // Descending (high first)
            clearChildren(individualPlotsContainer);
            sortedFreqs.forEach((freq) => {
                individualPlotsContainer.appendChild(
                    this._createIndividualPlotCard(freq, titleClass, plotHeightClass, infoClass)
                );
            });
        }

        // Populate KDM frequency selectors
        this._populateKdmSelectors();
    }

    // ─── Post Correction ──────────────────────────────────────────────────────

    _initCorrectionPanel() {
        const c = this.dom.visualization.correction;
        if (!c.header) return;

        // Collapsible toggle
        c.header.addEventListener('click', () => {
            const collapsed = c.body.style.display === 'none';
            c.body.style.display = collapsed ? '' : 'none';
            c.toggle.textContent = collapsed ? '▼' : '▶';
        });

        // Populate frequency selector
        const sortedFreqs = [...this.state.currentFrequencies].sort((a, b) => a - b);
        setSelectOptions(c.freqSelect, sortedFreqs.map((freq) => ({
            value: String(freq),
            label: `${freq} Hz`
        })));

        // Populate electrode selector — individual electrodes only (1-based labels, 0-based values)
        // Correction is not allowed on "Averaged" directly; averaged is recalculated server-side.
        if (this.state.selectedElectrodes.length === 0) {
            setSelectOptions(c.electrodeSelect, [
                { value: 'averaged', label: 'Averaged (only electrode)' }
            ]);
        } else {
            setSelectOptions(c.electrodeSelect, this.state.selectedElectrodes.map((idx) => ({
                value: String(idx),
                label: `Electrode ${idx + 1}`
            })));
        }
        c.loadBtn.onclick = () => this._loadVoltammogramForCorrection();

        // Preview on input change
        [c.baselineV1, c.baselineV2, c.peakV].forEach(inp => {
            inp.addEventListener('input', () => this._updateCorrectionPreview());
        });

        // Apply button
        c.applyBtn.onclick = () => this._applyCorrection();

        // Reset button
        c.resetBtn.onclick = () => this._resetCorrection();
    }

    _createIndividualPlotCard(freq, titleClass, plotHeightClass, infoClass) {
        const card = document.createElement('div');
        card.className = 'border rounded-lg p-3 bg-gray-50';

        const title = document.createElement('h4');
        title.className = titleClass;
        title.textContent = `${freq} Hz`;

        const plotArea = document.createElement('div');
        plotArea.id = `plotArea-${freq}`;
        plotArea.className = `w-full ${plotHeightClass} bg-gray-100 flex justify-center items-center text-gray-400`;
        plotArea.textContent = 'Waiting for data...';

        const info = document.createElement('p');
        info.className = infoClass;
        info.append('File: ');

        const fileNum = document.createElement('span');
        fileNum.id = `fileNumDisplay-${freq}`;
        fileNum.textContent = 'N/A';
        info.appendChild(fileNum);

        info.append(' | Peak: ');

        const peakHeight = document.createElement('span');
        peakHeight.id = `peakHeightDisplay-${freq}`;
        peakHeight.textContent = 'N/A';
        info.appendChild(peakHeight);

        card.appendChild(title);
        card.appendChild(plotArea);
        card.appendChild(info);

        return card;
    }

    async _loadVoltammogramForCorrection() {
        const c = this.dom.visualization.correction;
        const freq = parseInt(c.freqSelect.value);
        const fileNum = parseInt(c.fileNumInput.value);
        const electrode = c.electrodeSelect.value;

        if (isNaN(freq) || isNaN(fileNum) || fileNum < 1) {
            c.statusSpan.textContent = 'Invalid frequency or file number.';
            return;
        }

        c.loadBtn.disabled = true;
        c.loadBtn.textContent = 'Loading...';
        c.statusSpan.textContent = '';

        try {
            // Try to load from cached frontend state first (no disk re-read needed)
            const electrodeKey = electrode === 'averaged' ? 'averaged' : electrode.toString();
            const freqStr = freq.toString();
            const fileNumStr = fileNum.toString();
            const cached = this.state.electrodeData?.[electrodeKey]?.[freqStr]?.[fileNumStr];

            let data;
            if (cached && cached.potentials && cached.potentials.length > 0) {
                // Use cached voltammogram data from memory
                console.log('[VoltammogramLoad] Using cached data from state.electrodeData');
                // Get stored peak from memory_store trend data via server
                const storedResp = await fetch(`/api/get_voltammogram?frequency=${freq}&file_number=${fileNum}&electrode=${electrode}&peaks_only=1`);
                const storedJson = storedResp.ok ? await storedResp.json() : {};
                data = {
                    status: 'success',
                    potentials: cached.potentials,
                    raw_currents: cached.raw_currents || [],
                    smoothed_currents: cached.smoothed_currents || [],
                    regression_line: cached.regression_line || [],
                    adjusted_potentials: cached.adjusted_potentials || cached.potentials,
                    peak_info: cached.peak_info || {},
                    peak_value: cached.peak_value,
                    current_stored_peak: storedJson.current_stored_peak ?? cached.peak_value,
                    current_stored_potential: storedJson.current_stored_potential ?? cached.peak_info?.peak_potential,
                };
            } else {
                // Fall back to server re-read (e.g. for older files not in cache)
                console.log('[VoltammogramLoad] Cache miss — fetching from server');
                const resp = await fetch(`/api/get_voltammogram?frequency=${freq}&file_number=${fileNum}&electrode=${electrode}`);
                data = await resp.json();
                console.log('[VoltammogramLoad] server response:', {
                    status: data.status,
                    potentials_len: (data.potentials||[]).length,
                    current_stored_peak: data.current_stored_peak,
                    message: data.message,
                    debug: data.debug,
                });
            }

            if (data.status !== 'success') {
                c.statusSpan.textContent = `Error: ${data.message}`;
                return;
            }
            if (!data.potentials || data.potentials.length === 0) {
                c.statusSpan.textContent = 'No voltammogram data available for this file.';
                return;
            }

            this.state.correctionLoadedData = { freq, fileNum, electrode, ...data };

            // Show plot div, hide placeholder
            c.voltammogramPlaceholder.classList.add('hidden');
            c.voltammogramDiv.classList.remove('hidden');
            this._renderCorrectionPlot(data);

            // Pre-fill correction inputs from detected values
            const pi = data.peak_info || {};
            if (pi.baseline_left && pi.baseline_right) {
                c.baselineV1.value = pi.baseline_left.potential != null ? pi.baseline_left.potential.toFixed(4) : '';
                c.baselineV2.value = pi.baseline_right.potential != null ? pi.baseline_right.potential.toFixed(4) : '';
            } else {
                const pots = data.potentials || [];
                if (pots.length >= 2) {
                    c.baselineV1.value = Math.min(...pots).toFixed(4);
                    c.baselineV2.value = Math.max(...pots).toFixed(4);
                }
            }
            c.peakV.value = pi.peak_potential != null ? pi.peak_potential.toFixed(4) : '';

            // Show current stored value
            const storedVal = data.current_stored_peak;
            c.currentValueSpan.textContent = storedVal != null ? storedVal.toExponential(4) : (data.peak_value != null ? data.peak_value.toExponential(4) : '—');
            c.newValueSpan.textContent = '—';
            c.applyBtn.disabled = true;
            const electrodeDisplay = electrode === 'averaged' ? 'Averaged' : `Electrode ${parseInt(electrode) + 1}`;
            c.statusSpan.textContent = `Loaded: ${freq}Hz, file #${fileNum}, ${electrodeDisplay}`;

            this._updateCorrectionPreview();

        } catch (err) {
            c.statusSpan.textContent = `Request failed: ${err.message}`;
            console.error('[VoltammogramLoad] Error:', err);
        } finally {
            c.loadBtn.disabled = false;
            c.loadBtn.textContent = 'Load';
        }
    }

    _updateCorrectionPreview() {
        const c = this.dom.visualization.correction;
        const loaded = this.state.correctionLoadedData;
        if (!loaded) return;

        const v1 = parseFloat(c.baselineV1.value);
        const v2 = parseFloat(c.baselineV2.value);
        const vp = parseFloat(c.peakV.value);

        if (isNaN(v1) || isNaN(v2) || isNaN(vp) || v1 === v2) {
            c.newValueSpan.textContent = '—';
            c.applyBtn.disabled = true;
            return;
        }

        const potentials = loaded.potentials || [];
        const currents = loaded.smoothed_currents || [];
        if (potentials.length === 0) return;

        // Find index of closest potential
        const closest = (val) => potentials.reduce((best, curr, i) =>
            Math.abs(curr - val) < Math.abs(potentials[best] - val) ? i : best, 0);

        const idx1 = closest(v1);
        const idx2 = closest(v2);
        const idxP = closest(vp);

        const i1 = currents[idx1], i2 = currents[idx2], ip = currents[idxP];
        const actualV1 = potentials[idx1], actualV2 = potentials[idx2], actualVp = potentials[idxP];

        const slope = (i2 - i1) / (actualV2 - actualV1);
        const baselineAtPeak = i1 + slope * (actualVp - actualV1);
        const newPeakHeight = Math.abs(ip - baselineAtPeak);

        c.newValueSpan.textContent = newPeakHeight.toExponential(4);
        c.applyBtn.disabled = false;

        // Redraw the plot with new baseline overlay
        this._drawCorrectionOverlay(loaded, actualV1, i1, actualV2, i2, actualVp, ip, baselineAtPeak);
    }

    _renderCorrectionPlot(data) {
        const divEl = document.getElementById('corrVoltammogramDiv');
        if (!divEl) return;

        const pots = data.potentials || [];
        const raw  = data.raw_currents || [];
        const smth = data.smoothed_currents || [];
        const base = data.regression_line || [];
        const adjP = data.adjusted_potentials || pots;
        const pi   = data.peak_info || {};

        console.log('[CorrectionPlot] potentials:', pots.length,
                    'raw_currents:', raw.length,
                    'smoothed:', smth.length,
                    'baseline:', base.length);

        const traces = [];

        if (pots.length > 0 && raw.length > 0) {
            traces.push({ x: pots, y: raw,  mode: 'lines', name: 'Raw',
                          line: { color: '#3B82F6', width: 1 } });
        }
        if (pots.length > 0 && smth.length > 0) {
            traces.push({ x: pots, y: smth, mode: 'lines', name: 'Smoothed',
                          line: { color: '#EF4444', width: 2 } });
        }
        if (adjP.length > 0 && base.length > 0) {
            traces.push({ x: adjP, y: base, mode: 'lines', name: 'Baseline',
                          line: { color: '#22C55E', width: 1.5, dash: 'dash' } });
        }
        if (pi.peak_potential != null && pi.peak_current != null) {
            traces.push({ x: [pi.peak_potential], y: [pi.peak_current],
                          mode: 'markers', name: 'Peak',
                          marker: { color: '#DC2626', size: 10, symbol: 'circle',
                                    line: { color: '#7F1D1D', width: 2 } } });
        }
        if (pi.baseline_left && pi.baseline_right) {
            traces.push({ x: [pi.baseline_left.potential, pi.baseline_right.potential],
                          y: [pi.baseline_left.current,   pi.baseline_right.current],
                          mode: 'markers', name: 'Baseline pts',
                          marker: { color: '#16A34A', size: 8, symbol: 'circle' } });
        }

        const layout = {
            height: 380,
            autosize: true,
            margin: { t: 40, b: 55, l: 70, r: 20 },
            xaxis: { title: 'Potential (V)', autorange: true,
                     tickangle: -30, tickfont: { size: 10 } },
            yaxis: { title: 'Current (A)', autorange: true,
                     exponentformat: 'SI', tickfont: { size: 10 } },
            legend: { orientation: 'h', yanchor: 'bottom', y: 1.02,
                      xanchor: 'center', x: 0.5, font: { size: 10 } },
        };

        Plotly.newPlot(divEl, traces, layout, { responsive: true });
    }

    _drawCorrectionOverlay(loaded, v1, i1, v2, i2, vp, ip, baselineAtPeak) {
        this._renderCorrectionPlot(loaded);

        const plotEl = document.getElementById('corrVoltammogramDiv');
        const newBaselineTrace = {
            x: [v1, v2],
            y: [i1, i2],
            mode: 'lines+markers',
            line: { color: 'orange', width: 2, dash: 'dash' },
            marker: { color: 'orange', size: 8 },
            name: 'New Baseline'
        };
        const newPeakTrace = {
            x: [vp],
            y: [ip],
            mode: 'markers',
            marker: { color: 'red', size: 10, symbol: 'diamond' },
            name: 'New Peak'
        };
        const peakLineTrace = {
            x: [vp, vp],
            y: [baselineAtPeak, ip],
            mode: 'lines',
            line: { color: 'red', width: 2 },
            name: 'New Peak Height'
        };
        try {
            Plotly.addTraces(plotEl, [newBaselineTrace, newPeakTrace, peakLineTrace]);
        } catch (_) {}
    }

    async _applyCorrection() {
        const c = this.dom.visualization.correction;
        const loaded = this.state.correctionLoadedData;
        if (!loaded) return;

        const v1 = parseFloat(c.baselineV1.value);
        const v2 = parseFloat(c.baselineV2.value);
        const vp = parseFloat(c.peakV.value);
        if (isNaN(v1) || isNaN(v2) || isNaN(vp) || v1 === v2) return;

        const potentials = loaded.potentials || [];
        const currents = loaded.smoothed_currents || [];
        const closest = (val) => potentials.reduce((best, curr, i) =>
            Math.abs(curr - val) < Math.abs(potentials[best] - val) ? i : best, 0);

        const idx1 = closest(v1), idx2 = closest(v2), idxP = closest(vp);
        const actualV1 = potentials[idx1], actualV2 = potentials[idx2], actualVp = potentials[idxP];
        const i1 = currents[idx1], i2 = currents[idx2], ip = currents[idxP];
        const slope = (i2 - i1) / (actualV2 - actualV1);
        const baselineAtPeak = i1 + slope * (actualVp - actualV1);
        const newPeakHeight = Math.abs(ip - baselineAtPeak);

        const { freq, fileNum, electrode } = loaded;
        const electrodeKey = electrode === 'averaged' ? 'averaged' : electrode.toString();
        const freqStr = freq.toString();
        const fileNumStr = fileNum.toString();

        // Store override on client for this electrode
        if (!this.state.correctionOverrides[electrodeKey]) this.state.correctionOverrides[electrodeKey] = {};
        if (!this.state.correctionOverrides[electrodeKey][freqStr]) this.state.correctionOverrides[electrodeKey][freqStr] = {};
        this.state.correctionOverrides[electrodeKey][freqStr][fileNumStr] = {
            peak_value: newPeakHeight,
            peak_potential: actualVp
        };

        // Push to server — server also recalculates the averaged value across all electrodes
        let serverResp = null;
        try {
            const resp = await fetch('/api/apply_correction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frequency: freq,
                    file_number: fileNum,
                    electrode: electrode,
                    new_peak_value: newPeakHeight,
                    new_peak_potential: actualVp
                })
            });
            serverResp = await resp.json();
        } catch (err) {
            console.warn('apply_correction server sync failed:', err);
        }

        // Update the averaged override so the averaged trend plot reflects the correction
        if (serverResp?.new_averaged_peak != null) {
            if (!this.state.correctionOverrides['averaged']) this.state.correctionOverrides['averaged'] = {};
            if (!this.state.correctionOverrides['averaged'][freqStr]) this.state.correctionOverrides['averaged'][freqStr] = {};
            this.state.correctionOverrides['averaged'][freqStr][fileNumStr] = {
                peak_value: serverResp.new_averaged_peak,
                peak_potential: serverResp.new_averaged_potential ?? actualVp
            };
        }

        // Refresh all trend plots
        this._handlePostProcessUpdate();

        c.currentValueSpan.textContent = newPeakHeight.toExponential(4);
        c.statusSpan.textContent = `Correction applied: ${freq}Hz, file #${fileNum} — new value ${newPeakHeight.toExponential(4)}`;
        c.applyBtn.disabled = true;
    }

    async _resetCorrection() {
        const c = this.dom.visualization.correction;
        const loaded = this.state.correctionLoadedData;
        if (!loaded) return;

        const { freq, fileNum, electrode } = loaded;
        const electrodeKey = electrode === 'averaged' ? 'averaged' : electrode.toString();
        const freqStr = freq.toString();
        const fileNumStr = fileNum.toString();

        // Remove client-side override for this electrode and averaged
        if (this.state.correctionOverrides[electrodeKey]?.[freqStr]) {
            delete this.state.correctionOverrides[electrodeKey][freqStr][fileNumStr];
        }
        if (this.state.correctionOverrides['averaged']?.[freqStr]) {
            delete this.state.correctionOverrides['averaged'][freqStr][fileNumStr];
        }

        // Restore server-side value by posting the original (server will recalculate averaged too)
        const original = loaded.current_stored_peak;
        const originalPotential = loaded.current_stored_potential;
        if (original != null) {
            try {
                await fetch('/api/apply_correction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        frequency: freq, file_number: fileNum, electrode,
                        new_peak_value: original, new_peak_potential: originalPotential
                    })
                });
            } catch (_) {}
        }

        // Refresh trend plots
        this._handlePostProcessUpdate();

        c.currentValueSpan.textContent = original != null ? original.toExponential(4) : '—';
        c.newValueSpan.textContent = '—';
        c.statusSpan.textContent = `Reset to original: ${freq}Hz, file #${fileNum}`;
        c.applyBtn.disabled = true;
    }

    // ─── End Post Correction ──────────────────────────────────────────────────

    // ─── Frequency Map Post Correction ───────────────────────────────────────

    _setupFrequencyMapCorrectionUI() {
        const c = this.dom.visualization.fmCorrection;
        if (!c) return;

        c.loadBtn.onclick = () => this._loadFrequencyMapVoltammogramForCorrection();

        [c.baselineV1, c.baselineV2, c.peakV].forEach(inp => {
            inp.addEventListener('input', () => this._updateFrequencyMapCorrectionPreview());
        });

        c.applyBtn.onclick = () => this._applyFrequencyMapCorrection();
        c.resetBtn.onclick = () => this._resetFrequencyMapCorrection();
    }

    _populateFmCorrectionDropdowns() {
        const c = this.dom.visualization.fmCorrection;
        if (!c) return;
        const isHoldMode = this.state.heldData !== null;

        // Gather all available frequencies from current session (and session1 if hold mode)
        const freqSet = new Set();
        const addFreqsFrom = (dataObj) => {
            Object.values(dataObj || {}).forEach(edData =>
                Object.keys(edData).forEach(f => freqSet.add(parseFloat(f)))
            );
        };
        addFreqsFrom(this.state.frequencyMapData);
        if (isHoldMode) addFreqsFrom(this.state.heldData);

        const sortedFreqs = Array.from(freqSet).sort((a, b) => a - b);
        if (sortedFreqs.length > 0) {
            setSelectOptions(c.freqSelect, sortedFreqs.map((freq) => ({
                value: String(freq),
                label: `${freq} Hz`
            })));
        } else {
            setSelectOptions(c.freqSelect, [
                { value: '', label: 'No data yet' }
            ]);
        }

        // Gather available electrodes
        const elecSet = new Set();
        const addElecsFrom = (dataObj) => {
            Object.keys(dataObj || {}).forEach(k => {
                if (k !== 'averaged') elecSet.add(parseInt(k));
            });
        };
        addElecsFrom(this.state.frequencyMapData);
        if (isHoldMode) addElecsFrom(this.state.heldData);

        if (elecSet.size === 0) {
            setSelectOptions(c.electrodeSelect, [
                { value: 'averaged', label: 'Averaged' }
            ]);
        } else {
            setSelectOptions(c.electrodeSelect, Array.from(elecSet).sort((a, b) => a - b).map((idx) => ({
                value: String(idx),
                label: `Electrode ${idx + 1}`
            })));
        }
        if (isHoldMode) {
            c.sessionSelectContainer.classList.remove('hidden');
        } else {
            c.sessionSelectContainer.classList.add('hidden');
        }
    }

    _loadFrequencyMapVoltammogramForCorrection() {
        const c = this.dom.visualization.fmCorrection;
        const freq = parseFloat(c.freqSelect.value);
        const electrodeVal = c.electrodeSelect.value;
        const isHoldMode = this.state.heldData !== null;
        const sessionKey = isHoldMode ? c.sessionSelect.value : 'current';

        if (isNaN(freq)) { c.statusSpan.textContent = 'Invalid frequency.'; return; }

        const electrodeKey = electrodeVal === 'averaged' ? 'averaged' : electrodeVal.toString();
        const source = sessionKey === 'session1' ? this.state.heldData : this.state.frequencyMapData;
        const freqData = source?.[electrodeKey]?.[freq];

        if (!freqData || !freqData.smoothed_currents || freqData.smoothed_currents.length === 0) {
            c.statusSpan.textContent = 'No voltammogram data available for this selection.';
            return;
        }

        const potentials = freqData.adjusted_potentials || freqData.potentials || [];
        const effective = this._getFmEffectiveValues(sessionKey, electrodeKey, freq);
        const currentPeak = effective?.peak_value ?? freqData.peak_value;

        this.state.frequencyMapCorrectionLoadedData = {
            freq, electrode: electrodeVal, electrodeKey, sessionKey,
            potentials,
            raw_currents: freqData.raw_currents || [],
            smoothed_currents: freqData.smoothed_currents || [],
            regression_line: freqData.regression_line || [],
            peak_info: freqData.peak_info || {},
            original_peak: freqData.peak_value,
            original_charge: freqData.charge,
            current_peak: currentPeak,
        };

        c.voltammogramPlaceholder.classList.add('hidden');
        c.voltammogramDiv.classList.remove('hidden');
        this._renderFrequencyMapCorrectionPlot(this.state.frequencyMapCorrectionLoadedData);

        // Use stored baseline points if available (from peak_info via server), else fall back to data endpoints
        const pi = freqData.peak_info || {};
        const blLeft  = pi.baseline_left  || freqData.baseline_left  || null;
        const blRight = pi.baseline_right || freqData.baseline_right || null;
        if (blLeft && blRight) {
            c.baselineV1.value = blLeft.potential  != null ? blLeft.potential.toFixed(4)  : '';
            c.baselineV2.value = blRight.potential != null ? blRight.potential.toFixed(4) : '';
        } else if (potentials.length >= 2) {
            // Fallback: most positive and most negative potential in the data
            c.baselineV1.value = Math.max(...potentials).toFixed(4);
            c.baselineV2.value = Math.min(...potentials).toFixed(4);
        }
        // freq_data stores peak_potential directly (not nested under peak_info)
        const peakPot = pi.peak_potential ?? freqData.peak_potential ?? null;
        c.peakV.value = peakPot != null ? peakPot.toFixed(4) : '';

        c.currentValueSpan.textContent = currentPeak != null ? currentPeak.toExponential(4) : '—';
        c.newValueSpan.textContent = '—';
        c.newChargeSpan.textContent = '—';
        c.applyBtn.disabled = true;

        const sessLabel = sessionKey === 'session1' ? ` (${this.state.heldSessionName})` :
                          sessionKey === 'session2' ? ` (${this.state.currentSessionName})` : '';
        const elLabel = electrodeVal === 'averaged' ? 'Averaged' : `Electrode ${parseInt(electrodeVal) + 1}`;
        c.statusSpan.textContent = `Loaded: ${freq} Hz, ${elLabel}${sessLabel}`;

        this._updateFrequencyMapCorrectionPreview();
    }

    _renderFrequencyMapCorrectionPlot(data) {
        const divEl = document.getElementById('fmCorrVoltammogramDiv');
        if (!divEl) return;

        const pots = data.potentials || [];
        const raw  = data.raw_currents || [];
        const smth = data.smoothed_currents || [];
        const base = data.regression_line || [];
        const pi   = data.peak_info || {};

        const traces = [];
        if (pots.length > 0 && raw.length > 0)
            traces.push({ x: pots, y: raw,  mode: 'lines', name: 'Raw',
                          line: { color: '#3B82F6', width: 1 } });
        if (pots.length > 0 && smth.length > 0)
            traces.push({ x: pots, y: smth, mode: 'lines', name: 'Smoothed',
                          line: { color: '#EF4444', width: 2 } });
        if (pots.length > 0 && base.length > 0)
            traces.push({ x: pots, y: base, mode: 'lines', name: 'Baseline',
                          line: { color: '#22C55E', width: 1.5, dash: 'dash' } });
        if (pi.peak_potential != null && pi.peak_current != null)
            traces.push({ x: [pi.peak_potential], y: [pi.peak_current], mode: 'markers', name: 'Peak',
                          marker: { color: '#DC2626', size: 10, symbol: 'circle',
                                    line: { color: '#7F1D1D', width: 2 } } });
        if (pi.baseline_left && pi.baseline_right)
            traces.push({ x: [pi.baseline_left.potential, pi.baseline_right.potential],
                          y: [pi.baseline_left.current,   pi.baseline_right.current],
                          mode: 'markers', name: 'Baseline pts',
                          marker: { color: '#16A34A', size: 8, symbol: 'circle' } });

        const layout = {
            height: 280, autosize: true,
            margin: { t: 30, b: 50, l: 65, r: 15 },
            xaxis: { title: 'Potential (V)', autorange: 'reversed', tickangle: -30, tickfont: { size: 10 } },
            yaxis: { title: 'Current (A)', autorange: true, exponentformat: 'SI', tickfont: { size: 10 } },
            legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'center', x: 0.5, font: { size: 10 } },
        };

        Plotly.newPlot(divEl, traces, layout, { responsive: true, displayModeBar: false });
    }

    _updateFrequencyMapCorrectionPreview() {
        const c = this.dom.visualization.fmCorrection;
        const loaded = this.state.frequencyMapCorrectionLoadedData;
        if (!loaded) return;

        const v1 = parseFloat(c.baselineV1.value);
        const v2 = parseFloat(c.baselineV2.value);
        const vp = parseFloat(c.peakV.value);

        if (isNaN(v1) || isNaN(v2) || isNaN(vp) || v1 === v2) {
            c.newValueSpan.textContent = '—';
            c.newChargeSpan.textContent = '—';
            c.applyBtn.disabled = true;
            return;
        }

        const potentials = loaded.potentials || [];
        const currents   = loaded.smoothed_currents || [];
        if (potentials.length === 0) return;

        const closest = (val) => potentials.reduce((best, curr, i) =>
            Math.abs(curr - val) < Math.abs(potentials[best] - val) ? i : best, 0);

        const idx1 = closest(v1), idx2 = closest(v2), idxP = closest(vp);
        const actualV1 = potentials[idx1], actualV2 = potentials[idx2], actualVp = potentials[idxP];
        const i1 = currents[idx1], i2 = currents[idx2], ip = currents[idxP];

        const slope = (i2 - i1) / (actualV2 - actualV1);
        const baselineAtPeak = i1 + slope * (actualVp - actualV1);
        const newPeakHeight = Math.abs(ip - baselineAtPeak);
        const newCharge = newPeakHeight / loaded.freq;

        c.newValueSpan.textContent = newPeakHeight.toExponential(4);
        c.newChargeSpan.textContent = newCharge.toExponential(4);
        c.applyBtn.disabled = false;

        this._drawFmCorrectionOverlay(loaded, actualV1, i1, actualV2, i2, actualVp, ip, baselineAtPeak);
    }

    _drawFmCorrectionOverlay(loaded, v1, i1, v2, i2, vp, ip, baselineAtPeak) {
        this._renderFrequencyMapCorrectionPlot(loaded);
        const plotEl = document.getElementById('fmCorrVoltammogramDiv');
        try {
            Plotly.addTraces(plotEl, [
                { x: [v1, v2], y: [i1, i2], mode: 'lines+markers',
                  line: { color: 'orange', width: 2, dash: 'dash' },
                  marker: { color: 'orange', size: 8 }, name: 'New Baseline' },
                { x: [vp], y: [ip], mode: 'markers',
                  marker: { color: 'red', size: 10, symbol: 'diamond' }, name: 'New Peak' },
                { x: [vp, vp], y: [baselineAtPeak, ip], mode: 'lines',
                  line: { color: 'red', width: 2 }, name: 'New Peak Height' },
            ]);
        } catch (_) {}
    }

    _applyFrequencyMapCorrection() {
        const c = this.dom.visualization.fmCorrection;
        const loaded = this.state.frequencyMapCorrectionLoadedData;
        if (!loaded) return;

        const v1 = parseFloat(c.baselineV1.value);
        const v2 = parseFloat(c.baselineV2.value);
        const vp = parseFloat(c.peakV.value);
        if (isNaN(v1) || isNaN(v2) || isNaN(vp) || v1 === v2) return;

        const potentials = loaded.potentials || [];
        const currents   = loaded.smoothed_currents || [];
        const closest = (val) => potentials.reduce((best, curr, i) =>
            Math.abs(curr - val) < Math.abs(potentials[best] - val) ? i : best, 0);

        const idx1 = closest(v1), idx2 = closest(v2), idxP = closest(vp);
        const actualV1 = potentials[idx1], actualV2 = potentials[idx2], actualVp = potentials[idxP];
        const i1 = currents[idx1], i2 = currents[idx2], ip = currents[idxP];
        const slope = (i2 - i1) / (actualV2 - actualV1);
        const baselineAtPeak = i1 + slope * (actualVp - actualV1);
        const newPeakHeight = Math.abs(ip - baselineAtPeak);
        const newCharge = newPeakHeight / loaded.freq;

        const { sessionKey, electrodeKey, freq } = loaded;
        const freqStr = freq.toString();

        if (!this.state.frequencyMapCorrectionOverrides[sessionKey])
            this.state.frequencyMapCorrectionOverrides[sessionKey] = {};
        if (!this.state.frequencyMapCorrectionOverrides[sessionKey][electrodeKey])
            this.state.frequencyMapCorrectionOverrides[sessionKey][electrodeKey] = {};
        this.state.frequencyMapCorrectionOverrides[sessionKey][electrodeKey][freqStr] = {
            peak_value: newPeakHeight, charge: newCharge, peak_potential: actualVp,
        };

        // Recalculate averaged override if an individual electrode was corrected
        if (electrodeKey !== 'averaged') {
            this._recalculateFmAveragedOverride(sessionKey, freq);
        }

        this._updateFrequencyChargeChart();

        c.currentValueSpan.textContent = newPeakHeight.toExponential(4);
        c.statusSpan.textContent = `Applied: ${freq} Hz — peak ${newPeakHeight.toExponential(4)} A, charge ${newCharge.toExponential(4)} C`;
        c.applyBtn.disabled = true;
    }

    _resetFrequencyMapCorrection() {
        const c = this.dom.visualization.fmCorrection;
        const loaded = this.state.frequencyMapCorrectionLoadedData;
        if (!loaded) return;

        const { sessionKey, electrodeKey, freq } = loaded;
        const freqStr = freq.toString();

        if (this.state.frequencyMapCorrectionOverrides[sessionKey]?.[electrodeKey]) {
            delete this.state.frequencyMapCorrectionOverrides[sessionKey][electrodeKey][freqStr];
        }

        if (electrodeKey !== 'averaged') {
            this._recalculateFmAveragedOverride(sessionKey, freq);
        }

        this._updateFrequencyChargeChart();

        c.currentValueSpan.textContent = loaded.original_peak?.toExponential(4) ?? '—';
        c.newValueSpan.textContent = '—';
        c.newChargeSpan.textContent = '—';
        c.statusSpan.textContent = `Reset: ${freq} Hz — restored to original value`;
        c.applyBtn.disabled = true;
    }

    // After correcting an individual electrode, recompute the averaged override for that frequency
    _recalculateFmAveragedOverride(sessionKey, freq) {
        const source = sessionKey === 'session1' ? this.state.heldData : this.state.frequencyMapData;
        if (!source) return;
        const electrodeKeys = Object.keys(source).filter(k => k !== 'averaged');
        if (electrodeKeys.length === 0) return;

        const freqStr = freq.toString();
        const overrides = this.state.frequencyMapCorrectionOverrides[sessionKey] || {};

        const peakValues = electrodeKeys.map(ek => {
            const ov = overrides[ek]?.[freqStr];
            return ov ? ov.peak_value : (source[ek]?.[freq]?.peak_value ?? null);
        }).filter(v => v !== null);

        if (!this.state.frequencyMapCorrectionOverrides[sessionKey])
            this.state.frequencyMapCorrectionOverrides[sessionKey] = {};
        if (!this.state.frequencyMapCorrectionOverrides[sessionKey]['averaged'])
            this.state.frequencyMapCorrectionOverrides[sessionKey]['averaged'] = {};

        if (peakValues.length > 0) {
            const avgPeak = peakValues.reduce((s, v) => s + v, 0) / peakValues.length;
            this.state.frequencyMapCorrectionOverrides[sessionKey]['averaged'][freqStr] = {
                peak_value: avgPeak, charge: avgPeak / freq, peak_potential: null,
            };
        } else {
            delete this.state.frequencyMapCorrectionOverrides[sessionKey]['averaged'][freqStr];
        }
    }

    // Get effective (possibly corrected) values for a frequency in a session
    _getFmEffectiveValues(sessionKey, electrodeKey, freq) {
        const override = this.state.frequencyMapCorrectionOverrides?.[sessionKey]?.[electrodeKey]?.[freq.toString()];
        if (override) return override;
        const source = sessionKey === 'session1' ? this.state.heldData : this.state.frequencyMapData;
        const raw = source?.[electrodeKey]?.[freq];
        if (!raw) return null;
        return { peak_value: raw.peak_value, charge: raw.charge, peak_potential: raw.peak_potential };
    }

    // ─── End Frequency Map Post Correction ───────────────────────────────────

    _populateKdmSelectors() {
        const highSelect = document.getElementById('kdmHighFreqSelect');
        const lowSelect = document.getElementById('kdmLowFreqSelect');
        if (!highSelect || !lowSelect) return;

        const kdmSection = document.getElementById('kdmSection');
        const sortedAsc = [...this.state.currentFrequencies].sort((a, b) => a - b);
        const sortedDesc = [...sortedAsc].reverse();

        // Hide KDM section when only one frequency is selected
        if (kdmSection) {
            if (sortedAsc.length <= 1) {
                kdmSection.classList.add('hidden');
                return;
            } else {
                kdmSection.classList.remove('hidden');
            }
        }

        setSelectOptions(highSelect, sortedDesc.map((freq) => ({
            value: String(freq),
            label: `${freq} Hz`
        })));
        setSelectOptions(lowSelect, sortedAsc.map((freq) => ({
            value: String(freq),
            label: `${freq} Hz`
        })));

        // Set defaults to max/min frequencies
        highSelect.value = this.state.currentKdmHighFreq;
        lowSelect.value = this.state.currentKdmLowFreq;

        // Event listeners
        highSelect.onchange = () => {
            const newVal = parseInt(highSelect.value);
            if (!isNaN(newVal)) {
                this.state.currentKdmHighFreq = newVal;
                this._handlePostProcessUpdate();
            }
        };
        lowSelect.onchange = () => {
            const newVal = parseInt(lowSelect.value);
            if (!isNaN(newVal)) {
                this.state.currentKdmLowFreq = newVal;
                this._handlePostProcessUpdate();
            }
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

    _updatePeakDetectionWarnings(warnings) {
        const warningsContainer = this.dom.visualization.peakDetectionWarnings;
        const warningsList = this.dom.visualization.warningsList;

        // Remove only previously rendered peak-detection items (preserve missing-file warnings)
        warningsList.querySelectorAll('.peak-warning-item').forEach(el => el.remove());

        if (!warnings || warnings.length === 0) {
            if (!warningsList.children.length) warningsContainer.classList.add('hidden');
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
            warningDiv.className = 'peak-warning-item mb-2 p-2 bg-yellow-100 border border-yellow-200 rounded';

            // Create collapsible details
            const summary = document.createElement('div');
            summary.className = 'font-medium cursor-pointer flex items-center justify-between';
            const summaryText = document.createElement('span');
            summaryText.textContent = description;
            const summaryBadge = document.createElement('span');
            summaryBadge.className = 'text-xs bg-yellow-200 px-2 py-1 rounded';
            summaryBadge.textContent = 'Show Files';
            summary.appendChild(summaryText);
            summary.appendChild(summaryBadge);

            const details = document.createElement('div');
            details.className = 'mt-2 text-xs hidden';
            warningGroup.forEach((w) => {
                const detailLine = document.createElement('div');
                detailLine.textContent = `- ${w.filename} (${w.frequency}Hz, File #${w.file_number})`;
                details.appendChild(detailLine);
            });

            summary.addEventListener('click', () => {
                details.classList.toggle('hidden');
                const showText = details.classList.contains('hidden') ? 'Show Files' : 'Hide Files';
                summaryBadge.textContent = showText;
            });

            warningDiv.appendChild(summary);
            warningDiv.appendChild(details);
            warningsList.appendChild(warningDiv);
        });

        warningsContainer.classList.remove('hidden');
    }

    _addMissingFileWarning(data) {
        // Show a persistent orange warning for files the instrument software skipped
        const warningsContainer = this.dom.visualization.peakDetectionWarnings;
        const warningsList = this.dom.visualization.warningsList;
        if (!warningsContainer || !warningsList) return;

        const missing = data.missing_file_numbers || [];
        const freq = data.frequency;
        const detectedBy = data.detected_by_file_number;

        const warningDiv = document.createElement('div');
        warningDiv.className = 'mb-2 p-2 bg-orange-100 border border-orange-400 rounded';
        const warningLabel = document.createElement('span');
        warningLabel.className = 'font-semibold text-orange-800';
        warningLabel.textContent = `Warning: Missing file(s) at ${freq} Hz: `;
        const warningText = document.createElement('span');
        warningText.className = 'text-orange-700';
        warningText.textContent = `File #${missing.join(', #')} not detected (discovered when file #${detectedBy} arrived). Possible instrument software block - data gap(s) will appear as null in plots and export.`;
        warningDiv.appendChild(warningLabel);
        warningDiv.appendChild(warningText);
        warningsList.appendChild(warningDiv);
        warningsContainer.classList.remove('hidden');
        console.warn(`[MISSING FILE] Freq ${freq}Hz: files ${missing} missing, detected by #${detectedBy}`);
    }

    _addFileProcessingWarning(data) {
        const warningsContainer = this.dom.visualization.peakDetectionWarnings;
        const warningsList = this.dom.visualization.warningsList;
        if (!warningsContainer || !warningsList || !data?.message) return;

        const warningDiv = document.createElement('div');
        warningDiv.className = 'mb-2 p-2 bg-amber-100 border border-amber-400 rounded';
        const warningLabel = document.createElement('span');
        warningLabel.className = 'font-semibold text-amber-800';
        warningLabel.textContent = 'Warning: File skipped: ';
        const warningText = document.createElement('span');
        warningText.className = 'text-amber-700';
        warningText.textContent = `${data.filename || 'Unknown file'} - ${data.message}`;
        warningDiv.appendChild(warningLabel);
        warningDiv.appendChild(warningText);

        warningsList.appendChild(warningDiv);
        warningsContainer.classList.remove('hidden');
        console.warn('[FILE WARNING]', data);
    }

    _updateUIForMode(mode) {
        const frequencySelectorContainer = document.getElementById('frequencySelectorContainer');

        // Update UI elements based on analysis mode
        if (mode === 'frequency_map') {
            // Update frequency input hint
            this.dom.params.frequencyInputHint.classList.remove('hidden');
            this.dom.params.frequencyInput.placeholder = 'e.g., 10,20,50,100,200,500,1000';

            // Hide num files input, show frequency map hint
            this.dom.params.numFilesContainer.classList.add('hidden');
            this.dom.params.numFilesFrequencyMapHint.classList.remove('hidden');

            // Show frequency selector
            if (frequencySelectorContainer) {
                frequencySelectorContainer.classList.remove('hidden');
            }

            // Switch button text
            this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';
        } else {
            // Continuous monitor mode
            this.dom.params.frequencyInputHint.classList.add('hidden');
            this.dom.params.frequencyInput.placeholder = '';

            // Show num files input, hide frequency map hint
            this.dom.params.numFilesContainer.classList.remove('hidden');
            this.dom.params.numFilesFrequencyMapHint.classList.add('hidden');

            // Hide frequency selector
            if (frequencySelectorContainer) {
                frequencySelectorContainer.classList.add('hidden');
            }

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

            // Keep FM correction dropdowns current as data arrives
            this._populateFmCorrectionDropdowns();

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
            // Handle comparison: backend sends 'averaged' for null electrode, frontend uses null
            const isCurrentElectrode = (electrode_index === this.state.currentElectrode) ||
                                      (electrode_index === 'averaged' && this.state.currentElectrode === null) ||
                                      (electrode_index === null && this.state.currentElectrode === null);

            if (isCurrentElectrode) {
                console.log(`[OK] Updating visualization for current electrode ${electrodeKey}`);
                this._updateFrequencyMapStats();

                if (electrodeComplete) {
                    // Show overlay if all frequencies are complete for current electrode
                    console.log(`[COMPLETE] All frequencies complete for electrode ${electrodeKey} - SHOWING OVERLAY`);
                    this._updateFrequencyMapOverlay();
                } else {
                    // Update voltammogram plot (top) - only for NEW frequency
                    console.log(`[OK] Showing individual frequency ${frequency}Hz for electrode ${electrodeKey}`);
                    this._updateFrequencyMapVoltammogram(freqData);
                }

                // Update frequency-charge plot (bottom) - cumulative
                this._updateFrequencyChargeChart();
            } else {
                console.log(`[SKIP] Not current electrode - skipping visualization update (current: ${this.state.currentElectrode}, received: ${electrode_index})`);
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
                this.dom.folderStatus.textContent = 'Frequency map analysis started. Monitoring for files...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.startAnalysisBtn.textContent = 'Start Frequency Map Analysis';

                if (data.message) {
                    alert('Error starting frequency map analysis: ' + data.message);
                }
            }
        });

        // Handle frequency map export response
        this.socketManager.on('export_frequency_map_data_response', (data) => {
            if (data.status === 'success') {
                const filename = data.filename || this.dom.visualization.exportFrequencyMapDataBtn.dataset.filename || 'frequency_map_export.xlsx';
                this.dom.visualization.exportFrequencyMapStatus.textContent = `Export successful! Downloading ${filename}...`;
                this._triggerWorkbookDownload(data.content_b64, filename);
            } else {
                this.dom.visualization.exportFrequencyMapStatus.textContent = `Export failed: ${data.message}`;
            }
        });
    }

    _updateFrequencyMapVoltammogram(freqData) {
        console.log('[PLOT] _updateFrequencyMapVoltammogram called with data:', {
            frequency: freqData.frequency,
            hasSmoothedCurrents: !!freqData.smoothed_currents,
            smoothedCurrentsLength: freqData.smoothed_currents?.length,
            hasRegressionLine: !!freqData.regression_line,
            regressionLineLength: freqData.regression_line?.length,
            hasPotentials: !!freqData.potentials,
            potentialsLength: freqData.potentials?.length
        });

        // Choose plot div based on hold mode
        const isHoldMode = !!this.state.heldData;
        const plotDiv = isHoldMode
            ? this.dom.visualization.frequencyMapVoltammogramPlot  // Right side in hold mode
            : this.dom.visualization.nonHoldVoltammogramPlot;      // Non-hold mode plot

        const labelDiv = isHoldMode
            ? this.dom.visualization.currentFrequencyLabel
            : this.dom.visualization.nonHoldFrequencyLabel;

        console.log(`   Using plotDiv: ${plotDiv?.id}, isHoldMode: ${isHoldMode}`);

        if (!plotDiv) {
            console.error('[ERROR] Plot div not found!');
            return;
        }

        // Show individual frequency plot with baseline
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
            console.log('   [OK] Added smoothed data trace');
        } else {
            console.warn('   [WARN] No smoothed currents data');
        }

        // Regression line trace (baseline)
        if (freqData.regression_line && freqData.regression_line.length > 0) {
            traces.push({
                x: freqData.adjusted_potentials || freqData.potentials,
                y: freqData.regression_line, // Keep in Amperes (A)
                type: 'scatter',
                mode: 'lines',
                name: 'Baseline',
                line: { color: 'red', width: 2 }
            });
            console.log('   [OK] Added regression line trace');
        } else {
            console.warn('   [WARN] No regression line data');
        }

        if (traces.length === 0) {
            console.error('[ERROR] No traces to plot!');
            return;
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

        console.log(`   [CHART] Plotting ${traces.length} traces to ${plotDiv.id}`);
        Plotly.react(plotDiv, traces, layout, { responsive: true });
        console.log('   [OK] Plot updated successfully');

        // Update label
        if (labelDiv) {
            labelDiv.textContent =
                `Current: ${freqData.frequency} Hz | Peak: ${freqData.peak_value?.toExponential(4) || 'N/A'} A | Charge: ${freqData.charge?.toExponential(4) || 'N/A'} C`;
        }
    }

    _updateFrequencyMapOverlay() {
        console.log('[RENDER] _updateFrequencyMapOverlay called');

        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

        console.log(`   Electrode: ${electrodeKey}`);
        console.log(`   Analyzed frequencies: ${analyzedFreqs.length} [${analyzedFreqs.join(', ')}]`);

        // Generate color palette for different frequencies
        const colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'];

        // Choose plot div based on hold mode
        const isHoldMode = !!this.state.heldData;
        const plotDiv = isHoldMode
            ? this.dom.visualization.frequencyMapVoltammogramPlot  // Right side in hold mode
            : this.dom.visualization.nonHoldVoltammogramPlot;      // Non-hold mode plot

        const labelDiv = isHoldMode
            ? this.dom.visualization.currentFrequencyLabel
            : this.dom.visualization.nonHoldFrequencyLabel;

        // Render overlay without baseline (final summary view)
        this._renderVoltammogramOverlay(
            plotDiv,
            electrodeFreqData,
            colors,
            'All Frequencies Overlay' // Title
        );

        // Update label
        if (labelDiv) {
            labelDiv.textContent =
                `Analysis Complete - Showing all ${analyzedFreqs.length} frequencies`;
        }

        console.log(`   [OK] Overlay plot complete!`);
    }

    _renderVoltammogramOverlay(plotDiv, frequencyData, colors, titleText) {
        const traces = [];
        const freqs = Object.keys(frequencyData).map(f => parseFloat(f)).sort((a, b) => a - b);

        if (freqs.length === 0) {
            // No data to plot
            Plotly.react(plotDiv, [], {
                title: titleText,
                xaxis: { title: 'Potential (V)', autorange: 'reversed' },
                yaxis: { title: 'Current (A)' },
                annotations: [{
                    text: 'Waiting for data...',
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    showarrow: false,
                    font: { size: 16, color: 'gray' }
                }]
            }, { responsive: true });
            return;
        }

        freqs.forEach((freq, index) => {
            const freqData = frequencyData[freq];
            if (freqData && freqData.smoothed_currents && freqData.smoothed_currents.length > 0) {
                traces.push({
                    x: freqData.potentials,
                    y: freqData.smoothed_currents,
                    type: 'scatter',
                    mode: 'markers',
                    name: `${freq} Hz`,
                    marker: { size: 3, color: colors[index % colors.length] }
                });
            }
        });

        const layout = {
            title: titleText,
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

        Plotly.react(plotDiv, traces, layout, { responsive: true });
    }

    _updateFrequencyChargeChart() {
        const electrodeKey = this.state.currentElectrode !== null ? this.state.currentElectrode.toString() : 'averaged';
        const electrodeFreqData = this.state.frequencyMapData[electrodeKey] || {};
        const analyzedFreqs = this.state.analyzedFrequencies[electrodeKey] || [];

        if (analyzedFreqs.length === 0) {
            /* fall through to render empty chart */
            return; // No data to plot yet
        }

        const isHoldMode = !!this.state.heldData;

        if (isHoldMode) {
            // Hold mode: overlay both sessions on the same plot
            const heldElectrodeData = this.state.heldData[electrodeKey] || {};
            this._renderChargeVsFrequencyOverlay(
                this.dom.visualization.frequencyMapChargePlot,
                heldElectrodeData,
                electrodeFreqData,
                this.state.heldSessionName,
                this.state.currentSessionName,
                electrodeKey
            );
        } else {
            // Non-hold mode: render to non-hold plot div
            this._renderChargeVsFrequency(
                this.dom.visualization.nonHoldChargePlot,
                electrodeFreqData,
                'Frequency Map: Charge vs Frequency',
                electrodeKey,
                'current'
            );
        }
    }

    _renderChargeVsFrequency(plotDiv, frequencyData, titleText, electrodeKey, sessionKey) {
        const freqs = Object.keys(frequencyData).map(f => parseFloat(f)).sort((a, b) => a - b);

        if (freqs.length === 0) {
            Plotly.react(plotDiv, [], {
                title: titleText,
                xaxis: { title: 'Frequency (Hz)' },
                yaxis: { title: 'Charge (C)' },
                annotations: [{
                    text: 'Waiting for data...',
                    xref: 'paper', yref: 'paper', x: 0.5, y: 0.5,
                    showarrow: false, font: { size: 16, color: 'gray' }
                }]
            }, { responsive: true });
            return;
        }

        const ek = electrodeKey || 'averaged';
        const sk = sessionKey || 'current';
        const charges = freqs.map(freq => {
            const eff = this._getFmEffectiveValues(sk, ek, freq);
            return eff?.charge ?? frequencyData[freq]?.charge ?? 0;
        });

        const trace = {
            x: freqs, y: charges,
            type: 'scatter', mode: 'markers+lines',
            name: 'Charge vs Frequency',
            marker: { size: 8, color: 'blue' },
            line: { color: 'blue', width: 2 }
        };

        const layout = {
            title: titleText,
            xaxis: { title: 'Frequency (Hz)', type: 'log', autorange: true },
            yaxis: { title: 'Charge (C)' },
            showlegend: false,
            margin: { l: 60, r: 30, t: 50, b: 50 },
            hovermode: 'closest'
        };

        Plotly.react(plotDiv, [trace], layout, { responsive: true });
    }

    _renderChargeVsFrequencyOverlay(plotDiv, heldSessionData, currentSessionData, heldSessionName, currentSessionName, electrodeKey) {
        const heldFreqs = Object.keys(heldSessionData).map(f => parseFloat(f)).sort((a, b) => a - b);
        const currentFreqs = Object.keys(currentSessionData).map(f => parseFloat(f)).sort((a, b) => a - b);

        console.log('[HOLD MODE] Rendering charge vs frequency overlay:');
        console.log('  Held session frequencies:', heldFreqs);
        console.log('  Current session frequencies:', currentFreqs);

        const ek = electrodeKey || 'averaged';
        const traces = [];

        if (heldFreqs.length > 0) {
            const heldCharges = heldFreqs.map(freq => {
                const eff = this._getFmEffectiveValues('session1', ek, freq);
                return eff?.charge ?? heldSessionData[freq]?.charge ?? 0;
            });
            traces.push({
                x: heldFreqs, y: heldCharges,
                type: 'scatter', mode: 'markers+lines',
                name: heldSessionName || 'Session 1',
                marker: { size: 8, color: 'blue' },
                line: { color: 'blue', width: 2 }
            });
        }

        if (currentFreqs.length > 0) {
            const currentCharges = currentFreqs.map(freq => {
                const eff = this._getFmEffectiveValues('session2', ek, freq);
                return eff?.charge ?? currentSessionData[freq]?.charge ?? 0;
            });
            traces.push({
                x: currentFreqs, y: currentCharges,
                type: 'scatter', mode: 'markers+lines',
                name: currentSessionName || 'Session 2',
                marker: { size: 8, color: 'green' },
                line: { color: 'green', width: 2 }
            });
        }

        const layout = {
            title: 'Charge vs Frequency (Both Sessions)',
            xaxis: { title: 'Frequency (Hz)', type: 'log', autorange: true },
            yaxis: { title: 'Charge (C)' },
            showlegend: true,
            legend: { x: 1.05, y: 1, xanchor: 'left' },
            margin: { l: 60, r: 120, t: 50, b: 50 },
            hovermode: 'closest'
        };

        Plotly.react(plotDiv, traces, layout, { responsive: true });
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

        // If in hold mode, update held session voltammogram for the new electrode
        const isHoldMode = !!this.state.heldData;
        if (isHoldMode) {
            this._renderHeldSessionVoltammogram();
        }

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

    _handleReplicationGrouping() {
            alert('Please enter a valid replication value (>= 1)');
        const replication = parseInt(this.dom.visualization.replicationInput.value);

        if (!replication || replication < 1) {
            alert('Please enter a valid replication value (>= 1)');
            return;
        }

        // Get the current calculated data
        const originalData = this.state.lastCalculatedData;
        if (!originalData) {
            alert('No data available to group. Please run analysis first.');
            return;
        }

        console.log(`Grouping data with replication n=${replication}`);

            alert('Please enter a valid replication value (>= 1)');
        this.state.currentReplication = replication;

        // If replication is 1, no grouping needed
        if (replication === 1) {
            this.state.groupedData = null;
            this._renderTrendPlots(originalData);
            return;
        }

        // Group the data
        const groupedData = this._groupDataByReplication(originalData, replication);

        // Store grouped data in state
        this.state.groupedData = groupedData;

        // Render grouped data with error bars
        this._renderTrendPlotsWithErrorBars(groupedData);
    }

    _groupDataByReplication(data, replication) {
        // Calculate number of groups
        const numDataPoints = data.x_axis_values.length;
        const numGroups = Math.floor(numDataPoints / replication);

        if (numGroups === 0) {
            alert(`Not enough data points for replication n=${replication}. Only ${numDataPoints} data points available.`);
            return null;
        }

        console.log(`Grouping ${numDataPoints} data points into ${numGroups} groups`);

        // Initialize grouped data structure
        const groupedData = {
            x_axis_values: [],
            x_axis_errors: [],
            peak_current_trends: {},
            peak_current_errors: {},
            normalized_peak_trends: {},
            normalized_peak_errors: {},
            kdm_trend: [],
            kdm_errors: [],
            num_groups: numGroups,
            replication: replication
        };

        // Helper function to calculate mean and standard error
        const calculateStats = (values) => {
            const validValues = values.filter(v => v !== null && v !== undefined && !isNaN(v));
            if (validValues.length === 0) return { mean: null, se: null };

            const mean = validValues.reduce((sum, v) => sum + v, 0) / validValues.length;

            if (validValues.length === 1) {
                return { mean, se: 0 };
            }

            // Calculate standard deviation
            const variance = validValues.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (validValues.length - 1);
            const std = Math.sqrt(variance);

            // Calculate standard error: SE = SD / sqrt(n)
            const se = std / Math.sqrt(validValues.length);

            return { mean, se };
        };

        // Group x-axis values
        for (let g = 0; g < numGroups; g++) {
            const startIdx = g * replication;
            const endIdx = Math.min(startIdx + replication, numDataPoints);
            const groupValues = data.x_axis_values.slice(startIdx, endIdx);

            const stats = calculateStats(groupValues);
            groupedData.x_axis_values.push(stats.mean);
            groupedData.x_axis_errors.push(stats.se);
        }

        // Group peak current trends for each frequency
        const freqStrings = Object.keys(data.peak_current_trends);
        for (const freqStr of freqStrings) {
            groupedData.peak_current_trends[freqStr] = [];
            groupedData.peak_current_errors[freqStr] = [];

            for (let g = 0; g < numGroups; g++) {
                const startIdx = g * replication;
                const endIdx = Math.min(startIdx + replication, numDataPoints);
                const groupValues = data.peak_current_trends[freqStr].slice(startIdx, endIdx);

                const stats = calculateStats(groupValues);
                groupedData.peak_current_trends[freqStr].push(stats.mean);
                groupedData.peak_current_errors[freqStr].push(stats.se);
            }
        }

        // Group normalized peak trends for each frequency
        for (const freqStr of freqStrings) {
            groupedData.normalized_peak_trends[freqStr] = [];
            groupedData.normalized_peak_errors[freqStr] = [];

            for (let g = 0; g < numGroups; g++) {
                const startIdx = g * replication;
                const endIdx = Math.min(startIdx + replication, numDataPoints);
                const groupValues = data.normalized_peak_trends[freqStr].slice(startIdx, endIdx);

                const stats = calculateStats(groupValues);
                groupedData.normalized_peak_trends[freqStr].push(stats.mean);
                groupedData.normalized_peak_errors[freqStr].push(stats.se);
            }
        }

        // Group KDM trend
        for (let g = 0; g < numGroups; g++) {
            const startIdx = g * replication;
            const endIdx = Math.min(startIdx + replication, numDataPoints);
            const groupValues = data.kdm_trend.slice(startIdx, endIdx);

            const stats = calculateStats(groupValues);
            groupedData.kdm_trend.push(stats.mean);
            groupedData.kdm_errors.push(stats.se);
        }

        return groupedData;
    }

    _renderTrendPlotsWithErrorBars(groupedData) {
        if (!groupedData) return;

        const injectionPoint = parseInt(this.dom.visualization.postProcessInjectionPointInput.value) || null;
        const freqStrs = this.state.currentFrequencies.map(String);
        const xAxisTitle = (this.state.currentXAxisOptions === "Experiment Time") ? 'Experiment Time (min)' : 'Group Number';

        // Determine Y-axis title based on analysis mode
        const selectedOptions = this.dom.settings.selectedOptionsInput.value;
        const isAUCMode = selectedOptions === "Area Under the Curve";
        const firstPlotYTitle = isAUCMode ? 'AUC (a.u.)' : 'Peak Current (A)';

        // Render plots with error bars
        this._renderTrendPlotWithErrorBars('peakCurrentTrendPlot', groupedData, freqStrs, xAxisTitle, firstPlotYTitle, 'peak', injectionPoint);
        this._renderTrendPlotWithErrorBars('normalizedPeakTrendPlot', groupedData, freqStrs, xAxisTitle, 'Normalized Current', 'normalized', injectionPoint);
        this._renderTrendPlotWithErrorBars('kdmTrendPlot', groupedData, freqStrs, xAxisTitle, 'KDM (%)', 'kdm', injectionPoint);
    }

    _renderTrendPlotWithErrorBars(plotDivId, data, freqStrings, xAxisTitle, yAxisTitle, trendType, injectionPoint) {
        const plotDiv = document.getElementById(plotDivId);
        if (!plotDiv) return;
        clearChildren(plotDiv);

        let traces = [];
        const xData = data.x_axis_values;

        if (!xData || xData.length === 0) {
            setSingleMessage(plotDiv, 'No data available to plot.', 'text-gray-400');
            return;
        }

        const colors = {
            lowFreqBefore: '#E6194B', highFreqBefore: '#4363d8', kdmBefore: '#911EB4',
            lowFreqAfter: '#F58231', highFreqAfter: '#42D4F4', kdmAfter: '#3CB44B',
            otherFreqBase: ['#FABEBE', '#FFE119', '#BF360C', '#A9A9A9', '#800000', '#AA6E28', '#808000', '#F032E6', '#000075', '#F58231']
        };

        const kdmHighFreq = this.state.currentKdmHighFreq;
        const kdmLowFreq = this.state.currentKdmLowFreq;

        if (trendType === "peak" || trendType === "normalized") {
            const trendKey = trendType === "peak" ? "peak_current_trends" : "normalized_peak_trends";
            const errorKey = trendType === "peak" ? "peak_current_errors" : "normalized_peak_errors";

            freqStrings.forEach((freqStr, i) => {
                const freq = parseInt(freqStr);
                const yData = data[trendKey][freqStr] || [];
                const yErrors = data[errorKey][freqStr] || [];

                let color;
                if (freq === kdmLowFreq) {
                    color = colors.lowFreqBefore;
                } else if (freq === kdmHighFreq) {
                    color = colors.highFreqBefore;
                } else {
                    const colorIndex = i % colors.otherFreqBase.length;
                    color = colors.otherFreqBase[colorIndex];
                }

                traces.push({
                    x: xData,
                    y: yData,
                    error_y: {
                        type: 'data',
                        array: yErrors,
                        visible: true,
                        color: color
                    },
                    mode: 'markers+lines',
                    name: `${freqStr}Hz`,
                    marker: { size: 8, color: color },
                    line: { color: color }
                });
            });
        } else if (trendType === "kdm") {
            const yData = data.kdm_trend || [];
            const yErrors = data.kdm_errors || [];

            traces.push({
                x: xData,
                y: yData,
                error_y: {
                    type: 'data',
                    array: yErrors,
                    visible: true,
                    color: colors.kdmBefore
                },
                mode: 'markers+lines',
                name: 'KDM',
                marker: { size: 8, color: colors.kdmBefore },
                line: { color: colors.kdmBefore }
            });
        }

        const layout = {
            title: '',
            xaxis: {
                title: xAxisTitle,
                autorange: true
            },
            yaxis: {
                title: yAxisTitle,
                autorange: true,
                exponentformat: 'SI'
            },
            margin: { t: 40, b: 60, l: 60, r: 20 },
            showlegend: true,
            legend: {
                x: 1.05,
                y: 1,
                xanchor: 'left'
            }
        };

        Plotly.newPlot(plotDivId, traces, layout);
    }
}





