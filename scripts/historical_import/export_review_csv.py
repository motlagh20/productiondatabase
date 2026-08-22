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
        prop_s=f" → پیشنهاد {prop}" if prop is not None else " (فاحش؛ نیاز بررسی کارخونه)"
        return ("دمای کوره خارج از محدوده مجاز (۱۰۰–۱۲۰۰ درجه)",
                "بررسی و تأیید پیشنهاد توسط کارخونه (بدون اعمال خودکار)",
                f"مقدار {raw_s} خارج از محدوده است{prop_s} — ابتدا مقدار درون‌محدوده‌ی محتمل استخراج شد (حذف/جابه‌جایی یک رقم)، سپس با نزدیک‌ترین مقدار سالم همین زون در پوش‌های دیگر سنجش شد")
    if cls=="Invalid" and "grade1" in field:
        return ("درجه ۱ بزرگتر از کل تولید (نامعتبر)",
                "بررسی توسط کارخونه",
                f"مقدار درجه ۱ از کل بیشتر است: {raw_s}")
    if cls=="Invalid" and ("humidity" in field or "value" in field):
        # '6+4' style dirty strings are not numeric; '>100' values are impossible for %
        if any(ch not in "0123456789." for ch in raw_s):
            return ("مقدار رطوبت نامخوانا (کاراکتر اضافه)",
                    "تمیزسازی / بررسی توسط کارخونه",
                    f"مقدار {raw_s} شامل کاراکتر غیرعددی است و قابل تفسیر به عنوان رطوبت نیست")
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
cur.execute("""SELECT table_name, field_name, raw_value, issue_class, suggested_fix, resolved,
                      cleaned_value, correction_reason, natural_key
               FROM review_queue""")
rows=cur.fetchall()

# load kiln-temp proposed corrections (+ 3 nearest healthy same-zone neighbors + applied mean + reason)
cur.execute("""SELECT c.raw_value, c.proposed_value, c.neighbor_1, c.neighbor_2, c.neighbor_3,
                      r.corrected_value, c.correction_reason, c.corrected_by,
                      c.zone_group, c.zone_reading
                 FROM kiln_temp_correction c
                 JOIN kiln_temperature_readings r ON r.id = c.reading_id""")
ktc_map={}
ktc_rows=[]
for r in cur.fetchall():
    nbrs=[x for x in (r[1],r[2],r[3]) if x is not None]   # neighbor_1..3
    ktc_map[str(r[0])]={"prop":r[1],"nbrs":nbrs,"mean":r[5],"reason":r[6],"by":r[7]}
    ktc_rows.append({"raw":r[0],"mean":r[5],"reason":r[6],"field":f"{r[8]}.{r[9]}"})

# load dryer-humidity corrections (out-of-range humidity >100, mean of 3 healthy same-op)
cur.execute("""SELECT c.raw_value, c.neighbor_1, c.neighbor_2, c.neighbor_3,
                      r.corrected_value, c.correction_reason, c.corrected_by,
                      r.operation_id
                 FROM dryer_humidity_correction c
                 JOIN dryer_readings r ON r.id = c.reading_id""")
dhc_map={}
dhc_rows=[]
for r in cur.fetchall():
    nbrs=[x for x in (r[1],r[2],r[3]) if x is not None]
    dhc_map[str(r[0])]={"nbrs":nbrs,"mean":r[4],"reason":r[5],"by":r[6],"op":r[7]}
    dhc_rows.append({"raw":r[0],"mean":r[4],"reason":r[5],"op":r[7]})
conn.close()

# group + count (resolved rows folded in, tracked separately)
grp=defaultdict(lambda:{"n":0,"cls":None,"fix":None,"resolved":0,"cleaned":None,"reason":None,"nk":set()})
for t,f,raw,cls,fix,res,cleaned,reason,nk in rows:
    key=(t,f,str(raw),cls)
    grp[key]["n"]+=1
    grp[key]["cls"]=cls; grp[key]["fix"]=fix
    if res: grp[key]["resolved"]+=1
    if cleaned is not None: grp[key]["cleaned"]=cleaned
    if reason is not None: grp[key]["reason"]=reason
    if nk is not None: grp[key]["nk"].add(str(nk))

def extract_date(nk_set):
    """First '|'-segment of any natural_key is the Jalali date of the erroneous record.
    Canonicalized to YYYY.MM.DD (2-digit year -> 13xx; any separator -> '.')."""
    import re as _re
    for nk in nk_set:
        if nk and "|" in nk:
            seg=nk.split("|",1)[0].strip()
            m=_re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", seg)
            if m:
                return f"{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}"
            m=_re.match(r"^(\d{2})[./-](\d{1,2})[./-](\d{1,2})$", seg)
            if m:
                return f"13{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}"
            return seg
    return ""

