# TB Gap Finder: project summary (handoff for slides & explanations)

Team: Kow Kang, Rachel Lee Yi Wen · Repo: github.com/Tacticpikachu/Tuberculosis-Gap-Finder-Analysis (branch `main`)
Pre-registration: README.md, git tag `prereg-v1` (2026-10-04 16:28 MYT). Deviations are logged in the README with times.

## 1. What the project does
Finds Johor districts likely to have **hidden (undiagnosed) tuberculosis**, explains why, and suggests where
scarce **portable X-ray units** should go. Outputs: analysis scripts, a Streamlit app (`app/app.py`) and a website
(`web/`, deployable on Vercel: Home, Explore = map + planner, Method = animated methodology).

## 2. Data sources
| Data | Source | Use | Label |
|---|---|---|---|
| TB cases & TB deaths by district | Johor State Health Department weekly epidemiological bulletins (latest week per year: 2014 W31, 2015 W52, 2016 W41, 2017 W31, 2023 W52, 2024 W23; 2018–2022 not available) | Reported TB, V4 deaths | Real |
| Population by district | DOSM (2020+); WorldPop 1 km rasters summed in district borders (2014–2017) | Rates | Real |
| Malaysia TB incidence | WHO TB burden estimates: 97 per 100,000 in 2023 (95% UI 79–117) | Score B | Estimate |
| Relative risks | Franco et al. 2024 Cochrane: diabetes RR 1.60, undernutrition RR 1.96; Imtiaz et al. 2017: alcohol use disorders RR 3.33 | Score B risk | Estimate |
| Clinics & hospitals | OpenStreetMap (399: 330 clinics, 47 hospitals, 22 doctors) | Travel, siting | Real |
| District borders | geoBoundaries (Kulai = "Kulaijaya", Tangkak = "Ledang") | Maps | Real |
| Travel friction (future use) | Malaria Atlas Project 2019 motorised friction surface | Not yet used | — |

Quality check: in every bulletin the 10 district TB values (and deaths) sum exactly to the printed state total.

## 3. Methods
- **Raw rate** = cases ÷ population × 100,000.
- **Score A (Empirical Bayes smoothing)**: m = Σcases/Σpop; s² = Σn(r−m)²/Σn − m/n̄ (0 if negative); C = s²/(s² + m/n);
  smoothed = m + C(r − m). Small districts are pulled more toward the Johor mean (e.g. Johor Bahru C = 0.97: 58.9→58.6;
  Mersing C = 0.61: 47.4→47.9). Analogy: a restaurant with 2 reviews vs 500 reviews.
- **Score B (expected TB)**: risk = Π(1 + p(RR − 1)); Johor total = WHO rate/100k × Johor pop (≈ 3,984 cases);
  expected = total × pop×risk / Σ(pop×risk). **Limitation:** no district-level prevalence found (NHMS is state-level),
  so currently risk = 1 everywhere and Score B = WHO rate shared by population (97/100k in every district).
- **Hidden gap** = expected rate − smoothed rate.
- **Travel (approximate)**: population-weighted straight-line distance from WorldPop cells to the nearest facility, at 40 km/h.
- **Local Moran's I (exploratory)**: queen neighbours, 999 permutations, seed 42 → HH / LL / HL / LH.
- **Desert points (0–3)**: +1 LH quadrant, +1 gap above median, +1 travel above median. 3 = strong, 2 = possible.
  Action: gap & travel high → portable X-ray unit; gap high, travel low → trusted-messenger campaign; else monitor.
- **Siting**: greedy, N = 1–5 units, coverage = within 60 min (40 km straight-line); expected-TB vs population-only versions.

## 4. Key results (2023)
- Reported TB in Johor: **1,992** cases; expected (WHO): **3,984**; possibly missed ≈ **1,992**.
- Highest smoothed rate: **Johor Bahru 58.6**/100k; then Kota Tinggi 53.4, Segamat 49.0. Johor mean 48.5.
- **Strong desert: Kluang (3/3)** → portable X-ray unit. Possible: Kulai, Pontian (2/3).
- Siting (expected-TB): 1 unit 58%, 2 units 80%, **3 units ≈ 3,500 cases (88%)**, 4 units 94%, 5 units 97% of expected TB within 60 min.

## 5. Validation (pass rules fixed before analysis)
| Test | What it asks | Result | Verdict |
|---|---|---|---|
| V1 data accuracy | Blind re-entry of 20 values | Skipped (team decision); extraction sums matched state totals 6/6 | not completed |
| **V2 forecast accuracy** | Does Score A predict next year's top-3 better than "same as last year"? 4 year-pairs, n = 40 | AUC 0.60 (CI 0.40–0.78), sensitivity 0.50 (6/12), skill −0.003; baseline 7/12 | **FAIL** (needs AUC CI low > 0.5, sens ≥ 0.67, skill > 0) |
| **V3 better than chance** | P(≥ 6 hits in 4 rounds) if picking 3 of 10 at random | **p = 0.087**: 2× random (6 vs 3), not significant | reported |
| **V4 death check** | Funnel plot of deaths per case, 95%/99.8% limits (run by **district**, 2014–2017; planned by state) | Johor 1.6 deaths/100 cases; flagged **Tangkak 9.0** and **Kluang 5.4** | 2 flagged; state-level H2 untested |
| V5–V10 | Face validity, cost model, siting robustness, Moran stability | not completed (time) | — |

Plain-language: V2 = "smarter than a lazy guess?" → not yet. V3 = "smarter than random?" → probably (p = 0.087).
V4 = "where do TB patients die more than normal?" → Kluang & Tangkak, a sign of **late diagnosis**; independent
real-data support for the Kluang desert finding.

## 6. Limitations
Bulletins 2018–2022 missing and 4 of 6 years part-year; Score B population-only until district risk data exist;
straight-line travel; Moran's I exploratory (10 districts); 2014–2017 population from WorldPop; V4 by district, not state.

## 7. Next steps
Obtain 2018–2022 week-52 bulletins (≈ 9 year pairs for V2); district risk-factor prevalence; road-network travel
with the MAP friction surface; pilot with the Johor State Health Department; clinical advisor review (V5).

## 8. Suggested pitch (10 slides)
1 Title · 2 Problem (reported ≈ 70 vs WHO 97 per 100k; scarce X-ray units) · 3 Solution · 4 How it works (5 engines) ·
5 Finding: gap & deserts (Kluang 3/3) · 6 Finding: V4 funnel (Tangkak, Kluang) · 7 Planner demo (3 units ≈ 88%) ·
8 Trust: pre-registered + V3 + V2 honesty · 9 Limitations & next steps · 10 Impact & ask.

Figures: outputs/funnel.png, outputs/roc_curve.png, outputs/confusion_matrix.png. Full methods: outputs/validation_report.md.
