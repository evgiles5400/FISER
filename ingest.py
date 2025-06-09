# ingest.py
"""CSV ingest and schema validation for Anomalous Access Detector."""
import pandas as pd
import os

REQUIRED_COLUMNS = [
    "UserID",
    "Username",
    "Acc Priv Category",
    "Role",
    "Entitlement",
    "Acc Priv Group",
    "Title",
    "Department"
]

def validate_and_preview_csv(file_path):
    """
    Validate CSV file format and return preview of data.
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        DataFrame: Preview of first 5 rows of data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If CSV format doesn't match requirements
        pd.errors.EmptyDataError: If CSV file is empty
        pd.errors.ParserError: If CSV parsing fails
    """
    # Check file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        # Try to read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if the file is empty
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Check for required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        extra_columns = [col for col in df.columns if col not in REQUIRED_COLUMNS]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        if extra_columns:
            raise ValueError(f"Extra columns found: {', '.join(extra_columns)}")
            
        # Check column order
        if list(df.columns) != REQUIRED_COLUMNS:
            raise ValueError("Columns are in incorrect order. Please ensure columns are in the exact order specified.")
        
        # Check for missing values in important columns
        for col in ["UserID", "Role", "Entitlement", "Department"]:
            if df[col].isna().any():
                missing_count = df[col].isna().sum()
                raise ValueError(f"Column '{col}' contains {missing_count} missing values. All entries must be populated.")
        
        # Return preview
        return df.head(5)
        
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty or contains no data")
    except pd.errors.ParserError:
        raise ValueError("Failed to parse CSV file. Please ensure it's properly formatted.")
