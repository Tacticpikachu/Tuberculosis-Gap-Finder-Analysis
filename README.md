# TB Gap Finder: pre-registered analysis plan
Team: Kow Kang, Rachel Lee Yi Wen · Clinical advisor: None (no advisor as of now)
Registered: 2026-10-04 16:28 MYT (UTC+08:00) · before any outcome data was analysed

## Research question
Which Johor districts are likely to carry hidden or rising tuberculosis (TB), why, and where should
limited portable X-ray screening units go?

## Study design
Retrospective ecological study (area-level, past data) with temporal validation (tested on years the
model has not seen), plus a model-based economic evaluation.
Unit: district-year (10 Johor districts, 2014-2023); state-year for the death check.

## Hypotheses
- H1: Score A (Empirical Bayes smoothed ranking) identifies next year's top-3 districts at least as
  well as the "same as last year" baseline.
- H2: At least one state lies above the 95% funnel limit for TB deaths per notified case.
- H3: MCLP (maximal covering location problem) siting weighted by expected TB covers more expected
  cases within 60 minutes than population-only siting.
- H4 (exploratory): TB rates are spatially clustered (Global Moran's I > 0).

## Data
- Johor State Health Department weekly epidemiological bulletins (week 52, 2014-2023): district TB counts
- State TB notifications and deaths: MOH (Ministry of Health) reports, Hansard parliamentary replies,
  and news quoting official figures, each tagged by reliability tier (1-3)
- OpenDOSM: population and household income by district
- WorldPop 2020 1 km population; Malaria Atlas Project 2019 friction surface; OpenStreetMap clinics
- WHO Global TB Report and published studies: relative risks, national estimate, cost parameters

## Primary outcome
TB notifications per 100,000 population, by district and year.

## Method summary
- Score A: Empirical Bayes smoothed rate per year.
- Score B: expected rate from living conditions, risk = product of (1 + p x (RR - 1)), sharing out
  WHO's national incidence by population x risk. It never uses TB counts.
- Hidden gap = Score B - Score A.
- Local Moran's I (queen neighbours, 999 permutations) on smoothed rates.
- Diagnostic desert points = [low-high Moran quadrant] + [gap above median] + [travel time above median];
  3 = strong, 2 = possible.
- Top 3 of 10 districts = top quartile; ties broken by higher raw case count.

## Pass rules (fixed before analysis)
| Test | Method | Pass rule |
|---|---|---|
| V1 Data accuracy | Person B retypes 20 randomly sampled bulletin values blind; script compares | Zero mismatches; any mismatch triggers a full recheck of that year |
| V2 Forecast accuracy | Rolling hold-out over every year pair; model vs "same as last year" | Lower end of AUC 95% CI > 0.5; sensitivity >= 0.67; skill score > 0 |
| V3 Better than chance | Hypergeometric probability of total top-3 hits | Report p-value |
| V4 Death check | Funnel plot, 95% and 99.8% limits | Flag only states above the 95% limit |
| V6 Cost model verification | Calibration to registry deaths; extreme-value tests | Within 2 percentage points of 10.2%; all extreme-value tests pass |
| V7 Cost robustness | One-way sensitivity, tornado chart | Cost-effectiveness verdict unchanged for most parameters; any that flip it are named |
| V8 Siting robustness | Rerun at 30, 90, 120 minutes | At N = 3, at least 2 of 3 sites shared between 60 and 90 minutes |
| V9 Siting verification | Brute-force solver check (N = 1-2); 10 routes vs Google Maps; vs largest hospitals and random placement | Solver matches brute force; other results reported |
| V10 Moran stability | Labels across all years; rook, queen, k = 3 neighbours; FDR correction; travel time of low-high districts | Reported; only labels stable across years shown as deserts |

All results are reported whether they pass or fail. AUC = area under the ROC curve; CI = confidence
interval; FDR = false discovery rate.

## Planned extra checks
- V2 run with and without COVID years (2020-2021).
- V4 run with and without Tier 3 (news-sourced) numbers.
- Spearman's rho between Score B and reported rates.
- Moran's I results are exploratory (10 districts limit statistical power).

## Deviations from plan
Any change is logged here with date, time, change and reason, before the affected results exist.

| Date and time | Change | Reason |
|---|---|---|
| 2026-10-04 17:38 MYT | Bulletin data kept as available: 2018-2022 missing; 2014 (to W31), 2016 (to W41) and 2017 (to W31) partial; 2015 and 2023 full. No values are filled in; analyses use only years present, and partial years are flagged. | Bulletins for these weeks/years were not obtained; team decision to proceed with the data as is (before any TB values were extracted). |
| 2026-10-04 18:04 MYT | District population for 2014-2017 taken from WorldPop 1 km yearly rasters (sum within district boundaries); DOSM used for 2020+. | DOSM district series starts in 2020, leaving only one V2 year pair. Added after a first V2 run on 2023-2024 (FAIL); pass rules unchanged and the earlier result is kept in the validation log. |
| 2026-10-04 18:11 MYT | V4 run at Johor district level (TB deaths / notifications from the bulletins' cumulative tables, 2014-2017) instead of state level. H2 (states) remains untested. | State-level TB deaths not reachable (data.gov.my and MOH sites blocked); district deaths are printed in the bulletins. |
| 2026-10-04 20:33 MYT | Added pre-registered desert-validation tests V11 (confirmatory) and V12 (exploratory), section below. Registered before either was computed; no V11/V12 values had been looked at. | V2 showed next-year forecasting is not the tool's strength; the tool's main claim (diagnostic deserts) needed its own test. |

## Pre-registered addendum: diagnostic-desert validation (2026-10-04 20:33 MYT, tag prereg-v2)
Fixed before analysis. Original pass rules above are unchanged.

**Desert points for year t** (t = 2014, 2015, 2016, 2017): computed exactly as in the main method, using that year's
Score A; expected rate = WHO Malaysia incidence for year t (`e_inc_100k`, WHO burden estimates file); gap = expected − Score A;
LH quadrant from Local Moran's I on year-t Score A (queen weights, 999 permutations, seed 42); travel = the same approximate
district travel minutes as the main analysis. Points = [LH] + [gap > median] + [travel > median].

| Test | Method | Pass rule |
|---|---|---|
| V11 Deaths vs deserts (confirmatory) | Per district: total desert points summed over 2014–2017 (0–12) vs TB death ratio = deaths ÷ notifications, 2014–2017 (bulletins). Spearman's ρ; one-sided permutation p (10,000 permutations, seed 42). Secondary: death ratio of districts with total points ≥ 6 vs < 6. | ρ > 0. Supportive if p < 0.05; otherwise reported as direction only. |
| V12 Chest X-ray vs deserts (exploratory) | Bulletin row "TB – CXR" in the "cluster / outbreak" table (2014–2015 only; meaning uncertain, likely X-rays linked to cluster investigations) per 100,000 vs total desert points 2014–2015. Spearman's ρ. | No pass rule; reported only (expected direction ρ < 0). |

All results are reported whether they support the desert method or not. With 10 districts, both tests have low power.

## Pre-registered addendum 2: running V8, V9, V10 and a data-consistency check (2026-10-04 20:38 MYT)
Registered before computing. Pass rules for V8, V9 and V10 are those in the original table; changes are listed here.

| Test | Method | Pass rule |
|---|---|---|
| V1b Data consistency (new) | For every pair of consecutive weekly bulletins in the same year (all 182 PDFs), per district: cumulative TB(week w) − cumulative TB(week w−1) compared with "current week" TB(week w). | ≥ 95% of district-week checks match exactly; all mismatches listed. |
| V8 Siting robustness | Greedy expected-TB siting rerun with 30, 90, 120-minute coverage (20, 60, 80 km at 40 km/h). | At N = 3, ≥ 2 of 3 sites shared between 60 and 90 minutes (original rule). |
| V9a Solver check | Brute force over all 1- and 2-site combinations of the 399 facilities (60 min). | Greedy matches brute force for N = 1–2 (original rule). |
| V9b Baselines | Greedy vs (i) one hospital per district, chosen as the hospital nearest each district's population-weighted centre, added in order of district population; (ii) 1,000 random facility sets (seed 42); N = 1–5. | Reported (original rule). |
| V9c Travel check (replaces "10 routes vs Google Maps": no Maps access) | Motorised travel time from the Malaria Atlas Project 2019 friction surface (least-cost path to nearest facility), population-weighted per district, vs the straight-line estimate. | Spearman ρ ≥ 0.7 between the two district rankings; number of districts whose travel desert point changes is reported. |
| V10 Moran stability | Local Moran quadrants for 2014–2017 and 2023 with queen, rook and k = 3 nearest-neighbour weights (999 permutations, seed 42). | Reported (original rule). |