out=[]
for (t,f,raw,cls),g in grp.items():
    diag,act,note=diagnose(f,cls,raw,g["fix"])
    # A kiln-temp anomaly is "resolved" if review_queue marked it resolved OR a mean
    # correction was applied to it (per instruction: apply mean to ALL kiln-temp items).
    ktc=ktc_map.get(str(raw))
    dhc=dhc_map.get(str(raw))
    mean_applied = bool(ktc and ktc.get("mean") is not None) or bool(dhc and dhc.get("mean") is not None)
    needs = "خیر (حل‌شده)" if (g["resolved"]>0 or mean_applied) else "بله"
    nbrs = (ktc["nbrs"] if ktc else []) or (dhc["nbrs"] if dhc else [])
    nbr_s = " | ".join(str(x) for x in nbrs) if nbrs else ""
    mean_s = str(ktc["mean"]) if (ktc and ktc.get("mean") is not None) else (str(dhc["mean"]) if (dhc and dhc.get("mean") is not None) else "")
    reason_s = g["reason"] if g.get("reason") else (str(ktc["reason"]) if (ktc and ktc.get("reason")) else (str(dhc["reason"]) if (dhc and dhc.get("reason")) else ""))
    cleaned_s = str(g["cleaned"]) if g.get("cleaned") is not None else ""
    # Date of the erroneous record: first '|'-segment of natural_key. Applied to ALL
    # rows that carry a natural_key (owner directive: every item needing review must
    # show its date so it can be traced back to the physical ledgers).
    date_err = extract_date(g["nk"]) if g["nk"] else ""
    out.append([t,f,raw,g["n"],CLASS_FA.get(cls,cls),diag,act,needs,note,nbr_s,mean_s,reason_s,cleaned_s,date_err])

# Append kiln-temp corrections NOT already covered by review_queue (e.g. low <100 rows
# that validate_anomalies.py did not flag). Each is a resolved, mean-applied row.
# Dedup on (field, raw) — not raw alone — because the same raw can appear under a
# different zone field in review_queue (e.g. kiln_temp.bottom vs kiln_temp.bottom.01).
seen=set((str(r[1]), str(r[2])) for r in out if str(r[1]).startswith("kiln_temp"))
for k in ktc_rows:
    col=f"kiln_temp.{k['field']}"
    if (col, str(k["raw"])) in seen:
        continue
    raw=k["raw"]
    mean_s=str(k["mean"]) if k["mean"] is not None else ""
    nbrs=ktc_map[str(raw)]["nbrs"] if str(raw) in ktc_map else []
    nbr_s=" | ".join(str(x) for x in nbrs)
    cls="نامعتبر" if (isinstance(raw,(int,float)) and raw>1200) else "هشدار"
    out.append(["kiln_temperature_readings",col,raw,1,cls,
                "دمای کوره خارج از محدوده مجاز (۱۰۰–۱۲۰۰ درجه)",
                "بررسی و تأیید پیشنهاد توسط کارخونه (بدون اعمال خودکار)",
                "خیر (حل‌شده)", f"مقدار {raw} خارج از محدوده؛ با میانگین ۳ مقدار سالم همین زون جایگزین شد",
                nbr_s, mean_s, "mean_of_neighbors", ""])

# Append dryer-humidity corrections (out-of-range >100) NOT already in review_queue.
seen_d=set((str(r[1]), str(r[2])) for r in out if str(r[1]).startswith("dryer_humidity"))
for k in dhc_rows:
    col="dryer_readings.value"
    if (col, str(k["raw"])) in seen_d:
        continue
    raw=k["raw"]; mean_s=str(k["mean"]) if k["mean"] is not None else ""
    nbrs=dhc_map[str(raw)]["nbrs"] if str(raw) in dhc_map else []
    nbr_s=" | ".join(str(x) for x in nbrs)
    out.append(["dryer_readings",col,raw,1,"نامعتبر",
                "رطوبت بالای ۱۰۰٪ (نامعتبر)",
                "بررسی توسط کارخونه",
                "خیر (حل‌شده)", f"مقدار {raw} خارج از محدوده رطوبت؛ با میانگین ۳ مقدار سالم همین عملیات جایگزین شد",
                nbr_s, mean_s, "mean_of_neighbors", ""])
# sort: open (needs review) first, then resolved; Invalid first within each
out.sort(key=lambda r:(0 if r[7].startswith("بله") else 1, 0 if r[4].startswith("نامعتبر") else 1, -r[3]))

HEADERS=["جدول","ستون","مقدار_خام","تعداد_تکرار","وضعیت","عیب‌شناسی","اقدام_پیشنهادی","نیاز_به_بررسی","یادداشت","مقادیر_متناظر_سالم","مقدار_اصلاح‌شده_میانگین","علت_اصلاح","مقدار_تمیز‌شده","تاریخ_درج_اشتباه"]

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
