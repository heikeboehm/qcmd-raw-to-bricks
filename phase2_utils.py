"""
Phase 2 Utilities: Adjusted Data → Bricks

Wrapper functions for Phase 2 brick segmentation.
Imports the actual functions from the original analysis code.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import DIRECTLY from the main QCMD flow file
import importlib.util
spec = importlib.util.spec_from_file_location("QCMD_flow_adj_to_bricks_folder",
                                               os.path.join(os.path.dirname(__file__), "QCMD_flow_adj_to_bricks_folder.py"))
qcmd_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qcmd_module)

_plot_bricks_original = qcmd_module.plot_qcmd_bricks_with_mean
_plot_brick_summary_original = qcmd_module.plot_brick_summary
_plot_full_experiment_original = qcmd_module.plot_full_experiment_with_bricks_v2


def plot_bricks_for_streamlit(adj_qcmd_bricks_pd, mean_brick_pd, timeline_bricks_pd, sensor):
    """
    Wrapper around the original plot_qcmd_bricks_with_mean to capture the figure for Streamlit.
    """
    persistent_id = f"S{int(sensor)}"

    # Override plt.savefig and plt.close to prevent file writes and figure closure
    import matplotlib.pyplot as mpl_plt
    old_savefig = mpl_plt.savefig
    old_close = mpl_plt.close

    def dummy_savefig(*args, **kwargs):
        pass

    def dummy_close(*args, **kwargs):
        pass

    try:
        mpl_plt.savefig = dummy_savefig
        mpl_plt.close = dummy_close

        # Call the original function
        _plot_bricks_original(adj_qcmd_bricks_pd, mean_brick_pd, timeline_bricks_pd, persistent_id)

        # Capture the figure before it would be closed
        fig = mpl_plt.gcf()
        return fig

    finally:
        # Restore original functions
        mpl_plt.savefig = old_savefig
        mpl_plt.close = old_close


def plot_summary_for_streamlit(mean_brick_pd, sensor):
    """
    Wrapper around the original plot_brick_summary to capture the figure for Streamlit.
    """
    persistent_id = f"S{int(sensor)}"

    import matplotlib.pyplot as mpl_plt
    old_savefig = mpl_plt.savefig
    old_close = mpl_plt.close

    def dummy_savefig(*args, **kwargs):
        pass

    def dummy_close(*args, **kwargs):
        pass

    try:
        mpl_plt.savefig = dummy_savefig
        mpl_plt.close = dummy_close

        _plot_brick_summary_original(mean_brick_pd, persistent_id)
        fig = mpl_plt.gcf()
        return fig

    finally:
        mpl_plt.savefig = old_savefig
        mpl_plt.close = old_close


def plot_full_for_streamlit(adj_qcmd_pd, timeline_bricks_pd, sensor):
    """
    Wrapper around the original plot_full_experiment_with_bricks_v2 to capture the figure for Streamlit.
    """
    persistent_id = f"S{int(sensor)}"

    import matplotlib.pyplot as mpl_plt
    old_savefig = mpl_plt.savefig
    old_close = mpl_plt.close

    def dummy_savefig(*args, **kwargs):
        pass

    def dummy_close(*args, **kwargs):
        pass

    try:
        mpl_plt.savefig = dummy_savefig
        mpl_plt.close = dummy_close

        _plot_full_experiment_original(adj_qcmd_pd, timeline_bricks_pd, persistent_id)
        fig = mpl_plt.gcf()
        return fig

    finally:
        mpl_plt.savefig = old_savefig
        mpl_plt.close = old_close


def process_phase2(
    adj_data_dict: dict,
    adj_timeline_dict: dict
) -> dict:
    """
    Process Phase 2: Adjusted Data → Bricks

    Args:
        adj_data_dict: {sensor: adjusted_data_df}
        adj_timeline_dict: {sensor: adjusted_timeline_df}

    Returns:
        {
            "mean_bricks_dict": {sensor: mean_bricks_df},
            "timeline_bricks_dict": {sensor: timeline_bricks_df},
            "adj_qcmd_bricks_dict": {sensor: adj_qcmd_bricks_df}
        }
    """

    mean_bricks_dict = {}
    timeline_bricks_dict = {}
    adj_qcmd_bricks_dict = {}

    for sensor in sorted(adj_data_dict.keys()):
        adj_qcmd_pd = adj_data_dict[sensor]
        adj_timeline_pd = adj_timeline_dict[sensor]

        # Get overtone 7 for reference
        adj_qcmd_n7_pd = adj_qcmd_pd[adj_qcmd_pd["Overtone"] == 7]

        # Generate timeline bricks
        timeline_bricks_pd = generate_timeline_bricks(adj_timeline_pd, adj_qcmd_n7_pd)
        timeline_bricks_pd = assign_brick_times(timeline_bricks_pd)

        # Create brick assignments
        adj_qcmd_pd_copy, adj_qcmd_bricks_pd = create_qcmd_bricks(adj_qcmd_pd, timeline_bricks_pd)

        # Calculate means
        mean_brick_pd = calculate_mean_bricks(adj_qcmd_bricks_pd)

        # Store results
        timeline_bricks_dict[sensor] = timeline_bricks_pd
        adj_qcmd_bricks_dict[sensor] = adj_qcmd_bricks_pd
        mean_bricks_dict[sensor] = mean_brick_pd

    return {
        "mean_bricks_dict": mean_bricks_dict,
        "timeline_bricks_dict": timeline_bricks_dict,
        "adj_qcmd_bricks_dict": adj_qcmd_bricks_dict
    }


def generate_timeline_bricks(adj_timeline_pd: pd.DataFrame, adj_qcmd_n7_pd: pd.DataFrame) -> pd.DataFrame:
    """Generate timeline with brick assignments."""

    timeline_bricks_pd = pd.DataFrame(adj_timeline_pd)

    timeline_bricks_pd.rename(columns={
        "Time": "Change_time",
        "Information": "Solution"
    }, inplace=True)

    timeline_bricks_pd["Change_time"] = timeline_bricks_pd["Change_time"].astype(float)
    timeline_bricks_pd["Solution"] = timeline_bricks_pd["Solution"].str.replace("changed to ", "", regex=False)

    # Add end row
    last_speed = timeline_bricks_pd["Speed"].iloc[-1] if len(timeline_bricks_pd) > 0 else 50
    last_time = adj_qcmd_n7_pd["Time_s"].iloc[-1] if len(adj_qcmd_n7_pd) > 0 else 0

    end_row = pd.DataFrame({
        "Change_time": [last_time],
        "Solution": ["end of experiment"],
        "Speed": [last_speed],
        "Block_type": ["static"]
    })

    timeline_bricks_pd = pd.concat([timeline_bricks_pd, end_row], ignore_index=True)

    timeline_bricks_pd["Brick"] = range(1, len(timeline_bricks_pd) + 1)

    return timeline_bricks_pd


def assign_brick_times(timeline_bricks_pd: pd.DataFrame) -> pd.DataFrame:
    """Assign brick start/end times based on block type."""

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


def create_qcmd_bricks(adj_qcmd_pd: pd.DataFrame, timeline_bricks_pd: pd.DataFrame) -> tuple:
    """Assign brick labels to time-resolved data."""

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

    if brick_data:
        adj_qcmd_bricks_pd = pd.concat(brick_data, ignore_index=True)
    else:
        # No bricks found - return empty dataframe with correct columns
        adj_qcmd_bricks_pd = pd.DataFrame(columns=list(adj_qcmd_pd.columns) + ["Brick", "Rel_brick_time_s"])

    return adj_qcmd_pd, adj_qcmd_bricks_pd


def calculate_mean_bricks(adj_qcmd_bricks_pd: pd.DataFrame) -> pd.DataFrame:
    """Calculate mean and std per brick per overtone."""

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

    if not filtered_data:
        return pd.DataFrame()

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


def plot_brick_summary(mean_brick_pd: pd.DataFrame, sensor: int) -> plt.Figure:
    """Generate brick summary plot (bar chart with error bars)."""

    overtones = sorted(mean_brick_pd["Overtone"].unique())
    bricks = sorted(mean_brick_pd["Brick"].unique())

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    ax_f, ax_d = axes

    # Color palettes
    norm = np.linspace(0.3, 1.0, len(overtones))
    freq_colors = {o: cm.Blues(n) for o, n in zip(overtones, norm)}
    diss_colors = {o: cm.OrRd(n) for o, n in zip(overtones, norm)}

    brick_spacing = 2.0
    offsets = np.linspace(-0.4, 0.4, len(overtones))

    for offset, overtone in zip(offsets, overtones):
        df_o = mean_brick_pd[mean_brick_pd["Overtone"] == overtone]
        x_positions = df_o["Brick"] * brick_spacing + offset

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

    xticks = [b * brick_spacing for b in bricks]
    ax_d.set_xticks(xticks)
    ax_d.set_xticklabels(bricks)

    ax_f.set_ylabel("Δf/n [Hz]")
    ax_d.set_ylabel("D/n [ppm]")
    ax_d.set_xlabel("Brick")

    ax_f.grid(axis="x", color="lightgrey", linewidth=0.5)
    ax_d.grid(axis="x", color="lightgrey", linewidth=0.5)

    ax_f.legend(loc="upper left", fontsize=8)

    plt.tight_layout()

    return fig


def plot_full_experiment(adj_qcmd_pd: pd.DataFrame, timeline_bricks_pd: pd.DataFrame, sensor: int) -> plt.Figure:
    """Generate full experiment timeline plot."""

    fig, ax = plt.subplots(figsize=(14, 4))

    df7 = adj_qcmd_pd[adj_qcmd_pd["Overtone"] == 7]

    # Main signals
    ax.plot(df7["Time_s"], df7["Deltaf_div_n_Hz"], color="tab:blue", label="Δf/n")

    ax2 = ax.twinx()
    ax2.plot(df7["Time_s"], df7["Dissipation_ppm"], color="tab:orange", label="D/n")
    ax2.set_ylabel("D/n [ppm]", color="tab:orange")
    ax2.tick_params(axis='y', labelcolor="tab:orange")

    # Shade bricks
    for _, row in timeline_bricks_pd.iterrows():
        start = row["Brick_start"]
        end = row["Brick_end"]

        if pd.isna(start) or pd.isna(end):
            continue

        color = "lightgray" if row["Block_type"] == "static" else "lightblue"
        ax.axvspan(start, end, color=color, alpha=0.3)

    # Vertical lines and labels
    for _, row in timeline_bricks_pd.iterrows():
        change_time = row["Change_time"]

        if pd.isna(change_time):
            continue

        ax.axvline(change_time, color="grey", linestyle="-", linewidth=1, alpha=0.5)

        solution = row["Solution"]
        if solution != "end of experiment":
            speed = row["Speed"]
            ax.text(
                change_time, 1.02, f"{solution} ({int(speed)})",
                transform=ax.get_xaxis_transform(),
                rotation=45, ha="left", va="bottom", fontsize=8
            )

    ax.set_xlim(0, adj_qcmd_pd["Time_s"].max())
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + 0.25 * (ymax - ymin))

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Δf/n [Hz]")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    return fig
