"""
Phase 1 Utilities: Raw Data → Adjusted Data

Wrapper functions for Phase 1 processing.
Imports the actual functions from the original analysis code.
"""

import pandas as pd
import numpy as np
import os
import re
from io import BytesIO, StringIO
import tempfile
import importlib.util

# Import DIRECTLY from the main QCMD flow file
spec = importlib.util.spec_from_file_location("QCMD_flow_raw_to_adj_folder",
                                               os.path.join(os.path.dirname(__file__), "QCMD_flow_raw_to_adj_folder.py"))
qcmd_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qcmd_module)

_process_rawdata_original = qcmd_module.process_rawdata
_read_timeline_data_original = qcmd_module.read_timeline_data


def extract_experiment_id_from_filename(filename: str) -> str:
    """
    Extract experiment ID from Data_*.txt filename format.

    Expected format: Data_EXPERIMENT_ID_rawdata.txt or Data_EXPERIMENT_ID_timeline.txt

    Returns:
        Experiment ID string, or None if format doesn't match
    """
    # Remove Data_ prefix and file suffix
    name = filename.replace("Data_", "")
    # Remove common suffixes
    for suffix in ["_rawdata.txt", "_timeline.txt", ".txt"]:
        if name.endswith(suffix):
            name = name.replace(suffix, "")
            return name
    return None


def extract_experiment_id_from_timeline_content(timeline_text: str) -> str:
    """
    Extract experiment ID from OPTION_B timeline metadata.

    OPTION_B: looks for "EXPERIMENT ID: ..."

    Returns:
        Experiment ID string, or None if not found
    """
    lines = timeline_text.strip().split('\n')
    for line in lines:
        if line.startswith('EXPERIMENT ID:'):
            return line.replace('EXPERIMENT ID:', '').strip()
    return None


def process_phase1(
    raw_file,
    timeline_file,
    lag_times: dict,
    persistent_id: str
) -> dict:
    """
    Process Phase 1: Raw → Adjusted Data

    Args:
        raw_file: Uploaded raw data file
        timeline_file: Uploaded timeline file
        lag_times: Dict with {sensor: lag_time_seconds}
        persistent_id: Experiment ID for naming

    Returns:
        {
            "adj_data_dict": {sensor: adjusted_data_df},
            "adj_timeline_dict": {sensor: adjusted_timeline_df},
            "validation_report": validation results
        }
    """

    # Read raw data from Streamlit UploadedFile
    raw_bytes = raw_file.getvalue()
    raw_data_df = pd.read_csv(
        BytesIO(raw_bytes),
        sep="\t",
        decimal=",",
        encoding="latin-1"
    )

    # Process raw data (normalize and convert to long format)
    persistent_id_extracted, sensors, adj_qcmd_data = process_rawdata(raw_data_df)

    # Read timeline from file
    timeline_text = timeline_file.getvalue().decode("utf-8")

    # Check experiment ID consistency from filenames
    raw_file_id = extract_experiment_id_from_filename(raw_file.name)
    timeline_file_id = extract_experiment_id_from_filename(timeline_file.name)

    if raw_file_id and timeline_file_id:
        # Both files have standard Data_*_*.txt naming
        if raw_file_id != timeline_file_id:
            raise ValueError(
                f"Filename mismatch - files are from different experiments:\n"
                f"  Raw data: {raw_file.name}\n"
                f"  Timeline: {timeline_file.name}\n\n"
                f"Make sure both files have matching experiment IDs in their filenames."
            )

    # Also check OPTION_B metadata if present
    timeline_content_id = extract_experiment_id_from_timeline_content(timeline_text)
    if timeline_content_id and raw_file_id and timeline_content_id != raw_file_id:
        raise ValueError(
            f"Experiment ID mismatch between filename and timeline metadata:\n"
            f"  Raw data filename: {raw_file_id}\n"
            f"  Timeline metadata: {timeline_content_id}\n\n"
            f"Make sure the EXPERIMENT ID in timeline metadata matches the filename."
        )

    # Process timeline
    timeline_df, validation_report = read_timeline_data(timeline_text, lag_times)

    # Handle timeline parsing errors
    if timeline_df is None:
        raise ValueError(
            f"Timeline processing failed:\n" +
            "\n".join(validation_report["messages"])
        )

    # Split by sensor
    adj_data_dict = {}
    adj_timeline_dict = {}

    for sensor in sensors:
        sensor_qcmd_data = adj_qcmd_data[adj_qcmd_data["Sensor"] == sensor].copy()
        del sensor_qcmd_data["Sensor"]

        adj_data_dict[sensor] = sensor_qcmd_data

        # Timeline for this sensor
        sensor_timeline = timeline_df[timeline_df["Sensor"] == sensor].copy()
        del sensor_timeline["Sensor"]

        adj_timeline_dict[sensor] = sensor_timeline

    return {
        "adj_data_dict": adj_data_dict,
        "adj_timeline_dict": adj_timeline_dict,
        "validation_report": validation_report
    }


