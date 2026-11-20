# Pre-specified analysis plan: conformal staffing guarantees for EMS

Committed to git before any conformal, service-level or staffing-rule code
is run on the data. Amendments are appended at the end with dates and reasons;
nothing above the amendment log is edited after the first commit.

## Disclosure about the data

The data are the seven emergency medical service (EMS) systems prepared for an
earlier study by the same author (input models for ambulance staffing; under
review). That study chose cost-optimal plans by sample average approximation
and compared arrival models; it computed no service-level guarantee, no
chance-constrained plan and no conformal quantity. Facts already known from
it: daily call counts are over-dispersed (dispersion index 1.8 to 4.6), mean
busy times are 65 to 71 minutes, and loads drift over 2022 to 2025. No result
in this plan has been computed before this commit.

Systems (weekday operational days 04:00 to 04:00, 2022-01-03 to 2025-12-30,
999 days each): NYC_AREA (one dispatch area), NYC_SI, NYC_BX, NYC_MN,
NYC_QN, NYC_BK (boroughs), SF (San Francisco medic units). One call needs one
unit for its recorded busy time; units form one pool; calls wait first come,
first served (trace-driven simulator `sim.py` from the earlier study, used
unchanged).

## Question

Can an hourly ambulance staffing plan carry a finite-sample,
distribution-free guarantee that the service-level target is met on at least
a fraction 1 - alpha of future days, and what does the guarantee cost
compared with the rules used in practice?

## Definitions

- Plan: c = (c_0, ..., c_23), units on duty in each hour of the operational
  day (held at c_23 after the day ends until the queue clears).
- Day d meets the target if the fraction of its calls that wait for a unit
  (wait > 0) is at most beta = 0.05. Secondary target: fraction waiting more
  than 10 minutes at most 0.01.
- Plan family: c_p(theta) = max(1, ceil(m_p + theta * sqrt(m_p))), with m_p the
  mean number of calls in service at the midpoint of hour p over the base
  days (square-root staffing). theta on the grid -2.00, -1.95, ..., 10.00.
  Monotonicity of "day meets target" in theta is checked on every grid; if a
  day ever violates it, its score is the smallest theta from which it meets
  the target at every larger grid value.
- Score of day i given base days B: theta_i(B) = smallest grid theta at
  which day i meets the target under c(theta). If none, theta_i = +inf.
- Coverage of a plan on a window: fraction of its days that meet the target.
- Cost: unit-hours per day, sum_p c_p.

## Design

- Training window: the n weekdays before an origin; n = 80 primary,
  40 and 160 secondary.
- Origins: o = 160, 180, ..., while o + 20 <= 999 (41 origins). Test window:
  the 20 weekdays from o. The same origins are used for every n.
- alpha = 0.10 primary; 0.05 and 0.20 secondary.

## Rules compared

1. SCD (split conformal on the decision, the proposal). Base = first n/2
   training days, calibration = last n/2. theta-hat = the k-th smallest
   calibration score, k = ceil((n/2 + 1)(1 - alpha)); if k > n/2 or the
   k-th score is +inf, use the top of the grid and flag the case.
2. EMP (in-sample chance constraint). Base = all n days; theta-hat = the
   ceil((1 - alpha) n)-th smallest score of the same n days.
3. SIPP (practitioner rule). For each hour, lambda_p = mean calls in hour p,
   E[S] = mean busy time, both over all n days; offered load a_p = lambda_p
   E[S]; c_p = smallest c with Erlang-C delay probability <= beta (c_p >= 1,
   c_p > a_p).
4. ACA (conformal on arrivals, then plug in). Base = first n/2 days give
   lambda-hat_p; calibration score of day i = max_p (N_ip - lambda-hat_p) /
   sqrt(lambda-hat_p) (N_ip = calls in hour p); q = k-th smallest score
   (same k as SCD); upper envelope U_p = lambda-hat_p + q sqrt(lambda-hat_p);
   then SIPP with lambda = U_p and E[S] from the base days.
