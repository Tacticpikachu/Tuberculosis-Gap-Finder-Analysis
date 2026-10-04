# CLAUDE.md — TB Gap Finder

Rules for every session working in this repository.

## Project
TB Gap Finder is a Python research project that maps hidden tuberculosis (TB) in Johor
districts, with a Streamlit app.

## Layout
- `analysis/` — analysis scripts, numbered in run order (`a03_download.py`, `a04_extract.py`, ...).
- `data/raw/` — downloaded/source inputs (large rasters `*.tif`/`*.tiff` are git-ignored).
- `data/clean/` — cleaned, analysis-ready data.
- `outputs/` — results, figures and tables.
- `app/` — Streamlit app (`app.py`).

## Rules
1. Scripts live in `analysis/` and are numbered (`a03_download.py`, `a04_extract.py`, ...).
2. Read inputs only from `data/raw/` or `data/clean/`. Save outputs only to `data/clean/` or `outputs/`.
3. Never type data values into code. If data is missing, stop and tell the user.
4. Every script prints a short summary of what it saved (rows, columns, example values).
5. Use district names from `data/clean/district_lookup.csv` everywhere (created in A3).
6. `app.py` reads only files in `data/clean/` and `outputs/` and uses only streamlit, pandas, plotly.
   The deployed app installs `requirements.txt` (streamlit, pandas, plotly only); heavy analysis
   packages are pinned in `requirements-analysis.txt` and are for local analysis only.
7. Never edit the pass rules in `README.md`; changes go under "Deviations from plan" with a time.
8. Always activate `.venv` before running Python: `source .venv/bin/activate`.
