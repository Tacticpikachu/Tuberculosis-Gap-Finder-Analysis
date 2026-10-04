"""A6: export analysis results as JSON for the static website (web/).

Reads:  data/clean/district_summary.csv, data/clean/johor_districts.geojson, data/clean/score_a.csv,
        data/clean/tb_district_year.csv, data/raw/health_facilities.geojson,
        data/raw/mys_ppp_2020_1km_Aggregated.tif, outputs/siting_results.csv,
        outputs/validation_results.csv
Saves:  outputs/web_data/site.json, outputs/web_data/districts.geojson, outputs/web_data/grid.json
        (copied into the site at build time; see vercel.json)
"""
import json
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RAW, OUT = ROOT / "data" / "clean", ROOT / "data" / "raw", ROOT / "outputs"
DEST = OUT / "web_data"
GRID_DEG = 0.05  # ~5.5 km cells for in-browser coverage


def clean(v):
    if isinstance(v, (float, np.floating)) and not np.isfinite(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(CLEAN / "district_summary.csv")
    a = pd.read_csv(CLEAN / "score_a.csv")
    tb = pd.read_csv(CLEAN / "tb_district_year.csv")
    sit = pd.read_csv(OUT / "siting_results.csv")
    val = pd.read_csv(OUT / "validation_results.csv")
    districts = gpd.read_file(CLEAN / "johor_districts.geojson")
    fac = gpd.read_file(RAW / "health_facilities.geojson")
    fac = gpd.sjoin(fac, districts[["code", "geometry"]], predicate="within", how="left")

    # population grid: aggregate WorldPop 1 km to GRID_DEG cells, expected TB by district share
    with rasterio.open(RAW / "mys_ppp_2020_1km_Aggregated.tif") as src:
        d = districts.to_crs(src.crs)
        cells = []
        for code, geom in zip(d["code"], d.geometry):
            arr, tr = mask(src, [geom], crop=True, filled=False)
            band = arr[0]
            ii, jj = np.nonzero(~np.ma.getmaskarray(band) & (band.filled(0) > 0))
            xs, ys = rasterio.transform.xy(tr, ii, jj)
            cells.append(pd.DataFrame({"code": code, "lon": xs, "lat": ys, "pop": band[ii, jj].astype(float)}))
    c = pd.concat(cells, ignore_index=True)
    c["gx"] = np.floor(c["lon"] / GRID_DEG).astype(int)
    c["gy"] = np.floor(c["lat"] / GRID_DEG).astype(int)
    g = c.groupby(["code", "gx", "gy"], as_index=False).agg(pop=("pop", "sum"))
    g["lon"], g["lat"] = (g["gx"] + 0.5) * GRID_DEG, (g["gy"] + 0.5) * GRID_DEG
    share = g["pop"] / g.groupby("code")["pop"].transform("sum")
    g["exp"] = share * g["code"].map(s.set_index("code")["expected_cases"])
    grid = {"deg": GRID_DEG, "cells": [[round(r.lat, 4), round(r.lon, 4), round(r.pop), round(r.exp, 3), r.code]
                                       for r in g.itertuples()]}
    (DEST / "grid.json").write_text(json.dumps(grid, separators=(",", ":")))

    trend = tb.pivot_table(index="code", columns="year", values="cases").reset_index()
    site = {
        "year": int(s["year"].iloc[0]),
        "districts": records(s),
        "trend": {"years": [int(y) for y in sorted(tb["year"].unique())],
                  "cases": {r["code"]: [clean(r[y]) for y in sorted(tb["year"].unique())] for _, r in trend.iterrows()},
                  "partial": {int(y): bool(p) for y, p in tb.drop_duplicates("year")[["year", "partial_year"]].values}},
        "rates": records(a[["code", "year", "raw_rate", "smoothed_rate"]]),
        "deaths": records(tb.dropna(subset=["deaths"]).groupby(["code", "district"], as_index=False)[["cases", "deaths"]].sum()),
        "siting": records(sit[["version", "n_units", "osm_id", "name", "amenity", "district", "lat", "lon",
                               "covered_expected_cases", "covered_expected_pct", "covered_pop"]]),
        "facilities": [[r.osm_id, r.name if isinstance(r.name, str) else "(unnamed)",
                        r.amenity if isinstance(r.amenity, str) else "facility",
                        r.code if isinstance(r.code, str) else None, round(r.lat, 5), round(r.lon, 5)]
                       for r in fac.itertuples()],
        "validation": records(val),
        "cover_km": 40, "speed_kmh": 40, "cover_min": 60,
    }
    (DEST / "site.json").write_text(json.dumps(site, separators=(",", ":"), allow_nan=False))
    shutil.copy(CLEAN / "johor_districts.geojson", DEST / "districts.geojson")
    for png in ("roc_curve.png", "confusion_matrix.png", "funnel.png"):
        if (OUT / png).exists():
            shutil.copy(OUT / png, DEST / png)

    for f in sorted(DEST.iterdir()):
        print(f"Saved {f.relative_to(ROOT)} ({f.stat().st_size / 1e3:.0f} KB)")
    print(f"  grid cells: {len(g)}, facilities: {len(fac)}, districts: {len(s)}, "
          f"grid expected total {g['exp'].sum():.0f} vs Score B {s['expected_cases'].sum():.0f}")


if __name__ == "__main__":
    main()
