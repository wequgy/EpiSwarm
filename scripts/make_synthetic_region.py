"""Script and utility to generate example_synthetic region pack."""

import os
import sys
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import yaml
from episwarm.importers.templates import CSV_CONTRACTS, TEMPLATE_EXAMPLES


def create_synthetic_region(output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write region.yaml
    meta = {
        "meta": {
            "name": "example_synthetic",
            "country_iso": "SYN",
            "data_year": 2024,
            "data_level": "L2",
            "area_levels": ["ward", "zone"],
            "contact_country": "SYN",
            "units": {
                "distance": "km",
                "area": "km2",
                "currency": "tokens"
            },
            "notes": "Synthetic benchmark fixture for system testing. Not a real location.",
            "file_levels": {f: "L2" for f in CSV_CONTRACTS.keys()},
            "provenance": {
                "general": {
                    "source": "EpiSwarm Synthetic Generator",
                    "status": "synthetic",
                    "notes": "Generated for test automation and acceptance verification"
                }
            }
        },
        "quick_inputs": {
            "total_population": 110000,
            "num_areas": 2,
            "avg_household_size": 3.8,
            "urban_fraction": 1.0,
            "employment_rate": 0.61,
            "beds_per_1000": 2.0,
            "icu_beds_per_1000": 0.3
        }
    }

    with open(output_dir / "region.yaml", "w", encoding="utf-8") as f:
        yaml.dump(meta, f, sort_keys=False)

    # 2. Write CSV files using TEMPLATE_EXAMPLES
    for fname, headers in CSV_CONTRACTS.items():
        rows = TEMPLATE_EXAMPLES.get(fname, [])
        lines = [",".join(headers)]
        for r in rows:
            line = [str(r.get(h, "")) for h in headers]
            lines.append(",".join(line))
        with open(output_dir / fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    print(f"Synthetic region generated successfully at {output_dir}")


if __name__ == "__main__":
    target = Path("regions/example_synthetic")
    create_synthetic_region(target)
