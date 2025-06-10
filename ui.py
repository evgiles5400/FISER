# ui.py
"""Streamlit UI entrypoint for Anomalous Access Detector."""

import streamlit as st
import pandas as pd
# import plotly.express as px # Not used in the current version, can be removed if not needed later
from ingest import validate_and_preview_csv, REQUIRED_COLUMNS # Assuming ingest.py is in the same directory or PYTHONPATH
from analysis import baseline_access, anomalies, gap_report # Assuming analysis.py is in the same directory or PYTHONPATH
import io
import os
from datetime import datetime

def generate_txt_report(filename, df, peer_group, baseline_threshold, anomaly_threshold, users_wo_title,
                       baseline_df_display=None, anomalies_display=None, gap_data_df=None):
    """Generate a comprehensive text report with all analysis results."""
    # Helper function to truncate text and add ellipsis if needed
    def truncate_text(text, max_length):
        text = str(text)
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + '...'
    # Initialize report string
    report = []
    
    # Add report header
    report.append("="*80)
    report.append("FIS ENTITLEMENTS REVIEW REPORT")
    report.append("="*80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n")
    
    # Add configuration section
    report.append("-"*80)
    report.append("CONFIGURATION")
    report.append("-"*80)
    report.append(f"File: {filename}")
    report.append(f"Peer Group Type: {peer_group}")
    report.append(f"Baseline Threshold: {baseline_threshold}%")
    report.append(f"Anomaly Threshold: {anomaly_threshold}%")
    report.append("\n")
    
    # Add dataset metrics
    report.append("-"*80)
    report.append("DATASET METRICS")
    report.append("-"*80)
    report.append(f"Total Records: {len(df)}")
    report.append(f"Unique Users: {df['UserID'].nunique()}")
    report.append(f"Departments: {df['Department'].nunique()}")
    report.append(f"Roles: {df['Role'].nunique()}")
    report.append(f"Entitlements: {df['Entitlement'].nunique()}")
    report.append(f"Users Without Title: {users_wo_title}")
    report.append("\n")
    
    # Add gap report section
    report.append("-"*80)
    report.append("GAP REPORT (MISSING BASELINE ACCESS)")
    report.append("-"*80)
    report.append(f"Users missing common roles/entitlements (from baseline) for their '{peer_group}' peer group.")
    report.append("\n")
    
    if gap_data_df is not None and not gap_data_df.empty:
        # Get column names for header
        columns = gap_data_df.columns
        
        # Create a format string based on the columns
        format_parts = []
        header_parts = []
        col_widths = {}
        for col in columns:
            width = max(len(col), 20)
            col_widths[col] = width
            format_parts.append(f"{{:{width}}}")
            header_parts.append(col)
        
        format_str = " ".join(format_parts)
        
        # Create header
        report.append(format_str.format(*header_parts))
        report.append("-" * (sum(col_widths.values()) + len(columns) - 1))
        
        # Add rows
        for _, row in gap_data_df.iterrows():
            # Truncate values if needed
            truncated_values = [truncate_text(row[col], col_widths[col]) for col in columns]
            report.append(format_str.format(*truncated_values))
    else:
        report.append("No gaps found (all users appear to have baseline access for their group).")
    report.append("\n")
    
    # Add anomalies section
    report.append("-"*80)
    report.append("ANOMALOUS ACCESS")
    report.append("-"*80)
    report.append(f"Users with roles/entitlements held by fewer than {anomaly_threshold}% of their '{peer_group}' peers.")
    report.append("\n")
    
    if anomalies_display is not None and not anomalies_display.empty:
        # Create header
        dept_width = 20
        title_width = 20
        user_width = 30
        role_width = 30
        ent_width = 10
        report.append(f"{'Department':<{dept_width}} {'Title':<{title_width}} {'User':<{user_width}} {'Anomalous Role':<{role_width}} {'Anomalous Entitlements':<{ent_width}}")
        report.append("-"*110)
        
        # Add rows
        for _, row in anomalies_display.iterrows():
            dept = truncate_text(row['Department'], dept_width)
            title = truncate_text(row['Title'], title_width)
            user = truncate_text(row['User'], user_width)
            role = truncate_text(row['Anomalous Role'], role_width)
            ent = truncate_text(row['Anomalous Entitlements'], ent_width)
            report.append(f"{dept:<{dept_width}} {title:<{title_width}} {user:<{user_width}} {role:<{role_width}} {ent:<{ent_width}}")
    else:
        report.append("No anomalies found based on current criteria.")
    report.append("\n")
    
    # Add baseline access section
    report.append("-"*80)
    report.append("BASELINE ACCESS")
    report.append("-"*80)
    report.append(f"Common roles held by at least {baseline_threshold}% of users in their '{peer_group}' peer group.")
    report.append("\n")
    
    if baseline_df_display is not None and not baseline_df_display.empty:
        # Format baseline data as a table
        if peer_group == "Department-wide":
            # Create header
            dept_width = 30
            role_width = 50
            report.append(f"{'Department':<{dept_width}} {'Role':<{role_width}}")
            report.append("-"*80)
            
            # Add rows
            for _, row in baseline_df_display.iterrows():
                dept = truncate_text(row['Department'], dept_width)
                role = truncate_text(row['Role'], role_width)
                report.append(f"{dept:<{dept_width}} {role:<{role_width}}")
        else:  # Department + Title
            # Create header
            dept_width = 20
            title_width = 30
            role_width = 50
            report.append(f"{'Department':<{dept_width}} {'Title':<{title_width}} {'Role':<{role_width}}")
            report.append("-"*100)
            
            # Add rows
            for _, row in baseline_df_display.iterrows():
                dept = truncate_text(row['Department'], dept_width)
                title = truncate_text(row['Title'], title_width)
                role = truncate_text(row['Role'], role_width)
                report.append(f"{dept:<{dept_width}} {title:<{title_width}} {role:<{role_width}}")
    else:
        report.append("No baseline data available based on current criteria.")
    
    # Return the complete report as a string
    return "\n".join(report)

def main():
    st.set_page_config(page_title="FIS Entitlements Review", layout="wide")
    st.title("FIS Entitlements Review")
    st.write("Upload a CSV of user entitlements to analyze baseline access, anomalies, and gaps.")

    uploaded_file = st.file_uploader("Upload Entitlements CSV", type=["csv"])

    if uploaded_file:
        try:
            print(f"DEBUG_CSV: uploaded_file object: {uploaded_file}")
            uploaded_file.seek(0) # Reset stream position
            try:
                print("DEBUG_CSV: Attempting to read and decode uploaded file as UTF-8.")
                # It's crucial that uploaded_file.read() returns bytes
                file_bytes = uploaded_file.read()
                if not isinstance(file_bytes, bytes):
                    st.error(f"DEBUG_CSV: File read did not return bytes, got {type(file_bytes)}. Cannot decode.")
                    print(f"DEBUG_CSV: File read did not return bytes, got {type(file_bytes)}. Cannot decode.")
                    return
                csv_string_data = file_bytes.decode('utf-8')
                print("DEBUG_CSV: Successfully decoded to string. Now parsing with pandas from io.StringIO.")
                df = pd.read_csv(io.StringIO(csv_string_data))
                print("DEBUG_CSV: Successfully parsed CSV with pandas.")
            except UnicodeDecodeError as ude:
                print(f"DEBUG_CSV: UnicodeDecodeError while decoding file: {ude}")
                st.error(f"Error decoding file: The file does not appear to be UTF-8 encoded. Please ensure it's UTF-8. Details: {ude}")
                return # Stop processing
            except Exception as e_pandas: # Catch more general pandas errors
                print(f"DEBUG_CSV: Error during pandas parsing from StringIO: {e_pandas}")
                st.error(f"Error parsing CSV data: {e_pandas}")
                return # Stop processing
            
            # Validate CSV columns using the imported REQUIRED_COLUMNS
            if list(df.columns) != REQUIRED_COLUMNS:
                st.error(f"CSV validation failed. Expected columns: {REQUIRED_COLUMNS}. Found: {list(df.columns)}.")
                st.info("Please ensure the uploaded CSV has the correct headers in the correct order and no extra columns.")
                return # Stop processing
            
            st.success("CSV schema valid!")
            with st.expander("Preview Data (First 5 Rows)", expanded=False):
                st.dataframe(df.head(5))

            # --- Configuration Panel ---
            st.sidebar.header("Configuration Panel")
            anomaly_threshold = st.sidebar.number_input(
                "Anomaly Threshold (%):",
                min_value=0.1, max_value=100.0, value=2.0, step=0.1,
                help="Flag privileges held by fewer than this percent of peers as anomalous."
            )
            baseline_threshold = st.sidebar.number_input(
                "Baseline Threshold (%):",
                min_value=0.1, max_value=100.0, value=95.0, step=0.1,
                help="Define 'common' privileges (held by at least this percent of peers)."
            )
            peer_group_options = ["Department-wide", "Department + Title"]
            peer_group = st.sidebar.radio(
                "Choose Peer Group Definition:",
                peer_group_options,
                index=0, # Default to "Department-wide"
                help="'Department-wide': Peers are all users in the same department. 'Department + Title': Peers are users in the same department with the same title."
            )
            st.sidebar.info(f"Using: Anomaly {anomaly_threshold}%, Baseline {baseline_threshold}%, Peer group: {peer_group}")

            # --- Dataset Metrics ---
            st.markdown("---")
            st.header("Dataset Metrics")
            users_wo_title = df[df['Title'].isnull() | (df['Title'].astype(str).str.strip() == '')]['UserID'].nunique()
            col1_metrics, col2_metrics, col3_metrics = st.columns(3)
            col1_metrics.metric("Total Records", len(df))
            col1_metrics.metric("Unique Users", df['UserID'].nunique())
            col1_metrics.metric("Unique Departments", df['Department'].nunique())
            col2_metrics.metric("Unique Titles", df['Title'].nunique())
            col2_metrics.metric("Unique Roles", df['Role'].nunique())
            col2_metrics.metric("Unique Access Groups", df['Acc Priv Group'].nunique())
            col3_metrics.metric("Unique Access Categories", df['Acc Priv Category'].nunique())
            col3_metrics.metric("Unique Entitlements", df['Entitlement'].nunique())
            col3_metrics.metric("Users w/o Title", users_wo_title)

            # Filter out users with no Title for baseline analysis if peer group involves Title
            df_for_baseline_analysis = df.copy()
            if peer_group == "Department + Title":
                 df_for_baseline_analysis = df[df['Title'].notnull() & (df['Title'].astype(str).str.strip() != '')].copy() # Use .copy() to avoid SettingWithCopyWarning
                 if len(df_for_baseline_analysis) < len(df):
                     st.warning(f"{len(df) - len(df_for_baseline_analysis)} records without a Title were excluded from 'Department + Title' peer group analysis for baseline calculation.")

            # --- Core Analyses ---
            st.markdown("---")
            st.header("Core Analyses & Reports")
            
            # Run analyses
            baseline_data_dict = baseline_access(df_for_baseline_analysis, baseline_threshold, peer_group)
            anomalies_data_df = anomalies(df, anomaly_threshold, peer_group) 
            gap_data_df = gap_report(df, baseline_data_dict, peer_group)

            # --- Report Generation ---

            # --- Display & Download Sections ---
            tab1, tab2, tab3 = st.tabs(["Baseline Access", "Anomalous Access", "Gap Report"])

            with tab1:
                st.subheader("1. Baseline Access")
                st.caption(f"Common roles held by at least {baseline_threshold}% of users in their '{peer_group}' peer group.")
                baseline_display_list = []
                
                # Process baseline data to extract unique roles per department
                if peer_group == "Department-wide":
                    cols_display = ["Department", "Role"]
                    # Create a dictionary to track unique roles per department
                    dept_roles = {}
                    
                    for group_key, entitlements_set in baseline_data_dict.items():
                        dept = group_key[0] if isinstance(group_key, tuple) else group_key
                        if dept not in dept_roles:
                            dept_roles[dept] = set()
                            
                        # Extract just the role name from each (role, percentage) tuple
                        for role, _ in entitlements_set:
                            dept_roles[dept].add(role)
                    
                    # Convert to display format with unique roles
                    for dept, roles in dept_roles.items():
                        for role in sorted(roles):
                            baseline_display_list.append({"Department": dept, "Role": role})
                            
                    baseline_df_display = pd.DataFrame(baseline_display_list, columns=cols_display) if baseline_display_list else pd.DataFrame(columns=cols_display)
                
                elif peer_group == "Department + Title":
                    cols_display = ["Department", "Title", "Role"]
                    # Create a dictionary to track unique roles per department+title
                    dept_title_roles = {}
                    
                    for group_key, entitlements_set in baseline_data_dict.items():
                        dept, title = group_key
                        key = (dept, title)
                        if key not in dept_title_roles:
                            dept_title_roles[key] = set()
                            
                        # Extract just the role name from each (role, percentage) tuple
                        for role, _ in entitlements_set:
                            dept_title_roles[key].add(role)
                    
                    # Convert to display format with unique roles
                    for (dept, title), roles in dept_title_roles.items():
                        for role in sorted(roles):
                            baseline_display_list.append({"Department": dept, "Title": title, "Role": role})
                    baseline_df_display = pd.DataFrame(baseline_display_list, columns=cols_display) if baseline_display_list else pd.DataFrame(columns=cols_display)
                
                st.dataframe(baseline_df_display)
                if not baseline_df_display.empty:
                    csv_baseline = baseline_df_display.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Baseline as CSV", csv_baseline, "baseline_access.csv", "text/csv", key="csv_baseline")
                else:
                    st.write("No baseline data to display based on current criteria.")

            with tab2:
                st.subheader("2. Anomalous Access")
                st.caption(f"Users with roles/entitlements held by fewer than {anomaly_threshold}% of their '{peer_group}' peers.")
                
                if not anomalies_data_df.empty:
                    # Process anomalies data to group by user and their anomalous roles
                    try:
                        # Ensure we have all required columns
                        required_columns = ['Group', 'UserID', 'Username', 'Role', 'Entitlement']
                        missing_cols = [col for col in required_columns if col not in anomalies_data_df.columns]
                        if missing_cols:
                            raise ValueError(f"Missing required columns in anomalies data: {', '.join(missing_cols)}")
                        
                        # Format the display while keeping UserID for PDF generation
                        display_data = []
                        
                        # Handle both peer group types
                        if peer_group == "Department-wide":
                            anomalies_data_df['Department'] = anomalies_data_df['Group'].apply(
                                lambda x: x[0] if isinstance(x, tuple) else x
                            )
                            
                            # Get titles from the original dataframe
                            title_map = {}
                            for user_id in anomalies_data_df['UserID'].unique():
                                user_titles = df[df['UserID'] == user_id]['Title'].unique()
                                if len(user_titles) > 0:
                                    title_map[user_id] = user_titles[0]
                                else:
                                    title_map[user_id] = 'N/A'
                            
                            for (dept, user_id, username, role), group in anomalies_data_df.groupby(['Department', 'UserID', 'Username', 'Role']):
                                display_data.append({
                                    'Department': dept,
                                    'UserID': user_id,
                                    'Username': username,
                                    'User': f"{username} ({user_id})",  # For display
                                    'Title': title_map.get(user_id, 'N/A'),  # Get title from original data
                                    'Anomalous Role': role,
                                    'Anomalous Entitlements': len(group['Entitlement'].unique())
                                })
                        else:  # Department + Title
                            # Handle the case where Group might be a string or tuple
                            if isinstance(anomalies_data_df['Group'].iloc[0], tuple):
                                anomalies_data_df[['Department', 'Title']] = pd.DataFrame(
                                    anomalies_data_df['Group'].tolist(), 
                                    index=anomalies_data_df.index
                                )
                            else:
                                anomalies_data_df['Department'] = anomalies_data_df['Group']
                                anomalies_data_df['Title'] = 'N/A'
                            
                            # Format the display while keeping UserID for PDF generation
                            for (dept, title, user_id, username, role), group in anomalies_data_df.groupby(['Department', 'Title', 'UserID', 'Username', 'Role']):
                                display_data.append({
                                    'Department': dept,
                                    'UserID': user_id,
                                    'Username': username,
                                    'User': f"{username} ({user_id})",
                                    'Title': title if pd.notna(title) and str(title).strip() else 'N/A',
                                    'Anomalous Role': role,
                                    'Anomalous Entitlements': len(group['Entitlement'].unique())
                                })
                        
                        # Create the display dataframe
                        anomalies_display = pd.DataFrame(display_data)
                        
                        # Display the anomalies
                        st.dataframe(
                            anomalies_display[['Department', 'Title', 'User', 'Anomalous Role', 'Anomalous Entitlements']],
                            column_config={
                                'User': 'User',
                                'Anomalous Role': 'Anomalous Role',
                                'Anomalous Entitlements': 'Anomalous Entitlements',
                                'Title': 'Job Title',
                                'Department': 'Department'
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Add CSV download button
                        csv = anomalies_display[['Department', 'Title', 'User', 'Anomalous Role', 'Anomalous Entitlements']].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "Download Anomalies as CSV",
                            csv,
                            "anomalies_report.csv",
                            "text/csv",
                            key='download-csv-anomalies'
                        )
                    
                    except Exception as e:
                        st.error(f"Error processing anomalies data: {e}")
                        print(f"Error in anomalies display: {e}")
                else:
                    st.write("No anomalies found based on current criteria.")

            with tab3:
                st.subheader("3. Gap Report (Missing Baseline Access)")
                st.caption(f"Users missing common roles/entitlements (from baseline) for their '{peer_group}' peer group.")
                st.dataframe(gap_data_df) # gap_data_df is already a DataFrame
                if not gap_data_df.empty:
                    csv_gap = gap_data_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Gap Report as CSV", csv_gap, "gap_report.csv", "text/csv", key="csv_gap")
                else:
                    st.write("No gaps found (all users appear to have baseline access for their group).")

        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {e}")
            print(f"ERROR_MAIN_TRY_EXCEPT: Type: {type(e)}, Error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            st.code(f"Traceback:\n{traceback.format_exc()}") # Display traceback in UI for easier debugging by user
            
        # Generate comprehensive TXT report if data is available
        if uploaded_file and not df.empty:
            st.markdown("---")
            st.subheader("Comprehensive Report")
            st.caption("Download a complete text report with all analysis results.")
            
            txt_report = generate_txt_report(
                filename=uploaded_file.name,
                df=df,
                peer_group=peer_group,
                baseline_threshold=baseline_threshold,
                anomaly_threshold=anomaly_threshold,
                users_wo_title=users_wo_title,
                baseline_df_display=baseline_df_display if 'baseline_df_display' in locals() else None,
                anomalies_display=anomalies_display if 'anomalies_display' in locals() else None,
                gap_data_df=gap_data_df if 'gap_data_df' in locals() else None
            )
            
            st.download_button(
                "Download Report as TXT",
                txt_report,
                "fis_entitlements_review_report.txt",
                "text/plain",
                key="txt_report"
            )

if __name__ == "__main__":
    main()
