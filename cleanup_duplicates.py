
import sqlite3

def cleanup():
    db_path = 'kiln_monitoring.db'
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        print("Starting cleanup...")
        
        # 1. Ensure UNK glaze exists
        cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
        row = cursor.fetchone()
        if not row:
            print("Creating UNK glaze...")
            cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsGlazed, IsActive) VALUES('UNK', 'نامشخص', 1, 1)")
            cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
            row = cursor.fetchone()
        
        unk_glaze_id = row['GlazeID']
        print(f"UNK Glaze ID: {unk_glaze_id}")
        
        # 2. Find duplicate 'نامشخص' glazes
        cursor.execute("SELECT GlazeID, GlazeCode FROM Glazes WHERE GlazeName='نامشخص' AND GlazeCode != 'UNK'")
        dup_glazes = cursor.fetchall()
        
        for dg in dup_glazes:
            old_gid = dg['GlazeID']
            print(f"Processing duplicate glaze: ID={old_gid}, Code={dg['GlazeCode']}")
            
            # Update direct references to GlazeID in tables (DryerLoading, SettingWagons if any)
            # DryerLoading has GlazeID
            cursor.execute("UPDATE DryerLoading SET GlazeID = ? WHERE GlazeID = ?", (unk_glaze_id, old_gid))
            
            # SettingWagons does NOT have GlazeID directly usually (it has ProductID), 
            # but wait, my recent search showed it has `GlazeOverride`? 
            # Let's check schema. `SettingWagons` has `GlazeOverride` text, not ID.
            # But wait, `add_setting_wagons` inserts into `SettingWagons`.
            # Let's check `SettingWagons` schema again.
            # I recall `SettingWagons` has `ProductID`.
            # Does it have `GlazeID`?
            # In `server.py` get_setting_details query: `SELECT sw.*, g.GlazeName ... LEFT JOIN Glazes g ON g.GlazeID = sw.GlazeID` was the error!
            # So `SettingWagons` does NOT have `GlazeID`.
            # So I only need to worry about `Products` and `DryerLoading` (and `SettingWagons` via `ProductID`).
            
            # 3. Handle Products using this old glaze
            cursor.execute("SELECT * FROM Products WHERE GlazeID = ?", (old_gid,))
            products = cursor.fetchall()
            
            for p in products:
                old_pid = p['ProductID']
                cat_id = p['CategoryID']
                mold_id = p['MoldID']
                extra = p['ExtraCode'] or ''
                
                # Check if a product already exists with UNK glaze
                cursor.execute("""
                    SELECT ProductID FROM Products 
                    WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ?
                """, (cat_id, mold_id, unk_glaze_id, extra))
                target_p = cursor.fetchone()
                
                if target_p:
                    target_pid = target_p['ProductID']
                    if target_pid == old_pid:
                        continue # Should not happen if GlazeID is different
                        
                    print(f"  Merging Product {old_pid} into {target_pid}...")
                    
                    # Update references to use target_pid
                    cursor.execute("UPDATE DryerLoading SET ProductID = ? WHERE ProductID = ?", (target_pid, old_pid))
                    cursor.execute("UPDATE SettingWagons SET ProductID = ? WHERE ProductID = ?", (target_pid, old_pid))
                    
                    # Delete old product
                    cursor.execute("DELETE FROM Products WHERE ProductID = ?", (old_pid,))
                else:
                    print(f"  Migrating Product {old_pid} to use UNK glaze...")
                    # Just update the GlazeID
                    # Also need to update ProductCode and ProductName
                    # We can let the trigger handle it? No, triggers usually fire on INSERT/UPDATE.
                    # Let's manually update or rely on app logic?
                    # The app logic updates ProductCode via trigger `trg_products_after_insert` (server.py schema check).
                    # Is there an update trigger?
                    # `schema.sql` shows `trg_products_after_insert`.
                    # I don't see an UPDATE trigger.
                    # So I should update Code/Name manually.
                    
                    # Fetch names
                    cursor.execute("SELECT CategoryCode, CategoryName FROM Categories WHERE CategoryID=?", (cat_id,))
                    c_row = cursor.fetchone()
                    c_code = c_row['CategoryCode'] if c_row else 'UNK'
                    c_name = c_row['CategoryName'] if c_row else ''
                    
                    cursor.execute("SELECT MoldCode, MoldName FROM Molds WHERE MoldID=?", (mold_id,))
                    m_row = cursor.fetchone()
                    m_code = m_row['MoldCode'] if m_row else 'UNK'
                    m_name = m_row['MoldName'] if m_row else ''
                    
                    # UNK Glaze info
                    g_code = 'UNK'
                    g_name = 'نامشخص'
                    
                    new_code = f"{c_code}-{m_code}-{g_code}{extra}"
                    new_name = f"{c_name} {m_name} {g_name}".strip()
                    
                    cursor.execute("""
                        UPDATE Products 
                        SET GlazeID = ?, ProductCode = ?, ProductName = ? 
                        WHERE ProductID = ?
                    """, (unk_glaze_id, new_code, new_name, old_pid))

            # Now safe to delete the duplicate glaze
            print(f"Deleting glaze {old_gid}...")
            cursor.execute("DELETE FROM Glazes WHERE GlazeID = ?", (old_gid,))
            
        conn.commit()
        print("Cleanup completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    cleanup()
