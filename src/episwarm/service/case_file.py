"""EpiSwarm Studio v2 - Case File Service and Intake Store.

Manages persistent, versioned Case Files on disk with audit logs,
provenance tracking, attachment storage, and export bundles.
"""

from __future__ import annotations
import copy
import hashlib
import json
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    user: str = "health_authority_officer"
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)


class EvidenceLedgerEntry(BaseModel):
    field_path: str
    evidence_class: str = "assumed"  # user_supplied | sourced | assumed | synthetic
    source: str = "Default Assumption"
    citation: Optional[str] = None
    checksum: Optional[str] = None


class CaseFileManifest(BaseModel):
    id: str
    title: str
    description: str = ""
    author: str = "Regional Health Authority"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    version: int = 1
    locked: bool = False
    locked_run_id: Optional[str] = None
    is_demo: bool = False
    completeness: float = 0.0  # 0.0 to 1.0

    # 8 Guided Intake Sections
    sections: Dict[str, Any] = Field(default_factory=lambda: {
        "area_population": {
            "region_name": "",
            "country": "",
            "admin_level_name": "Borough",
            "total_population": 0,
            "areas": [],
            "age_distribution": {},
            "density_sq_km": 0.0,
            "boundary_type": "schematic",
            "is_complete": False,
        },
        "work_schools": {
            "workplaces": [],
            "schools": [],
            "transit_hubs": [],
            "commute_model": "gravity",
            "commute_matrix": [],
            "is_complete": False,
        },
        "health_system": {
            "hospitals": [],
            "total_acute_beds": 0,
            "total_icu_beds": 0,
            "non_outbreak_occupancy_pct": 0.82,
            "triage_transfer_enabled": True,
            "is_complete": False,
        },
        "disease": {
            "preset_id": "respiratory_generic",
            "name": "Novel Respiratory Pathogen",
            "target_r0": 2.5,
            "incubation_mean_days": 5.1,
            "infectious_mean_days": 4.5,
            "hospitalization_rate_pct": 4.5,
            "icu_rate_pct": 1.2,
            "ifr_pct": 0.65,
            "is_complete": False,
        },
        "behavior": {
            "behavior_mode": "rule",
            "initial_compliance_pct": 75.0,
            "compliance_fatigue_rate": 0.005,
            "rumor_adoption_rate": 0.08,
            "rumor_dispersion_rate": 0.04,
            "trust_in_authorities_pct": 70.0,
            "is_complete": False,
        },
        "measures": {
            "timeline": [],
            "is_complete": False,
        },
        "run_settings": {
            "scale_agents": 3000,
            "replicates": 3,
            "horizon_days": 60,
            "seed": 42,
            "is_complete": True,
        },
        "review": {
            "assumptions_accepted": True,
            "notes": "",
            "is_complete": False,
        }
    })

    evidence_ledger: Dict[str, EvidenceLedgerEntry] = Field(default_factory=dict)
    audit_log: List[AuditEntry] = Field(default_factory=list)
    attached_files: List[str] = Field(default_factory=list)


