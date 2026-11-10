"""Evidence Loader Gate (Phase 26).

Enforces structural impossibility of loading unverified 'real' data.
Pack loaders and calibration engines query this gate. Any data claiming
empirical or 'real' status without a matching cryptographic ledger entry
is immediately rejected with an IntegrityGateError.
"""

from pathlib import Path
from typing import Union, Optional
import pandas as pd

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord


class IntegrityGateError(Exception):
    """Raised when unverified or fabricated data attempts to enter the simulation or calibration pipeline."""
    pass


def verify_real_dataset(
    file_path: Union[str, Path],
    ledger: Optional[EvidenceLedger] = None
) -> LedgerRecord:
    """Validate that an empirical data file on disk is authenticated in the Evidence Ledger.

    Raises:
        IntegrityGateError: if file is not found, or its cryptographic hash does not
        match any verified record in the ledger.
    """
    path = Path(file_path)
    if not path.exists():
        raise IntegrityGateError(f"Integrity Gate Error: File '{path}' does not exist.")

    ledger = ledger or EvidenceLedger()
    record = ledger.verify_file(path)

    if record is None or record.record_status != "verified":
        raise IntegrityGateError(
            f"Integrity Gate Violation: Dataset '{path.name}' claims 'status: real' "
            f"or empirical provenance, but its SHA-256 digest has NO verified entry "
            f"in the cryptographic Evidence Ledger ({ledger.db_path}). "
            f"Under EpiSwarm Rule 1, unverified or fabricated real data is strictly prohibited."
        )

    return record


def check_dataframe_integrity(
    df: pd.DataFrame,
    source_file: Optional[Union[str, Path]] = None,
    ledger: Optional[EvidenceLedger] = None
) -> None:
    """Check if DataFrame contains 'status: real' rows and verify source file against ledger."""
    if "status" not in df.columns:
        return

    real_mask = df["status"].astype(str).str.lower() == "real"
    if real_mask.any():
        if not source_file:
            raise IntegrityGateError(
                "Integrity Gate Violation: In-memory DataFrame asserts 'status: real' "
                "without an associated physical source file to verify against the Evidence Ledger."
            )
        verify_real_dataset(source_file, ledger=ledger)

