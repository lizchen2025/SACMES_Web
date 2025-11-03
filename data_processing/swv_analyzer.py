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
    original_peak = np.max(np.abs(original_data))  # Use absolute max to handle negative peaks
    filtered_peak = np.max(np.abs(filtered_data))

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


def convert_units(value, from_unit, to_unit='base'):
    """
    Convert units for voltage and current measurements.

    Args:
        value: Numeric value to convert
        from_unit: Source unit (V, mV, μV, nV, A, mA, μA, nA)
        to_unit: Target unit ('base' for V/A, or specific unit)

    Returns:
        Converted value
    """
    # Voltage units to base (V)
    voltage_factors = {
        'V': 1.0,
        'mV': 1e-3,
        'μV': 1e-6,
        'uV': 1e-6,  # Alternative spelling
        'nV': 1e-9
    }

    # Current units to base (A)
    current_factors = {
        'A': 1.0,
        'mA': 1e-3,
        'μA': 1e-6,
        'uA': 1e-6,  # Alternative spelling
        'nA': 1e-9
    }

    # Get conversion factor
    factors = {**voltage_factors, **current_factors}
    factor = factors.get(from_unit, 1.0)

    if to_unit == 'base':
        return value * factor
    else:
        to_factor = factors.get(to_unit, 1.0)
        return value * factor / to_factor


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

    # Apply unit conversions if specified
    voltage_units = analysis_params.get('voltage_units', 'V')
    current_units = analysis_params.get('current_units', 'A')

    # Convert to base units (V and A) for internal calculations
    if voltage_units != 'V':
        potentials = [convert_units(v, voltage_units, 'base') for v in potentials]
    if current_units != 'A':
        currents = [convert_units(c, current_units, 'base') for c in currents]

    min_potential, max_potential = min(potentials), max(potentials)
    current_freq = analysis_params['frequency']
    cutoff_frequency = analysis_params.get('cutoff_frequency', 500)  # Default to 500 Hz if not provided

    if current_freq > cutoff_frequency:
        xstart_val = analysis_params['high_xstart'] if analysis_params['high_xstart'] is not None else max_potential
        xend_val = analysis_params['high_xend'] if analysis_params['high_xend'] is not None else min_potential
    else:
        xstart_val = analysis_params['low_xstart'] if analysis_params['low_xstart'] is not None else max_potential
        xend_val = analysis_params['low_xend'] if analysis_params['low_xend'] is not None else min_potential

    # Ensure data is sorted by potential for convex hull algorithm
    data_pairs = sorted(zip(potentials, currents), key=lambda p: p[0])
    sorted_potentials = [p for p, c in data_pairs]
    sorted_currents = [c for p, c in data_pairs]

    # Apply peak detection range filtering if specified (user-defined range for excluding noise peaks)
    peak_min_voltage = analysis_params.get('peak_min_voltage')
    peak_max_voltage = analysis_params.get('peak_max_voltage')

    logger.info(f"Voltage range parameters: peak_min={peak_min_voltage}, peak_max={peak_max_voltage}, xstart={xstart_val}, xend={xend_val}")

    # Convert peak range limits to base units if specified
    if peak_min_voltage is not None and voltage_units != 'V':
        peak_min_voltage = convert_units(peak_min_voltage, voltage_units, 'base')
    if peak_max_voltage is not None and voltage_units != 'V':
        peak_max_voltage = convert_units(peak_max_voltage, voltage_units, 'base')

    # Apply potential range filtering on sorted data
    # First apply the original scanning range
    range_indices = [i for i, p in enumerate(sorted_potentials) if
                     min(xend_val, xstart_val) <= p <= max(xend_val, xstart_val)]

    logger.info(f"After xstart/xend filtering: {len(range_indices)}/{len(sorted_potentials)} points remain")

    # Then apply user-defined peak detection range if specified
    if peak_min_voltage is not None or peak_max_voltage is not None:
        peak_range_indices = []
        for i in range_indices:
            p = sorted_potentials[i]
            if peak_min_voltage is not None and p < peak_min_voltage:
                continue
            if peak_max_voltage is not None and p > peak_max_voltage:
                continue
            peak_range_indices.append(i)
        logger.info(f"After peak detection range filtering: {len(peak_range_indices)}/{len(range_indices)} points remain")
        logger.info(f"Voltage range of filtered data: [{min([sorted_potentials[i] for i in peak_range_indices]):.4f}, {max([sorted_potentials[i] for i in peak_range_indices]):.4f}]V")
        range_indices = peak_range_indices

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

    # Get filter modes and parameters
    hampel_mode = analysis_params.get('hampel_mode', 'disabled')
    sg_mode = analysis_params.get('sg_mode', 'auto')

    # Handle Hampel filter parameters
    if hampel_mode == 'auto':
        # Auto Hampel: Calculate parameters based on FWHM or data length
        if fwhm is not None:
            voltage_range = max(adjusted_potentials) - min(adjusted_potentials)
            voltage_step = voltage_range / len(adjusted_potentials) if len(adjusted_potentials) > 1 else 0.01
            hampel_window_points = max(3, int(fwhm / (10 * voltage_step))) if voltage_step > 0 else 5
        else:
            hampel_window_points = max(3, int(len(adjusted_currents) * 0.1))

        hampel_window_size = min(hampel_window_points if hampel_window_points % 2 == 1 else hampel_window_points + 1, len(adjusted_currents) // 3)
        hampel_threshold = 3.0  # 3 times MAD
    elif hampel_mode == 'manual':
        # Manual Hampel: Use provided parameters
        hampel_window_size = analysis_params.get('hampel_window', 5)
        hampel_threshold = analysis_params.get('hampel_threshold', 3.0)
    else:
        # Disabled Hampel: Set to None
        hampel_window_size = None
        hampel_threshold = None

    # Handle SG filter parameters
    if sg_mode == 'auto':
        # Auto SG: Calculate parameters based on FWHM or data length
        if fwhm is not None:
            voltage_range = max(adjusted_potentials) - min(adjusted_potentials)
            voltage_step = voltage_range / len(adjusted_potentials) if len(adjusted_potentials) > 1 else 0.01
            sg_window_points = max(3, int(fwhm / (3 * voltage_step))) if voltage_step > 0 else 15
        else:
            sg_window_points = max(3, int(len(adjusted_currents) * 0.2))

        sg_window = min(sg_window_points if sg_window_points % 2 == 1 else sg_window_points + 1, len(adjusted_currents) // 2)
        sg_degree = 2
    elif sg_mode == 'manual':
        # Manual SG: Use provided parameters
        sg_window = analysis_params.get('sg_window', 5)
        sg_degree = analysis_params.get('sg_degree', 2)
    else:
        # Disabled SG: Set to None
        sg_window = None
        sg_degree = None

    # Validate and adjust window sizes only if filters are enabled
    if hampel_window_size is not None:
        if hampel_window_size % 2 == 0:
            hampel_window_size += 1
        if hampel_window_size > len(adjusted_currents):
            hampel_window_size = len(adjusted_currents) if len(adjusted_currents) % 2 != 0 else len(adjusted_currents) - 1

    if sg_window is not None:
        if sg_window % 2 == 0:
            sg_window += 1

        min_effective_sg_window = max(3, sg_degree + 1)
        if sg_window <= sg_degree:
            sg_window = sg_degree + 2 if (sg_degree + 2) % 2 != 0 else sg_degree + 3
        if sg_window < min_effective_sg_window:
            sg_window = min_effective_sg_window
        if sg_window > len(adjusted_currents):
            sg_window = len(adjusted_currents) if len(adjusted_currents) % 2 != 0 else len(adjusted_currents) - 1
        if sg_window < min_effective_sg_window:
            sg_window = min_effective_sg_window

        if sg_window <= sg_degree or sg_window > len(adjusted_currents):
            return {"status": "error", "message": f"SG filter failed: Data too short for settings.",
                    "potentials": potentials, "raw_currents": currents, "smoothed_currents": [], "regression_line": [],
                    "adjusted_potentials": [], "peak_value": 0, "normalized_currents_data": [], "auc_vertices": [],
                    "filter_params": {}, "qc_metrics": {}}

    try:
        # Apply filters sequentially based on enabled modes
        adjusted_currents_array = np.array(adjusted_currents)

        # Apply Hampel filter if enabled
        if hampel_window_size is not None:
            hampel_filtered = hampel_filter(adjusted_currents_array, hampel_window_size, hampel_threshold)
        else:
            hampel_filtered = adjusted_currents_array

        # Apply Savitzky-Golay filter if enabled
        if sg_window is not None:
            adjusted_smoothed_currents = savgol_filter(hampel_filtered, sg_window, sg_degree).tolist()
        else:
            adjusted_smoothed_currents = hampel_filtered.tolist()

        # Calculate QC metrics
        snr_improvement = calculate_snr(adjusted_currents, adjusted_smoothed_currents)
        peak_retention = calculate_peak_retention(adjusted_currents, adjusted_smoothed_currents)
        residual_metric = calculate_residual_analysis(adjusted_currents, adjusted_smoothed_currents)
        qc_status = evaluate_qc_metrics(snr_improvement, peak_retention, residual_metric)

        # Store filter parameters and QC metrics
        filter_params = {
            'hampel_mode': hampel_mode,
            'sg_mode': sg_mode,
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
            positive_peak_candidates = []  # Peaks (mountains)
            negative_peak_candidates = []  # Valleys (troughs)

            # Log some debug information
            logger.info(f"Peak detection: Data points={len(adjusted_potentials)}, Current range=[{min(adjusted_smoothed_currents):.4f}, {max(adjusted_smoothed_currents):.4f}]")

            # Detect both positive peaks (derivative: + to -) and negative peaks (derivative: - to +)
            for i in range(1, len(first_derivative)):
                if first_derivative[i - 1] > 0 and first_derivative[i] <= 0:
                    # Positive peak (mountain)
                    positive_peak_candidates.append((adjusted_smoothed_currents[i], adjusted_potentials[i], i))
                elif first_derivative[i - 1] < 0 and first_derivative[i] >= 0:
                    # Negative peak (valley/trough)
                    negative_peak_candidates.append((adjusted_smoothed_currents[i], adjusted_potentials[i], i))

            logger.info(f"Peak detection: Found {len(positive_peak_candidates)} positive peaks, {len(negative_peak_candidates)} negative valleys")

            # Determine which type of peak is more prominent
            peak_candidates = []
            if positive_peak_candidates and negative_peak_candidates:
                # Compare the magnitude of the most prominent positive and negative peaks
                max_positive = max(positive_peak_candidates, key=lambda x: x[0])
                min_negative = min(negative_peak_candidates, key=lambda x: x[0])

                # Choose based on absolute magnitude from zero
                if abs(max_positive[0]) > abs(min_negative[0]):
                    peak_candidates = positive_peak_candidates
                    peak_type = "positive"
                    logger.info(f"Selecting positive peak (magnitude: {abs(max_positive[0]):.4e} > {abs(min_negative[0]):.4e})")
                else:
                    peak_candidates = negative_peak_candidates
                    peak_type = "negative"
                    logger.info(f"Selecting negative valley (magnitude: {abs(min_negative[0]):.4e} > {abs(max_positive[0]):.4e})")
            elif positive_peak_candidates:
                peak_candidates = positive_peak_candidates
                peak_type = "positive"
                logger.info("Only positive peaks found")
            elif negative_peak_candidates:
                peak_candidates = negative_peak_candidates
                peak_type = "negative"
                logger.info("Only negative valleys found")

            if peak_candidates:
                # Select the most prominent peak based on type
                if peak_type == "positive":
                    original_peak_current, peak_potential, peak_index = max(peak_candidates, key=lambda x: x[0])
                else:
                    original_peak_current, peak_potential, peak_index = min(peak_candidates, key=lambda x: x[0])

                logger.info(f"Peak detection: Selected {peak_type} peak at V={peak_potential:.4f}, I={original_peak_current:.4f}, index={peak_index}")

                # --- Intelligent Convex Hull Based Tangent Algorithm ---
                points = list(zip(adjusted_potentials, adjusted_smoothed_currents))

                def cross_product(p1, p2, p3):
                    return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

                # Build appropriate hull based on peak TYPE (not current sign)
                # For positive peaks (mountains): baseline connects valleys below the peak -> use LOWER hull
                # For negative peaks (valleys): baseline connects ridges above the valley -> use UPPER hull
                if peak_type == "negative":
                    # Negative peak (valley): use upper convex hull to find baseline above the valley
                    upper_hull = []
                    for p in reversed(points):
                        while len(upper_hull) >= 2 and cross_product(upper_hull[-2], upper_hull[-1], p) <= 0:
                            upper_hull.pop()
                        upper_hull.append(p)
                    upper_hull.reverse()  # Reverse back to left-to-right order
                    hull = upper_hull
                    logger.info(f"Using upper hull for negative peak/valley (hull points: {len(hull)})")
                else:
                    # Positive peak (mountain): use lower convex hull to find baseline below the peak
                    lower_hull = []
                    for p in points:
                        while len(lower_hull) >= 2 and cross_product(lower_hull[-2], lower_hull[-1], p) <= 0:
                            lower_hull.pop()
                        lower_hull.append(p)
                    hull = lower_hull
                    logger.info(f"Using lower hull for positive peak/mountain (hull points: {len(hull)})")

                # Find the baseline edge on the hull that spans the peak
                baseline_edge_found = False
                for i in range(len(hull) - 1):
                    p_left = hull[i]
                    p_right = hull[i + 1]

                    idx_left = adjusted_potentials.index(p_left[0])
                    idx_right = adjusted_potentials.index(p_right[0])

                    if idx_left <= peak_index < idx_right:
                        V_left_baseline, I_left_baseline = p_left
                        V_right_baseline, I_right_baseline = p_right
                        baseline_edge_found = True
                        logger.info(f"Baseline edge found: Left({V_left_baseline:.4f}V, {I_left_baseline:.4e}A), Right({V_right_baseline:.4f}V, {I_right_baseline:.4e}A)")
                        break

                if not baseline_edge_found:
                    # Fallback: use hull endpoints for baseline (handles monotonic data and edge cases)
                    baseline_warning_type = "peak_outside_hull_fallback"
                    if len(hull) >= 2:
                        # Use first and last hull points (most common for monotonic data)
                        V_left_baseline, I_left_baseline = hull[0]
                        V_right_baseline, I_right_baseline = hull[-1]
                        logger.warning(f"Peak outside hull segments, using hull endpoints as baseline: Left({V_left_baseline:.4f}V, {I_left_baseline:.4e}A), Right({V_right_baseline:.4f}V, {I_right_baseline:.4e}A)")
                    else:
                        # Only one hull point (degenerate case)
                        if peak_type == "negative":
                            # For valley, use the highest point as baseline
                            max_idx = np.argmax(adjusted_smoothed_currents)
                            V_left_baseline = V_right_baseline = adjusted_potentials[max_idx]
                            I_left_baseline = I_right_baseline = adjusted_smoothed_currents[max_idx]
                        else:
                            # For mountain, use the lowest point as baseline
                            min_idx = np.argmin(adjusted_smoothed_currents)
                            V_left_baseline = V_right_baseline = adjusted_potentials[min_idx]
                            I_left_baseline = I_right_baseline = adjusted_smoothed_currents[min_idx]
                        logger.warning(f"Degenerate hull, using {'max' if peak_type == 'negative' else 'min'} current point")

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
                    peak_value = 0  # Set to 0 instead of None for consistency
                    baseline_warning_type = "internal_baseline_error"
            else:
                peak_value = 0  # Set to 0 instead of None for consistency
                baseline_warning_type = "no_derivative_peak"
                logger.warning(f"Peak detection: No derivative peaks found in data with {len(adjusted_potentials)} points")
        else:
            peak_value = 0  # Set to 0 instead of None for consistency
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

    # Prepare peak-to-baseline visualization data
    peak_baseline_line = []
    peak_info = {}

    if analysis_params['SelectedOptions'] == "Peak Height Extraction" and 'peak_potential' in locals() and 'baseline_at_peak' in locals():
        peak_info = {
            'peak_potential': peak_potential,
            'peak_current': original_peak_current,
            'baseline_current': baseline_at_peak,
            'peak_height': peak_value,
            'baseline_left': {'potential': V_left_baseline, 'current': I_left_baseline} if V_left_baseline is not None else None,
            'baseline_right': {'potential': V_right_baseline, 'current': I_right_baseline} if V_right_baseline is not None else None
        }

        # Create vertical line from baseline to peak for visualization
        if baseline_at_peak is not None:
            peak_baseline_line = [
                {'potential': peak_potential, 'current': baseline_at_peak},
                {'potential': peak_potential, 'current': original_peak_current}
            ]

    return {
        "status": status, "message": message, "warning_type": baseline_warning_type,
        "potentials": adjusted_potentials,  # Return sorted, ranged data
        "raw_currents": adjusted_currents,  # Return sorted, ranged data
        "smoothed_currents": adjusted_smoothed_currents,  # Return sorted, ranged, smoothed data
        "regression_line": eval_regress,
        "adjusted_potentials": adjusted_potentials,  # This is somewhat redundant, but kept for consistency
        "peak_value": peak_value,
        "auc_vertices": auc_vertices,
        "peak_info": peak_info,  # NEW: Peak detection details for visualization
        "peak_baseline_line": peak_baseline_line,  # NEW: Line from baseline to peak
        "filter_params": filter_params if 'filter_params' in locals() else {},
        "qc_metrics": qc_metrics if 'qc_metrics' in locals() else {}
    }