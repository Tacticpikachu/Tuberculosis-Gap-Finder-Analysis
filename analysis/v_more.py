"""V1b, V8, V9 (a: solver, b: baselines, c: travel model) and V10, as pre-registered in README (addendum 2).

Reads:  data/raw/bulletins_all/*.pdf, data/raw/bulletin_inventory.csv, data/raw/health_facilities.geojson,
        data/raw/mys_ppp_2020_1km_Aggregated.tif, data/raw/map_friction_motorised_2019_johor.tif,
        data/clean/district_summary.csv, data/clean/score_a.csv, data/clean/johor_districts.geojson,
        outputs/siting_results.csv
Saves:  outputs/validation_more.csv, outputs/v9_baselines.png, outputs/v1b_mismatches.csv
"""
import sys
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
import rasterio
from esda.moran import Moran_Local
from libpysal.weights import KNN, Queen, Rook
from scipy.stats import spearmanr
from skimage.graph import MCP_Geometric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import a04_extract as E  # noqa: E402
import a05_scores as A  # noqa: E402

CLEAN, RAW, OUT = ROOT / "data" / "clean", ROOT / "data" / "raw", ROOT / "outputs"
SPEED, SEED = 40, 42
rows = []


def add(test, metric, value, verdict=""):
    rows.append({"test": test, "metric": metric, "value": value, "pass": verdict})
    print(f"  {test:5s} {metric}: {value} {verdict}")


# ---------------------------------------------------------------- V1b
def current_week_row(pdf, codes):
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "CUMULATIVE" in text.upper():
            continue
        header = None
        for line in text.split("\n"):
            toks = [E.HEADER_ALIASES.get(t, t) for t in line.split()]
            cols = [t for t in toks if t in codes or t in E.TOTAL_HEADERS]
            if len([t for t in cols if t in codes]) == len(codes) and cols and cols[-1] in E.TOTAL_HEADERS:
                header = cols
                continue
            m = E.TB_ROW.match(line)
            if header and m:
                vals = [int(v.replace(",", "")) for v in E.NUM.findall(m.group(1))]
                if len(vals) == len(header):
                    return dict(zip(header, vals))
    return None


def v1b(codes):
    print("V1b data consistency (all bulletins)")
    inv = pd.read_csv(RAW / "bulletin_inventory.csv").dropna(subset=["year", "week"])
    recs = []
    for _, b in inv.iterrows():
        with pdfplumber.open(RAW / "bulletins_all" / b["original_name"]) as pdf:
            cum = E.find_table(pdf, codes)
            cur = current_week_row(pdf, codes)
        if cum and cur:
            cvals = dict(zip(cum[1], cum[2]))
            for c in codes:
                recs.append({"year": int(b.year), "week": int(b.week), "code": c, "cum": cvals[c], "cur": cur[c]})
    r = pd.DataFrame(recs)
    parsed = r.drop_duplicates(["year", "week"]).shape[0]
    r = r.sort_values(["code", "year", "week"])
    r["prev_week"] = r.groupby(["code", "year"])["week"].shift()
    r["prev_cum"] = r.groupby(["code", "year"])["cum"].shift()
    chk = r[r["prev_week"] == r["week"] - 1].copy()
    chk["diff"] = chk["cum"] - chk["prev_cum"]
    chk["match"] = chk["diff"] == chk["cur"]
    rate = chk["match"].mean()
    add("V1b", "bulletins parsed (both tables)", f"{parsed} of {len(inv)}")
    add("V1b", "district-week checks", len(chk))
    add("V1b", "exact match rate", round(rate, 4), "PASS" if rate >= 0.95 else "FAIL")
    mism = chk[~chk["match"]][["year", "week", "code", "prev_cum", "cum", "diff", "cur"]]
    mism.to_csv(OUT / "v1b_mismatches.csv", index=False)
    if len(mism):
        add("V1b", "mismatch mean |diff − current|", round((mism["diff"] - mism["cur"]).abs().mean(), 2))


# ---------------------------------------------------------------- siting helpers
def coverage(fac, cells, km):
    d = A.haversine_km(fac["lat"].to_numpy()[:, None], fac["lon"].to_numpy()[:, None],
                       cells["lat"].to_numpy()[None, :], cells["lon"].to_numpy()[None, :])
    return d <= km


def greedy_sites(C, w, n):
    covered = np.zeros(C.shape[1], bool); out = []
    for _ in range(n):
        gain = (C & ~covered).astype(np.float64) @ w
        gain[out] = -1
        best = int(np.argmax(gain)); out.append(best); covered |= C[best]
    return out


