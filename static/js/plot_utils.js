// static/js/plot_utils.js

export class PlotlyPlotter {
    static plotIndividualData(plotDivId, potentials, rawCurrents, smoothedCurrents, regressionLine, adjustedPotentials, aucVertices, selectedOptions) {
        const traces = [];

        // Raw Current Trace
        traces.push({
            x: potentials,
            y: rawCurrents,
            mode: 'lines',
            name: 'Raw Current',
            line: {color: 'blue'}
        });

        // Smoothed Current Trace
        traces.push({
            x: potentials,
            y: smoothedCurrents,
            mode: 'lines',
            name: 'Smoothed Current',
            line: {color: 'red', width: 2}
        });

        // Regression Line Trace
        if (regressionLine && adjustedPotentials) {
            traces.push({
                x: adjustedPotentials,
                y: regressionLine,
                mode: 'lines',
                name: 'Regression Line',
                line: {color: 'green', dash: 'dash', width: 1}
            });
        }

        // AUC Area Trace (for plotting the filled region)
        if (selectedOptions === "Area Under the Curve" && aucVertices && aucVertices.length > 0) {
            const shapeX = aucVertices.map(v => v[0]);
            const shapeY = aucVertices.map(v => v[1]);

            traces.push({
                x: shapeX,
                y: shapeY,
                fill: 'toself',
                fillcolor: 'rgba(0,100,80,0.2)', // A light, semi-transparent green fill
                mode: 'lines', // Use lines to define the perimeter of the filled area
                line: {color: 'transparent'}, // Make the line transparent
                name: 'AUC Area',
                hoverinfo: 'none' // Don't show hover info for the fill area itself
            });
        }

        const layout = {
            title: '', // Title is set dynamically by SWVModule, or can be added here
            autosize: true,
            xaxis: {
                title: 'Potential (V)',
                autorange: true,
                tickangle: -45,
                tickfont: { size: 10 }
            },
            yaxis: {
                title: 'Current (µA)', // Ensure unit consistency
                autorange: true,
                rangemode: 'normal'
            },
            legend: {
                    orientation: 'h', // Changed from 'v' to 'h' for horizontal layout
                    yanchor: 'bottom',
                    y: 1.02,
                    xanchor: 'center',
                    x: 0.5,
                    font: { size: 10 }
            },
            margin: { t: 50, b: 50, l: 60, r: 20 } // Increased top margin for legend
        };

        Plotly.newPlot(plotDivId, traces, layout);
        // Clear "Waiting for data..." message after plot is initialized
        const plotDiv = document.getElementById(plotDivId);
        if (plotDiv && plotDiv.textContent.includes('Waiting for data...')) {
            plotDiv.textContent = '';
        }
    }

