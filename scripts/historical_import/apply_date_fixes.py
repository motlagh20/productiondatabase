#!/usr/bin/env python3
# APPLY kiln_pushes date_jalali fixes for RESOLVABLE malformed rows only
# (HIGH + CHECK, i.e. neighbor-year + parseable MM.DD). Leaves FLAG rows
# (ambiguous MM.DD) untouched so they stay in review_queue.
# Also re-aligns the date segment of natural_key (= date|hour|car) so the
# clean views (which derive record_date FROM natural_key) stay consistent.
# Idempotent: only updates rows whose date_jalali is still malformed.
import psycopg2, re

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("SELECT id, date_jalali, hour, incoming_car_id, natural_key FROM kiln_pushes ORDER BY id")
rows=cur.fetchall(); cur.close()

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

def parse_mmdd(s, Y):
    t=s.strip('.')
    sy=str(Y)
    if t.startswith(sy):
        t=t[len(sy):].lstrip('.')
    else:
        y2=str(Y)[2:]
        if t[:2]==y2 and len(t)>2 and t[2] in '. ':
            t=t[2:].lstrip('.')
        else:
            for L in (3,2,1):
                if len(t)>=L and t[:L]==sy[:L]:
                    t=t[L:].lstrip('.'); break
    parts=[int(p) for p in re.split(r'[.\s]', t) if p.isdigit()]
    if len(parts)>=2 and 1<=parts[0]<=12 and 1<=parts[1]<=31:
        return parts[0],parts[1]
    return None

applied=0; skipped_flag=0; skipped_already=0
for i,(pid,dt,hr,car,nk) in enumerate(rows):
    if valid4(dt):
        continue
    b,a=neighbors(i)
    Y=None
    if b and a and b[0]==a[0]: Y=b[0]
    elif b: Y=b[0]
    elif a: Y=a[0]
    if Y is None:
        skipped_flag+=1; continue
    md=parse_mmdd(dt,Y)
    if md is None:
        skipped_flag+=1; continue
    prop=f"{Y}.{md[0]:02d}.{md[1]:02d}"
    # re-align natural_key date segment (keep hour|car)
    new_nk=f"{prop}|{hr or ''}|{car or ''}"
    cur2=psycopg2.connect(**CONN); cu=cur2.cursor()
    cu.execute("UPDATE kiln_pushes SET date_jalali=%s, natural_key=%s WHERE id=%s",
               (prop, new_nk, pid))
    cur2.commit(); cu.close(); cur2.close()
    applied+=1

c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("SELECT count(*) FROM kiln_pushes WHERE date_jalali !~ '^\\d{4}\\.\\d{1,2}\\.\\d{1,2}$'")
left=cur.fetchone()[0]
cur.close(); c.close()
print(f"APPLIED date fixes: {applied}")
print(f"SKIPPED (FLAG/ambiguous or no neighbor): {skipped_flag}")
print(f"Malformed rows remaining in DB: {left} (expect 9)")
