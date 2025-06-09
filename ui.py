# ui.py
"""Streamlit UI entrypoint for Anomalous Access Detector."""

import streamlit as st
import pandas as pd
import plotly.express as px
from ingest import validate_and_preview_csv, REQUIRED_COLUMNS
from analysis import baseline_access, anomalies, gap_report
import io
from fpdf import FPDF
import tempfile
import datetime
import os

st.set_page_config(page_title="FIS Entitlements Review")
st.title("FIS Entitlements Review")
st.write("Upload a CSV of user entitlements to begin.")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        if list(df.columns) != REQUIRED_COLUMNS:
            st.error(f"CSV must have columns: {REQUIRED_COLUMNS}")
        else:
            st.success("CSV schema valid!")
            st.write("Preview (first 5 rows):")
            st.dataframe(df.head(5))

            st.markdown("---")
            st.header("Configuration Panel")
            col1, col2 = st.columns(2)
            with col1:
                anomaly_threshold = st.number_input(
                    "Anomaly threshold (%):",
                    min_value=0.1, max_value=100.0, value=2.0, step=0.1,
                    help="Flag any privilege held by fewer than this percent of peers as anomalous."
                )
            with col2:
                baseline_threshold = st.number_input(
                    "Baseline threshold (%):",
                    min_value=0.1, max_value=100.0, value=95.0, step=0.1,
                    help="Define 'common' privileges a group should always have."
                )
            peer_group = st.radio(
                "Choose peer group:",
                ["Department-wide", "Department + Title"]
            )
            st.info(f"Selected: Anomaly {anomaly_threshold}%, Baseline {baseline_threshold}%, Peer group: {peer_group}")

            # Metrics section
            st.markdown("---")
            st.header("Dataset Metrics")
            users_wo_title = df[df['Title'].isnull() | (df['Title'].astype(str).str.strip() == '')]['UserID'].nunique()
            col1, col2, col3 = st.columns(3)
            col1.metric("Records", len(df))
            col1.metric("Unique Users", df['UserID'].nunique())
            col1.metric("Departments", df['Department'].nunique())
            col2.metric("Titles", df['Title'].nunique())
            col2.metric("Roles", df['Role'].nunique())
            col2.metric("Access Groups", df['Acc Priv Group'].nunique())
            col3.metric("Access Categories", df['Acc Priv Category'].nunique())
            col3.metric("Entitlements", df['Entitlement'].nunique())
            col3.metric("Users w/o Title", users_wo_title)

            # Filter out users with no Title for baseline analysis
            df_baseline = df[df['Title'].notnull() & (df['Title'].astype(str).str.strip() != '')]

            # Run analyses and show results
            st.markdown("---")
            st.header("Core Analyses & Reports")
            baseline = baseline_access(df_baseline, baseline_threshold, peer_group)
            anomalies_df = anomalies(df, anomaly_threshold, peer_group)
            gap_df = gap_report(df, baseline, peer_group)

            st.subheader("1. Baseline Access")
            st.caption(f"""\
Baseline Access: For each peer group, lists Roles present in at least the baseline threshold ({baseline_threshold}%) of users (excluding users with no Title). These are considered the 'common' roles that most users in the group have.
""")
            baseline_table = []
            if peer_group == "Department-wide":
                for group, ents in baseline.items():
                    department = group[0]
                    roles = set(role for role, _ in ents)
                    for role in roles:
                        baseline_table.append({
                            "Department": department,
                            "Role": role
                        })
                baseline_df = pd.DataFrame(baseline_table)
                st.dataframe(baseline_df)
                # Export buttons
                if not baseline_df.empty:
                    csv = baseline_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Baseline as CSV", csv, "baseline_access.csv", "text/csv")
                    # PDF export
                    def generate_pdf_report(df, baseline_df=None, anomalies_df=None, gap_df=None, peer_group="Department-wide", 
                                            baseline_threshold=95.0, anomaly_threshold=2.0, users_wo_title=0, report_type="full"):
                        """
                        Generate a comprehensive PDF report for FIS Entitlements Review.
                        
                        This function creates a PDF report containing analysis results including baseline access,
                        anomalies, and gap reports based on the provided dataframes and configuration settings.
                        
                        Args:
                            df (pandas.DataFrame): Main dataframe with all entitlement data
                            baseline_df (pandas.DataFrame, optional): Dataframe with baseline access information
                            anomalies_df (pandas.DataFrame, optional): Dataframe with anomaly information
                            gap_df (pandas.DataFrame, optional): Dataframe with gap information
                            peer_group (str, optional): Peer grouping strategy ("Department-wide" or "Department + Title")
                            baseline_threshold (float, optional): Percentage threshold for baseline calculation (0-100)
                            anomaly_threshold (float, optional): Percentage threshold for anomaly detection (0-100)
                            users_wo_title (int, optional): Number of users without a title
                            report_type (str, optional): Type of report to generate ("full" or "baseline")
                            
                        Returns:
                            bytes: PDF document as bytes for download
                            
                        Note:
                            The function attempts to use Aptos font if available, otherwise falls back to Arial.
                            For the full report, all three analysis sections are included: baseline, anomalies, and gaps.
                            For baseline-only reports, only the first section is included.
                        """
                        pdf = FPDF()
                        # Try to use Aptos font if available
                        font_path = os.path.join("fonts", "Aptos-Regular.ttf")
                        if os.path.exists(font_path):
                            try:
                                pdf.add_font("Aptos", "", font_path, uni=True)
                                base_font = "Aptos"
                            except Exception as e:
                                base_font = "Arial"
                        else:
                            base_font = "Arial"
                        pdf.add_page()
                        # Title Page
                        pdf.set_font(base_font, "B", 20)
                        pdf.cell(0, 15, "FIS Entitlement Review", ln=1, align="C")
                        pdf.set_font(base_font, size=12)
                        pdf.cell(0, 10, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align="C")
                        pdf.ln(10)

                        # Dataset Metrics
                        pdf.set_font(base_font, "B", 14)
                        pdf.cell(0, 12, "Dataset Metrics", ln=1)
                        pdf.set_font(base_font, size=11)
                        metrics = [
                            ("Records", len(df)),
                            ("Unique Users", df['UserID'].nunique()),
                            ("Departments", df['Department'].nunique()),
                            ("Titles", df['Title'].nunique()),
                            ("Roles", df['Role'].nunique()),
                            ("Access Groups", df['Acc Priv Group'].nunique()),
                            ("Access Categories", df['Acc Priv Category'].nunique()),
                            ("Entitlements", df['Entitlement'].nunique()),
                            ("Users w/o Title", users_wo_title)
                        ]
                        metrics_col_count = 2
                        metrics_col_width = (pdf.w - 20) / metrics_col_count  # 10 units margin each side
                        pdf.set_x(10)
                        for i in range(0, len(metrics), 2):
                            pdf.set_x(10)
                            # Left column
                            pdf.set_font(base_font, "B", 11)
                            pdf.cell(metrics_col_width * 0.6, 8, str(metrics[i][0]) + ':', border=0, align='R')
                            pdf.set_font(base_font, size=11)
                            pdf.cell(metrics_col_width * 0.4, 8, str(metrics[i][1]), border=0, align='L')
                            # Right column
                            if i + 1 < len(metrics):
                                pdf.set_font(base_font, "B", 11)
                                pdf.cell(metrics_col_width * 0.6, 8, str(metrics[i+1][0]) + ':', border=0, align='R')
                                pdf.set_font(base_font, size=11)
                                pdf.cell(metrics_col_width * 0.4, 8, str(metrics[i+1][1]), border=0, align='L')
                            pdf.ln(8)
                        pdf.ln(5)
                        # Analysis basis
                        analysis_basis = (
                            "Analysis based on user Department and Title"
                            if peer_group == "Department + Title" else
                            "Analysis based on user Department only"
                        )
                        pdf.set_font(base_font, "I", 11)
                        pdf.cell(0, 8, analysis_basis, ln=1)
                        pdf.ln(3)

                        # --- Baseline Access Section ---
                        pdf.set_font(base_font, "B", 13)
                        pdf.cell(0, 10, "Baseline Access", ln=1)
                        pdf.set_font(base_font, size=11)
                        pdf.multi_cell(0, 8, f"Baseline Access: For each peer group, lists Roles present in at least the baseline threshold ({baseline_threshold}%) of users (excluding users with no Title). These are considered the 'common' roles that most users in the group have.")
                        pdf.ln(2)
                        # Block format: each group/department gets its own block, roles in grid
                        roles_data = []
                        if peer_group == "Department-wide":
                            for dept in sorted(baseline_df['Department'].unique()):
                                roles = sorted(baseline_df[baseline_df['Department'] == dept]['Role'].unique())
                                roles_data.append((dept, roles))
                        else:
                            for dept in sorted(baseline_df['Department'].unique()):
                                titles = sorted(baseline_df[baseline_df['Department'] == dept]['Title'].unique())
                                for title in titles:
                                    roles = sorted(baseline_df[(baseline_df['Department'] == dept) & (baseline_df['Title'] == title)]['Role'].unique())
                                    roles_data.append((f"{dept} / {title}", roles))
                        # Print each group block
                        roles_col_count = 2
                        roles_col_width = (pdf.w - 20) / roles_col_count  # 10 units margin each side
                        for group, roles in roles_data:
                            pdf.set_font(base_font, "B", 11)
                            pdf.set_x(10)
                            pdf.cell(0, 8, group, ln=1)
                            pdf.set_font(base_font, size=11)
                            for i in range(0, len(roles), roles_col_count):
                                pdf.set_x(10)
                                for j in range(roles_col_count):
                                    if i + j < len(roles):
                                        pdf.cell(roles_col_width, 8, roles[i+j], border=0)
                                pdf.ln(8)
                            pdf.ln(2)
                        pdf.add_page()

                        # --- Anomalies Section ---
                        if report_type == "full":
                            pdf.set_font(base_font, "B", 13)
                            pdf.cell(0, 10, "Anomalies", ln=1)
                            pdf.set_font(base_font, size=11)
                            pdf.multi_cell(0, 8, f"Anomalies: Flags any Roles or Entitlements held by fewer than the anomaly threshold ({anomaly_threshold}%) of users in their peer group. These are outlier privileges that may require investigation.")
                            pdf.ln(2)
                            # --- Robust anomalies section: skip or show message if no anomalies ---
                            if not anomalies_df.empty and 'Department' in anomalies_df.columns:
                                # Before using anomalies_df for PDF, extract Department and Title columns if needed
                                anomalies_df = anomalies_df.copy()
                                if 'Group' in anomalies_df.columns:
                                    anomalies_df['Department'] = anomalies_df['Group'].apply(lambda x: x[0] if isinstance(x, (tuple, list)) and len(x) > 0 else "")
                                    if peer_group == "Department + Title":
                                        anomalies_df['Title'] = anomalies_df['Group'].apply(lambda x: x[1] if isinstance(x, (tuple, list)) and len(x) > 1 else "")

                                anomalies_data = []
                                if peer_group == "Department-wide":
                                    for dept in sorted(anomalies_df['Department'].unique()):
                                        users = sorted(anomalies_df[anomalies_df['Department'] == dept]['Username'].unique())
                                        for user in users:
                                            roles = sorted(anomalies_df[(anomalies_df['Department'] == dept) & (anomalies_df['Username'] == user)]['Role'].unique())
                                            anomalies_data.append((f"{dept} / {user}", roles))
                                else:  # Department + Title
                                    for dept in sorted(anomalies_df['Department'].unique()):
                                        titles = sorted(anomalies_df[anomalies_df['Department'] == dept]['Title'].unique())
                                        for title in titles:
                                            users = sorted(anomalies_df[(anomalies_df['Department'] == dept) & (anomalies_df['Title'] == title)]['Username'].unique())
                                            for user in users:
                                                roles = sorted(anomalies_df[(anomalies_df['Department'] == dept) & (anomalies_df['Title'] == title) & (anomalies_df['Username'] == user)]['Role'].unique())
                                                anomalies_data.append((f"{dept} / {title} / {user}", roles))
                                # Print each group block
                                anomalies_col_count = 2
                                anomalies_col_width = (pdf.w - 20) / anomalies_col_count  # 10 units margin each side
                                for group, roles in anomalies_data:
                                    pdf.set_font(base_font, "B", 11)
                                    pdf.set_x(10)
                                    pdf.cell(0, 8, group, ln=1)
                                    pdf.set_font(base_font, size=11)
                                    for i in range(0, len(roles), anomalies_col_count):
                                        pdf.set_x(10)
                                        for j in range(anomalies_col_count):
                                            if i + j < len(roles):
                                                pdf.cell(anomalies_col_width, 8, roles[i+j], border=0)
                                        pdf.ln(8)
                                    pdf.ln(2)
                            else:
                                pdf.set_font(base_font, "I", 11)
                                pdf.cell(0, 8, "No anomalies found for the selected criteria.", ln=1)
                                pdf.ln(2)
                            pdf.add_page()

                            # --- Gap Report Section ---
                            pdf.set_font(base_font, "B", 13)
                            pdf.cell(0, 10, "Gap Report", ln=1)
                            pdf.set_font(base_font, size=11)
                            pdf.multi_cell(0, 8, "Gap Report: For each peer group, lists any baseline Entitlements that are present in the department baseline but missing from this subgroup. These represent potential gaps in access.")
                            pdf.ln(2)
                            if not gap_df.empty and 'Department' in gap_df.columns:
                                gap_data = []
                                for idx, row in gap_df.iterrows():
                                    group = row['Group']
                                    role = row['Role']
                                    if peer_group == "Department-wide":
                                        gap_data.append((str(group), [role]))
                                    else:
                                        dept, title = group if isinstance(group, tuple) else (group, '')
                                        gap_data.append((f"{dept} / {title}", [role]))
                                # Print each group block
                                gap_col_count = 2
                                gap_col_width = (pdf.w - 20) / gap_col_count  # 10 units margin each side
                                for group, roles in gap_data:
                                    pdf.set_font(base_font, "B", 11)
                                    pdf.set_x(10)
                                    pdf.cell(0, 8, group, ln=1)
                                    pdf.set_font(base_font, size=11)
                                    for i in range(0, len(roles), gap_col_count):
                                        pdf.set_x(10)
                                        for j in range(gap_col_count):
                                            if i + j < len(roles):
                                                pdf.cell(gap_col_width, 8, roles[i+j], border=0)
                                        pdf.ln(8)
                                    pdf.ln(2)
                            else:
                                pdf.set_font(base_font, "I", 11)
                                pdf.cell(0, 8, "No gaps found for the selected criteria.", ln=1)
                                pdf.ln(2)
                        return pdf.output(dest='S').encode('latin1')

                    def generate_baseline_pdf(df, baseline_df, peer_group, baseline_threshold):
                        """
                        Generate a PDF report focused only on baseline access analysis.
                        
                        This is a wrapper function that calls generate_pdf_report with report_type='baseline'.
                        
                        Args:
                            df (pandas.DataFrame): Main dataframe with all entitlement data
                            baseline_df (pandas.DataFrame): Dataframe with baseline access information
                            peer_group (str): Peer grouping strategy ("Department-wide" or "Department + Title")
                            baseline_threshold (float): Percentage threshold for baseline calculation (0-100)
                            
                        Returns:
                            bytes: PDF document as bytes for download
                        """
                        users_wo_title = df[df['Title'].isnull() | (df['Title'].astype(str).str.strip() == '')]['UserID'].nunique()
                        return generate_pdf_report(df, baseline_df=baseline_df, peer_group=peer_group, 
                                                  baseline_threshold=baseline_threshold, users_wo_title=users_wo_title, 
                                                  report_type="baseline")

                    def generate_full_report_pdf(df, baseline_df, anomalies_df, gap_df, peer_group, baseline_threshold, anomaly_threshold, users_wo_title):
                        """
                        Generate a comprehensive PDF report with all analysis sections.
                        
                        This is a wrapper function that calls generate_pdf_report with report_type='full'.
                        
                        Args:
                            df (pandas.DataFrame): Main dataframe with all entitlement data
                            baseline_df (pandas.DataFrame): Dataframe with baseline access information
                            anomalies_df (pandas.DataFrame): Dataframe with anomaly information
                            gap_df (pandas.DataFrame): Dataframe with gap information
                            peer_group (str): Peer grouping strategy ("Department-wide" or "Department + Title")
                            baseline_threshold (float): Percentage threshold for baseline calculation (0-100)
                            anomaly_threshold (float): Percentage threshold for anomaly detection (0-100)
                            users_wo_title (int): Number of users without a title
                            
                        Returns:
                            bytes: PDF document as bytes for download
                        """
                        return generate_pdf_report(df, baseline_df=baseline_df, anomalies_df=anomalies_df, gap_df=gap_df,
                                                  peer_group=peer_group, baseline_threshold=baseline_threshold, 
                                                  anomaly_threshold=anomaly_threshold, users_wo_title=users_wo_title,
                                                  report_type="full")

                    # PDF export
                    pdf_filename = f"Baseline Access Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.pdf"
                    st.download_button("Download Baseline as PDF", generate_baseline_pdf(df, baseline_df, peer_group, baseline_threshold), pdf_filename, "application/pdf")

            else:
                for group, ents in baseline.items():
                    department = group[0]
                    title = group[1] if len(group) > 1 else None
                    if title is None or str(title).strip() == '':
                        continue
                    roles = set(role for role, _ in ents)
                    for role in roles:
                        baseline_table.append({
                            "Department": department,
                            "Title": title,
                            "Role": role
                        })
                baseline_df = pd.DataFrame(baseline_table)
                st.dataframe(baseline_df)
                # Export buttons
                if not baseline_df.empty:
                    csv = baseline_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Baseline as CSV", csv, "baseline_access.csv", "text/csv")
                # Bar chart: Number of common roles per Department+Title
                if not baseline_df.empty:
                    fig = px.bar(baseline_df.groupby(["Department", "Title"]).size().reset_index(name="Common Roles"),
                                 x="Title", y="Common Roles", color="Department",
                                 title="Number of Common Roles per Title (by Department)")
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader("2. Anomalies")
            st.caption(f"""\
Anomalies: Flags any Roles or Entitlements held by fewer than the anomaly threshold ({anomaly_threshold}%) of users in their peer group. These are outlier privileges that may require investigation.
""")

            # --- Web Anomalies Table Correction (robust Department/Title extraction for both peer groups, handle missing columns) ---
            if not anomalies_df.empty:
                import warnings
                warnings.filterwarnings("ignore", category=UserWarning)
                if 'Group' in anomalies_df.columns:
                    # Handle both peer groups
                    anomalies_df = anomalies_df.copy()
                    anomalies_df['Department'] = anomalies_df['Group'].apply(lambda x: x[0] if isinstance(x, (tuple, list)) and len(x) > 0 else "")
                    if peer_group == "Department + Title":
                        anomalies_df['Title'] = anomalies_df['Group'].apply(lambda x: x[1] if isinstance(x, (tuple, list)) and len(x) > 1 else "")

                # Only use columns that exist in the DataFrame
                wanted_cols = ['Department', 'Title', 'UserID', 'Username', 'Role']
                display_cols = [col for col in wanted_cols if col in anomalies_df.columns]
                anomalies_df = anomalies_df[display_cols].drop_duplicates()
                csv = anomalies_df.to_csv(index=False).encode('utf-8')
                st.dataframe(anomalies_df)
                st.download_button("Download Anomalies as CSV", csv, "anomalies.csv", "text/csv")

            # Bar chart: Number of anomalies per Department/Title
            if not anomalies_df.empty:
                if peer_group == "Department-wide":
                    anomalies_count = anomalies_df.groupby("Department").size().reset_index(name="Anomalies")
                    fig = px.bar(anomalies_count, x="Department", y="Anomalies", title="Number of Anomalies per Department")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    anomalies_count = anomalies_df.groupby("Department").size().reset_index(name="Anomalies")
                    fig = px.bar(anomalies_count, x="Department", y="Anomalies", title="Number of Anomalies per Department")
                    st.plotly_chart(fig, use_container_width=True)
                    # Heatmap: Anomalies per (Department, Title)
                    heatmap_data = anomalies_df.groupby(["Department", "Title"]).size().reset_index(name="Anomalies")
                    fig2 = px.imshow(heatmap_data.pivot(index="Department", columns="Title", values="Anomalies").fillna(0),
                                    labels=dict(x="Title", y="Department", color="Anomalies"),
                                    title="Anomalies Heatmap (Department x Title)")
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("3. Gap Report")
            st.caption(f"""\
Gap Report: For each peer group, lists any baseline Entitlements that are present in the department baseline but missing from this subgroup. These represent potential gaps in access.
""")
            st.dataframe(gap_df)
            # Export buttons
            if not gap_df.empty:
                csv = gap_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Gaps as CSV", csv, "gap_report.csv", "text/csv")
            # Heatmap: Gaps per (Department, Title)
            if not gap_df.empty and peer_group != "Department-wide":
                gap_count = gap_df.groupby(["Group"]).size().reset_index(name="Gaps")
                gap_count[["Department", "Title"]] = pd.DataFrame(gap_count["Group"].tolist(), index=gap_count.index)
                heatmap_gap = gap_count.pivot(index="Department", columns="Title", values="Gaps").fillna(0)
                fig_gap = px.imshow(heatmap_gap, labels=dict(x="Title", y="Department", color="Gaps"),
                                   title="Gap Heatmap (Department x Title)")
                st.plotly_chart(fig_gap, use_container_width=True)

            # --- Full PDF Export ---
            now = datetime.datetime.now()
            date_str = now.strftime("%y%m%d")
            pdf_filename = f"FIS Entitlements Review - {date_str}.pdf"

            st.markdown("---")
            st.download_button(
                "Download Full Report as PDF",
                generate_full_report_pdf(df, baseline_df, anomalies_df, gap_df, peer_group, baseline_threshold, anomaly_threshold, users_wo_title),
                pdf_filename,
                "application/pdf"
            )
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.info("Please check that your CSV file follows the required format and try again.")
