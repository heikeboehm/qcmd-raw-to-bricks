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
            "adj_timeline_dict": {sensor: adjusted_timeline_df}
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
    timeline_df = read_timeline_data(timeline_text, lag_times)

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
        "adj_timeline_dict": adj_timeline_dict
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


def read_timeline_data(timeline_text: str, lag_times: dict) -> pd.DataFrame:
    """
    Parse timeline text and apply lag corrections.
    Wrapper around the original function to handle Streamlit's text input.
    """
    # Write timeline text to temp file (original expects file path)
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

        return timeline_data_pd
