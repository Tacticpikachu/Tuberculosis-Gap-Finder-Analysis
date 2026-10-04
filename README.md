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
