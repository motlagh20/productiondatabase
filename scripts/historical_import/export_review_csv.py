#!/usr/bin/env python3
# Export review_queue to (1) XLSX (Farsi+RTL, opens cleanly in Excel) and
# (2) CSV (UTF-8 BOM). Richer diagnosis/action format per plant QA samples.
# Groups identical (table,field,raw_value,class) and counts occurrences.
import psycopg2, csv
from pathlib import Path
from collections import defaultdict
try:
    import openpyxl
    from openpyxl.styles import Alignment
    HAVE_XLSX=True
except ImportError:
    HAVE_XLSX=False
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
OUTDIR=Path("C:/Projects/ProductionDatabase/xls/consolidated")
OUTDIR.mkdir(parents=True, exist_ok=True)
CLASS_FA={"Invalid":"نامعتبر (غیرممکن)","Warning":"مشکوک (نیاز بررسی)",
          "Unmapped":"بدون نگاشت","NeedsReview":"نیاز بررسی","Duplicate":"تکراری","Valid":"معتبر"}

def diagnose(field, cls, raw, fix):
    """Return (diagnosis_fa, action_fa, note_fa)."""
    raw_s=str(raw)
    if cls=="Invalid" and "kiln_temp" in field:
        prop=ktc_map.get(raw_s)
        prop_s=f" → پیشنهاد {prop}" if prop is not None else " (همسایه سالم یافت نشد)"
        return ("دمای کوره خارج از محدوده مجاز (۱۰۰–۱۲۰۰ درجه)",
                "بررسی و تأیید پیشنهاد توسط کارخونه (بدون اعمال خودکار)",
                f"مقدار {raw_s} خارج از محدوده است{prop_s} — عدد سمت راست یا چپ اشتباه مشخص نیست، لذا نزدیک‌ترین مقدار سالم همین زون در پوش‌های دیگر در نظر گرفته شد")
    if cls=="Invalid" and "grade1" in field:
        return ("درجه ۱ بزرگتر از کل تولید (نامعتبر)",
                "بررسی توسط کارخونه",
                f"مقدار درجه ۱ از کل بیشتر است: {raw_s}")
    if cls=="Invalid" and ("humidity" in field or "value" in field):
        return ("رطوبت بالای ۱۰۰٪ (نامعتبر)",
                "بررسی توسط کارخونه",
                "رطوبت نمی‌تواند بیشتر از ۱۰۰٪ باشد")
    if cls=="Warning" and ("wagon" in field or "incoming_car" in field):
        return ("شماره واگن خارج از محدوده (بالای ۸۰)",
                "بررسی و تصحیح دستی توسط کارخونه (بدون تغییر خودکار)",
                f"مقدار {raw_s} احتمالاً اشتباه تایپی است")
    if cls=="Warning" and "chamber" in field:
        return ("شماره چمبر خارج از محدوده (بالای ۴۰)",
                "بررسی توسط کارخونه",
                f"مقدار {raw_s} خارج از محدوده چمبرهاست")
    if cls=="Warning" and "kiln_temp" in field:
        return ("دمای غیرعادی پایین (زیر ۱۰۰ درجه)",
                "بررسی سنسور / مقیاس توسط کارخونه",
                f"مقدار {raw_s} غیرعادی پایین است")
    # fallback
    return (CLASS_FA.get(cls,cls), "بررسی توسط کارخونه", raw_s)

conn=psycopg2.connect(**CONN); cur=conn.cursor()
cur.execute("""SELECT table_name, field_name, raw_value, issue_class, suggested_fix
               FROM review_queue""")
rows=cur.fetchall()

# load kiln-temp proposed corrections (nearest valid same-zone value, NOT applied)
cur.execute("SELECT raw_value, proposed_value FROM kiln_temp_correction")
ktc_map={str(r[0]): r[1] for r in cur.fetchall()}
conn.close()

# group + count
grp=defaultdict(lambda:{"n":0,"cls":None,"fix":None})
for t,f,raw,cls,fix in rows:
    key=(t,f,str(raw),cls)
    grp[key]["n"]+=1
    grp[key]["cls"]=cls; grp[key]["fix"]=fix

out=[]
for (t,f,raw,cls),g in grp.items():
    diag,act,note=diagnose(f,cls,raw,g["fix"])
    out.append([t,f,raw,g["n"],CLASS_FA.get(cls,cls),diag,act,"بله",note])
# sort: Invalid first, then by count desc
out.sort(key=lambda r:(0 if r[4].startswith("نامعتبر") else 1, -r[3]))

HEADERS=["جدول","ستون","مقدار_خام","تعداد_تکرار","وضعیت","عیب‌شناسی","اقدام_پیشنهادی","نیاز_به_بررسی","یادداشت"]

# 1. XLSX
if HAVE_XLSX:
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="review_queue"
    ws.append(HEADERS)
    for r in out: ws.append(r)
    ws.sheet_view.rightToLeft=True
    for c in ws[1]: c.alignment=Alignment(horizontal="right",vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment=Alignment(horizontal="right",vertical="center")
    xlsx=OUTDIR/"review_queue_export.xlsx"; wb.save(xlsx)
    print(f"XLSX: {len(out)} grouped rows -> {xlsx}")
else:
    print("openpyxl missing; skipping XLSX")

# 2. CSV (UTF-8 BOM)
csvp=OUTDIR/"review_queue_export.csv"
with open(csvp,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(HEADERS)
    for r in out: w.writerow(r)
print(f"CSV : {len(out)} grouped rows -> {csvp}")
