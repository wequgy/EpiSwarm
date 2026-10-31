"""Data contract validation engine for RegionPack files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd
import yaml

from episwarm.importers.templates import CSV_CONTRACTS
from episwarm.packs.region import RegionPack


@dataclass
class ValidationIssue:
    file: str
    field: Optional[str]
    message: str
    severity: str = "ERROR"  # ERROR or WARNING


@dataclass
class ValidationReport:
    is_valid: bool = True
    file_statuses: Dict[str, str] = field(default_factory=dict)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    def summary_table(self) -> str:
        lines = [
            "+---------------------+-----------------+----------+",
            "| File                | Status          | Issues   |",
            "+---------------------+-----------------+----------+"
        ]
        all_files = sorted(set(list(self.file_statuses.keys()) + list(CSV_CONTRACTS.keys()) + ["region.yaml"]))
        for f in all_files:
            status = self.file_statuses.get(f, "MISSING")
            err_count = sum(1 for e in self.errors if e.file == f)
            warn_count = sum(1 for w in self.warnings if w.file == f)
            issue_str = f"{err_count} err, {warn_count} warn" if (err_count or warn_count) else "OK"
            lines.append(f"| {f:<19} | {status:<15} | {issue_str:<8} |")
        lines.append("+---------------------+-----------------+----------+")
        return "\n".join(lines)


def validate_region_pack(region_dir: Path) -> ValidationReport:
    """Validate all tables and metadata within a RegionPack directory."""
    report = ValidationReport()
    region_dir = Path(region_dir)

    yaml_path = region_dir / "region.yaml"
    if not yaml_path.exists():
        report.errors.append(ValidationIssue("region.yaml", None, "Missing region.yaml metadata file"))
        report.file_statuses["region.yaml"] = "MISSING"
        report.is_valid = False
        return report

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        pack = RegionPack(**yaml_data)
        report.file_statuses["region.yaml"] = "VALID"
    except Exception as e:
        report.errors.append(ValidationIssue("region.yaml", None, f"YAML parse/validation error: {e}"))
        report.file_statuses["region.yaml"] = "INVALID"
        report.is_valid = False

    known_area_ids: Set[str] = set()

    # 1. Validate areas.csv
    areas_path = region_dir / "areas.csv"
    if areas_path.exists():
        try:
            df_areas = pd.read_csv(areas_path)
            report.file_statuses["areas.csv"] = _extract_status(df_areas)
            _validate_headers("areas.csv", df_areas, report)

            if "population" in df_areas.columns:
                if (df_areas["population"] < 0).any():
                    report.errors.append(ValidationIssue("areas.csv", "population", "Population contains negative values"))
            if "area_id" in df_areas.columns:
                if df_areas["area_id"].duplicated().any():
                    dups = df_areas["area_id"][df_areas["area_id"].duplicated()].tolist()
                    report.errors.append(ValidationIssue("areas.csv", "area_id", f"Duplicate area_ids found: {dups}"))
                known_area_ids = set(df_areas["area_id"].astype(str))
        except Exception as e:
            report.errors.append(ValidationIssue("areas.csv", None, f"Failed to read areas.csv: {e}"))
            report.file_statuses["areas.csv"] = "ERROR"
    else:
        report.file_statuses["areas.csv"] = "MISSING"
        if yaml_data.get("meta", {}).get("data_level") != "L0":
            report.errors.append(ValidationIssue("areas.csv", None, "areas.csv is mandatory for L1/L2 data levels"))

    # 2. Validate age_structure.csv
    age_path = region_dir / "age_structure.csv"
    if age_path.exists():
        try:
            df_age = pd.read_csv(age_path)
            report.file_statuses["age_structure.csv"] = _extract_status(df_age)
            _validate_headers("age_structure.csv", df_age, report)

            if "share" in df_age.columns:
                if (df_age["share"] < 0).any() or (df_age["share"] > 1.0).any():
                    report.errors.append(ValidationIssue("age_structure.csv", "share", "Shares must be between 0.0 and 1.0"))

                # Check shares sum to ~1.0 per area
                if "area_id" in df_age.columns:
                    grouped = df_age.groupby("area_id")["share"].sum()
                    for aid, total in grouped.items():
                        if abs(total - 1.0) > 0.05:
                            report.warnings.append(ValidationIssue(
                                "age_structure.csv", "share",
                                f"Shares for area '{aid}' sum to {total:.4f} (expected 1.0)"
                            ))
        except Exception as e:
            report.errors.append(ValidationIssue("age_structure.csv", None, f"Failed to read age_structure.csv: {e}"))
    else:
        report.file_statuses["age_structure.csv"] = "MISSING"

    # 3. Validate commute_od.csv
    commute_path = region_dir / "commute_od.csv"
    if commute_path.exists():
        try:
            df_commute = pd.read_csv(commute_path)
            report.file_statuses["commute_od.csv"] = _extract_status(df_commute)
            _validate_headers("commute_od.csv", df_commute, report)

            if known_area_ids:
                if "from_area" in df_commute.columns:
                    unknown = set(df_commute["from_area"].astype(str)) - known_area_ids
                    if unknown:
                        report.warnings.append(ValidationIssue(
                            "commute_od.csv", "from_area",
                            f"Unknown from_area references: {list(unknown)[:5]}"
                        ))
                if "to_area" in df_commute.columns:
                    unknown = set(df_commute["to_area"].astype(str)) - known_area_ids
                    if unknown:
                        report.warnings.append(ValidationIssue(
                            "commute_od.csv", "to_area",
                            f"Unknown to_area references: {list(unknown)[:5]}"
                        ))
        except Exception as e:
            report.errors.append(ValidationIssue("commute_od.csv", None, f"Failed to read commute_od.csv: {e}"))
    else:
        report.file_statuses["commute_od.csv"] = "MISSING"

    # 4. Validate other CSV contracts if present
    for fname, req_cols in CSV_CONTRACTS.items():
        if fname in ("areas.csv", "age_structure.csv", "commute_od.csv"):
            continue
        fpath = region_dir / fname
        if fpath.exists():
            try:
                df = pd.read_csv(fpath)
                report.file_statuses[fname] = _extract_status(df)
                _validate_headers(fname, df, report)
            except Exception as e:
                report.errors.append(ValidationIssue(fname, None, f"Error parsing {fname}: {e}"))
                report.file_statuses[fname] = "ERROR"
        else:
            report.file_statuses[fname] = "MISSING"

    report.is_valid = len(report.errors) == 0
    return report


def _validate_headers(filename: str, df: pd.DataFrame, report: ValidationReport) -> None:
    expected = CSV_CONTRACTS.get(filename, [])
    missing = [c for c in expected if c not in df.columns]
    if missing:
        report.errors.append(ValidationIssue(
            filename, None,
            f"Missing required columns in {filename}: {missing}"
        ))


def _extract_status(df: pd.DataFrame) -> str:
    if "status" in df.columns:
        statuses = df["status"].dropna().unique().tolist()
        if len(statuses) == 1:
            return str(statuses[0]).upper()
        elif len(statuses) > 1:
            return "MIXED"
    return "UNKNOWN"

