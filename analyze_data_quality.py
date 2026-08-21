#!/usr/bin/env python3
"""
Historical Data Quality Analysis Script
Analyzes all CSV files in xls/ directory comprehensively.
"""

import pandas as pd
import numpy as np
import os
import re
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path("xls")

def read_csv_safe(path):
    """Read CSV with various encodings and handle common issues."""
    for encoding in ['utf-8-sig', 'utf-8', 'cp1256', 'latin1']:
        try:
            df = pd.read_csv(path, encoding=encoding)
            return df
        except Exception as e:
            last_error = e
    print(f"  WARNING: Could not read {path}: {last_error}")
    return None

def analyze_file(filepath, name):
    """Comprehensive single-file analysis."""
    df = read_csv_safe(filepath)
    if df is None:
        return None
    
    result = {
        'name': name,
        'rows': len(df),
        'columns': list(df.columns),
        'col_count': len(df.columns),
        'missing': {},
        'missing_pct': {},
        'duplicate_rows': df.duplicated().sum(),
        'sample': df.head(3).to_dict('records'),
        'dtypes': {c: str(df[c].dtype) for c in df.columns},
        'unique_counts': {c: df[c].nunique(dropna=False) for c in df.columns},
    }
    
    # Missing values
    for col in df.columns:
        missing = df[col].isna().sum() + (df[col].astype(str).str.strip() == '').sum()
        # Also count literal 'nan' or 'NaN' strings
        nan_strings = df[col].astype(str).str.lower().isin(['nan', 'none', 'null', '']).sum()
        result['missing'][col] = int(missing)
        result['missing_pct'][col] = round(missing / len(df) * 100, 2) if len(df) > 0 else 0
    
    return result, df

print("=" * 80)
print("HISTORICAL DATA QUALITY ANALYSIS")
print("Directory: xls/")
print("=" * 80)

# Map of files to analyze
files = {
    'Dryer.csv': 'Dataset A - Dryer Chamber Load/Unload',
    'Setting_wagons.csv': 'Dataset B - Wagon/Glaze/Packages',
    'Setting_Setting.csv': 'Dataset C - Setting/Shift/Supervision',
    'Packing.csv': 'Dataset D - Grading/Quality/Waste',
    'Kiln.csv': 'Kiln Push + Temperature Profile',
    'Categories.csv': 'Reference - Product Categories',
    'Molds.csv': 'Reference - Molds',
    'Glaze.csv': 'Reference - Glaze Types',
    'ProductName.csv': 'Reference - Product Names',
    'Operators.csv': 'Reference - Operators',
    'Supervisors.csv': 'Reference - Supervisors',
}

results = {}
dataframes = {}

for fname, description in files.items():
    fpath = DATA_DIR / fname
    if not fpath.exists():
        print(f"\n[SKIP] {fname} not found")
        continue
    
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    print(f"DESCRIPTION: {description}")
    print(f"{'='*60}")
    
    res, df = analyze_file(fpath, fname)
    if res is None:
        continue
    
    results[fname] = res
    dataframes[fname] = df
    
    print(f"  Rows: {res['rows']:,}")
    print(f"  Columns ({res['col_count']}): {', '.join(res['columns'])}")
    print(f"  Duplicate rows: {res['duplicate_rows']}")
    
    print(f"\n  Missing Values:")
    for col, count in res['missing'].items():
        pct = res['missing_pct'][col]
        if count > 0:
            print(f"    {col}: {count} ({pct}%)")
    
    print(f"\n  Sample rows:")
    for i, row in enumerate(res['sample'][:2]):
        print(f"    Row {i+1}: {row}")

print("\n" + "=" * 80)
print("CROSS-FILE ANALYSIS")
print("=" * 80)

# ---- DATE FORMAT ANALYSIS ----
print("\n[1] JALALI DATE FORMAT VARIATIONS")
date_patterns = defaultdict(list)

for fname, df in dataframes.items():
    for col in df.columns:
        if 'date' in col.lower() or 'jalali' in col.lower():
            sample_vals = df[col].dropna().astype(str).head(50).tolist()
            for val in sample_vals:
                val = val.strip()
                if re.match(r'^\d{4}[-./]\d{1,2}[-./]\d{1,2}$', val):
                    sep = re.search(r'[-./]', val).group()
                    parts = val.split(sep)
                    if len(parts[1]) == 1 or len(parts[2]) == 1:
                        pattern = f"YYYY{sep}M{sep}D (unpadded)"
                    else:
                        pattern = f"YYYY{sep}MM{sep}DD (padded)"
                    date_patterns[pattern].append(f"{fname}.{col}")
                elif re.match(r'^\d{4}[-./]\d{2}[-./]\d{2}$', val):
                    sep = re.search(r'[-./]', val).group()
                    pattern = f"YYYY{sep}MM{sep}DD"
                    date_patterns[pattern].append(f"{fname}.{col}")

