#!/usr/bin/env python3
# PREVIEW ONLY (no DB write): propose corrected date_jalali for malformed rows,
# inferring the YEAR from the nearest valid-date neighbors (owner method:
# "match with prev/next rows so you don't make a mistake"). Writes a review CSV
# to Desktop and prints a table. Nothing is mutated.
import psycopg2, re, csv
from pathlib import Path

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("SELECT id, date_jalali, hour FROM kiln_pushes ORDER BY id")
rows=cur.fetchall(); cur.close(); c.close()

def valid4(d):
    m=re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", str(d or ""))
    if not m: return None
    y,mo,dd=int(m.group(1)),int(m.group(2)),int(m.group(3))
    return (y,mo,dd) if (1<=mo<=12 and 1<=dd<=31) else None

def neighbors(i):
    b=None;a=None
    for j in range(i-1,-1,-1):
        v=valid4(rows[j][1])
        if v: b=v; break
    for j in range(i+1,len(rows)):
        v=valid4(rows[j][1])
        if v: a=v; break
    return b,a

def year_of(b,a):
    if b and a and b[0]==a[0]: return b[0],"both-neighbors-agree"
    if b: return b[0],"before-only"
    if a: return a[0],"after-only"
    return None,"no-neighbor"

def parse_mmdd(s, Y):
    """Return (mm,dd) or None from a malformed string, using neighbor year Y to
    strip the year prefix. Handles 'YYYY.M.D', 'YY.M.D', 'YYYY.M.D.' etc.
    Confidence: >=2 numeric parts after year strip -> clean; else None."""
    t=s.strip('.')
    sy=str(Y)
    # strip full 4-digit year prefix if present
    if t.startswith(sy):
        t=t[len(sy):].lstrip('.')
    else:
        # strip a 2-digit shorthand of the year (99->1399, 02->1402, etc.)
        y2=str(Y)[2:]   # last two digits of the 4-digit year
        if t[:2]==y2 and len(t)>2 and t[2] in '. ':
            t=t[2:].lstrip('.')
        else:
            for L in (3,2,1):
                if len(t)>=L and t[:L]==sy[:L]:
                    t=t[L:].lstrip('.'); break
    parts=[int(p) for p in re.split(r'[.\s]', t) if p.isdigit()]
    if len(parts)>=2 and 1<=parts[0]<=12 and 1<=parts[1]<=31:
        return parts[0],parts[1]
    return None  # <2 usable parts -> ambiguous

out=[]
print(f"{'id':>7} | {'old':<14} | {'proposed':<12} | {'conf':<5} | neighbor-evidence")
print("-"*80)
for i,(pid,dt,hr) in enumerate(rows):
    if valid4(dt): continue
    b,a=neighbors(i)
    Y,src=year_of(b,a)
    if Y is None:
        print(f"{pid:>7} | {str(dt):<14} | {'???':<12} | {'FLAG':<5} | no valid neighbor at all")
        out.append((pid,dt,"","FLAG","no valid neighbor"))
        continue
    md=parse_mmdd(dt,Y)
    if md is None:
        print(f"{pid:>7} | {str(dt):<14} | {'???':<12} | {'FLAG':<5} | year={Y} ({src}) but MM.DD ambiguous")
        out.append((pid,dt,f"{Y}.??.??","FLAG",f"year={Y} ({src}) MM.DD ambiguous"))
        continue
    prop=f"{Y}.{md[0]:02d}.{md[1]:02d}"
    # sanity: proposed should sit between neighbors if both exist
    ok=True
    if b: ok = ok and (Y,md[0],md[1]) >= b
    if a: ok = ok and (Y,md[0],md[1]) <= a
    conf = "HIGH" if ok else "CHECK"
    print(f"{pid:>7} | {str(dt):<14} | {prop:<12} | {conf:<5} | year={Y} ({src})")
    out.append((pid,dt,prop,conf,f"year={Y} ({src})"))

# write preview CSV
OUT=Path(r"C:/Users/Mohammad/Desktop/kiln_date_fixes_preview.csv")
with open(OUT,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["push_id","old_date_jalali","proposed_date_jalali","confidence","neighbor_evidence"])
    for r in out: w.writerow(r)
print(f"\nPreview written: {OUT}  ({len(out)} malformed rows)")
