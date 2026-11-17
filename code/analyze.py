"""Apply the staffing rules to the stored outcomes and test H1-H4 (PLAN.md).

Run: python -I analyze.py <out_dir>
Writes <out_dir>/panel.csv.gz and <out_dir>/results.json.
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

OUT = sys.argv[1]
SYSTEMS = ["NYC_AREA", "NYC_SI", "NYC_BX", "NYC_MN", "NYC_QN", "NYC_BK", "SF"]
NS = [40, 80, 160]
ALPHAS = [0.05, 0.10, 0.20]
GAMMAS = [0.02, 0.05, 0.10]
BETA = {"A": 0.05, "B": 0.01}
TEST = 20
PRIMARY = dict(n=80, alpha=0.10, target="A")
B_REPS, BLOCK = 10000, 4
RNG = np.random.default_rng(20261118)


def unpack(p, G):
    return np.unpackbits(p, axis=1)[:, :G].astype(bool)


def load_all():
    R = {}
    for f in glob.glob(os.path.join(OUT, "*.npz")):
        b = os.path.basename(f)[:-4]
        if b.endswith(".part"):
            continue
        name, o, n = b.rsplit("_", 2)
        z = np.load(f)
        R[(name, int(n), int(o))] = {k: z[k] for k in z.files}
    return R


def k_of(h, a):
    return math.ceil((h + 1) * (1 - a))


def idx_from_scores(sc, k, G):
    """k-th smallest score index; top of grid if k exceeds the sample or the
    score is +inf (= G). Returns (index, flagged)."""
    s = np.sort(sc)
    if k > s.size or k < 1:
        return G - 1, True
    i = int(s[k - 1])
    return (G - 1, True) if i >= G else (i, False)


def rule_rows(R):
    rows = []
    for (name, n, o), z in R.items():
        G = z["grid"].size
        h = n // 2
        mh = {tg: unpack(z[f"test_meets_half_{tg}"], G) for tg in "AB"}
        ma = {tg: unpack(z[f"test_meets_all_{tg}"], G) for tg in "AB"}
        ratio = float(z["calls_test"].mean() / z["calls_cal"].mean())
        base = dict(system=name, n=n, origin=o, test_start=str(z["test_start"]), load_ratio=ratio)
        for tg in "AB":
            ti = 0 if tg == "A" else 1
            for a in ALPHAS:
                need = math.ceil((1 - a) * TEST)
                cnt = ma[tg].sum(axis=0)
                ok = np.nonzero(cnt >= need)[0]
                io = int(ok[0]) if ok.size else G - 1
                uh_or = float(z["uh_all"][io])
                common = dict(base, target=tg, alpha=a, uh_oracle=uh_or)
                # SCD
                i, fl = idx_from_scores(z[f"cal_score_{tg}"], k_of(h, a), G)
                rows.append(dict(common, rule="SCD", theta=float(z["grid"][i]), flag=fl,
                                 coverage=float(mh[tg][:, i].mean()), uh=float(z["uh_half"][i]),
                                 fracA=float(z["test_fracA_half"][:, i].mean())))
                # EMP
                i, fl = idx_from_scores(z[f"train_score_{tg}"], math.ceil((1 - a) * n), G)
                rows.append(dict(common, rule="EMP", theta=float(z["grid"][i]), flag=fl,
                                 coverage=float(ma[tg][:, i].mean()), uh=float(z["uh_all"][i]),
                                 fracA=float(z["test_fracA_all"][:, i].mean())))
                # ORACLE
                rows.append(dict(common, rule="ORACLE", theta=float(z["grid"][io]), flag=not ok.size,
                                 coverage=float(ma[tg][:, io].mean()), uh=uh_or,
                                 fracA=float(z["test_fracA_all"][:, io].mean())))
                # ORACLE_H (amendment 2, exploratory): hindsight within SCD's own family (half-window base)
                okh = np.nonzero(mh[tg].sum(axis=0) >= need)[0]
                ih = int(okh[0]) if okh.size else G - 1
                rows.append(dict(common, rule="ORACLE_H", theta=float(z["grid"][ih]), flag=not okh.size,
                                 coverage=float(mh[tg][:, ih].mean()), uh=float(z["uh_half"][ih]),
                                 fracA=float(z["test_fracA_half"][:, ih].mean())))
                # SIPP, MOL (do not depend on alpha)
                for rule in ("SIPP", "MOL"):
                    fr = z[f"{rule}_{tg}_test_frac"]
                    rows.append(dict(common, rule=rule, theta=np.nan, flag=False,
                                     coverage=float((fr[ti] <= BETA[tg] + 1e-12).mean()),
                                     uh=float(z[f"{rule}_{tg}_plan"].sum()), fracA=float(fr[0].mean())))
                fr = z[f"ACA_{a:.2f}_{tg}_test_frac"]
                rows.append(dict(common, rule="ACA", theta=np.nan, flag=bool(z[f"ACA_{a:.2f}_flag"]),
                                 coverage=float((fr[ti] <= BETA[tg] + 1e-12).mean()),
                                 uh=float(z[f"ACA_{a:.2f}_{tg}_plan"].sum()), fracA=float(fr[0].mean())))
    return pd.DataFrame(rows)


def aci_rows(R, df):
    rows = []
    orc = df[df.rule == "ORACLE"].set_index(["system", "n", "target", "alpha", "origin"])["uh_oracle"]
    for name in SYSTEMS:
        for n in NS:
            origins = sorted(o for (s, nn, o) in R if s == name and nn == n)
            if not origins:
                continue
            h = n // 2
            for tg in "AB":
                for a in ALPHAS:
                    for g in GAMMAS:
                        at = a
                        for o in origins:
                            z = R[(name, n, o)]
                            G = z["grid"].size
                            mh = unpack(z[f"test_meets_half_{tg}"], G)
                            ac = min(max(at, 0.001), 0.999)
                            i, fl = idx_from_scores(z[f"cal_score_{tg}"], k_of(h, ac), G)
                            cov = float(mh[:, i].mean())
                            rows.append(dict(system=name, n=n, origin=o, target=tg, alpha=a, gamma=g,
                                             rule=f"ACI_g{g:.2f}", alpha_t=at, theta=float(z["grid"][i]),
                                             flag=fl, coverage=cov, uh=float(z["uh_half"][i]),
                                             fracA=float(z["test_fracA_half"][:, i].mean()),
                                             uh_oracle=float(orc[(name, n, tg, a, o)]),
                                             load_ratio=float(z["calls_test"].mean() / z["calls_cal"].mean()),
                                             test_start=str(z["test_start"])))
                            at = at + g * (a - (1 - cov))
    return pd.DataFrame(rows)


def block_boot_mean(x, reps=B_REPS, block=BLOCK, rng=None):
    rng = RNG if rng is None else rng
    x = np.asarray(x, float)
    J = x.size
    nb = math.ceil(J / block)
    starts = rng.integers(0, J - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :J]
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (p.size - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def wilcox(x, y, alternative):
    d = np.asarray(x) - np.asarray(y)
    if np.all(d == 0):
        return 1.0
    return float(stats.wilcoxon(x, y, alternative=alternative).pvalue)


def summarize(df, n, alpha, target):
    s = df[(df.n == n) & (df.alpha == alpha) & (df.target == target)]
    out = {}
    for name in SYSTEMS:
        t = s[s.system == name]
        orc = t[t.rule == "ORACLE"].set_index("origin")["uh"]
        orh = t[t.rule == "ORACLE_H"].set_index("origin")["uh"]
        d = {}
        for rule, g in t.groupby("rule"):
            g = g.sort_values("origin")
            lo, hi = block_boot_mean(g.coverage.values)
            rel = g.set_index("origin")["uh"] / orc
            d[rule] = dict(coverage=float(g.coverage.mean()), cov_lo=lo, cov_hi=hi,
                           rel_oracle_mean=float(g.uh.mean() / orc.mean()),
                           rel_oracle_h_mean=float(g.uh.mean() / orh.mean()),
                           uh=float(g.uh.mean()), rel_oracle_median=float(rel.median()),
                           rel_oracle_q25=float(rel.quantile(0.25)), rel_oracle_q75=float(rel.quantile(0.75)),
                           share_below_075=float((g.coverage < 0.75).mean()), fracA=float(g.fracA.mean()),
                           flags=int(g.flag.sum()), origins=int(len(g)))
        out[name] = d
    return out


def conditional_check(df, n, alpha, target, sims=200000):
    """Observed spread of SCD window coverage vs exchangeable theory:
    C ~ Beta(k, h + 1 - k), window coverage ~ Binomial(20, C) / 20."""
    h = n // 2
    k = k_of(h, alpha)
    res = {}
    if k > h:
        return res
    C = RNG.beta(k, h + 1 - k, size=sims)
    W = RNG.binomial(TEST, C) / TEST
    th = dict(mean=float(W.mean()), sd=float(W.std()), p_below_075=float((W < 0.75).mean()))
    s = df[(df.n == n) & (df.alpha == alpha) & (df.target == target) & (df.rule == "SCD")]
    for name in SYSTEMS:
        c = s[s.system == name].coverage
        res[name] = dict(sd=float(c.std(ddof=0)), p_below_075=float((c < 0.75).mean()), mean=float(c.mean()))
    allc = s.coverage
    res["pooled"] = dict(sd=float(allc.std(ddof=0)), p_below_075=float((allc < 0.75).mean()), mean=float(allc.mean()))
    res["theory"] = th
    return res


def hypotheses(df):
    n, a, tg = PRIMARY["n"], PRIMARY["alpha"], PRIMARY["target"]
    s = df[(df.n == n) & (df.alpha == a) & (df.target == tg)]
    H = {}
    # H1
    lo = {}
    for name in SYSTEMS:
        g = s[(s.system == name) & (s.rule == "SCD")].sort_values("origin")
        lo[name] = block_boot_mean(g.coverage.values)[0]
    n_ok = sum(v >= 0.85 for v in lo.values())
    H["H1"] = dict(lower_bounds=lo, systems_ok=n_ok, supported=n_ok >= 6)
    # H2, H3

    def paired(rule_x, rule_y, col, alt):
        ps = {}
        for name in SYSTEMS:
            x = s[(s.system == name) & (s.rule == rule_x)].sort_values("origin")[col].values
            y = s[(s.system == name) & (s.rule == rule_y)].sort_values("origin")[col].values
            ps[name] = wilcox(x, y, alt)
        adj = holm(list(ps.values()))
        return ps, dict(zip(ps, adj.tolist()))

    p2, a2 = paired("EMP", "SCD", "coverage", "less")
    H["H2"] = dict(p=p2, p_holm=a2, n_sig=sum(v < 0.05 for v in a2.values()),
                   supported=sum(v < 0.05 for v in a2.values()) >= 4)
    p3, a3 = paired("ACA", "SCD", "uh", "greater")
    H["H3"] = dict(p=p3, p_holm=a3, n_sig=sum(v < 0.05 for v in a3.values()),
                   supported=sum(v < 0.05 for v in a3.values()) >= 4)
    # H4: pooled Spearman, permutation within systems
    g = s[s.rule == "SCD"]
    rho = stats.spearmanr(g.load_ratio, g.coverage).statistic
    perm = np.empty(10000)
    groups = [np.nonzero((g.system == nm).values)[0] for nm in SYSTEMS]
    cov = g.coverage.values
    lr = g.load_ratio.values
    for r in range(perm.size):
        c2 = cov.copy()
        for ix in groups:
            c2[ix] = cov[RNG.permutation(ix)]
        perm[r] = stats.spearmanr(lr, c2).statistic
    p4 = float((np.sum(perm <= rho) + 1) / (perm.size + 1))
    H["H4"] = dict(rho=float(rho), p_one_sided=p4, supported=bool(rho < 0 and p4 < 0.05))
    return H


def exploratory(panel):
    """Amendment 2 additions (exploratory)."""
    n, a, tg = PRIMARY["n"], PRIMARY["alpha"], PRIMARY["target"]
    s = panel[(panel.n == n) & (panel.alpha == a) & (panel.target == tg)]
    E = {}
    # H1 sensitivity to the bootstrap seed, with and without NYC_AREA
    counts, counts_noq4, bk = [], [], []
    for seed in range(50):
        rng = np.random.default_rng(1000 + seed)
        lo = {nm: block_boot_mean(s[(s.system == nm) & (s.rule == "SCD")].sort_values("origin").coverage.values,
                                  rng=rng)[0] for nm in SYSTEMS}
        counts.append(sum(v >= 0.85 for v in lo.values()))
        counts_noq4.append(sum(v >= 0.85 for k, v in lo.items() if k != "NYC_AREA"))
        bk.append(lo["NYC_BK"])
    E["h1_seed"] = dict(min=int(min(counts)), max=int(max(counts)), share_max=float(np.mean(np.array(counts) == max(counts))),
                        noq4_min=int(min(counts_noq4)), noq4_max=int(max(counts_noq4)),
                        bk_lo_min=float(min(bk)), bk_lo_max=float(max(bk)))
    # ACI vs SCD, paired one-sided Wilcoxon per system
    p = {}
    for nm in SYSTEMS:
        x = s[(s.system == nm) & (s.rule == "ACI_g0.05")].sort_values("origin").coverage.values
        y = s[(s.system == nm) & (s.rule == "SCD")].sort_values("origin").coverage.values
        p[nm] = wilcox(x, y, "greater")
    E["aci_vs_scd_p"] = p
    E["aci_vs_scd_p_holm"] = dict(zip(p, holm(list(p.values())).tolist()))
    # H4: within-system rho; circular-shift permutation of coverage within systems
    g = s[s.rule == "SCD"].sort_values(["system", "origin"])
    E["h4_within_rho"] = {nm: float(stats.spearmanr(g[g.system == nm].load_ratio, g[g.system == nm].coverage).statistic)
                          for nm in SYSTEMS}
    obs = stats.spearmanr(g.load_ratio, g.coverage).statistic
    rng = np.random.default_rng(7)
    cov_by = [g[g.system == nm].coverage.values for nm in SYSTEMS]
    lr = np.concatenate([g[g.system == nm].load_ratio.values for nm in SYSTEMS])
    sims = np.empty(10000)
    for r in range(sims.size):
        c2 = np.concatenate([np.roll(c, rng.integers(1, c.size)) for c in cov_by])
        sims[r] = stats.spearmanr(lr, c2).statistic
    E["h4_circular_p"] = float((np.sum(sims <= obs) + 1) / (sims.size + 1))
    # spread of window coverage vs the independent-days Beta-Binomial model
    h = n // 2
    k = k_of(h, a)
    obs_sd = float(g.coverage.std(ddof=0))
    J = [int((g.system == nm).sum()) for nm in SYSTEMS]
    rng = np.random.default_rng(11)
    sds = np.empty(20000)
    for r in range(sds.size):
        C = rng.beta(k, h + 1 - k, size=sum(J))
        sds[r] = (rng.binomial(TEST, C) / TEST).std()
    E["spread_p"] = float((np.sum(sds >= obs_sd) + 1) / (sds.size + 1))
    # systems below nominal coverage per configuration
    below = {}
    for nn in NS:
        for aa in ALPHAS:
            for tt in "AB":
                q = panel[(panel.n == nn) & (panel.alpha == aa) & (panel.target == tt)]
                key = f"n{nn}_a{aa:.2f}_{tt}"
                below[key] = {r: int(sum(q[(q.system == nm) & (q.rule == r)].coverage.mean() < 1 - aa for nm in SYSTEMS))
                              for r in ("SCD", "ACI_g0.05", "EMP")}
    E["below_nominal"] = below
    return E


def main():
    R = load_all()
    df = rule_rows(R)
    aci = aci_rows(R, df)
    panel = pd.concat([df, aci], ignore_index=True)
    panel.to_csv(os.path.join(OUT, "panel.csv.gz"), index=False)
    res = {"n_files": len(R), "nonmono_total": int(sum(int(z["nonmono"]) for z in R.values())),
           "hypotheses": hypotheses(df), "summary": {}, "conditional": {}}
    for n in NS:
        for a in ALPHAS:
            for tg in "AB":
                key = f"n{n}_a{a:.2f}_{tg}"
                res["summary"][key] = summarize(panel, n, a, tg)
                res["conditional"][key] = conditional_check(panel, n, a, tg)
    res["exploratory"] = exploratory(panel)
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    H = res["hypotheses"]
    print("H1", H["H1"]["systems_ok"], H["H1"]["supported"], {k: round(v, 3) for k, v in H["H1"]["lower_bounds"].items()})
    print("H2", H["H2"]["n_sig"], H["H2"]["supported"])
    print("H3", H["H3"]["n_sig"], H["H3"]["supported"])
    print("H4", round(H["H4"]["rho"], 3), round(H["H4"]["p_one_sided"], 4), H["H4"]["supported"])
    S = res["summary"]["n80_a0.10_A"]
    for name in SYSTEMS:
        print(name, {r: (round(v["coverage"], 3), round(v["uh"]), round(v["rel_oracle_median"], 3))
                     for r, v in S[name].items()})


if __name__ == "__main__":
    main()
