#!/usr/bin/env python3
# Export review_queue to (1) XLSX (Farsi, opens correctly in Excel) and
# (2) CSV (UTF-8 BOM, for tooling). Handoff file for plant QA.
import psycopg2
from pathlib import Path
try:
    import openpyxl
    HAVE_XLSX=True
except ImportError:
    HAVE_XLSX=False
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
OUTDIR=Path("C:/Projects/ProductionDatabase/xls/consolidated")
OUTDIR.mkdir(parents=True, exist_ok=True)
LABELS=["جدول","کلید رکورد","ستون","مقدار خام","وضعیت","پیشنهاد اصلاح"]
CLASS_FA={"Invalid":"نامعتبر (غیرممکن)","Warning":"مشکوک (نیاز بررسی)",
          "Unmapped":"بدون نگاشت","NeedsReview":"نیاز بررسی","Duplicate":"تکراری","Valid":"معتبر"}
conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("""SELECT table_name, natural_key, field_name, raw_value, issue_class, suggested_fix
               FROM review_queue ORDER BY issue_class, table_name, field_name""")
rows=[list(r) for r in cur.fetchall()]
for r in rows: r[4]=CLASS_FA.get(r[4],r[4])
conn.close()

# 1. XLSX (best for Excel Persian)
if HAVE_XLSX:
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="review_queue"
    ws.append(LABELS)
    for r in rows: ws.append(r)
    # RTL sheet + right-aligned cells for correct Persian display
    from openpyxl.styles import Alignment
    ws.sheet_view.rightToLeft=True
    for c in ws[1]: c.alignment=Alignment(horizontal="right",vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment=Alignment(horizontal="right",vertical="center")
    xlsx=OUTDIR/"review_queue_export.xlsx"
    wb.save(xlsx)
    print(f"XLSX: {len(rows)} rows -> {xlsx}")
else:
    print("openpyxl missing; skipping XLSX")

# 2. CSV (UTF-8 BOM)
import csv
csvp=OUTDIR/"review_queue_export.csv"
with open(csvp,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(LABELS)
    for r in rows: w.writerow(r)
print(f"CSV : {len(rows)} rows -> {csvp}")
