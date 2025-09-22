# data_processing/swv_analyzer.py

import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import median_abs_deviation
import logging

# Import the new data_reader
from .data_reader import ReadData

logger = logging.getLogger(__name__)


# --- Main analysis function ---

def hampel_filter(data, window_size, threshold=3.0):
    """
    Applies Hampel filter to remove outliers

    Args:
        data: Input signal
        window_size: Window size for median calculation (should be odd)
        threshold: Number of MADs for outlier detection

    Returns:
        Filtered data
    """
    if window_size % 2 == 0:
        window_size += 1

    filtered_data = data.copy()
    half_window = window_size // 2

    for i in range(len(data)):
        start_idx = max(0, i - half_window)
        end_idx = min(len(data), i + half_window + 1)
        window = data[start_idx:end_idx]

        median = np.median(window)
        mad = median_abs_deviation(window, scale='normal')

        if mad == 0:
            mad = 1e-10  # Avoid division by zero

        if abs(data[i] - median) > threshold * mad:
            filtered_data[i] = median

    return filtered_data


def calculate_fwhm(potentials, currents):
    """
    Calculate Full Width at Half Maximum (FWHM) of the peak

    Args:
        potentials: Voltage values
        currents: Current values

    Returns:
        FWHM in voltage units
    """
    if len(currents) < 3:
        return None

    # Find peak
    peak_idx = np.argmax(currents)
    peak_current = currents[peak_idx]
    half_max = peak_current / 2

    # Find left and right half-maximum points
    left_idx = None
    right_idx = None

    # Search left side
    for i in range(peak_idx, -1, -1):
        if currents[i] <= half_max:
            left_idx = i
            break

    # Search right side
    for i in range(peak_idx, len(currents)):
        if currents[i] <= half_max:
            right_idx = i
            break

    if left_idx is not None and right_idx is not None:
        return abs(potentials[right_idx] - potentials[left_idx])

    return None


def calculate_snr(original_data, filtered_data):
    """
    Calculate Signal-to-Noise Ratio improvement

    Args:
        original_data: Original signal
        filtered_data: Filtered signal

    Returns:
        SNR improvement ratio
    """
    original_noise = np.std(np.diff(original_data))
    filtered_noise = np.std(np.diff(filtered_data))

    if original_noise == 0 or filtered_noise == 0:
        return 1.0

    return original_noise / filtered_noise


def calculate_peak_retention(original_data, filtered_data):
    """
    Calculate peak retention ratio

    Args:
        original_data: Original signal
        filtered_data: Filtered signal

    Returns:
        Peak retention ratio (0-1)
    """
    original_peak = np.max(original_data)
    filtered_peak = np.max(filtered_data)

    if original_peak == 0:
        return 1.0

    return filtered_peak / original_peak


def calculate_residual_analysis(original_data, filtered_data):
    """
    Calculate residual analysis metrics

    Args:
        original_data: Original signal
        filtered_data: Filtered signal

    Returns:
        Normalized residual standard deviation
    """
    residuals = np.array(original_data) - np.array(filtered_data)
    residual_std = np.std(residuals)
    signal_range = np.max(original_data) - np.min(original_data)

    if signal_range == 0:
        return 0.0

    return residual_std / signal_range


