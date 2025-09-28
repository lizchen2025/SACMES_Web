# data_processing/cv_analyzer.py
# Description: Module for performing Cyclic Voltammetry (CV) analysis.
# This module is adapted from the original SACMES desktop application's CV functionalities.

import numpy as np
import logging
import os
from .data_reader import ReadData as GeneralReadData  # Keep the original reader for multichannel handling

logger = logging.getLogger(__name__)


# --- Helper Functions ---

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
    logger.info(f"=== CV Data Reading Start ===")
    logger.info(f"File path: {file_path}")
    logger.info(f"Selected electrode: {selected_electrode}")
    logger.info(f"Params available: {list(params.keys())}")
    logger.info(f"Required params check:")
    logger.info(f"  - voltage_column: {params.get('voltage_column', 'MISSING')}")
    logger.info(f"  - current_column: {params.get('current_column', 'MISSING')}")
    logger.info(f"  - delimiter: {params.get('delimiter', 'MISSING')}")

    delimiter_map = {1: " ", 2: "\t", 3: ","}
    delimiter_char = delimiter_map.get(params.get('delimiter', 1), " ")
    logger.info(f"Using delimiter: '{delimiter_char}'")

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
            logger.info(f"Attempting to read CV data using numpy.loadtxt")

            # Check for required parameters
            required_params = ['voltage_column', 'current_column', 'spacing_index']
            missing_params = [p for p in required_params if p not in params]
            if missing_params:
                logger.error(f"Missing required parameters: {missing_params}")
                return [], [], {}

            logger.info(f"Parameters for reading:")
            logger.info(f"  - voltage_column (0-based): {params['voltage_column'] - 1}")
            logger.info(f"  - current_column (0-based): {params['current_column'] - 1 + electrode_idx * params['spacing_index']}")
            logger.info(f"  - electrode_idx: {electrode_idx}")
            logger.info(f"  - spacing_index: {params['spacing_index']}")

            data = np.loadtxt(file_path, delimiter=delimiter_char, usecols=(
            params['voltage_column'] - 1, params['current_column'] - 1 + electrode_idx * params['spacing_index']))
            potentials = data[:, 0].tolist()
            currents = (data[:, 1] * 1e6).tolist()  # Convert to microAmps
            logger.info(f"CV data read successfully: {len(potentials)} data points")
        except KeyError as ke:
            logger.error(f"CV Reader failed - missing parameter: {ke}")
            return [], [], {}
        except Exception as e:
            logger.error(f"CV Reader failed for {file_path}: {e}")
            logger.error(f"File exists: {os.path.exists(file_path)}")
            if os.path.exists(file_path):
                logger.error(f"File size: {os.path.getsize(file_path)} bytes")
                # Try to read first few lines for debugging
                try:
                    with open(file_path, 'r') as f:
                        first_lines = [f.readline().strip() for _ in range(3)]
                    logger.error(f"First 3 lines of file: {first_lines}")
                except Exception as read_err:
                    logger.error(f"Could not read file for debugging: {read_err}")
            return [], [], {}

    if not potentials or not currents:
        return [], [], {}

    # Apply unit conversions if specified
    voltage_units = params.get('voltage_units', 'V')
    current_units = params.get('current_units', 'A')

    # Convert to base units (V and A) for internal calculations
    if voltage_units != 'V':
        potentials = [convert_units(v, voltage_units, 'base') for v in potentials]
    if current_units != 'A':
        currents = [convert_units(c, current_units, 'base') for c in currents]

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


