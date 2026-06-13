
import sqlite3

try:
    conn = sqlite3.connect('kiln_monitoring.db')
    cursor = conn.cursor()
    
    # Create Operator table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Operator (
            OperatorID INTEGER PRIMARY KEY,
            OperatorCode INTEGER NOT NULL UNIQUE,
            OperatorName TEXT NOT NULL,
            Role TEXT NOT NULL,
            DepartmentID_FK INTEGER
        )
    """)
    
    # Insert defaults
    cursor.execute("INSERT OR IGNORE INTO Operator (OperatorCode, OperatorName, Role) VALUES (1, 'Operator 1', 'Dryer')")
    cursor.execute("INSERT OR IGNORE INTO Operator (OperatorCode, OperatorName, Role) VALUES (2, 'Operator 2', 'Kiln')")
    cursor.execute("INSERT OR IGNORE INTO Operator (OperatorCode, OperatorName, Role) VALUES (3, 'Operator 3', 'Packing')")
    
    conn.commit()
    print("Operator table created/updated.")
    
    # Verify
    cursor.execute("SELECT * FROM Operator")
    print("Operators:", cursor.fetchall())
    
    conn.close()
except Exception as e:
    print(e)