def process_rawdata(raw_data_df: pd.DataFrame) -> tuple:
    """
    Process raw QCM-D data: normalize and convert to long format.
    Wrapper around the original function to handle Streamlit's in-memory data.
    """
    # Write to temp file (original expects file path)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        raw_data_df.to_csv(tmp.name, sep='\t', decimal=',', encoding='latin-1', index=False)
        tmp_path = tmp.name

    try:
        persistent_id, sensors, adj_qcmd_data = _process_rawdata_original(tmp_path)
        return persistent_id, sensors, adj_qcmd_data
    finally:
        os.unlink(tmp_path)


def parse_option_b_timeline(timeline_text: str) -> tuple:
    """
    Parse OPTION_B timeline format with metadata, solution registry, and timeline.

    Format:
        # EXPERIMENT METADATA
        EXPERIMENT ID: ...
        DATE: ...
        RESEARCHER: ...
        # SENSORS USED
        S1: ... | ...
        ...
        # SOLUTION REGISTRY
        ShortName | Full description
        ...
        # TIMELINE
        HH:MM:SS S{sensor} {speed}_ul-min {solution_name} [optional: (dynamic)]

    Returns:
        (solution_registry_dict, timeline_lines)
        - solution_registry_dict: {short_name: full_description}
        - timeline_lines: list of timeline text lines (without comments, stripped)

    Raises:
        ValueError: If format is invalid
    """
    lines = timeline_text.strip().split('\n')

    solution_registry = {}
    timeline_lines = []
    in_metadata_section = False
    in_solution_section = False
    in_timeline_section = False

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments within sections
        if not line or line.startswith('#'):
            if 'EXPERIMENT METADATA' in line or 'SENSORS USED' in line:
                in_metadata_section = True
                in_solution_section = False
                in_timeline_section = False
            elif 'SOLUTION REGISTRY' in line:
                in_metadata_section = False
                in_solution_section = True
                in_timeline_section = False
            elif 'TIMELINE' in line:
                in_timeline_section = True
                in_solution_section = False
                in_metadata_section = False
            continue

        # Parse solution registry
        if in_solution_section:
            if '|' not in line:
                raise ValueError(
                    f"Line {line_num} in SOLUTION REGISTRY: Missing '|' separator.\n"
                    f"Format should be: ShortName | Full description\n"
                    f"Got: {line}"
                )
            parts = line.split('|', 1)
            short_name = parts[0].strip()
            full_desc = parts[1].strip()

            if not short_name:
                raise ValueError(f"Line {line_num}: Solution short name cannot be empty")
            if not full_desc:
                raise ValueError(f"Line {line_num}: Solution description cannot be empty")

            solution_registry[short_name] = full_desc

        # Parse timeline
        elif in_timeline_section:
            timeline_lines.append(line)

    if not solution_registry:
        raise ValueError("No SOLUTION REGISTRY found. File must start with '# SOLUTION REGISTRY'")
    if not timeline_lines:
        raise ValueError("No TIMELINE found. File must have '# TIMELINE' section")

    return solution_registry, timeline_lines


