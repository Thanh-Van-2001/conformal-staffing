"""Amendment 4 (exploratory, PLAN.md): the calibration days' shares of
delayed calls on the theta grid (SCD's base load), which conformal risk
control with a continuous loss (CRC-share) needs and the first run did not
store. QT and SCD-I need no new simulation.

Run: python -I exp_amend4.py <data_dir> <out_dir> [workers]
Writes <out_dir>/amend4/<system>_<origin>_<n>.npz.
"""
import os
import sys

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(v, "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
from multiprocessing import Pool

import numpy as np

import exp
import sim


def run_task(args):
    data, out, name, o, n = args
    path = os.path.join(out, "amend4", f"{name}_{o:04d}_{n:03d}.npz")
    if os.path.exists(path):
        return path
    t0 = time.time()
    S = exp.load(data, name)
    tr_idx = np.arange(o - n, o)
    h = n // 2
    base, cal = exp.sub(S, tr_idx[:h]), exp.sub(S, tr_idx[h:])
    m_half = sim.busy_profile(base["arr"], base["svc"], base["off"], exp.P, exp.L)
    ca, cb, _ = exp.grid_fracs(cal, m_half)
    # consistency with the first run: the scores implied by these shares must equal the stored ones
    z = np.load(os.path.join(out, f"{name}_{o:04d}_{n:03d}.npz"))
    same = all(np.array_equal(exp.scores(f_, exp.BETA[tg])[0], z[f"cal_score_{tg}"]) for tg, f_ in (("A", ca), ("B", cb)))
    tmp = path + ".part.npz"
    np.savez_compressed(tmp, cal_fracA_half=ca.astype(np.float32), cal_fracB_half=cb.astype(np.float32),
                        scores_reproduced=np.array(same), secs=np.array(time.time() - t0))
    os.replace(tmp, path)
    return path


def main():
    data, out = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    os.makedirs(os.path.join(out, "amend4"), exist_ok=True)
    tasks = []
    for name in exp.SYSTEMS:
        D = exp.load(data, name)["off"].size - 1
        for n in exp.NS:
            for o in range(exp.FIRST_ORIGIN, D - exp.TEST + 1, exp.STEP):
                tasks.append((data, out, name, o, n))
    order = {s: i for i, s in enumerate(["NYC_BK", "NYC_MN", "NYC_BX", "NYC_QN", "SF", "NYC_SI", "NYC_AREA"])}
    tasks.sort(key=lambda t: (order.get(t[2], 9), -t[4]))
    t0 = time.time()
    done = 0
    with Pool(workers) as pool:
        for _ in pool.imap_unordered(run_task, tasks):
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"{done}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    with open(os.path.join(out, "amend4", "RUN_INFO.json"), "w") as f:
        json.dump({"tasks": len(tasks), "secs": time.time() - t0, "workers": workers}, f)


if __name__ == "__main__":
    main()
