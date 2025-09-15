// static/js/plot_utils.js (Final version with injection point fix)

export class PlotlyPlotter {
    static plotIndividualData(plotDivId, potentials, rawCurrents, smoothedCurrents, regressionLine, adjustedPotentials, aucVertices, selectedOptions) {
        const traces = [];

        traces.push({
            x: potentials, y: rawCurrents, mode: 'lines',
            name: 'Raw Current', line: {color: 'blue'}
        });

        traces.push({
            x: potentials, y: smoothedCurrents, mode: 'lines',
            name: 'Smoothed Current', line: {color: 'red', width: 2}
        });

        if (regressionLine && adjustedPotentials) {
            traces.push({
                x: adjustedPotentials, y: regressionLine, mode: 'lines',
                name: 'Regression Line', line: {color: 'green', dash: 'dash', width: 1}
            });
        }

        if (selectedOptions === "Area Under the Curve" && aucVertices && aucVertices.length > 0) {
            const shapeX = aucVertices.map(v => v[0]);
            const shapeY = aucVertices.map(v => v[1]);
            traces.push({
                x: shapeX, y: shapeY, fill: 'toself',
                fillcolor: 'rgba(0,100,80,0.2)', mode: 'lines',
                line: {color: 'transparent'}, name: 'AUC Area',
                hoverinfo: 'none'
            });
        }

        const layout = {
            title: '', autosize: true,
            xaxis: { title: 'Potential (V)', autorange: true, tickangle: -45, tickfont: { size: 10 } },
            yaxis: { title: 'Current (µA)', autorange: true, rangemode: 'normal' },
            legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'center', x: 0.5, font: { size: 10 } },
            margin: { t: 50, b: 50, l: 60, r: 20 }
        };

        Plotly.newPlot(plotDivId, traces, layout);
        const plotDiv = document.getElementById(plotDivId);
        if (plotDiv && plotDiv.textContent.includes('Waiting for data...')) {
            plotDiv.textContent = '';
        }
    }

    static renderFullTrendPlot(plotDivId, data, freqStrings, xAxisTitle, yAxisTitle, numFiles, title, trendType, xAxisUnits, resizeInterval, kdmHighFreq = null, kdmLowFreq = null, injectionPoint = null) {
        document.getElementById(plotDivId).innerHTML = ''; 
        
        let traces = [];
        let xData = data.x_axis_values;

        if (!xData || xData.length === 0) {
            document.getElementById(plotDivId).innerHTML = '<p class="text-gray-400">No data available to plot.</p>';
            return;
        }

        const colors = {
            lowFreqBefore: '#E6194B', highFreqBefore: '#4363d8', kdmBefore: '#911EB4',
            lowFreqAfter: '#F58231', highFreqAfter: '#42D4F4', kdmAfter: '#3CB44B',
            otherFreqBase: ['#FABEBE', '#FFE119', '#BF360C', '#A9A9A9', '#800000', '#AA6E28', '#808000', '#F032E6', '#000075', '#F58231']
        };
        colors.otherFreqAfter = colors.otherFreqBase.map(c => Plotly.d3.rgb(c).darker(1.5).toString());
        
        const getTraceConfig = (yData, namePrefix, initialColor, injectedColor, injectIdx) => {
            const currentTraces = [];
            if (!yData || yData.length === 0) return [];
            
            if (injectIdx !== null && injectIdx >= 1 && injectIdx <= xData.length) {
                const xBefore = [], yBefore = [], xAfter = [], yAfter = [];
                
                // Correctly split the data
                for (let i = 0; i < xData.length; i++) {
                    const xValue = xData[i];
                    // "Before" trace includes all points UP TO AND INCLUDING the injection point
                    if (xValue <= injectIdx) {
                        xBefore.push(xValue);
                        yBefore.push(yData[i]);
                    }
                    // "After" trace includes all points FROM the injection point ONWARD
                    if (xValue >= injectIdx) {
                        xAfter.push(xValue);
                        yAfter.push(yData[i]);
                    }
                }
                
                if (xBefore.length > 0) {
                    currentTraces.push({ x: xBefore, y: yBefore, mode: 'lines+markers', name: `${namePrefix} (Before Inj.)`, marker: { size: 6, color: initialColor }, line: { color: initialColor } });
                }
                if (xAfter.length > 0) {
                    currentTraces.push({ x: xAfter, y: yAfter, mode: 'lines+markers', name: `${namePrefix} (After Inj.)`, marker: { size: 6, color: injectedColor }, line: { color: injectedColor } });
                }

            } else {
                currentTraces.push({ x: xData.slice(0, yData.length), y: yData, mode: 'lines+markers', name: namePrefix, marker: { size: 6, color: initialColor }, line: { color: initialColor } });
            }
            return currentTraces;
        };
        
        let injectFileNumIdx = (injectionPoint !== null && injectionPoint >= 1) ? injectionPoint : null;

        if (trendType === "peak" || trendType === "normalized") {
            const trendKey = trendType === "peak" ? "peak_current_trends" : "normalized_peak_trends";
            freqStrings.forEach((freqStr, i) => {
                const freq = parseInt(freqStr);
                const yData = data[trendKey][freqStr] || [];
                let initialColor, injectedColor;
                if (freq === kdmLowFreq) { initialColor = colors.lowFreqBefore; injectedColor = colors.lowFreqAfter; } 
                else if (freq === kdmHighFreq) { initialColor = colors.highFreqBefore; injectedColor = colors.highFreqAfter; } 
                else { const colorIndex = i % colors.otherFreqBase.length; initialColor = colors.otherFreqBase[colorIndex]; injectedColor = colors.otherFreqAfter[colorIndex]; }
                traces = traces.concat(getTraceConfig(yData, `${freqStr}Hz`, initialColor, injectedColor, injectFileNumIdx));
            });
        } else if (trendType === "kdm") {
            const yData = data.kdm_trend || [];
            traces = traces.concat(getTraceConfig(yData, 'KDM', colors.kdmBefore, colors.kdmAfter, injectFileNumIdx));
        }

        const layout = { 
            title: title, 
            xaxis: { title: xAxisTitle, range: [1, numFiles] }, 
            yaxis: { title: yAxisTitle, autorange: true }, 
            margin: { t: 40, b: 40, l: 60, r: 20 }, 
            shapes: [], 
            annotations: [] 
        };

        if (injectFileNumIdx !== null) {
             layout.shapes.push({
                type: 'line', xref: 'x', yref: 'paper', x0: injectFileNumIdx, y0: 0, x1: injectFileNumIdx, y1: 1,
                line: { color: 'grey', width: 2, dash: 'dot' }
            });
            layout.annotations.push({
                xref: 'x', yref: 'paper', x: injectFileNumIdx, y: 1.05, text: 'Injection', showarrow: false,
                font: { color: 'grey', size: 10 }
            });
        }
        
        Plotly.newPlot(plotDivId, traces, layout);
    }
}