def value(C, w, idx):
    return float(w[np.any(C[idx], axis=0)].sum()) if len(idx) else 0.0


def siting_checks(fac, cells, w, districts, summ):
    total = w.sum()
    print("V9a solver check (brute force, 60 min)")
    C60 = coverage(fac, cells, 40)
    s = C60.astype(np.float64) @ w
    g1 = greedy_sites(C60, w, 1); g2 = greedy_sites(C60, w, 2)
    best1 = int(np.argmax(s))
    Cw = C60.astype(np.float32) * w.astype(np.float32)
    O = Cw @ C60.astype(np.float32).T  # overlap of expected TB between every pair
    pair = s[:, None] + s[None, :] - O
    np.fill_diagonal(pair, -1)
    i, j = np.unravel_index(np.argmax(pair), pair.shape)
    brute2 = value(C60, w, [i, j]); greedy2 = value(C60, w, g2)
    add("V9a", "N=1 greedy vs brute force", f"{s[g1[0]]:.1f} vs {s[best1]:.1f}", "match" if abs(s[g1[0]] - s[best1]) < 1e-6 else "DIFFER")
    add("V9a", "N=2 greedy vs brute force", f"{greedy2:.1f} vs {brute2:.1f} ({len(fac) * (len(fac) - 1) // 2:,} pairs)",
        "match" if greedy2 >= brute2 - 1e-3 else f"greedy {100 * greedy2 / brute2:.2f}% of optimum")
    v9a_pass = abs(s[g1[0]] - s[best1]) < 1e-6 and greedy2 >= brute2 - 1e-3
    add("V9a", "verdict", "", "PASS" if v9a_pass else "FAIL")

    print("V9b baselines (N = 1-5)")
    hosp = fac[fac["amenity"] == "hospital"].reset_index()
    order = summ.sort_values("pop", ascending=False)
    dist_hosp = []
    for code in order.index:
        cc = cells[cells["code"] == code]
        lat, lon = np.average(cc["lat"], weights=cc["cell_pop"]), np.average(cc["lon"], weights=cc["cell_pop"])
        dh = A.haversine_km(lat, lon, hosp["lat"].to_numpy(), hosp["lon"].to_numpy())
        dist_hosp.append(int(hosp.loc[int(np.argmin(dh)), "index"]))
    rng = np.random.default_rng(SEED)
    res = []
    for n in range(1, 6):
        gv = value(C60, w, greedy_sites(C60, w, n)); hv = value(C60, w, dist_hosp[:n])
        rv = np.array([value(C60, w, rng.choice(len(fac), n, replace=False)) for _ in range(1000)])
        res.append((n, gv / total * 100, hv / total * 100, rv.mean() / total * 100, (gv > rv).mean() * 100))
        add("V9b", f"N={n} % expected TB: greedy / district hospitals / random mean", f"{res[-1][1]:.1f} / {res[-1][2]:.1f} / {res[-1][3]:.1f}",
            f"greedy beats {res[-1][4]:.1f}% of random sets")
    r = pd.DataFrame(res, columns=["n", "greedy", "hospitals", "random", "beats"])
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for col, lab, colr in [("greedy", "TB Gap Finder (greedy)", "#1c4a3a"), ("hospitals", "One hospital per district", "#c97f10"), ("random", "Random sites (mean of 1,000)", "#a8a290")]:
        ax.plot(r.n, r[col], marker="o", label=lab, color=colr)
    ax.set(xlabel="Number of portable X-ray units", ylabel="% of expected TB within 60 min", title="V9b: siting vs simple alternatives")
    ax.legend(); ax.set_xticks(range(1, 6)); fig.tight_layout(); fig.savefig(OUT / "v9_baselines.png", dpi=150); plt.close(fig)

    print("V8 robustness (30 / 60 / 90 / 120 min)")
    picks = {}
    for minutes in (30, 60, 90, 120):
        Ck = C60 if minutes == 60 else coverage(fac, cells, minutes / 60 * SPEED)
        idx = greedy_sites(Ck, w, 3); picks[minutes] = idx
        add("V8", f"{minutes} min, N=3 sites", "; ".join(fac.iloc[k]["name"] or "?" for k in idx), f"{value(Ck, w, idx) / total * 100:.1f}% covered")
    shared = len(set(picks[60]) & set(picks[90]))
    add("V8", "sites shared 60 vs 90 min (N=3)", shared, "PASS" if shared >= 2 else "FAIL")


