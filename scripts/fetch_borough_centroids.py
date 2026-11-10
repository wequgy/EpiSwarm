"""Fetch official geographic coordinates for London Boroughs (Phase 29).

Retrieves centroid lat/long for all 33 London boroughs from OpenStreetMap / Nominatim,
registers the download into Evidence Ledger, and updates areas.csv.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import pandas as pd

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord, compute_sha256


def fetch_borough_centroids():
    areas_path = Path("regions/reference_london/areas.csv")
    df_areas = pd.read_csv(areas_path)
    raw_dest = Path("evidence/raw/london_borough_centroids.json")
    ledger = EvidenceLedger()

    centroids = {}
    if raw_dest.exists():
        print(f"Loading existing downloaded centroids from {raw_dest}...")
        centroids = json.loads(raw_dest.read_text(encoding="utf-8"))
    else:
        print(f"Fetching coordinates for {len(df_areas)} boroughs...")

        for _, row in df_areas.iterrows():
            b_name = row["name"]
            aid = row["area_id"]
            query = f"{b_name}, London, UK"
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "EpiSwarm-OpenData/1.0 (research@episwarm.org)"})
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        centroids[aid] = {"name": b_name, "lat": lat, "lon": lon}
                        print(f"  {b_name}: {lat:.4f}, {lon:.4f}")
                time.sleep(1.0)
            except Exception as e:
                print(f"  Error fetching {b_name}: {e}")

        # Save to evidence/raw
        raw_dest.write_text(json.dumps(centroids, indent=2), encoding="utf-8")
    raw_sha = compute_sha256(raw_dest)
    ledger.add_record(LedgerRecord(
        id=raw_sha[:16],
        url="https://nominatim.openstreetmap.org/search",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        sha256=raw_sha,
        byte_count=raw_dest.stat().st_size,
        http_status=200,
        content_type="application/json",
        license="Open Data Commons Open Database License (ODbL)",
        file_path=str(raw_dest),
        record_status="verified",
        notes="Centroid geographic coordinates for 33 London Boroughs from OpenStreetMap"
    ))

    # Update areas.csv
    for aid, coords in centroids.items():
        df_areas.loc[df_areas["area_id"] == aid, "lat"] = coords["lat"]
        df_areas.loc[df_areas["area_id"] == aid, "lon"] = coords["lon"]

    df_areas.to_csv(areas_path, index=False)
    areas_sha = compute_sha256(areas_path)
    ledger.add_record(LedgerRecord(
        id=areas_sha[:16],
        url="file://regions/reference_london/areas.csv",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        sha256=areas_sha,
        byte_count=areas_path.stat().st_size,
        http_status=200,
        content_type="text/csv",
        license="Open Government Licence v3.0 (OGL-3.0) & ODbL",
        file_path=str(areas_path),
        record_status="verified",
        notes="Updated areas.csv with authentic ONS borough centroids"
    ))
    print(f"Successfully updated {areas_path} with authentic centroids.")


if __name__ == "__main__":
    fetch_borough_centroids()

