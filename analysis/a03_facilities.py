"""A3: convert an Overpass Turbo GeoJSON export into data/raw/health_facilities.geojson.

Used when the Overpass API cannot be reached from the analysis machine and the same query
(see OVERPASS_QUERY in a03_download.py) was run by hand at overpass-turbo.eu.

Reads:  data/raw/overpass_turbo_export.geojson
Saves:  data/raw/health_facilities.geojson (columns name, amenity, lat, lon, osm_id)
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "overpass_turbo_export.geojson"
DEST = ROOT / "data" / "raw" / "health_facilities.geojson"


def main():
    if not SRC.exists():
        sys.exit(f"STOP: {SRC.relative_to(ROOT)} not found")
    features = json.loads(SRC.read_text())["features"]
    out, skipped = [], Counter()
    for f in features:
        geom = f.get("geometry") or {}
        if geom.get("type") != "Point":
            skipped[geom.get("type")] += 1
            continue
        lon, lat = geom["coordinates"][:2]
        props = f.get("properties", {})
        out.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": props.get("name"),
                # amenity tag; for objects tagged only with healthcare=*, the healthcare value
                "amenity": props.get("amenity") or props.get("healthcare"),
                "lat": lat,
                "lon": lon,
                "osm_id": f.get("id") or props.get("@id"),
            },
        })
    if not out:
        sys.exit("STOP: no point features in the export")
    DEST.write_text(json.dumps({"type": "FeatureCollection", "features": out}))

    print(f"Saved {DEST.relative_to(ROOT)}: {len(out)} rows, columns [name, amenity, lat, lon, osm_id]")
    if skipped:
        print(f"  skipped non-point features: {dict(skipped)}")
    print("  per type:", dict(Counter(f["properties"]["amenity"] for f in out)))
    print("  without a name:", sum(1 for f in out if not f["properties"]["name"]))
    for f in out[:3]:
        print("  e.g.", f["properties"])


if __name__ == "__main__":
    main()