for pattern, sources in date_patterns.items():
    print(f"  {pattern}: found in {len(set(sources))} column(s)")
    for src in set(sources):
        print(f"    - {src}")

# ---- ID DUPLICATES ----
print("\n[2] DUPLICATE ID ANALYSIS")
for fname, df in dataframes.items():
    for col in df.columns:
        if col.upper() == 'ID' or col.lower().endswith('_id') or col.lower() == 'settingid':
            dupes = df[col].duplicated().sum()
            if dupes > 0:
                unique_vals = df[col].nunique()
                total_vals = len(df)
                print(f"  {fname}.{col}: {dupes} duplicates out of {total_vals} rows ({unique_vals} unique values)")
                # Show which IDs are duplicated
                vc = df[col].value_counts()
                dup_ids = vc[vc > 1].head(5)
                for vid, count in dup_ids.items():
                    print(f"    ID {vid}: appears {count} times")

# ---- OPERATOR CODE ANALYSIS ----
print("\n[3] OPERATOR CODE CONSISTENCY")
operator_sets = {}
for fname, df in dataframes.items():
    for col in df.columns:
        if 'operator' in col.lower() and 'code' in col.lower():
            ops = set(df[col].dropna().astype(str).tolist())
            operator_sets[f"{fname}.{col}"] = ops
            print(f"  {fname}.{col}: {len(ops)} unique codes: {sorted(ops, key=lambda x: str(x))}")

# Cross-check operator codes across files
if len(operator_sets) > 1:
    print(f"\n  Cross-file operator code overlap:")
    keys = list(operator_sets.keys())
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            common = operator_sets[keys[i]] & operator_sets[keys[j]]
            only_a = operator_sets[keys[i]] - operator_sets[keys[j]]
            only_b = operator_sets[keys[j]] - operator_sets[keys[i]]
            print(f"    {keys[i]} vs {keys[j]}:")
            print(f"      Common: {len(common)} codes")
            if only_a:
                print(f"      Only in {keys[i]}: {sorted(only_a, key=lambda x: str(x))}")
            if only_b:
                print(f"      Only in {keys[j]}: {sorted(only_b, key=lambda x: str(x))}")

# ---- PRODUCT CODE ANALYSIS ----
print("\n[4] PRODUCT/MOLD CODE ANALYSIS")
product_code_sets = {}
for fname, df in dataframes.items():
    for col in df.columns:
        if 'product' in col.lower() or 'mold' in col.lower() or 'glaze' in col.lower():
            if 'type' in col.lower() and 'glaze' in col.lower():
                # GlazeType is a separate analysis
                pass
            elif 'code' in col.lower() or 'name' in col.lower() or col == 'productName':
                vals = set(df[col].dropna().astype(str).tolist())
                product_code_sets[f"{fname}.{col}"] = vals
                print(f"  {fname}.{col}: {len(vals)} unique values")
                if len(vals) <= 30:
                    print(f"    Values: {sorted(vals, key=lambda x: str(x))}")
                else:
                    sample = sorted(vals, key=lambda x: str(x))[:10]
                    print(f"    Sample: {sample} ...")

# Check for unmapped codes
print(f"\n[5] UNMAPPED CODE DETECTION")
# Known reference codes
known_molds = set()
known_glazes = set()
known_categories = set()
known_products = set()

if 'Molds.csv' in dataframes:
    if 'MoldID' in dataframes['Molds.csv'].columns:
        known_molds = set(dataframes['Molds.csv']['MoldID'].dropna().astype(str).tolist())
if 'Glaze.csv' in dataframes:
    if 'TypeID' in dataframes['Glaze.csv'].columns:
        known_glazes = set(dataframes['Glaze.csv']['TypeID'].dropna().astype(str).tolist())
if 'Categories.csv' in dataframes:
    if 'ProductCategoriesID' in dataframes['Categories.csv'].columns:
        known_categories = set(dataframes['Categories.csv']['ProductCategoriesID'].dropna().astype(str).tolist())
if 'ProductName.csv' in dataframes:
    if 'ID' in dataframes['ProductName.csv'].columns:
        known_products = set(dataframes['ProductName.csv']['ID'].dropna().astype(str).tolist())

print(f"  Known mold codes: {known_molds}")
print(f"  Known glaze codes: {known_glazes}")
print(f"  Known category codes: {known_categories}")
print(f"  Known product codes: {known_products}")

