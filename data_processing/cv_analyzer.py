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

def _read_cv_data_simple(file_path, selected_electrode=None):
    """
    Simple CV data reader for the standard CV format.

    CV files have a simple format:
    - Column 1: Potential (V)
    - Column 2-N: Current for each electrode (A)

    Args:
        file_path (str): Path to CV file
        selected_electrode (int): Electrode index (0-based), None for averaged

    Returns:
        tuple: (potentials, currents) or ([], []) if failed
    """
    try:
        logger.info(f"=== Simple CV Data Reading ===")
        logger.info(f"File: {file_path}")
        logger.info(f"Selected electrode: {selected_electrode}")

        # First try to read with space delimiter
        try:
            data = np.loadtxt(file_path, delimiter=' ')
        except:
            # Try tab delimiter if space fails
            try:
                data = np.loadtxt(file_path, delimiter='\t')
            except:
                # Try comma delimiter if tab fails
                try:
                    data = np.loadtxt(file_path, delimiter=',')
                except:
                    # Try automatic delimiter detection
                    data = np.loadtxt(file_path)

        logger.info(f"Data shape: {data.shape}")

        if data.size == 0:
            logger.error("No data found in file")
            return [], []

        # Ensure data is 2D
        if data.ndim == 1:
            if len(data) >= 2:
                # Assume first half is potentials, second half is currents
                mid = len(data) // 2
                potentials = data[:mid].tolist()
                currents = data[mid:].tolist()
                logger.info(f"1D data split into potentials and currents")
            else:
                logger.error("Insufficient 1D data")
                return [], []
        else:
            # Extract potentials (first column)
            potentials = data[:, 0].tolist()

            # Extract currents
            if selected_electrode is not None and selected_electrode >= 0:
                # Specific electrode (1-based column indexing: electrode 0 = column 1, etc.)
                electrode_column = selected_electrode + 1
                if electrode_column < data.shape[1]:
                    currents = data[:, electrode_column].tolist()
                    logger.info(f"Using electrode {selected_electrode} (column {electrode_column})")
                else:
                    logger.warning(f"Electrode {selected_electrode} not available (only {data.shape[1]-1} electrodes)")
                    return [], []
            else:
                # Average all electrodes (columns 1 to end)
                if data.shape[1] > 1:
                    currents = np.mean(data[:, 1:], axis=1).tolist()
                    logger.info(f"Using averaged data from {data.shape[1]-1} electrodes")
                else:
                    logger.warning("No current columns found")
                    return [], []

        logger.info(f"Successfully read {len(potentials)} data points")
        return potentials, currents

    except Exception as e:
        logger.error(f"Simple CV reader failed: {e}")
        return [], []


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
    # Use the robust GeneralReadData function with proper parameters
    try:
        # Extract parameters from the front-end settings
        voltage_column = params.get('voltage_column', 1)  # 1-based from frontend
        current_column = params.get('current_column', 2)  # 1-based from frontend
        spacing_index = params.get('spacing_index', 1)
        delimiter_num = params.get('delimiter', 1)
        file_extension = params.get('file_extension', '.txt')
        num_electrodes = params.get('num_electrodes', 1)

        # Convert delimiter number to character
        delimiter_map = {1: ' ', 2: '\t', 3: ',', 4: ';'}
        delimiter_char = delimiter_map.get(delimiter_num, ' ')

        # Convert to 0-based indices for GeneralReadData function
        voltage_column_0based = voltage_column - 1
        current_column_0based = current_column - 1

        logger.info(f"CV segment detection using: voltage_col={voltage_column}(0-based: {voltage_column_0based}), current_col={current_column}(0-based: {current_column_0based}), delimiter='{delimiter_char}', electrodes={num_electrodes}")

        # Call the robust data reader with 0-based indices
        data_result = GeneralReadData(
            file_path,
            voltage_column_0based,
            current_column_0based,
            spacing_index,
            num_electrodes,
            delimiter_char,
            file_extension
        )

        if not data_result or 'voltage' not in data_result or 'current' not in data_result:
            logger.error("GeneralReadData returned invalid result")
            return [], [], {}

        potentials = data_result['voltage']

        # Handle electrode selection for CV
        if selected_electrode is not None and selected_electrode >= 0:
            # Use specific electrode data if available
            electrode_key = f'electrode_{selected_electrode}'
            if electrode_key in data_result:
                currents = data_result[electrode_key]
                logger.info(f"Using electrode {selected_electrode} data for segment detection")
            else:
                currents = data_result['current']  # Fall back to averaged
                logger.warning(f"Electrode {selected_electrode} not found, using averaged data")
        else:
            currents = data_result['current']  # Averaged data
            logger.info("Using averaged electrode data for segment detection")

    except Exception as e:
        logger.error(f"Failed to read CV data with GeneralReadData: {e}")
        # Fallback to simple reader if GeneralReadData fails
        logger.info("Falling back to simple CV reader")
        potentials, currents = _read_cv_data_simple(file_path, selected_electrode)

    if not potentials or not currents:
        return [], [], {}

    # For CV data, assume correct units (V for potential, A for current)
    # We'll convert current to microAmps for consistency with existing code
    currents = [c * 1e6 for c in currents]  # Convert A to µA

    # --- Enhanced CV Segment Detection Logic (Based on SACMES_CV.py) ---
    segment_dictionary = {}
    forward_segments = {}
    reverse_segments = {}

    if len(potentials) < 3:  # Need at least 3 points to detect direction changes
        return potentials, currents, {}

    logger.info(f"CV Segment Detection: Processing {len(potentials)} data points")

    # Determine initial scan direction from the first meaningful step
    initial_step = None
    for i in range(1, min(10, len(potentials))):  # Check first few points for direction
        step = potentials[i] - potentials[i-1]
        if abs(step) > 1e-6:  # Avoid noise/zero steps
            initial_step = "Positive" if step > 0 else "Negative"
            break

    if initial_step is None:
        logger.warning("Could not determine initial scan direction")
        return potentials, currents, {}

    logger.info(f"Initial scan direction: {initial_step}")

    # Create step direction list
    step_list = []
    for i in range(1, len(potentials)):
        step = potentials[i] - potentials[i-1]
        if abs(step) > 1e-6:  # Filter out noise
            step_direction = "Positive" if step > 0 else "Negative"
        else:
            step_direction = step_list[-1] if step_list else initial_step  # Keep previous direction for tiny steps
        step_list.append(step_direction)

    # Detect segments based on sustained direction changes
    segment_number = 1
    segment_dictionary[segment_number] = []
    current_indices = [0]  # Start with first point

    for i in range(1, len(potentials)):
        current_indices.append(i)

        # Check for direction change (need consistent change over multiple points)
        if i >= 2:  # Need at least 2 steps to compare
            # Look for sustained direction change (not just single point fluctuation)
            current_direction = step_list[i-1]
            previous_direction = step_list[i-2] if i >= 2 else initial_step

            # Check if we have a consistent direction change over several points
            if current_direction != previous_direction:
                # Verify this is a real direction change by looking ahead
                is_real_change = True
                look_ahead = min(5, len(potentials) - i)  # Look ahead up to 5 points
                if look_ahead > 1:
                    consistent_count = 0
                    for j in range(1, look_ahead):
                        if i + j < len(step_list) and step_list[i + j - 1] == current_direction:
                            consistent_count += 1

                    # Only create new segment if direction change is sustained
                    if consistent_count < look_ahead // 2:
                        is_real_change = False

                if is_real_change:
                    # Finalize current segment
                    segment_dictionary[segment_number] = {
                        'indices': list(current_indices[:-1]),  # Don't include the turning point yet
                        'potentials': [potentials[j] for j in current_indices[:-1]],
                        'currents': [currents[j] for j in current_indices[:-1]],
                        'direction': previous_direction,
                        'type': 'forward' if previous_direction == initial_step else 'reverse'
                    }

                    # Classify the completed segment
                    if previous_direction == initial_step:
                        forward_segments[segment_number] = segment_dictionary[segment_number]
                    else:
                        reverse_segments[segment_number] = segment_dictionary[segment_number]

                    # Start new segment with the turning point
                    segment_number += 1
                    current_indices = [i-1, i]  # Include turning point in new segment
                    segment_dictionary[segment_number] = []

    # Finalize the last segment
    if current_indices:
        last_direction = step_list[-1] if step_list else initial_step
        segment_dictionary[segment_number] = {
            'indices': list(current_indices),
            'potentials': [potentials[j] for j in current_indices],
            'currents': [currents[j] for j in current_indices],
            'direction': last_direction,
            'type': 'forward' if last_direction == initial_step else 'reverse'
        }

        # Classify the final segment
        if last_direction == initial_step:
            forward_segments[segment_number] = segment_dictionary[segment_number]
        else:
            reverse_segments[segment_number] = segment_dictionary[segment_number]

    # Remove empty segments
    segment_dictionary = {k: v for k, v in segment_dictionary.items() if v and len(v.get('indices', [])) > 0}

    logger.info(f"CV Segment Detection Results:")
    logger.info(f"  - Total segments detected: {len(segment_dictionary)}")
    logger.info(f"  - Forward segments: {list(forward_segments.keys())}")
    logger.info(f"  - Reverse segments: {list(reverse_segments.keys())}")

    # Store segment classification for later use
    for seg_num, seg_data in segment_dictionary.items():
        seg_data['is_forward'] = seg_num in forward_segments
        seg_data['is_reverse'] = seg_num in reverse_segments

    return potentials, currents, segment_dictionary


