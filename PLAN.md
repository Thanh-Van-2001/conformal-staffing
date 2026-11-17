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
