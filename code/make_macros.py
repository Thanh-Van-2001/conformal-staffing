"""Every number in the paper comes from here. Reads out/results.json,
out/panel.csv.gz and facts/prep_log.json; writes paper/macros.tex.
Run from the repository root: python -I code/make_macros.py"""
import json

import numpy as np
import pandas as pd

R = json.load(open("out/results.json"))
P = pd.read_csv("out/panel.csv.gz")
F = json.load(open("facts/prep_log.json"))
SYS = ["NYC_AREA", "NYC_SI", "NYC_BX", "NYC_MN", "NYC_QN", "NYC_BK", "SF"]
TAG = {"NYC_AREA": "Area", "NYC_SI": "SI", "NYC_BX": "BX", "NYC_MN": "MN", "NYC_QN": "QN", "NYC_BK": "BK", "SF": "SF"}
M = {}


def f(x, d=3):
    return f"{x:.{d}f}"


def pct(x, d=0):
    return f"{100 * x:.{d}f}"


def rng(vals, fmt):
    return fmt(min(vals)), fmt(max(vals))


# data facts
calls = [F[s]["mean_calls_per_day"] for s in SYS]
M["nSystems"] = str(len(SYS))
M["nDays"] = str(F["NYC_BK"]["days"])
M["callsMin"], M["callsMax"] = f"{min(calls):,.0f}", f"{max(calls):,.0f}"
# NYC_AREA (dispatch area Q4) is a subset of Queens: count its calls once
M["totalCalls"] = f"{sum(F[s]['calls'] for s in SYS if s != 'NYC_AREA'):,}"
M["areaName"] = F["nyc_small_area"]["area"]
disp = [F[s]["dispersion_index_daily_total"] for s in SYS]
M["dispMin"], M["dispMax"] = f(min(disp), 1), f(max(disp), 1)
svc = [F[s]["mean_service_min"] for s in SYS]
M["svcMin"], M["svcMax"] = f(min(svc), 0), f(max(svc), 0)
load = [F[s]["offered_load_erlang"] for s in SYS]
M["loadMin"], M["loadMax"] = f(min(load), 1), f(max(load), 1)
for s in SYS:
    t = TAG[s]
    M[f"calls{t}"] = f"{F[s]['mean_calls_per_day']:,.0f}"
    M[f"disp{t}"] = f(F[s]["dispersion_index_daily_total"], 1)
    M[f"svc{t}"] = f(F[s]["mean_service_min"], 0)
    M[f"load{t}"] = f(F[s]["offered_load_erlang"], 1)

runinfo = json.load(open("out/RUN_INFO.json"))
M["nTasks"] = str(runinfo["tasks"])
M["nonmono"] = str(R["nonmono_total"])
nor = P[(P.rule == "SCD") & (P.n == 80) & (P.alpha == 0.1) & (P.target == "A")].groupby("system").size()
M["nOrigins"] = str(int(nor.iloc[0]))
M["nWindows"] = str(int(nor.sum()))
M["firstTest"] = P.test_start.min()
M["lastTest"] = P.test_start.max()

# primary summary
S = R["summary"]["n80_a0.10_A"]
RULES = ["SCD", "EMP", "ACI_g0.05", "MOL", "SIPP", "ACA", "ORACLE"]
RT = {"SCD": "SCD", "EMP": "EMP", "ACI_g0.05": "ACI", "MOL": "MOL", "SIPP": "SIPP", "ACA": "ACA", "ORACLE": "OR"}
for r in RULES:
    covs = [S[s][r]["coverage"] for s in SYS]
    rel = [S[s][r]["rel_oracle_median"] for s in SYS]
    M[f"cov{RT[r]}Min"], M[f"cov{RT[r]}Max"] = rng(covs, lambda x: f(x, 3))
    M[f"rel{RT[r]}Min"], M[f"rel{RT[r]}Max"] = rng(rel, lambda x: f(x, 2))
    M[f"prem{RT[r]}Min"], M[f"prem{RT[r]}Max"] = rng([x - 1 for x in rel], lambda x: pct(x, 0))
    M[f"short{RT[r]}Min"], M[f"short{RT[r]}Max"] = rng([1 - x for x in rel], lambda x: pct(x, 0))
    M[f"miss{RT[r]}Min"], M[f"miss{RT[r]}Max"] = rng([1 - x for x in covs], lambda x: pct(x, 0))
    below = [S[s][r]["share_below_075"] for s in SYS]
    M[f"below{RT[r]}Min"], M[f"below{RT[r]}Max"] = rng(below, lambda x: pct(x, 0))
    for s in SYS:
        v = S[s][r]
        k = f"{RT[r]}{TAG[s]}"
        M[f"cov{k}"] = f(v["coverage"], 3)
        M[f"lo{k}"] = f(v["cov_lo"], 3)
        M[f"hi{k}"] = f(v["cov_hi"], 3)
        M[f"rel{k}"] = f(v["rel_oracle_median"], 2)
        M[f"uh{k}"] = f"{v['uh']:,.0f}"
        M[f"fracA{k}"] = pct(v["fracA"], 1)
