# Handoff: the 3 validation slides — TB Gap Finder

**For the assistant receiving this file:** please turn this into a **PDF guide** that shows the team, slide by slide, how to
build these three validation slides: layout, exact wording, which chart goes where, what to say, and what not to claim.
All numbers below are final and come from the project's validation files; do not change or round them differently.
Attached charts (PNG, 2400 × 1300 px, white background):

| File | Use on |
|---|---|
| `slide1_planner_vs_alternatives.png` | Slide 1 (main visual) |
| `slide2_deaths_funnel.png` | Slide 2 (main visual) |
| `slide2_kluang_stability.png` | Slide 2 (supporting strip) |

---

## Context in one paragraph (for the guide's introduction)
TB Gap Finder is a hackathon project for Johor, Malaysia. It compares the TB each of Johor's 10 districts **reports**
(1,992 cases in 2023) with the TB it **should** have (≈ 3,984 using WHO's estimate of 97 per 100,000), finds
"diagnostic deserts" (places where TB is likely being missed and care is far away), and plans where scarce **portable
chest X-ray vans** should go. All tests were **pre-registered** (rules written and saved publicly on GitHub before the
results were computed) and every result is reported, pass or fail. The deck has only **three validation slides**, so they
must show (1) the product works, (2) the main finding is backed by independent real data, (3) the team is trustworthy.

## Design system (match the project website)
- **Colours:** forest green `#1c4a3a` (primary, "our tool"), amber `#c97f10` (comparison / attention), muted red `#b3382c`
  (warnings, Tangkak), warm grey `#a8a290` (other districts / random), ink `#15221c` (text), cream background `#f4f3ec`
  (optional slide background; charts have white backgrounds, so place them on white cards).
- **Fonts:** Figtree (headings and body), JetBrains Mono (small uppercase labels, e.g. "VALIDATION 1 OF 3").
- **Style:** one big headline per slide, one main visual, 2–4 short proof points, generous white space, no emoji, no clip art.
- **Labels:** if space allows, small tags "REAL DATA" (green), "ESTIMATED" (amber), "EXPLORATORY" (purple) as used on the site.

---

## Slide 1 — "Our van planner is proven optimal"
**Purpose:** prove the product itself works. This is the strongest validation.

**Eyebrow label:** VALIDATION 1 OF 3 · PLANNER
**Headline:** *3 vans reach 88% of Johor's expected TB, vs 77% at district hospitals.*

**Layout:** chart on the left (~60% width), three proof cards stacked on the right.

**Main visual:** `slide1_planner_vs_alternatives.png`
- Shows % of Johor's expected TB living within 60 minutes of the vans, for 1–5 vans.
- Green line = TB Gap Finder; amber = one van at the hospital nearest each district's population centre (largest districts
  first); grey = average of 1,000 random site choices. Dotted line marks 3 vans (88% / 77% / 68%).

**Proof cards (exact text):**
1. **Mathematically optimal** — We checked all **79,401** possible two-van combinations; our planner found the best one. (Same for one van.)
2. **Beats the alternatives** — Better than placing vans at district hospitals at every van count, and better than **≥ 98.8%** of 1,000 random plans.
3. **Realistic travel** — Our quick distance estimate ranks districts the same way as a proper road-and-terrain travel-time model (Malaria Atlas Project 2019): **ρ = 0.87**.

**Speaker notes (~35 s):**
"The planner is the heart of our product, so we tested it hardest. First, is it really choosing the best sites? We checked
every one of the 79,401 possible two-van combinations, and it found the optimum. Second, is it better than what a planner
would do by hand? Putting one van at each district hospital reaches 77% of expected TB; our plan reaches 88% with the
same three vans. Random placement reaches 68%. And the travel distances behind this agree with a full road-and-terrain
travel model."

**Footnote (small):** Coverage = within 60 minutes at 40 km/h straight-line; expected TB from WHO 2023 estimate shared by population. Tests V9a, V9b, V9c (pre-registered).

**Do not claim:** that 88% of TB cases *will be found* — it means 88% of the people expected to have TB *live within an hour* of a van.

---

## Slide 2 — "Kluang is flagged by three independent signals"
**Purpose:** show the main finding (a diagnostic desert) is backed by real data, not just our estimate.

**Eyebrow label:** VALIDATION 2 OF 3 · DIAGNOSTIC DESERT
**Headline:** *Kluang: our estimate, its history and its death records all point the same way.*

**Layout:** funnel chart on the left (~55%); on the right a 3-row checklist; the stability strip across the bottom.

**Main visual:** `slide2_deaths_funnel.png` (funnel plot)
- Each dot is a district: horizontal = TB cases 2014–2017, vertical = deaths per 100 TB cases.
- Grey line = Johor average **1.6**; dashed = 95% limit, dotted = 99.8% limit (wider for small districts because small
  numbers swing by chance).
