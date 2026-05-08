# OPTION_B Timeline Format — Quick Reference Guide

## What Changed

The timeline system now supports **OPTION_B format** with automatic detection and validation. The app still supports your legacy format, but OPTION_B provides better error handling and documentation.

## OPTION_B Format Structure

```
# EXPERIMENT METADATA
EXPERIMENT ID: [your_experiment_id]
DATE: [date]
RESEARCHER: [name]

# SENSORS USED
S1: [surface type] lot [lot#]  |  [prep notes, e.g., new sensor, ozone activated]
S2: [surface type] lot [lot#]  |  [prep notes]
S3: [surface type] lot [lot#]  |  [prep notes]
S4: [surface type] lot [lot#]  |  [prep notes]

# SOLUTION REGISTRY
ShortName | Full description (vendor, lot number, concentration, etc.)
ShortName2 | Another solution description

# TIMELINE
HH:MM:SS S{sensor} {speed}_ul-min {solution_name} [optional: (dynamic)]
```

### Key Rules

1. **Experiment Metadata** (required):
   - Appears first in the file
   - Fields: EXPERIMENT ID, DATE, RESEARCHER
   - Provides permanent record of when/who conducted the experiment

2. **Sensors Used** (required):
   - Documents each sensor's surface type, lot number, and prep notes
   - Format: `S{num}: [type] lot [lot#]  |  [prep notes]`
   - Kept with experiment for reproducibility and traceability

3. **Solution Registry** (required):
   - Format: `ShortName | Description`
   - Each solution must be defined before use
   - No restrictions on short names, but underscores help readability

4. **Timeline** (required):
   - Appears after `# TIMELINE` header
   - Format: `M:SS S{sensor} {speed}_ul-min {solution_name} [(dynamic)]` or `HH:MM:SS S{sensor} ...`
   - Times can be:
     - `M:SS` or `MM:SS` format before 1 hour (e.g., `0:00`, `9:51`, `38:00`)
     - `HH:MM:SS` format after 1 hour (e.g., `1:07:33`, `1:21:14`)
   - Valid sensors: S1, S2, S3, S4
   - Speed: must end with `_ul-min`
   - Solution: must match a registry entry
   - `(dynamic)` marks kinetic measurements (optional)

## Example

```
# SOLUTION REGISTRY
PBS | PBS pH 7.4, isotonic phosphate-buffered saline
PBS_Mg | PBS with 2mM MgCl2
SUV_batch_6249612 | Small unilamellar vesicles, batch 6249612

# TIMELINE
0:00 S1 50_ul-min PBS
9:51 S1 50_ul-min PBS_Mg
38:00 S1 30_ul-min SUV_batch_6249612 (dynamic)
56:55 S1 50_ul-min PBS_Mg
```

## Error Handling

The app now catches common mistakes and shows helpful messages:

| Error | What Went Wrong | Fix |
|-------|-----------------|-----|
| Missing `\|` in registry | Forgot pipe separator | Use: `ShortName \| Description` |
| Unknown solution in timeline | Timeline references undefined solution | Add solution to registry first |
| Invalid sensor name | Used S5, S0, or misspelled | Use S1, S2, S3, or S4 |
| Invalid time format | Time not in HH:MM:SS format | Use format like `1:23:45` |
| Invalid speed format | Speed doesn't end with `_ul-min` | Use format like `50_ul-min` |

## Format Detection

The app automatically detects which format you're using:

- **OPTION_B detected**: File contains `# SOLUTION REGISTRY` section
- **Legacy format detected**: File doesn't have registry section (old format still works!)

The Processing results will show you which format was detected.

## Download Template

In Phase 1, click **📋 Download Timeline Template** to get a pre-formatted OPTION_B template you can fill in with your experiment data.

## Benefits of OPTION_B

✓ Defines all solutions upfront (prevents undefined references)
✓ Full metadata in registry (permanent record, publication-ready)
✓ Clear error messages (exact line and problem)
✓ Less error-prone (small typos caught and explained)
✓ Reusable (same solution registry across experiments)

## Testing with Your Existing Timeline

Your existing timeline data (from the uploaded file) has already been converted to show OPTION_B structure in `TIMELINE_TEMPLATE_OPTION_B.txt`. You can:

1. Review the template
2. Download it and edit with your own solutions
3. Upload it to test the new validation

## Backwards Compatibility

Don't want to convert yet? No problem! The app still fully supports the legacy format:

```
0:00 S1 50_ul-min PBS
0:00 S2 50_ul-min PBS
9:51 S1 50_ul-min changed to PBS_Mg
```

Both formats work. OPTION_B just adds better error handling and documentation.
