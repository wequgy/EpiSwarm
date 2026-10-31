"""Quick Region (L0) generator for synthesizing detailed tables from high-level inputs."""

import math
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import yaml

from episwarm.packs.region import L0QuickInputs, RegionMeta, RegionPack, DataLevel


# Standard fallback 4-band age structure (Libin et al. 2020: 0-4, 5-18, 19-64, 65+)
DEFAULT_AGE_STRUCTURE = [
    {"sex": "M", "age_band": "0-4", "share": 0.035},
    {"sex": "F", "age_band": "0-4", "share": 0.035},
    {"sex": "M", "age_band": "5-18", "share": 0.115},
    {"sex": "F", "age_band": "5-18", "share": 0.115},
    {"sex": "M", "age_band": "19-64", "share": 0.310},
    {"sex": "F", "age_band": "19-64", "share": 0.310},
    {"sex": "M", "age_band": "65+", "share": 0.040},
    {"sex": "F", "age_band": "65+", "share": 0.040},
]

# Standard conversational contact matrix (Prem et al. / Libin et al. 2020 UK/Generic baseline)
DEFAULT_CONTACT_MATRIX = [
    {"layer": "all", "age_band_i": "0-4", "age_band_j": "0-4", "contacts_per_day": 3.2},
    {"layer": "all", "age_band_i": "0-4", "age_band_j": "5-18", "contacts_per_day": 1.1},
    {"layer": "all", "age_band_i": "0-4", "age_band_j": "19-64", "contacts_per_day": 4.5},
    {"layer": "all", "age_band_i": "0-4", "age_band_j": "65+", "contacts_per_day": 0.7},
    {"layer": "all", "age_band_i": "5-18", "age_band_j": "5-18", "contacts_per_day": 8.1},
    {"layer": "all", "age_band_i": "5-18", "age_band_j": "19-64", "contacts_per_day": 4.8},
    {"layer": "all", "age_band_i": "5-18", "age_band_j": "65+", "contacts_per_day": 0.8},
    {"layer": "all", "age_band_i": "19-64", "age_band_j": "19-64", "contacts_per_day": 8.9},
    {"layer": "all", "age_band_i": "19-64", "age_band_j": "65+", "contacts_per_day": 1.4},
    {"layer": "all", "age_band_i": "65+", "age_band_j": "65+", "contacts_per_day": 2.5},
]


