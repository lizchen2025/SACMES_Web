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
        logger.error(f"=== Simple CV Data Reading ===")
        logger.error(f"File: {file_path}")
        logger.error(f"Selected electrode: {selected_electrode}")

        # Read all data as space-separated values
        data = np.loadtxt(file_path, delimiter=' ')
        logger.error(f"Data shape: {data.shape}")

        # Extract potentials (first column)
        potentials = data[:, 0].tolist()

        # Extract currents
        if selected_electrode is not None and selected_electrode >= 0:
            # Specific electrode (1-based column indexing: electrode 0 = column 1, etc.)
            electrode_column = selected_electrode + 1
            if electrode_column < data.shape[1]:
                currents = data[:, electrode_column].tolist()
                logger.error(f"Using electrode {selected_electrode} (column {electrode_column})")
            else:
                logger.error(f"Electrode {selected_electrode} not available (only {data.shape[1]-1} electrodes)")
                return [], []
        else:
            # Average all electrodes (columns 1 to end)
            if data.shape[1] > 1:
                currents = np.mean(data[:, 1:], axis=1).tolist()
                logger.error(f"Using averaged data from {data.shape[1]-1} electrodes")
            else:
                logger.error("No current columns found")
                return [], []

        logger.error(f"Successfully read {len(potentials)} data points")
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
    # Use the simple CV reader instead of complex parameter-based reader
    potentials, currents = _read_cv_data_simple(file_path, selected_electrode)

    if not potentials or not currents:
        return [], [], {}

    # For CV data, assume correct units (V for potential, A for current)
    # We'll convert current to microAmps for consistency with existing code
    currents = [c * 1e6 for c in currents]  # Convert A to µA

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
