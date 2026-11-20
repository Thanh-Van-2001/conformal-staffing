"""Amendment 4 (exploratory, PLAN.md): quantile tracking (QT), SCD with an
integrator (SCD-I), both from conformal PID control, and conformal risk
control with the share of delayed calls as the loss (CRC-share). Also checks
that CRC with the 0/1 day loss selects SCD's theta at every origin.

Run: python -I analyze_amend4.py <out_dir>
Writes <out_dir>/amend4_results.json and <out_dir>/panel_amend4.csv.gz.
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402  (reads sys.argv[1] = out_dir)
import analyze_amend3 as X3  # noqa: E402

OUT = sys.argv[1]
SYSTEMS, NS, ALPHAS, BETA = A.SYSTEMS, A.NS, A.ALPHAS, A.BETA
CS = [0.05, 0.10, 0.20]
CRC_LEVEL = 0.05


def load_amend4():
    Q = {}
    for f in glob.glob(os.path.join(OUT, "amend4", "*.npz")):
        b = os.path.basename(f)[:-4]
        if b.endswith(".part"):
            continue
        name, o, n = b.rsplit("_", 2)
        z = np.load(f)
        Q[(name, int(n), int(o))] = {k: z[k] for k in z.files}
    return Q


def to_idx(theta, G):
    return int(min(max(round((theta + 2.0) / 0.05), 0), G - 1))


def crc_binary_idx(sc, a, G):
    """Conformal risk control with loss 1{day misses} = 1{score > theta}, B = 1:
    smallest grid index g with (#{s_i > g} + 1)/(h + 1) <= a."""
    h = sc.size
    for g in range(G):
        if (np.sum(sc > g) + 1) / (h + 1) <= a + 1e-12:
            return g, False
    return G - 1, True


def crc_share_idx(frac, G):
    """CRC with loss = share of calls delayed (made non-increasing in theta), B = 1."""
    L = np.flip(np.maximum.accumulate(np.flip(frac, axis=1), axis=1), axis=1)
    h = L.shape[0]
    ok = np.nonzero((L.sum(axis=0) + 1.0) / (h + 1) <= CRC_LEVEL + 1e-12)[0]
    return (int(ok[0]), False) if ok.size else (G - 1, True)


def main():
    R = A.load_all()
    Q = load_amend4()
    assert set(R) == set(Q), (len(R), len(Q))
    assert all(bool(q["scores_reproduced"]) for q in Q.values()), "stored scores not reproduced"
    rows, crc_mismatch = [], 0
    for name in SYSTEMS:
        for n in NS:
            origins = sorted(o for (s, nn, o) in R if s == name and nn == n)
            h = n // 2
            for tg in "AB":
                for a in ALPHAS:
                    need = math.ceil((1 - a) * A.TEST)
                    state = {c: {"QT": None, "SCDI": 0.0} for c in CS}
                    for o in origins:
                        z, q = R[(name, n, o)], Q[(name, n, o)]
                        G = z["grid"].size
                        grid = z["grid"]
                        mh = A.unpack(z[f"test_meets_half_{tg}"], G)
                        ma = A.unpack(z[f"test_meets_all_{tg}"], G)
                        ok = np.nonzero(ma.sum(axis=0) >= need)[0]
                        uh_or = float(z["uh_all"][int(ok[0]) if ok.size else G - 1])
                        sc = z[f"cal_score_{tg}"]
                        common = dict(system=name, n=n, origin=o, target=tg, alpha=a, uh_oracle=uh_or,
                                      load_ratio=float(z["calls_test"].mean() / z["calls_cal"].mean()))
                        i_scd, fl = A.idx_from_scores(sc, A.k_of(h, a), G)
                        i_crc, _ = crc_binary_idx(sc, a, G)
                        crc_mismatch += int(i_crc != i_scd)
                        rows.append(dict(common, rule="SCD", flag=fl, theta=float(grid[i_scd]),
                                         coverage=float(mh[:, i_scd].mean()), uh=float(z["uh_half"][i_scd]),
                                         share_delayed=float(z["test_fracA_half"][:, i_scd].mean())))
                        fin = grid[sc[sc < G].astype(int)]
                        span = float(fin.max() - fin.min()) if fin.size > 1 else 0.0
                        for c in CS:
                            st = state[c]
                            if st["QT"] is None:  # first origin: start from SCD's theta-hat
                                st["QT"] = float(grid[i_scd])
                            eta = c * span
                            for rule in ("QT", "SCDI"):
                                theta = st["QT"] if rule == "QT" else float(grid[i_scd]) + st["SCDI"]
                                i = to_idx(theta, G)  # applied plan: rounded to the grid, clipped to [-2, 10]
                                cov = float(mh[:, i].mean())
                                rows.append(dict(common, rule=f"{rule}_c{c:.2f}", flag=False, theta=float(grid[i]),
                                                 coverage=cov, uh=float(z["uh_half"][i]),
                                                 share_delayed=float(z["test_fracA_half"][:, i].mean())))
                                err = (1.0 - cov) - a  # miss_j - alpha
                                if rule == "QT":
                                    st["QT"] = min(max(st["QT"] + eta * err, -2.0), 10.0)
                                else:
                                    st["SCDI"] = st["SCDI"] + eta * err
                        if tg == "A":
                            i, fl = crc_share_idx(q["cal_fracA_half"].astype(float), G)
                            rows.append(dict(common, rule="CRCS", flag=fl, theta=float(grid[i]),
                                             coverage=float(mh[:, i].mean()), uh=float(z["uh_half"][i]),
                                             share_delayed=float(z["test_fracA_half"][:, i].mean())))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "panel_amend4.csv.gz"), index=False)
    P = pd.read_csv(os.path.join(OUT, "panel.csv.gz"))
    key = ["system", "n", "origin", "target", "alpha"]
    m = df[df.rule == "SCD"].merge(P[P.rule == "SCD"], on=key, suffixes=("", "_p"))
    assert len(m) == len(df[df.rule == "SCD"]) and np.allclose(m.coverage, m.coverage_p) and np.allclose(m.uh, m.uh_p)
    res = {"n_files": len(Q), "crc_binary_equals_scd_mismatches": crc_mismatch, "summary": {}, "share_delayed": {}}
    assert crc_mismatch == 0, crc_mismatch
    for n in NS:
        for a in ALPHAS:
            for tg in "AB":
                res["summary"][f"n{n}_a{a:.2f}_{tg}"] = X3.summarize(df, n, a, tg)
    # mean share of calls delayed on test days (the quantity CRC-share controls), primary configuration
    s = df[(df.n == 80) & (df.alpha == 0.10) & (df.target == "A")]
    for rule in ("SCD", "CRCS", "QT_c0.10", "SCDI_c0.10"):
        res["share_delayed"][rule] = {nm: float(s[(s.system == nm) & (s.rule == rule)].share_delayed.mean())
                                      for nm in SYSTEMS}
    with open(os.path.join(OUT, "amend4_results.json"), "w") as f:
        json.dump(res, f, indent=1)
    prim = res["summary"]["n80_a0.10_A"]
    print("crc(0/1) == SCD at every origin:", crc_mismatch == 0)
    for rule, v in prim.items():
        cov = [v["per_system"][nm]["coverage"] for nm in SYSTEMS]
        rel = [v["per_system"][nm]["rel_scd"] for nm in SYSTEMS]
        print(f"{rule:11s} cov {min(cov):.3f}-{max(cov):.3f} below {v['below_nominal']} H1 {v['h1_count']} "
              f"({v['h1_seed_min']}-{v['h1_seed_max']}) relSCD {min(rel):.3f}-{max(rel):.3f} rho {v['rho']:.2f} "
              f"sig {v['sig_vs_scd']}")
    for rule, d in res["share_delayed"].items():
        print("share delayed", rule, {k: round(x, 4) for k, x in d.items()})


if __name__ == "__main__":
    main()
