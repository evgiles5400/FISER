# FIS Entitlements Review

A comprehensive web-based tool for security analysts and compliance teams to analyze user entitlements, identify anomalous access patterns, and detect gaps in baseline access across organizational groups.

## Overview

FIS Entitlements Review helps organizations maintain the principle of least privilege by analyzing user access rights and identifying potential security risks. The application processes CSV data containing user entitlements and performs three key analyses:

1. **Baseline Access Analysis**: Identifies common entitlements that most users in a peer group have, establishing a baseline for expected access.
2. **Anomalous Access Detection**: Flags unusual entitlements that few users in a peer group possess, which may indicate excessive privileges.
3. **Gap Analysis**: Identifies users missing baseline entitlements that are common for their peer group, which may indicate incomplete access provisioning.

## Benefits

- **Enhanced Security Posture**: Quickly identify over-privileged accounts that could pose security risks
- **Compliance Support**: Generate reports for access reviews required by regulations like SOX, HIPAA, or GDPR
- **Streamlined Access Management**: Identify access patterns to improve role definitions and access provisioning
- **Efficient Reviews**: Reduce manual effort in periodic access reviews by automatically highlighting anomalies
- **Flexible Analysis**: Compare access patterns within departments or specific job titles

## Features

- Upload and validate entitlement CSVs with strict schema validation
- Configure anomaly and baseline thresholds to adjust sensitivity
- Choose between Department-wide or Department+Title peer grouping
- Interactive dashboard with filtering, searching, and sorting capabilities
- Export findings as CSV for further analysis
- Generate comprehensive TXT reports with all analysis results

## Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation
1. Clone this repository:
   ```bash
   git clone [https://github.com/yourusername/FISER.git](https://github.com/yourusername/FISER.git)
   cd FISER

2. Create and activate a virtual environment (recommended):
   # On Windows
   python -m venv .venv
   .venv\Scripts\activate

   # On macOS/Linux
   python -m venv .venv
   source .venv/bin/activate

3. Install required packages:

   pip install -r requirements.txt

4. Run the application:

   streamlit run ui.py

The application will be available at http://localhost:8501 in your web browser.

## Usage Guide
Upload Data: Use the file uploader to select your CSV file containing entitlement data
Configure Analysis:
- Set the peer group type (Department-wide or Department+Title)
- Adjust baseline threshold (% of users that must have an entitlement to be considered baseline)
- Adjust anomaly threshold (% of users that have an entitlement below which it's considered anomalous)
- Review Results: Navigate through the tabs to view baseline access, anomalies, and gap reports
- Export Findings: Download CSV reports for specific analyses or a comprehensive TXT report

## CSV Format Requirements
Your CSV file must have these columns in exactly this order:

| Column            | Description                                     |
| ----------------- | ----------------------------------------------- |
| UserID            | Unique identifier for each user                 |
| Username          | User's login name                               |
| Acc Priv Category | Access privilege category                       |
| Role              | User's role or job function                     |
| Entitlement       | Specific permission or access right             |
| Acc Priv Group    | Access privilege grouping                       |
| Title             | User's job title                                |
| Department        | User's department                               |

A sample CSV file is provided at sample_data/sample_entitlements.csv for reference.

## How It Works

### Analysis Methods
The application uses the following methods to analyze entitlements:
- Peer Grouping: Users are grouped either by Department alone or by Department+Title combinations
- Threshold-Based Analysis:
  - Baseline: Entitlements held by ≥X% of users in a peer group
  - Anomalies: Entitlements held by ≤Y% of users in a peer group
- Gap Detection: Compares each user's entitlements against the baseline for their peer group

### Technical Implementation
The application is built using:
- Streamlit: For the web interface and interactive components
- Pandas: For data processing and analysis
- Plotly: For data visualization capabilities

### Troubleshooting
- CSV Upload Issues: Ensure your CSV is UTF-8 encoded and follows the exact column structure
- No Results: Try adjusting the threshold percentages to be more inclusive
- Performance Issues: For large datasets, consider filtering your data before upload   