# data_processing/cv_analyzer.py
# Description: Module for performing Cyclic Voltammetry (CV) analysis.
# This module is adapted from the original SACMES desktop application's CV functionalities.

import numpy as np
import logging
from scipy import signal
from scipy.integrate import simps
from .data_reader import ReadData as GeneralReadData  # Keep the original reader for multichannel handling

logger = logging.getLogger(__name__)


# --- Helper Functions ---

def _read_and_segment_data(file_path, params, selected_electrode=None):
    """
    Reads CV data from a file and identifies the scanning segments.

    A segment is a continuous scan in one direction (e.g., positive or negative potential sweep).
    This function is the core of CV data parsing.

    Args:
        file_path (str): The full path to the data file.
        params (dict): Dictionary of analysis parameters.
        selected_electrode (int): Index of specific electrode to analyze (0-based).

    Returns:
        tuple: A tuple containing:
            - potentials (list): Full list of potential values.
            - currents (list): Full list of current values.
            - segment_dictionary (dict): A dictionary mapping segment numbers to their data.
              e.g., {1: {'indices': [...], 'potentials': [...], 'currents': [...]}}
    """
    delimiter_map = {1: " ", 2: "\t", 3: ","}
    delimiter_char = delimiter_map.get(params.get('delimiter', 1), " ")

    # Determine electrode index to use
    electrode_idx = selected_electrode if selected_electrode is not None else params.get('selected_electrode', 0)

    # Read CV data using either multichannel reader or direct numpy loading
    potentials, currents = [], []

    if selected_electrode is not None:
        # Use multichannel reader for specific electrode
        from .data_reader import ReadData
        electrodes_data = ReadData(
            myfile=file_path,
            voltage_column_index=params['voltage_column'] - 1,
            current_column_start_index=params['current_column'] - 1,
            spacing_index=params['spacing_index'],
            num_electrodes=params['num_electrodes'],
            delimiter_char=delimiter_char,
            file_extension=params.get('file_extension', '.txt'),
            selected_electrodes=[electrode_idx]
        )

        # Check electrode validation
        detected_electrodes = electrodes_data.get('detected_electrodes', 0)
        if electrode_idx >= detected_electrodes:
            logger.error(f"Electrode validation failed: File contains {detected_electrodes} electrodes, but electrode {electrode_idx + 1} was requested.")
            return [], [], {'error': f'electrode_validation_failed', 'detected_electrodes': detected_electrodes, 'requested_electrode': electrode_idx + 1}

        if electrode_idx in electrodes_data:
            electrode_data = electrodes_data[electrode_idx]
            potentials = electrode_data['potentials']
            currents = electrode_data['currents']
        else:
            logger.error(f"No data found for electrode {electrode_idx}")
            return [], [], {}
    else:
        # Original single-electrode or averaged behavior
        try:
            data = np.loadtxt(file_path, delimiter=delimiter_char, usecols=(
            params['voltage_column'] - 1, params['current_column'] - 1 + electrode_idx * params['spacing_index']))
            potentials = data[:, 0].tolist()
            currents = (data[:, 1] * 1e6).tolist()  # Convert to microAmps
        except Exception as e:
            logger.error(f"CV Reader failed for {file_path}: {e}")
            return [], [], {}

    if not potentials or not currents:
        return [], [], {}

    # --- Segment Detection Logic ---
    segment_dictionary = {}
    if len(potentials) < 3:  # Need at least 3 points to detect a change in direction
        return potentials, currents, {}

    current_segment = 1
    segment_indices = []

    # Determine initial scan direction
    initial_direction = np.sign(potentials[1] - potentials[0])
    last_direction = initial_direction

    for i in range(len(potentials) - 1):
        segment_indices.append(i)
        direction = np.sign(potentials[i + 1] - potentials[i])

        # When direction changes, a segment ends and a new one begins
        if direction != last_direction and direction != 0:
            # Add the vertex point to the current segment before starting a new one
            segment_indices.append(i)

            segment_dictionary[current_segment] = {
                'indices': list(segment_indices),
                'potentials': [potentials[j] for j in segment_indices],
                'currents': [currents[j] for j in segment_indices]
            }

            # Start new segment
            current_segment += 1
            segment_indices = [i]  # The vertex point is also the start of the new segment
            last_direction = direction

    # Add the last point and the final segment
    segment_indices.append(len(potentials) - 1)
    segment_dictionary[current_segment] = {
        'indices': list(segment_indices),
        'potentials': [potentials[j] for j in segment_indices],
        'currents': [currents[j] for j in segment_indices]
    }

    return potentials, currents, segment_dictionary