- **Kluang (green) 5.4** and **Tangkak (red) 9.0** are far above both limits; Johor Bahru 0.9 labelled for scale.
- How to explain in one line: "Dots above the dashed line lose more TB patients than chance can explain."

**Checklist (exact text):**
| Signal | Evidence |
|---|---|
| ✓ Our estimate | **3 of 3** desert points: low TB beside high-TB neighbours, large hidden gap, far from care |
| ✓ Stable over time | "Low next to high" in **4 of 5 years** (2014, 2015, 2017, 2023) |
| ✓ Real death records | **5.4 deaths per 100 TB patients** vs 1.6 Johor average — about **3×** |

(Use simple check marks drawn as shapes or text "✓"; avoid emoji.)

**Supporting strip:** `slide2_kluang_stability.png` — five tiles 2014–2023, amber = LH ("low TB next to high-TB neighbours"), 2016 = HH.

**Bottom line on slide:** *Proposed proof: a screening pilot in Kluang — success = more new TB cases found per 1,000 people screened than in a comparison district.*

**Speaker notes (~40 s):**
"Our method flags Kluang as the strongest diagnostic desert: it reports less TB than its neighbours, far less than WHO's
estimate implies, and people live further from care. That could be our model talking, so we checked two independent
things. It's not a one-year fluke: Kluang shows the same pattern in four of five years. And the death records agree:
Kluang loses 5.4 TB patients per hundred, three times the Johor average. TB is curable, so extra deaths usually mean
late diagnosis. Tangkak is also a red flag on deaths, which our desert score alone didn't catch. The real proof is a
screening pilot, and we've defined its success criterion."

**Footnote (small):** Deaths 2014–2017 (bulletin TB-death rows); district-level check because state data were unavailable. Across all 10 districts the link between desert score and deaths is weak (Spearman ρ = 0.03), though desert districts as a group lose ≈ 2× more patients (2.8 vs 1.4 per 100). Tests V4, V10, V11.

**Do not claim:** that the death data *prove* every desert, or that the desert score predicts deaths across all districts.

---

## Slide 3 — "Built to be trusted"
**Purpose:** credibility — show rigour and own the weaknesses before judges ask.

**Eyebrow label:** VALIDATION 3 OF 3 · TRUST
**Headline:** *We set the rules first, and we report every result.*

**Layout:** three columns (cards), no chart needed. Optional: small GitHub tag badge "prereg-v1" in the corner.

**Column 1 — Data you can check**
- Every district number matches the **state total printed in the bulletin** (100%, all years used).
- Sources: Johor State Health Department bulletins, DOSM, WHO, WorldPop, OpenStreetMap.

**Column 2 — Rules fixed in advance**
- Hypotheses and pass marks saved publicly on GitHub **before** analysis (tag *prereg-v1*); later additions dated.
- Every test reported, including failures.

**Column 3 — What we're honest about**
- Predicting next year's hotspots: no better than "same as last year" (6 vs 7 of 12 correct).
- Best van sites shift if the travel-time limit changes (60 vs 90 min).
- Data gaps: no bulletins for 2018–2022; Score B uses population only until district risk data exist.

**Bottom strip — Next steps:** missing bulletins (more years to test) · district risk-factor data · **Kluang screening pilot**.

**Speaker notes (~30 s):**
"Everything here is checkable. Our numbers match the official state totals exactly. We wrote our tests and pass marks
down publicly before running them, and we report the ones we failed: forecasting next year's hotspots isn't our
strength, which is exactly why we focus on finding missed cases. The next steps are more data and a real screening pilot."

---

## Likely judge questions (put on a backup slide or the guide's last page)
- **"Your forecast test failed — why trust it?"** We set the bar before seeing data and report it. Ranking known cases is only as good as last year's list; our value is finding *missed* cases, where independent death data back us up on Kluang, and the planner is verified optimal.
- **"Is 88% real coverage?"** It is the share of *expected* TB living within an hour (straight-line) of the vans — a way to compare sites, not a promise of cases found.
- **"Why Kluang and not Tangkak?"** Kluang is flagged by all three signals; Tangkak is a strong death-rate warning that deserves investigation too.
- **"Data is from 2023 — it's 2026."** Latest complete year in our dataset; the pipeline updates in minutes when new bulletins are added.
- **"How do you know the optimiser is right?"** We brute-forced every 1- and 2-van combination and it matched.

## Glossary for the guide
- **Expected TB:** cases a district *should* have if WHO's national estimate (97 per 100,000) applied there.
- **Diagnostic desert:** a district with low reported TB beside high-TB neighbours, a large gap between expected and reported TB, and longer travel to care (3 of 3 = strong).
- **Funnel plot:** dots outside the funnel lines differ from the average by more than chance explains.
- **Pre-registration:** writing the tests and pass marks down publicly before seeing the results.
- **ρ (rho):** rank agreement from −1 to 1; 0.87 = strong agreement, 0.03 = none.
