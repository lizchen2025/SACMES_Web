// static/js/swv_module.js
// This is the complete and final version for the real-time agent architecture.

import { PlotlyPlotter } from './plot_utils.js';

export class SWVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        // --- DOM Element Caching ---
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
                numElectrodesInput: document.getElementById('numElectrodesInput'),
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
                byteLimitInput: document.getElementById('byteLimitInput'),
                sampleRateInput: document.getElementById('sampleRateInput'),
                analysisIntervalInput: document.getElementById('analysisIntervalInput'),
                resizeIntervalInput: document.getElementById('resizeIntervalInput'),
                selectedOptionsInput: document.getElementById('selectedOptionsInput'),
                xAxisOptionsInput: document.getElementById('xAxisOptionsInput'),
            },
            visualization: {
                visualizationArea: document.getElementById('visualizationArea'),
                individualPlotsContainer: document.getElementById('individualPlotsContainer'),
                trendPlotsContainer: document.getElementById('trendPlotsContainer'),
                adjustmentControls: document.getElementById('adjustmentControls'),
                backToSWVBtn: document.getElementById('backToSWVBtn'),
            },
        };

        // --- State Management ---
        this.state = {
            isAnalysisRunning: false,
            currentFrequencies: [],
            currentNumFiles: 0,
            currentXAxisOptions: "File Number",
            currentKdmHighFreq: null,
            currentKdmLowFreq: null,
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
    }

    _setupEventListeners() {
        this.dom.swvBtn.addEventListener('click', () => this.uiManager.showScreen('swvAnalysisScreen'));
        this.dom.startAnalysisBtn.addEventListener('click', this._handleStartAnalysis.bind(this));
        this.dom.backToWelcomeBtn.addEventListener('click', () => this.uiManager.showScreen('welcomeScreen'));
        
        this.dom.visualization.backToSWVBtn.addEventListener('click', () => {
            this.uiManager.showScreen('swvAnalysisScreen');
            this.state.isAnalysisRunning = false;
            this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
            this.dom.startAnalysisBtn.disabled = false;
        });
    }

    _setupSocketHandlers() {
        this.socketManager.on('connect', () => {
            this.socketManager.emit('request_agent_status', {});
        });

        this.socketManager.on('agent_status', (data) => {
            if (data.status === 'connected') {
                this.dom.agentStatus.textContent = 'Local agent connected. Ready to sync.';
                this.dom.agentStatus.className = 'text-sm text-green-700 mt-1';
            } else {
                this.dom.agentStatus.textContent = 'Error: Local agent is disconnected. Please run the agent program.';
                this.dom.agentStatus.className = 'text-sm text-red-700 mt-1';
            }
        });

        this.socketManager.on('ack_start_session', (data) => {
            if (data.status === 'success') {
                this.dom.folderStatus.textContent = 'Instructions sent. Agent is now scanning and syncing files...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
                this.dom.startAnalysisBtn.disabled = false;
            }
        });

        this.socketManager.on('live_analysis_update', (data) => {
            if (this.state.isAnalysisRunning) {
                this.handleLiveUpdate(data);
            }
        });
    }

    _handleStartAnalysis() {
        const numFiles = parseInt(this.dom.params.numFilesInput.value);
        if (isNaN(numFiles) || numFiles < 1) {
            alert("Please enter a valid number of files.");
            return;
        }

        const frequencies = this.dom.params.frequencyInput.value.split(',').map(f => parseInt(f.trim())).filter(f => !isNaN(f));
        if (frequencies.length < 2) {
            alert("Please enter at least two valid frequencies.");
            return;
        }

        // --- Update State ---
        this.state.currentFrequencies = frequencies;
        this.state.currentNumFiles = numFiles;
        this.state.currentXAxisOptions = this.dom.settings.xAxisOptionsInput.value;
        this.state.currentKdmHighFreq = Math.max(...frequencies);
        this.state.currentKdmLowFreq = Math.min(...frequencies);

        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            frequencies: this.state.currentFrequencies,
            range_start: 1,
            range_end: numFiles
        };

        const analysisParams = {
            num_files: numFiles,
            frequencies: this.state.currentFrequencies,
            num_electrodes: parseInt(this.dom.params.numElectrodesInput.value.trim()),
            sg_window: parseInt(this.dom.params.sgWindowInput.value.trim()),
            sg_degree: parseInt(this.dom.params.sgDegreeInput.value.trim()),
            polyfit_deg: parseInt(this.dom.params.polyfitDegreeInput.value.trim()),
            cutoff_frequency: parseInt(this.dom.params.cutoffFrequencyInput.value.trim()),
            normalizationPoint: parseInt(this.dom.params.normalizationPointInput.value.trim()),
            lowFrequencyOffset: parseFloat(this.dom.params.lowFrequencyOffsetInput.value.trim()),
            lowFrequencySlope: parseFloat(this.dom.params.lowFrequencySlopeInput.value.trim()),
            injectionPoint: this.dom.params.injectionPointInput.value.trim() === '' ? null : parseInt(this.dom.params.injectionPointInput.value.trim()),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value.trim()),
            current_column: parseInt(this.dom.settings.currentColumnInput.value.trim()),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value.trim()),
            delimiter: parseInt(this.dom.settings.delimiterInput.value.trim()),
            file_extension: this.dom.settings.fileExtensionInput.value.trim(),
            SelectedOptions: this.dom.settings.selectedOptionsInput.value.trim(),
            XaxisOptions: this.state.currentXAxisOptions,
        };

        // --- UI and State Update ---
        this.state.isAnalysisRunning = true;
        this.dom.startAnalysisBtn.textContent = 'Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending instructions to server...";

        this._setupVisualizationLayout();
        this.uiManager.showScreen('visualizationArea');
        
        this.socketManager.emit('start_analysis_session', {
            filters: filters,
            analysisParams: analysisParams
        });
    }

    handleLiveUpdate(data) {
        const { filename, individual_analysis, trend_data } = data;
        
        // Update Individual Plot
        if (individual_analysis && individual_analysis.status !== 'error') {
            const match = filename.match(/_(\d+)Hz_?_?(\d+)\./);
            if (match) {
                const freq = parseInt(match[1]);
                const fileNum = parseInt(match[2]);
                
                const plotDivId = `plotArea-${freq}`;
                const fileNumEl = document.getElementById(`fileNumDisplay-${freq}`);
                const peakHeightEl = document.getElementById(`peakHeightDisplay-${freq}`);
                
                if (document.getElementById(plotDivId) && fileNumEl && peakHeightEl) {
                    PlotlyPlotter.plotIndividualData(plotDivId, individual_analysis.potentials, individual_analysis.raw_currents, individual_analysis.smoothed_currents,
                                                    individual_analysis.regression_line, individual_analysis.adjusted_potentials, individual_analysis.auc_vertices, this.dom.settings.selectedOptionsInput.value);
                    fileNumEl.textContent = fileNum;
                    peakHeightEl.textContent = individual_analysis.peak_value !== null ? individual_analysis.peak_value.toFixed(4) : "N/A";
                }
            }
        }

        // Update all trend plots using the complete data from the server
        if (trend_data) {
            this._renderTrendPlots(trend_data);
        }
    }

    _renderTrendPlots(trendData) {
        const injectionPoint = parseInt(this.dom.params.injectionPointInput.value) || null;
        const resizeInterval = parseInt(this.dom.settings.resizeIntervalInput.value);
        const freqStrs = this.state.currentFrequencies.map(String);
        let xAxisTitle = (this.state.currentXAxisOptions === "Experiment Time") ? 'Experiment Time (h)' : 'File Number';

        PlotlyPlotter.renderFullTrendPlot('peakCurrentTrendPlot', trendData, freqStrs, xAxisTitle, 'Peak Current (µA)', this.state.currentNumFiles, 'Peak Current vs. ' + xAxisTitle, 'peak', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('normalizedPeakTrendPlot', trendData, freqStrs, xAxisTitle, 'Normalized Current', this.state.currentNumFiles, 'Normalized Peak Current vs. ' + xAxisTitle, 'normalized', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('kdmTrendPlot', trendData, ['KDM'], xAxisTitle, 'KDM Value', this.state.currentNumFiles, 'KDM Trend vs. ' + xAxisTitle, 'kdm', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
    }

    _setupVisualizationLayout() {
        const { individualPlotsContainer, trendPlotsContainer } = this.dom.visualization;
        const highFreq = this.state.currentKdmHighFreq;
        const lowFreq = this.state.currentKdmLowFreq;

        if (individualPlotsContainer) {
            individualPlotsContainer.innerHTML = `
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">${highFreq} Hz Analysis</h4>
                    <div id="plotArea-${highFreq}" class="w-full plotly-plot-container bg-gray-100 flex justify-center items-center text-gray-400">Waiting for data...</div>
                    <p class="text-sm mt-2">File: <span id="fileNumDisplay-${highFreq}">N/A</span>, Peak: <span id="peakHeightDisplay-${highFreq}">N/A</span></p>
                </div>
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">${lowFreq} Hz Analysis</h4>
                    <div id="plotArea-${lowFreq}" class="w-full plotly-plot-container bg-gray-100 flex justify-center items-center text-gray-400">Waiting for data...</div>
                    <p class="text-sm mt-2">File: <span id="fileNumDisplay-${lowFreq}">N/A</span>, Peak: <span id="peakHeightDisplay-${lowFreq}">N/A</span></p>
                </div>
            `;
        }
        if (trendPlotsContainer) {
            trendPlotsContainer.innerHTML = `
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">Peak Current Trend</h4>
                    <div id="peakCurrentTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                        Waiting for data...
                    </div>
                </div>
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">Normalized Peak Current Trend</h4>
                    <div id="normalizedPeakTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                        Waiting for data...
                    </div>
                </div>
                <div class="border rounded-lg p-4 bg-gray-50">
                    <h4 class="text-lg font-semibold text-gray-700 mb-2">KDM Trend</h4>
                    <div id="kdmTrendPlot" class="w-full plotly-trend-plot-container bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400">
                        Waiting for data...
                    </div>
                </div>
            `;
        }
    }
}