def _baseline_surface_bound(potentials, currents):
    """Calculates a linear baseline for surface-bound species using first-last point connection."""
    # CV baseline: connect first and last points of the segment
    if len(potentials) < 2:
        return [0] * len(potentials)

    first_potential, first_current = potentials[0], currents[0]
    last_potential, last_current = potentials[-1], currents[-1]

    # Create linear baseline from first to last point
    if first_potential == last_potential:  # Avoid division by zero
        slope = 0
    else:
        slope = (last_current - first_current) / (last_potential - first_potential)

    intercept = first_current - slope * first_potential
    baseline_currents = [(slope * p + intercept) for p in potentials]

    logger.error(f"CV baseline created: first({first_potential:.3f}V, {first_current:.3e}A) -> last({last_potential:.3f}V, {last_current:.3e}A)")
    return baseline_currents


def _baseline_solution_phase(potentials, currents):
    """For solution-phase, also use first-last point connection for consistency."""
    # For CV, both surface and solution use the same baseline approach
    return _baseline_surface_bound(potentials, currents)


# --- Main Public Functions ---

def get_cv_segments(file_path, params, selected_electrode=None):
    """
    Performs a preliminary analysis on a CV file just to get the available segments.

    Args:
        file_path (str): Path to the data file.
        params (dict): Analysis parameters.
        selected_electrode (int): Index of specific electrode to analyze (0-based).

    Returns:
        dict: A dictionary containing the status, segment numbers, and classification info.
    """
    try:
        _, _, segment_dictionary = _read_and_segment_data(file_path, params, selected_electrode)
        if not segment_dictionary:
            return {"status": "error", "message": "No data or segments found."}

        # Organize segments by type for better frontend handling
        forward_segments = []
        reverse_segments = []
        all_segments = []

        for seg_num, seg_data in segment_dictionary.items():
            all_segments.append(seg_num)
            segment_type = seg_data.get('type', 'unknown')
            if segment_type == 'forward' or seg_data.get('is_forward', False):
                forward_segments.append(seg_num)
            elif segment_type == 'reverse' or seg_data.get('is_reverse', False):
                reverse_segments.append(seg_num)

        logger.info(f"Segment classification: Forward={forward_segments}, Reverse={reverse_segments}")

        return {
            "status": "success",
            "segments": all_segments,
            "forward_segments": forward_segments,
            "reverse_segments": reverse_segments,
            "total_segments": len(all_segments),
            "segment_info": {
                str(seg_num): {
                    "type": seg_data.get('type', 'unknown'),
                    "direction": seg_data.get('direction', 'unknown'),
                    "points": len(seg_data.get('indices', [])),
                    "potential_range": [
                        min(seg_data.get('potentials', [0])),
                        max(seg_data.get('potentials', [0]))
                    ] if seg_data.get('potentials') else [0, 0],
                    "potentials": seg_data.get('potentials', []),
                    "currents": seg_data.get('currents', [])
                }
                for seg_num, seg_data in segment_dictionary.items()
            }
        }
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