M["flagsAll"] = str(sum(S[s][r]["flags"] for s in SYS for r in ["SCD", "EMP", "ACI_g0.05"]))
# extra unit-hours of SCD over MOL and over ORACLE, in units on duty around the clock
for s in SYS:
    t = TAG[s]
    M[f"extraOR{t}"] = f((S[s]["SCD"]["uh"] - S[s]["ORACLE"]["uh"]) / 24, 1)
    M[f"extraMOL{t}"] = pct(S[s]["SCD"]["uh"] / S[s]["MOL"]["uh"] - 1, 0)
ex = [S[s]["SCD"]["uh"] / S[s]["MOL"]["uh"] - 1 for s in SYS]
M["extraMOLMin"], M["extraMOLMax"] = pct(min(ex), 0), pct(max(ex), 0)
aci = [S[s]["ACI_g0.05"]["uh"] / S[s]["SCD"]["uh"] - 1 for s in SYS]
M["aciOverSCDMin"], M["aciOverSCDMax"] = pct(min(aci), 1), pct(max(aci), 1)
aca = [S[s]["ACA"]["uh"] / S[s]["SCD"]["uh"] - 1 for s in SYS]
M["acaOverSCDMin"], M["acaOverSCDMax"] = pct(min(aca), 0), pct(max(aca), 0)

# hypotheses
H = R["hypotheses"]
M["hOneOk"] = str(H["H1"]["systems_ok"])
lo = H["H1"]["lower_bounds"]
M["hOneLoMin"], M["hOneLoMax"] = f(min(lo.values()), 3), f(max(lo.values()), 3)
for s in SYS:
    M[f"hOneLo{TAG[s]}"] = f(lo[s], 3)
M["hOneFail"] = ", ".join(TAG[s] for s in SYS if lo[s] < 0.85)
p2 = H["H2"]["p"]
M["hTwoPMin"], M["hTwoPMax"] = f(min(p2.values()), 3), f(max(p2.values()), 2)
M["hTwoSig"] = str(H["H2"]["n_sig"])
M["hTwoHolmMin"] = f(min(H["H2"]["p_holm"].values()), 3)
M["empBelowScd"] = str(sum(S[s]["EMP"]["coverage"] < S[s]["SCD"]["coverage"] for s in SYS))
M["hThreeSig"] = str(H["H3"]["n_sig"])
M["hThreePMax"] = f"{max(H['H3']['p_holm'].values()):.1e}".replace("e-0", "e-")
M["hFourRho"] = f(H["H4"]["rho"], 2)
M["hFourP"] = f(H["H4"]["p_one_sided"], 4)

# conditional-coverage check (primary)
C = R["conditional"]["n80_a0.10_A"]
M["condSdObs"], M["condSdTh"] = f(C["pooled"]["sd"], 3), f(C["theory"]["sd"], 3)
M["condBelowObs"], M["condBelowTh"] = pct(C["pooled"]["p_below_075"], 1), pct(C["theory"]["p_below_075"], 1)
M["condMeanTh"] = f(C["theory"]["mean"], 3)

# H4 descriptives: SCD coverage when load grew vs not
g = P[(P.rule == "SCD") & (P.n == 80) & (P.alpha == 0.1) & (P.target == "A")]
up = g[g.load_ratio > 1.03]
dn = g[g.load_ratio < 0.97]
mid = g[(g.load_ratio >= 0.97) & (g.load_ratio <= 1.03)]
M["covLoadUp"], M["nLoadUp"] = f(up.coverage.mean(), 3), str(len(up))
M["covLoadDown"], M["nLoadDown"] = f(dn.coverage.mean(), 3), str(len(dn))
M["covLoadFlat"], M["nLoadFlat"] = f(mid.coverage.mean(), 3), str(len(mid))
M["loadRatioMin"], M["loadRatioMax"] = f(g.load_ratio.min(), 2), f(g.load_ratio.max(), 2)

# secondary configurations: SCD and ACI ranges
for key, tag in [("n40_a0.10_A", "nForty"), ("n160_a0.10_A", "nOneSixty"), ("n80_a0.05_A", "aFive"),
                 ("n80_a0.20_A", "aTwenty"), ("n80_a0.10_B", "tTen")]:
    T = R["summary"][key]
    for r, rt in [("SCD", "SCD"), ("ACI_g0.05", "ACI"), ("EMP", "EMP"), ("MOL", "MOL"), ("ACA", "ACA")]:
        c = [T[s][r]["coverage"] for s in SYS]
        rel = [T[s][r]["rel_oracle_median"] for s in SYS]
        M[f"{tag}cov{rt}Min"], M[f"{tag}cov{rt}Max"] = f(min(c), 3), f(max(c), 3)
        M[f"{tag}rel{rt}Min"], M[f"{tag}rel{rt}Max"] = f(min(rel), 2), f(max(rel), 2)
for gm in ("0.02", "0.10"):
    c = [S[s][f"ACI_g{gm}"]["coverage"] for s in SYS]
    t = "gTwo" if gm == "0.02" else "gTen"
    M[f"{t}covMin"], M[f"{t}covMax"] = f(min(c), 3), f(max(c), 3)

with open("paper/macros.tex", "w", encoding="utf-8") as fh:
    fh.write("% generated by code/make_macros.py -- do not edit\n\\makeatletter\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\expandafter\\def\\csname res@{k}\\endcsname{{{v}}}\n")
    fh.write("\\makeatother\n\\newcommand{\\res}[1]{\\ifcsname res@#1\\endcsname\\csname res@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
json.dump(M, open("out/macros.json", "w"), indent=0)
print(len(M), "macros")
