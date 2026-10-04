# Validation log
Run: 2026-10-04 18:17 MYT · script analysis/v_core.py

| Test | Result | Pass |
|---|---|---|
| V1 Data accuracy | skipped (team decision) | - |
| V2 Forecast accuracy | pairs [(2014, 2015), (2015, 2016), (2016, 2017), (2023, 2024)]; n=40; AUC 0.60 (CI 0.40-0.78); sens 0.50; skill -0.00; McNemar p=0.50; includes partial year(s) | FAIL |
| V3 Better than chance | 6 hits over 4 round(s); P = 0.087 | reported |
| V4 Death check | by district (Johor bulletins 2014, 2015, 2016, 2017); pooled deaths/case 0.016; flagged above 95%: Kluang, Tangkak | reported |
| V5 Face validity | not completed (time) | - |
| V6 Cost model verification | not completed (time) | - |
| V7 Cost robustness | not completed (time) | - |
| V8 Siting robustness | not completed (time) | - |
| V9 Siting verification | not completed (time) | - |
| V10 Moran stability | not completed (time) | - |

## Desert validation (pre-registered addendum)

| Test | Result | Verdict |
|---|---|---|
| V11 Deaths vs deserts | Spearman ρ = 0.03 (one-sided p = 0.482); deaths per 100 cases: 2.8 in districts with ≥ 6 points vs 1.4 below | PASS (direction only (p ≥ 0.05)) |
| V12 Chest X-ray vs deserts (exploratory) | Spearman ρ = 0.23 (one-sided p = 0.748) | reported only |
| V1b Data consistency | 88.7% week-to-week match (lags/corrections in source) | FAIL |
| V8 Siting robustness | 0/3 sites shared 60 vs 90 min | FAIL |
| V9a Solver | greedy = brute force, N = 1–2 | PASS |
| V9b Baselines | N=3: 87.8% vs 76.7% hospitals vs 67.7% random | reported |
| V9c Travel model | ρ = 0.87 vs MAP friction | PASS |
| V10 Moran stability | Kluang LH 4/5 years; queen=rook 100% | reported |

