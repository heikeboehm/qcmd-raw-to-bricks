"""
Program Description:
This program reads in a csv file created by the "QCMD_flow_raw_to_adj" program.
It creates "bricks" of data for easy comparison of different experimental "blocks."

Author:
- Heike Böhm, Department of Cellular Biophysics, MPI for Medical Research (MPImF-CBP-GS)
- With strong support from Martin Schröter in the same department.
- Idea and design for brick structure to enable comparison of different data sets by Florian Köhldorfer, MPImF-CBP-GS.
"""

import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt


# -------------------------------------------------------------------
# Folder structure
# -------------------------------------------------------------------

adj_files_path = "adj_files"
bricks_output_path = "bricks"
FIRST_BRICK_LABEL = "PBS"  # Default value; can be overridden via command-line


# -------------------------------------------------------------------
# Load adjusted data
# -------------------------------------------------------------------

def process_adj_qcmd_data(csv_file_path, adj_files_path):

    persistentID = os.path.basename(csv_file_path)
    persistentID = persistentID.replace("Data_", "").replace("_adj_qcmd_data.csv", "")

    adj_qcmd_pd = pd.read_csv(csv_file_path, index_col=0)

    adj_qcmd_n7_pd = adj_qcmd_pd[adj_qcmd_pd["Overtone"] == 7]

    timeline_file_path = os.path.join(
        adj_files_path,
        f"Data_{persistentID}_adj_timeline.csv"
    )

    adj_timeline_pd = pd.read_csv(timeline_file_path, index_col=0)

    return persistentID, adj_qcmd_pd, adj_qcmd_n7_pd, adj_timeline_pd


# -------------------------------------------------------------------
# Timeline → bricks
# -------------------------------------------------------------------

def generate_timeline_bricks(adj_timeline_pd, adj_qcmd_n7_pd, first_brick_label=FIRST_BRICK_LABEL):

    timeline_bricks_pd = pd.DataFrame(adj_timeline_pd)

    timeline_bricks_pd.rename(columns={
        "Time": "Change_time",
        "Information": "Solution"
    }, inplace=True)

    timeline_bricks_pd["Change_time"] = timeline_bricks_pd["Change_time"].astype(float)

    timeline_bricks_pd["Solution"] = timeline_bricks_pd["Solution"].str.replace(
        "changed to ", "", regex=False
    )

    # End
    end_row = pd.DataFrame({
        "Change_time": [adj_qcmd_n7_pd["Time_s"].iloc[-2]],
        "Solution": ["end of experiment"],
        "Speed": [timeline_bricks_pd["Speed"].iloc[-1]],
        "Block_type": ["static"]
    })

    timeline_bricks_pd = pd.concat([timeline_bricks_pd, end_row], ignore_index=True)

    timeline_bricks_pd["Brick"] = range(1, len(timeline_bricks_pd) + 1)

    return timeline_bricks_pd


def assign_brick_times(timeline_bricks_pd):

    timeline_bricks_pd = timeline_bricks_pd.copy()

    timeline_bricks_pd["Brick_start"] = None
    timeline_bricks_pd["Brick_end"] = None

    for i in range(len(timeline_bricks_pd) - 1):

        current_row = timeline_bricks_pd.iloc[i]
        next_row = timeline_bricks_pd.iloc[i + 1]

        change_time = next_row["Change_time"]

        if current_row["Block_type"] == "dynamic":
            start_time = current_row["Change_time"]
            end_time = change_time
        else:
            start_time = change_time - 360
            end_time = change_time - 60

        timeline_bricks_pd.loc[i, "Brick_start"] = start_time
        timeline_bricks_pd.loc[i, "Brick_end"] = end_time

    return timeline_bricks_pd


# -------------------------------------------------------------------
# Create bricks
# -------------------------------------------------------------------

