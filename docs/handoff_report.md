# TB Gap Finder — Full Handoff Report

**Team:** Kow Kang, Rachel Lee Yi Wen · **Clinical advisor:** none yet
**Repository:** github.com/Tacticpikachu/Tuberculosis-Gap-Finder-Analysis (branch `main`)
**Pre-registration:** `README.md`, git tag `prereg-v1` (registered 2026-10-04 16:28 MYT). All later changes are logged under "Deviations from plan" with times.
**Purpose of this file:** give a new assistant or teammate everything needed to build slides, explain the project to beginners, and answer judges' questions — without access to the code or the original conversation.

---

## 1. The project in one paragraph
Tuberculosis (TB) is a curable lung infection that spreads through the air. In 2023 Johor recorded **1,992** TB cases, but the WHO estimate for Malaysia (97 per 100,000) implies about **3,984** for Johor's 4.1 million people — so roughly **2,000 people may have TB without being diagnosed**. TB Gap Finder compares the TB each of Johor's 10 districts *reports* with the TB it *should* have, measures how far people live from care, flags "diagnostic deserts", and plans where scarce **portable X-ray vans** should go. Everything is pre-registered and every result is reported, pass or fail.

---

## 2. Data sources

| Data | Source | Used for | Label | Example |
|---|---|---|---|---|
| TB cases per district | Johor State Health Department weekly epidemiological bulletins (182 PDFs; latest week per year: 2014 W31, 2015 W52, 2016 W41, 2017 W31, 2023 W52, 2024 W23; **2018–2022 not available**) | Reported TB | Real | Kluang 2023: 136 cases |
| TB deaths per district | Same bulletins, cumulative "Tuberculosis death" row (2014–2017 only) | V4 death check | Real | Kluang 2014–17: 28 deaths / 518 cases |
| Population | DOSM district population (2020+, published in thousands); WorldPop 1 km rasters summed inside district borders (2014–2017) | Rates | Real | Kluang 2023: 328,700 |
| True TB level | WHO TB burden estimates: Malaysia 2023 **97 per 100,000** (uncertainty 79–117) | Score B | Estimate | Johor ≈ 3,984 expected |
| Relative risks | Franco et al. 2024 Cochrane: diabetes RR **1.60**, undernutrition RR **1.96**; Imtiaz et al. 2017: alcohol use disorders RR **3.33** | Score B risk (ready, not yet used) | Estimate | — |
| Clinics & hospitals | OpenStreetMap (Overpass Turbo export): **399** = 330 clinics, 47 hospitals, 22 doctors | Travel, van sites | Real | — |
| District borders | geoBoundaries (Kulai = "Kulaijaya", Tangkak = "Ledang") | Maps, neighbours | Real | — |
| Travel friction | Malaria Atlas Project 2019 motorised friction surface (Johor) | Future road-time travel (not used yet) | — | — |

**Built-in quality check:** for every bulletin used, the 10 district TB values (and death values) add up exactly to the state total printed in that bulletin.

---

## 3. Back-end pipeline (scripts in `analysis/`, run in order)

| Step | Script | What it does | Main output |
|---|---|---|---|
| 1 | `a03_bulletins.py` | Copies the 182 PDFs, reads year/week from file names (or page 1), keeps the highest-week bulletin per year | `bulletin_inventory.csv`, `johor_epid_W52_<year>.pdf` |
| 2 | `a03_download.py` | Downloads DOSM population & income, geoBoundaries, WorldPop (skips existing files) | raw data files |
| 3 | `a03_facilities.py` | Converts the OpenStreetMap export to name/type/lat/lon/id | `health_facilities.geojson` |
| 4 | `a03_lookup.py` | Matches bulletin codes ↔ DOSM ↔ geoBoundaries names; saves the 10 district shapes | `district_lookup.csv`, `johor_districts.geojson` |
| 5 | `a03_clip_friction.py` | Gets the MAP friction map for Johor | `map_friction_motorised_2019_johor.tif` |
| 6 | `a04_extract.py` | Reads the cumulative "Tuberculosis (all forms)" and "Tuberculosis death" rows; checks district sums = state total | `tb_district_year.csv` |
| 7 | `a04b_population.py` | Population per district-year (DOSM 2020+, WorldPop 2014–2017) | `population_district_year.csv` |
| 8 | `a05_scores.py` | Score A, Score B, gap, travel, Moran's I, desert points, actions, van siting | `score_a.csv`, `district_summary.csv`, `siting_results.csv` |
| 9 | `v_core.py` | Validation V2, V3, V4 + charts | `validation_results.csv`, `validation_log.md`, `roc_curve.png`, `confusion_matrix.png`, `funnel.png` |
| 10 | `a06_web_export.py` | Small JSON files + 5 km grid for the website | `outputs/web_data/*` |

