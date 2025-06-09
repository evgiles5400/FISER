# ui.py
"""Streamlit UI entrypoint for Anomalous Access Detector."""

import streamlit as st
import pandas as pd
# import plotly.express as px # Not used in the current version, can be removed if not needed later
from ingest import validate_and_preview_csv, REQUIRED_COLUMNS # Assuming ingest.py is in the same directory or PYTHONPATH
from analysis import baseline_access, anomalies, gap_report # Assuming analysis.py is in the same directory or PYTHONPATH
import io
import fpdf
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import datetime
import os

# Debug prints for FPDF import verification (can be removed in production)
print(f"DEBUG: FPDF module path: {fpdf.__file__}")
try:
    print("DEBUG: Successfully imported XPos and YPos from fpdf.enums")
    print(f"DEBUG: XPos type: {type(XPos)}, YPos type: {type(YPos)}")
    if hasattr(XPos, 'LMARGIN'):
        print(f"DEBUG: XPos.LMARGIN value: {XPos.LMARGIN}") # This should exist
    else:
        print("DEBUG: XPos.LMARGIN does not exist") # This indicates a problem
    if hasattr(YPos, 'NEXT'):
        print(f"DEBUG: YPos.NEXT value: {YPos.NEXT}") # This should exist
    else:
        print("DEBUG: YPos.NEXT does not exist") # This indicates a problem
except ImportError as e_import:
    print(f"DEBUG: Failed to import XPos/YPos from fpdf.enums: {e_import}")
