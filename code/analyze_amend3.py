"""Amendment 3 (exploratory, PLAN.md): apply WCP, TAB, TAB-ACI and ACA0 and
compare them with SCD and ACI. Pre-registered results (results.json) are not
touched.

Run: python -I analyze_amend3.py <out_dir>
Writes <out_dir>/amend3_results.json and <out_dir>/panel_amend3.csv.gz.
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
import analyze as A  # noqa: E402  (reads sys.argv[1] = out_dir, as here)

OUT = sys.argv[1]
SYSTEMS, NS, ALPHAS, BETA, TEST = A.SYSTEMS, A.NS, A.ALPHAS, A.BETA, A.TEST
HALF_LIVES = [10, 20, 40]
GAMMA = 0.05
H1_SEED = 20261118  # the pre-specified bootstrap seed (analyze.RNG)


def load_amend3():
    R = {}
    for f in glob.glob(os.path.join(OUT, "amend3", "*.npz")):
        b = os.path.basename(f)[:-4]
        if b.endswith(".part"):
            continue
        name, o, n = b.rsplit("_", 2)
        z = np.load(f)
        R[(name, int(n), int(o))] = {k: z[k] for k in z.files}
    return R


def wcp_index(sc, a, H, G):
    """Weighted split conformal (Barber et al. 2023, fixed weights): smallest
    grid index with sum_j w_j 1{s_j <= i} >= (1 - a)(sum_j w_j + 1)."""
    h = sc.size
    w = 2.0 ** (-(h - 1 - np.arange(h)) / H)  # most recent calibration day: weight 1
    need = (1 - a) * (w.sum() + 1.0)
    order = np.argsort(sc, kind="stable")
    cum = np.cumsum(w[order])
    pos = np.nonzero(cum >= need - 1e-12)[0]
    if not pos.size:
        return G - 1, True
    i = int(sc[order][pos[0]])
    return (G - 1, True) if i >= G else (i, False)


def rows(R, Q):
    out = []
    for (name, n, o), z in R.items():
        q = Q[(name, n, o)]
        G = z["grid"].size
        h = n // 2
        ratio = float(z["calls_test"].mean() / z["calls_cal"].mean())
        mh = {tg: A.unpack(z[f"test_meets_half_{tg}"], G) for tg in "AB"}
        mt = {tg: A.unpack(q[f"tab_test_meets_{tg}"], G) for tg in "AB"}
        ma = {tg: A.unpack(z[f"test_meets_all_{tg}"], G) for tg in "AB"}
        for tg in "AB":
            ti = 0 if tg == "A" else 1
            for a in ALPHAS:
                need = math.ceil((1 - a) * TEST)
                ok = np.nonzero(ma[tg].sum(axis=0) >= need)[0]
                uh_or = float(z["uh_all"][int(ok[0]) if ok.size else G - 1])
                common = dict(system=name, n=n, origin=o, target=tg, alpha=a, load_ratio=ratio, uh_oracle=uh_or,
                              r_test=float(q["tab_r_test"]))
                i, fl = A.idx_from_scores(z[f"cal_score_{tg}"], A.k_of(h, a), G)
                out.append(dict(common, rule="SCD", flag=fl, theta=float(z["grid"][i]),
                                coverage=float(mh[tg][:, i].mean()), uh=float(z["uh_half"][i])))
                for H in HALF_LIVES:
                    i, fl = wcp_index(z[f"cal_score_{tg}"], a, H, G)
                    out.append(dict(common, rule=f"WCP_H{H}", flag=fl, theta=float(z["grid"][i]),
                                    coverage=float(mh[tg][:, i].mean()), uh=float(z["uh_half"][i])))
                i, fl = A.idx_from_scores(q[f"tab_cal_score_{tg}"], A.k_of(h, a), G)
                out.append(dict(common, rule="TAB", flag=fl, theta=float(z["grid"][i]),
                                coverage=float(mt[tg][:, i].mean()), uh=float(q["tab_uh"][i])))
                fr = q[f"ACA0_{a:.2f}_test_frac"]
                out.append(dict(common, rule="ACA0", flag=bool(q[f"ACA0_{a:.2f}_flag"]), theta=np.nan,
                                coverage=float((fr[ti] <= BETA[tg] + 1e-12).mean()),
                                uh=float(q[f"ACA0_{a:.2f}_plan"].sum())))
    df = pd.DataFrame(out)
    info = {(r.system, r.n, r.origin, r.target, r.alpha): (r.load_ratio, r.uh_oracle, r.r_test)
            for r in df[df.rule == "SCD"].itertuples()}
    # adaptive level (gamma = 0.05) for SCD and TAB, carried across successive origins
    ad = []
    for name in SYSTEMS:
        for n in NS:
            origins = sorted(o for (s, nn, o) in R if s == name and nn == n)
            h = n // 2
            for tg in "AB":
                for a in ALPHAS:
                    for rule, score_key, src in (("ACI", "cal_score", "R"), ("TAB_ACI", "tab_cal_score", "Q")):
                        at = a
                        for o in origins:
                            z, q = R[(name, n, o)], Q[(name, n, o)]
                            G = z["grid"].size
                            sc = (z if src == "R" else q)[f"{score_key}_{tg}"]
                            i, fl = A.idx_from_scores(sc, A.k_of(h, min(max(at, 0.001), 0.999)), G)
                            if src == "R":
                                cov = float(A.unpack(z[f"test_meets_half_{tg}"], G)[:, i].mean())
                                uh = float(z["uh_half"][i])
                            else:
                                cov = float(A.unpack(q[f"tab_test_meets_{tg}"], G)[:, i].mean())
                                uh = float(q["tab_uh"][i])
                            lr, uo, rr = info[(name, n, o, tg, a)]
                            ad.append(dict(system=name, n=n, origin=o, target=tg, alpha=a, load_ratio=lr,
                                           uh_oracle=uo, r_test=rr, rule=rule, flag=fl,
                                           theta=float(z["grid"][i]), coverage=cov, uh=uh))
                            at = at + GAMMA * (a - (1 - cov))
    return pd.concat([df, pd.DataFrame(ad)], ignore_index=True)


def summarize(df, n, a, tg):
    s = df[(df.n == n) & (df.alpha == a) & (df.target == tg)]
    out = {}
    for rule in sorted(s.rule.unique()):
        rng = np.random.default_rng(H1_SEED)  # same seed and system order as the pre-registered H1 test
        per = {}
        for name in SYSTEMS:
            g = s[(s.system == name) & (s.rule == rule)].sort_values("origin")
            scd = s[(s.system == name) & (s.rule == "SCD")].sort_values("origin")
            lo, hi = A.block_boot_mean(g.coverage.values, rng=rng)
            per[name] = dict(coverage=float(g.coverage.mean()), cov_lo=lo, cov_hi=hi, uh=float(g.uh.mean()),
                             rel_scd=float(g.uh.mean() / scd.uh.mean()),
                             rel_oracle=float(g.uh.mean() / g.uh_oracle.mean()),
                             share_below_075=float((g.coverage < 0.75).mean()), flags=int(g.flag.sum()),
                             p_vs_scd=A.wilcox(g.coverage.values, scd.coverage.values, "greater"))
        seeds = []
        for sd in range(50):
            r2 = np.random.default_rng(1000 + sd)
            seeds.append(sum(A.block_boot_mean(s[(s.system == nm) & (s.rule == rule)].sort_values("origin")
                                               .coverage.values, rng=r2)[0] >= 0.85 for nm in SYSTEMS))
        adj = A.holm([per[nm]["p_vs_scd"] for nm in SYSTEMS])
        for nm, p in zip(SYSTEMS, adj):
            per[nm]["p_vs_scd_holm"] = float(p)
        g = s[s.rule == rule]
        out[rule] = dict(per_system=per, below_nominal=int(sum(per[nm]["coverage"] < 1 - a for nm in SYSTEMS)),
                         h1_count=int(sum(per[nm]["cov_lo"] >= 0.85 for nm in SYSTEMS)),
                         h1_seed_min=int(min(seeds)), h1_seed_max=int(max(seeds)),
                         rho=float(stats.spearmanr(g.load_ratio, g.coverage).statistic),
                         sig_vs_scd=int(sum(per[nm]["p_vs_scd_holm"] < 0.05 for nm in SYSTEMS)))
    return out


def main():
    R = A.load_all()
    Q = load_amend3()
    assert set(R) == set(Q), (len(R), len(Q))
    df = rows(R, Q)
    df.to_csv(os.path.join(OUT, "panel_amend3.csv.gz"), index=False)
    # consistency with the pre-registered panel: SCD and ACI rows must match
    P = pd.read_csv(os.path.join(OUT, "panel.csv.gz"))
    key = ["system", "n", "origin", "target", "alpha"]
    for mine, theirs in (("SCD", "SCD"), ("ACI", "ACI_g0.05")):
        m = df[df.rule == mine].merge(P[P.rule == theirs], on=key, suffixes=("", "_p"))
        assert len(m) == len(df[df.rule == mine]), mine
        assert np.allclose(m.coverage, m.coverage_p) and np.allclose(m.uh, m.uh_p), mine
    res = {"n_files": len(Q), "tab_nonmono_total": int(sum(int(q["tab_nonmono"]) for q in Q.values())),
           "summary": {}, "aca_plan_reproduced": bool(all(
               np.array_equal(Q[k][f"ACA_{a:.2f}_A_plan_recomputed"], R[k][f"ACA_{a:.2f}_A_plan"])
               for k in Q for a in ALPHAS))}
    rt = df[(df.rule == "TAB") & (df.alpha == 0.10) & (df.target == "A")]
    res["tab_r_test"] = {str(n): dict(min=float(rt[rt.n == n].r_test.min()), max=float(rt[rt.n == n].r_test.max()))
                         for n in NS}
    h1 = json.load(open(os.path.join(OUT, "results.json")))["hypotheses"]["H1"]["lower_bounds"]
    for n in NS:
        for a in ALPHAS:
            for tg in "AB":
                res["summary"][f"n{n}_a{a:.2f}_{tg}"] = summarize(df, n, a, tg)
    prim = res["summary"]["n80_a0.10_A"]
    for nm in SYSTEMS:  # the pre-registered H1 bounds must be reproduced for SCD
        assert abs(prim["SCD"]["per_system"][nm]["cov_lo"] - h1[nm]) < 1e-12, nm
    with open(os.path.join(OUT, "amend3_results.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("aca plan reproduced:", res["aca_plan_reproduced"], "| tab nonmono:", res["tab_nonmono_total"],
          "| r_test:", res["tab_r_test"])
    for rule, v in prim.items():
        cov = [v["per_system"][nm]["coverage"] for nm in SYSTEMS]
        rel = [v["per_system"][nm]["rel_scd"] for nm in SYSTEMS]
        print(f"{rule:9s} cov {min(cov):.3f}-{max(cov):.3f} below {v['below_nominal']} H1 {v['h1_count']} "
              f"({v['h1_seed_min']}-{v['h1_seed_max']}) relSCD {min(rel):.3f}-{max(rel):.3f} rho {v['rho']:.2f} "
              f"sig {v['sig_vs_scd']}")


if __name__ == "__main__":
    main()
