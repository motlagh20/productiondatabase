
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import re

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)

DATABASE = os.getenv('DATABASE', 'kiln_monitoring.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    return conn

def normalize_extra_code(val):
    try:
        s = (val or '').strip()
        if not s:
            return ''
        s = s.upper().replace(' ', '')
        if not s.startswith('-'):
            s = '-' + s
        allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
        s = ''.join(ch for ch in s if ch in allowed)
        return s
    except Exception:
        return (val or '').strip()

def to_ascii_digits(s: str) -> str:
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return str(s or '').translate(trans)

def normalize_jalali_date(s: str) -> str:
    try:
        raw = to_ascii_digits(str(s or '').strip())
        m = re.match(r'^(\d{4})\D?(\d{1,2})\D?(\d{1,2})$', raw)
        if not m:
            digits = re.sub(r'\D', '', raw)
            if len(digits) == 8:
                m = re.match(r'^(\d{4})(\d{2})(\d{2})$', digits)
        if not m:
            return raw
        y = int(m.group(1))
        mm = int(m.group(2))
        dd = int(m.group(3))
        if y < 1200 or y > 1600:
            y = int(str(y).zfill(4))
        if mm < 1: mm = 1
        if mm > 12: mm = 12
        if dd < 1: dd = 1
        if dd > 31: dd = 31
        return f"{y:04d}/{mm:02d}/{dd:02d}"
    except Exception:
        return str(s or '').strip()
def initialize_database():
    conn = get_db()
    cur = conn.cursor()
    try:
        script = """
        PRAGMA foreign_keys = OFF;
        CREATE TABLE IF NOT EXISTS FuelTypes(
            FuelTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
            FuelName TEXT NOT NULL UNIQUE,
            IsActive INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Categories (
            CategoryID      INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryCode    TEXT NOT NULL UNIQUE,
            CategoryName    TEXT NOT NULL,
            Description     TEXT,
            IsActive        INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Molds (
            MoldID          INTEGER PRIMARY KEY AUTOINCREMENT,
            MoldCode        TEXT NOT NULL UNIQUE,
            MoldName        TEXT NOT NULL,
            Width           REAL,
            Length          REAL,
            Height          REAL,
            PiecesPerPress  INTEGER DEFAULT 1,
            IsActive        INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Glazes (
            GlazeID         INTEGER PRIMARY KEY AUTOINCREMENT,
            GlazeCode       TEXT NOT NULL UNIQUE,
            GlazeName       TEXT NOT NULL,
            IsGlazed        INTEGER DEFAULT 1,
            IsActive        INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Products (
            ProductID       INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductCode     TEXT UNIQUE NOT NULL,
            ProductName     TEXT NOT NULL,
            CategoryID      INTEGER NOT NULL,
            MoldID          INTEGER NOT NULL,
            GlazeID         INTEGER NOT NULL,
            ExtraCode       TEXT DEFAULT '',
            IsActive        INTEGER DEFAULT 1,
            CreatedAt       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(CategoryID) REFERENCES Categories(CategoryID) ON DELETE RESTRICT,
            FOREIGN KEY(MoldID) REFERENCES Molds(MoldID) ON DELETE RESTRICT,
            FOREIGN KEY(GlazeID) REFERENCES Glazes(GlazeID) ON DELETE RESTRICT,
            UNIQUE(CategoryID, MoldID, GlazeID, ExtraCode)
        );
        CREATE TABLE IF NOT EXISTS ExtraCodeMapping (
            ExtraCode   TEXT PRIMARY KEY,
            DisplayName TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Users(
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            FullName TEXT,
            IsActive INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Roles(
            RoleID INTEGER PRIMARY KEY AUTOINCREMENT,
            RoleName TEXT NOT NULL UNIQUE,
            IsActive INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS UserRoles(
            UserID INTEGER NOT NULL,
            RoleID INTEGER NOT NULL,
            PRIMARY KEY(UserID, RoleID),
            FOREIGN KEY(UserID) REFERENCES Users(UserID) ON DELETE RESTRICT,
            FOREIGN KEY(RoleID) REFERENCES Roles(RoleID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS ShiftsDefinition(
            ShiftID INTEGER PRIMARY KEY AUTOINCREMENT,
            ShiftCode TEXT NOT NULL UNIQUE,
            ShiftName TEXT,
            IsActive INTEGER DEFAULT 1,
            StartTime TEXT,
            EndTime TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_shifts_name_nocase ON ShiftsDefinition(ShiftName COLLATE NOCASE);
        CREATE TABLE IF NOT EXISTS Pages(
            PageID INTEGER PRIMARY KEY AUTOINCREMENT,
            PageKey TEXT NOT NULL UNIQUE,
            PageTitle TEXT NOT NULL,
            IsActive INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS RolePageAccess(
            RoleID INTEGER NOT NULL,
            PageID INTEGER NOT NULL,
            PRIMARY KEY(RoleID, PageID),
            FOREIGN KEY(RoleID) REFERENCES Roles(RoleID) ON DELETE RESTRICT,
            FOREIGN KEY(PageID) REFERENCES Pages(PageID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS DryerLoading (
            LoadID INTEGER PRIMARY KEY AUTOINCREMENT,
            ChamberNo INTEGER NOT NULL,
            ProductID INTEGER NOT NULL,
            LoadDateJalali TEXT,
            LoadTime TEXT,
            LoadOperatorID INTEGER,
            FingerCount INTEGER,
            LoadTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            IsUnloaded INTEGER DEFAULT 0,
            FOREIGN KEY(ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT,
            FOREIGN KEY(LoadOperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS DryerUnloading (
            UnloadID INTEGER PRIMARY KEY AUTOINCREMENT,
            LoadID INTEGER NOT NULL,
            UnloadDateJalali TEXT,
            UnloadTime TEXT,
            UnloadOperatorID INTEGER,
            FingerCount INTEGER,
            UnloadTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(LoadID) REFERENCES DryerLoading(LoadID) ON DELETE RESTRICT,
            FOREIGN KEY(UnloadOperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT
        );
        CREATE TRIGGER IF NOT EXISTS trg_unload_marks_loading
        AFTER INSERT ON DryerUnloading
        BEGIN
            UPDATE DryerLoading SET IsUnloaded = 1 WHERE LoadID = NEW.LoadID;
        END;
        CREATE TABLE IF NOT EXISTS DryerReadings (
            ReadID INTEGER PRIMARY KEY AUTOINCREMENT,
            LoadID INTEGER NOT NULL,
            ExhaustTemp REAL,
            Preheat1 REAL,
            Preheat2 REAL,
            Thermostat REAL,
            Zone0 REAL, Zone1 REAL, Zone2 REAL, Zone3 REAL, Zone4 REAL, Zone5 REAL, Zone6 REAL, Zone7 REAL,
            Rapid1 REAL, Rapid2 REAL, BottomA REAL, Bottom1 REAL, BottomB REAL, Bottom2 REAL,
            Notes TEXT,
            FOREIGN KEY(LoadID) REFERENCES DryerLoading(LoadID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS SimpleDryerReadings (
            ReadingID INTEGER PRIMARY KEY AUTOINCREMENT,
            ChamberNo INTEGER NOT NULL,
            DateJalali TEXT NOT NULL,
            Time TEXT NOT NULL,
            Temperature REAL,
            Humidity REAL,
            OperatorCode_FK INTEGER,
            CreatedAt TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(OperatorCode_FK) REFERENCES Users(UserID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS SettingProcesses ( 
            SettingID           INTEGER PRIMARY KEY AUTOINCREMENT, 
            SettingDateJalali   TEXT NOT NULL, 
            ShiftID             INTEGER NOT NULL, 
            SupervisorID        INTEGER NOT NULL, 
            OperatorID          INTEGER NOT NULL, 
            PersonnelCount      INTEGER, 
            ChamberNo           INTEGER NOT NULL, 
            CategoryID          INTEGER NOT NULL, 
            FingersCount        INTEGER, 
            ColumnsCount        INTEGER, 
            DryerWaste          INTEGER DEFAULT 0, 
            CreatedAt           TEXT DEFAULT (datetime('now')), 
            Notes               TEXT, 
            FOREIGN KEY(ShiftID) REFERENCES ShiftsDefinition(ShiftID) ON DELETE RESTRICT, 
            FOREIGN KEY(SupervisorID) REFERENCES Users(UserID) ON DELETE RESTRICT, 
            FOREIGN KEY(OperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT, 
            FOREIGN KEY(CategoryID) REFERENCES Categories(CategoryID) ON DELETE RESTRICT, 
            UNIQUE(SettingDateJalali, ChamberNo) 
        );
        CREATE TABLE IF NOT EXISTS SettingWagons (
            WagonID INTEGER PRIMARY KEY AUTOINCREMENT,
            SettingID INTEGER NOT NULL,
            WagonOrder INTEGER NOT NULL CHECK(WagonOrder BETWEEN 1 AND 4),
            WagonNo INTEGER NOT NULL,
            ProductID INTEGER NOT NULL,
            GlazeOverride TEXT,
            StartTime TEXT,
            EndTime TEXT,
            Packages INTEGER NOT NULL,
            Notes TEXT,
            FOREIGN KEY (SettingID) REFERENCES SettingProcesses(SettingID) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT,
            UNIQUE(SettingID, WagonOrder),
            UNIQUE(SettingID, WagonNo)
        );
        CREATE TABLE IF NOT EXISTS WarehouseStock (
            StockID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductID INTEGER NOT NULL,
            Quantity INTEGER NOT NULL DEFAULT 0,
            UpdatedAt TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS WarehouseTransactions (
            TransID INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductID INTEGER NOT NULL,
            Quantity INTEGER NOT NULL,
            Type TEXT NOT NULL,
            Timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS PackagingRecords (
            PackageID INTEGER PRIMARY KEY AUTOINCREMENT,
            PackageDateJalali TEXT NOT NULL,
            ShiftID INTEGER NOT NULL,
            OperatorID INTEGER NOT NULL,
            TypeOfWorkers TEXT,
            WorkersCount INTEGER,
            ProductID INTEGER NOT NULL,
            WagonNo INTEGER,
            TotalCount INTEGER NOT NULL,
            Grade1Count INTEGER NOT NULL,
            WasteCount INTEGER DEFAULT 0,
            CreatedAt TEXT DEFAULT (datetime('now')),
            Notes TEXT,
            FOREIGN KEY(ShiftID) REFERENCES ShiftsDefinition(ShiftID) ON DELETE RESTRICT,
            FOREIGN KEY(OperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT,
            FOREIGN KEY(ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT,
            CHECK (Grade1Count + WasteCount <= TotalCount)
        );
        CREATE TABLE IF NOT EXISTS KilnPushData(
            PushID INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            DateJalali TEXT,
            Time TEXT,
            ShiftID INTEGER,
            OperatorID INTEGER,
            ProductID INTEGER NOT NULL,
            IncomingCarID INTEGER,
            FuelTypeID INTEGER,
            PushingTime_min REAL,
            ExhaustTemp REAL,
            Preheat1 REAL,
            Preheat2 REAL,
            Thermostat REAL,
            Zone0 REAL, Zone1 REAL, Zone2 REAL, Zone3 REAL, Zone4 REAL, Zone5 REAL, Zone6 REAL, Zone7 REAL,
            Rapid1 REAL, Rapid2 REAL,
            BottomA REAL, Bottom1 REAL, BottomB REAL, Bottom2 REAL,
            Notes TEXT,
            FOREIGN KEY (FuelTypeID) REFERENCES FuelTypes(FuelTypeID) ON DELETE RESTRICT,
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT,
            FOREIGN KEY (OperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT
        );
        DROP TRIGGER IF EXISTS v_product_insert_ins;
        DROP VIEW IF EXISTS v_ProductInsert;
        CREATE VIEW IF NOT EXISTS v_ProductInsert AS
        SELECT CategoryID, MoldID, GlazeID, ExtraCode, IsActive FROM Products;
        CREATE TRIGGER IF NOT EXISTS v_product_insert_ins
        INSTEAD OF INSERT ON v_ProductInsert
        BEGIN
          INSERT INTO Products (ProductCode, ProductName, CategoryID, MoldID, GlazeID, ExtraCode, IsActive)
          SELECT
            c.CategoryCode || '-' || m.MoldCode || '-' || g.GlazeCode || COALESCE(NULLIF(TRIM(NEW.ExtraCode), ''), ''),
            c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName ||
              COALESCE(
                (SELECT ' ' || DisplayName FROM ExtraCodeMapping WHERE ExtraCode = NULLIF(TRIM(NEW.ExtraCode), '')),
                CASE WHEN TRIM(NEW.ExtraCode) <> '' THEN ' ' || TRIM(NEW.ExtraCode) ELSE '' END
              ),
            NEW.CategoryID, NEW.MoldID, NEW.GlazeID, COALESCE(NEW.ExtraCode, ''), COALESCE(NEW.IsActive, 1)
          FROM Categories c, Molds m, Glazes g
          WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_products_after_insert
        AFTER INSERT ON Products
        BEGIN
          UPDATE Products
          SET
            ProductCode = (
              SELECT c.CategoryCode || '-' || m.MoldCode || '-' || g.GlazeCode || COALESCE(NULLIF(TRIM(NEW.ExtraCode), ''), '')
              FROM Categories c, Molds m, Glazes g
              WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID
            ),
            ProductName = (
              SELECT c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName ||
                     COALESCE(
                       (SELECT ' ' || DisplayName FROM ExtraCodeMapping WHERE ExtraCode = NULLIF(TRIM(NEW.ExtraCode), '')),
                       CASE WHEN TRIM(NEW.ExtraCode) <> '' THEN ' ' || TRIM(NEW.ExtraCode) ELSE '' END
                     )
              FROM Categories c, Molds m, Glazes g
              WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID
            )
          WHERE ProductID = NEW.ProductID;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_products_after_update
        AFTER UPDATE OF CategoryID, MoldID, GlazeID, ExtraCode ON Products
        BEGIN
          UPDATE Products
          SET
            ProductCode = (
              SELECT c.CategoryCode || '-' || m.MoldCode || '-' || g.GlazeCode || COALESCE(NULLIF(TRIM(NEW.ExtraCode), ''), '')
              FROM Categories c, Molds m, Glazes g
              WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID
            ),
            ProductName = (
              SELECT c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName ||
                     COALESCE(
                       (SELECT ' ' || DisplayName FROM ExtraCodeMapping WHERE ExtraCode = NULLIF(TRIM(NEW.ExtraCode), '')),
                       CASE WHEN TRIM(NEW.ExtraCode) <> '' THEN ' ' || TRIM(NEW.ExtraCode) ELSE '' END
                     )
              FROM Categories c, Molds m, Glazes g
              WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID
            )
          WHERE ProductID = NEW.ProductID;
        END;
        PRAGMA foreign_keys = ON;
        """
        cur.executescript(script)
        cleanup_duplicate_tables(cur)
        try:
            cur.execute("PRAGMA table_info(Molds)")
            mold_cols = [r['name'] for r in cur.fetchall()]
            if 'CategoryID' in mold_cols:
                cur.executescript("""
                PRAGMA foreign_keys = OFF;
                CREATE TABLE IF NOT EXISTS _MoldsNew (
                    MoldID          INTEGER PRIMARY KEY AUTOINCREMENT,
                    MoldCode        TEXT NOT NULL UNIQUE,
                    MoldName        TEXT NOT NULL,
                    Width           REAL,
                    Length          REAL,
                    Height          REAL,
                    PiecesPerPress  INTEGER DEFAULT 1,
                    IsActive        INTEGER DEFAULT 1
                );
                INSERT INTO _MoldsNew(MoldID, MoldCode, MoldName, Width, Length, Height, PiecesPerPress, IsActive)
                SELECT MoldID, MoldCode, MoldName, Width, Length, Height, PiecesPerPress, IsActive FROM Molds;
                DROP TABLE Molds;
                ALTER TABLE _MoldsNew RENAME TO Molds;
                PRAGMA foreign_keys = ON;
                """)
        except Exception:
            pass
        try:
            cur.execute("PRAGMA table_info(Glazes)")
            glaze_cols = [r['name'] for r in cur.fetchall()]
            if ('IsSelfColored' in glaze_cols) and ('IsGlazed' not in glaze_cols):
                cur.executescript("""
                PRAGMA foreign_keys = OFF;
                CREATE TABLE IF NOT EXISTS _GlazesNew (
                    GlazeID         INTEGER PRIMARY KEY AUTOINCREMENT,
                    GlazeCode       TEXT NOT NULL UNIQUE,
                    GlazeName       TEXT NOT NULL,
                    IsGlazed        INTEGER DEFAULT 1,
                    IsActive        INTEGER DEFAULT 1
                );
                INSERT INTO _GlazesNew(GlazeID, GlazeCode, GlazeName, IsGlazed, IsActive)
                SELECT GlazeID, GlazeCode, GlazeName, CASE WHEN COALESCE(IsSelfColored,0)=1 THEN 0 ELSE 1 END, IsActive
                FROM Glazes;
                DROP TABLE Glazes;
                ALTER TABLE _GlazesNew RENAME TO Glazes;
                PRAGMA foreign_keys = ON;
                """)
        except Exception:
            pass
        migrate_legacy_data(cur)
        try:
            seeds = [('S','سفال'),('T','تیزه'),('P','پنجه‌ای'),('A','آجر'),('X','اکسسوری')]
            for code, name in seeds:
                cur.execute("INSERT OR IGNORE INTO Categories(CategoryCode, CategoryName, IsActive) VALUES(?, ?, 1)", (code, name))
        except Exception:
            pass
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

def cleanup_duplicate_tables(cursor):
    try:
        legacy = [
            'Product', 'ProductCategory', 'User',
            'DryerCycle', 'PushingModel', 'PackingReport',
            'KilnOperationData', 'SettingTransaction', 'ChamberUnloadReport',
            'Operator', 'Supervisors'
        ]
        for t in legacy:
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
                if cursor.fetchone():
                    cursor.execute(f"DROP TABLE IF EXISTS {t}")
            except Exception:
                pass
        # Drop old views conflicting with new naming if exist
        legacy_views = ['product_details', 'example_view']
        for v in legacy_views:
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name=?", (v,))
                if cursor.fetchone():
                    cursor.execute(f"DROP VIEW IF EXISTS {v}")
            except Exception:
                pass
    except Exception:
        pass

def migrate_legacy_data(cursor):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Product'")
        has_legacy_product = cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('Category','Categories')")
        has_legacy_category = cursor.fetchone() is not None
        cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryCode='UNK'")
        unk_cat = cursor.fetchone()
        if not unk_cat:
            cursor.execute("INSERT INTO Categories(CategoryCode, CategoryName, Description, IsActive) VALUES('UNK','نامشخص','',1)")
        cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryCode='UNK'")
        unk_cat_id = (cursor.fetchone() or {'CategoryID': None})['CategoryID']
        cursor.execute("SELECT MoldID FROM Molds WHERE MoldCode='UNK'")
        unk_mold = cursor.fetchone()
        if not unk_mold:
            cursor.execute("INSERT INTO Molds(MoldCode, MoldName, IsActive) VALUES('UNK','نامشخص',1)")
        cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
        unk_glaze = cursor.fetchone()
        if not unk_glaze:
            cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsSelfColored, IsActive) VALUES('UNK','خام',0,1)")
        cursor.execute("SELECT MoldID FROM Molds WHERE MoldCode='UNK'")
        unk_mold_id = (cursor.fetchone() or {'MoldID': None})['MoldID']
        cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
        unk_glaze_id = (cursor.fetchone() or {'GlazeID': None})['GlazeID']
        if has_legacy_product:
            cursor.execute("SELECT ProductCode, ProductName FROM Product")
            rows = cursor.fetchall()
            for r in rows:
                cursor.execute("""
                    INSERT OR IGNORE INTO Products(CategoryID, MoldID, GlazeID, ExtraCode, IsActive)
                    VALUES(?, ?, ?, '', 1)
                """, (unk_cat_id, unk_mold_id, unk_glaze_id))
        if has_legacy_product:
            cursor.execute("DROP TABLE IF EXISTS Product")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ProductCategory'")
        if cursor.fetchone():
            cursor.execute("DROP TABLE IF EXISTS ProductCategory")
        if has_legacy_category:
            # Preserve the modern 'Categories' table created during initialization.
            # Only drop legacy 'Category' table if it exists.
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Category'")
            if cursor.fetchone():
                cursor.execute("DROP TABLE IF EXISTS Category")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='User'")
        if cursor.fetchone():
            cursor.execute("DROP TABLE IF EXISTS User")
    except Exception:
        pass

