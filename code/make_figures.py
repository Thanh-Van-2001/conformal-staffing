"""Figures for the paper (primary configuration n = 80, alpha = 0.10, target A).
Run from the repository root: python -I code/make_figures.py"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R = json.load(open("out/results.json"))
P = pd.read_csv("out/panel.csv.gz")
SYS = ["NYC_AREA", "NYC_SI", "NYC_BX", "NYC_MN", "NYC_QN", "NYC_BK", "SF"]
LAB = {"NYC_AREA": "NYC area Q4", "NYC_SI": "Staten Island", "NYC_BX": "Bronx", "NYC_MN": "Manhattan",
       "NYC_QN": "Queens", "NYC_BK": "Brooklyn", "SF": "San Francisco"}
# Okabe-Ito (colour-blind safe), fixed order; marker shapes as a second cue
RULES = [("SCD", "SCD (split conformal)", "#0072B2", "o"), ("ACI_g0.05", "ACI (adaptive conformal)", "#009E73", "D"),
         ("EMP", "EMP (in-sample)", "#56B4E9", "s"), ("MOL", "MOL (Erlang-C)", "#E69F00", "^"),
         ("SIPP", "SIPP (Erlang-C)", "#D55E00", "v"), ("ACA", "ACA (conformal on arrivals)", "#CC79A7", "P")]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#555555", "axes.labelcolor": "#222222", "xtick.color": "#444444",
                     "ytick.color": "#444444", "savefig.dpi": 300})
S = R["summary"]["n80_a0.10_A"]

# Figure 1: coverage vs cost
fig, ax = plt.subplots(figsize=(6.3, 3.9))
ax.axvline(0.90, color="#888888", lw=0.8, ls="--", zorder=0)
ax.axhline(1.00, color="#bbbbbb", lw=0.8, zorder=0)
ax.text(0.893, 1.93, "target:\n90% of days", fontsize=7, color="#555555", va="top", ha="right")
ins = ax.inset_axes([0.43, 0.30, 0.36, 0.40])
for r, lab, col, mk in RULES:
    x = [S[s][r]["coverage"] for s in SYS]
    y = [S[s][r]["rel_oracle_mean"] for s in SYS]
    ax.scatter(x, y, s=34, marker=mk, color=col, edgecolor="white", linewidth=0.7, label=lab, zorder=3)
    ins.scatter(x, y, s=30, marker=mk, color=col, edgecolor="white", linewidth=0.6, zorder=3)
ins.axvline(0.90, color="#888888", lw=0.8, ls="--", zorder=0)
ins.axhline(1.00, color="#bbbbbb", lw=0.8, zorder=0)
ins.set_xlim(0.84, 0.915)
ins.set_ylim(0.99, 1.055)
ins.tick_params(labelsize=6.5)
ins.grid(color="#eeeeee", lw=0.5)
ins.set_title("zoom", fontsize=7, loc="left", color="#555555")
ax.indicate_inset_zoom(ins, edgecolor="#999999", lw=0.7)
ax.set_xlabel("Share of test days meeting the target (coverage)")
ax.set_ylabel("Unit-hours relative to the hindsight plan")
ax.set_xlim(0.35, 1.03)
ax.set_ylim(0.85, 1.97)
ax.grid(axis="both", color="#eeeeee", lw=0.6)
ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=1)
fig.tight_layout()
fig.savefig("paper/fig_coverage_cost.pdf")
fig.savefig("out/fig_coverage_cost.png")
plt.close(fig)

# Figure 2: drift. (a) SCD window coverage vs load growth; (b) SCD vs ACI per system
g = P[(P.rule == "SCD") & (P.n == 80) & (P.alpha == 0.1) & (P.target == "A")]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 3.0), gridspec_kw={"width_ratios": [1.35, 1]})
rng = np.random.default_rng(1)
a1.scatter(g.load_ratio, g.coverage + rng.uniform(-0.008, 0.008, len(g)), s=9, color="#0072B2", alpha=0.45,
           edgecolor="none", label="test window")
bins = np.quantile(g.load_ratio, np.linspace(0, 1, 8))
mid = 0.5 * (bins[1:] + bins[:-1])
means = [g.coverage[(g.load_ratio >= lo) & (g.load_ratio <= hi)].mean() for lo, hi in zip(bins[:-1], bins[1:])]
a1.plot(mid, means, color="#222222", lw=1.6, marker="o", ms=3.5, label="mean by load-change bin")
a1.axhline(0.90, color="#888888", lw=0.8, ls="--")
a1.set_xlabel("Calls per day, test window / calibration days")
a1.set_ylabel("SCD coverage in the window")
a1.set_ylim(0.0, 1.05)
a1.grid(color="#eeeeee", lw=0.6)
a1.legend(frameon=False, fontsize=7, loc="lower left")
a1.set_title("(a) Coverage falls when load grows", fontsize=9, loc="left")
y = np.arange(len(SYS))
for i, s in enumerate(SYS):
    pass
for r, col, mk, dy, lab in (("SCD", "#0072B2", "o", 0.12, "SCD"), ("ACI_g0.05", "#009E73", "D", -0.12, "ACI")):
    xs = np.array([S[s][r]["coverage"] for s in SYS])
    err = np.array([[S[s][r]["coverage"] - S[s][r]["cov_lo"] for s in SYS], [S[s][r]["cov_hi"] - S[s][r]["coverage"] for s in SYS]])
    a2.errorbar(xs, y + dy, xerr=err, fmt="none", ecolor=col, elinewidth=0.9, alpha=0.6, zorder=2)
    a2.scatter(xs, y + dy, color=col, marker=mk, s=22, label=lab, zorder=3)
a2.axvline(0.90, color="#888888", lw=0.8, ls="--")
a2.set_yticks(y, [LAB[s] for s in SYS])
a2.set_xlim(0.80, 0.97)
a2.set_xlabel("Pooled coverage")
a2.grid(axis="x", color="#eeeeee", lw=0.6)
a2.legend(frameon=False, fontsize=7, loc="upper left")
a2.set_title("(b) SCD vs ACI (95% CI)", fontsize=9, loc="left")
fig.tight_layout()
fig.savefig("paper/fig_drift.pdf")
fig.savefig("out/fig_drift.png")
plt.close(fig)
print("figures written")