class QuickRegionBuilder:
    """Synthesizes an L1/L2 compatible RegionPack directory from L0 quick inputs."""

    def __init__(self, meta: RegionMeta, inputs: L0QuickInputs):
        self.meta = meta
        self.inputs = inputs

    def generate_all(self, output_dir: Path) -> None:
        """Generate all required CSVs and updated region.yaml into output_dir."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        num_areas = self.inputs.num_areas
        total_pop = self.inputs.total_population
        avg_hh_size = self.inputs.avg_household_size

        # 1. Generate areas.csv
        # Partition population across areas with slight synthetic dispersion
        base_pop = total_pop // num_areas
        remainder = total_pop % num_areas
        area_pops = [base_pop + (1 if i < remainder else 0) for i in range(num_areas)]

        # Synthetic grid layout for centroids
        grid_dim = math.ceil(math.sqrt(num_areas))
        areas_rows = []
        for i in range(num_areas):
            aid = f"A{i+1:02d}"
            gx = i % grid_dim
            gy = i // grid_dim
            # synthetic coordinates centered near lat 0.0, lon 0.0 or reference
            lat = round(gx * 0.05, 4)
            lon = round(gy * 0.05, 4)
            hh = max(1, int(round(area_pops[i] / avg_hh_size)))
            area_km2 = round(max(0.5, area_pops[i] / 8000.0), 2)  # assumed 8000/km2 density

            areas_rows.append({
                "area_id": aid,
                "name": f"Area {i+1}",
                "level": self.meta.area_levels[0],
                "parent_id": f"Z{(i // 4) + 1}",
                "population": area_pops[i],
                "households": hh,
                "area_km2": area_km2,
                "lat": lat,
                "lon": lon,
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
        pd.DataFrame(areas_rows).to_csv(output_dir / "areas.csv", index=False)

        # 2. Generate age_structure.csv
        age_rows = []
        for r in DEFAULT_AGE_STRUCTURE:
            age_rows.append({
                "area_id": "ALL",
                "sex": r["sex"],
                "age_band": r["age_band"],
                "share": r["share"],
                "source": "L0_QuickRegionBuilder (Libin et al. 2020)",
                "status": "assumed"
            })
        pd.DataFrame(age_rows).to_csv(output_dir / "age_structure.csv", index=False)

        # 3. Generate employment.csv
        emp_rows = []
        for i, a in enumerate(areas_rows):
            jobs = int(round(a["population"] * self.inputs.employment_rate))
            emp_rows.append({
                "area_id": a["area_id"],
                "jobs": jobs,
                "employment_rate": round(self.inputs.employment_rate, 3),
                "sector_shares": "services:0.75,manufacturing:0.25",
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
        pd.DataFrame(emp_rows).to_csv(output_dir / "employment.csv", index=False)

        # 4. Generate venues.csv
        venue_rows = []
        schools_total = self.inputs.num_schools or max(1, total_pop // 2500)
        markets_total = self.inputs.num_markets or max(1, total_pop // 5000)
        schools_per_area = max(1, schools_total // num_areas)
        markets_per_area = max(1, markets_total // num_areas)

        for a in areas_rows:
            # Schools
            venue_rows.append({
                "area_id": a["area_id"],
                "venue_type": "school",
                "count": schools_per_area,
                "mean_size": 350,
                "size_sd": 75,
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
            # Workplaces (mean size ~25 workers)
            workplaces = max(1, int(round(a["population"] * self.inputs.employment_rate / 25)))
            venue_rows.append({
                "area_id": a["area_id"],
                "venue_type": "workplace",
                "count": workplaces,
                "mean_size": 25,
                "size_sd": 15,
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
            # Markets
            venue_rows.append({
                "area_id": a["area_id"],
                "venue_type": "market",
                "count": markets_per_area,
                "mean_size": 200,
                "size_sd": 50,
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
        pd.DataFrame(venue_rows).to_csv(output_dir / "venues.csv", index=False)

        # 5. Generate commute_od.csv using gravity formulation (Libin et al. 2020)
        commute_rows = []
        coords = np.array([[a["lat"], a["lon"]] for a in areas_rows])
        for i, a_from in enumerate(areas_rows):
            weights = []
            for j, a_to in enumerate(areas_rows):
                if i == j:
                    # High internal retention (default 65% stay within area)
                    weights.append(3.0)
                else:
                    dist = max(0.5, np.linalg.norm(coords[i] - coords[j]) * 111.0)  # km approx
                    # Gravity T_ij ~ Jobs_j / dist^1.5
                    w = (areas_rows[j]["population"] * self.inputs.employment_rate) / (dist ** 1.5)
                    weights.append(w)
            weights = np.array(weights)
            shares = weights / weights.sum()
            for j, share in enumerate(shares):
                commute_rows.append({
                    "from_area": a_from["area_id"],
                    "to_area": areas_rows[j]["area_id"],
                    "share": round(float(share), 4),
                    "source": "L0_Gravity_Model (Libin et al. 2020)",
                    "status": "assumed"
                })
        pd.DataFrame(commute_rows).to_csv(output_dir / "commute_od.csv", index=False)

        # 6. Generate contacts.csv
        contact_rows = []
        for c in DEFAULT_CONTACT_MATRIX:
            contact_rows.append({
                "layer": c["layer"],
                "age_band_i": c["age_band_i"],
                "age_band_j": c["age_band_j"],
                "contacts_per_day": c["contacts_per_day"],
                "source": "Prem et al. 2021 / Libin et al. 2020",
                "status": "assumed"
            })
        pd.DataFrame(contact_rows).to_csv(output_dir / "contacts.csv", index=False)

        # 7. Generate hospitals.csv and capacity.csv
        hosp_rows = []
        cap_rows = []
        total_gen_beds = max(1, int(round((total_pop / 1000.0) * self.inputs.beds_per_1000)))
        total_icu_beds = max(1, int(round((total_pop / 1000.0) * self.inputs.icu_beds_per_1000)))
        gen_per_area = max(1, total_gen_beds // num_areas)
        icu_per_area = max(1, total_icu_beds // num_areas)

        for i, a in enumerate(areas_rows):
            hid = f"H{i+1:02d}"
            hosp_rows.append({
                "hospital_id": hid,
                "name": f"Hospital {a['name']}",
                "area_id": a["area_id"],
                "lat": a["lat"],
                "lon": a["lon"],
                "sector": "government" if i % 2 == 0 else "private",
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
            cap_rows.append({
                "date": "static",
                "hospital_id": hid,
                "category": "general",
                "nominal": gen_per_area,
                "effective_low": int(round(gen_per_area * 0.8)),
                "effective_high": int(round(gen_per_area * 1.1)),
                "medicine_stock": "adequate",
                "upper_cap_extra": int(round(gen_per_area * 0.25)),
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
            cap_rows.append({
                "date": "static",
                "hospital_id": hid,
                "category": "icu",
                "nominal": icu_per_area,
                "effective_low": int(round(icu_per_area * 0.75)),
                "effective_high": int(round(icu_per_area * 1.1)),
                "medicine_stock": "adequate",
                "upper_cap_extra": int(round(icu_per_area * 0.3)),
                "source": "L0_QuickRegionBuilder",
                "status": "assumed"
            })
        pd.DataFrame(hosp_rows).to_csv(output_dir / "hospitals.csv", index=False)
        pd.DataFrame(cap_rows).to_csv(output_dir / "capacity.csv", index=False)

        # 8. Generate comorbidity.csv
        comorb_rows = [
            {"age_band": "19-64", "sex": "M", "condition": "hypertension", "prevalence": 0.20, "source": "L0_Default", "status": "assumed"},
            {"age_band": "19-64", "sex": "F", "condition": "hypertension", "prevalence": 0.18, "source": "L0_Default", "status": "assumed"},
            {"age_band": "65+", "sex": "M", "condition": "diabetes", "prevalence": 0.30, "source": "L0_Default", "status": "assumed"},
            {"age_band": "65+", "sex": "F", "condition": "diabetes", "prevalence": 0.28, "source": "L0_Default", "status": "assumed"}
        ]
        pd.DataFrame(comorb_rows).to_csv(output_dir / "comorbidity.csv", index=False)

        # 9. Generate sanitation.csv
        san_rows = []
        for a in areas_rows:
            san_rows.append({
                "area_id": a["area_id"],
                "water_access_score": 0.85,
                "drainage_coverage": 0.80,
                "waste_collection_frequency": 0.90,
                "source": "L0_Default",
                "status": "assumed"
            })
        pd.DataFrame(san_rows).to_csv(output_dir / "sanitation.csv", index=False)

        # 10. Update region.yaml metadata
        updated_meta = self.meta.model_dump()
        updated_meta["data_level"] = "L0"
        pack_dict = {
            "meta": updated_meta,
            "quick_inputs": self.inputs.model_dump()
        }
        with open(output_dir / "region.yaml", "w", encoding="utf-8") as f:
            yaml.dump(pack_dict, f, sort_keys=False)

