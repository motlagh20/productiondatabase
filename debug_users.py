
import sqlite3
import os

DATABASE = 'kiln_monitoring.db'

def check_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Users Table Info ---")
    cursor.execute("PRAGMA table_info(Users)")
    for r in cursor.fetchall():
        print(dict(r))

    print("--- Users ---")
    cursor.execute("SELECT * FROM Users")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- Roles ---")
    cursor.execute("SELECT RoleID, RoleName FROM Roles")
    for r in cursor.fetchall():
        print(dict(r))

    print("\n--- UserRoles ---")
    cursor.execute("SELECT * FROM UserRoles")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- Operators Dryer View Simulation ---")
    # Simulate the query from server.py get_operators('dryer')
    role_names = ['Dryer', 'Dryer Operator', 'Operator.Dryer', 'اپراتور خشک کن', 'اپراتور خشک‌کن', 'Operator']
    placeholders = ",".join(["?"] * len(role_names))
    sql = f"""
        SELECT u.UserID AS OperatorCode, COALESCE(u.FullName, u.Username) AS OperatorName
        FROM Users u
        JOIN UserRoles ur ON ur.UserID = u.UserID
        JOIN Roles r ON r.RoleID = ur.RoleID
        WHERE r.RoleName IN ({placeholders})
          AND u.IsActive = 1
    """
    cursor.execute(sql, tuple(role_names))
    rows = [dict(row) for row in cursor.fetchall()]
    print(rows)

    conn.close()

if __name__ == '__main__':
    check_db()
