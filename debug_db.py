import sqlite3
import os

db_path = r'c:\Users\Mohammad\Documents\trae_projects\ProductionDatabase\kiln_monitoring.db'

print(f"Checking DB at: {db_path}")
if not os.path.exists(db_path):
    print(f"Database {db_path} not found!")
    print(f"CWD: {os.getcwd()}")
    print(f"Files: {os.listdir('.')}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- Table Info: DryerLoading ---")
    try:
        cursor.execute("PRAGMA table_info(DryerLoading)")
        cols = cursor.fetchall()
        for r in cols:
            print(r)
    
        print("\n--- Foreign Keys: DryerLoading ---")
        cursor.execute("PRAGMA foreign_key_list(DryerLoading)")
        for r in cursor.fetchall():
            print(r)

    except Exception as e:
        print(e)

    print("\n--- User 0 Check ---")
    try:
        cursor.execute("SELECT * FROM Users WHERE UserID = 0")
        print(cursor.fetchall())
    except Exception as e:
        print(e)

    print("\n--- Latest DryerLoading and test insert/uninsert in DryerUnloading ---")
    try:
        cursor.execute("SELECT LoadID, ChamberNo, LoadDateJalali, LoadTime, LoadOperatorID FROM DryerLoading ORDER BY LoadID DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(dict(zip(['LoadID','ChamberNo','LoadDateJalali','LoadTime','LoadOperatorID'], row)))
            load_id = int(row[0])
            # pick a valid operator (first active user)
            cursor.execute("SELECT UserID FROM Users WHERE IsActive = 1 ORDER BY UserID LIMIT 1")
            u = cursor.fetchone()
            op_id = int(u[0]) if u else 0
            print(f"Trying insert: LoadID={load_id}, OperatorID={op_id}")
            cursor.execute("""
                INSERT INTO DryerUnloading(LoadID, UnloadDateJalali, UnloadTime, UnloadOperatorID, FingerCount, UnloadTimestamp)
                VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (load_id, '1403/10/01', '12:34', op_id, 10))
            ins_id = cursor.lastrowid
            print(f"Inserted UnloadID={ins_id}, now deleting for cleanup...")
            cursor.execute("DELETE FROM DryerUnloading WHERE UnloadID = ?", (ins_id,))
            print("Cleanup done.")
            conn.commit()
        else:
            print("No DryerLoading rows found.")
    except Exception as e:
        print(f"Test insert failed: {e}")

    conn.close()
