#!/usr/bin/env python3
"""Deep-dive analysis for the data quality report."""

import pandas as pd
import numpy as np
from pathlib import Path
import re

DATA_DIR = Path("xls")

def read_csv_safe(path):
    for encoding in ['utf-8-sig', 'utf-8', 'cp1256', 'latin1']:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception:
            pass
    return None

# Load all dataframes
dfs = {}
for fname in ['Dryer.csv', 'Setting_wagons.csv', 'Setting_Setting.csv', 
              'Packing.csv', 'Kiln.csv', 'Categories.csv', 'Molds.csv', 
              'Glaze.csv', 'ProductName.csv', 'Operators.csv', 'Supervisors.csv']:
    fpath = DATA_DIR / fname
    if fpath.exists():
        dfs[fname] = read_csv_safe(fpath)

print("=" * 80)
print("DEEP-DIVE ANALYSIS")
print("=" * 80)

# ---- DATE RANGE COVERAGE ----
print("\n[1] DATE RANGE COVERAGE")
for fname in ['Dryer.csv', 'Setting_Setting.csv', 'Packing.csv', 'Kiln.csv']:
    if fname in dfs:
        df = dfs[fname]
        for col in df.columns:
            if 'date' in col.lower() or 'jalali' in col.lower():
                dates = df[col].dropna().astype(str).tolist()
                # Normalize for sorting
                normalized = []
                for d in dates:
                    d = d.strip()
                    m = re.match(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', d)
                    if m:
                        y, mo, da = m.groups()
                        normalized.append(f"{y}/{int(mo):02d}/{int(da):02d}")
                if normalized:
                    print(f"  {fname}.{col}: {min(normalized)} to {max(normalized)} ({len(set(normalized))} unique days)")

# ---- SHIFT DISTRIBUTION ----
print("\n[2] SHIFT DISTRIBUTION")
for fname in ['Setting_Setting.csv', 'Packing.csv']:
    if fname in dfs and 'shift' in dfs[fname].columns:
        shifts = dfs[fname]['shift'].value_counts().sort_index()
        print(f"  {fname}:")
        for shift, count in shifts.items():
            pct = count / len(dfs[fname]) * 100
            print(f"    Shift {shift}: {count} records ({pct:.1f}%)")

# ---- CHAMBER USAGE ----
print("\n[3] CHAMBER USAGE (Dryer.csv)")
if 'Dryer.csv' in dfs:
    df = dfs['Dryer.csv']
    chambers = df['ChamberNo'].value_counts().sort_index()
    print(f"  Chambers used: {sorted(chambers.index.tolist())}")
    print(f"  Min loads per chamber: {chambers.min()}, Max: {chambers.max()}, Avg: {chambers.mean():.1f}")
    print(f"  Most used: Chamber {chambers.idxmax()} with {chambers.max()} loads")
    print(f"  Least used: Chamber {chambers.idxmin()} with {chambers.min()} loads")

# ---- DRYING DURATION ----
print("\n[4] DRYING DURATION ANALYSIS (Dryer.csv)")
if 'Dryer.csv' in dfs:
    df = dfs['Dryer.csv']
    # Filter rows with both load and unload dates
    complete = df[df['UnloadDateJalali'].notna()].copy()
    print(f"  Complete cycles (load + unload): {len(complete)} / {len(df)}")
    
    # Parse dates and calculate duration
    durations = []
    for _, row in complete.iterrows():
        try:
            ld = str(row['LoadDateJalali']).strip()
            ud = str(row['UnloadDateJalali']).strip()
            # Extract year, month, day
            lm = re.match(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', ld)
            um = re.match(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', ud)
            if lm and um:
                ly, lmo, lda = map(int, lm.groups())
                uy, umo, uda = map(int, um.groups())
                # Simple day difference (same month assumption mostly)
                if ly == uy and lmo == umo:
                    duration = uda - lda
                    durations.append(duration)
                elif ly == uy:
                    # Different month - rough estimate
                    import calendar
                    days_in_month = calendar.monthrange(2025, lmo)[1]  # placeholder
                    duration = (days_in_month - lda) + uda
                    durations.append(duration)
        except Exception:
            pass
    
    if durations:
        print(f"  Duration stats (days): min={min(durations)}, max={max(durations)}, avg={np.mean(durations):.1f}")
        # Count by duration
        from collections import Counter
        dur_counts = Counter(durations)
        print(f"  Most common durations: {dur_counts.most_common(5)}")

# ---- KILN TEMPERATURE STATS ----
print("\n[5] KILN TEMPERATURE PROFILE STATS")
if 'Kiln.csv' in dfs:
    df = dfs['Kiln.csv']
    temp_cols = [c for c in df.columns if c.startswith('temp_')]
    print(f"  Temperature columns: {len(temp_cols)}")
    
    stats = df[temp_cols].describe().T
    stats['missing'] = df[temp_cols].isna().sum()
    print(f"\n  {'Column':<20} {'Min':>6} {'Max':>6} {'Mean':>7} {'Std':>7} {'Missing':>7}")
    print(f"  {'-'*20} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7}")
    for col in temp_cols:
        row = stats.loc[col]
        print(f"  {col:<20} {row['min']:>6.0f} {row['max']:>6.0f} {row['mean']:>7.1f} {row['std']:>7.1f} {int(row['missing']):>7}")
    
    # Check for impossible temperatures
    print(f"\n  Anomaly detection:")
    for col in temp_cols:
        low = (df[col] < 0).sum()
        high = (df[col] > 1200).sum()
        if low > 0 or high > 0:
            print(f"    {col}: {low} below 0°C, {high} above 1200°C")

# ---- PACKING WASTE RATE ----
print("\n[6] PACKING WASTE RATE ANALYSIS")
if 'Packing.csv' in dfs:
    df = dfs['Packing.csv']
    df_clean = df[['TotalCount', 'Grade1Count', 'WasteCount']].dropna().apply(pd.to_numeric, errors='coerce').dropna()
    df_clean = df_clean[df_clean['TotalCount'] > 0]
    df_clean['waste_rate'] = df_clean['WasteCount'] / df_clean['TotalCount'] * 100
    df_clean['grade1_rate'] = df_clean['Grade1Count'] / df_clean['TotalCount'] * 100
    
    print(f"  Records analyzed: {len(df_clean)}")
    print(f"  Waste rate: min={df_clean['waste_rate'].min():.2f}%, max={df_clean['waste_rate'].max():.2f}%, avg={df_clean['waste_rate'].mean():.2f}%")
    print(f"  Grade 1 rate: min={df_clean['grade1_rate'].min():.2f}%, max={df_clean['grade1_rate'].max():.2f}%, avg={df_clean['grade1_rate'].mean():.2f}%")
    
    # Outliers
    high_waste = df_clean[df_clean['waste_rate'] > 30]
    print(f"  Records with waste > 30%: {len(high_waste)}")
    
    zero_waste = df_clean[df_clean['WasteCount'] == 0]
    print(f"  Records with zero waste: {len(zero_waste)}")

# ---- SETTING ID LINKAGE ----
print("\n[7] SETTING ID CROSS-FILE LINKAGE")
if all(f in dfs for f in ['Setting_Setting.csv', 'Setting_wagons.csv']):
    ss_ids = set(dfs['Setting_Setting.csv']['ID'].dropna().astype(str).tolist())
    sw_ids = set(dfs['Setting_wagons.csv']['SettingID'].dropna().astype(str).tolist())
    
    in_both = ss_ids & sw_ids
    only_ss = ss_ids - sw_ids
    only_sw = sw_ids - ss_ids
    
    print(f"  Setting_Setting IDs: {len(ss_ids)}")
    print(f"  Setting_wagons IDs: {len(sw_ids)}")
    print(f"  IDs in both files: {len(in_both)}")
    print(f"  IDs only in Setting_Setting: {len(only_ss)}")
    print(f"  IDs only in Setting_wagons: {len(only_sw)}")
    
    if only_ss:
        print(f"  Orphan Setting_Setting IDs (first 10): {sorted(list(only_ss))[:10]}")
    if only_sw:
        print(f"  Orphan Setting_wagons IDs (first 10): {sorted(list(only_sw))[:10]}")

# ---- THE MYSTERIOUS 140.0 OPERATOR ----
print("\n[8] ANOMALOUS OPERATOR CODE: 140.0")
if 'Setting_Setting.csv' in dfs:
    df = dfs['Setting_Setting.csv']
    anomalous = df[df['OperatorCode_FK'] == 140.0]
    print(f"  Records with OperatorCode_FK = 140.0: {len(anomalous)}")
    if len(anomalous) > 0:
        print(f"  Sample rows:")
        for _, row in anomalous.head(5).iterrows():
            print(f"    date={row['date_jalali']}, shift={row['shift']}, chamber={row['chamber_no']}, product={row['productName']}, fingers={row['fingers_count']}")

# ---- WAGON NUMBER RANGE ----
print("\n[9] WAGON NUMBER RANGE")
if 'Setting_wagons.csv' in dfs:
    df = dfs['Setting_wagons.csv']
    wn = pd.to_numeric(df['wagon_no'], errors='coerce').dropna()
    print(f"  Wagon numbers: min={int(wn.min())}, max={int(wn.max())}")
    print(f"  Wagon number distribution (top 10):")
    print(f"  {wn.value_counts().head(10).to_dict()}")

print("\n" + "=" * 80)
print("DEEP-DIVE COMPLETE")
print("=" * 80)
