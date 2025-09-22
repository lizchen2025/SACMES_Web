# data_processing/excel_exporter.py
"""
Enhanced Excel export functionality for SWV data with multi-sheet support
Includes metadata, QC results, and filtering parameters for each electrode
"""

import pandas as pd
import io
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def create_metadata_dict():
    """
    Create metadata dictionary with timestamp and system information.

    Returns:
        dict: Metadata information
    """
    return {
        'Export Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Software': 'SACMES Analysis System',
        'Version': '1.0',
        'Analysis Type': 'SWV (Square Wave Voltammetry)',
        'Data Processing': 'Hampel + Savitzky-Golay Filtering with QC'
    }


def format_qc_status(qc_results):
    """
    Format QC results into readable strings.

    Args:
        qc_results: QC results dictionary

    Returns:
        dict: Formatted QC information
    """
    if not qc_results:
        return {
            'QC Status': 'NOT AVAILABLE',
            'SNR Improvement (dB)': 'N/A',
            'Peak Preservation (%)': 'N/A',
            'Residual (%)': 'N/A',
            'Hampel Trigger Rate (%)': 'N/A'
        }

    return {
        'QC Status': qc_results.get('status', 'UNKNOWN'),
        'SNR Improvement (dB)': f"{qc_results.get('snr_improvement', 0):.2f}",
        'Peak Preservation (%)': f"{qc_results.get('peak_preservation', 0):.1f}",
        'Residual (%)': f"{qc_results.get('residual_percentage', 0):.1f}",
        'Hampel Trigger Rate (%)': f"{qc_results.get('hampel_trigger_rate', 0):.1f}"
    }


def format_filter_parameters(filtering_metadata):
    """
    Format filtering parameters into readable strings.

    Args:
        filtering_metadata: Filtering metadata dictionary

    Returns:
        dict: Formatted filter parameters
    """
    if not filtering_metadata:
        return {
            'Filter Mode': 'Legacy SG Only',
            'FWHM (V)': 'N/A',
            'Hampel Window': 'N/A',
            'Hampel Threshold': 'N/A',
            'SG Window': 'N/A',
            'SG Polynomial Order': 'N/A',
            'Outliers Detected': 'N/A'
        }

    hampel_params = filtering_metadata.get('hampel_params', {})
    sg_params = filtering_metadata.get('sg_params', {})

    filter_mode = 'Auto (FWHM-based)' if hampel_params.get('auto_mode', True) else 'Manual'

    return {
        'Filter Mode': filter_mode,
        'FWHM (V)': f"{filtering_metadata.get('fwhm', 0):.4f}" if filtering_metadata.get('fwhm') else 'N/A',
        'Hampel Window': str(hampel_params.get('window_size', 'N/A')),
        'Hampel Threshold': f"{hampel_params.get('threshold', 3.0):.1f}",
        'SG Window': str(sg_params.get('window_length', 'N/A')),
        'SG Polynomial Order': str(sg_params.get('polyorder', 'N/A')),
        'Outliers Detected': str(filtering_metadata.get('outlier_count', 'N/A'))
    }


def create_electrode_dataframe(electrode_data, electrode_index):
    """
    Create a comprehensive DataFrame for a single electrode's data.

    Args:
        electrode_data: Dictionary containing all analysis data for the electrode
        electrode_index: Index of the electrode (for naming purposes)

    Returns:
        pd.DataFrame: Formatted data for the electrode
    """
    try:
        data_rows = []

        # Extract frequency data
        frequencies = list(electrode_data.keys())
        frequencies.sort(key=int)  # Sort numerically

        for freq in frequencies:
            freq_data = electrode_data[freq]

            # Sort file numbers
            file_numbers = sorted(freq_data.keys(), key=int)

            for file_num in file_numbers:
                analysis_result = freq_data[file_num]

                # Basic data
                row = {
                    'Frequency (Hz)': int(freq),
                    'File Number': int(file_num),
                    'Peak Value': analysis_result.get('peak_value', 'N/A'),
                    'Status': analysis_result.get('status', 'Unknown'),
                    'Warning Type': analysis_result.get('warning_type', 'None')
                }

                # Add filtering metadata if available
                filtering_metadata = analysis_result.get('filtering_metadata', {})
                filter_params = format_filter_parameters(filtering_metadata)
                row.update(filter_params)

                # Add QC results if available
                qc_results = filtering_metadata.get('qc_results', {}) if filtering_metadata else {}
                qc_formatted = format_qc_status(qc_results)
                row.update(qc_formatted)

                data_rows.append(row)

        if not data_rows:
            # Create empty row if no data
            return pd.DataFrame([{'Error': 'No data available for this electrode'}])

        df = pd.DataFrame(data_rows)
        return df

    except Exception as e:
        logger.error(f"Failed to create DataFrame for electrode {electrode_index}: {e}")
        return pd.DataFrame([{'Error': f'Failed to process electrode data: {str(e)}'}])