def create_qcmd_bricks(adj_qcmd_pd, timeline_bricks_pd):

    adj_qcmd_pd = adj_qcmd_pd.copy()

    adj_qcmd_pd["Brick"] = None
    adj_qcmd_pd["Rel_brick_time_s"] = None

    brick_data = []

    for i in range(len(timeline_bricks_pd) - 1):

        row = timeline_bricks_pd.iloc[i]

        start_time = row["Brick_start"]
        end_time = row["Brick_end"]

        if pd.isna(start_time) or pd.isna(end_time):
            continue

        mask = (
            (adj_qcmd_pd["Time_s"] >= start_time) &
            (adj_qcmd_pd["Time_s"] <= end_time)
        )

        brick_df = adj_qcmd_pd.loc[mask].copy()

        brick_df["Brick"] = row["Brick"]
        brick_df["Rel_brick_time_s"] = brick_df["Time_s"] - start_time

        brick_data.append(brick_df)

    adj_qcmd_bricks_pd = pd.concat(brick_data, ignore_index=True)

    return adj_qcmd_pd, adj_qcmd_bricks_pd


# -------------------------------------------------------------------
# Mean calculation
# -------------------------------------------------------------------

def calculate_mean_bricks(adj_qcmd_bricks_pd):

    filtered_data = []

    for brick in adj_qcmd_bricks_pd["Brick"].unique():

        brick_df = adj_qcmd_bricks_pd[adj_qcmd_bricks_pd["Brick"] == brick]

        if brick_df.empty:
            continue

        max_time = brick_df["Rel_brick_time_s"].max()

        start_time = max_time - 360
        end_time = max_time - 60

        window_df = brick_df[
            (brick_df["Rel_brick_time_s"] >= start_time) &
            (brick_df["Rel_brick_time_s"] <= end_time)
        ]

        filtered_data.append(window_df)

    filtered_pd = pd.concat(filtered_data, ignore_index=True)

    mean_brick_pd = (
        filtered_pd
        .groupby(["Brick", "Overtone"])
        .agg(
            Mean_Deltaf_div_n_Hz=("Deltaf_div_n_Hz", "mean"),
            Std_Deltaf_div_n_Hz=("Deltaf_div_n_Hz", "std"),
            Mean_Dissipation_ppm=("Dissipation_ppm", "mean"),
            Std_Dissipation_ppm=("Dissipation_ppm", "std")
        )
        .reset_index()
    )

    return mean_brick_pd

def plot_full_experiment_with_bricks_v2(adj_qcmd_pd, timeline_bricks_pd, persistentID):

    fig, ax = plt.subplots(figsize=(10, 4))

    df7 = adj_qcmd_pd[adj_qcmd_pd["Overtone"] == 7]

    # ------------------------------------------------------------
    # Main signals
    # ------------------------------------------------------------

    ax.plot(df7["Time_s"], df7["Deltaf_div_n_Hz"], color="tab:blue")

    ax2 = ax.twinx()
    ax2.plot(df7["Time_s"], df7["Dissipation_ppm"], color="tab:orange")

    ax2.set_ylabel("D/n [ppm]", color="tab:orange")
    ax2.tick_params(axis='y', labelcolor="tab:orange")

    # ------------------------------------------------------------
    # Shade bricks
    # ------------------------------------------------------------

    for _, row in timeline_bricks_pd.iterrows():

        start = row["Brick_start"]
        end = row["Brick_end"]

        if pd.isna(start) or pd.isna(end):
            continue

        color = "lightgray" if row["Block_type"] == "static" else "lightblue"

        ax.axvspan(start, end, color=color, alpha=0.3)

    # ------------------------------------------------------------
    # Vertical lines + solution labels (FIXED)
    # ------------------------------------------------------------

    for _, row in timeline_bricks_pd.iterrows():

        change_time = row["Change_time"]

        if pd.isna(change_time):
            continue

        # vertical line
        ax.axvline(
            change_time,
            color="grey",
            linestyle="-",
            linewidth=1,
            alpha=0.5,
            ymin=0,
            ymax=1.03,
            clip_on=False   # 🔥 THIS is the key
        )

        # solution label anchored at change time
        solution = row["Solution"]

        if solution == "end of experiment":
            continue
        speed = row["Speed"]

        ax.text(
            change_time,
            1.02,
            f"{solution} ({int(speed)})",
            transform=ax.get_xaxis_transform(),
            rotation=45,              # 🔥 angled
            ha="left",
            va="bottom",
            fontsize=8
        )

    # ------------------------------------------------------------
    # Axis limits FIRST (important)
    # ------------------------------------------------------------

    ax.set_xlim(0, adj_qcmd_pd["Time_s"].max())

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + 0.25 * (ymax - ymin))

    # ------------------------------------------------------------
    # Brick labels AFTER scaling (FIXED)
    # ------------------------------------------------------------

    for _, row in timeline_bricks_pd.iterrows():

        start = row["Brick_start"]
        end = row["Brick_end"]
        brick = row["Brick"]

        if pd.isna(start) or pd.isna(end):
            continue

        mid = (start + end) / 2

        ymin, ymax = ax.get_ylim()
        y_pos = ymax - 0.05 * (ymax - ymin)

        ax.text(
            mid,
            y_pos,
            f"brick{brick}",
            ha="center",
            va="top",
            fontsize=6,
            alpha=0.8       
        )

    # ------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Δf/n [Hz]")

    plt.tight_layout()

    filename = os.path.join(
        bricks_output_path,
        f"Plot_{persistentID}_full_experiment.png"
    )

    plt.savefig(filename)
    plt.close()

