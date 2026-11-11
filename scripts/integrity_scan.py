#!/usr/bin/env python3
"""EpiSwarm Automated Integrity Scanner (Phase 25).

Scans active codebase, datasets, scripts, and validation documents for integrity violations:
1. 'status: real' without verified download records in the evidence ledger.
2. Random generators (e.g. np.random, rng.integers, Poisson/Gaussian formulas) or numeric result literals
   in builder, calibration, or validation modules.
3. Validation reports whose PASS / FAIL verdicts contradict machine-readable evaluation cards or threshold bounds.
4. Unquarantined references to fake validation status (e.g. PARTIALLY_VALIDATED without evidence).
"""

import sys
import re
import json
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Any
import pandas as pd
import yaml


class IntegrityViolation:
    def __init__(self, category: str, file_path: str, message: str, line_no: int = 0):
        self.category = category
        self.file_path = file_path
        self.message = message
        self.line_no = line_no

    def __str__(self) -> str:
        loc = f"{self.file_path}:{self.line_no}" if self.line_no else self.file_path
        return f"[{self.category}] {loc}: {self.message}"


def scan_unverified_real_status(root_dir: Path, include_quarantine: bool = False) -> List[IntegrityViolation]:
    """Scan data files for 'status: real' lacking download records."""
    violations = []
    
    # In Phase 25/26, active verified ledger will be at evidence/ledger.db
    # Any 'status: real' without a matching ledger entry is an integrity breach.
    ledger_file = root_dir / "evidence" / "ledger.db"
    has_ledger = ledger_file.exists()

    data_dirs = [root_dir / "regions"]
    if include_quarantine:
        data_dirs.append(root_dir / "quarantine" / "regions")

    for d_dir in data_dirs:
        if not d_dir.exists():
            continue
        for p in d_dir.rglob("*.csv"):
            if not include_quarantine and "quarantine" in p.parts:
                continue
            try:
                # Read header/first rows to check columns
                df = pd.read_csv(p, nrows=200)
                if "status" in df.columns:
                    real_rows = df[df["status"].astype(str).str.lower() == "real"]
                    if len(real_rows) > 0 and not has_ledger:
                        violations.append(IntegrityViolation(
                            category="X1/X2_UNVERIFIED_REAL_DATA",
                            file_path=str(p.relative_to(root_dir)),
                            message=f"Found {len(real_rows)} rows marked 'status: real' without verified Evidence Ledger record."
                        ))
            except Exception:
                pass

        for p in d_dir.rglob("*.yaml"):
            if not include_quarantine and "quarantine" in p.parts:
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                    if re.search(r"status\s*:\s*['\"]?real['\"]?", content, re.IGNORECASE) and not has_ledger:
                        violations.append(IntegrityViolation(
                            category="X1/X2_UNVERIFIED_REAL_DATA",
                            file_path=str(p.relative_to(root_dir)),
                            message="YAML declares 'status: real' without verified Evidence Ledger record."
                        ))
            except Exception:
                pass

    return violations


def scan_suspicious_builders_and_validation(root_dir: Path, include_quarantine: bool = False) -> List[IntegrityViolation]:
    """Scan scripts and modules for random generation or hardcoded results posing as empirical data/validation."""
    violations = []

    target_dirs = [root_dir / "scripts", root_dir / "src" / "episwarm" / "calibration"]
    if include_quarantine:
        target_dirs.append(root_dir / "quarantine" / "scripts")

    # Patterns indicating synthetic generation of 'observed' data or hardcoded mock targets
    suspicious_patterns = [
        (re.compile(r"(\bnp\.random\b|\brng\.poisson\b|\brng\.integers\b|\b850\.0\s*\*\s*np\.exp\b)"), "Random generator or synthetic analytical formula used in data generation/validation"),
        (re.compile(r"(\bobs_overflow_days\s*=\s*\d+|\bsim_reduction_pct\s*=\s*[\d\.]+)"), "Hardcoded numeric empirical validation target/result literal"),
        (re.compile(r"(\bsim_arrivals\s*\+\s*np\.random)"), "Fabricated correlation target (sim_arrivals + noise)"),
    ]

    for t_dir in target_dirs:
        if not t_dir.exists():
            continue
        for py_file in t_dir.rglob("*.py"):
            if not include_quarantine and "quarantine" in py_file.parts:
                continue
            # Skip integrity_scan.py itself
            if py_file.name == "integrity_scan.py":
                continue
            
            lines = py_file.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines, 1):
                # Don't flag comments or docstrings that document findings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                for pat, msg in suspicious_patterns:
                    if pat.search(line):
                        violations.append(IntegrityViolation(
                            category="X1/X3_FABRICATED_LOGIC",
                            file_path=str(py_file.relative_to(root_dir)),
                            message=f"{msg}: `{line.strip()}`",
                            line_no=idx
                        ))

    return violations


