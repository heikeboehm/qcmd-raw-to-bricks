# QCM-D Raw → Bricks: Streamlit Data Preparation Tool

A two-phase data preparation and organization pipeline for QCM-D (Quartz Crystal Microbalance with Dissipation) experiments.

## Overview

This tool converts raw QCM-D measurements from Q-Tools into clean, organized datasets ready for downstream analysis. It implements:

- **Phase 1**: Raw data cleaning, baseline correction, lag time adjustment
- **Phase 2**: Brick segmentation and steady-state value extraction

## Features

- Baseline correction for visualization clarity
- Frequency display normalization by overtone for easy comparison
- Automatic lag time correction for solution exchange timing
- Brick segmentation into static (equilibrium) and dynamic (kinetic) windows
- Mean and standard deviation calculation per brick-overtone pair
- Three complementary visualizations: brick grid, brick summary, full timeline
- Batch ZIP export of all results (CSVs + plots)

## Installation

### Local Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/qcmd-raw-to-bricks.git
cd qcmd-raw-to-bricks

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Streamlit Cloud

1. Push this repository to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub account and deploy this repo
4. Streamlit will auto-detect `streamlit_app.py` and run the app

## Usage

### Local

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`.

### Data Format

**Raw data file** (from Q-Tools):
- Tab-separated with comma decimal separators
- Columns: `Time_{sensor}`, `f{overtone}_{sensor}`, `D{overtone}_{sensor}`

**Timeline file** (from Q-Tools):
- Format: `HH:MM:SS S{sensor} {speed}_ul-min change to {solution}`
- Example: `8:48 S1 50_ul-min change to PBS`

### Workflow

1. **Phase 1**:
   - Upload raw data and timeline files
   - Set sensor-specific lag times (calibrate via air-buffer exchange)
   - Process to get baseline-corrected, lag-adjusted data

2. **Phase 2**:
   - Process Phase 1 output through brick segmentation
   - Generates steady-state values and three publication-quality plots
   - Download all results as ZIP

## Documentation

See `QCM-D_Analysis_Documentation.md` for:
- Detailed explanation of each processing step
- Interpretation of results
- Downstream analysis guidance (Sauerbrey, Voigt modeling)

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## Project Structure

```
qcmd-raw-to-bricks/
├── streamlit_app.py                    # Main Streamlit application
├── phase1_utils.py                     # Phase 1 processing wrapper
├── phase2_utils.py                     # Phase 2 processing wrapper
├── QCMD_flow_raw_to_adj_folder.py      # Original Phase 1 analysis code
├── QCMD_flow_adj_to_bricks_folder.py   # Original Phase 2 analysis code
├── QCM-D_Analysis_Documentation.md     # Scientific documentation
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Git ignore rules
└── README.md                           # This file
```

## Key Principles

- **Data Preparation Only**: Phases 1 & 2 organize and prepare data; analysis (Sauerbrey, viscoelastic modeling) happens downstream
- **Live Code Import**: Analysis functions are imported directly from original code files, ensuring changes propagate automatically
- **Quality Control**: Standard deviation within brick windows indicates data stability
- **Multi-Overtone Analysis**: All overtones preserved for interpretation (rigid vs. viscoelastic behavior assessment)

## Notes on Lag Time Calibration

To measure actual lag time for your system:
1. Perform a precise air-buffer exchange at 50 µL/min
2. Note exact pump start time
3. Record exact time when frequency begins to change
4. Lag time = onset time - start time (in seconds)
5. Enter this value per sensor in the app

## Future Enhancements

- Temperature data integration
- Alternative lag time adjustment options
- Voigt/Kelvin-Voigt viscoelastic fitting (Phase 3)
- Sauerbrey mass extraction

## Contact

For questions or issues, contact: boehm.heike@gmail.com

## License

[Choose appropriate license]
