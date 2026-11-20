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
    rel = [S[s][r]["rel_oracle_mean"] for s in SYS]  # ratio of mean unit-hours (amendment 2)
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
        M[f"rel{k}"] = f(v["rel_oracle_mean"], 2)
        M[f"below{k}"] = pct(v["share_below_075"], 0)
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
for s in SYS:
    M[f"unitsMOL{TAG[s]}"] = f((S[s]["SCD"]["uh"] - S[s]["MOL"]["uh"]) / 24, 1)
relh = [S[s]["SCD"]["rel_oracle_h_mean"] for s in SYS]
M["relHSCDMin"], M["relHSCDMax"] = f(min(relh), 2), f(max(relh), 2)
relh = [S[s]["ACI_g0.05"]["rel_oracle_h_mean"] for s in SYS]
M["relHACIMin"], M["relHACIMax"] = f(min(relh), 2), f(max(relh), 2)
band = [S[s]["ACA"]["uh"] / S[s]["MOL"]["uh"] - 1 for s in SYS]
M["acaOverMOLMin"], M["acaOverMOLMax"] = pct(min(band), 0), pct(max(band), 0)
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
        rel = [T[s][r]["rel_oracle_mean"] for s in SYS]  # ratio of mean unit-hours, as everywhere (amendment 2)
        M[f"{tag}cov{rt}Min"], M[f"{tag}cov{rt}Max"] = f(min(c), 3), f(max(c), 3)
        M[f"{tag}rel{rt}Min"], M[f"{tag}rel{rt}Max"] = f(min(rel), 2), f(max(rel), 2)
c = [S[s][f"ACI_g{gm}"]["coverage"] for s in SYS for gm in ("0.02", "0.10")]
M["gOthercovMin"], M["gOthercovMax"] = f(min(c), 3), f(max(c), 3)

# amendment 2: exploratory additions
E = R["exploratory"]
M["hOneSeedMin"], M["hOneSeedMax"] = str(E["h1_seed"]["min"]), str(E["h1_seed"]["max"])
M["hOneSeedShareMax"] = pct(E["h1_seed"]["share_max"], 0)
M["hOneNoQMin"], M["hOneNoQMax"] = str(E["h1_seed"]["noq4_min"]), str(E["h1_seed"]["noq4_max"])
M["bkLoMin"], M["bkLoMax"] = f(E["h1_seed"]["bk_lo_min"], 3), f(E["h1_seed"]["bk_lo_max"], 3)
ph = E["aci_vs_scd_p_holm"]
M["aciSig"] = str(sum(v < 0.05 for v in ph.values()))
_names = [{"NYC_BX": "the Bronx", "NYC_QN": "Queens", "NYC_BK": "Brooklyn", "NYC_MN": "Manhattan",
                              "NYC_SI": "Staten Island", "SF": "San Francisco", "NYC_AREA": "area Q4"}[k]
                             for k in SYS if ph[k] < 0.05]
M["aciSigNames"] = (", ".join(_names[:-1]) + " and " + _names[-1]) if len(_names) > 1 else "".join(_names)
M["aciSigPMax"] = f(max(v for v in ph.values() if v < 0.05), 3)
wr = E["h4_within_rho"].values()
M["hFourWithinMin"], M["hFourWithinMax"] = f(min(wr), 2), f(max(wr), 2)
M["hFourCircP"] = f(E["h4_circular_p"], 4)
M["spreadP"] = "<0.001" if E["spread_p"] < 0.001 else f(E["spread_p"], 3)
B = E["below_nominal"]
for key, tag in [("n40_a0.10_A", "nForty"), ("n160_a0.10_A", "nOneSixty"), ("n80_a0.05_A", "aFive"),
                 ("n80_a0.20_A", "aTwenty"), ("n80_a0.10_B", "tTen"), ("n80_a0.10_A", "prim")]:
    M[f"{tag}belowSCD"], M[f"{tag}belowACI"], M[f"{tag}belowEMP"] = (str(B[key]["SCD"]), str(B[key]["ACI_g0.05"]),
                                                                    str(B[key]["EMP"]))
