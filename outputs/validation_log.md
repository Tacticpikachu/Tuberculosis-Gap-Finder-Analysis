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