Project rules: no data values typed into code (if data is missing, the script stops); every script prints what it saved.

---

## 4. Methodology step by step (with Kluang as the worked example)

### Step 1 — Rate (fair comparison)
**rate = cases ÷ population × 100,000**
Kluang 2023: 136 ÷ 328,700 × 100,000 = **41.4 per 100,000**.

### Step 2 — Score A: reported TB, steadied (Empirical Bayes smoothing, per year)
Small districts' rates jump around by chance, so each rate is pulled toward the Johor average; small districts are pulled more.

| Symbol | Meaning | Formula |
|---|---|---|
| nᵢ | population | |
| rᵢ | raw rate | casesᵢ / nᵢ |
| m | Johor average | Σcases / Σpopulation |
| s² | true between-district variation | Σnᵢ(rᵢ−m)² / Σnᵢ − m/n̄ (0 if negative) |
| Cᵢ | trust in district's own rate (0–1) | s² / (s² + m/nᵢ) |
| **Score A** | smoothed rate | m + Cᵢ(rᵢ − m) |

2023: m = 48.5. Johor Bahru (1.76 M people) C = 0.97: 58.9 → 58.6. Mersing (80,100) C = 0.61: 47.4 → 47.9. **Kluang: 41.4 → 42.3.**
Analogy: a restaurant with 2 five-star reviews is not really better than one with 500 reviews averaging 4.6.
Ranking: sort by Score A; ties broken by higher raw cases; top 3 = hotspots.

### Step 3 — Score B: expected TB
1. Johor total = WHO rate ÷ 100,000 × Johor population = 97 ÷ 100,000 × 4,107,200 = **3,984 cases**.
2. Risk per district: **riskᵢ = Π (1 + pᵢₖ × (RRₖ − 1))** over risk factors k (p = share of district with the factor).
3. Share: **Eᵢ = Total × popᵢ·riskᵢ / Σ popⱼ·riskⱼ**; expected rate = Eᵢ / popᵢ × 100,000.

**Current limitation:** no district-level prevalence data exist (NHMS reports Johor as a whole), so risk = 1 for every district and the expected rate is **97 in every district**.
Kluang: share 328,700 / 4,107,200 = 8.0% → 319 expected cases → 97 per 100,000.
Illustration only (not real data): if 25% of Kluang adults had diabetes, its diabetes factor = 1 + 0.25 × 0.60 = 1.15, giving it a larger slice.

### Step 4 — Hidden gap
**Gap = expected rate − Score A.** Kluang: 97 − 42.3 = **54.7 per 100,000 ≈ 180 people** possibly undiagnosed.

### Step 5 — Accessibility (approximate travel)
For every 1 km WorldPop square: straight-line (haversine) distance to the nearest of 399 facilities,
**d = 2R·asin√(sin²(Δlat/2) + cos lat₁·cos lat₂·sin²(Δlon/2)), R = 6,371 km**;
district value = population-weighted average; minutes = km ÷ 40 × 60.
Kluang **7.2 min** (Johor Bahru 2.1, Kota Tinggi 11.0, median 4.8). Straight-line, so real trips are longer — use for comparison.
**Purpose:** tells *why* cases are missing (far from care vs not coming), feeds one desert point, and defines van coverage.

