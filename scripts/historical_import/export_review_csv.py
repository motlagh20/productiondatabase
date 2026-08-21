#!/usr/bin/env python3
# Export review_queue to CSV (UTF-8 BOM for Excel Persian) with Farsi labels.
# Output: xls/consolidated/review_queue_export.csv  (git-ignored, local handoff file)
import psycopg2, csv
from pathlib import Path
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
OUT=Path("C:/Projects/ProductionDatabase/xls/consolidated/review_queue_export.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)
LABELS={
 "table_name":"جدول","natural_key":"کلید رکورد","field_name":"ستون",
 "raw_value":"مقدار خام","issue_class":"وضعیت","suggested_fix":"پیشنهاد اصلاح",
}
CLASS_FA={"Invalid":"نامعتبر (غیرممکن)","Warning":"مشکوک (نیاز بررسی)","Unmapped":"بدون نگاشت",
          "NeedsReview":"نیاز بررسی","Duplicate":"تکراری","Valid":"معتبر"}
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("""SELECT table_name, natural_key, field_name, raw_value, issue_class, suggested_fix
               FROM review_queue ORDER BY issue_class, table_name, field_name""")
rows=cur.fetchall()
with open(OUT,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f)
    w.writerow([LABELS[c] for c in ["table_name","natural_key","field_name","raw_value","issue_class","suggested_fix"]])
    for r in rows:
        r=list(r)
        r[4]=CLASS_FA.get(r[4],r[4])
        w.writerow(r)
conn.close()
print(f"Exported {len(rows)} review_queue rows -> {OUT}")