def _apply_savgol_filter(currents, sg_window=5, sg_degree=1):
    """Apply Savitzky-Golay filter for signal smoothing."""
    if len(currents) < sg_window:
        return currents  # Not enough points for filtering

    # Ensure window size is odd
    if sg_window % 2 == 0:
        sg_window += 1

    # Apply Savitzky-Golay filter
    try:
        filtered_currents = signal.savgol_filter(currents, sg_window, sg_degree)
        return filtered_currents.tolist()
    except Exception as e:
        logger.warning(f"Savitzky-Golay filter failed: {e}")
        return currents


def _apply_polynomial_regression(potentials, currents, polyfit_deg=15):
    """Apply polynomial regression for further smoothing."""
    try:
        if len(potentials) < polyfit_deg + 1:
            polyfit_deg = max(1, len(potentials) - 2)

        coeffs = np.polyfit(potentials, currents, polyfit_deg)
        smoothed_currents = np.polyval(coeffs, potentials)
        return smoothed_currents.tolist()
    except Exception as e:
        logger.warning(f"Polynomial regression failed: {e}")
        return currents


def _extract_peak_vertices(potentials, currents, peak_idx, sign_type="cathodic"):
    """Extract vertex currents before and after the peak (SACMES algorithm)."""
    try:
        if sign_type == "cathodic":
            # For cathodic peaks, find minimum currents on either side
            if peak_idx > 0:
                vertex1 = min(currents[:peak_idx])
            else:
                vertex1 = currents[0]

            if peak_idx < len(currents) - 1:
                vertex2 = min(currents[peak_idx:])
            else:
                vertex2 = currents[-1]
        else:  # anodic
            # For anodic peaks, find maximum currents on either side
            if peak_idx > 0:
                vertex1 = max(currents[:peak_idx])
            else:
                vertex1 = currents[0]

            if peak_idx < len(currents) - 1:
                vertex2 = max(currents[peak_idx:])
            else:
                vertex2 = currents[-1]

        return vertex1, vertex2
    except Exception as e:
        logger.warning(f"Vertex extraction failed: {e}")
        return currents[0], currents[-1]


def _baseline_surface_bound(potentials, currents, use_vertices=True):
    """Enhanced baseline calculation for surface-bound species using SACMES algorithm."""
    peak_idx = np.argmax(np.abs(currents))

    if use_vertices:
        # Determine if peak is cathodic or anodic
        sign_type = "cathodic" if currents[peak_idx] > 0 else "anodic"

        # Extract vertex currents
        vertex1, vertex2 = _extract_peak_vertices(potentials, currents, peak_idx, sign_type)

        # Find corresponding potentials for vertices
        vertex1_indices = [i for i, c in enumerate(currents) if c == vertex1]
        vertex2_indices = [i for i, c in enumerate(currents) if c == vertex2]

        # Use the vertex closest to the peak
        v1_idx = vertex1_indices[0] if vertex1_indices else 0
        v2_idx = vertex2_indices[-1] if vertex2_indices else len(currents) - 1
    else:
        # Original method - find minima on either side
        v1_idx = np.argmin(currents[:peak_idx]) if peak_idx > 0 else 0
        v2_idx_rel = np.argmin(currents[peak_idx:]) if peak_idx < len(currents) - 1 else -1
        v2_idx = peak_idx + v2_idx_rel

    v1_potential, v1_current = potentials[v1_idx], currents[v1_idx]
    v2_potential, v2_current = potentials[v2_idx], currents[v2_idx]

    # Create linear baseline
    if v1_potential == v2_potential:  # Avoid division by zero
        slope = 0
    else:
        slope = (v2_current - v1_current) / (v2_potential - v1_potential)

    intercept = v1_current - slope * v1_potential
    baseline_currents = [(slope * p + intercept) for p in potentials]

    return baseline_currents


