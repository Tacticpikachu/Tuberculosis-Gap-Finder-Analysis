"""A3 part 2: download population, income, boundaries, WorldPop raster and OSM health facilities.

Saves into data/raw/. Skips files that already exist. Reports and skips any failure.
"""
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TIMEOUT = 120

FILES = {
    "population_district.parquet": "https://storage.dosm.gov.my/population/population_district.parquet",
    "hh_income_district.parquet": "https://storage.dosm.gov.my/hies/hh_income_district.parquet",
    "mys_ppp_2020_1km_Aggregated.tif": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/MYS/mys_ppp_2020_1km_Aggregated.tif",
}
GEOBOUNDARIES_API = "https://www.geoboundaries.org/api/current/gbOpen/MYS/ADM2/"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:300];
area["ISO3166-2"="MY-01"]["admin_level"="4"]->.johor;
(
  node["amenity"~"^(clinic|hospital|doctors)$"](area.johor);
  way["amenity"~"^(clinic|hospital|doctors)$"](area.johor);
  node["healthcare"~"^(clinic|hospital)$"](area.johor);
  way["healthcare"~"^(clinic|hospital)$"](area.johor);
);
out center tags;
"""


def size_mb(path):
    return f"{path.stat().st_size / 1e6:.2f} MB"


def download(url, dest):
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(dest)


def get_boundaries(dest):
    meta = requests.get(GEOBOUNDARIES_API, timeout=TIMEOUT)
    meta.raise_for_status()
    url = meta.json()["gjDownloadURL"]
    print(f"  gjDownloadURL = {url}")
    download(url, dest)


def get_health_facilities(dest):
    r = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, timeout=TIMEOUT * 3)
    r.raise_for_status()
    elements = r.json()["elements"]
    features = []
    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": tags.get("name"),
                # amenity tag; for objects tagged only with healthcare=*, the healthcare value
                "amenity": tags.get("amenity") or tags.get("healthcare"),
                "lat": lat,
                "lon": lon,
                "osm_id": f"{el['type']}/{el['id']}",
            },
        })
    if not features:
        raise RuntimeError("Overpass returned 0 facilities")
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    print(f"  {len(features)} facilities")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [(name, lambda d, u=url: download(u, d)) for name, url in FILES.items()]
    jobs.insert(2, ("mys_adm2.geojson", get_boundaries))
    jobs.append(("health_facilities.geojson", get_health_facilities))

    saved, failed = [], []
    for name, fn in jobs:
        dest = RAW / name
        if dest.exists():
            print(f"SKIP  {name} (exists, {size_mb(dest)})")
            saved.append(name)
            continue
        print(f"GET   {name}")
        try:
            fn(dest)
            print(f"OK    {name} ({size_mb(dest)})")
            saved.append(name)
        except Exception as exc:
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
            failed.append(name)

    print(f"\nSummary: {len(saved)} files present in data/raw/, {len(failed)} failed")
    for name in failed:
        print(f"  FAILED: {name}")


if __name__ == "__main__":
    main()
