"""Conformal staffing experiment (see PLAN.md, including amendment 1).

For every system, origin o and training size n this script evaluates the
square-root plan family c(theta) on the theta grid for
  - the calibration days (base = first n/2 training days),
  - all n training days (base = all n days, for EMP and ORACLE),
  - the 20 test days under both bases,
and simulates the test days under the SIPP, MOL and ACA plans. The rules
(SCD, EMP, ORACLE, ACI) are applied afterwards in analyze.py, so every rule
sees exactly the same simulated outcomes.

Run: python -I exp.py <data_dir> <out_dir> [workers] [systems...] [--smoke]
"""
import os
import sys

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(v, "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import math
import time
from multiprocessing import Pool

import numpy as np

import sim

P, L, TEST = 24, 1.0, 20
NS = [40, 80, 160]
FIRST_ORIGIN, STEP = 160, 20
GRID = np.round(np.arange(-2.0, 10.0 + 1e-9, 0.05), 2)
G = GRID.size
BETA = {"A": 0.05, "B": 0.01}  # A: fraction delayed (wait > 0); B: fraction waiting > 10 min
T_B = 10.0 / 60.0
ALPHAS = [0.05, 0.10, 0.20]
SYSTEMS = ["NYC_AREA", "NYC_SI", "NYC_BX", "NYC_MN", "NYC_QN", "NYC_BK", "SF"]
EPS = 1e-12

_CACHE = {}


def load(data, name):
    if name not in _CACHE:
        z = np.load(os.path.join(data, f"sys_{name}.npz"))
        _CACHE[name] = {"dates": z["dates"], "counts": z["counts"], "arr": z["arr"],
                        "svc": z["svc"], "off": z["off"]}
    return _CACHE[name]


def sub(S, idx):
    a = [S["arr"][S["off"][i]:S["off"][i + 1]] for i in idx]
    s = [S["svc"][S["off"][i]:S["off"][i + 1]] for i in idx]
    off = np.zeros(len(idx) + 1, dtype=np.int64)
    off[1:] = np.cumsum([x.size for x in a])
    return {"arr": np.concatenate(a), "svc": np.concatenate(s), "off": off,
            "counts": S["counts"][np.asarray(idx)]}


def plan_theta(m, th):
    return np.maximum(1, np.ceil(m + th * np.sqrt(m))).astype(np.int64)


def fracs(D, c):
    st = sim.per_day_stats(D["arr"], D["svc"], D["off"], np.asarray(c, dtype=np.int64), L)
    return st[:, 1] / st[:, 3], st[:, 2] / st[:, 3]


def grid_fracs(D, m):
    """Fractions delayed (A) and waiting > 10 min (B) for every day of D under
    every grid plan; distinct plans are simulated once. Returns (nd x G) x 2
    and unit-hours per grid point."""
    key, uniq, idx = {}, [], np.empty(G, dtype=np.int64)
    for g, th in enumerate(GRID):
        c = plan_theta(m, th)
        k = c.tobytes()
        if k not in key:
            key[k] = len(uniq)
            uniq.append(c)
        idx[g] = key[k]
    nd = D["off"].size - 1
    fa = np.empty((len(uniq), nd))
    fb = np.empty((len(uniq), nd))
    for u, c in enumerate(uniq):
        fa[u], fb[u] = fracs(D, c)
    uh = np.array([uniq[idx[g]].sum() * L for g in range(G)])
    return fa[idx].T, fb[idx].T, uh


def scores(frac, beta):
    """Score index per day: first grid index from which the day meets the
    target at every larger grid value (G = never). Also the number of days
    whose 'meets' sequence is not monotone in theta."""
    meets = frac <= beta + EPS
    allfrom = np.flip(np.logical_and.accumulate(np.flip(meets, axis=1), axis=1), axis=1)
    sc = np.where(allfrom.any(axis=1), allfrom.argmax(axis=1), G)
    nonmono = int((meets & ~allfrom).any(axis=1).sum())
    return sc.astype(np.int16), nonmono


def erlang_c(c, a):
    if a <= 0:
        return 0.0
    b = 1.0
    for k in range(1, c + 1):
        b = a * b / (k + a * b)
    return c * b / (c - a * (1.0 - b))


def ec_staff(a, beta, t, es):
    c = max(1, int(math.floor(a)) + 1)
    while True:
        p = erlang_c(c, a) * math.exp(-(c - a) * t / es)
        if p <= beta:
            return c
        c += 1


def ec_plan(load, target, es):
    t = 0.0 if target == "A" else T_B
    return np.array([ec_staff(float(a), BETA[target], t, es) for a in load], dtype=np.int64)


def kernel(svc):
    """K_j = P(call arriving uniformly in hour p - j is in service at the
    midpoint of hour p), from busy times svc (hours)."""
    K = [float(np.clip(svc, 0.0, 0.5).mean())]
    j = 1
    while j - 0.5 < svc.max():
        K.append(float(np.clip(svc - (j - 0.5), 0.0, 1.0).mean()))
        j += 1
    return np.array(K)


def load_from_arrivals(U, K):
    m = np.zeros(P)
    for p in range(P):
        for j in range(min(K.size, p + 1)):
            m[p] += K[j] * U[p - j]
    return m


def run_task(args):
    data, out, name, o, n = args
    path = os.path.join(out, f"{name}_{o:04d}_{n:03d}.npz")
    if os.path.exists(path):
        return path
    t0 = time.time()
    S = load(data, name)
    tr_idx = np.arange(o - n, o)
    h = n // 2
    base, cal, al, te = (sub(S, tr_idx[:h]), sub(S, tr_idx[h:]), sub(S, tr_idx), sub(S, np.arange(o, o + TEST)))
    m_half = sim.busy_profile(base["arr"], base["svc"], base["off"], P, L)
    m_all = sim.busy_profile(al["arr"], al["svc"], al["off"], P, L)
    res = {"grid": GRID, "m_half": m_half, "m_all": m_all}
    nonmono = 0
    # half base: calibration and test days
    ca, cb, uh_half = grid_fracs(cal, m_half)
    ta, tb, _ = grid_fracs(te, m_half)
    for tg, cf, tf in (("A", ca, ta), ("B", cb, tb)):
        sc, nm = scores(cf, BETA[tg])
        res[f"cal_score_{tg}"] = sc
        res[f"test_meets_half_{tg}"] = np.packbits(tf <= BETA[tg] + EPS, axis=1)
        nonmono += nm
    res["test_fracA_half"] = ta.astype(np.float32)
    res["uh_half"] = uh_half
    # all-n base: training days (EMP) and test days (EMP, ORACLE)
    aa, ab, uh_all = grid_fracs(al, m_all)
    ta2, tb2, _ = grid_fracs(te, m_all)
    for tg, af, tf in (("A", aa, ta2), ("B", ab, tb2)):
        sc, nm = scores(af, BETA[tg])
        res[f"train_score_{tg}"] = sc
        res[f"test_meets_all_{tg}"] = np.packbits(tf <= BETA[tg] + EPS, axis=1)
        nonmono += nm
    res["test_fracA_all"] = ta2.astype(np.float32)
    res["uh_all"] = uh_all
    # practitioner rules on all n days
    es_all = float(al["svc"].mean())
    lam_all = al["counts"].mean(axis=0) / L
    for tg in ("A", "B"):
        for rule, ld in (("SIPP", lam_all * es_all), ("MOL", m_all)):
            c = ec_plan(ld, tg, es_all)
            fa_, fb_ = fracs(te, c)
            res[f"{rule}_{tg}_plan"] = c
            res[f"{rule}_{tg}_test_frac"] = np.stack([fa_, fb_])
    # ACA: conformal envelope of hourly arrivals (base half), MOL plug-in
    lam_h = base["counts"].mean(axis=0) / L
    sd = np.sqrt(np.maximum(lam_h, 1e-9))
    s_cal = np.sort(((cal["counts"] - lam_h) / sd).max(axis=1))
    K = kernel(base["svc"])
    es_h = float(base["svc"].mean())
    for al_ in ALPHAS:
        k = math.ceil((h + 1) * (1 - al_))
        q = s_cal[k - 1] if k <= h else s_cal[-1]
        U = np.maximum(lam_h + q * sd, 0.0)
        mU = load_from_arrivals(U, K)
        for tg in ("A", "B"):
            c = ec_plan(mU, tg, es_h)
            fa_, fb_ = fracs(te, c)
            res[f"ACA_{al_:.2f}_{tg}_plan"] = c
            res[f"ACA_{al_:.2f}_{tg}_test_frac"] = np.stack([fa_, fb_])
            res[f"ACA_{al_:.2f}_flag"] = np.array(k > h)
    res["calls_test"] = te["counts"].sum(axis=1)
    res["calls_cal"] = cal["counts"].sum(axis=1)
    res["calls_train"] = al["counts"].sum(axis=1)
    res["nonmono"] = np.array(nonmono)
    res["test_start"] = np.array(str(S["dates"][o]))
    res["secs"] = np.array(time.time() - t0)
    tmp = path + ".part.npz"
    np.savez_compressed(tmp, **res)
    os.replace(tmp, path)
    return path


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    smoke = "--smoke" in sys.argv
    data, out = argv[0], argv[1]
    workers = int(argv[2]) if len(argv) > 2 else 4
    systems = argv[3:] if len(argv) > 3 else SYSTEMS
    os.makedirs(out, exist_ok=True)
    tasks = []
    for name in systems:
        D = load(data, name)["off"].size - 1
        origins = list(range(FIRST_ORIGIN, D - TEST + 1, STEP))
        ns = NS
        if smoke:
            origins, ns = origins[:2], [80]
        for n in ns:
            for o in origins:
                tasks.append((data, out, name, o, n))
    # largest systems first so the pool drains evenly
    order = {s: i for i, s in enumerate(["NYC_BK", "NYC_MN", "NYC_BX", "NYC_QN", "SF", "NYC_SI", "NYC_AREA"])}
    tasks.sort(key=lambda t: (order.get(t[2], 9), -t[4]))
    t0 = time.time()
    done = 0
    with Pool(workers) as pool:
        for _ in pool.imap_unordered(run_task, tasks):
            done += 1
            if done % 20 == 0 or done == len(tasks):
                print(f"{done}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    with open(os.path.join(out, "RUN_INFO.json"), "w") as f:
        json.dump({"tasks": len(tasks), "secs": time.time() - t0, "smoke": smoke,
                   "systems": systems, "grid": [float(GRID[0]), float(GRID[-1]), 0.05]}, f)


if __name__ == "__main__":
    main()
