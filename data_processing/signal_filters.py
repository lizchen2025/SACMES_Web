# data_processing/signal_filters.py
"""
Advanced signal filtering module for SWV data processing
Includes Hampel and Savitzky-Golay filters with automatic parameter estimation
"""

import numpy as np
from scipy.signal import savgol_filter
import logging

logger = logging.getLogger(__name__)


def calculate_fwhm(potentials, currents):
    """
    Calculate Full Width at Half Maximum (FWHM) of the peak.

    Args:
        potentials: List of potential values
        currents: List of current values

    Returns:
        float: FWHM value or None if cannot be calculated
    """
    try:
        # Find peak
        peak_idx = np.argmax(currents)
        peak_current = currents[peak_idx]

        # Find half maximum
        half_max = peak_current / 2

        # Find points closest to half maximum on both sides
        left_half_idx = None
        right_half_idx = None

        # Search left side
        for i in range(peak_idx, -1, -1):
            if currents[i] <= half_max:
                left_half_idx = i
                break

        # Search right side
        for i in range(peak_idx, len(currents)):
            if currents[i] <= half_max:
                right_half_idx = i
                break

        if left_half_idx is not None and right_half_idx is not None:
            fwhm = abs(potentials[right_half_idx] - potentials[left_half_idx])
            return fwhm

        return None
    except Exception as e:
        logger.warning(f"Failed to calculate FWHM: {e}")
        return None


def hampel_filter(data, window_size=None, threshold=3.0, auto_params=True, fwhm=None):
    """
    Apply Hampel filter to remove outliers from signal.

    Args:
        data: Input signal as numpy array or list
        window_size: Size of the moving window (if None and auto_params=True, will be auto-calculated)
        threshold: Threshold in terms of MAD (Median Absolute Deviation)
        auto_params: If True, automatically calculate window_size based on FWHM
        fwhm: FWHM value for auto parameter calculation

    Returns:
        tuple: (filtered_data, outlier_indices, trigger_rate, used_window_size)
    """
    data = np.array(data)
    n = len(data)

    if auto_params and fwhm is not None:
        # Auto window size: 1/10 FWHM, range 3-7
        estimated_window = max(3, min(7, int(len(data) * fwhm / 10)))
        window_size = estimated_window
    elif window_size is None:
        window_size = 5  # Default fallback

    # Ensure odd window size
    if window_size % 2 == 0:
        window_size += 1

    # Ensure minimum window size
    window_size = max(3, min(window_size, n))

    filtered_data = data.copy()
    outlier_indices = []
    half_window = window_size // 2

    for i in range(n):
        # Define window bounds
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)

        # Extract window
        window = data[start:end]

        # Calculate median and MAD
        median = np.median(window)
        mad = np.median(np.abs(window - median))

        # Apply threshold (3 times MAD is typical for outlier detection)
        if mad > 0:  # Avoid division by zero
            if np.abs(data[i] - median) > threshold * mad:
                filtered_data[i] = median
                outlier_indices.append(i)

    # Calculate trigger rate (percentage of points replaced)
    trigger_rate = len(outlier_indices) / n * 100 if n > 0 else 0

    return filtered_data, outlier_indices, trigger_rate, window_size


def enhanced_savgol_filter(data, window_length=None, polyorder=2, auto_params=True, fwhm=None):
    """
    Apply enhanced Savitzky-Golay filter with automatic parameter estimation.

    Args:
        data: Input signal as numpy array or list
        window_length: Length of the filter window (if None and auto_params=True, will be auto-calculated)
        polyorder: Order of the polynomial used for filtering
        auto_params: If True, automatically calculate window_length based on FWHM
        fwhm: FWHM value for auto parameter calculation

    Returns:
        tuple: (filtered_data, used_window_length, used_polyorder)
    """
    data = np.array(data)
    n = len(data)

    if auto_params and fwhm is not None:
        # Auto window length: 1/3 FWHM, range 7-31
        estimated_window = max(7, min(31, int(len(data) * fwhm / 3)))
        window_length = estimated_window
    elif window_length is None:
        window_length = 15  # Default fallback

    # Ensure odd window length
    if window_length % 2 == 0:
        window_length += 1

    # Ensure minimum requirements for SG filter
    window_length = max(polyorder + 1, window_length)
    window_length = min(window_length, n)

    # Ensure window is odd and at least polyorder + 1
    if window_length <= polyorder:
        window_length = polyorder + 2 if (polyorder + 2) % 2 != 0 else polyorder + 3

    # Final constraint check
    if window_length > n:
        window_length = n if n % 2 != 0 else n - 1
    if window_length < 3:
        window_length = 3

    try:
        filtered_data = savgol_filter(data, window_length, polyorder)
        return filtered_data, window_length, polyorder
    except ValueError as e:
        logger.warning(f"SG filter failed with window_length={window_length}, polyorder={polyorder}: {e}")
        # Fallback to simpler parameters
        window_length = max(3, min(7, n))
        polyorder = min(1, polyorder)
        if window_length > polyorder:
            filtered_data = savgol_filter(data, window_length, polyorder)
            return filtered_data, window_length, polyorder
        else:
            # Ultimate fallback: return original data
            return data, window_length, polyorder


