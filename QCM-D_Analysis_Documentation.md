# QCM-D Analysis Tool: Scientific Documentation

## Overview

This QCM-D (Quartz Crystal Microbalance with Dissipation) analysis tool provides a two-phase **data preparation and organization** pipeline. It takes raw QCM-D measurements from Q-Tools and converts them into clean, organized, ready-to-compare datasets. These phases enable **direct visualization and comparison** of your data—the foundation for any downstream analysis (Sauerbrey mass extraction, viscoelastic modeling via Voigt or Kelvin-Voigt equations, or other quantitative interpretation).

**Important:** Phases 1 and 2 do not perform analysis themselves. They organize your raw data so you can analyze it reliably.

---

## What QCM-D Measures

Before discussing data processing, it's essential to understand what the raw data represents.

Your QCM-D instrument records two measurements continuously:

- **Δf (Frequency Shift)** [Hz]: The change in the crystal's oscillation frequency from its baseline in air. When mass accumulates on the crystal surface, its frequency decreases. Smaller oscillations result from the added inertial load of surface-bound material.

- **ΔD (Dissipation)** [10⁻⁶]: A measure of energy loss per oscillation cycle. Rigid, elastic materials (like thin metal films) show low dissipation. Soft, viscoelastic materials (like branched proteins or hydrogels) show high dissipation due to internal friction.

Both measurements are recorded at **multiple overtones** (typically n = 3, 5, 7, 9, 11, 13...). For a 5 MHz fundamental frequency crystal, these correspond to actual oscillation frequencies of approximately 15 MHz, 25 MHz, 35 MHz, 45 MHz, 55 MHz, and 65 MHz. Each overtone probes the surface at a different frequency, providing information about the depth and frequency-dependence of your surface layer.

---

## Phase 1: Raw Data Processing and Adjustment

### Input Data Format

The raw data file from Q-Tools is tab-separated with comma decimal separators (European format). Column names follow the pattern:
- `Time_{sensor} [s]`: Time in seconds (one column per sensor)
- `f{overtone}_{sensor} [Hz]`: Frequency in Hz (one per overtone-sensor pair)
- `D{overtone}_{sensor} [ppm]`: Dissipation in ppm (one per overtone-sensor pair)

### Step 1: Data Baseline Correction

**What happens:** Each frequency and dissipation column is baseline-corrected by subtracting the mean of the first 100 data points.

**Why this is necessary:** 
- The instrument's electronic components require brief stabilization upon startup, creating transient artifacts in the raw data
- The air-to-buffer solution exchange produces very large frequency shifts (~300 Hz) that obscure smaller changes (~1–10 Hz) from molecular adsorption without baseline subtraction
- This correction is **purely for visualization clarity**—it rescales the data so all changes are visible on the same plot

**What it preserves:**
- The true dynamics of your experiment—baseline correction doesn't introduce artificial drift or smooth out real changes
- The actual frequency and dissipation changes

**Result:** Cleaned frequency and dissipation time series, normalized to initial 100 data points.

### Step 2: Frequency Display by Overtone Number

**What happens:** Each frequency value is divided by its overtone number (Δf/n).

**Important:** This is **not a normalization**—it's purely a display convenience.

**Why do this?**
- Under Sauerbrey conditions (rigid, evenly-distributed film), the equation Δf_n/n = -C_f × Δm means that **all overtones should give the same Δf/n value** for the same mass change
- By plotting Δf/n instead of raw Δf, you can visually overlay all overtones on the same scale and immediately see if they track together (rigid film) or diverge (viscoelastic behavior)
- Without this division, higher overtones show larger frequency shifts simply due to different penetration depth due to their different wavelengths, making comparison difficult

**What it reveals:**
- **Similar Δf/n across overtones** → Rigid, evenly-distributed mass (Sauerbrey-compliant)
- **Varying Δf/n across overtones** → Viscoelastic or non-uniform material (requires advanced modeling)

### Step 3: Lag Time Correction

**What is lag time?**
- The delay between when your pump switches solutions and when the new solution actually arrives at the sensor crystal
- Depends on tube volume and flow rate: τ_lag = (tube length in mm) / (flow rate in µL/min) × time constant

**What happens:**
- Adjusts the recorded time for each solution change by the lag time so that the timeline marks align with when the solution actually arrives at the sensor

**Formula:**
```
t_corrected = t_recorded + τ_lag(Q)
where τ_lag(Q) = τ_ref × (Q_ref / Q)
```

**Measuring actual lag time:**
To measure the actual lag time for your system, perform a precise air-buffer exchange:
1. Note the exact time the pump is started at 50 µL/min
2. Monitor the frequency signal and record the exact time when it begins to change
3. Calculate the lag time as the difference between pump start time and frequency change onset (in seconds)
4. Enter this lag time value in the program, which will then adjust the lag time accordingly, correcting for the actual speed in your experiment

**Why this matters:**
- Your timeline marks when the pump switched, but the new solution didn't reach the sensor until the lag time had passed
- Correcting this aligns your marked solution changes with the actual frequency/dissipation transients
- Without this correction, your brick windows would include data from the wrong solution phase

