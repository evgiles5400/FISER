# Anomalous Access Detector

A web-based tool for security analysts to upload a CSV of user entitlements, instantly surfacing outliers and gaps.

## Features
- Upload and validate entitlement CSVs (strict schema)
- Set anomaly and baseline thresholds
- Department and Department+Title peer grouping
- Baseline, Anomaly, and Gap analyses
- Interactive dashboard (filter, search, sort)
- Export all reports (CSV/Excel)
- Visualizations (bar charts, heatmaps)
- Handles large datasets (>20MB)
- Automated tests for core logic

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
- TID
- Acc Priv Category
- Role
- Entitlement
- Acc Priv Group
- Title
- Department

See `sample_data/sample_entitlements.csv` for an example.

## Testing
Run all tests with:
```bash
pytest
```

## Deliverables
- Working Streamlit dashboard
- Automated tests
- Sample CSV
- Screenshots in README (to be added)