class CaseFileService:
    def __init__(self, root_dir: str = "case_files"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_preloaded_demos()

    def _get_case_dir(self, case_id: str) -> Path:
        return self.root_dir / case_id

    def _ensure_preloaded_demos(self) -> None:
        """Seed canonical preloaded reference demos if they do not exist."""
        template_path = Path(__file__).resolve().parent.parent.parent.parent / "case_files" / "demos" / "case_reference_wave1.json"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            ref_demo_id = manifest_data["id"]
            ref_dir = self._get_case_dir(ref_demo_id)
            if not ref_dir.exists():
                ref_manifest = CaseFileManifest(**manifest_data)
                self._save_case_file(ref_manifest)

        sandbox_dir = self._get_case_dir("case_sandbox")
        if not sandbox_dir.exists():
            sandbox_manifest = CaseFileManifest(
                id="case_sandbox",
                title="Sandbox Mini-City (2 Areas, Fast Tests)",
                description="Lightweight synthetic 2-borough city for rapid smoke tests and UI walkthroughs.",
                author="EpiSwarm Sandbox",
                is_demo=True,
                completeness=1.0,
                sections={
                    "area_population": {
                        "region_name": "Sandbox Boroughs",
                        "country": "Synthetic",
                        "admin_level_name": "Ward",
                        "total_population": 10000,
                        "areas": [
                            {"id": "area_north", "name": "North Ward", "population": 5000},
                            {"id": "area_south", "name": "South Ward", "population": 5000},
                        ],
                        "age_distribution": {"0-19": 0.25, "20-64": 0.60, "65+": 0.15},
                        "density_sq_km": 1500.0,
                        "boundary_type": "schematic",
                        "is_complete": True,
                    },
                    "work_schools": {
                        "workplaces": [{"name": "Central District", "capacity": 2000}],
                        "schools": [{"name": "Community School", "capacity": 800}],
                        "transit_hubs": [{"name": "Metro Shuttle", "flow": 1200}],
                        "commute_model": "gravity",
                        "commute_matrix": [],
                        "is_complete": True,
                    },
                    "health_system": {
                        "hospitals": [
                            {"name": "Community Clinic North", "acute_beds": 40, "icu_beds": 8},
                            {"name": "Community Clinic South", "acute_beds": 40, "icu_beds": 8},
                        ],
                        "total_acute_beds": 80,
                        "total_icu_beds": 16,
                        "non_outbreak_occupancy_pct": 0.75,
                        "triage_transfer_enabled": True,
                        "is_complete": True,
                    },
                    "disease": {
                        "preset_id": "respiratory_generic",
                        "name": "Generic Respiratory Virus",
                        "target_r0": 2.2,
                        "incubation_mean_days": 4.5,
                        "infectious_mean_days": 4.0,
                        "hospitalization_rate_pct": 3.5,
                        "icu_rate_pct": 0.8,
                        "ifr_pct": 0.4,
                        "is_complete": True,
                    },
                    "behavior": {
                        "behavior_mode": "rule",
                        "initial_compliance_pct": 70.0,
                        "compliance_fatigue_rate": 0.005,
                        "rumor_adoption_rate": 0.08,
                        "rumor_dispersion_rate": 0.04,
                        "trust_in_authorities_pct": 65.0,
                        "is_complete": True,
                    },
                    "measures": {
                        "timeline": [
                            {"day": 10, "action": "mask_mandate", "area": "all", "stringency": 0.7}
                        ],
                        "is_complete": True,
                    },
                    "run_settings": {
                        "scale_agents": 1000,
                        "replicates": 1,
                        "horizon_days": 30,
                        "seed": 42,
                        "is_complete": True,
                    },
                    "review": {
                        "assumptions_accepted": True,
                        "notes": "Fast sandbox testing environment.",
                        "is_complete": True,
                    }
                },
                evidence_ledger={
                    "area_population.total_population": EvidenceLedgerEntry(
                        field_path="area_population.total_population",
                        evidence_class="synthetic",
                        source="Synthetic generator for testing",
                        citation="Internal Benchmark Suite"
                    )
                },
                audit_log=[
                    AuditEntry(action="CREATE_PRELOADED_DEMO", details={"name": "Sandbox Mini-City"})
                ]
            )
            self._save_case_file(sandbox_manifest)

    def _save_case_file(self, manifest: CaseFileManifest) -> None:
        case_dir = self._get_case_dir(manifest.id)
        case_dir.mkdir(parents=True, exist_ok=True)
        manifest.updated_at = time.time()
        file_path = case_dir / "case_file.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)

    def list_case_files(self) -> List[Dict[str, Any]]:
        results = []
        for d in self.root_dir.iterdir():
            if d.is_dir():
                mf_path = d / "case_file.json"
                if mf_path.exists():
                    try:
                        with open(mf_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            results.append({
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "description": data.get("description"),
                                "author": data.get("author"),
                                "updated_at": data.get("updated_at"),
                                "version": data.get("version", 1),
                                "locked": data.get("locked", False),
                                "is_demo": data.get("is_demo", False),
                                "completeness": data.get("completeness", 0.0),
                            })
                    except Exception:
                        continue
        results.sort(key=lambda x: (not x.get("is_demo"), -x.get("updated_at", 0)))
        return results

    def get_case_file(self, case_id: str) -> CaseFileManifest:
        case_dir = self._get_case_dir(case_id)
        mf_path = case_dir / "case_file.json"
        if not mf_path.exists():
            raise FileNotFoundError(f"Case file '{case_id}' not found.")
        with open(mf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CaseFileManifest(**data)

    def create_case_file(self, title: str, description: str = "", author: str = "Regional Health Authority") -> CaseFileManifest:
        case_id = f"case_{int(time.time() * 1000)}"
        manifest = CaseFileManifest(
            id=case_id,
            title=title,
            description=description,
            author=author,
            is_demo=False,
            completeness=0.125,
            audit_log=[
                AuditEntry(user=author, action="CREATE_CASE_FILE", details={"title": title})
            ]
        )
        self._save_case_file(manifest)
        return manifest

    def duplicate_case_file(self, case_id: str, new_title: str) -> CaseFileManifest:
        source = self.get_case_file(case_id)
        new_id = f"case_{int(time.time() * 1000)}"
        new_manifest = source.model_copy(deep=True)
        new_manifest.id = new_id
        new_manifest.title = new_title
        new_manifest.is_demo = False
        new_manifest.locked = False
        new_manifest.locked_run_id = None
        new_manifest.created_at = time.time()
        new_manifest.updated_at = time.time()
        new_manifest.version = 1
        new_manifest.audit_log.append(
            AuditEntry(action="DUPLICATED_FROM", details={"source_id": case_id})
        )
        self._save_case_file(new_manifest)

        # Copy attachments if any
        source_dir = self._get_case_dir(case_id)
        target_dir = self._get_case_dir(new_id)
        for item in source_dir.iterdir():
            if item.is_file() and item.name != "case_file.json":
                shutil.copy2(item, target_dir / item.name)

        return new_manifest

    def lock_version(self, case_id: str, run_id: str) -> CaseFileManifest:
        manifest = self.get_case_file(case_id)
        manifest.locked = True
        manifest.locked_run_id = run_id
        manifest.audit_log.append(
            AuditEntry(action="LOCK_VERSION_FOR_RUN", details={"run_id": run_id, "version": manifest.version})
        )
        self._save_case_file(manifest)
        return manifest

    def update_section(self, case_id: str, section_key: str, data: Dict[str, Any], user: str = "health_authority_officer") -> CaseFileManifest:
        manifest = self.get_case_file(case_id)
        if manifest.locked:
            # Auto-bump version on modification of locked case file
            manifest.version += 1
            manifest.locked = False
            manifest.locked_run_id = None
            manifest.audit_log.append(
                AuditEntry(user=user, action="VERSION_BUMP", details={"new_version": manifest.version, "reason": "Edit on locked file"})
            )

        if section_key not in manifest.sections:
            manifest.sections[section_key] = {}
        manifest.sections[section_key].update(data)
        manifest.sections[section_key]["is_complete"] = True

        # Recompute overall completeness
        complete_count = sum(1 for s in manifest.sections.values() if isinstance(s, dict) and s.get("is_complete"))
        manifest.completeness = round(complete_count / 8.0, 3)

        manifest.audit_log.append(
            AuditEntry(user=user, action=f"UPDATE_SECTION_{section_key.upper()}", details={"keys_updated": list(data.keys())})
        )
        self._save_case_file(manifest)
        return manifest

    def attach_user_csv(self, case_id: str, section_key: str, filename: str, content_bytes: bytes, column_mapping: Dict[str, str], user: str = "health_authority_officer") -> Dict[str, Any]:
        """Save raw user CSV, compute SHA-256 hash, log in ledger as user_supplied, and map records."""
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        case_dir = self._get_case_dir(case_id)
        data_dir = case_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        file_path = data_dir / filename
        with open(file_path, "wb") as f:
            f.write(content_bytes)

        manifest = self.get_case_file(case_id)
        rel_path = f"data/{filename}"
        if rel_path not in manifest.attached_files:
            manifest.attached_files.append(rel_path)

        # Register in evidence ledger
        ledger_key = f"{section_key}.import_{filename}"
        manifest.evidence_ledger[ledger_key] = EvidenceLedgerEntry(
            field_path=ledger_key,
            evidence_class="user_supplied",
            source=f"Uploaded {filename}",
            citation="Direct User CSV Ingestion",
            checksum=sha256
        )

        manifest.audit_log.append(
            AuditEntry(
                user=user,
                action="ATTACH_USER_DATA",
                details={"filename": filename, "checksum": sha256, "column_mapping": column_mapping}
            )
        )
        self._save_case_file(manifest)

        return {
            "status": "success",
            "filename": filename,
            "sha256": sha256,
            "evidence_class": "user_supplied",
            "mapped_columns": column_mapping
        }

    def estimate_parameters(self, region_name: str, population: int) -> Dict[str, Any]:
        """Propose empirical distributions with citations as Class C assumptions for the official."""
        return {
            "age_distribution": {
                "values": {"0-19": 0.22, "20-64": 0.63, "65+": 0.15},
                "evidence_class": "assumed",
                "source": "UN World Population Prospects (Metropolitan Archetype)",
                "citation": "UN Population Division, 2022 Revision"
            },
            "health_system": {
                "acute_beds_per_1000": 2.5,
                "icu_beds_per_1000": 0.25,
                "estimated_acute_beds": int(population * 0.0025),
                "estimated_icu_beds": int(population * 0.00025),
                "non_outbreak_occupancy": 0.82,
                "evidence_class": "assumed",
                "source": "OECD Health Statistics Benchmark Average",
                "citation": "OECD Health at a Glance 2021"
            },
            "work_schools": {
                "commute_flow_model": "gravity",
                "workplace_mean_size": 28,
                "school_mean_class_size": 24,
                "evidence_class": "assumed",
                "source": "Synthesized European/North American commuting gravity model",
                "citation": "EpiSwarm Synthetics Guide 2024"
            },
            "behavior": {
                "initial_compliance": 75.0,
                "compliance_fatigue_rate": 0.004,
                "evidence_class": "assumed",
                "source": "WHO Behavioral Insights Survey Tool",
                "citation": "WHO Regional Office for Europe, Monitoring public perceptions"
            }
        }

    def export_bundle(self, case_id: str) -> Path:
        """Create a complete .zip bundle containing case_file.json, all data attachments, and checksums.sha256."""
        case_dir = self._get_case_dir(case_id)
        if not case_dir.exists():
            raise FileNotFoundError(f"Case file '{case_id}' not found.")

        export_dir = self.root_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / f"{case_id}_export.zip"

        checksums = {}
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(case_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(case_dir)
                    with open(full_p, "rb") as fp:
                        content = fp.read()
                        checksums[str(rel_p).replace("\\", "/")] = hashlib.sha256(content).hexdigest()
                    zf.write(full_p, arcname=str(rel_p))

            # Add manifest checksums
            checksum_text = "\n".join(f"{ch}  {fn}" for fn, ch in sorted(checksums.items()))
            zf.writestr("checksums.sha256", checksum_text)

        return zip_path

