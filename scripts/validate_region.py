"""CLI entrypoint to validate a RegionPack data contract (Phase 20)."""

import argparse
import sys
from pathlib import Path

from episwarm.importers.validate import validate_region_pack


def main():
    parser = argparse.ArgumentParser(description="Validate RegionPack directory against EpiSwarm data contracts.")
    parser.add_argument("region_dir", type=str, help="Path to RegionPack directory (e.g. regions/london)")
    args = parser.parse_args()

    region_path = Path(args.region_dir)
    if not region_path.exists() or not region_path.is_dir():
        print(f"Error: Directory '{args.region_dir}' does not exist or is not a directory.")
        sys.exit(1)

    print(f"Validating RegionPack at: {region_path.resolve()}")
    report = validate_region_pack(region_path)
    print("\n" + report.summary_table())

    if report.errors:
        print("\nERRORS DETECTED:")
        for err in report.errors:
            fld_str = f" in field '{err.field}'" if err.field else ""
            print(f"  [ERROR] {err.file}{fld_str}: {err.message}")

    if report.warnings:
        print("\nWARNINGS:")
        for warn in report.warnings:
            fld_str = f" in field '{warn.field}'" if warn.field else ""
            print(f"  [WARNING] {warn.file}{fld_str}: {warn.message}")

    if report.is_valid:
        print(f"\nSUCCESS: RegionPack '{region_path.name}' passed all data contract validations.")
        sys.exit(0)
    else:
        print(f"\nFAILURE: RegionPack '{region_path.name}' failed contract validation ({len(report.errors)} errors).")
        sys.exit(1)


if __name__ == "__main__":
    main()
