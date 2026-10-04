"""A3: cut the global MAP 2019 motorised friction surface down to Johor (plus a margin).

Usage: python analysis/a03_clip_friction.py [path to global friction .tif]
       (default: data/raw/map_friction_motorised_2019.tif)

Reads:  the global friction GeoTIFF downloaded by hand from data.malariaatlas.org,
        data/clean/johor_districts.geojson
Saves:  data/raw/map_friction_motorised_2019_johor.tif
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DEFAULT_SRC = RAW / "map_friction_motorised_2019.tif"
DEST = RAW / "map_friction_motorised_2019_johor.tif"
DISTRICTS = ROOT / "data" / "clean" / "johor_districts.geojson"
MARGIN_DEG = 0.2  # about 20 km, so travel across district borders is not cut off


def main():
    src_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_SRC
    if not src_path.exists():
        tifs = sorted(p.name for p in RAW.glob("*.tif*"))
        sys.exit(f"STOP: {src_path} not found. .tif files in data/raw/: {tifs or 'none'}")
    if not DISTRICTS.exists():
        sys.exit("STOP: data/clean/johor_districts.geojson missing. Run analysis/a03_lookup.py first.")

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

    band = data[0].astype("float64")
    valid = band[np.isfinite(band) & (band != nodata)] if nodata is not None else band[np.isfinite(band)]
    print(f"Saved {DEST.relative_to(ROOT)} ({DEST.stat().st_size / 1e6:.2f} MB)")
    print(f"  from {src_path.name}, CRS {meta['crs']}, {meta['width']} x {meta['height']} cells")
    print(f"  cells with data: {valid.size}; friction (minutes per metre) min {valid.min():.6g}, "
          f"median {np.median(valid):.6g}, max {valid.max():.6g}")


if __name__ == "__main__":
    main()
