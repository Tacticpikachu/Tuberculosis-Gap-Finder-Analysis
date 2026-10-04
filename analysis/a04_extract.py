"""A4: extract cumulative district TB notifications from the selected yearly bulletins.

Reads:  data/raw/johor_epid_W52_<year>.pdf, data/raw/bulletin_inventory.csv,
        data/clean/district_lookup.csv
Saves:  data/clean/tb_district_year.csv
        columns: code, district, year, cases, bulletin_week, partial_year, source_file, page,
                 state_total, sum_check

Uses the "CUMULATIVE" by-district table, row "TUBERCULOSIS (all forms)" (not deaths, not CXR).
Each row's 10 district values must add up to the bulletin's own state total.
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
OUT = CLEAN / "tb_district_year.csv"

# Column headers used in the bulletins -> codes in district_lookup.csv
# (2023+ bulletins print TG for Tangkak and SG for Segamat)
HEADER_ALIASES = {"TG": "LG", "SG": "ST"}
TOTAL_HEADERS = {"STATE", "JOHOR", "JOHORE"}
TB_ROW = re.compile(r"^\s*\d+\.?\s*TUBERCULOSIS\s*\(all forms\)\s*(.*)$", re.I)
NUM = re.compile(r"\d[\d,]*")


def find_table(pdf, codes):
    """Return (page_no, header_codes, values) for the cumulative TB row, or None."""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "CUMULATIVE" not in text.upper():
            continue
        lines = text.split("\n")
        header = None
        for line in lines:
            tokens = [HEADER_ALIASES.get(t, t) for t in line.split()]
            cols = [t for t in tokens if t in codes or t in TOTAL_HEADERS]
            if len([t for t in cols if t in codes]) == len(codes) and cols[-1] in TOTAL_HEADERS:
                header = cols
                continue
            m = TB_ROW.match(line)
            if header and m:
                values = [int(v.replace(",", "")) for v in NUM.findall(m.group(1))]
                if len(values) != len(header):
                    raise ValueError(f"page {i + 1}: {len(values)} numbers for {len(header)} "
                                     f"columns in line: {line!r}")
                return i + 1, header, values
    return None


def main():
    lookup = pd.read_csv(CLEAN / "district_lookup.csv")
    codes = set(lookup["code"])
    inv = pd.read_csv(RAW / "bulletin_inventory.csv")
    selected = inv[inv["selected"]].sort_values("year")
    if selected.empty:
        sys.exit("STOP: no selected bulletins in bulletin_inventory.csv")

    rows, problems = [], []
    for _, b in selected.iterrows():
        year, week = int(b["year"]), int(b["week"])
        path = RAW / f"johor_epid_W52_{year}.pdf"
        if not path.exists():
            problems.append(f"{year}: {path.name} missing")
            continue
        with pdfplumber.open(path) as pdf:
            found = find_table(pdf, codes)
        if not found:
            problems.append(f"{year}: cumulative TB row not found in {path.name}")
            continue
        page, header, values = found
        vals = dict(zip(header, values))
        total = next(vals[h] for h in header if h in TOTAL_HEADERS)
        dsum = sum(vals[c] for c in codes)
        check = "ok" if dsum == total else f"MISMATCH districts {dsum} vs state {total}"
        if check != "ok":
            problems.append(f"{year}: {check}")
        for c in lookup["code"]:
            rows.append({"code": c, "year": year, "cases": vals[c], "bulletin_week": week,
                         "partial_year": week < 52, "source_file": path.name,
                         "original_name": b["original_name"], "page": page,
                         "state_total": total, "sum_check": check})

    if not rows:
        sys.exit("STOP: nothing extracted\n  " + "\n  ".join(problems))
    df = pd.DataFrame(rows).merge(lookup[["code", "district"]], on="code")
    df = df[["code", "district", "year", "cases", "bulletin_week", "partial_year", "source_file",
             "original_name", "page", "state_total", "sum_check"]]
    df.to_csv(OUT, index=False)

    print(f"Saved {OUT.relative_to(ROOT)}: {len(df)} rows, columns {list(df.columns)}")
    wide = df.pivot(index="code", columns="year", values="cases").loc[lookup["code"]]
    print(wide.to_string())
    print("\nPer year: week, page, state total, check")
    print(df.drop_duplicates("year")[["year", "bulletin_week", "partial_year", "page",
                                      "state_total", "sum_check"]].to_string(index=False))
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
