#!/usr/bin/env python3
# M5 PILOT — kiln thermal profile charts (SVG, stdlib only).
# Shows: (1) kiln spatial profile at a push, (2) a wagon's thermal history,
# (3) an exited wagon's full 44-slot profile + grade/waste linkage.
# Models the 44-wagon tunnel-kiln queue: each push shifts the queue forward by 1;
# kiln_pushes.incoming_car_id tells which wagon entered; wagon exits 44 pushes later.
# Read-only over v_clean_* views + kiln_pushes. Pilot for design/fixing only.

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, urllib.parse, psycopg2, sys, html, math

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")

# 44-slot layout (position -> (label, zone_group, zone_reading or None))
# W slots have no direct sensor; they get interpolated from neighbouring zones.
SLOTS = [
    (1,  "اگزوز",         "exhaust",     "exhaust"),
    (2,  "W2",            None, None),
    (3,  "پیش‌گرما۱",     "preheat",     "01"),
    (4,  "W4",            None, None),
    (5,  "پیش‌گرما۲",     "preheat",     "02"),
    (6,  "W6",            None, None),
    (7,  "W7",            None, None),
    (8,  "W8",            None, None),
    (9,  "ترموستات",     "thermostat",  "thermostat"),
    (10, "W10",           None, None),
    (11, "W11",           None, None),
    (12, "W12",           None, None),
    (13, "W13",           None, None),
    (14, "W14",           None, None),
    (15, "زون۰",          "zone",        "00"),
    (16, "W16",           None, None),
    (17, "زون۱",          "zone",        "01"),
    (18, "زون۲",          "zone",        "02"),
    (19, "W19",           None, None),
    (20, "زون۳",          "zone",        "03"),
    (21, "زون۴",          "zone",        "04"),
    (22, "W22",           None, None),
    (23, "زون۵",          "zone",        "05"),
    (24, "زون۶",          "zone",        "06"),
    (25, "W25",           None, None),
    (26, "زون۷",          "zone",        "07"),
    (27, "W27",           None, None),
    (28, "رپید۱",         "rapid",       "01"),
    (29, "رپید۲",         "rapid",       "02"),
    (30, "W30",           None, None),
    (31, "باتومA",        "bottom",      "A"),
    (32, "W32",           None, None),
    (33, "باتوم۱",        "bottom",      "01"),
    (34, "W34",           None, None),
    (35, "W35",           None, None),
    (36, "باتومB",        "bottom",      "B"),
    (37, "W37",           None, None),
    (38, "باتوم۲",        "bottom",      "B2"),
    (39, "W39",           None, None),
    (40, "W40",           None, None),
    (41, "W41",           None, None),
    (42, "W42",           None, None),
    (43, "W43",           None, None),
    (44, "W44",           None, None),
]
QUEUE_LEN = 44

def db():
    return psycopg2.connect(**CONN)

