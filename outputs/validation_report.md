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
Funnel plot of TB deaths per notified case by state with 95% and 99.8% binomial control limits;
states above the 95% limit are flagged. Requires `data/raw/tb_state_year.csv`.

## 3. Results

| Test | Result | Pass rule | Verdict |
|---|---|---|---|
| V1 Data accuracy | Not performed (team decision); extraction cross-check: district sums = state totals in 6/6 bulletins | 0 mismatches | not completed |
| V2 Forecast accuracy | AUC 0.60 (95% CI 0.40–0.78); sensitivity 0.50 (0.20–0.78); specificity 0.79; PPV 0.50; NPV 0.79; skill −0.003 (−0.07 to 0.07); McNemar 0 vs 2 discordant, p = 0.50 | AUC CI lower > 0.5; sens ≥ 0.67; skill > 0 | **FAIL** |
| V3 Better than chance | 6 hits in 4 rounds; P(≥ 6) = 0.087 | report p | reported |
| V4 Death check | not run (state-level deaths not yet obtained) | flag > 95% limit | not completed |
| V5–V10 | not completed (time) | — | — |

Baseline for comparison: AUC 0.66, sensitivity 0.58 (7 of 12 hotspots found).
A first V2 run with only the (2023, 2024) pair (n = 10) also failed (0 of 3 hits); it is kept in
the log, as the plan requires all results to be reported.

## 4. Interpretation
- **H1 not supported.** Score A found 6 of 12 next-year hotspots (twice the 3 expected by chance,
  P = 0.087), but did not beat the "same as last year" baseline, and none of the three pass
  criteria were met.
- **Why.** (1) Only four year pairs, so the confidence intervals are wide; (2) four of the six
  bulletin years are part-year (to week 23–41), so year-to-year rankings are noisier and MAE
  compares periods of different length; (3) with 10 districts that all have ≥ 17 cases, EB
  smoothing changes rates very little (C = 0.6–0.97), so the model and baseline make almost the
  same picks; (4) 2014–2017 population is modelled (WorldPop), not census-based.

## 5. What would change the result (legitimately)
1. Obtain the missing week-52 bulletins for 2018–2022: this adds five full-year pairs that use
   DOSM population directly.
2. Use full-year counts only for V2 (would be a logged deviation).
3. Complete V1 (blind re-entry of 20 values) and V4 (state deaths by tier) before the pitch.

Pass rules were not changed, and no values were adjusted to obtain a pass.
