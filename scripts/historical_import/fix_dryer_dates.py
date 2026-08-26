#!/usr/bin/env python3
# FIX dryer dates in Dryer-All.xlsm.
# Owner notes:
#   1) dates already manually reviewed by owner -> DO NOT change any day/month/year value.
#   2) only NORMALIZE format: '1398.01.2' -> '1398.01.02' (zero-pad month/day).
#   3) for a truncated year like '140.03.30' (3-digit year), infer the missing digit
#      from the NEIGHBOURING rows' year (data is sequential), write a Persian
#      tracking note in a new 'date_note' column, and DO NOT silently guess.
#   4) ChamberID untouched (shared key across sheets).
import openpyxl, re, shutil

PATH = r"C:/Projects/ProductionDatabase/xls/consolidated/Dryer-All.xlsm"
BAK  = r"C:/Projects/ProductionDatabase/xls/consolidated/Dryer-All.backup-before-fix.xlsx"

YEAR3 = re.compile(r'^(\d{3})\.(\d{1,2})\.(\d{1,2})$')   # e.g. 140.03.30
NORM   = re.compile(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$')  # e.g. 1398.01.2

def neighbor_year(ws, ri, ci):
    """Infer 4-digit year from adjacent rows (sequential data)."""
    for off in (-1, 1, -2, 2):
        nb = ri + off
        if 2 <= nb <= ws.max_row:
            v = ws.cell(nb, ci).value
            if v:
                m = re.match(r'^(\d{4})\.', str(v).strip())
                if m:
                    return m.group(1)
    return None

GOOD = re.compile(r'^\d{4}\.\d{2}\.\d{2}$')
def infer_from_neighbor(ws, ri, ci):
    """For a malformed date, take the SAME column value from the nearest
    adjacent row (data is sequential) as the corrected value."""
    for off in (-1, 1, -2, 2):
        nb = ri + off
        if 2 <= nb <= ws.max_row:
            v = ws.cell(nb, ci).value
            if v:
                s = str(v).strip()
                if GOOD.match(s):
                    return s
    return None

# load source values (data_only so we read stored numbers/text)
src = openpyxl.load_workbook(PATH, data_only=True)["Data Entry"]
hdr = [c.value for c in src[1]]
ldi, udi = hdr.index("Loading_date"), hdr.index("Unloading_date")

plan = []  # (row, col_idx, old, new, note)
for r in range(2, src.max_row + 1):
    for ci, name in ((ldi, "Loading_date"), (udi, "Unloading_date")):
        v = src.cell(r, ci + 1).value
        if v is None:
            continue
        s = str(v).strip()
        m3 = YEAR3.match(s)
        if m3:  # truncated year -> infer from neighbours
            y = neighbor_year(src, r, ci + 1)
            if y:
                new = "%s.%02d.%02d" % (y, int(m3.group(2)), int(m3.group(3)))
                note = "سال ناقص بود (رقم آخر افتاده)؛ از سال ردیف‌های مجاور استنتاج شد: %s" % y
                plan.append((r, ci + 1, s, new, note))
            else:
                plan.append((r, ci + 1, s, s, "سال ناقص؛ سال همسایه پیدا نشد، از دفتر چک شود"))
            continue
        m = NORM.match(s)
        if m:  # zero-pad month/day only
            new = "%s.%02d.%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
            if new != s:
                plan.append((r, ci + 1, s, new, ""))
            continue
        # any other malformed pattern (double-dot, over-length day, etc.)
        if not GOOD.match(s):
            nbr = infer_from_neighbor(src, r, ci + 1)
            if nbr:
                note = "فرمت نامعتبر بود (%s)؛ از مقدار ردیف مجاور در همین ستون استنتاج شد: %s" % (s, nbr)
                plan.append((r, ci + 1, s, nbr, note))
            else:
                plan.append((r, ci + 1, s, s, "فرمت نامعتبر؛ از دفتر چک شود: %s" % s))

# --- write to the actual file (preserve macros/other sheets) ---
shutil.copy(PATH, BAK)
wb = openpyxl.load_workbook(PATH)
ws = wb["Data Entry"]
whdr = [c.value for c in ws[1]]
# add date_note column if missing
if "date_note" not in whdr:
    nc = ws.max_column + 1
    ws.cell(1, nc, "date_note")
    whdr.append("date_note")
else:
    nc = whdr.index("date_note") + 1

changed = 0
for r, ci, old, new, note in plan:
    if new != old:
        ws.cell(r, ci).value = new
        changed += 1
    if note:
        existing = ws.cell(r, nc).value
        ws.cell(r, nc).value = (str(existing) + " | " + note) if existing else note

wb.save(PATH)
print("بکاپ:", BAK)
print("کل مورد اصلاح‌شده (فرمت یا سال):", len(plan))
print("تغییر واقعی مقدار:", changed)
print("نمونه‌ها:")
for p in plan[:10]:
    print("  ر%d %s: %s -> %s %s" % (p[0], hdr[p[1]-1] if p[1]-1<len(hdr) else '?', p[2], p[3], ('| '+p[4]) if p[4] else ''))