### Step 6 — Neighbour pattern (Local Moran's I, exploratory)
Queen neighbours (shared border or corner), row-standardised; zᵢ = standardised Score A; Iᵢ ∝ zᵢ × average neighbour z; 999 random permutations (seed 42) for p.
Quadrants: HH, LL, HL, **LH = low next to high** (suspicious: low may mean less testing). Kluang: **LH, p = 0.42** (a hint, not proof).

### Step 7 — Desert points and action
**Points = [LH] + [gap > median] + [travel > median]** (0–3; 3 strong, 2 possible).
Kluang: LH ✅ + gap 54.7 > 54.5 ✅ (borderline) + travel 7.2 > 4.8 ✅ = **3/3 strong desert**.
Action: gap high & travel high → 🚐 portable X-ray van (access gap); gap high & travel low → 📣 trusted-messenger campaign (awareness gap); else 👀 monitor.
Kluang → 🚐 van. Kulai (gap 54.9, travel 4.0) → 📣 campaign.

### Step 8 — Van siting (greedy)
Demand: each 1 km square gets expected TB = district Eᵢ × square's share of district population. A van at a clinic covers squares within **40 km (60 min at 40 km/h)**. Repeatedly pick the clinic adding the most *uncovered* expected TB, N = 1–5. Population-only version maximises people instead.

| Vans | Added site | Expected TB covered |
|---|---|---|
| 1 | Top Vision (Kulai) | 58% |
| 2 | Klinik Desa (Batu Pahat) | 80% |
| 3 | Klinik Desa Sungai Sayong (Kluang) | **88% (≈ 3,500 of 3,984)** |
| 4 | — | 94% |
| 5 | — | 97% |

Diminishing returns help decide whether extra vans are worth funding.

---

## 5. Key results (2023)
- Reported 1,992; expected 3,984; possibly missed ≈ 1,992.
- Highest Score A: Johor Bahru 58.6, Kota Tinggi 53.4, Segamat 49.0 (Johor mean 48.5).
- Strong desert: **Kluang** (3/3). Possible: Kulai, Pontian (2/3).
- 3 vans reach ≈ 88% of expected TB within 60 minutes (straight-line).

---

## 6. Validation (rules fixed before analysis)

### V1 — Data accuracy: skipped (team decision). Extraction cross-check passed (district sums = state totals, 6/6 years).

### V2 — Forecast accuracy: **FAIL**
**Question:** does Score A predict next year's top-3 districts better than "same as last year"?
**Procedure:** for each year pair (t, t+1): model = top 3 by Score A in year t; baseline = top 3 by raw rate in year t; truth = top 3 by raw rate in t+1 (only year t data may be used). Pool all rounds.

| Round | Model | Baseline | Truth | Model hits | Baseline hits |
|---|---|---|---|---|---|
| 2014→15 | KT, PN, MR | KT, PN, MG | MG, KT, JB | 1 | 2 |
| 2015→16 | MG, KT, JB | MG, KT, JB | KT, MG, JB | 3 | 3 |
| 2016→17 | KT, MG, JB | KT, MG, JB | MG, KT, PN | 2 | 2 |
| 2023→24 | JB, KT, ST | JB, KT, ST | MG, KG, PN | 0 | 0 |
| Total | | | | **6/12** | **7/12** |

Worked example 2014→2015: 2014 Johor mean 35.5; Mersing (67,900 people) raw 39.7 was pulled to 36.9 (C = 0.32), dropping it out of the model's top 3 — then Mersing had the highest rate in 2015 (123.5). Lesson: smoothing guards against flukes but can hide a real rise in a small district. (2014 is 31 weeks vs 52 in 2015, so compare rankings within a year, not numbers across years.)

