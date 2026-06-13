
import sqlite3

try:
    conn = sqlite3.connect('kiln_monitoring.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO Product (ProductCode, ProductName) VALUES (1, 'Sofal 10')")
    cursor.execute("INSERT OR IGNORE INTO Product (ProductCode, ProductName) VALUES (2, 'Sofal 15')")
    cursor.execute("INSERT OR IGNORE INTO Product (ProductCode, ProductName) VALUES (3, 'Sofal 20')")
    conn.commit()
    print("Products added.")
    conn.close()
except Exception as e:
    print(e)
