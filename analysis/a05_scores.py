"""A5: Score A, Score B, hidden gap, approximate travel, local Moran's I, desert points, greedy siting.

Reads
  data/clean/tb_district_year.csv      columns: code, year, cases   (from bulletin extraction)
  data/raw/parameters.csv              columns: parameter, value [, source, ...]
                                         - who_incidence_per_100k     WHO national TB incidence
                                         - rr_<factor>                relative risk for each factor
  data/raw/risk_factors_district.csv   columns: code, factor, p      (p = prevalence, 0-1)
  data/raw/population_district.parquet, data/raw/mys_ppp_2020_1km_Aggregated.tif,
  data/raw/health_facilities.geojson, data/clean/district_lookup.csv,
  data/clean/johor_districts.geojson, data/raw/bulletin_inventory.csv
Saves
  data/clean/score_a.csv, data/clean/district_summary.csv, outputs/siting_results.csv

Travel time and siting use straight-line distance at 40 km/h: APPROXIMATE.
Local Moran's I on 10 districts is EXPLORATORY.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, OUT = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "outputs"

TB = CLEAN / "tb_district_year.csv"
PARAMS = RAW / "parameters.csv"
RISK = RAW / "risk_factors_district.csv"
POP = RAW / "population_district.parquet"
WORLDPOP = RAW / "mys_ppp_2020_1km_Aggregated.tif"
FACILITIES = RAW / "health_facilities.geojson"
LOOKUP = CLEAN / "district_lookup.csv"
DISTRICTS = CLEAN / "johor_districts.geojson"
INVENTORY = RAW / "bulletin_inventory.csv"

DOSM_POP_UNIT = 1000      # DOSM publishes population in thousands
SPEED_KMH = 40            # task spec: straight-line distance converted at 40 km/h
COVER_MIN = 60            # siting coverage threshold (minutes)
MAX_UNITS = 5
PER = 100_000
EARTH_KM = 6371.0088


def stop(msg):
    sys.exit(f"STOP: {msg}")


def check_inputs():
    missing = [p for p in (TB, POP, FACILITIES, LOOKUP, DISTRICTS) if not p.exists()]
    if missing:
        stop("missing input files:\n" + "\n".join(f"  - {p.relative_to(ROOT)}" for p in missing))


def need_cols(df, cols, name):
    lacking = [c for c in cols if c not in df.columns]
    if lacking:
        stop(f"{name} lacks columns {lacking}; found {list(df.columns)}")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------- inputs
def load_population(lookup):
    pop = pd.read_parquet(POP)
    pop = pop[pop["state"].str.lower() == "johor"].copy()
    for col, total in [("sex", "both"), ("age", "overall"), ("ethnicity", "overall")]:
        if col in pop.columns:
            pop = pop[pop[col] == total]
    pop["year"] = pd.to_datetime(pop["date"]).dt.year
    pop = pop.merge(lookup[["code", "dosm_name"]], left_on="district", right_on="dosm_name")
    pop["pop"] = pop["population"] * DOSM_POP_UNIT
    return pop[["code", "year", "pop"]]


def load_tb(lookup):
    tb = pd.read_csv(TB)
    need_cols(tb, ["code", "year", "cases"], TB.name)
    unknown = sorted(set(tb["code"]) - set(lookup["code"]))
    if unknown:
        stop(f"{TB.name} has codes not in district_lookup.csv: {unknown}")
    tb = tb[["code", "year", "cases"]].dropna(subset=["cases"])
    if INVENTORY.exists():
        inv = pd.read_csv(INVENTORY)
        weeks = inv[inv["selected"]].set_index("year")["week"]
        tb["bulletin_week"] = tb["year"].map(weeks).astype("Int64")
        tb["partial_year"] = tb["bulletin_week"] < 52
    else:
        tb["bulletin_week"], tb["partial_year"] = pd.NA, pd.NA
    return tb


# ---------------------------------------------------------------- 1) Score A
def empirical_bayes(g):
    n, x = g["pop"].to_numpy(float), g["cases"].to_numpy(float)
    r = x / n
    m = x.sum() / n.sum()
    s2 = (n * (r - m) ** 2).sum() / n.sum() - m / n.mean()
    s2 = max(s2, 0.0)
    c = s2 / (s2 + m / n) if s2 > 0 else np.zeros_like(n)
    return g.assign(raw_rate=r * PER, eb_mean=m * PER, eb_s2=s2, eb_C=c,
                    smoothed_rate=(m + c * (r - m)) * PER)


def score_a(tb, pop):
    df = tb.merge(pop, on=["code", "year"], how="left")
    no_pop = sorted(df.loc[df["pop"].isna(), "year"].unique().tolist())
    if no_pop:
        print(f"  Years without DOSM population (not used for Score A): {no_pop}")
    df = df.dropna(subset=["pop"])
    if df.empty:
        stop("no TB year has matching DOSM population")
    df = pd.concat([empirical_bayes(g) for _, g in df.groupby("year")], ignore_index=True)
    # rank within year; ties broken by higher raw case count (README)
    df["rank"] = df.sort_values(["smoothed_rate", "cases"], ascending=False).groupby("year").cumcount() + 1
    df["top3"] = df["rank"] <= 3
    return df


# ---------------------------------------------------------------- 2) Score B
def blank_score_b(latest, pop_latest, reason):
    print(f"  NOT COMPUTED: {reason}. Score B, gap, desert points and "
          "TB-weighted siting are left blank (never filled with guesses).")
    b = pop_latest[["code", "pop"]].assign(risk=np.nan, expected_cases=np.nan, expected_rate=np.nan)
    b = b.merge(latest[["code", "smoothed_rate"]], on="code")
    return b.assign(gap=np.nan), None


def score_b(latest, pop_latest):
    absent = [p.relative_to(ROOT).as_posix() for p in (PARAMS, RISK) if not p.exists()]
    if absent:
        return blank_score_b(latest, pop_latest, f"missing {absent}")
    params = pd.read_csv(PARAMS, dtype=str)
    risk = pd.read_csv(RISK, dtype={"code": str, "factor": str})
    need_cols(params, ["parameter", "value"], PARAMS.name)
    need_cols(risk, ["code", "factor", "p"], RISK.name)
    for name, df in [(PARAMS.name, params), (RISK.name, risk)]:
        ph = df[df.astype(str).apply(lambda col: col.str.contains("PLACEHOLDER", case=False)).any(axis=1)]
        if len(ph):
            print(f"  PLACEHOLDER rows in {name} (skipped): {len(ph)}")
            key = "parameter" if "parameter" in df.columns else ["code", "factor"]
            print("    " + ", ".join(ph[key].astype(str).agg("/".join, axis=1) if isinstance(key, list)
                                     else ph[key].astype(str)))
            df.drop(ph.index, inplace=True)

    pv = params.set_index("parameter")["value"]
    if "who_incidence_per_100k" not in pv:
        return blank_score_b(latest, pop_latest, f"{PARAMS.name} has no usable 'who_incidence_per_100k' row")
    who_rate = float(pv["who_incidence_per_100k"])

    risk["p"] = pd.to_numeric(risk["p"], errors="coerce")
    risk = risk.dropna(subset=["p"])
    risk["rr"] = pd.to_numeric(risk["factor"].map(lambda f: pv.get(f"rr_{f}")), errors="coerce")
    no_rr = sorted(risk.loc[risk["rr"].isna(), "factor"].unique())
    if no_rr:
        print(f"  Factors without a usable rr_<factor> in parameters.csv (skipped): {no_rr}")
    risk = risk.dropna(subset=["rr"])
    if risk.empty:
        return blank_score_b(latest, pop_latest, "no usable risk-factor rows (need p and a matching rr_<factor>)")
    print(f"  Factors used: {sorted(risk['factor'].unique())}; WHO incidence {who_rate}/100k")

    risk["term"] = 1 + risk["p"] * (risk["rr"] - 1)
    rel = risk.groupby("code")["term"].prod().rename("risk")
    b = pop_latest.set_index("code")[["pop"]].join(rel)
    if b["risk"].isna().any():
        print(f"  Districts with no risk-factor rows (risk = 1): {b.index[b['risk'].isna()].tolist()}")
        b["risk"] = b["risk"].fillna(1.0)
    johor_total = who_rate / PER * b["pop"].sum()
    w = b["pop"] * b["risk"]
    b["expected_cases"] = johor_total * w / w.sum()
    b["expected_rate"] = b["expected_cases"] / b["pop"] * PER
    b = b.join(latest.set_index("code")[["smoothed_rate"]])
    b["gap"] = b["expected_rate"] - b["smoothed_rate"]
    return b.reset_index(), johor_total


# ---------------------------------------------------------------- 3) travel
def population_cells(districts):
    """WorldPop cells inside each district: code, lat, lon, pop. None if the raster fails."""
    try:
        import rasterio
        from rasterio.mask import mask
        rows = []
        with rasterio.open(WORLDPOP) as src:
            d = districts.to_crs(src.crs)
            for code, geom in zip(d["code"], d.geometry):
                arr, tr = mask(src, [geom], crop=True, filled=False)
                band = arr[0]
                ii, jj = np.nonzero(~np.ma.getmaskarray(band) & (band.filled(0) > 0))
                xs, ys = rasterio.transform.xy(tr, ii, jj)
                rows.append(pd.DataFrame({"code": code, "lon": xs, "lat": ys,
                                          "cell_pop": band[ii, jj].astype(float)}))
        cells = pd.concat(rows, ignore_index=True)
        return cells if len(cells) else None
    except Exception as exc:
        print(f"  WorldPop raster failed ({type(exc).__name__}: {exc}); using district centroids")
        return None


def travel(districts, cells, fac):
    flat, flon = fac["lat"].to_numpy(), fac["lon"].to_numpy()
    if cells is not None:
        out = []
        for code, g in cells.groupby("code"):
            dist = haversine_km(g["lat"].to_numpy()[:, None], g["lon"].to_numpy()[:, None],
                                flat[None, :], flon[None, :]).min(axis=1)
            out.append((code, np.average(dist, weights=g["cell_pop"]), "worldpop_weighted"))
    else:
        c = districts.to_crs(3375).centroid.to_crs(4326)
        out = [(code, haversine_km(p.y, p.x, flat, flon).min(), "centroid")
               for code, p in zip(districts["code"], c)]
    t = pd.DataFrame(out, columns=["code", "nearest_km", "travel_method"])
    t["travel_min_approx"] = t["nearest_km"] / SPEED_KMH * 60
    return t


# ---------------------------------------------------------------- 4) Moran
def local_moran(districts, values):
    from esda.moran import Moran_Local
    from libpysal.weights import Queen
    d = districts.merge(values, on="code").reset_index(drop=True)
    w = Queen.from_dataframe(d, use_index=False)
    if w.islands:
        print(f"  Queen islands (no neighbours): {[d.loc[i, 'code'] for i in w.islands]}")
    w.transform = "r"
    lm = Moran_Local(d["smoothed_rate"].to_numpy(float), w, permutations=999, seed=42)
    quad = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    return pd.DataFrame({"code": d["code"], "moran_I": lm.Is,
                         "moran_quadrant": [quad[q] for q in lm.q], "moran_p": lm.p_sim})


# ---------------------------------------------------------------- 6) siting
def greedy(weights, covers, fac, label, expected):
    """covers: facilities x cells boolean. weights: what greedy maximises; expected: reported."""
    covered = np.zeros(covers.shape[1], bool)
    rows, used = [], set()
    for n in range(1, MAX_UNITS + 1):
        gain = (covers & ~covered).astype(float) @ weights
        gain[list(used)] = -1
        best = int(np.argmax(gain))
        if gain[best] <= 0:
            print(f"  {label}: no facility adds coverage at N = {n}; stopping")
            break
        used.add(best)
        covered |= covers[best]
        f = fac.iloc[best]
        rows.append({"version": label, "n_units": n, "osm_id": f["osm_id"], "name": f["name"],
                     "amenity": f["amenity"], "district": f.get("district"), "lat": f["lat"],
                     "lon": f["lon"], "added_weight": gain[best],
                     "covered_expected_cases": expected[covered].sum(),
                     "covered_expected_pct": expected[covered].sum() / expected.sum() * 100,
                     "covered_pop": cells_pop[covered].sum(),
                     "threshold_min": COVER_MIN, "method": "straight-line at 40 km/h (approximate)"})
    return rows


# ---------------------------------------------------------------- main
def main():
    global cells_pop
    check_inputs()
    OUT.mkdir(exist_ok=True)
    lookup = pd.read_csv(LOOKUP)
    districts = gpd.read_file(DISTRICTS)[["code", "geometry"]]
    pop = load_population(lookup)

    print("1) Score A")
    a = score_a(load_tb(lookup), pop)
    a = a.merge(lookup[["code", "district"]], on="code")
    cols = ["code", "district", "year", "cases", "pop", "raw_rate", "eb_mean", "eb_s2", "eb_C",
            "smoothed_rate", "rank", "top3", "bulletin_week", "partial_year"]
    a[cols].to_csv(CLEAN / "score_a.csv", index=False)
    full = a[a["partial_year"] != True]  # noqa: E712  (keeps NA = unknown)
    if full.empty:
        stop("no full-year TB data with population; cannot pick a latest year")
    year = int(full["year"].max())
    latest = full[full["year"] == year]
    print(f"  Saved data/clean/score_a.csv: {len(a)} rows, years {sorted(int(y) for y in a['year'].unique())}; "
          f"latest full year = {year}")

    print("2) Score B")
    pop_latest = pop[pop["year"] == year]
    b, johor_total = score_b(latest, pop_latest)
    if johor_total is not None:
        print(f"  Johor expected total = {johor_total:,.0f} cases")

    print("3) Approximate travel (straight-line, 40 km/h)")
    fac = gpd.read_file(FACILITIES)
    fac = gpd.sjoin(fac, districts, predicate="within", how="left").rename(columns={"code": "district"})
    cells = population_cells(districts)
    t = travel(districts, cells, fac)

    print("4) Local Moran's I (EXPLORATORY)")
    mor = local_moran(districts, latest[["code", "smoothed_rate"]])

    print("5) Desert points")
    s = (lookup[["code", "district"]].merge(latest[["code", "cases", "pop", "raw_rate",
                                                     "smoothed_rate", "rank", "top3"]], on="code")
         .merge(b[["code", "risk", "expected_cases", "expected_rate", "gap"]], on="code")
         .merge(t, on="code").merge(mor, on="code"))
    gap_hi = s["gap"] > s["gap"].median()
    min_hi = s["travel_min_approx"] > s["travel_min_approx"].median()
    s["desert_points"] = (s["moran_quadrant"].eq("LH").astype(int) + gap_hi.astype(int)
                          + min_hi.astype(int))
    s["desert_level"] = np.select([s["desert_points"] == 3, s["desert_points"] == 2],
                                  ["strong", "possible"], "none")
    s["gap_type"] = np.select([gap_hi & min_hi, gap_hi & ~min_hi],
                              ["access gap", "awareness gap"], "monitor")
    if s["gap"].isna().all():  # no Score B: the gap criterion cannot be judged
        s["desert_points"] = pd.NA
        s["desert_level"] = s["gap_type"] = "not computed (no Score B)"
    s["travel_label"] = "approximate (straight-line, 40 km/h)"
    s["moran_label"] = "exploratory (10 districts)"
    s["action"] = s["gap_type"].map({"access gap": "portable X-ray unit",
                                     "awareness gap": "trusted-messenger campaign",
                                     "monitor": "monitor"})
    s["year"] = year
    s.to_csv(CLEAN / "district_summary.csv", index=False)

    print("6) Greedy siting")
    if cells is None:
        cells = districts.to_crs(3375).centroid.to_crs(4326)
        cells = pd.DataFrame({"code": districts["code"], "lat": cells.y, "lon": cells.x,
                              "cell_pop": pop_latest.set_index("code").loc[districts["code"], "pop"].to_numpy()})
    share = cells["cell_pop"] / cells.groupby("code")["cell_pop"].transform("sum")
    exp_cells = (share * cells["code"].map(b.set_index("code")["expected_cases"])).to_numpy()
    cells_pop = cells["cell_pop"].to_numpy()
    km = haversine_km(fac["lat"].to_numpy()[:, None], fac["lon"].to_numpy()[:, None],
                      cells["lat"].to_numpy()[None, :], cells["lon"].to_numpy()[None, :])
    covers = km / SPEED_KMH * 60 <= COVER_MIN
    rows = greedy(cells_pop, covers, fac, "population_only", exp_cells)
    if np.isnan(exp_cells).all():
        print("  expected_tb version NOT COMPUTED (no Score B); population-only version only")
    else:
        rows = greedy(exp_cells, covers, fac, "expected_tb", exp_cells) + rows
    sit = pd.DataFrame(rows)
    sit.to_csv(OUT / "siting_results.csv", index=False)

    # ---- summary
    print(f"\nSaved data/clean/district_summary.csv: {len(s)} rows, {len(s.columns)} columns")
    print(s[["district", "smoothed_rate", "expected_rate", "gap", "travel_min_approx",
             "moran_quadrant", "moran_p", "desert_points", "gap_type"]]
          .round(2).to_string(index=False))
    print(f"\nSaved outputs/siting_results.csv: {len(sit)} rows")
    print(sit[["version", "n_units", "name", "district", "covered_expected_pct"]]
          .round(1).to_string(index=False))
    print("\nNotes: travel and siting are APPROXIMATE (straight-line, 40 km/h); "
          "local Moran's I is EXPLORATORY (10 districts).")


if __name__ == "__main__":
    main()