def export_swv_data_to_excel(electrode_data_dict, analysis_params=None):
    """
    Export SWV analysis data to Excel with multiple sheets.

    Args:
        electrode_data_dict: Dictionary with electrode indices as keys and analysis data as values
        analysis_params: Analysis parameters used

    Returns:
        bytes: Excel file as bytes object
    """
    try:
        # Create BytesIO buffer for Excel file
        output = io.BytesIO()

        # Create Excel writer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:

            # Create metadata
            metadata = create_metadata_dict()
            if analysis_params:
                metadata.update({
                    'Baseline Strategy': analysis_params.get('baseline_strategy', 'original'),
                    'Calculation Method': analysis_params.get('SelectedOptions', 'Peak Height Extraction'),
                    'Filter Mode': analysis_params.get('filter_mode', 'auto'),
                    'Selected Electrodes': str(analysis_params.get('selected_electrodes', [])),
                    'Frequency Range': str(analysis_params.get('frequencies', [])),
                    'File Range': f"{analysis_params.get('range_start', 'N/A')}-{analysis_params.get('range_end', 'N/A')}"
                })

            # Convert metadata to DataFrame and write to Summary sheet
            metadata_df = pd.DataFrame(list(metadata.items()), columns=['Parameter', 'Value'])
            metadata_df.to_excel(writer, sheet_name='Summary', index=False)

            # Check if we have electrode-specific data or averaged data
            if isinstance(electrode_data_dict, dict) and electrode_data_dict:
                electrode_keys = list(electrode_data_dict.keys())

                # If keys are electrode indices
                if all(isinstance(k, (int, str)) and str(k).isdigit() for k in electrode_keys):
                    # Multi-electrode data
                    for electrode_idx, electrode_data in electrode_data_dict.items():
                        electrode_df = create_electrode_dataframe(electrode_data, electrode_idx)

                        # Create sheet name
                        sheet_name = f'Electrode_{int(electrode_idx)+1}'  # Convert to 1-based naming
                        electrode_df.to_excel(writer, sheet_name=sheet_name, index=False)

                        # Add metadata header to each electrode sheet
                        worksheet = writer.sheets[sheet_name]

                        # Insert metadata rows at the top
                        worksheet.insert_rows(1, len(metadata) + 2)

                        # Write metadata
                        for idx, (key, value) in enumerate(metadata.items(), 1):
                            worksheet.cell(row=idx, column=1, value=key)
                            worksheet.cell(row=idx, column=2, value=value)

                        # Add separator
                        worksheet.cell(row=len(metadata) + 2, column=1, value='=== DATA ===')

                elif 'averaged' in electrode_keys or len(electrode_keys) == 1:
                    # Averaged data or single data set
                    data_key = 'averaged' if 'averaged' in electrode_keys else electrode_keys[0]
                    electrode_data = electrode_data_dict[data_key]
                    electrode_df = create_electrode_dataframe(electrode_data, 'Averaged')

                    electrode_df.to_excel(writer, sheet_name='Averaged_Data', index=False)

                    # Add metadata header
                    worksheet = writer.sheets['Averaged_Data']
                    worksheet.insert_rows(1, len(metadata) + 2)

                    for idx, (key, value) in enumerate(metadata.items(), 1):
                        worksheet.cell(row=idx, column=1, value=key)
                        worksheet.cell(row=idx, column=2, value=value)

                    worksheet.cell(row=len(metadata) + 2, column=1, value='=== DATA ===')

                else:
                    # Fallback: treat as single data set
                    logger.warning(f"Unexpected electrode data structure: {electrode_keys}")
                    error_df = pd.DataFrame([{'Error': 'Unexpected data structure', 'Keys': str(electrode_keys)}])
                    error_df.to_excel(writer, sheet_name='Error', index=False)

            else:
                # No data available
                error_df = pd.DataFrame([{'Error': 'No electrode data available for export'}])
                error_df.to_excel(writer, sheet_name='No_Data', index=False)

        # Get the bytes
        output.seek(0)
        excel_bytes = output.read()
        output.close()

        logger.info(f"Successfully created Excel file with {len(electrode_data_dict) if electrode_data_dict else 0} electrode(s)")
        return excel_bytes

    except Exception as e:
        logger.error(f"Failed to export Excel data: {e}")
        # Create error Excel file
        error_output = io.BytesIO()
        error_df = pd.DataFrame([{'Error': f'Export failed: {str(e)}', 'Timestamp': datetime.now()}])

        with pd.ExcelWriter(error_output, engine='openpyxl') as writer:
            error_df.to_excel(writer, sheet_name='Export_Error', index=False)

        error_output.seek(0)
        error_bytes = error_output.read()
        error_output.close()

        return error_bytes


def convert_to_csv_fallback(electrode_data_dict):
    """
    Fallback CSV export if Excel export fails.

    Args:
        electrode_data_dict: Dictionary with electrode data

    Returns:
        str: CSV formatted string
    """
    try:
        # Create a simple CSV format
        csv_lines = ['# SACMES SWV Analysis Export (CSV Fallback)']
        csv_lines.append(f'# Export Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        csv_lines.append('')

        # CSV headers
        csv_lines.append('Electrode,Frequency_Hz,File_Number,Peak_Value,Status,Warning_Type,QC_Status')

        for electrode_idx, electrode_data in electrode_data_dict.items():
            frequencies = list(electrode_data.keys())
            frequencies.sort(key=int)

            for freq in frequencies:
                freq_data = electrode_data[freq]
                file_numbers = sorted(freq_data.keys(), key=int)

                for file_num in file_numbers:
                    analysis_result = freq_data[file_num]

                    # Extract basic data for CSV
                    electrode_name = f'Electrode_{int(electrode_idx)+1}' if str(electrode_idx).isdigit() else str(electrode_idx)
                    peak_value = analysis_result.get('peak_value', 'N/A')
                    status = analysis_result.get('status', 'Unknown')
                    warning_type = analysis_result.get('warning_type', 'None')

                    # Get QC status
                    filtering_metadata = analysis_result.get('filtering_metadata', {})
                    qc_results = filtering_metadata.get('qc_results', {}) if filtering_metadata else {}
                    qc_status = qc_results.get('status', 'N/A')

                    csv_line = f'{electrode_name},{freq},{file_num},{peak_value},{status},{warning_type},{qc_status}'
                    csv_lines.append(csv_line)

        return '\n'.join(csv_lines)

    except Exception as e:
        logger.error(f"CSV fallback also failed: {e}")
        return f"# Export Error: {str(e)}\n# Timestamp: {datetime.now()}"