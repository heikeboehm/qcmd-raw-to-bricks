"""
Program Description:
This program processes QCM-D data recorded on a QSense-Analyzer using Q-Tools Software (Version 2.8.5) 
and flow modules. It breaks down the data into independent, unified datasets for each sensor position.

Lag time between start of tubing to crystal (needs to be adjusted if different tube set used - see cell No. 4)
(Experimental note: all tubes are labeled to ensure the same tubes are used with the same sensors each time)
S1: 135 sek at 50µl/min
S2: 140 sek at 50µl/min
S3: 140 sek at 50µl/min
S4: 145 sek at 50µl/min

Author:
- Heike Böhm, Department of Cellular Biophysics, MPI for Medical Research (MPImF-CBP-GS)

Input Data Sources:
- Rawdata as a tab-spaced CSV file exported from Q-Tools using "," as decimal points
  (expects data to be saved with 'Data_ID_rawdata.txt' format)
- Corresponding timeline copied and pasted from the notes window of Q-Tools into a plain text file
  (expects data to be saved with 'Data_ID_timeline.txt' format)
  Format: h:mm:ss S# flow_speed description. (Where S# corresponds to the sensor and its respective number)

Output Generated:
- CSV-Files saving:
    - adj_qcmd_data: 
        Adjusted QCM-D dataset with time in seconds adjusted with resp. lag time, normalized Δf/n, and normalized D for all overtones. 
        Normalization is achieved by subtracting the averaged value of the first 100 data points 
        for each measured frequency and dissipation overtone.
        All normalized frequency values have been divided by the overtone number to represent Δf/n.
    - adj_timeline_data: 
        Timeline given in the text file for the respective sensor, including the time in seconds, 
        the flow speed in µm/min, and information on the solution change.

Comments on Coding:
- For all variables lower_case_with_underscores are used. 
- CapWords are used for class names 
- UPPER_CASE_WITH_UNDERSCORES are used for constants.
"""

import os
import argparse
import numpy as np
import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns


# ------------------------------------------------------------
# RAWDATA PROCESSING
# ------------------------------------------------------------
"""
Input:
- Reads in the rawdata txt File with time in seconds as the index.

Output:
- persistentID: represents the uniqueID of the dataset - extracted from the name of the rawdata title 
- sensors: number of sensors for which data is available
- adj_qcmd_data as long format pandas dataframe
    - frequency and Dissipation values are normalized to start at zero by subtracting the averaged value of the first 100 data points.
    - frequency values are divided by the overtone number to represent Δf/n.

Note on Coding:
- The rawdata is expected to be exported with column titles in the format"Time_S" and "Mn_S [unit]"
    where M represents f for frequency or D for dissipation; n is the overtone number and S the sensor No.
"""


def process_rawdata(file_path):

    qcmd_data_wide = pd.read_csv(file_path, sep="\t", decimal=",", encoding='latin-1')
    rawdata = qcmd_data_wide

    rawdata_array = rawdata.to_numpy()
    rawdata_column_names = rawdata.columns

    persistentID = os.path.basename(file_path)
    persistentID = persistentID.replace("Data_", "").replace("_rawdata.txt", "")

    sensors = {int(item.split("_")[1].split(" ")[0]) for item in qcmd_data_wide if item[0] == "f"}
    overtones = {int(item.split("_")[0][1:]) for item in qcmd_data_wide if item[0] == "f"}

    print("Starting to process data with the persistent ID:", persistentID)
    print("In this dataset, the following overtones were measured:")
    print(overtones)
    print("on the sensor positions")
    print(sensors)

    norm_qcmd_data_wide = qcmd_data_wide

    # the data contains a Time column for each of the sensors.
    # Thus we must ensure that none of the columns labeled "Time_n [s]" - with n being the overtone number - is normalized
    for col in qcmd_data_wide.columns:
        if not re.match(r'Time_\d+\s+\[s\]', col):
            norm_qcmd_data_wide[col] = qcmd_data_wide[col] - qcmd_data_wide[col].iloc[0:100].mean()

    # Create adj_qcmd_data in long format
    adj_qcmd_data = pd.DataFrame(
        columns=["Time_s", "Overtone", "Sensor", "Deltaf_div_n_Hz", "Dissipation_ppm"]
    )

    for sensor in sensors:
        for overtone in overtones:

            columns_selected = [
                "Time_" + str(sensor) + " [s]",
                "f" + str(overtone) + "_" + str(sensor) + " [Hz]",
                "D" + str(overtone) + "_" + str(sensor) + " [ppm]"
            ]

            data_temp = qcmd_data_wide.loc[:, columns_selected]

            data_temp.columns = ["Time_s", "Deltaf_div_n_Hz", "Dissipation_ppm"]
            data_temp["Overtone"] = float(overtone)
            data_temp["Sensor"] = float(sensor)

            adj_qcmd_data = pd.concat([adj_qcmd_data, data_temp], ignore_index=True)

    adj_qcmd_data["Deltaf_div_n_Hz"] = adj_qcmd_data["Deltaf_div_n_Hz"] / adj_qcmd_data["Overtone"]

    adj_qcmd_data["Deltaf_div_n_Hz"] = adj_qcmd_data["Deltaf_div_n_Hz"].astype(float)
    adj_qcmd_data["Time_s"] = adj_qcmd_data["Time_s"].astype(float)
    adj_qcmd_data["Dissipation_ppm"] = adj_qcmd_data["Dissipation_ppm"].astype(float)

    adj_qcmd_data = adj_qcmd_data.dropna()

    print("Transformed to normalized long format")

    return persistentID, sensors, adj_qcmd_data


