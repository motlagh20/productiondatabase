#!/usr/bin/env python3
# Extract dimension masters (operators, products, glazes) from workbooks -> load into PostgreSQL.
# Config-driven, no fabricated values. Read-only on source; insert into pg.
import openpyxl, xlrd, re, psycopg2
from pathlib import Path
from collections import defaultdict
RD = Path("C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data")
def clean(v):
    if v is None: return ""
    if isinstance(v,float): return str(int(v)) if v.is_integer() else str(v)
    return str(v).replace("\n"," ").strip()

# ---- collect operators (code, name) ----
ops = {}   # (file_tag, code) -> name  (name immutable, keep first seen)
op_name_only = {}  # name -> set of codes
def scan_ops():
    files = sorted(RD.glob("*.xls*"))
    for f in files:
        if f.name.startswith("~$"): continue
        base = f.name.split("-")[0].split("_")[0]
        try:
            if f.suffix.lower()==".xls":
                bk=xlrd.open_workbook(str(f))
                for sh in bk.sheets():
                    if sh.nrows<2: continue
                    hdr=[clean(c.value) for c in sh.row(0)]
                    for ri in range(1,sh.nrows):
                        r=[clean(c.value) for c in sh.row(ri)]
                        for hi,h in enumerate(hdr):
                            if h in ("نام اپراتور","اپراتور بارگیری","اپراتور تخلیه","نام اپراتور بارگیری","نام اپراتور تخلیه"):
                                if hi<len(r) and r[hi]:
                                    ops[(base, r[hi])] = ops.get((base,r[hi]), r[hi])
            else:
                wb=openpyxl.load_workbook(f, read_only=True, data_only=True)
                for sn in wb.sheetnames:
                    if sn in {"Rand_Tize","Rand_sofal","Analyse","Analyse1","راندمان","Tabarestan","Access","error","Note","Backupmnu","backup"}: continue
                    rows=list(wb[sn].iter_rows(values_only=True))
                    if not rows: continue
                    hdr=[clean(h) for h in rows[0]]
                    for r in rows[1:]:
                        for hi,h in enumerate(hdr):
                            if h in ("نام اپراتور","اپراتور بارگیری","اپراتور تخلیه","نام اپراتور بارگیری","نام اپراتور تخلیه"):
                                if hi<len(r) and r[hi]:
                                    v=clean(r[hi]); ops[(base,v)]=ops.get((base,v), v)
                wb.close()
        except Exception as e:
            print(f"SKIP {f.name}: {e}")

scan_ops()
print(f"=== operators: {len(ops)} (code,name) pairs across files ===")
for k in sorted(ops)[:10]:
    print(f"  {k[0]}: {k[1]!r}")
print("  ...")

# ---- collect products from (نوع + شرح) in Packing ----
prods = defaultdict(int)
f = RD/"Packing-All.xlsx"
wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
ws = wb["Sheet1"]
rows = list(ws.iter_rows(values_only=True))
hdr = [clean(h) for h in rows[0]]
i_type=hdr.index("نوع محصول"); i_desc=hdr.index("شرح مجصول")
for r in rows[1:]:
    t=clean(r[i_type]); d=clean(r[i_desc])
    if d:
        prods[(t,d)] += 1
wb.close()
print(f"\n=== products (type,desc): {len(prods)} distinct ===")
for k,v in sorted(prods.items(), key=lambda x:-x[1])[:15]:
    print(f"  {v:6d}  {k[0]!r:10} {k[1]!r}")
print("  ...")

# ---- glazes ----
glaze_vals = defaultdict(int)
files = sorted(RD.glob("*.xls*"))
for f in files:
    if f.name.startswith("~$"): continue
    try:
        if f.suffix.lower()==".xls":
            bk=xlrd.open_workbook(str(f))
            sheets=[(sh.name,sh) for sh in bk.sheets()]
        else:
            wb=openpyxl.load_workbook(f, read_only=True, data_only=True)
            sheets=[(sn,wb[sn]) for sn in wb.sheetnames]
        for sn,sh in sheets:
            if sn in {"Rand_Tize","Rand_sofal","Analyse","Analyse1","راندمان","Tabarestan","Access","error","Note","Backupmnu","backup"}: continue
            if f.suffix.lower()==".xls":
                if sh.nrows<2: continue
                hdr=[clean(c.value) for c in sh.row(0)]
                rgen=(tuple(clean(c.value) for c in sh.row(i)) for i in range(1,sh.nrows))
            else:
                ra=list(sh.iter_rows(values_only=True))
                if not ra: continue
                hdr=[clean(h) for h in ra[0]]
                rgen=(tuple(clean(c) for c in r) for r in ra[1:])
            for hi,h in enumerate(hdr):
                if "لعاب" in h or "خودرنگ" in h:
                    for r in rgen:
                        if hi<len(r) and r[hi]:
                            v=clean(r[hi])
                            if v not in ("خودرنگ",):  # خودرنگ is no-glaze; track separately
                                glaze_vals[v]+=1
        if f.suffix.lower()!=".xls": wb.close()
    except Exception as e:
        print(f"SKIP {f.name}: {e}")
print(f"\n=== glaze values (non-خودرنگ): {len(glaze_vals)} distinct ===")
for k,v in sorted(glaze_vals.items(), key=lambda x:-x[1])[:15]:
    print(f"  {v:6d}  {k!r}")