DC = json.load(open("facts/data_checks.json"))
M["carryBK"] = f(DC["NYC_BK"]["carry_over_mean"], 0)
M["ownBK"] = f(DC["NYC_BK"]["own_in_service_0430_mean"], 0)
cr = [DC[s]["carry_over_mean"] for s in SYS]
M["carryMin"], M["carryMax"] = f(min(cr), 0), f(max(cr), 0)
sh = [DC[s]["share_svc_lt15min"] for s in SYS]
M["shortSvcMin"], M["shortSvcMax"] = pct(min(sh), 0), pct(max(sh), 0)
M["shortSvcNYCMax"] = pct(max(DC[s]["share_svc_lt15min"] for s in SYS if s != "SF"), 0)
M["shortSvcSF"] = pct(DC["SF"]["share_svc_lt15min"], 0)

# SCD at the 95% level against SCD at 90% (pre-specified secondary configuration), extra unit-hours
S5 = R["summary"]["n80_a0.05_A"]
x = [S5[s]["SCD"]["uh"] / S[s]["SCD"]["uh"] - 1 for s in SYS]
M["aFiveOverSCDMin"], M["aFiveOverSCDMax"] = pct(min(x), 1), pct(max(x), 1)

# amendment 3: exploratory rules (out/amend3_results.json, out/panel_amend3.csv.gz)
X = json.load(open("out/amend3_results.json"))
XP = pd.read_csv("out/panel_amend3.csv.gz")
XS = X["summary"]["n80_a0.10_A"]
XT = {"SCD": "SCD", "ACI": "ACI", "WCP_H20": "WCP", "WCP_H10": "WCPten", "WCP_H40": "WCPforty", "TAB": "TAB",
      "TAB_ACI": "TABACI", "ACA0": "ACAZ"}
# amendment 4 (out/amend4_results.json): conformal PID controllers and conformal risk control
X4 = json.load(open("out/amend4_results.json"))
assert X4["crc_binary_equals_scd_mismatches"] == 0
XS4 = X4["summary"]["n80_a0.10_A"]
XT4 = {"QT_c0.10": "QT", "SCDI_c0.10": "SCDI", "CRCS": "CRCS", "QT_c0.05": "QTlo", "QT_c0.20": "QThi",
       "SCDI_c0.05": "SCDIlo", "SCDI_c0.20": "SCDIhi"}
for s in SYS:  # amendment 4 recomputes SCD too
    assert f(XS4["SCD"]["per_system"][s]["coverage"], 3) == M[f"covSCD{TAG[s]}"], s
for r, t in list(XT.items()) + list(XT4.items()):
    v = XS[r] if r in XT else XS4[r]
    per = v["per_system"]
    M[f"x{t}covMin"], M[f"x{t}covMax"] = rng([per[s]["coverage"] for s in SYS], lambda q: f(q, 3))
    M[f"x{t}overSCDMin"], M[f"x{t}overSCDMax"] = rng([per[s]["rel_scd"] - 1 for s in SYS], lambda q: pct(q, 1))
    M[f"x{t}relORMin"], M[f"x{t}relORMax"] = rng([per[s]["rel_oracle"] for s in SYS], lambda q: f(q, 2))
    M[f"x{t}below"], M[f"x{t}hOne"], M[f"x{t}sig"] = str(v["below_nominal"]), str(v["h1_count"]), str(v["sig_vs_scd"])
    M[f"x{t}hOneSeedMin"], M[f"x{t}hOneSeedMax"] = str(v["h1_seed_min"]), str(v["h1_seed_max"])
    M[f"x{t}rho"] = f(v["rho"], 2)
    M[f"x{t}flags"] = str(sum(per[s]["flags"] for s in SYS))
    for s in SYS:
        M[f"x{t}cov{TAG[s]}"] = f(per[s]["coverage"], 3)
        M[f"x{t}over{TAG[s]}"] = pct(per[s]["rel_scd"] - 1, 1)
# the amendment-3 analysis recomputes SCD and ACI: they must match the pre-registered summary
for s in SYS:
    assert M[f"xSCDcov{TAG[s]}"] == M[f"covSCD{TAG[s]}"] and M[f"xACIcov{TAG[s]}"] == M[f"covACI{TAG[s]}"], s
assert M["xSCDrho"] == M["hFourRho"] and M["xSCDhOne"] == M["hOneOk"]
for key, tag in [("n40_a0.10_A", "nForty"), ("n160_a0.10_A", "nOneSixty"), ("n80_a0.05_A", "aFive"),
                 ("n80_a0.20_A", "aTwenty"), ("n80_a0.10_B", "tTen")]:
    for r, t in (("WCP_H20", "WCP"), ("TAB", "TAB"), ("ACA0", "ACAZ")):
        v = X["summary"][key][r]
        M[f"x{t}{tag}below"] = str(v["below_nominal"])
        M[f"x{t}{tag}flags"] = str(sum(v["per_system"][s]["flags"] for s in SYS))
        c = [v["per_system"][s]["coverage"] for s in SYS]
        M[f"x{t}{tag}covMin"], M[f"x{t}{tag}covMax"] = f(min(c), 3), f(max(c), 3)