    /**
     * Initializes trend plots with empty data (placeholders for later extension).
     * @param {string} plotDivId - The ID of the div element where the plot will be rendered.
     * @param {Array<string>} traceNames - Names for each trace (e.g., "15Hz Peak Current").
     * @param {string} xAxisTitle - Title for the X-axis.
     * @param {string} yAxisTitle - Title for the Y-axis.
     * @param {number} numFiles - Total number of files for X-axis range.
     * @param {string} title - Plot title.
     * @param {string} xAxisUnits - "File Number" or "Experiment Time".
     * @param {number} resizeInterval - Interval for dynamic X-axis resizing.
     * @param {number} kdmHighFreq - High KDM frequency for color differentiation.
     * @param {number} kdmLowFreq - Low KDM frequency for color differentiation.
     */
    static initializeTrendPlot(plotDivId, traceNames, xAxisTitle, yAxisTitle, numFiles, title, xAxisUnits, resizeInterval, kdmHighFreq, kdmLowFreq) {
        // Clear "Waiting for data..." message before initializing plot
        const plotDiv = document.getElementById(plotDivId);
        if (plotDiv) {
            plotDiv.textContent = ''; // Clear the initial loading text
        }

        let xAxisRange = [1, numFiles];
        if (xAxisUnits === "Experiment Time") {
            // Initial time range will be 0 to (numFiles - 1) * SampleRate / 3600
            // For initialization, we can just set a placeholder or let Plotly autorange later
            xAxisRange = [0, (numFiles - 1) * (resizeInterval / 3600)]; // Placeholder, will be updated by actual data
        }

        // Define a set of distinct, saturated colors
        const colors = {
            lowFreqBefore: '#E6194B', // Vivid Red
            lowFreqAfter: '#F58231',  // Bright Orange
            highFreqBefore: '#4363d8', // Strong Blue
            highFreqAfter: '#42D4F4',  // Cyan
            kdmBefore: '#911EB4',     // Dark Purple
            kdmAfter: '#3CB44B',      // Vibrant Green
            // Using d3's categorical colors for 'otherFreq' to ensure distinctness
            otherFreqBase: [
                '#FABEBE', '#FFE119', '#BF360C', '#A9A9A9', '#800000',
                '#AA6E28', '#808000', '#F032E6', '#000075', '#F58231'
            ],
        };

        colors.otherFreqBefore = colors.otherFreqBase;
        colors.otherFreqAfter = colors.otherFreqBase.map(c => Plotly.d3.rgb(c).darker(1.5).toString());


        const initialTraces = [];
        traceNames.forEach((name, i) => {
            const freq = parseInt(name.split('Hz')[0]); // Extract frequency from trace name
            
            let beforeColor, afterColor;

            // Handle KDM trace names differently if they don't contain 'Hz'
            if (name === 'KDM') {
                beforeColor = colors.kdmBefore;
                afterColor = colors.kdmAfter;
            } else if (freq === kdmLowFreq) {
                beforeColor = colors.lowFreqBefore;
                afterColor = colors.lowFreqAfter;
            } else if (freq === kdmHighFreq) {
                beforeColor = colors.highFreqBefore;
                afterColor = colors.highFreqAfter;
            } else {
                // For other frequencies, use a neutral color or d3 scale
                const colorIndex = i % colors.otherFreqBefore.length;
                beforeColor = colors.otherFreqBefore[colorIndex];
                afterColor = colors.otherFreqAfter[colorIndex];
            }

            // Always push two traces: one for 'Before Inj.' and one for 'After Inj.'
            // Initially, both are empty. Data will be extended to the correct trace.
            initialTraces.push({
                x: [], y: [],
                mode: 'lines+markers',
                name: `${name} (Before Inj.)`,
                marker: { size: 6, color: beforeColor },
                line: { color: beforeColor }
            });
            initialTraces.push({
                x: [], y: [],
                mode: 'lines+markers',
                name: `${name} (After Inj.)`,
                marker: { size: 6, color: afterColor },
                line: { color: afterColor },
                showlegend: true
            });
        });


        const layout = {
            title: title,
            xaxis: { title: xAxisTitle, range: xAxisRange },
            yaxis: { title: yAxisTitle },
            margin: { t: 40, b: 40, l: 60, r: 20 },
            shapes: [], // Initialize shapes for injection line
            annotations: [] // Initialize annotations for injection text
        };

        Plotly.newPlot(plotDivId, initialTraces, layout);
    }