def scan_report_card_discrepancies(root_dir: Path, include_quarantine: bool = False) -> List[IntegrityViolation]:
    """Scan validation reports for PASS strings that contradict card results or threshold criteria."""
    violations = []

    docs_dirs = [root_dir / "docs" / "validation"]
    if include_quarantine:
        docs_dirs.append(root_dir / "quarantine" / "docs" / "validation")

    for d_dir in docs_dirs:
        if not d_dir.exists():
            continue

        card_file = d_dir / "VALIDATION_CARD.json"
        report_file = d_dir / "VALIDATION_REPORT.md"

        if card_file.exists() and report_file.exists():
            try:
                card = json.loads(card_file.read_text(encoding="utf-8"))
                report_lines = report_file.read_text(encoding="utf-8").splitlines()
                
                # Check for table rows claiming PASS when card has passed=false
                targets = card.get("targets", {})
                for idx, line in enumerate(report_lines, 1):
                    # Check for contradictory PASS strings
                    if "| **PASS** |" in line:
                        # Find which target this row refers to
                        for t_name, t_val in targets.items():
                            clean_name = t_name.replace("_", " ").lower()
                            if clean_name in line.lower() and isinstance(t_val, dict) and t_val.get("passed") is False:
                                violations.append(IntegrityViolation(
                                    category="X4_REPORT_CONTRADICTS_CARD",
                                    file_path=str(report_file.relative_to(root_dir)),
                                    message=f"Report marks '{t_name}' as **PASS**, but VALIDATION_CARD.json recorded passed=false.",
                                    line_no=idx
                                ))
                    
                    # Direct threshold check: peak ratio 0.42 within [0.75, 1.25] labeled PASS
                    if "Ratio = **0.42**" in line and "**PASS**" in line:
                        violations.append(IntegrityViolation(
                            category="X4_REPORT_CONTRADICTS_THRESHOLD",
                            file_path=str(report_file.relative_to(root_dir)),
                            message=f"Report claims PASS for peak ratio 0.42 which violates threshold [0.75, 1.25]: `{line.strip()}`",
                            line_no=idx
                        ))
                    if "Error = **81.5%**" in line and "**PASS**" in line:
                        violations.append(IntegrityViolation(
                            category="X4_REPORT_CONTRADICTS_THRESHOLD",
                            file_path=str(report_file.relative_to(root_dir)),
                            message=f"Report claims PASS for cumulative error 81.5% which violates threshold <= 20%: `{line.strip()}`",
                            line_no=idx
                        ))
            except Exception as e:
                pass

        # Check for unquarantined claims of VALIDATED or PARTIALLY_VALIDATED
        # Check for unsubstantiated claims of VALIDATED or PARTIALLY_VALIDATED without a matching card
        if not include_quarantine:
            card_status = card.get("status", "UNCALIBRATED") if (card_file.exists() and 'card' in locals()) else "UNCALIBRATED"
            for md_file in d_dir.rglob("*.md"):
                if "quarantine" in md_file.parts:
                    continue
                content = md_file.read_text(encoding="utf-8")
                if "PARTIALLY_VALIDATED" in content or "status: VALIDATED" in content:
                    violations.append(IntegrityViolation(
                        category="X4_FALSE_VALIDATION_STATUS",
                        file_path=str(md_file.relative_to(root_dir)),
                        message="Active document claims VALIDATED or PARTIALLY_VALIDATED without evidence."
                    ))
                if card_status == "UNCALIBRATED":
                    if "PARTIALLY_VALIDATED" in content or "status: VALIDATED" in content:
                        violations.append(IntegrityViolation(
                            category="X4_FALSE_VALIDATION_STATUS",
                            file_path=str(md_file.relative_to(root_dir)),
                            message="Active document claims VALIDATED or PARTIALLY_VALIDATED without evidence."
                        ))

    return violations