M["xTabRMin"], M["xTabRMax"] = f(X["tab_r_test"]["80"]["min"], 2), f(X["tab_r_test"]["80"]["max"], 2)
for r, t in (("CRCS", "CRCS"), ("SCD", "SCD"), ("QT_c0.10", "QT"), ("SCDI_c0.10", "SCDI")):
    sh = X4["share_delayed"][r].values()
    M[f"x{t}shareMin"], M[f"x{t}shareMax"] = pct(min(sh), 1), pct(max(sh), 1)
for key, tag in [("n40_a0.10_A", "nForty"), ("n160_a0.10_A", "nOneSixty"), ("n80_a0.05_A", "aFive"),
                 ("n80_a0.20_A", "aTwenty"), ("n80_a0.10_B", "tTen")]:
    for r, t in (("QT_c0.10", "QT"), ("SCDI_c0.10", "SCDI")):
        M[f"x{t}{tag}below"] = str(X4["summary"][key][r]["below_nominal"])
M["xFourTasks"] = str(json.load(open("out/RUN_INFO_amend4.json"))["tasks"])
cr = [XS4["CRCS"]["per_system"][s]["coverage"] for s in SYS]
M["xCRCSmissMin"], M["xCRCSmissMax"] = pct(1 - max(cr), 0), pct(1 - min(cr), 0)
# ACA0 built at the 80% level against SCD at 90%
q = XP[(XP.n == 80) & (XP.target == "A")]
cov20, over20 = [], []
for s in SYS:
    a0 = q[(q.system == s) & (q.rule == "ACA0") & (q.alpha == 0.2)]
    sc = q[(q.system == s) & (q.rule == "SCD") & (q.alpha == 0.1)]
    cov20.append(a0.coverage.mean())
    over20.append(a0.uh.mean() / sc.uh.mean() - 1)
M["xACAZtwcovMin"], M["xACAZtwcovMax"] = f(min(cov20), 3), f(max(cov20), 3)
M["xACAZtwoverSCDMin"], M["xACAZtwoverSCDMax"] = pct(min(over20), 1), pct(max(over20), 1)
# share of calibration weight (WCP, H = 20) or of days (SCD) that must lie at or below theta-hat; n = 80, alpha = 0.10
h, Hl, al = 40, 20, 0.10
w = 2.0 ** (-(h - 1 - np.arange(h)) / Hl)
M["xWCPshare"] = pct((1 - al) * (w.sum() + 1) / w.sum(), 1)
M["xSCDshare"] = pct(int(np.ceil((h + 1) * (1 - al))) / h, 1)
SW = json.load(open("facts/software_versions.json"))
M["swPython"], M["swNumpy"], M["swNumba"] = SW["python"], SW["numpy"], SW["numba"]
M["swPandas"], M["swScipy"], M["swOS"] = SW["pandas"], SW["scipy"], SW["os_release"]
M["xTABlower"] = str(sum(XS["TAB"]["per_system"][s]["coverage"] < XS["SCD"]["per_system"][s]["coverage"] for s in SYS))
# percent forms for the cover letter
for k in ("covSCDMin", "covSCDMax", "covSIPPMin", "covMOLMax", "covACIMin", "covACIMax", "xWCPcovMin", "xWCPcovMax"):
    M[k + "Pct"] = pct(float(M[k]), 0)
M["xTasks"] = str(json.load(open("out/RUN_INFO_amend3.json"))["tasks"])
M["xSecs"] = f(json.load(open("out/RUN_INFO_amend3.json"))["secs"], 0)

with open("paper/macros.tex", "w", encoding="utf-8") as fh:
    fh.write("% generated by code/make_macros.py -- do not edit\n\\makeatletter\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\expandafter\\def\\csname res@{k}\\endcsname{{{v}}}\n")
    fh.write("\\makeatother\n\\newcommand{\\res}[1]{\\ifcsname res@#1\\endcsname\\csname res@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
json.dump(M, open("out/macros.json", "w"), indent=0)
print(len(M), "macros")
