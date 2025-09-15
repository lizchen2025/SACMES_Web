// static/js/swv_module.js (The final, fully functional version)

import { PlotlyPlotter } from './plot_utils.js';

export class SWVModule {
    constructor(socketManager, uiManager) {
        this.socketManager = socketManager;
        this.uiManager = uiManager;

        // --- DOM Element Caching (Complete) ---
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
                exportDataBtn: document.getElementById('exportDataBtn'),
                exportStatus: document.getElementById('exportStatus'),
                postProcessNormalizationPointInput: document.getElementById('postProcessNormalizationPointInput'),
                postProcessLowFrequencyOffsetInput: document.getElementById('postProcessLowFrequencyOffsetInput'),
                postProcessLowFrequencySlopeInput: document.getElementById('postProcessLowFrequencySlopeInput'),
                postProcessInjectionPointInput: document.getElementById('postProcessInjectionPointInput'),
                updateInjectionPointBtn: document.getElementById('updateInjectionPointBtn'),
                applyPostProcessNormalizationBtn: document.getElementById('applyPostProcessNormalizationBtn'),
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
            rawTrendData: null
        };

        this._setupEventListeners();
        this._setupSocketHandlers();
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
            const defaultFilename = `SACMES_Analysis_${new Date().toISOString().slice(0,10)}.csv`;
            const filename = prompt("Please enter a filename for the CSV export:", defaultFilename);
            if (filename) {
                this.dom.visualization.exportDataBtn.dataset.filename = filename;
                this.dom.visualization.exportStatus.textContent = 'Generating export file...';
                this.socketManager.emit('request_export_data', {});
            }
        });

        this.dom.visualization.updateInjectionPointBtn.addEventListener('click', () => this._handlePostProcessUpdate());
        this.dom.visualization.applyPostProcessNormalizationBtn.addEventListener('click', () => this._handlePostProcessUpdate());
    }
    
    _setupSocketHandlers() {
        this.socketManager.on('connect', () => this.socketManager.emit('request_agent_status', {}));

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
                this.dom.folderStatus.textContent = 'Instructions sent. Agent is now scanning...';
            } else {
                this.dom.folderStatus.textContent = data.message;
                this.state.isAnalysisRunning = false;
                this.dom.startAnalysisBtn.disabled = false;
                this.dom.startAnalysisBtn.textContent = 'Start Analysis & Sync';
            }
        });

        this.socketManager.on('live_analysis_update', (data) => {
            if (this.state.isAnalysisRunning) {
                this.state.rawTrendData = data.trend_data;
                this.handleLiveUpdate(data);
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
    }

    _triggerCsvDownload(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    _handlePostProcessUpdate() {
        if (!this.state.rawTrendData) {
            console.warn("No raw trend data available for post-processing.");
            return;
        }
        this._renderTrendPlots(this.state.rawTrendData);
    }

    _handleStartAnalysis() {
        const numFiles = parseInt(this.dom.params.numFilesInput.value);
        if (isNaN(numFiles) || numFiles < 1) { alert("Please enter a valid number of files."); return; }
        const frequencies = this.dom.params.frequencyInput.value.split(',').map(f => parseInt(f.trim())).filter(f => !isNaN(f));
        if (frequencies.length < 2) { alert("Please enter at least two valid frequencies."); return; }

        this.state = {
            isAnalysisRunning: true,
            currentFrequencies: frequencies,
            currentNumFiles: numFiles,
            currentXAxisOptions: this.dom.settings.xAxisOptionsInput.value,
            currentKdmHighFreq: Math.max(...frequencies),
            currentKdmLowFreq: Math.min(...frequencies),
            rawTrendData: null
        };
        
        this.dom.visualization.postProcessNormalizationPointInput.value = this.dom.params.normalizationPointInput.value;
        this.dom.visualization.postProcessLowFrequencyOffsetInput.value = this.dom.params.lowFrequencyOffsetInput.value;
        this.dom.visualization.postProcessLowFrequencySlopeInput.value = this.dom.params.lowFrequencySlopeInput.value;
        this.dom.visualization.postProcessInjectionPointInput.value = this.dom.params.injectionPointInput.value;
        
        const analysisParams = {
            num_files: numFiles,
            frequencies: this.state.currentFrequencies,
            num_electrodes: parseInt(this.dom.params.numElectrodesInput.value),
            sg_window: parseInt(this.dom.params.sgWindowInput.value),
            sg_degree: parseInt(this.dom.params.sgDegreeInput.value),
            polyfit_deg: parseInt(this.dom.params.polyfitDegreeInput.value),
            cutoff_frequency: parseInt(this.dom.params.cutoffFrequencyInput.value),
            normalizationPoint: parseInt(this.dom.params.normalizationPointInput.value),
            lowFrequencyOffset: parseFloat(this.dom.params.lowFrequencyOffsetInput.value),
            lowFrequencySlope: parseFloat(this.dom.params.lowFrequencySlopeInput.value),
            injectionPoint: this.dom.params.injectionPointInput.value === '' ? null : parseInt(this.dom.params.injectionPointInput.value),
            voltage_column: parseInt(this.dom.settings.voltageColumnInput.value),
            current_column: parseInt(this.dom.settings.currentColumnInput.value),
            spacing_index: parseInt(this.dom.settings.spacingIndexInput.value),
            delimiter: parseInt(this.dom.settings.delimiterInput.value),
            file_extension: this.dom.settings.fileExtensionInput.value,
            SelectedOptions: this.dom.settings.selectedOptionsInput.value,
            XaxisOptions: this.state.currentXAxisOptions,
        };
        const filters = {
            handle: this.dom.params.fileHandleInput.value.trim(),
            frequencies: this.state.currentFrequencies,
            range_start: 1,
            range_end: numFiles
        };

        this.dom.startAnalysisBtn.textContent = 'Analysis Running...';
        this.dom.startAnalysisBtn.disabled = true;
        this.dom.folderStatus.textContent = "Sending instructions to server...";

        this._setupVisualizationLayout();
        this.uiManager.showScreen('visualizationArea');
        
        this.dom.visualization.adjustmentControls.classList.remove('hidden');
        this.dom.visualization.exportDataBtn.classList.remove('hidden');
        this.dom.visualization.exportStatus.textContent = '';
        
        this.socketManager.emit('start_analysis_session', { filters, analysisParams });
    }
    
    handleLiveUpdate(data) {
        const { filename, individual_analysis, trend_data } = data;
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
        if (trend_data) {
            this._renderTrendPlots(trend_data);
        }
    }

    _renderTrendPlots(trendData) {
        const injectionPoint = parseInt(this.dom.visualization.postProcessInjectionPointInput.value) || null;
        const resizeInterval = parseInt(this.dom.settings.resizeIntervalInput.value);
        const freqStrs = this.state.currentFrequencies.map(String);
        let xAxisTitle = (this.state.currentXAxisOptions === "Experiment Time") ? 'Experiment Time (h)' : 'File Number';
        PlotlyPlotter.renderFullTrendPlot('peakCurrentTrendPlot', trendData, freqStrs, xAxisTitle, 'Peak Current (µA)', this.state.currentNumFiles, 'Peak Current vs. ' + xAxisTitle, 'peak', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('normalizedPeakTrendPlot', trendData, freqStrs, xAxisTitle, 'Normalized Current', this.state.currentNumFiles, 'Normalized Peak Current vs. ' + xAxisTitle, 'normalized', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
        PlotlyPlotter.renderFullTrendPlot('kdmTrendPlot', trendData, ['KDM'], xAxisTitle, 'KDM Value', this.state.currentNumFiles, 'KDM Trend vs. ' + xAxisTitle, 'kdm', this.state.currentXAxisOptions, resizeInterval, this.state.currentKdmHighFreq, this.state.currentKdmLowFreq, injectionPoint);
    }
    
    _setupVisualizationLayout() {
        const { individualPlotsContainer } = this.dom.visualization;
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
        // Trend plots container is cleared and populated by _renderTrendPlots, so no need to set it up here.
    }
}