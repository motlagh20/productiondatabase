#!/usr/bin/env python3
# Load SETTING fact data into PostgreSQL (4-layer: operations/shift_unloads/wagons + wagon_master).
# Repeating wagon blocks (cols 12-19,20-27,28-35,36-43). Glaze text. Read-only source.
import openpyxl, xlrd, psycopg2, re
from pathlib import Path
RD=Path("C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data")
def clean(v):
    if v is None: return ""
    if isinstance(v,float): return str(int(v)) if v.is_integer() else str(v)
    return str(v).replace("\n"," ").strip()
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("SELECT canonical_code,description FROM products"); prod_map={d:c for c,d in cur.fetchall()}
cur.close(); conn.close()

# wagon block column groups (Append C 14): 4 blocks of 8 cols starting at 12
BLOCK_STARTS=[12,20,28,36]
BLOCK_LEN=8  # شماره واگن, لعاب/خودرنگ, زمان شروع, زمان پایان, کارکرد, تعداد بسته, تعداد خشت, تعداد کل سفال

def to_num(v):
    v=clean(v)
    if v=="" : return None
    try: return float(v)
    except: return None

setting_files=sorted(RD.glob("Set_*.xls*"))
ops=0; unloads=0; wagons=0; wm=0; flags=0
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("SELECT DISTINCT wagon_no FROM wagon_master"); existing_wm={r[0] for r in cur.fetchall()}
new_wm=set()
for f in setting_files:
    if f.name.startswith("~$"): continue
    try:
        if f.suffix.lower()==".xls":
            bk=xlrd.open_workbook(str(f)); sh=bk.sheet_by_index(0)
            rows=[tuple(clean(c.value) for c in sh.row(i)) for i in range(sh.nrows)]
        else:
            wb=openpyxl.load_workbook(f,read_only=True,data_only=True)
            sn="Data" if "Data" in wb.sheetnames else wb.sheetnames[0]
            rows=[tuple(clean(c) for c in r) for r in wb[sn].iter_rows(values_only=True)]
            wb.close()
        if not rows: continue
        hdr=[clean(h) for h in rows[0]]
        idx={h:i for i,h in enumerate(hdr)}
        # determine how many wagon blocks exist: a block starts at col 12 and repeats every 8,
        # but only while that column has data in some row. Cap at 4.
        ncols=len(hdr)
        block_starts=[12+8*b for b in range(4) if 12+8*b+7 < ncols]
        for r in rows[1:]:
            date_j=clean(r[idx["تاریخ"]]) if "تاریخ" in idx and idx["تاریخ"]<len(r) else ""
            if not date_j: continue
            shift=clean(r[idx["شیفت"]]) if "شیفت" in idx and idx["شیفت"]<len(r) else ""
            chamber=clean(r[idx["شماره چمبر"]]) if "شماره چمبر" in idx and idx["شماره چمبر"]<len(r) else ""
            pdesc=clean(r[idx["محصول"]]) if "محصول" in idx and idx["محصول"]<len(r) else ""
            pcode=prod_map.get(pdesc)
            finger=clean(r[idx["تعداد فینگر"]]) if "تعداد فینگر" in idx and idx["تعداد فینگر"]<len(r) else ""
            cols=clean(r[idx["تعداد ستون"]]) if "تعداد ستون" in idx and idx["تعداد ستون"]<len(r) else ""
            dwaste=clean(r[idx["ضایعات خشک کن"]]) if "ضایعات خشک کن" in idx and idx["ضایعات خشک کن"]<len(r) else ""
            batch=f"{date_j}|{chamber}|{shift}"
            review=[]
            try:
                ch=int(float(chamber))
                if ch>40: review.append(("chamber_no",ch,"Warning","flag>40"))
            except: pass
            cur.execute("""INSERT INTO setting_operations(batch_key,date_jalali,shift,operator_id,personnel_count,chamber_no,product_code,finger_count,column_count,dryer_waste,source)
                         VALUES(%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,'historical')""",
                        (batch,date_j,shift or None,None,chamber or None,pcode or None,to_num(finger),to_num(cols),to_num(dwaste)))
            cur.execute("SELECT id FROM setting_operations WHERE batch_key=%s",(batch,)); op_id=cur.fetchone()[0]
            ops+=1
            # shift unload (1 per op for now; multi-shift split handled post-build if needed)
            cur.execute("INSERT INTO setting_shift_unloads(operation_id,shift,sub_id) VALUES(%s,%s,1) ON CONFLICT (operation_id,shift) DO NOTHING",(op_id,shift or 1))
            cur.execute("SELECT id FROM setting_shift_unloads WHERE operation_id=%s AND shift=%s",(op_id,shift or 1)); su_id=cur.fetchone()[0]
            unloads+=1
            # parse wagon blocks
            for bs in block_starts:
                if bs>=len(r): break
                wagon=clean(r[bs]) if bs<len(r) else ""
                if not wagon: continue
                glaze=clean(r[bs+1]) if bs+1<len(r) else ""
                st=clean(r[bs+2]) if bs+2<len(r) else ""
                et=clean(r[bs+3]) if bs+3<len(r) else ""
                pkgs=clean(r[bs+5]) if bs+5<len(r) else ""
                cur.execute("INSERT INTO setting_wagons(shift_unload_id,wagon_no,glaze,start_time,end_time,packages,source) VALUES(%s,%s,%s,%s,%s,%s,'historical') ON CONFLICT (shift_unload_id,wagon_no) DO NOTHING",(su_id,wagon,glaze,st,et,to_num(pkgs)))
                wagons+=1
                new_wm.add(wagon)
                try:
                    w=int(float(wagon))
                    if w>80: review.append(("wagon_no",w,"Warning","flag>80"))
                except: pass
            for field,val,cls,fix in review:
                cur.execute("INSERT INTO review_queue(table_name,natural_key,field_name,raw_value,issue_class,suggested_fix) VALUES('setting_operations',%s,%s,%s,%s,%s)",(batch,field,str(val),cls,fix))
                flags+=1
    except Exception as e:
        print(f"SKIP {f.name}: {e}")
# wagon_master aggregation
for w in new_wm:
    if w not in existing_wm:
        cur.execute("SELECT COALESCE(SUM(packages),0) FROM setting_wagons WHERE wagon_no=%s",(w,))
        tot=cur.fetchone()[0]
        cur.execute("INSERT INTO wagon_master(wagon_no,total_packages,source) VALUES(%s,%s,'historical') ON CONFLICT (wagon_no) DO UPDATE SET total_packages=EXCLUDED.total_packages",(w,tot))
        wm+=1
conn.commit()
print(f"Setting: ops={ops}, shift_unloads={unloads}, wagons={wagons}, wagon_master_new={wm}, flagged={flags}")
cur.execute("SELECT count(*) FROM setting_operations"); print("total setting_operations:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM setting_wagons"); print("total setting_wagons:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM wagon_master"); print("total wagon_master:",cur.fetchone()[0])
cur.close(); conn.close()
