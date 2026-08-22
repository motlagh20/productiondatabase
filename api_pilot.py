#!/usr/bin/env python3
# M5 PILOT — read-only API over the clean data layer (v_clean_* views).
# PURPOSE: design + contract validation ONLY (owner-approved: pilot for design/fixing,
# NOT the final product). The final enterprise product will be Django+DRF/React/PostgreSQL
# per ADR-0001/0002; this server defines the *response contract* that DRF will mirror.
#
# Zero external deps (stdlib http.server + psycopg2). Run:
#   python api_pilot.py
# Endpoints (raw rows):
#   GET /health
#   GET /packing?limit=50&offset=0
#   GET /kiln-temps?limit=50&offset=0
#   GET /dryer-readings?limit=50&offset=0
#   GET /anomalies?limit=50&offset=0        (flag-only rows needing ledger review)
#   GET /metrics                            (counts + correction coverage)
# Analytic endpoints (aggregated, analysis-friendly):
#   GET /packing/by-month?year=1398         (per-month totals + grade1 + waste)
#   GET /packing/by-product                 (per composite product: mold x glaze)
#   GET /kiln-temps/by-zone                 (mean temp per zone_group.zone_reading)
# Dashboard:
#   GET /                                  (simple HTML summary + links)
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, urllib.parse, psycopg2, sys, html

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")

def db():
    return psycopg2.connect(**CONN)

