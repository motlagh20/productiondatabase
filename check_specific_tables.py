import sqlite3
import os

db_path = os.path.join('samples', 'kiln_monitoring.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables_to_check = ['Operator', 'User', 'Users', 'SettingTransaction', 'Shifts', 'ShiftWagons']

print("Checking existence and row counts of specific tables:")
for table in tables_to_check:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if cursor.fetchone():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: Exists, {count} rows")
    else:
        print(f"{table}: Does NOT exist")

conn.close()
