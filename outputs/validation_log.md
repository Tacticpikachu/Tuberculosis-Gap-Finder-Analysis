# Validation log
Run: 2026-10-04 18:00 MYT · script analysis/v_core.py

| Test | Result | Pass |
|---|---|---|
| V1 Data accuracy | skipped (team decision) | - |
| V2 Forecast accuracy | pairs [(2023, 2024)]; n=10; AUC 0.57 (CI 0.20-1.00); sens 0.00; skill -0.03; McNemar p=1.00; includes partial year(s) | FAIL |
| V3 Better than chance | 0 hits over 1 round(s); P = 1.000 | reported |
| V4 Death check | not run: data/raw/tb_state_year.csv missing | - |
| V5 Face validity | not completed (time) | - |
| V6 Cost model verification | not completed (time) | - |
| V7 Cost robustness | not completed (time) | - |
| V8 Siting robustness | not completed (time) | - |
| V9 Siting verification | not completed (time) | - |
| V10 Moran stability | not completed (time) | - |
