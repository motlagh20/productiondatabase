#!/usr/bin/env python3
# Load dimension masters into PostgreSQL from workbooks (config-driven, no fabrication).
# Operators: detect code vs name (name immutable per Master Rules 32).
# Products: derived from (نوع محصول + شرح محصول) per M1-A1.
# Glazes: text vocab, typo-fix only.
import openpyxl, xlrd, re, psycopg2
from pathlib import Path
from collections import defaultdict
RD = Path("C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data")

def clean(v):
    if v is None: return ""
    if isinstance(v,float): return str(int(v)) if v.is_integer() else str(v)
    return str(v).replace("\n"," ").strip()

CONN = dict(host="localhost", port=5433, dbname="postgres", user="postgres", password="test")

def is_code(s):
    return bool(re.fullmatch(r"\d{1,3}", s.strip())) or bool(re.fullmatch(r"\d+", s.strip()))

# ---- Operators ----
ops_pairs = defaultdict(set)  # name -> set of codes seen
raw_ops = []
def scan_ops():
    for f in sorted(RD.glob("*.xls*")):
        if f.name.startswith("~$"): continue
        base=f.name.split("-")[0].split("_")[0]
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
                for r in rgen:
                    for hi,h in enumerate(hdr):
                        if h in ("نام اپراتور","اپراتور بارگیری","اپراتور تخلیه","نام اپراتور بارگیری","نام اپراتور تخلیه"):
                            if hi<len(r) and r[hi]:
                                v=clean(r[hi])
                                raw_ops.append((base,v))
            if f.suffix.lower()!=".xls": wb.close()
        except Exception as e:
            print(f"SKIP {f.name}: {e}")

scan_ops()
# Build name->codes. If value is code (digits), it's a code; else it's a name.
name_to_codes=defaultdict(set)
for base,v in raw_ops:
    if is_code(v):
        # code seen; associate with this file's operators later (we don't have name mapping per row)
        pass
    else:
        name_to_codes[v].add(base)
# Since source mixes code and name in same column, we insert distinct NAMES as operators
# and distinct CODES separately; name is immutable, code normalized per file.
op_names = sorted({v for base,v in raw_ops if not is_code(v)})
op_codes = sorted({v for base,v in raw_ops if is_code(v)})
print(f"Operator NAMES: {len(op_names)}, CODES: {len(op_codes)}")

# ---- Products (type+desc) ----
prods=defaultdict(int)
f=RD/"Packing-All.xlsx"
wb=openpyxl.load_workbook(f, read_only=True, data_only=True)
ws=wb["Sheet1"]; rows=list(ws.iter_rows(values_only=True))
hdr=[clean(h) for h in rows[0]]
i_t,i_d=hdr.index("نوع محصول"),hdr.index("شرح مجصول")
for r in rows[1:]:
    t,d=clean(r[i_t]),clean(r[i_d])
    if d: prods[(t,d)]+=1
wb.close()
print(f"Products (type,desc): {len(prods)}")

# ---- Glazes ----
glaze_vals=defaultdict(int)
for f in sorted(RD.glob("*.xls*")):
    if f.name.startswith("~$"): continue
    try:
        if f.suffix.lower()==".xls":
            bk=xlrd.open_workbook(str(f)); sheets=[(sh.name,sh) for sh in bk.sheets()]
        else:
            wb=openpyxl.load_workbook(f, read_only=True, data_only=True); sheets=[(sn,wb[sn]) for sn in wb.sheetnames]
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
            for r in rgen:
                for hi,h in enumerate(hdr):
                    if ("لعاب" in h or "خودرنگ" in h) and hi<len(r) and r[hi]:
                        v=clean(r[hi])
                        if v not in ("خودرنگ",) and not re.search(r"\d{1,2}:\d{2}", v):
                            glaze_vals[v]+=1
        if f.suffix.lower()!=".xls": wb.close()
    except Exception as e:
        print(f"SKIP {f.name}: {e}")
print(f"Glazes: {len(glaze_vals)}")

# ---- insert ----
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("TRUNCATE operators, products, glazes RESTART IDENTITY CASCADE;")
for n in op_names:
    cur.execute("INSERT INTO operators(code,full_name,role,source) VALUES(%s,%s,'operator','historical')", ("?", n))
for c in op_codes:
    cur.execute("INSERT INTO operators(code,full_name,role,source) VALUES(%s,'UNKNOWN', 'operator','historical')", (c,))
# products -> canonical code
mold_map={"سفال":"SOFAL","تیزه":"TIZEH","پنجه ای":"PANJEH","تيزه":"TIZEH"}
glaze_map={"خودرنگ":"KHODRANG","اخرا":"AKHRA","اخراء":"AKHRA","لعاب":"LA'AB","سبز":"SABZ","مشکی":"MESHKII","مولتی":"MULTI"}
for (t,d),cnt in prods.items():
    m=mold_map.get(t,"UNK")
    # extract glaze token from desc
    gl=""
    for g in ["خودرنگ","اخرا","اخراء","سبز","مشکی","مولتی","لعاب"]:
        if g in d: gl=glaze_map.get(g,g); break
    canon=f"P-{m}-{gl}" if gl else f"P-{m}"
    cur.execute("INSERT INTO products(canonical_code,mold_type,glaze,description,source) VALUES(%s,%s,%s,%s,'historical') ON CONFLICT (canonical_code) DO NOTHING", (canon,t,gl,d))
# glazes
for g,cnt in glaze_vals.items():
    norm=None
    for k,v in glaze_map.items():
        if k in g: norm=v; break
    is_combined = "مولتی" in g
    cur.execute("INSERT INTO glazes(glaze_value,normalized,is_combined,note) VALUES(%s,%s,%s,'from workbook')", (g,norm,is_combined))
conn.commit()
print("INSERTED operators/products/glazes.")
cur.execute("SELECT count(*) FROM operators"); print("operators:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM products"); print("products:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM glazes"); print("glazes:",cur.fetchone()[0])
cur.close(); conn.close()