@app.route('/')
def serve_index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('web', path)

# --- API Endpoints ---

@app.route('/api/dryer/chambers/status', methods=['GET'])
def get_chamber_status():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              dl.ChamberNo,
              dl.LoadDateJalali,
              dl.LoadTime,
              dl.FingerCount,
              COALESCE(u.FullName, u.Username) AS Operator,
              CASE 
                WHEN c.CategoryName IS NULL OR TRIM(c.CategoryName) = '' 
                THEN m.MoldName || ' ' || g.GlazeName 
                ELSE c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName 
              END AS ProductName,
              c.CategoryName, m.MoldName
            FROM DryerLoading dl
            LEFT JOIN DryerUnloading du ON du.LoadID = dl.LoadID
            LEFT JOIN Categories c ON c.CategoryID = dl.CategoryID
            LEFT JOIN Molds m ON m.MoldID = dl.MoldID
            LEFT JOIN Glazes g ON g.GlazeID = dl.GlazeID
            LEFT JOIN Users u ON u.UserID = dl.LoadOperatorID
            WHERE du.UnloadID IS NULL AND dl.IsUnloaded = 0
        """)
        active = {row['ChamberNo']: dict(row) for row in cursor.fetchall()}
        result = []
        for i in range(1, 33):
            a = active.get(i)
            if a:
                result.append({
                    'ChamberNo': i,
                    'occupied': True,
                    'LoadDateJalali': a.get('LoadDateJalali'),
                    'LoadTime': a.get('LoadTime'),
                    'FingerCount': a.get('FingerCount'),
                    'Operator': a.get('Operator'),
                    'ProductName': a.get('ProductName'),
                    'CategoryName': a.get('CategoryName'),
                    'MoldName': a.get('MoldName'),
                    'Overdue': False
                })
            else:
                result.append({
                    'ChamberNo': i,
                    'occupied': False,
                    'Overdue': False
                })
        return jsonify(result)
    finally:
        conn.close()


@app.route('/api/operators/<role>', methods=['GET'])
def get_operators(role):
    conn = get_db()
    cursor = conn.cursor()
    try:
        rk = (role or '').strip().lower()
        role_sets = {
            'kiln': ['Kiln', 'Kiln Operator', 'Operator.Kiln', 'اپراتور کوره', 'Operator'],
            'dryer': ['Dryer', 'Dryer Operator', 'Operator.Dryer', 'اپراتور خشک کن', 'اپراتور خشک‌کن', 'Operator'],
            'setting': ['Setting', 'Operator.Setting', 'اپراتور ستینگ', 'Operator'],
            'packing': ['Packing Operator', 'Packing', 'Operator.Packing', 'اپراتور بسته\u200cبندی', 'Operator'],
            'operator': ['Operator', 'اپراتور'],
            'supervisor': ['Supervisor', 'HeadShift', 'سرشیفت']
        }
        names = role_sets.get(rk, [role])
        placeholders = ",".join(["?"] * len(names))
        sql = f"""
            SELECT u.UserID AS OperatorCode, COALESCE(u.FullName, u.Username) AS OperatorName
            FROM Users u
            JOIN UserRoles ur ON ur.UserID = u.UserID
            JOIN Roles r ON r.RoleID = ur.RoleID
            WHERE r.RoleName IN ({placeholders})
              AND u.IsActive = 1
        """
        cursor.execute(sql, tuple(names))
        rows = [dict(row) for row in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/load', methods=['POST'])
def record_load():
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        ensure_triple_product_schema()
        ensure_product_tables()
        cursor.execute("SELECT LoadID FROM DryerLoading WHERE ChamberNo = ? AND IsUnloaded = 0", (data['chamber_no'],))
        if cursor.fetchone():
            return jsonify({'error': 'Chamber is already occupied'}), 400

        op_val = data.get('operator_id')
        op_id = None
        try:
            op_id = int(op_val)
        except Exception:
            op_id = resolve_user_id(cursor, op_val)

        cid = data.get('category_id')
        mid = data.get('mold_id')
        gid = data.get('glaze_id')
        try:
            cid = int(cid) if cid is not None else None
            mid = int(mid) if mid is not None else None
            gid = int(gid) if gid is not None else None
        except Exception:
            cid = None
            mid = None
            gid = None
        if not mid:
            return jsonify({'error': 'mold_id required'}), 400
        if gid is None:
            cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
            g = cursor.fetchone()
            if not g:
                # Use fixed 'UNK' code so it can be found next time
                cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsGlazed, IsActive) VALUES(?, ?, ?, ?)", ('UNK', 'خام', 1, 1))
                cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
                g = cursor.fetchone()
            glaze_id = int((g or {'GlazeID': 0})['GlazeID'])
        else:
            glaze_id = gid

        cursor.execute("""
            SELECT ProductID FROM Products
            WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ''
            LIMIT 1
        """, (cid, mid, glaze_id))
        pr = cursor.fetchone()
        if not pr:
            cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, '', 1)", (cid, mid, glaze_id))
            conn.commit()
            cursor.execute("""
                SELECT ProductID FROM Products
                WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ''
                ORDER BY ProductID DESC LIMIT 1
            """, (cid, mid, glaze_id))
            pr = cursor.fetchone()
        product_id = int((pr or {'ProductID': 0})['ProductID'])

        cursor.execute("""
            INSERT INTO DryerLoading (
                ChamberNo, ProductID, CategoryID, MoldID, GlazeID, LoadTimestamp, LoadDateJalali, LoadTime, 
                LoadOperatorID, FingerCount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['chamber_no'],
            product_id,
            cid,
            mid,
            glaze_id,
            datetime.now(), # LoadTimestamp
            data['load_date_jalali'],
            data['load_time'],
            op_id or data['operator_id'],
            data['finger_count']
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/history', methods=['GET'])
def get_dryer_history():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            dl.LoadID as id,
            dl.ChamberNo as chamber,
            CASE 
              WHEN c.CategoryName IS NULL OR TRIM(c.CategoryName) = ''
              THEN m.MoldName
              ELSE c.CategoryName || ' ' || m.MoldName
            END as product,
            dl.CategoryID as category_id,
            dl.MoldID as mold_id,
            dl.GlazeID as glaze_id,
            dl.LoadDateJalali as date,
            dl.LoadTime as time,
            dl.FingerCount as finger,
            COALESCE(u.FullName, u.Username) as operator,
            dl.LoadOperatorID as operator_id
        FROM DryerLoading dl
        LEFT JOIN Categories c ON c.CategoryID = dl.CategoryID
        LEFT JOIN Molds m ON m.MoldID = dl.MoldID
        LEFT JOIN DryerUnloading du ON du.LoadID = dl.LoadID
        LEFT JOIN Users u ON dl.LoadOperatorID = u.UserID
        WHERE du.UnloadID IS NULL
        ORDER BY dl.LoadTimestamp DESC
        LIMIT 20
    """)
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(history)

@app.route('/api/dryer/update_load', methods=['POST'])
def update_dryer_load():
    data = request.json
    if not data or 'load_id' not in data:
        return jsonify({'error': 'Load ID is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Construct update query dynamically based on provided fields
        fields = []
        values = []
        
        if 'load_date_jalali' in data:
            fields.append("LoadDateJalali = ?")
            values.append(normalize_jalali_date(data['load_date_jalali']))
        if 'load_time' in data:
            fields.append("LoadTime = ?")
            values.append(data['load_time'])
        if 'finger_count' in data:
            fields.append("FingerCount = ?")
            values.append(data['finger_count'])
        if 'operator_id' in data:
            fields.append("LoadOperatorID = ?")
            values.append(data['operator_id'])
        if 'category_id' in data:
            fields.append("CategoryID = ?")
            values.append(data['category_id'])
        if 'mold_id' in data:
            fields.append("MoldID = ?")
            values.append(data['mold_id'])
        if 'glaze_id' in data:
            fields.append("GlazeID = ?")
            values.append(data['glaze_id'])
        if 'chamber_no' in data:
            fields.append("ChamberNo = ?")
            values.append(data['chamber_no'])
            
        if not fields:
            return jsonify({'success': True, 'message': 'No changes provided'})
            
        values.append(data['load_id'])
        query = f"UPDATE DryerLoading SET {', '.join(fields)} WHERE LoadID = ?"
        
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/occupied', methods=['GET'])
def get_occupied_chambers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            dl.LoadID,
            dl.ChamberNo, 
            CASE 
              WHEN c.CategoryName IS NULL OR TRIM(c.CategoryName) = ''
              THEN m.MoldName || ' ' || g.GlazeName
              ELSE c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName
            END AS ProductName,
            c.CategoryID,
            c.CategoryName,
            m.MoldID,
            m.MoldName,
            dl.LoadDateJalali,
            dl.LoadTime
        FROM DryerLoading dl
        LEFT JOIN DryerUnloading du ON du.LoadID = dl.LoadID
        LEFT JOIN Categories c ON c.CategoryID = dl.CategoryID
        LEFT JOIN Molds m ON m.MoldID = dl.MoldID
        LEFT JOIN Glazes g ON g.GlazeID = dl.GlazeID
        WHERE du.UnloadID IS NULL AND dl.IsUnloaded = 0
    """)
    occupied = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(occupied)

