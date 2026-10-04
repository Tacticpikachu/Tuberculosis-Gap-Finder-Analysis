"""V11 (confirmatory) and V12 (exploratory): do diagnostic deserts show real-world signs of missed TB?
Pre-registered in README.md ("Pre-registered addendum: diagnostic-desert validation", commit 84c14cd).

Reads:  data/clean/score_a.csv, data/clean/tb_district_year.csv, data/clean/district_summary.csv,
        data/clean/johor_districts.geojson, data/clean/population_district_year.csv,
        data/raw/who_tb_burden_estimates.csv, data/raw/johor_epid_W52_<year>.pdf (V12)
Saves:  outputs/validation_desert.csv, outputs/v11_deaths_vs_deserts.png; appends to outputs/validation_log.md
"""
import re
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
from esda.moran import Moran_Local
from libpysal.weights import Queen
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RAW, OUT = ROOT / "data" / "clean", ROOT / "data" / "raw", ROOT / "outputs"
YEARS = [2014, 2015, 2016, 2017]
CXR_YEARS = [2014, 2015]
N_PERM, SEED = 10_000, 42
QUAD = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
HEADER_ALIASES = {"TG": "LG", "SG": "ST"}


def desert_points(year, a, who, travel, districts):
    g = a[a.year == year].set_index("code")
    d = districts.merge(g[["smoothed_rate"]], left_on="code", right_index=True).reset_index(drop=True)
    w = Queen.from_dataframe(d, use_index=False); w.transform = "r"
    lm = Moran_Local(d["smoothed_rate"].to_numpy(float), w, permutations=999, seed=42)
    out = pd.DataFrame({"code": d["code"], "quad": [QUAD[q] for q in lm.q]}).set_index("code")
    out["gap"] = who[year] - g["smoothed_rate"]
    out["travel"] = travel
    out["points"] = ((out["quad"] == "LH").astype(int) + (out["gap"] > out["gap"].median()).astype(int)
                     + (out["travel"] > out["travel"].median()).astype(int))
    return out.assign(year=year)


def perm_p(x, y, rng, greater=True):
    obs = spearmanr(x, y).statistic
    sims = np.array([spearmanr(x, rng.permutation(y)).statistic for _ in range(N_PERM)])
    hits = (sims >= obs).sum() if greater else (sims <= obs).sum()
    return obs, (hits + 1) / (N_PERM + 1)


def cxr_cumulative(year, codes):
    """Cumulative 'TB - CXR' row from the cluster/outbreak table (section after a CUMULATIVE marker)."""
    with pdfplumber.open(RAW / f"johor_epid_W52_{year}.pdf") as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "CXR" not in text:
                continue
            header, section = None, None
            for line in text.split("\n"):
                up = line.upper()
                if "CUMULATIVE" in up:
                    section = "cumulative"
                elif "CURRENT WEEK" in up:
                    section = "current"
                toks = [HEADER_ALIASES.get(t, t) for t in line.split()]
                if sum(t in codes for t in toks) == len(codes):
                    header = [t for t in toks if t in codes or t in ("STATE", "JOHOR", "JOHORE")]
                if "CXR" in up and header and section == "cumulative":
                    nums = [int(v.replace(",", "")) for v in re.findall(r"\d[\d,]*", line.split("CXR", 1)[1])]
                    if len(nums) == len(header):
                        return dict(zip(header, nums)), section
    return None, None