def calculate_snr(original_signal, filtered_signal):
    """
    Calculate Signal-to-Noise Ratio improvement.

    Args:
        original_signal: Original noisy signal
        filtered_signal: Filtered signal

    Returns:
        float: SNR improvement in dB
    """
    try:
        original_signal = np.array(original_signal)
        filtered_signal = np.array(filtered_signal)

        # Calculate signal power (variance of the signal)
        signal_power = np.var(filtered_signal)

        # Calculate noise power (variance of the difference)
        noise_original = original_signal - np.mean(original_signal)
        noise_filtered = filtered_signal - np.mean(filtered_signal)
        noise_reduction = np.var(noise_original) - np.var(noise_filtered)

        if noise_reduction > 0 and signal_power > 0:
            snr_improvement = 10 * np.log10(noise_reduction / np.var(noise_filtered))
            return max(0, snr_improvement)  # Return 0 if negative

        return 0.0
    except Exception as e:
        logger.warning(f"Failed to calculate SNR: {e}")
        return 0.0


def calculate_peak_preservation(original_signal, filtered_signal):
    """
    Calculate how well the peak shape is preserved.

    Args:
        original_signal: Original signal
        filtered_signal: Filtered signal

    Returns:
        float: Peak preservation score (0-100%)
    """
    try:
        original_signal = np.array(original_signal)
        filtered_signal = np.array(filtered_signal)

        # Find peaks in both signals
        orig_peak_idx = np.argmax(original_signal)
        filt_peak_idx = np.argmax(filtered_signal)

        # Calculate peak height preservation
        orig_peak_height = original_signal[orig_peak_idx]
        filt_peak_height = filtered_signal[filt_peak_idx]

        height_preservation = min(100, 100 * filt_peak_height / orig_peak_height) if orig_peak_height > 0 else 0

        # Calculate peak position preservation
        position_shift = abs(orig_peak_idx - filt_peak_idx)
        position_preservation = max(0, 100 - position_shift * 10)  # Penalize position shifts

        # Calculate overall shape correlation
        correlation = np.corrcoef(original_signal, filtered_signal)[0, 1]
        correlation_score = max(0, correlation * 100)

        # Weighted average
        peak_preservation = (height_preservation * 0.4 + position_preservation * 0.3 + correlation_score * 0.3)

        return min(100, max(0, peak_preservation))
    except Exception as e:
        logger.warning(f"Failed to calculate peak preservation: {e}")
        return 0.0


def calculate_residual_percentage(original_signal, filtered_signal):
    """
    Calculate residual percentage between original and filtered signals.

    Args:
        original_signal: Original signal
        filtered_signal: Filtered signal

    Returns:
        float: Residual percentage
    """
    try:
        original_signal = np.array(original_signal)
        filtered_signal = np.array(filtered_signal)

        residual = np.mean(np.abs(original_signal - filtered_signal))
        signal_range = np.max(original_signal) - np.min(original_signal)

        if signal_range > 0:
            residual_percentage = (residual / signal_range) * 100
            return min(100, max(0, residual_percentage))

        return 0.0
    except Exception as e:
        logger.warning(f"Failed to calculate residual percentage: {e}")
        return 0.0