# -------------------------------------------------------------------
# Plot
# -------------------------------------------------------------------
def plot_qcmd_bricks_with_mean(adj_qcmd_bricks_pd, mean_brick_pd, timeline_bricks_pd, persistentID):

    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import numpy as np

    os.makedirs(bricks_output_path, exist_ok=True)

    bricks = sorted(adj_qcmd_bricks_pd["Brick"].dropna().unique())
    overtones = sorted(adj_qcmd_bricks_pd["Overtone"].unique())

    n_bricks = len(bricks)

    fig, axes = plt.subplots(2, n_bricks, figsize=(3 * n_bricks, 6))

    if n_bricks == 1:
        axes = axes.reshape(2, 1)

    # ------------------------------------------------------------
    # Color palettes
    # ------------------------------------------------------------

    norm = np.linspace(0.3, 1.0, len(overtones))
    freq_colors = {o: cm.Blues(n) for o, n in zip(overtones, norm)}
    diss_colors = {o: cm.OrRd(n) for o, n in zip(overtones, norm)}

    # ------------------------------------------------------------
    # Global axis limits + headroom
    # ------------------------------------------------------------

    ymin_f = adj_qcmd_bricks_pd["Deltaf_div_n_Hz"].min()
    ymax_f = adj_qcmd_bricks_pd["Deltaf_div_n_Hz"].max()

    ymin_d = adj_qcmd_bricks_pd["Dissipation_ppm"].min()
    ymax_d = adj_qcmd_bricks_pd["Dissipation_ppm"].max()

    pad_f = 0.05 * (ymax_f - ymin_f)
    pad_d = 0.05 * (ymax_d - ymin_d)

    extra_f = 0.15 * (ymax_f - ymin_f)
    extra_d = 0.15 * (ymax_d - ymin_d)

    ymin_f -= pad_f
    ymax_f += pad_f + extra_f

    ymin_d -= pad_d
    ymax_d += pad_d + extra_d

    # ------------------------------------------------------------
    # Plot loop
    # ------------------------------------------------------------

    for col, brick in enumerate(bricks):

        brick_df = adj_qcmd_bricks_pd[adj_qcmd_bricks_pd["Brick"] == brick]

        ax_f = axes[0, col]
        ax_d = axes[1, col]

        for overtone in overtones:

            df_o = brick_df[brick_df["Overtone"] == overtone]

            if df_o.empty:
                continue

            alpha = 1.0 if overtone == 7 else 0.4
            lw = 2 if overtone == 7 else 1

            ax_f.plot(
                df_o["Rel_brick_time_s"],
                df_o["Deltaf_div_n_Hz"],
                color=freq_colors[overtone],
                alpha=alpha,
                linewidth=lw
            )

            ax_d.plot(
                df_o["Rel_brick_time_s"],
                df_o["Dissipation_ppm"],
                color=diss_colors[overtone],
                alpha=alpha,
                linewidth=lw
            )

        # --------------------------------------------------------
        # Mean ± std labels (mathtext)
        # --------------------------------------------------------

        mean_row = mean_brick_pd[
            (mean_brick_pd["Brick"] == brick) &
            (mean_brick_pd["Overtone"] == 7)
        ]

        if not mean_row.empty:

            mean_f = mean_row["Mean_Deltaf_div_n_Hz"].values[0]
            std_f = mean_row["Std_Deltaf_div_n_Hz"].values[0]

            mean_d = mean_row["Mean_Dissipation_ppm"].values[0]
            std_d = mean_row["Std_Dissipation_ppm"].values[0]

            label_f = rf"$\overline{{\Delta f_7}} = {mean_f:.2f} \pm {std_f:.2f}$"
            label_d = rf"$\overline{{D_7}} = {mean_d:.2f} \pm {std_d:.2f}$"

            ax_f.text(0.95, 0.95, label_f,
                      transform=ax_f.transAxes,
                      ha="right", va="top", fontsize=10)

            ax_d.text(0.95, 0.95, label_d,
                      transform=ax_d.transAxes,
                      ha="right", va="top", fontsize=9)

        # --------------------------------------------------------
        # Titles
        # --------------------------------------------------------

        info = timeline_bricks_pd[timeline_bricks_pd["Brick"] == brick]
        if not info.empty:
            ax_f.set_title(f"{info['Solution'].values[0]} ({int(info['Speed'].values[0])})")

        # --------------------------------------------------------
        # Axis limits
        # --------------------------------------------------------

        ax_f.set_ylim(ymin_f, ymax_f)
        ax_d.set_ylim(ymin_d, ymax_d)

        ax_f.grid(True, which="major", color="lightgrey", linestyle="-", linewidth=0.5)
        ax_d.grid(True, which="major", color="lightgrey", linestyle="-", linewidth=0.5)


        # --------------------------------------------------------
        # Clean y-axis ticks (THIS is the fix)
        # --------------------------------------------------------

        if col == 0:
            ax_f.set_ylabel("Δf/n [Hz]")
            ax_d.set_ylabel("D/n [ppm]")
        else:
            ax_f.tick_params(labelleft=False)
            ax_d.tick_params(labelleft=False)

        ax_d.set_xlabel(f"t_{brick} [s]")

    plt.tight_layout()

    filename = os.path.join(
        bricks_output_path,
        f"Plot_{persistentID}_bricks_plot.png"
    )

    plt.savefig(filename)
    plt.close()