def validate_option_b_timeline(timeline_lines: list, solution_registry: dict) -> list:
    """
    Validate OPTION_B timeline lines and convert to old format.

    Old format: HH:MM:SS S{sensor} {speed}_ul-min [changed to] {solution}
    OPTION_B format: HH:MM:SS S{sensor} {speed}_ul-min {solution_name} [optional: (dynamic)]

    Returns:
        list of timeline lines in old format

    Raises:
        ValueError: If validation fails
    """
    converted_lines = []
    valid_sensors = {'S1', 'S2', 'S3', 'S4'}

    for line_num, line in enumerate(timeline_lines, 1):
        parts = line.split()

        if len(parts) < 4:
            raise ValueError(
                f"Timeline line {line_num}: Too few fields.\n"
                f"Expected: HH:MM:SS S{{sensor}} {{speed}}_ul-min {{solution_name}} [optional: (dynamic)]\n"
                f"Got: {line}"
            )

        time_str = parts[0]
        sensor = parts[1]
        speed = parts[2]
        solution_name = parts[3]
        is_dynamic = "(dynamic)" in line

        # Validate time format: accepts both MM:SS (before 1 hour) and HH:MM:SS (after 1 hour)
        try:
            time_parts = time_str.split(':')
            if len(time_parts) not in [2, 3]:
                raise ValueError("Invalid time format")
            for part in time_parts:
                int(part)
        except:
            raise ValueError(
                f"Timeline line {line_num}: Invalid time format '{time_str}'.\n"
                f"Expected format: M:SS (e.g., 9:51, 0:00) or HH:MM:SS (e.g., 1:23:45)"
            )

        # Validate sensor
        if sensor not in valid_sensors:
            raise ValueError(
                f"Timeline line {line_num}: Invalid sensor '{sensor}'.\n"
                f"Valid sensors: {', '.join(sorted(valid_sensors))}"
            )

        # Validate speed format
        if not speed.endswith('_ul-min'):
            raise ValueError(
                f"Timeline line {line_num}: Invalid speed format '{speed}'.\n"
                f"Expected format: {{number}}_ul-min (e.g., 50_ul-min)"
            )

        # Validate solution exists in registry
        if solution_name not in solution_registry:
            available = ', '.join(sorted(solution_registry.keys()))
            raise ValueError(
                f"Timeline line {line_num}: Solution '{solution_name}' not found in SOLUTION REGISTRY.\n"
                f"Available solutions: {available}"
            )

        # Convert to old format: HH:MM:SS S{sensor} {speed}_ul-min [changed to] {solution} [(dynamic)]
        if is_dynamic:
            converted = f"{time_str} {sensor} {speed} changed to {solution_name} (dynamic)"
        else:
            converted = f"{time_str} {sensor} {speed} changed to {solution_name}"

        converted_lines.append(converted)

    return converted_lines


def is_option_b_format(timeline_text: str) -> bool:
    """Check if timeline is in OPTION_B format (has SOLUTION REGISTRY section)."""
    return "SOLUTION REGISTRY" in timeline_text


def read_timeline_data(timeline_text: str, lag_times: dict) -> tuple:
    """
    Parse timeline text and apply lag corrections.
    Supports both OPTION_B and legacy formats.
    Wrapper around the original function to handle Streamlit's text input.

    Returns:
        (timeline_df, validation_report)
        - timeline_df: processed timeline dataframe
        - validation_report: dict with status and details
    """
    validation_report = {
        "status": "success",
        "messages": [],
        "format_detected": None,
        "solution_count": 0
    }

    try:
        # Check which format we have
        if is_option_b_format(timeline_text):
            validation_report["format_detected"] = "OPTION_B"

            # Parse OPTION_B format
            solution_registry, timeline_lines = parse_option_b_timeline(timeline_text)
            validation_report["solution_count"] = len(solution_registry)

            # Validate and convert
            converted_lines = validate_option_b_timeline(timeline_lines, solution_registry)

            # Convert back to text format for original function
            converted_text = '\n'.join(converted_lines)
            timeline_text = converted_text

            validation_report["messages"].append(
                f"✓ OPTION_B format detected with {len(solution_registry)} solutions"
            )
        else:
            validation_report["format_detected"] = "Legacy"
            validation_report["messages"].append("✓ Legacy timeline format detected")

    except ValueError as e:
        validation_report["status"] = "error"
        validation_report["messages"].append(f"✗ Format validation failed:\n{str(e)}")
        return None, validation_report
    except Exception as e:
        validation_report["status"] = "error"
        validation_report["messages"].append(f"✗ Unexpected error parsing timeline:\n{str(e)}")
        return None, validation_report

    # Process with original function
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy persistent ID for file path
            timeline_path = os.path.join(tmpdir, "Data_temp_timeline.txt")
            with open(timeline_path, 'w') as f:
                f.write(timeline_text)

            # Call original function
            timeline_data_pd = _read_timeline_data_original(tmpdir, "temp")

            # Apply custom lag corrections from Streamlit settings
            if timeline_data_pd is not None and not timeline_data_pd.empty:
                for sensor in [1, 2, 3, 4]:
                    lag_sec = lag_times.get(sensor, 2.7)
                    mask = timeline_data_pd['Sensor'] == sensor
                    timeline_data_pd.loc[mask, 'Time'] = (
                        timeline_data_pd.loc[mask, 'Time'] +
                        (lag_sec * timeline_data_pd.loc[mask, 'Speed'] / 50).astype(int).values
                    )

            # Add block type column
            if timeline_data_pd is not None:
                timeline_data_pd["Block_type"] = timeline_data_pd["Information"].apply(
                    lambda x: "dynamic" if "(dynamic)" in str(x) else "static"
                )
                timeline_data_pd["Information"] = timeline_data_pd["Information"].str.replace(
                    " (dynamic)", "", regex=False
                )

            return timeline_data_pd, validation_report

    except Exception as e:
        validation_report["status"] = "error"
        validation_report["messages"].append(
            f"✗ Error processing timeline with original function:\n{str(e)}"
        )
        return None, validation_report