@app.route('/api/dryer/unload', methods=['POST'])
def record_unload():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        op_val = data.get('operator_id')
        op_id = None
        try:
            op_id = int(op_val)
        except Exception:
            op_id = resolve_user_id(cursor, op_val)
        cursor.execute("""
            INSERT INTO DryerUnloading(
                LoadID, UnloadDateJalali, UnloadTime, UnloadOperatorID, FingerCount, UnloadTimestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['load_id'],
            normalize_jalali_date(data['unload_date_jalali']),
            data['unload_time'],
            op_id or data['operator_id'],
            data['finger_count'],
            datetime.now()
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/unload-history', methods=['GET'])
def get_unload_history():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            du.UnloadID as id,
            dl.ChamberNo as chamber,
            CASE 
              WHEN c.CategoryName IS NULL OR TRIM(c.CategoryName) = ''
              THEN m.MoldName || ' ' || g.GlazeName
              ELSE c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName
            END AS product,
            du.UnloadDateJalali as date,
            du.UnloadTime as time,
            du.FingerCount as finger,
            COALESCE(u.FullName, u.Username) as operator,
            du.UnloadOperatorID as operator_id
        FROM DryerUnloading du
        LEFT JOIN DryerLoading dl ON du.LoadID = dl.LoadID
        LEFT JOIN Categories c ON c.CategoryID = dl.CategoryID
        LEFT JOIN Molds m ON m.MoldID = dl.MoldID
        LEFT JOIN Glazes g ON g.GlazeID = dl.GlazeID
        LEFT JOIN Users u ON du.UnloadOperatorID = u.UserID
        ORDER BY du.UnloadTimestamp DESC
        LIMIT 20
    """)
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(history)