Confusion matrix (40 district-rounds): TP 6, FP 6, FN 6, TN 22 → sensitivity 0.50, specificity 0.79, PPV 0.50, NPV 0.79.
AUC (chance a true hotspot outranks a non-hotspot): model **0.60**, baseline 0.66 (0.5 = coin flip).
MAE: model 24.17 vs baseline 24.10 → skill = 1 − 24.17/24.10 = **−0.003**.
Bootstrap (1,000 resamples, seed 42): AUC 95% CI **0.40–0.78**; sensitivity 0.20–0.78; skill −0.07 to 0.07.
McNemar: discordant 0 vs 2, p = 0.50.
Pass rules: AUC CI lower > 0.5 ✗, sensitivity ≥ 0.67 ✗, skill > 0 ✗ → **FAIL**.
Why: only 4 rounds; 4 of 6 years part-year; Johor districts large enough that smoothing barely changes the order.
History: first run used only 2023→24 (n = 10, 0 hits, FAIL); population for 2014–2017 was then added (logged deviation) and the test re-run; pass rules unchanged.

### V3 — Better than chance: p = 0.087 (reported)
Random 3-of-10 picks with 3 true hotspots: P(k hits) = C(3,k)·C(7,3−k)/C(10,3) → 0.292, 0.525, 0.175, 0.008 (average 0.9 per round). Convolved over 4 rounds: average **3.6** hits; **P(≥ 6) = 0.087** (≈ 1 in 11).
Plain words: 6 hits vs 3.6 expected by chance — about **1.7× better than random**, but not statistically significant (needs p < 0.05).

### V4 — Death check: Kluang and Tangkak flagged
Per district (2014–2017): ratio = deaths ÷ cases. Johor average p₀ = 0.016 (1.6 per 100). Funnel limits for n cases: p₀ ± z·√(p₀(1−p₀)/n), z = 1.96 (95%), 3.09 (99.8%). Flag above the upper 95% line.
**Tangkak 19/210 = 9.0 per 100; Kluang 28/518 = 5.4 per 100** — both flagged.
Why it matters: TB is curable, so more deaths usually means late diagnosis. It is independent real-data support: **Kluang is flagged by both the estimate (3/3 desert) and the death records.** Deviation: planned by state (H2), run by district because state death data were blocked; H2 untested.

### V11 — Deaths vs desert score (pre-registered addendum, confirmatory)
Desert points recomputed for 2014–2017 and summed (0–12) per district, compared with deaths per case 2014–2017.
**Spearman ρ = 0.03, p = 0.48** → technically meets the (lenient) rule ρ > 0, but there is **no meaningful correlation**.
Districts with ≥ 6 points (Kluang, Kulai, Segamat) have **2.8 deaths per 100 cases vs 1.4** for the rest (about double).
Kluang is consistent (9/12 points, 5.4 per 100); Segamat (8 points, 1 death) and Tangkak (3 points, 9.0 per 100) break the pattern.
Plain words: "The strongest desert also loses many patients, and deserts as a group lose about twice as many, but across all ten districts the link is not clear."

### V12 — Chest X-ray vs desert score (exploratory)
"TB – CXR" row (cluster/outbreak table, 2014–2015 only; meaning uncertain). ρ = +0.23 — opposite of the expected direction. Reported only.

### V5–V10: not completed (time).

---

## 7. Website (Vercel) and app — how users use them
**Home:** headline, live van slider (1–5 vans → expected TB covered), stats strip, how-it-works engine cards, findings.
**Explore → Map:** choose view (Reported rate · Hidden gap · Diagnostic desert · Clustering), hover, click a district → panel with reported rate, cases, expected rate, gap, travel, clustering, desert points, suggested action.
**Explore → Planner:** *Recommended* (slider + target expected TB or population; numbered sites, 60-min circles, coverage table) or *Choose my own* (search/tick clinics or click map dots; live coverage and comparison with the recommended plan).
**Method:** 8-step animated timeline with formulas, validation scorecard and charts, sources, limitations.
Labels: 🟢 REAL · 🟡 ESTIMATED · 🟣 EXPLORATORY. Light/dark toggle; mobile-friendly.
Streamlit app (`app/app.py`): same content in a simpler dashboard.

