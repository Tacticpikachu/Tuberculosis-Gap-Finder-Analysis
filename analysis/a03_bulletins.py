"""A3 part 1: copy Johor bulletin PDFs, find year/week of each, select the last week per year.

Usage: python analysis/a03_bulletins.py <folder with downloaded bulletin PDFs>

Reads only the first page text (for year/week). Never reads TB case numbers.
Saves: data/raw/bulletins_all/*.pdf, data/raw/johor_epid_W52_<year>.pdf,
       data/raw/bulletin_inventory.csv
"""
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ALL_DIR = RAW / "bulletins_all"
INVENTORY = RAW / "bulletin_inventory.csv"
STUDY_YEARS = range(2014, 2024)  # README: district-year 2014-2023

YEAR_RE = re.compile(r"(?<!\d)(20[0-3]\d)(?!\d)")
FILENAME_WEEK_RES = [
    re.compile(r"(?i)(?<![a-z])W\s*[-_.]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)minggu\s*[-_.]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)(?<![a-z])ME\s*[-_.]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)week\s*[-_.]?\s*(\d{1,2})(?!\d)"),
]
TEXT_WEEK_RES = [
    re.compile(r"(?i)minggu\s+epidemiologi\s*(?:ke)?\s*[-:]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)minggu\s*(?:ke)?\s*[-:]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)epid(?:emiological)?\s+week\s*[-:]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?i)week\s*[-:]?\s*(\d{1,2})(?!\d)"),
    re.compile(r"(?<![A-Za-z])ME\s*[-:]?\s*(\d{1,2})(?!\d)"),
]


def valid_week(w):
    return w is not None and 1 <= w <= 53


def week_from(text, patterns):
    for pat in patterns:
        for m in pat.finditer(text):
            w = int(m.group(1))
            if valid_week(w):
                return w
    return None


def year_from(text):
    years = sorted(set(int(y) for y in YEAR_RE.findall(text)))
    if len(years) == 1:
        return years[0], ""
    if len(years) > 1:
        return None, f"several years found: {years}"
    return None, ""


def inspect_pdf(path):
    notes = []
    year, ynote = year_from(path.stem)
    if ynote:
        notes.append(f"file name: {ynote}")
    week = week_from(path.stem, FILENAME_WEEK_RES)
    sources = {"year": "filename" if year else None, "week": "filename" if week else None}

    pages = None
    try:
        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            if year is None or week is None:
                text = (pdf.pages[0].extract_text() or "") if pages else ""
                if not text.strip():
                    notes.append("first page has no extractable text (scanned?)")
                if year is None:
                    year, ynote = year_from(text)
                    if year:
                        sources["year"] = "page text"
                    elif ynote:
                        notes.append(f"page text: {ynote}")
                if week is None:
                    week = week_from(text, TEXT_WEEK_RES)
                    if week:
                        sources["week"] = "page text"
    except Exception as exc:
        notes.append(f"could not open PDF: {type(exc).__name__}: {exc}")

    if year is None:
        notes.append("FLAG: year not determined")
    if week is None:
        notes.append("FLAG: week not determined")
    used = {s for s in sources.values() if s}
    source = "page text" if "page text" in used else ("filename" if used else "")
    if used == {"filename", "page text"}:
        notes.append(f"year from {sources['year']}, week from {sources['week']}")
    return {
        "original_name": path.name,
        "year": year,
        "week": week,
        "pages": pages,
        "source": source,
        "notes": "; ".join(notes),
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python analysis/a03_bulletins.py <folder with bulletin PDFs>")
    src = Path(sys.argv[1]).expanduser()
    pdfs = sorted(p for p in src.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    if not pdfs:
        sys.exit(f"STOP: no PDF files found in {src}")

    ALL_DIR.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in pdfs]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        sys.exit(f"STOP: same file name in several subfolders, cannot keep original names: {dupes}")
    for p in pdfs:
        shutil.copy2(p, ALL_DIR / p.name)
    print(f"Copied {len(pdfs)} PDFs to {ALL_DIR.relative_to(ROOT)}/")

    inv = pd.DataFrame([inspect_pdf(ALL_DIR / p.name) for p in pdfs])
    inv["year"] = inv["year"].astype("Int64")
    inv["week"] = inv["week"].astype("Int64")
    inv["selected"] = False

    known = inv.dropna(subset=["year", "week"])
    for year, grp in known.groupby("year"):
        top_week = grp["week"].max()
        top = grp[grp["week"] == top_week].sort_values("pages", ascending=False)
        idx = top.index[0]
        inv.loc[idx, "selected"] = True
        if len(top) > 1:
            inv.loc[top.index, "notes"] = inv.loc[top.index, "notes"].str.cat(
                [f"{len(top)} files for week {top_week}; kept the one with most pages"] * len(top),
                sep="; ").str.lstrip("; ")
        dest = RAW / f"johor_epid_W52_{year}.pdf"
        shutil.copy2(ALL_DIR / inv.loc[idx, "original_name"], dest)

    inv.to_csv(INVENTORY, index=False)
    print(f"Saved {INVENTORY.relative_to(ROOT)}: {len(inv)} rows, columns {list(inv.columns)}")
    print(inv.head(5).to_string(index=False))

    flagged = inv[inv["notes"].str.contains("FLAG", na=False)]
    if len(flagged):
        print(f"\nFLAGGED ({len(flagged)} files, year or week unknown):")
        print(flagged[["original_name", "year", "week", "notes"]].to_string(index=False))

    years = sorted(set(STUDY_YEARS) | set(known["year"].dropna().astype(int)))
    rows = []
    for y in years:
        n = int((inv["year"] == y).sum())
        sel = inv[(inv["year"] == y) & inv["selected"]]
        wk = int(sel["week"].iloc[0]) if len(sel) else None
        status = "MISSING" if wk is None else ("yes" if wk >= 52 else "PARTIAL")
        rows.append({"year": y, "bulletins_found": n, "week_selected": wk if wk else "-",
                     "full_year": status,
                     "saved_as": f"johor_epid_W52_{y}.pdf" if wk else "-"})
    print("\nYear summary:")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
