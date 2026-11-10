"""Evidence & Integrity Infrastructure (Phase 26).

Makes data fabrication structurally impossible via cryptographic evidence ledgers,
network-only real data fetchers, and hard loader gates.
"""

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord
from episwarm.evidence.gate import verify_real_dataset, IntegrityGateError

__all__ = [
    "EvidenceLedger",
    "LedgerRecord",
    "verify_real_dataset",
    "IntegrityGateError"
]

