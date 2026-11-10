"""Cryptographic Evidence Ledger (Phase 26).

Maintains an append-only, checksummed database of all external data acquired
for empirical calibration and regional benchmarking.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from typing import List, Optional, Dict, Any, Union
import pandas as pd


@dataclass
class LedgerRecord:
    id: str  # Hash or unique identifier
    url: str
    retrieved_at: str  # ISO 8601 UTC
    sha256: str
    byte_count: int
    http_status: int
    content_type: str
    license: str
    file_path: str
    record_status: str = "verified"  # 'verified', 'quarantined', 'deprecated'
    notes: str = ""


def compute_sha256(file_path: Path) -> str:
    """Compute standard SHA-256 digest of a file using chunked binary reading."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class EvidenceLedger:
    """SQLite-backed Evidence Ledger enforcing immutable record of empirical downloads."""

    DEFAULT_DB_PATH = Path("evidence/ledger.db")

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_records (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    sha256 TEXT NOT NULL UNIQUE,
                    byte_count INTEGER NOT NULL,
                    http_status INTEGER NOT NULL,
                    content_type TEXT,
                    license TEXT,
                    file_path TEXT NOT NULL,
                    record_status TEXT NOT NULL DEFAULT 'verified',
                    notes TEXT
                );
            """)
            conn.commit()

    def add_record(self, record: LedgerRecord) -> None:
        """Insert a verified download record into the ledger."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evidence_records (
                    id, url, retrieved_at, sha256, byte_count, http_status,
                    content_type, license, file_path, record_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.url,
                record.retrieved_at,
                record.sha256,
                record.byte_count,
                record.http_status,
                record.content_type,
                record.license,
                record.file_path,
                record.record_status,
                record.notes
            ))
            conn.commit()

    def get_by_sha256(self, sha256: str) -> Optional[LedgerRecord]:
        """Lookup a record by exact SHA-256 hash."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM evidence_records WHERE sha256 = ? AND record_status = 'verified'",
                (sha256.lower(),)
            )
            row = cur.fetchone()
            if row:
                return LedgerRecord(**dict(row))
        return None

    def get_by_url(self, url: str) -> Optional[LedgerRecord]:
        """Lookup the latest verified record for a source URL."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM evidence_records WHERE url = ? AND record_status = 'verified' ORDER BY retrieved_at DESC LIMIT 1",
                (url,)
            )
            row = cur.fetchone()
            if row:
                return LedgerRecord(**dict(row))
        return None

    def verify_file(self, file_path: Path) -> Optional[LedgerRecord]:
        """Verify that a physical file on disk matches a verified ledger entry."""
        if not file_path.exists() or not file_path.is_file():
            return None
        file_sha256 = compute_sha256(file_path)
        return self.get_by_sha256(file_sha256)

    def list_records(self, status: str = "verified") -> List[LedgerRecord]:
        """List all records with matching status."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM evidence_records WHERE record_status = ? ORDER BY retrieved_at ASC",
                (status,)
            )
            return [LedgerRecord(**dict(r)) for r in cur.fetchall()]

    def export_parquet(self, output_path: Path) -> Path:
        """Export ledger contents to Parquet for immutable archival audit."""
        records = self.list_records(status="verified")
        data = [asdict(r) for r in records]
        df = pd.DataFrame(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        return output_path
