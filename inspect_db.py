import sqlite3
import os

db_path = os.path.join('samples', 'kiln_monitoring.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Current Database Structure:")
for table in tables:
    table_name = table[0]
    if table_name == 'sqlite_sequence':
        continue
    print(f"\nTable: {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        # cid, name, type, notnull, dflt_value, pk
        print(f"  - {col[1]} ({col[2]})")

conn.close()
