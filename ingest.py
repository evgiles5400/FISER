# ingest.py
"""CSV ingest and schema validation for Anomalous Access Detector."""
import pandas as pd

REQUIRED_COLUMNS = [
    "UserID",
    "Username",
    "TID",
    "Acc Priv Category",
    "Role",
    "Entitlement",
    "Acc Priv Group",
    "Title",
    "Department"
]

def validate_and_preview_csv(file_path):
    df = pd.read_csv(file_path)
    if list(df.columns) != REQUIRED_COLUMNS:
        raise ValueError(f"CSV must have columns: {REQUIRED_COLUMNS}")
    return df.head(5)
