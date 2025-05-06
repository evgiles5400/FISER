# analysis.py
"""Core analysis logic for Anomalous Access Detector."""
import pandas as pd
from collections import Counter

def get_peer_groups(df, peer_group_type):
    if peer_group_type == "Department-wide":
        return df.groupby(["Department"])
    else:
        return df.groupby(["Department", "Title"])

def baseline_access(df, baseline_threshold, peer_group_type):
    """
    For each group, list Roles/Entitlements present in >= baseline_threshold percent of users.
    Returns: dict of group -> set of (Role, Entitlement)
    """
    group_obj = get_peer_groups(df, peer_group_type)
    baseline = {}
    for group, group_df in group_obj:
        users = group_df["UserID"].nunique()
        ent_counts = group_df.groupby(["Role", "Entitlement"])["UserID"].nunique()
        common = ent_counts[ent_counts >= (baseline_threshold/100)*users].index.tolist()
        baseline[group] = set(common)
    return baseline

def anomalies(df, anomaly_threshold, peer_group_type):
    """
    For each user, flag Roles/Entitlements below anomaly_threshold percent of peers.
    Returns: DataFrame with anomalous items.
    """
    group_obj = get_peer_groups(df, peer_group_type)
    records = []
    for group, group_df in group_obj:
        users = group_df["UserID"].nunique()
        ent_counts = group_df.groupby(["Role", "Entitlement"])["UserID"].nunique()
        rare = ent_counts[ent_counts <= (anomaly_threshold/100)*users].index.tolist()
        for user, user_df in group_df.groupby("UserID"):
            username = user_df["Username"].iloc[0] if not user_df.empty else None
            user_ents = set(zip(user_df["Role"], user_df["Entitlement"]))
            for ent in user_ents:
                if ent in rare:
                    records.append({
                        "Group": group,
                        "UserID": user,
                        "Username": username,
                        "Role": ent[0],
                        "Entitlement": ent[1]
                    })
    return pd.DataFrame(records)

def gap_report(df, baseline, peer_group_type):
    """
    For each group, list baseline Entitlements missing from subgroups.
    Returns: DataFrame with missing entitlements per group.
    """
    group_obj = get_peer_groups(df, peer_group_type)
    records = []
    for group, group_df in group_obj:
        user_ents = set(zip(group_df["Role"], group_df["Entitlement"]))
        missing = baseline[group] - user_ents
        for ent in missing:
            records.append({
                "Group": group,
                "Role": ent[0],
                "Entitlement": ent[1]
            })
    return pd.DataFrame(records)
