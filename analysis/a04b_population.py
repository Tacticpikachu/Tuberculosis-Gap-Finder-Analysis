"""A4b: district population per year: DOSM where available (2020+), WorldPop 1 km sums otherwise.

Reads:  data/raw/population_district.parquet, data/raw/mys_ppp_<year>_1km_Aggregated.tif,
        data/clean/district_lookup.csv, data/clean/johor_districts.geojson
Saves:  data/clean/population_district_year.csv (code, year, pop, source)
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.mask import mask

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
DOSM_POP_UNIT = 1000  # DOSM publishes population in thousands


def main():
    lookup = pd.read_csv(CLEAN / "district_lookup.csv")
    pop = pd.read_parquet(RAW / "population_district.parquet")
    pop = pop[(pop.state == "Johor") & (pop.sex == "both") & (pop.age == "overall")
              & (pop.ethnicity == "overall")]
    pop = pop.merge(lookup[["code", "dosm_name"]], left_on="district", right_on="dosm_name")
    dosm = pd.DataFrame({"code": pop["code"], "year": pd.to_datetime(pop["date"]).dt.year,
                         "pop": pop["population"] * DOSM_POP_UNIT, "source": "DOSM population_district"})

    districts = gpd.read_file(CLEAN / "johor_districts.geojson")
    rows = []
    for tif in sorted(RAW.glob("mys_ppp_*_1km_Aggregated.tif")):
        year = int(tif.name.split("_")[2])
        if year in set(dosm["year"]):
            continue
        with rasterio.open(tif) as src:
            d = districts.to_crs(src.crs)
            for code, geom in zip(d["code"], d.geometry):
                arr, _ = mask(src, [geom], crop=True, filled=False)
                rows.append({"code": code, "year": year, "pop": float(arr[0].clip(min=0).sum()),
                             "source": f"WorldPop 1km {tif.name}"})
    out = pd.concat([dosm, pd.DataFrame(rows)], ignore_index=True).sort_values(["year", "code"])
    out.to_csv(CLEAN / "population_district_year.csv", index=False)
    print(f"Saved data/clean/population_district_year.csv: {len(out)} rows, columns {list(out.columns)}")
    print(out.pivot(index="code", columns="year", values="pop").round(-2).to_string())
    print(out.drop_duplicates("year")[["year", "source"]].to_string(index=False))


if __name__ == "__main__":
    main()
