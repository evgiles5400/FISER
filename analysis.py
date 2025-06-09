# analysis.py
"""Core analysis logic for Anomalous Access Detector."""
import pandas as pd
from collections import Counter

def get_peer_groups(df, peer_group_type):
    """Group dataframe by department or department+title depending on peer_group_type."""
    if peer_group_type == "Department-wide":
        return df.groupby(["Department"])
    else:
        return df.groupby(["Department", "Title"])

def get_entitlement_counts(group_df):
    """Calculate entitlement counts for a group.
    
    Args:
        group_df: DataFrame for a specific peer group
        
    Returns:
        Tuple of (user count, entitlement counts Series)
    """
    users = group_df["UserID"].nunique()
    ent_counts = group_df.groupby(["Role", "Entitlement"])["UserID"].nunique()
    return users, ent_counts

def filter_entitlements(ent_counts, users, threshold, is_baseline=True):
    """Filter entitlements based on threshold.
    
    Args:
        ent_counts: Series of entitlement counts
        users: Total number of users
        threshold: Percentage threshold
        is_baseline: If True, return entitlements >= threshold,
                     If False, return entitlements <= threshold
        
    Returns:
        List of (Role, Entitlement) tuples
    """
    threshold_ratio = threshold / 100.0 * users
    if is_baseline:
        filtered = ent_counts[ent_counts >= threshold_ratio].index.tolist()
    else:
        filtered = ent_counts[ent_counts <= threshold_ratio].index.tolist()
    return filtered

def baseline_access(df, baseline_threshold, peer_group_type):
    """
    For each group, list Roles/Entitlements present in >= baseline_threshold percent of users.
    Returns: dict of group -> set of (Role, Entitlement)
    """
    group_obj = get_peer_groups(df, peer_group_type)
    baseline = {}
    
    for group, group_df in group_obj:
        users, ent_counts = get_entitlement_counts(group_df)
        common = filter_entitlements(ent_counts, users, baseline_threshold, is_baseline=True)
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
        users, ent_counts = get_entitlement_counts(group_df)
        rare = filter_entitlements(ent_counts, users, anomaly_threshold, is_baseline=False)
        
        # Process each user in the group
        for user, user_df in group_df.groupby("UserID"):
            username = user_df["Username"].iloc[0] if not user_df.empty else None
            user_ents = set(zip(user_df["Role"], user_df["Entitlement"]))
            
            # Find anomalous entitlements for this user
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
        
        # Find missing entitlements that should be in the baseline
        if group in baseline:
            missing = baseline[group] - user_ents
            for ent in missing:
                records.append({
                    "Group": group,
                    "Role": ent[0],
                    "Entitlement": ent[1]
                })
    
    return pd.DataFrame(records)