def evaluate_qc_metrics(snr_improvement, peak_retention, residual_metric):
    """
    Evaluate QC metrics and assign pass/warning/fail status

    Args:
        snr_improvement: SNR improvement ratio
        peak_retention: Peak retention ratio
        residual_metric: Normalized residual metric

    Returns:
        QC status: 'pass', 'warning', or 'fail'
    """
    # Define thresholds
    snr_threshold_good = 1.2
    snr_threshold_warning = 1.05
    peak_retention_threshold_good = 0.95
    peak_retention_threshold_warning = 0.90
    residual_threshold_good = 0.1
    residual_threshold_warning = 0.2

    # Count metrics that meet criteria
    good_metrics = 0
    warning_metrics = 0

    if snr_improvement >= snr_threshold_good:
        good_metrics += 1
    elif snr_improvement >= snr_threshold_warning:
        warning_metrics += 1

    if peak_retention >= peak_retention_threshold_good:
        good_metrics += 1
    elif peak_retention >= peak_retention_threshold_warning:
        warning_metrics += 1

    if residual_metric <= residual_threshold_good:
        good_metrics += 1
    elif residual_metric <= residual_threshold_warning:
        warning_metrics += 1

    # Determine overall status
    if good_metrics >= 2:
        return 'pass'
    elif good_metrics + warning_metrics >= 2:
        return 'warning'
    else:
        return 'fail'