# Check Kiln.csv for the infamous 90000001
if 'Kiln.csv' in dataframes and 'productName' in dataframes['Kiln.csv'].columns:
    kiln_products = set(dataframes['Kiln.csv']['productName'].dropna().astype(str).tolist())
    unknown = kiln_products - known_molds - known_products
    if unknown:
        print(f"\n  UNMAPPED codes in Kiln.csv.productName: {unknown}")
        for code in unknown:
            count = (dataframes['Kiln.csv']['productName'].astype(str) == code).sum()
            print(f"    {code}: appears {count} times")

# Check all transactional files for unmapped product codes
for fname in ['Dryer.csv', 'Setting_Setting.csv', 'Packing.csv']:
    if fname in dataframes:
        for col in dataframes[fname].columns:
            if 'product' in col.lower() or 'productcode' in col.lower():
                vals = set(dataframes[fname][col].dropna().astype(str).tolist())
                unknown = vals - known_molds - known_products
                if unknown:
                    print(f"\n  UNMAPPED codes in {fname}.{col}: {unknown}")

# ---- WAGON ANALYSIS ----
print(f"\n[6] WAGON ANALYSIS (Setting_wagons.csv)")
if 'Setting_wagons.csv' in dataframes:
    sw = dataframes['Setting_wagons.csv']
    print(f"  Total records: {len(sw)}")
    print(f"  Unique SettingIDs: {sw['SettingID'].nunique()}")
    print(f"  Unique wagon numbers: {sw['wagon_no'].nunique()}")
    
    # Wagon duplication per setting
    setting_wagon_counts = sw.groupby('SettingID')['wagon_no'].count()
    print(f"  Settings with multiple wagon records: {(setting_wagon_counts > 1).sum()}")
    print(f"  Max wagon records per setting: {setting_wagon_counts.max()}")
    
    # Partial fills (same wagon in same setting)
    dup_wagons = sw.groupby(['SettingID', 'wagon_no']).size()
    partial_fills = dup_wagons[dup_wagons > 1]
    print(f"  Same wagon appearing multiple times in same setting: {len(partial_fills)} instances")
    if len(partial_fills) > 0:
        print(f"  Examples:")
        for (sid, wno), count in partial_fills.head(5).items():
            rows = sw[(sw['SettingID'] == sid) & (sw['wagon_no'] == wno)]
            packages = rows['packages'].tolist()
            print(f"    Setting {sid}, Wagon {wno}: {count} records, packages = {packages}")

# ---- TIME FORMAT ANALYSIS ----
print(f"\n[7] TIME FORMAT ANALYSIS")
for fname, df in dataframes.items():
    for col in df.columns:
        if 'time' in col.lower():
            sample = df[col].dropna().astype(str).head(30).tolist()
            formats_found = set()
            for val in sample:
                val = val.strip()
                if re.match(r'^\d{1,2}:\d{2}:\d{2}$', val):
                    if len(val.split(':')[0]) == 1:
                        formats_found.add('H:MM:SS (unpadded hour)')
                    else:
                        formats_found.add('HH:MM:SS')
                elif re.match(r'^\d{1,2}:\d{2}$', val):
                    if len(val.split(':')[0]) == 1:
                        formats_found.add('H:MM (unpadded hour)')
                    else:
                        formats_found.add('HH:MM')
                elif re.match(r'^\d{1,2}:\d{2}:\d{2}$', val):
                    formats_found.add('H:MM:SS')
            if formats_found:
                print(f"  {fname}.{col}: {formats_found}")

# ---- PACKING GRADE ANALYSIS ----
print(f"\n[8] PACKING (GRADING) CONSISTENCY CHECK")
if 'Packing.csv' in dataframes:
    pk = dataframes['Packing.csv']
    print(f"  Total records: {len(pk)}")
    
    # Check if TotalCount = Grade1Count + WasteCount
    if all(c in pk.columns for c in ['TotalCount', 'Grade1Count', 'WasteCount']):
        pk_clean = pk[['TotalCount', 'Grade1Count', 'WasteCount']].dropna()
        pk_clean = pk_clean.apply(pd.to_numeric, errors='coerce').dropna()
        
        matches = (pk_clean['TotalCount'] == pk_clean['Grade1Count'] + pk_clean['WasteCount']).sum()
        mismatches = len(pk_clean) - matches
        print(f"  Records where TotalCount == Grade1 + Waste: {matches}/{len(pk_clean)}")
        print(f"  Mismatches: {mismatches}")
        
        if mismatches > 0:
            mismatched = pk_clean[pk_clean['TotalCount'] != pk_clean['Grade1Count'] + pk_clean['WasteCount']].head(5)
            print(f"  Examples of mismatch:")
            for idx, row in mismatched.iterrows():
                diff = row['TotalCount'] - (row['Grade1Count'] + row['WasteCount'])
                print(f"    Total={row['TotalCount']}, G1={row['Grade1Count']}, Waste={row['WasteCount']}, Diff={diff}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