# ------------------------------------------------------------
# TIMELINE PROCESSING
# ------------------------------------------------------------
"""
Input:
- path
- persistenID
- Reads in the timeline txt based on our naming conventions 
    expects title of timeline to be path+"Data_"+persistentID+"_timeline.txt"

Output:
- timeline_data_pd: adjusted time points at which liquid has been exchanged in a pandas data frame 
    column names: ['Time', 'Sensor', 'Speed' 'Information']
"""


def read_timeline_data(path, persistentID):

    file_timeline = os.path.join(path, f"Data_{persistentID}_timeline.txt")

    try:
        with open(file_timeline, 'r', encoding='utf-8') as file:
            timeline = file.read()
            print("Timeline file read:")
            print(f"Data_{persistentID}_timeline.txt")
    except FileNotFoundError:
        print(f"The file '{file_timeline}' was not found. Check if it was saved with the correct name")
        return None

    timelines_times = []
    timelines_sensors = []
    timelines_speeds = []
    timelines_infos = []

    timelines = timeline.split("\n")

    for line in timelines:

        line = line.strip()

        if line:

            parts = line.split(" ", 3)

            time_str = parts[0]
            timelines_info = parts[3]

            timelines_sensor = int(parts[1].replace("S", ""))
            timelines_speed = int(parts[2].replace("_ul-min", ""))

            time_parts = time_str.split(":")

            if len(time_parts) == 2:
                hours, minutes, seconds = 0, int(time_parts[0]), int(time_parts[1])
            elif len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
            else:
                raise ValueError(f"Invalid time format: {time_str}")

            timelines_time = hours * 3600 + minutes * 60 + seconds

            timelines_times.append(timelines_time)
            timelines_sensors.append(timelines_sensor)
            timelines_speeds.append(timelines_speed)
            timelines_infos.append(timelines_info)

    dtype = [('Time', int), ('Sensor', int), ('Speed', int), ('Information', 'S100')]

    timeline_data_np = np.array(
        list(zip(timelines_times, timelines_sensors, timelines_speeds, timelines_infos)),
        dtype=dtype
    )

    delayS1 = 135/50
    delayS2 = 100/50
    delayS3 = 140/50
    delayS4 = 135/50

    timeline_data_np['Time'] = np.where(
        timeline_data_np['Sensor'] == 1,
        timeline_data_np['Time'] + delayS1 * timeline_data_np['Speed'],
        timeline_data_np['Time']
    )

    timeline_data_np['Time'] = np.where(
        timeline_data_np['Sensor'] == 2,
        timeline_data_np['Time'] + delayS2 * timeline_data_np['Speed'],
        timeline_data_np['Time']
    )

    timeline_data_np['Time'] = np.where(
        timeline_data_np['Sensor'] == 3,
        timeline_data_np['Time'] + delayS3 * timeline_data_np['Speed'],
        timeline_data_np['Time']
    )

    timeline_data_np['Time'] = np.where(
        timeline_data_np['Sensor'] == 4,
        timeline_data_np['Time'] + delayS4 * timeline_data_np['Speed'],
        timeline_data_np['Time']
    )

    timeline_data_pd = pd.DataFrame(
        timeline_data_np,
        columns=['Time', 'Sensor', 'Speed', 'Information']
    )

    timeline_data_pd['Information'] = timeline_data_pd['Information'].apply(lambda x: x.decode('utf-8'))

    # ------------------------------------------------------------
    # Identify block type (dynamic vs static)
    # ------------------------------------------------------------

    timeline_data_pd["Block_type"] = timeline_data_pd["Information"].apply(
        lambda x: "dynamic" if "(dynamic)" in x else "static"
    )

    # Remove "(dynamic)" from solution description
    timeline_data_pd["Information"] = timeline_data_pd["Information"].str.replace(
        " (dynamic)", "",
        regex=False
)

    return timeline_data_pd


# ------------------------------------------------------------
# FILE DISCOVERY
# ------------------------------------------------------------

def identify_similar_files(directory):

    files = os.listdir(directory)

    similar_files = [file for file in files if "rawdata.txt" in file.lower()]

    return similar_files


# ------------------------------------------------------------
# MAIN PROGRAM
# ------------------------------------------------------------

def main(path):

    rawdata_files = identify_similar_files(path)

    if not rawdata_files:
        print(f"There are no files containing 'rawdata.txt' in the folder {path}")
        return

    for file in rawdata_files:

        print(file)

        file_path = os.path.join(path, file)

        persistentID, sensors, adj_qcmd_data = process_rawdata(file_path)

        timeline_data = read_timeline_data(path, persistentID)

        if timeline_data is None:
            return

        baseID = persistentID.replace("_QCMD", "")
        parent_dir = os.path.dirname(path)
        output_dir = os.path.join(parent_dir, "adj_files")
        os.makedirs(output_dir, exist_ok=True)

        csv_filename = os.path.join(output_dir, "Data_" + baseID)

        for sensor in sensors:

            sensor_qcmd_data = adj_qcmd_data[adj_qcmd_data["Sensor"] == sensor].copy()
            del sensor_qcmd_data["Sensor"]

            adj_qcmd_data_name = f"{csv_filename}_S{sensor}_QCMD_adj_qcmd_data.csv"

            sensor_qcmd_data.to_csv(adj_qcmd_data_name, index=True)

            adj_timeline_filename = f"{csv_filename}_S{sensor}_QCMD_adj_timeline.csv"

            adj_sensor_timeline = timeline_data[timeline_data["Sensor"] == sensor].copy()
            del adj_sensor_timeline["Sensor"]

            adj_sensor_timeline.to_csv(adj_timeline_filename, index=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process QCM-D flow data.")

    parser.add_argument(
        "path",
        type=str,
        help="Path to the folder containing the QCMD rawdata"
    )

    args = parser.parse_args()

    main(args.path)