    /**
     * Renders all trend plots from scratch (used for real-time updates and re-normalization/full data refresh).
     * This function now handles splitting data by injection point and drawing the line.
     * @param {string} plotDivId - The ID of the plot div.
     * @param {Object} data - The trend data (e.g., peak_current_trends, normalized_peak_trends, kdm_trend).
     * @param {Array<string>} freqStrings - Frequencies as strings (e.g., ["15", "200"]).
     * @param {string} xAxisTitle - Title for the X-axis.
     * @param {string} yAxisTitle - Title for the Y-axis.
     * @param {number} numFiles - Total number of files for X-axis range.
     * @param {string} title - Plot title.
     * @param {string} trendType - "peak", "normalized", or "kdm"
     * @param {string} xAxisUnits - "File Number" or "Experiment Time".
     * @param {number} resizeInterval - Interval for dynamic X-axis resizing.
     * @param {number | null} kdmHighFreq - High KDM frequency for color differentiation.
     * @param {number | null} kdmLowFreq - Low KDM frequency for color differentiation.
     * @param {number | null} injectionPoint - File number where injection occurred (1-based).
     */
    static renderFullTrendPlot(plotDivId, data, freqStrings, xAxisTitle, yAxisTitle, numFiles, title, trendType, xAxisUnits, resizeInterval, kdmHighFreq = null, kdmLowFreq = null, injectionPoint = null) {
        document.getElementById(plotDivId).innerHTML = ''; // Clear existing plot

        let traces = [];
        let xData = data.x_axis_values;

        if (!xData || xData.length === 0) {
            console.warn(`No X-axis data available for plot ${plotDivId}. Skipping full render.`);
            document.getElementById(plotDivId).innerHTML = '<p class="text-gray-400">No data available to plot.</p>';
            return;
        }

        let xAxisRange = [xData[0], xData[xData.length - 1]] || [1, numFiles];
        if (xAxisUnits === "File Number") {
             xAxisRange = [1, numFiles];
        }

        const colors = {
            lowFreqBefore: '#E6194B', // Vivid Red
            lowFreqAfter: '#F58231',  // Bright Orange
            highFreqBefore: '#4363d8', // Strong Blue
            highFreqAfter: '#42D4F4',  // Cyan
            kdmBefore: '#911EB4',     // Dark Purple
            kdmAfter: '#3CB44B',      // Vibrant Green
            otherFreqBase: [
                '#FABEBE', '#FFE119', '#BF360C', '#A9A9A9', '#800000',
                '#AA6E28', '#808000', '#F032E6', '#000075', '#F58231'
            ],
        };

        colors.otherFreqBefore = colors.otherFreqBase;
        colors.otherFreqAfter = colors.otherFreqBase.map(c => Plotly.d3.rgb(c).darker(1.5).toString());


        // Helper function to get trace configurations based on injection point and frequency.
        const getTraceConfig = (yData, namePrefix, initialColor, injectedColor, injectIdx) => {
            const currentTraces = [];
            if (!yData || yData.length === 0) {
                return [];
            }

            if (injectIdx !== null && injectIdx >= 1 && injectIdx <= xData.length) {
                // Find the actual x-axis value for the injection point
                const injectionXValue = xData[injectIdx - 1]; // xData is 0-indexed, injectIdx is 1-based file number

                // Split data based on injectionXValue
                const xBefore = [];
                const yBefore = [];
                const xAfter = [];
                const yAfter = [];

                for (let i = 0; i < xData.length; i++) {
                    if (xData[i] < injectionXValue) {
                        xBefore.push(xData[i]);
                        yBefore.push(yData[i]);
                    } else {
                        // Include the injection point itself in both segments for continuity
                        if (xData[i-1] < injectionXValue && i > 0) { // Add previous point to "after" for line continuity
                            xAfter.push(xData[i-1]);
                            yAfter.push(yData[i-1]);
                        }
                        xAfter.push(xData[i]);
                        yAfter.push(yData[i]);
                    }
                }
                // Ensure the injection point is included in the "before" segment if it's the last point
                if (xBefore.length > 0 && xBefore[xBefore.length - 1] < injectionXValue && injectionXValue === xData[injectIdx - 1]) {
                     xBefore.push(xData[injectIdx - 1]);
                     yBefore.push(yData[injectIdx - 1]);
                }


                currentTraces.push({
                    x: xBefore, y: yBefore,
                    mode: 'lines+markers',
                    name: `${namePrefix} (Before Inj.)`,
                    marker: { size: 6, color: initialColor },
                    line: { color: initialColor }
                });
                currentTraces.push({
                    x: xAfter, y: yAfter,
                    mode: 'lines+markers',
                    name: `${namePrefix} (After Inj.)`,
                    marker: { size: 6, color: injectedColor },
                    line: { color: injectedColor },
                    showlegend: true
                });
            } else {
                // If no injection point or out of range, plot as a single trace
                currentTraces.push({
                    x: xData.slice(0, yData.length), y: yData,
                    mode: 'lines+markers',
                    name: namePrefix,
                    marker: { size: 6, color: initialColor },
                    line: { color: initialColor }
                });
            }
            return currentTraces;
        };


        let injectFileNumIdx = null; // This represents the file number as an index (1-based)
        if (injectionPoint !== null && injectionPoint >= 1 && injectionPoint <= numFiles) {
            injectFileNumIdx = injectionPoint;
        }


        if (trendType === "peak") {
            freqStrings.forEach((freqStr, i) => {
                const freq = parseInt(freqStr);
                const yData = data.peak_current_trends[freqStr] || [];

                let initialColor;
                let injectedColor;

                if (freq === kdmLowFreq) {
                    initialColor = colors.lowFreqBefore;
                    injectedColor = colors.lowFreqAfter;
                } else if (freq === kdmHighFreq) {
                    initialColor = colors.highFreqBefore;
                    injectedColor = colors.highFreqAfter;
                } else {
                    const colorIndex = i % colors.otherFreqBefore.length;
                    initialColor = colors.otherFreqBefore[colorIndex];
                    injectedColor = colors.otherFreqAfter[colorIndex];
                }

                traces = traces.concat(getTraceConfig(yData, `${freqStr}Hz`, initialColor, injectedColor, injectFileNumIdx));
            });
        } else if (trendType === "normalized") {
            freqStrings.forEach((freqStr, i) => {
                const freq = parseInt(freqStr);
                const yData = data.normalized_peak_trends[freqStr] || [];

                let initialColor;
                let injectedColor;

                if (freq === kdmLowFreq) {
                    initialColor = colors.lowFreqBefore;
                    injectedColor = colors.lowFreqAfter;
                } else if (freq === kdmHighFreq) {
                    initialColor = colors.highFreqBefore;
                    injectedColor = colors.highFreqAfter;
                } else {
                    const colorIndex = i % colors.otherFreqBefore.length;
                    initialColor = colors.otherFreqBefore[colorIndex];
                    injectedColor = colors.otherFreqAfter[colorIndex];
                }

                traces = traces.concat(getTraceConfig(yData, `${freqStr}Hz`, initialColor, injectedColor, injectFileNumIdx));
            });
        } else if (trendType === "kdm" && kdmHighFreq !== null && kdmLowFreq !== null) {
            const yData = data.kdm_trend || [];
            // KDM trend itself doesn't have high/low freq, but its color can differentiate pre/post injection
            traces = traces.concat(getTraceConfig(yData, 'KDM', colors.kdmBefore, colors.kdmAfter, injectFileNumIdx));
        }

        const layout = {
            title: title,
            xaxis: { title: xAxisTitle, range: xAxisRange },
            yaxis: { title: yAxisTitle },
            margin: { t: 40, b: 40, l: 60, r: 20 },
            shapes: [],
            annotations: []
        };

        // Add vertical line and annotation for injection point if specified and valid
        if (injectFileNumIdx !== null && injectFileNumIdx >= 1 && injectFileNumIdx <= xData.length) {
            let xInjectionPoint = null;
            if (xAxisUnits === "File Number") {
                xInjectionPoint = injectFileNumIdx;
            } else if (xAxisUnits === "Experiment Time" && xData.length > (injectFileNumIdx - 1) && xData[injectFileNumIdx - 1] !== undefined && xData[injectFileNumIdx - 1] !== null) {
                xInjectionPoint = xData[injectFileNumIdx - 1];
            }

            if (xInjectionPoint !== null) {
                layout.shapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'paper',
                    x0: xInjectionPoint,
                    y0: 0,
                    x1: xInjectionPoint,
                    y1: 1,
                    line: {
                        color: 'grey',
                        width: 2,
                        dash: 'dot'
                    }
                });
                layout.annotations.push({
                    xref: 'x',
                    yref: 'paper',
                    x: xInjectionPoint,
                    y: 1.05, // Position above the plot
                    text: 'Injection',
                    showarrow: false,
                    font: {
                        color: 'grey',
                        size: 10
                    }
                });
            }
        }

        Plotly.newPlot(plotDivId, traces, layout);
    }
}