# ---------------------------------------------------------------- V9c travel model
def v9c(fac, cells, summ):
    print("V9c travel model (MAP friction vs straight line)")
    with rasterio.open(RAW / "map_friction_motorised_2019_johor.tif") as src:
        fr = src.read(1).astype(float); tr = src.transform; nod = src.nodata
        lat0 = (src.bounds.top + src.bounds.bottom) / 2
    fr[(fr <= 0) | ~np.isfinite(fr) | ((fr == nod) if nod is not None else False)] = 1.0  # unusable cells: very slow
    dy = abs(tr.e) * 110_574; dx = abs(tr.a) * 111_320 * np.cos(np.radians(lat0))
    rows_, cols_ = rasterio.transform.rowcol(tr, fac["lon"].to_numpy(), fac["lat"].to_numpy())
    ok = [(r, c) for r, c in zip(rows_, cols_) if 0 <= r < fr.shape[0] and 0 <= c < fr.shape[1]]
    mcp = MCP_Geometric(fr, sampling=(dy, dx))
    tt, _ = mcp.find_costs(ok)
    cr, cc = rasterio.transform.rowcol(tr, cells["lon"].to_numpy(), cells["lat"].to_numpy())
    cr, cc = np.clip(cr, 0, fr.shape[0] - 1), np.clip(cc, 0, fr.shape[1] - 1)
    cells = cells.assign(fric_min=tt[cr, cc])
    f = cells.groupby("code").apply(lambda g: np.average(g["fric_min"], weights=g["cell_pop"]), include_groups=False).rename("friction_min")
    t = summ[["district", "travel_min_approx"]].join(f)
    rho = spearmanr(t["travel_min_approx"], t["friction_min"]).statistic
    add("V9c", "Spearman rho straight-line vs friction travel", round(rho, 3), "PASS" if rho >= 0.7 else "FAIL")
    a = t["travel_min_approx"] > t["travel_min_approx"].median(); b = t["friction_min"] > t["friction_min"].median()
    add("V9c", "districts whose travel desert point changes", int((a != b).sum()), ", ".join(t.loc[a != b, "district"]) or "none")
    print(t.round(1).sort_values("friction_min", ascending=False).to_string())
    return t


# ---------------------------------------------------------------- V10
def v10(districts):
    print("V10 Moran stability")
    a = pd.read_csv(CLEAN / "score_a.csv")
    quad = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    lab = {}
    for year in (2014, 2015, 2016, 2017, 2023):
        d = districts.merge(a[a.year == year][["code", "smoothed_rate"]], on="code").reset_index(drop=True)
        y = d["smoothed_rate"].to_numpy(float)
        for name, W in [("queen", Queen), ("rook", Rook), ("knn3", None)]:
            w = KNN.from_dataframe(d, k=3) if W is None else W.from_dataframe(d, use_index=False)
            w.transform = "r"
            lm = Moran_Local(y, w, permutations=999, seed=42)
            for code, q, p in zip(d["code"], lm.q, lm.p_sim):
                lab[(code, year, name)] = (quad[q], p)
    t = pd.Series({k: v[0] for k, v in lab.items()}).unstack([1, 2])
    queen = t.xs("queen", axis=1, level=1)
    lh_years = (queen == "LH").sum(axis=1)
    agree23 = (t[(2023, "queen")] == t[(2023, "rook")]).mean(), (t[(2023, "queen")] == t[(2023, "knn3")]).mean()
    sig = sum(1 for v in lab.values() if v[1] < 0.05)
    add("V10", "queen vs rook / queen vs k=3 agreement (2023)", f"{agree23[0]:.0%} / {agree23[1]:.0%}")
    add("V10", "LH under queen, years out of 5", "; ".join(f"{c} {n}" for c, n in lh_years.sort_values(ascending=False).items() if n), "reported")
    add("V10", "labels with p < 0.05 (all years x schemes)", f"{sig} of {len(lab)}")
    print(queen.to_string())


def main():
    summ = pd.read_csv(CLEAN / "district_summary.csv").set_index("code")
    districts = gpd.read_file(CLEAN / "johor_districts.geojson")[["code", "geometry"]]
    codes = set(summ.index)
    v1b(codes)
    fac = gpd.read_file(RAW / "health_facilities.geojson").reset_index(drop=True)
    cells = A.population_cells(districts)
    share = cells["cell_pop"] / cells.groupby("code")["cell_pop"].transform("sum")
    w = (share * cells["code"].map(summ["expected_cases"])).to_numpy()
    siting_checks(fac, cells, w, districts, summ)
    v9c(fac, cells, summ)
    v10(districts)
    pd.DataFrame(rows).to_csv(OUT / "validation_more.csv", index=False)
    print(f"\nSaved outputs/validation_more.csv ({len(rows)} rows), outputs/v9_baselines.png, outputs/v1b_mismatches.csv")


if __name__ == "__main__":
    main()
