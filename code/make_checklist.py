"""STRESS-DES reporting checklist (Monks et al., J Simulation 2019) for the
submission. Run from the repository root: python -I code/make_checklist.py"""
import json
import re

import docx
from docx.shared import Pt

M = json.load(open("out/macros.json"))
info = json.load(open("out/RUN_INFO.json"))
SW = json.load(open("facts/software_versions.json"))
X3 = json.load(open("out/RUN_INFO_amend3.json"))
X4 = json.load(open("out/RUN_INFO_amend4.json"))
ROWS = [
    ("Objectives", None, None),
    ("1.1", "Purpose of the model", "Introduction (last paragraph); Methods, Study design and data: test whether calibrating an hourly "
     "ambulance staffing plan on recent days meets a day-level service target on 9 of 10 days, and at what cost."),
    ("1.2", "Model outputs", "Methods, Service model and outcomes: per day, the fraction of calls that waited for a free unit and "
     "the fraction waiting > 10 min; coverage = share of days meeting the target; cost = unit-hours per day."),
    ("1.3", "Experimentation aims", "Methods, Analysis plan and statistical analysis: hypotheses H1-H4 and secondary configurations "
     "(training days 40/80/160; alpha 0.05/0.10/0.20; 10-minute target); exploratory baselines of amendments 3 and 4 "
     "(WCP, TAB, TAB-ACI, ACA0, QT, SCD-I, CRC-share), Methods, Exploratory baselines."),
    ("Logic", None, None),
    ("2.1", "Base model overview diagram", "Methods, Service model and outcomes. The model is one pool of units serving one "
     "first-come-first-served queue; it is described in text rather than a diagram."),
    ("2.2", "Base model logic", "Methods, Service model and outcomes; code/sim.py."),
    ("2.3", "Scenario logic", "Methods, Staffing rules: scenarios differ only in the hourly staffing plan c (SCD, EMP, SIPP, MOL, "
     "ACA, ACI, hindsight; exploratory WCP, TAB, TAB-ACI, ACA0, QT, SCD-I, CRC-share); the queue logic is unchanged."),
    ("2.4", "Algorithms", "Methods, Staffing rules: square-root plan family, conformal rank, Erlang-C (delay probability and "
     "10-minute tail), ACA load kernel, ACI level update, recency weights, trend projection, PID-type updates, "
     "conformal risk control; code/exp.py, code/analyze.py, code/*_amend3.py, code/*_amend4.py."),
    ("2.5.1", "Components: entities", "Calls (one per incident), each with its recorded arrival time and busy time."),
    ("2.5.2", "Components: activities", "Service: a unit is busy with a call for its recorded busy time."),
    ("2.5.3", "Components: resources", "Ambulance units; c_p units on duty in hour p; a unit busy at the end of an hour finishes "
     "its call."),
    ("2.5.4", "Components: queues", "One first-come-first-served queue; no priorities, balking or abandonment."),
    ("2.5.5", "Components: entry/exit points", "Calls enter at their recorded time and leave at service completion. Each "
     "operational day (04:00-04:00) starts empty and runs until the queue clears (Limitations quantify carry-over)."),
    ("Data", None, None),
    ("3.1", "Data sources", "Methods, Study design and data: NYC Open Data EMS Incident Dispatch Data (76xm-jjuj); DataSF Fire "
     "Department and EMS Dispatched Calls for Service (nuek-vuh3); weekdays 2022-2025."),
    ("3.2", "Pre-processing", "Methods, Study design and data: weekdays, US federal holidays removed, busy times outside 1 min "
     "to 6 h dropped, low-count days rule; facts/prep_log.json."),
    ("3.3", "Input parameters", "Trace-driven: recorded arrival and busy times are used directly (Table 1 summarises them). "
     "Rule parameters: beta = 0.05 (0.01 for the 10-minute target), alpha, n, theta grid -2 to 10 step 0.05, gamma."),
    ("3.4", "Assumptions", "Single closed pool per area, one unit per call, no travel or geography, empty start at 04:00 "
     "(Methods; Limitations)."),
    ("Experimentation", None, None),
    ("4.1", "Initialisation", "Terminating simulation: each operational day starts empty at 04:00 (no warm-up)."),
    ("4.2", "Run length", f"Each day from 04:00 until the queue clears; {M['nDays']} days per area; {M['nWindows']} test windows "
     "of 20 days; time unit hours."),
    ("4.3", "Estimation approach", "The simulation is deterministic given the recorded trace (no random sampling). Uncertainty "
     "across planning dates: moving-block bootstrap (blocks of 4, 10,000 replicates)."),
    ("Implementation", None, None),
    ("5.1", "Software or programming language", f"Python {SW['python']} (NumPy {SW['numpy']}, Numba {SW['numba']}, "
     f"pandas {SW['pandas']}, SciPy {SW['scipy']}) on {SW['os_release']} (facts/software_versions.json)."),
    ("5.2", "Random sampling", "None in the simulator. Bootstrap and permutation tests use NumPy's default generator (PCG64) "
     "with fixed seeds."),
    ("5.3", "Model execution", "Next-event simulation of a multi-server queue: a binary heap of unit release times "
     "(code/sim.py, compiled with Numba)."),
    ("5.4", "System specification", f"{info['tasks']} tasks in {info['secs']:.0f} s on 6 cores of an AMD Ryzen 9 9950X "
     f"(32 threads) shared server; amendments 3 and 4: {X3['tasks']} and {X4['tasks']} tasks on 2 cores (minutes "
     "each; restarted from finished files after memory-guard stops)."),
    ("Code access", None, None),
    ("6.1", "Computer model sharing statement", "https://github.com/Thanh-Van-2001/conformal-staffing (MIT licence): "
     "simulator, analysis code, analysis plan with commit history, results."),
]
# IISE THSE (double-anonymous review): no repository address, the section is
# "Materials and methods", American spelling. The PEC rows above are unchanged.
ANON_SHARING = ("Simulator, analysis code, analysis plan with commit history and results: available from the corresponding "
                "author on request and to be deposited in a public repository (MIT license) upon acceptance; address "
                "withheld for anonymous review.")


def thse_rows():
    out = []
    for item, name, where in ROWS:
        if name is not None:
            where = ANON_SHARING if item == "6.1" else where
            where = re.sub(r"\bMethods\b", "Materials and methods", where)
            where = where.replace("summarises", "summarizes")
            assert "github" not in where.lower() and "licence" not in where
        out.append((item, name, where))
    return out


def build(path, rows, anonymous=False):
    d = docx.Document()
    if anonymous:
        d.core_properties.author = ""
        d.core_properties.last_modified_by = ""
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(10)
    d.add_heading("STRESS-DES reporting checklist", level=1)
    d.add_paragraph("Manuscript: How many ambulances for nine good days in ten? A conformal staffing rule tested in seven EMS "
                    "service areas. Checklist items from Monks et al., Journal of Simulation 2019;13(1):55-67, "
                    "doi:10.1080/17477778.2018.1442155.")
    t = d.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, ("Item", "Name", "Where and how reported")):
        c.text = h
        c.paragraphs[0].runs[0].bold = True
    for item, name, where in rows:
        r = t.add_row().cells
        if name is None:
            m = r[0].merge(r[1]).merge(r[2])
            m.text = item
            m.paragraphs[0].runs[0].bold = True
        else:
            r[0].text, r[1].text, r[2].text = item, name, where
    d.save(path)
    return sum(1 for r in rows if r[1])


if __name__ == "__main__":
    n = build("paper/submission/STRESS_DES_checklist.docx", ROWS)
    print("checklist written:", n, "items")
