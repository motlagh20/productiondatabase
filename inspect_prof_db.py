import sqlite3
import os

db_path = os.path.join('samples', 'kiln_system_professional.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Structure of {db_path}:")
for table in tables:
    table_name = table[0]
    print(f"- {table_name}")

conn.close()