def plot_brick_summary(mean_brick_pd, persistentID):

    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import numpy as np

    overtones = sorted(mean_brick_pd["Overtone"].unique())
    bricks = sorted(mean_brick_pd["Brick"].unique())

    # ------------------------------------------------------------
    # Layout: vertical stacking + wider figure
    # ------------------------------------------------------------

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    ax_f, ax_d = axes

    # ------------------------------------------------------------
    # Color palettes
    # ------------------------------------------------------------

    norm = np.linspace(0.3, 1.0, len(overtones))
    freq_colors = {o: cm.Blues(n) for o, n in zip(overtones, norm)}
    diss_colors = {o: cm.OrRd(n) for o, n in zip(overtones, norm)}

    # ------------------------------------------------------------
    # Spacing controls (🔥 main tuning knobs)
    # ------------------------------------------------------------

    brick_spacing = 2.0                     # space BETWEEN bricks
    offsets = np.linspace(-0.4, 0.4, len(overtones))  # space WITHIN brick

    # ------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------

    for offset, overtone in zip(offsets, overtones):

        df_o = mean_brick_pd[mean_brick_pd["Overtone"] == overtone]

        x_positions = df_o["Brick"] * brick_spacing + offset

        # Δf
        ax_f.errorbar(
            x_positions,
            df_o["Mean_Deltaf_div_n_Hz"],
            yerr=df_o["Std_Deltaf_div_n_Hz"],
            fmt="o",
            markersize=6 if overtone == 7 else 4,
            alpha=1.0 if overtone == 7 else 0.7,
            capsize=5 if overtone == 7 else 3,
            color=freq_colors[overtone],
            label=f"n={overtone}"
        )

        # D
        ax_d.errorbar(
            x_positions,
            df_o["Mean_Dissipation_ppm"],
            yerr=df_o["Std_Dissipation_ppm"],
            fmt="o",
            markersize=6 if overtone == 7 else 4,
            alpha=1.0 if overtone == 7 else 0.7,
            capsize=5 if overtone == 7 else 3,
            color=diss_colors[overtone]
        )

    # ------------------------------------------------------------
    # X-axis: map back to brick numbers
    # ------------------------------------------------------------

    xticks = [b * brick_spacing for b in bricks]

    ax_d.set_xticks(xticks)
    ax_d.set_xticklabels(bricks)

    # ------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------

    ax_f.set_ylabel("Δf/n [Hz]")

    ax_d.set_ylabel("D/n [ppm]")
    ax_d.set_xlabel("Brick")

    # ------------------------------------------------------------
    # Optional: subtle grid (helps reading spacing)
    # ------------------------------------------------------------

    ax_f.grid(axis="x", color="lightgrey", linewidth=0.5)
    ax_d.grid(axis="x", color="lightgrey", linewidth=0.5)

    # ------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------

    plt.tight_layout()

    filename = os.path.join(
        bricks_output_path,
        f"Plot_{persistentID}_brick_summary.png"
    )

    plt.savefig(filename)
    plt.close()
    
