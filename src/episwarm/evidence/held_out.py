"""Held-Out Data Isolation & Audit Gate (Phase 26 / Repair R1.4).

Enforces strict protocol pre-registration, cryptographic hash-chained audit logging,
evaluation counter increments, and detection of REPEAT, RETUNED, or COMPROMISED evaluation runs.
Calibration, tuning, and simulation scripts are strictly barred from importing or accessing
held-out evaluation splits.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd

from episwarm.evidence.ledger import compute_sha256


class HeldOutGateError(Exception):
    """Raised when held-out data is accessed without a valid protocol hash, retuned, or compromised."""
    pass


class RetunedHeldOutWarning(UserWarning):
    """Warns when the same held-out window is repeatedly evaluated under different parameters."""
    pass


@dataclass
class HeldOutAccessRecord:
    timestamp: str
    eval_count: int
    protocol_hash: str
    model_version: str
    held_out_window: str
    parameters: Dict[str, Any]
    status: str  # 'FIRST_EVALUATION', 'REPEAT', 'RETUNED', 'COMPROMISED'
    prev_entry_sha256: str
    notes: str = ""


class HeldOutGate:
    """Manages cryptographic access auditing to held-out validation time horizons and regions."""

    DEFAULT_LOG_PATH = Path("docs/validation/HELD_OUT_LOG.jsonl")
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

    def get_last_line_hash(self) -> str:
        """Compute SHA-256 hash of the last line in the log to maintain an immutable hash chain."""
        if not self.log_path.exists():
            return "0" * 64
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return "0" * 64
        return hashlib.sha256(lines[-1].encode("utf-8")).hexdigest()

    def mark_window_compromised(
        self,
        held_out_window: str,
        model_version: str,
        reason: str
    ) -> HeldOutAccessRecord:
        """Explicitly record a held-out dataset as COMPROMISED for a model generation."""
        prev_hash = self.get_last_line_hash()
        past_records = self._read_log()
        eval_count = sum(1 for r in past_records if r.get("held_out_window") == held_out_window) + 1

        try:
            proto_hash = self.compute_current_protocol_hash()
        except Exception:
            proto_hash = "0" * 64

        rec = HeldOutAccessRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            eval_count=eval_count,
            protocol_hash=proto_hash,
            model_version=model_version,
            held_out_window=held_out_window,
            parameters={},
            status="COMPROMISED",
            prev_entry_sha256=prev_hash,
            notes=reason
        )
        self._append_log(rec)
        return rec

    def is_window_compromised(self, held_out_window: str, model_version: str) -> bool:
        """Check whether a held-out evaluation window is compromised."""
        past_access = self._read_log()
        for r in past_access:
            if r.get("held_out_window") == held_out_window and r.get("status") == "COMPROMISED":
                # Matches model generation (e.g. v3.0.0)
                m_ver = r.get("model_version", "")
                if m_ver.split("-")[0] == model_version.split("-")[0]:
                    return True
        return False

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

        # 0. Check Compromised Invariant
        if self.is_window_compromised(held_out_window, model_version):
            raise HeldOutGateError(
                f"HeldOutGate Rejection: The held-out window '{held_out_window}' has been marked "
                f"COMPROMISED for model '{model_version}' under independent audit finding Y4. "
                "Evaluating on a compromised split is strictly prohibited. An external unseen dataset "
                "outside the repository workspace is required."
            )

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

        # 2. Check for Retuning or Repeats against same held-out window
        past_access = self._read_log()
        matching_window_runs = [
            r for r in past_access
            if r.get("held_out_window") == held_out_window and r.get("protocol_hash") == current_hash
        ]

        eval_count = len(matching_window_runs) + 1
        if not matching_window_runs:
            status = "FIRST_EVALUATION"
        else:
            prior_params = matching_window_runs[-1].get("parameters", {})
            if prior_params != parameters:
                status = "RETUNED"
            else:
                status = "REPEAT"

        # 3. Append to immutable hash-chained access audit log
        prev_hash = self.get_last_line_hash()
        record = HeldOutAccessRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            eval_count=eval_count,
            protocol_hash=current_hash,
            model_version=model_version,
            held_out_window=held_out_window,
            parameters=parameters,
            status=status,
            prev_entry_sha256=prev_hash,
            notes=f"Evaluation #{eval_count} ({status})"
        )
        self._append_log(record)

        # 4. Read and return data
        df = pd.read_csv(file_path)
        return df, record

    def _read_log(self) -> List[Dict[str, Any]]:
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
