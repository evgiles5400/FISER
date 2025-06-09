# Anomalous Access Detector

A web-based tool for security analysts to upload a CSV of user entitlements, instantly surfacing outliers and gaps.

## Features
- Upload and validate entitlement CSVs (strict schema)
- Set anomaly and baseline thresholds
- Department and Department+Title peer grouping
- Baseline, Anomaly, and Gap analyses
- Interactive dashboard (filter, search, sort)
- Export reports as CSV
- Visualizations (bar charts, heatmaps)
- Handles large datasets (>20MB)

## Setup
1. Clone this repo
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run ui.py
   ```

## CSV Format
Your CSV **must** have these columns in order:
- UserID
- Username
- Acc Priv Category
- Role
- Entitlement
- Acc Priv Group
- Title
- Department

See `sample_data/sample_entitlements.csv` for an example.

## Deliverables
- Working Streamlit dashboard
- Sample CSV
- CSV data export