def analyze_swv_data(file_path, analysis_params, selected_electrode=None):
    """
    Analyzes a single SWV data file based on provided parameters.
    Implements a robust tangent-based baseline correction using a convex hull approach.

    Args:
        selected_electrode: Index of specific electrode to analyze (0-based).
                          If None, uses original averaging behavior.
    """
    delimiter_map = {1: " ", 2: "\t", 3: ","}
    delimiter_char = delimiter_map.get(analysis_params.get('delimiter', 1), " ")

    # Handle single electrode analysis or original averaging
    if selected_electrode is not None:
        # Single electrode analysis
        electrodes_data = ReadData(
            myfile=file_path,
            voltage_column_index=analysis_params['voltage_column'] - 1,
            current_column_start_index=analysis_params['current_column'] - 1,
            spacing_index=analysis_params['spacing_index'],
            num_electrodes=analysis_params['num_electrodes'],
            delimiter_char=delimiter_char,
            file_extension=analysis_params.get('file_extension', '.txt'),
            selected_electrodes=[selected_electrode]
        )

        # Check electrode validation
        detected_electrodes = electrodes_data.get('detected_electrodes', 0)
        if selected_electrode >= detected_electrodes:
            return {"status": "error",
                   "message": f"Electrode validation failed: File contains {detected_electrodes} electrodes, but electrode {selected_electrode + 1} was requested.",
                   "detected_electrodes": detected_electrodes,
                   "requested_electrode": selected_electrode + 1}

        if selected_electrode in electrodes_data:
            electrode_data = electrodes_data[selected_electrode]
            potentials = electrode_data['potentials']
            currents = electrode_data['currents']
        else:
            potentials, currents = [], []
    else:
        # Original averaging behavior
        data_result = ReadData(
            myfile=file_path,
            voltage_column_index=analysis_params['voltage_column'] - 1,
            current_column_start_index=analysis_params['current_column'] - 1,
            spacing_index=analysis_params['spacing_index'],
            num_electrodes=analysis_params['num_electrodes'],
            delimiter_char=delimiter_char,
            file_extension=analysis_params.get('file_extension', '.txt')
        )
        potentials = data_result['voltage']
        currents = data_result['current']

    if not potentials or not currents:
        return {"status": "warning", "message": "No valid data found.", "warning_type": "no_data", "potentials": [],
                "raw_currents": [], "smoothed_currents": [], "regression_line": [], "adjusted_potentials": [],
                "peak_value": 0, "normalized_currents_data": [], "auc_vertices": []}

    min_potential, max_potential = min(potentials), max(potentials)
    current_freq = analysis_params['frequency']

    if current_freq > analysis_params['cutoff_frequency']:
        xstart_val = analysis_params['high_xstart'] if analysis_params['high_xstart'] is not None else max_potential
        xend_val = analysis_params['high_xend'] if analysis_params['high_xend'] is not None else min_potential
    else:
        xstart_val = analysis_params['low_xstart'] if analysis_params['low_xstart'] is not None else max_potential
        xend_val = analysis_params['low_xend'] if analysis_params['low_xend'] is not None else min_potential

    # Ensure data is sorted by potential for convex hull algorithm
    data_pairs = sorted(zip(potentials, currents), key=lambda p: p[0])
    sorted_potentials = [p for p, c in data_pairs]
    sorted_currents = [c for p, c in data_pairs]

    # Apply potential range filtering on sorted data
    range_indices = [i for i, p in enumerate(sorted_potentials) if
                     min(xend_val, xstart_val) <= p <= max(xend_val, xstart_val)]
    if not range_indices:
        return {"status": "warning", "message": "No data in specified potential range.",
                "warning_type": "no_data_in_range", "potentials": [], "raw_currents": [], "smoothed_currents": [],
                "regression_line": [], "adjusted_potentials": [], "peak_value": 0, "normalized_currents_data": [],
                "auc_vertices": []}

    # adjusted_potentials and adjusted_currents are now guaranteed to be sorted by potential
    adjusted_potentials = [sorted_potentials[i] for i in range_indices]
    adjusted_currents = [sorted_currents[i] for i in range_indices]

    # Calculate FWHM for automatic parameter estimation
    fwhm = calculate_fwhm(adjusted_potentials, adjusted_currents)

    # Get filter mode and parameters
    filter_mode = analysis_params.get('filter_mode', 'auto')

    if filter_mode == 'auto':
        # Automatic mode: Calculate parameters based on FWHM or data length
        if fwhm is not None:
            # Calculate voltage step size
            voltage_range = max(adjusted_potentials) - min(adjusted_potentials)
            voltage_step = voltage_range / len(adjusted_potentials) if len(adjusted_potentials) > 1 else 0.01

            # Calculate window sizes based on FWHM
            hampel_window_points = max(3, int(fwhm / (10 * voltage_step))) if voltage_step > 0 else 5
            sg_window_points = max(3, int(fwhm / (3 * voltage_step))) if voltage_step > 0 else 15
        else:
            # Fallback to data length based calculation
            hampel_window_points = max(3, int(len(adjusted_currents) * 0.1))
            sg_window_points = max(3, int(len(adjusted_currents) * 0.2))

        # Ensure odd window sizes and reasonable limits
        hampel_window_size = min(hampel_window_points if hampel_window_points % 2 == 1 else hampel_window_points + 1, len(adjusted_currents) // 3)
        hampel_threshold = 3.0  # 3 times MAD
        sg_window = min(sg_window_points if sg_window_points % 2 == 1 else sg_window_points + 1, len(adjusted_currents) // 2)
        sg_degree = 2
    else:
        # Manual mode: Use provided parameters
        hampel_window_size = analysis_params.get('hampel_window', 5)
        hampel_threshold = analysis_params.get('hampel_threshold', 3.0)
        sg_window = analysis_params.get('sg_window', 5)
        sg_degree = analysis_params.get('sg_degree', 2)

    # Ensure odd window sizes
    if hampel_window_size % 2 == 0:
        hampel_window_size += 1
    if sg_window % 2 == 0:
        sg_window += 1

    # Validate window sizes
    min_effective_sg_window = max(3, sg_degree + 1)
    if sg_window <= sg_degree:
        sg_window = sg_degree + 2 if (sg_degree + 2) % 2 != 0 else sg_degree + 3
    if sg_window < min_effective_sg_window:
        sg_window = min_effective_sg_window
    if sg_window > len(adjusted_currents):
        sg_window = len(adjusted_currents) if len(adjusted_currents) % 2 != 0 else len(adjusted_currents) - 1
    if sg_window < min_effective_sg_window:
        sg_window = min_effective_sg_window

    if hampel_window_size > len(adjusted_currents):
        hampel_window_size = len(adjusted_currents) if len(adjusted_currents) % 2 != 0 else len(adjusted_currents) - 1

    if sg_window <= sg_degree or sg_window > len(adjusted_currents):
        return {"status": "error", "message": f"SG filter failed: Data too short for settings.",
                "potentials": potentials, "raw_currents": currents, "smoothed_currents": [], "regression_line": [],
                "adjusted_potentials": [], "peak_value": 0, "normalized_currents_data": [], "auc_vertices": [],
                "filter_params": {}, "qc_metrics": {}}

    try:
        # Apply Hampel filter first
        adjusted_currents_array = np.array(adjusted_currents)
        hampel_filtered = hampel_filter(adjusted_currents_array, hampel_window_size, hampel_threshold)

        # Then apply Savitzky-Golay filter
        adjusted_smoothed_currents = savgol_filter(hampel_filtered, sg_window, sg_degree).tolist()

        # Calculate QC metrics
        snr_improvement = calculate_snr(adjusted_currents, adjusted_smoothed_currents)
        peak_retention = calculate_peak_retention(adjusted_currents, adjusted_smoothed_currents)
        residual_metric = calculate_residual_analysis(adjusted_currents, adjusted_smoothed_currents)
        qc_status = evaluate_qc_metrics(snr_improvement, peak_retention, residual_metric)

        # Store filter parameters and QC metrics
        filter_params = {
            'filter_mode': filter_mode,
            'hampel_window': hampel_window_size,
            'hampel_threshold': hampel_threshold,
            'sg_window': sg_window,
            'sg_degree': sg_degree,
            'fwhm': fwhm
        }

        qc_metrics = {
            'snr_improvement': snr_improvement,
            'peak_retention': peak_retention,
            'residual_metric': residual_metric,
            'qc_status': qc_status
        }

    except ValueError as e:
        return {"status": "error", "message": f"Filter failed: {e}.", "potentials": potentials,
                "raw_currents": currents, "smoothed_currents": [], "regression_line": [], "adjusted_potentials": [],
                "peak_value": 0, "normalized_currents_data": [], "auc_vertices": [], "filter_params": {}, "qc_metrics": {}}

    # Reconstruct the full smoothed curve for plotting if needed
    full_smoothed_currents = list(currents)  # Start with a copy
    # This part is complex if we need to map back. For now, let's focus on the analysis logic.
    # The UI plots adjusted_potentials vs adjusted_smoothed_currents anyway for the individual plot.

    eval_regress = []
    peak_value = 0
    auc_vertices = []
    baseline_warning_type = None
    V_left_baseline, I_left_baseline, V_right_baseline, I_right_baseline = None, None, None, None

    if analysis_params['SelectedOptions'] == "Peak Height Extraction":
        if len(adjusted_potentials) > 2:
            # Peak finding must be done on smoothed data
            first_derivative = np.gradient(np.array(adjusted_smoothed_currents), np.array(adjusted_potentials))
            peak_candidates = []

            # Since data is sorted by potential, scan direction is always increasing
            for i in range(1, len(first_derivative)):
                if first_derivative[i - 1] > 0 and first_derivative[i] <= 0:
                    peak_candidates.append((adjusted_smoothed_currents[i], adjusted_potentials[i], i))

            if peak_candidates:
                original_peak_current, peak_potential, peak_index = max(peak_candidates, key=lambda x: x[0])

                # --- Convex Hull Based Tangent Algorithm ---
                points = list(zip(adjusted_potentials, adjusted_smoothed_currents))

                # Andrew's monotone chain algorithm to find the lower convex hull
                def cross_product(p1, p2, p3):
                    return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

                lower_hull = []
                for p in points:
                    while len(lower_hull) >= 2 and cross_product(lower_hull[-2], lower_hull[-1], p) <= 0:
                        lower_hull.pop()
                    lower_hull.append(p)

                # Find the baseline edge on the hull that spans the peak
                baseline_edge_found = False
                for i in range(len(lower_hull) - 1):
                    p_left = lower_hull[i]
                    p_right = lower_hull[i + 1]

                    # Find original indices
                    idx_left = adjusted_potentials.index(p_left[0])
                    idx_right = adjusted_potentials.index(p_right[0])

                    if idx_left <= peak_index < idx_right:
                        V_left_baseline, I_left_baseline = p_left
                        V_right_baseline, I_right_baseline = p_right
                        baseline_edge_found = True
                        break

                if not baseline_edge_found:
                    # Fallback if peak is outside the main hull segment (e.g., at the very edge)
                    baseline_warning_type = "peak_outside_hull_fallback"
                    min_idx = np.argmin(adjusted_smoothed_currents)
                    V_left_baseline = V_right_baseline = adjusted_potentials[min_idx]
                    I_left_baseline = I_right_baseline = adjusted_smoothed_currents[min_idx]

                # --- Apply chosen baseline ---
                if V_left_baseline is not None:
                    if V_left_baseline != V_right_baseline:
                        m = (I_right_baseline - I_left_baseline) / (V_right_baseline - V_left_baseline)
                        b_line = I_left_baseline - m * V_left_baseline
                    else:
                        m, b_line = 0, I_left_baseline
                    baseline_at_peak = m * peak_potential + b_line
                    peak_value = original_peak_current - baseline_at_peak
                    eval_regress = [m * p + b_line for p in adjusted_potentials]
                else:
                    peak_value = None
                    baseline_warning_type = "internal_baseline_error"
            else:
                peak_value = None
                baseline_warning_type = "no_derivative_peak"
        else:
            peak_value = None
            baseline_warning_type = "insufficient_points_for_derivative"

    elif analysis_params['SelectedOptions'] == "Area Under the Curve":
        # This section would need a baseline to subtract from.
        # We can run the same baseline logic as above to get eval_regress.
        # For simplicity, let's assume it needs a simple polynomial baseline for now.
        polyfit_deg = analysis_params['polyfit_deg']
        effective_polyfit_deg = polyfit_deg if len(adjusted_potentials) > polyfit_deg else max(1,
                                                                                               len(adjusted_potentials) - 1)
        polynomial_coeffs = np.polyfit(adjusted_potentials, adjusted_smoothed_currents, effective_polyfit_deg).tolist()
        eval_regress = np.polyval(polynomial_coeffs, adjusted_potentials).tolist()

        if adjusted_smoothed_currents and adjusted_potentials:
            diff_currents = [Y - B for Y, B in zip(adjusted_smoothed_currents, eval_regress)]
            peak_value = np.trapz([abs(d) for d in diff_currents], adjusted_potentials)
            auc_currents_shifted = [max(0, d) for d in diff_currents]
            auc_vertices = list(zip(adjusted_potentials, auc_currents_shifted))
            auc_vertices.extend(list(zip(reversed(adjusted_potentials), [0] * len(adjusted_potentials))))
        else:
            peak_value = 0

    # For plotting, we return the adjusted (ranged and sorted) data
    # The full smoothed curve isn't easily reconstructed without more complex mapping,
    # but the UI primarily uses the adjusted data for the individual plot.

    status = "success"
    message = "Analysis successful."
    if baseline_warning_type == "no_derivative_peak":
        status = "warning"
        message = "No clear derivative peak found. Experiment might have issues."
    elif baseline_warning_type:
        message += f" (Note: {baseline_warning_type})"

    return {
        "status": status, "message": message, "warning_type": baseline_warning_type,
        "potentials": adjusted_potentials,  # Return sorted, ranged data
        "raw_currents": adjusted_currents,  # Return sorted, ranged data
        "smoothed_currents": adjusted_smoothed_currents,  # Return sorted, ranged, smoothed data
        "regression_line": eval_regress,
        "adjusted_potentials": adjusted_potentials,  # This is somewhat redundant, but kept for consistency
        "peak_value": peak_value,
        "auc_vertices": auc_vertices,
        "filter_params": filter_params if 'filter_params' in locals() else {},
        "qc_metrics": qc_metrics if 'qc_metrics' in locals() else {}
    }