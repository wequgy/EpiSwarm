"""Spot-Check Checklist Generator (Phase 26).

Generates human-auditable spot-check checklists for verified empirical datasets.
Picks 5 deterministic pseudo-random values per dataset for manual verification
against the primary external publisher.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord


def generate_spot_check_checklist(
    dataset_paths: List[Path],
    ledger: Optional[EvidenceLedger] = None,
    samples_per_file: int = 5,
    seed: int = 2026
) -> str:
    """Generate markdown verification checklist table for human audit."""
    ledger = ledger or EvidenceLedger()
    rng = np.random.default_rng(seed)

    lines = [
        "# Empirical Data Spot-Check Verification Checklist",
        "",
        "**Standard**: EpiSwarm Rule 1 & Rule 6 (Evidence Before Claims).",
        "Every empirical dataset must have 5 randomly sampled data points manually checked",
        "against primary source tables by an auditor before calibration or benchmarking.",
        "",
        "| Dataset File | Row Index | Field / Column | Recorded Value | Source URL / Publisher | Auditor Verification Link / Note |",
        "|---|---|---|---|---|---|"
    ]

    for p in dataset_paths:
        p = Path(p)
        if not p.exists():
            continue

        record = ledger.verify_file(p)
        source_url = record.url if record else "UNVERIFIED"

        try:
            df = pd.read_csv(p)
            if len(df) == 0:
                continue

            n_samples = min(samples_per_file, len(df))
            sample_indices = rng.choice(len(df), size=n_samples, replace=False)

            # Exclude provenance columns from spot check
            check_cols = [c for c in df.columns if c not in ("source", "status", "notes")]
            if not check_cols:
                check_cols = list(df.columns)

            for idx in sample_indices:
                col = rng.choice(check_cols)
                val = df.iloc[idx][col]
                lines.append(
                    f"| `{p.name}` | Row {idx} | `{col}` | `{val}` | {source_url} | [ ] Pending Auditor Match |"
                )
        except Exception as e:
            lines.append(f"| `{p.name}` | ERROR | - | - | {source_url} | Error parsing CSV: {e} |")

    lines.append("")
    lines.append("---")
    lines.append("*Checklist generated programmatically from verified Evidence Ledger files.*")
    return "\n".join(lines)