**Result:** Adjusted timeline with solution change events precisely aligned to when solutions actually arrived at each sensor.

### Output

While you can perform four measurements on the QCM-D simultaneously, the experiments are not actually related to one another. In this first step, they are saved as individual datasets that can subsequently be analyzed and compared individually.

Phase 1 generates per-sensor CSV files:
- `Data_{ExperimentID}_S{N}_QCMD_adj_qcmd_data.csv`: Cleaned frequency and dissipation data for each sensor
- `Data_{ExperimentID}_S{N}_QCMD_adj_timeline.csv`: Lag-corrected solution change timeline for each sensor

These files are ready for Phase 2 processing or external analysis.

---

## Phase 2: Brick Segmentation and Steady-State Comparison

### Concept: What Are Bricks?

**Important prerequisite:** Adsorption analysis requires stable plateau formation. The brick segmentation analysis assumes a stable plateau for at least 6 minutes before solutions are changed. This stable region provides the reliable data needed to extract meaningful steady-state values.

Experimental time is divided into **bricks**—distinct windows corresponding to different experimental conditions. Two types exist:

**Static Bricks** (between solution changes):
- Time window: from 360 seconds before the next solution change until 60 seconds before
- Duration: 300-second plateau window
- Purpose: Capture steady-state equilibrium within the stable 6+ minute plateau, excluding kinetic uptake and pre-change transients
- Typical use: Comparing adsorbed mass or material properties across different solutions

**Dynamic Bricks** (during active solution flow):
- Time window: entire period when solution is actively flowing
- Duration: variable, based on your timeline
- Purpose: Capture the full kinetic trajectory of adsorption or desorption
- Typical use: Extracting rate constants or watching temporal evolution of material properties

### Brick Assignment and Steady-State Calculation

**For each brick and each overtone:**

1. **Window extraction**: Select data points within the brick's time window
2. **Mean calculation**: Compute mean frequency and dissipation
3. **Standard deviation**: Compute std dev as a measure of stability during that window

**Formula:**
```
⟨Δf/n⟩ᵢ = (1/Nᵢ) × Σ(Δf/n at each time point in window i)
σ(Δf/n)ᵢ = sqrt( (1/Nᵢ) × Σ(Δf/n - ⟨Δf/n⟩ᵢ)² )
```

**Why standard deviation matters:**
- **Low scatter (σ < 2 Hz for frequency)**: Stable plateau—true equilibrium state
- **High scatter (σ > 2 Hz)**: Drift, ongoing kinetics, or system instability during this window—interpretation requires caution

### Three Visualization Plots

**Plot 1: Brick Grid (All Raw Data per Brick)**
- Shows every individual frequency and dissipation data point for each brick
- Frequency (top row) and dissipation (bottom row) displayed as separate subplots
- All overtones overlaid with distinct colors
- Mean value annotated on each frequency plot
- **Purpose:** Visual quality control—assess data scatter, overtone tracking, and whether the plateau is truly stable

**Plot 2: Brick Summary (Bar Chart with Error Bars)**
- Mean ± std dev for each brick-overtone pair
- Frequency panel (top): Shows Δf/n values
- Dissipation panel (bottom): Shows D/n values
- Overtone 7 emphasized with larger markers (primary focus)
- **Purpose:** Quantitative comparison across bricks and overtones at a glance

**Plot 3: Full Experiment Timeline**
- Continuous time series of overtone 7 frequency and dissipation
- Brick regions shaded (light gray = static, light blue = dynamic)
- Vertical lines mark solution change events with labels
- **Purpose:** Context—see kinetic transients, equilibration times, and which bricks capture which phenomena

### Output

Phase 2 generates per-sensor files:
- `Data_{ExperimentID}_S{N}_QCMD_mean_bricks.csv`: Summary table with mean and std dev per brick-overtone pair
- `Data_{ExperimentID}_S{N}_QCMD_timeline_bricks.csv`: Timeline with brick assignments and time windows
- Three PNG plots per sensor (bricks grid, summary, full timeline)

---

## Using Your Prepared Data

Once Phase 1 and 2 are complete, you have clean, organized data ready for analysis:

**For Sauerbrey analysis:**
- Use Phase 2's mean Δf/n values per brick
- If Δf/n is constant across overtones and Dissipation is low, apply Sauerbrey equation to extract mass: Δm = -ΔF / C_f (where C_f ≈ 17.7 Hz·cm²/μg for a 5 MHz crystal)
- The standard deviation tells you measurement uncertainty

**For viscoelastic modeling:**
- Use both frequency and dissipation data from Phase 2
- If Δf/n varies across overtones or dissipation is high, fit a Voigt or Kelvin-Voigt model to extract shear modulus (μ) and shear viscosity (η)
- Multiple overtones provide multiple data points for robust fitting

**For qualitative interpretation:**
- Compare brick summaries across different solution conditions
- Look for patterns in dissipation changes (rigid vs. soft materials)
- Assess reversibility by comparing dynamic brick kinetics with subsequent static brick equilibrium

