"""Cryptographic Evidence Ledger (Phase 26 & Repair R1).

Maintains an append-only, checksummed database of all external data acquired
for empirical calibration and regional benchmarking. Supports:
1. Raw download records (HTTP status, URL, license, SHA-256).
2. Derived table records (parent download IDs, transform script & hash, null http_status).
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import List, Optional, Dict, Any, Union, Tuple
import pandas as pd


@dataclass
class LedgerRecord:
    id: str  # Hash or unique identifier
    url: str
    retrieved_at: str  # ISO 8601 UTC
    sha256: str
    byte_count: int
    http_status: Optional[int]
    content_type: str
    license: str
    file_path: str
    record_status: str = "verified"  # 'verified', 'quarantined', 'deprecated'
    notes: str = ""
    record_type: str = "download"  # 'download' or 'derived'
    parent_ids: Optional[str] = None  # JSON string of raw parent SHA-256 IDs
    transform_script: Optional[str] = None  # Script that generated this derived file
    transform_script_sha256: Optional[str] = None  # SHA-256 of the transform script


def compute_sha256(file_path: Path) -> str:
    """Compute standard SHA-256 digest of a file using chunked binary reading."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class EvidenceLedger:
    """SQLite-backed Evidence Ledger enforcing immutable record of empirical downloads & derivations."""

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
                    http_status INTEGER,
                    content_type TEXT,
                    license TEXT,
                    file_path TEXT NOT NULL,
                    record_status TEXT NOT NULL DEFAULT 'verified',
                    notes TEXT,
                    record_type TEXT NOT NULL DEFAULT 'download',
                    parent_ids TEXT,
                    transform_script TEXT,
                    transform_script_sha256 TEXT
                );
            """)
            # Check for existing table schema migrations
            cur = conn.execute("PRAGMA table_info(evidence_records);")
            col_info = {row["name"]: dict(row) for row in cur.fetchall()}
            
            # If http_status was created with NOT NULL constraint, migrate to nullable
            if col_info.get("http_status", {}).get("notnull") == 1:
                conn.execute("""
                    CREATE TABLE evidence_records_migrated (
                        id TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        retrieved_at TEXT NOT NULL,
                        sha256 TEXT NOT NULL UNIQUE,
                        byte_count INTEGER NOT NULL,
                        http_status INTEGER,
                        content_type TEXT,
                        license TEXT,
                        file_path TEXT NOT NULL,
                        record_status TEXT NOT NULL DEFAULT 'verified',
                        notes TEXT,
                        record_type TEXT NOT NULL DEFAULT 'download',
                        parent_ids TEXT,
                        transform_script TEXT,
                        transform_script_sha256 TEXT
                    );
                """)
                conn.execute("""
                    INSERT INTO evidence_records_migrated 
                    SELECT id, url, retrieved_at, sha256, byte_count, http_status,
                           content_type, license, file_path, record_status, notes,
                           COALESCE(record_type, 'download'), parent_ids, transform_script, transform_script_sha256
                    FROM evidence_records;
                """)
                conn.execute("DROP TABLE evidence_records;")
                conn.execute("ALTER TABLE evidence_records_migrated RENAME TO evidence_records;")
                cur = conn.execute("PRAGMA table_info(evidence_records);")
                col_info = {row["name"]: dict(row) for row in cur.fetchall()}

            columns = list(col_info.keys())
            if "record_type" not in columns:
                conn.execute("ALTER TABLE evidence_records ADD COLUMN record_type TEXT NOT NULL DEFAULT 'download';")
            if "parent_ids" not in columns:
                conn.execute("ALTER TABLE evidence_records ADD COLUMN parent_ids TEXT;")
            if "transform_script" not in columns:
                conn.execute("ALTER TABLE evidence_records ADD COLUMN transform_script TEXT;")
            if "transform_script_sha256" not in columns:
                conn.execute("ALTER TABLE evidence_records ADD COLUMN transform_script_sha256 TEXT;")
            conn.commit()

    def add_record(self, record: LedgerRecord) -> None:
        """Insert a verified download or derived record into the ledger."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evidence_records (
                    id, url, retrieved_at, sha256, byte_count, http_status,
                    content_type, license, file_path, record_status, notes,
                    record_type, parent_ids, transform_script, transform_script_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                record.notes,
                record.record_type,
                record.parent_ids,
                record.transform_script,
                record.transform_script_sha256
            ))
            conn.commit()

    def add_derived_record(
        self,
        file_path: Path,
        parent_paths: List[Path],
        transform_script: Path,
        license_name: str,
        notes: str = ""
    ) -> LedgerRecord:
        """Register a derived table linked directly to its verified raw parent downloads."""
        file_path = Path(file_path)
        transform_script = Path(transform_script)
        if not file_path.exists():
            raise FileNotFoundError(f"Derived file not found: {file_path}")
        if not transform_script.exists():
            raise FileNotFoundError(f"Transform script not found: {transform_script}")

        # Compute hashes
        file_sha = compute_sha256(file_path)
        script_sha = compute_sha256(transform_script)

        # Verify each parent exists in ledger
        parent_hashes = []
        for p in parent_paths:
            p_sha = compute_sha256(Path(p))
            parent_rec = self.get_by_sha256(p_sha)
            if parent_rec is None:
                raise ValueError(f"Parent dataset '{p}' (SHA: {p_sha[:12]}...) not found in Evidence Ledger.")
            parent_hashes.append(p_sha)

        rec = LedgerRecord(
            id=file_sha[:16],
            url=f"derived://{file_path.name}",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            sha256=file_sha,
            byte_count=file_path.stat().st_size,
            http_status=None,  # Null for derived files
            content_type="text/csv" if file_path.suffix == ".csv" else "application/octet-stream",
            license=license_name,
            file_path=str(file_path),
            record_status="verified",
            notes=notes,
            record_type="derived",
            parent_ids=json.dumps(parent_hashes),
            transform_script=str(transform_script),
            transform_script_sha256=script_sha
        )
        self.add_record(rec)
        return rec

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

    def verify_file(self, file_path: Union[str, Path]) -> Optional[LedgerRecord]:
        """Verify that a physical file on disk matches a verified ledger entry."""
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            return None
        file_sha256 = compute_sha256(file_path)
        return self.get_by_sha256(file_sha256)

    def verify_derived_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Verify that a derived table has a verified record and all its parents trace to verified records."""
        rec = self.verify_file(file_path)
        if rec is None:
            return False, f"File '{file_path}' has no verified ledger record."
        if rec.record_type != "derived":
            return False, f"File '{file_path}' is not registered as a derived table (record_type={rec.record_type})."
        if not rec.parent_ids:
            return False, f"Derived file '{file_path}' has no parent_ids recorded."
        
        try:
            parents = json.loads(rec.parent_ids)
        except Exception:
            return False, f"Invalid parent_ids JSON: {rec.parent_ids}"

        for p_sha in parents:
            p_rec = self.get_by_sha256(p_sha)
            if p_rec is None:
                return False, f"Parent record {p_sha[:12]}... is missing from Evidence Ledger."
        return True, None

    def list_records(self, status: str = "verified") -> List[LedgerRecord]:
        """List all records with matching status."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM evidence_records WHERE record_status = ? ORDER BY retrieved_at ASC",
                (status,)
            )
            return [LedgerRecord(**dict(r)) for r in cur.fetchall()]

    def export_parquet(self, output_path: Union[str, Path]) -> Path:
        """Export ledger contents to Parquet for immutable archival audit."""
        output_path = Path(output_path)
        records = self.list_records(status="verified")
        data = [asdict(r) for r in records]
        df = pd.DataFrame(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        return output_path