def rows_to_dicts(cur):
    cols=[d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# --- raw row endpoints -----------------------------------------------------
def q_packing(limit, offset):
    c=db(); cur=c.cursor()
    cur.execute("SELECT * FROM v_clean_packing ORDER BY date_jalali LIMIT %s OFFSET %s", (limit, offset))
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_kiln(limit, offset):
    c=db(); cur=c.cursor()
    cur.execute("SELECT * FROM v_clean_kiln_temps ORDER BY push_id LIMIT %s OFFSET %s", (limit, offset))
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_dryer(limit, offset):
    c=db(); cur=c.cursor()
    cur.execute("SELECT * FROM v_clean_dryer_readings ORDER BY operation_id LIMIT %s OFFSET %s", (limit, offset))
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_anomalies(limit, offset):
    c=db(); cur=c.cursor()
    cur.execute("SELECT * FROM v_open_anomalies LIMIT %s OFFSET %s", (limit, offset))
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_metrics():
    c=db(); cur=c.cursor()
    m={}
    for t,sql in [
        ("packing_total", "SELECT count(*) FROM v_clean_packing"),
        ("kiln_total", "SELECT count(*) FROM v_clean_kiln_temps"),
        ("dryer_total", "SELECT count(*) FROM v_clean_dryer_readings"),
        ("anomalies_open", "SELECT count(*) FROM v_open_anomalies"),
        ("kiln_corrected", "SELECT count(*) FROM v_clean_kiln_temps WHERE was_corrected"),
        ("dryer_corrected", "SELECT count(*) FROM v_clean_dryer_readings WHERE was_corrected"),
        ("wagon_flagged", "SELECT count(*) FROM v_clean_packing WHERE wagon_flagged"),
    ]:
        cur.execute(sql); m[t]=cur.fetchone()[0]
    cur.close(); c.close(); return m

# --- analytic endpoints ----------------------------------------------------
def q_packing_by_month(year):
    c=db(); cur=c.cursor()
    cur.execute("""
        SELECT split_part(date_jalali,'.',1) AS yr,
               split_part(date_jalali,'.',2) AS mo,
               count(*) AS rows,
               sum(total) AS total_sum,
               sum(grade1) AS grade1_sum,
               sum(grade2) AS grade2_sum,
               sum(waste) AS waste_sum,
               round(avg(total),1) AS total_avg
        FROM v_clean_packing
        WHERE split_part(date_jalali,'.',1) = %s
        GROUP BY 1,2 ORDER BY 2
    """, (str(year),))
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_packing_by_product():
    c=db(); cur=c.cursor()
    cur.execute("""
        SELECT coalesce(mold_type,'?') AS mold_type,
               coalesce(glaze,'?') AS glaze,
               count(*) AS rows,
               sum(total) AS total_sum,
               sum(grade1) AS grade1_sum,
               sum(waste) AS waste_sum,
               round(avg(total),1) AS total_avg
        FROM v_clean_packing
        GROUP BY 1,2 ORDER BY rows DESC
    """)
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

def q_kiln_by_zone():
    c=db(); cur=c.cursor()
    cur.execute("""
        SELECT zone_group, zone_reading,
               count(*) AS n,
               round(avg(value),1) AS mean_temp,
               round(min(value),1) AS min_temp,
               round(max(value),1) AS max_temp
        FROM v_clean_kiln_temps
        GROUP BY 1,2 ORDER BY 1,2
    """)
    d=rows_to_dicts(cur); cur.close(); c.close(); return d

# --- HTML dashboard --------------------------------------------------------
def dashboard_html():
    m=q_metrics()
    by_prod=q_packing_by_product()[:10]
    by_zone=q_kiln_by_zone()
    def row(d):
        return "<tr>"+"".join(f"<td>{html.escape(str(x))}</td>" for x in d.values())+"</tr>"
    def head(rows):
        return "<tr>"+"".join(f"<th>{html.escape(str(k))}</th>" for k in (rows[0].keys() if rows else []))+"</tr>"
    prod_tbl="<table class='t'>"+head(by_prod)+"".join(row(d) for d in by_prod)+"</table>"
    zone_tbl="<table class='t'>"+head(by_zone)+"".join(row(d) for d in by_zone)+"</table>"
    return f"""<!doctype html><html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<title>M5 Pilot Dashboard</title>
<style>
 body{{font-family:system-ui,Tahoma,sans-serif;margin:0;background:#0f1419;color:#e6e6e6;padding:24px}}
 h1{{color:#4fd1c5}} h2{{color:#63b3ed;border-bottom:1px solid #2d3748;padding-bottom:6px}}
 a{{color:#63b3ed;text-decoration:none}} a:hover{{text-decoration:underline}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
 .card{{background:#1a202c;border:1px solid #2d3748;border-radius:8px;padding:14px 18px;min-width:120px}}
 .card .n{{font-size:24px;font-weight:700;color:#4fd1c5}} .card .l{{font-size:12px;color:#a0aec0}}
 .t{{border-collapse:collapse;width:100%;margin-top:8px;font-size:13px}}
 .t th,.t td{{border:1px solid #2d3748;padding:5px 9px;text-align:right}}
 .t th{{background:#2d3748;color:#e6e6e6}}
 .links a{{display:inline-block;margin:4px 8px 4px 0;background:#1a202c;border:1px solid #2d3748;border-radius:6px;padding:6px 12px}}
</style></head><body>
<h1>M5 Pilot — Manufacturing Analytics</h1>
<div class='cards'>
 <div class='card'><div class='n'>{m['packing_total']:,}</div><div class='l'>بسته‌بندی</div></div>
 <div class='card'><div class='n'>{m['kiln_total']:,}</div><div class='l'>قرائت کوره</div></div>
 <div class='card'><div class='n'>{m['dryer_total']:,}</div><div class='l'>قرائت خشک‌کن</div></div>
 <div class='card'><div class='n'>{m['anomalies_open']:,}</div><div class='l'>موارد باز</div></div>
 <div class='card'><div class='n'>{m['wagon_flagged']:,}</div><div class='l'>واگن پرچم‌دار</div></div>
</div>
<h2>API Endpoints</h2>
<div class='links'>
 <a href='/packing?limit=10'>/packing</a>
 <a href='/kiln-temps?limit=10'>/kiln-temps</a>
 <a href='/dryer-readings?limit=10'>/dryer-readings</a>
 <a href='/anomalies?limit=10'>/anomalies</a>
 <a href='/metrics'>/metrics</a>
 <a href='/packing/by-month?year=1398'>/packing/by-month?year=1398</a>
 <a href='/packing/by-product'>/packing/by-product</a>
 <a href='/kiln-temps/by-zone'>/kiln-temps/by-zone</a>
</div>
<h2>Top Products (mold × glaze)</h2>
{prod_tbl}
<h2>Kiln Temp by Zone</h2>
{zone_tbl}
<p style='color:#718096;font-size:12px'>Pilot only — final product = Django+DRF/React/PostgreSQL (ADR-0001/0002)</p>
</body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        if isinstance(payload, (dict, list)):
            body=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        else:
            body=payload.encode("utf-8") if isinstance(payload, str) else payload
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u=urllib.parse.urlparse(self.path)
        p=urllib.parse.parse_qs(u.query)
        def gi(k,d):
            try: return int(p.get(k,[d])[0])
            except: return d
        def gs(k,d):
            return p.get(k,[d])[0]
        try:
            if u.path=="/health":
                self._send(200, {"status":"ok","note":"M5 pilot read-only API"})
            elif u.path=="/packing":
                self._send(200, {"endpoint":"/packing","data":q_packing(gi("limit",50),gi("offset",0))})
            elif u.path=="/kiln-temps":
                self._send(200, {"endpoint":"/kiln-temps","data":q_kiln(gi("limit",50),gi("offset",0))})
            elif u.path=="/dryer-readings":
                self._send(200, {"endpoint":"/dryer-readings","data":q_dryer(gi("limit",50),gi("offset",0))})
            elif u.path=="/anomalies":
                self._send(200, {"endpoint":"/anomalies","data":q_anomalies(gi("limit",50),gi("offset",0))})
            elif u.path=="/metrics":
                self._send(200, {"endpoint":"/metrics","data":q_metrics()})
            elif u.path=="/packing/by-month":
                self._send(200, {"endpoint":"/packing/by-month","year":gs("year",""),"data":q_packing_by_month(gs("year",""))})
            elif u.path=="/packing/by-product":
                self._send(200, {"endpoint":"/packing/by-product","data":q_packing_by_product()})
            elif u.path=="/kiln-temps/by-zone":
                self._send(200, {"endpoint":"/kiln-temps/by-zone","data":q_kiln_by_zone()})
            elif u.path=="/" or u.path=="/index.html":
                self._send(200, dashboard_html(), "text/html; charset=utf-8")
            else:
                self._send(404, {"error":"not found","available":["/","/health","/packing","/kiln-temps","/dryer-readings","/anomalies","/metrics","/packing/by-month","/packing/by-product","/kiln-temps/by-zone"]})
        except Exception as e:
            self._send(500, {"error":str(e)})

    def log_message(self, *a): pass

if __name__=="__main__":
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8000
    srv=ThreadingHTTPServer(("0.0.0.0", port), H)
    print(f"M5 pilot API on http://localhost:{port}  (ctrl-c to stop)")
    srv.serve_forever()