5. ACI (adaptive conformal, window level). As SCD, but the level is updated
   across successive origins of a system: alpha_1 = alpha,
   alpha_{j+1} = alpha_j + gamma (alpha - miss_j), with miss_j = 1 - coverage of
   window j and gamma = 0.05; k uses alpha_j clipped to [0.001, 0.999].
6. ORACLE (hindsight, benchmark only). Base = all n days; theta = smallest
   grid theta at which at least ceil((1 - alpha) 20) of the 20 test days
   meet the target.

## Hypotheses and tests (primary configuration: n = 80, alpha = 0.10, beta = 0.05)

Uncertainty: moving-block bootstrap over origins within a system (block of 4
origins, 10,000 replicates), percentile 95% intervals. Paired comparisons
use origin-level values. Holm correction across the seven systems within
each hypothesis.

- H1 (validity). SCD's pooled test coverage is non-inferior to 1 - alpha:
  the lower 95% bound is at least 0.85 (margin 0.05). Supported if this holds
  in at least 6 of the 7 systems.
- H2 (in-sample optimism). EMP's coverage is lower than SCD's: one-sided
  Wilcoxon signed-rank on origin coverage, Holm-adjusted p < 0.05. Supported
  if significant in at least 4 of 7 systems.
- H3 (conformalizing the forecast over-staffs). ACA uses more unit-hours
  than SCD: one-sided Wilcoxon on origin unit-hours, Holm-adjusted p < 0.05.
  Supported if significant in at least 4 of 7 systems.
- H4 (drift). Across origins pooled over systems, SCD coverage falls as the
  load grows from the calibration days to the test days: Spearman rho
  between (mean daily calls in test window / mean in calibration days) and
  coverage is negative, one-sided p < 0.05 (permutation within systems).

Reported for every rule without a hypothesis: coverage, unit-hours, cost
relative to ORACLE, share of origins with coverage below 0.75, and SIPP's
coverage (the practitioner rule targets an hourly delay probability, not a
day-level risk, so no direction is predicted).

Conditional-coverage check: with n/2 calibration days the coverage
conditional on the calibration set is Beta(k, n/2 + 1 - k) under
exchangeability; the observed spread of window coverage is compared with
this distribution mixed with Binomial(20) sampling.

## Secondary and robustness (descriptive, no new hypotheses)

n in {40, 160}; alpha in {0.05, 0.20}; the 10-minute target; ACI with gamma in
{0.02, 0.10}.

## Workflow

1. Smoke test on NYC_SI, origins 160 and 180 only, primary configuration;
   used to check code and run time, not to tune anything. Any change after
   the smoke test is an amendment.
2. Full run on titan (nice 19, memory guard), results to `out/`.
3. Every number in the paper is a macro generated from `out/*.json`.

## Amendment log

### Amendment 1 (2026-11-18, before any code was run on the data)

Busy times average about 70 minutes, longer than the one-hour period, so
SIPP (offered load = hourly arrivals x mean busy time) is known to misplace
the load in time and would be a weak baseline; and ACA as written would mix
"conformalize the forecast" with SIPP's lag error. Changes:

- Added rule 3b, MOL (modified offered load, the standard fix for
  time-varying loads): a_p = m_p from all n days (mean number in service at
  the midpoint of hour p); c_p = smallest c > a_p with Erlang-C delay
  probability <= beta. SIPP is kept unchanged.
- ACA now plugs its envelope into MOL instead of SIPP: the envelope U_p of
  hourly arrivals is turned into a load m_p(U) = sum_j K_j U_{p-j}, where K_j is
  the probability that a call arriving uniformly within hour p - j is still
  in service at the midpoint of hour p, estimated from the base days' busy
  times; then Erlang-C as in MOL.
- For the secondary 10-minute target, SIPP, MOL and ACA use the Erlang-C
  tail P(W > t) = C(c, a) exp(-(c - a) t / E[S]) <= 0.01 with t = 10 minutes.