def rows_to_dicts(cur):
    cols=[d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# ---- ordered push timeline (by date_jalali + hour) -------------------------
def ordered_pushes():
    c=db(); cur=c.cursor()
    cur.execute("""SELECT id, incoming_car_id, date_jalali, hour, pushing_time_min
                  FROM kiln_pushes
                  WHERE incoming_car_id IS NOT NULL
                  ORDER BY date_jalali, hour""")
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def push_time_str(p):
    return f"{p['date_jalali']} {p.get('hour') or ''}"

# ---- kiln spatial profile at a push ---------------------------------------
def kiln_profile_at_push(push_id):
    c=db(); cur=c.cursor()
    cur.execute("""SELECT zone_group, zone_reading, value
                  FROM kiln_temperature_readings WHERE push_id=%s""", (push_id,))
    raw=rows_to_dicts(cur); cur.close(); c.close()
    val={(r["zone_group"], r["zone_reading"]): float(r["value"]) for r in raw}
    # build 44-slot series
    series=[]
    for pos,label,zg,zr in SLOTS:
        if zg:
            v=val.get((zg,zr))
            series.append([pos,label, v if v is not None else None])
        else:
            series.append([pos,label, None])  # W slot: no sensor, interpolate linearly
    # Linear interpolation for W (sensor-less) slots, per:
    #   T_i = T_0 + (i / n) * (T_n - T_0)
    # where T_0/T_n are the bounding sensor slots and n = slots between them.
    # Slots are equidistant (step 1), so i is the count of slots from T_0.
    i=0
    while i < len(series):
        if series[i][2] is not None:
            i+=1; continue
        # find previous known (j) and next known (k)
        j=i-1
        while j>=0 and series[j][2] is None: j-=1
        k=i+1
        while k<len(series) and series[k][2] is None: k+=1
        if j<0 or k>=len(series) or series[j][2] is None or series[k][2] is None:
            # no two bounding sensors -> leave as None (will be dropped in chart)
            i+=1; continue
        n=k-j  # number of segments between the two sensors
        T0=series[j][2]; Tn=series[k][2]
        for m in range(j+1, k):
            frac=(m-j)/n
            series[m][2]=T0 + frac*(Tn-T0)
        i=k
    # Trailing sensor-less slots after the last sensor (W39..W44 at kiln exit).
    # Owner directive: W44 (final wagon, no sensor) is taken as a fixed mean of
    # 70C; intermediate W-slots are linearly interpolated between the last known
    # sensor value (T0 at slot j) and W44=70 (at the final slot), per
    #   T_i = T0 + (i/n)*(70 - T0),  n = (final_slot - j)
    LAST_SLOT = series[-1][0]          # 44
    W44_TEMP = 70.0
    last_known=None; last_pos=None
    for s in series:
        if s[2] is not None:
            last_known=s[2]; last_pos=s[0]
    if last_known is not None and last_pos < LAST_SLOT:
        n = LAST_SLOT - last_pos
        T0 = last_known
        for s in series:
            if s[2] is None and last_pos < s[0] <= LAST_SLOT:
                frac = (s[0]-last_pos)/n
                s[2] = T0 + frac*(W44_TEMP - T0)
    return [(s[0], s[1], s[2]) for s in series]  # list of (pos,label,temp)


# ---- wagon thermal history ------------------------------------------------
def wagon_history(wagon_no):
    """For each push where this wagon was inside the kiln (entry .. entry+43),
    report the temp at the slot the wagon occupied (its zone at that time)."""
    pushes=ordered_pushes()
    entries=[i for i,p in enumerate(pushes) if str(p["incoming_car_id"])==str(wagon_no)]
    if not entries:
        return []
    # Preload all readings for the pushes this wagon touches (one query, one conn).
    max_idx=min(max(ei+QUEUE_LEN-1 for ei in entries), len(pushes)-1)
    pid_list=[pushes[i]["id"] for i in range(min(entries), max_idx+1)]
    c=db(); cur=c.cursor()
    cur.execute("""SELECT push_id, zone_group, zone_reading, value
                  FROM kiln_temperature_readings WHERE push_id = ANY(%s)""", (pid_list,))
    rd={}
    for r in cur.fetchall():
        rd.setdefault(r[0], {})[(r[1], r[2])] = float(r[3])
    cur.close(); c.close()
    hist=[]
    for ei in entries:
        for k in range(QUEUE_LEN):
            idx=ei+k
            if idx>=len(pushes): break
            p=pushes[idx]; pos=k+1; slot=SLOTS[pos-1]
            if slot[2]:
                t=rd.get(p["id"], {}).get((slot[2], slot[3]))
            else:
                t=None
            hist.append({"push_seq": idx+1, "push_id": p["id"],
                         "date": p["date_jalali"], "slot": pos,
                         "slot_label": slot[1], "temp": t,
                         "is_exit": (k==QUEUE_LEN-1)})
    return hist

def wagon_exit_profile(wagon_no):
    """Last push where wagon was inside kiln -> full 44-slot profile + grade/waste."""
    pushes=ordered_pushes()
    entries=[i for i,p in enumerate(pushes) if str(p["incoming_car_id"])==str(wagon_no)]
    if not entries:
        return None
    ei=entries[-1]
    exit_idx=ei+QUEUE_LEN-1
    if exit_idx>=len(pushes): exit_idx=len(pushes)-1
    exit_push=pushes[exit_idx]
    series=kiln_profile_at_push(exit_push["id"])
    # grade/waste for linkage (by date + product if available)
    c=db(); cur=c.cursor()
    cur.execute("""SELECT grade1, grade2, waste, total, product_code
                  FROM v_clean_packing
                  WHERE date_jalali=%s LIMIT 1""", (exit_push["date_jalali"],))
    gr=rows_to_dicts(cur); cur.close(); c.close()
    return {"wagon_no": wagon_no, "exit_push_id": exit_push["id"],
            "exit_date": exit_push["date_jalali"],
            "series": series, "grade": gr[0] if gr else None}

# ---- SVG rendering ---------------------------------------------------------
def svg_kiln(series, title):
    W,H=900,360; m=50
    temps=[s[2] for s in series if s[2] is not None]
    tmin,tmax=(min(temps),max(temps)) if temps else (0,1000)
    pad=(tmax-tmin)*0.1 or 50; tmin-=pad; tmax+=pad
    def X(i): return m+(W-2*m)*(i/(QUEUE_LEN-1))
    def Y(v): return H-m-(H-2*m)*((v-tmin)/(tmax-tmin))
    pts=" ".join(f"{X(i):.1f},{Y(s[2]):.1f}" for i,s in enumerate(series) if s[2] is not None)
    dots="".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(s[2]):.1f}" r="3" fill="#63b3ed">'+
        f'<title>{html.escape(s[1])}: {s[2]:.0f}°C</title></circle>'
        for i,s in enumerate(series) if s[2] is not None)
    labels="".join(
        f'<text x="{X(i):.1f}" y="{H-m+14}" font-size="8" fill="#a0aec0" '+
        f'transform="rotate(60 {X(i):.1f} {H-m+14})" text-anchor="start">{html.escape(s[1])}</text>'
        for i,s in enumerate(SLOTS))
    # zone background bands
    bands=""
    for i,(pos,label,zg,zr) in enumerate(SLOTS):
        col="#1a202c" if zg else "#141923"
        bands+=f'<rect x="{X(i)-3:.1f}" y="{m}" width="6" height="{H-2*m}" fill="{col}"/>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" dir="ltr">