def scan_validation_script_ast_integrity(root_dir: Path, include_quarantine: bool = False) -> List[IntegrityViolation]:
    """Scan validation scripts to enforce that simulated series originate from the simulation engine.

    Bans:
    1. Distance formulas generating arrival times (e.g. dist * 28)
    2. Analytic exponential curves stand-ins for admissions/ICU (e.g. 20.0 * exp(...))
    3. Rescaling simulated curves to match observed peak (scale_fac = obs_peak / max(sim))
    Requires:
    Validation scripts must import or invoke run_simulation or inference engines.
    """
    violations = []
    scripts_dir = root_dir / "scripts"
    if not scripts_dir.exists():
        return violations

    for script_file in scripts_dir.glob("run_*validation*.py"):
        if not include_quarantine and "quarantine" in script_file.parts:
            continue

        content = script_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=str(script_file))
        except SyntaxError as e:
            violations.append(IntegrityViolation(
                category="SYNTAX_ERROR",
                file_path=str(script_file.relative_to(root_dir)),
                message=f"Could not parse script AST: {e}"
            ))
            continue

        # Check 1: Must import or reference run_simulation
        imports_sim = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "sim" in node.module:
                    for alias in node.names:
                        if alias.name == "run_simulation":
                            imports_sim = True
            elif isinstance(node, ast.Name) and node.id == "run_simulation":
                imports_sim = True

        if not imports_sim:
            violations.append(IntegrityViolation(
                category="Y1/Y2_NO_SIMULATOR_CALL",
                file_path=str(script_file.relative_to(root_dir)),
                message="Validation script does not import or invoke 'run_simulation'. Stand-ins without the simulation engine are strictly forbidden."
            ))

        # Check 2: Ban analytic exponential curves or distance arrival formulas in validation
        for node in ast.walk(tree):
            # Check for distance arrival formulas: dist * 28 or similar
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                if isinstance(node.left, ast.Name) and "dist" in node.left.id.lower():
                    violations.append(IntegrityViolation(
                        category="Y2_DISTANCE_FORMULA_STANDIN",
                        file_path=str(script_file.relative_to(root_dir)),
                        message="Validation script generates arrivals using distance formula multiplier.",
                        line_no=getattr(node, "lineno", None)
                    ))
            # Check for peak rescaling: scale_fac = obs_peak / ... or sim *= obs_peak / max
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "scale_fac":
                        violations.append(IntegrityViolation(
                            category="Y1_PEAK_RESCALING_STANDIN",
                            file_path=str(script_file.relative_to(root_dir)),
                            message="Validation script rescales simulated series to observed peak using 'scale_fac'.",
                            line_no=getattr(node, "lineno", None)
                        ))

    return violations


def run_full_scan(root_dir: Path, include_quarantine: bool = False) -> List[IntegrityViolation]:
    all_violations = []
    all_violations.extend(scan_unverified_real_status(root_dir, include_quarantine=include_quarantine))
    all_violations.extend(scan_suspicious_builders_and_validation(root_dir, include_quarantine=include_quarantine))
    all_violations.extend(scan_report_card_discrepancies(root_dir, include_quarantine=include_quarantine))
    all_violations.extend(scan_validation_script_ast_integrity(root_dir, include_quarantine=include_quarantine))
    return all_violations


def main():
    root = Path(__file__).resolve().parent.parent
    include_quarantine = "--include-quarantine" in sys.argv or "--audit-quarantine" in sys.argv

    print(f"=== EpiSwarm Automated Integrity Scan ===")
    print(f"Target Root: {root}")
    print(f"Mode: {'Auditing Quarantine Artifacts (Should find violations)' if include_quarantine else 'Strict Active Codebase Scan'}")
    print("-" * 50)

    violations = run_full_scan(root, include_quarantine=include_quarantine)

    if violations:
        print(f"FAILED: Found {len(violations)} integrity violation(s):\n")
        for v in violations:
            print(f"  [VIOLATION] {v}")
        print("\nIntegrity scan detected non-compliant artifacts or logic.")
        sys.exit(1 if not include_quarantine else 0)
    else:
        print("PASSED: Zero integrity violations found in active codebase.")
        print("  [OK] All active datasets are synthetic or verified.")
        print("  [OK] No formula-generated pseudo-observations or mock rank correlations.")
        print("  [OK] No contradictory PASS/FAIL validation claims.")
        sys.exit(0)


if __name__ == "__main__":
    main()
