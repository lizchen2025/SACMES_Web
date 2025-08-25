import numpy as np

def ReadData(myfile, voltage_column_index, current_column_start_index, spacing_index, num_electrodes, delimiter_char, file_extension=".txt"):
    """Enhanced ReadData to support Gamry .DTA files by skipping header lines."""
    potentials = []
    currents_raw_per_electrode = [[] for _ in range(num_electrodes)]
    data_dict = {}
    encoding = "utf-8"

    # --- Detect encoding ---
    try:
        with open(myfile, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        encoding = "utf-16"
        with open(myfile, "r", encoding=encoding) as f:
            lines = f.readlines()

    # --- Handle Gamry .DTA files ---
    if file_extension.lower() == ".dta": # Explicitly check for .dta extension
        start_index = 0
        found_curve_table = False
        for i, line in enumerate(lines):
            if "CURVE" in line and "TABLE" in line: # Look for "CURVE TABLE" to mark the start of data section header
                found_curve_table = True
                # The next line after "CURVE TABLE" is usually the column headers
                # The actual data starts after the header line.
                start_index = i + 2 # Skip "CURVE TABLE" and the header row below it.
                break
        if not found_curve_table: # Fallback if "CURVE TABLE" is not found (though unlikely for valid DTA)
            # Try to find the first line that looks like data if CURVE TABLE isn't explicit
            for i, line in enumerate(lines):
                if line.strip() and (line[0].isdigit() or line[0] in ['-', '+']):
                    start_index = i
                    break
        lines = lines[start_index:]
    # --- End Handle Gamry .DTA files ---

    # --- Parse numeric lines ---
    for line in lines:
        check_split_list = line.split(delimiter_char)
        while check_split_list and check_split_list[0].strip() == "":
            del check_split_list[0]

        max_needed_column = voltage_column_index
        for i in range(num_electrodes):
            current_col_index = current_column_start_index + i * spacing_index
            if current_col_index > max_needed_column:
                max_needed_column = current_col_index

        # Add an additional check to ensure enough columns are present for potential and at least one current
        if len(check_split_list) <= max(voltage_column_index, current_column_start_index):
            continue

        try:
            # Check if the potential column can be converted to float
            float(check_split_list[voltage_column_index].replace(",", "").strip())
            is_data_line = True
        except (ValueError, IndexError):
            is_data_line = False

        if is_data_line:
            try:
                potential_value_str = check_split_list[voltage_column_index].replace(",", "").strip()
                potential_value = float(potential_value_str)
                potentials.append(potential_value)

                currents_for_this_line = []
                for i in range(num_electrodes):
                    current_col_index = current_column_start_index + i * spacing_index
                    # Ensure current_col_index is within bounds before accessing
                    if current_col_index < len(check_split_list):
                        current_value_str = check_split_list[current_col_index].replace(",", "").strip()
                        current_value = float(current_value_str) * 1e6  # Convert to microAmps
                        currents_for_this_line.append(current_value)
                    else:
                        # If a current column is missing, append None or 0 and log a warning
                        # For robustness, we'll just append 0 and assume incomplete data for this electrode
                        # Or, you might choose to skip the entire line if a required current column is missing.
                        # For now, let's append 0 and continue to allow averaging of available electrodes.
                        currents_for_this_line.append(0.0)
                        # Optional: logger.warning(f"Missing current data for electrode {i+1} in line: {line.strip()}")

                for i, current_val in enumerate(currents_for_this_line):
                    # Ensure we have enough sublists for all electrodes
                    while len(currents_raw_per_electrode) <= i:
                        currents_raw_per_electrode.append([])
                    currents_raw_per_electrode[i].append(current_val)

            except (ValueError, IndexError) as e:
                # If an error occurs during parsing a data line, remove the last added potential
                # to keep potentials and currents aligned.
                if potentials and len(potentials) > len(currents_raw_per_electrode[0]):
                    potentials.pop()
                # Optional: log the error for debugging
                # logger.error(f"Error parsing data line: {line.strip()} - {e}")
                pass

    # --- Average currents ---
    averaged_currents = []
    # Ensure all electrode lists have the same length before transposing
    min_len = len(potentials)
    if currents_raw_per_electrode:
        for sublist in currents_raw_per_electrode:
            if len(sublist) < min_len:
                min_len = len(sublist)

    if min_len < len(potentials):
        potentials = potentials[:min_len]
        # Trim current lists if they are longer than the new min_len
        for i in range(len(currents_raw_per_electrode)):
            currents_raw_per_electrode[i] = currents_raw_per_electrode[i][:min_len]


    if num_electrodes > 0 and currents_raw_per_electrode and all(len(sublist) == min_len for sublist in currents_raw_per_electrode):
        if min_len > 0:
            currents_transposed = np.array(currents_raw_per_electrode).T
            averaged_currents = np.mean(currents_transposed, axis=1).tolist()

            # Ensure data_dict is populated correctly with averaged currents
            for i in range(len(potentials)):
                data_dict.setdefault(potentials[i], []).append(averaged_currents[i])
    else:
        # Handle case where no valid currents could be read or lengths mismatch after trimming
        averaged_currents = []
        potentials = [] # Clear potentials if no valid averaged currents can be formed.

    return potentials, averaged_currents, data_dict
