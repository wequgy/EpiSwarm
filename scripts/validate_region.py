"""CLI script to validate a RegionPack directory."""

import sys
from pathlib import Path

# Add src to sys.path to allow execution without package install
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from episwarm.importers.validate import validate_region_pack


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path("regions/example_synthetic")

    if not target.exists():
        print(f"Error: Target directory '{target}' does not exist.")
        sys.exit(1)

    print(f"Validating RegionPack at: {target.resolve()}\n")
    report = validate_region_pack(target)

    print(report.summary_table())
    print()

    if report.errors:
        print(f"FAILED with {len(report.errors)} errors:")
        for err in report.errors:
            fld = f" (field: {err.field})" if err.field else ""
            print(f"  [ERROR] {err.file}{fld}: {err.message}")

    if report.warnings:
        print(f"\n{len(report.warnings)} warnings:")
        for warn in report.warnings:
            fld = f" (field: {warn.field})" if warn.field else ""
            print(f"  [WARN]  {warn.file}{fld}: {warn.message}")

    if report.is_valid:
        print("\nSUCCESS: All data contracts and invariants satisfied.")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