def main():
    a = pd.read_csv(CLEAN / "score_a.csv")
    tb = pd.read_csv(CLEAN / "tb_district_year.csv")
    summ = pd.read_csv(CLEAN / "district_summary.csv").set_index("code")
    lookup = summ["district"]
    districts = gpd.read_file(CLEAN / "johor_districts.geojson")[["code", "geometry"]]
    who_all = pd.read_csv(RAW / "who_tb_burden_estimates.csv")
    who = who_all[who_all.iso3 == "MYS"].set_index("year")["e_inc_100k"]
    pts = pd.concat([desert_points(y, a, who, summ["travel_min_approx"], districts) for y in YEARS])
    total = pts.groupby(level=0)["points"].sum().rename("points_2014_17")

    d = tb[tb.year.isin(YEARS)].groupby("code")[["cases", "deaths"]].sum()
    d["death_ratio"] = d["deaths"] / d["cases"]
    v11 = d.join(total)
    v11["district"] = lookup
    rng = np.random.default_rng(SEED)
    rho, p = perm_p(v11["points_2014_17"].to_numpy(), v11["death_ratio"].to_numpy(), rng, greater=True)
    hi = v11[v11.points_2014_17 >= 6]; lo = v11[v11.points_2014_17 < 6]
    hi_r = hi.deaths.sum() / hi.cases.sum() if len(hi) else np.nan
    lo_r = lo.deaths.sum() / lo.cases.sum() if len(lo) else np.nan
    verdict = "PASS" if rho > 0 else "FAIL"
    strength = "supportive (p < 0.05)" if (rho > 0 and p < 0.05) else "direction only (p ≥ 0.05)" if rho > 0 else "opposite direction"

    rows = [
        {"test": "V11", "metric": "spearman_rho_points_vs_death_ratio", "value": rho, "pass": verdict},
        {"test": "V11", "metric": "one_sided_permutation_p", "value": p, "pass": strength},
        {"test": "V11", "metric": "death_ratio_points_ge6", "value": hi_r, "pass": f"{len(hi)} districts: {', '.join(hi.district)}"},
        {"test": "V11", "metric": "death_ratio_points_lt6", "value": lo_r, "pass": f"{len(lo)} districts"},
    ]

    # V12 exploratory
    codes = set(summ.index)
    pop = pd.read_csv(CLEAN / "population_district_year.csv")
    cx = []
    for y in CXR_YEARS:
        vals, sec = cxr_cumulative(y, codes)
        if vals is None:
            print(f"V12: cumulative CXR row not found for {y}")
            continue
        state = next((vals[k] for k in ("STATE", "JOHOR", "JOHORE") if k in vals), None)
        dsum = sum(vals[c] for c in codes)
        print(f"V12 {y}: cumulative CXR row found; district sum {dsum} vs state {state} -> {'ok' if dsum == state else 'MISMATCH'}")
        for c in codes:
            cx.append({"code": c, "year": y, "cxr": vals[c]})
    if cx:
        cx = pd.DataFrame(cx).merge(pop, on=["code", "year"])
        cxr = cx.groupby("code").agg(cxr=("cxr", "sum"), pop=("pop", "sum"))
        cxr["cxr_per_100k"] = cxr.cxr / cxr["pop"] * 1e5
        p12 = pts[pts.year.isin(CXR_YEARS)].groupby(level=0)["points"].sum().rename("points_2014_15")
        v12 = cxr.join(p12)
        rho12, p12v = perm_p(v12["points_2014_15"].to_numpy(), v12["cxr_per_100k"].to_numpy(), np.random.default_rng(SEED), greater=False)
        rows += [{"test": "V12", "metric": "spearman_rho_points_vs_cxr_rate", "value": rho12, "pass": "exploratory"},
                 {"test": "V12", "metric": "one_sided_permutation_p (rho<0)", "value": p12v, "pass": "exploratory"}]
        v11 = v11.join(v12[["cxr_per_100k", "points_2014_15"]])
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "validation_desert.csv", index=False)

    # chart
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(v11.points_2014_17, v11.death_ratio * 100, s=v11.cases / 6, c="#1c4a3a", alpha=.8)
    for _, r in v11.iterrows():
        ax.annotate(r.district, (r.points_2014_17, r.death_ratio * 100), fontsize=8, xytext=(4, 3), textcoords="offset points")
    ax.set(xlabel="Desert points, summed 2014–2017 (0–12)", ylabel="TB deaths per 100 cases, 2014–2017",
           title=f"V11: deserts vs TB deaths (Spearman ρ = {rho:.2f}, p = {p:.3f})")
    fig.tight_layout(); fig.savefig(OUT / "v11_deaths_vs_deserts.png", dpi=150); plt.close(fig)

    show = v11[["district", "points_2014_17", "cases", "deaths", "death_ratio"] + (["cxr_per_100k"] if "cxr_per_100k" in v11 else [])]
    print("\nPer-year desert points:")
    print(pts.reset_index().pivot(index="code", columns="year", values="points").join(lookup).set_index("district").to_string())
    print("\nV11/V12 table:")
    print(show.sort_values("points_2014_17", ascending=False).round(4).to_string(index=False))
    print("\nSaved outputs/validation_desert.csv and outputs/v11_deaths_vs_deserts.png")
    print(res.to_string(index=False))

    log = OUT / "validation_log.md"
    md = log.read_text() if log.exists() else ""
    md = md.split("\n## Desert validation")[0].rstrip() + "\n\n## Desert validation (pre-registered addendum)\n\n| Test | Result | Verdict |\n|---|---|---|\n"
    md += (f"| V11 Deaths vs deserts | Spearman ρ = {rho:.2f} (one-sided p = {p:.3f}); deaths per 100 cases: "
           f"{hi_r*100:.1f} in districts with ≥ 6 points vs {lo_r*100:.1f} below | {verdict} ({strength}) |\n")
    if any(r["test"] == "V12" for r in rows):
        md += f"| V12 Chest X-ray vs deserts (exploratory) | Spearman ρ = {rho12:.2f} (one-sided p = {p12v:.3f}) | reported only |\n"
    log.write_text(md)


if __name__ == "__main__":
    main()