- H3 compares ACA (with the MOL plug-in) and SCD as before. MOL is reported
  like SIPP, with no predicted direction.

### Note (2026-11-18, after the full run; no analysis change)

- The smoke test (NYC_SI, origins 160 and 180, n = 80) ran without any code
  change; the full run used the committed code unchanged.
- Correction to the data disclosure above: per prep_log.json the dispersion
  index ranges 1.4 to 5.2, not 1.8 to 4.6 (quoted from memory). NYC_AREA
  (dispatch area Q4) is a subset of Queens, so its calls are counted once in
  totals.

### Amendment 2 (2026-11-18, after the results and an internal referee review)

No pre-specified test, rule or threshold changes; H1-H4 are reported as
pre-specified. Added, all labelled exploratory in the paper:

- H1 sensitivity to the bootstrap random seed (50 seeds; Brooklyn's bound
  sits at the 0.85 threshold), and H1 without NYC_AREA (a subset of Queens).
- Cost reported as the ratio of mean unit-hours (one convention for every
  cost figure), against the pre-specified hindsight plan and against a
  hindsight plan in SCD's own family (half-window base load).
- ACI vs SCD: paired one-sided Wilcoxon on window coverage per system.
- H4: within-system Spearman correlations and a circular-shift permutation
  test that keeps each system's serial dependence.
- Spread of window coverage: parametric-bootstrap p-value for the observed
  pooled standard deviation under the independent-days Beta-Binomial model.
- Counts of systems below nominal coverage in each secondary configuration.
- Descriptive data checks: calls still in service at 04:00 (carry-over that
  the simulator omits) and the share of very short busy times.

### Amendment 3 (2026-11-20, after the results and a second, independent referee-style review; written and committed before any computation below was run)

The review asked for baselines that address drift and for a forecast-band
baseline that does not stack a band on MOL's hourly margin. No pre-specified
rule, test, threshold or result changes; H1-H4 stay as reported. Everything
below is exploratory: it decides nothing and is reported whatever it shows.

New rules (same origins, training and test windows as the primary design):

- WCP (weighted split conformal; Barber et al. 2023, fixed weights). Uses
  SCD's base load, calibration scores and simulated test outcomes unchanged
  (no new simulation). Calibration day j = 1..h in time order (j = h the most
  recent) gets weight w_j = 2^(-(h - j)/H); the new day gets weight 1.
  theta-hat = smallest grid theta with sum_j w_j 1{theta_j <= theta} >=
  (1 - alpha)(sum_j w_j + 1); if there is none (including +inf scores), the
  top of the grid, flagged. Half-life H = 20 weekdays primary; H = 10 and 40
  as sensitivity values.
- TAB (trend-adjusted base load). As SCD (base load from the first n/2
  training days, scores from the last n/2), but the base load is rescaled to
  the trend in daily call counts. N-hat(t) = OLS line through the daily call
  counts of all n training days, t = 0..n-1; r(t) = N-hat(t) / N-hat(t_B),
  with t_B = (h - 1)/2 the midpoint of the base days. Calibration day t is
  scored with the plan family built on the load r(t) m_p. The test window
  gets one plan with load r(t*) m_p, t* = n + 9.5 (the midpoint of the 20 test
  days), and theta-hat = the k-th smallest score (same k as SCD). Cost =
  unit-hours of that plan. r is not clipped; its range is reported. The
  trend uses training-day call counts only (no outcomes), but the
  calibration days enter the trend fit, so the split-conformal argument no
  longer holds exactly.
- TAB-ACI: ACI's level update (gamma = 0.05) applied to TAB.
- ACA0 (conformal arrival band without the Erlang-C margin). ACA's envelope
  U_p and load m_p(U) as in amendment 1, staffed with c_p =
  max(1, ceil(m_p(U))), i.e. the square-root family at theta = 0 on the band
  load, so the band supplies the whole margin.