def perform_qc_analysis(original_signal, filtered_signal, hampel_trigger_rate):
    """
    Perform quality control analysis on filtered signal.

    Args:
        original_signal: Original signal
        filtered_signal: Filtered signal
        hampel_trigger_rate: Trigger rate from Hampel filter

    Returns:
        dict: QC results with scores and overall status
    """
    try:
        snr_improvement = calculate_snr(original_signal, filtered_signal)
        peak_preservation = calculate_peak_preservation(original_signal, filtered_signal)
        residual_percentage = calculate_residual_percentage(original_signal, filtered_signal)

        # QC criteria
        qc_results = {
            'snr_improvement': snr_improvement,
            'peak_preservation': peak_preservation,
            'residual_percentage': residual_percentage,
            'hampel_trigger_rate': hampel_trigger_rate
        }

        # Determine overall QC status
        # PASS criteria: SNR > 1 dB, Peak preservation > 80%, Residual < 20%, Hampel trigger < 10%
        pass_criteria = (
            snr_improvement >= 1.0 and
            peak_preservation >= 80.0 and
            residual_percentage <= 20.0 and
            hampel_trigger_rate <= 10.0
        )

        # WARNING criteria: SNR > 0.5 dB, Peak preservation > 60%, Residual < 30%, Hampel trigger < 20%
        warning_criteria = (
            snr_improvement >= 0.5 and
            peak_preservation >= 60.0 and
            residual_percentage <= 30.0 and
            hampel_trigger_rate <= 20.0
        )

        if pass_criteria:
            qc_results['status'] = 'PASS'
        elif warning_criteria:
            qc_results['status'] = 'WARNING'
        else:
            qc_results['status'] = 'FAIL'

        return qc_results
    except Exception as e:
        logger.error(f"Failed to perform QC analysis: {e}")
        return {
            'snr_improvement': 0.0,
            'peak_preservation': 0.0,
            'residual_percentage': 100.0,
            'hampel_trigger_rate': hampel_trigger_rate,
            'status': 'FAIL'
        }


def apply_combined_filtering(potentials, currents, hampel_params=None, sg_params=None, auto_mode=True):
    """
    Apply combined Hampel + SG filtering to SWV data.

    Args:
        potentials: Potential values
        currents: Current values
        hampel_params: Dict with 'window_size', 'threshold' for Hampel filter
        sg_params: Dict with 'window_length', 'polyorder' for SG filter
        auto_mode: If True, automatically calculate parameters based on FWHM

    Returns:
        dict: Complete filtering results including QC analysis
    """
    try:
        potentials = np.array(potentials)
        currents = np.array(currents)

        # Calculate FWHM for auto parameter estimation
        fwhm = calculate_fwhm(potentials, currents) if auto_mode else None

        # Step 1: Apply Hampel filter
        if hampel_params is None:
            hampel_params = {}

        hampel_window = hampel_params.get('window_size', None)
        hampel_threshold = hampel_params.get('threshold', 3.0)

        hampel_filtered, outliers, trigger_rate, used_hampel_window = hampel_filter(
            currents,
            window_size=hampel_window,
            threshold=hampel_threshold,
            auto_params=auto_mode,
            fwhm=fwhm
        )

        # Step 2: Apply SG filter to Hampel-filtered data
        if sg_params is None:
            sg_params = {}

        sg_window = sg_params.get('window_length', None)
        sg_polyorder = sg_params.get('polyorder', 2)

        final_filtered, used_sg_window, used_sg_polyorder = enhanced_savgol_filter(
            hampel_filtered,
            window_length=sg_window,
            polyorder=sg_polyorder,
            auto_params=auto_mode,
            fwhm=fwhm
        )

        # Step 3: Perform QC analysis
        qc_results = perform_qc_analysis(currents, final_filtered, trigger_rate)

        # Compile results
        results = {
            'original_currents': currents.tolist(),
            'hampel_filtered': hampel_filtered.tolist(),
            'final_filtered': final_filtered.tolist(),
            'outlier_indices': outliers,
            'fwhm': fwhm,
            'hampel_params': {
                'window_size': used_hampel_window,
                'threshold': hampel_threshold,
                'auto_mode': auto_mode
            },
            'sg_params': {
                'window_length': used_sg_window,
                'polyorder': used_sg_polyorder,
                'auto_mode': auto_mode
            },
            'qc_results': qc_results
        }

        return results

    except Exception as e:
        logger.error(f"Failed to apply combined filtering: {e}")
        return {
            'original_currents': currents.tolist() if 'currents' in locals() else [],
            'hampel_filtered': currents.tolist() if 'currents' in locals() else [],
            'final_filtered': currents.tolist() if 'currents' in locals() else [],
            'outlier_indices': [],
            'fwhm': None,
            'hampel_params': hampel_params or {},
            'sg_params': sg_params or {},
            'qc_results': {'status': 'FAIL', 'snr_improvement': 0, 'peak_preservation': 0, 'residual_percentage': 100, 'hampel_trigger_rate': 0}
        }