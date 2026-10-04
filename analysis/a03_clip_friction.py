"""A3: get the MAP 2019 motorised friction surface for Johor (plus a margin).

Usage: python analysis/a03_clip_friction.py [path to global friction .tif]
  - with a global GeoTIFF downloaded by hand (default data/raw/map_friction_motorised_2019.tif):
    cuts it down to Johor.
  - if that file does not exist: requests only the Johor window from the MAP WCS server
    (coverage Accessibility__202001_Global_Motorized_Friction_Surface).

Reads:  the global friction GeoTIFF, or the MAP WCS server; data/clean/johor_districts.geojson
Saves:  data/raw/map_friction_motorised_2019_johor.tif
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DEFAULT_SRC = RAW / "map_friction_motorised_2019.tif"
DEST = RAW / "map_friction_motorised_2019_johor.tif"
DISTRICTS = ROOT / "data" / "clean" / "johor_districts.geojson"
MARGIN_DEG = 0.2  # about 20 km, so travel across district borders is not cut off
WCS_URL = "https://data.malariaatlas.org/geoserver/ows"
WCS_COVERAGE = "Accessibility__202001_Global_Motorized_Friction_Surface"


def fetch_from_wcs():
    """Download only the Johor window of the global surface (values are not modified)."""
    minx, miny, maxx, maxy = gpd.read_file(DISTRICTS).to_crs(4326).total_bounds
    params = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
              ("coverageId", WCS_COVERAGE), ("format", "image/tiff"),
              ("subset", f"Lat({miny - MARGIN_DEG},{maxy + MARGIN_DEG})"),
              ("subset", f"Long({minx - MARGIN_DEG},{maxx + MARGIN_DEG})")]
    r = requests.get(WCS_URL, params=params, timeout=300)
    print(f"GET {r.url}")
    r.raise_for_status()
    if not r.content.startswith((b"II*\x00", b"MM\x00*")):
        sys.exit(f"STOP: server did not return a GeoTIFF: {r.text[:300]}")
    DEST.write_bytes(r.content)
    return f"MAP WCS {WCS_COVERAGE}"


def main():
    src_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_SRC
    if not DISTRICTS.exists():
        sys.exit("STOP: data/clean/johor_districts.geojson missing. Run analysis/a03_lookup.py first.")
    if not src_path.exists():
        if len(sys.argv) > 1:
            sys.exit(f"STOP: {src_path} not found")
        print(f"{src_path.name} not found; requesting the Johor window from the MAP server")
        report(fetch_from_wcs())
        return
    clip(src_path)
    report(src_path.name)


def clip(src_path):
    with rasterio.open(src_path) as src:
        johor = gpd.read_file(DISTRICTS).to_crs(src.crs)
        minx, miny, maxx, maxy = johor.total_bounds
        window = from_bounds(minx - MARGIN_DEG, miny - MARGIN_DEG,
                             maxx + MARGIN_DEG, maxy + MARGIN_DEG, src.transform)
        window = window.round_offsets().round_lengths()
        data = src.read(window=window)
        meta = src.meta | {"height": data.shape[1], "width": data.shape[2],
                           "transform": src.window_transform(window), "compress": "deflate"}
        nodata = src.nodata

    with rasterio.open(DEST, "w", **meta) as dst:
        dst.write(data)


def report(source):
    with rasterio.open(DEST) as r:
        data, meta, nodata = r.read(), r.meta, r.nodata
    band = data[0].astype("float64")
    valid = band[np.isfinite(band) & (band != nodata)] if nodata is not None else band[np.isfinite(band)]
    print(f"Saved {DEST.relative_to(ROOT)} ({DEST.stat().st_size / 1e6:.2f} MB)")
    print(f"  from {source}, CRS {meta['crs']}, {meta['width']} x {meta['height']} cells")
    print(f"  cells with data: {valid.size}; friction (minutes per metre) min {valid.min():.6g}, "
          f"median {np.median(valid):.6g}, max {valid.max():.6g}")


if __name__ == "__main__":
    main()