except AttributeError as e_attr:
    print(f"DEBUG: Attribute error accessing XPos/YPos or their members: {e_attr}")

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
                     st.warning(f"{len(df) - len(df_for_baseline_analysis)} users without a Title were excluded from 'Department + Title' peer group analysis for baseline calculation.")

            # --- Core Analyses ---
            st.markdown("---")
            st.header("Core Analyses & Reports")
            
            # Run analyses
            baseline_data_dict = baseline_access(df_for_baseline_analysis, baseline_threshold, peer_group)
            anomalies_data_df = anomalies(df, anomaly_threshold, peer_group) 
            gap_data_df = gap_report(df, baseline_data_dict, peer_group)

            # --- PDF Generation Functions (defined inside main) ---
            def generate_pdf_report(main_df_for_metrics, baseline_data_for_pdf_dict=None, anomalies_df_for_pdf=None, gap_df_for_pdf=None, 
                                    current_peer_group="Department-wide", current_baseline_threshold=95.0, current_anomaly_threshold=2.0, 
                                    num_users_wo_title=0, report_type="full"):
                pdf = FPDF()
                base_font = "Helvetica" 
                
                def add_table_to_pdf(data_frame, title):
                    if data_frame is not None and not data_frame.empty:
                        pdf.set_font(base_font, "B", 12)
                        pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.set_font(base_font, "B", 8) 
                        
                        col_names = list(data_frame.columns)
                        available_width = pdf.w - pdf.l_margin - pdf.r_margin
                        num_cols = len(col_names)
                        default_col_width = available_width / num_cols if num_cols > 0 else available_width
                        col_widths = {col: default_col_width for col in col_names}
                        
                        # Dynamic column width adjustments (example)
                        if 'Role' in col_widths and num_cols > 1: col_widths['Role'] = default_col_width * 1.2
                        if 'Entitlement' in col_widths and num_cols > 1: col_widths['Entitlement'] = default_col_width * 1.5
                        if 'UserID' in col_widths and num_cols > 1: col_widths['UserID'] = default_col_width * 0.8
                        
                        # Re-normalize if adjustments made total width too large
                        current_total_width = sum(col_widths.values())
                        if current_total_width > available_width and num_cols > 0:
                            scale_factor = available_width / current_total_width
                            col_widths = {col: w * scale_factor for col, w in col_widths.items()}
                        
                        pdf.set_fill_color(220, 220, 220)
                        for col_name in col_names:
                            pdf.cell(col_widths[col_name], 7, str(col_name), border=1, fill=True, align="C")
                        pdf.ln() # Use ln() for new line
                        pdf.set_font(base_font, size=7) 
                        pdf.set_fill_color(255, 255, 255) # White background for data cells
                        for _, row_data in data_frame.iterrows():
                            for col_name in col_names:
                                cell_text = str(row_data[col_name])
                                # Simple truncation for long text
                                if pdf.get_string_width(cell_text) > col_widths[col_name] - 2: # -2 for padding
                                    while pdf.get_string_width(cell_text + '...') > col_widths[col_name] - 2 and len(cell_text) > 5:
                                        cell_text = cell_text[:-1]
                                    cell_text += '...'
                                pdf.cell(col_widths[col_name], 6, cell_text, border=1, align="L")
                            pdf.ln() # New line after each row
                        pdf.ln(5) # Extra space after table
                    else:
                        pdf.set_font(base_font, "I", 10)
                        pdf.cell(0, 10, f"No data available for {title}.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.ln(5)

                pdf.add_page()
                pdf.set_font(base_font, "B", 18)
                pdf.cell(0, 15, "FIS Entitlement Review Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.set_font(base_font, size=10)
                pdf.cell(0, 10, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.ln(8)

                pdf.set_font(base_font, "B", 12)
                pdf.cell(0, 10, "Dataset Metrics Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font(base_font, size=9)
                metrics_summary_list = [
                    ("Total Records", len(main_df_for_metrics)), ("Unique Users", main_df_for_metrics['UserID'].nunique()),
                    ("Unique Departments", main_df_for_metrics['Department'].nunique()), ("Unique Titles", main_df_for_metrics['Title'].nunique()),
                    ("Unique Roles", main_df_for_metrics['Role'].nunique()), ("Unique Access Groups", main_df_for_metrics['Acc Priv Group'].nunique()),
                    ("Unique Access Categories", main_df_for_metrics['Acc Priv Category'].nunique()), ("Unique Entitlements", main_df_for_metrics['Entitlement'].nunique()),
                    ("Users w/o Title (in input)", num_users_wo_title)
                ]
                metrics_col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2 # Width for one metric item (label + value)
                
                for i in range(0, len(metrics_summary_list), 2): # Process two metrics per line
                    pdf.set_x(pdf.l_margin) # Ensure starting at left margin
                    # Metric 1
                    pdf.set_font(base_font, "B", 9)
                    pdf.cell(metrics_col_w * 0.6, 6, str(metrics_summary_list[i][0]) + ':', border=0, align='R')
                    pdf.set_font(base_font, "", 9) # Regular font for value
                    pdf.cell(metrics_col_w * 0.4, 6, str(metrics_summary_list[i][1]), border=0, new_x=XPos.RIGHT, align='L') # Move to right for next metric
                    
                    # Metric 2 (if exists)
                    if i + 1 < len(metrics_summary_list):
                        pdf.set_font(base_font, "B", 9)
                        pdf.cell(metrics_col_w * 0.6, 6, str(metrics_summary_list[i+1][0]) + ':', border=0, align='R')
                        pdf.set_font(base_font, "", 9) # Regular font for value
                        pdf.cell(metrics_col_w * 0.4, 6, str(metrics_summary_list[i+1][1]), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L') # New line after second metric
                    else:
                        pdf.ln(6) # Ensure line break if only one item in the last row
                pdf.ln(5)

                analysis_basis_text = (
                    f"Analysis Configuration: Peer Group by '{current_peer_group}'. "
                    f"Baseline Threshold: {current_baseline_threshold}%. Anomaly Threshold: {current_anomaly_threshold}%."
                )
                pdf.set_font(base_font, "I", 9) # Italic for config summary
                pdf.multi_cell(0, 5, analysis_basis_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.ln(5)
                
                # Convert baseline_data_dict to DataFrame for PDF reporting
                baseline_df_for_report = pd.DataFrame()
                if baseline_data_for_pdf_dict:
                    baseline_table_rows = []
                    if current_peer_group == "Department-wide":
                        cols = ["Department", "Baseline Role"]
                        for group_key, entitlements_set in baseline_data_for_pdf_dict.items():
                            dept = group_key[0] if isinstance(group_key, tuple) else group_key # Handle single string or tuple
                            for role, _ in sorted(list(entitlements_set)): # Percentage not needed for this report table
                                baseline_table_rows.append({"Department": dept, "Baseline Role": role})
                        if baseline_table_rows: baseline_df_for_report = pd.DataFrame(baseline_table_rows, columns=cols)
                    elif current_peer_group == "Department + Title":
                        cols = ["Department", "Title", "Baseline Role"]
                        for group_key, entitlements_set in baseline_data_for_pdf_dict.items():
                            dept, title = group_key
                            for role, _ in sorted(list(entitlements_set)):
                                baseline_table_rows.append({"Department": dept, "Title": title, "Baseline Role": role})
                        if baseline_table_rows: baseline_df_for_report = pd.DataFrame(baseline_table_rows, columns=cols)
                
                if report_type == "full" or report_type == "baseline":
                    if not baseline_df_for_report.empty: pdf.add_page() 
                    add_table_to_pdf(baseline_df_for_report, "Baseline Access Report")
                
                if report_type == "full" or report_type == "anomalies":
                    if not anomalies_df_for_pdf.empty: pdf.add_page()
                    add_table_to_pdf(anomalies_df_for_pdf, "Anomalous Access Report")
                
                if report_type == "full" or report_type == "gap":
                    if not gap_df_for_pdf.empty: pdf.add_page()
                    add_table_to_pdf(gap_df_for_pdf, "Gap Report (Users Missing Baseline Access)")
                
                return pdf.output()  # Get PDF as bytes (dest='S' or no dest returns bytes)

            # Wrapper for specific PDF types
            def generate_specific_pdf(report_subtype, main_df_metrics, b_data_dict, an_df, g_df, pg_val, bt_val, at_val, uwt_val):
                # Common args for generate_pdf_report
                common_args = {
                    "main_df_for_metrics": main_df_metrics,
                    "current_peer_group": pg_val,
                    "current_baseline_threshold": bt_val,
                    "current_anomaly_threshold": at_val,
                    "num_users_wo_title": uwt_val
                }
                if report_subtype == "baseline":
                    return generate_pdf_report(baseline_data_for_pdf_dict=b_data_dict, report_type="baseline", **common_args)
                elif report_subtype == "anomalies":
                    return generate_pdf_report(anomalies_df_for_pdf=an_df, report_type="anomalies", **common_args)
                elif report_subtype == "gap":
                    return generate_pdf_report(gap_df_for_pdf=g_df, report_type="gap", **common_args)
                elif report_subtype == "full":
                    return generate_pdf_report(baseline_data_for_pdf_dict=b_data_dict, anomalies_df_for_pdf=an_df, gap_df_for_pdf=g_df, report_type="full", **common_args)
                return None

            # --- Display & Download Sections ---
            tab1, tab2, tab3 = st.tabs(["Baseline Access", "Anomalous Access", "Gap Report"])

            with tab1:
                st.subheader("1. Baseline Access")
                st.caption(f"Common roles/entitlements held by at least {baseline_threshold}% of users in their '{peer_group}' peer group.")
                baseline_display_list = []
                if peer_group == "Department-wide":
                    cols_display = ["Department", "Baseline Role", "Prevalence (%)"]
                    for group_key, entitlements_set in baseline_data_dict.items():
                        dept = group_key[0] if isinstance(group_key, tuple) else group_key
                        for role, percentage in sorted(list(entitlements_set)):
                            try:
                                prevalence_display = f"{float(percentage):.1f}"
                            except ValueError:
                                prevalence_display = "N/A"
                            baseline_display_list.append({"Department": dept, "Baseline Role": role, "Prevalence (%)": prevalence_display})
                    baseline_df_display = pd.DataFrame(baseline_display_list, columns=cols_display) if baseline_display_list else pd.DataFrame(columns=cols_display)
                elif peer_group == "Department + Title":
                    cols_display = ["Department", "Title", "Baseline Role", "Prevalence (%)"]
                    for group_key, entitlements_set in baseline_data_dict.items():
                        dept, title = group_key
                        for role, percentage in sorted(list(entitlements_set)):
                            try:
                                prevalence_display = f"{float(percentage):.1f}"
                            except ValueError:
                                prevalence_display = "N/A"
                            baseline_display_list.append({"Department": dept, "Title": title, "Baseline Role": role, "Prevalence (%)": prevalence_display})
                    baseline_df_display = pd.DataFrame(baseline_display_list, columns=cols_display) if baseline_display_list else pd.DataFrame(columns=cols_display)
                
                st.dataframe(baseline_df_display)
                if not baseline_df_display.empty:
                    csv_baseline = baseline_df_display.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Baseline as CSV", csv_baseline, "baseline_access.csv", "text/csv", key="csv_baseline")
                    pdf_bytes_baseline = bytes(generate_specific_pdf("baseline", df, baseline_data_dict, None, None, peer_group, baseline_threshold, anomaly_threshold, users_wo_title))
                    if pdf_bytes_baseline:
                        st.download_button("Download Baseline as PDF", pdf_bytes_baseline, "baseline_report.pdf", "application/pdf", key="pdf_baseline")
                else: st.write("No baseline data to display based on current criteria.")

            with tab2:
                st.subheader("2. Anomalous Access")
                st.caption(f"Users with roles/entitlements held by fewer than {anomaly_threshold}% of their '{peer_group}' peers.")
                st.dataframe(anomalies_data_df) # anomalies_data_df is already a DataFrame
                if not anomalies_data_df.empty:
                    csv_anomalies = anomalies_data_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Anomalies as CSV", csv_anomalies, "anomalous_access.csv", "text/csv", key="csv_anomalies")
                    pdf_bytes_anomalies = bytes(generate_specific_pdf("anomalies", df, None, anomalies_data_df, None, peer_group, baseline_threshold, anomaly_threshold, users_wo_title))
                    if pdf_bytes_anomalies:
                        st.download_button("Download Anomalies as PDF", pdf_bytes_anomalies, "anomalies_report.pdf", "application/pdf", key="pdf_anomalies")
                else: st.write("No anomalies found based on current criteria.")

            with tab3:
                st.subheader("3. Gap Report (Missing Baseline Access)")
                st.caption(f"Users missing common roles/entitlements (from baseline) for their '{peer_group}' peer group.")
                st.dataframe(gap_data_df) # gap_data_df is already a DataFrame
                if not gap_data_df.empty:
                    csv_gap = gap_data_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Gap Report as CSV", csv_gap, "gap_report.csv", "text/csv", key="csv_gap")
                    pdf_bytes_gap = bytes(generate_specific_pdf("gap", df, None, None, gap_data_df, peer_group, baseline_threshold, anomaly_threshold, users_wo_title))
                    if pdf_bytes_gap:
                        st.download_button("Download Gap Report as PDF", pdf_bytes_gap, "gap_report.pdf", "application/pdf", key="pdf_gap")
                else: st.write("No gaps found (all users appear to have baseline access for their group).")

            st.markdown("---")
            st.header("Full Consolidated PDF Report")
            if not df.empty: # Ensure df is not empty before generating full report
                pdf_bytes_full = bytes(generate_specific_pdf("full", df, baseline_data_dict, anomalies_data_df, gap_data_df, peer_group, baseline_threshold, anomaly_threshold, users_wo_title))
                if pdf_bytes_full:
                    st.download_button(
                        label="Download Full Report as PDF",
                        data=pdf_bytes_full,
                        file_name="full_entitlement_review_report.pdf",
                        mime="application/pdf",
                        key="pdf_full_report"
                    )
            else:
                st.write("No data available to generate a full report (upload a CSV first).")

        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {e}")
            print(f"ERROR_MAIN_TRY_EXCEPT: Type: {type(e)}, Error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            st.code(f"Traceback:\n{traceback.format_exc()}") # Display traceback in UI for easier debugging by user

if __name__ == "__main__":
    main()
