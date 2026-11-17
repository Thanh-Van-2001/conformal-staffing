# Conformal staffing guarantees for EMS

Replication package for *How many ambulances for nine good days in ten? A
distribution-free staffing guarantee tested in seven EMS systems*.

- `PLAN.md` — the pre-specified analysis plan and its amendment log. The git
  history shows that the plan and the analysis code were committed before
  the results.
- `code/sim.py` — trace-driven simulator of one ambulance pool (first come,
  first served, hourly staffing levels), from the author's earlier EMS study.
- `code/exp.py` — evaluates the square-root plan family on a grid of safety
  factors for calibration, training and test days, and simulates the Erlang-C
  (SIPP, MOL) and conformal-on-arrivals (ACA) plans.
- `code/analyze.py` — applies the rules (SCD, EMP, ACI, hindsight) and tests
  hypotheses H1–H4.
- `code/make_macros.py`, `code/make_figures.py` — every number and figure in
  the paper.
- `refs/build_bib.py` — builds `paper/refs.bib` from Crossref and arXiv, so
  every reference is checked.
- `out/` — results (`results.json`, `panel.csv.gz`); `facts/prep_log.json` —
  data preparation log.

## Data

The data are public: NYC Open Data *EMS Incident Dispatch Data* (76xm-jjuj)
and DataSF *Fire Department and Emergency Medical Services Dispatched Calls
for Service* (nuek-vuh3), weekdays 2022–2025. The per-system day arrays
(`sys_<name>.npz`) are built by the preparation script of the earlier
study, which is summarised in `facts/prep_log.json`.

## Run

```
python -I code/exp.py <data_dir> out 6        # about 4 minutes on 6 cores
python -I code/analyze.py out
python -I code/make_macros.py && python -I code/make_figures.py
```

Python 3.11 with numpy, numba, pandas, scipy and matplotlib.

## Licence

MIT (code). The data remain under their publishers' terms.
