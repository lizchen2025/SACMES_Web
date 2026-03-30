import numpy as np


def ReadData(myfile, voltage_column_index, current_column_start_index, spacing_index, num_electrodes, delimiter_char, file_extension=".txt", selected_electrodes=None):
    """Read multichannel electrochemical data from text-like files.

    If ``selected_electrodes`` is provided, rows missing any requested electrode are
    discarded. In averaged mode, rows are averaged only across the electrodes that
    have numeric values on that row. Missing columns are never coerced to zero.
    """
    potentials = []
    data_dict = {}
    currents_raw_per_electrode = [[] for _ in range(num_electrodes)]
    requested_electrodes = set(selected_electrodes or [])
    encoding = "utf-8"

    try:
        with open(myfile, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        encoding = "utf-16"
        with open(myfile, "r", encoding=encoding) as f:
            lines = f.readlines()

    if file_extension.lower() == ".dta":
        start_index = 0
        found_curve_table = False
        for i, line in enumerate(lines):
            if "CURVE" in line and "TABLE" in line:
                found_curve_table = True
                start_index = i + 2
                break
        if not found_curve_table:
            for i, line in enumerate(lines):
                if line.strip() and (line[0].isdigit() or line[0] in ["-", "+"]):
                    start_index = i
                    break
        lines = lines[start_index:]

    def _parse_float(parts, index):
        if index >= len(parts):
            return None
        value_str = parts[index].replace(",", "").strip()
        if value_str == "":
            return None
        try:
            return float(value_str)
        except ValueError:
            return None

    for line in lines:
        check_split_list = line.split(delimiter_char)
        while check_split_list and check_split_list[0].strip() == "":
            del check_split_list[0]

        if len(check_split_list) <= max(voltage_column_index, current_column_start_index):
            continue

        potential_value = _parse_float(check_split_list, voltage_column_index)
        if potential_value is None:
            continue

        row_currents = []
        valid_electrode_count = 0
        for i in range(num_electrodes):
            current_col_index = current_column_start_index + i * spacing_index
            current_value = _parse_float(check_split_list, current_col_index)
            row_currents.append(current_value)
            if current_value is not None:
                valid_electrode_count += 1

        if valid_electrode_count == 0:
            continue

        if requested_electrodes and any(
            electrode_idx >= len(row_currents) or row_currents[electrode_idx] is None
            for electrode_idx in requested_electrodes
        ):
            continue

        potentials.append(potential_value)
        for i, current_val in enumerate(row_currents):
            currents_raw_per_electrode[i].append(current_val)

    row_count = len(potentials)
    if row_count == 0:
        if selected_electrodes is not None:
            return {"detected_electrodes": 0}
        return {
            "voltage": [],
            "current": [],
            "data_dict": {},
            "detected_electrodes": 0
        }

    detected_electrodes = 0
    for i, electrode_currents in enumerate(currents_raw_per_electrode):
        if any(current is not None for current in electrode_currents):
            detected_electrodes = i + 1

    if selected_electrodes is not None:
        electrodes_data = {}
        for electrode_idx in selected_electrodes:
            if 0 <= electrode_idx < len(currents_raw_per_electrode):
                electrode_currents = currents_raw_per_electrode[electrode_idx]
                normalized_currents = list(electrode_currents) if len(electrode_currents) == row_count and all(
                    current is not None for current in electrode_currents
                ) else []
                electrodes_data[electrode_idx] = {
                    "potentials": potentials.copy(),
                    "currents": normalized_currents,
                    "data_dict": {potentials[i]: [normalized_currents[i]] for i in range(len(potentials))} if normalized_currents else {}
                }
        electrodes_data["detected_electrodes"] = detected_electrodes
        return electrodes_data

    averaged_potentials = []
    averaged_currents = []
    for row_idx, potential in enumerate(potentials):
        valid_currents = [
            electrode_currents[row_idx]
            for electrode_currents in currents_raw_per_electrode
            if row_idx < len(electrode_currents) and electrode_currents[row_idx] is not None
        ]
        if not valid_currents:
            continue

        averaged_current = float(np.mean(valid_currents))
        averaged_potentials.append(potential)
        averaged_currents.append(averaged_current)
        data_dict.setdefault(potential, []).append(averaged_current)

    return {
        "voltage": averaged_potentials,
        "current": averaged_currents,
        "data_dict": data_dict,
        "detected_electrodes": detected_electrodes
    }
