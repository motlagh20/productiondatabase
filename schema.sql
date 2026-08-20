PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Categories (
  CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
  CategoryCode TEXT NOT NULL UNIQUE,
  CategoryName TEXT NOT NULL,
  Description TEXT,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS Molds (
  MoldID INTEGER PRIMARY KEY AUTOINCREMENT,
  MoldCode TEXT NOT NULL UNIQUE,
  MoldName TEXT NOT NULL,
  CategoryID INTEGER NOT NULL,
  Width REAL,
  Length REAL,
  Height REAL,
  PiecesPerPress INTEGER DEFAULT 1 CHECK (PiecesPerPress >= 1),
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1)),
  FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Glazes (
  GlazeID INTEGER PRIMARY KEY AUTOINCREMENT,
  GlazeCode TEXT NOT NULL UNIQUE,
  GlazeName TEXT NOT NULL,
  IsSelfColored INTEGER DEFAULT 0 CHECK (IsSelfColored IN (0,1)),
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS Products (
  ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
  ProductCode TEXT UNIQUE NOT NULL,
  ProductName TEXT NOT NULL,
  CategoryID INTEGER NOT NULL,
  MoldID INTEGER NOT NULL,
  GlazeID INTEGER NOT NULL,
  ExtraCode TEXT DEFAULT '',
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1)),
  CreatedAt TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE RESTRICT,
  FOREIGN KEY (MoldID) REFERENCES Molds(MoldID) ON DELETE RESTRICT,
  FOREIGN KEY (GlazeID) REFERENCES Glazes(GlazeID) ON DELETE RESTRICT,
  UNIQUE (CategoryID, MoldID, GlazeID, ExtraCode)
);

CREATE INDEX IF NOT EXISTS idx_products_cat ON Products(CategoryID);
CREATE INDEX IF NOT EXISTS idx_products_mold ON Products(MoldID);
CREATE INDEX IF NOT EXISTS idx_products_glaze ON Products(GlazeID);

CREATE TABLE IF NOT EXISTS ExtraCodeMap (
  code TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_ProductInsert AS
SELECT CategoryID, MoldID, GlazeID, ExtraCode, IsActive FROM Products WHERE 0;

CREATE TRIGGER IF NOT EXISTS trg_v_ProductInsert_insert
INSTEAD OF INSERT ON v_ProductInsert
BEGIN
  INSERT INTO Products (CategoryID, MoldID, GlazeID, ExtraCode, IsActive)
  VALUES (NEW.CategoryID, NEW.MoldID, NEW.GlazeID, COALESCE(NEW.ExtraCode, ''), COALESCE(NEW.IsActive, 1));
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
        CASE WHEN TRIM(NEW.ExtraCode) <> '' THEN ' ' || COALESCE((SELECT display_name FROM ExtraCodeMap WHERE code = TRIM(NEW.ExtraCode)), TRIM(NEW.ExtraCode)) ELSE '' END
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
        CASE WHEN TRIM(NEW.ExtraCode) <> '' THEN ' ' || COALESCE((SELECT display_name FROM ExtraCodeMap WHERE code = TRIM(NEW.ExtraCode)), TRIM(NEW.ExtraCode)) ELSE '' END
      FROM Categories c, Molds m, Glazes g
      WHERE c.CategoryID = NEW.CategoryID AND m.MoldID = NEW.MoldID AND g.GlazeID = NEW.GlazeID
    )
  WHERE ProductID = NEW.ProductID;
END;