<rect width="{W}" height="{H}" fill="#0f1419"/>
<text x="{m}" y="22" fill="#4fd1c5" font-size="15">{html.escape(title)}</text>
<line x1="{m}" y1="{Y(tmin):.1f}" x2="{W-m}" y2="{Y(tmin):.1f}" stroke="#2d3748"/>
<line x1="{m}" y1="{Y(tmax):.1f}" x2="{W-m}" y2="{Y(tmax):.1f}" stroke="#2d3748"/>
<text x="{W-m}" y="{Y(tmax)-4:.1f}" fill="#718096" font-size="10">{tmax:.0f}°C</text>
<text x="{W-m}" y="{Y(tmin)+12:.1f}" fill="#718096" font-size="10">{tmin:.0f}°C</text>
{bands}
<polyline points="{pts}" fill="none" stroke="#4fd1c5" stroke-width="2"/>
{dots}
{labels}
</svg>'''
    return svg

def svg_wagon(hist, title):
    if not hist: return "<p>واگن یافت نشد</p>"
    W,H=900,360; m=50
    temps=[h["temp"] for h in hist if h["temp"] is not None]
    tmin,tmax=(min(temps),max(temps)) if temps else (0,1000)
    pad=(tmax-tmin)*0.1 or 50; tmin-=pad; tmax+=pad
    n=len(hist)
    def X(i): return m+(W-2*m)*(i/(n-1)) if n>1 else m
    def Y(v): return H-m-(H-2*m)*((v-tmin)/(tmax-tmin))
    pts=" ".join(f"{X(i):.1f},{Y(h['temp']):.1f}" for i,h in enumerate(hist) if h["temp"] is not None)
    dots="".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(h["temp"]):.1f}" r="3" fill="#f6ad55">'+
        f'<title>push {h["push_seq"]} / slot {h["slot"]} ({html.escape(h["slot_label"])}): {h["temp"]:.0f}°C'+
        (' [EXIT]' if h["is_exit"] else '')+'</title></circle>'
        for i,h in enumerate(hist) if h["temp"] is not None)
    exdots="".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(h["temp"]):.1f}" r="5" fill="none" stroke="#fc8181" stroke-width="2"/>'
        for i,h in enumerate(hist) if h["is_exit"] and h["temp"] is not None)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" dir="ltr">
<rect width="{W}" height="{H}" fill="#0f1419"/>
<text x="{m}" y="22" fill="#4fd1c5" font-size="15">{html.escape(title)}</text>
<line x1="{m}" y1="{Y(tmin):.1f}" x2="{W-m}" y2="{Y(tmin):.1f}" stroke="#2d3748"/>
<line x1="{m}" y1="{Y(tmax):.1f}" x2="{W-m}" y2="{Y(tmax):.1f}" stroke="#2d3748"/>
<text x="{W-m}" y="{Y(tmax)-4:.1f}" fill="#718096" font-size="10">{tmax:.0f}°C</text>
<text x="{W-m}" y="{Y(tmin)+12:.1f}" fill="#718096" font-size="10">{tmin:.0f}°C</text>
<polyline points="{pts}" fill="none" stroke="#f6ad55" stroke-width="2"/>
{dots}
{exdots}
<text x="{m}" y="{H-12}" fill="#718096" font-size="10">محور X = توالی پوش (ورود → خروج). نقطه قرمز = لحظه خروج</text>
</svg>'''
    return svg

