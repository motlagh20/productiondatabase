#!/usr/bin/env python3
# Load PACKING fact data into PostgreSQL. Product re-derived from (نوع+شرح) per M1-A1.
# grade2=waste (carry if present). wagon_no -> wagon_master FK. Read-only source.
import openpyxl, psycopg2, re
from pathlib import Path
RD=Path("C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data")
def clean(v):
    if v is None: return ""
    if isinstance(v,float): return str(int(v)) if v.is_integer() else str(v)
    return str(v).replace("\n"," ").strip()
def to_num(v):
    v=clean(v)
    if v in ("","."): return None
    try: return float(v)
    except: return None
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("SELECT id,canonical_code,description FROM products"); prod_map={d:c for pid,c,d in cur.fetchall()}
cur.execute("SELECT DISTINCT wagon_no FROM wagon_master"); wm={r[0] for r in cur.fetchall()}
cur.close(); conn.close()

f=RD/"Packing-All.xlsx"
wb=openpyxl.load_workbook(f,read_only=True,data_only=True)
ws=wb["Sheet1"]; rows=list(ws.iter_rows(values_only=True))
hdr=[clean(h) for h in rows[0]]
idx={h:i for i,h in enumerate(hdr)}
i_t=idx["نوع محصول"]; i_d=idx["شرح مجصول"]; i_w=idx["شماره واگن"]

loaded=0; flags=0
conn=psycopg2.connect(**CONN); cur=conn.cursor()
for r in rows[1:]:
    date_j=clean(r[idx["تاریخ بسته بندی"]]) if "تاریخ بسته بندی" in idx and idx["تاریخ بسته بندی"]<len(r) else ""
    if not date_j: continue
    shift=clean(r[idx["شیفت"]]) if "شیفت" in idx and idx["شیفت"]<len(r) else ""
    month=clean(r[idx["ماه"]]) if "ماه" in idx and idx["ماه"]<len(r) else ""
    day=clean(r[idx["روز"]]) if "روز" in idx and idx["روز"]<len(r) else ""
    pdesc=clean(r[i_d]) if i_d<len(r) else ""
    pcode=prod_map.get(pdesc)
    wagon=clean(r[i_w]) if i_w<len(r) else ""
    total=clean(r[idx["تعداد کل محصول"]]) if "تعداد کل محصول" in idx and idx["تعداد کل محصول"]<len(r) else ""
    g1=clean(r[idx["تعداد درجه 1"]]) if "تعداد درجه 1" in idx and idx["تعداد درجه 1"]<len(r) else ""
    g2=clean(r[idx["تعداد درجه 2"]]) if "تعداد درجه 2" in idx and idx["تعداد درجه 2"]<len(r) else ""
    waste=clean(r[idx["تعداد ضایعات"]]) if "تعداد ضایعات" in idx and idx["تعداد ضایعات"]<len(r) else ""
    eff=clean(r[idx["راندمان"]]) if "راندمان" in idx and idx["راندمان"]<len(r) else ""
    ctrl=clean(r[idx["کنترلر"]]) if "کنترلر" in idx and idx["کنترلر"]<len(r) else ""
    wtype=clean(r[idx["نوع کارگران"]]) if "نوع کارگران" in idx and idx["نوع کارگران"]<len(r) else ""
    wcnt=clean(r[idx["تعداد کارگران"]]) if "تعداد کارگران" in idx and idx["تعداد کارگران"]<len(r) else ""
    nk=f"{date_j}|{shift}|{wagon}|{pcode}"
    review=[]
    try:
        w=int(float(wagon)) if wagon else 0
        if w>80: review.append(("wagon_no",w,"Warning","flag>80 (typo)"))
    except: pass
    wfk=wagon if wagon in wm else None
    cur.execute("""INSERT INTO packing_records(date_jalali,month,day,shift,controller,worker_type,worker_count,product_code,wagon_no,total,grade1,grade2,waste,efficiency_raw,source,natural_key)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'historical',%s)
                 ON CONFLICT (natural_key) DO UPDATE SET product_code=EXCLUDED.product_code""",
                (date_j or None,month or None,day or None,shift or None,ctrl or None,wtype or None,to_num(wcnt),pcode or None,wfk,to_num(total),to_num(g1),to_num(g2),to_num(waste),to_num(eff),nk))
    loaded+=1
    for field,val,cls,fix in review:
        cur.execute("INSERT INTO review_queue(table_name,natural_key,field_name,raw_value,issue_class,suggested_fix) VALUES('packing_records',%s,%s,%s,%s,%s)",(nk,field,str(val),cls,fix))
        flags+=1
conn.commit()
print(f"Packing: records={loaded}, flagged={flags}")
cur.execute("SELECT count(*) FROM packing_records"); print("total packing_records:",cur.fetchone()[0])
cur.close(); conn.close()