def _baseline_solution_phase(potentials, currents):
    """Calculates a tangential baseline for solution-phase species."""
    # This is a simplified version of the complex logic.
    # It finds the point of minimum absolute current (foot of the wave)
    # and calculates a tangent there.

    foot_idx = np.argmin(np.abs(currents))

    # Define a small range around the foot to calculate the slope
    range_width = max(3, int(0.05 * len(potentials)))  # 5% of points or at least 3
    start_idx = max(0, foot_idx - range_width // 2)
    end_idx = min(len(potentials), foot_idx + range_width // 2)

    if end_idx - start_idx < 2:  # Not enough points for slope
        return [np.mean(currents)] * len(potentials)  # Return a flat average baseline

    slope_potentials = potentials[start_idx:end_idx]
    slope_currents = currents[start_idx:end_idx]

    # Fit a line to this small section
    coeffs = np.polyfit(slope_potentials, slope_currents, 1)
    slope, intercept = coeffs[0], coeffs[1]

    # Extrapolate this line across all potentials
    baseline_currents = [(slope * p + intercept) for p in potentials]

    return baseline_currents


# --- Main Public Functions ---

def get_cv_segments(file_path, params, selected_electrode=None):
    """
    Performs a preliminary analysis on a CV file just to get the available segments.

    Args:
        file_path (str): Path to the data file.
        params (dict): Analysis parameters.
        selected_electrode (int): Index of specific electrode to analyze (0-based).

    Returns:
        dict: A dictionary containing the status and the list of segment numbers.
    """
    try:
        _, _, segment_dictionary = _read_and_segment_data(file_path, params, selected_electrode)
        if not segment_dictionary:
            return {"status": "error", "message": "No data or segments found."}

        return {"status": "success", "segments": list(segment_dictionary.keys())}
    except Exception as e:
        logger.error(f"Error getting CV segments: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def analyze_cv_data(file_path, params, selected_electrode=None):
    """
    Performs a full analysis of a single CV data file.

    Args:
        file_path (str): The full path to the data file.
        params (dict): A dictionary containing all analysis parameters from the frontend.
                       Expected keys: 'forward_segment', 'reverse_segment', 'low_voltage',
                       'high_voltage', 'mass_transport', 'SelectedOptions', 'scan_rate', etc.
        selected_electrode (int): Index of specific electrode to analyze (0-based).
                                If None, uses original averaging behavior.

    Returns:
        dict: A comprehensive dictionary with all analysis results.
    """
    try:
        # Step 1: Read and segment the entire file
        all_potentials, all_currents, segment_dictionary = _read_and_segment_data(file_path, params, selected_electrode)
        if not segment_dictionary:
            return {"status": "error", "message": "Could not read or segment data file."}

        results = {
            "forward": {},
            "reverse": {},
            "peak_separation": None,
            "status": "success"
        }

        # Step 2: Analyze forward and reverse segments individually
        for scan_type in ["forward", "reverse"]:
            segment_num = params.get(f'{scan_type}_segment')
            if not segment_num or segment_num not in segment_dictionary:
                continue

            segment = segment_dictionary[segment_num]

            # Filter by user-defined voltage range
            p_raw, i_raw = np.array(segment['potentials']), np.array(segment['currents'])
            voltage_mask = (p_raw >= params['low_voltage']) & (p_raw <= params['high_voltage'])
            p_adj, i_adj = p_raw[voltage_mask].tolist(), i_raw[voltage_mask].tolist()

            if len(p_adj) < 3:
                continue  # Not enough data in range

            # Step 1: Apply signal processing (SACMES algorithm)
            sg_window = params.get('sg_window', 5)
            sg_degree = params.get('sg_degree', 1)
            polyfit_deg = params.get('polyfit_deg', 15)
            phe_method = params.get('phe_method', 'Abs')  # 'Abs' or 'Rel'

            # Apply Savitzky-Golay filter for smoothing
            i_smoothed = _apply_savgol_filter(i_adj, sg_window, sg_degree)

            # Apply polynomial regression if requested
            if params.get('apply_polynomial_regression', False):
                i_smoothed = _apply_polynomial_regression(p_adj, i_smoothed, polyfit_deg)

            # Step 2: Calculate baseline
            if params['mass_transport'] == 'surface':
                baseline = _baseline_surface_bound(p_adj, i_smoothed, use_vertices=True)
            else:  # solution
                baseline = _baseline_solution_phase(p_adj, i_smoothed)

            i_corrected = np.array(i_smoothed) - np.array(baseline)

            # Step 3: Peak extraction using PHE method
            if phe_method == 'Abs':
                # Absolute method: difference between absolute max/min
                peak_idx = np.argmax(np.abs(i_corrected))
                peak_current = i_corrected[peak_idx]  # This is the peak height
            else:  # Relative method
                # Relative method: peak relative to baseline
                peak_idx = np.argmax(np.abs(i_corrected))
                peak_current = abs(i_corrected[peak_idx])  # Always positive for relative

            peak_potential = p_adj[peak_idx]

            # Step 4: Calculate area under curve (charge) with enhanced integration
            scan_rate = params.get('scan_rate', 0.1)
            if scan_rate <= 0:
                scan_rate = 0.1  # Default scan rate

            # Use Simpson's rule for more accurate integration
            try:
                charge = simps(np.abs(i_corrected), x=p_adj) / scan_rate
            except:
                charge = np.trapz(np.abs(i_corrected), x=p_adj) / scan_rate  # Fallback to trapezoidal

            # Calculate additional CV metrics
            peak_width = None
            half_peak_potential = None

            if len(i_corrected) > 3:
                # Find half-peak width (rough estimation)
                half_peak_current = peak_current / 2
                half_peak_indices = np.where(np.abs(i_corrected) >= abs(half_peak_current))[0]
                if len(half_peak_indices) > 1:
                    peak_width = abs(p_adj[half_peak_indices[-1]] - p_adj[half_peak_indices[0]])
                    half_peak_potential = (p_adj[half_peak_indices[-1]] + p_adj[half_peak_indices[0]]) / 2

            # Step 5: Calculate additional SACMES metrics
            sign_type = "cathodic" if peak_current > 0 else "anodic"

            # Extract vertex information
            vertex1, vertex2 = _extract_peak_vertices(p_adj, i_corrected.tolist(), peak_idx, sign_type)

            # Calculate peak-to-vertex ratio
            if phe_method == 'Abs':
                peak_to_vertex_ratio = abs(peak_current) / max(abs(vertex1), abs(vertex2)) if max(abs(vertex1), abs(vertex2)) > 0 else 1
            else:
                peak_to_vertex_ratio = peak_current / max(vertex1, vertex2) if max(vertex1, vertex2) > 0 else 1

            # Store results for this segment with enhanced SACMES data
            results[scan_type] = {
                'potentials': p_adj,
                'currents': i_adj,
                'smoothed_currents': i_smoothed,
                'baseline': baseline,
                'corrected_currents': i_corrected.tolist(),
                'peak_potential': peak_potential,
                'peak_current': peak_current,
                'charge': charge,
                'peak_width': peak_width,
                'half_peak_potential': half_peak_potential,
                'sign_type': sign_type,
                'vertex1': vertex1,
                'vertex2': vertex2,
                'peak_to_vertex_ratio': peak_to_vertex_ratio,
                'phe_method': phe_method,
                'filtering_params': {
                    'sg_window': sg_window,
                    'sg_degree': sg_degree,
                    'polyfit_deg': polyfit_deg if params.get('apply_polynomial_regression', False) else None
                },
                'auc_vertices': list(zip(p_adj, np.maximum(0, i_corrected)))  # For shading
            }

        # Step 3: Calculate peak separation
        if results["forward"].get("peak_potential") is not None and results["reverse"].get(
                "peak_potential") is not None:
            results["peak_separation"] = abs(
                results["forward"]["peak_potential"] - results["reverse"]["peak_potential"])

        # Step 6: Enhanced CV metrics calculations
        if results["forward"].get("peak_potential") is not None and results["reverse"].get("peak_potential") is not None:
            # Calculate formal potential (midpoint potential)
            formal_potential = (results["forward"]["peak_potential"] + results["reverse"]["peak_potential"]) / 2
            results["formal_potential"] = formal_potential

            # Calculate peak current ratio (reversibility indicator)
            forward_peak = abs(results["forward"]["peak_current"])
            reverse_peak = abs(results["reverse"]["peak_current"])
            peak_current_ratio = forward_peak / reverse_peak if reverse_peak > 0 else 1
            results["peak_current_ratio"] = peak_current_ratio

            # Reversibility assessment
            if 0.85 <= peak_current_ratio <= 1.15 and results["peak_separation"] <= 0.059:  # ~59mV at 25°C
                results["reversibility"] = "reversible"
            elif results["peak_separation"] > 0.2:
                results["reversibility"] = "irreversible"
            else:
                results["reversibility"] = "quasi_reversible"

        return results

    except Exception as e:
        logger.error(f"Critical error in CV analysis for {file_path}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def analyze_cv_batch(file_paths, params, selected_electrode=None):
    """
    Performs batch analysis of multiple CV data files (SACMES-style batch processing).

    Args:
        file_paths (list): List of file paths to analyze.
        params (dict): Analysis parameters.
        selected_electrode (int): Index of specific electrode to analyze.

    Returns:
        dict: Batch analysis results with statistics.
    """
    try:
        batch_results = {
            "files": {},
            "statistics": {},
            "status": "success"
        }

        valid_results = []

        for file_path in file_paths:
            result = analyze_cv_data(file_path, params, selected_electrode)
            batch_results["files"][file_path] = result

            if result.get("status") == "success":
                valid_results.append(result)

        if valid_results:
            # Calculate batch statistics
            forward_potentials = [r["forward"].get("peak_potential") for r in valid_results if "forward" in r and r["forward"].get("peak_potential") is not None]
            reverse_potentials = [r["reverse"].get("peak_potential") for r in valid_results if "reverse" in r and r["reverse"].get("peak_potential") is not None]
            formal_potentials = [r.get("formal_potential") for r in valid_results if r.get("formal_potential") is not None]
            peak_separations = [r.get("peak_separation") for r in valid_results if r.get("peak_separation") is not None]

            batch_results["statistics"] = {
                "total_files": len(file_paths),
                "successful_analyses": len(valid_results),
                "forward_peak_potential": {
                    "mean": np.mean(forward_potentials) if forward_potentials else None,
                    "std": np.std(forward_potentials) if forward_potentials else None,
                    "count": len(forward_potentials)
                },
                "reverse_peak_potential": {
                    "mean": np.mean(reverse_potentials) if reverse_potentials else None,
                    "std": np.std(reverse_potentials) if reverse_potentials else None,
                    "count": len(reverse_potentials)
                },
                "formal_potential": {
                    "mean": np.mean(formal_potentials) if formal_potentials else None,
                    "std": np.std(formal_potentials) if formal_potentials else None,
                    "count": len(formal_potentials)
                },
                "peak_separation": {
                    "mean": np.mean(peak_separations) if peak_separations else None,
                    "std": np.std(peak_separations) if peak_separations else None,
                    "count": len(peak_separations)
                }
            }

        return batch_results

    except Exception as e:
        logger.error(f"Critical error in CV batch analysis: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
