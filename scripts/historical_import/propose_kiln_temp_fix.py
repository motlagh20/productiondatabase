#!/usr/bin/env python3
# Propose kiln-temp corrections WITHOUT applying them (owner directive 2026-08-21, revised).
# Method (corrected per owner): first derive an in-range candidate from the raw value by
# removing ONE stray digit (right or left) or scaling, then sanity-check that candidate
# against the nearest valid value of the SAME (zone_group, zone_reading) in OTHER pushes.
#   - if candidate is close to a healthy neighbor -> propose the candidate (self-corrected).
#   - if candidate is far from any healthy neighbor -> flag for plant review (no confident fix).
# Nothing is auto-applied; applied always FALSE.
import psycopg2
from collections import defaultdict
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
LO,HI=100,1200
FAR_RATIO=0.20   # candidate must be within 20% of nearest healthy neighbor to be "close"

def in_range(v): return LO<=v<=HI

def candidates(v):
    """Return list of plausible in-range values derived from raw v by removing one digit
    (left/right) or scaling by 10. v is float; works on its integer representation."""
    out=set()
    s=str(int(round(v)))
    # remove one digit from the right (e.g. 9450 -> 945)
    if len(s)>1:
        out.add(int(s[:-1]))
    # remove one digit from the left (e.g. 9450 -> 450)
    if len(s)>1:
        out.add(int(s[1:]))
    # scale: divide by 10 if too big, multiply by 10 if too small
    if v>HI:
        out.add(round(v/10))
    if v<LO:
        out.add(round(v*10))
    # also: divide by 100 / multiply by 100 for extreme cases
    if v>HI*10:
        out.add(round(v/100))
    if v<LO/10:
        out.add(round(v*100))
    return [c for c in out if in_range(c)]

conn=psycopg2.connect(**CONN); cur=conn.cursor()

# valid same-zone values -> for neighbor check
cur.execute("SELECT zone_group, zone_reading, value FROM kiln_temperature_readings WHERE value BETWEEN %s AND %s",(LO,HI))
valid=defaultdict(list)
for zg,zr,vv in cur.fetchall():
    valid[(zg,zr)].append(float(vv))

# also overall per-zone mean for "close" threshold
zone_mean={}
for k,vs in valid.items():
    zone_mean[k]=sum(vs)/len(vs)

cur.execute("SELECT id, push_id, zone_group, zone_reading, value FROM kiln_temperature_readings WHERE value > %s OR value < %s",(HI,LO))
flagged=cur.fetchall()
cur.execute("TRUNCATE kiln_temp_correction RESTART IDENTITY")
ins=0
for rid,pid,zg,zr,v in flagged:
    cands=candidates(float(v))
    neigh=valid.get((zg,zr),[])
    mean=zone_mean.get((zg,zr))
    chosen=None; note=""
    if not cands:
        note="no in-range candidate derivable"
    elif not neigh:
        # no neighbor to sanity-check -> propose the smallest-magnitude in-range candidate
        chosen=min(cands, key=lambda x: abs(x-float(v)))
        note=f"no healthy neighbor; propose self-corrected {chosen}"
    else:
        nearest=min(neigh, key=lambda x: abs(x-float(v)))
        # pick candidate closest to the raw magnitude AND check closeness to neighbor
        # prefer candidate that is near a healthy neighbor
        best=None; best_dist=1e18
        for c in cands:
            d=min(abs(c-n) for n in neigh)   # distance to nearest healthy neighbor
            if d<best_dist:
                best_dist=d; best=c
        if mean is not None and best_dist <= max(FAR_RATIO*mean, 50):
            chosen=best
            note=f"raw {v} -> candidate {best} (in-range); close to healthy neighbor (dist {int(best_dist)}) -> propose {best}"
        else:
            note=f"raw {v} -> candidate {best} but FAR from healthy neighbor (dist {int(best_dist)}); needs plant review"
    # 3 nearest healthy same-zone values (regardless of candidate confidence)
    nbrs=sorted(neigh, key=lambda x: abs(x-float(v)))[:3] if neigh else []
    n1=n2=n3=None
    if len(nbrs)>0: n1=nbrs[0]
    if len(nbrs)>1: n2=nbrs[1]
    if len(nbrs)>2: n3=nbrs[2]
    cur.execute("""INSERT INTO kiln_temp_correction(reading_id,push_id,zone_group,zone_reading,raw_value,proposed_value,neighbor_1,neighbor_2,neighbor_3,applied,note)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE,%s)""",
                (rid,pid,zg,zr,v,chosen,n1,n2,n3,note))
    ins+=1
conn.commit()

cur.execute("SELECT count(*), count(proposed_value) FROM kiln_temp_correction")
n,nhas=cur.fetchone()
print(f"Proposed corrections (not applied): {n}, with proposal: {nhas}")
cur.execute("SELECT raw_value, proposed_value, note FROM kiln_temp_correction WHERE raw_value::text LIKE '9450%' LIMIT 3")
for r in cur.fetchall(): print("  ", r)
cur.close(); conn.close()
