"""
QCM-D Analysis Tool — Streamlit App
Raw Data → Bricks (Phases 1 & 2)
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Streamlit

import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="QCM-D Raw → Bricks",
    page_icon="🧱",
    layout="wide",
)

# Reduce vertical whitespace
st.markdown("""
    <style>
        h1 {
            margin-top: -1.5rem !important;
            margin-bottom: 0.2rem !important;
        }
        h2, h3, h4, h5, h6 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        .stDivider {
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        .stMarkdown {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }
        .stInfo, .stSuccess, .stError, .stWarning {
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        .stButton {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }
        .stSelectbox, .stNumberInput, .stFileUploader {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }
        [data-testid="column"] {
            align-items: flex-start !important;
        }
    </style>
""", unsafe_allow_html=True)

col_title, col_info = st.columns([3, 1])

with col_title:
    st.title("🧱 QCM-D Raw → Bricks")

with col_info:
    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
**Two-phase data preparation:**
- Phase 1: Baseline correction, lag adjustment
- Phase 2: Brick segmentation, steady-state values

See QCM-D_Analysis_Documentation.md for details.
        """)

# ============================================================================
# SESSION STATE
# ============================================================================

if "phase1_complete" not in st.session_state:
    st.session_state.phase1_complete = False
if "adj_data_dict" not in st.session_state:
    st.session_state.adj_data_dict = {}
if "adj_timeline_dict" not in st.session_state:
    st.session_state.adj_timeline_dict = {}
if "persistent_id" not in st.session_state:
    st.session_state.persistent_id = None
if "phase2_complete" not in st.session_state:
    st.session_state.phase2_complete = False
if "mean_bricks_dict" not in st.session_state:
    st.session_state.mean_bricks_dict = {}
if "timeline_bricks_dict" not in st.session_state:
    st.session_state.timeline_bricks_dict = {}
if "adj_qcmd_bricks_dict" not in st.session_state:
    st.session_state.adj_qcmd_bricks_dict = {}

# ============================================================================
# PHASE 1: UPLOAD & PROCESS
# ============================================================================

st.subheader("Phase 1: Raw Data Processing")

col_raw, col_timeline = st.columns(2)

with col_raw:
    raw_file = st.file_uploader("Raw data file", type=["txt"], key="raw_uploader")

with col_timeline:
    timeline_file = st.file_uploader("Timeline file", type=["txt"], key="timeline_uploader")

st.markdown("**Lag times (seconds at 50 µl/min):**")
lag_col1, lag_col2, lag_col3, lag_col4, lag_col5, lag_col6, lag_col7, lag_col8 = st.columns([0.3, 0.7, 0.3, 0.7, 0.3, 0.7, 0.3, 0.7])

with lag_col1:
    st.write("S1:")
with lag_col2:
    lag_s1 = st.number_input("S1", value=2.7, step=0.1, label_visibility="collapsed")

with lag_col3:
    st.write("S2:")
with lag_col4:
    lag_s2 = st.number_input("S2", value=2.0, step=0.1, label_visibility="collapsed")

with lag_col5:
    st.write("S3:")
with lag_col6:
    lag_s3 = st.number_input("S3", value=2.8, step=0.1, label_visibility="collapsed")

with lag_col7:
    st.write("S4:")
with lag_col8:
    lag_s4 = st.number_input("S4", value=2.7, step=0.1, label_visibility="collapsed")

lag_times = {1: lag_s1, 2: lag_s2, 3: lag_s3, 4: lag_s4}

# ============================================================================
# PROCESS PHASE 1
# ============================================================================

if raw_file and timeline_file:
    if st.button("🚀 Process Phase 1", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                from phase1_utils import process_phase1

                # Extract persistent ID
                persistent_id = raw_file.name.replace("Data_", "").replace("_rawdata.txt", "")

                # Run processing
                result = process_phase1(
                    raw_file=raw_file,
                    timeline_file=timeline_file,
                    lag_times=lag_times,
                    persistent_id=persistent_id
                )

                st.session_state.adj_data_dict = result["adj_data_dict"]
                st.session_state.adj_timeline_dict = result["adj_timeline_dict"]
                st.session_state.phase1_complete = True

            except ValueError as e:
                st.error("❌ File format error: Check that raw data and timeline files are in the correct format")
                with st.expander("Details"):
                    st.code(str(e))
            except Exception as e:
                st.error(f"❌ Processing error: {str(e)}")
                with st.expander("Details"):
                    st.code(str(e))

# ============================================================================
# RESULTS
# ============================================================================

if st.session_state.phase1_complete:
    st.divider()
    st.subheader("Results")

    sensors = sorted(st.session_state.adj_data_dict.keys())
    st.success(f"✓ Processed {len(sensors)} sensors")

    # Download all data as ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for sensor in sensors:
            # Add adjusted data
            csv_adj = st.session_state.adj_data_dict[sensor].to_csv(index=False)
            zf.writestr(f"Data_S{int(sensor)}_QCMD_adj_qcmd_data.csv", csv_adj)

            # Add timeline
            csv_timeline = st.session_state.adj_timeline_dict[sensor].to_csv(index=False)
            zf.writestr(f"Data_S{int(sensor)}_QCMD_adj_timeline.csv", csv_timeline)

    zip_buffer.seek(0)

    # Extract persistent ID from filename
    if st.session_state.persistent_id is None and raw_file:
        st.session_state.persistent_id = raw_file.name.replace("Data_", "").replace("_rawdata.txt", "")

    zip_filename = f"{st.session_state.persistent_id}_adj_file.zip" if st.session_state.persistent_id else "phase1_data.zip"

    st.download_button(
        label="📥 Download All Phase 1 Data (ZIP)",
        data=zip_buffer.getvalue(),
        file_name=zip_filename,
        mime="application/zip",
        use_container_width=True
    )

    # ========================================================================
    # PHASE 2: BRICK SEGMENTATION
    # ========================================================================

    st.subheader("Phase 2: Brick Segmentation")

    if st.button("🚀 Process Phase 2", use_container_width=True):
        with st.spinner("Segmenting into bricks..."):
            try:
                from phase2_utils import process_phase2

                result = process_phase2(
                    adj_data_dict=st.session_state.adj_data_dict,
                    adj_timeline_dict=st.session_state.adj_timeline_dict
                )

                st.session_state.mean_bricks_dict = result["mean_bricks_dict"]
                st.session_state.timeline_bricks_dict = result["timeline_bricks_dict"]
                st.session_state.adj_qcmd_bricks_dict = result["adj_qcmd_bricks_dict"]
                st.session_state.phase2_complete = True

            except Exception as e:
                st.error(f"❌ Phase 2 processing error: {str(e)}")
                with st.expander("Details"):
                    st.code(str(e))

    # Phase 2 results
    if st.session_state.phase2_complete:
        sensors = sorted(st.session_state.mean_bricks_dict.keys())

        # Generate plots and prepare download
        from phase2_utils import plot_bricks_for_streamlit, plot_summary_for_streamlit, plot_full_for_streamlit

        # First, generate and save all plots to ZIP
        plot_dict = {}  # Store figures for display later

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for sensor in sensors:
                # CSVs
                csv_mean = st.session_state.mean_bricks_dict[sensor].to_csv(index=False)
                zf.writestr(f"Data_S{int(sensor)}_QCMD_mean_bricks.csv", csv_mean)

                csv_timeline = st.session_state.timeline_bricks_dict[sensor].to_csv(index=False)
                zf.writestr(f"Data_S{int(sensor)}_QCMD_timeline_bricks.csv", csv_timeline)

                # Generate plots using wrappers that capture figures before they're closed
                fig_bricks = plot_bricks_for_streamlit(
                    st.session_state.adj_qcmd_bricks_dict[sensor],
                    st.session_state.mean_bricks_dict[sensor],
                    st.session_state.timeline_bricks_dict[sensor],
                    sensor
                )
                fig_summary = plot_summary_for_streamlit(
                    st.session_state.mean_bricks_dict[sensor],
                    sensor
                )
                fig_full = plot_full_for_streamlit(
                    st.session_state.adj_data_dict[sensor],
                    st.session_state.timeline_bricks_dict[sensor],
                    sensor
                )

                # Store for later display
                plot_dict[sensor] = {"bricks": fig_bricks, "summary": fig_summary, "full": fig_full}

                # Save to ZIP - bricks plot
                bricks_bytes = BytesIO()
                fig_bricks.savefig(bricks_bytes, format='png', dpi=100, bbox_inches='tight')
                bricks_bytes.seek(0)
                zf.writestr(f"Plot_S{int(sensor)}_bricks_plot.png", bricks_bytes.getvalue())

                # Save to ZIP - brick summary
                summary_bytes = BytesIO()
                fig_summary.savefig(summary_bytes, format='png', dpi=100, bbox_inches='tight')
                summary_bytes.seek(0)
                zf.writestr(f"Plot_S{int(sensor)}_brick_summary.png", summary_bytes.getvalue())

                # Save to ZIP - full experiment
                full_bytes = BytesIO()
                fig_full.savefig(full_bytes, format='png', dpi=100, bbox_inches='tight')
                full_bytes.seek(0)
                zf.writestr(f"Plot_S{int(sensor)}_full_experiment.png", full_bytes.getvalue())

        zip_buffer.seek(0)
        zip_filename = f"{st.session_state.persistent_id}_bricks_file.zip" if st.session_state.persistent_id else "phase2_data.zip"

        st.download_button(
            label="📥 Download All Phase 2 Data (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=zip_filename,
            mime="application/zip",
            use_container_width=True
        )

        st.divider()

        # Display plots and data for each sensor (using stored figures)
        for sensor in sensors:
            st.markdown(f"**Sensor S{int(sensor)}:**")

            # Display bricks plot (full width)
            st.pyplot(plot_dict[sensor]["bricks"])

            # Display summary and full experiment side by side
            col1, col2 = st.columns(2)

            with col1:
                st.pyplot(plot_dict[sensor]["summary"])

            with col2:
                st.pyplot(plot_dict[sensor]["full"])

            # Close plots after display
            plt.close(plot_dict[sensor]["bricks"])
            plt.close(plot_dict[sensor]["summary"])
            plt.close(plot_dict[sensor]["full"])