CREATE TABLE IF NOT EXISTS Users (
  UserID INTEGER PRIMARY KEY AUTOINCREMENT,
  Username TEXT NOT NULL UNIQUE,
  FullName TEXT,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS Roles (
  RoleID INTEGER PRIMARY KEY AUTOINCREMENT,
  RoleName TEXT NOT NULL UNIQUE,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS UserRoles (
  UserID INTEGER NOT NULL,
  RoleID INTEGER NOT NULL,
  PRIMARY KEY (UserID, RoleID),
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE RESTRICT,
  FOREIGN KEY (RoleID) REFERENCES Roles(RoleID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Pages (
  PageID INTEGER PRIMARY KEY AUTOINCREMENT,
  PageKey TEXT NOT NULL UNIQUE,
  PageTitle TEXT NOT NULL,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS RolePageAccess (
  RoleID INTEGER NOT NULL,
  PageID INTEGER NOT NULL,
  PRIMARY KEY (RoleID, PageID),
  FOREIGN KEY (RoleID) REFERENCES Roles(RoleID) ON DELETE RESTRICT,
  FOREIGN KEY (PageID) REFERENCES Pages(PageID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS ShiftsDefinition (
  ShiftID INTEGER PRIMARY KEY AUTOINCREMENT,
  ShiftCode TEXT NOT NULL UNIQUE,
  ShiftName TEXT,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1)),
  StartTime TEXT,
  EndTime TEXT
);

CREATE TABLE IF NOT EXISTS DryerCycle (
  CycleID INTEGER PRIMARY KEY AUTOINCREMENT,
  ChamberNo INTEGER NOT NULL,
  ProductCode_FK TEXT,
  LoadTimestamp DATETIME,
  LoadDateJalali TEXT,
  LoadTime TEXT,
  LoadOperatorCode_FK INTEGER,
  LoadFingerCount INTEGER,
  UnloadTimestamp DATETIME,
  UnloadDateJalali TEXT,
  UnloadTime TEXT,
  UnloadOperatorCode_FK INTEGER,
  UnloadFingerCount INTEGER,
  FOREIGN KEY (ProductCode_FK) REFERENCES Products(ProductCode) ON DELETE RESTRICT,
  FOREIGN KEY (LoadOperatorCode_FK) REFERENCES Users(UserID) ON DELETE RESTRICT,
  FOREIGN KEY (UnloadOperatorCode_FK) REFERENCES Users(UserID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS DryerReadings (
  ReadingID INTEGER PRIMARY KEY AUTOINCREMENT,
  ChamberNo INTEGER NOT NULL,
  DateJalali TEXT NOT NULL,
  Time TEXT NOT NULL,
  Temperature REAL,
  Humidity REAL,
  OperatorCode_FK INTEGER,
  FOREIGN KEY (OperatorCode_FK) REFERENCES Users(UserID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS SettingProcesses (
  SettingID INTEGER PRIMARY KEY AUTOINCREMENT,
  SettingDateJalali TEXT NOT NULL,
  ShiftID INTEGER NOT NULL,
  SupervisorID INTEGER NOT NULL,
  OperatorID INTEGER NOT NULL,
  PersonnelCount INTEGER,
  ChamberNo INTEGER NOT NULL,
  CategoryID INTEGER NOT NULL,
  FingersCount INTEGER,
  ColumnsCount INTEGER,
  DryerWaste INTEGER DEFAULT 0,
  CreatedAt TEXT DEFAULT (datetime('now')),
  Notes TEXT,
  FOREIGN KEY (ShiftID) REFERENCES ShiftsDefinition(ShiftID) ON DELETE RESTRICT,
  FOREIGN KEY (SupervisorID) REFERENCES Users(UserID) ON DELETE RESTRICT,
  FOREIGN KEY (OperatorID) REFERENCES Users(UserID) ON DELETE RESTRICT,
  FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE RESTRICT,
  UNIQUE (SettingDateJalali, ChamberNo)
);

CREATE TABLE IF NOT EXISTS SettingWagons (
  WagonID INTEGER PRIMARY KEY AUTOINCREMENT,
  SettingID INTEGER NOT NULL,
  WagonOrder INTEGER NOT NULL CHECK (WagonOrder BETWEEN 1 AND 4),
  WagonNo INTEGER NOT NULL,
  ProductID INTEGER NOT NULL,
  GlazeOverride TEXT,
  StartTime TEXT,
  EndTime TEXT,
  Packages INTEGER NOT NULL,
  Notes TEXT,
  FOREIGN KEY (SettingID) REFERENCES SettingProcesses(SettingID) ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT,
  UNIQUE (SettingID, WagonOrder),
  UNIQUE (SettingID, WagonNo)
);

CREATE TABLE IF NOT EXISTS FuelTypes (
  FuelTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
  FuelName TEXT NOT NULL UNIQUE,
  IsActive INTEGER DEFAULT 1 CHECK (IsActive IN (0,1))
);

CREATE TABLE IF NOT EXISTS KilnPushData (
  PushID INTEGER PRIMARY KEY AUTOINCREMENT,
  Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  DateJalali TEXT,
  Time TEXT,
  ShiftID INTEGER,
  OperatorCode_FK INTEGER,
  ProductCode_FK INTEGER NOT NULL,
  IncomingCarID INTEGER,
  FuelTypeID INTEGER,
  PushingTime_min REAL,
  ExhaustTemp REAL,
  Preheat1 REAL,
  Preheat2 REAL,
  Thermostat REAL,
  Zone0 REAL,
  Zone1 REAL,
  Zone2 REAL,
  Zone3 REAL,
  Zone4 REAL,
  Zone5 REAL,
  Zone6 REAL,
  Zone7 REAL,
  Rapid1 REAL,
  Rapid2 REAL,
  BottomA REAL,
  Bottom1 REAL,
  BottomB REAL,
  Bottom2 REAL,
  Notes TEXT,
  FOREIGN KEY (FuelTypeID) REFERENCES FuelTypes(FuelTypeID) ON DELETE RESTRICT,
  FOREIGN KEY (ProductCode_FK) REFERENCES Products(ProductCode) ON DELETE RESTRICT,
  FOREIGN KEY (OperatorCode_FK) REFERENCES Users(UserID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS WarehouseStock (
  StockID INTEGER PRIMARY KEY AUTOINCREMENT,
  ProductID INTEGER NOT NULL,
  Quantity INTEGER NOT NULL,
  UpdatedAt TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS WarehouseTransactions (
  TxID INTEGER PRIMARY KEY AUTOINCREMENT,
  ProductID INTEGER NOT NULL,
  Quantity INTEGER NOT NULL,
  TxType TEXT NOT NULL,
  Timestamp TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS PackagingRecords (
  PackID INTEGER PRIMARY KEY AUTOINCREMENT,
  ProductID INTEGER NOT NULL,
  Packages INTEGER NOT NULL,
  Timestamp TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE RESTRICT
);

INSERT OR IGNORE INTO Roles(RoleName, IsActive) VALUES ('Admin', 1), ('Operator', 1), ('Supervisor', 1);

INSERT OR IGNORE INTO FuelTypes(FuelName, IsActive) VALUES ('گاز', 1), ('گازوئیل', 1), ('مازوت', 1), ('برق', 1);

INSERT OR IGNORE INTO Pages(PageKey, PageTitle) VALUES
('home','خانه'),
('dryer_dashboard','داشبورد خشک‌کن'),
('dryer_load','بارگیری خشک‌کن'),
('dryer_unload','تخلیه خشک‌کن'),
('setting_entry','ثبت ستینگ'),
('setting_transactions','تراکنش‌های ستینگ'),
('kiln_pushing','پوشینگ کوره'),
('admin_roles','تعریف نقش‌ها'),
('admin_shifts','تعریف شیفت‌ها'),
('admin_fuel','تعریف سوخت‌ها'),
('admin_users_roles','تعریف کاربران و نقش‌ها'),
('admin_access','دسترسی صفحات'),
('admin_glazes','تعریف لعاب‌ها'),
('admin_molds','تعریف قالب‌ها'),
('admin_products','مدیریت محصولات'),
('admin_categories','مدیریت دسته‌ها'),
('admin_product_categories','دسته‌بندی محصول');

INSERT OR IGNORE INTO RolePageAccess(RoleID, PageID)
SELECT r.RoleID, p.PageID FROM Roles r CROSS JOIN Pages p WHERE r.RoleName = 'Admin';

INSERT OR IGNORE INTO RolePageAccess(RoleID, PageID)
SELECT r.RoleID, p.PageID FROM Roles r JOIN Pages p ON p.PageKey IN ('home','dryer_dashboard','dryer_load','dryer_unload','setting_entry','setting_transactions','kiln_pushing') WHERE r.RoleName = 'Operator';