def _baseline_surface_bound(potentials, currents):
    """Calculates a linear baseline for surface-bound species."""
    peak_idx = np.argmax(np.abs(currents))

    # Find vertices on either side of the peak
    vertex1_idx = np.argmin(currents[:peak_idx]) if peak_idx > 0 else 0
    vertex2_idx_rel = np.argmin(currents[peak_idx:]) if peak_idx < len(currents) - 1 else -1
    vertex2_idx = peak_idx + vertex2_idx_rel

    v1_potential, v1_current = potentials[vertex1_idx], currents[vertex1_idx]
    v2_potential, v2_current = potentials[vertex2_idx], currents[vertex2_idx]

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
        logger.info(f"Starting CV analysis for {file_path}")
        logger.info(f"CV analysis params keys: {list(params.keys())}")

        # Step 1: Read and segment the entire file
        all_potentials, all_currents, segment_dictionary = _read_and_segment_data(file_path, params, selected_electrode)
        logger.info(f"CV segmentation result: {len(segment_dictionary) if segment_dictionary else 0} segments found")

        if not segment_dictionary:
            logger.error("CV segmentation failed - no segments found")
            return {"status": "error", "message": "Could not read or segment data file."}

        logger.info(f"CV segments available: {list(segment_dictionary.keys())}")

        results = {
            "forward": {},
            "reverse": {},
            "peak_separation": None,
            "status": "success"
        }

        # Step 2: Analyze forward and reverse segments individually
        for scan_type in ["forward", "reverse"]:
            logger.info(f"Processing {scan_type} segment...")
            segment_num = params.get(f'{scan_type}_segment')
            logger.info(f"Initial {scan_type} segment from params: {segment_num}")

            # If no segment specified, try to auto-detect based on scan type
            if not segment_num or segment_num not in segment_dictionary:
                available_segments = list(segment_dictionary.keys())
                logger.info(f"No valid segment specified for {scan_type}, available segments: {available_segments}")

                if not available_segments:
                    logger.warning(f"No segments available for {scan_type} analysis")
                    continue

                # Auto-assign segments: forward = 1st segment, reverse = 2nd segment (or 1st if only one)
                if scan_type == "forward":
                    segment_num = available_segments[0] if available_segments else None
                elif scan_type == "reverse":
                    segment_num = available_segments[1] if len(available_segments) > 1 else available_segments[0]

                logger.info(f"CV Auto-assigned {scan_type} segment: {segment_num} from available segments: {available_segments}")

                if not segment_num or segment_num not in segment_dictionary:
                    logger.warning(f"CV {scan_type} segment {segment_num} not found in segment dictionary")
                    continue

            segment = segment_dictionary[segment_num]
            logger.info(f"Using segment {segment_num} for {scan_type}, data points: {len(segment.get('potentials', []))}")

            # Filter by user-defined voltage range (convert range limits to base units if needed)
            p_raw, i_raw = np.array(segment['potentials']), np.array(segment['currents'])

            # Convert voltage range limits to base units
            voltage_units = params.get('voltage_units', 'V')
            low_voltage = params['low_voltage']
            high_voltage = params['high_voltage']

            if voltage_units != 'V':
                low_voltage = convert_units(low_voltage, voltage_units, 'base')
                high_voltage = convert_units(high_voltage, voltage_units, 'base')

            # Apply peak detection range filtering if specified (additional user-defined range)
            peak_min_voltage = params.get('peak_min_voltage')
            peak_max_voltage = params.get('peak_max_voltage')

            # Convert peak range limits to base units if specified
            if peak_min_voltage is not None and voltage_units != 'V':
                peak_min_voltage = convert_units(peak_min_voltage, voltage_units, 'base')
            if peak_max_voltage is not None and voltage_units != 'V':
                peak_max_voltage = convert_units(peak_max_voltage, voltage_units, 'base')

            # First apply the general voltage range
            voltage_mask = (p_raw >= low_voltage) & (p_raw <= high_voltage)

            # Then apply peak detection range if specified
            if peak_min_voltage is not None or peak_max_voltage is not None:
                if peak_min_voltage is not None:
                    voltage_mask = voltage_mask & (p_raw >= peak_min_voltage)
                if peak_max_voltage is not None:
                    voltage_mask = voltage_mask & (p_raw <= peak_max_voltage)

            p_adj, i_adj = p_raw[voltage_mask].tolist(), i_raw[voltage_mask].tolist()

            if len(p_adj) < 3:
                continue  # Not enough data in range

            # Calculate baseline
            if params['mass_transport'] == 'surface':
                baseline = _baseline_surface_bound(p_adj, i_adj)
            else:  # solution
                baseline = _baseline_solution_phase(p_adj, i_adj)

            i_corrected = np.array(i_adj) - np.array(baseline)

            # Find peak
            peak_idx = np.argmax(np.abs(i_corrected))
            peak_potential = p_adj[peak_idx]
            peak_current = i_corrected[peak_idx]  # This is the peak height

            # Calculate area under curve (charge)
            scan_rate = params.get('scan_rate', 0.1)
            if scan_rate <= 0:
                scan_rate = 0.1  # Default scan rate

            charge = np.trapz(np.abs(i_corrected), x=p_adj) / scan_rate  # Convert to charge

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

            # Store results for this segment
            results[scan_type] = {
                'potentials': p_adj,
                'currents': i_adj,
                'baseline': baseline,
                'corrected_currents': i_corrected.tolist(),
                'peak_potential': peak_potential,
                'peak_current': peak_current,
                'charge': charge,
                'peak_width': peak_width,
                'half_peak_potential': half_peak_potential,
                'auc_vertices': list(zip(p_adj, np.maximum(0, i_corrected)))  # For shading
            }

            logger.info(f"CV {scan_type} analysis completed successfully:")
            logger.info(f"  - Data points: {len(p_adj)}")
            logger.info(f"  - Peak potential: {peak_potential}")
            logger.info(f"  - Peak current: {peak_current}")
            logger.info(f"  - Charge: {charge}")

        # Step 3: Calculate peak separation
        if results["forward"].get("peak_potential") is not None and results["reverse"].get(
                "peak_potential") is not None:
            results["peak_separation"] = abs(
                results["forward"]["peak_potential"] - results["reverse"]["peak_potential"])
            logger.info(f"CV peak separation calculated: {results['peak_separation']}")

        # Log final results summary
        logger.info(f"CV analysis final results for {file_path}:")
        logger.info(f"  - Forward data available: {bool(results['forward'])}")
        logger.info(f"  - Reverse data available: {bool(results['reverse'])}")
        logger.info(f"  - Peak separation: {results.get('peak_separation', 'N/A')}")
        logger.info(f"  - Status: {results['status']}")

        return results

    except Exception as e:
        logger.error(f"Critical error in CV analysis for {file_path}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