Computed for every system, origin, n in {40, 80, 160}, alpha in
{0.05, 0.10, 0.20} and both targets (TAB is evaluated on the whole theta grid,
so alpha enters only when the rules are applied).

Reported (primary configuration; secondary configurations descriptively):
coverage, unit-hours relative to SCD and to the hindsight plan, share of
windows below 0.75, number of systems below 1 - alpha; the H1 criterion
applied to each variant (lower moving-block bootstrap bound >= 0.85,
pre-specified seed; descriptive, not a new hypothesis); pooled Spearman rho
between load ratio and coverage per variant; per-system paired one-sided
Wilcoxon of window coverage against SCD with Holm adjustment.

Run on titan with nice 19 and a memory guard (the job is killed if
MemAvailable falls below 1.5 GB); new outcome files go to `out/amend3/`;
`results.json` is not touched. Code: `code/exp_amend3.py`,
`code/analyze_amend3.py`.

Note (2026-11-20, after the amendment 3 run): the run finished (861 tasks;
consistency checks passed: TAB with r = 1 reproduced SCD's stored scores and
outcomes, the recomputed ACA envelope reproduced the stored ACA plans). The
memory guard stopped the first attempt once (MemAvailable 1.53 GB, caused by
other users); the run resumed from the finished files with 2 workers. The
secondary-configuration cost macros used the median ratio to hindsight; they
now use the ratio of mean unit-hours, the convention amendment 2 set for
every cost figure (reporting only; no rule or test changes).

### Amendment 4 (2026-11-20, after the amendment 3 results; written and committed before any computation below was run)

Reason: a request to compare against current conformal methods for drift
and decision losses. Same status as amendment 3: exploratory, decides
nothing, reported whatever it shows; pre-registered results unchanged.

- QT (quantile tracking, the P part of conformal PID control; Angelopoulos,
  Candes and Tibshirani 2023). Per system, theta_1 = SCD's theta-hat at the
  first origin; theta_{j+1} = theta_j + eta_j (miss_j - alpha), where miss_j is
  the share of window j's test days that missed the target, rounded to the
  grid and clipped to [-2, 10]. Base load and outcomes are SCD's (first n/2
  training days of each origin); no new calibration after the first origin.
- SCD-I (SCD as the scorecaster plus an integrator, the I part of conformal
  PID control). theta_j = SCD's theta-hat_j + D_j, D_1 = 0,
  D_{j+1} = D_j + eta_j (miss_j - alpha), rounded and clipped as above.
- Step: eta_j = c (max - min of the finite calibration scores at origin j),
  a step proportional to the score scale; c = 0.1 primary, 0.05 and 0.2
  sensitivity. No new simulation (SCD's stored grid outcomes are used).
- CRC-share (conformal risk control, Angelopoulos et al. 2024, with a
  continuous decision loss). Loss of day i at theta: the share of its calls
  delayed under c(theta), made non-increasing in theta by a running maximum
  from the top of the grid; bound B = 1. theta-hat = smallest grid theta with
  (sum_i L_i(theta) + 1)/(h + 1) <= 0.05 over the h calibration days (SCD's
  base load). This promises an expected share of delayed calls of at most 5%
  on a new day, not the day-level target; reported: day-level coverage, mean
  share delayed on test days, unit-hours. Needs the calibration days' delayed
  shares on the grid, which the first run did not store: they are recomputed
  with the unchanged simulator (`code/exp_amend4.py`).
- Check: CRC with the 0/1 loss "day misses the target" and B = 1 must select
  the same theta as SCD at every origin (it is the same rank rule); asserted.
- Reported like amendment 3 (primary configuration; target A only for
  CRC-share), plus the H1 criterion descriptively.
- Library versions of the titan environment are written to
  `facts/software_versions.json` and quoted in the paper from there.

Run on titan as amendment 3 (nice 19, memory guard); outputs in
`out/amend4/`, `out/amend4_results.json`. Code: `code/exp_amend4.py`,
`code/analyze_amend4.py`.