@app.route('/api/dryer/update_unload', methods=['POST'])
def update_dryer_unload():
    data = request.json
    if not data or 'unload_id' not in data:
        return jsonify({'error': 'Unload ID is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        fields = []
        values = []
        
        if 'unload_date_jalali' in data:
            fields.append("UnloadDateJalali = ?")
            values.append(normalize_jalali_date(data['unload_date_jalali']))
        if 'unload_time' in data:
            fields.append("UnloadTime = ?")
            values.append(data['unload_time'])
        if 'finger_count' in data:
            fields.append("FingerCount = ?")
            values.append(data['finger_count'])
        if 'operator_id' in data:
            fields.append("UnloadOperatorID = ?")
            values.append(data['operator_id'])
            
        if not fields:
            return jsonify({'success': True, 'message': 'No changes provided'})
            
        values.append(data['unload_id'])
        query = f"UPDATE DryerUnloading SET {', '.join(fields)} WHERE UnloadID = ?"
        
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/unload-and-setting', methods=['POST'])
def dryer_unload_and_setting():
    data = request.json or {}
    chamber_no = int(data.get('chamber_no') or 0)
    load_id = int(data.get('load_id') or 0)
    unload_date = normalize_jalali_date(data.get('unload_date_jalali') or '')
    unload_time = (data.get('unload_time') or '').strip()
    op_val = data.get('operator_id')
    setting_op_val = data.get('setting_operator_id')
    operator_id = None
    setting_operator_id = None
    unloaded_finger_count = int(data.get('unloaded_finger_count') or 0)
    dryer_waste = int(data.get('dryer_waste') or 0)
    wagons = data.get('wagons') or []
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_setting_tables()
        ensure_triple_product_schema()
        ensure_product_tables()
        operator_id = resolve_user_id(cursor, op_val)
        setting_operator_id = resolve_user_id(cursor, setting_op_val)
        if not load_id and chamber_no:
            cursor.execute("SELECT LoadID FROM DryerLoading WHERE ChamberNo = ? AND IsUnloaded = 0 ORDER BY LoadTimestamp DESC LIMIT 1", (chamber_no,))
            r = cursor.fetchone()
            load_id = int((r or {'LoadID': 0})['LoadID'])
        if not load_id:
            return jsonify({'error': 'Active load not found for chamber'}), 404
        cursor.execute("SELECT CategoryID, MoldID, GlazeID, FingerCount, COALESCE(LoadOperatorID, 0) AS LoadOperatorID, ChamberNo FROM DryerLoading WHERE LoadID = ?", (load_id,))
        _li = cursor.fetchone()
        li = dict(_li) if _li is not None else {}
        cat_id = int(li.get('CategoryID') or 0)
        mold_id = int(li.get('MoldID') or 0)
        base_glaze_id = int(li.get('GlazeID') or 0)
        loaded_fingers = int(li.get('FingerCount') or 0)
        chamber_no = int(li.get('ChamberNo') or chamber_no or 0)
        if operator_id is None or int(operator_id or 0) <= 0:
            operator_id = int(li.get('LoadOperatorID') or 0)
        if operator_id is None or int(operator_id or 0) <= 0:
            return jsonify({'error': 'Valid operator is required'}), 400
        if setting_operator_id is None or int(setting_operator_id or 0) <= 0:
            return jsonify({'error': 'Valid setting operator is required'}), 400
        if not unloaded_finger_count and loaded_fingers:
            unloaded_finger_count = loaded_fingers
        if not dryer_waste and loaded_fingers and unloaded_finger_count >= 0:
            dryer_waste = max(0, loaded_fingers - unloaded_finger_count)
        cursor.execute("""
            INSERT INTO DryerUnloading(
                LoadID, UnloadDateJalali, UnloadTime, UnloadOperatorID, FingerCount, UnloadTimestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (load_id, unload_date, unload_time, operator_id, unloaded_finger_count, datetime.now()))
        conn.commit()
        cursor.execute("UPDATE DryerLoading SET IsUnloaded = 1 WHERE LoadID = ?", (load_id,))
        conn.commit()
        shift_id = resolve_shift_id(cursor)
        cursor.execute("""
            INSERT INTO SettingProcesses(
              SettingDateJalali, ShiftID, SupervisorID, OperatorID, PersonnelCount,
              ChamberNo, CategoryID, FingersCount, ColumnsCount, DryerWaste, Notes
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (unload_date, shift_id, operator_id, setting_operator_id, 0, chamber_no, cat_id, unloaded_finger_count, 0, dryer_waste, ''))
        batch_id = cursor.lastrowid
        conn.commit()
        for w in (wagons if isinstance(wagons, list) else []):
            wagon_order = int(w.get('wagon_order') or 0)
            wagon_no = int(w.get('wagon_no') or 0)
            glaze_id = w.get('glaze_id')
            try:
                glaze_id = int(glaze_id) if glaze_id is not None else base_glaze_id
            except Exception:
                glaze_id = base_glaze_id
            extra_code = normalize_extra_code((w.get('extra_code') or '').strip())
            start_time = (w.get('start_time') or '').strip() or None
            end_time = (w.get('end_time') or '').strip() or None
            packages = int(w.get('packages') or 0)
            if wagon_order < 1 or wagon_order > 4 or wagon_no <= 0:
                continue
            cursor.execute("""
                SELECT ProductID FROM Products
                WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                LIMIT 1
            """, (cat_id, mold_id, glaze_id, extra_code))
            found = cursor.fetchone()
            if not found:
                cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, ?, 1)", (cat_id, mold_id, glaze_id, extra_code))
                conn.commit()
                cursor.execute("""
                    SELECT ProductID FROM Products
                    WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                    ORDER BY ProductID DESC LIMIT 1
                """, (cat_id, mold_id, glaze_id, extra_code))
                found = cursor.fetchone()
            product_id = int((found or {'ProductID': 0})['ProductID'])
            cursor.execute("""
                INSERT INTO SettingWagons(
                  SettingID, WagonOrder, WagonNo, ProductID,
                  GlazeOverride, StartTime, EndTime, Packages, Notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (batch_id, wagon_order, wagon_no, product_id, None, start_time, end_time, packages, None))
        conn.commit()
        return jsonify({'success': True, 'batch_id': batch_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/dryer/delete_load', methods=['POST'])
def delete_dryer_load():
    data = request.json or {}
    lid = data.get('load_id')
    try:
        lid = int(lid)
    except Exception:
        return jsonify({'error': 'Valid Load ID is required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM DryerUnloading WHERE LoadID = ? LIMIT 1", (lid,))
        if cursor.fetchone():
            return jsonify({'error': 'Cannot delete: unload record exists for this load'}), 409
        cursor.execute("DELETE FROM DryerLoading WHERE LoadID = ?", (lid,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/latest', methods=['GET'])
def setting_latest():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              s.SettingID,
              s.SettingDateJalali,
              s.ChamberNo,
              s.CategoryID,
              s.FingersCount,
              s.DryerWaste,
              s.OperatorID,
              COALESCE(u.FullName, u.Username) AS OperatorName
            FROM SettingProcesses s
            LEFT JOIN Users u ON u.UserID = s.OperatorID
            ORDER BY s.SettingID DESC
            LIMIT 1
        """)
        srow = cursor.fetchone()
        if not srow:
            return jsonify({'exists': False})
        sid = srow['SettingID']
        chamber = srow['ChamberNo']
        cursor.execute("""
            SELECT du.UnloadID, du.UnloadDateJalali, du.UnloadTime
            FROM DryerUnloading du
            JOIN DryerLoading dl ON dl.LoadID = du.LoadID
            WHERE dl.ChamberNo = ?
            ORDER BY du.UnloadTimestamp DESC, du.UnloadID DESC
            LIMIT 1
        """, (chamber,))
        ul = cursor.fetchone()
        cursor.execute("""
            SELECT 
              w.WagonID,
              w.WagonOrder,
              w.WagonNo,
              w.ProductID,
              p.ProductName,
              p.GlazeID,
              p.ExtraCode,
              w.StartTime,
              w.EndTime,
              w.Packages
            FROM SettingWagons w
            LEFT JOIN Products p ON p.ProductID = w.ProductID
            WHERE w.SettingID = ?
            ORDER BY w.WagonOrder
        """, (sid,))
        wagons = [dict(r) for r in cursor.fetchall()]
        setting = dict(srow)
        if ul:
            setting.update({'UnloadID': ul['UnloadID'], 'UnloadTime': ul['UnloadTime'], 'UnloadDateJalali': ul['UnloadDateJalali']})
        return jsonify({'exists': True, 'setting': setting, 'wagons': wagons})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/by_chamber', methods=['GET'])
def setting_by_chamber():
    chamber_param = (request.args.get('chamber_no') or '').strip()
    try:
        chamber_no = int(chamber_param)
    except Exception:
        chamber_no = 0
    if chamber_no <= 0:
        return jsonify({'error': 'Invalid chamber_no'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              s.SettingID,
              s.SettingDateJalali,
              s.ChamberNo,
              s.CategoryID,
              s.FingersCount,
              s.DryerWaste,
              s.OperatorID,
              COALESCE(u.FullName, u.Username) AS OperatorName
            FROM SettingProcesses s
            LEFT JOIN Users u ON u.UserID = s.OperatorID
            WHERE s.ChamberNo = ?
            ORDER BY s.CreatedAt DESC, s.SettingID DESC
            LIMIT 1
        """, (chamber_no,))
        srow = cursor.fetchone()
        if not srow:
            return jsonify({'exists': False})
        sid = srow['SettingID']
        cursor.execute("""
            SELECT 
              w.WagonID,
              w.WagonOrder,
              w.WagonNo,
              w.ProductID,
              p.ProductName,
              w.StartTime,
              w.EndTime,
              w.Packages
            FROM SettingWagons w
            LEFT JOIN Products p ON p.ProductID = w.ProductID
            WHERE w.SettingID = ?
            ORDER BY w.WagonOrder
        """, (sid,))
        wagons = [dict(r) for r in cursor.fetchall()]
        try:
            for w in wagons:
                pid = w.get('ProductID')
                if pid:
                    cursor.execute("SELECT GlazeID, ExtraCode FROM Products WHERE ProductID = ?", (pid,))
                    pr = cursor.fetchone()
                    if pr:
                        w['GlazeID'] = pr['GlazeID']
                        w['ExtraCode'] = pr['ExtraCode']
        except Exception:
            pass
        setting = dict(srow)
        cursor.execute("""
            SELECT du.UnloadID, du.UnloadDateJalali, du.UnloadTime
            FROM DryerUnloading du
            JOIN DryerLoading dl ON dl.LoadID = du.LoadID
            WHERE dl.ChamberNo = ?
            ORDER BY du.UnloadTimestamp DESC, du.UnloadID DESC
            LIMIT 1
        """, (chamber_no,))
        ul = cursor.fetchone()
        if ul:
            setting.update({'UnloadID': ul['UnloadID'], 'UnloadTime': ul['UnloadTime'], 'UnloadDateJalali': ul['UnloadDateJalali']})
        return jsonify({'exists': True, 'setting': setting, 'wagons': wagons})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/setting/by_id', methods=['GET'])
def setting_by_id():
    setting_id_param = (request.args.get('setting_id') or '').strip()
    try:
        setting_id = int(setting_id_param)
    except Exception:
        setting_id = 0
    if setting_id <= 0:
        return jsonify({'error': 'Invalid setting_id'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              s.SettingID,
              s.SettingDateJalali,
              s.ChamberNo,
              s.CategoryID,
              s.FingersCount,
              s.DryerWaste,
              s.OperatorID,
              COALESCE(u.FullName, u.Username) AS OperatorName,
              p.ProductName
            FROM SettingProcesses s
            LEFT JOIN Users u ON u.UserID = s.OperatorID
            LEFT JOIN (
              SELECT sw.SettingID, p2.ProductName
              FROM SettingWagons sw
              LEFT JOIN Products p2 ON p2.ProductID = sw.ProductID
              WHERE sw.SettingID = ?
              LIMIT 1
            ) p ON p.SettingID = s.SettingID
            WHERE s.SettingID = ?
        """, (setting_id, setting_id))
        srow = cursor.fetchone()
        if not srow:
            return jsonify({'exists': False})
        sid = srow['SettingID']
        chamber = srow['ChamberNo']
        cursor.execute("""
            SELECT 
              w.WagonID,
              w.WagonOrder,
              w.WagonNo,
              w.ProductID,
              p.ProductName,
              p.GlazeID,
              p.ExtraCode,
              w.StartTime,
              w.EndTime,
              w.Packages
            FROM SettingWagons w
            LEFT JOIN Products p ON p.ProductID = w.ProductID
            WHERE w.SettingID = ?
            ORDER BY w.WagonOrder
        """, (sid,))
        wagons = [dict(r) for r in cursor.fetchall()]
        setting = dict(srow)
        cursor.execute("""
            SELECT du.UnloadID, du.UnloadDateJalali, du.UnloadTime
            FROM DryerUnloading du
            JOIN DryerLoading dl ON dl.LoadID = du.LoadID
            WHERE dl.ChamberNo = ?
            ORDER BY du.UnloadTimestamp DESC, du.UnloadID DESC
            LIMIT 1
        """, (chamber,))
        ul = cursor.fetchone()
        if ul:
            setting.update({'UnloadID': ul['UnloadID'], 'UnloadTime': ul['UnloadTime'], 'UnloadDateJalali': ul['UnloadDateJalali']})
        return jsonify({'exists': True, 'setting': setting, 'wagons': wagons})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/update', methods=['POST'])
def setting_update():
    data = request.json or {}
    sid = int(data.get('setting_id') or 0)
    fingers = data.get('fingers_count')
    waste = data.get('dryer_waste')
    sdate = data.get('setting_date_jalali')
    utime = (data.get('unload_time') or '').strip()
    unload_id = data.get('unload_id')
    wagons = data.get('wagons') or []
    conn = get_db()
    cursor = conn.cursor()
    try:
        if sid <= 0:
            return jsonify({'error': 'setting_id required'}), 400
        fields = []
        vals = []
        if sdate is not None:
            fields.append("SettingDateJalali = ?")
            vals.append(normalize_jalali_date(str(sdate)))
        if fingers is not None:
            fields.append("FingersCount = ?")
            vals.append(int(fingers))
        if waste is not None:
            fields.append("DryerWaste = ?")
            vals.append(int(waste))
        if fields:
            vals.append(sid)
            cursor.execute(f"UPDATE SettingProcesses SET {', '.join(fields)} WHERE SettingID = ?", tuple(vals))
        # Update unload time if provided
        if utime:
            uid = None
            try:
                uid = int(unload_id) if unload_id is not None else None
            except Exception:
                uid = None
            if uid is None or uid <= 0:
                cursor.execute("SELECT ChamberNo FROM SettingProcesses WHERE SettingID = ?", (sid,))
                r = cursor.fetchone()
                chamber = r and r['ChamberNo']
                if chamber:
                    cursor.execute("""
                        SELECT du.UnloadID
                        FROM DryerUnloading du
                        JOIN DryerLoading dl ON dl.LoadID = du.LoadID
                        WHERE dl.ChamberNo = ?
                        ORDER BY du.UnloadTimestamp DESC, du.UnloadID DESC
                        LIMIT 1
                    """, (chamber,))
                    rr = cursor.fetchone()
                    uid = rr and rr['UnloadID']
            if uid:
                cursor.execute("UPDATE DryerUnloading SET UnloadTime = ? WHERE UnloadID = ?", (utime, uid))
        for w in wagons:
            wid = int(w.get('wagon_id') or 0)
            if wid <= 0:
                continue
            st = (w.get('start_time') or '').strip() or None
            et = (w.get('end_time') or '').strip() or None
            pk = int(w.get('packages') or 0)
            cursor.execute("UPDATE SettingWagons SET StartTime = ?, EndTime = ?, Packages = ? WHERE WagonID = ?", (st, et, pk, wid))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/delete', methods=['POST'])
def setting_delete():
    data = request.json or {}
    sid = int(data.get('setting_id') or 0)
    if sid <= 0:
        return jsonify({'error': 'setting_id required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM SettingWagons WHERE SettingID = ?", (sid,))
        cursor.execute("DELETE FROM SettingProcesses WHERE SettingID = ?", (sid,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/delete_unload', methods=['POST'])
def delete_dryer_unload():
    data = request.json or {}
    uid = data.get('unload_id')
    try:
        uid = int(uid)
    except Exception:
        return jsonify({'error': 'Valid Unload ID is required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM DryerUnloading WHERE UnloadID = ?", (uid,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UserID as user_id, Username as username, FullName as full_name, IsActive as is_active FROM Users ORDER BY Username")
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify(users)
    finally:
        conn.close()

@app.route('/api/rpc/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Simple mock login - in production use real auth
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE Username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Here we should check password hash
        return jsonify({'token': 'mock-token-123', 'user': dict(user)})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

# -------- Setting (Production Batches & Wagons) API - No DB schema changes --------

def table_exists(cursor, table_name):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
    except Exception:
        return False

def get_product_name(cursor, product_id):
    try:
        cursor.execute("SELECT ProductName FROM Products WHERE ProductID = ?", (product_id,))
        r = cursor.fetchone()
        return r and r['ProductName']
    except Exception:
        return None

def resolve_user_id(cursor, value):
    try:
        if value is None:
            return None
        # Accept numeric id
        try:
            n = int(value)
            return n
        except Exception:
            pass
        cursor.execute("SELECT UserID FROM Users WHERE FullName = ? OR Username = ?", (value, value))
        r = cursor.fetchone()
        if r:
            return r['UserID']
        return None
    except Exception:
        return None
def ensure_operator_from_user(cursor, user_id, role):
    try:
        return user_id
    except Exception:
        return None
def resolve_shift_id(cursor):
    try:
        cursor.execute("SELECT ShiftID FROM ShiftsDefinition WHERE IsActive = 1 ORDER BY ShiftID LIMIT 1")
        r = cursor.fetchone()
        if r:
            return r['ShiftID']
        cursor.execute("INSERT INTO ShiftsDefinition(ShiftCode, ShiftName, IsActive) VALUES('D1','شیفت 1',1)")
        return cursor.lastrowid
    except Exception:
        return 1

def get_category_table_name(cursor):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Categories'")
        if cursor.fetchone():
            return 'Categories'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Category'")
        if cursor.fetchone():
            return 'Category'
    except Exception:
        pass
    return 'Categories'

def ensure_product_tables():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Categories'")
        if not cursor.fetchone():
            raise Exception('Required table Categories not found')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Molds'")
        if not cursor.fetchone():
            raise Exception('Required table Molds not found')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Glazes'")
        if not cursor.fetchone():
            raise Exception('Required table Glazes not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_triple_product_schema():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(DryerLoading)")
        cols = [r['name'] for r in cursor.fetchall()]
        if 'CategoryID' not in cols:
            cursor.execute("ALTER TABLE DryerLoading ADD COLUMN CategoryID INTEGER")
        if 'MoldID' not in cols:
            cursor.execute("ALTER TABLE DryerLoading ADD COLUMN MoldID INTEGER")
        if 'GlazeID' not in cols:
            cursor.execute("ALTER TABLE DryerLoading ADD COLUMN GlazeID INTEGER")
        cursor.execute("PRAGMA table_info(KilnPushData)")
        kcols = [r['name'] for r in cursor.fetchall()]
        if 'CategoryID' not in kcols:
            cursor.execute("ALTER TABLE KilnPushData ADD COLUMN CategoryID INTEGER")
        if 'MoldID' not in kcols:
            cursor.execute("ALTER TABLE KilnPushData ADD COLUMN MoldID INTEGER")
        if 'GlazeID' not in kcols:
            cursor.execute("ALTER TABLE KilnPushData ADD COLUMN GlazeID INTEGER")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='v_ProductDetails'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE VIEW v_ProductDetails AS
                SELECT 
                  CAST(c.CategoryID AS TEXT) || '-' || CAST(m.MoldID AS TEXT) || '-' || CAST(g.GlazeID AS TEXT) AS ProductComboID,
                  c.CategoryID, c.CategoryName,
                  m.MoldID, m.MoldName,
                  g.GlazeID, g.GlazeName,
                  c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName AS ProductName
                FROM Categories c
                CROSS JOIN Molds m
                CROSS JOIN Glazes g
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'GET':
            cursor.execute("SELECT CategoryID, CategoryCode, CategoryName, Description, IsActive FROM Categories ORDER BY CategoryCode")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('CategoryName') or data.get('category_name') or '').strip()
        desc = (data.get('Description') or data.get('description') or '').strip() or None
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        if not name:
            return jsonify({'error': 'CategoryName required'}), 400
        cursor.execute("SELECT COALESCE(MAX(CategoryID), 0) + 1 AS NextID FROM Categories")
        rr = cursor.fetchone()
        next_id = (rr and rr['NextID']) or 1
        code = f"C{int(next_id):03d}"
        cursor.execute("INSERT INTO Categories(CategoryCode, CategoryName, Description, IsActive) VALUES(?, ?, ?, ?)", (code, name, desc, is_active))
        conn.commit()
        return jsonify({'CategoryID': cursor.lastrowid, 'CategoryCode': code, 'CategoryName': name}), 201
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Duplicate or constraint violation'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/categories/<int:category_id>', methods=['PUT', 'DELETE'])
def category_update_delete(category_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM Categories WHERE CategoryID = ?", (category_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('CategoryName') or data.get('category_name') or '').strip()
        desc = (data.get('Description') or data.get('description') or '').strip() or None
        ia = data.get('IsActive') or data.get('is_active')
        sets = []
        params = []
        if name:
            sets.append("CategoryName = ?"); params.append(name)
        sets.append("Description = ?"); params.append(desc)
        if ia is not None:
            sets.append("IsActive = ?"); params.append(int(ia))
        sql = f"UPDATE Categories SET {', '.join(sets)} WHERE CategoryID = ?"
        params.append(category_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products-with-categories', methods=['GET'])
def products_with_categories():
    return jsonify({'error': 'Endpoint deprecated in simplified schema'}), 410

@app.route('/api/product-categories/<product_code>', methods=['POST'])
def product_categories_map(product_code: str):
    return jsonify({'error': 'Endpoint deprecated in simplified schema'}), 410

@app.route('/api/product-categories/<product_code>/<int:category_id>', methods=['DELETE'])
def product_categories_unmap(product_code: str, category_id: int):
    return jsonify({'error': 'Endpoint deprecated in simplified schema'}), 410

@app.route('/api/product-categories/<int:product_code>', methods=['POST'])
def assign_product_category(product_code: int):
    return jsonify({'error': 'Endpoint deprecated in simplified schema'}), 410

@app.route('/api/product-categories/<int:product_code>/<int:category_id>', methods=['DELETE'])
def remove_product_category(product_code: int, category_id: int):
    return jsonify({'error': 'Endpoint deprecated in simplified schema'}), 410

@app.route('/api/shifts/options', methods=['GET'])
def get_shift_options():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ShiftID AS shift_id, ShiftCode AS shift_code, ShiftName AS shift_name, StartTime AS start_time, EndTime AS end_time FROM ShiftsDefinition WHERE IsActive = 1 ORDER BY ShiftCode")
        rows = [dict(row) for row in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/glazes', methods=['GET'])
def list_glazes():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        cursor.execute("SELECT GlazeID, GlazeName FROM Glazes ORDER BY GlazeName")
        return jsonify([dict(r) for r in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/molds', methods=['GET'])
def list_molds():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        cursor.execute("SELECT MoldID, MoldName FROM Molds ORDER BY MoldName")
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


def ensure_setting_tables():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ('SettingProcesses',))
        if not cursor.fetchone():
            raise Exception('Required table SettingProcesses not found')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ('SettingWagons',))
        if not cursor.fetchone():
            raise Exception('Required table SettingWagons not found')
    except Exception:
        raise
    finally:
        conn.close()

def ensure_kiln_tables():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ('FuelTypes',))
        if not cursor.fetchone():
            raise Exception('Required table FuelTypes not found')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ('KilnPushData',))
        if not cursor.fetchone():
            raise Exception('Required table KilnPushData not found')
    except Exception:
        raise
    finally:
        conn.close()

def ensure_admin_tables():
    conn = get_db()
    cursor = conn.cursor()
    try:
        required_tables = ['Users', 'Roles', 'UserRoles', 'ShiftsDefinition', 'Pages', 'RolePageAccess']
        for t in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
            if not cursor.fetchone():
                raise Exception(f"Required table {t} not found")
    except Exception:
        raise
    finally:
        conn.close()

@app.route('/api/admin/shifts', methods=['GET', 'POST'])
def admin_shifts():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'GET':
            cursor.execute("SELECT ShiftID, ShiftCode, ShiftName, StartTime, EndTime, IsActive FROM ShiftsDefinition ORDER BY ShiftCode")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('ShiftName') or data.get('shift_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        start_time = (data.get('StartTime') or data.get('start_time') or '').strip() or None
        end_time = (data.get('EndTime') or data.get('end_time') or '').strip() or None
        if not name:
            return jsonify({'error': 'ShiftName required'}), 400
        cursor.execute("SELECT 1 FROM ShiftsDefinition WHERE ShiftName = ? COLLATE NOCASE", (name,))
        if cursor.fetchone():
            return jsonify({'error': 'Duplicate shift name'}), 409
        cursor.execute("SELECT COALESCE(MAX(ShiftID), 0) + 1 AS NextID FROM ShiftsDefinition")
        rr = cursor.fetchone()
        next_id = (rr and rr['NextID']) or 1
        code = f"S{int(next_id):02d}"
        cursor.execute("INSERT INTO ShiftsDefinition(ShiftCode, ShiftName, IsActive, StartTime, EndTime) VALUES(?, ?, ?, ?, ?)", (code, name, is_active, start_time, end_time))
        sid = cursor.lastrowid
        conn.commit()
        return jsonify({'shift_id': sid, 'shift_code': code}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/shifts/<int:shift_id>', methods=['PUT', 'DELETE'])
def admin_shift_update(shift_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM ShiftsDefinition WHERE ShiftID = ?", (shift_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('ShiftName') or data.get('shift_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        start_time = (data.get('StartTime') or data.get('start_time') or '').strip() or None
        end_time = (data.get('EndTime') or data.get('end_time') or '').strip() or None
        if not name:
            return jsonify({'error': 'ShiftName required'}), 400
        cursor.execute("SELECT 1 FROM ShiftsDefinition WHERE ShiftID <> ? AND ShiftName = ? COLLATE NOCASE", (shift_id, name))
        if cursor.fetchone():
            return jsonify({'error': 'Duplicate shift name'}), 409
        cursor.execute("UPDATE ShiftsDefinition SET ShiftName = ?, IsActive = ?, StartTime = ?, EndTime = ? WHERE ShiftID = ?", (name, is_active, start_time, end_time, shift_id))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/fuel-types', methods=['GET', 'POST'])
def admin_fuel_types():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_kiln_tables()
        if request.method == 'GET':
            cursor.execute("SELECT FuelTypeID, FuelName, IsActive FROM FuelTypes ORDER BY FuelName")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('FuelName') or data.get('fuel_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        if not name:
            return jsonify({'error': 'FuelName required'}), 400
        cursor.execute("INSERT INTO FuelTypes(FuelName, IsActive) VALUES(?, ?)", (name, is_active))
        conn.commit()
        return jsonify({'fuel_type_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/glazes', methods=['GET', 'POST'])
def admin_glazes():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'GET':
            cursor.execute("SELECT GlazeID, GlazeCode, GlazeName, IsGlazed, IsActive FROM Glazes ORDER BY GlazeName")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('GlazeName') or data.get('glaze_name') or '').strip()
        _is_glazed = data.get('IsGlazed')
        if _is_glazed is None:
            _is_glazed = data.get('is_glazed')
        is_glazed = int(_is_glazed) if _is_glazed is not None else 1
        _is_active = data.get('IsActive')
        if _is_active is None:
            _is_active = data.get('is_active')
        is_active = int(_is_active) if _is_active is not None else 1
        if not name:
            return jsonify({'error': 'GlazeName required'}), 400
        cursor.execute("SELECT COALESCE(MAX(GlazeID), 0) + 1 AS next_id FROM Glazes")
        next_id = (cursor.fetchone() or {'next_id': 1})['next_id']
        glaze_code = f"G{int(next_id):03d}"
        cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsGlazed, IsActive) VALUES(?, ?, ?, ?)", (glaze_code, name, is_glazed, is_active))
        conn.commit()
        return jsonify({'glaze_id': cursor.lastrowid, 'GlazeCode': glaze_code}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/glazes/<int:glaze_id>', methods=['PUT', 'DELETE'])
def admin_glaze_update(glaze_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM Glazes WHERE GlazeID = ?", (glaze_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('GlazeName') or data.get('glaze_name') or '').strip()
        has_is_glazed = ('IsGlazed' in data) or ('is_glazed' in data)
        has_is_active = ('IsActive' in data) or ('is_active' in data)
        is_glazed = data.get('IsGlazed', data.get('is_glazed'))
        is_active = data.get('IsActive', data.get('is_active'))
        sets = []
        params = []
        if name:
            sets.append("GlazeName = ?"); params.append(name)
        if has_is_glazed and is_glazed is not None:
            sets.append("IsGlazed = ?"); params.append(int(is_glazed))
        if has_is_active and is_active is not None:
            sets.append("IsActive = ?"); params.append(int(is_active))
        if not sets:
            return jsonify({'updated': False})
        sql = f"UPDATE Glazes SET {', '.join(sets)} WHERE GlazeID = ?"
        params.append(glaze_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/molds', methods=['GET', 'POST'])
def admin_molds():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'GET':
            cursor.execute("SELECT MoldID, MoldCode, MoldName, IsActive FROM Molds ORDER BY MoldName")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('MoldName') or data.get('mold_name') or '').strip()
        _is_active = data.get('IsActive')
        if _is_active is None:
            _is_active = data.get('is_active')
        is_active = int(_is_active) if _is_active is not None else 1
        if not name:
            return jsonify({'error': 'MoldName required'}), 400
        cursor.execute("SELECT COALESCE(MAX(MoldID), 0) + 1 AS next_id FROM Molds")
        next_id = (cursor.fetchone() or {'next_id': 1})['next_id']
        mold_code = f"M{int(next_id):03d}"
        cursor.execute("INSERT INTO Molds(MoldCode, MoldName, IsActive) VALUES(?, ?, ?)", (mold_code, name, is_active))
        conn.commit()
        return jsonify({'mold_id': cursor.lastrowid, 'MoldCode': mold_code}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/molds/<int:mold_id>', methods=['PUT', 'DELETE'])
def admin_mold_update(mold_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM Molds WHERE MoldID = ?", (mold_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('MoldName') or data.get('mold_name') or '').strip()
        has_is_active = ('IsActive' in data) or ('is_active' in data)
        is_active = data.get('IsActive', data.get('is_active'))
        sets = []
        params = []
        if name:
            sets.append("MoldName = ?"); params.append(name)
        if has_is_active and is_active is not None:
            sets.append("IsActive = ?"); params.append(int(is_active))
        if not sets:
            return jsonify({'updated': False})
        sql = f"UPDATE Molds SET {', '.join(sets)} WHERE MoldID = ?"
        params.append(mold_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/fuel-types/<int:fuel_id>', methods=['PUT', 'DELETE'])
def admin_fuel_update(fuel_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_kiln_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM FuelTypes WHERE FuelTypeID = ?", (fuel_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('FuelName') or data.get('fuel_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        cursor.execute("UPDATE FuelTypes SET FuelName = ?, IsActive = ? WHERE FuelTypeID = ?", (name or None, is_active, fuel_id))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/users', methods=['GET', 'POST'])
def admin_users():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'GET':
            cursor.execute("SELECT UserID, Username, FullName, IsActive FROM Users ORDER BY Username")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        username = (data.get('Username') or data.get('username') or '').strip()
        full_name = (data.get('FullName') or data.get('full_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        if not username:
            return jsonify({'error': 'Username required'}), 400
        cursor.execute("INSERT INTO Users(Username, FullName, IsActive) VALUES(?, ?, ?)", (username, full_name or None, is_active))
        conn.commit()
        return jsonify({'user_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/users/<int:user_id>', methods=['PUT', 'DELETE'])
def admin_user_update(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM Users WHERE UserID = ?", (user_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        username = (data.get('Username') or data.get('username') or '').strip()
        full_name = (data.get('FullName') or data.get('full_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        cursor.execute("UPDATE Users SET Username = ?, FullName = ?, IsActive = ? WHERE UserID = ?", (username or None, full_name or None, is_active, user_id))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/roles', methods=['GET', 'POST'])
def admin_roles():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'GET':
            cursor.execute("SELECT RoleID, RoleName, IsActive FROM Roles ORDER BY RoleName")
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        name = (data.get('RoleName') or data.get('role_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        if not name:
            return jsonify({'error': 'RoleName required'}), 400
        cursor.execute("INSERT INTO Roles(RoleName, IsActive) VALUES(?, ?)", (name, is_active))
        conn.commit()
        return jsonify({'role_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/roles/<int:role_id>', methods=['PUT', 'DELETE'])
def admin_role_update(role_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM Roles WHERE RoleID = ?", (role_id,))
            conn.commit()
            return jsonify({'deleted': True})
        data = request.json or {}
        name = (data.get('RoleName') or data.get('role_name') or '').strip()
        is_active = int(data.get('IsActive') or data.get('is_active') or 1)
        cursor.execute("UPDATE Roles SET RoleName = ?, IsActive = ? WHERE RoleID = ?", (name or None, is_active, role_id))
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/user-roles/<int:user_id>', methods=['GET', 'POST'])
def admin_user_roles(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'GET':
            cursor.execute("SELECT RoleID FROM UserRoles WHERE UserID = ?", (user_id,))
            return jsonify([r['RoleID'] for r in cursor.fetchall()])
        data = request.json or {}
        roles = data.get('role_ids') or []
        cursor.execute("DELETE FROM UserRoles WHERE UserID = ?", (user_id,))
        for rid in roles:
            try:
                cursor.execute("INSERT OR IGNORE INTO UserRoles(UserID, RoleID) VALUES(?, ?)", (user_id, int(rid)))
            except Exception:
                pass
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/pages', methods=['GET'])
def admin_pages():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        cursor.execute("SELECT PageID, PageKey, PageTitle, IsActive FROM Pages ORDER BY PageTitle")
        return jsonify([dict(r) for r in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/role-access/<int:role_id>', methods=['GET', 'POST'])
def admin_role_access(role_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        if request.method == 'GET':
            cursor.execute("""
                SELECT p.PageID, p.PageKey, p.PageTitle,
                       CASE WHEN rpa.PageID IS NOT NULL THEN 1 ELSE 0 END AS Allowed
                FROM Pages p
                LEFT JOIN RolePageAccess rpa ON rpa.PageID = p.PageID AND rpa.RoleID = ?
                ORDER BY p.PageTitle
            """, (role_id,))
            return jsonify([dict(r) for r in cursor.fetchall()])
        data = request.json or {}
        page_ids = data.get('page_ids') or []
        cursor.execute("DELETE FROM RolePageAccess WHERE RoleID = ?", (role_id,))
        for pid in page_ids:
            try:
                cursor.execute("INSERT OR IGNORE INTO RolePageAccess(RoleID, PageID) VALUES(?, ?)", (role_id, int(pid)))
            except Exception:
                pass
        conn.commit()
        return jsonify({'updated': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/admin/user-allowed-pages/<int:user_id>', methods=['GET'])
def admin_user_allowed_pages(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_admin_tables()
        cursor.execute("""
            SELECT p.PageID, p.PageKey, p.PageTitle,
                   CASE WHEN EXISTS(
                        SELECT 1
                        FROM RolePageAccess rpa
                        JOIN UserRoles ur ON ur.RoleID = rpa.RoleID
                        WHERE ur.UserID = ?
                          AND rpa.PageID = p.PageID
                   ) THEN 1 ELSE 0 END AS Allowed
            FROM Pages p
            ORDER BY p.PageTitle
        """, (user_id,))
        return jsonify([dict(r) for r in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/batch', methods=['POST'])
def create_setting_batch():
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_setting_tables()
        setting_date = normalize_jalali_date(data.get('setting_date') or data.get('date_jalali') or '')
        shift = int(data.get('shift') or 0)
        sv = resolve_user_id(cursor, data.get('supervisor'))
        op = resolve_user_id(cursor, data.get('operator'))
        supervisor = int(sv or 0)
        operator = int(op or 0)
        personnel = int(data.get('personnel_count') or 0)
        chamber = int(data.get('chamber_no') or 0)
        product_id = int(data.get('product_id') or 0)
        category_id = data.get('category_id')
        try:
            category_id = int(category_id) if category_id is not None else None
        except Exception:
            category_id = None
        if (category_id is None or category_id == 0):
            try:
                cursor.execute("""
                    SELECT p.CategoryID
                    FROM DryerLoading dl
                    LEFT JOIN Products p ON p.ProductID = dl.ProductID
                    WHERE dl.ChamberNo = ? AND dl.IsUnloaded = 0
                    ORDER BY dl.LoadTimestamp DESC
                    LIMIT 1
                """, (chamber,))
                rr = cursor.fetchone()
                if rr and rr['CategoryID'] is not None:
                    category_id = int(rr['CategoryID'])
            except Exception:
                pass
        if category_id is None:
            category_id = 0
        fingers = int(data.get('fingers_count') or 0)
        columns = int(data.get('columns_count') or 0)
        waste = int(data.get('dryer_waste') or data.get('waste_count') or 0)
        notes = (data.get('notes') or '').strip()
        if not (setting_date and shift in (1,2,3) and chamber > 0 and category_id >= 0):
            return jsonify({'error': 'Missing required fields'}), 400
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
        except Exception:
            pass
        cursor.execute("""
            INSERT INTO SettingProcesses(
              SettingDateJalali, ShiftID, SupervisorID, OperatorID, PersonnelCount,
              ChamberNo, CategoryID, FingersCount, ColumnsCount, DryerWaste, Notes
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            setting_date, shift, supervisor, operator, personnel,
            chamber, category_id, fingers, columns, waste, notes
        ))
        conn.commit()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        return jsonify({'batch_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/setting/batch/<int:batch_id>/wagons', methods=['POST'])
def add_setting_wagons(batch_id: int):
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_setting_tables()
        # Accept single wagon or array
        wagons = data if isinstance(data, list) else [data]
        inserted = 0
        for w in wagons:
            wagon_order = int(w.get('wagon_order') or 0)
            wagon_no = int(w.get('wagon_no') or 0)
            product_id = w.get('product_id')
            try:
                if product_id is not None:
                    product_id = int(product_id)
            except Exception:
                pass
            if not product_id:
                cat_id = w.get('category_id')
                mold_id = w.get('mold_id')
                glaze_id = w.get('glaze_id')
                extra_code = normalize_extra_code((w.get('extra_code') or '').strip())
                try:
                    cat_id = int(cat_id) if cat_id is not None else None
                    mold_id = int(mold_id) if mold_id is not None else None
                    glaze_id = int(glaze_id) if glaze_id is not None else None
                except Exception:
                    cat_id = None; mold_id = None; glaze_id = None
                if not (cat_id and mold_id and glaze_id is not None):
                    return jsonify({'error': 'Missing product fields; provide product_id or category_id, mold_id, glaze_id'}), 400
                cursor.execute("""
                    SELECT ProductID FROM Products
                    WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                    LIMIT 1
                """, (cat_id, mold_id, glaze_id, extra_code))
                found = cursor.fetchone()
                if not found:
                    cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, ?, 1)", (cat_id, mold_id, glaze_id, extra_code))
                    conn.commit()
                    cursor.execute("""
                        SELECT ProductID FROM Products
                        WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                        ORDER BY ProductID DESC LIMIT 1
                    """, (cat_id, mold_id, glaze_id, extra_code))
                    found = cursor.fetchone()
                product_id = int((found or {'ProductID': 0})['ProductID'])
            glaze_override = (w.get('glaze_override') or w.get('glaze_type') or '').strip() or None
            start_time = (w.get('start_time') or '').strip() or None
            end_time = (w.get('end_time') or '').strip() or None
            packages = int(w.get('packages') or 0)
            notes = (w.get('notes') or '').strip() or None
            if wagon_order < 1 or wagon_order > 4:
                return jsonify({'error': 'wagon_order must be between 1 and 4'}), 400
            if wagon_no <= 0 or not product_id:
                return jsonify({'error': 'Missing wagon_no or product_id'}), 400
            cursor.execute("""
                INSERT INTO SettingWagons(
                  SettingID, WagonOrder, WagonNo, ProductID,
                  GlazeOverride, StartTime, EndTime, Packages, Notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id, wagon_order, wagon_no, product_id,
                glaze_override, start_time, end_time, packages, notes
            ))
            inserted += 1
        conn.commit()
        return jsonify({'inserted': inserted}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/fuel-types', methods=['GET'])
def list_fuel_types():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT FuelTypeID, FuelName, IsActive FROM FuelTypes WHERE IsActive = 1 ORDER BY FuelName")
        return jsonify([dict(r) for r in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/kiln/push', methods=['POST'])
def kiln_push_create():
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_kiln_tables()
        ensure_triple_product_schema()
        dt = normalize_jalali_date(data.get('push_date_jalali') or '')
        tm = (data.get('push_time') or '').strip()
        ts = (data.get('push_timestamp') or '').strip()
        shift_id = int(data.get('shift_id') or 0)
        operator_id = int(data.get('operator_id') or 0)
        category_id = data.get('category_id')
        mold_id = data.get('mold_id')
        glaze_id = data.get('glaze_id')
        try:
            category_id = int(category_id) if category_id is not None else None
        except Exception:
            category_id = None
        try:
            mold_id = int(mold_id) if mold_id is not None else None
        except Exception:
            mold_id = None
        try:
            glaze_id = int(glaze_id) if glaze_id is not None else None
        except Exception:
            glaze_id = None
        incoming_car_id = int(data.get('incoming_car_id') or 0)
        fuel_type_id = data.get('fuel_type_id')
        try:
            fuel_type_id = int(fuel_type_id) if fuel_type_id is not None else None
        except Exception:
            fuel_type_id = None
        ptm = None
        if ts:
            ptm = ts
        elif dt and tm:
            ptm = f"{dt} {tm}"
        cursor.execute("""
            INSERT INTO KilnPushData(
                Timestamp, DateJalali, Time, ShiftID, OperatorID, CategoryID, MoldID, GlazeID,
                IncomingCarID, FuelTypeID, PushingTime_min,
                ExhaustTemp, Preheat1, Preheat2, Thermostat,
                Zone0, Zone1, Zone2, Zone3, Zone4, Zone5, Zone6, Zone7,
                Rapid1, Rapid2, BottomA, Bottom1, BottomB, Bottom2, Notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ptm, dt or None, tm or None, shift_id or None, operator_id or None, category_id, mold_id, glaze_id,
            incoming_car_id or None, fuel_type_id, None,
            data.get('temp_exhaust'), data.get('temp_preheat01'), data.get('temp_preheat02'), data.get('temp_thermostat'),
            data.get('temp_zone00'), data.get('temp_zone01'), data.get('temp_zone02'), data.get('temp_zone03'),
            data.get('temp_zone04'), data.get('temp_zone05'), data.get('temp_zone06'), data.get('temp_zone07'),
            data.get('temp_rapid01'), data.get('temp_rapid02'),
            data.get('temp_bottom_a'), data.get('temp_bottom01'), data.get('temp_bottom_b'), data.get('temp_bottom02'),
            (data.get('notes') or '').strip() or None
        ))
        conn.commit()
        return jsonify({'push_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/kiln/pushing/recent', methods=['GET'])
def kiln_pushing_recent():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_kiln_tables()
        cursor.execute("""
            SELECT 
              k.PushID, k.Timestamp, k.DateJalali, k.Time, k.ShiftID, k.OperatorID, k.CategoryID, k.MoldID, k.GlazeID, k.IncomingCarID, k.FuelTypeID,
              COALESCE(c.CategoryName || ' ' || m.MoldName || ' ' || g.GlazeName, pr.ProductName) AS ProductName, f.FuelName,
              COALESCE(u.FullName, u.Username) AS OperatorName
            FROM KilnPushData k
            LEFT JOIN Products pr ON k.ProductID = pr.ProductID
            LEFT JOIN Categories c ON c.CategoryID = COALESCE(k.CategoryID, pr.CategoryID)
            LEFT JOIN Molds m ON m.MoldID = COALESCE(k.MoldID, pr.MoldID)
            LEFT JOIN Glazes g ON g.GlazeID = COALESCE(k.GlazeID, pr.GlazeID)
            LEFT JOIN FuelTypes f ON k.FuelTypeID = f.FuelTypeID
            LEFT JOIN Users u ON k.OperatorID = u.UserID
            ORDER BY k.PushID DESC
            LIMIT 20
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        out = []
        for r in rows:
            out.append({
                'push_id': r.get('PushID'),
                'push_date_jalali': r.get('DateJalali'),
                'shift_id': r.get('ShiftID'),
                'operator_id': r.get('OperatorID'),
                'operator_name': r.get('OperatorName'),
                'product_name': r.get('ProductName'),
                'incoming_car_id': r.get('IncomingCarID'),
                'fuel_name': r.get('FuelName'),
                'push_timestamp': r.get('Timestamp') or r.get('Time')
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/kiln/last-push-info', methods=['GET'])
def kiln_last_push_info():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_kiln_tables()
        cursor.execute("SELECT * FROM KilnPushData ORDER BY PushID DESC LIMIT 1")
        r = cursor.fetchone()
        return jsonify({'last_push': dict(r) if r else None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/api/setting/transactions', methods=['GET'])
def list_setting_transactions():
    page = int((request.args.get('page') or 1))
    per_page = int((request.args.get('per_page') or 10))
    if per_page < 1: per_page = 10
    if per_page > 200: per_page = 200
    order = (request.args.get('order') or '').lower()
    order_dir = 'ASC' if order == 'asc' else 'DESC'
    date_filter = (request.args.get('date') or '').strip()
    chamber_filter = request.args.get('chamber')
    conditions = []
    params = []
    if date_filter:
        conditions.append("sp.SettingDateJalali = ?")
        params.append(date_filter)
    if chamber_filter:
        try:
            cno = int(chamber_filter)
            conditions.append("sp.ChamberNo = ?")
            params.append(cno)
        except Exception:
            pass
    conn = get_db()
    cursor = conn.cursor()
    try:
        if not table_exists(cursor, 'SettingWagons') or not table_exists(cursor, 'SettingProcesses'):
            return jsonify({'transactions': [], 'total_count': 0, 'total_pages': 1}), 200
        count_sql = "SELECT COUNT(DISTINCT sp.SettingID) AS c FROM SettingProcesses sp LEFT JOIN SettingWagons sw ON sw.SettingID = sp.SettingID"
        if conditions:
            count_sql += " WHERE " + " AND ".join(conditions)
        cursor.execute(count_sql, tuple(params))
        rc = cursor.fetchone()
        total_count = (rc['c'] if rc else 0)
        total_pages = (total_count // per_page) + (1 if total_count % per_page != 0 else 0)
        if total_pages == 0: total_pages = 1
        if page < 1: page = 1
        if page > total_pages: page = total_pages
        offset = (page - 1) * per_page
        select_sql = """
            SELECT
              sp.SettingID,
              sp.SettingDateJalali,
              sp.ChamberNo,
              sp.FingersCount,
              sp.DryerWaste,
              COALESCE(u.FullName, u.Username) AS OperatorName,
              sh.ShiftName,
              COUNT(sw.WagonID) AS WagonCount,
              GROUP_CONCAT(sw.WagonNo || ':' || COALESCE(g.GlazeName, '') || ':' || COALESCE(sw.Packages, 0)) AS WagonDetails,
              (
                SELECT p.ProductName
                FROM SettingWagons sw2
                LEFT JOIN Products p ON p.ProductID = sw2.ProductID
                WHERE sw2.SettingID = sp.SettingID
                ORDER BY sw2.WagonOrder
                LIMIT 1
              ) AS ProductName,
              (
                SELECT du.UnloadTime
                FROM DryerUnloading du
                JOIN DryerLoading dl ON dl.LoadID = du.LoadID
                WHERE dl.ChamberNo = sp.ChamberNo
                ORDER BY du.UnloadTimestamp DESC, du.UnloadID DESC
                LIMIT 1
              ) AS UnloadTime
            FROM SettingProcesses sp
            LEFT JOIN Users u ON u.UserID = sp.OperatorID
            LEFT JOIN SettingWagons sw ON sw.SettingID = sp.SettingID
            LEFT JOIN Products p ON p.ProductID = sw.ProductID
            LEFT JOIN Glazes g ON g.GlazeID = p.GlazeID
            LEFT JOIN ShiftsDefinition sh ON sh.ShiftID = sp.ShiftID
        """
        if conditions:
            select_sql += " WHERE " + " AND ".join(conditions)
        select_sql += f" GROUP BY sp.SettingID ORDER BY sp.SettingID {order_dir} LIMIT ? OFFSET ?"
        cursor.execute(select_sql, tuple(params + [per_page, offset]))
        out = []
        for r in cursor.fetchall():
            row = dict(r)
            wagon_details = row.get('WagonDetails') or ''
            formatted_wagons = []
            if wagon_details:
                # format: "No:Glaze:Packages,No:Glaze:Packages"
                parts = str(wagon_details).split(',')
                parsed = []
                for p in parts:
                    if not p.strip(): continue
                    sub = p.split(':')
                    wn = int(sub[0]) if sub[0].isdigit() else 0
                    gn = sub[1] if len(sub) > 1 else ''
                    pk = sub[2] if len(sub) > 2 else '0'
                    if wn:
                        parsed.append({'no': wn, 'glaze': gn, 'pk': pk})
                
                # Sort by Wagon Number
                parsed.sort(key=lambda x: x['no'])
                
                for item in parsed:
                    # Format: "1: Glaze (Pack)"
                    txt = f"{item['no']}"
                    if item['glaze']: txt += f": {item['glaze']}"
                    # if item['pk'] != '0': txt += f" ({item['pk']})"
                    formatted_wagons.append(txt)
            
            wagon_display = ' - '.join(formatted_wagons)
            
            out.append({
                'SettingID': row.get('SettingID'),
                'SettingDateJalali': row.get('SettingDateJalali') or '',
                'ChamberNo': row.get('ChamberNo'),
                'FingersCount': row.get('FingersCount') or 0,
                'DryerWaste': row.get('DryerWaste') or 0,
                'OperatorName': row.get('OperatorName') or '',
                'ShiftName': row.get('ShiftName') or '',
                'WagonCount': row.get('WagonCount') or 0,
                'WagonNos': wagon_display,
                'ProductName': row.get('ProductName') or '',
                'UnloadTime': row.get('UnloadTime') or ''
            })
        return jsonify({'transactions': out, 'total_count': total_count, 'total_pages': total_pages, 'page': page, 'per_page': per_page}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ---- Frontend alias endpoints to match web/app.js ----

@app.route('/api/dryer_chambers_status', methods=['GET'])
def alias_dryer_chambers_status():
    return get_chamber_status()

@app.route('/api/dryer_occupied', methods=['GET'])
def alias_dryer_occupied():
    return get_occupied_chambers()

@app.route('/api/dryer_history', methods=['GET'])
def alias_dryer_history():
    return get_dryer_history()

@app.route('/api/dryer_unload_history', methods=['GET'])
def alias_dryer_unload_history():
    return get_unload_history()

@app.route('/api/operators_dryer', methods=['GET'])
def alias_operators_dryer():
    return get_operators('dryer')

@app.route('/api/operators_kiln', methods=['GET'])
def alias_operators_kiln():
    return get_operators('kiln')

@app.route('/api/kiln_pushing_recent', methods=['GET'])
def alias_kiln_pushing_recent():
    return kiln_pushing_recent()

@app.route('/api/kiln_last_push_info', methods=['GET'])
def alias_kiln_last_push_info():
    return kiln_last_push_info()

@app.route('/api/rpc/kiln_push', methods=['POST'])
def alias_kiln_push():
    return kiln_push_create()

@app.route('/api/rpc/get_setting_transactions', methods=['GET'])
def alias_get_setting_transactions():
    return list_setting_transactions()

@app.route('/api/rpc/get_setting_details', methods=['GET'])
def get_setting_details():
    try:
        setting_id = int(request.args.get('setting_id') or 0)
        if not setting_id:
            return jsonify({'error': 'Missing setting_id'}), 400
        conn = get_db()
        cursor = conn.cursor()
        
        # Get Process
        cursor.execute("""
            SELECT 
                sp.*,
                sh.ShiftName,
                COALESCE(u.FullName, u.Username) as OperatorName
            FROM SettingProcesses sp
            LEFT JOIN ShiftsDefinition sh ON sh.ShiftID = sp.ShiftID
            LEFT JOIN Users u ON u.UserID = sp.OperatorID
            WHERE sp.SettingID = ?
        """, (setting_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Setting not found'}), 404
        setting = dict(row)
        
        # Get Wagons
        cursor.execute("""
            SELECT sw.*, g.GlazeID, g.GlazeName, p.MoldID, p.CategoryID as ProdCategoryID
            FROM SettingWagons sw
            LEFT JOIN Products p ON p.ProductID = sw.ProductID
            LEFT JOIN Glazes g ON g.GlazeID = p.GlazeID
            WHERE sw.SettingID = ?
            ORDER BY sw.WagonOrder
        """, (setting_id,))
        wagons = [dict(w) for w in cursor.fetchall()]
        
        # Infer MoldID from first wagon if not in setting (SettingProcesses doesn't store MoldID)
        if wagons and 'MoldID' not in setting:
            setting['MoldID'] = wagons[0]['MoldID']
        
        return jsonify({'setting': setting, 'wagons': wagons}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/rpc/update_setting_transaction', methods=['POST'])
def update_setting_transaction():
    conn = get_db()
    cursor = conn.cursor()
    try:
        data = request.json or {}
        setting_id = int(data.get('setting_id') or 0)
        if not setting_id:
            return jsonify({'error': 'Missing setting_id'}), 400
            
        # Update Process
        update_sql = """
            UPDATE SettingProcesses SET
                SettingDateJalali = ?,
                ShiftID = ?,
                SupervisorID = ?,
                OperatorID = ?,
                PersonnelCount = ?,
                ChamberNo = ?,
                CategoryID = ?,
                FingersCount = ?,
                ColumnsCount = ?,
                DryerWaste = ?,
                Notes = ?
            WHERE SettingID = ?
        """
        params = (
            data.get('setting_date'),
            data.get('shift'),
            data.get('supervisor'),
            data.get('operator'),
            data.get('personnel_count'),
            data.get('chamber_no'),
            data.get('category_id'),
            data.get('fingers_count'),
            data.get('columns_count'),
            data.get('waste_count'),
            data.get('notes'),
            setting_id
        )
        cursor.execute(update_sql, params)
        
        # Update Wagons (Delete and Re-insert)
        cursor.execute("DELETE FROM SettingWagons WHERE SettingID = ?", (setting_id,))
        
        wagons = data.get('wagons') or []
        for w in wagons:
            wagon_order = int(w.get('wagon_order') or 0)
            wagon_no = int(w.get('wagon_no') or 0)
            product_id = w.get('product_id')
            try:
                if product_id is not None:
                    product_id = int(product_id)
            except Exception:
                pass
            if not product_id:
                cat_id = w.get('category_id')
                mold_id = w.get('mold_id')
                glaze_id = w.get('glaze_id')
                extra_code = normalize_extra_code((w.get('extra_code') or '').strip())
                try:
                    cat_id = int(cat_id) if cat_id is not None else None
                    mold_id = int(mold_id) if mold_id is not None else None
                    glaze_id = int(glaze_id) if glaze_id is not None else None
                except Exception:
                    cat_id = None; mold_id = None; glaze_id = None
                
                # If we have category/mold/glaze, try to resolve ProductID
                if (cat_id is not None and mold_id is not None and glaze_id is not None):
                    cursor.execute("""
                        SELECT ProductID FROM Products
                        WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                        LIMIT 1
                    """, (cat_id, mold_id, glaze_id, extra_code))
                    found = cursor.fetchone()
                    if not found:
                        cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, ?, 1)", (cat_id, mold_id, glaze_id, extra_code))
                        conn.commit()
                        cursor.execute("""
                            SELECT ProductID FROM Products
                            WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = COALESCE(?, '')
                            ORDER BY ProductID DESC LIMIT 1
                        """, (cat_id, mold_id, glaze_id, extra_code))
                        found = cursor.fetchone()
                    product_id = int((found or {'ProductID': 0})['ProductID'])
                else:
                    # If we don't have enough info to resolve product, but maybe it's just an update of wagon details
                    # For now, if no product_id and no components, we skip or error? 
                    # Existing logic in add_setting_wagons returns error.
                    # But here we might be permissive if data comes from a form that might not have full product details if they weren't changed.
                    # However, usually the form sends back what it got.
                    # Let's assume if product_id is missing, we need components.
                    pass

            if not product_id:
                # Fallback: if we still don't have a product ID, check if the wagon row had one before? No, we deleted them.
                # If we can't resolve product, we can't insert into SettingWagons as ProductID is NOT NULL (usually).
                # Check schema: ProductID INTEGER NOT NULL
                # So we must have it.
                # If the UI didn't send it, we have a problem.
                # The UI `initDryerUnloadSetting` logic sends `wagon_id` (from dataset), `start_time`, `end_time`, `packages`.
                # It does NOT send product_id or category/mold/glaze in the `wagons` array payload in line 549 of app.js!
                # Wait! Line 549: `const payload = { setting_id: editSid, wagons: [{ wagon_id: ..., start_time: ..., end_time: ..., packages: ... }] };`
                # That payload is for `save-row` button.
                # But the submit handler (line 592) sends `wagons: rows` where `rows` (line 575) includes `glaze_id` and `extra_code`.
                # It does NOT include `category_id` or `mold_id` or `product_id`.
                # This is a problem. The current UI logic for editing setting wagons seems to rely on the fact that maybe `add_setting_wagons` wasn't used for updates before?
                # Or maybe the edit logic in `app.js` is incomplete?
                # In `app.js` line 592, it calls `/api/setting/update` (which I assume is this endpoint).
                # But `rows` only has `wagon_order`, `wagon_no`, `glaze_id`, `extra_code`, `start_time`, `end_time`, `packages`.
                # It's missing `category_id` and `mold_id`.
                # Without those, we can't resolve `ProductID`.
                # UNLESS: The ProductID is derived from the SettingProcess (which has `CategoryID`)?
                # No, `SettingWagons` has its own `ProductID` because wagons can have different glazes/products?
                # Usually SettingProcess has `CategoryID`, `MoldID`?
                # Let's check `SettingProcesses` schema.
                # Line 2575 of server.py update_sql updates `CategoryID`.
                # Does `SettingProcesses` have `MoldID`?
                # server.py line 2568 UPDATE: SettingDateJalali, ShiftID, SupervisorID, OperatorID, PersonnelCount, ChamberNo, CategoryID, FingersCount, ColumnsCount, DryerWaste, Notes.
                # No MoldID in SettingProcesses update?
                # Let's check `get_setting_details` query (line 2526). `SELECT sp.* ...`.
                # If `SettingProcesses` has `MoldID`, it should be there.
                # If the UI form has `mold_id` (it does, `dus-load-mold` is displayed, but is it in the form data?),
                # In `app.js`, `loadInfo` shows `mold` (line 383), but that's just text content.
                # The form data `new FormData(form)` includes inputs.
                # Is there a hidden input for `mold_id`?
                # I need to check the HTML for the form.
                pass
            
            # If we can't find ProductID from the wagon data, maybe we can use the Setting's product info if available?
            # But wait, `add_setting_wagons` requires them.
            # If the user is editing, they might not be changing the product, just the wagon details.
            # If `SettingWagons` stores `ProductID`, we need it to re-insert.
            # If the UI doesn't send it back, we are in trouble.
            # I need to modify `app.js` to include `product_id` (or cat/mold) in the wagon rows data.
            # Or, `update_setting_transaction` should look up the previous values?
            # But we deleted the rows!
            # We could fetch the existing wagons before deleting, map them by WagonOrder/WagonNo, and preserve ProductID if not provided?
            
            # Let's try to preserve existing ProductID if not provided.
            pass

        # To preserve ProductIDs:
        # 1. Fetch existing wagons before delete.
        # 2. Map by WagonOrder (or ID if available).
        # 3. Use existing ProductID if new one not provided.
        
        # Fetch existing
        cursor.execute("SELECT WagonID, WagonOrder, ProductID FROM SettingWagons WHERE SettingID = ?", (setting_id,))
        existing_wagons = {row['WagonOrder']: row['ProductID'] for row in cursor.fetchall()} # Assuming WagonOrder is unique per setting
        
        # Delete
        cursor.execute("DELETE FROM SettingWagons WHERE SettingID = ?", (setting_id,))
        
        wagons = data.get('wagons') or []
        inserted = 0
        for w in wagons:
            wagon_order = int(w.get('wagon_order') or 0)
            wagon_no = int(w.get('wagon_no') or 0)
            product_id = w.get('product_id')
            
            # Try to resolve/cast product_id
            if product_id:
                try: product_id = int(product_id)
                except: product_id = None
            
            # If not provided, check existing
            if not product_id and wagon_order in existing_wagons:
                product_id = existing_wagons[wagon_order]
            
            # If still not provided, try to resolve from components (if sent)
            if not product_id:
                cat_id = w.get('category_id')
                mold_id = w.get('mold_id')
                glaze_id = w.get('glaze_id')
                extra_code = normalize_extra_code((w.get('extra_code') or '').strip())
                
                # If we are missing mold_id/cat_id on the wagon line, maybe we can use the Setting's ones?
                # But SettingProcesses might only have CategoryID.
                # If the UI sends `mold_id` in the main form data, we could use that as default?
                # The `data` object has `category_id` (line 2589 params).
                # Does it have `mold_id`? The update SQL didn't use it.
                # If the form sends it, we can use it.
                form_mold_id = data.get('mold_id')
                form_cat_id = data.get('category_id')
                
                cat_id = int(cat_id) if cat_id else (int(form_cat_id) if form_cat_id else None)
                mold_id = int(mold_id) if mold_id else (int(form_mold_id) if form_mold_id else None)
                glaze_id = int(glaze_id) if glaze_id else None
                
                if (cat_id and mold_id and glaze_id is not None):
                     cursor.execute("SELECT ProductID FROM Products WHERE CategoryID=? AND MoldID=? AND GlazeID=? AND COALESCE(ExtraCode,'')=COALESCE(?,'') LIMIT 1", (cat_id, mold_id, glaze_id, extra_code))
                     found = cursor.fetchone()
                     if not found:
                         cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, ?, 1)", (cat_id, mold_id, glaze_id, extra_code))
                         conn.commit()
                         cursor.execute("SELECT ProductID FROM Products WHERE CategoryID=? AND MoldID=? AND GlazeID=? AND COALESCE(ExtraCode,'')=COALESCE(?,'') ORDER BY ProductID DESC LIMIT 1", (cat_id, mold_id, glaze_id, extra_code))
                         found = cursor.fetchone()
                     product_id = found['ProductID']

            if not product_id:
                # If we absolutely can't find a product ID, we can't insert.
                # But maybe we should throw an error?
                # Or skip?
                # Skipping might result in data loss.
                # Let's error.
                raise Exception(f"Cannot resolve ProductID for wagon {wagon_order}")

            glaze_override = (w.get('glaze_override') or w.get('glaze_type') or '').strip() or None
            start_time = (w.get('start_time') or '').strip() or None
            end_time = (w.get('end_time') or '').strip() or None
            packages = int(w.get('packages') or 0)
            notes = (w.get('notes') or '').strip() or None
            
            cursor.execute("""
                INSERT INTO SettingWagons(
                  SettingID, WagonOrder, WagonNo, ProductID,
                  GlazeOverride, StartTime, EndTime, Packages, Notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                setting_id, wagon_order, wagon_no, product_id,
                glaze_override, start_time, end_time, packages, notes
            ))
            inserted += 1
            
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/rpc/create_dryer_loading', methods=['POST'])
def alias_create_dryer_loading():
    data = request.json or {}
    mapped = {
        'chamber_no': int(data.get('p_chamber_no') or 0),
        'load_date_jalali': normalize_jalali_date(data.get('p_load_date_jalali') or ''),
        'load_time': (data.get('p_load_time') or '').strip(),
        'operator_id': int(data.get('p_load_operator_id') or 0),
        'product_id': int(data.get('p_product_id') or 0),
        'finger_count': int(data.get('p_finger_count') or 0)
    }
    # perform insert directly (don't mutate request object)
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT LoadID FROM DryerLoading WHERE ChamberNo = ? AND IsUnloaded = 0", (mapped['chamber_no'],))
        if cursor.fetchone():
            return jsonify({'error': 'Chamber is already occupied'}), 400
        op_id = mapped['operator_id']
        cursor.execute("""
            INSERT INTO DryerLoading (
                ChamberNo, ProductID, LoadTimestamp, LoadDateJalali, LoadTime, 
                LoadOperatorID, FingerCount
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mapped['chamber_no'],
            mapped['product_id'],
            datetime.now(),
            mapped['load_date_jalali'],
            mapped['load_time'],
            op_id,
            mapped['finger_count']
        ))
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/rpc/create_dryer_loading_simple', methods=['POST'])
def create_dryer_loading_simple():
    data = request.json or {}
    chamber_no = int(data.get('chamber_no') or 0)
    load_date = (data.get('load_date_jalali') or '').strip()
    load_time = (data.get('load_time') or '').strip()
    operator_id = int(data.get('operator_id') or 0)
    finger_count = int(data.get('finger_count') or 0)
    category_id = int(data.get('category_id') or 0)
    mold_id = int(data.get('mold_id') or 0)
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        cursor.execute("SELECT LoadID FROM DryerLoading WHERE ChamberNo = ? AND IsUnloaded = 0", (chamber_no,))
        if cursor.fetchone():
            return jsonify({'error': 'Chamber is already occupied'}), 400
        cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
        g = cursor.fetchone()
        if not g:
            cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsGlazed, IsActive) VALUES(?, ?, ?, ?)", ('UNK', 'خام', 1, 1))
            cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
            g = cursor.fetchone()
        glaze_id = int((g or {'GlazeID': 0})['GlazeID'])
        cursor.execute("""
            SELECT ProductID FROM Products
            WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ''
            LIMIT 1
        """, (category_id, mold_id, glaze_id))
        pr = cursor.fetchone()
        if not pr:
            cursor.execute("INSERT INTO v_ProductInsert(CategoryID, MoldID, GlazeID, ExtraCode, IsActive) VALUES(?, ?, ?, '', 1)", (category_id, mold_id, glaze_id))
            conn.commit()
            cursor.execute("""
                SELECT ProductID FROM Products
                WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ''
                ORDER BY ProductID DESC LIMIT 1
            """, (category_id, mold_id, glaze_id))
            pr = cursor.fetchone()
        product_id = int((pr or {'ProductID': 0})['ProductID'])
        cursor.execute("""
            INSERT INTO DryerLoading (ChamberNo, ProductID, LoadTimestamp, LoadDateJalali, LoadTime, LoadOperatorID, FingerCount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (chamber_no, product_id, datetime.now(), load_date, load_time, operator_id, finger_count))
        conn.commit()
        return jsonify({'success': True, 'product_id': product_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/rpc/create_dryer_unloading', methods=['POST'])
def alias_create_dryer_unloading():
    data = request.json or {}
    mapped = {
        'load_id': int(data.get('p_load_id') or 0),
        'unload_date_jalali': normalize_jalali_date(data.get('p_unload_date_jalali') or ''),
        'unload_time': (data.get('p_unload_time') or '').strip(),
        'operator_id': int(data.get('p_unload_operator_id') or 0),
        'finger_count': int(data.get('p_unloaded_finger_count') or 0),
    }
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO DryerUnloading(
                LoadID, UnloadDateJalali, UnloadTime, UnloadOperatorID, FingerCount, UnloadTimestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mapped['load_id'],
            mapped['unload_date_jalali'],
            mapped['unload_time'],
            mapped['operator_id'],
            mapped['finger_count'],
            datetime.now()
        ))
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/rpc/create_dryer_reading_by_chamber', methods=['POST'])
def create_dryer_reading_by_chamber():
    data = request.json or {}
    chamber_no = int(data.get('p_chamber_no') or 0)
    date_jalali = normalize_jalali_date(data.get('p_record_date_jalali') or '')
    time_val = (data.get('p_record_time') or '').strip()
    temperature = data.get('p_temperature')
    humidity = data.get('p_humidity')
    operator = data.get('p_recorded_by')
    try:
        operator_id = int(operator) if operator is not None else None
    except Exception:
        operator_id = None
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO SimpleDryerReadings(ChamberNo, DateJalali, Time, Temperature, Humidity, OperatorCode_FK)
            VALUES(?, ?, ?, ?, ?, ?)
        """, (chamber_no, date_jalali, time_val, temperature, humidity, operator_id))
        conn.commit()
        return jsonify({'reading_id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer_readings_recent', methods=['GET'])
def dryer_readings_recent():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              ChamberNo, DateJalali, Time, Temperature, Humidity,
              COALESCE(u.FullName, u.Username) AS OperatorName,
              OperatorCode_FK
            FROM SimpleDryerReadings s
            LEFT JOIN Users u ON s.OperatorCode_FK = u.UserID
            ORDER BY s.ReadingID DESC
            LIMIT 20
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dryer/occupied_details', methods=['GET'])
def dryer_occupied_details():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
              dl.LoadID AS CycleID,
              dl.ChamberNo,
              dl.LoadDateJalali,
              dl.LoadTime,
              dl.FingerCount AS FingerCount,
              COALESCE(u.FullName, u.Username) AS Operator,
              dl.ProductID AS ProductID,
              -- Fallback names: prefer denormalized fields, else derive from Product triple
              COALESCE(c.CategoryName, c2.CategoryName) AS CategoryName,
              COALESCE(m.MoldName, m2.MoldName) AS MoldName,
              COALESCE(g.GlazeName, g2.GlazeName) AS GlazeName,
              dl.CategoryID AS CategoryID,
              dl.MoldID AS MoldID,
              dl.GlazeID AS GlazeID,
              CASE 
                WHEN COALESCE(c.CategoryName, '') = '' 
                     AND COALESCE(m.MoldName, '') = '' 
                THEN COALESCE(m2.MoldName, '') || ' ' || COALESCE(g2.GlazeName, '')
                WHEN COALESCE(c.CategoryName, '') = ''
                THEN m.MoldName || ' ' || COALESCE(g.GlazeName, '')
                ELSE COALESCE(c.CategoryName, c2.CategoryName) || ' ' || COALESCE(m.MoldName, m2.MoldName) || ' ' || COALESCE(g.GlazeName, g2.GlazeName)
              END AS ProductName
            FROM DryerLoading dl
            LEFT JOIN DryerUnloading du ON du.LoadID = dl.LoadID
            LEFT JOIN Categories c ON c.CategoryID = dl.CategoryID
            LEFT JOIN Molds m ON m.MoldID = dl.MoldID
            LEFT JOIN Glazes g ON g.GlazeID = dl.GlazeID
            LEFT JOIN Products p ON p.ProductID = dl.ProductID
            LEFT JOIN Categories c2 ON c2.CategoryID = p.CategoryID
            LEFT JOIN Molds m2 ON m2.MoldID = p.MoldID
            LEFT JOIN Glazes g2 ON g2.GlazeID = p.GlazeID
            LEFT JOIN Users u ON u.UserID = dl.LoadOperatorID
            WHERE du.UnloadID IS NULL AND dl.IsUnloaded = 0
            ORDER BY dl.ChamberNo
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/shift_options', methods=['GET'])
def shift_options():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ShiftID, ShiftCode, ShiftName FROM ShiftsDefinition WHERE IsActive = 1 ORDER BY ShiftID")
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/fuel_types_view', methods=['GET'])
def fuel_types_view():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT FuelTypeID, FuelName FROM FuelTypes WHERE IsActive = 1 ORDER BY FuelName")
        return jsonify([dict(r) for r in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/role_allowed_pages', methods=['GET'])
def role_allowed_pages():
    role_id_param = request.args.get('role_id') or ''
    role_id = None
    if role_id_param.startswith('eq.'):
        try:
            role_id = int(role_id_param.split('eq.')[1])
        except Exception:
            role_id = None
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.PageKey, p.PageTitle
            FROM RolePageAccess rpa
            JOIN Pages p ON p.PageID = rpa.PageID
            WHERE rpa.RoleID = ?
            ORDER BY p.PageTitle
        """, (role_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/user_allowed_pages', methods=['GET'])
def user_allowed_pages():
    user_id_param = request.args.get('user_id') or ''
    user_id = None
    if user_id_param.startswith('eq.'):
        try:
            user_id = int(user_id_param.split('eq.')[1])
        except Exception:
            user_id = None
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT p.PageKey, p.PageTitle
            FROM UserRoles ur
            JOIN RolePageAccess rpa ON rpa.RoleID = ur.RoleID
            JOIN Pages p ON p.PageID = rpa.PageID
            WHERE ur.UserID = ?
            ORDER BY p.PageTitle
        """, (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
def cleanup_duplicates():
    conn = get_db()
    cursor = conn.cursor()
    try:
        ensure_product_tables()
        ensure_triple_product_schema()
        cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
        r = cursor.fetchone()
        if not r:
            cursor.execute("INSERT INTO Glazes(GlazeCode, GlazeName, IsGlazed, IsActive) VALUES(?, ?, ?, ?)", ('UNK', 'خام', 1, 1))
            cursor.execute("SELECT GlazeID FROM Glazes WHERE GlazeCode='UNK'")
            r = cursor.fetchone()
        unk_gid = int((r or {'GlazeID': 0})['GlazeID'])
        cursor.execute("SELECT GlazeID FROM Glazes WHERE TRIM(GlazeName) IN (?, ?) AND GlazeCode <> 'UNK'", ('خام','نامشخص'))
        dup_glazes = [row['GlazeID'] for row in cursor.fetchall()]
        glazes_merged = 0
        for gid in dup_glazes:
            cursor.execute("SELECT ProductID, CategoryID, MoldID, COALESCE(ExtraCode,'') AS ExtraCode FROM Products WHERE GlazeID = ?", (gid,))
            prod_rows = [dict(r) for r in cursor.fetchall()]
            for pr in prod_rows:
                cursor.execute("""
                    SELECT ProductID FROM Products
                    WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ?
                    ORDER BY ProductID
                    LIMIT 1
                """, (pr['CategoryID'], pr['MoldID'], unk_gid, pr['ExtraCode']))
                target = cursor.fetchone()
                if target:
                    target_pid = int(target['ProductID'])
                    old_pid = int(pr['ProductID'])
                    if old_pid != target_pid:
                        cursor.execute("UPDATE DryerLoading SET ProductID = ? WHERE ProductID = ?", (target_pid, old_pid))
                        try:
                            cursor.execute("UPDATE SettingWagons SET ProductID = ? WHERE ProductID = ?", (target_pid, old_pid))
                        except Exception:
                            pass
                        try:
                            cursor.execute("UPDATE KilnPushData SET ProductID = ? WHERE ProductID = ?", (target_pid, old_pid))
                        except Exception:
                            pass
                        cursor.execute("DELETE FROM Products WHERE ProductID = ?", (old_pid,))
                else:
                    cursor.execute("UPDATE Products SET GlazeID = ? WHERE ProductID = ?", (unk_gid, pr['ProductID']))
            cursor.execute("UPDATE DryerLoading SET GlazeID = ? WHERE GlazeID = ?", (unk_gid, gid))
            try:
                cursor.execute("UPDATE KilnPushData SET GlazeID = ? WHERE GlazeID = ?", (unk_gid, gid))
            except Exception:
                pass
            cursor.execute("DELETE FROM Glazes WHERE GlazeID = ?", (gid,))
            glazes_merged += 1
        products_merged = 0
        cursor.execute("""
            SELECT CategoryID, MoldID, GlazeID, COALESCE(ExtraCode,'') AS ExtraCode, COUNT(*) AS cnt
            FROM Products
            GROUP BY CategoryID, MoldID, GlazeID, COALESCE(ExtraCode,'')
            HAVING COUNT(*) > 1
        """)
        groups = [dict(r) for r in cursor.fetchall()]
        for g in groups:
            cid = g['CategoryID']
            mid = g['MoldID']
            gid = g['GlazeID']
            extra = g['ExtraCode']
            cursor.execute("""
                SELECT ProductID FROM Products
                WHERE CategoryID = ? AND MoldID = ? AND GlazeID = ? AND COALESCE(ExtraCode,'') = ?
                ORDER BY ProductID
            """, (cid, mid, gid, extra))
            pids = [row['ProductID'] for row in cursor.fetchall()]
            if len(pids) <= 1:
                continue
            canonical = pids[0]
            others = pids[1:]
            if others:
                ph = ",".join("?" * len(others))
                cursor.execute(f"UPDATE DryerLoading SET ProductID = ? WHERE ProductID IN ({ph})", (canonical, *others))
                try:
                    cursor.execute(f"UPDATE SettingWagons SET ProductID = ? WHERE ProductID IN ({ph})", (canonical, *others))
                except Exception:
                    pass
                try:
                    cursor.execute(f"UPDATE KilnPushData SET ProductID = ? WHERE ProductID IN ({ph})", (canonical, *others))
                except Exception:
                    pass
                cursor.execute(f"DELETE FROM Products WHERE ProductID IN ({ph})", tuple(others))
                products_merged += len(others)
        conn.commit()
        return {'glazes_merged': glazes_merged, 'products_merged': products_merged}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=5000)
