#!/usr/bin/env python3
# Display table: computed PushID (push_seq) for kiln_pushes via Option A.
# push_seq = 1-based chronological rank by (date_jalali, hour). NOT stored.
import sys
sys.path.insert(0, r"C:/Projects/ProductionDatabase")
import kiln_chart as K

pushes = K.ordered_pushes()
n = len(pushes)
print(f"Total pushes: {n}")
print(f"{'PushID':>7} | {'id':>6} | {'date_jalali':>11} | {'hour':>10} | {'wagon':>5}")
print("-"*52)
# first 3
for p in pushes[:3]:
    print(f"{p['push_seq']:>7} | {p['id']:>6} | {p['date_jalali']:>11} | {p['hour'] or '':>10} | {p['incoming_car_id']:>5}")
print("... (middle) ...")
mid = n//2
for p in pushes[mid-1:mid+2]:
    print(f"{p['push_seq']:>7} | {p['id']:>6} | {p['date_jalali']:>11} | {p['hour'] or '':>10} | {p['incoming_car_id']:>5}")
print("... (last 3) ...")
for p in pushes[-3:]:
    print(f"{p['push_seq']:>7} | {p['id']:>6} | {p['date_jalali']:>11} | {p['hour'] or '':>10} | {p['incoming_car_id']:>5}")
print("-"*52)
print(f"FIRST push (PushID=1): {pushes[0]['date_jalali']} {pushes[0]['hour']} wagon={pushes[0]['incoming_car_id']}")
print(f"LAST  push (PushID={n}): {pushes[-1]['date_jalali']} {pushes[-1]['hour']} wagon={pushes[-1]['incoming_car_id']}")
# sanity: PushID sequence is unbroken 1..n
seq_ok = all(p['push_seq']==i for i,p in enumerate(pushes,1))
print(f"PushID unbroken 1..{n}: {seq_ok}")
