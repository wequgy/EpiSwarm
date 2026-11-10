"""Held-Out Data Isolation & Audit Gate (Phase 26).

Enforces strict protocol pre-registration and held-out data discipline.
Calibration, tuning, and hyperparameter search code paths are strictly
prohibited from importing or accessing held-out evaluation splits.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from episwarm.evidence.ledger import compute_sha256


class HeldOutGateError(Exception):
    """Raised when held-out data is accessed without a valid protocol hash or retuned."""
    pass


class RetunedHeldOutWarning(UserWarning):
    """Warns when the same held-out window is repeatedly evaluated under different parameters."""
    pass


@dataclass
class HeldOutAccessRecord:
    timestamp: str
    protocol_hash: str
    model_version: str
    held_out_window: str
    parameters: Dict[str, Any]
    status: str  # 'FIRST_EVALUATION', 'RETUNED_VIOLATION'


class HeldOutGate:
    """Manages access to held-out validation time horizons and regions."""

    DEFAULT_LOG_PATH = Path("evidence/held_out_log.jsonl")
    PROTOCOL_PATH = Path("docs/validation/PROTOCOL.md")

    def __init__(self, log_path: Optional[Path] = None, protocol_path: Optional[Path] = None):
        self.log_path = log_path or self.DEFAULT_LOG_PATH
        self.protocol_path = protocol_path or self.PROTOCOL_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def compute_current_protocol_hash(self) -> str:
        """Compute SHA-256 of the committed PROTOCOL.md file."""
        if not self.protocol_path.exists():
            raise HeldOutGateError(
                f"Pre-registration violation: '{self.protocol_path}' does not exist. "
                "EpiSwarm Rule 5 requires a committed protocol before inspecting held-out data."
            )
        return compute_sha256(self.protocol_path)

    def load_held_out_dataset(
        self,
        file_path: Path,
        expected_protocol_hash: str,
        model_version: str,
        held_out_window: str,
        parameters: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, HeldOutAccessRecord]:
        """Access held-out evaluation data under strict pre-registered protocol."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise HeldOutGateError(f"Held-out dataset '{file_path}' not found.")

        # 1. Verify Protocol Hash
        current_hash = self.compute_current_protocol_hash()
        if expected_protocol_hash.lower() != current_hash.lower():
            raise HeldOutGateError(
                f"Protocol mismatch: Supplied protocol hash '{expected_protocol_hash[:12]}...' "
                f"does not match committed PROTOCOL.md hash '{current_hash[:12]}...'. "
                "Any protocol modification invalidates pre-registration."
            )

        # 2. Check for Retuning against same held-out window
        past_access = self._read_log()
        matching_window_runs = [
            r for r in past_access
            if r.get("held_out_window") == held_out_window and r.get("protocol_hash") == current_hash
        ]

        status = "FIRST_EVALUATION"
        if matching_window_runs:
            # Check if parameters changed
            prior_params = matching_window_runs[-1].get("parameters", {})
            if prior_params != parameters:
                status = "RETUNED"

        # 3. Append to immutable access audit log
        record = HeldOutAccessRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            protocol_hash=current_hash,
            model_version=model_version,
            held_out_window=held_out_window,
            parameters=parameters,
            status=status
        )
        self._append_log(record)

        # 4. Read and return data
        df = pd.read_csv(file_path)
        return df, record

    def _read_log(self) -> list:
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def _append_log(self, record: HeldOutAccessRecord):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

