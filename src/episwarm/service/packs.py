"""Service facade for managing, loading, and validating EpiSwarm Pack assets."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import pandas as pd
from pydantic import ValidationError

from episwarm.importers.validate import validate_region_pack
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.packs.behavior import BehaviorPack
from episwarm.service.models import (
    RegionSummary,
    DiseaseSummary,
    ScenarioSummary,
    BehaviorSummary,
    PackValidationResult,
)


class PacksService:
    """Service facade for reading, listing, and validating domain configuration packs."""

    def __init__(
        self,
        regions_dir: Optional[Path] = None,
        diseases_dir: Optional[Path] = None,
        scenarios_dir: Optional[Path] = None,
        behavior_dir: Optional[Path] = None,
    ):
        self.regions_dir = Path(regions_dir or "regions")
        self.diseases_dir = Path(diseases_dir or "diseases")
        self.scenarios_dir = Path(scenarios_dir or "scenarios")
        self.behavior_dir = Path(behavior_dir or "behavior")

    # --------------------------------------------------------------------------
    # Regions
    # --------------------------------------------------------------------------

    def list_regions(self) -> List[RegionSummary]:
        """List all installed region packs with metadata and availability flags."""
        results: List[RegionSummary] = []
        if not self.regions_dir.exists():
            return results

        for r_dir in sorted(self.regions_dir.iterdir()):
            if not r_dir.is_dir():
                continue

            yaml_path = r_dir / "region.yaml"
            meta: Dict[str, Any] = {}
            if yaml_path.exists():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        meta = data.get("meta", data)
                except Exception:
                    pass

            areas_file = r_dir / "areas.csv"
            num_areas = None
            total_population = None
            if areas_file.exists():
                try:
                    df = pd.read_csv(areas_file)
                    num_areas = len(df)
                    if "population" in df.columns:
                        total_population = int(df["population"].sum())
                except Exception:
                    pass

            results.append(
                RegionSummary(
                    id=r_dir.name,
                    name=meta.get("name", r_dir.name),
                    country_iso=meta.get("country_iso"),
                    data_year=meta.get("data_year"),
                    data_level=meta.get("data_level"),
                    num_areas=num_areas,
                    total_population=total_population,
                    areas_file_exists=areas_file.exists(),
                    contacts_file_exists=(r_dir / "contacts.csv").exists(),
                    commute_file_exists=(r_dir / "commute_od.csv").exists(),
                    observed_cases_exists=(r_dir / "observed_cases.csv").exists(),
                    provenance_status="REAL" if (r_dir / "observed_cases.csv").exists() else "SYNTHETIC",
                    notes=meta.get("notes"),
                )
            )
        return results

    def get_region(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full raw region configuration and table schemas."""
        r_dir = self.regions_dir / region_id
        if not r_dir.exists() or not r_dir.is_dir():
            return None

        yaml_path = r_dir / "region.yaml"
        meta: Dict[str, Any] = {}
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    meta = yaml.safe_load(f) or {}
            except Exception:
                pass

        files = [f.name for f in r_dir.iterdir() if f.is_file()]
        return {
            "id": region_id,
            "directory": str(r_dir),
            "manifest": meta,
            "files": sorted(files),
            "provenance_status": "REAL" if (r_dir / "observed_cases.csv").exists() else "SYNTHETIC",
        }

    def validate_region(self, region_id: str) -> PackValidationResult:
        """Execute contract validation against region pack CSVs and metadata."""
        r_dir = self.regions_dir / region_id
        if not r_dir.exists() or not r_dir.is_dir():
            return PackValidationResult(
                pack_type="region",
                pack_id=region_id,
                is_valid=False,
                errors=[f"Region directory not found: {r_dir}"],
            )

        report = validate_region_pack(r_dir)
        errors = [f"[{e.file}] {e.field or ''}: {e.message}" for e in report.errors]
        warnings = [f"[{w.file}] {w.field or ''}: {w.message}" for w in report.warnings]

        return PackValidationResult(
            pack_type="region",
            pack_id=region_id,
            is_valid=report.is_valid,
            errors=errors,
            warnings=warnings,
            details=report.file_statuses,
        )

    # --------------------------------------------------------------------------
    # Diseases
    # --------------------------------------------------------------------------

    def list_diseases(self) -> List[DiseaseSummary]:
        """List all pathogen configuration packs."""
        results: List[DiseaseSummary] = []
        if not self.diseases_dir.exists():
            return results

        for d_file in sorted(self.diseases_dir.glob("*.yaml")):
            try:
                with open(d_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                trans = data.get("transmission", {})
                states = data.get("states", [])
                
                # Estimate basic metrics from pack
                r0 = trans.get("target_r0")
                incubation = None
                infectious = None
                for st in states:
                    dur = st.get("dwell_time", {})
                    if st.get("role") == "exposed" and "mean_days" in dur:
                        incubation = dur.get("mean_days")
                    elif st.get("role") in ("infectious", "symptomatic") and "mean_days" in dur:
                        infectious = dur.get("mean_days")

                results.append(
                    DiseaseSummary(
                        id=d_file.stem,
                        name=data.get("name", d_file.stem),
                        r0=r0,
                        incubation_days=incubation,
                        infectious_days=infectious,
                        states_count=len(states),
                        has_vulnerability_factors=bool(data.get("vulnerability_factors")),
                        description=data.get("description"),
                    )
                )
            except Exception:
                results.append(
                    DiseaseSummary(
                        id=d_file.stem,
                        name=d_file.stem,
                        description="Error parsing YAML",
                    )
                )
        return results

    def get_disease(self, disease_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full disease configuration data."""
        d_file = self.diseases_dir / f"{disease_id}.yaml"
        if not d_file.exists():
            return None
        with open(d_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_disease(self, disease_id: str) -> PackValidationResult:
        """Validate disease pack structure, transition graph, and reachability."""
        d_file = self.diseases_dir / f"{disease_id}.yaml"
        if not d_file.exists():
            return PackValidationResult(
                pack_type="disease",
                pack_id=disease_id,
                is_valid=False,
                errors=[f"Disease file not found: {d_file}"],
            )

        try:
            with open(d_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            DiseasePack(**data)
            return PackValidationResult(
                pack_type="disease",
                pack_id=disease_id,
                is_valid=True,
                errors=[],
                warnings=[],
                details={"status": "VALID", "states": len(data.get("states", []))},
            )
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return PackValidationResult(
                pack_type="disease",
                pack_id=disease_id,
                is_valid=False,
                errors=errors,
            )
        except Exception as e:
            return PackValidationResult(
                pack_type="disease",
                pack_id=disease_id,
                is_valid=False,
                errors=[str(e)],
            )

    # --------------------------------------------------------------------------
    # Scenarios
    # --------------------------------------------------------------------------

    def list_scenarios(self) -> List[ScenarioSummary]:
        """List all intervention policy scenario packs."""
        results: List[ScenarioSummary] = []
        if not self.scenarios_dir.exists():
            return results

        for s_file in sorted(self.scenarios_dir.glob("*.yaml")):
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                results.append(
                    ScenarioSummary(
                        id=s_file.stem,
                        name=data.get("name", s_file.stem),
                        horizon_days=data.get("horizon_days", 90),
                        behavior_mode=data.get("behavior_mode", "rule"),
                        n_interventions=len(data.get("interventions", [])),
                        description=data.get("description"),
                    )
                )
            except Exception:
                results.append(
                    ScenarioSummary(
                        id=s_file.stem,
                        name=s_file.stem,
                        description="Error parsing YAML",
                    )
                )
        return results

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full scenario configuration data."""
        s_file = self.scenarios_dir / f"{scenario_id}.yaml"
        if not s_file.exists():
            return None
        with open(s_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_scenario(self, scenario_id: str) -> PackValidationResult:
        """Validate scenario pack dates, actions, and schema."""
        s_file = self.scenarios_dir / f"{scenario_id}.yaml"
        if not s_file.exists():
            return PackValidationResult(
                pack_type="scenario",
                pack_id=scenario_id,
                is_valid=False,
                errors=[f"Scenario file not found: {s_file}"],
            )

        try:
            with open(s_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            ScenarioPack(**data)
            return PackValidationResult(
                pack_type="scenario",
                pack_id=scenario_id,
                is_valid=True,
                errors=[],
                warnings=[],
                details={"status": "VALID", "interventions": len(data.get("interventions", []))},
            )
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return PackValidationResult(
                pack_type="scenario",
                pack_id=scenario_id,
                is_valid=False,
                errors=errors,
            )
        except Exception as e:
            return PackValidationResult(
                pack_type="scenario",
                pack_id=scenario_id,
                is_valid=False,
                errors=[str(e)],
            )

    # --------------------------------------------------------------------------
    # Behaviors
    # --------------------------------------------------------------------------

    def list_behaviors(self) -> List[BehaviorSummary]:
        """List all behavior and compliance packs."""
        results: List[BehaviorSummary] = []
        if not self.behavior_dir.exists():
            return results

        for b_file in sorted(self.behavior_dir.glob("*.yaml")):
            try:
                with open(b_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                results.append(
                    BehaviorSummary(
                        id=b_file.stem,
                        name=data.get("name", b_file.stem),
                        context=data.get("context"),
                        rumor_spread_rate=data.get("rumor_spread_rate"),
                        n_rumor_topics=len(data.get("rumor_topics", [])),
                        n_questions=len(data.get("questions", [])),
                    )
                )
            except Exception:
                pass
        return results

    def get_behavior(self, behavior_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full behavior configuration data."""
        b_file = self.behavior_dir / f"{behavior_id}.yaml"
        if not b_file.exists():
            return None
        with open(b_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_behavior(self, behavior_id: str) -> PackValidationResult:
        """Validate behavior pack schema and weights."""
        b_file = self.behavior_dir / f"{behavior_id}.yaml"
        if not b_file.exists():
            return PackValidationResult(
                pack_type="behavior",
                pack_id=behavior_id,
                is_valid=False,
                errors=[f"Behavior file not found: {b_file}"],
            )

        try:
            with open(b_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            BehaviorPack(**data)
            return PackValidationResult(
                pack_type="behavior",
                pack_id=behavior_id,
                is_valid=True,
                errors=[],
                warnings=[],
                details={"status": "VALID", "rumor_topics": len(data.get("rumor_topics", []))},
            )
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return PackValidationResult(
                pack_type="behavior",
                pack_id=behavior_id,
                is_valid=False,
                errors=errors,
            )
        except Exception as e:
            return PackValidationResult(
                pack_type="behavior",
                pack_id=behavior_id,
                is_valid=False,
                errors=[str(e)],
            )