---

## 8. Keeping it current (why 2023, and 2026)
The map shows **2023** because it is the latest complete year in the provided bulletins (2024 only to week 23; 2025–2026 not provided). TB patterns change slowly, so 2023 is a reasonable guide to *where to look first*, but rankings can shift (2023 vs early-2024 top 3 did not overlap). Adding the 2024/2025 week-52 bulletins and rerunning the scripts updates the map, van plan and validation within minutes; a scheduled GitHub Action could automate weekly updates. Historical years are needed to test the method (V2/V3), supply deaths (V4), and show which hotspots are stable.

---

## 9. Limitations and how to improve
| Limitation | Fix |
|---|---|
| Bulletins 2018–2022 missing; 2014, 2016, 2017, 2024 partial | Obtain week-52 bulletins (≈ 10 V2 rounds instead of 4) |
| Score B equal for all districts | District risk-factor prevalence (diabetes, smoking, poverty) |
| Straight-line travel | Road travel time with the MAP friction surface |
| Moran's I weak with 10 districts | Treat as a hint; check stability across years (V10) |
| V4 by district, not state | State TB deaths (MOH reports, Hansard) for H2 |
| Kluang's gap point borderline (54.7 vs 54.5) | More data |
Possible V2 improvements (must be pre-registered as a new plan, e.g. `prereg-v2`, before testing): more and full years; average 2–3 past years; matched-week comparisons; neighbour-based smoothing; trend term; risk-factor predictors.

---

## 10. Pitch plan (10 slides, ~5 min)
1. **Title** — "TB Gap Finder: finding hidden TB in Johor"; ≈ 2,000 possibly undiagnosed.
2. **Problem** — 1,992 reported vs 3,984 expected; vans are scarce.
3. **Solution** — compare reported vs expected, find deserts, plan vans (home page screenshot).
4. **How it works** — 5 engines: bulletins → steady rates → expected TB → distance → siting.
5. **Finding 1** — desert map; Kluang 3/3 with the Kluang worked numbers.
6. **Finding 2 (V4)** — funnel chart; Tangkak 9.0, Kluang 5.4 vs 1.6 per 100.
7. **Planner demo** — 3 vans ≈ 88%; "Choose my own" comparison.
8. **Trust** — pre-registered; V3 ≈ 1.7× random (p = 0.087); V2 honest FAIL and why.
9. **Limits & next steps** — missing years, risk data, road times, JKN pilot.
10. **Impact & ask** — data access, pilot partner, clinical advisor; site link/QR.
Which validation to show: V4 as headline, V3 briefly, V2 as honesty plus pre-registration; V1/V5–V10 only in Q&A.

---

## 11. Likely questions and answers
- **"Your prediction test failed — why trust it?"** We set the pass mark before seeing data and report it honestly. Ranking known cases is no better than "same as last year", but the tool's value is finding hidden cases — and real death records independently agree on Kluang.
- **"Is 2023 relevant in 2026?"** Latest complete year we had; patterns change slowly; the pipeline updates in minutes with new bulletins.
- **"Are 2,000 missed cases certain?"** No — it is based on WHO's estimate (range 79–117 per 100,000); it shows scale, not an exact count.
- **"Why are travel times so short?"** Straight-line to the nearest of 399 facilities, including small clinics; used to compare districts, not as real journey times.
- **"Why place vans at clinics?"** Existing clinics have staff, power and access, so the plan is realistic.
- **"What is 'desert points'?"** One point each for low-next-to-high neighbours, gap above median, travel above median; 3 = strong desert.

---

## 12. Files to give the next assistant
`docs/handoff_report.md` (this file), `README.md` (plan and pass rules), `outputs/validation_report.md`, `outputs/funnel.png`, `outputs/roc_curve.png`, `outputs/confusion_matrix.png`, plus website screenshots (home, map, planner) for slides.
