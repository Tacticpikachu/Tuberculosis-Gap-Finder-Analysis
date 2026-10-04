"""A3 parts 3-4: build the Johor district lookup and run quick checks on the downloaded data.

Reads:  data/raw/population_district.parquet, data/raw/hh_income_district.parquet,
        data/raw/mys_adm2.geojson, data/raw/health_facilities.geojson
Saves:  data/clean/district_lookup.csv, data/clean/johor_districts.geojson
"""
import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

# Bulletin codes and names as given in the A3 task. Alternative names used for matching.
DISTRICTS = [
    ("JB", "Johor Bahru", []),
    ("KJ", "Kulai", ["Kulaijaya"]),
    ("MR", "Muar", []),
    ("LG", "Tangkak", ["Ledang"]),
    ("BP", "Batu Pahat", []),
    ("KG", "Kluang", []),
    ("ST", "Segamat", []),
    ("PN", "Pontian", []),
    ("KT", "Kota Tinggi", []),
    ("MG", "Mersing", []),
]


def norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def match(names, candidates):
    """Return the candidates whose normalised name equals any of `names`."""
    keys = {norm(n) for n in names}
    return sorted({c for c in candidates if norm(c) in keys})


def require(path):
    if not path.exists():
        sys.exit(f"STOP: {path.relative_to(ROOT)} is missing. Run analysis/a03_download.py first.")


def year_col(df):
    if "date" in df.columns:
        return pd.to_datetime(df["date"]).dt.year
    if "year" in df.columns:
        return df["year"]
    sys.exit(f"STOP: no date/year column in {list(df.columns)}")


def total_rows(df):
    """Keep only the all-sexes / all-ages / all-ethnicities rows, where those columns exist."""
    for col, total in [("sex", "both"), ("age", "overall"), ("ethnicity", "overall")]:
        if col in df.columns:
            if total not in set(df[col]):
                sys.exit(f"STOP: expected '{total}' in column {col}, found {sorted(set(df[col]))[:10]}")
            df = df[df[col] == total]
    return df


def main():
    for f in ["population_district.parquet", "hh_income_district.parquet",
              "mys_adm2.geojson", "health_facilities.geojson"]:
        require(RAW / f)
    CLEAN.mkdir(parents=True, exist_ok=True)

    # ---- quick checks: population ----
    pop = pd.read_parquet(RAW / "population_district.parquet")
    print("population_district.parquet columns:", list(pop.columns))
    pop["year"] = year_col(pop)
    print("  years:", sorted(pop["year"].unique().tolist()))
    pop_j = pop[pop["state"].str.lower() == "johor"]
    if pop_j.empty:
        sys.exit("STOP: no rows with state == Johor in population_district.parquet")
    latest = pop_j["year"].max()
    pop_latest = total_rows(pop_j[pop_j["year"] == latest])
    print(f"  Johor, {latest} (district, population):")
    print(pop_latest[["district", "population"]].to_string(index=False))

    # ---- quick checks: income ----
    inc = pd.read_parquet(RAW / "hh_income_district.parquet")
    print("\nhh_income_district.parquet columns:", list(inc.columns))
    print("  years:", sorted(year_col(inc).unique().tolist()))

    # ---- lookup ----
    adm2 = gpd.read_file(RAW / "mys_adm2.geojson")
    name_col = "shapeName" if "shapeName" in adm2.columns else None
    if name_col is None:
        sys.exit(f"STOP: no shapeName column in mys_adm2.geojson: {list(adm2.columns)}")
    dosm_names = pop_j["district"].unique()
    geo_names = adm2[name_col].unique()

    rows, problems = [], []
    for code, district, alts in DISTRICTS:
        names = [district] + alts
        d = match(names, dosm_names)
        g = match(names, geo_names)
        if len(d) != 1:
            problems.append(f"{code} {district}: DOSM matches {d or 'none'}")
        if len(g) != 1:
            problems.append(f"{code} {district}: geoBoundaries matches {g or 'none'}")
        rows.append({"code": code, "district": district,
                     "dosm_name": d[0] if len(d) == 1 else "",
                     "geo_name": g[0] if len(g) == 1 else ""})
    lookup = pd.DataFrame(rows)
    lookup.to_csv(CLEAN / "district_lookup.csv", index=False)
    print(f"\nSaved data/clean/district_lookup.csv: {len(lookup)} rows, columns {list(lookup.columns)}")
    print(lookup.to_string(index=False))
    if problems:
        print("\nUNMATCHED / AMBIGUOUS:")
        for p in problems:
            print("  " + p)
    else:
        print("All 10 districts matched in DOSM and geoBoundaries.")

    # ---- Johor boundaries ----
    matched = lookup[lookup["geo_name"] != ""]
    johor = adm2[adm2[name_col].isin(matched["geo_name"])].merge(
        matched, left_on=name_col, right_on="geo_name")
    johor = johor[["code", "district", "dosm_name", "geo_name", "geometry"]]
    johor.to_file(CLEAN / "johor_districts.geojson", driver="GeoJSON")
    print(f"\nSaved data/clean/johor_districts.geojson: {len(johor)} districts, CRS {johor.crs}")
    print(f"  mys_adm2.geojson: {len(adm2)} districts in Malaysia, "
          f"{len(johor)} of 10 Johor districts found -> {'OK' if len(johor) == 10 else 'CHECK'}")

    # ---- quick checks: health facilities ----
    hf = gpd.read_file(RAW / "health_facilities.geojson")
    print(f"\nhealth_facilities.geojson: {len(hf)} facilities, columns {list(hf.columns)}")
    print(hf["amenity"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
