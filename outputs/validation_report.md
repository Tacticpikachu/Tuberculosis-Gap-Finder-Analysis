# TB Gap Finder — Validation Report

Kow Kang, Rachel Lee Yi Wen · 4 October 2026 · pre-registration tag `prereg-v1`
Scripts: `analysis/a04_extract.py`, `analysis/a04b_population.py`, `analysis/a05_scores.py`, `analysis/v_core.py`

## 1. Aim
To test, against rules fixed before analysis (README, `prereg-v1`), whether an Empirical Bayes
(EB) ranking of Johor's 10 districts identifies next year's top-3 TB districts better than the
naive "same as last year" ranking (H1), and whether this beats chance.

## 2. Methods

### 2.1 Data
- **TB notifications.** Johor State Health Department weekly epidemiological bulletins. For each year,
  the bulletin with the highest epidemiological week was selected (2014 W31, 2015 W52, 2016 W41,
  2017 W31, 2023 W52, 2024 W23; 2018–2022 not available). From the *cumulative by-district* table,
  the row "Tuberculosis (all forms)" was transcribed for the 10 districts.
- **Quality control at extraction.** For every bulletin, the 10 district values were summed and
  compared with the bulletin's own printed state total. All six years matched exactly.
- **Population.** DOSM district estimates for 2020 onwards; for 2014–2017, the sum of WorldPop 1 km
  population rasters inside each district boundary (logged as a deviation, README).

### 2.2 Scores
- **Raw rate** = cases / population × 100 000.
- **Score A (EB-smoothed rate)**, per year: m = Σcases/Σpop; s² = Σn(r−m)²/Σn − m/n̄ (0 if
  negative); C = s²/(s² + m/n); smoothed = m + C(r − m). Small districts are pulled toward the
  Johor mean more strongly than large ones.
- **Top 3** = the three highest-ranked districts in a year (top quartile of 10); ties broken by the
  higher raw case count.

### 2.3 V2 — forecast accuracy (rolling hold-out)
Performed as a reviewer would by hand:
1. For each consecutive year pair (t, t+1) with data — (2014, 2015), (2015, 2016), (2016, 2017),
   (2023, 2024) — write down the **truth**: the top-3 districts by raw rate in year t+1.
2. Using only year t, write down two predictions: the **model** (top-3 by Score A) and the
   **baseline** (top-3 by raw rate, "same as last year").
3. Tally each district-pair into a 2×2 table (predicted top-3 yes/no × true top-3 yes/no),
   pooled over all pairs (n = 4 × 10 = 40).
4. From the table: sensitivity = TP/(TP+FN), specificity = TN/(TN+FP), PPV, NPV.
5. ROC AUC: probability that a randomly chosen true top-3 district had a higher year-t score than
   a randomly chosen other district.
6. MAE: mean absolute difference between the year-t rate and the year-t+1 raw rate;
   skill score = 1 − MAE_model / MAE_baseline (> 0 means the model is closer).
7. Uncertainty: 1 000 bootstrap resamples of the 40 district-pairs (seed 42); 95% percentile CIs.
8. McNemar's exact test on the pairs where the model and baseline disagree in correctness.
9. **Pass rule (fixed in advance):** lower AUC 95% CI > 0.5 **and** sensitivity ≥ 0.67 **and**
   skill score > 0.

### 2.4 V3 — better than chance
If the 3 picks were random each round, hits per round follow a hypergeometric distribution
(10 districts, 3 true hotspots, 3 picks). The distribution of total hits over all rounds is the
convolution of the per-round distributions; we report P(total hits ≥ observed).

### 2.5 V4 — death check
Funnel plot of TB deaths per notified case with 95% and 99.8% binomial control limits; units above
the 95% limit are flagged. Planned by state; state data could not be obtained, so it was run on
Johor's 10 districts using the bulletins' cumulative TB death row (2014-2017; logged deviation;
district death sums matched the printed state totals). By hand: for each district divide deaths by
notifications, plot against notifications, draw the Johor average with limits
p0 ± z·sqrt(p0(1−p0)/n) (z = 1.96 and 3.09), and flag points above the upper 95% line.

## 3. Results

| Test | Result | Pass rule | Verdict |
|---|---|---|---|
| V1 Data accuracy | Not performed (team decision); extraction cross-check: district sums = state totals in 6/6 bulletins | 0 mismatches | not completed |
| V2 Forecast accuracy | AUC 0.60 (95% CI 0.40–0.78); sensitivity 0.50 (0.20–0.78); specificity 0.79; PPV 0.50; NPV 0.79; skill −0.003 (−0.07 to 0.07); McNemar 0 vs 2 discordant, p = 0.50 | AUC CI lower > 0.5; sens ≥ 0.67; skill > 0 | **FAIL** |
| V3 Better than chance | 6 hits in 4 rounds; P(≥ 6) = 0.087 | report p | reported |
| V4 Death check (deviation: by district) | Johor districts, 2014-2017: pooled 0.016 deaths per notified case; above the 95% limit: **Kluang** (28/518 = 0.054) and **Tangkak** (19/210 = 0.090) | flag > 95% limit | 2 districts flagged |
| V5–V10 | not completed (time) | — | — |