# ---- HTTP ----------------------------------------------------------------
class H(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        if isinstance(payload,(dict,list)):
            body=json.dumps(payload,ensure_ascii=False,default=str).encode("utf-8")
        else:
            body=payload.encode("utf-8") if isinstance(payload,str) else payload
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u=urllib.parse.urlparse(self.path); p=urllib.parse.parse_qs(u.query)
        def gi(k,d):
            try: return int(p.get(k,[d])[0])
            except: return d
        def gs(k,d):
            return p.get(k,[d])[0]
        try:
            if u.path=="/kiln-profile":
                pid=gi("push_id",1); s=kiln_profile_at_push(pid)
                self._send(200,{"push_id":pid,"series":[{"pos":x[0],"label":x[1],"temp":x[2]} for x in s]})
            elif u.path=="/kiln-chart":
                pid=gi("push_id",1); s=kiln_profile_at_push(pid)
                self._send(200, svg_kiln(s, f"پروفایل کوره — push {pid}"), "image/svg+xml; charset=utf-8")
            elif u.path=="/wagon-profile":
                wn=gs("wagon_no","1"); h=wagon_history(wn)
                self._send(200,{"wagon_no":wn,"history":h})
            elif u.path=="/wagon-chart":
                wn=gs("wagon_no","1"); h=wagon_history(wn)
                self._send(200, svg_wagon(h, f"سیر حرارتی واگن {wn}"), "image/svg+xml; charset=utf-8")
            elif u.path=="/wagon-exit-chart":
                wn=gs("wagon_no","1"); e=wagon_exit_profile(wn)
                if not e: self._send(404,{"error":"wagon not found"})
                else:
                    svg=svg_kiln(e["series"], f"پروفایل خروج واگن {wn} — push {e['exit_push_id']} ({e['exit_date']})")
                    grade=e.get("grade") or {}
                    info=f"<p>واگن {wn} در push {e['exit_push_id']} ({e['exit_date']}) خارج شد. "+\
                         (f"grade1={grade.get('grade1')}, waste={grade.get('waste')}, total={grade.get('total')}" if grade else "ردیف بسته‌بندی مرتبط یافت نشد")
                    self._send(200, f"<div dir='rtl'>{info}</div>{svg}", "text/html; charset=utf-8")
            else:
                self._send(404,{"error":"not found","available":["/kiln-profile","/kiln-chart","/wagon-profile","/wagon-chart","/wagon-exit-chart"]})
        except Exception as e:
            self._send(500,{"error":str(e)})
    def log_message(self,*a): pass

if __name__=="__main__":
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8001
    srv=ThreadingHTTPServer(("0.0.0.0",port),H)
    print(f"Kiln chart pilot on http://localhost:{port}")
    srv.serve_forever()
