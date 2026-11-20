"""Amendment 3 (exploratory, PLAN.md): outcomes for the trend-adjusted base
load (TAB) and for the conformal arrival band without the Erlang-C margin
(ACA0). WCP needs no new simulation (it re-weights SCD's stored scores) and
is applied in analyze_amend3.py.

Reuses exp.py (plan family, grid evaluation, scores, ACA envelope) and the
unchanged simulator. Writes <out_dir>/amend3/<system>_<origin>_<n>.npz.

Run: python -I exp_amend3.py <data_dir> <out_dir> [workers] [--check]
--check: consistency checks only (TAB with r = 1 must reproduce SCD's stored
scores and test outcomes; ACA's envelope must reproduce the stored ACA plan).
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

import exp
import sim

P, L, TEST = exp.P, exp.L, exp.TEST
G = exp.G


def tab_outcomes(S, tr_idx, h, n, m_half, unit_scale=False):
    """Calibration scores and grid outcomes of the test days under the
    trend-adjusted load. unit_scale=True forces r = 1 (consistency check)."""
    y = S["counts"][tr_idx].sum(axis=1).astype(float)
    b, a = np.polyfit(np.arange(n, dtype=float), y, 1)
    t_b = (h - 1) / 2.0
    ref = a + b * t_b
    r_cal = (a + b * np.arange(h, n, dtype=float)) / ref
    r_test = (a + b * (n + 9.5)) / ref
    if unit_scale:
        r_cal, r_test = np.ones(h), 1.0
    assert ref > 0 and np.all(r_cal > 0) and r_test > 0
    fa_c, fb_c = np.empty((h, G)), np.empty((h, G))
    for j, d in enumerate(tr_idx[h:]):
        fa, fb, _ = exp.grid_fracs(exp.sub(S, [int(d)]), m_half * r_cal[j])
        fa_c[j], fb_c[j] = fa[0], fb[0]
    te = exp.sub(S, np.arange(tr_idx[-1] + 1, tr_idx[-1] + 1 + TEST))
    ta, tb, uh = exp.grid_fracs(te, m_half * r_test)
    out = {"tab_r_cal": r_cal, "tab_r_test": np.array(r_test), "tab_slope": np.array(b), "tab_uh": uh,
           "tab_test_fracA": ta.astype(np.float32)}
    nonmono = 0
    for tg, cf, tf in (("A", fa_c, ta), ("B", fb_c, tb)):
        sc, nm = exp.scores(cf, exp.BETA[tg])
        out[f"tab_cal_score_{tg}"] = sc
        out[f"tab_test_meets_{tg}"] = np.packbits(tf <= exp.BETA[tg] + exp.EPS, axis=1)
        nonmono += nm
    out["tab_nonmono"] = np.array(nonmono)
    return out


def aca0_outcomes(S, tr_idx, h):
    base, cal = exp.sub(S, tr_idx[:h]), exp.sub(S, tr_idx[h:])
    te = exp.sub(S, np.arange(tr_idx[-1] + 1, tr_idx[-1] + 1 + TEST))
    lam_h = base["counts"].mean(axis=0) / L
    sd = np.sqrt(np.maximum(lam_h, 1e-9))
    s_cal = np.sort(((cal["counts"] - lam_h) / sd).max(axis=1))
    K = exp.kernel(base["svc"])
    es_h = float(base["svc"].mean())
    out = {}
    for al_ in exp.ALPHAS:
        k = math.ceil((h + 1) * (1 - al_))
        q = s_cal[k - 1] if k <= h else s_cal[-1]
        mU = exp.load_from_arrivals(np.maximum(lam_h + q * sd, 0.0), K)
        c = np.maximum(1, np.ceil(mU)).astype(np.int64)
        fa_, fb_ = exp.fracs(te, c)
        out[f"ACA0_{al_:.2f}_plan"] = c
        out[f"ACA0_{al_:.2f}_test_frac"] = np.stack([fa_, fb_])
        out[f"ACA0_{al_:.2f}_flag"] = np.array(k > h)
        out[f"ACA_{al_:.2f}_A_plan_recomputed"] = exp.ec_plan(mU, "A", es_h)
    return out


def run_task(args):
    data, out, name, o, n = args
    path = os.path.join(out, "amend3", f"{name}_{o:04d}_{n:03d}.npz")
    if os.path.exists(path):
        return path
    t0 = time.time()
    S = exp.load(data, name)
    tr_idx = np.arange(o - n, o)
    h = n // 2
    base = exp.sub(S, tr_idx[:h])
    m_half = sim.busy_profile(base["arr"], base["svc"], base["off"], P, L)
    res = {"grid": exp.GRID}
    res.update(tab_outcomes(S, tr_idx, h, n, m_half))
    res.update(aca0_outcomes(S, tr_idx, h))
    res["secs"] = np.array(time.time() - t0)
    tmp = path + ".part.npz"
    np.savez_compressed(tmp, **res)
    os.replace(tmp, path)
    return path


def check(data, out):
    """TAB with r = 1 must equal SCD; ACA's envelope must give the stored ACA plan."""
    name, o, n = "NYC_SI", 160, 80
    z = np.load(os.path.join(out, f"{name}_{o:04d}_{n:03d}.npz"))
    S = exp.load(data, name)
    tr_idx = np.arange(o - n, o)
    h = n // 2
    base = exp.sub(S, tr_idx[:h])
    m_half = sim.busy_profile(base["arr"], base["svc"], base["off"], P, L)
    assert np.allclose(m_half, z["m_half"])
    t = tab_outcomes(S, tr_idx, h, n, m_half, unit_scale=True)
    ok = {}
    for tg in "AB":
        ok[f"score_{tg}"] = bool(np.array_equal(t[f"tab_cal_score_{tg}"], z[f"cal_score_{tg}"]))
        ok[f"test_{tg}"] = bool(np.array_equal(t[f"tab_test_meets_{tg}"], z[f"test_meets_half_{tg}"]))
    ok["uh"] = bool(np.allclose(t["tab_uh"], z["uh_half"]))
    a0 = aca0_outcomes(S, tr_idx, h)
    for al_ in exp.ALPHAS:
        ok[f"aca_{al_:.2f}"] = bool(np.array_equal(a0[f"ACA_{al_:.2f}_A_plan_recomputed"], z[f"ACA_{al_:.2f}_A_plan"]))
    print("consistency:", ok, flush=True)
    assert all(ok.values()), ok
    return ok


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    data, out = argv[0], argv[1]
    workers = int(argv[2]) if len(argv) > 2 else 4
    ok = check(data, out)
    if "--check" in sys.argv:
        return
    os.makedirs(os.path.join(out, "amend3"), exist_ok=True)
    tasks = []
    for name in exp.SYSTEMS:
        D = exp.load(data, name)["off"].size - 1
        for n in exp.NS:
            for o in range(exp.FIRST_ORIGIN, D - TEST + 1, exp.STEP):
                tasks.append((data, out, name, o, n))
    order = {s: i for i, s in enumerate(["NYC_BK", "NYC_MN", "NYC_BX", "NYC_QN", "SF", "NYC_SI", "NYC_AREA"])}
    tasks.sort(key=lambda t: (order.get(t[2], 9), -t[4]))
    t0 = time.time()
    done = 0
    with Pool(workers) as pool:
        for _ in pool.imap_unordered(run_task, tasks):
            done += 1
            if done % 20 == 0 or done == len(tasks):
                print(f"{done}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    with open(os.path.join(out, "amend3", "RUN_INFO.json"), "w") as f:
        json.dump({"tasks": len(tasks), "secs": time.time() - t0, "workers": workers, "consistency": ok}, f)


if __name__ == "__main__":
    main()