Baseline for comparison: AUC 0.66, sensitivity 0.58 (7 of 12 hotspots found).
A first V2 run with only the (2023, 2024) pair (n = 10) also failed (0 of 3 hits); it is kept in
the log, as the plan requires all results to be reported.

## 4. Interpretation
- **H1 not supported.** Score A found 6 of 12 next-year hotspots (about 1.7× the 3.6 expected by chance,
  P = 0.087), but did not beat the "same as last year" baseline, and none of the three pass
  criteria were met.
- **Why.** (1) Only four year pairs, so the confidence intervals are wide; (2) four of the six
  bulletin years are part-year (to week 23–41), so year-to-year rankings are noisier and MAE
  compares periods of different length; (3) with 10 districts that all have ≥ 17 cases, EB
  smoothing changes rates very little (C = 0.6–0.97), so the model and baseline make almost the
  same picks; (4) 2014–2017 population is modelled (WorldPop), not census-based.

## 6. Desert validation (pre-registered addendum, commit 84c14cd)
Registered in README before computing. Desert points recomputed for each year 2014–2017 (that year's Score A, WHO
incidence for that year, Moran LH, same travel minutes), summed per district (0–12).

| Test | Result | Rule | Verdict |
|---|---|---|---|
| V11 Deaths vs deserts | Spearman ρ = 0.03 (one-sided permutation p = 0.48). Deaths per 100 cases: 2.8 in districts with ≥ 6 points (Kluang, Kulai, Segamat) vs 1.4 in the other 7 | ρ > 0 | Technically PASS, but ρ ≈ 0: no meaningful correlation |
| V12 Chest X-ray vs deserts (exploratory) | ρ = +0.23 (opposite of the expected negative direction; p = 0.75). The "TB – CXR" row (cluster/outbreak table, 2014–2015) is of uncertain meaning | none | reported only |

Interpretation: the strongest desert, **Kluang (9/12 points), also has a high death ratio (5.4 per 100)**, and the
desert group as a whole has about twice the death ratio of the rest. But the rank correlation across all ten districts is
essentially zero, because Segamat scores high with almost no deaths (1 of 310) and Tangkak scores low with the highest
death ratio (19 of 210). With 10 districts this test has low power; it neither confirms nor refutes the desert method.
The pass rule (ρ > 0) was lenient; the honest reading is "no clear relationship, with Kluang consistent".

## 7. Further pre-registered checks (addendum 2, commit b3a736a)

| Test | What it checks | Result | Verdict |
|---|---|---|---|
| V1b Data consistency | Week-to-week: cumulative(w) − cumulative(w−1) = current week(w), all bulletins (174 of 182 parsed, 1,560 district-week checks) | 88.7% exact match (2014 99%, 2015 97%, 2016 100%, 2017 100%, 2023 86%, 2024 51%). Mismatches are mostly reporting lags and corrections inside the bulletins themselves (e.g. a cumulative total that falls between weeks). Year-end totals used in the analysis all match printed state totals. | FAIL (rule ≥ 95%) |
| V9a Solver check | Greedy siting vs brute force over every 1- and 2-site combination (79,401 pairs) | Identical optimum for N = 1 and N = 2 | **PASS** |
| V9b Baselines | Expected TB within 60 min: greedy vs one hospital per district vs 1,000 random sets | N=3: **87.8% vs 76.7% vs 67.7%**; N=5: 97.2% vs 90.7% vs 78.4%; greedy beats ≥ 98.8% of random sets at every N | reported (greedy best at every N) |
| V9c Travel model | Straight-line minutes vs Malaria Atlas motorised friction travel time (least-cost path) | Spearman ρ = **0.87**; travel desert point changes for 2 districts (Tangkak, Pontian) | **PASS** (rule ρ ≥ 0.7) |
| V8 Siting robustness | Greedy 3-site plans at 30/60/90/120 min | 0 of 3 sites shared between 60 and 90 min (wider reach favours different, more central clinics); coverage 63.6% / 87.8% / 98.2% / 100% | FAIL (rule ≥ 2 shared) |
| V10 Moran stability | Quadrants 2014–2017 and 2023; queen vs rook vs k = 3 | Queen = rook 100%, queen vs k=3 90% (2023). **Kluang LH in 4 of 5 years**, Kulai 4 of 5; Pontian LH only in 2023. 23 of 150 labels have p < 0.05 | reported |

Plain words: the van optimiser is verified (it finds the true best 1–2 sites and clearly beats simple alternatives), the
quick travel estimate ranks districts like a proper road-friction model, and Kluang's "low next to high" label is stable
across years. The exact van sites depend on the travel-time limit chosen, and the weekly bulletins contain internal
reporting lags, especially in 2024.

## 5. What would change the result (legitimately)
1. Obtain the missing week-52 bulletins for 2018–2022: this adds five full-year pairs that use
   DOSM population directly.
2. Use full-year counts only for V2 (would be a logged deviation).
3. Complete V1 (blind re-entry of 20 values) and the state-level V4 (for H2) before the pitch.

Pass rules were not changed, and no values were adjusted to obtain a pass.
