"""Descriptive data checks (amendment 2): calls carried over past 04:00,
which the simulator omits, and the share of very short busy times.
Run: python -I code/data_checks.py <data_dir>  ->  facts/data_checks.json"""
import json
import os
import sys

import numpy as np

DATA = sys.argv[1]
SYS = ["NYC_AREA", "NYC_SI", "NYC_BX", "NYC_MN", "NYC_QN", "NYC_BK", "SF"]
out = {}
for s in SYS:
    z = np.load(os.path.join(DATA, f"sys_{s}.npz"))
    arr, svc, off = z["arr"], z["svc"], z["off"]
    D = off.size - 1
    carry = np.array([np.sum(arr[off[d]:off[d + 1]] + svc[off[d]:off[d + 1]] > 24.0) for d in range(D)])
    # mean number in service at 04:30 from the day's own calls (what the simulator sees in hour 0)
    own0 = np.array([np.sum((arr[off[d]:off[d + 1]] <= 0.5) & (arr[off[d]:off[d + 1]] + svc[off[d]:off[d + 1]] > 0.5))
                     for d in range(D)])
    out[s] = {"carry_over_mean": float(carry.mean()), "own_in_service_0430_mean": float(own0.mean()),
              "share_svc_lt5min": float(np.mean(svc < 5 / 60)), "share_svc_lt15min": float(np.mean(svc < 0.25)),
              "median_svc_min": float(np.median(svc) * 60), "mean_svc_min": float(svc.mean() * 60)}
json.dump(out, open("facts/data_checks.json", "w"), indent=1)
for s, v in out.items():
    print(s, {k: round(x, 3) for k, x in v.items()})
