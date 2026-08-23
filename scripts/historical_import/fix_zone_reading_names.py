#!/usr/bin/env python3
# Fix mis-named zone_reading for exhaust/thermostat groups.
# exhaust.exhaust -> exhaust.temp, thermostat.thermostat -> thermostat.temp.
# Only renames the zone_reading label; values untouched. Idempotent.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
fixes=[("exhaust","exhaust","temp"),("thermostat","thermostat","temp")]
total=0
for grp,bad,good in fixes:
    cur.execute("UPDATE kiln_temperature_readings SET zone_reading=%s WHERE zone_group=%s AND zone_reading=%s",
                (good, grp, bad))
    n=cur.rowcount; total+=n
    print(f"  {grp}.{bad} -> {grp}.{good}: {n} rows")
c.commit(); cur.close(); c.close()
print(f"TOTAL renamed: {total}")
