#!/usr/bin/env python3
# Load DRYER fact data into PostgreSQL. Row-oriented temp/humidity from 2 parallel rows.
# Config-driven, validation-class, idempotent. Read-only on source.
import openpyxl, psycopg2, re
from pathlib import Path
RD = Path("C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data")
def clean(v):
    if v is None: return ""
    if isinstance(v,float): return str(int(v)) if v.is_integer() else str(v)
    return str(v).replace("\n"," ").strip()

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")

# product lookup by (type,desc) -> canonical_code
import psycopg2
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("SELECT canonical_code,mold_type,glaze,description FROM products")
prod_map={}
for code,mold,glaze,desc in cur.fetchall():
    prod_map[desc]=code  # desc is the شرح محصول text
cur.close(); conn.close()

dryer_files=sorted(RD.glob("Dryer-*.xls*"))
loaded_ops=0; loaded_reads=0; flags=0
conn=psycopg2.connect(**CONN); cur=conn.cursor()
for f in dryer_files:
    if f.name.startswith("~$"): continue
    try:
        wb=openpyxl.load_workbook(f,read_only=True,data_only=True)
        # find the data sheet (usually 'Data Entry')
        sn="Data Entry" if "Data Entry" in wb.sheetnames else wb.sheetnames[0]
        ws=wb[sn]; rows=list(ws.iter_rows(values_only=True))
        if not rows: wb.close(); continue
        hdr=[clean(h) for h in rows[0]]
        # locate columns
        idx={h:i for i,h in enumerate(hdr)}
        i_date=idx.get("تاریخ بارگیری شمسی") or idx.get("تاریخ")
        i_shift=idx.get("شیفت")
        i_oper_load=idx.get("اپراتور بارگیری")
        i_oper_unload=idx.get("اپراتور تخلیه")
        i_prod=idx.get("نام محصول")
        i_pcode=idx.get("کد محصول")
        i_finger=idx.get("تعداد فینگر تولیدی")
        i_chamber=idx.get("شماره چمبر")
        i_dur=idx.get("مدت زمان")
        # numeric columns start after metadata; find header row for hours
        # In this sheet layout, hours are in a separate header row ABOVE the 2 data rows.
        # Simpler: scan all numeric cols after chamber; pair (top=temp, bottom=humidity).
        meta_end=max([x for x in [i_date,i_shift,i_oper_load,i_oper_unload,i_prod,i_pcode,i_finger,i_chamber,i_dur] if x is not None])+1
        num_cols=[i for i in range(meta_end,len(hdr)) if re.fullmatch(r"\d+",clean(hdr[i]))]  # hour-labeled header
        for ri in range(1,len(rows)-1,2):  # step 2: temp row, then humidity row
            r_temp=rows[ri]; r_hum=rows[ri+1] if ri+1<len(rows) else None
            if i_date is None or i_date>=len(r_temp) or not clean(r_temp[i_date]): continue
            date_j=clean(r_temp[i_date])
            shift=clean(r_temp[i_shift]) if i_shift is not None else ""
            chamber=clean(r_temp[i_chamber]) if i_chamber is not None else ""
            prod_desc=clean(r_temp[i_prod]) if i_prod is not None else ""
            pcode=prod_map.get(prod_desc)
            finger=clean(r_temp[i_finger]) if i_finger is not None else ""
            # bounds check
            review=[]
            try:
                ch=int(float(chamber))
                if ch>40: review.append(("chamber_no",ch,"Warning","flag>40"))
            except: pass
            nk=f"{date_j}|{shift}|{chamber}|{pcode}"
            cur.execute("""INSERT INTO dryer_operations(date_jalali,month,day,shift,operator_load_id,operator_unload_id,product_code,finger_count,chamber_no,duration,source,natural_key)
                         VALUES(%s,%s,%s,%s,NULL,NULL,%s,%s,%s,%s,'historical',%s)
                         ON CONFLICT (natural_key) DO UPDATE SET product_code=EXCLUDED.product_code""",
                        (date_j,None,None,shift or None,pcode or None,finger or None,chamber or None,clean(r_temp[i_dur]) or None,nk))
            op_id=cur.execute("SELECT id FROM dryer_operations WHERE natural_key=%s",(nk,)) or None
            cur.execute("SELECT id FROM dryer_operations WHERE natural_key=%s",(nk,)); op_id=cur.fetchone()[0]
            loaded_ops+=1
            # readings
            for ci in num_cols:
                hour=clean(hdr[ci])
                tv=clean(r_temp[ci]) if ci<len(r_temp) else ""
                hv=clean(r_hum[ci]) if (r_hum is not None and ci<len(r_hum)) else ""
                for metric,val in (("temp",tv),("humidity",hv)):
                    if val:
                        try: v=float(val)
                        except: 
                            review.append((f"dryer_readings.{metric}",val,"Invalid","non-numeric")); continue
                        cur.execute("INSERT INTO dryer_readings(operation_id,hour_offset,metric,value,source) VALUES(%s,%s,%s,%s,'historical')",(op_id,int(hour),metric,v))
                        loaded_reads+=1
            for field,val,cls,fix in review:
                cur.execute("INSERT INTO review_queue(table_name,natural_key,field_name,raw_value,issue_class,suggested_fix) VALUES('dryer_operations',%s,%s,%s,%s,%s)",(nk,field,str(val),cls,fix))
                flags+=1
        wb.close()
    except Exception as e:
        print(f"SKIP {f.name}: {e}")
conn.commit()
print(f"Dryer: operations={loaded_ops}, readings={loaded_reads}, flagged={flags}")
cur.execute("SELECT count(*) FROM dryer_operations"); print("total dryer_operations:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM dryer_readings"); print("total dryer_readings:",cur.fetchone()[0])
cur.close(); conn.close()