# -------------------------------------------------------------------
# File discovery
# -------------------------------------------------------------------

def identify_adj_files(directory):
    return [f for f in os.listdir(directory) if "adj_qcmd_data.csv" in f]


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main(first_brick_label=FIRST_BRICK_LABEL):

    os.makedirs(bricks_output_path, exist_ok=True)

    for file in identify_adj_files(adj_files_path):

        print(f"Processing {file}")

        path = os.path.join(adj_files_path, file)

        persistentID, adj_qcmd_pd, adj_qcmd_n7_pd, adj_timeline_pd = process_adj_qcmd_data(
            path, adj_files_path
        )

        timeline_bricks_pd = generate_timeline_bricks(adj_timeline_pd, adj_qcmd_n7_pd, first_brick_label)
        timeline_bricks_pd = assign_brick_times(timeline_bricks_pd)

        timeline_bricks_pd.to_csv(
            os.path.join(bricks_output_path, f"Data_{persistentID}_timeline_bricks.csv")
        )

        adj_qcmd_pd, adj_qcmd_bricks_pd = create_qcmd_bricks(adj_qcmd_pd, timeline_bricks_pd)

        adj_qcmd_bricks_pd.to_csv(
            os.path.join(bricks_output_path, f"Data_{persistentID}_adj_qcmd_bricks.csv")
        )

        adj_qcmd_pd.to_csv(
            os.path.join(bricks_output_path, f"Data_{persistentID}_adj_qcmd_with_bricks.csv")
        )

        mean_brick_pd = calculate_mean_bricks(adj_qcmd_bricks_pd)

        mean_brick_pd.to_csv(
            os.path.join(bricks_output_path, f"Data_{persistentID}_mean_bricks.csv"),
            index=False
        )

        plot_qcmd_bricks_with_mean(
            adj_qcmd_bricks_pd,
            mean_brick_pd,
            timeline_bricks_pd,
            persistentID
        )

        plot_full_experiment_with_bricks_v2(
            adj_qcmd_pd,
            timeline_bricks_pd,
            persistentID
        )

        plot_brick_summary(
            mean_brick_pd,
            persistentID
        )


        print(f"Finished {file}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Process adjusted QCM-D data into bricks."
    )

    parser.add_argument(
        "--first-brick-label",
        type=str,
        default=FIRST_BRICK_LABEL,
        help=f"Label for the first brick (initial baseline solution). Default: '{FIRST_BRICK_LABEL}'"
    )

    args = parser.parse_args()

    main(first_brick_label=args.first_brick_label)